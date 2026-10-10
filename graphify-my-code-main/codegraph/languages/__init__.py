"""Language registry + cached tree-sitter parsers."""
from __future__ import annotations

from tree_sitter import Language, Parser

_PARSERS: dict[str, Parser] = {}


def parser_for(name: str, module) -> Parser:
    """Return a cached Parser for a tree-sitter language module.

    `module` is e.g. `tree_sitter_java` (pip wheel); we deliberately use the
    individual language wheels, not tree-sitter-language-pack (which hangs on
    macOS arm64 with tree-sitter 0.25.x).
    """
    if name not in _PARSERS:
        _PARSERS[name] = Parser(Language(module.language()))
    return _PARSERS[name]
