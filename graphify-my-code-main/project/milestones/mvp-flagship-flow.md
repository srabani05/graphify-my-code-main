# Milestone: MVP - Flagship Flow

**Goal:** Deliver a PII-safe internal pilot for one client and the New hire → Eligibility → Enrollment → Premium calculation flow.

## Definition of Done

- [ ] Graph links flagship-flow tests, endpoints, configuration metadata, and business rules.
- [ ] BA/PO users can explore the end-to-end flow for the selected client under approved access controls.
- [ ] A sample 30-to-60-day waiting-period change yields a graph-grounded PRD draft and gap checklist with evidence and explicit unknowns.
- [ ] Redaction tests verify member-level PII is not persisted or emitted in prompts/logs.
- [ ] Query and mutation audit events are available without sensitive payloads.
- [ ] A sample merged PR updates graph metadata and the update is observable.
- [ ] BA/PO, engineering, and security/compliance owners review the pilot and record follow-up work.

## Initial Issues

- [M1-1: Define ontology and naming conventions](../issues/M1-1-ontology-and-naming.md)
- [M1-2: Provision internal graph-store dev environment](../issues/M1-2-graph-store-dev.md)
- [M2-1: Implement internal code-parser PoC](../issues/M2-1-code-parser.md)
- [M2-2: Implement config-metadata importer PoC](../issues/M2-2-config-importer.md)
- [M2-3: Implement E2E test-parser PoC](../issues/M2-3-e2e-test-parser.md)

## Scheduling Note

The full milestone estimates in the project overview sum to 15 sequential weeks. This milestone is an 8–10 week calendar target only if ingestion, graph/UI work, and security review can run in parallel with agreed owners and dependencies.