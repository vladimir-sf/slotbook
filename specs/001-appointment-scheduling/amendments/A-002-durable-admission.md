# A-002 — Persisted database admission timestamp

**Status**: APPROVED WITH CLARIFICATION by the human project owner.
**Approved / Recorded**: 2026-10-25.
**Authority**: Constitution 1.2.0 Governance; baseline commit
`e9f16809058fe826523bf8c19387b6ba65b8e145`, approved A-001 and this explicit human decision.
**Reviewed proposal blob**: `b0009980c5dd710abc0e9fbf57c17a7bd3928673`.
**Pre-amendment specification blob**: `f7c16d68337870fe0e4c4180fe94a69416960078`.

## Approval and final policy

The human approved: “Define durable admission using a database-generated timestamp persisted
in a successfully committed transaction. The 24-hour retry deadline is calculated from that
timestamp, not PostgreSQL commit metadata.” The human required delayed-commit handling,
no valid attempt from rolled-back admission, and unverified treatment of uncertain commit outcomes.
This clarification supersedes the earlier proposal's exact commit-event/metadata mechanism.

The admission transaction persists an authoritative database-generated timestamp T, original-detail
binding and deadline E = T + 24 elapsed hours. The attempt becomes valid only when that transaction
successfully commits durably. T is sampled within the transaction; it is NOT the commit instant,
HTTP arrival, response receipt or a later retry's time. No committed admission means no valid
attempt through that transaction. Once committed, its T/E and binding are immutable.

A verified rollback admits nothing through that transaction and starts no booking execution.
It does not prove a competing same-key request never committed. A lost COMMIT acknowledgement
is unverified until a fresh committed-state read resolves it; no unsupported pending/confirmation
or assertion of rollback is allowed. Preserve the same key/details for explicit recovery.
If no admission ever committed, a later explicit request may establish the first admission and T.

## Delayed commits and operational handling

Let C be actual commit time and E=T+24h. If commit is delayed after sampling T, it consumes
part of that fixed window: remaining validity at C is max(0, E-C). The window is NOT reset
or extended to C+24h. An admission that commits at/after E is already expired and cannot execute
a booking, return ordinary pending, or expose a final result. Its key remains rejected as expired.

Sample T late, after admission-key contention and binding preparation, as the final stamping write
before COMMIT. Use one clock_timestamp() sample for T and E; do not use transaction-start now().
Any earlier provisional values in this uncommitted transaction are not a valid receipt. Stamp only
a newly created, still-uncommitted admission; never restamp an existing committed attempt.
Keep admission transactions short with bounded lock/statement/application budgets. A timeout or
connection cancellation during COMMIT can still leave its outcome uncertain; budgets cannot prove
rollback or guarantee commit latency. After admission acknowledgement or recovery, recheck current
DB wall-clock time before execution. No minimum of 24 hours after C is promised.

The human fixed the deadline rule and asked delayed commits to be addressed; the late-stamping
and bounded-budget choices are technical safeguards, not a silent TTL extension. Exact operational
budget values remain implementation configuration, subject to T-02 runtime verification.

## Reconciled requirements and acceptance

Updated FR-008/012/022/024, D-009 and SC-011; existing US2.8/13/15 were qualified for admission,
pending and A-003 semantics. Added US2.17–22 for rollback, delayed commit, lost acknowledgement,
no prior admission, unresolved COMMIT and normal restart. The combined approved suite after
A-003 contains 77 scenarios (65 previously approved plus twelve policy cases).

Private storage keeps non-null first_received_at/expires_at and immutable binding in the same
admission transaction. Remove admission-XID, receipt-resolution state, post-commit materialization
and worker sealing. No track_commit_timestamp configuration, pg_xact_commit_timestamp lookup,
commit-metadata retention assumption or transaction-epoch machinery is required.

## Compatibility, agents, tests and migration impact

Only the receipt anchor definition changes. Matching/detail binding, terminal-result stability,
contact-free results, chronological expiry and at-most-once behavior remain, with A-003's separate
approved restore exception. Original fifteen Q/A entries remain historical evidence; current
requirements and decision rows carry the amendments. A-001 clock alignment and all DST/window,
authentication and 720-hour contact policies are preserved. Existing booking intervals do not move.

Lead owns PRD/contract/ADR reconciliation; Backend owns timestamp stamping, durability and split
transactions; Frontend owns honest unknown/pending/final feedback; QA verifies timing/crash cases.
No additional table, commit-clock resolver or execution coordinator is introduced. Planned private
attempt schema uses ordinary timestamp/deadline columns; no application migration is executed now.

Runtime verification must delay commit after stamping, cross E while waiting, lose COMMIT ACK,
roll back admission/execution, contend on identical/different payloads and restart with the same
state. Unit-controlled clocks supplement real PostgreSQL durability/locking tests; documentation
checks do not prove runtime behavior. Detailed cases: [retry protocol](../contracts/retry-protocol.md).

## Approval scope and history

The earlier PROPOSED record required exact commit metadata. It was never approved as written;
this record preserves its reviewed blob and records the human's replacement clarification.
A-002's product gate is now approved and reconciled. T-02 is only provisionally approved pending
runtime verification; no full implementation authorization is inferred. Constitution 1.2.0 and
its ratification dates remain unchanged. Canonical TypeSpec/PRD reconciliation is still future
reviewed work; no tasks, application code, commit, push or agent execution is authorized here.
