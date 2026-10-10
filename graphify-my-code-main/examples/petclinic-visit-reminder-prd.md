# PRD: Vet-visit email reminders

**Requirement:** Send email reminders to pet owners the day before a scheduled vet visit.
**Codebase:** spring-petclinic (knowledge graph: `final-joern.kuzu`, Joern engine)
**Date:** 2026-10-03 · Status: Draft

## 1. Problem
Pet owners forget scheduled vet visits. Missed visits waste clinic capacity and delay animal care. Today the system records visits (`POST /owners/{ownerId}/pets/{petId}/visits/new` → `VisitController.processNewVisitForm`) but never proactively notifies anyone afterwards — the visit data just sits in the database.

## 2. Users
- **Pet owners** (`org.springframework.samples.petclinic.owner.Owner`) — receive the reminder.
- **Clinic staff** — benefit from fewer no-shows; no new UI needed for MVP.

## 3. Goals
- Every visit scheduled for tomorrow triggers exactly one reminder email to the owning owner, sent the day before.
- Zero changes to the existing visit-booking flow (`initNewVisitForm` / `processNewVisitForm` keep working untouched).

## 4. Non-goals
- No SMS, push, or in-app notifications.
- No recurring/cascading reminders (one email, one time).
- No owner preference center (no opt-out UI in MVP; logged skip instead).
- No reminder for same-day bookings made after the daily send.

## 5. Proposed behavior (mapped to the real codebase)
- A daily scheduled job (e.g. 08:00) finds all `org.springframework.samples.petclinic.owner.Visit` entities whose `date` field equals tomorrow.
- For each visit it resolves the owner: `Visit` → pet → `Owner` (via `Owner.pets` / `Pet.visits` associations; owner lookup through `OwnerRepository.findById`, the same repository `VisitController` already uses).
- It emails the owner the pet name, visit date, and `Visit.description`, then marks the visit so it is never reminded twice.
- Visits are created today through `VisitController.processNewVisitForm`, which persists via `OwnerRepository.save` (cascade owner → pet → visit). The reminder job reads the same object graph — no booking-flow changes.

## 6. Data changes
- **New:** `Owner.email` (`String`). The graph proves this does not exist today — `Owner` has only `address`, `city`, `pets`, `telephone` (+ inherited `firstName`/`lastName`). Requires a DB migration and adding `email` to the owner form binding (`OwnerController`'s allowed-fields setup, mirroring `processCreationForm` / `processUpdateOwnerForm`).
- **New:** `Visit.reminderSent` (`boolean`, default false) — makes the daily job idempotent.
- **New dependency:** `spring-boot-starter-mail` (or equivalent). The graph shows **no existing email infrastructure** — no `JavaMailSender`, no mail queue entities, no notification service. This is greenfield inside the codebase.

## 7. Risks
- `Visit.date` is a **date, not a timestamp** — "day before" is calendar-day arithmetic; time-zone edge cases are limited but the send time (08:00 server time) must be documented.
- Owners registered before this ships have no email → the job must skip-and-log, not fail.
- No existing mail infra means new operational surface: SMTP credentials, sender reputation, template rendering.

## 8. Open questions
1. Which email provider / SMTP relay does the clinic use? (drives the `JavaMailSender` config)
2. Should the reminder include clinic contact info / cancellation instructions?
3. Is 08:00 the right send time, or should owners get it the prior evening?
4. Do we backfill `email` for existing owners, or collect it at next visit?

---
*Generated from the code knowledge graph: every class, method, endpoint, and field named above was read from the extracted graph, not assumed.*
