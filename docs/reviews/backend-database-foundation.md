# T007 / T009 PostgreSQL foundation integration

Recorded: 2026-10-29. Owner: Lead/Architect. Local acceptance: PASS.
The human authorized the exact green Backend ancestor pair, non-fast-forward integration,
regression/database verification, separate progress commit and feature-branch publication.
No main merge, deployment, contract change or production security clearance is authorized.

## Provenance and scope

| Revision | Full commit |
| --- | --- |
| Clean published Lead entry | `82e683bb73c3c143a290f7491a4cd29d55924a1d` |
| Backend source parent | `3148b980cbe3d1b7fe3f8fd19916494b41e68d6d` |
| T007 pinned development image | `37e75238bca58262b5ca98d1fcf266adbfc5e48a` |
| T009 schema/role/session foundation | `60e4dbe591b5267d61101d1f68d54dbe81117da8` |
| Non-fast-forward Lead merge / verified candidate | `36afeae751cd1719089b11ba7f3f1cbefb5a49a0` |
| T010, deliberately excluded from Lead | `620a8bed8a8c0768a4b78908ffc37e1118199efd` |

T009 is T007's direct child; T010 is T009's direct child. The exact T009 commit was merged,
not the moving `feat/backend` tip. Both original green commits remain ancestors of Lead;
T010 does not. Source hashes match the reviewed acceptance manifests. T007 changes only
`backend/Dockerfile` and `backend/.dockerignore`; T009 adds its six assigned foundation
files and the required focused `backend/tests/unit/test_db_foundation.py`. No locks, shared
task metadata, frozen contract files or unrelated component files changed in those commits.
The merge adds precisely those nine Backend paths. README and approved requirements are preserved.

Existing source acceptance was checked, separately from the fresh checks below: T007 passed
237 build/runtime tests, four timezone rejection cases, 18 smoke groups and private-context
exclusions; T009 passed 267 tests and 26 real PostgreSQL groups. Source manifest SHA-256 values:
T007 `0befa2c77b9ccd132187da075d0fa519f287a95b14ba34a80549ec0e8092e0af`;
T009 `c0d982c6c14b4a692ed441a0ff0897df6f7f21f87ec33e45165363c04137e926`.
Future seed/worker/readiness/backup/restore commands remain published interfaces, not implemented
features. T009 now supplies the real online Alembic migration interface.

## Fresh combined verification

All four local CI lanes passed on the merge above with source SHA-256
`98e8ff4aab8ca9f30b4843d84e2fcd44ba10766a48ddd551b06b1f5f39aa4b34`.
Backend and QA used separate fresh hash-locked environments. Node 22.22.0 / npm 10.9.4 and
Python 3.12.12 were selected. Contract and Frontend installs ran serially. Every command
below exited 0. Executed mandatory cases had no skips or expected-failure masking.

| Command / check | Result |
| --- | --- |
| `python .github/ci/checks.py backend` | Locked install/pip check, Ruff/format/mypy; **267 pytest cases**, including 30 new T009 unit cases |
| `python .github/ci/checks.py contract` | T005 self-test: 18 operation matrices, 71 schema fixtures, 20 negative guards, TypeSpec/OpenAPI/generated TS checks and byte-for-byte regeneration |
| `python .github/ci/checks.py frontend` | Locked install/audit, typecheck/build; **85 Playwright cases** |
| `SLOTBOOK_CATALOG_MODE=authoring python .github/ci/checks.py qa` | Independent locked installs/audits, Ruff/format/typecheck; **317 Python + 4 browser + 23 CI policy cases** |
| From Backend: `python -m ruff check app tests migrations`; `python -m ruff format --check app tests migrations`; `python -m mypy app migrations` | All pass, including migration files omitted by the ordinary Backend lane |
| Reviewed private `verify_postgres.py` driver with merged Backend mounted read-only | **26 real PostgreSQL acceptance groups**, driver and cleanup exit 0 |
| `docker build --platform linux/arm64 --iidfile <private-output>/image.id backend` | Fresh pinned image build succeeds; embedded static/test/timezone checks pass |
| `docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,mode=1777 IMAGE python -m pytest -q` | **267 cases pass** inside the freshly built image |
| Frozen comparison, ownership/ancestry, `git diff --check`, `git fsck --full --no-reflogs` | Pass; dangling objects are not corruption |

The Python commands use `TZ=UTC` and `PYTHONTZPATH=''`; packaged tzdata is 2026.5 / IANA
2026e. Browser versions are Playwright 1.64.1 / Chromium 156.0.8078.4, revision 1248.
All npm audit gates passed; this does not clear Python/base-image findings. Fresh Backend
image (ARM64): `sha256:f4034c26e7f9f3fe5f109410bf52a82871b19846cf2db98cce3fab1791534357`,
using the approved Python 3.12.15 base. No AMD64 runtime result is claimed.

The real database probe used pinned PostgreSQL 16.15 ARM64 image index
`sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab`,
unique labeled internal networking, synthetic principals, tmpfs storage and no published ports.
Its reviewed client uses the original pinned T007 image with the merged Backend mounted read-only.
The 23 normal groups prove empty/repeat migrations, restricted roles/ACLs and future defaults,
explicit column grants, usable btree_gist, UTC/READ COMMITTED sessions, independent simultaneous
connections, rollback, pooled-setting checks, redacted privilege failures and atomic rejection
of unsafe existing roles/extensions. Three negative groups reject `fsync=off` at migration
and transaction admission without migration side effects. Cleanup removed both owned PostgreSQL
containers and their network. These checks establish configured durability prerequisites;
they do not prove hosting/storage durability or T-02 crash/retry behavior.

| Sanitized ignored evidence under `test-results/` | SHA-256 |
| --- | --- |
| `ci-backend-ad5bc460c641588c/verification.json` | `f6a61ed7363e94c47df5b7017f0d00ab95d858e57dbe00fcae50e3a828c3c8fb` |
| `ci-contract-783131af993476f9/verification.json` | `2d57691eb106bd26e7188ac52cf569a1691a2fcdf96234ea40e14f01c7ee6591` |
| `ci-frontend-374b7a0ed586f10c/verification.json` | `894726fdfece69e6ec6775e5296187a43bc549dbea738a21094169345a0de8b6` |
| `ci-qa-6234a49b255f9954/verification.json` | `0306d64cfc3fd4954f123a5ff2fe9274e463cff10a38bd8f72648950548e0fbf` |
| `backend-database-36afeae751cd/verification.json` | `b2ca87819f5ce9faf6ccd0ad0a5ca2d13f08889eb644954ee42592d77213ca74` |

Raw logs, generated credentials, driver commands and private manifests remain outside Git.
The sanitized database/image record retains input commit, image IDs, assertions, exit codes
and private-record digests without credentials or local machine paths.

## Release risks retained

The original T007 development acceptance does not require zero vulnerabilities. Its prior
scan recorded 296 package/advisory matches, including 4 critical and 81 high, using the
2026-10-26 scanner database; this is historical evidence, not a fresh scan or reachability proof.
The [earlier release-risk record](backend-foundations.md) remains authoritative: reviewed
Starlette/AnyIO constraint-and-lock maintenance, Python/base/pip/Debian OpenSSL provenance,
the separately bundled psycopg OpenSSL replacement and vendor-open findings still need
remediation or applicable release-risk disposition. The base alone cannot fix the bundled library.
The [Frontend image findings](ci-frontend-image.md) also remain open. No dependency or image
finding was waived by this integration. **Unresolved critical risks block production deployment.**
T-02 remains provisional and T-03 conditional on their full runtime, backup and hosting evidence.

## Completion and next handoff

Only T007 and T009 completion markers change: **15/92 complete; 77 unchecked**. All 31 FRs,
19 SCs, 77 scenarios, the 16/16 checklist and frozen API v1 remain unchanged. The separate
progress commit changes only this record and `tasks.md`. Hosted CI must be checked against
the exact published progress commit; local results above are not claims about a hosted run.

`feat/backend` is preserved clean at T010, with no T011 files or commit present at review.
T010 authoring acceptance remains separately verified: 75 new cases, 12 new passes and
63 intentional missing-schema/constraint assertion failures; configured full run 279 passed /
63 failed, exit 1, zero errors/skips. T010 stays unchecked centrally and excluded from the
published branch. No skip, xfail or test suppression was introduced to obtain green Lead checks.
The [existing T011 handoff](discovery-development.md) and current human authorization permit
Backend to continue **from that exact T010 commit** without reset/rebase. Implement configuration
models/migration and pass their mapped tests; remaining T012–T014 red cases must stay visible.
Integrate this red-test/schema chain only when mandatory CI is compatible.

QA may prepare T022's static Compose/overlay/orchestration files after completed T004/T008.
T022 remains unchecked: T017, T020 and T021 plus runtime acceptance are still outstanding.
Then T023 verifies startup/readiness and Lead T024 verifies the foundation slice. T025→T028→
T029→T030 enables the real discovery API; T030 must pass all 35 T026 live cases. Frontend
T027/T031/T032 is already fixture-complete, with no further dependency-ready Frontend task
under the approved graph. QA T033 and Lead T034 still require real combined discovery evidence.
No later implementation task or agent was started by this integration.
