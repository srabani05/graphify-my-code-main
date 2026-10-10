"""Shared entity/edge model for the extract layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Entity:
    id: str            # f"{repo}::{relpath}[::Class][::method/nparams]"
    kind: str          # file | package | class | interface | enum | method | function | module | doc | external
    name: str
    qualified: str     # java: pkg.Class.method | python: mod.Class.func
    repo: str
    rel: str           # repo-relative path
    path: str          # absolute path (for snippet reads)
    lang: str = ""
    line: int = 0
    end_line: int = 0
    signature: str = ""
    extra: str = ""    # package / module dotted name for files

    def to_dict(self):
        return asdict(self)


@dataclass
class Edge:
    src: str
    dst: str | None    # None until the build layer resolves it
    type: str          # CONTAINS | CALLS | IMPORTS | EXTENDS | IMPLEMENTS | MENTIONS
    raw: str = ""      # unresolved textual reference
    resolved: bool = False

    def to_dict(self):
        return asdict(self)
