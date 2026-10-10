"""codegraph CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_extract(a):
    from .extract import index_repos
    metas = index_repos(a.repos, a.out, langs=tuple(a.langs.split(",")),
                        workers=a.workers, engine=a.engine,
                        incremental=a.incremental)
    print(json.dumps(metas, indent=2))


def cmd_build(a):
    from .build import build
    counts = build(a.data, a.db)
    print(json.dumps(counts, indent=2))


def cmd_enrich(a):
    from .enrich import enrich
    print(json.dumps(enrich(a.db, a.docs), indent=2))


def cmd_stats(a):
    from .query import CodeGraph
    g = CodeGraph(a.db)
    try:
        print(json.dumps(g.stats(), indent=2))
    finally:
        g.close()


def cmd_query(a):
    from .query import CodeGraph
    g = CodeGraph(a.db)
    try:
        op = a.op
        if op == "callers":
            rows = g.callers(a.target, a.depth)
        elif op == "callees":
            rows = g.callees(a.target, a.depth)
        elif op == "impact":
            rows = g.impact(a.target, a.depth)
        elif op == "deps":
            rows = g.dependencies(a.target)
        elif op == "dependents":
            rows = g.dependents(a.target)
        elif op == "trace":
            rows = g.trace(a.target, a.target2, a.depth)
        elif op == "find":
            rows = g.find(a.target, limit=a.limit)
        else:
            raise SystemExit(f"unknown op: {op}")
        print(json.dumps(rows, indent=2))
    finally:
        g.close()


def cmd_context(a):
    from .query import CodeGraph
    g = CodeGraph(a.db)
    try:
        md = g.context(a.target, depth=a.depth)
        if a.out:
            open(a.out, "w").write(md)
            print(f"wrote {a.out}")
        else:
            print(md)
    finally:
        g.close()


def cmd_ask(a):
    from .query import CodeGraph
    from .llm import ask_with_context, config_from_env
    cfg = config_from_env()
    g = CodeGraph(a.db)
    try:
        # keyword candidates: match entity names against question tokens
        toks = [t.strip("?,.'\"()") for t in a.question.split() if len(t) > 3]
        seen, parts = set(), []
        for t in toks[:6]:
            for c in g.find(t, limit=3):
                q = c["qualified"]
                if q not in seen:
                    seen.add(q)
                    parts.append(g.context(q, depth=1))
                    if len(parts) >= a.top_k:
                        break
            if len(parts) >= a.top_k:
                break
        context_md = "\n\n---\n\n".join(parts) if parts else "(no matching entities found)"
        print(f"[codegraph] grounding on {len(parts)} entit(ies), asking {cfg.model} ...",
              file=sys.stderr)
        print(ask_with_context(cfg, a.question, context_md))
    finally:
        g.close()


def cmd_cypher(a):
    from .query import CodeGraph
    g = CodeGraph(a.db)
    try:
        print(json.dumps(g.cypher(a.query), indent=2))
    finally:
        g.close()


def cmd_summarize(a):
    from .lastmile import summarize
    print(json.dumps(summarize(a.db, qualified_names=a.entities or None,
                               top_n=a.top_n, all_entities=a.all), indent=2))


def cmd_prd(a):
    from .lastmile import prd
    text = prd(a.db, a.requirement)
    if a.out:
        Path(a.out).write_text(text + "\n")
        print(f"wrote {a.out}")
    else:
        print(text)


def cmd_design(a):
    from .lastmile import design
    prd_text = Path(a.prd).read_text() if a.prd else None
    text = design(a.db, a.requirement, prd_text)
    if a.out:
        Path(a.out).write_text(text + "\n")
        print(f"wrote {a.out}")
    else:
        print(text)


def main(argv=None):
    p = argparse.ArgumentParser(prog="codegraph",
                                description="Multi-layer code knowledge-graph pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="Layer 1: parse repos -> JSONL")
    e.add_argument("--repos", nargs="+", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--langs", default="java,python")
    e.add_argument("--workers", type=int, default=None)
    e.add_argument("--engine", default="treesitter", choices=["treesitter", "joern"],
                   help="joern: CPG-based deep mode for Java (needs Joern+JAVA_HOME); "
                        "tree-sitter still handles MyBatis XML/Python")
    e.add_argument("--incremental", action="store_true",
                   help="only re-parse files changed since the last extract "
                        "(state in <out>/<repo>/.extract-state.json)")
    e.set_defaults(fn=cmd_extract)

    b = sub.add_parser("build", help="Layer 2: merge + resolve -> Kuzu DB")
    b.add_argument("--data", required=True)
    b.add_argument("--db", required=True)
    b.set_defaults(fn=cmd_build)

    n = sub.add_parser("enrich", help="Layer 3: link docs -> code (MENTIONS)")
    n.add_argument("--db", required=True)
    n.add_argument("--docs", required=True)
    n.set_defaults(fn=cmd_enrich)

    s = sub.add_parser("stats", help="DB stats")
    s.add_argument("--db", required=True)
    s.set_defaults(fn=cmd_stats)

    q = sub.add_parser("query", help="callers|callees|impact|deps|dependents|trace|find")
    q.add_argument("op")
    q.add_argument("target")
    q.add_argument("target2", nargs="?")
    q.add_argument("--db", required=True)
    q.add_argument("--depth", type=int, default=2)
    q.add_argument("--limit", type=int, default=20)
    q.set_defaults(fn=cmd_query)

    c = sub.add_parser("context", help="LLM-ready markdown dump for one entity")
    c.add_argument("target")
    c.add_argument("--db", required=True)
    c.add_argument("--depth", type=int, default=1)
    c.add_argument("--out", default=None)
    c.set_defaults(fn=cmd_context)

    k = sub.add_parser("ask", help="Ask the graph via an LLM (needs CODEGRAPH_LLM_URL)")
    k.add_argument("question")
    k.add_argument("--db", required=True)
    k.add_argument("--top-k", type=int, default=4)
    k.set_defaults(fn=cmd_ask)

    y = sub.add_parser("cypher", help="Raw Cypher passthrough")
    y.add_argument("query")
    y.add_argument("--db", required=True)
    y.set_defaults(fn=cmd_cypher)

    z = sub.add_parser("summarize",
                       help="Last mile (optional): LLM summaries for key entities")
    z.add_argument("--db", required=True)
    z.add_argument("--top-n", type=int, default=20)
    z.add_argument("--all", action="store_true",
                   help="all methods+classes except mappers, pojos, framework/test code")
    z.add_argument("entities", nargs="*", help="qualified names (default: top by fan-in)")
    z.set_defaults(fn=cmd_summarize)

    pr = sub.add_parser("prd",
                        help="Last mile (optional): one-line requirement -> one-page PRD, grounded in the graph")
    pr.add_argument("--db", required=True)
    pr.add_argument("--requirement", required=True, help="the one-line requirement")
    pr.add_argument("--out", default=None, help="write markdown to this file")
    pr.set_defaults(fn=cmd_prd)

    d = sub.add_parser("design",
                       help="Last mile (optional): requirement -> HLD + LLD, grounded in the graph")
    d.add_argument("--db", required=True)
    d.add_argument("--requirement", required=True, help="the one-line requirement")
    d.add_argument("--prd", default=None, help="approved PRD markdown file to design from")
    d.add_argument("--out", default=None, help="write markdown to this file")
    d.set_defaults(fn=cmd_design)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
