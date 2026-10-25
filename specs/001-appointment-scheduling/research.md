# SlotBook MVP technical research

Date: 2026-10-25. Status: part of the formally approved R-003 technical-plan baseline;
A-001/A-002/A-003 and T-01/T-04 approved, T-02 provisional and T-03 conditional.
Other design rationale is not a claim of runtime proof or an approved ADR.
Baseline: `e9f16809058fe826523bf8c19387b6ba65b8e145`, branch
`001-appointment-scheduling`, constitution 1.2.0. Research was performed directly by the
planning agent; no research or implementation subagents were launched.

Policy note: baseline + A-001 is now explicitly amended by clarified A-002/A-003. Historical
fifteen answers are preserved; current receipt/recovery policy is reconciled below and in the
[full protocol](contracts/retry-protocol.md). No broader implementation approval is inferred.

## R-01 — One API and one database

**Decision:** Keep a modular FastAPI application, React/Vite client, PostgreSQL 16, synchronous
SQLAlchemy 2 sessions with psycopg 3, and Alembic. Use ordinary synchronous request handlers for
DB work. One session per request/worker transaction; never share sessions across threads.
A separate retention-worker process uses the same backend image and database. No Redis,
message broker, microservices, generic repository framework, or external scheduling service.

**Rationale:** The single-admin MVP needs transactions and a small number of cohesive services,
not distributed orchestration. All chosen frameworks are already in the agreed stack. Keep
Python 3.12 and Node 22 from existing Dockerfiles, TypeSpec packages at existing 1.17.0, and
OpenAPI 3.0 until an independently reviewed upgrade is needed. Exact Python/npm dependency
locks and image digests are implementation deliverables, not researched claims of latest versions.

**Alternatives:** Async SQLAlchemy adds lifecycle complexity without an established throughput
need. SQLite cannot verify PostgreSQL exclusion or locking behavior. An in-process background
thread alone would couple mandatory deletion to API uptime and replica count.

## R-02 — Database integrity plus conservative serialization

**Decision:** Preserve ADR-0002's partial GiST exclusion constraint on activity ID and
`tstzrange(starts_at, ends_at, '[)')` for confirmed bookings. Use READ COMMITTED transactions.
Take an exclusive activity-row lock for new booking decisions, configuration changes, and
cancellation. Lock ordering is attempt, activity, booking, contact. Re-read rules and capture
fresh database wall-clock time after waiting for locks. A savepoint contains an insertion that
may violate exclusion; the outer transaction records the attempt's terminal rejection.

**Rationale:** Activity serialization is deliberately conservative and easy to audit. The
constraint remains the final invariant even if another writer bypasses service locking.
Configuration cannot change eligibility between validation and commit. Back-to-back intervals
remain legal. PostgreSQL documents range exclusions and row locks; SQLAlchemy documents
savepoints that preserve an outer transaction after an integrity error.
[Ranges](https://www.postgresql.org/docs/16/rangetypes.html),
[row locks](https://www.postgresql.org/docs/16/explicit-locking.html),
[SQLAlchemy savepoints](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).

**Alternatives:** SELECT-before-INSERT alone races. SERIALIZABLE still needs retries and the
exclusion constraint. Shared activity locks could allow more parallel bookings but complicate
configuration/cancellation ordering. Coarse per-activity serialization can be revisited after
measurement; it introduces no new host-wide exclusion.

## R-03 — Persisted database receipt and provisionally approved split admission

**Approved policy:** [A-002](amendments/A-002-durable-admission.md) uses a database-generated
T persisted with binding/E in a successfully committed admission transaction. E=T+24 elapsed
hours, immutable thereafter. T is a clock sample within the transaction, not the commit instant,
HTTP/ACK time or PostgreSQL commit metadata. Known rollback admits nothing; uncertain COMMIT
remains unverified. Sample T late, after contention/binding preparation, and check current time
again after commit or waits. Delayed commit consumes validity, possibly leaving an expired key
at commit; never reset E to commit+24h. Bound admission budgets without pretending a timeout
proves COMMIT rolled back. [DB clock semantics](https://www.postgresql.org/docs/16/functions-datetime.html),
[durable commit](https://www.postgresql.org/docs/16/runtime-config-wal.html).

**T-02 provisionally approved:** Keep one short admission transaction then one locked execution
transaction. This preserves original T/binding across execution rollback; execution commits
booking/contact/result atomically. Remove proposed transaction identity/receipt-resolution fields,
post-commit resolver, metadata retention/worker sealing and tracking configuration. The earlier
exact commit-metadata approach was never approved as written and was explicitly superseded.

**Alternatives:** One transaction is simpler but execution rollback also loses admission T/binding.
The approved persisted-clock-sample approach is simpler than exact commit-event reconstruction,
with the explicit tradeoff that delayed commit consumes some validity. A broker/lease or extra
pre-registration endpoint is unnecessary. Runtime proof of delay, restart, ACK loss and lock
handling remains required; no experiment or test is claimed here.

**A-003 approved:** Keep generation/random identifiers and non-authorizing tombstones. Only a
separately approved unrecoverable disaster restore may retire old generation with writer fencing;
return 409 attempt_invalidated_by_restore, including for old unexpired keys. Normal restart,
transient failure and routine rotation preserve valid retry state; missing normal startup state
fails readiness. Contact-free retry-state archives are an alternative needing separate binding/
privacy/snapshot design; MVP accepts only the explicitly qualified recovery-state loss. Never
infer a booking failed or automatically replace an uncertain old identifier.

## R-04 — Explicit retry with a guarded pending response

**Provisionally approved T-02 design:** Use the same booking POST/key/details. Admission contention uses a scoped
bounded timeout; execution ownership uses FOR UPDATE NOWAIT. On either failed lock transaction,
roll back the whole transaction and classify on a fresh committed read. 202 requires committed,
matching, unexpired, timestamp-verified unfinished committed admission. Mismatch is generic 409, current-key
chronological expiry is 410, and unverified admission/execution is 503 with explicit phase codes.
No confirmation before known booking/result commit, no automatic new-key replacement, no
background completion promise and no broker/lease. A later explicit retry can finish admitted work.

**Rationale:** A generic timeout-to-pending shortcut can misclassify changed/expired or not-yet-
committed requests. The complete [protocol and seventeen runtime verification cases](contracts/retry-protocol.md)
cover admission/execution crash boundaries, lost acknowledgements, lock rollback and post-wait
wall-clock checks. An exclusion savepoint remains useful for a definite terminal slot conflict;
using another nested transaction solely for lock-timeout recovery is unnecessary complexity.
[PostgreSQL timeout behavior](https://www.postgresql.org/docs/16/runtime-config-client.html).

**Alternatives:** Returning 503 for every contention is simpler but loses useful verified pending
feedback. Catching a timeout and continuing through an aborted transaction is invalid. Waiting
indefinitely holds resources. A key-only recovery GET adds an avoidable lookup surface; keep
matching-details POST and contact-free success responses.

## R-05 — Opaque, memory-only administrator bearer session

**Decision:** Retain the contracted bearer mechanism. Login creates a 256-bit opaque token;
store only its SHA-256 verifier with admin ID and database-issued login/expiry instants.
React holds the raw token in memory only, with no localStorage, sessionStorage, IndexedDB,
URL, persisted state, or browser cache. Server checks `authorization_time < expires_at`, exactly
60 elapsed minutes from login, without idle extension or refresh. No JWT is needed; the scaffold's
PyJWT dependency can be removed later. Argon2 password hashing uses existing pwdlib support.

**Rationale:** This avoids introducing cookie authentication or a refresh flow into the existing
bearer contract. Reloading the page requires login again, an intentional technical storage
tradeoff for review. Memory storage reduces persistence, but XSS can still steal a live token;
plain-text rendering, restrictive CSP, TLS, and dependency review remain necessary. OWASP
recommends server-side expiry, avoiding web-storage credentials, and no-store responses.
[Session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

**Alternatives:** HttpOnly/Secure/SameSite cookies better isolate tokens from JavaScript but
would change the existing authentication mechanism and require a CSRF design. JWTs do not
remove the need for server-enforced policy and reliable expiry. Persisting a bearer in web
storage is rejected. No additional idle timeout overrides the approved fixed-session policy.

## R-06 — Contact isolation and logical, contact-free recovery

**Decision:** Move live name/email into a private `booking_contacts` table; retained bookings
contain only the approved history fields. Private tables also hold attempts, binding digests,
and sessions. Backups are a reviewed logical allowlist of configuration and contact-free history,
never a whole database/volume/WAL snapshot. Under approved A-003, a separately approved restore
uses migrations, allowed data, fresh admin provisioning, recovery-event metadata and a new retry
generation after fencing old writers; contacts/sessions/attempts remain empty. T-03 is
conditionally approved: enforce the documented hosting/privacy/recovery restrictions and verify
them before public use; no actual restore or deployment is authorized.

**Rationale:** A nullable-field filter applied after a full dump is too late: the backup has
already received the data. A dedicated backup role lacks private-table SELECT; the backup tool
uses a positive table/column allowlist and consistent snapshot. pg_dump table selection does not
project individual columns: the simplest proposal validates the exact allowed table column sets
and fails closed on schema drift before dumping; an explicit-column snapshot exporter is the
alternative. Both require inspection of restored data, not just a compressed byte scan. A new table is not included by
default. PostgreSQL supports selecting tables for logical dumps; policy still requires inspection
of the resulting artifact, not trust in a filename or exclude pattern.
[pg_dump options](https://www.postgresql.org/docs/16/app-pgdump.html).

The worker targets each exact deadline, deletes due contacts transactionally, and catches up on
startup. Independent serializers suppress contacts at `now >= deadline` even if deletion fails.
Any overdue undeleted row is an operational failure immediately; there is no approved polling
grace period. Physical deletion cannot be guaranteed while the DB/worker is unavailable. Tests
and operator status must report this honestly, while reads fail closed. SQL deletion is logical
row deletion, not a promise of forensic disk erasure. Physical snapshots, WAL archiving, managed
provider backups, and persistent crash dumps containing contacts are disallowed for this design.
If a future host requires them, change the storage/recovery design and reopen approval first.

**Alternatives:** Whole-volume backups violate the approved policy even if encrypted. UNLOGGED
contacts still appear in logical dumps unless explicitly excluded and introduce crash-loss behavior;
use ordinary private tables plus explicit backup controls. Envelope encryption with separate
key destruction adds key lifecycle complexity and still needs a reviewed backup interpretation.

## R-07 — UTC arithmetic, IANA window membership

**Decision:** Use Python `zoneinfo` with a pinned `tzdata` package as the server's explicit data
source. Perform elapsed arithmetic/comparison in UTC. Convert local labels with both fold values
and UTC round trips: zero matching instants means nonexistent, two distinct matches means repeated.
Define real window portions by the approved local-date/clock membership predicate, not by
attaching a timezone to two endpoints. Keep each window separate.

**Rationale:** ZoneInfo supports IANA data and fold distinctions; constructing a local datetime
alone does not validate an imaginary time. No new timezone library is necessary.
[ZoneInfo](https://docs.python.org/3.12/library/zoneinfo.html).

For a simple correctness-first portion builder, partition the finite UTC search envelope at
integer UTC seconds and valid UTC preimages of both local window boundaries (including any
fractional seconds). TZif transitions are at integer seconds. Membership is constant inside
each resulting open cell; evaluate it and coalesce adjacent valid cells only within the same
window. This avoids private ZoneInfo internals or assuming transitions are one hour or aligned
to minutes. Cache only these contact-free portions by timezone-data version/date/window revision.
Do not cache notice, occupancy, or permission decisions. A faster transition iterator is optional
only after equivalence tests and measurement; no new latency guarantee is introduced.
[TZif format](https://www.rfc-editor.org/rfc/rfc9636.html).

**Alternatives:** Fixed offsets, shifting missing times, checking only start/end labels, or
joining touching windows contradict approved requirements. Minute sampling alone can miss
transition/boundary details. A custom TZif/POSIX-tail parser is unnecessary for the MVP.

## R-08 — Display-date query belongs on the server

**Decision:** Add optional `displayTimezone` to the existing slots query. When absent, date
retains activity-local meaning. When present, generate eligibility from activity-local windows
and blocks across every relevant activity date, then group/deduplicate by UTC start whose
converted display-local date equals the query. Return UTC starts/ends; client formats using Intl.
A missing, repeated, or unusually long local date is handled by date membership, not by adding
24 hours to a guessed midnight. This is G-008's proposed reconciliation.

**Alternatives:** Client fan-out over activity dates can work but duplicates date-coverage logic
in clients and complicates error/empty-state handling. A UTC-only date parameter conflicts with
visitor-date policy. The server remains eligibility authority if browser and server tzdata differ;
fixtures verify actual supported browser rendering and the selected server tzdata version.

## R-09 — Explicit validation/error schema and generated artifacts

**Decision:** Define concrete typed error responses in TypeSpec, including field paths and
stable codes without submitted values. Map FastAPI request-validation failures to contracted 400
responses instead of leaking default 422 bodies. Preserve UTC API instants and 204 cancellation.
Keep generated OpenAPI and `schema.d.ts` committed after approval; CI regenerates and checks drift.
Use a small fetch wrapper typed from generated operations, not parallel handwritten DTOs.

**Rationale:** TypeSpec supports named headers, status codes, and response models; generated
TypeScript declarations do not themselves validate JSON at runtime. QA validates real HTTP
responses against generated OpenAPI with a pinned schema validator (proposed `jsonschema`
plus YAML loading), including error paths. FastAPI supports custom validation handlers.
[TypeSpec operations](https://typespec.io/docs/libraries/http/operations/),
[FastAPI errors](https://fastapi.tiangolo.com/tutorial/handling-errors/),
[generated types](https://openapi-ts.dev/introduction).

**Alternatives:** FastAPI's generated OpenAPI as source would reverse ADR-0001. Framework defaults
are insufficient because undeclared statuses/errors would reach clients. No separate full client
code generator is needed for this small REST API.

## R-10 — Reproducible lifecycle and independent verification

**Design:** Compose validates durability/UTC/storage settings, then orders healthy DB →
one-shot migration → development seed → API and
retention worker → frontend. Optional test services use an isolated test database. CI has
contract drift/static checks, PostgreSQL integration/concurrency/privacy checks, then Compose
Playwright journeys. Use explicit seed commands gated to development/test; seed reruns never
reset existing bookings or silently rotate passwords.

**Rationale:** Compose supports health and successful-completion dependencies. GitHub Actions
supports PostgreSQL service containers. Playwright supports API setup and post-condition checks
alongside browser flows. These are planned capabilities, absent from today's scaffold.
[Compose startup](https://docs.docker.com/compose/how-tos/startup-order/),
[Actions PostgreSQL](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers),
[Playwright API testing](https://playwright.dev/docs/api-testing).

**Alternatives:** Migrations in every API replica startup race. SQLite integration and sequential
requests do not establish PostgreSQL safety. E2E-only verification gives poor failure isolation.

## Research result and approved product amendment

The human formally approved these technical design decisions on 2026-10-25, retaining
T-02 runtime-verification and T-03 backup/hosting conditions; implementation remains unauthorized. P-01 was identified during planning and explicitly resolved
by the human project owner
on 2026-10-25 through [specification amendment A-001](amendments/A-001-clock-aligned-starts.md).

**Decision:** Starts align to activity-local clock minutes 00/15/30/45, with zero seconds/fractions.
A 09:10 opening first permits 09:15 if the full elapsed duration fits one continuous valid portion
of the unchanged window. Submit-time eligibility rejects off-grid instants without rounding.

**Rationale:** A stable clock grid preserves predictable appointment labels across windows and
keeps display-zone choice separate from activity-local scheduling. This is an explicitly approved
product amendment, not an agent-selected technical default.

**Alternative rejected by the human choice:** Window-relative starts such as 09:10/09:25. Rounding
bookings or extending windows is also excluded. Both otherwise eligible occurrences of repeated
aligned labels remain distinct with their UTC offsets; nonexistent labels remain absent. The
original fifteen answers remain historical evidence and all DST/continuous-window policies are
unchanged. A-002/A-003 now explicitly amend only receipt/recovery; current requirements reflect
the approved clarification. A-001 requires no database migration; private attempt and recovery
schema changes remain planned work. PRD/TypeSpec semantic reconciliation and runtime evidence
are still required. No product-policy question remains open; T-02/T-03 conditions remain unsatisfied.
