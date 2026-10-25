# Architecture

Documentation aligned on 2026-10-25 with the human-approved technical design at
`5f1ce85bc16b25541337b5ef55d6f25d7b3a574d`, amendments A-001/A-002/A-003 and T-01–T-04.
The [canonical contract](../contracts/main.tsp) was formally approved and frozen as API v1
(1.0.0) on 2026-10-25; see the [freeze/change-control record](../specs/001-appointment-scheduling/contracts/canonical-review.md#api-v1-human-approval-and-freeze).
The following describes intended implementation; the current app remains a frontend scaffold
and a backend /health route. Documentation alignment does not establish runtime verification.

```text
React/TypeScript/Vite ---> FastAPI ---> PostgreSQL 16
         ^                   |              ^
  generated TS types    SQLAlchemy/Alembic   |
         ^                                  |
       OpenAPI                     retention worker
         ^                         (same backend image)
       TypeSpec
```

Use one modular API with synchronous SQLAlchemy/psycopg transaction scopes, Python 3.12,
PostgreSQL, and React/TypeScript/Vite. No broker, distributed lock, execution lease or additional
service framework is required. Exact design and alternatives are recorded in the approved
[plan](../specs/001-appointment-scheduling/plan.md),
[research](../specs/001-appointment-scheduling/research.md) and
[data model](../specs/001-appointment-scheduling/data-model.md).

## Sources, ownership and interface boundaries

- `contracts/main.tsp` is the sole REST source. Lead owns it, generated OpenAPI and
  `frontend/src/api/schema.d.ts`; generated files are derived artifacts, never independent DTOs.
- Frontend owns `frontend/**` and its Dockerfile except generated API definitions. Backend owns
  `backend/**`, its Dockerfile, migrations, service transactions and retention-worker code.
  QA/DevOps owns `tests/**`, root Compose and CI, excluding component Dockerfiles (T-04).
- [docs/AGENT_TASKS.md](AGENT_TASKS.md) governs shared ownership. Future feature tasks must fit
  those boundaries; no tasks or implementation agents are authorized by this document.
- The canonical review defines eighteen operations on fifteen paths. Public catalog/detail/
  availability, generation context, booking POST and login are public; every admin operation
  and session logout requires bearer authentication. Health/readiness stay outside `/api`.
- Shared input/body/error/header/security shapes come only from generated OpenAPI/TypeScript.
  Frontend uses the generated types and server-returned UTC slots. Backend validates and
  serializes to those same shapes; its framework OpenAPI cannot replace TypeSpec.

## Planned persistence and privacy boundaries

The earlier scaffold sketch placed contacts and created-at history in bookings. The approved
privacy design supersedes that storage sketch; this changes documentation, not an existing schema.

| Area | Planned contents |
| --- | --- |
| Public configuration | activities (including mandatory description), weekly windows, per-activity blocked dates |
| Contact-free booking history | reference, activity, immutable UTC start/end, confirmed/canceled status, original cancellation time only |
| Private contacts | booking reference, live name/email, indexed deletion deadline; zero or one contact row per booking |
| Private attempt ledger and bindings | generation/HMAC verifier, immutable receipt T/deadline E, original-detail fingerprint, safe terminal result and non-authorizing expiry tombstone |
| Other private state | retry generation/recovery events, single admin/password hash, session verifiers/expiry, safe worker status |

No raw retry credential or bearer is stored. Binding fingerprints are derived personal state,
not contact-free backup data. Role permissions and explicit backup allowlists enforce isolation;
private schema names alone do not. No additional booking-history fields or identifying free text
are inferred. Retained history may remain externally correlatable; irreversible anonymity is not claimed.

## Booking consistency, lock order and retries

[ADR-0002](ADR-0002-booking-concurrency.md) retains PostgreSQL GiST exclusion for same-activity
confirmed half-open intervals `[start,end)`, allowing adjacency. Application SELECT checks alone
are insufficient; derive end and revalidate current rules inside the execution transaction.

T-02 is provisionally approved: use a short admission transaction, then a separate locked
execution transaction. Admission persists binding, DB-generated wall-clock T and E=T+24 elapsed
hours atomically. Stamp T late after contention/preparation. Only successful durable commit makes
it valid; T is not commit metadata, transaction-start time, HTTP/ACK time or retry time. Delayed
commit consumes the fixed window, possibly leaving it already expired; never restamp a committed
attempt. Known rollback admits nothing through that transaction; uncertain COMMIT stays unverified.

Global lock order is attempt → activity → booking → contact. Admission never locks activity;
execution takes the attempt NOWAIT, then the activity lock with bounded waiting. Configuration
and cancellation share the activity lock, refresh state, and cannot race new-booking eligibility.
Cancellation starts at activity then booking/contact, never locks an earlier attempt. Workers
follow the approved [retry protocol](../specs/001-appointment-scheduling/contracts/retry-protocol.md):
attempt cleanup takes attempt/binding only, contact cleanup takes contacts only; neither acquires
earlier-order parent locks. No lock inversion or catch-and-continue through an aborted transaction.

Sample fresh database wall-clock time after waits for expiry, eligibility and protected
authorization; transaction-start now() is insufficient. A known named exclusion violation rolls
back an insertion savepoint and records a terminal slot rejection. Lock timeout, deadlock or
unexpected execution failure rolls back the whole failed transaction before fresh committed-state
classification. Booking/contact/result commit together; no confirmation precedes known commit.

Distinct conflicting keys yield one 201 and one 409 slot_unavailable. Matching retries before E
return a stable rejection or the same booking/current status (200 on replay), never recreate a
canceled booking. 202 requires proven committed matching unexpired unfinished admission, known
expiry and Retry-After; it is not a promise of a background worker. Missing proof produces
phase-specific unverified 503, not ordinary pending or assumed rollback. Chronological expiry is
410 attempt_expired before binding/result disclosure; tombstones prevent key reuse.

Normal restarts/transient failures retain generation/T/E/binding/results. Only a separately
human-approved unrecoverable disaster restore may fence old writers and change generation (A-003),
returning 409 attempt_invalidated_by_restore even for previously unexpired identifiers. It proves
neither chronological expiry nor booking failure. Unknown/expired/invalidated results direct host
verification; no automatic replacement key, key-only recovery or contact lookup is permitted.
All seventeen protocol/runtime cases remain required and unexecuted; scaffold tests do not close T-02.

## Availability and time

Use UTC API instants and elapsed arithmetic with pinned IANA timezone rules. Initial display is
the detected visitor timezone with activity fallback/manual selection. The slots date means the
selected display date; optional displayTimezone defaults to activity timezone for existing queries.
The server covers all intersecting activity dates, groups by display-local start date and returns
sorted/deduplicated UTC slots. Working windows/blocked dates stay activity-local.

A-001 fixes starts at activity-local minutes 00/15/30/45 with zero seconds/fractions, independently
of window opening or display zone. Do not round direct submissions. Windows are same-day,
nonoverlapping, may touch and need not align to the start grid. An entire elapsed `[start,end)`
must fit one continuous valid real portion of one window; end may equal its boundary. Skip missing
local times, distinguish both eligible repeated occurrences/offsets, and never shift/extend/merge
windows or bridge excluded portions. A 30-minute activity in 09:10–10:00 permits 09:15/09:30;
09:10–09:40 permits none. At each fresh new-booking check N, require N+1h <= start <= N+1440h,
inclusive, with no browsing hold/grace. Existing confirmed intervals remain unchanged by config edits.

## Authentication and response privacy

T-01: opaque 256-bit bearer credentials, only hashed session verifiers in the DB, fixed 60 elapsed
minutes from login, no renewal/refresh or active-use extension. Browser storage is memory only;
reload requires login and XSS can still compromise a live credential. Server authorization checks
expiry, including after waits. Authenticate before protected validation/existence lookup; missing,
invalid or expired credentials return 401 + WWW-Authenticate: Bearer without contact disclosure.
At expiry lock/clear protected state; keep only non-sensitive config drafts and require credentials,
review and explicit resubmission. Logout revokes the presented session; no auth cookies are introduced.

Every public booking success is contact-free, including the first 201. Protected history uses an
explicit present/removed contact discriminator. Safe typed errors never contain submitted values,
credentials or raw framework validation objects; malformed requests map to contracted 400 rather
than uncontracted 422. No-store, explicit-origin CORS/header exposure, literal text rendering,
redacted logs and deployment-time TLS/CSP review remain required. The current /health scaffold
has no no-store header yet; runtime conformance remains implementation work.

## Contact deletion, backups and recovery

Automatically delete contacts at recorded end +720 elapsed hours for non-canceled bookings or
first cancellation +720h for canceled bookings. Repeated cancellation/config edits/retries never
move that anchor or restore removed contacts. All reads suppress contacts at/after the applicable
deadline even if physical deletion fails. Any overdue row is an immediate operator-visible
failure, not permission for a grace period or a claim of completed deletion. A separate worker
uses bounded transactions, startup catch-up and deadline scheduling. SQL deletion is not forensic
disk erasure. Retention, cancellation and worker-failure interactions require privacy verification.

T-03 remains conditional: contact-free logical backups only, with fail-closed table/column/schema
allowlists and restricted backup roles. Exclude contacts, original submissions, private attempts/
bindings/sessions and credentials. Do not allow contact-bearing volume/provider snapshots, WAL
archives, request/statement logs or crash dumps. Ordinary live WAL for normal crash recovery is
not an approved backup. Validate actual artifacts, restored data and hosting controls before public use.

Separately approved A-003 recovery fences writers, restores permitted history/configuration,
validates constraints, reprovisions admin/generation and leaves contacts/sessions/attempts empty.
Contact loss and snapshot-age/history-loss limits must be disclosed; no new RPO/RTO is promised.
Restored history honestly shows removed contacts and never revives expired retry access. Approval
of the policy is not approval to execute a restore or deployment.

## Lifecycle and verification gates

Lead compiles TypeSpec to OpenAPI and regenerates frontend types with existing npm commands.
Review breaking shapes/errors/security/headers, demonstrate byte-for-byte regeneration, then stop
for human contract approval/freeze. Generated-file review does not grant implementation permission.
Accepted ADR history is retained; the following documentation supplements record already approved
design, not new architecture decisions. Material future changes require the constitution's review.

Development uses Docker Compose with PostgreSQL durability/UTC checks, migrations, explicit
synthetic development seeds, API/worker readiness and frontend startup. Component owners publish
image/CLI interfaces; QA owns Compose/CI. Planned checks cover contract generation/conformance,
frontend build, pytest/HTTPX/PostgreSQL races/privacy and Playwright desktop/mobile journeys.

Backend's existing `requirements.txt` declares runtime and scaffold-test dependencies together,
including pytest and HTTPX; no separate dev/test manifest or Python lock exists. A root `.venv`
keeps host dependencies isolated and ignored. Installing the declared PyJWT package for testing
does not change the approved opaque-session design; future dependency pruning/locking is separate
implementation/infrastructure work. Current pytest covers only /health, not MVP/API acceptance.
