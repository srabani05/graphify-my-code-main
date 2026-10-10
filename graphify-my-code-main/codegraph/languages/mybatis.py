"""MyBatis mapper-XML extractor: namespace + statement ids + table accesses."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from ..model import Edge, Entity
from ..sqltables import tables_in_sql

STMT_TAGS = {"select": "SELECT", "insert": "INSERT", "update": "UPDATE", "delete": "DELETE"}


def extract(repo: str, rel: str, path: str, src: bytes):
    ents: list[Entity] = []
    edges: list[Edge] = []
    file_id = f"{repo}::{rel}"
    try:
        root = ET.fromstring(src)
    except ET.ParseError:
        return ents, edges
    if root.tag != "mapper":
        return ents, edges
    namespace = root.attrib.get("namespace", "")
    f = Entity(id=file_id, kind="file", name=rel.split("/")[-1],
               qualified=namespace or rel, repo=repo, rel=rel, path=path,
               lang="mybatis", line=1, signature="", extra=namespace)
    ents.append(f)
    for stmt in root:
        tag = stmt.tag.split("}")[-1]
        if tag not in STMT_TAGS:
            continue
        sid = stmt.attrib.get("id", "")
        if not sid:
            continue
        q = f"{namespace}.{sid}" if namespace else sid
        mid = f"{file_id}::{sid}"
        ents.append(Entity(id=mid, kind="method", name=sid, qualified=q,
                           repo=repo, rel=rel, path=path, lang="mybatis",
                           line=0, signature="", extra=namespace))
        edges.append(Edge(src=file_id, dst=mid, type="CONTAINS", resolved=True))
        sql = "".join(stmt.itertext())
        for op, tbl in tables_in_sql(sql):
            edges.append(Edge(src=mid, dst=None, type="ACCESSES",
                              raw=f"{op}:{tbl}"))
    return ents, edges
