# Proposed booking admission and retry protocol

Status: R-003 technical-plan baseline formally approved on 2026-10-25.
Policy amendments [A-002](../amendments/A-002-durable-admission.md)
and [A-003](../amendments/A-003-disaster-recovery.md) are explicitly approved; T-02 split execution
is provisionally approved subject to runtime verification. T-01/T-04 are approved, T-03 conditional.
The reconciled specification has 77 scenarios. This document is not implemented or runtime-verified
and grants no task/implementation authorization.

## Minimal architecture and invariants

Keep PostgreSQL, synchronous SQLAlchemy, one short admission transaction, then one execution
transaction. The admission unique key serializes first-writer selection; an execution row lock
serializes completion. Use no broker, distributed lock, ownership lease, persistent execution queue
or asynchronous booking job. A 202 means unfinished admitted work, not a promise a worker is running.
The next explicit matching POST can acquire execution ownership and finish it.

- The private key contains current public generation plus 256 random bits; store only its HMAC.
- Immutable binding uses versioned canonical activity UUID, normalized UTC start and exact name/email.
  Invalid JSON/type inputs bind a versioned raw-body digest, never the raw bytes themselves.
- Terminal rejection is replayed; success returns the same booking identity and its current status.
- Chronological expiry is checked before binding/result disclosure. Changed details cannot expose
  the prior result, booking identity, contact values, or original fields.
- No booking execution starts on an uncommitted or unverified admission. No response confirms a
  booking until its booking/contact/result transaction is known committed.
- Configuration/booking/cancel share the same activity lock. The exclusion constraint independently
  protects confirmed intervals; adjacent intervals remain allowed. A-001 and DST policies are unchanged.

## Persisted admission timestamp and durability (approved A-002)

The admission transaction stores a database-generated T and immutable E=T+24 elapsed hours with
its original binding. Only successful durable commit makes the attempt valid. T is the persisted
clock sample, NOT the actual commit instant, HTTP arrival/response time, or a later retry time.
No transaction-XID field, nullable receipt-resolution stage, resolver, worker sealing, commit-time
tracking setting or post-commit timestamp lookup is needed.

Claim the unique key and prepare binding, then sample clock_timestamp() late in the newly created
admission transaction as a final stamping write before COMMIT. Derive T/E from the same sample;
use UTC elapsed arithmetic. This final write may replace provisional values only in this caller's
newly inserted, uncommitted row; it must never update an existing committed attempt after conflict.
No provisional/uncommitted timestamp is returned as evidence of admission. This ordering avoids
using a timestamp sampled before a long unique-key wait when the competing insert rolls back.

Let C be actual commit time. Commit delay consumes validity: remaining window at C is
max(0,E-C). Never extend E to C+24h or to retry time. If C>=E, the committed identifier is already
expired: preserve its tombstone and return 410, with no execution, ordinary pending or result
access. Before proceeding, reread committed T/E and check fresh DB wall-clock time after waits.

Require fsync=on, synchronous_commit=on for admission/execution, durable volumes and UTC sessions.
Bound lock/statement waits and application request/transaction budgets; keep admission short and
perform no external I/O while holding locks. Actual COMMIT delay cannot be guaranteed by these
budgets. A COMMIT timeout/disconnection may be an unknown commit, not a proved rollback. Fresh
committed-state recovery is mandatory; no client/database acknowledgement time substitutes for T.
Admission rollback leaves no valid attempt through that transaction. Missing/corrupt T/E on a
committed record fails closed; it must not be repaired by silently generating a later timestamp.

Runtime tests must verify final stamping after contention, delayed/late COMMIT, lost ACK, crash
recovery and identical original T/E across normal restart. No such tests have been run now.
[Database wall-clock semantics](https://www.postgresql.org/docs/16/functions-datetime.html),
[durable commit settings](https://www.postgresql.org/docs/16/runtime-config-wal.html).

## A — Admission and admission contention

1. Validate private-key syntax/generation without exposing data. A noncurrent generation after
   the separately approved restore transition is 409 attempt_invalidated_by_restore (A-003); a missing or
   malformed key is 400 validation_failed. Routine missing generation/secret state fails readiness.
2. In a short transaction with bounded waits, claim a new attempt + binding using unique
   (generation, key_digest) and conflict-do-nothing. If inserted by this caller, stamp final
   database T/E late as above and commit them atomically with the binding. Terminal malformed-input
   rejection may be stored too. Never update an existing committed winner's binding or timestamp.
3. COMMIT admission before booking execution. Recheck the committed T/E and current wall-clock
   time; delayed commit may have consumed/ended the window. If a winner already exists, end
   the no-op transaction and inspect its committed state, never the contender's provisional T.
4. If admission wait times out, rolls back, or COMMIT outcome is uncertain, discard/roll back the
   entire admission transaction. Open a fresh READ COMMITTED transaction to inspect the ledger.
   Do not query through an aborted SQLAlchemy session/transaction.
5. Classify any visible committed row using C below. In admission contention, a committed matching
   unexpired unfinished row can return 202; a terminal row returns its recorded result, a mismatch
   returns 409, expiry returns 410. If no committed row or receipt proof is available, return
   503 admission_unverified, with no admission/expiry/confirmation claim. An uncommitted competing
   insert is not evidence for pending. An inability to query likewise returns unverified failure.

A verified rollback means this admission transaction admitted nothing and did not execute a booking;
it does not prove no parallel request ever committed. If no row ever committed, a later explicit
same-key POST can create the first admission, using its final persisted database timestamp (A-002).
No client or infrastructure retry policy automatically substitutes a new private key.

## B — Execution, completion and execution contention

1. Begin a new execution transaction and acquire the attempt row using `FOR UPDATE NOWAIT`.
   If busy, roll back the whole execution transaction and use a fresh committed read under C.
   This avoids catch-and-continue on a failed lock statement and requires no execution lease.
2. Once locked, read original committed T/E without restamping, obtain fresh DB wall-clock time and
   classify under C. A terminal row is returned without new eligibility checks; its booking status
   is read from committed booking state. Never restart a canceled booking or reconsider a rejection.
3. For an admitted, matching, unexpired row, acquire the activity lock with a bounded wait, then
   refresh configuration/ORM state. Recheck expiry and evaluate eligibility with fresh
   `clock_timestamp()` after that wait: active activity, exact A-001 grid, continuous window fit,
   activity-local blocks, occupancy and inclusive notice/horizon. Derive end in UTC.
4. Inside a savepoint, create/flush booking and contact. Add these ORM objects only after entering
   the savepoint: SQLAlchemy can flush pending state when begin_nested() starts. Catch only the
   named exclusion violation (23P01) as slot_unavailable. Roll back that savepoint and record a
   durable terminal rejection in the outer transaction; unexpected errors are not slot conflicts.
5. Check current expiry before finalizing any new outcome after waits/work. If expired after
   tentative inserts, roll back the entire execution transaction before returning 410: no booking,
   contact or tentative result commits; committed admission remains for expiry rejection. Otherwise persist booking/contact
   and success, or the safe terminal rejection, in the same outer transaction. COMMIT durably.
   The decision point is the final DB eligibility/expiry check, not a promise about when the HTTP
   response arrives. A request evaluated at/after E cannot create a new outcome or retrieve a result.
6. Only after confirmed commit return 201 for this newly created booking. A later matching result
   is 200 with the same identity/current status. Rejection is definitive only once its result commits.

An activity-lock timeout, NOWAIT conflict, deadlock victim, or other pre-commit execution failure
rolls back the whole execution transaction, preserving committed admission. Reclassify on a fresh
connection. If the row is now final, return that final state; if valid/matching and unfinished,
202 is allowed; if expired/mismatched, return its dedicated error. Unknown DB/COMMIT state that
cannot be read is 503 execution_unverified, never confirmation or definite business rejection.
A lost COMMIT ACK may mean success committed; recover it rather than assume rollback.

Do not automatically rerun business execution after rollback in the same HTTP handler. The next
explicit same-key request acquires the row lock and can finish the admitted work. Normal crash
releases transactional locks; there is no durable owner flag that can strand a request.

## C — Fresh committed-state classification, including the pending guard

Use a fresh READ COMMITTED read joining attempt, binding and optional result with a fresh
DB wall-clock decision time. A committed snapshot cannot see a competing uncommitted insert.
Evaluate these outcomes in order; return no ordinary pending before these checks:

| Evidence | Response / mutation |
| --- | --- |
| A-003-qualified noncurrent generation | 409 attempt_invalidated_by_restore; no result, new attempt or expiry claim. |
| No provable committed row / persisted T/E unavailable or invalid / DB read unavailable | 503 admission_unverified or execution_unverified according to phase; no pending or success claim. |
| Persisted expired tombstone or current time >= E | 410 attempt_expired before binding/result access; never admit key anew. |
| Original binding missing/inconsistent before E | 503 execution_unverified; fail closed, not mismatch success or fresh admission. |
| Canonical submitted details differ from immutable binding | 409 attempt_mismatch, generic; no original values/result/identity. |
| Matching unexpired terminal rejected | Original safe status/code/field codes; no new booking. |
| Matching unexpired terminal succeeded | 200 BookingSummary/current status; no contacts or new booking. |
| Matching unexpired committed admitted row, no final result | Eligible for 202 ONLY on the contention/fallback path; otherwise the execution owner may proceed under B. |

For 202 specifically, recheck current DB time at the response decision after any lock timeout,
prove committed admission and persisted T/E, compare the binding and verify no visible final result.
Return AttemptPending + known E + Retry-After; expose no key/contact/booking ID. Its meaning is
“admitted but unfinished as of this read,” not “a background task will certainly finish.” A
concurrent transaction may commit just after that read; a subsequent explicit retry sees it.
Never queue fresh work, extend E, or make a different-payload request ordinary pending.

Chronological expiry and restore invalidation cannot reveal original payload/result data.
After expired-row cleanup, the tombstone still rejects that private identifier. Expired fingerprints
and result links are removed; generation/key digest/receipt/expiry remain non-authorizing state.

## Lock, timeout and worker rules

Global request order: attempt → activity → booking → contact. Binding belongs to its attempt.
Admission is short and never locks an activity. Cancellation skips attempt and starts with activity.
Configuration locks activity, then reads bookings without acquiring earlier-order attempt locks.
Generation changes occur only during an approved fenced/offline restore, never online rotation.

Workers process deterministic key order in small transactions. Attempt expiry locks attempt
then its binding and does not acquire activity/booking/contact locks. Contact deletion locks only
contact rows, rechecks the due predicate in the deletion transaction, and does not then lock parent
bookings/activities. Session cleanup is independent. Do not combine these jobs into one transaction
that reverses the global order. Rows skipped by SKIP LOCKED remain overdue until actually deleted.

Use `FOR UPDATE NOWAIT` for execution ownership and scoped bounded `lock_timeout` for admission/
activity waits. Values are deployment configuration; no new product SLA is implied. Catch 55P03
(lock unavailable/timeout) or 40P01 (deadlock) only after rolling back the entire failed transaction.
Do not map them to slot_unavailable, mismatch, or rejection. The only partial rollback retained
is the already-established savepoint for a known exclusion conflict. A savepoint-based timeout
recovery is possible but unnecessary here. Never perform a fresh classification inside an aborted
transaction. DB time is sampled again after every wait; transaction-start now() is insufficient.

References: [timeouts](https://www.postgresql.org/docs/16/runtime-config-client.html),
[locking order](https://www.postgresql.org/docs/16/explicit-locking.html),
[savepoints](https://www.postgresql.org/docs/16/sql-rollback-to.html),
[ORM flush behavior](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).

## State/schema and contract deltas proposed

Attempt has non-null first_received_at and expires_at, committed atomically with its immutable
binding; the latter stores the canonicalization version and payload fingerprint. A stable CHECK
verifies E=T+24 elapsed hours; no time-dependent CHECK is used. Add only safe rejection field
paths/codes for stable validation replay. T/E become immutable on commit; conflicts/retries never
restamp them. Remove previously proposed transaction identity, unresolved receipt fields and
post-commit processing machinery. No raw request/credential/contact copies are added.

A fenced restore gains privacy-safe recovery metadata (event/reference, restored-at, new generation,
old generation if known, snapshot reference, state-loss reason). It is not a guest lookup table.
The current generation and HMAC secrets survive normal restarts. For the MVP, no ordinary rotation
may invalidate current-generation retry recognition; missing configuration fails readiness.

Proposed errors: 503 admission_unverified, 503 execution_unverified, 409 attempt_mismatch,
410 attempt_expired, and (approved A-003) 409 attempt_invalidated_by_restore. X-Attempt-Expires-At is
returned only when original committed receipt/expiry are established; omit it for unverified
admission or lost restore state. A 202 requires it. Every final public success remains contact-free.
No new endpoint beyond the provisional context read; canonical TypeSpec is untouched.

## Runtime verification matrix (required by provisional T-02; not implemented tests)

| Case | Controlled trigger | Required assertion |
| --- | --- | --- |
| RP-01 admission rollback | Fail before admission COMMIT | No row/binding/booking from that transaction; no 202/confirmation; later explicit key can first-admit under A-002. |
| RP-02 delayed commit | Delay COMMIT after final DB T/E stamping | Persisted T/E remain fixed, not commit/ACK metadata; remaining window shrinks by delay. If commit occurs at/after E, 410 and no booking/pending; no clock reset. |
| RP-03 admission ACK lost | Commit admission then drop connection | Same original T/binding; no second admission/window reset on retry. |
| RP-04 concurrent admission rollback | Hold unique-key conflict, then roll back winner | Fresh read with no committed row cannot return pending; 503 or later first-admission as applicable. |
| RP-05 concurrent admission commit | Hold unique conflict then commit winner | Fresh classification yields 409 for changed details, 410 if expired, 202 only for matching valid unfinished row. |
| RP-06 execution contention | Hold attempt row past NOWAIT failure | Failed transaction fully rolled back; fresh read applies C, with no original data leak. |
| RP-07 activity wait crosses E | Hold activity until receipt window expires | Fresh expiry check returns 410; no new booking, ordinary pending or window extension. |
| RP-08 execution crash | Stop after admission, or after tentative booking insert before COMMIT | No partial booking/contact/result commit; next matching retry can execute once before E. |
| RP-09 execution ACK lost | Commit booking/contact/result then drop response | Same booking ID/current status on retry, even after config edit/cancel; no contacts/duplication. |
| RP-10 matching vs distinct keys | Independent connections and barriers | Matching keys converge to one booking; different overlapping keys yield one 201/one 409. |
| RP-11 deadlock/timeout | Inject controlled SQLSTATE/real lock wait | Whole execution rollback, admission preserved, correct fresh classification; no false success/rejection. |
| RP-12 exact E / mismatch | Just before/equal/after E; changed fields | Before E matching follows state; at/after E 410; unexpired changed fields 409, never ordinary pending. |
| RP-13 normal restart | Restart API/DB/worker using durable volume/secrets | Same generation/T/binding/result/tombstone; no A-003 invalidation. |
| RP-14 approved restore | Restore older contact-free snapshot and fence old writer | Old unexpired/missing-snapshot keys get distinct restore invalidation, not new admission or chronological-expiry claims. |
| RP-15 invalid persisted receipt | Corrupt/remove T/E in an isolated failure fixture | Fail closed, operator failure visible; no generated replacement T, ordinary pending or confirmation. No commit-metadata dependency exists. |
| RP-16 privacy/headers | Inspect error/pending/result/backup/log artifacts | No raw key/contact/binding values exposed; expiry header only when known; client never auto-replaces key. |
| RP-17 late unique-key winner | Contender waits, original insert rolls back | New winner stamps final T after contention, commits T/E/binding atomically; no provisional pre-wait timestamp used or prior committed winner restamped. |

Use PostgreSQL for persisted timestamp/durability/locking/exclusion and HTTPX for independent concurrent requests.
Use unit-controlled clock cases plus isolated DB boundary fixtures; do not expose test-clock APIs.
Playwright verifies unknown/pending/expired/restore-invalidated guidance and explicit retries.
These seventeen technical verification cases supplement the reconciled 77 approved acceptance
scenarios. A-002/A-003 policy cases are now integrated into spec.md; no runtime test is claimed
as executed, and no implementation tasks are generated.
