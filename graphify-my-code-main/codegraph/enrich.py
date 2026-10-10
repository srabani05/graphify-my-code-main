"""Layer 3 — enrich: link docs/design notes to code entities (MENTIONS)."""
from __future__ import annotations

from pathlib import Path

DOC_EXTS = {".md", ".rst", ".txt", ".adoc"}


def enrich(db_path: str, docs_dir: str) -> dict:
    from .query import CodeGraph
    from .model import Entity

    g = CodeGraph(db_path)
    try:
        classes = g.cypher(
            "MATCH (e:Entity) WHERE e.kind IN ['class','interface','enum'] "
            "RETURN e.id AS id, e.qualified AS q")
        doc_files = [p for p in Path(docs_dir).rglob("*")
                     if p.suffix.lower() in DOC_EXTS and p.is_file()]
        n_docs, n_edges = 0, 0
        for dp in doc_files:
            try:
                text = dp.read_text(errors="replace")
            except OSError:
                continue
            rel = str(dp.relative_to(docs_dir))
            did = f"docs::{rel}"
            g.conn.execute(
                "MERGE (d:Entity {id: $id}) SET d.kind='doc', d.name=$n, "
                "d.qualified=$n, d.repo='docs', d.rel=$r, d.path=$p",
                {"id": did, "n": dp.name, "r": rel, "p": str(dp)})
            n_docs += 1
            for c in classes:
                q = c["q"]
                if q and len(q) > 3 and q in text:
                    g.conn.execute(
                        "MATCH (d:Entity {id: $did}), (e:Entity {id: $eid}) "
                        "MERGE (d)-[:MENTIONS]->(e)",
                        {"did": did, "eid": c["id"]})
                    n_edges += 1
        return {"docs": n_docs, "mentions": n_edges}
    finally:
        g.close()
