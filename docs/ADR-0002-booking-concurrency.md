# ADR-0002: PostgreSQL-backed non-overlapping booking invariant

Status: Accepted for MVP

- Store `starts_at`/`ends_at` as `timestamptz` with `starts_at < ends_at`.
- Bookings for the **same activity** with status `confirmed` must never overlap.
- Enforce in DB with GiST exclusion constraint, not an application `SELECT` alone:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE bookings ADD CONSTRAINT no_overlap_confirmed
  EXCLUDE USING gist (
    activity_id WITH =,
    tstzrange(starts_at, ends_at, '[)') WITH &&
  ) WHERE (status = 'confirmed');
```

- Treat constraint violation as HTTP 409. Open interval boundaries `[)` allow back-to-back sessions.
- Validate activity status, weekly windows, blocked days, notice and booking horizon in server code.
- Test with multiple simultaneous transactions; a sequential unit test cannot prove race safety.
- This is a design example; backend agent must adapt the migration to its actual schema.

## Verification requirements

- For two simultaneous requests with **distinct booking-attempt identifiers** for the same
  available slot, exactly one returns HTTP 201 and one HTTP 409 slot_unavailable; only one
  confirmed booking is stored. The original unqualified example applies to competing attempts,
  not identical retries; see the approved-design supplement below.
- Back-to-back intervals are permitted; overlapping confirmed intervals are rejected.
- Availability is revalidated inside the transaction, and the server derives the end from
  activity duration. Tests must use PostgreSQL and simultaneous requests or transactions.

These details are retained from the constitution review and existing PRD/architecture/task
requirements; no new implementation or human approval is asserted by this documentation move.

## Approved-design supplement — 2026-10-25

This is documentation alignment with the human-approved plan at
`5f1ce85bc16b25541337b5ef55d6f25d7b3a574d` and amendments A-001/A-002/A-003. The Accepted for MVP
status, same-activity scope, original rationale, SQL example and half-open exclusion decision are
unchanged. No original acceptance date/approver or completed runtime evidence is inferred.

Matching simultaneous retries use the same private identifier and original details. They converge
on at most one booking and its current status/result, or verified unfinished state, rather than
forcing one retry to lose with slot_unavailable. New committed success is 201; completed-success
replay is 200. A canceled booking is never recreated, and terminal rejection remains final.
Different identifiers remain competitors subject to the original one-201/one-409 example.

Provisionally approved T-02 uses short durable admission then separate execution. A-002 persists
DB-generated wall-clock T and E=T+24h with the binding; only successful commit makes admission
valid. T is not PostgreSQL commit metadata. Delays consume the fixed window, rollback admits
nothing through that transaction, and uncertain COMMIT stays unverified. No booking/result
confirmation precedes known commit. This refines retry handling without replacing DB exclusion.

Use READ COMMITTED and consistent lock order: attempt → activity → booking → contact.
Execution locks attempt NOWAIT then activity; configuration/cancellation share the activity lock.
Configuration never acquires an earlier attempt lock; cancellation begins with activity before
booking/contact. Refresh configuration and sample fresh database wall-clock time after waits;
transaction-start now() cannot enforce moving expiry/notice/auth boundaries. The activity lock
prevents rule changes racing booking eligibility; GiST independently prevents overlap even if a
writer bypasses application locking. No cross-activity/host-wide exclusion is added.

Catch only the named exclusion violation (23P01) within the insertion savepoint and record a safe
terminal rejection. NOWAIT/lock-timeout/deadlock failures require whole-transaction rollback before
fresh committed-state classification, not catch-and-continue or conversion into slot_unavailable.
202 requires committed matching unexpired unfinished admission; mismatch is generic 409, normal
chronological expiry 410, unverified admission/execution phase-specific 503. Only separately
approved unrecoverable A-003 recovery may invalidate old generations with distinct 409
attempt_invalidated_by_restore; normal restart preserves valid retry state.

Revalidate A-001 activity-local quarter-hour starts, continuous single-window fit, IANA/DST rules,
blocks and inclusive 1h/1440h start bounds in execution. Preserve existing booked intervals/status
through rule edits; repeated cancellation is a successful no-op preserving its original timestamp.

PostgreSQL simultaneous-transaction tests, lock ordering/config races, crash/timeout/unknown-commit
recovery and the seventeen cases in the approved feature retry protocol remain mandatory. T-02
is still provisional; a passing /health scaffold test or schema fixture cannot satisfy it.
This supplement records the already approved design, not a new exclusion strategy or permission
to implement. A future change of invariant, isolation or retry guarantees requires renewed review.
