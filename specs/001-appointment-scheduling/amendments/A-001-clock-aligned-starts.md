# A-001 — Activity-local clock-aligned appointment starts

**Status**: Explicitly approved product-specification amendment; technical-plan review pending.
**Approved / Recorded**: 2026-10-25, by the human project owner in this conversation.
**Authority**: Constitution 1.2.0, Governance material-specification-change process and
Principles I (Specification First), II (Contract First), IV (Verification), VIII (Human Approval).
**Origin**: Planning question P-01 and its recommended clock-quarter-hour option.
**Specification revision**: A-001, based on commit `e9f16809058fe826523bf8c19387b6ba65b8e145`
on actual branch `001-appointment-scheduling`.

## Approval and exact change

The human explicitly stated: “I approve clock-aligned 15-minute appointment starts” and
“Treat this as an explicitly approved amendment to the existing specification.” The human also
specified minutes 00, 15, 30, 45 in the activity's IANA timezone, a first eligible 09:15 start
for a 09:10 opening, complete window fit, and preservation of approved repeated-time offsets.

The resulting policy is exact local quarter-hour starts (seconds/fractions zero), anchored to
the activity timezone, independently of window opening and visitor display timezone. Offer and
submission checks use the same rule; reject off-grid instants without rounding/shifting. The
entire elapsed half-open interval fits one continuous valid portion of one configured window.
Nonexistent labels remain omitted/rejected; both otherwise eligible repeated occurrences remain
distinct UTC instants with distinct offset labels. No window is shifted, extended or merged.

This is the sole new approved product policy. The original fifteen clarification answers and
D-001–D-012 remain unchanged. The constitution remains ratified version 1.2.0: this changes
functional requirements, not constitutional principles, dates, or governance versioning.

## Rationale and lead review

The previous phrase “15-minute increments” did not establish its origin. During planning, the
lead identified clock-aligned versus window-relative starts, presented the tradeoff, and paused
the affected slot-grid decision. The human selected clock alignment. The planning agent reviewed
that choice against working-window, timezone, duration, DST and booking-preservation policies
and reconciled the affected feature artifacts. No constitutional exception is requested.

A 30-minute activity in an otherwise available 09:10–10:00 window offers 09:15 and 09:30;
09:10/09:25 are off-grid and 09:45 fails duration fit. A 09:10–09:40 window offers no start.
Window-relative starts were rejected by the explicit human choice. Working-window boundaries
remain unrestricted by this grid; only appointment starts must align.

## Scope, compatibility and migration impact

| Area | Impact / obligation |
| --- | --- |
| Specification | Refine FR-004/005 and SC-002; add US1.7–8, US2.16, US5.13 and edge case; update journey traceability and G-009 source follow-up. |
| Prior acceptance | Preserve all 61 existing scenarios and all 15 answers; add four scenarios, total 65. Keep 31 functional requirements and 19 measurable outcomes. |
| Checklist | Reevaluate the existing sixteen quality criteria; retain 16/16 with amendment-specific evidence and separate technical-plan approval status. |
| API semantics | Off-grid starts are ineligible; planned 400 slot_ineligible covers rejection. No new field is needed. PRD/TypeSpec wording and generated documentation require later reviewed reconciliation. |
| Data compatibility | This narrows the previously ambiguous start set. Existing confirmed bookings retain start/end/status, even if a future record is off-grid. No retroactive rounding, cancellation or interval rewrite. |
| Migration | No application booking tables/data currently exist in the scaffold, and no schema/data migration is introduced by this amendment. Do not backfill or rewrite historical booking intervals. |
| Frontend | Render server-returned eligible slots; do not align to window start/display zone or round submitted instants. Preserve UTC identity and repeated offset labels. |
| Backend | Enumerate exact activity-local quarter-hours with both valid folds; revalidate alignment and full continuous-portion fit at submission. Preserve existing-booking and completed-retry semantics. |
| QA/DevOps | Add unit/integration/E2E verification for off-grid opening, insufficient fit, exact window end, off-grid seconds/fractions, direct-request rejection, display-zone changes, and repeated/nonexistent starts. |
| Ownership | Lead owns source/contract reconciliation. Other components stay within proposed ownership and await separate implementation authorization. |

## Artifact reconciliation and approval gates

Updated: spec.md, checklists/requirements.md, plan.md, research.md, data-model.md, quickstart.md,
contracts/api-proposal.md and contracts/source-reconciliation.md. This record adds traceable
approval, scope, compatibility, agent, test and migration consequences. No tasks.md exists to
reconcile. Existing ADR-0002's interval/exclusion decision is unchanged; later source review can
reference this policy without claiming a new database architectural decision.

The affected product gate was reopened for P-01 and explicitly approved by the human through
this amendment. P-01 is now closed; no product question remains unresolved. The complete
technical plan, exact contract proposals, ownership exceptions and implementation gates remain
open for their respective human reviews. This approval grants no implementation, task generation,
agent launch, merge or deployment authorization. No application, canonical TypeSpec, PRD, ADR,
constitution, infrastructure or generated API file is modified by this amendment pass.

The earlier feature-finalization commit remains HEAD. Planning artifacts were already untracked;
this pass updates them in place and does not commit or push anything. Remaining technical
choices T-01–T-04 stay proposed for technical-plan review.

## Revision provenance

Pre-amendment committed specification blob: `af0fbc301dede9612332432922643d158a99cf48`.
Pre-amendment committed checklist blob: `a67cc1329a72e9d8114b2c5bf964a5858f45b894`.
Original human-approved source blobs remain recorded in each artifact; those original approval
records are not replaced with the later administrative metadata revisions above. The amended
artifact hashes recorded below identify this review package, not a Git commit or plan approval.

| Amended artifact | Git content blob (uncommitted) |
| --- | --- |
| spec.md | `f7c16d68337870fe0e4c4180fe94a69416960078` |
| checklists/requirements.md | `d27121736d320f10b5c1631792aa863ff1cfdd7d` |
| plan.md | `170389b8f37695e78edc470262dd9cfc8eb5e19f` |
| research.md | `a0387703a67ad34f6d39550fd3850b19b76943d8` |
| data-model.md | `e48b5343437d6374271e1f235e059bc25dde3fa8` |
| quickstart.md | `f886ca27e7941fb9b9f8087d5f8b01ccc9fce234` |
| contracts/api-proposal.md | `ffbf2497c483c98237169851e89cd83d2800fe54` |
| contracts/source-reconciliation.md | `beada53afee4df01b26f2930c13ce8d24d20f90b` |

## Verification performed

- `python3 /tmp/slotbook-verify-A-001.py`: passed preservation of the 15 original answers,
  twelve decision rows and all 61 old scenarios; verified four additions (65 total), scoped
  FR-004/005 and SC-002 refinements, 16/16 checklist, documentation links/fences/whitespace,
  resolved P-01, unchanged protected sources, branch and HEAD. The temporary verifier is local
  review tooling, not a committed application test or shared project dependency.
- `bash .specify/scripts/bash/check-prerequisites.sh --json`: passed; reported research.md,
  data-model.md, contracts/ and quickstart.md available for this feature.
- `git diff --check`: passed. Working changes are feature documentation only, remain uncommitted,
  and no implementation tests are claimed. Runtime behavior remains unimplemented.
