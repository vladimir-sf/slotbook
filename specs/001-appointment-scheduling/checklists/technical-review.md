# Technical-plan approval report — R-003

**Recorded**: 2026-10-25. **Branch**: `001-appointment-scheduling`.
**Parent specification baseline**: `e9f16809058fe826523bf8c19387b6ba65b8e145`.
**Formal technical-plan approval**: 2026-10-25, by the human project owner in this conversation.
The human formally approved the complete technical implementation plan, including A-001/A-002/A-003
and T-01–T-04, as recorded in the latest R-003 report (approved report Git blob
`d2ebc5c638efe8369f9f238b1e1ec353761c54b2`). The input artifact revisions are preserved below.
This establishes the technical design baseline. T-02 remains provisional pending PostgreSQL
concurrency, crash, timeout and idempotency verification; T-03 remains conditional on validated
contact-free backup and hosting controls. No condition is represented as satisfied.
The human explicitly authorizes approval-record finalization and the local documentation commit
`docs: approve SlotBook technical architecture`. Application code, PRD and canonical TypeSpec
changes, tasks, implementation, pushes, deployments and agents are outside this step.

## Decisions and remaining conditions

| Item | Recorded decision | Reconciliation / remaining condition |
| --- | --- | --- |
| [A-002](../amendments/A-002-durable-admission.md) | APPROVED WITH CLARIFICATION | DB-generated T persisted with E/binding in successful durable admission; E=T+24h, not commit metadata. Delayed COMMIT consumes validity; rollback admits nothing; uncertain COMMIT remains unverified. FR/SC/cases/design reconciled. |
| [A-003](../amendments/A-003-disaster-recovery.md) | APPROVED | Separately approved unrecoverable restore may invalidate old keys using 409 attempt_invalidated_by_restore, distinct from 410 attempt_expired; host verification, no new-key fallback. Normal restart preserves valid state. |
| T-01 | APPROVED | Memory-only 60-minute administrator sessions with documented reload/XSS/expiration limitations, no refresh or automatic failed-write replay. No new guest persistence guarantee is inferred. |
| T-02 | PROVISIONALLY APPROVED | Split admission/execution under [retry-protocol.md](../contracts/retry-protocol.md). Seventeen runtime verification cases remain unexecuted. No commit-clock resolver, nullable receipt state, worker sealing, broker or lease. |
| T-03 | CONDITIONALLY APPROVED | Contact-free logical backups, fail-closed allowlist/schema checks, disclosed snapshot-age/recovery limitations and enforceable hosting controls. No completed privacy/restore/provider verification claimed; no actual restore authorized. |
| T-04 | APPROVED | FE/BE own their respective Dockerfiles; QA owns root Compose/CI; Lead owns canonical/generated API files. Shared docs/AGENT_TASKS.md is reconciled, including generated frontend schema exception. |

No blanket runtime-ready or unconditional whole-system implementation approval is inferred from
these decisions. The approved specification has **77** scenarios: the original 61, four A-001
cases, and twelve A-002/A-003 policy cases. The original fifteen Q/A entries remain history;
current D-009/011 and requirements explicitly carry the amendments. Requirements checklist is
reevaluated 16/16 for documentation quality, not runtime verification or closure of T-02/T-03.

## Resolved review blockers

1. Receipt boundary: approved clarified T is an ordinary database clock sample written in the
   admission transaction and authoritative only upon commit. This replaces, rather than approves,
   the previous exact-commit-metadata proposal. Late commit C yields remaining max(0,T+24h-C),
   never a fresh 24h from C. A key committed at/after E is expired without booking/pending.
2. Recovery exception: explicitly approved only for separately authorized recovery unable to
   preserve state, with distinct 409 and no chronological-age/booking-failure inference.
3. Pending protocol: failed lock transactions fully roll back before fresh committed-state
   classification. Only committed matching unexpired unfinished state may be 202. Mismatch,
   expiry and unverifiable state have dedicated outcomes. No confirmation before known commit.

The protocol covers concurrent admission/execution, post-wait time checks, immutable binding,
terminal-result replay, savepoint exclusion errors, unknown ACKs, crashes and tombstones. Its
runtime correctness is still an acceptance condition, not proven by the documentation update.

## Preservation, compatibility and scope

Constitution 1.2.0/ratification dates, approved historical A-001, clock-aligned activity starts,
DST folds/gaps/continuous-window rules, 60-minute session policy, 720-hour contact deletion,
per-activity exclusion and preserved booking intervals/status are unchanged. Only approved
receipt/recovery clauses and corresponding acceptance/traceability/status records changed.

Existing PRD/architecture/ADRs and canonical TypeSpec still need the exact reconciliation in
contracts/source-reconciliation.md. Their pending alignment is an intentional contract-first
hold, not permission for private JSON formats. Canonical/derived API artifacts must be reviewed,
compiled, regenerated and frozen later; no canonical API or application file changed now.
No tasks.md exists to reconcile. Shared ownership alone was finalized under explicit T-04.

## Remaining risks and ambiguities

No unresolved product-policy ambiguity was identified after applying the human's clarification.
The following technical/operational conditions remain, with no silent defaults or passing claims:

- T-02: prove late final stamping after admission contention, delayed/late/unknown COMMIT,
  rollback/crash/ACK recovery, expiry/mismatch pending guards, normal restart and exclusion races.
  Timeout values are bounded deployment configuration, not an approved SLA or expiry grace.
- T-03: verify contact deletion/read suppression during failure, backup schema/role restrictions,
  provider snapshots/logs, restore fencing and client guidance. SQL deletion is not forensic disk
  erasure; contact-free backup cannot restore contacts or post-snapshot history. No RPO/RTO is added.
- Public admission needs resource/rate/body controls and tombstone growth monitoring before public
  deployment. No numeric quota or additional 429 schema is silently approved by these decisions.
- The correctness-first timezone portion builder remains unbenchmarked. Bound caches/horizon work
  and verify the supported browser/server timezone behavior before relying on it publicly.
- Memory-only sessions do not prevent XSS and reload ends browser authentication. Verify expiry/
  clock-skew/focus handling and contact-cache suppression; no guest cross-reload recovery promise
  is added by T-01. Existing guest in-memory recovery limitation remains visible in design/UI review.

## Readiness assessment

The three earlier blockers have approved policy resolutions and a reconciled provisional protocol.
The human has formally approved the consolidated technical plan with the exact T-02/T-03
conditions retained. Documentation is ready for the next API contract reconciliation review. Do not call the system
implemented/tested, close these conditions,
or proceed to tasks/implementation on the basis of this report. Future source/contract freeze,
required verification and separate implementation authorization remain necessary.

## Approval history and revision provenance

R-002 was a proposal review, not an approval record. Its A-002 proposal blob was
`b0009980c5dd710abc0e9fbf57c17a7bd3928673`; the human replaced its commit-metadata definition.
A-003 proposal blob `072f5d965ca24cdcfcc667dae9a00f5998299703` was approved. Reviewed plan
R-002 blob `4ad2686004311b615b47c3182a5c5cbd48922dc7` is the input to this decision reconciliation,
not evidence of unconditional approval of every detail. Pre-reconciliation specification blob
`f7c16d68337870fe0e4c4180fe94a69416960078` contains the prior 65-case A-001-stage baseline.
Original source approvals and A-001's historical package hashes are retained in their records;
the original artifact blobs below identify the R-003 inputs now formally approved. Earlier
A-001/amendment and constitution approval scopes describe their historical approval events;
they do not negate the subsequent formal plan approval and local-commit authorization above.

## Prior reconciliation checks performed

- `python3 /tmp/slotbook-verify-approved-reconciliation.py`: passed approval-status/clarification
  reconciliation, 77 scenarios, twelve additions and scoped amendments to four earlier cases,
  fifteen historical Q/A preservation, exact FR-008/012/022/024/029 and SC-011/017/D-009/011
  change boundaries, A-001/DST preservation, 16/16 requirements criteria, seventeen runtime
  targets, local Markdown links/fences/whitespace, branch/HEAD and no tasks/staging checks.
- `bash .specify/scripts/bash/check-prerequisites.sh --json`: passed; feature research/data-model/
  contracts/quickstart artifacts are present.
- `git diff --check`: passed. Runtime, database, SQL/migration, canonical compilation, concurrency,
  privacy/backup/restore and provider hosting checks were NOT RUN in this documentation-only pass.
  T-02/T-03 conditions remain open. Temporary verifier is local review tooling, not application code.

## Human-approved R-003 input revisions

These are the exact human-approved input content blobs, verified before administrative approval
finalization. They remain historical provenance; the finalization below changes status records
without changing requirements or technical design. The approved report revision is recorded above.
Feature paths are relative to this feature directory unless marked repository root.

| Artifact | Git content blob |
| --- | --- |
| spec.md | `e4d75a0fd79dfaeec48e36b7457cd4d6c32c0656` |
| checklists/requirements.md | `cbeed9f140da0a5865f8cfe0c1d2cff0e6cb6a82` |
| plan.md | `e8298a179a345ea9457c7f856bcc30358c2f64ca` |
| research.md | `0817303a72ed1c8e36f307506e31f14681963dcb` |
| data-model.md | `0325d0f1c78f679ee27ef95473bb1b77f41a0f49` |
| quickstart.md | `32ef792878b5d682949841553b15baf442f0d291` |
| contracts/api-proposal.md | `e011c26e92e89131a50714a3ea5e6c0139768ca4` |
| contracts/source-reconciliation.md | `3bbcea69f98cecc5fe705b857f0c1a6d5816c039` |
| contracts/retry-protocol.md | `570308af68bfe08640dffe8cc9ae95739d33834f` |
| amendments/A-002-durable-admission.md | `e0dc6a29c0445656cfa3233dfe96fa2be8c73bd0` |
| amendments/A-003-disaster-recovery.md | `141f3b1e78fdf6c07698d7a4c6989804f2adce12` |
| docs/AGENT_TASKS.md (repository root) | `9078241ae8e77e9ede4226b84f4c0c7f481978ad` |

## Formal approval finalization checks — 2026-10-25

- Verified all twelve R-003 input manifest blobs against the working files before editing;
  verified the approved report blob recorded above. Approval finalization changes only status,
  provenance and current ownership/reconciliation records.
- `python3 /tmp/slotbook-verify-plan-finalization.py`: passed exact preservation of all 77
  acceptance scenarios (story counts 8/26/16/14/13), fifteen historical answers, 31 functional
  requirements, 19 success criteria and decision rows; unchanged amendment records/constitution;
  16/16 checklist; retained T-02/T-03 conditions and seventeen unexecuted protocol cases.
  Also passed local Markdown links/fences/whitespace, scoped credential/machine-path scan,
  exact 14-file documentation scope, actual branch and parent-baseline verification.
- `bash .specify/scripts/bash/check-prerequisites.sh --json`: passed; research, data model,
  contracts and quickstart are present. `git diff --check`: passed.
- PRD, canonical TypeSpec and application/infrastructure files are unchanged. No tasks or agents
  were created. Runtime, contract compilation, SQL/concurrency/crash/timeout/idempotency and
  backup/restore/provider controls were NOT RUN; T-02/T-03 remain open.

## Finalized documentation content revisions

These commit-ready blobs include administrative approval finalization. They preserve the
approved requirements/design; the earlier table records the human-reviewed input revisions.
The report itself is excluded to avoid a self-referential hash. The local commit hash and
post-commit Git status are reported in the handoff after committing.

| Artifact | Git content blob |
| --- | --- |
| amendments/A-001-clock-aligned-starts.md | `227e71a86d90d5d3d2a46ba53a0aa9e9d138c176` |
| amendments/A-002-durable-admission.md | `e0dc6a29c0445656cfa3233dfe96fa2be8c73bd0` |
| amendments/A-003-disaster-recovery.md | `141f3b1e78fdf6c07698d7a4c6989804f2adce12` |
| checklists/requirements.md | `d728cd23b1581e078e5fd3314380785c8231f3d3` |
| contracts/api-proposal.md | `e9e54837ab13f53402dc67bd08332b5c60e0f83f` |
| contracts/retry-protocol.md | `1d9005d2e599a39a29dcff9040227e2e0f3b82be` |
| contracts/source-reconciliation.md | `d11dcd6b0ebab49404a771afbb6ed16729dff449` |
| data-model.md | `4559c44bfddd2cd13dbc681e9a9c2fe75e1ad161` |
| plan.md | `24b65dd4bf027390254374a729cf81864d193780` |
| quickstart.md | `5252b2b7577458145924f7d2a21fb5e464850029` |
| research.md | `08733bdef353252aea6d341354437b96ba35b7b3` |
| spec.md | `5cc968b5cbf3ac899b6c46973c2cbd31862e7cde` |
| docs/AGENT_TASKS.md (repository root) | `b542a9daa7ab47e6ac45b89a9fec41a7ebb1914e` |
