# Contributing

## Before You Start

- Review the [project overview](README.md), [ontology](ontology.md), and [security checklist](security.md).
- Use only synthetic or explicitly approved sanitized artifacts in local development and tests.
- Never add member-level PII, credentials, or unredacted production samples to source control, graph fixtures, prompts, or logs.
- Confirm a work item has an owner, acceptance criteria, and a data classification before implementation.

## Change Expectations

- Keep source provenance with extracted graph data and document parser/schema changes.
- Add focused tests for ingestion, redaction, authorization, and graph-query behavior affected by a change.
- Treat heuristic links and LLM output as suggestions; include provenance and preserve human review.
- Update the ontology and example queries when node, edge, or identifier conventions change.
- Include relevant `BR-`, `FLOW-`, `API-`, or `CFG-` identifiers in pull request descriptions when known.

## Pull Request Checklist

- [ ] Acceptance criteria are addressed and tests are included.
- [ ] No raw member values, secrets, or sensitive test output are introduced.
- [ ] Access checks and audit behavior are covered where graph reads or writes change.
- [ ] Documentation, ontology, and migration notes are updated when needed.
- [ ] A human reviewer has checked graph-grounded or LLM-generated requirements for unsupported claims.