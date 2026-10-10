# Security and Nonfunctional Requirements

This document is the system-level requirement set. The operational checklist in [project security.md](../security.md) remains the sign-off record.

## 1. Data Classification and Privacy

- The graph contains metadata needed for traceability, never member-level records or direct identifiers.
- Config ingestion stores schemas and field names/types/classification only. No table rows or runtime config values are allowed by default.
- E2E ingestion stores test identity, step/action/assertion metadata, and references only. It excludes fixtures, response bodies, screenshots, and logs unless individually sanitized and approved.
- Source content is not copied into the graph. Any just-in-time excerpt retrieval is separately authorized, bounded, redacted, and included in the approved model data boundary.
- PII detection/redaction runs before graph writes, prompt construction, generated artifact persistence, and logging. Uncertain classification or scanner failure rejects/quarantines the record.
- Retention, deletion, backups, caches, temporary files, and graph snapshots follow the approved internal policy and are recorded in the decision register.

## 2. Identity and Authorization

- All API/UI and ingestion access requires an approved workload or user identity; no anonymous graph endpoint.
- Authorization is enforced in the service/query layer for every graph query, source lookup, export, and mutation. UI hiding is not authorization.
- Each request is scoped to the user's permitted flow/client and graph labels/properties. The model cannot elevate scope.
- BA/PO receives only approved non-sensitive metadata and source references; Dev/Arch access is broader only where explicitly granted; maintainers have separate write permissions.
- Evidence retrieval rechecks source authorization before returning or sending excerpts to a model.
- Denials fail closed and do not disclose whether inaccessible entities exist.

## 3. Audit and Secrets

- Audit graph reads, writes, ingestion runs, assistant requests, exports, and authorization denials with actor/workload, timestamp, action/intent, target scope, outcome, and correlation ID.
- Audit events exclude raw questions, query parameters, graph result payloads, source snippets, secrets, and member values.
- Store model and repository credentials only in approved secret management; never put secrets in repository context, graph nodes, fixtures, prompts, or logs.
- Audit access and retention are themselves restricted and reviewed.

## 4. Model and Prompt Safety

- Use only an approved internal/self-hosted or explicitly approved private model endpoint; record deployment, region, retention, training, and logging settings.
- Do not send source, graph metadata, user input, or generated content to an external service until transfer is explicitly approved.
- Apply least-context retrieval, input/output scanning, citation validation, and prompt-injection defenses.
- Retrieved code/docs/tests are untrusted content and cannot change system instructions or authorize tool use.
- LLM output is advisory. It cannot mutate graph records, repositories, tickets, or business policy.

## 5. Integrity and Reliability

- Validate schema version, stable IDs, source revision, provenance, relationship endpoint types, property allowlists, and classification before graph commit.
- Ingestion is idempotent and produces a report of additions, updates, deletions, unresolved links, rejected records, and parser failures.
- A failed import does not replace the last known-good graph snapshot; updates are atomic or staged with a validated promotion step.
- Every graph answer can be tied to an immutable source revision and extraction version. Staleness is visible to users.
- Unsupported parsing, unresolved mappings, or unavailable sources are surfaced as coverage gaps, not silently omitted.

## 6. Operational Quality

- Encrypt data in transit and at rest, restrict network access, and test backup/restore in accordance with internal standards.
- Instrument ingestion duration/counts/failures, query duration/counts/denials, model latency/outcome, and redaction outcomes without recording sensitive payloads.
- Apply bounded query depth, timeouts, result limits, prompt/context budgets, and output limits to control resource use and data exposure.
- Define service availability, recovery time/objectives, and numerical latency/scale targets after the pilot corpus and deployment topology are known. Do not claim production readiness before those targets are approved and tested.
- Keep local graph files, exports, and logs in approved storage with access controls; the existing developer prototype's local Kuzu file is not a production security boundary.

## 7. Release Gates

No ingestion of target artifacts before source-owner approval and data-boundary sign-off. No LLM integration before provider/context/retention approval. No BA/PO pilot before server-side authorization, audit, PII-canary tests, backup/restore, and acceptance scenarios pass. Any privacy or access-control failure blocks release regardless of schedule.