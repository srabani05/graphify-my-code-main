# Implementation Context Pack

This folder is the concise entry point for engineers and coding agents implementing the **single-flow knowledge graph**. Read these four documents before making changes:

1. [Architecture](architecture.md): what exists today, target component boundaries, and decisions still open.
2. [Specification summary](specification-summary.md): MVP behavior and the graph/LLM/security contract at a glance.
3. [Incremental implementation plan](implementation-plan.md): execution phases mapped to the detailed task ledger.
4. [Workspace integration guide](workspace-integration.md): how to bring in real service and E2E repositories without mixing codebases or indexing the wrong scope.

## Source of Truth

This pack summarizes, but does not replace, the detailed artifacts:

- [Full specification package](../spec/README.md)
- [Task ledger](../task-ledger.md)
- [Repository and single-flow context](../repository-context.md)
- [Initial ontology](../ontology.md)
- [Security checklist](../security.md)
- [Existing graphify README](../../README.md)

If a summary and its detailed source disagree, the detailed source is authoritative until the owner updates both. Repo-specific facts, selected technologies, and security approvals remain **TBD** until recorded with evidence in repository context or a decision record. Do not infer them from examples.

## Working Boundary

The current repository is the graph-building tool. The future benefits application repositories and E2E project are separate source inputs. Keep them as separate sibling checkouts; do not copy them into `codegraph/`, `tests/sample/`, or generated graph-data directories. Only ingest approved, pinned revisions through an explicit manifest and allowlisted paths.