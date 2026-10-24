# Agent ownership and milestones

## Phase 0 (Lead agent + human) — sequential; contract freeze
1. Review PRD and ADRs; run Spec Kit `constitution/specify/clarify/plan/tasks/analyze`.
2. Approve TypeSpec endpoints/errors, API time conventions, auth and status transitions.
3. Compile OpenAPI, commit all shared artifacts, tag `contract-v1` (optional).
4. Only then create the three worktrees.

## Phase 1 (parallel)
| Agent | Exclusive ownership | Deliverable | Checks |
|---|---|---|---|
| Frontend | `frontend/**` | Public activities/slots/booking flow; admin login and views; typed API calls | TS build, component tests |
| Backend | `backend/**` | DB models/migrations, REST endpoints matching contract, validation, auth, exclusion constraint | pytest, integration/concurrency tests |
| QA / Platform | `tests/**`, `.github/**`, root Docker configs | Playwright scenarios, CI, Compose readiness and deployment instructions | E2E green, CI green |

Agents may READ any files. They must not silently EDIT another agent's area.
Only lead changes `contracts/**` and `docs/PRD.md` after a proposed change is reviewed.

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
- Two simultaneous booking requests for same slot -> exactly one 201, one 409.
- Admin can log in, manage activity/availability, block a date, see and cancel booking.
- Contract generation, static checks, integration and E2E tests pass in CI.
- README documents env, migrations and local setup.
