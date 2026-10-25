# T001 — SlotBook implementation baseline and handoff

Recorded: 2026-10-25. Owner: Lead/Architect. Status: **T001 complete**. The reviewed handoff
was committed and verified before the completion marker was set; the local baseline now
includes that completion record. The human authorized **T001 finalization and its documentation
commit only** against task baseline
`04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419`. H0 is satisfied for that scope, not for
T002–T092, worktree creation, agent launch, push, merge, deployment or recovery.
No application feature, harness or infrastructure resource is implemented by this task.

## Scope and acceptance

T001 publishes baseline provenance, component interfaces and isolation/evidence handoffs,
and corrects historical status in the [ownership guide](AGENT_TASKS.md) and
[execution protocol](EXECUTION_PROTOCOL.md). The approved task definition/dependencies are
unchanged in [tasks.md](../specs/001-appointment-scheduling/tasks.md).

The human authorized publication in local Git; no remote push is authorized. The reviewed
handoff was first committed with T001 open. Its committed contents, source preservation and
four-file scope passed verification; only then was T001 marked complete. The completion record
is finalized in that new, unpushed local baseline. Its full resulting hash is reported after
finalization, not embedded in its own contents. Future owners must pin that reported release
commit, a descendant of the task input below, before starting. No owner acknowledgment,
checkout or runtime is claimed before it actually exists.

## Verified input revisions

Verified input branch: `001-appointment-scheduling`. HEAD at the start of T001, and reviewed task/protocol input commit:
`04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419`.
Frozen API v1 commit: `adc0b83a4408493ac44d3a7571dfd3d25a758679`.
The reviewed task commit descends from the frozen API commit. Approved product/design sources
and canonical/generated API files match their committed input bytes.

| Input at the task baseline | Full Git blob ID |
| --- | --- |
| `AGENTS.md` | `a61aa470806669cdee6a57e46c123cde8d5dde4b` |
| `.specify/memory/constitution.md` | `40b425d8053778d8abe64e72489b946924370d03` |
| `specs/001-appointment-scheduling/spec.md` | `5cc968b5cbf3ac899b6c46973c2cbd31862e7cde` |
| `specs/001-appointment-scheduling/plan.md` | `24b65dd4bf027390254374a729cf81864d193780` |
| `specs/001-appointment-scheduling/tasks.md` | `f4a387cc33994c2cf0da8f31576c2f0214ba5371` |
| `docs/EXECUTION_PROTOCOL.md` | `4ec3d5044bb405dc5f00bc076d6d0b6932225d11` |
| `contracts/main.tsp` | `b5076047fef868a17590d00e5c93753d8e67f044` |
| `contracts/tsp-output/@typespec/openapi3/openapi.yaml` | `3ad47840cc0dd120d070599e9fad218230f4a845` |
| `frontend/src/api/schema.d.ts` | `4b6a9b438f9ed60e8e271acd2b901a9376c738be` |

These are input revisions, not hashes of the finalized T001 output documents. All 31 FRs, 19 SCs,
77 scenarios and 18 operations remain approved; the requirements checklist remains 16/16.
T-01/T-04 are approved, T-02 provisional and T-03 conditional. No runtime proof is inferred.

| Component | Input commit | Input tree ID | Implementation handoff status |
| --- | --- | --- | --- |
| Backend | `04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419` | `b0e69b87c1361bce13cb2dd65f56ff727e2a107f` | Scaffold only; no implementation branch/worktree or new component commit |
| Frontend | `04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419` | `b6b37ac03533f25bc9af49c6b9a4b30c5d097e92` | Scaffold only; no implementation branch/worktree or new component commit |
| QA `tests/` | `04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419` | `a470b1159d565eca582f0e4f0a6cdaf49e079cbc` | Contains `tests/e2e/README.md`; no harness/QA image/CI workflow yet |

The existing README edit is unrelated local work, preserved byte-for-byte and excluded from
T001 publication. Do not build candidate images from this dirty checkout or silently include
the README in this or a subsequent T001 commit. No machine-specific checkout path is part
of this record.

## Component interface handoff

This is the required interface inventory from the approved design/tasks. Planned commands are
not claimed to exist or have been run. T002/T003/T004 provide tooling, T007/T008 images, and
T022 guarded Compose wiring; none is authorized by this record.

| Owner | Build/runtime interface | Existing versus required |
| --- | --- | --- |
| Backend | Context `backend/`, component-owned `backend/Dockerfile`, `/app`, API port 8000; `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Current image adds development reload; only `/health` is implemented. T007 publishes pinned image/lock, migration/seed/worker/status/backup/restore interfaces. |
| Frontend | Context `frontend/`, component-owned `frontend/Dockerfile`, `/app`, port 5173; `VITE_API_BASE_URL` identifies the browser-reachable API origin | Current image runs the Vite scaffold. T008 must state build/start origin behavior so QA can inject its assigned loopback API port; no reverse proxy or new API format is added. |
| QA/DevOps | `tests/Dockerfile`, root Compose and test/integration/fault overlays; host runner at `tests/harness/runner.py` | Not implemented. T004 defines/guard-tests tooling; T022 wires exact selected component contexts, internal DB/API networking and host-only lifecycle control. |
| Lead/Architect | Frozen TypeSpec/OpenAPI/generated TS, approved documents and shared verification scripts | Component owners consume the 18-operation API unchanged. T005 supplies drift/schema/type verification scripts after separate authorization. |

Backend migration and maintenance interfaces already named by the tasks are `alembic upgrade head`,
`python -m app.cli.seed`, `python -m app.workers.retention`,
`python -m app.cli.retention_status`, `python -m app.cli.backup` and
`python -m app.cli.restore`. They are future deliveries, not runnable modules today. Their
implementation owners must publish flags, guarded runtime inputs, exits and redacted diagnostics
before QA invokes them. This record does not invent restore flags or authorize their execution.

Python 3.12, Node 22, PostgreSQL 16 and locked tools/images/tzdata remain the agreed constraints.
Default production time uses DB wall-clock samples, authorization uses fixed 60-minute opaque
sessions, and all contract changes remain Lead-owned. No raw credentials, tokens, DSNs or secrets
belong in these handoffs; provide them only through private runtime configuration.

`docs/AGENT_PROMPTS.md` is a legacy source, unchanged by T001 and **blocked as an agent input
until corrected and reviewed**. Required pre-use corrections are:

- Replace Backend JWT instructions with the approved opaque bearer/session-verifier design,
  fixed 60-minute lifetime and memory-only browser storage (T-01).
- Remove Frontend-owned API generation; canonical TypeSpec, generated OpenAPI and generated
  TypeScript remain Lead-owned/read-only to component agents (T-04).
- Align its broad QA deployment-document instruction and full-feature/commit directions with
  shared directory ownership and each separately authorized task scope.

No agent may silently receive the stale file. Any later agent launch still requires explicit
scope authorization and a reviewed task-specific handoff; T001 does not authorize correcting
that legacy file, launching agents or executing their tasks.

## Isolation plan — naming conventions only, no resources created

| Lane | Proposed checkout label | Proposed branch | Compose project template | Test database template |
| --- | --- | --- | --- | --- |
| Frontend | `slotbook-frontend` | `feat/frontend` | `slotbook-fe-<run-id>` | `slotbook_fe_<run_id>` |
| Backend | `slotbook-backend` | `feat/backend` | `slotbook-be-<run-id>` | `slotbook_be_<run_id>` |
| QA/DevOps | `slotbook-quality` | `feat/quality` | `slotbook-qa-<run-id>` | `slotbook_qa_<run_id>` |

These are proposed relative labels/templates, not existing checkouts, refs, database names or
approval to create them. Before allocation, the Lead/QA check collisions and record the actual
values locally. Future owners must all start from the same reviewed published T001 descendant
of the task baseline; none receives uncommitted local files as its source of truth.

QA allocates distinct loopback API/UI host ports per run; **none is allocated now**. PostgreSQL
remains internal, with separate project/network/container/volume and test identities. Record
resolved ports, actual identities and approval scope in the private run manifest only after
provisioning is authorized. Mutating suites hold the project's exclusive run lock; intentional
race cases share their case DB via independent connections. Concurrent task verification uses
different projects/databases. No default developer DB, broad cleanup or Docker socket mount.

QA reads clean pinned component snapshots, builds their own component Dockerfiles and uses
`tests/compose.integration.yml` to remove stale QA-branch bind mounts. Candidate tests precede
human-approved merges; a changed source, image, script or overlay invalidates the candidate and
requires fresh evidence. No merge/cherry-pick is needed to combine artifacts for verification.

## Per-milestone manifest handoff

T004/T022 own implementation of the manifest/guard/collector interfaces. The inventory below is
the coordination schema, not an executable harness or a REST API schema. No synthetic run has
been represented as passing. Actual per-run manifests remain local and ignored.

| Required evidence field/group | Source and current state |
| --- | --- |
| Run ID, milestone and approved task subset | Allocate after the relevant authorization; no run exists now |
| Shared baseline, task/protocol source revision and frozen API revision | Input revisions recorded above; the final T001 release commit is reported with this handoff and must be pinned as the shared start revision |
| Backend/Frontend/QA and Lead-script commits | Initial source commits recorded above; later candidate refs must be clean descendants of the shared start revision |
| Contract blobs, lock hashes, image IDs/digests and platform | Frozen blobs verified; future locks/images are not built or verified by T001 |
| Resolved Compose fingerprint and component build contexts | QA records selected relative context identities plus local paths privately; no rendered secret-bearing environment is published |
| Project/network/container/volume/DB identities and loopback ports | Not allocated; validate unused names before provisioning, then record actual identities |
| Target/operation authorization and disposable-scope proof | T001-only authorization is not runtime, crash or restore authorization |
| Clock/fault mode, controlled versus production-clock evidence | Backend adapters and QA orchestration not implemented; never label a mock clock as durability proof |
| Exact commands, exit codes, test IDs/counts and assertion results | Per-milestone actual outputs only; T001 document-check outcomes are summarized below |
| Evidence path and open conditions | Ignored `test-results/<run-id>/` for sanitized reports; raw streams/control/fixtures stay in private temporary storage; T-02/T-03 remain open |

T024 first requires the foundation subset: schema/roles/migrations, cleanup, health/readiness,
static/unit checks and cold/repeat startup. T034 adds discovery/US1.1–8 with prepared schedules;
neither waits for later booking/auth/restore work. Later milestones map the full 77 scenarios
and RP-01–17. The runner must reject mixed-candidate or missing mandatory evidence.

## T001 verification and release gates

| Acceptance item | Current evidence/state |
| --- | --- |
| Approved input/source identities and branch | Verified against the committed task baseline; frozen files unchanged |
| Shared ownership and component/CLI handoff | Defined here and synchronized in the guide/protocol; interfaces explicitly label future deliverables |
| Isolation and per-milestone evidence handoff | Defined above; no actual resources, ports, test results or owner starts fabricated |
| Scope and confidentiality | README preserved; only T001 documents/task progress change; no secrets/personal host paths introduced |
| Publish the updated common handoff | PASS; reviewed handoff committed and verified in local Git before marking T001 complete; final baseline includes the completion record |
| Start other tasks/agents | **NOT AUTHORIZED**; no other task is started and no agent/worktree is created |

Applicable checks are Git identity/object comparisons, documentation links/format/secret checks,
task/dependency/coverage checks, scope/README preservation and unchanged worktree/branch inventory.
No application tests, dependency installation, image builds, regeneration scripts, database or
harness commands are required for this documentation-only work or claimed as runtime proof.

Document verification for publication (runtime suites are not run):

| Command/check | Result |
| --- | --- |
| `git branch --show-current`; `git rev-parse HEAD` | Expected branch and approved input verified at T001 entry; final release HEAD is reported after finalization |
| `git diff --exit-code 04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419 -- contracts/main.tsp contracts/tsp-output/@typespec/openapi3/openapi.yaml frontend/src/api/schema.d.ts` | PASS; frozen source and derived bytes unchanged |
| `git diff --check` | PASS; new-file whitespace also checked separately |
| Staged diff/path/blob checks | PASS; exactly the four reviewed T001 documents/progress files; README excluded and its input hash preserved |
| `git worktree list --porcelain` | One original checkout only; no worktree created |
| Python 3 temporary document verifier | PASS: input objects, README hash, 92 unchanged task definitions, dependency/ownership/coverage inventory, links, secret/path screening and scope; no application harness created |
| Shared T001 output commit/publication | PASS in local Git; verified before completion; no remote push or other task execution |

T001 is complete without changes to its acceptance criteria. T002–T005 are now dependency-ready;
each still needs separate execution authorization and none has started. The final full T001
release revision is reported for the later common-baseline handoff. The recommended first small
batch is T002 Backend tooling, T003 Frontend tests and T004 QA harness in isolated lanes,
with T005 Lead contract checks in parallel. Do not launch that batch from this document.
