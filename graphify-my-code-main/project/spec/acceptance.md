# Acceptance and Verification Plan

Acceptance is against one confirmed flow and pinned source revisions recorded in [repository context](../repository-context.md). Until those inputs are populated, scenarios below are executable templates, not evidence that the target system behaves this way.

## 1. Entry Criteria

- [ ] BA/PO has approved client/flow, start/end, key variants, and sample change.
- [ ] Application, E2E, config/schema, contracts, and documentation repos/paths are owner-approved and pinned to revisions.
- [ ] Graph store, identity mapping, deployment boundary, model/provider, and retention settings are approved.
- [ ] Synthetic/approved sanitized fixtures and PII canaries are available.
- [ ] The flow-to-evidence map identifies expected E2E scenarios and known unknowns.

## 2. Acceptance Scenarios

### AT-01: Ingest and Reproduce the Selected Flow

**Given** approved pinned repository revisions and sanitized fixtures,  
**When** ingestion runs twice with the same manifest,  
**Then** the graph contains the same stable IDs without duplicates, records the revisions/parser versions, reports unresolved links, and preserves the last good snapshot if validation fails.

### AT-02: Distinguish Business Flow from Test Flow

**Given** one approved business flow and its E2E scenario,  
**When** the graph is queried,  
**Then** the domain flow is a `BusinessFlow` with `FLOW-` identity and the automated scenario is a separate `TestFlow` with `TEST-` identity, linked through coverage edges.

### AT-03: Trace an End-to-End Step

**Given** an authorized user and an indexed flow step,  
**When** the user opens the step,  
**Then** the response shows only evidence-backed rule, implementation, endpoint/contract, config-field metadata, and E2E coverage, each with source revision/location and validation status; missing evidence is labeled as a gap.

### AT-04: Answer a Grounded Question

**Given** a question about where a selected rule is implemented and tested,  
**When** the assistant answers,  
**Then** each implementation/test claim references evidence IDs that resolve to authorized graph results; no unverified source or fabricated citation is presented as fact.

### AT-05: Handle Missing or Conflicting Evidence

**Given** a question about an unindexed behavior or conflicting source revisions,  
**When** the assistant responds,  
**Then** it states that evidence is absent or conflicting, cites the relevant known sources, and asks for resolution instead of inventing a definitive answer.

### AT-06: Draft the Candidate Change PRD

**Given** the approved sample waiting-period change from 30 to 60 days,  
**When** the BA/PO requests a draft,  
**Then** the output follows the PRD template, cites affected rules/code/config metadata/tests, includes a gap checklist, identifies assumptions and unknowns (including day-count, effective-date, exception, and scope policy), and is marked for human review.

### AT-07: Enforce Role and Client Scope

**Given** a BA/PO without access to a restricted entity or another client,  
**When** they query or ask the assistant,  
**Then** the service returns no restricted node or source excerpt and the model request contains no restricted evidence; the audit event records denial without sensitive query/result content.

### AT-08: Block PII Persistence and Leakage

**Given** synthetic PII canaries placed in prohibited config rows, E2E fixtures, source text, and prompts,  
**When** ingestion and assistant flows run,  
**Then** prohibited values are rejected or redacted according to policy and do not appear in graph properties/indexes, prompts, outputs, logs, audit events, caches, or exports; uncertain cases fail closed.

### AT-09: Verify Audit and PR Update

**Given** an authorized graph read/write and a sample merged PR,  
**When** the query and update hook run,  
**Then** audit records identify actor/action/time/outcome and correlation ID without payloads; the update is authenticated/idempotent; failures are observable and do not corrupt the valid snapshot.

## 3. Verification Matrix

| Area | Required tests/evidence | Owner |
|---|---|---|
| Parser adapters | Unit and fixture tests for supported languages/frameworks/formats; unsupported input reports clearly | Ingestion engineering |
| Graph contract | Schema, uniqueness, provenance, allowed-edge, idempotency, and migration tests | Graph engineering |
| Privacy | PII-canary scans over persistence, prompt construction, outputs, logs, audit, backup/export paths | Security + QA |
| Authorization | Positive/negative tests for each role and flow/client boundary at service/query/source layers | Security + platform |
| LLM quality | Golden/evaluation set for evidence validity, unsupported claims, conflicts, prompt injection, and unknowns | AI + BA/PO |
| End-to-end | AT-01 through AT-09 with approved sanitized data and recorded evidence | QA + product |
| Operations | Restore, retention/deletion, alerting, and failure recovery evidence | Platform/operations |

Numerical targets for latency, availability, evaluation quality, and maximum corpus size remain open until real repo sizes and pilot deployment constraints are known. Set and approve those targets before go-live, not after.

## 4. Exit Criteria

The MVP passes only when all entry criteria and applicable scenarios pass, no unresolved critical/high privacy or authorization findings remain, BA/PO validates the flow mapping and sample draft, security approves the deployment/model boundary, and all known coverage gaps are documented for the pilot handoff.