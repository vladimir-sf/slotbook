# T015 / T018 integration

Recorded: 2026-10-27. Owner: Lead/Architect. Local acceptance: PASS.
The human authorized the reviewed task integration, separate progress commit and push of
`001-appointment-scheduling`; no main merge, deployment or additional task execution.

## Provenance and scope

| Revision | Commit |
| --- | --- |
| Approved source parent | `e8331549af29c843de7150f3793a12856c1eb31d` |
| Actual clean Lead entry (preserves approved README fix) | `206192afef2d7e6511340ef716bfd54137fe5dd0` |
| T015, strict schemas | `57e6a34f67bcee2e72def3cdbd81d46936a13188` |
| T018, time primitives | `3f9ecda776256de2f7790a6b937741382b0bb1ea` |
| Non-fast-forward Lead merge / verified revision | `ae222a2fc5e52f8c71c6a20878b600707dc75a08` |

Source branch `codex/backend-foundations` was clean at T018. T015's direct parent is the
approved source parent; T018's direct parent is T015. The source changed only its five
T015 and three T018 Backend paths. The Lead merge adds exactly those eight paths, retains
both original commits and preserves the README correction. Source locks and shared task
metadata were unchanged. No routes, migrations, API contract or generated artifacts changed.
The progress commit is separate and changes only this record and `tasks.md`.

## Verification

All four local CI lanes passed on the exact merge revision with the same source SHA-256
`cbf0ad9d56d4be1da5652d6ef44b635000e2ca51181dba7580dac830fc8cc133`.
Backend and QA used independent fresh hash-locked Python environments; contract and Frontend
npm installs ran serially. Python 3.12.12, Node 22.22.0 and npm 10.9.4 were selected.
The CI entrypoint enforces `TZ=UTC` and `PYTHONTZPATH=''`; packaged tzdata is 2026.5 / IANA 2026e.

| Command / check | Result |
| --- | --- |
| `python -m pytest --collect-only -q tests/unit/test_schemas.py` on the clean source | 153 new T015 cases collected; exit 0 |
| `python -m pytest --collect-only -q tests/unit/test_time_primitives.py` on the clean source | 77 new T018 cases collected; exit 0 |
| `python .github/ci/checks.py backend` | Locked install and pip check; Ruff, formatting, `mypy app`; full pytest **237 passed**, zero skipped; exit 0 |
| `python .github/ci/checks.py contract` | T005 `bash scripts/check-contract.sh --self-test`: compile/OpenAPI/type/byte checks, 18 operations, 71 schema fixtures, 20 negative guards; exit 0 |
| `python .github/ci/checks.py frontend` | Locked install/audit, typecheck, production build; **54 browser cases passed**; exit 0 |
| `python .github/ci/checks.py qa` | Independent locked installs/audits, Ruff/format/typecheck; **80 Python + 4 browser + 23 CI policy cases passed**; exit 0 |
| Reviewed private PostgreSQL clock probe, repeated with merged Backend mounted read-only | **6 real database checks passed**; driver and cleanup exit 0 |
| `git diff --check`; `git fsck --full --no-reflogs`; source ownership/ancestry and frozen comparisons | Exit 0; fsck reports dangling objects, no corruption |

The Backend lane invokes, from `backend/`, `python -m ruff check app tests`,
`python -m ruff format --check app tests`, `python -m mypy app`, and full `python -m pytest -q`
with private inventory/JUnit handling. The 153 + 77 new cases and 7 existing cases total 237.
Browser toolchains remain Playwright 1.64.1 / Chromium 156.0.8078.4, revision 1248.
All npm audit gates passed; no dependency lock changed.

The fresh PostgreSQL 16.15 ARM64 probe used a unique labeled internal network, no published
ports, tmpfs database storage and no application tables. It observed an actual advisory-lock
wait on an independent connection, then verified fresh `DatabaseClock` sampling after release,
frozen transaction `now()` versus advancing wall-clock time, the SQLAlchemy Session adapter,
and UTC normalization from a non-UTC DB session. Both owned containers and the network were
removed. PostgreSQL image index:
`sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab`.
The cached Python probe image runs 3.12.15 and has known development-image security findings;
using it in this disposable test grants no production clearance.

The earlier source-worktree clock evidence was also checked against the committed source
hashes: six checks passed, including cleanup. SHA-256:
`347b77c86246f796c74c95aaa044fe2c8146a06516b9a4ca4b169e085b9a1850`.
The fresh post-merge clock record SHA-256 is
`9e07231f4133157dce8b8833377870d11c6f4e268a8cceed71c34b174e8cd758`.
Raw command streams, clock probe records and generated credentials stay private outside Git.

| Sanitized ignored report under `test-results/` | SHA-256 |
| --- | --- |
| `ci-backend-0abb61c780a49d83/verification.json` | `30c1891c78f7cc9c8f6e8caed1c3fac4fdcb2f5d18ec02c6d58534ddd39040dd` |
| `ci-contract-0796e9827c6ef28a/verification.json` | `0a35d585ad722ec01cae5b0f1e52a95364c85e6710fc07232d84f7ad1fbe0831` |
| `ci-frontend-701db2d56a7d1997/verification.json` | `1c676ea08113e4bad9ca219c981a214c176aade8bfe2d85e460e6bb012996d62` |
| `ci-qa-149f941be9030d05/verification.json` | `b61ade12693f08feb10960040090c4bf1a70fea893a5bb377010affaadd8673e` |

## T007 acceptance and the next dependency

T007 remains unchecked and its separate worktree was not modified or merged. Its HEAD,
dirty-file inventory and Dockerfile/`.dockerignore` hashes are preserved. The original task
requires a pinned Python 3.12 image/digest, locked dependencies, packaged timezone enforcement
and diagnostics, source/private-state exclusion, app import/tests/static checks, and published
migration/seed/worker/health command interfaces. Commands implemented by later tasks must be
identified as future interfaces, not faked as working. It **does not require zero image
vulnerabilities** or completion of a production security release review.

The earlier T007 functional evidence reports a successful build, 7 then-current Backend tests,
Ruff/format/mypy, four timezone rejection checks and 18 runtime/context smoke groups. That
evidence predates T015/T018 and is not represented here as a fresh 237-test image run.
Prioritize Backend finalization of the existing two-file T007 change: verify the approved
image/interface criteria against the integrated source and 237-test suite, retain the scan
disclosures, and submit its task handoff for integration. Do not impose an invented zero-findings
gate on development progress. Once T007 is complete, T009 can start the real PostgreSQL
SQLAlchemy/Alembic foundation, followed by T010 and the T011–T014 schema chain.

Production release remains blocked by unresolved critical risks. Preserve the earlier security
review's findings: Starlette 0.52.1 and AnyIO 4.11.0 need reviewed constraint/lock maintenance
(reviewed patch candidates 1.3.1 / 4.14.2 and compatible health-test changes); the Python
3.12.15 base, bundled pip and Debian OpenSSL need patch/base provenance review; psycopg-binary
3.3.6 bundles separate OpenSSL 3.5.8, requiring a verified replacement with at least 3.5.9.
The prior scan recorded 296 package/advisory matches, including 4 critical and 81 high;
matches are not all unique or proven reachable. Vendor-open/native-library findings and
conflicting metadata still need disposition. These are prior review observations, not a new
scan, fresh registry availability check, vulnerability-free claim or production risk acceptance.

## Completion boundary

Nine of 92 tasks are complete; 83 remain unchecked. Only T015 and T018 completion markers
change. All task definitions/dependencies/coverage tables, approved 77 acceptance scenarios,
16/16 requirements checklist and frozen API v1 at `adc0b83a4408493ac44d3a7571dfd3d25a758679`
remain intact. HTTP integration, availability, database schema and booking execution remain
later tasks. Clock checks do not close provisional T-02 or conditional T-03.

T016 and T019 now have their schema/time prerequisites but both still require T014. T007
is the next dependency-ready task; T009 awaits it. Frontend/QA story tasks and T024/T034
remain behind their foundation/story prerequisites. No later task is started by this record.
GitHub Actions must be checked for the exact published progress commit; the local results
above do not claim a hosted run.
