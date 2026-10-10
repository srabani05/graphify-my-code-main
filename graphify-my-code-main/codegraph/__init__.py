"""codegraph — multi-layer code knowledge-graph pipeline.

Layers:
    1. extract : tree-sitter parse of repos -> entities/edges (JSONL)
    2. build   : merge + cross-repo name resolution -> Kuzu graph DB
    3. enrich  : link docs/design notes to code entities (MENTIONS)
    4. query   : Cypher-backed query API + LLM-ready context dumps
    5. llm     : optional LLM hook over HTTP (OpenAI-compatible /v1 URL)
"""

__version__ = "0.1.0"

from .query import CodeGraph

__all__ = ["CodeGraph", "__version__"]
