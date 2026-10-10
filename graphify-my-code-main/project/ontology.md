# Benefits Domain Ontology (Initial)

This is a starting schema for the flagship flow, not a claim that every node type is required in the MVP. Validate names, identifiers, and relationships with the BA/PO and domain owners before ingesting production-derived metadata.

## Nodes

| Label | Purpose | Example properties (metadata only) |
|---|---|---|
| `Client` | Benefits customer or tenant | `id`, `name` |
| `Plan` | Benefits plan offered to a client | `id`, `type`, `name` |
| `Transaction` | A domain operation in a flow | `id`, `name`, `stage` |
| `BusinessFlow` | The domain process being modeled | `id` (`FLOW-`), `name`, `version`, `status` |
| `FlowStep` | Ordered step in a business flow | `id`, `sequence`, `name`, `behavior_summary` |
| `EligibilityRule` | Rule that determines eligibility | `id` (`BR-`), `name`, `summary`, `version` |
| `EnrollmentRule` | Rule governing enrollment | `id` (`BR-`), `name`, `summary`, `version` |
| `ConfigArtifact` | Config file, table, or schema | `id` (`CFG-`), `source`, `format`, `path`, `content_hash` |
| `Field` | A field defined by a schema or config | `id`, `name`, `data_type`, `classification`, `usage` |
| `Service` | Deployable application/service | `id`, `name`, `repository` |
| `Endpoint` | HTTP or message entry point | `id` (`API-`), `protocol`, `route_or_topic`, `method` |
| `CodeEntity` | Class, method, or other code symbol | `id`, `kind`, `qualified_name`, `path`, `line_start` |
| `TestFlow` | Automated test scenario covering a business flow | `id` (`TEST-`), `name`, `framework`, `source_path` |
| `TestStep` | Ordered action or assertion in a test | `id`, `sequence`, `action_kind`, `description` |
| `SourceArtifact` | Provenance reference to a pinned source artifact | `id`, `repo_alias`, `revision`, `source_path`, `content_hash` |
| `Document` | Approved design or requirements document | `id`, `title`, `source`, `version` |
| `Ticket` | Work item or change record | `id`, `system`, `title`, `status` |

`classification` describes the kind of data a field may contain (for example, `PII`); it must never contain an example member value. Keep descriptions and summaries free of copied production values.

## Relationships

| Relationship | Direction | Meaning |
|---|---|---|
| `USES` | `Client` → `Plan` | Client offers or uses a plan |
| `SCOPED_TO` | `BusinessFlow` → `Client` / `Plan` | Flow is in scope for a client/plan |
| `HAS_STEP` / `NEXT` | `BusinessFlow` → `FlowStep`; flow step → next flow step | Ordered domain-flow structure |
| `REALIZED_BY` | `FlowStep` → `Transaction` / `Endpoint` | System behavior implements a domain step |
| `GOVERNED_BY` | `Plan` / `Transaction` → rule | A rule applies to the plan or operation |
| `IMPLEMENTED_BY` | rule → `CodeEntity` | Code implements the rule |
| `BELONGS_TO` | `CodeEntity` / `Endpoint` → `Service` | Entity is part of a service |
| `CALLS` | `CodeEntity` → `CodeEntity` / `Endpoint` | Control-flow or invocation relation |
| `DEPENDS_ON` | entity → entity | Technical or domain dependency |
| `TESTS` | `TestFlow` / `TestStep` → entity | Test covers an entity or behavior |
| `COVERS` | `TestFlow` → `BusinessFlow` / `FlowStep` | Automated scenario covers domain behavior |
| `HAS_STEP` / `NEXT` | `TestFlow` → `TestStep`; test step → next test step | Ordered test-flow composition |
| `READS` / `WRITES` | `CodeEntity` → `Field` / `ConfigArtifact` | Code reads or writes metadata-defined configuration |
| `DESCRIBED_IN` | entity → `Document` / `Ticket` | Source describes or tracks the entity |
| `MODIFIES` | `Ticket` → entity | Ticket proposes a change to an entity |
| `DERIVED_FROM` | graph entity/relationship → `SourceArtifact` | Provenance to a pinned source revision/path |

## Identifier Conventions

- `BR-<stable-id>` for business rules.
- `FLOW-<stable-id>` for business flows.
- `TEST-<stable-id>` for automated test flows.
- `API-<stable-id>` for endpoints.
- `CFG-<stable-id>` for configuration artifacts.
- Use stable source-derived identifiers where possible; keep display names separate from IDs.
- Do not put client member IDs, names, or other personal data into identifiers.

## Modeling Rules

- Store source references, hashes, timestamps, and schema metadata needed for traceability; do not store raw member-level records or config values that may contain PII.
- Preserve provenance for every extracted node and edge (source repository/artifact, parser/version, and extraction time).
- Do not conflate a business `Flow` with a test `TestFlow`; link them with `COVERS` and keep identifiers in separate namespaces.
- Represent uncertain heuristic matches with confidence/provenance metadata; do not silently assert inferred business meaning as fact.
- Add uniqueness constraints and indexes for stable IDs in the selected graph store.
- Example Cypher is illustrative; adapt syntax and authorization to the graph store selected in M3.

### Example Queries

Find rules governing a client's medical plan:

```cypher
MATCH (c:Client {id: $clientId})-[:USES]->(p:Plan {type: 'medical'})-[:GOVERNED_BY]->(r)
RETURN p, r;
```

Trace implementations and tests for a business rule:

```cypher
MATCH (r {id: $ruleId})<-[:IMPLEMENTED_BY]-(ce:CodeEntity)-[:BELONGS_TO]->(s:Service)
OPTIONAL MATCH (t:TestFlow)-[:TESTS]->(r)
RETURN r, ce, s, t;
```