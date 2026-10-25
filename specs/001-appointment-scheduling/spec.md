# Feature Specification: SlotBook Appointment Scheduling MVP

**Feature Branch**: `001-appointment-scheduling` (verified current Git branch)

**Created**: 2026-10-24

**Status**: Approved specification and technical design baseline — all fifteen clarification
answers preserved; D-001–D-012 product choices resolved. Technical-plan approval was formally
recorded on 2026-10-25; T-02 remains provisional and T-03 conditional. Implementation is not authorized.

**Approved**: 2026-10-25 by the human project owner.

**Approved Source Revision**: Git blob `d180b9b83857cfd4ebf4ed118d2e74f3aa94512e`.
Approval finalization changes only review/status records; source reconciliation remains planning work.

**Current Specification Revision**: A-003, including approved A-001 and clarified A-002,
explicitly approved by the human project owner on 2026-10-25. Original approval provenance
above and the fifteen historical Q/A answers are preserved. Current receipt/recovery semantics
are amended only as recorded in [A-002](amendments/A-002-durable-admission.md) and
[A-003](amendments/A-003-disaster-recovery.md); A-001 clock/DST behavior remains unchanged.
T-01/T-04 are approved, T-02 provisional pending runtime verification, T-03 conditional on
backup/hosting restrictions. None authorizes tasks or implementation.

**Input**: User request to specify public activity browsing, availability and guest booking,
protected administration, responsive use, understandable failures, and consistent time display
within SlotBook's existing MVP boundaries.

## Clarifications

### Session 2026-10-24

- Q: Who should be allowed to cancel bookings in the MVP? → A: Administrator only. Guests
  request cancellation from the host; there is no guest self-service cancellation in the MVP.
- Q: During daylight-saving clock changes, how should SlotBook offer local times that are
  skipped or occur twice? → A: Omit nonexistent local starts and offer both occurrences of
  repeated starts as distinct instants with distinct timezone-offset labels, when otherwise
  eligible. This choice does not settle transition-spanning working-window boundaries.
- Q: What should happen to existing confirmed bookings when the administrator changes
  activity details, working hours, or blocked dates? → A: Preserve each existing booking's
  agreed start, end, and status. Apply changes to new bookings and warn the administrator
  about affected existing bookings. Cancellation remains an explicit individual action.
- Q: If a guest submits a booking but loses the response, how should they recover? → A: Offer
  a safe retry of the same attempt. Return its existing result or complete it at most once
  under current eligibility rules; otherwise return a definite rejection. Show confirmation
  as unverified until the outcome is known. Required contract support is follow-up work.
- Q: How long should SlotBook retain a guest's name and email after their appointment ends
  or their booking is canceled? → A: Remove the guest's name and email after 30 days, counted
  from appointment end for non-canceled bookings or from cancellation for canceled bookings.
  Retained booking history must no longer contain those contact details after that period.

### Session 2026-10-25

- Q: Should a blocked date prevent new bookings for one selected activity or for every
  activity? → A: Per activity, using that activity's local date and IANA timezone. Other
  activities are unaffected, and existing confirmed bookings remain unchanged.
- Q: Which booking horizon and minimum notice should SlotBook enforce, including the exact
  cutoff boundaries? → A: A start must be at least one elapsed hour and no more than 60 × 24
  elapsed hours ahead, with both boundaries inclusive. Limits apply to the start, not the end,
  use current system time, and are checked again on submission without a browsing grace period.
- Q: Which timezone should visitors initially see, and which timezone should define the
  calendar date they select? → A: Start in the visitor's detected timezone, allow them to
  change it, and interpret calendar dates in the selected display timezone. Fall back to the
  activity's timezone if detection is unavailable. Working hours and blocked dates continue
  to use the activity's timezone.
- Q: Should weekly working windows be allowed to overlap or cross midnight? → A: Neither.
  Require non-overlapping windows contained within one activity-local calendar day. Touching
  windows are allowed, but each appointment must fit inside one window. Overnight schedules
  are outside MVP scope; windows are not automatically combined.
- Q: What should happen when the administrator cancels a booking that is already canceled?
  → A: Acknowledge the existing canceled state as a successful no-op. Make no further changes,
  preserve the original cancellation time, and do not restart the 30-day contact-retention period.

**Round 3**

- Q: How long should an administrator stay signed in before being required to authenticate
  again? → A: A fixed 60-minute session from login. Activity does not extend it, and there is
  no automatic renewal. At expiration the server rejects protected actions and requires
  credentials again. Preserve only non-sensitive configuration drafts; failed changes require
  review and explicit resubmission after reauthentication. Token-storage design remains for planning.
- Q: How long should a guest's private booking-attempt identifier remain valid for safe
  retries? → A: 24 elapsed hours from first system receipt, without extension. Create a private,
  unpredictable identifier before the first submission and reuse it only with the same details.
  Changed details are rejected; simultaneous identical retries converge on at most one booking
  and its result, or report processing while unfinished. Retry confirmations omit guest name/email.
  At expiry reject retries, never treat the identifier as new, and advise host verification
  if the result is unknown. A genuinely new attempt requires a new identifier.
- Q: Which deletion and backup policy should enforce the already approved 30-day guest-contact
  limit? → A: Contact-free backups/exports only. Define the deadline as 720 elapsed hours from
  the booking's recorded end or first successful cancellation. Automatically delete contacts
  at the deadline and hide them from all reads at/after it; surface cleanup failures without
  extending retention. Apply this to attempt/recovery copies. Retain only booking reference,
  activity, start/end, status, and original cancellation time as contact-removed history, not
  a claim of irreversible anonymity. Backup loss of guest contacts is an accepted MVP tradeoff.
- Q: How should a working window behave when a daylight-saving change skips or repeats one
  of its boundary times? → A: Use its valid portions without moving the configured local-clock
  limits. Skip nonexistent starts and distinguish both repeated occurrences when eligible.
  The appointment's full elapsed duration must fit continuously within one real portion of
  that same local-clock window; do not bridge a portion outside its limits.
- Q: Should every activity require a description, and how should descriptions appear to
  guests and the administrator? → A: Require 1–2000 Unicode code points after trimming outer
  whitespace, allowing multiple lines. Empty/whitespace-only and overlong values are rejected,
  never silently truncated. Treat markup literally as plain text. Administrators edit the
  full description with validation feedback; the catalog may preview it, but full text is
  available on activity selection before booking.

The first and second clarification rounds each recorded five accepted answers.
The third round recorded five answers and preserves all ten earlier answers.
Product clarification is complete for D-001–D-012. On 2026-10-25 the human project owner
separately approved this complete specification, its requirements checklist, and constitution
1.2.0, and authorized technical planning with source reconciliation in scope. Individual answers
and checklist markers alone did not grant that approval. No technical plan, concrete contract
amendment, implementation, or passing application tests are approved or evidenced by this record.

## Approved Amendments

### A-001 — Clock-aligned appointment starts (2026-10-25)

The human project owner explicitly approved this amendment after planning identified P-01.
Appointment starts MUST be on minutes 00, 15, 30, or 45, with zero seconds/fractional seconds,
in the activity's IANA timezone. The grid is independent of working-window start and visitor
display timezone. A 09:10 window first permits 09:15 only if the entire appointment fits one
continuous valid portion of that window. Never round or shift a submitted off-grid instant.
The previous fifteen clarification answers, including skipped/repeated-time behavior and
distinct offsets for repeated local times, remain unchanged. P-01 is resolved.

Affected requirements and verification: FR-004/005, SC-002, US1.7–8, US2.16 and US5.13.
The [amendment record](amendments/A-001-clock-aligned-starts.md) documents rationale, compatibility,
agent/test impact and source reconciliation. This product approval does not approve the technical
plan, concrete contract changes, tasks or implementation. Stop for technical-plan review.

### A-002 — Persisted database admission timestamp (approved with clarification, 2026-10-25)

An attempt is valid only after admission commits durably. Its immutable database-generated
receipt timestamp T is persisted with the original binding in that successful transaction;
expiry is exactly E=T+24 elapsed hours. T is not PostgreSQL commit metadata or commit/HTTP
acknowledgement time. A delayed commit consumes the fixed window and never resets it; a key
committed at/after E is already expired and cannot execute or return pending. A known rollback
admits nothing through that transaction. An uncertain COMMIT remains unverified until a fresh
committed-state read resolves it. Only proven committed, matching, unexpired unfinished attempts
may return ordinary pending. See the [approval/impact record](amendments/A-002-durable-admission.md).

### A-003 — Qualified disaster-recovery invalidation (approved, 2026-10-25)

A separately human-approved disaster restore unable to preserve retry state may invalidate old
identifiers, including unexpired ones. Return 409 attempt_invalidated_by_restore with unknown-
outcome/host-verification guidance, distinct from ordinary 410 attempt_expired. Never silently
issue a new key, infer no booking exists, or restore guest contacts. Normal restart, routine
maintenance and transient failure preserve the original valid identifiers/T/E/results and never
invoke this exception. See the [approval/impact record](amendments/A-003-disaster-recovery.md).

These amendments refine FR-008/012/022/024/029, D-009/011, SC-011/017 and affected acceptance
cases. Twelve new cases supplement the A-001-stage 65, for 77 current scenarios. T-02 runtime
verification, T-03 operational restrictions, future PRD/TypeSpec reconciliation and separate
implementation authorization remain required; no runtime checks are claimed by product approval.

## User Scenarios & Testing *(mandatory)*

Priorities express delivery order, not permission to omit a journey. All five stories are MVP
release requirements. Public stories can be demonstrated with prepared activities and schedules;
real administrator configuration is a dependency for operating the complete product.
Scenarios use synthetic data. The recorded product choices and complete specification are
approved; concrete contract changes and technical design remain separate review obligations.

### User Story 1 - Discover an appointment type and date (Priority: P1)

As a visitor, I want to compare available appointment types and choose a date so I can find
an appointment that meets my needs without creating an account.

**Why this priority**: Discovery is the entry point to every public booking.

**Independent Test**: With prepared active/inactive activities and known schedules, a visitor
can browse, choose an activity, and navigate to a date's availability without administrator access.

**Acceptance Scenarios**:

1. **Given** active and inactive activities, **When** a visitor opens the catalog, **Then**
   only active activities are listed with their name, description, and duration.
2. **Given** an active activity with a known available date, **When** the visitor selects it,
   **Then** they can choose that date and see the activity and date context for available slots.
3. **Given** no active activities, **When** the visitor opens the catalog, **Then** an explicit
   empty state appears without suggesting an appointment was reserved.
4. **Given** a selected date with no eligible slots, **When** availability is shown, **Then**
   the visitor sees that no slots are available and can choose another date.
5. **Given** an activity that does not exist or is no longer active, **When** a visitor attempts
   to select it or continue from an older view, **Then** they receive an understandable
   unavailable-activity message and cannot create a booking for it.
6. **Given** an active activity with a valid multiline description, **When** a visitor browses
   and selects it, **Then** the catalog includes its description or a preview with access to
   full text, and the full description is available before booking. Markup-like content is
   ordinary visible text, never interpreted formatting or executable content.
7. **Given** an otherwise available activity-local window 09:10–10:00 and a 30-minute activity,
   **When** starts are offered, **Then** 09:15 and 09:30 are eligible, 09:10 and 09:25 are not
   on the clock-aligned grid, and 09:45 is excluded because its end would exceed the window.
   The window is not shifted, and 09:30 may end exactly at 10:00.
8. **Given** an otherwise available activity-local window 09:10–09:40 and a 30-minute activity,
   **When** availability is requested, **Then** there are no eligible starts: 09:10 is off-grid
   and 09:15 would end outside the window. The system does not round or extend the window.

---

### User Story 2 - Reserve an available appointment (Priority: P1)

As a visitor, I want to choose an available time, provide my name and email, and receive a
confirmation so I know that my appointment has been reserved.

**Why this priority**: A reliable confirmed appointment is the central product outcome.

**Independent Test**: With one prepared activity and schedule, a guest can complete a booking;
a separate competing submission can verify conflict handling without administrator UI actions.

**Acceptance Scenarios**:

1. **Given** an eligible slot, **When** a visitor selects it and submits a non-empty name and
   valid email, **Then** exactly one confirmed booking is created and an on-screen confirmation
   identifies the booking, activity, start/end, and displayed timezone.
2. **Given** a missing name or malformed email, **When** the visitor submits, **Then** no booking
   is created and the affected field is identified with an understandable correction message.
3. **Given** two visitors submitting the same available slot simultaneously using different
   booking-attempt identifiers, **When** both attempts finish, **Then** exactly one receives
   a confirmation, the other receives an
   unavailable-slot outcome, and only one confirmed booking exists.
4. **Given** an interval overlapping a confirmed booking, **When** another visitor requests
   it, **Then** the request is rejected and the existing booking remains unchanged.
5. **Given** an otherwise eligible interval that starts exactly when a confirmed booking ends,
   **When** a visitor books it, **Then** the adjacent appointment can be confirmed.
6. **Given** a displayed slot that becomes past, blocked, inactive, or occupied before submission,
   **When** the visitor submits, **Then** current eligibility is checked again, no ineligible
   booking is confirmed, and the visitor can return to availability.
7. **Given** a booking submission whose final outcome cannot be determined after a connection
   failure, **When** feedback is shown, **Then** it does not claim success or definite failure,
   does not automatically submit a second booking, and states that confirmation is unverified.
   The guest can explicitly retry the same attempt under the safe-retry policy in D-009.
8. **Given** an attempt that already created a booking but whose response was lost, **When**
   the guest retries that same attempt with matching details before its 24-hour expiry and
   without a qualified A-003 recovery invalidation,
   **Then** the same booking identity and its current
   status are returned without creating another booking, even if availability rules changed
   after the original success. A canceled booking is not recreated or reconfirmed by retrying.
9. **Given** an attempt for which no booking was created, **When** the guest safely retries,
   **Then**, if the identifier is still valid and no final outcome was recorded, it can create
   at most one booking if currently eligible or return a definite
   rejection if ineligible. Repeated/concurrent retries of the same attempt cannot duplicate
   a booking or expose another guest's result.
10. **Given** an eligibility-evaluation instant T and otherwise eligible starts exactly one
    elapsed hour or exactly 1440 elapsed hours after T, **When** either is evaluated for a new
    booking, **Then** it satisfies the notice/horizon rules. An end beyond the horizon is
    permitted if the start qualifies and the full duration still fits its working window.
11. **Given** an eligibility-evaluation instant T, **When** a new start less than one elapsed
    hour or more than 1440 elapsed hours after T is evaluated, **Then** it is neither offered
    nor accepted, even on a daylight-saving transition date.
12. **Given** a slot eligible when displayed but less than one hour away when submission is
    checked, **When** the guest submits, **Then** the new booking is rejected with notice-period
    feedback. Earlier display grants no hold or grace period; existing confirmed bookings and
    safe retries returning an already completed attempt remain unaffected.
13. **Given** a current-generation committed attempt with persisted database receipt timestamp T,
    **When** matching details are retried before T + 24 elapsed hours, **Then** retries share the original attempt and result
    without extending expiry. At or after T + 24 hours, retries are rejected as expired without
    revealing guest contacts or silently creating a new attempt; an unknown result directs
    the guest to host verification rather than assuming no booking exists.
14. **Given** an identifier already bound to booking details, **When** it is reused with
    different activity, start, name, or email, **Then** a generic mismatch is returned without
    changing the original attempt or revealing its original details/result. Deliberately
    corrected details require a new attempt, never an automatic replacement after uncertainty.
15. **Given** simultaneous matching retries with one valid identifier, **When** processing
    completes, **Then** at most one booking exists and all completed retry results refer to
    that identity/status without guest name/email. Ordinary pending requires proven committed,
    matching, unexpired unfinished admission, including after contention; unknown admission
    cannot claim pending. A recorded definite rejection is not reinterpreted as a new booking.
16. **Given** an otherwise eligible window and a request at activity-local 09:10, 09:25,
    09:15:30, or 09:15:00.001, **When** a new booking is submitted directly, **Then** it is
    rejected as off-grid without creating a booking or rounding to another instant. The same
    aligned-start validation applies to offered slots and submission-time eligibility.
17. **Given** an HTTP submission whose admission transaction is known to have rolled back,
    **When** feedback is returned, **Then** that transaction establishes no valid attempt and
    starts no booking execution. It claims neither committed pending admission nor confirmation;
    the same key/details are retained for an explicit retry, with no assertion about parallel work.
18. **Given** admission timestamp T stored by the database and commit C delayed after T,
    **When** validity is evaluated, **Then** expiry stays E=T+24h and commit delay consumes
    the window, rather than moving expiry to C+24h. At C>=E the key is already expired:
    no booking/pending/result is returned, and the expired identifier is never treated as new.
19. **Given** admission committed with T/E/binding but its acknowledgement was lost,
    **When** the same key/details are explicitly retried, **Then** the original committed
    timestamp, deadline and binding are used without a new admission or extended window.
20. **Given** an earlier failed HTTP request for which no admission ever committed,
    **When** a later explicit same-key request first commits admission, **Then** its persisted
    database-generated timestamp establishes the only valid T/E, not the earlier HTTP arrival.
21. **Given** a connection failure during COMMIT and an unavailable fresh committed-state read,
    **When** the outcome cannot safely be resolved, **Then** it remains unverified rather than
    claiming rollback, ordinary pending, definite rejection or a confirmed booking. No key is
    replaced or timestamp reset automatically; later committed-state recovery decides the result.
22. **Given** a committed, unexpired attempt and normal API/database/worker restart or transient
    failure, **When** service resumes and the guest retries matching details, **Then** the same
    binding/T/E/result is preserved without rotating generation or applying restore invalidation.
23. **Given** a separately approved disaster restore that cannot recover retry state,
    **When** a still-unexpired prior-generation identifier is retried, **Then** it receives
    409 attempt_invalidated_by_restore, never ordinary chronological-expiry feedback or a new
    booking. The client explains that the outcome is unknown and requires host verification.
24. **Given** an old identifier absent from the restored snapshot, **When** its prior generation
    is presented, **Then** it is rejected as restore-invalidated, not admitted as unseen/new.
    No original outcome or admission is inferred merely from the supplied identifier.
25. **Given** an expired current-generation identifier, **When** it is retried, **Then** it
    receives 410 attempt_expired, distinct from restore invalidation; no ordinary pending,
    new attempt, old result or contact details are returned.
26. **Given** missing retry state or HMAC secret during routine startup without an approved
    unrecoverable restore, **When** readiness is evaluated, **Then** it fails closed and does
    not silently create a new generation, invalidate valid identifiers or replace stored T/E.

---

### User Story 3 - Authenticate and configure appointment offerings (Priority: P2)

As the administrator, I want to sign in and maintain activities, working hours, and blocked
dates so visitors can book only the appointments I offer.

**Why this priority**: Configuration makes the public journey operable beyond prepared examples.

**Independent Test**: With the seeded synthetic administrator, sign in, create/update an
activity, configure its weekly hours, block a date, and verify public availability changes.

**Acceptance Scenarios**:

1. **Given** valid administrator credentials, **When** the administrator signs in, **Then**
   protected management functions become available without any public administrator sign-up.
2. **Given** invalid credentials or no valid administrator session, **When** a user attempts
   to sign in or use protected management functions, **Then** access is rejected without
   exposing booking contacts or modifying protected data.
3. **Given** an authenticated administrator, **When** they create or update an activity with
   valid name, description, unique public identifier, duration, timezone, and active status,
   **Then** those values are retained and reflected in the applicable public view.
4. **Given** a duplicate public identifier, a non-positive duration, a duration not divisible
   by 15 minutes, or an invalid timezone, **When** the administrator saves an activity,
   **Then** the change is rejected with understandable feedback and valid stored data is retained.
5. **Given** a weekly window in an activity's timezone, **When** the administrator saves it,
   **Then** offered starts are at 15-minute increments and each complete appointment fits
   inside the window. Reversed or zero-length windows are rejected.
6. **Given** a blocked local date for activity A and otherwise eligible activity B,
   **When** visitors view availability or attempt new bookings for that date, **Then** activity
   A offers and accepts no new appointments for its blocked date, activity B remains unaffected,
   and existing confirmed bookings remain unchanged.
7. **Given** an administrator session that has expired, **When** a protected action is attempted,
   **Then** it is rejected at or after 60 elapsed minutes from login and reauthentication
   is requested without performing the action. Activity does not extend the deadline.
8. **Given** existing confirmed appointments that would fall outside proposed hours, blocks,
   or active-status rules, **When** the administrator saves those changes, **Then** they are
   warned about affected appointments, the changes apply to new bookings, and existing start,
   end, and status remain unchanged. Affected bookings are not automatically canceled.
9. **Given** an existing 30-minute booking, **When** the activity duration becomes 60 minutes,
   **Then** the existing booking remains 30 minutes and new bookings use 60 minutes. Changing
   the activity timezone likewise does not move any existing booking's start/end instants.
10. **Given** a blocked date in the activity's timezone and a visitor viewing another timezone,
    **When** new availability or booking eligibility is evaluated, **Then** the block is applied
    using the activity-local date, not the visitor's different local date label.
11. **Given** overlapping windows for the same activity/weekday, duplicate windows, or a
    window crossing midnight, **When** the administrator saves the replacement schedule,
    **Then** the change is rejected with understandable feedback and the previous valid
    schedule remains unchanged. Zero-length and reversed windows are also rejected.
12. **Given** otherwise valid touching windows 09:00–10:00 and 10:00–11:00 and a 30-minute
    activity, **When** the schedule is saved and availability is viewed, **Then** both windows
    are accepted, 09:30 can be offered when otherwise eligible, and 09:45 cannot be offered
    because its full duration fits neither individual window. Windows are not silently merged.
13. **Given** a session created at T with otherwise valid credentials, **When** a protected
    operation is authorized before T + 60 elapsed minutes, **Then** it can proceed under normal
    rules. At or after T + 60 minutes, authorization is rejected even if the administrator has
    remained active, and no silent renewal or grace period extends the session.
14. **Given** expiration during editing, **When** the administrator signs in again, **Then**
    only a non-sensitive configuration draft may be restored for review; failed changes are
    not automatically replayed. Passwords and protected guest-contact views are not preserved
    as reauthentication drafts, and expired protected views are cleared or locked.
15. **Given** an administrator creating/updating an activity, **When** its description is
    validated after trimming leading/trailing whitespace, **Then** lengths of 1 and 2000
    Unicode code points pass this constraint; empty/whitespace-only or 2001-code-point values
    are rejected with field feedback and the previous valid saved activity remains unchanged.
16. **Given** a valid description containing international characters, line breaks, and
    markup-like text, **When** it is saved and viewed in admin and public activity views,
    **Then** the full plain text is available without silent truncation or markup execution.
    Only outer whitespace is trimmed; internal text and line breaks are retained.

---

### User Story 4 - Review and cancel appointments (Priority: P2)

As the administrator, I want to review bookings and cancel an appointment so I can maintain
an accurate schedule when circumstances change.

**Why this priority**: Hosts need to manage appointments after guests have booked them.

**Independent Test**: With prepared confirmed/canceled bookings, the authenticated administrator
can inspect appointment details, cancel one booking, and verify the resulting availability.

**Acceptance Scenarios**:

1. **Given** existing bookings and an authenticated administrator, **When** the booking list
   is opened, **Then** booking identity, activity, time, status, and attendee name/email are
   available to the administrator during the contact-retention period, without exposing them
   in public activity or slot views. After that period, history shows that contact details
   have been removed rather than requiring or displaying the original name/email.
2. **Given** a confirmed booking, **When** the administrator cancels it successfully, **Then**
   its status is canceled, it no longer excludes otherwise eligible slots, and other bookings
   are unchanged.
3. **Given** an unauthenticated user, **When** they attempt to view or cancel a booking,
   **Then** the action is denied without contact-data disclosure or booking changes.
4. **Given** a booking that does not exist, **When** the administrator attempts cancellation,
   **Then** the outcome explains that it cannot be found and no other booking changes.
5. **Given** a failed or unverified cancellation, **When** feedback is displayed, **Then**
   the interface does not claim cancellation succeeded until the canceled state is confirmed.
   A verified repeated cancellation follows the successful no-op policy in D-010.
6. **Given** a guest with a confirmed booking, **When** they view their confirmation or try
   to cancel through a protected administrator action, **Then** no guest self-service
   cancellation is offered, the protected action is denied, and the booking remains unchanged.
   The guest must request cancellation from the host outside this self-service flow.
7. **Given** a non-canceled appointment that ended 30 days ago, or a booking canceled 30 days
   ago, measured as 720 elapsed hours from its recorded end or first successful cancellation,
   **When** retained booking history is inspected at or after its retention deadline,
   **Then** the guest's name and email are absent, the contact-removed state is understandable,
   and appointment identity, activity, time, and status can remain as history.
8. **Given** contact details already removed under the retention policy, **When** an old
   current-generation booking attempt is retried or recovered, **Then** it does not reveal or restore those
   details and does not create another booking. Its expired retry identifier is rejected;
   contact-free expiry tracking must not restore expired recovery access. Contract and storage
   safeguards still require the review recorded in G-006/G-007.
9. **Given** an already canceled booking and an authenticated administrator, **When** the
   administrator cancels it again, **Then** the action succeeds without further changes and
   the interface acknowledges that it is already canceled. Original cancellation time,
   contact-removal deadline, booking interval, and other bookings remain unchanged.
10. **Given** an initial cancellation whose response was lost, **When** an authenticated
    administrator retries it, **Then** either the initial transition to canceled completes
    once or the existing canceled state is acknowledged. Only the first successful transition
    establishes cancellation time; retries cannot extend retention or restore removed contacts.
11. **Given** contact details at their 720-hour deadline and a failed cleanup operation,
    **When** booking or recovery reads occur, **Then** those reads still omit expired contacts,
    the deletion failure is surfaced to the operator, and no extra retention/access period is
    granted. The failure is not reported as successful physical deletion.
12. **Given** a backup/export or a restored copy of booking history, **When** its contents
    and recovery behavior are inspected, **Then** no guest name/email, original contact-bearing
    submission, or private retry credential is present. Restore preserves only the permitted
    history, cannot revive expired retry access, and cannot restore guest contacts even before
    their deadline. Missing contacts are clearly represented rather than fabricated.
13. **Given** restored contact-free history and an unknown old booking outcome,
    **When** retry state is unavailable after a qualified A-003 recovery, **Then** no contacts
    or private retry credentials are restored, no booking failure is inferred, and the guest
    is directed to host verification before deliberately starting another booking attempt.
14. **Given** a current-generation key at its chronological expiry and a prior-generation key
    invalidated by a separately approved restore, **When** recovery feedback is inspected,
    **Then** 410 attempt_expired and 409 attempt_invalidated_by_restore remain distinct, both
    avoid contact disclosure/new-key fallback, and neither revives expired access or a booking.

---

### User Story 5 - Complete journeys on mobile and across timezones (Priority: P3)

As a visitor or administrator, I want readable controls, useful failure feedback, and
unambiguous dates/times so I can complete the same tasks on desktop and mobile.

**Why this priority**: This completes the usability of the core journeys. Responsive use,
error clarity, and time correctness remain mandatory acceptance gates for all priorities.

**Independent Test**: Run the public and admin journeys at the proposed narrow and desktop
viewport widths and display one appointment in two named timezones, including DST test dates.

**Acceptance Scenarios**:

1. **Given** a narrow mobile viewport or desktop viewport, **When** any core journey is used,
   **Then** its controls, date choices, form errors, and confirmation remain visible and usable
   without horizontal page scrolling or hidden primary actions.
2. **Given** an appointment displayed in two supported IANA timezones, **When** its details
   are viewed in each, **Then** each view describes the same instant and duration, with the
   display timezone identifiable even when the local date differs.
3. **Given** a working window with a nonexistent local start during a clock change, **When**
   availability is shown or that start is submitted, **Then** the nonexistent start is omitted
   and rejected rather than shifted to another local time.
4. **Given** an unavailable service or failed availability retrieval, **When** the visitor
   sees feedback, **Then** it distinguishes failure to load from a genuinely empty schedule
   and provides a way to retry without creating a booking.
5. **Given** a repeated local start with both occurrences otherwise eligible, **When** slots
   are shown, **Then** both distinct instants are offered with their respective timezone-offset
   labels. Choosing either occurrence reserves that instant and the activity's elapsed duration;
   the other remains subject to the same eligibility and non-overlap checks as any slot.
6. **Given** a detectable visitor timezone, **When** the visitor first views availability,
   **Then** dates/times initially use that timezone and identify it. The visitor can select
   another IANA timezone; the calendar and time labels then use that selected display timezone.
7. **Given** no usable detected visitor timezone, **When** availability is first displayed,
   **Then** it uses and identifies the activity's timezone, while still allowing a manual change.
8. **Given** a selected display date spanning portions of two activity-local dates, **When**
   slots are shown, **Then** every otherwise eligible start whose display-local date matches
   the selection appears once, and starts on other display-local dates do not appear. Working
   windows and blocked dates still use their activity-local dates. Changing display timezone
   relabels a selected/booked instant rather than moving the appointment.
9. **Given** a date that skips local 02:00–03:00 and a configured window 02:30–04:00,
   **When** availability is computed, **Then** eligible starts in the real 03:00–04:00 portion
   can be offered; nonexistent starts are omitted and the window is not extended past 04:00.
10. **Given** a date repeating 02:00–03:00, a window 02:15–02:45, and a 30-minute activity,
    **When** availability is computed, **Then** both otherwise eligible 02:15 occurrences can
    be offered with distinct offsets. A booking cannot bridge the intervening real-time
    portion whose local clock is outside 02:15–02:45, even if its start/end labels look valid.
11. **Given** a window 01:00–04:00 on a date skipping 02:00–03:00, **When** an otherwise eligible
    30-minute appointment starts at 01:30, **Then** it may end at displayed 03:00 because its
    elapsed duration is 30 minutes and its whole real interval stays inside that window.
12. **Given** a window wholly inside a nonexistent local period, **When** that date is viewed,
    **Then** the window yields zero slots rather than shifting into another period or changing
    the recurring weekly rule. An appointment ending exactly at a valid portion's right
    boundary may fit; starts at an excluded right boundary do not fit that portion.
13. **Given** clock-aligned starts in the activity's IANA timezone and a different visitor
    display timezone, **When** starts are displayed or the display timezone changes, **Then**
    eligibility remains anchored to activity-local minutes 00, 15, 30, and 45; UTC instants
    do not move. On repeated-time dates both otherwise eligible occurrences of an aligned
    local start remain distinct choices with their respective UTC-offset labels. Nonexistent
    starts remain omitted, and full-duration continuous-window fit still applies to both.

---

### Edge Cases

- A slot shown earlier becomes invalid while a visitor is filling in attendee details.
- Double-clicks, repeated submissions, and simultaneous visitors must never create overlapping
  confirmed bookings. Retrying the same attempt returns its existing result or completes it
  at most once; an existing booking is not duplicated, restored after cancellation, or mistaken
  for another guest's booking (D-009, recovery policy resolved).
- An identifier expires after a lost response: reject it as expired, never infer that the
  original booking failed, and never silently issue a new identifier. Mismatch responses
  disclose no original submission details; a retry result omits guest name/email even when
  the requester presents a valid identifier. Do not expose private identifiers in logs.
- Partially overlapping appointments are conflicts even when their start times differ;
  back-to-back appointments are not conflicts (ADR-0002).
- The system clock advances across a notice boundary between browsing and submission: new
  bookings use the submission-time check, with no browsing grace period. Exact one-hour and
  1440-hour start boundaries are inclusive elapsed-time limits, independent of clock changes.
- A duration fits exactly at a working-window end, or exceeds it by one increment.
- A window begins off the clock-quarter-hour grid: start at the next activity-local minute
  00/15/30/45 only if the complete elapsed interval fits. Do not align relative to the window,
  shift its boundaries, admit a fractional-second start, or round an off-grid submission.
- A date has no working window, has been blocked, or is outside the approved booking horizon.
- Weekly windows overlap, duplicate, or cross midnight: reject the replacement schedule
  and retain the previous valid one. Touching windows are valid but are not merged, so a
  booking cannot bridge their shared boundary unless it fits one window (D-008, resolved).
- Two timezones show different calendar dates for the same instant: calendar selection groups
  starts by their date in the visitor's selected display timezone, while working and blocking
  rules use activity-local dates (D-006, resolved). A display date can span two activity dates
  and can have a different elapsed length during a clock change; do not assume it is 24 hours.
- A skipped local start is omitted/rejected; both repeated occurrences are eligible choices
  when other rules permit them and have distinct offset labels. Keep each working window's
  configured local limits and use only its continuous real portions, without shifting skipped
  boundaries, bridging excluded portions, or extending the end (D-005, resolved).
- An administrator changes duration, timezone, activity status, hours, or blocks after bookings
  exist: their agreed start/end and status remain unchanged, the administrator is warned about
  affected appointments, and new booking attempts use the changed rules (D-008, preservation
  and working-window policies resolved).
- Cancellation competes with a new request; every final confirmed booking must still satisfy
  non-overlap, new confirmations must satisfy eligibility at submission, preserved bookings
  retain their agreed intervals, and displayed action outcomes reflect committed results.
- Names containing international characters and whitespace are handled without silently
  changing identity; empty/whitespace-only names and invalid emails are rejected. Any limits
  or additional normalization rules require explicit specification rather than hidden rejection.
- Expired administrator sessions, missing activities/bookings, and service failures must not
  expose attendee details or produce false success messages.
- An administrator remains active across the 60-minute deadline: the session still expires.
  Reauthentication starts a new session, not a retroactive authorization of failed writes;
  only reviewed, explicitly resubmitted operations may proceed.
- Description length is evaluated after outer-whitespace trimming in Unicode code points,
  not bytes: boundary values pass, wholly blank or overlong values fail, and markup-like text
  remains literal. Public previews must not become the only way to read the description.
- A booking is canceled before its scheduled end: the contact-retention clock starts at
  cancellation, not the later scheduled end. Contact removal must also apply to retained
  recovery records; safe retry must not become a second source of expired contact details.
- Contact cleanup fails or a backup is restored: expired contacts remain unavailable on reads,
  cleanup failure is surfaced accurately, and contact-free backups cannot restore contacts or
  private retry credentials. Restored history may lack contacts before the normal deadline;
  this is an accepted recovery limitation, not permission to invent replacement identities.
- Repeated clicks, concurrent cancellation attempts, or retries after response loss succeed
  without further mutation once cancellation is confirmed. They must not change the original
  cancellation time, extend contact retention, or restore removed contact details (D-010).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Visitors MUST browse only active appointment types without creating an account.
- **FR-002**: Each public activity MUST present its name, mandatory description, and duration.
  A catalog preview is permitted only when full description text is available on activity
  selection before booking. Description validation/display MUST follow FR-031. The PRD and
  canonical-contract additions remain review work in G-001, not a private implementation format.
- **FR-003**: Visitors MUST select an activity and a date and view that date's availability,
  including an explicit empty state and a route back to another date or activity. The selected
  calendar date MUST mean the date of each offered start in the selected display timezone,
  even when this spans portions of multiple activity-local dates (D-006, resolved).
- **FR-004**: Availability MUST follow weekly windows in the activity's IANA timezone, with
  starts aligned to activity-local minutes 00, 15, 30, or 45 and zero seconds/fractional seconds,
  independently of the window's start or visitor display timezone (A-001, approved). Off-grid
  starts MUST NOT be offered, accepted, rounded, or shifted. The full activity duration MUST fit
  inside one individual window
  and one continuous valid real portion under FR-030. Touching windows MUST NOT be
  silently combined to admit a crossing appointment.
- **FR-005**: Past, blocked, inactive-activity, already-occupied, off-grid (FR-004), and policy-ineligible slots
  MUST NOT be offered or accepted for new bookings. Later rule changes MUST NOT invalidate or
  cancel existing bookings (FR-023). A blocked date applies only to its activity and is
  interpreted in that activity's IANA timezone (D-001, resolved). Notice and horizon MUST
  follow the inclusive elapsed-time boundaries in FR-026 (D-003/D-004, resolved).
- **FR-006**: Guests MUST submit their name, valid email, selected activity, and selected start;
  the appointment end MUST be determined from the activity duration, not chosen by the guest.
- **FR-007**: Invalid attendee details or ineligible starts MUST be rejected with understandable
  feedback; rejection MUST NOT create a confirmed booking or modify another booking.
- **FR-008**: Availability MUST be checked again when a booking is submitted, using current
  rules, current authoritative system time, and confirmed bookings rather than trusting
  earlier displayed availability or the visitor's clock. The same rules apply when offering
  slots, with no hold or notice grace period from browsing. A safe retry of an already
  completed attempt within its validity window returns its existing result under FR-024
  instead of making a new booking; expired identifiers reject and A-003-qualified recovery
  invalidation is reported separately. No failed/unverified admission establishes a valid attempt.
- **FR-009**: Confirmed bookings for the same activity MUST NOT overlap, including simultaneous
  requests with identical or different overlapping starts. Adjacent intervals MUST be allowed
  when otherwise eligible, following ADR-0002. Cross-activity exclusivity is not added here.
- **FR-010**: Successful guest submissions MUST produce one confirmed booking and an on-screen
  confirmation with booking identity, activity, start/end, timezone, and confirmed status.
  Confirmation MUST NOT depend on sending email or another external integration.
- **FR-011**: When another booking wins a contested slot, the guest MUST receive an unavailable
  outcome, no false confirmation, and a way to return to current availability.
- **FR-012**: Unverified submission outcomes MUST be distinguished from confirmed success and
  confirmed rejection. Guests MUST be able to explicitly retry the same attempt safely under
  FR-024, rather than starting a new submission. The interface MUST NOT blindly resubmit or
  claim an outcome before it is known (D-009, amended by A-002/A-003). Unverified admission/
  execution and verified committed-but-unfinished processing MUST be distinguished; ordinary
  pending requires committed matching unexpired admission. Restore-invalidated unknown outcomes
  MUST direct host verification before another deliberate attempt, without automatic replacement.
- **FR-013**: The single seeded administrator MUST authenticate before management access.
  Public administrator registration MUST NOT be offered. Each successful login MUST establish
  a fixed 60-minute session under FR-028 (D-007, resolved).
- **FR-014**: Missing, invalid, or expired administrator authentication MUST deny protected
  reads and changes without exposing booking contacts or performing the attempted change.
  Expiration MUST be enforced by the server, not the visitor's clock; protected views MUST be
  cleared or locked on expiration, and failed writes MUST NOT automatically replay after login.
- **FR-015**: The administrator MUST create/update activity name, description, public identifier,
  duration, IANA timezone, and active status. Public identifiers MUST be unique and durations
  MUST be positive multiples of 15 minutes. Administrators MUST edit the full multiline
  description with field validation under FR-031. Invalid changes MUST retain valid stored state.
- **FR-016**: The administrator MUST replace an activity's weekly working windows and block
  dates for that activity in its IANA timezone. A block MUST NOT affect other activities;
  taking a date off across activities requires blocking each activity separately.
  Invalid windows MUST be rejected under FR-027, retaining the previous valid schedule.
  Existing bookings MUST be preserved under FR-023 (D-008, resolved).
- **FR-017**: The administrator MUST view bookings with identity, activity, start/end, status,
  and attendee name/email while those contact details are present and within FR-025's period.
  Contact-free restores may yield earlier contact removal, which MUST be shown accurately.
  After removal, retained confirmed/canceled history MUST represent contact details as removed
  rather than require their continued storage or display.
- **FR-018**: The administrator MUST cancel a confirmed booking; after success, its canceled
  status MUST stop excluding otherwise eligible availability. Other bookings MUST be unchanged.
  Only the authenticated administrator may cancel bookings; guest self-service cancellation
  MUST NOT be offered in the MVP (D-002, resolved). Repeating cancellation of an already
  canceled booking MUST succeed as a no-op and acknowledge its existing canceled state,
  preserving the original cancellation time and contact-retention deadline (D-010, resolved).
  Missing bookings and unauthorized actions MUST retain their specified failure behavior.
- **FR-019**: Public activity/availability views and operational logs MUST NOT reveal guest
  contact details. Credentials and authentication material MUST NOT appear in ordinary errors
  or logs. Guest name/email retention MUST follow FR-025 and backup/recovery constraints in
  FR-029 (D-011, resolved). Deletion, restore, and privacy controls MUST be verified before
  public deployment; selected product policies are not deployment authorization.
- **FR-020**: All core journeys MUST work on desktop and mobile with readable controls,
  visible primary actions, and understandable feedback for invalid inputs, empty results,
  conflicts, expired access, and service failure. Draft viewport targets are stated in SC-007.
- **FR-021**: Appointment and availability display MUST identify the display timezone and
  represent the same instant consistently across IANA timezones. Local working rules MUST
  honor timezone changes rather than a fixed offset. Nonexistent local starts MUST be omitted
  and rejected, not shifted; both occurrences of a repeated start MUST be offered as distinct
  instants with distinct timezone-offset labels when otherwise eligible. The selected occurrence
  determines the booked instant; elapsed duration and overlap rules still apply. Initially use
  the detected visitor timezone, falling back to the activity's timezone if unavailable, and
  allow manual IANA timezone selection. Calendar dates and time labels MUST follow the selected
  display timezone, while working/blocked-date rules retain the activity's timezone. Changing
  display timezone MUST NOT move a selected/booked instant. Transition-window boundaries MUST
  follow FR-030 (D-005, resolved); initial display/date policy is resolved in D-006.
- **FR-022**: Failed or unverified operations MUST NOT claim successful booking, cancellation,
  or schedule changes. Uncertain COMMIT MUST remain unverified until committed-state evidence
  resolves it, never be assumed to prove rollback. Availability-load failure MUST be
  distinguishable from an empty schedule.
- **FR-023**: Changes to activity details, duration, timezone, active status, working windows,
  or blocked dates MUST preserve existing bookings' agreed start/end instants and status.
  The administrator MUST be warned about existing appointments affected by proposed changes.
  Changed rules and duration MUST apply to new booking attempts; unchanged confirmed intervals
  continue excluding overlaps. Cancellation MUST remain an explicit administrator action,
  not a side effect of configuration edits (D-008, preservation policy resolved).
- **FR-024**: Safe retry MUST recognize the original booking attempt while valid and return its
  recorded result, including the same booking identity/current status when one exists, subject
  only to the explicit A-003 recovery exception below. The private unpredictable identifier MUST
  be created before first submission and contain no contact data. Admission becomes valid only
  after its original binding and database-generated receipt timestamp T/deadline E commit
  successfully and durably in one transaction. E MUST equal T+24 elapsed hours and MUST NOT
  extend on retries or delayed commit; T is not commit metadata, HTTP/ACK time or transaction-start
  time. If commit occurs at/after E, the key is already expired and MUST NOT execute or return pending.
  Known admission rollback creates no valid attempt through that transaction; uncertain COMMIT
  MUST remain unverified until safely resolved. If no admission ever committed, a later explicit
  request may create the first valid admission using its own persisted database timestamp.
  Matching simultaneous retries MUST converge on at most one booking/result. Ordinary pending
  MUST require proven committed matching unexpired unfinished admission; changed-details/expired
  or unverified requests MUST NOT receive it. Recorded definite rejection remains final. Changed
  activity/start/name/email MUST reject generically without original-detail/result disclosure.
  Retry confirmations MUST omit guest name/email; contact-based lookup is prohibited. Current-
  generation chronological expiry MUST reject with 410 attempt_expired, never admit the key anew.
  Only a separately human-approved disaster recovery unable to preserve retry state MAY invalidate
  prior-generation identifiers, including unexpired ones, with 409 attempt_invalidated_by_restore.
  That outcome MUST NOT claim chronological expiry or booking failure; unknown outcomes require
  host verification before another deliberate attempt, never automatic key replacement. Normal
  restarts and transient failures MUST preserve valid keys/T/E/binding/results. No retry may
  duplicate/revive a booking or restore removed contacts. Exact API shapes and runtime mechanisms
  remain subject to contract review and provisional T-02 verification (G-006, A-002/A-003).

- **FR-025**: Guest name and email MUST be automatically deleted at a deadline of 720 elapsed
  hours after the booking's recorded end for non-canceled bookings, or after its first successful
  cancellation for canceled bookings. Later activity edits, retries, and repeated cancellation
  MUST NOT move that anchor. At/after the deadline, all reads MUST hide expired contacts even
  if cleanup fails; cleanup failure MUST be surfaced to the operator and MUST NOT authorize
  extension or be falsely reported as completed deletion. Attempt/recovery copies MUST obey
  the same deadline. Permitted history is limited to booking reference, activity, start/end,
  status, and original cancellation time, with no guest name/email or identifying free text.
  This is contact-removed history, not a guarantee of irreversible anonymity (G-007).
- **FR-026**: At each new-booking eligibility check at system instant T, the start S MUST
  satisfy T + 1 elapsed hour ≤ S ≤ T + 1440 elapsed hours. Both boundaries are inclusive and
  refer to the start; the end may exceed the horizon if the full duration fits its window.
  These limits MUST use elapsed time, not calendar-day lengths or fixed local-clock offsets.
  A start outside either bound MUST NOT be offered or accepted. Submission MUST recheck the
  limits at its current evaluation instant, without a grace period from prior browsing.
- **FR-027**: Weekly working windows MUST have an end later than the start within the same
  activity-local calendar day. Windows for the same activity/weekday MUST NOT overlap or
  duplicate one another; touching boundaries are permitted. Overnight, zero-length, reversed,
  or overlapping windows MUST cause schedule replacement to be rejected without partial
  changes. No automatic merging is implied. Each appointment MUST fit one accepted window;
  DST transition-window interpretation MUST follow FR-030 without moving local limits.
- **FR-028**: A session created at successful-login instant T MUST authorize protected actions
  only while system authorization time is strictly earlier than T + 60 elapsed minutes.
  Activity MUST NOT extend that deadline; no silent renewal or expiration grace period is
  permitted. At expiration, credentials MUST be supplied again. Only non-sensitive configuration
  drafts may survive for review, excluding passwords and guest-contact data; changes rejected
  for expiration MUST require explicit resubmission. Technical token storage remains for planning.
- **FR-029**: Backups and any exports MUST exclude guest names/emails, contact-bearing original
  submissions, and private booking-retry credentials; only the permitted contact-removed
  appointment history may be retained there. Restore MUST NOT reintroduce contacts or expired
  retry access. Loss of live guest contacts is not recoverable from these copies, including
  before the normal deletion deadline, and restored views MUST accurately show contact removal.
  These rules constrain recovery and any future exports; they do not add an export feature.
  Under approved A-003, separately human-approved disaster recovery unable to preserve retry
  state MAY invalidate unexpired old identifiers with distinct restore-invalidation feedback;
  it MUST NOT silently create new attempts or claim chronological expiry. Normal restarts and
  transient failures MUST retain valid retry state. Approved storage, purge, hosting and restore
  verification remain required before public use; T-03 approval is conditional on those controls.
- **FR-030**: On a transition date, a configured weekly window MUST keep its activity-local
  date and clock limits. Its valid real portions consist of the instants whose activity-local
  date matches that window's date and whose local clock is at/after its start and before its
  end. Missing local times yield no instants; repeated times yield both real occurrences.
  An appointment's entire half-open real interval, using the activity's elapsed duration,
  MUST fit one continuous valid portion of one window; its end may equal that portion's right
  boundary. Do not shift missing boundaries, bridge excluded portions, extend the end, merge
  separate windows, or change the weekly rule. A window with no real portion yields no slots.
- **FR-031**: Every activity description MUST contain 1–2000 Unicode code points after trimming
  leading/trailing whitespace. Whitespace-only/empty and overlong values MUST be rejected,
  never silently truncated. Multiline content MUST be allowed; internal text and line breaks
  MUST be retained. Public/admin views MUST treat the description as plain text, including
  literal markup-like characters without executing or interpreting them. Administrators MUST
  have full-text editing and field-error feedback, and guests MUST have full text available
  on activity selection before booking even when a catalog preview is used (D-012, resolved).

### Key Entities *(include if feature involves data)*

- **Activity**: An appointment type with identity, unique public identifier, name, mandatory
  plain-text description constrained by FR-031, duration, timezone, and active status. It has
  working windows, blocked dates, and bookings. Description requires source reconciliation (G-001).
- **Weekly working window**: A recurring day-of-week and local start/end interval belonging
  to one activity, contained within one local calendar day. Windows for the same activity/day
  are non-overlapping; touching is permitted without merging. Each defines when a complete
  appointment may fit (D-008, resolved).
- **Blocked date**: A local calendar date belonging to exactly one activity, interpreted in
  that activity's IANA timezone. It excludes new appointments for that activity/date without
  changing other activities or existing confirmed bookings (D-001, resolved).
- **Availability slot**: A derived start/end choice for an activity/date, reflecting working
  rules, exclusions, existing confirmed bookings, and current eligibility. It is not a reservation.
- **Booking**: An identified appointment for exactly one activity, with start/end, attendee
  name/email during the retention period, and confirmed/canceled status. Contact details are
  removed after the D-011 deadline; other history may remain. Only confirmed bookings exclude
  overlapping intervals. The first successful transition to canceled establishes the original
  cancellation time used for retention; repeated cancellation does not change it.
  After contact removal, only reference, activity, start/end, status, and original cancellation
  time remain as history. Contact-free recovery can remove contacts earlier than the deadline.
- **Booking attempt**: One guest's original submission and its outcome, associated with at
  most one booking. A private unpredictable identifier created before submission binds the
  original details and persisted database receipt timestamp T/deadline E, effective only upon
  successful durable admission commit (A-002). E=T+24h even after commit delay. Valid matching
  retries share the attempt/result; changed details and expired identifiers are rejected,
  and no guest account/contact lookup is introduced. A-003 adds only qualified recovery
  invalidation with distinct feedback; normal restarts preserve state. Contract reconciliation remains G-006;
  no concrete wire format, generator, or storage mechanism is chosen here.
- **Administrator**: The single authorized operator managing offerings, availability, and
  bookings. Guests have no account entity; their contact details belong to their booking.

### Journey Dependencies and Requirement Traceability

| Journey | Dependencies | Requirements | Verification |
| --- | --- | --- | --- |
| US1: discover | Configured activities/windows; activity-local clock-aligned starts; visitor-date grouping with activity-local eligibility; approved description contract addition | FR-001–005, FR-021, FR-031 | US1.1–8; SC-001–002, SC-014, SC-019 |
| US2: reserve | US1 selection; current availability; clock alignment, duration and attendee validation; private 24-hour retry contract follow-up | FR-004–012, FR-024, FR-026; FR-009 also applies to admin/config changes | US2.1–26; SC-002–005, SC-011, SC-013, SC-017 |
| US3: configure | Administrator provisioning and fixed-lifetime authentication; preserved bookings, same-day windows, per-activity blocks and validated descriptions | FR-004, FR-013–016, FR-023, FR-027–028, FR-031 | US3.1–16; SC-002, SC-006, SC-010, SC-015–016, SC-019 |
| US4: review/cancel | Authentication and existing bookings, prepared or from US2; contact-removal contract follow-up | FR-014, FR-017–019, FR-025, FR-029 | US4.1–14; SC-006, SC-008, SC-011–012, SC-017 |
| US5: responsive/time | Cross-cutting acceptance of US1–4; approved activity-local grid, local-window and visitor-date policies | FR-003–004, FR-019–022, FR-030 | US5.1–13; SC-002, SC-007–009, SC-014, SC-018 |

Admin configuration is an operational prerequisite for a usable public catalog, even though
public booking is the highest-priority value. Prepared synthetic schedules permit independent
public acceptance tests. US3 and US4 share authentication; US4 can be tested with prepared
bookings. P3 does not defer security, error clarity, or time correctness beyond MVP release.

### Source Consistency and Approval Gaps

- **G-001 — Activity description**: D-012 is resolved: mandatory multiline plain text of
  1–2000 Unicode code points after outer trimming, literal markup, full admin editing and
  full public text before booking. The PRD and canonical activity/read/write models lack this
  requirement. Reconcile them through reviewed PRD/TypeSpec changes; the approved product
  choice is not approval of a concrete contract amendment or private implementation format.
- **G-002 — Incomplete error coverage**: The PRD already flags missing invalid-slot-query and
  invalid-activity-update responses in the canonical contract. Error behavior in FR-007/015/022
  must be reconciled by contract owners; this specification does not invent response formats.
- **G-003 — Approval status resolved**: The human project owner approved this specification
  and its checklist and ratified constitution `1.2.0` on 2026-10-25. The approval records identify
  the reviewed source blobs. The human subsequently approved the complete R-003 technical plan
  on 2026-10-25, retaining T-02/T-03 conditions. Concrete contract amendments and implementation
  still require their respective reviews. ADRs labeled Accepted
  in existing files are source records, not evidence of new human approval.
- **G-004 — Cancellation boundary**: D-002 is resolved by the human choice recorded above:
  cancellation is administrator-only, with no guest self-service in the MVP. The PRD's open
  question needs reconciliation in a later documentation update. No contract change is needed
  to add guest cancellation because that capability is excluded. D-010 is also resolved:
  repeated administrator cancellation succeeds without further changes and preserves the
  original cancellation time/retention deadline. Contract review must carry these semantics
  forward without inventing an unapproved response format.
- **G-005 — Feature branch mismatch resolved**: The actual Git branch is now verified as
  `001-appointment-scheduling`; the stale `main` metadata has been corrected. Earlier rounds
  ran on `main`, but no branch was created or renamed by this clarification. Separate worktrees
  or independent checkouts still need verification before concurrent implementation agents run.
- **G-006 — Safe-retry contract gap**: The selected D-009 behavior requires recognition and
  private recovery of the same booking attempt under FR-024's 24-hour, matching-details,
  concurrency, expiry-rejection, and contact-free retry rules. The current contract has no
  attempt identity/recovery semantics and returns attendee contact fields in its booking
  model. An approved change must express the selected behavior and distinguish pending,
  mismatch, expired, and final outcomes without contact leakage. Expiry enforcement and
  contact-free tracking after expiry remain planning obligations, not permission to reuse
  forgotten keys. No endpoint, header, field, format, or application code is changed here.
- **G-007 — Contact-removal follow-up**: The D-011 period must be carried into the PRD and
  approved data lifecycle as a 720-hour deadline, read suppression, surfaced deletion failure,
  limited contact-removed history, and contact-free backups/exports under FR-025/029. The current
  booking contract requires attendee name/email strings and does not define their removed
  state, including restored records missing contacts earlier. Owners must approve this
  representation and the purge/restore/privacy design; no placeholder identity, nullable
  field, mechanism, or application behavior is implemented during clarification.
- **G-008 — Visitor-date/contract alignment**: D-006's calendar groups starts in the selected
  display timezone, while existing availability and blocking rules use activity-local dates.
  The contract currently accepts a date without specifying a display-timezone/date-grouping
  capability. Owners must document its date semantics and ensure a visitor date spanning
  activity dates is covered without omitted/duplicate starts. This may require combining
  existing activity-date results or an approved contract change; no approach is selected here.
- **G-009 — Clock-alignment source follow-up**: A-001 resolves planning question P-01:
  starts use exact activity-local minutes 00/15/30/45, with full continuous-window fit and the
  existing DST behavior preserved. The PRD's 15-minute wording and canonical slots/booking
  documentation must carry this origin and off-grid rejection through reviewed reconciliation.
  No new API field or persisted-data migration is required by this amendment. The PRD and
  canonical TypeSpec remain unchanged here; exact contract review, T-02 runtime verification
  and T-03 operational acceptance remain pending, without implementation authorization.
- Apart from these source/approval gaps, no new conflict with the PRD or
  constitution was found. Calendar synchronization, payments, multi-tenancy, external
  integrations, and the other existing exclusions remain outside this feature.

### Decisions Reserved for Clarification

D-001–D-012 are resolved by the fifteen recorded answers across three rounds. Earlier PRD
defaults are superseded only by the explicit product choices below; no other defaults are
silently adopted. Remaining work is source reconciliation, technical design, and verification,
as identified in G-001–G-009 and the follow-up list below. The separate 2026-10-25 human approval
ratifies the constitution and authorizes planning; it does not approve concrete contract
amendments, a technical plan, implementation, or deployment.

| ID | Decision or unresolved question | Existing proposal or constraint | Affected requirements |
| --- | --- | --- | --- |
| D-001 | Resolved: blocked dates apply to one selected activity, using that activity's local date and IANA timezone | Human selected per-activity blocks; other activities and existing confirmed bookings are unaffected; host-wide days off require separate blocks | FR-005, FR-016; US3.6, US3.10; SC-002 |
| D-002 | Resolved: only the authenticated administrator can cancel; no guest self-service cancellation in the MVP | Human selected the recommended administrator-only policy in this session; guests request cancellation from the host | FR-018; US4.1–6 |
| D-003 | Resolved: starts must be at least one elapsed hour and no more than 1440 elapsed hours ahead; both bounds inclusive; only the start is horizon-limited | Human selected the 60 × 24-hour horizon and one-hour notice; full duration must still fit the working window; existing booking times remain unchanged | FR-005, FR-008, FR-026; US2.10–12; SC-013 |
| D-004 | Resolved: use current system time at each eligibility check and recheck on submission; no hold or notice grace period from browsing | Human selected inclusive elapsed-time boundaries; a previously displayed start may become ineligible before submission; already completed safe retries return their original booking result | FR-005, FR-008, FR-024, FR-026; US2.12; SC-013 |
| D-005 | Resolved: retain configured local-window limits and offer only continuous real portions within them; skip nonexistent starts and offer both repeated occurrences with distinct offsets when otherwise eligible | Human retained the earlier start policy and selected valid portions; full elapsed duration fits one portion, right-boundary ends may fit, no shifting/extending/bridging or weekly-rule mutation | FR-004, FR-021, FR-030; US5.3, US5.5, US5.9–12; SC-009, SC-018 |
| D-006 | Resolved: initially use detected visitor timezone, with activity-timezone fallback and manual IANA timezone selection; calendar dates group starts in the selected display timezone | Human selected visitor-first display; working windows/blocks retain activity-local dates; changing display timezone does not move appointments; date-result coverage requires G-008 follow-up | FR-003–005, FR-021; US5.6–8; SC-014 |
| D-007 | Resolved: a fixed 60-minute session from login, with server-enforced expiration at the deadline and no automatic extension/renewal; credentials required again | Human selected option B; preserve only non-sensitive configuration drafts, clear/lock protected views, and require review plus explicit resubmission of failed changes; token-storage design remains for planning | FR-013–014, FR-028; US3.7, US3.13–14; SC-016 |
| D-008 | Resolved: preserve existing booking start/end and status with administrator warning; apply changes to new bookings. Reject overlapping/duplicate and overnight windows; allow touching same-day windows without merging; a booking must fit one window | Human retained the earlier preservation policy and selected same-day non-overlapping windows; reject invalid replacements without partial changes; DST portions follow resolved D-005 | FR-004–005, FR-015–016, FR-023, FR-027; US3.8–12; SC-010, SC-015 |
| D-009 | Resolved, amended by approved A-002/A-003: private unpredictable identifier; fixed E=T+24h from database timestamp persisted with binding in a successful durable admission transaction; delayed commit consumes validity; matching retry convergence/contact-free results | Original human answer preserved as history. A-002 clarifies T rather than commit metadata; rollback admits nothing and uncertain COMMIT stays unverified. A-003 permits only separately approved unrecoverable restore invalidation, distinct from expiry; normal restarts/transient failures preserve valid keys. No contact lookup, duplicate/revived booking or automatic replacement. | FR-008/010–012/022/024/029; US2.7–9/13–26, US4.13–14; SC-011/017 |
| D-010 | Resolved: authenticated cancellation of an already canceled booking succeeds as a no-op and acknowledges the existing canceled state | Human selected successful no-op; preserve original cancellation time and 30-day retention deadline; no contact restoration or other booking changes; missing/unauthorized cases still fail as specified | FR-018, FR-022, FR-025; US4.5, US4.9–10; SC-008, SC-012 |
| D-011 | Resolved, with A-003 recovery clarification: automatically delete guest contacts at 720 elapsed hours from recorded booking end or first successful cancellation; hide expired contacts on all reads even on cleanup failure; surface failures without extending retention | Human retained the 30-day period and selected contact-free backups/exports, with no private retry credentials or contact-bearing submissions; retained history is only reference/activity/start/end/status/original cancellation time, not promised irreversible anonymity; contact loss after restore is accepted; A-003 separately permits qualified retry-state invalidation without contacts or automatic replacement, and T-03 requires backup/hosting controls; contract/design verification remains G-007 | FR-017, FR-019, FR-025, FR-029; US4.7–8, US4.11–12; SC-012, SC-017 |
| D-012 | Resolved: every activity requires a multiline plain-text description of 1–2000 Unicode code points after outer trimming; reject blank/overlong values, preserve internal text, display markup literally | Human selected mandatory descriptions; full admin editing/validation and full public text before booking are required even if the catalog previews it; concrete PRD/TypeSpec changes still require review in G-001 | FR-002, FR-015, FR-031; US1.6, US3.15–16; SC-019 |

Provisioning synthetic admin/activity examples and repeatable local setup remain planning
obligations from the PRD. This feature does not select their technical design or authorize
implementation. The same applies to the contract gap in G-002.

Remaining review items after round three do not reopen the recorded product choices:

- D-005: working-window boundary and slot-start policies are resolved under FR-030.
  Carry those policies into the planned availability verification without selecting a different
  repeated-time occurrence or shifting nonexistent labels as an implementation shortcut.
- D-007: the 60-minute fixed lifetime, expiry, and reauthentication behavior are resolved.
  Token-storage and related security implementation review remain for planning without
  changing that selected lifetime or permitting silent renewal.
- D-012/G-001: description content, validation, and presentation are resolved. Reconcile the
  PRD and canonical activity models with FR-031 through the approved source-change process.
- G-006: the retry identity, 24-hour lifetime, binding, mismatch, concurrency, contact-free
  response, and expiry behavior are resolved. Carry them into an approved contract; select
  secure generation/transport/storage and reliable expiry enforcement during planning.
  Contact-free expiry tracking must not allow reuse or preserve guest data beyond retention.
- G-007: deadline calculation, deletion/read-suppression outcomes, history contents, and
  contact-free backup/restore policy are resolved. Approve the removed-contact contract
  representation and verify purge/read/restore controls in planning and implementation.
  No alternative retention period or hidden backup exception is authorized.
- G-002/G-008: reconcile validation/error coverage and visitor-date versus activity-date results
  with canonical contract semantics. Preserve the approved visitor-first display policy.
- G-003/G-005: constitution/feature review was explicitly approved on 2026-10-25. The branch
  mismatch is resolved: the verified branch is `001-appointment-scheduling`. Confirm isolated
  worktrees/checkouts before any separately authorized concurrent implementation.

Required source updates for the next review, without modifying those sources in this phase:

| Source | Required change or reconciliation | Approval boundary |
| --- | --- | --- |
| PRD | Record the resolved blocked-date, cancellation, notice/horizon, visitor-date, clock-aligned start grid (A-001), window/DST, 60-minute authentication, 24-hour retry from persisted admission T/E (A-002), distinct qualified recovery invalidation (A-003), retention/backup, and description requirements; replace open questions with the selected outcomes | Human review of the reconciled PRD; do not infer unrelated scope approval |
| TypeSpec activity read/write models | Add the required description and express/document its outer trimming, 1–2000 code-point constraints, and plain-text behavior | Lead proposes exact contract changes; no generated or private fields substituted |
| TypeSpec booking/retry operations | Define private identifiers and immutable E=T+24h from persisted successful admission (A-002), verified pending/final/mismatch/chronological-expiry outcomes, distinct A-003 restore invalidation, phase-specific unverified failures and contact-free results | Approve exact request/response/error shapes before dependent implementation |
| TypeSpec/admin history | Represent contact-removed records without requiring original attendee strings or invented placeholder identities; preserve cancellation/retention semantics | Review privacy and compatibility of the selected representation |
| TypeSpec existing operations | Complete validation/error coverage; document fixed session expiration and repeated-cancellation outcomes | Agree concrete status/error definitions without introducing new product behavior |
| TypeSpec availability/date semantics | State exact activity-local 00/15/30/45 starts and off-grid rejection under A-001; state activity-local query semantics and account for visitor-date grouping across activity dates; review whether existing operations suffice | Review the proposed approach during planning; do not silently invent a date-query format |

Technical planning was authorized on 2026-10-25 with the following required scope:

- Reconcile the PRD with the approved requirements and propose TypeSpec changes and error responses.
- Design authentication/session management, concurrent booking transactions, and idempotency.
- Design personal-data retention/deletion and timezone/DST handling, preserving approved policies.
- Cover database migrations, Docker, testing, multi-agent ownership boundaries, and integration.

Secure token storage, private-attempt generation/transport/expiry enforcement, purge/read/restore
mechanisms, timezone computation, and repeatable provisioning are technical design decisions,
not unresolved product choices. Concrete contract changes and implementation are not authorized.
The earlier specification-finalization commit is complete. On 2026-10-25 the human formally
approved the complete R-003 technical plan, including A-001/A-002/A-003 and T-01–T-04, retaining
T-02 runtime-verification and T-03 backup/hosting conditions. The approved specification revision
is Git blob `e4d75a0fd79dfaeec48e36b7457cd4d6c32c0656`; only approval/status records change now.
The human authorizes a local documentation-baseline commit, followed by a report and stop.
No tasks, canonical contract change, application implementation or push is authorized.
See [formal technical-plan approval](checklists/technical-review.md).

## Success Criteria *(mandatory)*

### Measurable Outcomes

These are approved acceptance targets, not measured implementation results.
The cases below preserve the recorded clarification policies approved on 2026-10-25.

- **SC-001**: In every prepared catalog case, 100% of active activities and zero inactive
  activities are offered; each offered activity shows name, description/preview, and duration,
  with full description available before booking (US1).
- **SC-002**: For every approved ordinary-date test schedule, displayed starts exactly match
  eligible activity-local clock minutes 00/15/30/45 with zero seconds/fractional seconds:
  zero past, blocked, off-grid, out-of-window, or occupied appointments are offered or accepted;
  a complete duration fits each offered window. For a 30-minute activity in a 09:10–10:00 window,
  exactly 09:15 and 09:30 remain eligible when otherwise available; a 09:10–09:40 window offers
  none. Grid alignment is unchanged by visitor display timezone. Every blocking case uses the
  activity-local date, excludes zero otherwise eligible choices from other activities, and
  changes zero existing confirmed bookings (US1/US3).
- **SC-003**: A guest can complete browse → date → slot → name/email → on-screen confirmation
  in one uninterrupted visit without an account. The confirmation contains all FR-010 details.
- **SC-004**: In every two-request contention case using different booking-attempt identifiers
  for one eligible slot, exactly one booking is confirmed and exactly one visitor receives an
  unavailable outcome. Same-identifier retries instead follow SC-011. Across identical and
  partially overlapping starts, zero overlapping confirmed bookings result (US2).
- **SC-005**: Across all invalid-input, stale-slot, and known-failure scenarios, zero rejected
  attempts create confirmed bookings; every rejection identifies a correction or next action.
  Unknown-outcome cases never show a verified success or falsely assert definite failure;
  safe retries resolve the same attempt under SC-011.
- **SC-006**: All specified admin create/update, working-window, blocking, review, and cancellation
  journeys succeed with valid authorization and synthetic inputs; 100% of unauthenticated,
  invalid, and expired-access attempts disclose no protected contacts and make no changes.
- **SC-007**: At proposed acceptance viewport widths of 320 and 1280 CSS pixels, every core
  journey is completable without horizontal page scrolling or hidden primary actions (US5).
- **SC-008**: After a successful cancellation, every otherwise eligible affected slot is
  available again; zero unrelated bookings are changed. Across repeated/concurrent cancellation
  and lost-response retry cases, an already canceled booking is acknowledged successfully with
  zero further mutations, zero changes to original cancellation time/retention deadline, and
  zero restored contact details (US4).
- **SC-009**: For each timezone acceptance case, including dates around both DST transitions,
  the same appointment displays the same instant and elapsed duration in at least two named
  timezones. Zero nonexistent local starts are offered or accepted; both otherwise eligible
  repeated occurrences are offered with distinct offset labels and reserve the chosen instant.
  Every offered full interval satisfies its unchanged window's valid-portion rule (US5).
- **SC-010**: Across configuration-change acceptance cases, 100% of pre-existing bookings keep
  their agreed start/end and status, including when their activity duration/timezone changes
  or their date becomes blocked. Every affected-booking case warns the administrator; zero
  bookings are automatically canceled. New booking choices use the changed rules and still
  exclude preserved confirmed intervals (US3).
- **SC-011**: Across lost-response, repeated/concurrent-retry and crash/timeout cases for one
  attempt, at most one booking identity is created. For committed admission, E=T+24h from the
  persisted database timestamp, never commit metadata/ACK/retry time. Commit delay consumes the
  fixed window, and commit at/after E yields expiry without execution/pending. Rollback admits
  nothing through that transaction; uncertain COMMIT produces zero unsupported confirmations,
  ordinary pending claims or assumed rollbacks. Before E, matching committed retries return the
  known result or verified unfinished state; mismatches reject generically. At/after E current-
  generation retry yields 410 attempt_expired. Only a qualified A-003 recovery produces distinct
  409 attempt_invalidated_by_restore for lost-generation keys, including unexpired ones. Normal
  restart/transient failures preserve original valid state. Zero automatic new-key fallback,
  contact-bearing retry confirmations, duplicate/revived bookings or changed final rejections.


- **SC-012**: In every non-canceled and canceled retention-boundary case, retained history
  and recovery results contain zero original guest names/emails at or after the applicable
  720-hour deadline, including cleanup-failure cases; deletion failures are surfaced accurately.
  Retrying an old attempt restores zero removed contact details and creates
  zero additional bookings. Admin history clearly identifies contact removal (US4).
- **SC-013**: In every notice/horizon boundary case, otherwise eligible starts exactly one
  hour and exactly 1440 hours ahead qualify; starts below/above those bounds do not. Zero
  stale displays bypass the submission-time notice check. Across DST changes the elapsed-time
  limits remain unchanged, and only the start is tested against the horizon (US2).
- **SC-014**: Every visitor-timezone case uses detected timezone initially, or the activity
  timezone when detection is unavailable, and permits a manual timezone change. For every
  selected display date, 100% of otherwise eligible matching-date starts appear once and
  zero other-date starts appear, including dates spanning two activity dates. Working/blocking
  rules remain activity-local and zero selected/booked instants move when relabeled (US1/US5).
- **SC-015**: All overlapping, duplicate, overnight, zero-length, and reversed-window
  replacement cases are rejected with zero partial schedule changes. All otherwise valid
  touching-window cases are accepted, and zero offered appointments require combining two
  individual windows to fit their duration (US3).
- **SC-016**: All session-boundary acceptance cases reject protected operations at or after
  60 elapsed minutes from login, including continuously active sessions, and authorize no
  failed write retroactively. Reauthentication restores zero passwords/guest-contact drafts;
  every retained non-sensitive draft requires review and explicit resubmission (US3).
- **SC-017**: Every inspected backup/export/restore acceptance case contains zero guest
  names/emails, contact-bearing submission copies, or private retry credentials. Restores
  reintroduce zero removed contacts or expired retry access; retained history contains only
  permitted fields, and unavailable guest contacts are represented honestly. Qualified A-003
  recovery invalidation returns distinct 409 feedback and host verification, while ordinary
  chronological expiry stays 410; normal restarts preserve valid identifiers (US2/US4).
- **SC-018**: In every skipped/repeated-boundary fixture, 100% of offered intervals fit one
  continuous real portion of one configured local window. Zero intervals shift a boundary,
  cross an excluded portion, or extend its end. Both otherwise eligible repeated starts have
  distinct offset labels, and a wholly nonexistent window yields zero slots (US5).
- **SC-019**: Every description boundary case accepts trimmed lengths 1 and 2000 code points
  and rejects blank or 2001-code-point content without truncation or saved-state corruption.
  All accepted multiline/international/markup-like fixtures remain plain text in admin and
  public views; 100% have full text available before booking (US1/US3).

## Assumptions

- The current scope is one host/administrator and account-free guests, as in the PRD. Public
  administrator sign-up and guest account management are not introduced.
- Confirmation means an on-screen result for the submitting guest. Email, invitations, payments,
  calendar sync, OAuth, team/multi-tenancy, external integrations, real-time updates, advanced
  recurring exceptions, and production observability remain outside MVP scope.
- An activity's public name corresponds to the PRD's title concept; this is a vocabulary
  equivalence, not permission to rename canonical fields. Mandatory description is a resolved
  product requirement awaiting the reviewed PRD/TypeSpec addition, not a private field.
- The admin's management scope is creation, updates, active status, availability, and booking
  cancellation. Hard deletion of activities/bookings is not inferred from the word "manage".
- Scope follows ADR-0002's non-overlap per activity. A host-wide constraint across different
  activities is not added without an approved scope/design change.
- The 320/1280 viewport widths are approved verification targets derived from mobile/desktop use,
  not a comprehensive browser/device matrix. No unrequested latency, load, or user-study
  performance commitments are implied.
- A minimum valid attendee submission is a non-empty name and syntactically valid email.
  Further length/normalization rules must be explicit if introduced; deliverability checks
  and email verification are not added as external integration requirements.
- Existing weekly-window rules, activity duration increments, and booking states come from
  the PRD/ADRs, refined by the recorded answers. D-001–D-012 product choices are resolved;
  constitution/specification approval is explicitly recorded above rather than inferred from
  individual answers. Concrete contract changes still require separate approval.
- Working-window clarification excludes overnight schedules and automatic window merging
  from this MVP. Disjoint or touching same-day windows remain available without changing
  the previously agreed booking-preservation or DST start-time choices.
- Local reproducibility, security controls, contract ownership, test evidence, and isolated
  implementation ownership remain obligations of the governing documents. They are inputs to
  later planning, not implementation choices made by this product specification.
