# SlotBook API v1 — approved contract freeze and C-002 review

Recorded: 2026-10-25. Current status: HUMAN-APPROVED AND FROZEN API v1 (1.0.0).
Application implementation is not authorized by the freeze. The C-001/C-002 sections below
retain historical review evidence; their pre-approval scope/status statements describe those
review stages. The current approval, revision and change-control record follows at the end.
C-001 input report content blob: `37cbba6a80becfcb338b4a84fc3b6e6d76987b6c`. Prior review evidence is retained below.
Parent approved design: `5f1ce85bc16b25541337b5ef55d6f25d7b3a574d`, actual branch
`001-appointment-scheduling`. The working tree was clean before C-001; C-002 began with exactly the eight expected
uncommitted PRD/contract/generated/report files from C-001. No unexpected changes were found. No commit/push,
implementation tasks or agents were created. The current user instruction authorizes this PRD/
canonical contract reconciliation; older approval-scope statements remain historical records.

## Applied reconciliation

- `docs/PRD.md`: replaced unresolved defaults with all fifteen approved product answers and
  A-001/A-002/A-003; preserves the five MVP journeys, exclusions and FR/SC traceability.
  Covers required descriptions; per-activity blocks; inclusive 1h/1440h start bounds;
  visitor-date grouping; same-day windows and DST portions; booking preservation/cancellation;
  60-minute memory-only sessions; fixed persisted T/E, delayed/failed/uncertain admission;
  distinct qualified restore invalidation; 720-hour deletion/read suppression and backups.
- `contracts/main.tsp`: canonical operations, closed request/response objects, concrete safe
  errors, bearer requirements, response headers, contact union and all approved time/retry/
  session/privacy semantics. This report is evidence, not an alternative API definition.
- Generated `contracts/tsp-output/@typespec/openapi3/openapi.yaml` using existing
  `npm run build` in contracts; generated `frontend/src/api/schema.d.ts` using existing
  `npm run generate:api` in frontend. Neither output was edited independently.
- `.gitignore`: exposes those two derived files for review/sharing; other compiler output,
  dependency directories, secrets and local state stay ignored. Nothing is staged.
- `contracts/package.json`/lock: declare the already installed `@typespec/openapi` 1.17.0
  directly for TypeSpec OpenAPI annotations. Compiler/http/openapi3 remain 1.17.0; no resolved
  dependency version changed. No application, infrastructure or production deployment changed.
- C-002 aligns `docs/ARCHITECTURE.md` and accepted ADR-0001/0002 with the already approved
  design, preserving accepted status, rationale, original GiST SQL and historical provenance.
  It corrects contacts-in-bookings, fixed sessions, recovery/worker boundaries and the distinct-
  attempt concurrency example. No new architectural decision or new ADR is required.
- Approved constitution, specification, all three amendment records, requirements checklist,
  technical plan/research/data model/proposals and original R-003 report remain byte-for-byte
  unchanged. All 77 scenarios and 16/16 quality criteria are preserved. Their descriptions of
  pre-reconciliation source gaps are historical; this report records the changes now applied.

## Reviewed operation surface

All product paths use `/api`. Operational paths remain `/health` and `/ready`.
All operations declare safe 500 internal_error and 503 service_unavailable with no-store.
All protected operations authenticate before parsing/validation/existence disclosure, return
401 + WWW-Authenticate: Bearer, and recheck the fixed session deadline at authorization time.

| Operation | Success | Additional errors / key behavior |
| --- | --- | --- |
| GET /api/activities | 200 Activity[] | Active only, full descriptions |
| GET /api/activities/{slug} | 200 Activity | 404 missing/inactive |
| GET /api/activities/{slug}/slots | 200 Slot[] | 400/404; date + optional displayTimezone; UTC output |
| GET /api/booking-attempts/context | 200 AttemptContext | Public generation, no contact/result lookup |
| POST /api/bookings | 201 new, 200 replay, 202 verified pending | 400/409/410 + phase-specific 503; required private Idempotency-Key |
| POST /api/auth/login | 200 AdminToken | 400/401; expiresAt, no renewal |
| DELETE /api/auth/session | 204 | 401; protected session revocation |
| GET /api/admin/activities | 200 Activity[] | 401; includes inactive |
| POST /api/admin/activities | 200 Activity | 400/401/409; preserves original success status |
| PUT /api/admin/activities/{id} | 200 Activity + preservation count | 400/401/404/409 |
| GET /api/admin/activities/{id}/weekly-windows | 200 WeeklyWindow[] | 400/401/404 |
| PUT /api/admin/activities/{id}/weekly-windows | 200 WeeklyWindow[] + preservation count | 400/401/404; atomic, empty allowed |
| GET /api/admin/activities/{id}/blocked-dates | 200 BlockedDate[] | 400/401/404 |
| POST /api/admin/activities/{id}/blocked-dates | 200 BlockedDate + preservation count | 400/401/404; repeated block returns existing state |
| GET /api/admin/bookings | 200 AdminBooking[] | 401; discriminated present/removed contacts |
| DELETE /api/admin/bookings/{id} | 204, including already canceled | 400/401/404; original cancellation/deletion anchor preserved |
| GET /health | 200 status=ok | Shallow liveness only |
| GET /ready | 200 status=ready | Generic unavailable; no public operator diagnostics |

Eighteen operations on fifteen paths. No guest lookup/detail/cancellation, unblock, hard-delete,
account registration/refresh, export, payment, calendar or external integration operation added.
Malformed UUID paths explicitly return 400 after authentication: this completes technical
validation coverage rather than changing missing-resource behavior (valid missing ID remains 404).

## Compatibility and exact wire decisions to review

- Required description is added to activity reads/writes. Raw input is trimmed BEFORE checking
  1–2000 Unicode code points; normalized read values carry schema length bounds. A raw input
  maxLength would incorrectly reject valid text with surrounding whitespace, so input trimming/
  length enforcement is a documented runtime rule. No extra attendee length/normalization policy.
- Public `Booking` is replaced by contact-free BookingSummary on BOTH first and retry success.
  Protected history becomes AdminBooking.contact with a generated state discriminator. Removed
  contacts forbid attendee fields, not null/fake strings. Old consumers expecting public contacts
  or top-level admin attendee fields must change. No existing feature client is implemented.
- Booking POST requires Idempotency-Key, adds 200/202/410 and concrete error codes. Retry POST
  still needs matching original details; no key-only GET or contact-based recovery exists.
  Generation is a canonical lowercase UUID followed by '.' and canonical unpadded base64url of
  32 random bytes. Public generation alone never authorizes recovery. These specify the approved
  random-generation/private-key design's exact wire representation, not a new product journey.
- FieldError paths name contracted inputs (array indexes allowed); unknown keys use '$', without
  echoing arbitrary submitted names/values. Stable field reasons are required, invalid,
  unknown_field, overlap, duplicate. Mismatch/restore/expiry/auth/unknown errors have no fields; validation, eligibility and
  slug-conflict errors may supply safe field guidance.
- X-Attempt-Expires-At is REQUIRED on 200/201/202/410, and on known admitted terminal rejections;
  it is omitted for unverified admission/lost restore state. Same-status response merging in
  OpenAPI makes some error headers schema-optional; code/evidence-specific presence remains a
  normative TypeSpec rule. 202 also requires Retry-After and matching body expiresAt.
- 409 attempt_invalidated_by_restore is distinct from chronological 410 attempt_expired. Normal
  restart cannot invalidate keys. Pending requires proven committed matching unexpired unfinished
  admission. Fresh rollback/classification and uncertain COMMIT semantics are preserved.
- Bearer protection covers every admin operation and logout. Public calls explicitly inherit
  NoAuth; no optional bearer/security alternative accidentally bypasses protected operations.
- The pinned emitter defaults datetime HEADERS to HTTP-date; explicit RFC 3339 encoding corrects
  X-Attempt-Expires-At to date-time. JSON response instants must still serialize UTC Z.
- plainTime emits format=time, whose standard validator interpretation requires an offset. Local
  working clocks must have none. LocalClock now uses an explicit ISO local-clock pattern (HH:mm,
  optional seconds/fraction), keeping fractional precision and no minute/grid restriction on windows.
- The 1.17 emitter represents never-valued additional properties as `{not:{}}`; the current TS
  generator widens that to an unknown index signature. Canonical TypeSpec OpenAPI annotations
  emit equivalent additionalProperties=false for body models, preserving closed schemas AND
  useful TypeScript excess-field checks. Duration multipleOf=15 is also emitted from TypeSpec.
  Response templates use spreads because nested generic inheritance crashed the pinned emitter.
  All fixes were recompiled/linted; generated files were not patched. No toolchain upgrade.

## C-001 validation history (before environment repair)

Host toolchain: Node v25.6.1, npm 11.9.0; TypeSpec compiler/http/openapi/openapi3 1.17.0;
openapi-typescript 7.13.0. Node 22/container execution is not claimed by these host checks.

| Command / check | Result |
| --- | --- |
| npm run build --prefix contracts | PASS; final compile/emission succeeds with no diagnostics |
| npm run generate:api --prefix frontend | PASS; generated definitions from canonical OpenAPI |
| contracts/node_modules/.bin/tsp format --check contracts/main.tsp | PASS |
| npm ls --prefix contracts --depth=0 | PASS; four direct TypeSpec libraries at 1.17.0 |
| node /tmp/slotbook-verify-canonical-contract.mjs | PASS; local review tooling described below |
| frontend/node_modules/.bin/tsc --noEmit --strict --skipLibCheck false --target ES2022 --module ESNext --moduleResolution Bundler /tmp/slotbook-contract-types-check.ts | PASS; generated-schema positive/expected-negative type checks |
| npm run build --prefix frontend | PASS; TypeScript and Vite scaffold production build |
| Repeated contract build + generation, comparing both output bytes | PASS; identical output hashes below |
| git diff --check | PASS |
| bash scripts/verify.sh | PARTIAL/FAILED: contract compile, generation and frontend build passed; backend pytest stopped during collection with ModuleNotFoundError: fastapi |

C-001 local review tooling used installed YAML/Ajv/Redocly packages, not production routes. It checked
OpenAPI structural validity, unresolved refs, unique operation IDs/parameters, defined paths and
security; all 18 exact status/security/header matrices; 60 positive/negative schema fixtures.
Fixtures cover missing/extra/invalid booking input, contact-free first/retry success, removed-
contact union, pending without identity/contact fields, error/status discrimination, safe field
feedback, UUID/email/date-time/key encoding, offset-free clocks, duration divisibility and Unicode
read-description bounds. Generated TS checks reject extra endsAt/public contact/pending booking
ID fields and allow narrowing the admin contact union. The temporary scripts are local review
tooling, not newly delivered shared CI gates or application tests.

## Readiness, conditions and remaining follow-up

The canonical surface is sufficient for Frontend and Backend to implement independently against
one generated interface: operation IDs, requests, success/status/error unions, auth, discriminator
and response headers are explicit. Frontend uses generated definitions and renders server-returned
UTC slots; Backend must validate/serialize to canonical OpenAPI. Lead retains generated-file
ownership. Integration still requires a human-reviewed frozen/committed common contract baseline,
reviewed task scope and separate implementation approval; no worktrees/agents/tasks are started.

No unresolved product decision or missing required operation was identified in this static review.
Human review must accept the breaking shapes and exact wire/validation details above before freeze.
The following remain explicit limitations/follow-up, not passing claims:

- Semantic rules cannot be proved by schema compilation: trim-before-length, IANA support,
  date/time normalization, status/canceledAt consistency, ordered/nonoverlapping window sets,
  preservation counts, code-specific error headers, fresh authorization and safe messages.
  Backend and HTTPX/QA checks must exercise real responses, including malformed JSON and auth
  precedence; generated TS types are not runtime validators.
- T-02 is still PROVISIONAL. All seventeen [protocol cases](retry-protocol.md), PostgreSQL
  exclusion/config-lock races, rollback, delayed/unknown COMMIT, crash and deadline checks remain
  unexecuted. Neither schema fixtures nor a frontend build demonstrate at-most-once execution.
- T-03 is still CONDITIONAL. Real 720h deletion/read suppression, contact-free backup bytes/restore,
  writer fencing, provider snapshots/WAL/log controls and hosting restrictions remain unverified.
- The only existing application route is scaffold /health; it does not yet supply the newly
  contracted no-store header. Other operations are not implemented. Common error handlers and
  CORS/header/redaction requirements must be verified during implementation, not inferred here.
- C-002 resolves the Python environment failure: all declared backend dependencies are installed
  in ignored `.venv`, the existing /health test passes, and the full scaffold verifier passes
  when that environment is activated. This remains scaffold coverage, not MVP acceptance.
- C-002 completes architecture/ADR alignment: private contacts/attempts/sessions, retention and
  recovery controls, fixed opaque sessions, shared activity locks/lock order, distinct-key
  competitors versus same-key convergence and generation/conformance ownership. Accepted ADR
  intent/history is preserved; no invariant or approved technical decision is replaced. Future
  implementation README/CI/lock updates remain separately scoped work.

Stop for human review. Contract freeze/implementation and T-02/T-03 condition closure are not
inferred from this report. No commit, push, deployment, restore or application change performed.

## C-001 reviewable content revisions (unchanged contract input)

The following content hashes identify this uncommitted review candidate, not human approval.
Report hash is omitted to avoid self-reference. All paths below are repository-relative.

| Artifact | Git content blob | SHA-256 where regeneration was checked |
| --- | --- | --- |
| .gitignore | `a4161b641247195364ed4b7de54200469b3e274b` | `—` |
| docs/PRD.md | `4f07493e345e1da25dd47ffed6d0028a535b98d0` | `—` |
| contracts/main.tsp | `6b7d0ef46273d789ed8af938fb3e38412908d7c5` | `—` |
| contracts/package.json | `107024fc3190ec384f61e76e77e946211f9c16f9` | `—` |
| contracts/package-lock.json | `f48da89fa9e223411156fadf9665cdd9423f42fd` | `—` |
| contracts/tsp-output/@typespec/openapi3/openapi.yaml | `b3094e6f92957789f701517bab3edae6d8b29500` | `f12e81beffb7a1e9ea79632da8311178def021b1e41533a9791c5bb5ad5b8b40` |
| frontend/src/api/schema.d.ts | `4b6a9b438f9ed60e8e271acd2b901a9376c738be` | `d381c8f83ca043e64b2d19e7cbe9f3a77c662cc05abc30cf2cf28f18ed91bc4a` |

## C-002 final completeness assessment

All eighteen operations were checked against the approved specification/PRD, A-001/A-002/A-003,
plan/research, TypeSpec and generated interfaces. No blocking missing operation, undeclared
required outcome or incompatible generated shape was identified. This is a source/schema review,
not a claim that product routes exist or satisfy runtime acceptance.

| Review focus | Finding |
| --- | --- |
| Authorization | Every admin call/logout requires BearerAuth; public calls do not inherit it. Protected 401 precedes parsing/existence disclosure, fixed server expiry and no replay/refresh remain normative. |
| Input/error coverage | Required fields, UUID/email/date-time, closed bodies, duration multiples, safe typed 400/401/404/409/410/500/503 are declared. Invalid protected UUIDs explicitly return 400 after authentication. No default framework 422/HTML contract. |
| Retry boundary | Immutable E=T+24h from a late DB wall-clock sample persisted with binding in successful admission; delayed commit consumes validity. Rollback/uncertain COMMIT never establishes unproved admission/confirmation. |
| Concurrency | Distinct keys compete (201/409); matching keys converge (201 new, 200 replay/current status, stable terminal rejection or verified 202). No revived canceled booking or new-key fallback. |
| Pending | Requires committed matching unexpired unfinished state after fresh classification, known expiry/header and Retry-After; no contact/booking identity or worker promise. |
| 409/410/recovery | Generic mismatch and slot conflict are distinct from qualified restore invalidation; only chronological expiry uses 410. Normal restart preserves valid state; restore invalidation directs host verification. |
| Response privacy | First/retry public confirmations are contact-free and closed. Admin contact union explicitly distinguishes present/removed, including restored-away contacts. Unsafe error fields/extra values are rejected structurally. Message redaction still needs real-runtime verification. |
| Cancellation | Protected 204 acknowledges first/repeated cancellation, with immutable original timestamp/deletion anchor; 400/401/404 remain separate. |
| Timezones/DST | Display-date grouping with optional displayTimezone, activity-local windows/blocks/quarter-hour grid, full continuous-window fit, skipped times and both eligible repeated offsets, inclusive 1h/1440h boundaries are retained. |
| Source/generation | TypeSpec, generated OpenAPI and TS align. No canonical/generated API bytes changed during C-002. All response/request schemas compile in local schema validation; generation remains byte-for-byte identical. |

Frontend and Backend can implement independently against these explicit interfaces AFTER human
approval/freeze and the reviewed common baseline. Cross-field/domain rules (for example IANA
support, exact local-clock parsing, status/canceledAt consistency, trim-before-length and
code/evidence-specific header presence) remain normative source documentation plus required
runtime conformance tests, not guarantees provided by TS declarations or generic JSON Schema.

## C-002 isolated backend environment and exact commands

The only declared Python dependency manifest is `backend/requirements.txt`; it contains runtime
and test dependencies together, including pytest and HTTPX. There is no separate dev/test file,
Python lock or pyproject. Requirements were installed as declared, including currently unused
PyJWT; no package ranges or application/test files were changed to silence failures/warnings.

From the repository root:

```sh
python3 -m venv .venv
uv pip install --python .venv/bin/python --cache-dir /tmp/slotbook-uv-cache -r backend/requirements.txt
.venv/bin/python --version
uv pip check --python .venv/bin/python --cache-dir /tmp/slotbook-uv-cache
```

The first install attempt hit sandbox DNS restrictions. The same install was rerun successfully
with approved network access. Installed 42 packages into the isolated environment; dependency
check passed. Local resolved dependency inventory is retained outside the repo for this review.
The broad declared ranges remain unlocked; this is not a new reproducibility/lock baseline.
Resolved direct dependencies for this run: FastAPI 0.162.0, Uvicorn 0.54.0, SQLAlchemy 2.1.6,
Alembic 1.20.1, psycopg 3.3.6, Pydantic 2.14.1, PyJWT 2.15.1, pwdlib 0.3.1, pytest 9.1.1
and HTTPX 0.28.1. Starlette 1.10.0 emits the warning below.

From `backend/`:

```sh
../.venv/bin/python -m pytest -q
```

Result: **1 passed, 1 warning**. No genuine scaffold test failure remains. The warning is
StarletteDeprecationWarning for TestClient's use of HTTPX (suggesting httpx2). Adding an
undeclared replacement or changing application behavior is unnecessary for this passing test;
review compatibility/locking in separately authorized dependency work.

From the repository root:

```sh
source .venv/bin/activate
bash scripts/verify.sh
```

Result: **PASS**, including TypeSpec compilation, generation, frontend TS/Vite build and the
same backend test (1 passed, 1 warning). This resolves the earlier missing-FastAPI environment
failure. It does not verify any booking endpoint, PostgreSQL transaction, privacy worker or E2E journey.

## C-002 final verification results

| Command / check | Result |
| --- | --- |
| npm run build --prefix contracts | PASS, no TypeSpec diagnostics |
| npm run generate:api --prefix frontend | PASS |
| contracts/node_modules/.bin/tsp format --check contracts/main.tsp | PASS |
| node /tmp/slotbook-verify-canonical-contract.mjs | PASS: OpenAPI structure/ref/security lint, all 18 operation/status/header/security matrices, compilation of every body schema, 71 positive/negative fixtures, unchanged spec/77 scenarios and 16/16 checklist |
| frontend/node_modules/.bin/tsc --noEmit --strict --skipLibCheck false --target ES2022 --module ESNext --moduleResolution Bundler /tmp/slotbook-contract-types-check.ts | PASS: generated-schema positive/expected-negative checks |
| npm run build --prefix frontend (also via activated scaffold verifier) | PASS |
| ../.venv/bin/python -m pytest -q (backend cwd) | PASS: 1 test; 1 dependency deprecation warning |
| uv pip check --python .venv/bin/python --cache-dir /tmp/slotbook-uv-cache | PASS |
| Repeated TypeSpec build + TS generation, comparing output bytes with C-001 input | PASS, identical |
| Git diff/whitespace, Markdown links and scoped secret/machine-path checks | PASS |

Additional fixtures cover auth expiry shape/no refresh token, public generation with no booking
lookup data, closed health/readiness payloads and protected error privacy. No new application
tests or shared CI gates are claimed; the schema/type review scripts remain temporary local tools.

The final source review preserves all 77 acceptance scenarios, 31 FRs, 19 SCs, fifteen recorded
answers, amendments, constitution and 16/16 checklist byte-for-byte. The ADR-0002 SQL block and
ADR-0001 original accepted decision text remain unchanged; the concurrency example is explicitly
qualified for distinct attempts and traced to the already approved design.

## C-002 readiness and unresolved limitations

**Ready for human approval and contract freeze; NOT frozen by this report.** No new ADR or
architectural approval is required for these documentation corrections. Exact wire details and
breaking schema changes described above remain part of the human contract review candidate.

- T-02 stays PROVISIONAL: PostgreSQL concurrency, lock/config races, crash, timeout, unknown/delayed
  commit and idempotency cases are not run. T-03 stays CONDITIONAL: deletion/read suppression,
  contact-free backup/restore and hosting controls are not validated. These remain implementation/
  deployment acceptance conditions; static contract review cannot close them.
- Actual /health still lacks the new no-store header, and product endpoints are absent. This is
  disclosed implementation/conformance work, not a reason to alter the approved contract or
  scaffold behavior during review. Real authorization/time/privacy/error behavior is untested.
- The dependency deprecation warning and unlocked Python ranges are non-blocking follow-up.
  Python 3.12 host tests and the existing Node host toolchain ran; Docker/Node 22, PostgreSQL,
  browser E2E and provider controls were not exercised.
- The root `.venv`, caches, `.env`/secrets and ignored machine-specific Spec Kit selectors remain
  excluded. Git exposes only the intended OpenAPI YAML/generated TS outputs, not other compiler
  output. No credentials or machine-specific agent files were added or staged.

## C-002 exact file scope and review revisions

Changed during this final-review turn: docs/ARCHITECTURE.md, docs/ADR-0001-contract-first.md,
docs/ADR-0002-booking-concurrency.md, and this report. The ignored local .venv is environment
state only. The canonical contract, PRD, package metadata and generated files are unchanged
from the C-001 review inputs; the full uncommitted review candidate comprises the eleven files
listed here, including this report. No application behavior, implementation tasks, agents,
commit, push, deploy or freeze action occurred. Nothing is staged; HEAD remains the approved
technical baseline on 001-appointment-scheduling.

The following content revisions identify the candidate for human review, not approval evidence.
Report hash is omitted to avoid self-reference; all paths are repository-relative.

| Artifact | Git content blob |
| --- | --- |
| .gitignore | `a4161b641247195364ed4b7de54200469b3e274b` |
| docs/PRD.md | `4f07493e345e1da25dd47ffed6d0028a535b98d0` |
| docs/ARCHITECTURE.md | `3425c6f60d8d04606d73a2b3c32feaa5fc4b2826` |
| docs/ADR-0001-contract-first.md | `5235d3787481bf44ff50ff52d71a5e98216bfa9f` |
| docs/ADR-0002-booking-concurrency.md | `69506ed726bed973cdda38a52d1a21dfe5c25666` |
| contracts/main.tsp | `6b7d0ef46273d789ed8af938fb3e38412908d7c5` |
| contracts/package.json | `107024fc3190ec384f61e76e77e946211f9c16f9` |
| contracts/package-lock.json | `f48da89fa9e223411156fadf9665cdd9423f42fd` |
| contracts/tsp-output/@typespec/openapi3/openapi.yaml | `b3094e6f92957789f701517bab3edae6d8b29500` |
| frontend/src/api/schema.d.ts | `4b6a9b438f9ed60e8e271acd2b901a9376c738be` |

## API-v1 human approval and freeze

**Human approval / freeze date**: 2026-10-25 (Europe/Vienna).
**Authority**: The human project owner explicitly approved the canonical contract based on
C-002 and authorized freezing it as the implementation interface baseline plus one local commit
with subject `feat(contract): freeze SlotBook API v1`. No implementation/agent/task authority is inferred.
**Approved C-002 report revision**: Git blob `6d204c12d06daf209d795668960cf7072af91333`.
**Reviewed canonical input revision**: Git blob `6b7d0ef46273d789ed8af938fb3e38412908d7c5`.
**Parent technical baseline Git revision**: `5f1ce85bc16b25541337b5ef55d6f25d7b3a574d`.
**Branch**: `001-appointment-scheduling` (actual branch verified).
**Frozen contract version**: API v1 / OpenAPI info.version 1.0.0. No URL version prefix is added.

**Frozen Git revision** is the local commit introducing this freeze record and the canonical
source blob in the finalization manifest below, with the exact subject above and direct parent
`5f1ce85bc16b25541337b5ef55d6f25d7b3a574d`. The full commit ID is reported in the commit handoff.
To resolve it from subsequent history on this branch:

```sh
git log --reverse --format=%H --fixed-strings --grep='feat(contract): freeze SlotBook API v1' -- contracts/main.tsp
```

The first matching commit is the API-v1 freeze revision; verify its parent and canonical blob
against this record. This containing-commit identity avoids embedding a self-referential commit
hash in its own content. Later metadata/documentation commits must not be mistaken for a new
contract freeze or permission to change the interface.

### Scope, compatibility and change control

The ten C-002 artifact blobs and the report blob were verified before finalization. The only
canonical change after approval is administrative: API version 1.0.0 and the frozen-status/
change-control service description. Paths, operations, schemas, statuses, headers, security and
wire semantics remain exactly the approved review design. Generated files are regenerated from
TypeSpec, never patched. Source/derived metadata changes and final documentation blobs are in
the manifest below; earlier manifests preserve the approved input provenance.

This is the first frozen MVP interface baseline. Compatibility changes from the starter remain
explicit in the review: required descriptions/private attempt key, contact-free public booking
results, protected present/removed contacts, extra retry outcomes and supporting operations.
These approved changes do not establish that earlier starter clients remain compatible.

After freeze, the constitutional contract-first/change process is mandatory:

1. Lead owns canonical TypeSpec and generated OpenAPI/TypeScript. Frontend and Backend must
   not independently modify or fork those interfaces or invent private JSON formats.
2. Propose changes with rationale, affected requirements/acceptance criteria, compatibility,
   impacted owners, migration/integration consequences and required verification. Assess whether
   consumers' shapes, statuses, authentication or behavior would change; do not label such a
   change editorial just because a URL remains the same.
3. Lead reviews; explicit human approval must precede material specification/API changes and
   affected implementation. Reopen affected approval gates and reconcile PRD/spec/plan/ADRs/
   contract/derived artifacts as applicable under constitution Governance.
4. Compile canonical TypeSpec, regenerate OpenAPI/TS, review compatibility and generated diffs,
   run required checks and commit a reviewed shared revision before dependent agents resume.
   Generated-only edits or routine regeneration cannot authorize a source/behavior change.
5. Preserve version/revision provenance and define a replacement approved baseline for material
   changes. Editorial non-semantic corrections follow the constitution's narrower review rule;
   merge/deploy/destructive-operation gates remain separate.

T-02 remains PROVISIONAL pending PostgreSQL concurrency, crash, timeout, delayed/unknown COMMIT
and idempotency evidence. T-03 remains CONDITIONAL pending contact-free backup/restore, deletion/
read-suppression and hosting validation. No runtime condition is closed by this approval, and
no actual restore/deployment is approved. All 77 acceptance scenarios, fifteen clarification
answers, 31 FRs, 19 SCs, amendment records, constitution and checklist 16/16 remain unchanged.

### Freeze verification

Required checks are rerun for the metadata-stamped baseline before the local commit. The recorded
results and final content manifest below identify exactly what was committed; runtime acceptance
limitations from C-002 remain in force. No application code, tasks, agents, push or deployment
is included. Only the reviewed eleven-file contract/documentation scope is eligible for staging.

| Freeze check / exact command | Result |
| --- | --- |
| npm run build --prefix contracts | PASS; version 1.0.0 emitted without diagnostics |
| npm run generate:api --prefix frontend | PASS; generated from canonical OpenAPI |
| node /tmp/slotbook-verify-canonical-contract.mjs | PASS: OpenAPI validation and all 18 status/security/header matrices, every body schema, 71 positive/negative fixtures |
| frontend/node_modules/.bin/tsc --noEmit --strict --skipLibCheck false --target ES2022 --module ESNext --moduleResolution Bundler /tmp/slotbook-contract-types-check.ts | PASS |
| contracts/node_modules/.bin/tsp format --check contracts/main.tsp | PASS |
| source .venv/bin/activate, then bash scripts/verify.sh | PASS: compile, generate, frontend TS/Vite build, backend pytest; 1 passed, 1 pre-existing dependency warning |
| uv pip check --python .venv/bin/python --cache-dir /tmp/slotbook-uv-cache | PASS; installed environment compatible |
| Repeated canonical build + TS generation, comparing both outputs byte for byte | PASS; final SHA-256 values below |
| OpenAPI structural comparison with C-002, ignoring only info.version/description | PASS; operations/schemas/security/statuses/headers unchanged; TS output identical to C-002 |
| python3 /tmp/slotbook-verify-freeze-finalization.py | PASS: unchanged 77 scenarios/15 answers/31 FR/19 SC/checklist 16/16; governing artifacts/app untouched; exact scope, links, whitespace, credential/machine-path and ignore checks |
| git diff --check | PASS |

The backend warning remains StarletteDeprecationWarning for TestClient/HTTPX; it is not a failed
test or a reason to change application behavior. No PostgreSQL/concurrency/crash/timeout/privacy/
backup/hosting verification was performed. The local schema/type/finalization scripts remain
review tooling outside the repository; no new implementation/CI tasks are delivered here.

### Frozen content manifest

These blobs identify the final metadata-stamped source and reviewed documentation/artifacts.
They are the freeze commit's contents, not replacements for the preserved approved-input hashes.
The freeze record itself is excluded to avoid a self-referential hash; it is the eleventh file.
All paths below are repository-relative.

| Artifact | Git content blob | SHA-256 for generated output |
| --- | --- | --- |
| .gitignore | `a4161b641247195364ed4b7de54200469b3e274b` | `—` |
| docs/PRD.md | `5c36ee6eb1f5d7cc30b64a662e450c063b641a5a` | `—` |
| docs/ARCHITECTURE.md | `926254e042202c5d4f945023b56ef21e26246f9e` | `—` |
| docs/ADR-0001-contract-first.md | `5cfce661aabbe309e0e0a81c032f182edae300e3` | `—` |
| docs/ADR-0002-booking-concurrency.md | `69506ed726bed973cdda38a52d1a21dfe5c25666` | `—` |
| contracts/main.tsp | `b5076047fef868a17590d00e5c93753d8e67f044` | `—` |
| contracts/package.json | `107024fc3190ec384f61e76e77e946211f9c16f9` | `—` |
| contracts/package-lock.json | `f48da89fa9e223411156fadf9665cdd9423f42fd` | `—` |
| contracts/tsp-output/@typespec/openapi3/openapi.yaml | `3ad47840cc0dd120d070599e9fad218230f4a845` | `9c4c08233e596536ac3aec4481b4e2e37dab680671c6906c7b5a82d54687a0d1` |
| frontend/src/api/schema.d.ts | `4b6a9b438f9ed60e8e271acd2b901a9376c738be` | `d381c8f83ca043e64b2d19e7cbe9f3a77c662cc05abc30cf2cf28f18ed91bc4a` |
