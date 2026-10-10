# M2-2: Implement config-metadata importer PoC

**Labels:** `epic:ingestion-config`, `milestone:MVP-flagship-flow`, `priority:P1`, `security-review`

## Goal

Import schema and field metadata needed to connect flagship-flow configuration to clients, plans, and rules without persisting row-level values.

## Scope

Support the pilot's approved config formats (for example, DB schema, CSV headers, JSON/YAML structure). Map field definitions to ontology metadata where approved. Do not ingest configuration values unless separately classified and explicitly approved; exclude all member-level records.

## Acceptance Criteria

- [ ] Supported formats and source allowlist are documented.
- [ ] Import produces ConfigArtifact and Field metadata with source provenance.
- [ ] Mapping rules for fields such as client and plan identifiers are documented without retaining their raw values.
- [ ] PII-like field names are classified as metadata only; no associated values are stored.
- [ ] Redaction/minimization tests cover representative fixtures and inspect persisted graph properties and logs.
- [ ] Import fails closed and quarantines input when classification/redaction is uncertain.

## Dependencies

M1-1 ontology; pilot config owner; approved sanitized schema samples.