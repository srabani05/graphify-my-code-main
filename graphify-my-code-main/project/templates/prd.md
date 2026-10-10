# PRD: [Change title]

**Status:** Draft  
**Owner:** [BA/PO]  
**Client:** [Client ID/name approved for this document]  
**Flow:** [FLOW-ID and name]  
**Related rules:** [BR-IDs]  
**Last updated:** [YYYY-MM-DD]

> Generated content is a starting point. A BA/PO and technical owner must validate each claim against approved source evidence. Do not include member-level PII.

## Background

[Business context and reason for the change. Cite approved documents or tickets.]

## Problem and Desired Outcome

[Who is affected, what problem they face, and what outcome is expected.]

## Current Behavior

[Graph-grounded behavior summary. List linked rules, services, endpoints, configuration metadata, and test flows with source references. Mark unknowns explicitly.]

## Proposed Requirements

| ID | Requirement | Rationale | Acceptance criteria |
|---|---|---|---|
| REQ-001 | [Requirement] | [Why] | [Observable, testable result] |

## Scope

**In scope:** [Behaviors and flows included]  
**Out of scope:** [Explicit exclusions]

## Impacted Components and Evidence

| Component or entity | Expected impact | Evidence/source | Confidence or open question |
|---|---|---|---|
| [Service, endpoint, rule, config, test] | [Change/verify/no change] | [Repository path, document, or graph ID] | [High/medium/low; explain uncertainty] |

## Gap Checklist

- [ ] Existing behavior confirmed with BA/PO.
- [ ] Rules and configuration metadata cover the proposed change.
- [ ] Impacted endpoints and services reviewed with engineering.
- [ ] Existing tests cover the changed behavior or new tests are identified.
- [ ] Missing evidence and unresolved assumptions are assigned an owner.
- [ ] Security, privacy, audit, and access-control impacts reviewed.

## Test Scenarios

| Scenario | Given | When | Then | Existing/new test reference |
|---|---|---|---|---|
| [Scenario] | [Context] | [Action] | [Expected result] | [FLOW-ID or planned test] |

## Assumptions, Risks, and Open Questions

- [Assumption, risk, or question; owner and resolution date]

## Example: Waiting Period Change (30 to 60 Days)

**Background:** A proposed policy change increases the waiting period before a new hire becomes eligible from 30 to 60 days. Confirm policy authority and effective date with the domain owner.

**Requirement draft:** For the selected client and in-scope plan, calculate eligibility no earlier than 60 days after the applicable hire date, subject to approved policy exceptions.

**Open validation:** Confirm day-count convention, boundary behavior, effective-date handling, impacted configuration fields, client/plan scope, exceptions, and existing eligibility tests. Do not infer these details from code alone.