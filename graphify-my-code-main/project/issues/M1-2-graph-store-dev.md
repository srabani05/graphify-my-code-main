# M1-2: Provision internal graph-store dev environment

**Labels:** `epic:graph-store`, `milestone:MVP-flagship-flow`, `priority:P0`, `security-review`

## Goal

Select and provision a development graph store inside the approved internal boundary.

## Scope

Compare the existing Kuzu prototype with internal Neo4j/Neptune options against deployment approval, access control, auditability, encryption, backup/restore, operational ownership, Cypher compatibility, and cost. Provision only after the approved hosting boundary and security owner are confirmed.

## Acceptance Criteria

- [ ] Decision record compares candidate stores and documents the selected option and rationale.
- [ ] Development instance is reachable only from approved identities/workloads and network paths.
- [ ] Encryption, backup, retention, and restore expectations are documented.
- [ ] Initial schema constraints and indexes for stable ontology IDs are applied.
- [ ] Read/write authorization and audit-event approach is demonstrated.
- [ ] No production member data is loaded; test data is synthetic or approved sanitized data.
- [ ] Security/compliance owner approves the development boundary before use.

## Dependencies

M1-1 ontology draft; internal hosting, identity, and security requirements.