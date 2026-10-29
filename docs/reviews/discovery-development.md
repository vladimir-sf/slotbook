# Discovery development integration and Backend handoff

Recorded: 2026-10-29. Owner: Lead/Architect. Frontend/QA local integration: PASS.
The human authorized the four reviewed discovery commits, non-fast-forward Lead merges,
green regression verification, separate progress commit and feature-branch publication.
This record also assesses Backend source readiness and supplies the separately requested
T011 authorization. It grants no main merge, deployment or frozen API change.

## Integrated source

| Revision | Full commit |
| --- | --- |
| Published common baseline / clean Lead entry | `230955156b50d8e6834aaafebeb966b082b00980` |
| T027 authoring | `4f860294efe5ae9490267d62fccf16176dc8e1da` |
| T031 catalog/detail | `0bd0e920c6080634bec9e16fb233525259975fbd` |
| T032 date/slot selection | `6e2bbaf6462a15bffef0fd667dbdcf011b4bc13e` |
| T026 QA authoring | `b10a5721f361ac13dc92f38e37aa1e3776d73c87` |
| Frontend merge | `3062812e228458e5b86a61191cb18359a5c02c6d` |
| QA merge / verified Lead candidate | `2cd655418e928da2fdbc58398c4d0e82df5c11f9` |

Both source worktrees were clean. Frontend's three commits form a direct chain from the
common baseline; QA's single commit has that baseline as its direct parent. The merges
retain all four original commits, add exactly seven Frontend discovery paths and
`tests/contract/test_catalog.py`, and have no Backend changes. Source locks, shared task
metadata, T003 fixture definitions and frozen API artifacts were unchanged.

Frontend's reviewed commits include narrow corrections to the T027 test helper: distinguish
Vite module paths from actual API routes, scope the description selector, and allow the native
date input while rejecting contact/booking fields. These stay in Frontend ownership and the
explicitly approved commit scope. T003's contract/privacy/report checks remain intact; only
its obsolete scaffold-render test changes to the discovery entry point.

## Green verification and evidence limits

Fresh source-branch checks passed before merge. All four local lanes then passed on the
exact combined Lead candidate above, with source SHA-256
`4142afdecde788963de8c3ce8e8b818dc34accfb84870caf2af522c0c6ba25f2`.
Node 22.22.0 / npm 10.9.4 and Python 3.12.12 were selected; Backend/QA used separate fresh
hash-locked environments. Contract and Frontend installs ran serially in Lead. All npm audit
gates passed. Every command below exited 0; all executed mandatory cases passed without skips.

| Command | Result |
| --- | --- |
| `python .github/ci/checks.py contract` | T005 self-test: TypeSpec/OpenAPI/generated TS and byte reproducibility; 18 operations, 71 schema fixtures, 20 negative guards |
| `python .github/ci/checks.py frontend` | Locked install, typecheck, build, **85 Playwright cases** |
| `SLOTBOOK_CATALOG_MODE=authoring python .github/ci/checks.py qa` | Locked installs, Ruff/format/typecheck, **317 Python cases** (237 T026 authoring + 80 existing), **4 browser cases**, **23 CI policy tests** |
| `python .github/ci/checks.py backend` | Locked install, Ruff/format/mypy, **237 pytest cases**; no T007/T009/T010 merged |
| `SLOTBOOK_CATALOG_MODE=authoring python -m pytest -c tests/pytest.ini tests/contract/test_catalog.py --collect-only -q` | 237 authoring cases collected |
| Same collection command with `SLOTBOOK_CATALOG_MODE=live` | 35 live cases collected, not executed; no live verification claimed |
| Frozen comparison, source scope/ancestry, `git diff --check`, `git fsck --full --no-reflogs` | PASS; dangling objects are not repository corruption |

The two collection commands use the same locked QA environment with private cache/output.
`TZ=UTC` and `PYTHONTZPATH=''` are enforced by the lanes; Backend tzdata is 2026.5 / IANA
2026e. Browser versions: Playwright 1.64.1, Chromium 156.0.8078.4, revision 1248.
Application and default Docker/Compose runtime were not exercised by these green tooling jobs.

| Sanitized local report under `test-results/` | SHA-256 |
| --- | --- |
| `ci-contract-bbaa682a997f3749/verification.json` | `0b1022a5c4d60ecd9aaade99f06ef818285cfc7d263f628006c631a7a966adb5` |
| `ci-frontend-bb0f0b6afc2a4c5a/verification.json` | `783b2cd088bbf91349933019b38d13f49d2ff1ef3b43bf474920719ff8b71d11` |
| `ci-qa-71dad171fe5ff644/verification.json` | `65ee80e5eeb388952ef85d1d34477119e10bd1467d8d33981c3989765b5048cc` |
| `ci-backend-2aa1650400347fe5/verification.json` | `29cb90c0ee48bc8c20a171a07e8f4bf1d6babbeba9b6c04f0d9be544e8aaef26` |

Frontend's intermediate evidence distinguishes 31 meaningful red T027 tests, a green 70-case
T031 subset with 15 date/slot cases still red, and the final 85 green cases. Final evidence
is fixture/UI behavior only. QA shares its assertions between explicit authoring/live modes;
there are no skips/xfails or automatic mock fallback. The source handoff's attempted live run
had 35 setup errors because the guarded runtime provider was absent, zero passed live cases,
and no real API correctness evidence. The current collection confirms that inventory remains
present; it does not convert those missing-runtime errors into passing behavior.

Before T030 completion, provide the approved guarded runtime fixture, synthetic seed/clock/fault
setup and real Backend, then pass all 35 live cases. T033 must repeat them on the immutable
combined candidate after verified T024 and prove every US1.1–8 real UI/API outcome. T034 stays
open. Neither mock success nor authoring completion proves Backend availability, persistence,
concurrency or privacy. T022 runtime dependencies, provisional T-02 and conditional T-03 remain.

## Backend source readiness — separate from these merges

The actual clean `feat/backend` chain is:

`3148b980cbe3d1b7fe3f8fd19916494b41e68d6d`
→ T007 `37e75238bca58262b5ca98d1fcf266adbfc5e48a`
→ T009 `60e4dbe591b5267d61101d1f68d54dbe81117da8`
→ T010 `620a8bed8a8c0768a4b78908ffc37e1118199efd`.

All source hashes in the existing acceptance records were checked against these exact commits;
their source worktree, HEAD and original commits were preserved. T010's definition, ownership
and dependency are unchanged in the published amended task plan despite Backend's older common
ancestor. No Backend task commit is an ancestor of the Lead candidate.

| Task | Verified source evidence | Integration disposition |
| --- | --- | --- |
| T007 | Original acceptance passed: pinned ARM64 image, 237 build/runtime tests, static checks, 4 timezone negatives, 18 smoke/context groups; exactly its two files | Ready as a separate green ancestor candidate; production security clearance remains withheld |
| T009 | 267 host/image tests, static checks, 26 real PostgreSQL acceptance groups; six implementation files plus required focused unit tests | Ready together with its T007 parent; adds migration `0001_schemas` and restricted role/schema/session foundations |
| T010 | Authoring acceptance passed: 75 new cases, 12 new passes and 63 expected assertion failures; configured full run **279 passed / 63 failed**, pytest exit 1, zero errors/skips | Retain on development branch; not a green schema milestone and not suitable for mandatory-green publication |

T010's failures classify as 54 missing-relation assertions and 9 missing CHECK/FK/exclusion
catalog assertions. Missing tables are checked before privilege tests, so unavailable relations
cannot falsely prove access denial. No unconditional skips, xfails, SQLite substitution or
configuration errors are counted as successful database verification.

The exact T007/T009 ancestor pair can later be integrated by selecting `60e4dbe...` with a
non-fast-forward merge after its separate integration authorization/checks. Do not merge the
moving `feat/backend` tip to obtain that pair: it includes T010's red suite. This turn merges
only the explicitly requested Frontend/QA sources and leaves Backend checkboxes unchanged.
The green Lead Backend suite is therefore 237 cases, not T009's 267 or T010's 342-case red run.

| Backend source evidence | SHA-256 |
| --- | --- |
| T007 final acceptance manifest | `0befa2c77b9ccd132187da075d0fa519f287a95b14ba34a80549ec0e8092e0af` |
| T009 final acceptance manifest | `c0d982c6c14b4a692ed441a0ff0897df6f7f21f87ec33e45165363c04137e926` |
| T009 real PostgreSQL record | `a76613ccfcd9d267107146924644161d82152fffb9c391abb40133c8ab0a5a84` |
| T010 final authoring manifest | `3ecdaff5ca48db8626fccc689363f2c216b5bacd66bfe1d65eb2f84996c10efe` |
| T010 real PostgreSQL record | `c26eab6d2d6e8e3ae34690027949badebb973ca9f7f9857a6fb6783a1268a058` |
| T010 classified pytest evidence | `8ea1fa42bfc55085fc65a4d22375d8464439f15b61ae6b275c7828be8fb69cd4` |

These are inspected existing source acceptance runs, not fresh Backend image/database runs
performed by this integration turn. Raw logs, credentials and local manifests stay private.
Known image findings and production remediation requirements are preserved; no new security
investigation or zero-vulnerability task gate is added. Unresolved critical risks still block
production deployment.

## Separate T011 authorization and next assignments

The human requested T011 authorization once T010 authorship and ancestry were verified. Those
conditions are satisfied. **Backend is authorized for T011 only**, continuing on `feat/backend`
from `620a8bed8a8c0768a4b78908ffc37e1118199efd`, preserving all three original Backend commits.
Read the current Lead task/protocol documents without resetting, rebasing or replacing that
T010-based development history. This is an owner handoff, not Lead implementation or an agent
launch in this turn. Do not advance automatically to T012 or publish/merge the red branch.

Implement the approved configuration-table scope: `backend/app/models/activity.py`,
`backend/app/models/availability.py`, registry wiring in `backend/app/models/__init__.py`,
and `backend/migrations/versions/0002_configuration.py`. Preserve source constraints and
explicit backup grants; verify activities, weekly windows and per-activity blocked dates,
slug uniqueness, weekday/duration rules, touching versus overlapping/duplicate/overnight
windows, and RESTRICT FKs against real PostgreSQL. Preserve frozen API v1 and dependency locks.
If registering the actual models makes T009's empty-registry unit expectation obsolete,
align that focused expectation in `backend/tests/unit/test_db_foundation.py` without removing
its naming/registry checks or weakening T010 assertions; this narrow Backend test maintenance
is part of the Lead-approved T011 handoff.

Run the configuration-specific acceptance cases and all applicable existing regressions.
Also run the full configured PostgreSQL suite and report remaining expected failures by their
T012/T013/T014 schema dependencies. Do not require unrelated later-schema cases to turn green
in T011, but do not hide them or describe the full suite as passing. Missing fixture/configuration
is a setup blocker, not expected behavioral red. Keep raw output private; hand off actual source
commits, commands, counts and limitations. Existing guarded disposable-target rules still apply;
no ordinary development/production DB or unapproved crash/restore operation is authorized.

QA can prepare T022's static checkpoint with T004/T008 satisfied; its runtime checkbox remains
blocked by T007/T009 integration and T017/T020/T021 acceptance. Frontend T027/T031/T032 is
integrated; new story work still follows its explicit prerequisites. T024, T030, T033 and T034
remain the required infrastructure/live-discovery sequence. Further assignments need their own
scope authorization; no extra feature or test-hiding work is included here.

## Published progress boundary

Only T026, T027, T031 and T032 are newly marked complete centrally: **13 of 92 complete,
79 unchecked**. T007/T009 accepted source work and T010's red authoring checkpoint remain
separately recorded, without central integration completion. All 31 FRs, 19 SCs, 77 scenarios,
the 16/16 checklist and 18 frozen API operations remain unchanged. GitHub Actions must be checked
for the exact pushed progress revision; local results above do not claim hosted execution.
