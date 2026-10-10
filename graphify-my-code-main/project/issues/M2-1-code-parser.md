# M2-1: Implement internal code-parser PoC

**Labels:** `epic:ingestion-code`, `milestone:MVP-flagship-flow`, `priority:P1`, `security-review`

## Goal

Extract services, endpoints, code entities, and call relationships needed to trace the flagship flow, using approved self-hosted tooling.

## Scope

Evaluate/reuse the repository's existing tree-sitter and Joern extraction paths before adding another parser. Map service, controller/endpoint, and method entities to the approved ontology. Record source provenance and label heuristic business-rule candidates as unverified.

## Acceptance Criteria

- [ ] Parser runs inside the approved internal environment against an approved pilot repository.
- [ ] Services, endpoints, code entities, and relevant call relationships are emitted with stable IDs and source provenance.
- [ ] Endpoint-to-service and code-call links can be queried for the flagship flow.
- [ ] Candidate business logic is distinguishable from domain-owner-validated rules.
- [ ] Incremental behavior or its MVP limitation is documented.
- [ ] Tests use synthetic/sanitized fixtures and verify no source snippets or sensitive values leak into logs or graph metadata.

## Dependencies

M1-1 ontology; approved source repositories; graph-store ingestion contract.