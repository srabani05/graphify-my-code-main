"""Layer 1 — extract: walk repos, tree-sitter parse, emit JSONL per repo."""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .languages import java as java_ext
from .languages import python as python_ext
from .languages import mybatis as mybatis_ext

EXTRACTORS = {
    ".java": ("java", java_ext.extract),
    ".py": ("python", python_ext.extract),
}

SKIP_DIRS = {
    ".git", ".hg", ".svn", "target", "build", "out", "dist",
    "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode",
}


def _fp(p: Path):
    """Cheap file fingerprint: (mtime_ns, size). None if unreadable."""
    try:
        st = p.stat()
        return [st.st_mtime_ns, st.st_size]
    except OSError:
        return None


def _rel_of_edge(e: dict) -> str:
    parts = (e.get("src") or "").split("::")
    return parts[1] if len(parts) >= 2 else ""


def _prune_jsonl(dest: Path, drop: set[str]) -> None:
    """Drop entities/edges belonging to repo-relative paths in `drop`."""
    if not drop:
        return
    for fn, rel_of in (("entities.jsonl", lambda e: e.get("rel", "")),
                       ("edges.jsonl", _rel_of_edge)):
        p = dest / fn
        if not p.exists():
            continue
        kept = []
        with open(p) as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rel_of(e) not in drop:
                    kept.append(line)
        with open(p, "w") as fh:
            fh.writelines(kept)


def _iter_files(repo: Path, langs: set[str]):
    exts = {e for e, (l, _) in EXTRACTORS.items() if l in langs}
    want_mybatis = True  # XML mappers ride along with java
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            p = Path(root) / fn
            if p.suffix in exts or (want_mybatis and p.suffix == ".xml"
                                    and p.stem.endswith("Mapper")):
                yield p


def _index_one(repo_name: str, repo_root: str, path: str):
    """Worker: extract one file. Returns dicts (picklable)."""
    from .languages import java as jx
    from .languages import python as px
    from .languages import mybatis as mx
    ext_map = {".java": ("java", jx.extract), ".py": ("python", px.extract)}
    p = Path(path)
    rel = str(p.relative_to(repo_root))
    if p.suffix == ".xml" and p.stem.endswith("Mapper"):
        lang, fn = "mybatis", mx.extract
    else:
        lang, fn = ext_map[p.suffix]
    try:
        src = p.read_bytes()
    except OSError:
        return {"file": rel, "error": "unreadable", "entities": [], "edges": []}
    if b"\x00" in src[:8192]:
        return {"file": rel, "error": "binary", "entities": [], "edges": []}
    try:
        ents, edges = fn(repo_name, rel, str(p), src)
    except Exception as ex:  # never let one bad file kill the run
        return {"file": rel, "error": f"parse: {ex}", "entities": [], "edges": []}
    return {
        "file": rel,
        "entities": [asdict(e) for e in ents],
        "edges": [asdict(e) for e in edges],
    }


def index_repo(repo_path: str, out_dir: str, langs=("java", "python"), workers: int | None = None,
               engine: str = "treesitter", incremental: bool = False):
    """Index one repo -> {out_dir}/{repo_name}/{entities,edges}.jsonl + meta.json.

    incremental=True: only (re)parse files whose mtime/size changed since the
    last run (tracked in .extract-state.json); entities/edges of changed or
    deleted files are pruned from the JSONL before appending the fresh ones.
    """
    repo = Path(repo_path).resolve()
    name = repo.name
    dest = Path(out_dir) / name
    dest.mkdir(parents=True, exist_ok=True)
    state_path = dest / ".extract-state.json"

    prev: dict = {}
    if incremental and state_path.exists():
        try:
            prev = json.loads(state_path.read_text())
        except (OSError, json.JSONDecodeError):
            prev = {}
    full = not incremental or not prev or prev.get("engine") != engine
    prev_files: dict = {} if full else prev.get("files", {})
    final_fps: dict[str, list] = {}

    # -- joern java pass (whole-repo CPG; re-run only if a .java changed) --
    joern_meta = None
    if engine == "joern" and "java" in langs:
        from .languages import joern as joern_ext
        java_files = [p for p in _iter_files(repo, {"java"}) if p.suffix == ".java"]
        java_cur = {str(p.relative_to(repo)): _fp(p) for p in java_files}
        changed = {r for r, fp in java_cur.items()
                   if fp is None or prev_files.get(r) != fp}
        removed = {r for r in prev_files
                   if r.endswith(".java") and r not in java_cur}
        if full or changed or removed:
            if not full:
                _prune_jsonl(dest, {r for r in prev_files if r.endswith(".java")})
            joern_meta = joern_ext.extract_repo(str(repo), out_dir)
            print(f"  joern deep scan: {len(changed)} java changed, "
                  f"{len(removed)} removed")
        else:
            print("  joern deep scan: no java changes, skipped")
            joern_meta = {"repo": name, "root": str(repo), "langs": ["java"],
                          "engine": "joern", "files_indexed": len(java_cur)}
        langs = tuple(l for l in langs if l != "java")  # rest via tree-sitter
        final_fps.update({r: fp for r, fp in java_cur.items() if fp})

    # -- tree-sitter pass --
    files = list(_iter_files(repo, set(langs)))
    cur = {str(p.relative_to(repo)): _fp(p) for p in files}
    if full:
        # joern already wrote fresh files with "w"; otherwise start clean
        if not joern_meta and (dest / "entities.jsonl").exists():
            (dest / "entities.jsonl").unlink()
            (dest / "edges.jsonl").unlink(missing_ok=True)
        todo, drop = files, set()
    else:
        todo = [p for p in files
                if cur[str(p.relative_to(repo))] is None
                or prev_files.get(str(p.relative_to(repo))) != cur[str(p.relative_to(repo))]]
        drop = ({r for r in prev_files if r not in cur and r not in final_fps}
                | {str(p.relative_to(repo)) for p in todo})
        _prune_jsonl(dest, drop)
        n_removed = len([r for r in drop
                         if r not in {str(p.relative_to(repo)) for p in todo}])
        print(f"  tree-sitter: {len(todo)} files changed, {n_removed} removed")

    n_ok, n_err = 0, 0
    ok_rels: set[str] = set()
    mode = "a" if (dest / "entities.jsonl").exists() else "w"
    with ProcessPoolExecutor(max_workers=workers or (os.cpu_count() or 4)) as ex:
        futs = [ex.submit(_index_one, name, str(repo), str(p)) for p in todo]
        with open(dest / "entities.jsonl", mode) as fe, \
                open(dest / "edges.jsonl", mode) as fg:
            for fut in futs:
                r = fut.result()
                if r.get("error"):
                    n_err += 1
                    continue
                n_ok += 1
                ok_rels.add(r["file"])
                for e in r["entities"]:
                    fe.write(json.dumps(e) + "\n")
                for e in r["edges"]:
                    fg.write(json.dumps(e) + "\n")
    for r in ok_rels:
        if cur.get(r):
            final_fps[r] = cur[r]
    for r, fp in prev_files.items():
        if r not in drop and r not in final_fps and fp:
            final_fps[r] = fp
    state_path.write_text(json.dumps({
        "engine": engine, "files": final_fps,
        "updated_at": datetime.now(timezone.utc).isoformat()}))

    n_unchanged = len(files) - len(todo)
    meta = {
        "repo": name, "root": str(repo), "langs": list(langs),
        "engine": engine if not joern_meta else "joern",
        "files_indexed": n_ok + n_unchanged + (joern_meta["files_indexed"] if joern_meta else 0),
        "files_reparsed": n_ok, "files_skipped": n_err,
        "incremental": incremental and not full,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def index_repos(repo_paths: list[str], out_dir: str, langs=("java", "python"),
                workers: int | None = None, engine: str = "treesitter",
                incremental: bool = False):
    metas = []
    for rp in repo_paths:
        m = index_repo(rp, out_dir, langs=langs, workers=workers,
                       engine=engine, incremental=incremental)
        print(f"indexed {m['repo']}: {m['files_indexed']} files "
              f"({m.get('files_reparsed', m['files_indexed'])} reparsed, "
              f"{m.get('files_skipped', 0)} skipped) [{m.get('engine', engine)}]")
        metas.append(m)
    return metas
