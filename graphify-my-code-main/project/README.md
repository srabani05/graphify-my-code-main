# Benefits Knowledge Graph

An internal, PII-safe knowledge platform for connecting benefits-platform code, configuration metadata, E2E tests, and approved documentation. Business analysts and product owners will use it to explore flagship flows, assess change impact, and draft PRDs grounded in graph evidence.

## Guardrails

- Keep raw artifacts and all ingestion and analysis inside approved internal infrastructure.
- Never persist member-level values or direct identifiers in the graph, prompts, generated documents, or logs. Store schema and field metadata only.
- Apply role-based access and audit graph reads and writes before exposing the platform to pilot users.
- Treat generated requirements and implementation suggestions as drafts for human review.

## MVP

Pilot one client and the flow **New hire → Eligibility → Enrollment → Premium calculation**. Ingest code, configuration schemas/metadata, and E2E tests; link tests, endpoints, configurations, and business rules; expose the flow to BA/PO users; and generate a draft PRD plus gap checklist for a waiting-period change from 30 to 60 days.

The MVP is accepted when:

- The graph links flagship-flow tests to endpoints, configuration metadata, and rules.
- A BA/PO can explore the end-to-end flow for the selected client.
- The sample change produces an evidence-grounded PRD draft and gap checklist.
- Automated checks verify that member-level PII is not persisted in graph data or emitted in logs.
- A sample merged PR updates graph metadata through the CI hook.

## Current Workspace Baseline

This repository already contains a code-graph prototype: tree-sitter/Joern ingestion, JSONL graph artifacts, a Kuzu query store, and optional graph-grounded LLM commands. It does not currently provide the benefits-domain ontology, config/test ingestion for this flow, a BA/PO explorer, or production RBAC and audit controls. The target graph store is an open decision; evaluate the existing Kuzu prototype against internal Neo4j/Neptune options before provisioning a service.

Keep the existing codegraph pipeline as a candidate ingestion component. Avoid duplicating its modules until discovery confirms a separate service boundary is needed.

## Milestones

| Milestone | Estimate | Outcome |
|---|---:|---|
| M1: Discovery & Schema | 2 weeks | Validated ontology, identifiers, and sample flagship-flow model |
| M2: Ingestion PoC | 3 weeks | Internal code, config-metadata, and E2E-test ingestion for the flow |
| M3: Graph Store & Queries | 2 weeks | Selected graph store, schema, impact/flow queries, and initial access controls |
| M4: LLM & PRD Prototype | 2 weeks | Graph-grounded PRD and gap-analysis draft |
| M5: UI & BA/PO Workflows | 2 weeks | Flow explorer and PRD editing workflow |
| M6: Hardening & CI | 2 weeks | PR update hook, redaction checks, audit controls, and operating docs |
| M7: Pilot & Handoff | 2 weeks | BA/PO feedback, fixes, and scale-up backlog |

These estimates add up to 15 weeks if run sequentially. The 8–10 week MVP target requires overlapping workstreams and a narrow pilot scope; confirm dependencies and staffing at kickoff.

## Starter GitHub Artifacts

- [MVP milestone](milestones/mvp-flagship-flow.md)
- [Issue drafts](issues/)
- [Repository and single-flow context](repository-context.md)
- [Implementation specification package](spec/README.md)
- [Domain ontology](ontology.md)
- [Security checklist](security.md)
- [PRD template](templates/prd.md)
- [Contributor guide](CONTRIBUTING.md)

## Decisions to Resolve at Kickoff

- Select the pilot client and confirm approved, sanitized sample artifacts.
- Confirm internal hosting, data residency, identity provider, and security-review owner.
- Choose graph store based on deployment, access-control, audit, and operational requirements.
- Agree on the first test framework and config formats to support.
- Confirm whether the 8–10 week target is calendar time with parallel staffing.