# Specification Summary

## MVP Goal

For one BA/PO-approved client and one confirmed feature flow, build a graph linking business steps to rules, code, services, API/event metadata, config schemas, E2E tests, and approved docs. Let authorized users explore that evidence and ask questions or draft a PRD/gap checklist with citations. The currently proposed New hire → Eligibility → Enrollment → Premium calculation flow is a candidate only; confirm it before implementation.

## Core Graph Concepts

- **Domain:** `Client`, `Plan`, `BusinessFlow`, `FlowStep`, `Transaction`, `BusinessRule`.
- **Implementation:** `Service`, `Endpoint`, `CodeEntity`, `ConfigArtifact`, `Field`.
- **Verification/context:** `TestFlow`, `TestStep`, `Document`, `Ticket`, `SourceArtifact`.
- **Traceability:** `SCOPED_TO`, `HAS_STEP`, `NEXT`, `REALIZED_BY`, `GOVERNED_BY`, `IMPLEMENTED_BY`, `BELONGS_TO`, `CALLS`, `READS`/`WRITES`, `COVERS`, `TESTS`, `DESCRIBES`, `MODIFIES`, `DERIVED_FROM`.

Stable IDs and property details are proposed in [the graph data contract](../spec/graph-data-contract.md) and require M1-1 domain approval. Every material node/edge must have provenance and an evidence/validation status. Missing links remain visible as gaps.

## LLM Contract

Supported MVP intents: explain a flow, find an implementation, identify test coverage, analyze bounded change impact, and draft a PRD. A trusted service authenticates, scopes, authorizes, queries, minimizes and scans evidence before any model call. Answers cite only retrieved, authorized evidence; distinguish fact, heuristic, domain approval, and suggestion; and expose unknown/conflicting/stale evidence. The assistant is read-only and generated PRDs are drafts for human review.

## Privacy and Security Must-Haves

- Never ingest member-level records, direct identifiers, request/response bodies, credentials, or unsanitized fixtures.
- Config ingestion is schema/field metadata only. E2E ingestion is test/step/assertion metadata only.
- Fail closed and quarantine safely on redaction/classification uncertainty.
- Enforce role and client scope server-side before retrieval/context construction.
- Audit reads, writes, model requests, and denials without raw prompts, source payloads, or result bodies.
- Do not use an LLM endpoint until model, region, retention/training, and context-sharing are approved.

## MVP Exit

Acceptance must demonstrate a reproducible graph for the selected flow; test-to-endpoint/config/rule evidence; authorized flow exploration; a cited PRD/gap draft for an approved sample change; PII-canary non-persistence/non-leakage; audit controls; and an idempotent sample PR-driven metadata refresh. Exact evaluation, latency, availability, and corpus-size targets must be set after source repos and hosting are known.

## Detailed Contracts

See [product requirements](../spec/product-requirements.md), [graph data contract](../spec/graph-data-contract.md), [LLM interaction](../spec/llm-interaction.md), [security/NFRs](../spec/security-nfr.md), and [acceptance](../spec/acceptance.md). These full documents override this summary if they are updated.