"""Layer 4 — query: Cypher-backed API + LLM-ready context dumps."""
from __future__ import annotations

import json
from pathlib import Path

from .store import open_db


class CodeGraph:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.db, self.conn = open_db(db_path)
        self.unresolved: dict[str, list[dict]] = {}
        un = Path(self.db_path).with_suffix(".unresolved.jsonl")
        if un.exists():
            for line in un.read_text().splitlines():
                if line.strip():
                    u = json.loads(line)
                    self.unresolved.setdefault(u["src"], []).append(u)
        self.summaries: dict[str, str] = {}
        sm = Path(self.db_path).with_suffix(".summaries.jsonl")
        if sm.exists():
            for line in sm.read_text().splitlines():
                if line.strip():
                    s = json.loads(line)
                    self.summaries[s["qualified"]] = s["summary"]

    def close(self):
        self.db.close()

    # -- low level ------------------------------------------------------
    def _rows(self, cypher: str, params: dict | None = None) -> list[dict]:
        res = self.conn.execute(cypher, params or {})
        cols = res.get_column_names() if hasattr(res, "get_column_names") else []
        out = []
        while res.has_next():
            row = res.get_next()
            out.append(dict(zip(cols, row)) if cols else {"v": row})
        return out

    def cypher(self, q: str, params: dict | None = None) -> list[dict]:
        """Passthrough for arbitrary Cypher."""
        return self._rows(q, params)

    # -- lookups --------------------------------------------------------
    def find(self, name: str, kind: str | None = None, limit: int = 20) -> list[dict]:
        q = "MATCH (e:Entity) WHERE lower(e.name) CONTAINS lower($pat)"
        params: dict = {"pat": name, "lim": limit}
        if kind:
            q += " AND e.kind = $kind"
            params["kind"] = kind
        q += " RETURN e.id AS id, e.kind AS kind, e.name AS name, e.qualified AS qualified, e.repo AS repo LIMIT $lim"
        return self._rows(q, params)

    def get(self, qualified: str) -> list[dict]:
        return self._rows(
            "MATCH (e:Entity) WHERE e.qualified = $q RETURN "
            "e.id AS id, e.kind AS kind, e.name AS name, e.qualified AS qualified, "
            "e.repo AS repo, e.rel AS rel, e.path AS path, e.lang AS lang, "
            "e.line AS line, e.end_line AS end_line, e.signature AS signature, "
            "e.extra AS extra LIMIT 25", {"q": qualified})

    def stats(self) -> dict:
        from .store import REL_COLS
        s = {}
        s["entities"] = self._rows("MATCH (e:Entity) RETURN COUNT(*) AS c")[0]["c"]
        for rel in REL_COLS:
            s[rel] = self._rows(f"MATCH ()-[r:{rel}]->() RETURN COUNT(*) AS c")[0]["c"]
        s["repos"] = [r["repo"] for r in self._rows(
            "MATCH (e:Entity) RETURN DISTINCT e.repo AS repo")]
        s["unresolved_refs"] = sum(len(v) for v in self.unresolved.values())
        return s

    # -- graph traversals -----------------------------------------------
    def _neighbors(self, qualified: str, rel: str, direction: str, depth: int) -> list[dict]:
        arrow = {"out": "-[r:REL*1..D]->", "in": "<-[r:REL*1..D]-"}[direction]
        arrow = arrow.replace("REL", rel).replace("D", str(depth))
        return self._rows(
            f"MATCH (a:Entity {{qualified: $q}}){arrow}(b:Entity) "
            "RETURN DISTINCT b.qualified AS qualified, b.kind AS kind, "
            "b.repo AS repo, b.rel AS rel LIMIT 200",
            {"q": qualified})

    def callers(self, qualified: str, depth: int = 1) -> list[dict]:
        return self._neighbors(qualified, "CALLS", "in", depth)

    def callees(self, qualified: str, depth: int = 1) -> list[dict]:
        return self._neighbors(qualified, "CALLS", "out", depth)

    def impact(self, qualified: str, depth: int = 4) -> list[dict]:
        """Transitive callers — 'what breaks if I change this'."""
        return self._neighbors(qualified, "CALLS", "in", depth)

    def dependencies(self, qualified: str) -> list[dict]:
        """What a file/module/class imports."""
        return self._rows(
            "MATCH (a:Entity {qualified: $q})-[r:IMPORTS]->(b:Entity) "
            "RETURN DISTINCT b.qualified AS qualified, b.kind AS kind, r.raw AS raw LIMIT 200",
            {"q": qualified})

    def dependents(self, qualified: str) -> list[dict]:
        """Who imports a module/class."""
        return self._rows(
            "MATCH (a:Entity)-[r:IMPORTS]->(b:Entity {qualified: $q}) "
            "RETURN DISTINCT a.qualified AS qualified, a.kind AS kind, a.repo AS repo LIMIT 200",
            {"q": qualified})

    def trace(self, src_q: str, dst_q: str, max_depth: int = 6) -> list[dict]:
        """Shortest CALLS paths between two qualified names (Python BFS)."""
        src = self._rows("MATCH (e:Entity {qualified: $q}) RETURN e.id AS id",
                         {"q": src_q})
        dst = self._rows("MATCH (e:Entity {qualified: $q}) RETURN e.id AS id",
                         {"q": dst_q})
        if not src or not dst:
            return []
        src_id, dst_id = src[0]["id"], {r["id"] for r in dst}
        adj: dict[str, list[str]] = {}
        for r in self._rows("MATCH (a:Entity)-[:CALLS]->(b:Entity) "
                            "RETURN a.id AS s, b.id AS t"):
            adj.setdefault(r["s"], []).append(r["t"])
        qname = {r["id"]: r["q"] for r in self._rows(
            "MATCH (e:Entity) RETURN e.id AS id, e.qualified AS q")}
        paths, seen, frontier = [], {src_id}, [[src_id]]
        while frontier and len(paths) < 5:
            nxt = []
            for p in frontier:
                for t in adj.get(p[-1], []):
                    if t in dst_id:
                        paths.append([qname.get(i, i) for i in p + [t]])
                    elif t not in seen and len(p) < max_depth:
                        seen.add(t)
                        nxt.append(p + [t])
            frontier = nxt
        return [{"path": p, "len": len(p) - 1} for p in paths]

    # -- framework dimensions (Spring / MyBatis / JMS) --------------------
    def endpoints(self, repo: str | None = None) -> list[dict]:
        q = "MATCH (e:Entity) WHERE e.kind = 'endpoint'"
        params: dict = {}
        if repo:
            q += " AND e.repo = $repo"
            params["repo"] = repo
        q += " RETURN e.qualified AS endpoint, e.extra AS handler LIMIT 500"
        return self._rows(q, params)

    def queues(self) -> list[dict]:
        return self._rows(
            "MATCH (q:Entity) WHERE q.kind = 'queue' "
            "RETURN q.qualified AS queue, q.repo AS repo LIMIT 200")

    def tables(self) -> list[dict]:
        return self._rows(
            "MATCH (t:Entity) WHERE t.kind = 'table' "
            "RETURN t.qualified AS tbl, t.repo AS repo LIMIT 500")

    def table_writers(self, table: str) -> list[dict]:
        return self._rows(
            "MATCH (m:Entity)-[r:ACCESSES]->(t:Entity {qualified: $t, kind: 'table'}) "
            "RETURN m.qualified AS method, r.op AS op, m.repo AS repo LIMIT 200",
            {"t": table})

    def queue_flow(self, queue: str) -> dict:
        return {
            "senders": self._rows(
                "MATCH (m:Entity)-[:SENDS]->(q:Entity {qualified: $q, kind: 'queue'}) "
                "RETURN m.qualified AS sender LIMIT 200", {"q": queue}),
            "listeners": self._rows(
                "MATCH (m:Entity)-[:LISTENS]->(q:Entity {qualified: $q, kind: 'queue'}) "
                "RETURN m.qualified AS listener LIMIT 200", {"q": queue}),
        }

    # -- LLM context ------------------------------------------------------
    def _snippet(self, eid: str, max_lines: int = 80) -> str:
        rows = self._rows("MATCH (e:Entity {id: $id}) RETURN e.path AS p, e.line AS l, e.end_line AS el",
                          {"id": eid})
        if not rows:
            return ""
        p, l, el = rows[0]["p"], rows[0]["l"], rows[0]["el"]
        try:
            lines = Path(p).read_text(errors="replace").splitlines()
        except OSError:
            return ""
        lo, hi = max(0, (l or 1) - 1), min(len(lines), (el or l or 1) + 1)
        body = lines[lo:hi][:max_lines]
        lang = rows and self._rows("MATCH (e:Entity {id: $id}) RETURN e.lang AS g", {"id": eid})
        fence = (lang[0]["g"] if lang else "")
        return f"```{fence}\n" + "\n".join(body) + "\n```"

    def context(self, qualified: str, depth: int = 1, max_nodes: int = 60) -> str:
        """Render everything an LLM needs to reason about one entity."""
        ents = self.get(qualified)
        if not ents:
            return f"# {qualified}\n\nNot found in the graph."
        e = ents[0]
        out = [f"# {e['qualified']}",
               f"kind: {e['kind']} | repo: {e['repo']} | file: {e['rel']}:{e['line']}-{e['end_line']}"]
        if e.get("signature"):
            out.append(f"signature: `{e['signature']}`")
        if qualified in self.summaries:
            out.append(f"\n## Summary (LLM)\n{self.summaries[qualified]}")
        callers = self.callers(qualified, depth)[:max_nodes]
        callees = self.callees(qualified, depth)[:max_nodes]
        out.append(f"\n## Called by ({len(callers)})")
        out += [f"- {c['qualified']} [{c['kind']}]" for c in callers] or ["- (none)"]
        out.append(f"\n## Calls ({len(callees)})")
        out += [f"- {c['qualified']} [{c['kind']}]" for c in callees] or ["- (none)"]
        unres = [u for u in self.unresolved.get(e["id"], []) if u["type"] == "CALLS"]
        if unres:
            out.append(f"\n## Unresolved calls ({len(unres)})")
            out += [f"- {u['raw']}" for u in unres[:20]]
        served = self._rows(
            "MATCH (m:Entity {id: $id})-[:SERVES]->(ep:Entity) "
            "RETURN ep.qualified AS ep LIMIT 50", {"id": e["id"]})
        if served:
            out.append("\n## REST endpoints served")
            out += [f"- {r['ep']}" for r in served]
        acc = self._rows(
            "MATCH (m:Entity {id: $id})-[r:ACCESSES]->(t:Entity) "
            "RETURN r.op AS op, t.qualified AS tbl LIMIT 50", {"id": e["id"]})
        if acc:
            out.append("\n## Tables accessed")
            out += [f"- {r['op']} {r['tbl']}" for r in acc]
        mq = self._rows(
            "MATCH (m:Entity {id: $id})-[:SENDS|LISTENS]->(q:Entity) "
            "RETURN q.qualified AS q LIMIT 50", {"id": e["id"]})
        if mq:
            out.append("\n## Messaging")
            out += [f"- {r['q']}" for r in mq]
        if e["kind"] in ("method", "function", "class"):
            out.append("\n## Source")
            out.append(self._snippet(e["id"]))
        return "\n".join(out)
