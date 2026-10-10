# M1-1: Define ontology and naming conventions

**Labels:** `epic:domain-modeling`, `milestone:MVP-flagship-flow`, `priority:P0`

## Goal

Agree on the initial benefits-domain graph vocabulary and stable identifier conventions for the flagship flow.

## Scope

Define node properties and permitted relationships for Client, Plan, Transaction, EligibilityRule, EnrollmentRule, ConfigArtifact, Field, Service, Endpoint, CodeEntity, TestFlow, TestStep, Document, and Ticket. Reconcile this draft with the pilot BA/PO and domain owners; identify which types are genuinely needed for the MVP.

## Acceptance Criteria

- [ ] Ontology documents node purpose, metadata-only properties, and allowed relationship direction/meaning.
- [ ] `BR-`, `FLOW-`, `API-`, and `CFG-` identifier conventions are approved and stable.
- [ ] Source provenance and treatment of uncertain heuristic matches are defined.
- [ ] PII classification metadata is documented without example member values.
- [ ] Sample New hire → Eligibility → Enrollment → Premium calculation graph is reviewed by BA/PO and engineering.
- [ ] Schema decisions are recorded, including unresolved graph-store-specific constraints.

## Dependencies

Pilot client and flagship flow selection; domain-owner availability.