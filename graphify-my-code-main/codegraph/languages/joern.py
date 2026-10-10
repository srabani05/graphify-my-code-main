"""Joern engine (deep mode): CPG-based Java extraction.

Hybrid by design: Joern owns .java (precise, type-resolved call graph from
the Code Property Graph); tree-sitter still handles MyBatis XML (and Python)
via the normal extract path.

Requires Joern on PATH and JAVA_HOME set, e.g.:
    export JAVA_HOME=~/workspace/joern-spike/jdk21
    export PATH=$JAVA_HOME/bin:~/workspace/joern-spike/joern/joern-cli:$PATH

Pipeline per repo:
    joern-parse <repo> --language javasrc --output <work>/<repo>.cpg.bin
    joern --script <baked joern_dump.sc>     -> JSONL dump of the CPG
    parse dump -> entities.jsonl / edges.jsonl (same schema as tree-sitter)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..model import Edge, Entity
from ..sqltables import tables_in_sql
from .java import MAPPINGS, MYBATIS_ANNOS, STEREOTYPES

DUMP_SC = Path(__file__).with_name("joern_dump.sc").read_text()
_STR = re.compile(r'"((?:[^"\\]|\\.)*)"')


def check() -> None:
    if not os.environ.get("JAVA_HOME"):
        raise RuntimeError("joern engine needs JAVA_HOME set "
                           "(e.g. ~/workspace/joern-spike/jdk21)")
    for bin_ in ("joern-parse", "joern"):
        if shutil.which(bin_) is None:
            raise RuntimeError(
                f"joern engine needs '{bin_}' on PATH "
                "(e.g. ~/workspace/joern-spike/joern/joern-cli)")


def _q(fullname: str) -> str:
    """Strip Joern's :signature suffix -> our qualified name."""
    return (fullname or "").split(":")[0]


def _first_str(code: str) -> str | None:
    m = _STR.search(code or "")
    return m.group(1) if m else None


def _pair(code: str, key: str) -> str | None:
    m = re.search(rf"{key}\s*=\s*\"((?:[^\"\\]|\\.)*)\"", code or "")
    return m.group(1) if m else None


def _parse_and_dump(input_path: Path, cpg: Path, dump: Path) -> None:
    """Run joern-parse + the dump script; raises on failure."""
    if cpg.exists():
        cpg.unlink()
    r = subprocess.run(
        ["joern-parse", str(input_path), "--language", "javasrc",
         "--output", str(cpg)],
        capture_output=True, text=True, timeout=1800)
    if not cpg.exists():
        raise RuntimeError(
            f"joern-parse failed for {input_path}:\n{r.stderr[-2000:]}")
    sc = DUMP_SC.replace("__CPG__", str(cpg)).replace("__OUT__", str(dump))
    sc_path = dump.with_suffix(".sc")
    sc_path.write_text(sc)
    if dump.exists():
        dump.unlink()
    r = subprocess.run(["joern", "--script", str(sc_path)],
                       capture_output=True, text=True, timeout=1800)
    if not dump.exists():
        raise RuntimeError(
            f"joern dump failed for {input_path}:\n{r.stderr[-2000:]}")


def extract_repo(repo_path: str, out_dir: str, workdir: str | None = None) -> dict:
    check()
    repo = Path(repo_path).resolve()
    name = repo.name
    dest = Path(out_dir) / name
    dest.mkdir(parents=True, exist_ok=True)
    work = Path(workdir or Path(out_dir) / ".joern-work")
    work.mkdir(parents=True, exist_ok=True)

    # joern-parse skips **/test/** relative to its input root, so mirror
    # src/test to a temp dir with the segment renamed, parse that, and map
    # the dump paths back (build.py resolves cross-references between runs).
    runs: list[tuple[Path, str]] = [(repo, "")]
    tmp_mirrors: list[Path] = []
    test_dir = repo / "src" / "test"
    if test_dir.is_dir():
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="cg-joern-test-"))
        tmp_mirrors.append(tmp)
        mirror = tmp / "src" / "__cgtest__"
        shutil.copytree(test_dir, mirror)
        runs.append((mirror, "src/test/"))
    dumps: list[tuple[Path, str]] = []
    try:
        for i, (inp, prefix) in enumerate(runs):
            cpg = work / f"{name}.cpg{i}.bin"
            dump = work / f"{name}.dump{i}.jsonl"
            _parse_and_dump(inp, cpg, dump)
            dumps.append((dump, prefix))
            try:
                cpg.unlink()  # CPGs are big; the dump is what we keep
            except OSError:
                pass
    finally:
        for tmp in tmp_mirrors:
            shutil.rmtree(tmp, ignore_errors=True)

    entities: dict[str, Entity] = {}
    edges: list[Edge] = []
    files: dict[str, Entity] = {}          # dump file key -> file entity
    methods: dict[str, Entity] = {}        # qualified -> method entity
    ann_by_method: dict[str, list[dict]] = {}
    ann_by_type: dict[str, list[dict]] = {}

    def file_of(dump_key: str, prefix: str) -> Entity | None:
        if not dump_key or dump_key == "<empty>":
            return None
        key = prefix + dump_key
        if key in files:
            return files[key]
        p = repo / key
        try:
            rel = str(p.resolve().relative_to(repo))
        except ValueError:
            return None
        f = Entity(id=f"{name}::{rel}", kind="file", name=rel.split("/")[-1],
                   qualified=rel, repo=name, rel=rel, path=str(p),
                   lang="java", line=1, extra="")
        files[key] = f
        entities[f.id] = f
        return f

    n = {"type": 0, "member": 0, "method": 0, "call": 0}
    for dump, prefix in dumps:
        with open(dump) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                t = d["t"]
                if t == "type":
                    qn = d["fullName"]
                    f = file_of(d["file"], prefix)
                    if not f or not qn:
                        continue
                    e = Entity(id=f"{name}::{qn}", kind="class", name=d["name"],
                               qualified=qn, repo=name, rel=f.rel, path=f.path,
                               lang="java", line=d["line"], extra="")
                    entities[e.id] = e
                    edges.append(Edge(src=f.id, dst=e.id, type="CONTAINS",
                                      resolved=True))
                    for s in (d.get("super") or "").split(","):
                        s = s.strip()
                        if s and s != "java.lang.Object":
                            edges.append(Edge(src=e.id, dst=None, type="EXTENDS",
                                              raw=f"joern:{s}"))
                    n["type"] += 1
                elif t == "member":
                    owner, mname = d["owner"], d["name"]
                    if not owner or not mname:
                        continue
                    f = file_of(d["file"], prefix)
                    if not f:
                        continue
                    e = Entity(id=f"{name}::{owner}.{mname}", kind="field",
                               name=mname, qualified=f"{owner}.{mname}",
                               repo=name, rel=f.rel, path=f.path, lang="java",
                               line=d["line"], extra=d.get("type", ""))
                    entities[e.id] = e
                    pe = entities.get(f"{name}::{owner}")
                    if pe:
                        edges.append(Edge(src=pe.id, dst=e.id, type="CONTAINS",
                                          resolved=True))
                    n["member"] += 1
                elif t == "method":
                    qn = _q(d["fullName"])
                    cls = d.get("class") or ""
                    simple = cls.split(".")[-1]
                    mname = simple if d["name"] == "<init>" else d["name"]
                    if not qn:
                        continue
                    f = file_of(d["file"], prefix)
                    if not f:
                        continue
                    sig = d["fullName"].split(":", 1)[1] if ":" in d["fullName"] else ""
                    e = Entity(id=f"{name}::{qn}", kind="method", name=mname,
                               qualified=qn, repo=name, rel=f.rel, path=f.path,
                               lang="java", line=d["line"], signature=sig,
                               extra="")
                    entities[e.id] = e
                    methods[qn] = e
                    pe = entities.get(f"{name}::{cls}")
                    edges.append(Edge(src=(pe.id if pe else f.id), dst=e.id,
                                      type="CONTAINS", resolved=True))
                    n["method"] += 1
                elif t == "call":
                    caller = _q(d["caller"])
                    callee = _q(d["callee"])
                    ce = methods.get(caller)
                    if not ce:
                        continue
                    if callee and "." in callee:
                        edges.append(Edge(src=ce.id, dst=None, type="CALLS",
                                          raw=f"joern:{callee}"))
                    elif d["name"]:
                        edges.append(Edge(src=ce.id, dst=None, type="CALLS",
                                          raw=d["name"]))
                    if d["name"] in ("convertAndSend", "send"):
                        queue = _first_str(d.get("code"))
                        if queue:
                            edges.append(Edge(src=ce.id, dst=None, type="SENDS",
                                              raw=queue))
                    n["call"] += 1
                elif t == "annotation":
                    an = {"name": d["name"], "code": d["code"]}
                    if d.get("method"):
                        ann_by_method.setdefault(_q(d["method"]), []).append(an)
                    elif d.get("type"):
                        ann_by_type.setdefault(d["type"], []).append(an)

    # -- framework layer from annotations ---------------------------------
    class_base: dict[str, str] = {}
    for tqn, anns in ann_by_type.items():
        te = entities.get(f"{name}::{tqn}")
        strs = []
        for a in anns:
            if a["name"] == "RequestMapping":
                s = _first_str(a["code"])
                if s:
                    strs.append(s)
        if strs and te:
            class_base[te.id] = strs[0]
        if te:
            sts = [a["name"] for a in anns if a["name"] in STEREOTYPES]
            if sts:
                te.extra = (te.extra + " " if te.extra else "") + \
                    "stereotype:" + ",".join(sts)
    for mqn, anns in ann_by_method.items():
        me = methods.get(mqn)
        if not me:
            continue
        pe_id = next((e.src for e in edges
                      if e.type == "CONTAINS" and e.dst == me.id), None)
        base = class_base.get(pe_id or "", "")
        for a in anns:
            aname, code = a["name"], a["code"]
            if aname in MAPPINGS:
                verb = MAPPINGS[aname]
                if aname == "RequestMapping":
                    m = _pair(code, "method")
                    if m:
                        verb = m.split(".")[-1]
                p = _first_str(code) or ""
                full = (base.rstrip("/") + "/" + p.lstrip("/")).rstrip("/") or "/"
                ep = Entity(
                    id=f"{me.id}::endpoint:{verb}:{full}", kind="endpoint",
                    name=f"{verb} {full}", qualified=f"{verb} {full}",
                    repo=name, rel=me.rel, path=me.path, lang="java",
                    line=me.line,
                    extra=entities[pe_id].qualified if pe_id and pe_id in entities else "")
                entities[ep.id] = ep
                edges.append(Edge(src=me.id, dst=ep.id, type="SERVES",
                                  resolved=True))
            elif aname == "JmsListener":
                queue = _pair(code, "destination") or _first_str(code)
                if queue:
                    edges.append(Edge(src=me.id, dst=None, type="LISTENS",
                                      raw=queue))
            elif aname in MYBATIS_ANNOS:
                sql = " ".join(_STR.findall(code or ""))
                for op, tbl in tables_in_sql(sql):
                    edges.append(Edge(src=me.id, dst=None, type="ACCESSES",
                                      raw=f"{op}:{tbl}"))

    # file package extras (for build.py file contexts)
    for f in files.values():
        pkgs = {e.qualified.rsplit(".", 1)[0]
                for e in entities.values()
                if e.kind == "class" and e.rel == f.rel and "." in e.qualified}
        if pkgs:
            f.extra = sorted(pkgs, key=len)[0]
            f.qualified = f.extra

    with open(dest / "entities.jsonl", "w") as fe, \
            open(dest / "edges.jsonl", "w") as fg:
        for e in entities.values():
            fe.write(json.dumps(e.to_dict()) + "\n")
        for e in edges:
            fg.write(json.dumps(e.to_dict()) + "\n")
    meta = {"repo": name, "root": str(repo), "langs": ["java"],
            "engine": "joern",
            "files_indexed": len(files),
            "indexed_at": datetime.now(timezone.utc).isoformat()}
    (dest / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta
