# ADR-0001: Contract-first development

Status: Accepted for MVP

- Source: `contracts/main.tsp` under lead ownership.
- Generated: OpenAPI YAML, then client-side TypeScript declarations.
- Backend endpoint implementation must conform to OpenAPI; generated definitions are not editable source.
- Breaking changes require PRD/contract update before the frontend and backend accept them.
- Why: lets independent agents work without inventing incompatible data models.

## Documentation alignment — 2026-10-25

This supplement reconciles the existing decision with the approved technical design at
`5f1ce85bc16b25541337b5ef55d6f25d7b3a574d`; Accepted for MVP status and the original rationale
above are retained. No original acceptance date/approver is invented. At C-002 review the
canonical contract was still a candidate; the subsequent human-approved API-v1 freeze is
recorded below.

Lead owns canonical TypeSpec, generated OpenAPI and `frontend/src/api/schema.d.ts`; Frontend
consumes the generated declarations as read-only (approved T-04). Compile with
`npm run build --prefix contracts`, then `npm run generate:api --prefix frontend`.
Regeneration must produce identical outputs. CI conformance/drift checks are planned, not
already implemented or proven by the existence of generated files.

Review includes operation IDs, all body/status/error variants, response headers, authentication,
contact-free public responses and present/removed admin contacts. Generated TypeScript is not a
runtime validator; Backend/QA must check actual successful/error responses against generated
OpenAPI, including malformed JSON and authorization precedence. Framework-generated OpenAPI
cannot replace the canonical source. No private frontend/backend JSON formats are permitted.

Human review/freeze and a committed common contract baseline precede dependent implementation
on isolated worktrees. Subsequent task generation and agent work remain subject to the user's
phase authorization; implementation, merges and deployment retain their approval gates. This supplement adds verification/ownership detail to the same contract-first
decision; it neither approves this candidate nor authorizes implementation.

## API-v1 freeze — 2026-10-25

The human project owner formally approved the C-002 canonical contract and authorized freezing
API v1 (1.0.0) as the shared interface baseline. See the
[freeze/revision record](../specs/001-appointment-scheduling/contracts/canonical-review.md#api-v1-human-approval-and-freeze).
This records the new contract approval, without changing this ADR's original acceptance history.

After freeze, Lead alone coordinates TypeSpec changes and regeneration. Frontend and Backend
must not edit canonical/generated API files independently. Proposals must identify motivation,
affected requirements, compatibility, impacted agents, migrations and validation. Lead reviews
the proposal; the human explicitly approves material specification/API changes before affected
implementation. Reconcile PRD/spec/plan/ADRs/contract as applicable, regenerate OpenAPI/TS,
review the diff and required checks, then establish a reviewed common baseline before dependent
work resumes. A breaking shape/status/security/semantic change cannot be smuggled into a generated
file or treated as a routine regeneration. Apply the constitution's editorial exception only to
non-semantic corrections with unaffected gates preserved.

This freeze does not authorize tasks, implementation agents, application work, merges, pushes or
deployment. T-02 remains provisional and T-03 conditional on their documented runtime/operational
verification. No new architecture decision or relaxation of either condition is introduced.
