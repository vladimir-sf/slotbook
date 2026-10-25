# Implementation Plan: SlotBook Appointment Scheduling MVP

**Branch**: `001-appointment-scheduling` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Approved input baseline**: `e9f16809058fe826523bf8c19387b6ba65b8e145` (parent specification baseline verified on the
actual feature branch before planning). Constitution 1.2.0 and requirements checklist
16/16 were approved; fifteen clarification answers remain unchanged. The approved product
baseline includes approved [A-001](amendments/A-001-clock-aligned-starts.md), clarified
A-002 and A-003, with 77 acceptance scenarios.

**Status**: TECHNICAL PLAN APPROVED by the human project owner on 2026-10-25, establishing
the technical design baseline. Approval covers the R-003 package, including A-001/A-002/A-003
and T-01–T-04. T-02 remains provisionally approved pending PostgreSQL concurrency, crash, timeout
and idempotency verification; T-03 remains conditional on validated contact-free backup and
hosting controls. Neither condition is satisfied by this documentation approval.
**Approved plan revision**: Git blob `e8298a179a345ea9457c7f856bcc30358c2f64ca`; the approved
report and package revisions are preserved in [technical-review.md](checklists/technical-review.md).
The human separately authorizes approval-record finalization and a local documentation commit.
No tasks, implementation, canonical contract changes, pushes or agent launch are authorized.

## Summary

Build the approved five user journeys with React/TypeScript/Vite, a modular FastAPI API and
PostgreSQL. TypeSpec → OpenAPI → generated TypeScript remains the sole API definition chain.
Database exclusion prevents overlapping confirmed bookings per activity. Durable attempt
admission, locked execution, and contact-free responses provide safe 24-hour retries. Fixed
60-minute opaque admin sessions stay in browser memory. A dedicated backend worker deletes
contacts at 720-hour deadlines; independent read suppression and allowlisted contact-free
backups protect privacy. Availability uses pinned IANA rules and continuous real window portions.

The current repository implements only a React landing scaffold, API `/health`, and its test.
It has dependency manifests, Dockerfiles/Compose and generation commands, but no booking routes,
ORM/Alembic setup, auth, generated committed schema, Playwright suite, or GitHub Actions workflow.
Do not count foundation startup as any MVP journey passing.

Design details: [research.md](research.md), [data-model.md](data-model.md),
[API proposal](contracts/api-proposal.md), [retry protocol](contracts/retry-protocol.md),
[source reconciliation](contracts/source-reconciliation.md),
[quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12; TypeScript ~5.9; React 19/Vite 7; Node 22;
PostgreSQL 16; existing TypeSpec compiler/http/openapi3 1.17.0; OpenAPI 3.0.
These are baseline compatibility choices, not latest-version assertions. Exact dependency
locks/image digests will be reviewed during authorized infrastructure finalization.

**Primary Dependencies**: FastAPI, synchronous SQLAlchemy 2, Alembic, psycopg 3, Pydantic/email
validation, pwdlib Argon2; Python ZoneInfo with pinned tzdata; generated openapi-typescript
schema and a small typed fetch wrapper. Opaque sessions need no JWT library. Planned test
helpers: pytest, HTTPX, Playwright, JSON Schema/YAML validation. No runtime broker or cache server.

**Storage**: One PostgreSQL database with public configuration/history and separately permissioned
private contacts/attempts/session tables. One retention-worker process shares backend code/image.
Only logical allowlisted backups; no full-volume/WAL backups containing guest data.

**Testing**: Unit tests, real PostgreSQL integration/concurrency/privacy tests, generated-contract
checks, Playwright browser and API journeys at 320/1280 widths, Compose migration/startup/restore
checks. No application tests are executed as evidence for this documentation-only planning pass.

**Target Platform**: Linux containers; desktop/mobile web. Browser and server use IANA identifiers;
server is scheduling authority, browser formats the same UTC instant and shows repeated offsets.

**Project Type**: Existing frontend/backend web application, retained as a modular monolith.

**Performance Goals**: No new latency/load/availability SLA is introduced. Correctness and the
approved measurable SC-001–019 govern acceptance. Coarse per-activity locks and correctness-first
window-portion calculation are acceptable starting tradeoffs; measure before optimizing.

**Constraints**: One seeded administrator, per-activity non-overlap, no guest account/cancellation,
no payments/calendar synchronization/email sending/multi-tenancy/external integration. No hold or
notice grace period. No automatic POST replay, token refresh, contact-bearing backup, or retention
extension. P-01 is resolved: exact quarter-hour starts are anchored to the activity timezone,
not to window start or visitor display timezone. Approved A-002 uses a database-generated
timestamp T persisted with binding in a successful admission transaction; E=T+24h. Commit delay
consumes validity without resetting T/E. Approved A-003 permits only separately authorized
unrecoverable-restore invalidation, distinct from chronological expiry. No product policy
question remains open; T-02 runtime proof and T-03 operational conditions remain unsatisfied.

**Scale/Scope**: Five prioritized stories, 31 functional requirements, 19 success criteria,
77 acceptance scenarios (61 original + four A-001 + twelve A-002/A-003), twelve decision IDs
with fifteen original answers preserved as approval history and receipt/recovery amended explicitly.
No new scale target.

## Constitution Check

Gates were assessed before research and re-evaluated against this design after Phase 1.
“Pass” below means design compliance, not implemented/tested behavior; human plan approval is recorded separately above.

| Principle | Pre-research | Post-design evidence / result |
| --- | --- | --- |
| I Specification First | Original baseline and amendment history retained | Pass for documentation: A-002/A-003 explicitly approved and reconciled, twelve policy cases integrated (77 total). A-001/DST preserved; no inferred implementation authorization. |
| II Contract First | Canonical TypeSpec read; gaps reported | Pass for planning: proposals isolated under feature contracts/. Canonical/generation changes remain lead-owned and gated; no application may implement this Markdown as private API. |
| III Multi-Agent Development | No agents active or launched | Pass: ownership and worktree/common-baseline strategy below; human restriction overrides skill's research-agent dispatch. Shared ownership guide reconciled under approved T-04. |
| IV Test-Driven Verification | Requirements checklist 16/16, not test evidence | Pass for design: verification matrix and future exact commands specified. Documentation checks only performed now. |
| V Code Quality | Existing typed stack inspected | Pass: cohesive services, direct SQLAlchemy units of work, no unnecessary broker/framework abstractions. |
| VI Infrastructure | Existing Compose/DB inspected | Pass for design: migrations, seeds, worker, locked dependencies, CI and contact-free recovery described. |
| VII Security and Correctness | Invariants and privacy policy read | Conditional acceptance: persisted T/E replaces commit metadata, guarded pending/rollback protocol and A-003 distinct error documented; T-02 runtime verification and T-03 backup/hosting/privacy evidence remain required. |
| VIII Human Approval | Constitution/spec and explicit decisions recorded | Pass for scope: record A-002/A-003 and T-01–T-04 approval statuses exactly; runtime/hosting conditions remain open. Stop before tasks, canonical contract changes or implementation. |

There is no proposed constitutional exception. Source gaps must be reconciled before dependent
implementation. P-01 was resolved through explicit human approval, not waived by a document check.
A-002/A-003 product gates were explicitly approved, not waived. T-02 is provisional and T-03
conditional; no blanket implementation approval is inferred. Contract and implementation gates
remain closed. See [technical review checklist](checklists/technical-review.md).

## Project Structure

### Documentation for this feature

```text
specs/001-appointment-scheduling/
├── spec.md                           # approved baseline plus A-001/A-002/A-003
├── checklists/requirements.md         # reevaluated 16/16 for approved amendments
├── amendments/A-001-clock-aligned-starts.md  # approved historical amendment record
├── amendments/A-002-durable-admission.md  # approved product amendment
├── amendments/A-003-disaster-recovery.md  # approved product amendment
├── checklists/technical-review.md      # formal plan approval; retained verification conditions
├── plan.md                           # this approved technical design
├── research.md                       # decisions, alternatives and official references
├── data-model.md                      # proposed schema and transaction lifecycle
├── quickstart.md                      # future runnable validation guide
└── contracts/
    ├── retry-protocol.md              # conditional admission/timeout/crash protocol
    ├── api-proposal.md                # proposed HTTP shapes/errors; not canonical
    └── source-reconciliation.md       # exact source changes to review later
```

No feature tasks.md is generated in this phase.

### Source layout after separately approved implementation

```text
contracts/                            # lead: canonical TypeSpec and derived OpenAPI
frontend/
├── src/
│   ├── api/{schema.d.ts,client.ts}     # generated schema; typed fetch adapter
│   ├── features/{catalog,booking,admin}/
│   ├── components/
│   └── time/                         # UTC/Intl display and label tests
└── tests/                            # component/pure-utility checks with Playwright runner
backend/
├── app/
│   ├── main.py
│   ├── api/                          # route adapters/contracted exception mapping
│   ├── schemas/                      # Python validation matching canonical OpenAPI
│   ├── models/                       # SQLAlchemy mapped configuration/private tables
│   ├── services/                     # availability, booking, config, auth, retention
│   ├── db/                           # sessions/transaction and role setup
│   ├── workers/retention.py
│   └── cli/                          # explicit seed, readiness, safe backup/restore tooling
├── migrations/                       # Alembic revisions
└── tests/{unit,integration,contract}/
tests/e2e/                            # QA: Playwright flows and API post-conditions
.github/workflows/                    # QA: contract/build/PostgreSQL/E2E jobs
scripts/                              # lead coordinates shared verification entry points
```

**Structure Decision:** Extend the existing two application directories. Route adapters map
HTTP/auth/validation, services own transactions and pure policy functions, models own durable
invariants. Do not add a separate repository interface per table or a separate worker codebase.
Paths above are proposed boundaries, not newly created source files.

## API and component architecture

- Public catalog/detail/slots and booking POST remain existing routes; optional displayTimezone
  closes G-008. A public context read supplies the non-secret restore generation for private keys.
- Protected admin reads support inactive activities and saved configuration. Writes retain
  existing success bodies and expose preservation warnings via a typed header. Cancellation
  remains 204 for initial and repeated success; current status is canceled in either case.
- Public booking success omits contacts on first submission and recovery. Admin history uses
  an explicit present/removed union. Fixed ApiError schemas cover 400/401/404/409/410/500/503;
  202 requires committed matching unexpired unfinished admission. Proposed 409
  attempt_invalidated_by_restore (A-003) is distinct from 410 chronological expiry; 503
  admission_unverified/execution_unverified never imply confirmation. FastAPI's default 422
  is mapped to the proposed 400 contract.
- Exact operation/error/header/model proposals live in contracts/api-proposal.md. They need
  lead/human review, application to canonical TypeSpec, generation, and freeze before integration.
- Frontend owns UI state: browsing, loading/empty/error, submitting, unknown/pending, confirmed,
  rejected and expired. Disable duplicate clicks, retain the original private key/details only
  in memory, and require explicit recovery. Unknown/expired outcomes never trigger fresh booking.
  Clear the frozen contact payload/private key at expiry or explicit completion/abandonment;
  never persist it in browser storage. Loss of recovery state routes to host verification.
  Use native form controls, responsive layouts and visible field/status feedback.

## Database, transactions and retry design

See data-model.md for fields and invariants. Configuration/history and personal/security state
are separate. Confirmed bookings have immutable UTC endpoints; a status transition to canceled
sets original canceled_at once. GiST `[)` exclusion follows ADR-0002 and allows adjacency.

The [current protocol](contracts/retry-protocol.md) records provisionally approved split
admission/execution. Admission atomically persists database-generated T/E and binding; only
successful durable commit makes it valid. Stamp T late after admission contention and preparation,
using one clock_timestamp() sample, with E=T+24 elapsed hours. Do not restamp committed attempts.
No transaction identity, nullable receipt state, post-commit resolver or worker sealing is needed.
The earlier exact commit-metadata design was superseded by the human's A-002 clarification.

If actual COMMIT C is delayed, remaining validity at C is max(0,E-C), not 24h from C. If C>=E,
reject as expired with no execution/pending/result. Bound lock/statement/application budgets,
but timed-out COMMIT remains uncertain until a fresh committed-state read resolves it. Normal
restart/transient failure preserves original T/E/binding/results/generation.

Execution locks attempt NOWAIT and activity with bounded wait; refreshes config/DB wall clock;
checks A-001, full-window, notice/horizon and expiry; and commits booking/contact/result together.
A named exclusion violation uses a savepoint for terminal 409. Other failed transactions roll
back completely before fresh classification. Pending requires proven committed matching
unexpired unfinished state; unknown/mismatch/expired requests cannot receive ordinary 202.
Only known committed booking/result permits confirmation; no broker/lease/replacement key.
Approved A-003 permits generation invalidation only after a separately approved unrecoverable
restore with writer fencing; return distinct 409, never chronological 410. Runtime evidence
for seventeen protocol cases is still required by T-02 and has not been produced.

## Authentication and privacy design

Opaque bearer tokens have 256 bits of entropy, hashed verifiers in DB, and a fixed issued-at
+60-minute expiry. Authorization uses current DB wall-clock time after lock waits. React keeps
tokens in memory; reload requires reauthentication. Token expiry/401 clears protected contacts,
passwords and caches; only non-sensitive config drafts can remain for explicit resubmission.
No refresh/automatic replay. Contracted logout revokes the presented session. Restrict CORS,
render all user text literally, use CSP/TLS for any later deployment, and redact logs by design.

Contacts are separate ephemeral rows with deletion deadlines calculated from preserved end or
first cancellation. A worker targets deadlines and reports any overdue row/failure; read paths
suppress at/after deadline regardless of worker success. No polling grace or outage exemption.
Logical deletion is not forensic disk erasure. Backups/exports have an explicit allowlist of
configuration and only approved contact-free history. Full-volume snapshots and WAL archives
would violate this design. Under approved A-003, a separately approved unrecoverable restore
records the recovery event, fences the old writer, changes generation, and returns distinct
restore-invalidation guidance; ordinary restart does none of these. Restored contacts/sessions/
attempts are empty; minimal history can
remain correlatable and is not claimed irreversibly anonymous.

## Time handling

ZoneInfo with explicitly pinned tzdata validates IANA rules. Convert local candidates using both
folds plus round-trip validation. Build actual continuous portions by local date/clock membership;
never infer them solely from ambiguous endpoint conversions. Full elapsed `[start,end)` must fit
one portion of one window. No combining touching windows. Elapsed notice/horizon/auth/retention
arithmetic uses UTC, independently of calendar-day lengths. Browser labels use selected IANA zone
and offset, preserving UTC identity when changing zones. Visitor-date grouping is performed by
server membership across all intersecting activity dates. A-001 fixes candidate starts to exact
activity-local minutes 00/15/30/45, with zero seconds/fractional seconds. A 09:10 window begins
with 09:15 only if the full interval fits; never round a submitted instant or require windows
themselves to align. All approved DST/window decisions are preserved, including both offsets
for eligible repeated starts. No stored booking is moved by this amendment.

## Infrastructure and development lifecycle

Compose design: DB starts with fsync/synchronous_commit settings, UTC sessions and durable
storage; readiness validates them. No commit timestamp tracking/lookup is required. Then db healthy → migrate exits
successfully → explicit dev/test seed exits
successfully → backend/retention worker ready → frontend. Reuse backend image for migration,
seed and worker; no migrations in every web replica. Readiness fails on unavailable DB, missing
schema/generation or unhealthy retention worker; the existing /health remains a shallow liveness
check. Add a contracted operational readiness endpoint outside the product REST namespace.
Postgres stays unexposed to host by default; explicit local test port/override is test-only.

Keep one-command development startup after copying/configuring `.env`; never commit `.env`.
Seeds use synthetic data, environment-provided dev credentials and a future valid schedule;
reruns do not reset existing data/passwords. Default production startup never seeds an example
admin. Lock Python/npm dependencies, pin images and Playwright browsers, install tzdata and set
its source explicitly. Use existing scripts/verify.sh as the lead-coordinated verification entry
point once it actually runs the full suite; its current scaffold success text is insufficient.

CI design: (1) locked dependency install and TypeSpec/OpenAPI/TS regeneration plus no-diff check;
(2) frontend type/build and backend static/unit checks; (3) PostgreSQL 16 migration, contract,
transaction race and privacy/backup/restore checks; (4) Compose readiness and Playwright desktop/
mobile public/admin journeys. No deployment job. Secrets come from temporary runtime env, never
artifacts. CI uploads only allowlisted synthetic/redacted reports; disable HAR/body-bearing
traces/videos on sensitive flows. Failing checks block merge, which still requires human review.

## Verification matrix and requirement coverage

The full specification retains the detailed scenario mapping; this matrix assigns evidence to
components rather than replacing any of its 77 cases. Freeze injectable time for exact boundaries;
do not add a public test clock or test-only production authorization bypass.

| Coverage | Evidence to implement after approval |
| --- | --- |
| FR-001–005, FR-021, FR-026–027, FR-030; SC-001–002/009/013–015/018 | Pure availability tests for each rule; real DB occupancy; Vienna spring/fall fixtures, Lord Howe non-hour transitions, cross-zone/date-boundary and skipped-date membership; nonexistent/repeated boundaries, no bridging, window end fit, touching windows, both notice/horizon equality and ±1 microsecond. A-001 fixtures: 09:10–10:00/30m offers only 09:15 and 09:30; 09:10–09:40 offers none; reject off-grid minutes and nonzero seconds/fractions without rounding; preserve both eligible repeated offsets and activity-zone anchoring after display-zone changes. |
| FR-006–012, FR-024; SC-003–005/011; approved A-002/A-003 and RP-01–17 | HTTPX integration with independent connections and start barriers: distinct same/overlapping starts one 201/one 409; matching same key one booking/results; mismatch isolation; terminal rejection replay; delayed admission commit, failed/unknown admission, contention classification, full timeout/deadlock rollback, crash after admission/before commit/after commit, post-contention final DB timestamp stamping, persisted T/E integrity; exact 24h expiry, DB/response loss, pending and expired tombstones; back-to-back and different activities. |
| FR-013–014, FR-028; SC-006/016 | Correct/incorrect login; auth before protected validation/existence; 60m minus/equal/plus boundary, active session still expires, wait crossing expiry, no renewal; memory-only token, locked views, sensitive draft removal and explicit resubmission E2E. |
| FR-015–018, FR-023; SC-006/008/010/015 | Config set validation/atomic rollback; slug uniqueness, inactive management; duration/timezone/hours/block edits preserve interval/status and warn; config-vs-booking/cancel races; repeated/concurrent cancel and response-loss replay preserve original cancellation/deadline. |
| FR-017/019/025/029; SC-012/017 | Clock-controlled end/cancel +720h deletion, boundary read suppression during worker failure, startup catch-up and honest overdue status; no contact-bearing binding/result copy; backup byte scan + restore DB inspection; normal restart preserves old valid keys; approved A-003 permits only separately approved restore invalidation of old/missing keys with a distinct error; no contact or credentials in errors/logs/reports. |
| FR-020–022; SC-007/009/014 | Playwright public/admin journeys at 320 and 1280 CSS pixels; visible primary controls, no horizontal overflow, empty vs load-failure, unknown vs success, explicit retries, zone changes preserve instant, repeated offset labels. |
| FR-002/015/031; SC-019 | Description 1/2000 code points, trim/blank/overlong, astral Unicode vs UTF-16 length, preserved multiline/interior whitespace, literal HTML/script text, preview plus full text and field feedback. Shared trimming semantics verified across browser/backend. |
| All FR/SC | Canonical OpenAPI request/response/status/header conformance for each operation, generated no-diff checks, Alembic empty upgrade, repeat seed/startup, real Compose and complete 77-scenario traceability report. Twelve policy cases are integrated; RP-01–17 are unexecuted runtime verification targets, not additional completed tests. |

Unit tests fail before behavior is implemented where practical; any different sequence must be
explained. QA independently reviews backend-authored race/privacy evidence. No claim of race
safety is based on sequential requests, a mocked exclusion, or SQLite.

## Multi-agent boundaries and integration strategy

This is a proposed allocation, not authorization to launch agents or create tasks/worktrees.
`docs/AGENT_TASKS.md` remains shared ownership authority; later feature tasks must reference it.
The shared guide already assigns root Docker configuration to QA and nested Dockerfiles to
their component owners through frontend/** and backend/**. Retain that ownership. Lead ownership
of generated frontend API definitions remains an explicit narrow exception to reconcile in the
shared guide before decomposition; this plan does not silently override it.

| Owner | Exclusive proposed scope | Boundary / required handoff |
| --- | --- | --- |
| Lead | contracts/**, generated frontend/src/api/schema.d.ts, docs/PRD.md, architecture/ADRs, specs/**, shared scripts and approval records | Own contract/source reconciliation, generated baseline and integration review; frontend treats schema.d.ts as read-only, any regeneration goes through lead. |
| Frontend | frontend/** except generated schema; includes frontend/Dockerfile | UI, typed fetch, in-memory auth/attempt state, formatting and component tests; report exact build/UI checks and contract commit. Own frontend package/lock changes. |
| Backend | backend/** including backend/Dockerfile | DB/Alembic/services/API/auth/worker/seed/backup logic and unit/integration/contract tests; own backend dependency locks; publish migration/CLI/health interfaces before QA wiring. |
| QA/DevOps | tests/**, .github/**, root docker-compose*.yml and other root Docker/CI configuration | Independent E2E/race/privacy acceptance, Compose/CI wiring, root test-runner manifest/lock if introduced; no edits to backend implementation or feature API types. Specify required image/CLI interfaces with component owners; do not edit nested Dockerfiles. |

After separate approval, lead reconciles PRD/architecture/ADRs and canonical TypeSpec, regenerates
API types and commits a reviewed shared baseline. Only then create independent worktrees/branches
from that same commit. Each worktree uses its own ignored Spec Kit feature selector and local
secrets, isolated test databases/ports/Compose project names, shared reviewed skills/config only.
Frontend may use fixtures typed against frozen generated operations while backend is built;
fixtures are not evidence that real integration works. Contract changes pause affected agents,
require a lead proposal/human review, regeneration and a coordinated baseline update.

Integration is reviewed and sequential: backend with migrations/contract checks, frontend with
real API flows, QA/DevOps with full Compose/CI acceptance. This does not bypass QA development in
parallel. Every merge requires human authorization; no unchecked automated merge. Handoffs name
scope/files, spec/contract commit, exact checks/outcomes, limitations and contract/migration flags.
No push is authorized by this planning request, even to isolated branches.

## Phase outputs, review and blockers

Phase 0 produced research.md with concrete technical decisions and alternatives. Phase 1
produced data-model.md, quickstart.md and contract/reconciliation proposals, supplemented
by the reviewed retry protocol. No extension
configuration was present at the pre-plan check; check again after output validation. No hooks,
agent dispatch, plan approval, implementation tasks, contract changes, or application work are
inferred from artifact generation.

| ID | Review question / consequence |
| --- | --- |
| P-01 — resolved product boundary | Human approved A-001 on 2026-10-25: exact activity-local minutes 00/15/30/45, full continuous-window fit, previous DST behavior unchanged. Specification/checklist and planning artifacts reconciled; this product blocker is closed. Technical-plan approval is recorded above; source reconciliation and contract review/freeze remain required. |
| A-002 — approved with clarification | Database-generated T persisted with binding/E in a successfully committed transaction; E=T+24h, not commit metadata. Delay consumes validity; rolled-back admission is invalid; uncertain COMMIT remains unverified. Reconciled in spec/checklist/design. |
| A-003 — approved | Separately approved unrecoverable restore may invalidate old keys with 409 attempt_invalidated_by_restore and host verification; 410 remains chronological expiry. Normal restarts/transient failures preserve valid state. |
| T-01 — approved | Memory-only 60m administrator sessions with documented reload/XSS/expiry limitations; no renewal/automatic write replay. Guest memory-only recovery remains a documented design limitation, not a new cross-reload recovery guarantee. |
| T-02 — provisionally approved | Split admission/execution retained under retry-protocol.md; seventeen runtime/crash/timeout/delay cases still need verification after separate implementation authorization. No commit-metadata machinery, broker or execution lease. |
| T-03 — conditionally approved | Contact-free logical backups with fail-closed allowlist/schema checks, disclosed snapshot-age/recovery limits and enforceable hosting restrictions. These controls are not yet verified; approving A-003 does not approve any actual restore/deployment. |
| T-04 — approved | FE/BE own their Dockerfiles; QA owns root Compose/CI; Lead owns canonical/generated contracts. Shared ownership documentation records the generated-file exception; no tasks are generated. |

The human formally approved this technical plan and the decisions above on 2026-10-25,
retaining T-02/T-03 conditions. No unconditional
whole-system/runtime readiness or permission for tasks/implementation is inferred. All 15 original
Q/A entries remain history, A-001/DST remain unchanged, and only the explicit receipt/recovery
clauses were amended. There is no remaining product-policy ambiguity identified in this pass.
PRD/architecture/ADR/canonical TypeSpec/generated-artifact reconciliation remains documented
future work; shared ownership is reconciled. contracts/main.tsp is unchanged by this pass.

Stop after the explicitly authorized local approval-baseline commit and report. No tasks,
agents, push, application migration, restore or deployment is authorized or performed. Runtime
verification requires separately authorized implementation;
its pending status blocks a claim that the conditions have been satisfied, not this documentation
reconciliation. The remaining technical/operational risks are in checklists/technical-review.md.

## Complexity Tracking

No constitutional waivers requested. The small retention process is necessary to decouple
mandatory deletion from API requests; private tables and retry tombstones implement approved
privacy/retry invariants. Rejected complexity and tradeoffs are recorded in research.md.
