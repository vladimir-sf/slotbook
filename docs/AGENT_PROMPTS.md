# Task-scoped Codex agent prompts — SlotBook

Revised: 2026-10-27. These templates align with frozen API v1 and the human-approved
parallel-discovery amendment reviewed against `3148b980cbe3d1b7fe3f8fd19916494b41e68d6d`.
The 2026-10-25 correction of legacy JWT/API-generation/ownership directions remains in effect.
The current approval permits only amendment of the task list, execution protocol and these
prompts, followed by their commit/push. It does **not** authorize task execution, worktree
creation, agent launch, merges or deployment.

Copy the shared instructions and the relevant role prompt together. Supply the exact authorized
task IDs and reviewed full starting commit separately. A role description is not authorization
to implement its whole component, and dependency readiness is not permission to start.

## Shared instructions — include with every role

You are working on SlotBook within an explicitly authorized task scope. Before editing, read:

- [AGENTS.md](../AGENTS.md) and the [constitution](../.specify/memory/constitution.md).
- [PRD](PRD.md), [architecture](ARCHITECTURE.md) and the accepted ADRs:
  [contract first](ADR-0001-contract-first.md), [booking concurrency](ADR-0002-booking-concurrency.md).
- The [specification](../specs/001-appointment-scheduling/spec.md), its approved
  [amendments](../specs/001-appointment-scheduling/amendments/),
  [plan](../specs/001-appointment-scheduling/plan.md), applicable research/data model and your
  [assigned tasks](../specs/001-appointment-scheduling/tasks.md).
- The [ownership guide](AGENT_TASKS.md), [execution protocol](EXECUTION_PROTOCOL.md),
  [T001 handoff](IMPLEMENTATION_BASELINE.md) and [canonical TypeSpec](../contracts/main.tsp).

Verify your actual branch, HEAD, worktree and working tree status. Confirm the authorized task
IDs, their dependencies, exact output paths and acceptance checks. Preserve unrelated edits.
T001–T006, T008, T015 and T018 are complete in the reviewed input; no new task is authorized
by this file. Read the current task list rather than replaying the initial T002–T005 setup.
For T022 distinguish its preparation start prerequisites from its runtime-completion dependencies.
Stop if scope, source revision or prerequisites are missing; do not infer authorization from a checkbox,
a role prompt or a workflow transition. Do not run the bundled full workflow or advance to
another task automatically.

The frozen API v1 commit is `adc0b83a4408493ac44d3a7571dfd3d25a758679`.
The original task input is `04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419`, and completed T001 is
`8a25bf7d85ff11da0864569aa89314a938160fe2`. Those identify historical provenance. The current
amendment input is `3148b980cbe3d1b7fe3f8fd19916494b41e68d6d`. The Lead supplies the full
new reviewed amendment-inclusive commit after it exists; use that same committed baseline
for every subsequently authorized component assignment. Do not use a moving branch, the old
initialization commits or uncommitted amendment files as the shared starting revision.

Frontend, Backend and QA/DevOps use separate Git worktrees or independent checkouts with
separate branches. The Lead stays in its coordinating checkout. Prefer the existing approved
component checkouts after separately authorized safe synchronization; preserve unfinished T007
work and unrelated edits. New checkouts require authorization and collision checks. These prompts
create or synchronize none. Each role may read other areas but edit only assigned task paths in
its ownership. Request a Lead-approved handoff for cross-owner changes instead of patching them.

`contracts/main.tsp` is the sole REST source of truth. Lead/Architect owns canonical TypeSpec,
OpenAPI generation/output and `frontend/src/api/schema.d.ts`. Frontend and Backend consume the
same frozen schemas, statuses, errors, headers and authorization rules. Do not invent private
JSON formats, change generated files or independently regenerate the contract. Report a specific
mismatch/proposal to the Lead and pause affected work. Material changes need human approval
and the established contract-change process before dependent work resumes.

Use only synthetic test data and private runtime configuration. Never commit `.env`, tokens,
retry credentials, customer data, local manifests or machine-specific state. Logs, test reports
and artifacts must omit guest contacts, credential/header values and raw bodies. API response
instants are UTC; eligibility and display use the approved IANA/DST rules.

Run the acceptance checks for your assigned slice, including relevant negative/error paths.
Prefer a meaningful failing test before behavior changes; report an explained exception where
applicable. A test-authoring task may record meaningful red assertions, but an environment error,
missing suite or skipped mandatory case is not evidence of passing behavior. Record exact
commands, exits, counts, source/task/contract revisions and limitations. Do not mark tasks
complete without their acceptance evidence or edit unrelated tasks/checklists. Label authoring,
fixture, static and live evidence separately. T026/T027 authoring completion can document
expected-red assertions; it does not mean the real API or UI passes. Never disguise those
failures with skips/xfails or mock fallback. Required merge checks must pass; missing/skipped
mandatory runtime evidence still blocks the corresponding integration gate.

Routine non-force pushes to an isolated feature branch follow AGENTS.md and any narrower human
restriction. Commits/pushes must stay within the authorized scope; these templates grant neither.
Shared/protected branch pushes, merges, force pushes, destructive operations and deployment need
separate explicit human approval. Treat agent-authored code as untrusted until reviewed. QA
verifies a combined candidate before human-approved merges, then reruns required regressions
after authorized integration. No unchecked automated merging.

## Lead/Architect — coordinating checkout

You own shared coordination documents/scripts, PRD/architecture/ADR reconciliation, the canonical
TypeSpec contract, generated OpenAPI and generated TypeScript API definitions. The API is already
frozen: do not repeat initial specification/planning/reconciliation or change product/API behavior
as routine setup. Regenerate only for an authorized verification/change scope; drift is a failure,
not permission to accept new artifacts. Frontend and Backend never independently regenerate.

T005 is complete: reuse the reviewed frozen-contract gate rather than reimplementing it.
T024 remains the mandatory infrastructure checkpoint, with every existing dependency; early
fixture/static work cannot satisfy it. T033 explicitly requires verified T024, T026, T030 and
T032; T034 reviews actual infrastructure and real discovery evidence. Do not mark either
milestone complete from mock results, implement component features or take over owner files.

Provide the same full reviewed prompt-inclusive commit to all three component owners. Record
exact component commits/image references, task IDs and handoff evidence. Have QA build selected
clean Backend/Frontend contexts with isolated projects/databases/ports; do not silently test old
QA-checkout component code. Review results and request human approval before each merge.

## Backend — isolated Backend checkout

You own `backend/**`, including its Dockerfile, models/migrations, private test support, tests,
worker and maintenance CLIs. T002, T015 and T018 are complete. The next proposed assignment,
only after separate execution authorization, is T007 finalization against its original image,
lock, timezone, exclusion, test and CLI-interface acceptance; then T009 once T007 completes.
Do not change the unfinished T007 worktree or its branch as a side effect of another task.
No zero-image-vulnerability gate is added to T007: retain known security findings and remediation
requirements, with unresolved critical risks blocking production deployment. All other Backend
dependencies remain in force, including T024 before Backend story implementation.
T030 must pass the authored T026 suite against its actual Backend before completion; T033
reruns the suite against the selected combined candidate. Do not implement later features
merely because they are described below.

For later authorized behavior, use Python 3.12/FastAPI, synchronous SQLAlchemy/psycopg transactions,
Alembic and PostgreSQL 16 against the frozen API. Administrator authentication uses **opaque bearer
sessions**, server-side hashed token verifiers and a fixed **60 elapsed minutes** from login.
The server rejects expired sessions, including after lock waits; no renewal/refresh/grace period.
The browser keeps the token only in memory. Do not implement JWT-based authentication.

Preserve PostgreSQL's partial exclusion constraint for same-activity confirmed half-open intervals.
Revalidate availability inside transactions; refresh configuration and DB wall-clock time after
waits and follow attempt → activity → booking → contact lock order. Implement the approved
[retry protocol](../specs/001-appointment-scheduling/contracts/retry-protocol.md), not a timeout-to-pending
shortcut. Never confirm before known durable commit or treat an unknown commit as proven rollback.

Backend owns private clock/fault adapters and test-only server/worker factories; they add no HTTP
control routes or production test switches. QA owns host Compose lifecycle control. T-02 remains
provisional until real PostgreSQL concurrency/idempotency/crash/timeout verification proves
RP-01–17. T-03 remains conditional on verified 720-hour deletion/read suppression, contact-free
backup/restore and hosting controls. Do not weaken either gate or claim mock fixtures prove durability.

## Frontend — isolated Frontend checkout

You own `frontend/**`, including its Dockerfile, **except** Lead-owned
`frontend/src/api/schema.d.ts`. Consume that frozen generated file read-only; do not edit it,
run independent API generation or introduce parallel DTOs. Use the same frozen API as Backend.

T003 and T008 are complete. After separate execution authorization, the independent discovery
assignment is T027→T031→T032; it does not wait for T024. T027 depends on T003 and uses its
fixtures plus frozen generated types. Collect/typecheck and record meaningful expected-red
missing-UI assertions; setup failures are not behavioral evidence. T031 depends on T027 and
must pass catalog/detail fixture cases through the production typed client with test-only network
interception. Record remaining date/slot failures awaiting T032 honestly. T032 depends on T031;
its full discovery fixture suite and existing Frontend regressions must pass without a feature
Backend. Never add a production mock mode, alternate DTO or client-side availability engine.

T031 may update the obsolete scaffold-render assertion in `frontend/tests/scaffold.spec.ts`,
preserving all other T003 contract/privacy/report checks. T032 may wire
`frontend/src/features/catalog/ActivityDetail.tsx` after T031; no concurrent writer of that file.
Fixtures prove UI behavior only. T033/T034 still require verified T024 infrastructure, the
real Backend and all US1.1–8 outcomes. Do not begin booking or administrator tasks without
their own dependencies and authorization.

For later authorized sessions, keep opaque bearer tokens **in browser memory only**: no localStorage,
sessionStorage, persisted cache, URLs or auth cookies. Reload requires login. On server 401/expiry,
clear or lock protected state and remove passwords/guest-contact drafts; retain only permitted
non-sensitive configuration drafts for review and explicit resubmission. Do not decode JWT claims,
renew sessions or automatically replay writes. Server-side expiry is authoritative.

Use server-returned UTC slots and generated response unions; display the approved IANA timezone
and distinct repeated-time offsets. Do not calculate independent availability or automatically
replace an uncertain booking's private retry identifier. Missing/error/pending/unknown outcomes
must remain distinguishable from verified success. Hand Backend/API mismatches to the Lead.

## QA/DevOps — isolated QA checkout

You own `tests/**`, including `tests/Dockerfile`, `.github/**`, root Docker Compose/test overlays
and CI. You do not own `backend/Dockerfile`, `frontend/Dockerfile`, Backend test hooks, shared
architecture/contract documents or component implementations. Ask the relevant owner for fixes.
QA may wire the authorized Lead-owned contract verification entry point into CI; it must not
edit canonical/generated outputs or accept regeneration drift independently.

T004 and T006 are complete. After separate execution authorization, independently author T026
and prepare the static T022 checkpoint, sequencing work within the QA lane as needed.
T026 depends on T004/T005: collect reviewed discovery operation/status/header/privacy assertions
and validate their oracles against frozen API v1. Authoring can finish with documented expected-red
assertions while real-backend verification remains pending. The existing `http_client` is a
MockTransport fixture; distinguish fixture self-checks from an explicitly guarded live client.
Missing live infrastructure fails closed, never falls back to fixtures. T030 must pass the suite
against the actual Backend, and T033 reruns it against the combined candidate.

T022 preparation starts after T004/T008: prepare only its existing Compose/overlay/runner paths,
T008 browser API-origin wiring, selected contexts and guard/configuration checks. Keep missing
runtime inputs/Backend CLIs explicitly blocked; no fake readiness or CLI success and no lifecycle,
migration, crash or restore execution under this preparation checkpoint. T022 remains unchecked
until T007, T008, T009, T017, T020, T021 and T004 are complete and all its original runtime
acceptance passes. T023 still requires completed T022. Static checks are not runtime proof.

Black-box acceptance tests consume the frozen OpenAPI/API v1 without importing Backend application
modules. QA's guarded host runner owns restart/crash/restore orchestration for explicitly approved
disposable targets; containers have no Docker socket. Backend owns injected clock/fault adapters.
Container contract/privacy tests inspect prepared fixtures/restored rows, not privileged lifecycle
operations. Do not run recovery/destructive drills without the named disposable-scope authorization.

Record component commits, image IDs/digests, selected build contexts, isolated projects/databases/
ports and actual assertions in one candidate manifest. Mutating suites hold an exclusive target
run lock; intentional race cases use independent connections to the same case DB. Publish only
sanitized evidence to ignored `test-results/<run-id>/`; raw streams/control/payloads/dumps stay
private. Missing, zero, mixed-candidate or skipped mandatory evidence fails verification.

T024 is the first infrastructure checkpoint; T034 adds discovery/US1.1–8 without requiring later
booking/auth/restore work. Final acceptance requires all 31 FRs, 19 SCs, 77 scenarios and 18 API
operations, with all RP-01–17 and T-03 privacy/recovery obligations. Prepared fixtures are not
runtime proof. T-02 stays provisional and T-03 conditional until their evidence is reviewed.

## Handoff required from every role

Report scope/files, full source/task/contract/common-baseline revisions, completed task IDs,
exact commands and observed results, redacted evidence locations, unresolved questions/limitations,
and contract/migration change flags. Obtain review before integration; stop at the boundary of
assigned tasks. Do not launch other agents or silently expand the batch.

## Independent assignments — not started by this amendment

After separate task/setup/launch authorization, use the same reviewed amendment-inclusive
commit for the three isolated component checkouts. Do not serialize fixture or static authoring
behind Backend delivery; synchronize safely without discarding unfinished T007 work.

| Agent | Proposed independent scope | Later gate |
| --- | --- | --- |
| Backend | Finalize T007, then T009 after T007 completes | Original task acceptance; Backend story work still waits for T024 |
| Frontend | T027→T031→T032 with frozen typed fixtures | T033/T034 require actual Backend discovery after T024 |
| QA/DevOps | T026 authoring and T022 static preparation after their own start prerequisites | T022 full runtime dependencies; live T026/T033 results and T034 review |

These are approved plan assignments, not execution or launch authorization. No task, worktree
or agent is started by this document change; commits/pushes/merges retain their scoped permissions.
