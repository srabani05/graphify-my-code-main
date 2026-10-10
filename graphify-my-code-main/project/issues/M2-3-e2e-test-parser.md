# M2-3: Implement E2E test-parser PoC

**Labels:** `epic:ingestion-tests`, `milestone:MVP-flagship-flow`, `priority:P1`, `security-review`

## Goal

Parse approved end-to-end test artifacts into flows and steps linked to endpoints, configuration metadata, and business rules.

## Scope

Start with the test framework used by the selected flagship-flow suite. Extract test identifiers, step order, API calls, and assertions needed for graph traceability. Do not execute tests against production or retain response bodies/member fixtures.

## Acceptance Criteria

- [ ] Supported framework and parsing limits are documented.
- [ ] TestFlow and TestStep nodes preserve stable test IDs, step order, and source provenance.
- [ ] API calls and assertions link to known Endpoint, ConfigArtifact/Field, or rule nodes where evidence supports the mapping.
- [ ] Client context and feature IDs are attached only when explicitly available in approved metadata.
- [ ] Tests cover extraction and prove sample payloads/member values are not persisted or logged.
- [ ] Unresolved links are reported as gaps rather than guessed silently.

## Dependencies

M1-1 ontology; selected test suite/framework; code-parser and graph-store contracts.