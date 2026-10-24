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
