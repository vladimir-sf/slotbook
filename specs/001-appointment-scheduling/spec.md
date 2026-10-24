# Feature Specification: SlotBook Appointment Scheduling MVP

**Feature Branch**: `001-appointment-scheduling` (verified current Git branch)

**Created**: 2026-10-24

**Status**: Approved for technical planning — all fifteen clarification answers preserved;
D-001–D-012 product choices resolved. Implementation is not authorized.

**Approved**: 2026-10-25 by the human project owner.

**Approved Source Revision**: Git blob `d180b9b83857cfd4ebf4ed118d2e74f3aa94512e`.
Approval finalization changes only review/status records; source reconciliation remains planning work.

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
   the guest retries that same attempt with matching details before its 24-hour expiry,
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
13. **Given** a private attempt identifier first received at T, **When** matching details are
    retried before T + 24 elapsed hours, **Then** retries share the original attempt and result
    without extending expiry. At or after T + 24 hours, retries are rejected as expired without
    revealing guest contacts or silently creating a new attempt; an unknown result directs
    the guest to host verification rather than assuming no booking exists.
14. **Given** an identifier already bound to booking details, **When** it is reused with
    different activity, start, name, or email, **Then** a generic mismatch is returned without
    changing the original attempt or revealing its original details/result. Deliberately
    corrected details require a new attempt, never an automatic replacement after uncertainty.
15. **Given** simultaneous matching retries with one valid identifier, **When** processing
    completes, **Then** at most one booking exists and all completed retry results refer to
    that identity/status without guest name/email. Unfinished processing may report pending;
    a recorded definite rejection is not reinterpreted as a new booking on later retry.

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
   booking attempt is retried or recovered, **Then** it does not reveal or restore those
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
  starts at 15-minute increments and the full activity duration fitting inside one individual
  window and one continuous valid real portion under FR-030. Touching windows MUST NOT be
  silently combined to admit a crossing appointment.
- **FR-005**: Past, blocked, inactive-activity, already-occupied, and policy-ineligible slots
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
  instead of making a new booking; an expired identifier is rejected.
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
  claim an outcome before it is known (D-009, recovery policy resolved).
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
  or schedule changes. Availability-load failure MUST be distinguishable from an empty schedule.
- **FR-023**: Changes to activity details, duration, timezone, active status, working windows,
  or blocked dates MUST preserve existing bookings' agreed start/end instants and status.
  The administrator MUST be warned about existing appointments affected by proposed changes.
  Changed rules and duration MUST apply to new booking attempts; unchanged confirmed intervals
  continue excluding overlaps. Cancellation MUST remain an explicit administrator action,
  not a side effect of configuration edits (D-008, preservation policy resolved).
- **FR-024**: Safe retry MUST recognize the guest's original booking attempt and return its
  recorded result while its private identifier is valid, including the same booking identity
  and current status when a booking exists. The identifier MUST be unpredictable, contain no
  contact data, and be created before first submission; its validity MUST end exactly 24 elapsed
  hours after first system receipt and MUST NOT extend on retry. Matching simultaneous retries
  MUST converge on at most one booking/result; unfinished work may report processing. A recorded
  definite rejection MUST remain that attempt's result. If no final outcome exists, it may
  complete at most once while currently eligible or reject definitively. Changed activity,
  start, name, or email with the same identifier MUST be rejected generically without disclosing
  original details. Retry confirmations MUST omit guest name/email, and contact-based lookup is
  prohibited. Expired identifiers MUST be rejected rather than reused as new; unknown outcomes
  require host verification, and deliberate new attempts require new identifiers. No retry
  may duplicate/revive a booking or restore removed contacts. Identifier transport, expiry
  enforcement/storage, and privacy controls require approved contract/planning work (G-006).
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
  Approved storage, purge, and restore design/verification remain required before public use.
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
  original details and expires 24 elapsed hours after first system receipt. Valid matching
  retries share the attempt/result; changed details and expired identifiers are rejected,
  and no guest account/contact lookup is introduced. Contract reconciliation remains G-006;
  no concrete wire format, generator, or storage mechanism is chosen here.
- **Administrator**: The single authorized operator managing offerings, availability, and
  bookings. Guests have no account entity; their contact details belong to their booking.

### Journey Dependencies and Requirement Traceability

| Journey | Dependencies | Requirements | Verification |
| --- | --- | --- | --- |
| US1: discover | Configured activities/windows; visitor-date grouping with activity-local eligibility; approved description contract addition | FR-001–005, FR-021, FR-031 | US1.1–6; SC-001–002, SC-014, SC-019 |
| US2: reserve | US1 selection; current availability; duration and attendee validation; private 24-hour retry contract follow-up | FR-005–012, FR-024, FR-026; FR-009 also applies to admin/config changes | US2.1–15; SC-003–005, SC-011, SC-013 |
| US3: configure | Administrator provisioning and fixed-lifetime authentication; preserved bookings, same-day windows, per-activity blocks and validated descriptions | FR-004, FR-013–016, FR-023, FR-027–028, FR-031 | US3.1–16; SC-002, SC-006, SC-010, SC-015–016, SC-019 |
| US4: review/cancel | Authentication and existing bookings, prepared or from US2; contact-removal contract follow-up | FR-014, FR-017–019, FR-025, FR-029 | US4.1–12; SC-006, SC-008, SC-012, SC-017 |
| US5: responsive/time | Cross-cutting acceptance of US1–4; approved local-window and visitor-date policies | FR-003–004, FR-019–022, FR-030 | US5.1–12; SC-007–009, SC-014, SC-018 |

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
  the reviewed source blobs. Technical planning is authorized; a plan, concrete contract
  amendments, and implementation still require their respective reviews. ADRs labeled Accepted
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
- Apart from these source/approval gaps, no new conflict with the PRD or
  constitution was found. Calendar synchronization, payments, multi-tenancy, external
  integrations, and the other existing exclusions remain outside this feature.

### Decisions Reserved for Clarification

D-001–D-012 are resolved by the fifteen recorded answers across three rounds. Earlier PRD
defaults are superseded only by the explicit product choices below; no other defaults are
silently adopted. Remaining work is source reconciliation, technical design, and verification,
as identified in G-001–G-008 and the follow-up list below. The separate 2026-10-25 human approval
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
| D-009 | Resolved: use a private unpredictable per-attempt identifier, valid for 24 elapsed hours from first system receipt without extension; bind original details, reject mismatches, converge simultaneous retries, and omit contacts from retry confirmations | Human retained safe retry and selected A for its validity policy; expired identifiers reject rather than become new, unknown outcomes require host verification, and deliberate new attempts require new identifiers; no contact lookup or booking duplication/revival; contract reconciliation remains G-006 | FR-010–012, FR-022, FR-024; US2.7–9, US2.13–15; SC-011 |
| D-010 | Resolved: authenticated cancellation of an already canceled booking succeeds as a no-op and acknowledges the existing canceled state | Human selected successful no-op; preserve original cancellation time and 30-day retention deadline; no contact restoration or other booking changes; missing/unauthorized cases still fail as specified | FR-018, FR-022, FR-025; US4.5, US4.9–10; SC-008, SC-012 |
| D-011 | Resolved: automatically delete guest contacts at 720 elapsed hours from recorded booking end or first successful cancellation; hide expired contacts on all reads even on cleanup failure; surface failures without extending retention | Human retained the 30-day period and selected contact-free backups/exports, with no private retry credentials or contact-bearing submissions; retained history is only reference/activity/start/end/status/original cancellation time, not promised irreversible anonymity; contact loss after restore is accepted; contract/design verification remains G-007 | FR-017, FR-019, FR-025, FR-029; US4.7–8, US4.11–12; SC-012, SC-017 |
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
| PRD | Record the resolved blocked-date, cancellation, notice/horizon, visitor-date, window/DST, 60-minute authentication, 24-hour retry, retention/backup, and description requirements; replace open questions with the selected outcomes | Human review of the reconciled PRD; do not infer unrelated scope approval |
| TypeSpec activity read/write models | Add the required description and express/document its outer trimming, 1–2000 code-point constraints, and plain-text behavior | Lead proposes exact contract changes; no generated or private fields substituted |
| TypeSpec booking/retry operations | Define the private attempt identifier and 24-hour lifetime, detail binding, pending/final/mismatch/expired outcomes, and contact-free retry confirmations | Approve exact request/response/error shapes before dependent implementation |
| TypeSpec/admin history | Represent contact-removed records without requiring original attendee strings or invented placeholder identities; preserve cancellation/retention semantics | Review privacy and compatibility of the selected representation |
| TypeSpec existing operations | Complete validation/error coverage; document fixed session expiration and repeated-cancellation outcomes | Agree concrete status/error definitions without introducing new product behavior |
| TypeSpec availability/date semantics | State activity-local query semantics and account for visitor-date grouping across activity dates; review whether existing operations suffice | Review the proposed approach during planning; do not silently invent a date-query format |

Technical planning was authorized on 2026-10-25 with the following required scope:

- Reconcile the PRD with the approved requirements and propose TypeSpec changes and error responses.
- Design authentication/session management, concurrent booking transactions, and idempotency.
- Design personal-data retention/deletion and timezone/DST handling, preserving approved policies.
- Cover database migrations, Docker, testing, multi-agent ownership boundaries, and integration.

Secure token storage, private-attempt generation/transport/expiry enforcement, purge/read/restore
mechanisms, timezone computation, and repeatable provisioning are technical design decisions,
not unresolved product choices. Concrete contract changes and implementation are not authorized.
For this finalization step, commit the approved documents and stop before starting planning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

These are approved acceptance targets, not measured implementation results.
The cases below preserve the recorded clarification policies approved on 2026-10-25.

- **SC-001**: In every prepared catalog case, 100% of active activities and zero inactive
  activities are offered; each offered activity shows name, description/preview, and duration,
  with full description available before booking (US1).
- **SC-002**: For every approved ordinary-date test schedule, displayed starts exactly match
  eligible 15-minute increments: zero past, blocked, out-of-window, or occupied appointments
  are offered; a complete duration fits each offered window. Every blocking case uses the
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
- **SC-011**: Across lost-response, repeated-retry, and concurrent-retry cases for one attempt,
  at most one booking identity is created. Valid matching retries return its existing outcome;
  expired retries at/after 24 elapsed hours reject, never create a new attempt, and never extend
  expiry. Every different-details retry is rejected without original-detail disclosure; zero
  retry confirmations contain guest name/email. A canceled booking is never revived, and no
  retry accesses another attempt through contact lookup or changes a final rejection (US2).
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
  permitted fields, and unavailable guest contacts are represented honestly (US4).
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
