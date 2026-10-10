"""Crude-but-useful table-name extraction from MyBatis SQL text."""
from __future__ import annotations

import re

_PATTERNS = [
    ("SELECT", re.compile(r"\bfrom\s+[`\"]?([\w$.]+)[`\"]?", re.IGNORECASE)),
    ("SELECT", re.compile(r"\bjoin\s+[`\"]?([\w$.]+)[`\"]?", re.IGNORECASE)),
    ("UPDATE", re.compile(r"\bupdate\s+[`\"]?([\w$.]+)[`\"]?", re.IGNORECASE)),
    ("INSERT", re.compile(r"\binsert\s+into\s+[`\"]?([\w$.]+)[`\"]?", re.IGNORECASE)),
    ("DELETE", re.compile(r"\bdelete\s+from\s+[`\"]?([\w$.]+)[`\"]?", re.IGNORECASE)),
]

_KEYWORDS = {"select", "where", "set", "values", "dual", "lateral"}


def tables_in_sql(sql: str) -> list[tuple[str, str]]:
    """Return [(op, table)] found in SQL text. MyBatis #{...}/${...} tolerated."""
    sql = re.sub(r"#\{[^}]*\}|\$\{[^}]*\}", "?", sql)
    out: list[tuple[str, str]] = []
    seen = set()
    for op, pat in _PATTERNS:
        for m in pat.finditer(sql):
            tbl = m.group(1).strip("`\"").split(".")[-1]
            if tbl.lower() in _KEYWORDS or not tbl:
                continue
            key = (op, tbl)
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out
