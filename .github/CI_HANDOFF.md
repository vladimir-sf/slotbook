# T006 — initial tooling CI handoff

Authorized scope: T006 only on `feat/quality`, starting clean at
`192a06d5fda29e3a01bac3ff0e8c026ce29c26de`. Dependencies T002, T003, T004 and T005
are complete in the approved task list and the foundation-tooling completion record.
The workflow verifies tooling/scaffolds; it does not establish foundation/product acceptance.

## Files

- `workflows/ci.yml`: four independent GitHub-hosted matrix jobs (contract, Backend,
  Frontend, QA) for push, pull request and manual dispatch.
- `ci/checks.py`: the same fixed command entry point for local and hosted validation;
  fresh isolated Backend/QA virtualenvs, locked installs, private command capture,
  frozen-file/source checks, safe version metadata and allowlisted evidence.
- `ci/inventory.py`: private pytest collection inventory and Backend provenance without
  importing application modules into the independent QA environment.
- `ci/browser-reporter.cjs`: Playwright inventory/results containing only hashed case IDs,
  status and candidate fingerprint; no names, attachments, streams or failure values.
- `ci/test_checks.py`: 23 CI regression/policy tests, including missing, zero, duplicate,
  skipped and mixed-candidate results, XML guards and raw-output containment.
- This handoff.

No Backend/Frontend/contract implementation, dependency lock, shared task list, root Compose
or other task is changed. These helper/test files directly support the workflow at T006's
specified output path and remain entirely in QA-owned `.github/`.

## Workflow behavior and security

Jobs use Python **3.12.12**, Node **22.22.0** and verified npm **10.9.4**; a mismatch fails.
Backend and QA each create a new mode-protected virtualenv outside the checkout and install
only their own `requirements.lock` with `--require-hashes`, then run `pip check`. npm projects
use their own `npm ci --ignore-scripts` and `npm audit --audit-level=low`.
The contract job also needs the Frontend's locked generation tools, per the Lead-owned gate.
GitHub matrix jobs use separate checkouts/runners; local contract/Frontend runs against one
checkout must be serial because both install Frontend generation/test tools.

The hosted runner is explicitly `ubuntu-24.04`. Evidence records the actual runner image
release (`ImageOS`/`ImageVersion`), architecture and runtime versions when hosted. Local runs
are explicitly labeled `local`; no hosted image identity is inferred. Application container
images belong to T007/T008 and are not built or claimed by this initial workflow.

Actions were resolved through the official repositories' release and Git-ref APIs:

| Action | Release | Immutable commit |
| --- | --- | --- |
| [checkout](https://github.com/actions/checkout/releases/tag/v7.0.1) | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| [setup-python](https://github.com/actions/setup-python/releases/tag/v7.1.0) | v7.1.0 | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` |
| [setup-node](https://github.com/actions/setup-node/releases/tag/v7.1.0) | v7.1.0 | `949feb2413d6458794dcd2491c4babbbce0c15c1` |

The workflow grants `contents: read`, disables persisted checkout credentials and dependency
caches, uses ordinary `pull_request`, and has no secret inputs, deployments, service databases,
Docker socket or artifact upload. Action inputs were checked at the pinned commits. Full-commit
pins and minimal token permissions follow [GitHub's secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).
GitHub's Node 24 action runtime is separate from the pinned Node 22 project toolchain.

Raw command streams, JUnit, inventories and browser working files live in a unique owner-only
private temporary directory outside the checkout. Credential-like environment variables and
report-redirection overrides are removed before child commands. Console output contains fixed
command IDs/exits and validated counts/versions. The GitHub job summary and ignored
`test-results/ci-<lane>-<candidate>/verification.json` contain only constructed allowlisted
metadata, hashes and outcomes. Raw streams/reports/media are never uploaded.

Collection is frozen before execution; missing, zero, duplicated, changed, skipped or failed
mandatory cases fail the job. Current required floors are Backend 7, Frontend 54, QA Python 80,
QA browser 4, and CI regressions 23; complete collected identities must match execution.
Frontend owns and launches its fixed loopback port 4173; CI checks it unused first and never
kills an unrelated listener. Sensitive recording settings remain those of the reviewed component
configs (trace/video/screenshots off). No public test-control route is introduced.

Future PostgreSQL/concurrency/privacy/lifecycle and product journey suites are explicitly
outside this tooling scope, deferred to T022/T087 and the applicable story tasks. They are
not represented as passing or implemented by an empty suite. T-02/T-03 remain open.

## Exact validation commands and results

Run from repository root with the pinned Node/npm on PATH and Python 3.12.12 selected.
The four lanes below completed locally using fresh private Python environments and the
same entry point invoked by the workflow. All four reports describe the same tested CI
code/config source fingerprint `e4a98e387df79cc733f467f0c871935055b3fca7d9dd78a842e1e549e5baa661`;
this documentation was added after that validation without changing executable sources.

| Command | Observed result |
| --- | --- |
| `python .github/ci/checks.py contract` | Exit 0; both locked npm installs/audits, Lead `check-contract.sh --self-test`, frozen no-diff all pass |
| `python .github/ci/checks.py backend` | Exit 0; hashed install/pip check, Ruff, format, mypy, **7 pytest cases**, timezone source check |
| `python .github/ci/checks.py frontend` | Exit 0; locked install/audit, typecheck, production build, Chromium install, **54 Playwright cases** |
| `python .github/ci/checks.py qa` | Exit 0; independent hashed install, **23 CI regressions**, QA Ruff/format, **80 Python + 4 browser cases**, npm audit/typecheck |
| `python -m unittest discover -s .github/ci -p 'test_*.py'` | Exit 0; 23 passed, none skipped |
| `python -m ruff check .github/ci` and `python -m ruff format --check .github/ci` (QA locked environment) | Exit 0 |
| `actionlint -shellcheck= .github/workflows/ci.yml` | Exit 0; actionlint 1.7.12 workflow/action/expression validation; external shellcheck unavailable |
| `git diff --exit-code adc0b83a4408493ac44d3a7571dfd3d25a758679 -- contracts/main.tsp contracts/tsp-output/@typespec/openapi3/openapi.yaml frontend/src/api/schema.d.ts` | Exit 0; frozen trio unchanged |
| `git diff --exit-code 192a06d5fda29e3a01bac3ff0e8c026ce29c26de -- backend frontend contracts specs/001-appointment-scheduling/tasks.md` | Exit 0; other owners and shared tasks unchanged |

The entry point executes these relevant component checks, preserving private report locations:

- Contract: `npm ci --ignore-scripts --no-fund` and `npm audit --audit-level=low` in
  `contracts/` and `frontend/`; `bash scripts/check-contract.sh --self-test`.
- Backend: `<private-python> -m pip install --disable-pip-version-check --require-hashes -r backend/requirements.lock`;
  `<private-python> -m pip check`; from `backend/`, `python -m ruff check app tests`,
  `python -m ruff format --check app tests`, `python -m mypy app`, and
  `python -m pytest -q -p inventory --collect-only` followed by execution with private JUnit.
- Frontend: `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`;
  from `frontend/`, `npm exec -- playwright install --with-deps chromium`, frozen reporter
  collection, and `npm test -- --reporter=<CI-reporter>`.
- QA: the independent `tests/requirements.lock` hashed install/pip check; CI unit tests;
  `python -m pytest -q -p inventory -c tests/pytest.ini tests/contract --collect-only` and
  the same selection with private JUnit; `npm --prefix tests/e2e run typecheck` and the
  QA-owned locked Chromium collection/test command with the same private reporter.

The custom reporter validates real assertion statuses, including global browser errors,
against the pre-execution inventory. Tests retain their component-owned commands/configs.
All executed mandatory tests passed with zero skips. npm audits passed for all three projects.
Backend tzdata is **2026.5 / IANA 2026e**, loaded through empty `PYTHONTZPATH`; both browser
lanes ran Playwright **1.64.1**, Chromium **156.0.8078.4**, revision **1248**.

The actionlint macOS ARM64 release archive was verified against the official release's SHA256
`aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f` before local use.
Dependency/bootstrap output stayed private. CI regression checks were authored alongside the
new workflow/helpers; no missing-workflow/environment error is claimed as a meaningful red test.

## Review status and limitations

T006's implementation and local acceptance checks pass. **No GitHub-hosted run has occurred**;
Ubuntu image provisioning, remote action execution, and Linux browser dependency installation
remain unverified remotely. The workflow will run only after separately authorized publication.
No branch protection/ruleset change or deployment is included. Runtime application/DB integration
and later acceptance suites remain deferred, rather than waived.

All changes remain uncommitted for review; the Lead owns central task progress. No commit,
push, merge, deployment, other task or agent launch was performed.
Contract changes: **no**. Migration changes: **no**.
