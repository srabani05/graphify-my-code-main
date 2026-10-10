# Security and Privacy Checklist

Security and privacy review is a release gate, not a follow-up hardening task. Confirm applicable internal policies and obtain the security/compliance owner's approval before connecting production-derived sources or inviting pilot users.

## Data Minimization and PII

- [ ] Inventory all source types, owners, environments, and data classifications before ingestion.
- [ ] Ingest schema and field metadata only from config tables, CSV, JSON, and YAML; exclude row-level/member-level values.
- [ ] Keep raw artifacts inside approved internal infrastructure; do not send source, configs, tests, graph records, or prompts to an unapproved external service.
- [ ] Detect and redact direct identifiers and sensitive values before graph writes, prompt construction, generated output, and logging.
- [ ] Fail closed on redaction errors or uncertain classification; quarantine the artifact and record a safe diagnostic without copying its contents.
- [ ] Verify no PII in graph properties, indexes, backups, caches, traces, test fixtures, or audit events.
- [ ] Use synthetic or approved sanitized data for development and acceptance tests.
- [ ] Define retention and deletion behavior for graph records and source-derived metadata.

## Access and Operations

- [ ] Require authenticated access through the approved identity provider.
- [ ] Enforce server-side least-privilege roles: BA/PO access is limited to approved non-sensitive graph data; Dev/Arch access is broader only where authorized.
- [ ] Authorize both graph reads and writes; do not rely on UI filtering as an access control.
- [ ] Encrypt graph data, backups, and transport in accordance with internal standards; restrict network access to approved workloads.
- [ ] Audit queries and mutations with actor, timestamp, action, and outcome while excluding query parameters or results that could contain sensitive data.
- [ ] Protect secrets through approved secret management; never commit credentials or include them in prompts/logs.
- [ ] Review service accounts, backup access, restore procedures, and incident response before pilot.

## Validation Evidence

- [ ] Automated fixtures prove representative PII patterns are rejected/redacted and safe metadata remains ingestible.
- [ ] Tests inspect persisted graph properties and captured logs/prompts for forbidden values.
- [ ] Access-control tests verify BA/PO and Dev/Arch permissions at the query/API boundary.
- [ ] Audit tests verify reads and writes are recorded without sensitive payloads.
- [ ] Security owner signs off on deployment boundary, model/provider, retention, and pilot access.