# Incremental Implementation Plan

This is a phase-level summary, not a replacement for the statuses, dependencies, owners, and evidence recorded in the [task ledger](../task-ledger.md). Do not skip privacy, authorization, or model-boundary gates to gain schedule.

| Phase | Ledger tasks | Deliverable / gate |
|---|---|---|
| 0. Bound the feature | 01–02 | Named client/flow, owners, approved source inventory, pinned revisions, sanitized samples, internal boundary |
| 1. Freeze vocabulary and decisions | 03–05 | Approved ontology and identifiers; graph/store/model/provider decisions; security controls and test plan |
| 2. Prepare platform and contract | 06–07 | Approved graph dev environment; versioned ingestion envelope, allowlist, idempotency, quarantine, contract tests |
| 3. Add source adapters | 08–10 | Reuse/scoped code extractor; config-schema metadata importer; E2E test metadata parser; focused safety tests |
| 4. Build the single-flow graph | 11–12 | Repeatable normalized load; verified and heuristic edges distinguished; bounded flow/impact/coverage/provenance queries |
| 5. Lock access and privacy | 13–14 | Role/client authorization, audit, PII-canary and failure-path verification; security sign-off before model context or pilot |
| 6. Deliver user workflows | 15–16 | Approved-provider grounded PRD/gap draft; authorized flow explorer and PRD review/edit workflow |
| 7. Automate and accept | 17–18 | Authenticated idempotent PR update; end-to-end acceptance evidence across graph, UI, LLM, security, and audit |
| 8. Pilot and hand off | 19 | BA/PO and security review; critical findings closed; operations and scale-up backlog recorded |

## Work Unit Discipline

For each phase, work against one small, testable vertical slice:

1. Confirm the source path and expected graph entities from [repository context](../repository-context.md).
2. Add or update the adapter/contract for only that source format and feature-flow slice.
3. Test with synthetic or approved sanitized fixtures, including negative privacy/access cases relevant to the change.
4. Inspect graph output and unresolved links before adding another source family.
5. Record task status, owner, evidence, and any schema/architecture decision in the source-of-truth docs.

Do not expand to other features/services until the current flow has traceable source-to-test evidence and the product owner accepts the boundary.

## Critical Sequencing Note

The existing milestone estimates sum to 15 weeks if sequential. This plan is a safe dependency order, not a promise of an 8–10 week calendar schedule. Any parallelization must preserve gates: adapter work can begin in parallel only after the ingestion contract, allowed source boundary, and sanitized fixtures are stable.