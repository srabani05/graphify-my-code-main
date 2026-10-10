# Product Requirements: Single-Flow Knowledge Graph

## 1. Problem and Outcome

The pilot team needs to understand how one business feature flow is implemented and tested across multiple repositories. Today, that understanding is distributed among code, config schemas, E2E tests, API/event contracts, and approved design documents.

The MVP shall create a bounded, provenance-preserving graph for one approved client and one approved feature flow. Authorized users shall be able to explore the flow and ask questions whose answers identify supporting evidence and unknowns. The graph shall not contain member-level data.

## 2. Users

| User | Need | MVP permissions |
|---|---|---|
| BA/PO | Understand current flow, evidence, gaps, and draft requirements | Read approved flow metadata and evidence; create/download draft PRD only if permitted |
| Developer/architect | Trace rules to services, endpoints, config metadata, and tests | Broader read access to approved technical metadata; graph mutation only through ingestion/admin paths |
| Graph maintainer | Ingest approved revisions, review unresolved links, repair mappings | Ingestion and graph administration according to least privilege |
| Security/compliance reviewer | Verify data boundary, access, audit, and privacy controls | Review configuration and audit evidence; access to source content only if separately authorized |

Role names and exact permissions must be mapped to the organization's identity provider before pilot access.

## 3. MVP Scope

- One client/tenant selected by the product owner.
- One confirmed feature-wise flow. The current candidate is New hire → Eligibility → Enrollment → Premium calculation; it is not confirmed until BA/PO approval.
- Only repositories and paths listed and revision-pinned in [repository context](../repository-context.md).
- Code structure and relationships, selected API/event metadata, E2E test names/steps/assertions, configuration schema/field metadata, and approved document references.
- A flow explorer/query surface and LLM-backed question answering plus a PRD/gap-analysis draft for a sample change.
- Internal processing and storage, with server-side authorization, audit, and privacy gates.

## 4. Out of Scope

- A graph of every client, product, service, or feature.
- Member-level records, production request/response bodies, credentials, or raw config values.
- Automated policy interpretation or automatic approval of generated requirements.
- LLM-authored or automatically applied source-code changes, graph mutations, tickets, or pull requests.
- Arbitrary user-authored Cypher or unrestricted model-generated database queries.
- Training/fine-tuning a model on repository content.
- Claiming broad language/framework coverage before its parser and tests are implemented.

## 5. Functional Requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| FR-001 | An administrator shall register an allowlisted repository revision and its in-scope paths before extraction. | Ingestion manifest records repo alias, commit, path filters, parser version, and approval reference. |
| FR-002 | The ingestion pipeline shall create or update graph metadata idempotently for the same repository revision and schema version. | Replaying an import produces no duplicate stable IDs and reports added/updated/removed entities. |
| FR-003 | The graph shall distinguish a domain `BusinessFlow` and its ordered `FlowStep` nodes from automated `TestFlow` and ordered `TestStep` nodes. | Schema and query tests verify different labels and ID namespaces (`FLOW-`, `TEST-`). |
| FR-004 | Each extracted node and relationship shall retain provenance sufficient to identify its repository revision and source location, or an explicit non-code source reference. | A returned graph entity can be traced to a pinned source path/symbol and extraction record. |
| FR-005 | The graph shall link flow steps to evidence-backed rules, code entities, endpoints/contracts, config metadata, and tests. | Pilot query returns linked evidence; unsupported links are recorded as unresolved, not silently guessed. |
| FR-006 | The system shall represent extraction confidence and domain validation separately. | Heuristic links cannot be presented as domain-approved rules; validation status is queryable. |
| FR-007 | An authorized user shall be able to retrieve a flow and inspect each step's related implementations, tests, config metadata, sources, and known gaps. | BA/PO scenario passes with access checks applied server-side. |
| FR-008 | An authorized user shall be able to ask supported natural-language questions about flow behavior, rule implementation, test coverage, and change impact. | Each material answer claim includes evidence references or is labeled unsupported/unknown. |
| FR-009 | The assistant shall produce a PRD/gap-analysis draft for the approved sample change using the agreed template. | Draft includes current behavior, proposed requirements, impacts, test gaps, citations, assumptions, and human-review status. |
| FR-010 | The system shall not answer beyond available evidence as if fact; it shall state when evidence is absent, contradictory, stale, or inaccessible. | Evaluation cases for missing, conflicting, and unauthorized evidence return explicit limitations. |
| FR-011 | The system shall enforce authorization for graph queries and evidence retrieval before constructing any model context. | Tests prove unauthorized nodes and source excerpts are excluded from both response and LLM request. |
| FR-012 | Approved graph metadata shall be refreshable from a merged change through an authenticated, auditable, idempotent update hook. | Sample merge updates only allowlisted metadata; failure is visible and leaves last valid snapshot intact. |
| FR-013 | The system shall audit graph reads, writes, assistant requests, and denials without recording sensitive query content or result payloads. | Audit tests verify actor/action/time/outcome and absence of raw prompt/result values. |

## 6. Core User Workflows

### Explore a Flow

1. User authenticates and selects the authorized client and `FLOW-`.
2. The service retrieves ordered flow steps and evidence using approved query templates.
3. The UI presents source-backed implementation/test/config links and labels unresolved or unvalidated links.
4. User opens only evidence permitted by their role and source-repository permissions.

### Ask a Question

1. User submits a question within an authorized client/flow scope.
2. The service validates request size, detects sensitive values, resolves intent/entities, authorizes retrieval, and runs parameterized query templates.
3. The service constructs a minimal evidence bundle from accessible graph metadata and, only if approved, bounded source excerpts.
4. The approved model drafts an answer; the service validates citation IDs and filters any prohibited output.
5. The response includes evidence, uncertainty, and audit correlation ID. It does not modify the graph.

### Draft a Change PRD

1. User supplies a change statement and selects the flow.
2. Retrieval finds impacted rules, flow steps, services, endpoints, config fields, tests, and documents.
3. The assistant fills the PRD template and gap checklist with source references.
4. BA/PO and technical owners review and edit the draft; generation is not approval.

## 7. Proposed Pilot Change

The candidate example is a waiting-period change from 30 to 60 days. The assistant must not assume day-count convention, effective date, exceptions, client/plan scope, or policy authority. It must retrieve evidence for these points or list them as open questions for the domain owner.