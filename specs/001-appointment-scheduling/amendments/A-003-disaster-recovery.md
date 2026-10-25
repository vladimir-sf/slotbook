# A-003 — Explicit disaster-recovery exception for retry state

**Status**: APPROVED by the human project owner.
**Approved / Recorded**: 2026-10-25.
**Reviewed proposal blob**: `072f5d965ca24cdcfcc667dae9a00f5998299703`.
**Authority**: Constitution 1.2.0 Governance; approved baseline commit
`e9f16809058fe826523bf8c19387b6ba65b8e145` plus approved A-001.
**Origin**: Explicit human approval of A-003 following technical architecture review.
The human approved restore invalidation with 409 attempt_invalidated_by_restore, distinct from
410 attempt_expired, and preservation of valid identifiers across normal restarts. This record
adds the qualified exception to current requirements; A-001 and constitution 1.2.0 remain unchanged.

## Approved product policy

The reconciled FR-024/029 include the following narrowly scoped exception:

> Following a separately human-approved disaster restore that cannot recover attempt state,
> the MVP may invalidate retry identifiers from the lost generation, including identifiers
> whose ordinary 24-hour lifetime has not ended. This is disaster-recovery invalidation,
> not chronological expiry, and does not establish whether the original booking succeeded.
> The system must reject the old identifier without creating/reviving a booking, retrieving
> another guest's details, or silently replacing the identifier. The client must explain that
> recovery state was lost and direct an unknown outcome to host verification.

Normal restarts, deployments, transient database/network failures, maintenance, worker failures
and ordinary secret rotation do not qualify. They must preserve the committed 24-hour guarantee,
binding, results and tombstones. Missing state/secrets during normal startup fails readiness;
it must not silently initialize another generation or claim a restore exception.

Restore approval records the affected database/snapshot, reason attempt state is unrecoverable,
old generation if known, new generation and restoration time. Before traffic resumes, use a new
random public generation and fence off the old writer/service; do not run two writable generations.
The exception is not authorization to perform a restore or other destructive action now.

## Approved error semantics and client guidance

- **410 `attempt_expired`**: same-generation attempt with authoritative chronological expiry
  `now >= T+24h`. Do not return a result or reinterpret the identifier as new.
- **409 `attempt_invalidated_by_restore`**: prior/noncurrent-generation identifier after the
  approved recovery transition. No original expiry/result/contact details are disclosed.
  This response does not claim the supplied identifier was ever admitted; when prior state is
  absent its original age/outcome cannot be proved. Do not label it expired merely from age guesses.
- Client guidance: “This service cannot recover this attempt after a restore. Its booking
  outcome is unverified. Contact the host before making another booking.” Do not automatically
  generate a new identifier or imply that no booking exists. A deliberately new attempt follows
  host verification when the previous outcome is unknown.
- Fresh-generation new attempts operate normally. Old expiry metadata is omitted when unknown.

No extra endpoint is necessary beyond the proposed generation-context read. Exact TypeSpec
response/header/error definitions remain separately reviewed contract work, not implemented or frozen by this approval.

## Reconciled requirements and acceptance criteria

- **FR-024 / D-009 / SC-011**: preserve ordinary 24h semantics with the explicit qualified restore
  exception; distinguish invalidation from expiry. A-002 defines persisted database timestamp T effective only after successful admission commit.
- **FR-012/022**: unknown recovery state cannot produce false rejection/confirmation or silent resubmit.
- **FR-029 / D-011 / SC-017 / US4.8/12**: retain contact-free backups and no expired-access revival;
  add explicit loss of unexpired retry recovery only during an approved unrecoverable restore.
- **US2.8/13/15**: qualified for ordinary validity and A-003; added US2.23–26 and US4.13–14
  for the six recovery cases below. Combined with A-002, the current approved suite is 77
  scenarios; the earlier 65-scenario suite remains historical provenance.

### Approved acceptance scenarios (mapped into spec.md)

1. **Given** a committed attempt still within 24h and a normal service/database restart,
   **When** matching retry occurs, **Then** its original expiry and result remain recoverable.
2. **Given** a separately approved disaster restore that lacks attempt state, **When** an old
   unexpired identifier is retried, **Then** it receives restore-invalidation feedback, never
   ordinary chronological-expiry feedback, booking creation or automatic new-key submission.
3. **Given** an identifier absent from an older snapshot, **When** the restored service sees its
   old generation, **Then** it rejects recovery without treating that identifier as unseen/new.
4. **Given** an expired current-generation identifier, **When** it is retried, **Then** 410
   attempt_expired remains distinct from the disaster-recovery error and never returns pending.
5. **Given** restored history with contacts absent and an unknown old booking outcome,
   **When** the client shows guidance, **Then** no guest contacts/credentials are restored,
   no booking failure is inferred, and host verification is required before replacement.
6. **Given** missing attempt state/HMAC secret during routine startup, **When** readiness runs,
   **Then** traffic stays blocked; the service does not create a fresh generation automatically.

## Tradeoff against preserving contact-free retry state

Approved MVP recovery direction: exclude attempt/binding/session data from logical
backups and accept documented retry-state loss during the qualified recovery event. This reduces
backup privacy surface and restore complexity but weakens retry availability after disaster and
may require manual host reconciliation. History newer than the backup can also be lost; recovery
procedures must disclose the snapshot age and limitations without claiming a new recovery SLA.

Alternative: preserve selected verifier, receipt, binding and terminal-result state in a consistent
contact-free recovery archive. Raw retry credentials and contact-bearing inputs must remain
excluded. A verifier is not itself an accepted credential, but contact-derived binding digests
and cross-record links need privacy review; omitting them would prevent safe original-detail
matching. This alternative also needs consistent booking/attempt snapshots and a policy for
post-snapshot admissions. It does not automatically guarantee recovery of every unexpired key.

Operators must enforce no contact-bearing volume/provider snapshots, WAL archives or crash
artifacts. Ordinary live WAL needed for PostgreSQL crash recovery remains; it is not an approved
backup/export and does not make SQL deletion forensic erasure. Physical backups containing
contacts are not made compliant merely by encrypting them.

## Governance and impact

Lead owns current FR and future reviewed PRD/TypeSpec/ADR reconciliation; Backend owns runtime generation/state
and fencing interfaces; FE owns explicit invalidation guidance; QA/DevOps owns restart/restore,
hosting and privacy acceptance evidence. No public feature, booking mutation or contact-retention
extension is added. Database planning gains recovery metadata; no migration or restore is executed.

A-003 and clarified A-002 were explicitly approved on 2026-10-25 and are reconciled in the
current spec/checklist/design. T-01/T-04 are approved, T-02 remains provisional and T-03
conditional. Those decisions do not authorize tasks or implementation. No constitutional
version/date change is needed; this is a recorded product-policy exception, not approval of
a restore operation or of future canonical TypeSpec syntax.
