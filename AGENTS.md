# Agent instructions — SlotBook

## Goal and source of truth
Build the MVP in `docs/PRD.md`. `contracts/main.tsp` is the canonical API contract;
`docs/ARCHITECTURE.md` defines design choices. Generated OpenAPI/TypeScript are derived artifacts.
If they conflict, flag the mismatch and request a contract change. Do not silently diverge.

## Non-negotiables
1. Read the PRD, architecture, TypeSpec, and assigned tasks before coding.
2. **Contract first**: never invent private frontend/backend JSON formats.
3. Stay in your assigned directories unless the lead explicitly approves a cross-cutting change.
4. Add tests for every behavioral change, including negative/error paths.
5. Run relevant checks and report exact commands/results; never claim tests passed without running them.
6. Never use real customer data or commit `.env`, tokens, or API keys.
7. An explicitly approved task scope permits routine, non-force pushes of its changes to its
   isolated feature branch unless the human restricts that authorization. Merges, deployments,
   destructive operations, force pushes, and pushes to shared integration/default/protected
   branches require separate human review and explicit approval.
8. Treat agent-authored code as untrusted until reviewed; no unchecked automated merging.
9. Time values: UTC over API; IANA timezone for display and availability rules.
10. PostgreSQL must enforce non-overlapping confirmed bookings, including simultaneous requests.

## Pull request / handoff template
- Scope and files changed
- Spec/contract version used
- Tests run: exact commands and outcomes
- Unresolved questions and known limitations
- Contract or migration changes (yes/no)
