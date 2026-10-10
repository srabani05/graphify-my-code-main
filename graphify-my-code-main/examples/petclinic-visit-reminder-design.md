# HLD + LLD: Vet-visit email reminders

**Requirement:** Send email reminders to pet owners the day before a scheduled vet visit.
**Designs from:** `examples/petclinic-visit-reminder-prd.md` (approved draft)
**Codebase:** spring-petclinic (knowledge graph: `final-joern.kuzu`, Joern engine)

---

## High-level design

### Components
| Component | New / Modified | Responsibility |
|---|---|---|
| `VisitReminderService` (`@Service`) | **New** | Daily job: find tomorrow's visits, resolve owners, send emails, mark sent |
| `EmailService` (`@Service`) | **New** | Thin wrapper over `JavaMailSender`; builds the reminder message |
| `Owner` (entity) | **Modified** | Add `email` field |
| `Visit` (entity) | **Modified** | Add `reminderSent` flag |
| `OwnerRepository` | **Modified** | Add a date-based visit lookup (no `VisitRepository` exists in the graph) |
| Owner form binding (`OwnerController`) | **Modified** | Allow binding the new `email` field on create/update |
| `spring-boot-starter-mail` | **New dependency** | No mail infrastructure exists in the codebase today |

### Data flow
```
@scheduler (daily 08:00)
  └─► VisitReminderService.sendReminders()
        ├─► OwnerRepository.findVisitsByDate(tomorrow)   // new query method
        ├─► per Visit: resolve Owner via pet (Owner.pets / Pet.visits)
        │     (skip + log if owner.email is blank)
        ├─► EmailService.sendReminder(owner, pet, visit)
        └─► visit.reminderSent = true  →  OwnerRepository.save(owner)  // cascade
```

### Sequencing
1. Migration + entity changes (`Owner.email`, `Visit.reminderSent`).
2. `EmailService` with `JavaMailSender` config (SMTP host/port/credentials externalized).
3. `VisitReminderService` with `@Scheduled(cron = "0 0 8 * * *")`.
4. Manual trigger endpoint (optional, admin-only) reusing `sendReminders()` for ops verification.
5. Backfill/collect owner emails; enable the schedule.

### Endpoints
- **No new public endpoints required for MVP.** Booking flow (`GET`/`POST /owners/{ownerId}/pets/{petId}/visits/new`) is untouched.
- Optional: `POST /admin/reminders/trigger` (admin-only) → `VisitReminderService.sendReminders()` for on-demand runs.

---

## Low-level design

### 1. `org.springframework.samples.petclinic.owner.Owner` — add email
```java
// new field + accessor pair, following the existing style (cf. telephone)
private String email;
public String getEmail() { return this.email; }
public void setEmail(String email) { this.email = email; }
```
- DB: `V<next>__add_owner_email.sql` → `ALTER TABLE owners ADD COLUMN email VARCHAR(255);`
- Form: extend `OwnerController`'s allowed-fields setup (`setAllowedFields`, as used by `processCreationForm` / `processUpdateOwnerForm`) with `"email"`; add the input to the owner create/update forms. Validation: `@Email` on the field, consistent with existing field validation.

### 2. `org.springframework.samples.petclinic.owner.Visit` — add idempotency flag
```java
// Visit today has only: date, description  (per the graph)
private boolean reminderSent = false;
public boolean isReminderSent() { return this.reminderSent; }
public void setReminderSent(boolean reminderSent) { this.reminderSent = reminderSent; }
```
- DB: `V<next>__add_visit_reminder_sent.sql` → `ALTER TABLE visits ADD COLUMN reminder_sent BOOLEAN DEFAULT FALSE;`

### 3. `OwnerRepository` — date-based lookup (new method)
The graph shows `OwnerRepository` exposing only `findById` / `findByLastNameStartingWith`, and **no `VisitRepository` exists** — visits persist via `OwnerRepository.save` cascade from `VisitController.processNewVisitForm`. Two options:
- **(a)** Add `List<Owner> findOwnersWithVisitsOn(LocalDate date)` with a `@Query` joining owner → pets → visits on `visit.date = :date AND visit.reminderSent = false`. Keeps the existing repository topology.
- **(b)** Create a new `VisitRepository` with `findByDateAndReminderSentFalse(LocalDate)`. Cleaner, but introduces a repository the codebase deliberately doesn't have.
- Recommended: **(a)** — smaller diff, consistent with the cascade-persistence model the graph reveals.

### 4. New `org.springframework.samples.petclinic.reminder.EmailService`
```java
@Service
public class EmailService {
    private final JavaMailSender mailSender;
    public void sendReminder(Owner owner, Pet pet, Visit visit);  // subject/body assembly + send
}
```
- Subject: `"Reminder: vet visit for {pet.name} tomorrow ({visit.date})"`.
- Body: owner first/last name, pet name + type, visit date + description, clinic contact line.
- Config: `spring.mail.*` in `application.properties`; credentials from environment, never committed.

### 5. New `org.springframework.samples.petclinic.reminder.VisitReminderService`
```java
@Service
public class VisitReminderService {
    @Scheduled(cron = "0 0 8 * * *")
    @Transactional
    public void sendReminders() {
        LocalDate tomorrow = LocalDate.now().plusDays(1);
        for (Owner owner : owners.findOwnersWithVisitsOn(tomorrow)) {
            for (Pet pet : owner.getPets())
                for (Visit visit : pet.getVisits()) {
                    if (visit.getDate().equals(tomorrow) && !visit.isReminderSent()) {
                        if (owner.getEmail() == null || owner.getEmail().isBlank()) {
                            log.warn("skipping reminder, no email: owner {}", owner.getId());
                            continue;
                        }
                        emailService.sendReminder(owner, pet, visit);
                        visit.setReminderSent(true);
                    }
                }
        }
    }   // @Transactional flushes reminderSent via the existing cascade
}
```
- Exact call chain: scheduler → `sendReminders` → `OwnerRepository.findOwnersWithVisitsOn` → `EmailService.sendReminder` → JPA flush on transaction commit.
- `@EnableScheduling` on the application class (verify not already present — the graph shows no scheduled jobs today).

### 6. Edge cases
| Case | Handling |
|---|---|
| Owner has no email (pre-existing data) | Skip + warn-log; do NOT mark `reminderSent` (retry tomorrow) |
| Visit deleted/rescheduled after 08:00 run | Next day's run sees the new date; `reminderSent` on the old row is moot |
| Same-day booking after the run | Out of scope (non-goal); picked up never — documented, not silent |
| Mail server down | Exception propagates, transaction rolls back, `reminderSent` stays false → retried next run; alert on repeated failure |
| Duplicate scheduler instances | Single-instance assumption for MVP; note for clustered deploys (needs a distributed lock) |

### 7. Tests to add
- `VisitReminderServiceTest`: visit tomorrow + owner with email → `EmailService` invoked once, `reminderSent` true.
- Owner without email → no send, `reminderSent` stays false, warning logged.
- Already-sent visit → not re-sent (idempotency).
- `OwnerControllerTests`-style MVC test: owner create/update form binds `email` (extends the existing 21-test `OwnerControllerTests` pattern).

---
*Generated from the code knowledge graph: every class, method, endpoint, field, and call chain named above was read from the extracted graph, not assumed.*
