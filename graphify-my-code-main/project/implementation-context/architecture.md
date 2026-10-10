# Architecture Summary

## Intent

Build a provenance-preserving graph for **one approved business feature flow** across the smallest set of application, E2E, config-schema, contract, and approved-document sources needed to explain it. Provide authorized graph queries and an LLM assistant that answers from retrieved evidence. The graph is a derived metadata index, not the source of truth and never a store for member records.

## Existing Tool Architecture

The repository already has a local code-analysis pipeline:

```text
Approved repository root(s)
        |
        v
codegraph.extract (tree-sitter; optional Joern for Java)
        |
        v
Per-repository entities.jsonl + edges.jsonl + metadata
        |
        v
codegraph.build (merge and resolve references)
        |
        v
Local Kuzu graph + unresolved-reference output
        |
        +--> codegraph query / context / cypher
        +--> optional LLM commands (ask, summarize, PRD, design)
```

Implemented coverage is strongest for Java/Spring, MyBatis XML, JMS, and Python. The current store is Kuzu. These are facts about the prototype, not decisions for the internal benefits deployment.

## Target MVP Boundaries

```text
Pinned, approved source repos
  |-- application code
  |-- E2E test definitions (metadata only)
  |-- config/schema and API/event contracts (metadata only)
  `-- approved requirements/design references
          |
          v
Allowlist + adapters + validation + PII rejection/quarantine
          |
          v
Versioned normalized graph records with provenance
          |
          v
Graph store (decision pending) + schema and indexes
          |
          v
Authorized query service / bounded query templates
      |                         |
      v                         v
Flow explorer              Evidence retrieval
                                |
                     approved LLM boundary only
                                |
                                v
             cited answer / PRD draft / explicit unknowns
```

The trusted service owns authentication, authorization, path allowlists, graph queries, redaction, evidence validation, and auditing. The model may synthesize a response from a bounded evidence bundle; it may not run arbitrary Cypher, access repositories directly, widen permissions, or mutate the graph.

## Current Versus Planned

| Capability | Current state | MVP target |
|---|---|---|
| Java/Python code extraction | Existing tree-sitter path; Joern deep Java option | Reuse after path scoping and provenance contract are validated |
| JSONL graph interchange | Existing per-repo entity/edge files | Versioned normalized contract with validation and idempotency |
| Graph database | Local embedded Kuzu store | Internal store chosen through architecture/security review |
| Config/schema metadata importer | Not established as benefits adapter | Import schema/field metadata only; no row/config values |
| E2E parser | No benefits `TestFlow` adapter established | Parse test IDs, steps, assertions, and references without payloads |
| Business ontology | Not present in current code graph | `BusinessFlow`/`FlowStep`, rules, services, endpoints, config and tests |
| PII controls | No target-platform guarantee | Fail-closed controls and canary verification at each boundary |
| RBAC/audit/UI | Not the current local CLI's production features | Server-side role checks, audit, and BA/PO exploration workflow |
| LLM grounding | Optional prototype command | Approved provider, scoped retrieval, citation validation, safety tests |

## Open Architecture Decisions

Do not implement these as settled choices until documented and approved:

- Graph store and hosting boundary (evaluate current Kuzu against approved alternatives).
- Application/API/UI deployment and identity-provider integration.
- Source repository and path allowlist mechanism; current CLI accepts repo roots, not path filters.
- E2E framework, config formats, and contract formats in scope.
- LLM provider, model, region, retention/training settings, and permitted context.
- Tenant/client isolation, audit retention, backup/restore, and operational SLOs.

## Key Design Rules

- Keep source repositories read-only inputs. Store stable references and metadata, not source copies or runtime/member values.
- Keep `BusinessFlow` (`FLOW-`) distinct from automated `TestFlow` (`TEST-`); connect them with explicit coverage edges.
- Preserve repo revision, relative path, parser version, extraction time, and validation status for graph evidence.
- Label heuristic edges as heuristic; only a domain owner can approve business semantics.
- Introduce adapters at the extraction/normalization boundary. Do not encode benefits-specific semantics inside generic language parsers unless that is the agreed ownership boundary.
- Keep authorization and safe query construction outside the LLM.