# Workspace Integration Guide

## Goal

Bring the graph tool together with the real application and E2E codebases for incremental, feature-bounded implementation without merging their source trees or accidentally indexing unrelated code/data.

## Suggested Checkout Layout

Use sibling checkouts in an approved development location. This is a layout proposal, not a request to move the current project or duplicate repository contents:

```text
<approved-dev-root>/
  graphify-tool/                 # this graphify-my-code project
  sources/                       # separate, read-only source checkouts
    service-eligibility/
    service-enrollment/
    benefits-e2e/
    benefits-config-schema/
    benefits-contracts/
  pilot-work/                    # generated, access-controlled outputs; never commit
    manifests/
    extracted-jsonl/
    graph-db/
    reports/
```

Only include repositories that the flow owner and repository owners approve. Do not put secrets or production data in `pilot-work`; do not commit generated extracts or graph databases unless an explicit policy requires a sanitized fixture.

## Before Connecting Repositories

1. Confirm one flow and its in/out-of-scope boundaries with BA/PO.
2. Populate [repository context](../repository-context.md) with repo aliases, owners, approved paths, branch/commit, languages/frameworks, E2E test names, contracts, config schemas, and evidence map.
3. Obtain source-owner and security approval. Use synthetic or explicitly sanitized test data.
4. Record the extraction tool revision and graph schema version. Pin each source revision so the graph can be reproduced.
5. Review excluded paths and validate that no secret/config-value/data export is in the extraction scope.

## Important Limitation in the Current Extractor

The current CLI accepts repository roots through `--repos`; `extract.py` walks the selected roots and filters out common generated/dependency directories, but it does not accept an explicit include-path allowlist or a feature-flow filter. Running it against a full service or monorepo can therefore index unrelated Java/Python files under that root. It also has no benefits-specific config importer or E2E `TestFlow` adapter.

Until allowlist support and privacy review are implemented, do **not** claim that a full-root extraction represents only one feature. The safer options are:

- Implement explicit include/exclude path filters in the ingestion manifest and extractor, with tests that prove out-of-scope files are not read; or
- Use an owner-approved, sanitized staging tree containing only the flow-relevant files and the required build context, then verify the extraction manifest before loading it.

Do not create an ad hoc copy of production source or test fixtures without approval. Avoid relying on the current skip-directory list as a security boundary.

## Incremental Development Loop

1. Change one adapter, graph contract, or query at a time.
2. Run focused unit/contract tests on synthetic fixtures before extracting real repository content.
3. Extract only pinned, approved paths to `pilot-work/extracted-jsonl`; review metadata and unresolved links.
4. Build a disposable graph snapshot and run the relevant flow/coverage/impact queries.
5. Compare graph changes to the expected diff; reject unexpected entities, paths, or properties.
6. Run PII, authorization, and audit checks affected by the change; retain safe test evidence only.
7. Promote or share a snapshot only after the relevant acceptance and owner approvals pass.

## Integration Manifest (Proposed)

Keep one reviewed manifest per pilot snapshot. Do not put secrets, raw field values, or member data in it.

```yaml
schema_version: 1
flow_id: FLOW-TBD
repositories:
  - alias: service-eligibility
    revision: COMMIT-TBD
    approved_by: OWNER-TBD
    include_paths:
      - src/main/java/APPROVED/PATH
    exclude_paths:
      - src/test/resources/UNSANITIZED
    adapter: java-code
  - alias: benefits-e2e
    revision: COMMIT-TBD
    approved_by: OWNER-TBD
    include_paths:
      - tests/APPROVED/FLOW/PATH
    adapter: e2e-TBD
  - alias: benefits-config-schema
    revision: COMMIT-TBD
    approved_by: OWNER-TBD
    include_paths:
      - schemas/APPROVED/PATH
    adapter: config-schema-TBD
output:
  directory: pilot-work/extracted-jsonl/SNAPSHOT-TBD
  graph_schema_version: TBD
```

This manifest is a design example. The current CLI does not consume it; implement and validate manifest support before treating it as executable configuration.

## Readiness to Start Real-Repo Integration

- [ ] Actual service/E2E/config/contracts repositories are available in the workspace or approved internal locations.
- [ ] Repository owners and BA/PO approve the exact scope and pinned commits.
- [ ] E2E tests for the feature flow are identified by path and test name.
- [ ] Config data is schema-only; fixtures and payloads are synthetic or approved sanitized.
- [ ] A safe path allowlist or reviewed staging tree is in place and verified.
- [ ] Graph, output, and model locations satisfy approved access and retention rules.
- [ ] Missing parsers and unresolved source links are reported as implementation tasks rather than hidden.