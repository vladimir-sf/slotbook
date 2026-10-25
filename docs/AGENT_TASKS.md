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
conditional on validated contact-free backup and hosting controls. No feature tasks.md exists.
These decisions do not authorize implementation. PRD/ADR/TypeSpec reconciliation and separate
contract freeze remain required before dependent work.

## Phase 0 (Lead agent + human) — sequential; contract freeze
1. Review PRD and ADRs; run Spec Kit `constitution/specify/clarify/plan/tasks/analyze`.
2. Approve TypeSpec endpoints/errors, API time conventions, auth and status transitions.
3. Compile OpenAPI, commit all shared artifacts, tag `contract-v1` (optional).
4. Only then create the three worktrees.

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
1. Merge backend, verify endpoints agree with OpenAPI.
2. Merge frontend, run public/admin journeys.
3. Merge QA/Platform (resolve root Compose changes with lead).
4. Run E2E in Docker Compose and simultaneous booking stress test.
5. Review security and deployment; no deployment until human approval.

## Definition of Done
- `docker compose up --build` starts all services.
- Seeded test admin and sample activity can be used locally.
- User can find slot, book, see confirmation.
- Two simultaneous distinct-attempt requests for one slot -> exactly one 201, one 409;
  matching same-key retries converge on one booking/result under the approved protocol.
- Admin can log in, manage activity/availability, block a date, see and cancel booking.
- Contract generation, static checks, integration and E2E tests pass in CI.
- README documents env, migrations and local setup.
