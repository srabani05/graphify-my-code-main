"""Last mile (optional): LLM-generated summaries for key entities.

The whole pipeline works with no LLM configured. This is the optional final
step: it reads graph context per entity, asks the LLM for a 2-3 sentence
brief, and stores results in a sidecar (<db>.summaries.jsonl) that `context`
picks up automatically.
"""
from __future__ import annotations

import json
from pathlib import Path

from .llm import chat, config_from_env
from .query import CodeGraph

import re

# -- requirement -> PRD -> design (grounded in the knowledge graph) ---------

PRD_SYSTEM = (
    "You are a principal product manager. Write a ONE-PAGE PRD grounded ONLY "
    "in the codebase facts provided below. Reference real endpoints, classes, "
    "and methods by their exact qualified names. Do not invent components, "
    "tables, queues, or integrations that are not in the facts. Structure: "
    "Problem, Users, Goals, Non-goals, Proposed behavior (mapped to real "
    "endpoints/classes), Data changes, Risks, Open questions. One page."
)

DESIGN_SYSTEM = (
    "You are a principal software architect. Write a HIGH-LEVEL DESIGN and a "
    "LOW-LEVEL DESIGN grounded ONLY in the codebase facts provided below. "
    "Reference real classes, methods, and endpoints by exact qualified name; "
    "do not invent components. HLD: components touched, new/modified "
    "endpoints, data flow, sequencing. LLD: concrete classes/methods to "
    "create or modify (with signatures), exact call chains, edge cases, "
    "tests to add. Be specific, not generic."
)

_REQ_STOPWORDS = frozenset("""
a an the and or of to in on for with by as at is are be was were will would
should could can may might must shall this that these those it its into from
out over under then than so such no not only also want wants need needs
app application system user users our we you your my our their his her
when where what which who whom how why add new existing make create update
send email daily before after during each every any all some more most other
another between through via per please like just get got gets getting set
puts put using use used uses want
""".split())


def _req_keywords(requirement: str) -> list[str]:
    words = re.findall(r"[A-Za-z]{4,}", requirement.lower())
    seen, out = set(), []
    for w in words:
        if w not in _REQ_STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def ground_requirement(db_path: str, requirement: str,
                       limit: int = 10) -> str:
    """Deterministic grounding for a requirement: keyword-matched entities
    with their graph context, plus the endpoint inventory. No LLM involved."""
    g = CodeGraph(db_path)
    try:
        kws = _req_keywords(requirement)
        hits: list[dict] = []
        seen: set[str] = set()
        for kw in kws:
            for e in g.find(kw, limit=limit):
                q = e.get("qualified") or ""
                # skip test code and framework noise in grounding
                if not q or q in seen or "Tests" in q or q.startswith("java."):
                    continue
                seen.add(q)
                hits.append(e)
                if len(hits) >= limit:
                    break
            if len(hits) >= limit:
                break
        parts = [f"REQUIREMENT: {requirement}",
                 f"KEYWORDS: {', '.join(kws)}",
                 "",
                 "== RELEVANT CODE ENTITIES (from the knowledge graph) =="]
        for e in hits:
            parts.append(g.context(e["qualified"], depth=1))
        parts.append("== REST ENDPOINT INVENTORY ==")
        for ep in g.endpoints():
            parts.append(f"{ep['endpoint']}  (handler: {ep.get('handler', '')})")
        return "\n\n".join(parts)
    finally:
        g.close()


def prd(db_path: str, requirement: str) -> str:
    """One-line requirement -> one-page PRD, grounded in the graph."""
    cfg = config_from_env()  # raises a clear error if CODEGRAPH_LLM_URL is unset
    grounding = ground_requirement(db_path, requirement)
    return chat(cfg, [
        {"role": "system", "content": PRD_SYSTEM},
        {"role": "user", "content": grounding + "\n\nWrite the one-page PRD."},
    ]).strip()


def design(db_path: str, requirement: str, prd_text: str | None = None) -> str:
    """Requirement (+ optional PRD) -> HLD + LLD, grounded in the graph."""
    cfg = config_from_env()  # raises a clear error if CODEGRAPH_LLM_URL is unset
    grounding = ground_requirement(db_path, requirement)
    if prd_text:
        grounding += "\n\n== APPROVED PRD ==\n" + prd_text
    return chat(cfg, [
        {"role": "system", "content": DESIGN_SYSTEM},
        {"role": "user", "content": grounding + "\n\nWrite the HLD and LLD."},
    ]).strip()

SUMMARY_SYSTEM = (
    "You are a senior engineer writing a codebase map. Summarize what this "
    "code entity does in 2-3 concrete sentences for a developer who has never "
    "seen this repo. Name its key collaborators (callers/callees) where it "
    "clarifies purpose. No preamble, just the summary."
)

# -- exclusions for --all -------------------------------------------------
# Framework detection is repo-relative: a class is "framework" when its
# qualified name doesn't start with any package found in the indexed repos
# (so org.springframework.samples.* is app code, org.springframework.web.* isn't).
MODEL_PKGS = (".model.", ".entity.", ".domain.", ".dto.", ".vo.", ".pojo.")
TRIVIAL_METHODS = {"equals", "hashCode", "toString", "canEqual"}


def _app_prefixes(g: CodeGraph) -> tuple[str, ...]:
    rows = g.cypher(
        "MATCH (e:Entity) WHERE e.kind = 'file' AND e.repo <> 'external' "
        "AND e.extra <> '' RETURN DISTINCT e.extra AS p")
    return tuple(p["p"] + "." for p in rows if p["p"])


def _is_trivial_method(name: str, class_name: str) -> bool:
    if not name:
        return True
    if name == class_name or name == "__init__" or name in TRIVIAL_METHODS:
        return True
    for prefix in ("get", "set"):
        if name.startswith(prefix) and len(name) > 3 and name[3].isupper():
            return True
    if name.startswith("is") and len(name) > 2 and name[2].isupper():
        return True
    return False


def _class_excluded(q: str | None, lang: str, extra: str, path: str,
                    app_prefixes: tuple[str, ...]) -> str | None:
    """Return exclusion reason, or None if the class is worth summarizing."""
    if not q:
        return "no-name"
    if (lang or "") == "mybatis":
        return "mybatis"
    if not q.startswith(app_prefixes):
        return "framework"
    cname = q.split(".")[-1]
    pkg = ".".join(q.split(".")[:-1])
    if cname.endswith("Mapper") or ".mapper." in q:
        return "mapper"
    if "stereotype:Configuration" in (extra or ""):
        return "config"
    if any(s in (extra or "") for s in ("stereotype:Entity", "stereotype:Embeddable",
                                        "stereotype:MappedSuperclass")):
        return "jpa-entity"
    if any(s in q for s in MODEL_PKGS) or pkg.split(".")[-1:] in (
            ["model"], ["entity"], ["domain"], ["dto"], ["vo"], ["pojo"]):
        return "pojo-pkg"
    if "/src/test/" in (path or "") or "/test/" in (path or ""):
        return "test"
    if cname.endswith(("Test", "Tests", "IT")):
        return "test"
    return None


def _all_targets(g: CodeGraph) -> tuple[list[str], dict[str, int]]:
    app_prefixes = _app_prefixes(g)
    classes = g.cypher(
        "MATCH (c:Entity) WHERE c.kind IN ['class','interface','enum'] "
        "OPTIONAL MATCH (c)-[:CONTAINS]->(m:Entity) "
        "WHERE m.kind IN ['method','function'] "
        "RETURN c.qualified AS q, c.lang AS lang, c.extra AS extra, "
        "c.path AS path, c.name AS name, collect(m.name) AS methods")
    callables = g.cypher(
        "MATCH (m:Entity) WHERE m.kind IN ['method','function'] "
        "OPTIONAL MATCH (c:Entity)-[:CONTAINS]->(m) "
        "WHERE c.kind IN ['class','interface','enum'] "
        "RETURN m.qualified AS mq, m.name AS mn, m.lang AS mlang, "
        "c.qualified AS cq, c.lang AS clang, c.extra AS cextra, c.path AS cpath, "
        "c.name AS cname")
    excluded: dict[str, int] = {}
    bad_classes: set[str] = set()
    good_classes: list[str] = []
    for c in classes:
        q = c["q"]
        reason = _class_excluded(q, c["lang"], c["extra"], c["path"], app_prefixes)
        if reason is None and c["methods"]:
            # pojo-by-shape: nothing but ctors/accessors
            if all(_is_trivial_method(m, c["name"]) for m in c["methods"] if m):
                reason = "pojo-shape"
        if reason is None and not c["methods"]:
            reason = "no-methods"
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            if q:
                bad_classes.add(q)
        elif q:
            good_classes.append(q)
    targets = list(good_classes)
    for r in callables:
        mq = r["mq"]
        if not mq:
            continue
        if r["cq"] and r["cq"] in bad_classes:
            excluded["via-class"] = excluded.get("via-class", 0) + 1
            continue
        if (r["mlang"] or "") == "mybatis" or not (mq or "").startswith(app_prefixes):
            excluded["framework-fn"] = excluded.get("framework-fn", 0) + 1
            continue
        if _is_trivial_method(r["mn"], r["cname"] or ""):
            excluded["trivial"] = excluded.get("trivial", 0) + 1
            continue
        targets.append(mq)
    # de-dupe, keep order
    seen, uniq = set(), []
    for t in targets:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq, excluded


def summarize(db_path: str, qualified_names: list[str] | None = None,
              top_n: int = 20, all_entities: bool = False) -> dict:
    cfg = config_from_env()  # raises a clear error if CODEGRAPH_LLM_URL is unset
    g = CodeGraph(db_path)
    try:
        excluded: dict[str, int] = {}
        if qualified_names:
            targets = qualified_names
        elif all_entities:
            targets, excluded = _all_targets(g)
            print(f"[summarize] {len(targets)} targets, excluded: {excluded}")
        else:
            rows = g.cypher(
                "MATCH (m:Entity)<-[r:CALLS]-(c:Entity) "
                "WHERE m.kind IN ['method','function'] "
                "RETURN m.qualified AS q, COUNT(*) AS n "
                "ORDER BY n DESC LIMIT $lim", {"lim": top_n})
            targets = [r["q"] for r in rows]
        summaries = {}
        for q in targets:
            ctx = g.context(q, depth=1)
            s = chat(cfg, [
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": ctx},
            ])
            summaries[q] = s.strip()
            print(f"summarized {q}")
        out = Path(str(db_path)).with_suffix(".summaries.jsonl")
        mode = "a" if out.exists() else "w"
        with open(out, mode) as f:
            for q, s in summaries.items():
                f.write(json.dumps({"qualified": q, "summary": s}) + "\n")
        return {"summarized": len(summaries), "excluded": excluded, "file": str(out)}
    finally:
        g.close()
