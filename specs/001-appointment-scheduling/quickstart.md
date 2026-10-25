# SlotBook MVP validation quickstart

Status: validation design approved as part of the R-003 technical plan, 2026-10-25. Baseline:
`e9f16809058fe826523bf8c19387b6ba65b8e145`, branch `001-appointment-scheduling`.
This guide describes the completed implementation to be built only after approval. Its revised
receipt/recovery checks now reflect approved A-002/A-003 with the persisted DB timestamp
clarification. The approved acceptance suite is now 77 scenarios; T-02 runtime verification
is still pending and T-03 backup/hosting acceptance remains conditional. Today's
scaffold does not provide migrations, seeds, retention worker, booking/auth routes, these CLI
modules, dependency locks, or E2E runner. Commands below are future acceptance interfaces, not
claims that they currently run. No application validation was performed during planning.

Prerequisites: Docker Compose v2 with a running engine; Git; Node 22/npm for contract/frontend
checks; Python 3.12 for optional host checks. Use synthetic names/emails and development-only
credentials from untracked environment configuration. Expected data/transactions:
[data-model.md](data-model.md); exact HTTP proposal: [contracts/api-proposal.md](contracts/api-proposal.md).
Detailed proposed contention/crash verification: [retry-protocol.md](contracts/retry-protocol.md).
Product grid boundary P-01 is resolved by approved [amendment A-001](amendments/A-001-clock-aligned-starts.md):
starts use activity-local 00/15/30/45 with zero seconds/fractions. Technical-plan approval is recorded in
[technical-review.md](checklists/technical-review.md);
implementation and execution of the future validation interfaces remain separately gated.

## Verify the approved integration inputs

```sh
git branch --show-current
git rev-parse HEAD
git status --short
```

At planning input these must identify `001-appointment-scheduling`, the approved baseline hash
above, and a clean tree. For later implementation use the separately reviewed contract/design
commit, recorded in every handoff; do not assert this input hash contains features.

## Reproducible generation and static checks (after lockfiles exist)

From the repository root:

```sh
npm --prefix contracts ci
npm --prefix contracts run build
npm --prefix frontend ci
npm --prefix frontend run generate:api
npm --prefix frontend run build
git diff --exit-code -- contracts/tsp-output frontend/src/api/schema.d.ts
```

Expected: canonical TypeSpec compiles, generated OpenAPI/TS match the frozen checked-in artifacts,
and frontend type/build succeeds. The generation commands exist today; lockfiles, generated
baseline and feature behavior are later deliverables. A drift failure requires a reviewed source
change/regeneration, not hand-editing derived files. Pin Python dependencies and tools similarly.

## Start the completed development stack

```sh
cp .env.example .env
# Configure synthetic development admin credentials and runtime-only secrets in .env.
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 migrate seed retention
```

Expected future service names: db, migrate, seed, backend, retention, frontend. The proposed
A-002 design requires fsync and admission/execution synchronous_commit enabled, UTC sessions
and durable volumes. It uses ordinary persisted DB timestamps, with no commit metadata dependency. Migration and
seed exit zero; DB/API/retention readiness is healthy. Current scaffold only has db/backend/
frontend. `.env` remains untracked. DB is internal by default, not exposed to the public host.
Safe logs contain service state/counts only, never credentials/contact payloads/attempt headers.
Repeated startup must not reset bookings/passwords or create duplicate seed data.

```sh
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/ready
curl --fail http://localhost:8000/api/activities
```

Expected: shallow liveness, dependency/schema/worker readiness, and active synthetic catalog
with full mandatory descriptions. `/ready` is a proposed operational endpoint, not present today.
Visit `http://localhost:5173`; API documentation remains at `http://localhost:8000/docs`.
A seeded activity has a known IANA timezone and ordinary valid windows; tests choose future
eligible dates using a controlled clock, rather than baking a soon-stale live appointment date.

## Automated verification (future tests and CLI commands)

The implementation must provide the named test directories, marker registration and scripts.
These commands run only against isolated development/test databases with synthetic data.
No command should silently fall back to SQLite or claim success when tests are absent.

```sh
docker compose exec backend python -m pytest tests/unit -q
docker compose exec backend python -m pytest tests/integration -q
docker compose exec backend python -m pytest tests/contract -q
docker compose exec backend alembic current
npm --prefix frontend run test
npm --prefix tests/e2e ci
npm --prefix tests/e2e exec -- playwright install --with-deps chromium
npm --prefix tests/e2e test
```

Expected: unit/date/validation tests; PostgreSQL migrations, auth, transactions, privacy and
concurrency tests; every operation/error/header checked against generated OpenAPI; frontend
utility/component tests and Playwright mobile/desktop flows. Record exact command, counts,
exit code and limitations. No network-time sleep is a substitute for an injected authoritative
clock when testing 24h/60m/720h boundaries. Browser fake time alone does not alter server time.
Backend integration fixtures provide the clock without exposing an unauthenticated test API.
Admission tests additionally inspect real committed T/E/binding in PostgreSQL and deliberately
delay COMMIT after the final timestamp write; prove E stays T+24h rather than C+24h, and that
commit at/after E cannot execute or return pending. A mocked clock alone cannot prove durability.

Proposed focused pytest selectors:

```sh
docker compose exec backend python -m pytest tests/integration -m concurrency -q
docker compose exec backend python -m pytest tests/integration -m privacy -q
docker compose exec backend python -m pytest tests/unit -m timezone -q
```

Expected concurrent requests use independent connections and a barrier. Distinct overlapping
keys produce one 201 and one 409 with one confirmed row; matching keys converge on one booking,
with no contact fields in results. Exact boundary tests prove inclusive notice/horizon and
exclusive session/retry expiry. No sequential-test result establishes race safety.

## Human-observable journeys

1. **Browse/select/book (P1):** Select a synthetic activity, read its complete description, choose
   a display-zone date and an eligible slot, provide a synthetic name/email, and submit. See one
   confirmation with booking reference/activity/UTC-derived local times and status. Empty schedule
   differs from retrieval failure. Invalid fields and stale slots have useful corrective feedback.
2. **Unknown outcome/retry (P1):** Test harness drops the response after server commit. UI shows
   unverified outcome and retains original private identifier/details. Explicit same-attempt retry
   returns the same ID/current status without name/email or another booking. Different details
   yield generic mismatch. At exactly 24h, retry fails expired; UI suggests host verification and
   does not silently submit a new attempt. Under approved A-002, HTTP arrival with known admission
   rollback claims no committed attempt; an uncertain COMMIT remains unverified. Delay admission
   COMMIT after DB timestamp stamping: T/E stay fixed and validity is consumed, not reset.
   At late commit C>=E expect 410, no booking or pending. Preserve original values on ACK loss. Force admission/execution
   contention, mismatched details, expiry and lock failure: only committed matching unexpired
   unfinished state may show 202. Fresh classification follows full rollback. Reload/lost memory
   uses the same cautious host route. RP-01–17 define the required, unexecuted crash/timeout cases.
3. **Admin configuration (P2):** Login with synthetic seeded credentials. Read/edit active and
   inactive activities/windows/blocks. Invalid/overlapping/overnight window replacement fails
   atomically. Existing bookings keep endpoints/status, with preservation warning on affected edits.
   A block affects only that activity's local date. At exactly 60m, protected actions fail and
   contacts clear/lock; after login only explicit reviewed resubmission occurs.
4. **Review/cancel (P2):** View a synthetic booking, cancel it, verify otherwise eligible availability
   returns. Repeat cancellation successfully; original canceledAt and contact deadline do not move.
   No guest cancellation control or public guest-contact lookup exists.
5. **Responsive/timezones (P3, mandatory):** Repeat journeys at 320 and 1280 CSS pixels. Change
   display timezone across a calendar-date boundary; selected UTC instant stays fixed. Vienna
   spring gap omits nonexistent starts; autumn repeat offers both offsets. A 02:15–02:45 repeated
   window does not admit a booking crossing its intervening excluded portion. Test Lord Howe
   non-hour transitions and a date with no valid real portion. For A-001, a 09:10–10:00 window
   with 30-minute duration offers exactly 09:15/09:30 when otherwise eligible; 09:10–09:40 offers
   none. Direct 09:10/09:25 or nonzero-second/fraction requests reject without rounding. Changing
   display zone never changes activity-local alignment; both eligible repeated offsets remain.

## Privacy/deletion/recovery verification

Use private test fixtures to set time at end/cancellation +720h. The retained history contains
only reference/activity/start/end/status/original canceledAt. Name/email are deleted by the worker;
all reads omit them even if the test makes physical deletion fail. Operator status reports overdue
rows/failure immediately, never declares deletion complete, and never grants a grace period.
Repeated cancellation/config changes/retries cannot extend retention or reintroduce contacts.

Proposed maintenance interfaces (not yet implemented):

```sh
docker compose exec backend python -m app.cli.retention_status
docker compose exec backend python -m app.cli.backup --output /tmp/slotbook-contact-free.backup
```

Expected: privacy-safe worker/overdue status and a backup produced under the restricted allowlist
role. It contains configuration and permitted history only, no private contact/attempt/session
rows, original submissions, retry keys, bearer tokens, or contact-bearing logs. Never back up the
Compose database volume, enable WAL archival, or rely on encryption to make contact data absent.

Restore verification is automated by `pytest -m privacy` into a separately provisioned, empty
test database. The planned `app.cli.restore` entry point must take its dedicated test target
from untracked runtime configuration and fail closed on a nonempty/unapproved target. This
planning guide does not execute a restore or authorize a destructive database operation.
Expected recovery: schema constraints work, contacts are removed even before former deadlines,
new admin provisioning is explicit and sessions are invalid. Under approved A-003, a
separately approved unrecoverable restore records its event/snapshot, fences old writers and
changes generation. Every old identifier (including unexpired/missing-snapshot ones) returns
409 attempt_invalidated_by_restore, not chronological 410. UI requires host verification, not
automatic replacement. Normal restart/transient outage preserves generation/T/binding/results;
missing routine secrets/metadata fails readiness and never silently rotates the generation.
Inspect restored rows and backup contents using synthetic marker scans; a binary string search
alone is insufficient to validate a compressed/custom backup.

## CI and evidence

GitHub Actions should run generation/no-diff, type/build/unit, PostgreSQL contract/race/privacy,
and Compose Playwright checks. Publish only allowlisted reports with synthetic/redacted values;
raw HTTP traces/HAR/video/storage dumps on sensitive flows are disabled. All required checks
pass before a separately approved merge. No deployment workflow is introduced by this plan.

A complete handoff states files/scope, exact approved spec and contract commit, commands and
actual outcomes, unresolved limits, and contract/migration flags. A green scaffold health test
or 16/16 requirements checklist is never presented as product verification.
