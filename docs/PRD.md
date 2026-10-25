# SlotBook MVP — Product Requirements Document

Status: reconciled PRD and canonical API v1 formally approved; contract frozen 2026-10-25.
Implementation is not authorized by this freeze.
Reconciled: 2026-10-25.
Source: approved technical baseline `5f1ce85bc16b25541337b5ef55d6f25d7b3a574d`,
[feature specification](../specs/001-appointment-scheduling/spec.md), and approved amendments
[A-001](../specs/001-appointment-scheduling/amendments/A-001-clock-aligned-starts.md),
[A-002](../specs/001-appointment-scheduling/amendments/A-002-durable-admission.md),
[A-003](../specs/001-appointment-scheduling/amendments/A-003-disaster-recovery.md).
All fifteen product clarification answers and all 77 acceptance scenarios remain in the
unchanged specification. This document reconciles those decisions without expanding scope.
The canonical REST definition is [contracts/main.tsp](../contracts/main.tsp); OpenAPI and
frontend API declarations must be generated from it. The human-approved revisions and frozen
baseline are recorded in [the contract freeze record](../specs/001-appointment-scheduling/contracts/canonical-review.md#api-v1-human-approval-and-freeze).

## Goal and actors

One host defines appointment types and weekly working hours. Guests browse and book without
creating an account, receive on-screen confirmation, and contact the host for cancellation or
an unknown booking outcome. The single seeded administrator authenticates to manage activities,
availability and bookings. Public administrator sign-up and guest account management are excluded.

All five prioritized journeys are required for the MVP: public discovery and booking (P1),
administrator authentication/configuration and booking cancellation (P2), and responsive,
timezone-consistent use (P3). Priorities are delivery order, not permission to omit journeys.

## Activity catalog — FR-001–003/015/031; SC-001/019

- Public lists contain active activities only, with name (`title` in the API), unique slug,
  mandatory description, positive duration divisible by 15 minutes, and IANA timezone.
- Descriptions require 1–2000 Unicode code points after trimming outer whitespace. Reject blank
  and overlong input without truncation; retain internal whitespace and line breaks. Render all
  content literally as plain text, including markup-like text. Administrators edit full text
  with field feedback. Catalog previews are allowed only with full text available before booking.
- Missing/inactive offerings cannot be booked. Catalog and date views show clear empty states,
  distinguish failures from empty results, and allow selection of another activity/date.

## Availability and time — FR-003–005/008–009/021/026–027/030; SC-002/009/013–015/018

- Working windows use ISO weekdays 1–7 and the activity's IANA timezone. Blocked dates apply
  per activity, using its local date; blocking all offerings requires blocking each separately.
- Windows must end after their start on one activity-local calendar day. Reject duplicate,
  overlapping, overnight, zero-length or reversed windows atomically, retaining the old schedule.
  Touching windows are allowed but never joined. Empty replacement is permitted.
- A-001: appointment starts align with activity-local minutes 00, 15, 30 or 45, with zero
  seconds/fractions, regardless of window opening or display timezone. Do not round or shift
  a submitted start. A 30-minute appointment in 09:10–10:00 offers 09:15 and 09:30 when otherwise
  eligible; 09:10–09:40 offers none. Working-window boundaries need not align to the grid.
- The entire half-open elapsed interval `[start,end)` must fit one continuous valid real portion
  of one window. Its end may equal the portion's right boundary. Never bridge an excluded
  portion, move a missing boundary, extend the window or combine windows to fit an appointment.
- On a DST transition, valid portions are instants with the same activity-local date and local
  clock at/after window start and before window end. Skip nonexistent starts; offer both eligible
  repeated occurrences as distinct UTC instants with distinct offset labels. A wholly nonexistent
  window has no slots. Use IANA rules, never a hard-coded fixed offset or calendar-day arithmetic.
- At current eligibility instant N, offer/accept a start S only when
  `N + 1 elapsed hour <= S <= N + 1440 elapsed hours`. Both bounds are inclusive and constrain
  start only. End may exceed the horizon if it fits the window. Recheck at submission, including
  after lock waits; browsing creates no hold, reservation or notice grace period.
- Exclude past, blocked, inactive, occupied, off-grid and otherwise ineligible starts. Confirmed
  intervals for the same activity cannot overlap; adjacent intervals and different activities
  remain independent. Server revalidation and PostgreSQL exclusion are both required.
- Initial display uses the detected visitor timezone, falling back to the activity timezone;
  allow manual IANA selection. Selected calendar dates group starts in that display timezone,
  including all relevant activity-local dates, once each. Working/block rules stay activity-local.
  Changing display timezone relabels instants and never moves a selected/booked appointment.
- API response instants use UTC `Z`; explicit-offset request instants normalize to UTC, and naive
  instants are rejected. The interface always identifies the display zone and repeated offsets.

## Booking and safe recovery — FR-006–012/022/024; SC-003–005/011

- Guests submit activity, start, nonblank name and syntactically valid email. The server derives
  end from current duration; the client cannot prescribe it. Preserve submitted identity strings
  for retry matching; do not add verification, deliverability, length or normalization policies.
- Success creates exactly one confirmed booking. The on-screen result shows reference, activity,
  start/end, displayed timezone and status. Every public success omits name/email, credentials
  and retry identifiers; labels come from activity/display context. No email delivery is required.
- Invalid input receives understandable correction feedback; stale/unavailable slots allow a
  return to availability. Rejections do not create a booking or change another booking.
- Distinct attempts competing for one available interval yield one 201 and one 409
  `slot_unavailable`. Matching retries of one attempt follow the separate at-most-once protocol,
  returning the same identity/current status, including cancellation, without reconfirming it.
- Before first submission create a private unpredictable contact-free attempt identifier and
  freeze its details. Reuse it only with the same activity, normalized UTC start and exact name/
  email. Changed details yield generic `attempt_mismatch` without original values/result/identity.
  Deliberate corrections need a new identifier only after a definite outcome or host verification.
- A-002: admission is valid only when its binding and database-generated wall-clock timestamp T
  and deadline E commit successfully and durably in one transaction. `E=T+24 elapsed hours`,
  immutable thereafter. T is not commit metadata, transaction-start time, HTTP arrival, ACK time
  or a retry timestamp. Stamp T late after contention/preparation. Commit delay consumes the
  fixed window; commit at/after E is already expired, with no execution/pending/result access.
- Known rollback admits nothing through that transaction, without asserting no competing request
  committed. Uncertain COMMIT remains unverified until fresh committed-state evidence resolves it.
  If no admission ever committed, a later explicit same-key request can establish first admission.
- Before E, matching simultaneous retries converge on one booking/result or a verified unfinished
  state; recorded rejection remains final. Completed success returns 200/current status without
  applying later eligibility rules. Newly committed success is 201. No confirmation precedes known
  booking/result commit. A 202 requires proven committed matching unexpired unfinished admission,
  known expiry and Retry-After, and promises no background completion. Failed lock transactions
  must roll back before fresh classification; mismatch/expiry/unverified admission cannot be pending.
- At/after E, chronological expiry is 410 `attempt_expired`, checked before payload/result access.
  Tombstones prevent treating expired keys as new. An unknown result directs host verification.
  Phase-specific 503 `admission_unverified`/`execution_unverified` and network/500/503 uncertainty
  must not be represented as confirmed success, definite rejection or proved rollback.
- Recovery is an explicit same-key/details POST, never an automatic new attempt, key-only result
  lookup or contact search. Browser memory loss/reload may lose recovery capability; direct the
  guest to the host. Clear contact-bearing frozen payload/key on completion, expiry or abandonment.
- A-003: a separately human-approved unrecoverable disaster restore may invalidate prior-generation
  identifiers, even unexpired ones, after writer fencing. Return 409 `attempt_invalidated_by_restore`,
  distinct from chronological 410. It proves neither prior admission, age nor booking failure;
  explain lost recovery state and require host verification before another deliberate attempt.
  Do not automatically issue a replacement key. Normal restarts, routine maintenance and transient
  failures preserve valid generation/T/E/binding/results; missing normal startup state fails readiness.

## Administrator — FR-013–018/023/028; SC-006/008/010/016

- One seeded administrator, hashed passwords, runtime-provided secrets; no public sign-up.
  Login returns an opaque bearer and server expiry. T-01 uses browser memory only, with no web
  storage, persisted cache, URL or auth cookie. Reload requires reauthentication; XSS remains a
  security risk requiring prevention. Logout revokes the presented session and clears memory.
- A login at T authorizes only before `T+60 elapsed minutes`. Activity never extends or renews it;
  the server rechecks expiry at authorization, including after waits. Missing/invalid/expired bearer
  yields 401 before protected validation or existence lookup, exposes no contacts and changes nothing.
- At expiry clear/lock protected state. Preserve only non-sensitive configuration drafts, never
  passwords/guest contacts; require credentials, review and explicit resubmission of failed writes.
- Manage title, description, slug, duration, timezone, active status, weekly windows and per-activity
  blocked dates; read inactive activities and saved configuration through protected operations.
  Invalid updates retain valid state. Repeated blocking returns the existing block.
- Configuration changes preserve every existing booking's agreed start/end/status. Warn about
  affected confirmed bookings using the preservation-count header; new rules affect new attempts
  only. Cancellation remains an explicit individual action, never a configuration side effect.
- View confirmed/canceled history and contacts while still present and within retention. Represent
  missing/deleted/restored-away contacts explicitly as removed, without invented placeholder names.
- Only the authenticated administrator cancels. Cancellation frees otherwise eligible slots,
  changes no other booking and returns 204. Repeated/concurrent cancellation succeeds as a no-op
  acknowledging current canceled state; preserve original cancellation time and retention deadline.
  Missing booking stays 404; unauthorized stays 401. No guest cancellation or hard deletion is added.

## Privacy and operational requirements — FR-019/025/029; SC-012/017

- Automatically delete name/email at exactly 720 elapsed hours after recorded appointment end
  for non-canceled bookings, or first successful cancellation for canceled bookings. Configuration,
  retries and repeated cancellation never move that anchor. Apply the deadline to recovery copies.
- At/after the deadline all reads suppress contacts even on cleanup failure. Surface any overdue
  deletion/failure to operators honestly, with no extension or polling grace; read suppression is
  not proof of physical deletion. SQL deletion is not forensic disk erasure.
- Retain only reference, activity, start/end, status and original cancellation time as booking
  history. This is contact removal, not promised irreversible anonymity. Public booking results,
  catalog/availability, ordinary errors, operational logs and traces reveal no guest contacts/secrets.
- Backups/exports contain only approved configuration and contact-free history, with no guest
  names/emails, contact-bearing submissions, retry credentials or private binding/session copies.
  Contact loss on restore, even before a normal deadline, is an accepted MVP tradeoff.
- T-03: use fail-closed allowlisted logical backups and validated hosting controls. Disallow
  contact-bearing volume/provider snapshots, WAL archives, statement/request logs and crash dumps.
  Ordinary live WAL for crash recovery is not an approved backup; normal restart preserves state.
  Restores must not reintroduce contacts or expired retry access; qualified retry-state loss follows
  A-003 and separate restore approval. Disclose snapshot-age/history-loss limits; no RPO/RTO is added.
- No-store applies to authentication, attempt/context, booking, admin and error responses. Restrict
  CORS/TLS, redact credentials/contacts and verify privacy/security controls before public deployment.
  Detailed worker failures are operator CLI output; public readiness exposes only generic status.

## User experience and verification

- Core public/admin journeys work at desktop/mobile acceptance widths 320 and 1280 CSS pixels,
  without horizontal page scrolling or hidden primary actions (FR-020, SC-007).
- Clearly distinguish loading, empty availability, validation, conflict, expired access, verified
  pending, unverified outcome, chronological expiry and restore invalidation. All failures provide
  an understandable correction/recovery action without claiming unproved success or failure.
- Reproducible Docker Compose startup with PostgreSQL, reviewed Alembic migrations and repeatable
  synthetic development seeds; component-owned Dockerfiles, QA-owned Compose/CI, Lead-owned API.
- Unit date/DST tests, real PostgreSQL integration/transaction/concurrency/privacy verification,
  API status/body/header/security conformance and E2E user journeys are mandatory. TypeSpec compiles
  to OpenAPI, which generates TypeScript; generated files are never independent source contracts.
- The unchanged specification's 31 functional requirements, 19 success criteria and 77 scenarios
  are the full acceptance suite. T-02 remains provisional pending PostgreSQL concurrency, crash,
  timeout and idempotency evidence; T-03 remains conditional on backup/hosting/privacy verification.
  Contract generation and documentation checks cannot satisfy either condition.

## Scope boundaries and remaining gates

Out of scope: calendar synchronization, OAuth, team/multi-tenancy, payments, email sending,
invitations, external integrations, real-time WebSockets, advanced recurring exceptions,
production observability, guest self-service cancellation, account management and hard deletion.

D-001–D-012 are resolved through fifteen recorded answers, with receipt/recovery explicitly amended
by A-002/A-003 and grid alignment by A-001; no product default is silently selected here.
[Source reconciliation](../specs/001-appointment-scheduling/contracts/source-reconciliation.md)
and the [approved plan](../specs/001-appointment-scheduling/plan.md) identify the remaining
architecture/ADR alignment and runtime verification work. Historical architecture/ADR wording
must not override approved same-key retry, isolated contacts or the current API schema.

The human formally approved the reviewed PRD/canonical API package and authorized API-v1 freeze
and its local baseline commit on 2026-10-25. The frozen contract follows Lead-owned compatibility/
change control; Frontend/Backend must not change it independently. This approval does not
authorize task generation, implementation, agent launch, merge, push, restore or deployment.
