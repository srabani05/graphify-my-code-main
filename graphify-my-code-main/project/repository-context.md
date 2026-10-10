# Repository Context: Single-Flow Graph

**Purpose:** Keep the minimum reliable context needed to build and later share a knowledge graph for one end-to-end feature flow across its owning code, E2E tests, configuration metadata, contracts, and approved documentation.

**Status:** Intake template; target application repositories have not yet been inventoried in this workspace. Do not treat example labels or the proposed flow below as confirmed facts.

## 1. Pilot Flow

**Selected client/tenant:** TBD  
**Feature / flow name:** TBD; proposed candidate is **New hire → Eligibility → Enrollment → Premium calculation**  
**Business owner (BA/PO):** TBD  
**Technical owner:** TBD  
**Trigger:** TBD  
**Start event:** TBD  
**End state / observable outcome:** TBD  
**In-scope variants and exceptions:** TBD  
**Explicitly out of scope:** Every other feature flow unless required to explain a dependency of this flow.

Confirm the candidate flow with the BA/PO before collecting source artifacts. Keep the graph boundary to the smallest set of repositories and paths that provide evidence for this flow.

## 2. Repository Inventory

Add one row per repository needed to explain or test the selected flow. Record a local path or approved repository URL, never credentials or tokens. Pin the branch and commit used for each extraction so the graph can be reproduced.

| Repo alias | Role in this flow | Local path / approved URL | Branch and commit | Stack / build | Owner | Status |
|---|---|---|---|---|---|---|
| `service-*` | Service implementing a flow step | TBD | TBD | TBD | TBD | Not inventoried |
| `e2e-*` | Automated scenario and assertions | TBD | TBD | TBD | TBD | Not inventoried |
| `config-*` | Config schema, migrations, or metadata | TBD | TBD | TBD | TBD | Not inventoried |
| `contracts-*` | API, event, or message contracts | TBD | TBD | TBD | TBD | Not inventoried |
| `docs-*` | Approved requirements or design evidence | TBD | TBD | N/A | TBD | Not inventoried |

Remove rows that are not applicable; add rows only when there is evidence that the repo participates in this single flow. Note shared libraries or platform repos only when a traced dependency reaches them.

### Current Workspace Boundary

The current workspace contains the graphify/codegraph tool and sample fixtures, not the target benefits application or its E2E project. The paths above must be populated from the approved target repositories; no application repository layout is assumed here.

## 3. Relevant Directory Map

Record the useful subtrees and key files, not a full recursive dump of every repository. Include source, test, configuration schema, API/event contract, build, and documentation locations that are in scope for the flow.

```text
<repo-root>/
  <application source path>/       # flow implementation
  <test source path>/               # E2E scenarios and assertions
  <schema or contract path>/        # metadata only; no row-level data
  <approved docs path>/             # requirements/design evidence
  <build file>                      # language/framework/dependencies
```

| Repo alias | Relevant path | Why it matters to this flow | Include in extraction? |
|---|---|---|---|
| TBD | TBD | TBD | Yes / No |

## 4. Flow-to-Evidence Map

Fill one row per meaningful step or transition. Paths, symbols, test names, and contract identifiers should point to evidence in the pinned repository revisions. Mark unknown links as gaps rather than inferring them silently.

| Step | Behavior / transition | Owning repo and source path/symbol | API, event, or message | Config/schema metadata | E2E repo and test name | Evidence confidence / open question |
|---:|---|---|---|---|---|---|
| 1 | TBD | TBD | TBD | TBD | TBD | TBD |
| 2 | TBD | TBD | TBD | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD | TBD | TBD | TBD |

Use as many rows as the confirmed flow requires. Do not force unrelated code into the path to make the graph look complete.

## 5. Cross-Repository Contracts

| Producer repo / component | Consumer repo / component | Contract type and stable ID | Contract source path | Flow step | Verified by |
|---|---|---|---|---|---|
| TBD | TBD | HTTP / event / queue / database schema | TBD | TBD | E2E test or contract test TBD |

Record versioning, asynchronous handoffs, retries, and ownership where relevant. Do not copy payloads containing member data into this document or graph.

## 6. Extraction Scope and Exclusions

**Allowlisted repositories and paths:** Complete sections 2–4 and use exact pinned revisions.  
**Allowed graph content:** Code structure and relationships, endpoint/contract metadata, test names and step/assertion metadata, configuration schemas/field metadata, and approved document references.  
**Never ingest:** Member-level records, real request/response bodies, credentials, tokens, production database exports, or unsanitized test fixtures.  
**Excluded paths:** Build outputs, dependency caches, generated files, secrets/config values, unrelated features, and any path not approved by the repository owner.  
**Data and artifact location:** TBD; must be inside the approved internal boundary.  
**Security approval / date:** TBD.

The existing codegraph extractor currently handles Java, Python, and MyBatis mapper XML. Config-schema and E2E `TestFlow` ingestion require additional implementation; inventorying a path here does not mean the current tool can safely or correctly parse it.

## 7. Reproducibility and Sharing

- Record the extraction date, tool revision, parser/engine, selected repository commits, and graph database version for each shared graph snapshot.
- Keep raw source repositories under their existing access controls; share this context file and graph results only with approved audiences.
- Before sharing, remove local paths, internal hostnames, sensitive identifiers, and any source text not approved for that audience.
- Share a flow summary with evidence references and known gaps; do not share member data or imply that inferred relationships are domain-validated.

## 8. Readiness Checklist

- [ ] BA/PO confirms one flow, client context, start event, end state, and important exceptions.
- [ ] Repository owners approve each listed repo and path; branches/commits are pinned.
- [ ] E2E scenarios for the flow are identified by file and test name.
- [ ] API/event/config/document evidence is mapped to flow steps, with unknowns called out.
- [ ] Security/compliance approves the source boundary and sample artifacts.
- [ ] Inputs are synthetic or approved sanitized material; no member-level PII is present.
- [ ] Extraction support and missing adapters are understood before claiming graph coverage.