"""Python extractor: tree-sitter -> entities + edges.

Captures: imports (incl. from-imports), classes (with bases), functions/methods,
and every call expression as a CALLS edge (resolved later by build.py).
"""
from __future__ import annotations

import tree_sitter_python as tspython

from . import parser_for
from ..model import Edge, Entity


def _text(node, src: bytes) -> str:
    if node is None:
        return ""
    return src[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _child_by_type(node, *types):
    for c in node.named_children:
        if c.type in types:
            return c
    return None


def _module_name(rel: str) -> str:
    p = rel[:-3] if rel.endswith(".py") else rel  # strip .py
    parts = p.split("/")
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


class _Walker:
    def __init__(self, repo: str, rel: str, path: str, src: bytes):
        self.repo, self.rel, self.path, self.src = repo, rel, path, src
        self.ents: list[Entity] = []
        self.edges: list[Edge] = []
        self.file_id = f"{repo}::{rel}"
        self.module = _module_name(rel)
        self.class_stack: list[Entity] = []
        self.caller_stack: list[str] = []
        self.imports: list[str] = []

    def _add(self, e: Entity) -> Entity:
        self.ents.append(e)
        return e

    def _contains(self, parent_id: str, child: Entity):
        self.edges.append(Edge(src=parent_id, dst=child.id, type="CONTAINS", resolved=True))

    def run(self):
        parser = parser_for("python", tspython)
        root = parser.parse(self.src).root_node
        f = self._add(Entity(
            id=self.file_id, kind="file", name=self.rel.split("/")[-1],
            qualified=self.module, repo=self.repo, rel=self.rel,
            path=self.path, lang="python", line=1,
            signature="", extra=self.module,
        ))
        for ch in root.named_children:
            self._visit(ch, f.id, self.module)
        return self.ents, self.edges

    # -- dispatch -------------------------------------------------------
    def _visit(self, node, parent_id: str, scope_q: str):
        t = node.type
        if t in ("import_statement", "import_from_statement"):
            self._visit_import(node, parent_id)
        elif t == "class_definition":
            self._visit_class(node, parent_id, scope_q)
        elif t == "function_definition":
            self._visit_function(node, parent_id, scope_q)
        elif t == "decorated_definition":
            for ch in node.named_children:
                self._visit(ch, parent_id, scope_q)
        elif t == "expression_statement":
            self._visit_generic(node)
        else:
            self._visit_generic(node)

    def _visit_generic(self, node):
        for ch in node.named_children:
            if ch.type == "call":
                self._visit_call(ch)
            else:
                # recurse manually to keep caller context for nested calls
                self._recurse(ch)

    def _recurse(self, node):
        for ch in node.named_children:
            if ch.type == "call":
                self._visit_call(ch)
            else:
                self._recurse(ch)

    # -- imports --------------------------------------------------------
    def _visit_import(self, node, file_id: str):
        if node.type == "import_statement":
            for ch in node.named_children:
                if ch.type == "dotted_name":
                    raw = _text(ch, self.src)
                    self.imports.append(raw)
                    self.edges.append(Edge(src=file_id, dst=None, type="IMPORTS", raw=raw))
                elif ch.type == "aliased_import":
                    dn = _child_by_type(ch, "dotted_name")
                    raw = _text(dn, self.src)
                    if raw:
                        self.imports.append(raw)
                        self.edges.append(Edge(src=file_id, dst=None, type="IMPORTS", raw=raw))
        else:  # import_from_statement
            mod = node.child_by_field_name("module_name")
            mod_s = _text(mod, self.src)
            level = sum(1 for c in node.children if not c.is_named and c.type == ".")
            if level and not mod_s:
                mod_s = "." * level
            names = []
            for ch in node.named_children:
                if ch.type == "dotted_name" and ch is not mod:
                    names.append(_text(ch, self.src))
                elif ch.type == "aliased_import":
                    dn = _child_by_type(ch, "dotted_name")
                    if dn is not None:
                        names.append(_text(dn, self.src))
                elif ch.type == "wildcard_import":
                    names.append("*")
            for n in names:
                raw = f"{mod_s}.{n}" if mod_s else n
                self.imports.append(raw)
                self.edges.append(Edge(src=file_id, dst=None, type="IMPORTS", raw=raw))

    # -- classes / functions --------------------------------------------
    def _visit_class(self, node, parent_id: str, scope_q: str):
        name = _text(node.child_by_field_name("name"), self.src)
        if not name:
            return
        q = f"{scope_q}.{name}"
        eid = f"{parent_id}::{name}"
        e = self._add(Entity(
            id=eid, kind="class", name=name, qualified=q,
            repo=self.repo, rel=self.rel, path=self.path, lang="python",
            line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            signature="", extra=self.module,
        ))
        self._contains(parent_id, e)
        # bases -> EXTENDS
        sup = node.child_by_field_name("superclasses")
        if sup is not None:
            for arg in sup.named_children:
                raw = _text(arg, self.src)
                if raw and raw not in ("object",):
                    self.edges.append(Edge(src=eid, dst=None, type="EXTENDS", raw=raw))
        self.class_stack.append(e)
        body = node.child_by_field_name("body")
        if body is not None:
            for ch in body.named_children:
                self._visit(ch, eid, q)
        self.class_stack.pop()

    def _visit_function(self, node, parent_id: str, scope_q: str):
        name = _text(node.child_by_field_name("name"), self.src)
        if not name:
            return
        params = node.child_by_field_name("parameters")
        sig = _text(params, self.src)
        kind = "method" if self.class_stack and parent_id == self.class_stack[-1].id else "function"
        q = f"{scope_q}.{name}"
        eid = f"{parent_id}::{name}"
        e = self._add(Entity(
            id=eid, kind=kind, name=name, qualified=q,
            repo=self.repo, rel=self.rel, path=self.path, lang="python",
            line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            signature=sig, extra=self.module,
        ))
        self._contains(parent_id, e)
        self.caller_stack.append(eid)
        body = node.child_by_field_name("body")
        if body is not None:
            self._recurse(body)
        self.caller_stack.pop()

    # -- calls ----------------------------------------------------------
    def _current_caller(self) -> str:
        if self.caller_stack:
            return self.caller_stack[-1]
        if self.class_stack:
            return self.class_stack[-1].id
        return self.file_id

    def _visit_call(self, node):
        fn = node.child_by_field_name("function")
        raw = ""
        if fn is not None:
            if fn.type == "identifier":
                raw = _text(fn, self.src)
            elif fn.type == "attribute":
                obj = _text(fn.child_by_field_name("object"), self.src)
                attr = _text(fn.child_by_field_name("attribute"), self.src)
                if obj == "self":
                    obj = ""
                raw = f"{obj}.{attr}" if obj else attr
        if raw:
            self.edges.append(Edge(src=self._current_caller(), dst=None,
                                   type="CALLS", raw=raw))
        # recurse into arguments (nested calls)
        args = node.child_by_field_name("arguments")
        if args is not None:
            self._recurse(args)


def extract(repo: str, rel: str, path: str, src: bytes):
    """Extract entities/edges from one Python file. Returns (entities, edges)."""
    w = _Walker(repo, rel, path, src)
    return w.run()
