# Feature Specification: SlotBook Appointment Scheduling MVP

**Feature Branch**: `main` (current working branch; no feature branch was created)

**Created**: 2026-10-24

**Status**: Draft — pending clarification and human review; not approved for planning or implementation

**Input**: User request to specify public activity browsing, availability and guest booking,
protected administration, responsive use, understandable failures, and consistent time display
within SlotBook's existing MVP boundaries.

## User Scenarios & Testing *(mandatory)*

Priorities express delivery order, not permission to omit a journey. All five stories are MVP
release requirements. Public stories can be demonstrated with prepared activities and schedules;
real administrator configuration is a dependency for operating the complete product.
Scenarios use synthetic data. Decisions marked pending below are not assumed to be approved.

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
3. **Given** two visitors submitting the same available slot simultaneously, **When** both
   attempts finish, **Then** exactly one receives a confirmation, the other receives an
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
   The recovery journey remains pending decision D-009.

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
6. **Given** a blocked date under the agreed scope, **When** visitors request availability
   or attempt a new booking for that date, **Then** no affected appointment is offered or
   confirmed. The affected activities are conditional on decision D-001.
7. **Given** an administrator session that has expired, **When** a protected action is attempted,
   **Then** it is rejected and reauthentication is requested without performing the action.

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
   available to the administrator without exposing them in public activity or slot views.
2. **Given** a confirmed booking, **When** the administrator cancels it successfully, **Then**
   its status is canceled, it no longer excludes otherwise eligible slots, and other bookings
   are unchanged.
3. **Given** an unauthenticated user, **When** they attempt to view or cancel a booking,
   **Then** the action is denied without contact-data disclosure or booking changes.
4. **Given** a booking that does not exist, **When** the administrator attempts cancellation,
   **Then** the outcome explains that it cannot be found and no other booking changes.
5. **Given** a failed or unverified cancellation, **When** feedback is displayed, **Then**
   the interface does not claim cancellation succeeded. Repeated cancellation behavior is
   pending decision D-010.

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
3. **Given** an ordinary availability window on a DST-transition date, **When** slots are
   shown, **Then** each offered slot corresponds to a real instant and no appointment is
   silently shifted by a fixed-offset assumption. Ambiguous/nonexistent local-time outcomes
   require the explicit policy in D-005 before final acceptance cases can be completed.
4. **Given** an unavailable service or failed availability retrieval, **When** the visitor
   sees feedback, **Then** it distinguishes failure to load from a genuinely empty schedule
   and provides a way to retry without creating a booking.

---

### Edge Cases

- A slot shown earlier becomes invalid while a visitor is filling in attendee details.
- Double-clicks, repeated submissions, and simultaneous visitors must never create overlapping
  confirmed bookings; outcome recovery is distinct from conflict prevention (D-009).
- Partially overlapping appointments are conflicts even when their start times differ;
  back-to-back appointments are not conflicts (ADR-0002).
- The current time advances across a start/notice boundary between browsing and submission.
- A duration fits exactly at a working-window end, or exceeds it by one increment.
- A date has no working window, has been blocked, or is outside the approved booking horizon.
- Weekly windows overlap or cross midnight; the permitted input policy is unresolved (D-008).
- Two timezones show different calendar dates for the same instant; the selected calendar-date
  meaning and initial display timezone must be made explicit (D-006).
- DST skips a wall-clock time or repeats it; repeated labels must not imply indistinguishable
  booking choices. Detailed handling remains pending (D-005).
- An administrator changes duration, timezone, activity status, hours, or blocks after bookings
  already exist; preservation and conflict behavior are pending (D-008).
- Cancellation competes with a new request; every final confirmed booking must still satisfy
  eligibility and non-overlap, and displayed action outcomes must reflect committed results.
- Names containing international characters and whitespace are handled without silently
  changing identity; empty/whitespace-only names and invalid emails are rejected. Any limits
  or additional normalization rules require explicit specification rather than hidden rejection.
- Expired administrator sessions, missing activities/bookings, and service failures must not
  expose attendee details or produce false success messages.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Visitors MUST browse only active appointment types without creating an account.
- **FR-002**: Each public activity MUST present its name, description, and duration. Description
  is requested behavior with a source/contract gap tracked in G-001; it is not an invented
  field in an implementation. Admin authoring is included in FR-015.
- **FR-003**: Visitors MUST select an activity and a date and view that date's availability,
  including an explicit empty state and a route back to another date or activity.
- **FR-004**: Availability MUST follow weekly windows in the activity's IANA timezone, with
  starts at 15-minute increments and the full activity duration fitting inside a window.
- **FR-005**: Past, blocked, inactive-activity, already-occupied, and policy-ineligible slots
  MUST NOT be offered or accepted. Date blocking, booking horizon, and notice parameters
  remain pending in D-001, D-003, and D-004.
- **FR-006**: Guests MUST submit their name, valid email, selected activity, and selected start;
  the appointment end MUST be determined from the activity duration, not chosen by the guest.
- **FR-007**: Invalid attendee details or ineligible starts MUST be rejected with understandable
  feedback; rejection MUST NOT create a confirmed booking or modify another booking.
- **FR-008**: Availability MUST be checked again when a booking is submitted, using current
  rules and confirmed bookings rather than trusting earlier displayed availability.
- **FR-009**: Confirmed bookings for the same activity MUST NOT overlap, including simultaneous
  requests with identical or different overlapping starts. Adjacent intervals MUST be allowed
  when otherwise eligible, following ADR-0002. Cross-activity exclusivity is not added here.
- **FR-010**: Successful guest submissions MUST produce one confirmed booking and an on-screen
  confirmation with booking identity, activity, start/end, timezone, and confirmed status.
  Confirmation MUST NOT depend on sending email or another external integration.
- **FR-011**: When another booking wins a contested slot, the guest MUST receive an unavailable
  outcome, no false confirmation, and a way to return to current availability.
- **FR-012**: Unverified submission outcomes MUST be distinguished from confirmed success and
  confirmed rejection. The interface MUST NOT automatically repeat a booking after an unknown
  outcome; the complete recovery policy is pending D-009.
- **FR-013**: The single seeded administrator MUST authenticate before management access.
  Public administrator registration MUST NOT be offered.
- **FR-014**: Missing, invalid, or expired administrator authentication MUST deny protected
  reads and changes without exposing booking contacts or performing the attempted change.
- **FR-015**: The administrator MUST create/update activity name, description, public identifier,
  duration, IANA timezone, and active status. Public identifiers MUST be unique and durations
  MUST be positive multiples of 15 minutes. Invalid changes MUST retain valid stored state.
- **FR-016**: The administrator MUST replace an activity's weekly working windows and block
  dates under the approved blocking scope. Invalid or zero-length/reversed windows MUST be
  rejected. Overnight/overlapping-window policy and existing-booking impact remain in D-008.
- **FR-017**: The administrator MUST view bookings with identity, activity, start/end, status,
  and attendee name/email, including confirmed and canceled records retained by policy.
- **FR-018**: The administrator MUST cancel a confirmed booking; after success, its canceled
  status MUST stop excluding otherwise eligible availability. Other bookings MUST be unchanged.
  Repeated cancellation is pending D-010; guest cancellation is pending D-002.
- **FR-019**: Public activity/availability views and operational logs MUST NOT reveal guest
  contact details. Credentials and authentication material MUST NOT appear in ordinary errors
  or logs. A data retention/deletion policy MUST be approved before public deployment (D-011).
- **FR-020**: All core journeys MUST work on desktop and mobile with readable controls,
  visible primary actions, and understandable feedback for invalid inputs, empty results,
  conflicts, expired access, and service failure. Draft viewport targets are stated in SC-007.
- **FR-021**: Appointment and availability display MUST identify the display timezone and
  represent the same instant consistently across IANA timezones. Local working rules MUST
  honor timezone changes rather than a fixed offset. Initial display/date and DST policies
  remain pending in D-005 and D-006.
- **FR-022**: Failed or unverified operations MUST NOT claim successful booking, cancellation,
  or schedule changes. Availability-load failure MUST be distinguishable from an empty schedule.

### Key Entities *(include if feature involves data)*

- **Activity**: An appointment type with identity, unique public identifier, name, requested
  description, duration, timezone, and active status. It has working windows, blocked dates,
  and bookings. Description requires source reconciliation (G-001).
- **Weekly working window**: A recurring day-of-week and local start/end interval belonging
  to one activity. It defines when complete appointments may fit.
- **Blocked date**: A local calendar date that excludes affected appointments. Its association
  with one or all activities remains an explicit decision (D-001).
- **Availability slot**: A derived start/end choice for an activity/date, reflecting working
  rules, exclusions, existing confirmed bookings, and current eligibility. It is not a reservation.
- **Booking**: An identified appointment for exactly one activity, with start/end, attendee
  name/email, and confirmed/canceled status. Only confirmed bookings exclude overlapping intervals.
- **Administrator**: The single authorized operator managing offerings, availability, and
  bookings. Guests have no account entity; their contact details belong to their booking.

### Journey Dependencies and Requirement Traceability

| Journey | Dependencies | Requirements | Verification |
| --- | --- | --- | --- |
| US1: discover | Configured activities/windows; public choices depend on unresolved date rules | FR-001–005 | US1.1–5; SC-001–002 |
| US2: reserve | US1 selection; current availability; duration and attendee validation | FR-006–012; FR-009 also applies to admin/config changes | US2.1–7; SC-003–005 |
| US3: configure | Administrator provisioning/authentication; approved blocking and edit rules | FR-013–016 | US3.1–7; SC-002, SC-006 |
| US4: review/cancel | Authentication and existing bookings, prepared or from US2 | FR-014, FR-017–019 | US4.1–5; SC-006, SC-008 |
| US5: responsive/time | Cross-cutting acceptance of US1–4; resolved timezone policies | FR-019–022 | US5.1–4; SC-007–009 |

Admin configuration is an operational prerequisite for a usable public catalog, even though
public booking is the highest-priority value. Prepared synthetic schedules permit independent
public acceptance tests. US3 and US4 share authentication; US4 can be tested with prepared
bookings. P3 does not defer security, error clarity, or time correctness beyond MVP release.

### Source Consistency and Approval Gaps

- **G-001 — Activity description**: The current request requires a description; the PRD's
  catalog criteria and canonical activity/write contract do not include one. FR-002/015 record
  the requested outcome, not a contract amendment. Lead review, human approval, and source
  reconciliation are required before dependent implementation. Description completeness/limits
  remain to be clarified without assuming hidden validation rules.
- **G-002 — Incomplete error coverage**: The PRD already flags missing invalid-slot-query and
  invalid-activity-update responses in the canonical contract. Error behavior in FR-007/015/022
  must be reconciled by contract owners; this specification does not invent response formats.
- **G-003 — Approval status**: The constitution is `1.2.0-draft`, explicitly pending human
  approval, with no recorded ratification/amendment date. This specification respects its
  safeguards but does not claim to ratify it. This feature is also a draft. ADRs labeled
  Accepted in existing files are source records, not evidence of new human approval.
- **G-004 — Cancellation boundary**: The PRD describes host cancellation while also listing
  guest cancellation as an open decision. This specification preserves host cancellation and
  records the guest question in D-002; it does not silently expand the journey.
- Apart from these gaps and the pending decisions below, no new conflict with the PRD or
  constitution was found. Calendar synchronization, payments, multi-tenancy, external
  integrations, and the other existing exclusions remain outside this feature.

### Decisions Reserved for Clarification

Every item is pending; suggested PRD defaults are proposals, not approved answers. Requirements
and scenarios affected by a decision are provisional at that boundary. Do not implement them
by choosing an undocumented default. The three bracketed markers identify the highest-impact
scope/policy questions; the remaining decisions are equally explicit without extra markers.
Per the user's request, questions are recorded for the clarification phase rather than asked
or resolved during this specification command.

| ID | Unresolved question | Existing proposal or constraint | Affected requirements |
| --- | --- | --- | --- |
| D-001 | [NEEDS CLARIFICATION: Do blocked dates apply to one activity or all activities?] | PRD proposal: per activity; not ratified | FR-005, FR-016; US3.6 |
| D-002 | [NEEDS CLARIFICATION: Is cancellation administrator-only or may guests cancel in the MVP?] | PRD proposal: administrator-only; guest capability would require scope/contract review | FR-018; US4 |
| D-003 | [NEEDS CLARIFICATION: What booking horizon and minimum notice apply, and are their boundary instants inclusive?] | PRD proposals: next 60 days and one hour; D-004 carries notice traceability | FR-005, FR-008; US2.6 |
| D-004 | How is minimum notice applied at browsing/submission boundaries? | Part of D-003, not a separate assumed value | FR-005, FR-008 |
| D-005 | How are ambiguous/nonexistent local times and windows spanning DST transitions handled? | Real instants and consistent duration are mandatory; exact inclusion policy is unresolved | FR-004, FR-021; US5.3 |
| D-006 | What is the initial display timezone, how can it be chosen, and which timezone defines a selected calendar date? | Activity working rules use its IANA timezone; no visitor-date policy is inferred | FR-003–005, FR-021 |
| D-007 | What session lifetime and expiry/re-entry experience should administrators have? | Short-lived authentication is required; storage/security design belongs in planning | FR-013–014 |
| D-008 | What happens to existing bookings after activity/window/block changes, and are overlapping or overnight windows allowed? | Do not invent silent rescheduling or cancellation; zero-length/reversed same-day windows are invalid | FR-004–005, FR-015–016 |
| D-009 | How should a guest recover when a submitted booking's final outcome is unknown? | No false confirmation or blind automatic resubmission; no contact-data lookup is assumed | FR-010–012, FR-022 |
| D-010 | What outcome should repeated cancellation of an already canceled booking produce? | Cancellation must not change other bookings or claim an unverified success | FR-018, FR-022 |
| D-011 | What guest-contact retention/deletion rules must precede public deployment? | No real customer data in development/tests; no contact data in public catalog/slots or logs | FR-017, FR-019 |
| D-012 | What description content/validation is needed, and will PRD/contract amendments be approved? | Description is requested in this feature; no canonical field or approved constraints exist yet | FR-002, FR-015; G-001 |

Provisioning synthetic admin/activity examples and repeatable local setup remain planning
obligations from the PRD. This feature does not select their technical design or authorize
implementation. The same applies to the contract gap in G-002.

## Success Criteria *(mandatory)*

### Measurable Outcomes

These are proposed acceptance targets for review, not measured implementation results.
Policy-dependent cases must be completed after clarification before planning approval.

- **SC-001**: In every prepared catalog case, 100% of active activities and zero inactive
  activities are offered; each offered activity shows name, description, and duration (US1).
- **SC-002**: For every approved ordinary-date test schedule, displayed starts exactly match
  eligible 15-minute increments: zero past, blocked, out-of-window, or occupied appointments
  are offered; a complete duration fits each offered window (US1/US3).
- **SC-003**: A guest can complete browse → date → slot → name/email → on-screen confirmation
  in one uninterrupted visit without an account. The confirmation contains all FR-010 details.
- **SC-004**: In every two-request contention case for one eligible slot, exactly one booking
  is confirmed and exactly one visitor receives an unavailable outcome. Across identical and
  partially overlapping starts, zero overlapping confirmed bookings result (US2).
- **SC-005**: Across all invalid-input, stale-slot, and known-failure scenarios, zero rejected
  attempts create confirmed bookings; every rejection identifies a correction or next action.
  Unknown-outcome cases never show a verified success or falsely assert definite failure.
- **SC-006**: All specified admin create/update, working-window, blocking, review, and cancellation
  journeys succeed with valid authorization and synthetic inputs; 100% of unauthenticated,
  invalid, and expired-access attempts disclose no protected contacts and make no changes.
- **SC-007**: At proposed acceptance viewport widths of 320 and 1280 CSS pixels, every core
  journey is completable without horizontal page scrolling or hidden primary actions (US5).
- **SC-008**: After a successful cancellation, every otherwise eligible affected slot is
  available again; zero unrelated bookings are changed (US4).
- **SC-009**: For each timezone acceptance case, including dates around both DST transitions,
  the same appointment displays the same instant and elapsed duration in at least two named
  timezones. Zero offered times violate the clarified DST policy (US5).

## Assumptions

- The current scope is one host/administrator and account-free guests, as in the PRD. Public
  administrator sign-up and guest account management are not introduced.
- Confirmation means an on-screen result for the submitting guest. Email, invitations, payments,
  calendar sync, OAuth, team/multi-tenancy, external integrations, real-time updates, advanced
  recurring exceptions, and production observability remain outside MVP scope.
- An activity's public name corresponds to the PRD's title concept; this is a vocabulary
  equivalence, not permission to rename canonical fields. Description is a flagged addition.
- The admin's management scope is creation, updates, active status, availability, and booking
  cancellation. Hard deletion of activities/bookings is not inferred from the word "manage".
- Scope follows ADR-0002's non-overlap per activity. A host-wide constraint across different
  activities is not added without an approved scope/design change.
- The 320/1280 viewport widths are draft verification targets derived from mobile/desktop use,
  not an already-approved browser/device matrix. No unrequested latency, load, or user-study
  performance commitments are implied.
- A minimum valid attendee submission is a non-empty name and syntactically valid email.
  Further length/normalization rules must be explicit if introduced; deliverability checks
  and email verification are not added as external integration requirements.
- Existing weekly-window rules, activity duration increments, and booking states come from
  the PRD/ADRs. Open product and edge-case decisions above remain unresolved, even where the
  PRD suggests defaults. No new specification approval is inferred from this draft's creation.
- Local reproducibility, security controls, contract ownership, test evidence, and isolated
  implementation ownership remain obligations of the governing documents. They are inputs to
  later planning, not implementation choices made by this product specification.
