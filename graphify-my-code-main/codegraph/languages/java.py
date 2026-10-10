"""Java extractor: tree-sitter -> entities + edges.

Captures: package, imports, classes/interfaces/enums/records (with
extends/implements), methods/constructors (with signatures), and every method
invocation + constructor call as a CALLS edge (resolved later by build.py).
"""
from __future__ import annotations

import tree_sitter_java as tsjava

from . import parser_for
from ..model import Edge, Entity
from ..sqltables import tables_in_sql

TYPE_DECLS = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "annotation_type_declaration": "annotation",
    "record_declaration": "record",
}

STEREOTYPES = {"RestController", "Controller", "Service", "Repository",
               "Component", "Configuration", "ControllerAdvice",
               "Entity", "Table", "Embeddable", "MappedSuperclass"}

MAPPINGS = {"GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
            "DeleteMapping": "DELETE", "PatchMapping": "PATCH",
            "RequestMapping": "ANY"}

MYBATIS_ANNOS = {"Select", "Insert", "Update", "Delete"}


def _unquote(t: str) -> str:
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"'):
        return t[1:-1]
    return t


def _annotations(node, src: bytes):
    """Yield (name, args_node|None) for annotations on a declaration."""
    mods = _child_by_type(node, "modifiers")
    if mods is None:
        return
    for ch in mods.named_children:
        if ch.type == "marker_annotation":
            yield _text(ch.child_by_field_name("name"), src), None
        elif ch.type == "annotation":
            yield (_text(ch.child_by_field_name("name"), src),
                   ch.child_by_field_name("arguments"))


def _strings_in(args_node, src: bytes) -> list[str]:
    out: list[str] = []

    def rec(n):
        for c in n.named_children:
            if c.type == "string_literal":
                out.append(_unquote(_text(c, src)))
            else:
                rec(c)

    if args_node is not None:
        rec(args_node)
    return out


def _pair_value(args_node, key: str, src: bytes) -> str | None:
    def rec(n):
        for c in n.named_children:
            if c.type == "element_value_pair":
                if _text(c.child_by_field_name("key"), src) == key:
                    return _unquote(_text(c.child_by_field_name("value"), src))
            r = rec(c)
            if r is not None:
                return r
        return None

    return rec(args_node) if args_node is not None else None


def _text(node, src: bytes) -> str:
    if node is None:
        return ""
    return src[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _child_by_type(node, *types):
    for c in node.named_children:
        if c.type in types:
            return c
    return None


class _Walker:
    def __init__(self, repo: str, rel: str, path: str, src: bytes):
        self.repo, self.rel, self.path, self.src = repo, rel, path, src
        self.ents: list[Entity] = []
        self.edges: list[Edge] = []
        self.file_id = f"{repo}::{rel}"
        self.package = ""
        self.class_stack: list[Entity] = []   # enclosing types, innermost last
        self.caller_stack: list[str] = []     # enclosing method ids, innermost last
        self.imports: list[str] = []
        self._class_base: dict[str, str] = {}  # class id -> @RequestMapping base path

    # -- entity helpers -------------------------------------------------
    def _add(self, e: Entity) -> Entity:
        self.ents.append(e)
        return e

    def _contains(self, parent_id: str, child: Entity):
        self.edges.append(Edge(src=parent_id, dst=child.id, type="CONTAINS", resolved=True))

    # -- entry ----------------------------------------------------------
    def run(self):
        parser = parser_for("java", tsjava)
        root = parser.parse(self.src).root_node
        for ch in root.named_children:
            if ch.type == "package_declaration":
                ident = ch.child_by_field_name("scoped_identifier") or _child_by_type(
                    ch, "scoped_identifier", "identifier"
                )
                self.package = _text(ident, self.src)

        f = self._add(Entity(
            id=self.file_id, kind="file", name=self.rel.split("/")[-1],
            qualified=self.package or self.rel, repo=self.repo, rel=self.rel,
            path=self.path, lang="java", line=1,
            signature="", extra=self.package,
        ))
        for ch in root.named_children:
            if ch.type == "import_declaration":
                self._visit_import(ch, f)
            elif ch.type in TYPE_DECLS:
                self._visit_type(ch, f.id, None)
            else:
                self._visit_generic(ch)
        return self.ents, self.edges

    # -- imports --------------------------------------------------------
    def _visit_import(self, node, f: Entity):
        raw = (
            _text(node, self.src)
            .replace("import", "").replace("static", "").replace(";", "").strip()
        )
        self.imports.append(raw)
        self.edges.append(Edge(src=f.id, dst=None, type="IMPORTS", raw=raw))

    # -- types ----------------------------------------------------------
    def _visit_type(self, node, parent_id: str, outer_q: str | None):
        name = _text(node.child_by_field_name("name"), self.src)
        if not name:
            self._visit_generic(node)
            return
        kind = TYPE_DECLS[node.type]
        q = f"{outer_q}.{name}" if outer_q else (
            f"{self.package}.{name}" if self.package else name
        )
        eid = f"{parent_id}::{name}"
        e = self._add(Entity(
            id=eid, kind=kind, name=name, qualified=q,
            repo=self.repo, rel=self.rel, path=self.path, lang="java",
            line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            signature=_text(_child_by_type(node, "type_parameters"), self.src),
            extra=self.package,
        ))
        self._contains(parent_id, e)

        # Spring stereotypes + class-level @RequestMapping base path
        stereotypes: list[str] = []
        for aname, aargs in _annotations(node, self.src):
            if aname in STEREOTYPES:
                stereotypes.append(aname)
            elif aname == "RequestMapping":
                strs = _strings_in(aargs, self.src)
                if strs:
                    self._class_base[eid] = strs[0]
        if stereotypes:
            e.extra = (e.extra + " " if e.extra else "") + "stereotype:" + ",".join(stereotypes)

        # extends / implements (kept raw; build.py resolves)
        sup = _child_by_type(node, "superclass")
        if sup is not None:
            t = _child_by_type(sup, "type_identifier", "scoped_identifier", "generic_type")
            raw = _text(t, self.src)
            if raw:
                self.edges.append(Edge(src=eid, dst=None, type="EXTENDS", raw=raw))
        sup_if = _child_by_type(node, "super_interfaces")
        if sup_if is not None:
            tlist = _child_by_type(sup_if, "type_list") or sup_if
            for t in tlist.named_children:
                raw = _text(t, self.src)
                if raw:
                    self.edges.append(Edge(src=eid, dst=None, type="IMPLEMENTS", raw=raw))

        self.class_stack.append(e)
        body = _child_by_type(node, "class_body", "interface_body", "enum_body",
                              "annotation_type_body", "record_body") or node
        for ch in body.named_children:
            if ch.type in TYPE_DECLS:
                self._visit_type(ch, eid, q)
            elif ch.type in ("method_declaration", "constructor_declaration"):
                self._visit_method(ch, e)
            elif ch.type == "field_declaration":
                self._visit_field(ch, e)
                self._visit_generic(ch)  # initializers may contain calls
            else:
                self._visit_generic(ch)
        self.class_stack.pop()

    def _visit_field(self, node, class_e: Entity):
        tnode = next(
            (c for c in node.named_children
             if c.type != "variable_declarator" and not c.type.startswith("annotation")
             and c.type != "modifiers"),
            None,
        )
        ttext = _text(tnode, self.src)
        for vd in node.named_children:
            if vd.type != "variable_declarator":
                continue
            name = _text(vd.child_by_field_name("name"), self.src)
            if not name:
                continue
            fe = self._add(Entity(
                id=f"{class_e.id}::{name}", kind="field", name=name,
                qualified=f"{class_e.qualified}.{name}",
                repo=self.repo, rel=self.rel, path=self.path, lang="java",
                line=vd.start_point[0] + 1, end_line=vd.end_point[0] + 1,
                signature="", extra=ttext,
            ))
            self._contains(class_e.id, fe)

    # -- methods --------------------------------------------------------
    def _visit_method(self, node, class_e: Entity):
        name = _text(node.child_by_field_name("name"), self.src)
        if not name and node.type == "constructor_declaration":
            name = class_e.name
        params = _child_by_type(node, "formal_parameters")
        nparams = len(params.named_children) if params else 0
        sig = _text(params, self.src)
        ptypes = []
        if params:
            for fp in params.named_children:
                if fp.type not in ("formal_parameter", "spread_parameter"):
                    continue
                nm_node = fp.child_by_field_name("name")
                tp_node = fp.child_by_field_name("type") or next(
                    (c for c in fp.named_children if c is not nm_node), None)
                nm, tp = _text(nm_node, self.src), _text(tp_node, self.src)
                if nm and tp:
                    ptypes.append(f"{nm}:{tp}")
        q = f"{class_e.qualified}.{name}"
        eid = f"{class_e.id}::{name}/{nparams}"
        e = self._add(Entity(
            id=eid, kind="method", name=name, qualified=q,
            repo=self.repo, rel=self.rel, path=self.path, lang="java",
            line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            signature=sig, extra=",".join(ptypes),
        ))
        self._contains(class_e.id, e)
        self._scan_method_annotations(node, e, class_e)
        self.caller_stack.append(eid)
        self._visit_generic(node)
        self.caller_stack.pop()

    def _scan_method_annotations(self, node, e: Entity, class_e: Entity):
        base = self._class_base.get(class_e.id, "")
        for aname, aargs in _annotations(node, self.src):
            if aname in MAPPINGS:
                verb = MAPPINGS[aname]
                if aname == "RequestMapping":
                    m = _pair_value(aargs, "method", self.src)
                    if m:
                        verb = m.split(".")[-1]
                strs = _strings_in(aargs, self.src)
                p = strs[0] if strs else ""
                full = (base.rstrip("/") + "/" + p.lstrip("/")).rstrip("/") or "/"
                ep = self._add(Entity(
                    id=f"{e.id}::endpoint:{verb}:{full}", kind="endpoint",
                    name=f"{verb} {full}", qualified=f"{verb} {full}",
                    repo=self.repo, rel=self.rel, path=self.path, lang="java",
                    line=e.line, signature="", extra=class_e.qualified,
                ))
                self.edges.append(Edge(src=e.id, dst=ep.id, type="SERVES", resolved=True))
            elif aname == "JmsListener":
                dest = (_pair_value(aargs, "destination", self.src)
                        or (next(iter(_strings_in(aargs, self.src)), None)))
                if dest:
                    self.edges.append(Edge(src=e.id, dst=None, type="LISTENS", raw=dest))
            elif aname in MYBATIS_ANNOS:
                sql = " ".join(_strings_in(aargs, self.src))
                for op, tbl in tables_in_sql(sql):
                    self.edges.append(Edge(src=e.id, dst=None, type="ACCESSES",
                                           raw=f"{op}:{tbl}"))

    # -- calls ----------------------------------------------------------
    def _current_caller(self) -> str:
        if self.caller_stack:
            return self.caller_stack[-1]
        if self.class_stack:
            return self.class_stack[-1].id
        return self.file_id

    def _visit_invocation(self, node):
        name_node = node.child_by_field_name("name") or _child_by_type(node, "identifier")
        mname = _text(name_node, self.src)
        recv_node = node.child_by_field_name("object")
        recv = _text(recv_node, self.src)
        if recv == "this":
            recv = ""
        raw = f"{recv}.{mname}" if recv else mname
        if mname:
            self.edges.append(Edge(src=self._current_caller(), dst=None,
                                   type="CALLS", raw=raw))
            if mname in ("convertAndSend", "send"):
                # JMS send with a literal destination -> SENDS edge
                args = node.child_by_field_name("arguments")
                if args is not None:
                    for c in args.named_children:
                        if c.type == "string_literal":
                            dest = _unquote(_text(c, self.src))
                            if dest:
                                self.edges.append(Edge(
                                    src=self._current_caller(), dst=None,
                                    type="SENDS", raw=dest))
                            break
        self._visit_generic(node)

    def _visit_new(self, node):
        t = _child_by_type(node, "type_identifier", "scoped_identifier", "generic_type")
        tname = _text(t, self.src).split("<")[0].split(".")[-1]
        if tname:
            self.edges.append(Edge(src=self._current_caller(), dst=None,
                                   type="CALLS", raw=f"{tname}.<init>"))
        self._visit_generic(node)

    def _visit_generic(self, node):
        for ch in node.named_children:
            if ch.type == "method_invocation":
                self._visit_invocation(ch)
            elif ch.type == "object_creation_expression":
                self._visit_new(ch)
            else:
                self._visit_generic(ch)


def extract(repo: str, rel: str, path: str, src: bytes):
    """Extract entities/edges from one Java file. Returns (entities, edges)."""
    w = _Walker(repo, rel, path, src)
    return w.run()
