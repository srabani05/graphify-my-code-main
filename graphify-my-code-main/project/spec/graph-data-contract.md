# Graph Data Contract: MVP v1 Proposal

This contract is a proposal to validate in M1-1. It models one business flow across approved repositories and explicitly separates domain behavior from its tests. Graph-store-specific DDL, indexes, and transaction semantics are selected after the store decision.

## 1. Identity and Common Metadata

Every node has a stable `id`, `kind`/label, and `schema_version`. Every extracted node and edge carries or resolves to provenance with:

- `repo_alias` and immutable `revision` (commit or source version).
- `source_path` relative to that repository; optional symbol and line range where available.
- `parser_name`, `parser_version`, and `extracted_at`.
- `content_hash` of the approved source artifact or metadata schema, not a copy of its contents.
- `evidence_status`: `extracted`, `heuristic`, or `domain_validated`.
- `confidence`: optional bounded numeric value for heuristic mapping; it is not a substitute for domain validation.

No raw file, source body, config value, test payload, or member record is stored as a graph property. Source citations resolve to authorized repository content on demand only when that retrieval path is approved.

## 2. Nodes

| Label | Stable ID | MVP properties |
|---|---|---|
| `Client` | `CLIENT-<approved-stable-id>` | `display_name` (approved), `status`; no member identifiers |
| `Plan` | `PLAN-<stable-id>` | `name`, `type`, `status` |
| `BusinessFlow` | `FLOW-<stable-id>` | `name`, `version`, `status`, `start_event`, `end_state` |
| `FlowStep` | `FLOWSTEP-<flow-id>-<sequence>` | `sequence`, `name`, `behavior_summary` (approved metadata only) |
| `Transaction` | `TXN-<stable-id>` | `name`, `stage`, `protocol_or_trigger` |
| `BusinessRule` | `BR-<stable-id>` | `name`, `summary` (approved), `version`, `validation_status` |
| `ConfigArtifact` | `CFG-<stable-id>` | `format`, `schema_name`, `source_path`, `content_hash` |
| `Field` | `FIELD-<artifact-id>-<field-key>` | `name`, `data_type`, `classification`, `usage`; never a field value |
| `Service` | `SVC-<stable-id>` | `name`, `repo_alias`, `lifecycle` |
| `Endpoint` | `API-<stable-id>` | `protocol`, `method`, `route_or_topic`, `contract_version` |
| `CodeEntity` | source-derived stable ID | `entity_type`, `qualified_name`, `source_path`, optional `line_start`/`line_end` |
| `TestFlow` | `TEST-<stable-id>` | `name`, `framework`, `source_path`, `test_status` (metadata only) |
| `TestStep` | `TESTSTEP-<test-id>-<sequence>` | `sequence`, `action_kind`, `assertion_kind`; no request/response body |
| `Document` | `DOC-<stable-id>` | `title`, `source_system`, `version`, `approved_status`; no unapproved body text |
| `Ticket` | `TICKET-<system>-<stable-id>` | `title` (approved), `status`, `source_system` |
| `SourceArtifact` | `SRC-<repo-alias>-<revision>-<path-hash>` | `repo_alias`, `revision`, `source_path`, `artifact_type`, `content_hash`, `approved_status` |

`classification` is a field-schema label such as `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, or `PII`; it describes the field, not its contents. Exact classifications and display-name policy must be approved. If a property is not needed for a supported query, do not ingest it.

## 3. Relationships and Direction

| Type | Direction | Meaning |
|---|---|---|
| `USES` | `Client` → `Plan` | Client offers/uses plan |
| `SCOPED_TO` | `BusinessFlow` → `Client` / `Plan` | Flow applies to approved client/plan context |
| `HAS_STEP` | `BusinessFlow` → `FlowStep`; `TestFlow` → `TestStep` | Ordered child steps, order stored on child |
| `NEXT` | `FlowStep` → `FlowStep`; `TestStep` → `TestStep` | Explicit next step; no inferred cross-flow order |
| `REALIZED_BY` | `FlowStep` → `Transaction` / `Endpoint` | System behavior implementing a domain step |
| `GOVERNED_BY` | `Plan` / `Transaction` / `FlowStep` → `BusinessRule` | Rule applies to behavior |
| `IMPLEMENTED_BY` | `BusinessRule` → `CodeEntity` | Code implements or evaluates a rule |
| `BELONGS_TO` | `CodeEntity` / `Endpoint` → `Service` | Entity belongs to deployable service |
| `CALLS` | `CodeEntity` → `CodeEntity` / `Endpoint` | Static or observed invocation; record relation type and provenance |
| `READS` / `WRITES` | `CodeEntity` → `Field` / `ConfigArtifact` | Code reads/writes schema-defined metadata |
| `COVERS` | `TestFlow` → `BusinessFlow` / `FlowStep` | Test scenario covers domain behavior |
| `TESTS` | `TestFlow` / `TestStep` → rule, endpoint, code, or config field | Test evidence targets entity |
| `DESCRIBES` | `Document` / `Ticket` → flow, step, rule, or component | Approved artifact describes/tracks entity |
| `MODIFIES` | `Ticket` → graph entity | Ticket proposes change to entity |
| `DERIVED_FROM` | graph entity or relationship → `SourceArtifact` | Provenance link to exact source revision/path |

Store extraction method (`static`, `test_reference`, `schema_mapping`, `domain_confirmed`) and evidence status on relationships where those differ. A heuristic match must not be presented as a verified semantic edge.

## 4. Source-to-Graph Mapping

| Source | Extract into graph | Must not extract |
|---|---|---|
| Application code | Services, code symbols, calls, endpoints, safe signatures, source references | Secrets, runtime values, unrelated source, unrestricted source snippets |
| E2E tests | Test IDs/names, ordered actions, endpoint references, assertion types, source path | Fixtures with member values, request/response bodies, screenshots containing PII |
| Config/schema repositories | Artifact/schema name, field name/type/classification, approved usage mapping | Table rows, config values, production exports, credentials |
| API/event contracts | Method/route or event name, version, producer/consumer, schema references | Example payloads containing sensitive values |
| Approved docs/tickets | Document/ticket identity, title, version, relevant approved statements and references | Unreviewed full-text dumps or sensitive attachments |

Each source adapter emits the same versioned ingestion envelope. Unsupported formats are reported as unsupported, not partially parsed without a visible warning.

## 5. Integrity and Evolution

- Enforce uniqueness on `(label, id)` and stable relationship identity in the chosen store.
- Make imports idempotent by source revision, parser/schema version, and source identity.
- Record removals/tombstones when an allowlisted source entity disappears; do not delete unrelated graph data.
- Validate referential integrity, required provenance, allowed labels/edges, property allowlists, and classification before commit.
- Quarantine rejected records with a safe error code and source locator; never duplicate rejected content into logs.
- Version schema migrations and retain the mapping from each graph snapshot to input commits.
- Apply client/tenant scoping as an authorization dimension, not as a user-supplied query filter alone.

## 6. Required Query Shapes

The query layer must support parameterized, bounded templates for:

1. Load one authorized `BusinessFlow` in step order, including `FlowStep` evidence.
2. Trace a `BusinessRule` to implementing code, service, endpoint, and tests.
3. Find test coverage for a flow step, endpoint, or rule, including uncovered items.
4. Find impact candidates for a rule, endpoint, config field, or code entity.
5. Resolve provenance and source revisions for returned entities.

Every query applies authorization and result limits in the server-side query service. The model may select an approved query intent and entity IDs; it may not submit arbitrary executable Cypher.