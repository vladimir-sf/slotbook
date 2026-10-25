# Proposed SlotBook REST contract reconciliation

Status: APPROVED TECHNICAL DESIGN, 2026-10-25; canonical contract reconciliation/review pending.
Proposal ID: `slotbook-mvp-api-3-review`.
Reconciled with approved A-001/A-003 and clarified A-002; T-02 execution remains provisional
and T-03 operational acceptance conditional. Exact canonical TypeSpec syntax/generated shapes
are still a contract proposal, unchanged in production. The current contention/crash design
is [retry-protocol.md](retry-protocol.md); no runtime evidence or implementation approval is implied.
This is a design document, not a second canonical contract or a generated OpenAPI file.
`contracts/main.tsp` at approved baseline `e9f16809058fe826523bf8c19387b6ba65b8e145`
remains unchanged and authoritative. Nothing here may be implemented as a private JSON format.
In the separately authorized contract-reconciliation step, the lead transcribes these models/operations
into TypeSpec, compiles it, reviews the OpenAPI diff, and freezes generated TypeScript before dependent implementation.

## Common rules

Product prefix `/api`; the explicitly proposed operational paths below have no product prefix.
JSON request/response bodies except 204; timestamps are RFC 3339 UTC `Z` values.
Reject naive timestamps; normalize explicit-offset input to UTC before matching instants.
IDs are opaque UUID strings. Dates are ISO calendar dates. Weekly clocks are offset-free local
times with the existing TypeSpec plainTime precision; no new minute-alignment restriction.
Bearer authorization is required on every `/admin/*` operation and logout. Authenticate before
exposing protected object existence or parsing errors. CORS permits only configured frontend
origins, explicitly permits Authorization/Idempotency-Key, and exposes the warning/expiry headers and Retry-After.
No ambient authentication cookies are introduced. Apply no-store to login, context, booking,
admin and error responses; no intermediary may cache a response containing security/contact data.

Use TypeSpec response models with explicit `@statusCode`, body and header properties. Existing
bare `BadRequestResponse`/`ConflictResponse`/`UnauthorizedResponse` branches become the concrete
bodies below. Exact syntax must be compiled against the pinned 1.17.0 toolchain during approved
contract finalization; no uncompiled TypeSpec sketch is presented as a working contract.

## Approved slot-grid semantics (A-001)

Availability and new-booking validation use exact clock minutes 00/15/30/45 with zero seconds
and fractional seconds in the activity's IANA timezone. The grid is independent of working-window
opening and visitor display timezone. A 09:10–10:00 window with 30-minute duration offers only
09:15 and 09:30 when otherwise eligible; 09:10–09:40 offers none. Reject direct off-grid instants
with the proposed 400 slot_ineligible; never round/shift them or extend/merge windows. The full
elapsed interval must fit one continuous valid portion of one window. Nonexistent local starts
remain omitted/rejected; both eligible repeated aligned starts retain distinct UTC instants and
offset labels. No new wire field or persisted-data migration is needed for this amendment.

## Proposed shared schemas

| Model | Fields and semantics |
| --- | --- |
| `Activity` | Existing id, slug, title, durationMinutes, timezone, isActive; add required description string. |
| `ActivityWrite` | Existing write fields plus required description. Description is trimmed at the boundary, 1–2000 Unicode code points, multiline/literal text; no truncation. Preserve internal text. Validate positive duration divisible by 15 and supported IANA timezone. |
| `Slot` | Existing startsAt, endsAt UTC instants. No contacts or booking IDs. Browser derives labels and offset from the chosen display zone. |
| `BookingRequest` | Existing activityId, startsAt, attendeeName, attendeeEmail. End is never accepted. Nonblank name and syntactically valid email; preserve submitted identity strings. Unknown fields rejected with field feedback. No extra length/normalization policy is silently added. |
| `BookingSummary` | id, activityId, startsAt, endsAt, status (`confirmed` or `canceled`), canceledAt (`utcDateTime` or null). No attendee fields, token, or retry key. Used for EVERY public booking success including first submission. |
| `PresentContacts` | state literal `present`, attendeeName, attendeeEmail; used only under protected AdminBooking.contact. |
| `RemovedContacts` | state literal `removed`; no attendee fields. Used after deadline/deletion or contact-free restore. Never empty fake identity strings. |
| `AdminBooking` | BookingSummary plus contact union `PresentContacts | RemovedContacts`. Read suppression occurs before serialization, at the current deadline check. |
| `AttemptContext` | generation string (public random restore epoch); no authorization power. Cache-Control no-store. |
| `AttemptPending` | state literal `pending`, expiresAt UTC. No confirmation, booking ID, contacts, or original payload. |
| `AdminToken` | Existing accessToken, tokenType literal `bearer`; add expiresAt UTC. Opaque token semantics, fixed server-enforced lifetime, no refresh token. |
| `FieldError` | path string naming a contracted field, code string, message safe human text. No submitted/rejected values, stack trace, credentials, contacts, or raw validation objects. |
| `ApiError` | code from the error table, message safe human text, fields optional array of FieldError. Body does not echo original request or reveal another attempt's details/result. |

All public confirmations are contact-free. Activity/zone labels come from the selected activity
and UI display context; timezone switching must not move the returned start/end. Admin union
must be discriminator-compatible in generated OpenAPI/TypeScript. Nullability alone must not
permit accidental serialization of expired names/emails.

## Operation and response matrix

Every operation additionally declares safe 500 `internal_error` and 503 `service_unavailable`.
503 is an uncertain result for mutations unless a durable terminal result is known. Do not
misrepresent internal errors as definite booking rejection. All error bodies follow ApiError.

| Operation | Success | Expected errors / change |
| --- | --- | --- |
| GET `/activities` | 200 Activity[] (active only) | Public, existing path; description addition. |
| GET `/activities/{slug}` | 200 Activity | 404 not_found for missing/inactive; description addition. |
| GET `/activities/{slug}/slots?date=...&displayTimezone=...` | 200 Slot[] | 400 validation_failed for invalid date/zone; 404 not_found for missing/inactive. Optional displayTimezone defaults to activity zone. Date means date in that display zone; working/block rules remain activity-local. Existing query without new parameter retains activity-local semantics. |
| GET `/booking-attempts/context` | 200 AttemptContext | New supporting read; no contact or guest lookup. Failure prevents creation of a new attempt, while an existing key is retained for explicit recovery. |
| POST `/bookings` + Idempotency-Key | 201 BookingSummary on newly committed booking; 200 BookingSummary for matching completed success, using current status; 202 AttemptPending only for proven committed matching unexpired unfinished admission | 400 validation_failed or slot_ineligible/notice_required/horizon_exceeded; 409 slot_unavailable or attempt_mismatch, or (approved A-003) attempt_invalidated_by_restore; 410 attempt_expired only for chronological expiry; 503 admission_unverified/execution_unverified for unresolved phase outcomes. Rejection of a prior terminal attempt replays its original safe status/code. Missing/malformed key = 400. No raw contact values in any response. |
| POST `/auth/login` | 200 AdminToken | 400 validation_failed; 401 unauthorized (generic invalid credentials). Preserve seeded-single-admin scope, no sign-up/refresh. |
| DELETE `/auth/session` | 204 no body | 401 unauthorized. Proposed explicit local-session termination: revoke presented verifier and clear browser memory. No account management capability. |
| GET `/admin/activities` | 200 Activity[] including inactive | 401 unauthorized. New read supports managing existing/inactive activities; public list is insufficient. |
| POST `/admin/activities` | 200 Activity | 400 validation_failed; 401 unauthorized; 409 slug_conflict. Keep current success status rather than silently changing to 201. |
| PUT `/admin/activities/{id}` | 200 Activity with X-Preserved-Booking-Count | 400 validation_failed; 401 unauthorized; 404 not_found; 409 slug_conflict. Existing invalid-update branch is missing today. |
| GET `/admin/activities/{id}/weekly-windows` | 200 WeeklyWindow[] | 401 unauthorized; 404 not_found. Supporting read for existing configuration. |
| PUT `/admin/activities/{id}/weekly-windows` | 200 WeeklyWindow[] with X-Preserved-Booking-Count | 400 validation_failed for invalid/overlap/overnight/duplicate set; 401 unauthorized; 404 not_found. Atomic replacement, including empty set. |
| GET `/admin/activities/{id}/blocked-dates` | 200 BlockedDate[] | 401 unauthorized; 404 not_found. Supporting read for existing configuration. |
| POST `/admin/activities/{id}/blocked-dates` | 200 BlockedDate with X-Preserved-Booking-Count | 400 validation_failed; 401 unauthorized; 404 not_found. Same block replays existing state, without changing bookings. No unblock feature inferred here. |
| GET `/admin/bookings` | 200 AdminBooking[] | 401 unauthorized. Contact-present/removed union replaces current always-required attendee strings. |
| DELETE `/admin/bookings/{id}` | 204 no body, including already canceled | 401 unauthorized; 404 not_found. Repeated cancellation keeps original canceledAt and deletion deadline. UI acknowledges current canceled state after 204; no response-body change needed. |

The three protected configuration reads and explicit session termination close UI/security
integration gaps; they are approved technical interface proposals pending canonical
contract review, not new product journeys. No public booking-list/detail endpoint, guest cancellation, exports, calendar sync,
payments, multi-tenancy, or email integration is added.

## Operational HTTP contracts

Declare these in canonical TypeSpec as well, placing the product `/api` prefix so it does not
accidentally prefix operational paths. Keep one reviewed definition chain for all HTTP shapes.
GET `/health` preserves existing 200 JSON `{ "status": "ok" }` liveness. Proposed GET `/ready`
returns 200 `{ "status": "ready" }` only when DB/schema/retry-generation/worker readiness pass;
otherwise 503 ApiError with code service_unavailable and generic text. No contact, credential,
DB connection detail, or operator failure inventory is public. Detailed worker status is an
operator CLI function, not an unauthenticated diagnostic endpoint. Both responses use no-store.

## Error codes and handling

| Status | code | Meaning / UI behavior |
| --- | --- | --- |
| 400 | validation_failed | Invalid syntax/type/field/window set; fields can identify safe input paths. FastAPI default 422 must map here. |
| 400 | slot_ineligible | Start is not an eligible configured slot or activity unavailable; return to current availability. No reservation was committed. |
| 400 | notice_required | Start falls below current inclusive one-hour notice boundary. |
| 400 | horizon_exceeded | Start exceeds current inclusive 1440-hour horizon. |
| 401 | unauthorized | Missing/invalid/expired credentials; clear/lock protected state and require login, never replay failed writes. No protected object information. |
| 404 | not_found | Visible activity/config/booking resource is missing; protected calls authenticate first. |
| 409 | slot_unavailable | Another confirmed booking overlaps; terminal for this attempt. Distinct competing keys produce one 201/one 409. |
| 409 | attempt_mismatch | Same private key with changed details; generic text and no fields identifying original values, result, or booking. |
| 409 | slug_conflict | Public identifier already used; safe field guidance for authenticated admin. |
| 410 | attempt_expired | Authoritative current-generation chronological expiry `now >= T+24h`; no result or new attempt, never ordinary pending. T is the immutable DB-generated timestamp persisted in successful admission under clarified A-002; delayed commit never extends E. |
| 409 | attempt_invalidated_by_restore | Approved A-003: prior/noncurrent generation after separately approved unrecoverable restore. Unknown outcome; host verification before replacement, no automatic new key or chronological-age claim. |
| 503 | admission_unverified | No provable committed admission/receipt after rollback, timeout or uncertain COMMIT; no pending, expiry header or confirmed booking claim. Preserve key/details for explicit retry. |
| 503 | execution_unverified | Admission/result/commit state cannot currently be established; no false success or definite business rejection. Preserve key/details for explicit retry. |
| 500 | internal_error | Safe generic service fault. Treat unverified mutations as unknown, not confirmed failure. |
| 503 | service_unavailable | DB/dependency unavailable; retain original attempt and show unverified state. Same-key explicit retry only. |

202 pending is neither an admission guess nor booking confirmation. It requires a fresh
committed-state classification proving original T/E, matching details, unexpired validity and
unfinished outcome. After NOWAIT/timeout/deadlock, roll back the whole failed transaction before
that classification; uncommitted admission, mismatch, expiry and missing receipt cannot get 202.
It carries Retry-After (integer seconds) and known expiry; it does not promise an active background
worker. Retry remains explicit, never a new-key fallback. Initial terminal validation/eligibility
rejections are definitive only after their result commits;
malformed credentials/keys that cannot identify a valid attempt are rejected without claiming
that a tracked booking attempt exists.

Missing/invalid bearer on protected routes wins over body validation and resource lookup.
No 403 is needed for a single administrator role; introducing roles would reopen the contract.
No default undocumented 422/HTML error body may escape from parsing, validation, or middleware.

## Required headers and privacy

- `Idempotency-Key`: required private request header on booking POST only. Exact syntax is
  public generation + dot + unpadded base64url encoding of 32 random bytes. Never accept the
  stored HMAC digest as a credential. Request URLs never contain this header's value.
- `X-Attempt-Expires-At`: original verified E on admitted booking responses, including known
  terminal rejections and 202. Omit if receipt/expiry cannot be established (admission_unverified
  or lost restore state); never imply committed admission merely by returning this header.
  Under approved A-002, E=T+24h from the DB-generated timestamp persisted by the successful
  admission transaction, never COMMIT metadata, ACK time or a later retry timestamp. Commit
  delay consumes this fixed interval; E is not reset when the admission becomes visible.
- `X-Preserved-Booking-Count`: nonnegative count on successful activity/window/block changes.
  Frontend shows the required preservation warning when nonzero. Responses carry no contact data.
- `Authorization: Bearer ...`: protected calls and logout only; API never accepts it from query
  parameters. Return `WWW-Authenticate: Bearer` with 401.
- `Cache-Control: no-store`: private/auth/attempt/context/error responses; do not log response
  bodies, request payloads, Idempotency-Key, Authorization, or validator inputs. No HAR/trace
  artifacts containing these values may be retained in CI.

## Retry binding, expiry and recovery wire semantics

Generate the private identifier before first submission. Freeze the original details in memory
for that attempt; a deliberate correction creates a new identifier only after the original
outcome is definite or the user follows host verification for unknown/expired outcomes.
Only explicit same-key POST retries are offered after connection loss. Clear the in-memory
contact-bearing submission and credential on expiry/completion/abandonment, retaining only
contact-free confirmation or unknown-outcome guidance. No key-only recovery
operation or contact lookup exists. Losing browser memory/reloading may lose this capability;
the UI directs the guest to the host rather than guessing an outcome or resubmitting.

Canonical matching normalizes activity UUID and start to UTC, but keeps submitted name/email
strings exact. It must not apply extra identity normalization. Mismatch is generic even when
an original attempt was rejected. At expiry the server checks 410 before exposing status/result;
a new key is required for a genuinely new attempt. Approved A-003 permits prior-generation
409 attempt_invalidated_by_restore after a separately approved unrecoverable restore. It is
not chronological 410, does not claim a prior admission/outcome/age, and directs host verification
before replacement. Normal restart/transient failure retains generation/T/binding/results.
No old result is reconstructed from another guest's contact data.

## Approved admission boundary and recovery messages

Clarified A-002 defines T as a database-generated timestamp stored with E/binding in a
successfully committed admission transaction. It is not commit metadata or necessarily the
commit instant. Only commit makes it valid; delayed commit reduces remaining validity and
commit at/after E yields 410 without booking/pending. HTTP arrival or rollback creates no valid
attempt through that transaction.
An uncertain COMMIT is not reported as a known rollback. Fresh committed-state lookup establishes
what is known; missing proof yields unverified 503. No booking business execution starts before proven admission.

Chronological expiry guidance: “This attempt's retry period has ended. Its outcome may still be
unknown; contact the host before another booking.” A-003 invalidation guidance: “This service
cannot recover this attempt after a restore. Its booking outcome is unverified. Contact the host
before making another booking.” Neither response automatically issues a new private identifier.
The generation context read supports the approved exception; its exact canonical operation
syntax still awaits the separately reviewed contract change.

## API proposal review evidence required later

The later canonical diff must include every model, operation, error branch, header, and security
requirement above, plus the approved slot-grid anchor. Compile TypeSpec → OpenAPI 3.0 → TS
schema declarations; review breaking changes (required description, public booking contact
removal, admin union). Verify operation-by-operation real responses, including malformed JSON,
missing/expired auth, wrong UUID/date/timezone, and headers. Swagger/FastAPI output is a
conformance aid, not a replacement source. No compiler or API tests were run for this Markdown
proposal because no executable contract changes were made.
