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

- For two simultaneous requests for the same available slot, exactly one returns HTTP 201
  and one returns HTTP 409; only one confirmed booking is stored.
- Back-to-back intervals are permitted; overlapping confirmed intervals are rejected.
- Availability is revalidated inside the transaction, and the server derives the end from
  activity duration. Tests must use PostgreSQL and simultaneous requests or transactions.

These details are retained from the constitution review and existing PRD/architecture/task
requirements; no new implementation or human approval is asserted by this documentation move.
