# SlotBook Constitution

## Core Principles

### I. Specification First

Requirements, scope, observable acceptance criteria, and relevant failure cases MUST be defined
before feature implementation. Contributors MUST read `AGENTS.md`, the README, PRD,
architecture, applicable ADRs, canonical API contract, feature artifacts, and assigned tasks.
Feature specifications MUST refine the PRD without silently changing it. Decisions affecting
implementation MUST be clarified, recorded, and reviewed before dependent work begins.
Plans MUST connect requirements to design, ownership, and verification. Generated artifacts
and a running scaffold are not evidence of approved requirements or completed behavior.

### II. Contract First

`contracts/main.tsp` MUST remain the source of truth for the REST API. OpenAPI MUST be compiled
from TypeSpec, and TypeScript API declarations MUST be generated from that OpenAPI. Generated
artifacts MUST NOT be edited as independent sources of truth. Frontend and backend MUST NOT
invent private JSON formats, fields, endpoints, or error responses.

The lead MUST own canonical contract changes and assess compatibility before regeneration
and dependent implementation. Mismatches among specifications, architecture, contract,
generated artifacts, and actual routes MUST be reported. Affected work MUST pause for the
approved-change process in Governance. Shared contracts preserve interoperability.

### III. Multi-Agent Development

Frontend, Backend, and QA/DevOps agents MUST have explicit ownership, dependencies, acceptance
criteria, and handoff requirements. Concurrent agents MUST use dedicated branches in separate
Git worktrees or independent checkouts, starting from the same reviewed, committed baseline.
Branches alone in a shared working directory do not provide isolation.

`docs/AGENT_TASKS.md` MUST define shared directory ownership and integration responsibilities.
Each feature's generated `tasks.md` MUST define its executable tasks within those boundaries;
it MUST NOT silently override shared ownership or authorize implementation. Changes outside
assigned directories MUST have lead approval. Canonical contract and PRD edits remain lead-owned.
Agents MAY read other areas to understand integration requirements.

Agent-authored code MUST be treated as untrusted until reviewed; unchecked automated merging
is prohibited. Handoffs MUST identify scope/files, specification and contract revision, exact
check commands/outcomes, unresolved questions, limitations, and contract or migration changes.

### IV. Test-Driven Verification

Every behavioral change MUST include appropriate unit, integration, and E2E coverage for
successful behavior and relevant negative/error paths. Verification MUST exercise contracts,
authorization, time handling, and database constraints where affected. Race-safety claims MUST
be demonstrated with simultaneous requests or transactions against PostgreSQL.

Contributors SHOULD write a failing test before implementing behavior to verify that the test
detects the missing behavior. A different sequence MUST be explained in the handoff; acceptance
and regression coverage remain mandatory. Required tests and checks MUST pass before merging.
Exact commands and outcomes MUST be reported; blocked, unrun, or failing checks MUST NOT be
represented as passing. Documentation-only changes require applicable document checks rather
than unrelated application test runs.

### V. Code Quality

Code MUST be maintainable, typed at application and API boundaries, and modular with clear
responsibilities. Changes MUST satisfy configured type, build, lint, and formatting checks
applicable to their scope. New dependencies and architectural abstractions MUST be justified.
Contributors SHOULD prefer cohesive modules, explicit data flow, and existing stack capabilities
because they reduce maintenance and review effort. Speculative complexity SHOULD be avoided
until an approved requirement justifies it. Type-checker escapes or weakened validation MUST
have a reviewed reason and MUST NOT bypass contracts, security, or booking invariants.

### VI. Infrastructure

The application MUST be reproducible with Docker Compose and PostgreSQL. Prerequisites,
environment configuration, dependencies, migrations, and synthetic development seeds MUST be
documented. Schema changes MUST use reviewed, reproducible migrations. PostgreSQL-specific
behavior MUST be tested against PostgreSQL. CI MUST check contract generation, application
builds/tests, and required acceptance coverage. Dependency versions SHOULD be locked where
supported to reduce environment drift. Stack choices and startup details belong in
`docs/ARCHITECTURE.md`, ADRs, and the README and MUST follow architectural change review.

### VII. Security and Correctness

Inputs MUST be validated at trust boundaries. Authorization MUST be enforced on protected
operations. Credentials MUST be protected with password hashing and appropriately limited
sessions/tokens. Operational secrets MUST come from runtime configuration; `.env`, tokens,
API keys, and operational credentials MUST NOT be committed. Example credentials MUST be
clearly development-only. Agent work and tests MUST NOT use real customer data. Responses MUST
NOT expose operational secrets; authentication tokens MUST be returned only through the
contracted authentication flow. Logs MUST NOT expose credentials, tokens, or guest contact data.
Public activity/availability responses MUST NOT expose guest contact data.

The server MUST revalidate booking availability within the transaction. PostgreSQL MUST
prevent overlapping confirmed bookings under concurrent requests; application queries alone
are insufficient. API instants MUST use UTC, and availability/display MUST use IANA timezones
with timezone-aware handling, including DST boundaries. Detailed booking outcomes, interval
semantics, and API status codes belong in the PRD, feature specifications, contract, and ADRs.
Security and privacy review, including retention/deletion policy, TLS, CORS, token storage,
and CSRF risks, MUST precede public deployment.

### VIII. Human Approval

Agents MUST stop for explicit human review and approval after specification/clarification,
after planning, and before implementation. Each gate MUST present identifiable artifacts,
open decisions, risks, and the next proposed phase. Approval of one phase MUST NOT authorize
later phases. Before implementation, approval MUST cover task scope, ownership, acceptance
checks, and the frozen contract. Material changes MUST reopen affected approval gates.

Approval of a task scope authorizes routine, non-force pushes of that task's changes to its
isolated feature branch unless the human restricts that authorization. It MUST NOT authorize
pushes to shared integration/default/protected branches, force pushes, merges, deployments,
or destructive operations. Those actions MUST receive separate human review and explicit
approval. A branch push is not approval to merge. Agents MUST NOT infer approval from a date,
a version label, generated tasks, passing checks, or an earlier unrelated action.

## Scope and Architecture Constraints

Durable engineering rules belong here. Functional acceptance criteria and unresolved product
choices belong in `docs/PRD.md` and feature `spec.md` files; design decisions belong in
`docs/ARCHITECTURE.md` and ADRs; API definitions belong in TypeSpec. Contributors MUST preserve
traceable requirements when moving detail between documents. The MVP scope and exclusions in
the PRD MUST NOT be expanded without human approval.

ADR-0001 and ADR-0002 are marked Accepted for MVP in the existing records. Those labels do not
establish who approved them or when. This revision preserves their contract-first and database
integrity requirements without claiming a new architectural approval. Changes to a recorded
architectural decision MUST include an updated or superseding ADR, impact analysis, lead review,
and human approval before implementation.

## Development Workflow and Quality Gates

1. Inspect the working tree, report unexpected modifications, and preserve unrelated work.
   Read the governing documents and establish the feature specification and acceptance criteria.
2. Complete specification/clarification, then STOP for human approval before planning.
3. Produce a plan covering architecture, contract, migrations, security, ownership, tests,
   and constitution compliance, then STOP for human approval before task decomposition.
4. Generate feature tasks consistent with `docs/AGENT_TASKS.md`, analyze cross-artifact
   consistency, and resolve blocking issues. Review/freeze the shared contract and baseline.
   STOP for human approval of implementation scope, ownership, and checks before agents code.
5. Implement approved tasks in assigned areas, run required checks, and submit reviewable
   changes with execution evidence. Routine feature-branch pushes follow Principle VIII.
   Human review and approval MUST precede merges; reviewers MUST examine code and API diffs.
6. Declare a feature complete only when its approved acceptance criteria and required checks
   pass. Declare the MVP complete only against the approved product specification. Deployment
   and destructive operations remain separately reviewed and authorized.

## Governance

MUST, MUST NOT, and REQUIRED identify mandatory rules. SHOULD and SHOULD NOT identify
recommendations: an alternative requires a documented reason and tradeoff. MAY identifies an
optional choice. Recommendations MUST NOT weaken mandatory rules.

`AGENTS.md` supplies operating instructions. The PRD, architecture, ADRs, canonical contract,
and feature artifacts retain their respective roles. Conflicts MUST be raised to the lead and
human rather than silently resolved. Plans, PRs, and integration reviews MUST assess compliance.

Material changes to an approved specification MUST start with a proposal explaining rationale,
affected acceptance criteria, compatibility, impacted agents, tests, and migration consequences.
The lead MUST review it and the human MUST approve it. Owners MUST reconcile the affected
specification, plan, tasks, ADRs, contract, and derived artifacts before dependent work resumes.
Affected approval gates MUST reopen. Editorial corrections MAY be reviewed without reopening
unaffected gates when they do not change behavior, scope, or design.

Exceptions to recommendations MUST record rationale. Exceptions to mandatory constitutional
rules MUST be proposed as prospective amendments with scope, risks, compensating controls,
owner, and applicable expiry/remediation conditions. Lead review and explicit human approval
MUST precede affected work. Agents and passing checks cannot grant implicit waivers. Unresolved
mandatory violations or missing required evidence MUST block merge/completion.

Amendments MUST explain changed principles, compatibility/workflow impact, and follow-up work.
Versioning MUST use MAJOR for incompatible principle/governance redefinitions, MINOR for added
principles or materially expanded guidance, and PATCH for non-semantic corrections. The
1.2.0 amendment clarifies scoped push authorization and task authority and corrects approval
metadata while retaining the eight principles and safety requirements.

Approval records MUST identify the human decision, artifact revision, and actual decision date.
The human project owner explicitly approved and authorized formal ratification of version 1.2.0
on 2026-10-25, approving source Git blob `1380354c28160bba448e9b503af27e263c51a023`.
This is the first recorded human ratification. The earlier 2026-10-24 ratification/amendment
labels were entered by the agent and are not approval evidence. Preserve the actual ratification
date in subsequent amendments and record each actual amendment-approval date. Draft-edit dates
MUST NOT stand in for approvals. This approval authorizes technical planning; it does not approve
a technical plan, concrete contract changes, implementation, merges, or deployment.

**Version**: 1.2.0 | **Status**: Ratified
**Ratified**: 2026-10-25 | **Last Amended**: 2026-10-25
