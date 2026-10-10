"""Layer 2 (merge) — resolve cross-file/cross-repo references, load Kuzu.

Resolution strategy (pragmatic, not compiler-precise):
  1. intra-file / same scope (method -> sibling method, this./self.)
  2. same package / module
  3. explicit imports (incl. cross-repo via qualified-name index)
  4. otherwise: dotted imports become `external` stubs; bare calls stay in
     unresolved.jsonl (still visible to the query layer).
"""
from __future__ import annotations

import csv
import json
import shutil
import tempfile
from pathlib import Path

from .store import ENTITY_COLS, copy_csvs, create_schema, open_db

CLASS_KINDS = {"class", "interface", "enum", "record", "annotation"}
CALLABLE_KINDS = {"method", "function"}


class Index:
    def __init__(self):
        self.ent = {}               # id -> entity dict
        self.class_qname = {}       # "pkg.Class" -> [ids]
        self.member = {}            # (scope_qname, member_name) -> [ids]
        self.file_ctx = {}          # file_id -> {"repo","package","imports",...}
        self.parent = {}            # child_id -> parent_id (CONTAINS)
        self.externals = {}         # raw -> entity dict
        self.var_types = {}         # method/class id -> {var_name: type_raw}

    def add_entity(self, e: dict):
        self.ent[e["id"]] = e
        q = e.get("qualified", "")
        if e["kind"] in CLASS_KINDS and q:
            self.class_qname.setdefault(q, []).append(e["id"])
        if e["kind"] in CALLABLE_KINDS and q and "." in q:
            scope, _, name = q.rpartition(".")
            self.member.setdefault((scope, name), []).append(e["id"])

    def index_vars(self):
        """Second pass (needs parent map): field + parameter type tables."""
        for e in self.ent.values():
            if e["kind"] == "field":
                owner = self.parent.get(e["id"], "")
                self.var_types.setdefault(owner, {})[e["name"]] = e.get("extra", "")
            elif e["kind"] in CALLABLE_KINDS and e.get("extra"):
                d = {}
                for part in e["extra"].split(","):
                    if ":" in part:
                        n, t = part.split(":", 1)
                        d[n.strip()] = t.strip()
                if d:
                    self.var_types[e["id"]] = d

    def enclosing_class(self, eid: str) -> str:
        cur = eid
        while cur in self.parent:
            cur = self.parent[cur]
            e = self.ent.get(cur)
            if e and e["kind"] in CLASS_KINDS:
                return cur
        return ""

    def scope_of(self, eid: str) -> str:
        """Enclosing class qualified name, else module/package, else ''."""
        cur = eid
        while cur in self.parent:
            cur = self.parent[cur]
            e = self.ent.get(cur)
            if not e:
                break
            if e["kind"] in CLASS_KINDS:
                return e.get("qualified", "")
        f = self.file_of(eid)
        fe = self.ent.get(f)
        return (fe or {}).get("extra", "") or ""

    def file_of(self, eid: str) -> str:
        cur = eid
        while cur in self.parent:
            cur = self.parent[cur]
        return cur


def _load(data_dir: Path):
    entities, edges = [], []
    for repo_dir in sorted(data_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        ef, gf = repo_dir / "entities.jsonl", repo_dir / "edges.jsonl"
        if ef.exists():
            entities += [json.loads(l) for l in ef.read_text().splitlines() if l.strip()]
        if gf.exists():
            edges += [json.loads(l) for l in gf.read_text().splitlines() if l.strip()]
    return entities, edges


def _strip_generics(raw: str) -> str:
    return raw.split("<")[0].strip()


def _resolve_class(idx: Index, raw: str, file_id: str) -> list[str]:
    """Resolve a class-ish raw name to entity ids."""
    raw = _strip_generics(raw)
    if not raw:
        return []
    ctx = idx.file_ctx.get(file_id, {})
    pkg = ctx.get("package", "")
    cands: list[str] = []
    if "." in raw and not raw.endswith(".*"):
        cands.append(raw)
    else:
        short = raw[:-2] if raw.endswith(".*") else raw
        if pkg:
            cands.append(f"{pkg}.{short}")
        for imp in ctx.get("imports", []):
            if imp.endswith(".*"):
                cands.append(f"{imp[:-2]}.{short}")
            elif imp.split(".")[-1] == short or imp == short:
                cands.append(imp)
    out = []
    for c in cands:
        out += idx.class_qname.get(c, [])
    return out


def _infra_entity(idx: Index, kind: str, name: str, file_id: str) -> str:
    """Get-or-create a queue/table node scoped to the source file's repo."""
    repo = (idx.ent.get(file_id) or {}).get("repo", "")
    key = (kind, repo, name)
    if not hasattr(idx, "_infra"):
        idx._infra = {}
    if key not in idx._infra:
        eid = f"{kind}::{repo}::{name}"
        idx._infra[key] = eid
        idx.add_entity({
            "id": eid, "kind": kind, "name": name, "qualified": name,
            "repo": repo, "rel": "", "path": "", "lang": "",
            "line": 0, "end_line": 0, "signature": "", "extra": "",
        })
    return idx._infra[key]


def _external(idx: Index, raw: str) -> str:
    if raw not in idx.externals:
        eid = f"external::{raw}"
        idx.externals[raw] = {
            "id": eid, "kind": "external", "name": raw.split(".")[-1],
            "qualified": raw, "repo": "external", "rel": "", "path": "",
            "lang": "", "line": 0, "end_line": 0, "signature": "", "extra": "",
        }
    return idx.externals[raw]["id"]


def build(data_dir: str, db_path: str) -> dict:
    data_dir = Path(data_dir)
    entities, edges = _load(data_dir)
    idx = Index()
    for e in entities:
        idx.add_entity(e)

    # file contexts + parent map (CONTAINS edges are pre-resolved)
    contains, calls, imports, extends, implements = [], [], [], [], []
    serves, accesses, sends, listens = [], [], [], []
    unresolved = []
    raw_others = []  # CALLS/IMPORTS/EXTENDS/IMPLEMENTS with dst=None
    for ed in edges:
        t = ed["type"]
        if t == "CONTAINS":
            contains.append(ed)
            idx.parent[ed["dst"]] = ed["src"]
        elif t == "SERVES":
            serves.append(ed)  # endpoints resolved at extract time
        else:
            raw_others.append(ed)
    for e in entities:
        if e["kind"] == "file":
            fctx = {"repo": e["repo"], "package": e.get("extra", ""), "imports": []}
            idx.file_ctx[e["id"]] = fctx
    for ed in raw_others:
        if ed["type"] == "IMPORTS":
            fctx = idx.file_ctx.get(ed["src"])
            if fctx is not None:
                fctx["imports"].append(ed["raw"])
    idx.index_vars()

    # -- resolve -------------------------------------------------------
    for ed in raw_others:
        t, src, raw = ed["type"], ed["src"], ed["raw"]
        file_id = idx.file_of(src)
        if t == "IMPORTS":
            done = _resolve_import(idx, src, raw, imports, unresolved)
        elif t in ("EXTENDS", "IMPLEMENTS"):
            if raw.startswith("joern:"):
                qn = raw[len("joern:"):]
                ids = idx.class_qname.get(qn, [])
                if ids:
                    (extends if t == "EXTENDS" else implements).extend(
                        {"src": src, "dst": i} for i in ids)
                elif "." in qn:
                    dst = _external(idx, qn)
                    (extends if t == "EXTENDS" else implements).append(
                        {"src": src, "dst": dst})
                else:
                    unresolved.append({"src": src, "type": t, "raw": raw})
            else:
                ids = _resolve_class(idx, raw, file_id)
                if ids:
                    (extends if t == "EXTENDS" else implements).extend(
                        {"src": src, "dst": i} for i in ids)
                elif "." in _strip_generics(raw):
                    dst = _external(idx, _strip_generics(raw))
                    (extends if t == "EXTENDS" else implements).append({"src": src, "dst": dst})
                else:
                    unresolved.append({"src": src, "type": t, "raw": raw})
        elif t == "CALLS":
            if raw.startswith("joern:"):
                # Joern pre-resolved callee: direct qualified lookup
                qn = raw[len("joern:"):]
                scope, _, mname = qn.rpartition(".")
                ids = idx.member.get((scope, mname), [])
                if ids:
                    calls.extend({"src": src, "dst": i, "raw": raw} for i in ids)
                elif scope and ("." in scope or scope.startswith("<")
                                or scope == "ANY"):
                    # JDK types and Joern's <unresolvedNamespace> markers ->
                    # external stubs keep the graph connected
                    calls.append({"src": src, "dst": _external(idx, qn),
                                  "raw": raw})
                elif scope not in ("void", ""):
                    unresolved.append({"src": src, "type": t, "raw": raw})
                # else: joern:void.<init> and friends carry no information
            else:
                _resolve_call(idx, src, file_id, raw, calls, unresolved)
        elif t in ("LISTENS", "SENDS"):
            qid = _infra_entity(idx, "queue", raw, file_id)
            (listens if t == "LISTENS" else sends).append({"src": src, "dst": qid})
        elif t == "ACCESSES":
            op, _, tbl = raw.partition(":")
            tid = _infra_entity(idx, "table", tbl or raw, file_id)
            accesses.append({"src": src, "dst": tid, "op": op or "?"})
    for raw, stub in idx.externals.items():
        idx.add_entity(stub)

    # -- emit CSVs ------------------------------------------------------
    from .store import REL_COLS
    edge_lists = {
        "CONTAINS": contains, "CALLS": calls, "IMPORTS": imports,
        "EXTENDS": extends, "IMPLEMENTS": implements,
        "SERVES": serves, "ACCESSES": accesses,
        "SENDS": sends, "LISTENS": listens, "MENTIONS": [],
    }
    tmp = Path(tempfile.mkdtemp(prefix="codegraph-"))
    try:
        with open(tmp / "entities.csv", "w", newline="") as f:
            w = csv.writer(f)
            for e in idx.ent.values():
                w.writerow([_clean(e.get(c, "")) for c in ENTITY_COLS])
        for rel, lst in edge_lists.items():
            _write_edges(tmp / f"{rel.lower()}.csv", lst, REL_COLS[rel])

        dbp = Path(db_path)
        if dbp.is_dir():
            shutil.rmtree(dbp)
        elif dbp.exists():
            dbp.unlink()
        db, conn = open_db(dbp)
        create_schema(conn)
        counts = copy_csvs(conn, tmp)
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    un_path = Path(str(db_path)).with_suffix(".unresolved.jsonl")
    with open(un_path, "w") as f:
        for u in unresolved:
            f.write(json.dumps(u) + "\n")
    counts["unresolved"] = len(unresolved)
    counts["repos"] = len([d for d in data_dir.iterdir() if d.is_dir()])
    return counts


def _write_edges(path: Path, edges: list[dict], cols: list[str]):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        for e in edges:
            w.writerow([_clean(e.get(c, "")) for c in cols])


def _clean(v) -> str:
    if v is None:
        return ""
    return str(v).replace("\r", " ").replace("\n", " ")


def _resolve_import(idx: Index, src: str, raw: str, imports: list, unresolved: list) -> bool:
    raw = raw.strip()
    if not raw or raw.endswith(".*"):
        unresolved.append({"src": src, "type": "IMPORTS", "raw": raw})
        return False
    file_id = idx.file_of(src)
    ctx = idx.file_ctx.get(file_id, {})
    # direct class hit
    ids = idx.class_qname.get(_strip_generics(raw), [])
    if ids:
        imports.extend({"src": src, "dst": i, "raw": raw} for i in ids)
        return True
    # python: "a.b.c.Name" -> try progressively shorter module prefixes
    parts = raw.split(".")
    for n in range(len(parts) - 1, 0, -1):
        mod = ".".join(parts[:n])
        fid = next((i for (r, m), i in
                    ((k, v) for k, v in _module_index(idx).items())
                    if m == mod and r == ctx.get("repo")), None)
        if fid:
            imports.append({"src": src, "dst": fid, "raw": raw})
            return True
    if "." in raw:  # third-party / stdlib -> external stub
        imports.append({"src": src, "dst": _external(idx, raw), "raw": raw})
        return True
    unresolved.append({"src": src, "type": "IMPORTS", "raw": raw})
    return False


def _module_index(idx: Index):
    if not hasattr(idx, "_mod_idx"):
        idx._mod_idx = {(e["repo"], e["extra"]): e["id"]
                        for e in idx.ent.values()
                        if e["kind"] == "file" and e.get("extra")}
    return idx._mod_idx


def _resolve_call(idx: Index, src: str, file_id: str, raw: str,
                  calls: list, unresolved: list):
    raw = raw.strip()
    if not raw:
        return
    if "." in raw:
        recv, _, name = raw.rpartition(".")
    else:
        recv, name = "", raw
    if recv == "this" or recv == "self":
        recv = ""
    elif recv.startswith("this.") or recv.startswith("self."):
        recv = recv.split(".", 1)[1]  # this.owners -> owners (field/param lookup)
    scope = idx.scope_of(src)

    # constructor call -> link to the class entity
    if name == "<init>":
        ids = _resolve_class(idx, recv, file_id)
        for i in ids:
            calls.append({"src": src, "dst": i, "raw": raw})
        if not ids:
            if recv[:1].isupper():
                calls.append({"src": src, "dst": _external(idx, recv), "raw": raw})
            else:
                unresolved.append({"src": src, "type": "CALLS", "raw": raw})
        return

    targets: list[str] = []
    ctx = idx.file_ctx.get(file_id, {})
    if recv in ("", "this", "self"):
        targets = idx.member.get((scope, name), [])
    else:
        for cid in _resolve_class(idx, recv, file_id):
            ce = idx.ent[cid]
            targets += idx.member.get((ce.get("qualified", ""), name), [])
        if not targets and "." not in recv and recv[:1].islower():
            # receiver is a variable -> look up its declared type
            vtype = (idx.var_types.get(src, {}).get(recv)
                     or idx.var_types.get(idx.enclosing_class(src), {}).get(recv))
            if vtype:
                for cid in _resolve_class(idx, vtype, file_id):
                    ce = idx.ent[cid]
                    targets += idx.member.get((ce.get("qualified", ""), name), [])
        if not targets and "." not in recv:
            # maybe recv is a module: mod.func
            for (s, n), ids in idx.member.items():
                if n == name and (s == recv or s.endswith("." + recv)):
                    targets += ids
    if not targets and not recv:
        # bare name imported from elsewhere: from billing.pricing import calc_total
        for imp in ctx.get("imports", []):
            if imp.endswith(".*") or "." not in imp:
                continue
            mscope, _, mname = imp.rpartition(".")
            if mname == name:
                targets += idx.member.get((mscope, name), [])
    # de-dupe, drop self-loops
    seen = set()
    for t in targets:
        if t != src and t not in seen:
            seen.add(t)
            calls.append({"src": src, "dst": t, "raw": raw})
    if not seen:
        if recv and "." in recv and recv.split(".")[0][:1].isupper():
            # Type-like dotted receiver (System.out.println) -> external stub
            calls.append({"src": src, "dst": _external(idx, raw), "raw": raw})
        else:
            unresolved.append({"src": src, "type": "CALLS", "raw": raw})
