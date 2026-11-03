# PostgreSQL schema foundation publication

Recorded 2026-11-03. The schema merge `0a7b55eae067ad870805cf99134ba43786e0f3e9`
retains the original T010–T014 commits. Reviewed verification fixes are integrated in
`a88b63cba13cb7eaef882b9d6bbf05bff97e31ea`.

| Workstream | Commit |
| --- | --- |
| Backend image checks | `7298fa0e63ddd378d4b1d17201df31ef695d3f75` |
| Disposable PostgreSQL CI | `16f430343509131e90ca120a6f8cffbe17a8da51` |
| Frontend tooling audit | `169c049bc5bb046459c949d41f67604b136ad7bc` |

All four local lanes passed via `python .github/ci/checks.py <lane>`. The Backend
lane built image `sha256:d2985c746864f208d5b6f72c45346b8f533d7132ac68bf1d073369342efe0689`, then verified all 500 collected cases
from the image. This includes 362 database-independent tests and 138 integration cases
against PostgreSQL 16.15. The job verified the isolated network,
disposable target and result inventory and cleaned up the containers and network.
The image build runs static checks, the database-independent tests and timezone
guards. PostgreSQL credentials and fixture configuration exist only during the test run.

The original schema assertions tracked the missing pieces as the batch progressed.
T010 recorded 63 expected failures, then T011, T012 and T013 reduced that count to
37, 16 and 6 respectively. The completed schema and fixture now pass all 500 cases.
The earlier 130 CI setup errors came from a missing database fixture.

The contract self-test regenerated the frozen artifacts byte for byte. The Frontend
passed its locked install, low-threshold audit, typecheck, build and 85 browser cases.
QA passed 355 Python cases, four browser cases and 23 CI policy tests. The Frontend
tooling override resolves [the minimatch advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249)
with 11.0.1. The scoped adapter preserves Redocly 1.x's callable import.

SHA-256 digests of the local sanitized lane reports for the tested merge:

| Lane | SHA-256 |
| --- | --- |
| backend | `f935d7dcabd58b6b576c6f2d21fadb033cfa051ae84ca2f53f5281d006214bc3` |
| contract | `037d18e75dde2e6372747b4dea1ac19c71344b0ed4dee1d46e2c4f3ee8e1af18` |
| frontend | `df852e9e5b63c0cc7326074df20777813d2ce082918c00260abe492ac58e4fae` |
| qa | `15b2a6b9734a21814f85250ada64d7bfa7141a8321456b4bc902ee9e4e513b4a` |

T010–T014 completion is based on this schema verification. T022 remains open for
full application runtime acceptance. The production release restrictions in the
[Backend foundation record](backend-database-foundation.md#release-risks-retained)
and [Frontend image review](ci-frontend-image.md) still apply.

The first [hosted run](https://github.com/vladimir-sf/slotbook/actions/runs/41610233593)
passed Contract, Frontend and QA. Backend built its image and started PostgreSQL,
then failed at container inspection. Follow-up `8cf76a4ccfe7a24dbdfff56ffb2fa5614ec6871c`
separates the pinned PostgreSQL pull from startup and validates the container ID
before inspection. All four local lanes passed on the follow-up merge
`30619455ee042b1ef6e281f3c72589387a9c014b`, including the fresh Backend build and
the complete 500-test PostgreSQL-backed suite.
