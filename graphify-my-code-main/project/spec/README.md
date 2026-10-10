# Single-Flow Knowledge Graph Specification

**Status:** Draft for product, engineering, and security review. This package specifies the intended MVP behavior; it does not assert facts about application repositories that have not yet been inventoried.

## Purpose

Define a buildable contract for ingesting approved code, E2E tests, configuration schemas, contracts, and documents for one feature flow, then answering authorized questions with graph-grounded evidence. The graph is a metadata and traceability index, not a store of member records or a replacement for source repositories.

## Documents

- [Product requirements](product-requirements.md): users, scope, workflows, and functional requirements.
- [Graph data contract](graph-data-contract.md): node/edge model, identity, provenance, and source mappings.
- [LLM interaction contract](llm-interaction.md): supported interactions, retrieval, evidence, and answer behavior.
- [Security and nonfunctional requirements](security-nfr.md): data boundary, authorization, privacy, operations, and quality attributes.
- [Acceptance and verification](acceptance.md): readiness gates, scenarios, and test evidence.

Use [repository context](../repository-context.md) to populate the selected flow and exact repo revisions. Use [the task ledger](../task-ledger.md) for implementation order. The detailed data contract here extends the initial [ontology draft](../ontology.md); product/domain owners must approve the final vocabulary before ingestion.

## Status and Source of Truth

The selected client, confirmed flow, source repositories, E2E framework, config formats, graph store, identity provider, LLM provider, and deployment boundary are **TBD**. Do not resolve these by guessing. Record decisions in the repository context and link evidence before implementation.

For MVP, `BusinessFlow` represents the domain process and `TestFlow` represents an automated test scenario. Their IDs must not be conflated: use `FLOW-` for a business flow and `TEST-` for an automated test flow. This is a proposed convention pending approval in M1-1.

## Decision Register

| Decision | Owner | Needed by | Status |
|---|---|---|---|
| Pilot client, feature flow, start/end, variants | BA/PO | Before source inventory | Open |
| Approved application, E2E, config, contract, and docs repos/revisions | Repo owners + tech lead | Before ingestion | Open |
| Final node labels, relationship semantics, IDs | BA/PO + architect | Before graph loader | Open |
| Graph store and internal deployment boundary | Architect + platform/security | Before provisioning | Open |
| Config and E2E formats/frameworks in MVP | Engineering + QA | Before parser implementation | Open |
| Identity provider, role mapping, audit retention | Security/platform | Before user access | Open |
| LLM provider, retention/training settings, allowed context | Security + product | Before LLM integration | Open |
| Corpus size, latency/availability targets, retention period | Tech lead + operations | Before acceptance baseline | Open |

## Specification Rules

- Requirements with unresolved repo-specific facts remain marked TBD and cannot be claimed as satisfied.
- Every asserted behavior must trace to graph evidence or be labeled as a domain-approved requirement/assumption.
- No source content or model output is authoritative without human validation.
- A failed security/privacy gate blocks ingestion or user/model access as described in [security requirements](security-nfr.md).