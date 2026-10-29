# SlotBook implementation coordination protocol

Prepared: 2026-10-25. Revised: 2026-10-27. The original approved coordination baseline is
`04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419`. The initial T001-only authorization and
[T001 handoff](IMPLEMENTATION_BASELINE.md) remain historical provenance; later separately
approved batch completion is recorded in the [task list](../specs/001-appointment-scheduling/tasks.md)
and its linked integration records. Nine tasks are complete; 83 remain unchecked.

On 2026-10-27 the human approved the parallel-discovery proposal reviewed against
`3148b980cbe3d1b7fe3f8fd19916494b41e68d6d`, authorizing the three-document amendment,
commit and feature-branch push only. The preparation/fixture checkpoints below are approved
plan rules, not permission to start tasks, launch agents, create worktrees or merge/deploy.
H0 and separately supplied task scopes remain required. This revision retains the I3/I4/I6
ownership, isolation and evidence rules and all original runtime safety requirements.

The frozen API v1 source baseline is `adc0b83a4408493ac44d3a7571dfd3d25a758679`.
The [constitution](../.specify/memory/constitution.md), approved specification/amendments,
technical plan and [retry protocol](../specs/001-appointment-scheduling/contracts/retry-protocol.md)
remain authoritative. This protocol changes neither product behavior nor the provisional T-02
and conditional T-03 gates. Shared ownership remains defined by [AGENT_TASKS.md](AGENT_TASKS.md).

## Ownership and interfaces

| Owner | Future files / responsibility | Boundary |
| --- | --- | --- |
| Lead/Architect | `docs/IMPLEMENTATION_BASELINE.md`, this protocol, milestone reviews and `scripts/verify.sh`; T001/T088/T091 | Records reviewed revisions and integration decisions. Owns canonical/generated contracts; no independent component fixes or automatic merges. |
| Backend | `backend/tests/support/clock.py`, `faults.py`, `server.py`, `worker.py`, backend fixtures and fault tests; T002/T016/T018/T020/T042–T044 | Owns private Python injection points, real PostgreSQL transaction barriers, test API/worker entrypoints and offline backup/restore CLIs. Production defaults use DB wall-clock time and no fault hooks. |
| Frontend | Its Dockerfile, typed fixture tests and `frontend/playwright.config.ts`; T003/T008 | Publishes build/start/API-origin requirements and locked browser tooling. Does not change generated API definitions or Backend test hooks. |
| QA/DevOps | `tests/harness/runner.py`, `targets.py`, `evidence.py`; `tests/compose.test.yml`, `compose.integration.yml`, `compose.faults.yml`; root Compose/CI and `tests/**`; T004/T022/T023/T048/T074/T087 | Owns host lifecycle orchestration, target guards, independent black-box assertions and sanitized evidence. Does not import Backend application modules or edit component Dockerfiles/hooks. |

Each owner publishes commit references, commands, supported interfaces and observed outcomes.
QA requests a missing Backend hook from Backend; it does not add a control endpoint or patch
Backend files. Backend requests Compose changes from QA. The Lead resolves coordination and
contract mismatches before affected work continues. No public endpoint or request field is added.

## Early discovery work and acceptance checkpoints

The approved technical plan permits Frontend fixtures and independent QA development while
Backend foundations are built. Keep all 92 task IDs and the existing owner boundaries. After
separate execution authorization, owners may work independently using one reviewed committed
amendment-inclusive baseline, supplied by the Lead as a full hash after it exists.

| Work / checkpoint | Prerequisites | Evidence and completion boundary |
| --- | --- | --- |
| T027 Frontend test authoring | T003 | Use frozen generated types and T003 fixtures; collect/typecheck and record meaningful expected-red missing-UI assertions. This is authoring, not functioning discovery or live API proof. |
| T031 catalog/detail UI | T027 | Use the production typed client with test-only network interception; catalog/detail fixture cases pass. Record remaining date/slot failures awaiting T032 honestly. |
| T032 date/slot UI | T031 | Full discovery fixture suite and existing Frontend regressions pass; consume returned UTC slots without calculating availability. Real integration remains pending. |
| T026 QA discovery test authoring | T004, T005 | Review/collect frozen-operation/status/header/privacy assertions and validate test oracles. Authoring may complete with documented expected-red evidence; live API verification stays pending. |
| T022 static preparation | T004, T008 | Prepare only its existing Compose/overlay/runner paths and guard/configuration checks. Keep the T022 checkbox unchecked. No runtime/lifecycle acceptance is established. |
| T022 runtime completion | T007, T008, T009, T017, T020, T021, T004 | All original runtime acceptance and target guards must pass before marking T022 complete. |
| T033 real discovery | T024, T026, T030, T032 | Verified infrastructure plus real T026 API assertions and all US1.1–8 UI/API outcomes against one immutable selected candidate, without intercepted feature responses or fixture transport. |
| T034 discovery review | T033 | Review actual T024 infrastructure and live discovery evidence; fixtures cannot replace runtime results. |

T024 retains every dependency and its mandatory infrastructure acceptance. Backend story
implementation still follows that gate, and T030 retains T029/T016/T026 as prerequisites.
Before T030 completes it must pass the authored T026 suite against its actual Backend;
T033 reruns that suite against the combined candidate. T026 completion means its authoring
acceptance is met, not that the Backend passed. This avoids making T026 authoring depend on
the Backend implementation it is meant to test.

QA's current `http_client` fixture uses `MockTransport`. It cannot supply live evidence.
T026 must distinguish fixture self-checks from an explicitly guarded live client: missing
runtime infrastructure/authorization fails closed, with no fixture fallback. Missing/skipped
mandatory live cases remain blockers. Do not disguise expected-red assertions with skips/xfails;
required merge checks still must pass. Report authoring, fixture, static and live results
separately, with actual commands/counts/exits and the correct source revision.

T022 preparation may wire selected component contexts, T008's build-time browser API origin,
removal of stale development mounts and fail-closed orchestration scaffolding. Configuration
checks use synthetic private inputs without publishing rendered secrets. Missing Backend CLIs
and runtime inputs stay explicit and blocked; no fake readiness/CLI success, lifecycle,
migration, crash or restore execution is permitted by the preparation checkpoint. T023 still
requires completed T022. Fault/restore operations retain their separately approved target scope.

Frontend T031 may change only the obsolete scaffold-render assertion in
`frontend/tests/scaffold.spec.ts`, preserving T003 contract/privacy/report checks. T032 may
also wire `frontend/src/features/catalog/ActivityDetail.tsx` after T031. Those paths stay
Frontend-owned and sequential; no generated API file changes or production mock API is allowed.
QA owns both T026 and T022; sequence its work if needed, without concurrent shared-file writers.
Backend can finalize T007 and then T009 after their own dependencies and authorization.
No zero-image-vulnerability condition is added to T007; known risks and production-release
restrictions recorded in the Backend foundations review remain intact.

## Common baseline and component candidates

The steps below apply only to separately authorized work. Historical T001 preparation did not
create component checkouts or authorize later tasks. Use the current reviewed task list,
this protocol and [AGENT_PROMPTS.md](AGENT_PROMPTS.md); the legacy JWT and Frontend-owned
contract-generation directions were corrected in the reviewed prompt baseline. The Lead supplies
one full committed revision containing the approved task/protocol/prompt amendment before
any newly authorized owner starts. Never use a dirty or older checkout as that shared baseline.

1. After H0, the Lead publishes a reviewed, committed common baseline containing the task list
   and protocol, descended from the frozen commit. All implementation checkouts start from that
   same full Git revision. T001 records the baseline provenance and handoff; a commit's own hash
   is recorded after it exists in the handoff/run manifest, not as a self-referential file value.
2. For each milestone, owners hand off clean committed Backend, Frontend and QA revisions.
   The candidate manifest records the common baseline, the three full commit hashes, the Lead
   verification-script revision, task/protocol revisions and the milestone/test scope. Each selected
   commit must descend from the common baseline. No dirty or untracked source is silently built.
3. QA consumes the Backend checkout's `backend/` and Frontend checkout's `frontend/` as exact
   build contexts, and the QA checkout's Compose/overlays and test files. It mounts the reviewed
   frozen contract read-only. The runner checks that canonical TypeSpec, generated OpenAPI and
   generated TS match the frozen baseline in every selected checkout before building.
4. `tests/compose.integration.yml` resolves those contexts and the corresponding component
   Dockerfiles. Development bind mounts from the QA checkout must be removed or explicitly
   replaced with the selected component checkout; they must never shadow the selected image
   with older QA-branch code. Record the rendered configuration fingerprint, context commits,
   resolved image IDs/digests and lockfile hashes before tests start. Do not publish resolved
   Compose environment values or its raw configuration, which may contain secrets.
5. Each candidate/run has a unique Compose project, network, PostgreSQL container, named volume
   and test database identity. QA allocates unused loopback-only API/UI host ports and records
   the resolved values. Frontend receives the corresponding browser-reachable API origin through
   its published build/start interface. Container QA uses `http://backend:8000` and internal DB
   networking. No default PostgreSQL host port or shared developer volume is needed.
6. Recheck component revisions and image/mount identity when the run completes. An owner changing
   its checkout during the build/run invalidates that candidate. Either hold the clean checkout
   fixed during verification or consume its immutable committed build snapshot. A changed component,
   lock, script or overlay starts a new candidate; results from different candidates cannot be mixed.

QA's candidate builds combine component artifacts without merging or cherry-picking branches.
They do not modify another owner's checkout. The Lead reviews the combined evidence before
requesting human approval for each actual merge. After authorized integration, QA reruns the
required regression/contract checks on the resulting revision; pre-merge evidence is not an
automatic substitute for checking integration changes. No current worktree or merge is authorized.

## Disposable PostgreSQL and target guards

The runner provisions an isolated PostgreSQL 16 instance from the pinned QA Compose definition,
runs Backend-owned migrations and explicit synthetic development/test seeds, and checks durability,
UTC sessions, schema, role isolation and readiness. API, worker and test clients for a scenario use
that same database; concurrency tests use independent connections and barriers, not separate
databases that cannot contend. Different runs/worktrees do not share database state or volumes.

`tests/harness/targets.py` must verify the run manifest, repository/candidate identity, disposable
project labels, exact database/container/volume identities and the approval scope before mutation.
For first provisioning, require approved unused resource names, create labeled resources, and
record their actual identities before later operations. A restore drill additionally names a fresh
empty destination and the old candidate writers to fence; it never overwrites the source database.
Production URLs, ordinary development projects, unknown targets and nonempty restore
destinations fail closed. An environment variable alone is not proof that a target is disposable.
After a guard fails, no stop, reset, migration, restore or deletion command is attempted.

H0 may explicitly include the named disposable crash/recovery drill scope. Otherwise that scope
requires separate human approval before the relevant tests run; elapsed time and task checkboxes
cannot supply it. Actual disaster recovery always requires separate human approval. Cleanup is
restricted to that run's explicitly authorized resources, never a broad Docker prune/down command
against an inferred project or a shared database. No real customer data enters any fixture.

The runner holds a local exclusive run lock while changing a project's lifecycle or fixtures.
Mutating suites run serially against that target; simultaneous connections within an intentional
race case remain required. Concurrent task verification uses different projects/databases/control
directories. No restart or fixture reset runs underneath another suite using the same target.

## Host runner and private test control

T004 defines and guard-tests the runner interface; T022 connects it to Compose. Its future commands
are `check`, `run --suite <name>`, `run --milestone T024`, `run --milestone T034` and `collect`,
invoked with `tests/.venv/bin/python tests/harness/runner.py`. Inputs are supplied through local ignored configuration, including
`SLOTBOOK_TEST_MANIFEST`; no credentials or DSNs appear in committed manifests or command output.

| Suite / control | Execution owner and location | Required behavior |
| --- | --- | --- |
| Backend static/unit/integration/contract suites | QA runner invokes the selected Backend image; Backend owns assertions | Executes locked Ruff/mypy and named pytest suites, migration/status commands and private report output. No default developer Compose target is inferred. |
| Startup, whole API/DB/worker restart and crash | QA host runner; `tests/infrastructure/test_startup.py`, `test_readiness.py`, `test_restart_recovery.py` | Uses guarded Compose commands against the selected disposable project. Preserves volume, HMAC configuration, generation and committed state for normal restart. Does not treat restart as A-003 recovery. |
| Backend transaction crashes/ACK loss and SQL locks | Backend pytest in its selected image; T042–T044 | Uses independent real connections and only self-launched test subprocesses. Injects barriers before/after admission/booking COMMIT and tentative inserts. No Docker control is required inside this suite. |
| Qualified restore | QA host runner; `tests/infrastructure/test_restore_recovery.py`; T074 | Stops/fences only the approved candidate writers, invokes Backend-owned backup/restore CLIs, then verifies readiness/history/old keys. Backend T073 checkpoints precede independent QA execution. |
| Ordinary contract/concurrency/privacy assertions | QA container; `/quality/contract`, `/quality/concurrency`, `/quality/privacy` | Uses API v1 and isolated DB inspection. Backup-content assertions inspect prepared read-only fixture artifacts/restored rows; they do not launch Docker or privileged restore commands. |
| Browser journeys | QA-pinned Playwright on host; `tests/e2e/` | Runner prepares the candidate and invokes its locked `npm test` command with assigned frontend/API URLs. Browser traffic uses only frozen API v1. Frontend fixture tests remain separately owned. |
| Boundary clocks and application fault barriers | Backend implements private adapters; QA host supplies per-case control | Test server/worker factories explicitly inject the adapters. QA does not import app modules, expose HTTP controls or mutate production configuration. |

Only the host runner controls Compose, container lifecycle and offline CLIs. Application and QA
containers receive no Docker socket. `tests/compose.faults.yml` explicitly selects Backend-owned
test server/worker entrypoints instead of ordinary entrypoints and mounts a protected per-run
temporary control directory. The host writes case clock/barrier instructions there; test adapters
read them and exchange safe reached/release markers. Control schemas carry case IDs, instants and
barrier names only, never contacts, request bodies, retry keys or credentials. Access is limited to
the test processes/host runner; control files are not public routes or evidence artifacts.

Test factories inject clock and callback dependencies through Python interfaces. Ordinary server
and worker entrypoints do not load these adapters or consume the control directory; HTTP input
cannot activate them. The harness verifies this separation. Server and worker use the same
controlled fixture clock when a boundary test requires it. Fault callbacks distinguish before
COMMIT, committed-but-ACK-lost, after tentative insert and response-loss boundaries; returning a
mocked success is never accepted as a committed-state assertion.

Controlled-time/pre-aged fixtures verify exact 24h/60m/720h and DST boundaries. Real PostgreSQL
durability, late admission stamping, lock waits, COMMIT delay, lost ACK and crash/restart cases
must also run with production `clock_timestamp()` and real commits. Label these evidence classes
separately: a mock clock is not proof of durable admission. Test final expiry after tentative
work/constraint waits and verify rollback of all tentative rows. Every RP-01–17 case remains
mandatory for T089; no missing harness capability is a reason to skip or waive one.

## Evidence and handoff

QA's collector owns the local ignored `test-results/<run-id>/` evidence directory. It publishes
only an allowlisted manifest, sanitized JUnit, assertion IDs/outcomes, command exit codes/counts,
safe SQLSTATEs, component/contract/lock hashes and image/timezone/browser versions. Lead milestone
reviews commit only safe summaries and source revisions, never machine-specific state.

Raw JUnit/stdout/stderr, test control, runtime secrets, fixture payloads and dumps awaiting
inspection stay in a protected per-run temporary directory outside the published evidence tree.
The collector strips captured streams, raw exception/SQL messages, bodies, headers and assertion
values before publishing reports. Tests use safe failure identifiers; CI does not print raw
subprocess output or upload raw XML/traces/dumps. It uploads only files the collector validates,
not a recursive workspace directory. A failed redaction check fails the run.

Each suite emits test IDs and scenario/FR/SC/RP associations plus actual assertion outcomes.
T086 reads only sanitized results for one manifest and requires all its producer tasks, including
T042/T043/T044/T057/T085, to have finished. A task label, missing result, zero tests or a skipped
mandatory case cannot satisfy coverage. `collect` must run before the acceptance-report command;
an incomplete milestone uses its explicit subset and cannot be represented as all-77 completion.

T024 covers infrastructure/schema/role/cleanup/readiness and static/unit checks only. T034 uses
those foundations plus discovery, seeded schedules and US1.1–8; neither milestone needs login,
booking or recovery tooling to pass. Their explicit `run --milestone` modes require those subsets
and their actual results, without collecting absent later-story suites or silently skipping a
required foundation/discovery test. Later milestones add their real suites. T089 reviews all
T-02 runtime proof. T090 reviews T-03 deletion/read suppression, contact-free backup/restore and
hosting evidence; unavailable provider controls stay CONDITIONAL and block public-use clearance.

## Reproducibility checks

- Backend, Frontend and QA owners pin **every** Dockerfile `FROM` to an exact compatible release
  and immutable verified digest. QA pins PostgreSQL to an exact 16.x release/digest in Compose.
  Record resolved image IDs and target platform. No mutable major tag alone satisfies the check;
  actual digests are selected/verified during approved implementation, not fabricated here.
- Backend locks runtime/test packages including `tzdata`, Ruff and mypy. It sets `TZ=UTC` and
  `PYTHONTZPATH=""` in its image so Python `zoneinfo` uses the locked package, reports the package
  and IANA release and validates that the intended source loads. DB sessions remain UTC. Browser
  timezone behavior is verified with the locked browser revision; server availability remains
  authoritative if browser/server timezone data differ. Missing configured data fails validation.
- Frontend/QA lock npm and Playwright versions and install the corresponding Chromium revision.
  The Lead records agreed runtime constraints; owners record exact resolved versions/lock hashes.
- T002 supplies `backend/pyproject.toml` and locked development tools. From `backend/`, the required
  executable checks are `python -m ruff check app tests`, `python -m ruff format --check app tests`
  and `python -m mypy app`. T006/T087 CI and T088 shared verification execute these; errors cannot
  be hidden with blanket ignores, missing-import suppression or skipped commands.

Configuration examples and handoffs identify required variables and version constraints without
real values. Routine restarts preserve retry secrets/state. Changes to these interfaces or pins
require scoped review and regression verification; they do not authorize a contract or product
change. Human implementation approval, T-02/T-03 evidence and separate merge/deployment approvals
remain distinct gates.
