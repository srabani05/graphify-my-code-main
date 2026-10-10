"""Layer 2 (storage) — Kuzu embedded graph DB: schema + bulk load.

One generic Entity node table (kind as property) keeps the schema stable as
languages are added. Only resolved edges are stored as relationships;
unresolved references live in unresolved.jsonl next to the DB.
"""
from __future__ import annotations

import csv
from pathlib import Path

import kuzu

SCHEMA = [
    """CREATE NODE TABLE Entity(
         id STRING PRIMARY KEY, kind STRING, name STRING, qualified STRING,
         repo STRING, rel STRING, path STRING, lang STRING,
         line INT64, end_line INT64, signature STRING, extra STRING)""",
    "CREATE REL TABLE CONTAINS(FROM Entity TO Entity, MANY_MANY)",
    "CREATE REL TABLE CALLS(FROM Entity TO Entity, raw STRING, MANY_MANY)",
    "CREATE REL TABLE IMPORTS(FROM Entity TO Entity, raw STRING, MANY_MANY)",
    "CREATE REL TABLE EXTENDS(FROM Entity TO Entity, MANY_MANY)",
    "CREATE REL TABLE IMPLEMENTS(FROM Entity TO Entity, MANY_MANY)",
    "CREATE REL TABLE MENTIONS(FROM Entity TO Entity, MANY_MANY)",
    "CREATE REL TABLE SERVES(FROM Entity TO Entity, MANY_MANY)",
    "CREATE REL TABLE ACCESSES(FROM Entity TO Entity, op STRING, MANY_MANY)",
    "CREATE REL TABLE SENDS(FROM Entity TO Entity, MANY_MANY)",
    "CREATE REL TABLE LISTENS(FROM Entity TO Entity, MANY_MANY)",
]

REL_COLS = {
    "CONTAINS": ["src", "dst"],
    "CALLS": ["src", "dst", "raw"],
    "IMPORTS": ["src", "dst", "raw"],
    "EXTENDS": ["src", "dst"],
    "IMPLEMENTS": ["src", "dst"],
    "MENTIONS": ["src", "dst"],
    "SERVES": ["src", "dst"],
    "ACCESSES": ["src", "dst", "op"],
    "SENDS": ["src", "dst"],
    "LISTENS": ["src", "dst"],
}

ENTITY_COLS = ["id", "kind", "name", "qualified", "repo", "rel", "path",
               "lang", "line", "end_line", "signature", "extra"]


def create_schema(conn) -> None:
    for stmt in SCHEMA:
        conn.execute(stmt)


def copy_csvs(conn, csv_dir: str | Path) -> dict:
    """COPY entities + per-type edge CSVs (no headers, fixed column order)."""
    csv_dir = Path(csv_dir)
    counts = {}
    conn.execute(f"COPY Entity FROM '{csv_dir / 'entities.csv'}'")
    counts["entities"] = conn.execute("MATCH (e:Entity) RETURN COUNT(*)").get_next()[0]
    for rel in REL_COLS:
        f = csv_dir / f"{rel.lower()}.csv"
        if not f.exists() or f.stat().st_size == 0:
            counts[rel] = 0
            continue
        conn.execute(f"COPY {rel} FROM '{f}' (HEADER=false)")
        counts[rel] = conn.execute(f"MATCH ()-[r:{rel}]->() RETURN COUNT(*)").get_next()[0]
    return counts


def open_db(db_path: str | Path):
    db_path = str(db_path)
    db = kuzu.Database(db_path)
    return db, kuzu.Connection(db)
