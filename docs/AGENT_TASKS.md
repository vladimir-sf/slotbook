# Agent ownership and milestones

## Relationship to generated feature tasks

This document defines shared directory ownership, integration responsibilities, and project
milestones. It is not a replacement for Spec Kit's feature task lists.

Each `specs/<feature>/tasks.md` (or the explicitly selected feature directory) contains the
executable task IDs, dependencies, file paths, acceptance links, and verification work derived
from that feature's reviewed `spec.md` and `plan.md`. Generated tasks must respect this document
and the constitution; they do not grant implementation approval or change ownership.
Ownership conflicts must be resolved with the lead before affected work begins. Approved
changes must be reflected in both this ownership guide and affected feature tasks.

The approved feature specification is `specs/001-appointment-scheduling/spec.md`, including
approved A-001/A-003 and clarified A-002 (2026-10-25), with 77 acceptance scenarios. The
feature plan and design artifacts were formally approved by the human project owner on
2026-10-25 as the R-003 technical design baseline. T-01/T-04 are approved; T-02 remains
provisional pending PostgreSQL concurrency/crash/timeout/idempotency verification; T-03 remains
conditional on validated contact-free backup and hosting controls.

The reconciled API v1 was frozen at `adc0b83a4408493ac44d3a7571dfd3d25a758679`.
The 92-task plan and execution protocol were approved and committed at
`04bb7ed4e7a83244cb8d84de2a6cd8901b8b2419`. On 2026-10-25 the human authorized **T001 only**:
prepare the Lead baseline/interface/isolation handoff. The human subsequently authorized its
finalization and local documentation commit. T002–T092, worktree creation, agent launch,
push, merge, deployment and recovery remain unauthorized.

Current handoff and verification status: [IMPLEMENTATION_BASELINE.md](IMPLEMENTATION_BASELINE.md).
Execution details: [EXECUTION_PROTOCOL.md](EXECUTION_PROTOCOL.md). **T001 is complete:** its
handoff was committed and verified before marking completion, then the completion metadata was
finalized in the new local baseline. Preserve the unrelated local README edit. Component
ownership below is unchanged. The legacy
AGENT_PROMPTS.md must be corrected and reviewed before agents use it: JWT and Frontend API
generation instructions conflict with the approved opaque-session and Lead-ownership rules.
Its QA scope/full-feature directions must also match the actual authorized task handoff.

## Phase 0 (Lead agent + human) — T001 handoff and release gates
1. Use the approved specification/design and frozen API; do not rerun prior phases or change scope.
2. Prepare and verify T001's source hashes, component/CLI interfaces and isolation/evidence handoff.
3. Use the human's T001 finalization/commit authorization to publish the reviewed shared descendant;
   verify its committed contents before completing T001 and report its full final revision.
   Exclude the unrelated README change. No push or other task execution is authorized.
4. T001 acceptance has passed; T002–T005 are dependency-ready but unstarted. Obtain separate
   authorization for the selected next task batch and its isolated checkouts; this T001-only
   turn creates none and launches no agent.

## Phase 1 (parallel)
| Agent | Exclusive ownership | Deliverable | Checks |
|---|---|---|---|
| Frontend | `frontend/**`, including `frontend/Dockerfile`, except Lead-owned generated API definitions | Public activities/slots/booking flow; admin login and views; typed API calls | TS build, component tests |
| Backend | `backend/**`, including `backend/Dockerfile` | DB models/migrations, REST endpoints matching contract, validation, auth, exclusion constraint | pytest, integration/concurrency tests |
| QA / Platform | `tests/**`, `.github/**`, root Compose/Docker/CI configs; no component Dockerfiles | Playwright scenarios, CI, Compose readiness and deployment instructions | E2E green, CI green |

Agents may READ any files. They must not silently EDIT another agent's area.
Approved T-04 (2026-10-25): Lead owns canonical `contracts/**`, generated OpenAPI and
`frontend/src/api/schema.d.ts`; Frontend treats that generated file as read-only. Lead also
owns reviewed PRD/architecture/ADR/feature reconciliation. Only the lead changes canonical or
generated API definitions after the corresponding contract proposal is reviewed; routine
regeneration is not permission to change the source contract. Component owners publish image/CLI
interfaces to QA; QA changes root Compose/CI rather than editing component Dockerfiles.
An explicitly approved task scope permits routine, non-force pushes of its changes to its
isolated feature branch unless restricted by the human. Merges, deployments, destructive
operations, force pushes, and pushes to shared integration/default/protected branches require
separate human review and explicit approval. A feature-branch push is not merge approval.

## Phase 2 (integration)
1. Owners hand off clean exact component commits, interface details and test evidence.
2. QA builds their selected contexts/images and verifies the combined candidate with isolated
   projects/databases/ports before branch merges, following EXECUTION_PROTOCOL.md.
3. Lead reviews Backend, Frontend and QA changes and evidence. Human review and explicit approval
   precede each merge; no unattended or unchecked merging.
4. Rerun the required contract/acceptance regressions after authorized integration changes.
5. Security/privacy/hosting review and separate deployment approval remain required. T-02 stays
   provisional and T-03 conditional until their mandatory evidence is reviewed.

## Definition of Done
- `docker compose up --build` starts all services.
- Seeded test admin and sample activity can be used locally.
- User can find slot, book, see confirmation.
- Two simultaneous distinct-attempt requests for one slot -> exactly one 201, one 409;
  matching same-key retries converge on one booking/result under the approved protocol.
- Admin can log in, manage activity/availability, block a date, see and cancel booking.
- Contract generation, static checks, integration and E2E tests pass in CI.
- README documents env, migrations and local setup.
