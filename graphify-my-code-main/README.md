# graphify-my-code

A multi-layer pipeline that turns a pile of repos into a queryable **code
knowledge graph** for humans and LLMs. Opinionated for Java/Spring/MyBatis/JMS
codebases; Python supported too.

## Layers

| # | Layer | Command | What it does |
|---|-------|---------|--------------|
| 1 | **extract** | `codegraph extract` | tree-sitter parses every file → entities/edges as JSONL (per repo) |
| 2 | **build** | `codegraph build` | merges repos, resolves cross-file/cross-repo references → embedded Kuzu graph DB |
| 3 | **enrich** | `codegraph enrich` | links docs/design notes to code entities (`MENTIONS`) |
| 4 | **query** | `codegraph query` / `context` / `cypher` | callers, callees, impact, trace, REST endpoints, tables, queues |
| 5 | **llm** | `codegraph ask` | graph-grounded Q&A via any OpenAI-compatible HTTP endpoint |

## What's captured

- **Structure**: files, packages, classes, methods, fields, imports, extends/implements
- **Behavior**: call graph (resolved through params, fields, `this.`, imports — not just names)
- **Spring**: `@RestController`/`@Controller` → REST endpoints (`SERVES`), stereotypes
- **MyBatis**: mapper XML + `@Select`/`@Insert`/`@Update`/`@Delete` → tables accessed (`ACCESSES`)
- **JMS**: `@JmsListener` (`LISTENS`), `convertAndSend`/`send` (`SENDS`) → queues
- Unresolved references are kept in `<db>.unresolved.jsonl` — visible, not silently dropped

## Quickstart

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# 1. extract (parallel, a 30-file repo takes seconds)
.venv/bin/python -m codegraph.cli extract --repos ~/repos/billing ~/repos/orders --out ./kgdata

# 2. build the graph
.venv/bin/python -m codegraph.cli build --data ./kgdata --db ./knowledge.kuzu

# 3. (optional) link docs
.venv/bin/python -m codegraph.cli enrich --db ./knowledge.kuzu --docs ~/repos/billing/docs
```

## Querying

```bash
# who calls this method (transitive)?
.venv/bin/python -m codegraph.cli query impact --db ./knowledge.kuzu \
  com.acme.billing.InvoiceService.charge --depth 3

# call path between two methods
.venv/bin/python -m codegraph.cli query trace --db ./knowledge.kuzu \
  com.acme.web.OrderController.create com.acme.billing.InvoiceService.charge

# every REST endpoint in the graph
.venv/bin/python -m codegraph.cli cypher --db ./knowledge.kuzu \
  "MATCH (e:Entity) WHERE e.kind='endpoint' RETURN e.qualified ORDER BY 1"

# who writes to the ORDERS table?
.venv/bin/python -m codegraph.cli cypher --db ./knowledge.kuzu \
  "MATCH (m:Entity)-[r:ACCESSES]->(t:Entity {kind:'table', qualified:'ORDERS'})
   RETURN m.qualified, r.op"

# LLM-ready brief for one method (edges + source snippet)
.venv/bin/python -m codegraph.cli context --db ./knowledge.kuzu \
  com.acme.billing.InvoiceService.charge --depth 1
```

## Ask via LLM — the optional last mile

Everything above works with **no LLM configured**. The LLM is purely the last
mile: grounded Q&A and batch summaries over the graph you already built.

`ask` retrieves graph context by keyword, then calls any OpenAI-compatible
endpoint — OpenAI, Azure, Ollama, vLLM, or an internal gateway. Nothing is
vendor-locked; the URL is the only integration point.

```bash
export CODEGRAPH_LLM_URL="http://localhost:11434/v1"  # or https://api.openai.com/v1
export CODEGRAPH_LLM_KEY="sk-..."                     # omit for local servers
export CODEGRAPH_LLM_MODEL="llama3.1"                 # default: "default"

# grounded Q&A
.venv/bin/python -m codegraph.cli ask --db ./knowledge.kuzu \
  "which endpoints trigger a write to the ORDERS table?"

# batch summaries for the most-called methods -> <db>.summaries.jsonl
# (picked up automatically by `context`)
.venv/bin/python -m codegraph.cli summarize --db ./knowledge.kuzu --top-n 20

# ...or everything worth summarizing: all methods + classes EXCEPT
# mappers, pojos (by package, @Entity, or getter/setter shape), test code,
# @Configuration, framework/external code, and trivial accessors/ctors
.venv/bin/python -m codegraph.cli summarize --db ./knowledge.kuzu --all

# one-line requirement -> one-page PRD, grounded in the graph's real entities
.venv/bin/python -m codegraph.cli prd --db ./knowledge.kuzu \
  --requirement "Send email reminders to pet owners the day before a vet visit" \
  --out prd.md

# requirement (+ optional approved PRD) -> high-level + low-level design
.venv/bin/python -m codegraph.cli design --db ./knowledge.kuzu \
  --requirement "Send email reminders to pet owners the day before a vet visit" \
  --prd prd.md --out design.md
```

```bash
# multi-repo: pass several roots; build merges them into one graph
.venv/bin/python -m codegraph.cli extract --repos ~/svc-a ~/svc-b --out ./data
.venv/bin/python -m codegraph.cli build --data ./data --db ./knowledge.kuzu

# incremental: only re-parse files changed since the last extract
# (state in <out>/<repo>/.extract-state.json; Joern re-runs only if a .java changed)
.venv/bin/python -m codegraph.cli extract --repos ~/svc-a --out ./data --incremental
.venv/bin/python -m codegraph.cli build --data ./data --db ./knowledge.kuzu
```

## Engines: tree-sitter (default) vs Joern (deep mode)

`extract --engine treesitter` (default): fast, dependency-light, multi-language.
`extract --engine joern`: Joern CPG-based deep mode for Java — a type-resolved
call graph straight from the compiler frontend. Tree-sitter still handles
MyBatis XML and Python in the same run (hybrid), so one command covers a repo.

Joern needs its CLI on PATH and JAVA_HOME set:

```bash
export JAVA_HOME=~/workspace/joern-spike/jdk21
export PATH=$JAVA_HOME/bin:~/workspace/joern-spike/joern/joern-cli:$PATH
.venv/bin/python -m codegraph.cli extract --repos /path/to/repo \
    --out ./data --engine joern
```

Measured on spring-petclinic (50 Java files, this VM):

|                      | tree-sitter | joern |
|----------------------|-------------|-------|
| extract time         | ~1s         | ~75s  |
| CALLS edges          | 257         | 1,742 |
| unresolved refs      | 1,471       | 0     |
| REST endpoints found | 17          | 17    |

Trade-off: Joern is ~2 orders of magnitude slower (JVM startup + CPG build)
but resolves virtually every call, including test→main chains and JDK calls.
Default to tree-sitter for 50–100 repo sweeps; switch to Joern for a deep dive
on one repo. Both engines feed the same graph schema, queries, and optional
LLM last mile. (Note: joern-parse skips `**/test/**` relative to its input —
the engine works around this by parsing `src/test` as a second CPG and
merging the dumps.)

## Design notes

- **Two engines, one schema**: tree-sitter for speed and multi-language breadth,
  Joern for depth on Java. The query layer and LLM last mile don't care which
  produced the graph.
- **Kuzu, not Neo4j**: embedded graph DB, Cypher queries, single file, no server
  to operate — fits locked-down environments.
- **JSONL between layers**: every stage's output is inspectable; re-run `build`
  without re-parsing.
- Method identity is `pkg.Class.method`; overloads share the qualified name and
  are disambiguated by id (`...::method/2`).

## Roadmap

- Kotlin / TypeScript extractors (tree-sitter grammars drop in)
- MyBatis `resultMap` → model class links
- JMS listener-container / XML config support
- Incremental re-index (only changed files since last run)
- Vector sidecar: embeddings on method source for hybrid graph+semantic retrieval
