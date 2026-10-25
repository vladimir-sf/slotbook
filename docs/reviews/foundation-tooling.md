# T002–T005 setup tooling completion

Recorded: 2026-10-25. Owner: Lead/Architect. Status: complete after explicit human approval, local integration, and passing post-merge verification.

## Approval and source identities

The human explicitly approved the reviewed first implementation batch and scoped security maintenance, authorized a non-fast-forward merge into local `001-appointment-scheduling`, and authorized task-progress documentation commitment only after mandatory checks pass. No later task, push or deployment is authorized.

| Source | Full commit |
| --- | --- |
| Common agent baseline | `53172acbf392db414fb52b2bf7dea2d48e9f622d` |
| lead | `f0af416df6b5fea1046a686a23e6fe0024ae370f` |
| backend | `3d99883178decf7641d1e22b91fc230c1d1fcb36` |
| frontend | `3b0869a1f1d44da8b23169d5c9a462c321be3fdf` |
| qa | `d653fa36aa77fd025580c9d8bf6e808bbf053103` |
| Verified isolated integration | `61a617e1147bfa8835aa2be20eb2fb684d0e7b0a` |
| Security maintenance | `4fec8d178fa7819bb937e304b06282ff541ec585` |
| Verified Lead merge | `252ffb114a7ad164380fc17e01cad4a241a537d7` |

The original four source commits and review merge history remain ancestors of the Lead merge. No squash or rebase was used. The Lead merge tree exactly equals the approved security commit tree, with no unrelated source changes. Task metadata was unchanged throughout verification.

## Results

All mandatory post-merge checks passed before T002–T005 were marked complete.

| Check | Observed result |
| --- | --- |
| Separate fresh Backend/QA Python 3.12 environments and hash-locked installs | PASS; dependency checks exit 0 |
| Clean locked contracts/Frontend/QA npm installs | PASS |
| npm audit for all three npm projects | Exit 0; zero vulnerabilities in each |
| T005 compile/OpenAPI/schema/type/reproducibility gate | PASS; 18 operation matrices, 71 schema fixtures, 20 negative guards |
| Backend Ruff, formatting and mypy | Exit 0 for every command |
| Backend pytest | 7 passed; zero failed/skipped |
| Frontend typecheck, production build and Playwright | Exit 0; 54 passed, zero failed/skipped |
| QA Python checks, Ruff/format, TypeScript and Playwright | Exit 0; 80 Python plus 4 browser cases passed, zero failed/skipped |
| QA Docker build and isolated network-disabled/read-only smoke | Exit 0; 80 repeated QA tooling cases passed |
| Frozen API, exact source scope, whitespace and Git object integrity | PASS |
| QA runner without an approval manifest | Expected guarded exit 2; no lifecycle operation attempted |
| Evidence sanitization and exact mandatory inventories | PASS; no missing/duplicate/mixed-candidate/skipped cases |

The host suites comprise 145 distinct tooling/scaffold cases; the container repeats 80 QA cases. Schema fixtures and negative guards are static contract verification, not product acceptance scenarios. Frontend port 4173 was checked unused before its self-owned preview started; no unrelated process was terminated.

## Security maintenance

The human-approved override applies only to `@typespec/openapi3@1.17.0 -> @scalar/json-magic@0.13.5 -> undici@7.30.1`. The separate Undici 8.12.3 path is unchanged. Only the contracts manifest override and one lock entry changed in the security commit. TypeSpec stays 1.17.0; canonical/generated API bytes are unchanged. Audits after the Lead clean install report zero findings. Reevaluate/remove the override on a reviewed upstream tooling update.

## Versions and frozen identities

- Node v22.22.0; npm 10.9.4; uv 0.13.5 (Homebrew 2026-10-22 aarch64-apple-darwin).
- Backend/QA Python: 3.12.0/3.12.0.
- Backend pytest 9.1.1; QA pytest 8.4.2.
- Playwright 1.64.1, Chromium 156.0.8078.4, revision 1248 in both browser toolchains.
- TypeSpec compiler/http/openapi/openapi3 1.17.0; openapi-typescript 7.13.0; TypeScript 5.9.3.
- Docker 27.4.0; QA image `sha256:4896dc3591e0f20a1aadbbc11ed15c0f66d1447f01abc26016f7df6869943c12`, linux/arm64, non-root user `65532:65532`.
- Backend tzdata package 2026.5; production/container timezone-source enforcement remains a later task.

Frozen API v1: `adc0b83a4408493ac44d3a7571dfd3d25a758679`.

| Artifact | Unchanged Git blob |
| --- | --- |
| `contracts/main.tsp` | `b5076047fef868a17590d00e5c93753d8e67f044` |
| `contracts/tsp-output/@typespec/openapi3/openapi.yaml` | `3ad47840cc0dd120d070599e9fad218230f4a845` |
| `frontend/src/api/schema.d.ts` | `4b6a9b438f9ed60e8e271acd2b901a9376c738be` |

## Exact commands and observed exits

The commands below ran against the verified Lead merge. `<checkout>` and `<private>` replace local paths. Node/npm used the versions above. Raw logs/reports remain in mode-restricted temporary storage outside source/evidence. Backend and QA environments are independent; browser reports used protected directories and the candidate fingerprint, with JUnit redirect overrides unset. The private review_inventory plugin only froze collection and attached Backend report provenance; Frontend metadata was normalized against its exact frozen collection. Assertion outcomes were not modified.

| Check | Working directory | Command | Exit |
| --- | --- | --- | ---: |
| node-version | `.` | `node --version` | 0 |
| npm-version | `.` | `npm --version` | 0 |
| python-version | `.` | `python3.12 --version` | 0 |
| uv-version | `.` | `uv --version` | 0 |
| backend-venv | `.` | `uv venv '<checkout>/backend/.venv' --python 3.12` | 0 |
| backend-install | `.` | `uv pip install --python '<checkout>/backend/.venv/bin/python' --require-hashes -r backend/requirements.lock` | 0 |
| backend-pip-check | `.` | `uv pip check --python '<checkout>/backend/.venv/bin/python'` | 0 |
| tests-venv | `.` | `uv venv '<checkout>/tests/.venv' --python 3.12` | 0 |
| tests-install | `.` | `uv pip install --python '<checkout>/tests/.venv/bin/python' --require-hashes -r tests/requirements.lock` | 0 |
| tests-pip-check | `.` | `uv pip check --python '<checkout>/tests/.venv/bin/python'` | 0 |
| contracts-npm-ci | `.` | `npm --prefix contracts ci --ignore-scripts` | 0 |
| frontend-npm-ci | `.` | `npm --prefix frontend ci --ignore-scripts` | 0 |
| tests-e2e-npm-ci | `.` | `npm --prefix tests/e2e ci --ignore-scripts` | 0 |
| frontend-browser-install | `frontend` | `npm exec -- playwright install chromium` | 0 |
| tests-e2e-browser-install | `tests/e2e` | `npm exec -- playwright install chromium` | 0 |
| backend-collect | `backend` | `.venv/bin/python -m pytest --collect-only -q -p review_inventory` | 0 |
| qa-collect | `.` | `tests/.venv/bin/python -m pytest -c tests/pytest.ini tests/contract --collect-only -q -p review_inventory` | 0 |
| frontend-collect | `frontend` | `node node_modules/playwright/cli.js test --list --reporter=json` | 0 |
| qa-browser-collect | `tests/e2e` | `node node_modules/playwright/cli.js test --list --reporter=json` | 0 |
| contracts-audit | `.` | `npm --prefix contracts audit --json` | 0 |
| frontend-audit | `.` | `npm --prefix frontend audit --json` | 0 |
| tests-e2e-audit | `.` | `npm --prefix tests/e2e audit --json` | 0 |
| contract-self-test | `.` | `bash scripts/check-contract.sh --self-test` | 0 |
| backend-ruff | `backend` | `.venv/bin/python -m ruff check app tests` | 0 |
| backend-format | `backend` | `.venv/bin/python -m ruff format --check app tests` | 0 |
| backend-mypy | `backend` | `.venv/bin/python -m mypy app` | 0 |
| backend-pytest | `backend` | `.venv/bin/python -m pytest -q -p review_inventory '--junitxml=<private>/backend.xml'` | 0 |
| frontend-typecheck | `.` | `npm --prefix frontend run typecheck` | 0 |
| frontend-build | `.` | `npm --prefix frontend run build` | 0 |
| frontend-playwright | `.` | `npm --prefix frontend test` | 0 |
| qa-pytest | `.` | `tests/.venv/bin/python -m pytest -c tests/pytest.ini tests/contract -p review_inventory '--junitxml=<private>/qa/harness.xml'` | 0 |
| qa-typecheck | `.` | `npm --prefix tests/e2e run typecheck` | 0 |
| qa-playwright | `.` | `npm --prefix tests/e2e test` | 0 |
| qa-ruff | `.` | `tests/.venv/bin/python -m ruff check tests/harness tests/conftest.py tests/contract` | 0 |
| qa-format | `.` | `tests/.venv/bin/python -m ruff format --check tests/harness tests/conftest.py tests/contract` | 0 |
| qa-no-manifest-check | `.` | `tests/.venv/bin/python tests/harness/runner.py check` | 2 |
| qa-no-manifest-collect | `.` | `tests/.venv/bin/python tests/harness/runner.py collect` | 2 |
| frozen-diff | `.` | `git diff --exit-code adc0b83a4408493ac44d3a7571dfd3d25a758679 -- contracts/main.tsp contracts/tsp-output/@typespec/openapi3/openapi.yaml frontend/src/api/schema.d.ts` | 0 |
| whitespace | `.` | `git diff --check 53172acbf392db414fb52b2bf7dea2d48e9f622d HEAD` | 0 |
| docker-info | `.` | `docker info --format '{{.ServerVersion}}'` | 0 |
| qa-docker-build | `.` | `docker build -f tests/Dockerfile -t slotbook-quality:tooling-ad6b1f06857e tests` | 0 |
| qa-docker-smoke | `.` | `docker run --rm --network none --read-only --tmpfs /tmp:rw,mode=1777 --mount 'type=bind,source=<checkout>/tests,target=/quality,readonly' --mount 'type=bind,source=<checkout>/contracts,target=/contracts,readonly' -e SLOTBOOK_CONTRACT=/contracts/tsp-output/@typespec/openapi3/openapi.yaml slotbook-quality:tooling-ad6b1f06857e python -m pytest -c /quality/pytest.ini /quality/contract -o cache_dir=/tmp/pytest-cache` | 0 |
| qa-docker-image | `.` | `docker image inspect slotbook-quality:tooling-ad6b1f06857e --format '{{json .Id}} {{json .Os}} {{json .Architecture}} {{json .Config.User}}'` | 0 |
| git-integrity | `.` | `git fsck --full --no-reflogs` | 0 |
| backend-package-versions | `.` | `'<checkout>/backend/.venv/bin/python' -c 'import importlib.metadata as m,json,sys;print(json.dumps({"python":sys.version.split()[0],"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},sort_keys=True))'` | 0 |
| tests-package-versions | `.` | `'<checkout>/tests/.venv/bin/python' -c 'import importlib.metadata as m,json,sys;print(json.dumps({"python":sys.version.split()[0],"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},sort_keys=True))'` | 0 |
| contracts-npm-versions | `.` | `npm --prefix contracts ls --depth=0 --json` | 0 |
| frontend-npm-versions | `.` | `npm --prefix frontend ls --depth=0 --json` | 0 |
| tests-e2e-npm-versions | `.` | `npm --prefix tests/e2e ls --depth=0 --json` | 0 |
| frontend-browser-versions | `frontend` | `node -e 'const fs=require("node:fs");const path=require("node:path");const {chromium}=require("playwright");(async()=>{const browser=await chromium.launch();console.log(JSON.stringify({playwright:require("playwright/package.json").version,chromium:browser.version(),registry:JSON.parse(fs.readFileSync(path.join(path.dirname(require.resolve("playwright-core/package.json")),"browsers.json"),"utf8")).browsers.filter(b=>b.name==="chromium").map(b=>({name:b.name,revision:b.revision,browserVersion:b.browserVersion}))}));await browser.close();})()'` | 0 |
| tests-e2e-browser-versions | `tests/e2e` | `node -e 'const fs=require("node:fs");const path=require("node:path");const {chromium}=require("playwright");(async()=>{const browser=await chromium.launch();console.log(JSON.stringify({playwright:require("playwright/package.json").version,chromium:browser.version(),registry:JSON.parse(fs.readFileSync(path.join(path.dirname(require.resolve("playwright-core/package.json")),"browsers.json"),"utf8")).browsers.filter(b=>b.name==="chromium").map(b=>({name:b.name,revision:b.revision,browserVersion:b.browserVersion}))}));await browser.close();})()'` | 0 |

## Sanitized evidence

Candidate fingerprint: `e323aacc21e6daf58305dd63f05bffc9695cf09fb8303a11c8944a3d53053005`.

Local ignored artifacts: `test-results/tooling-ad6b1f06857e/verification.json` and `test-results/tooling-ad6b1f06857e/junit.xml`. These do not travel in Git; this committed record preserves the portable source identities, commands and result summary.

| Artifact | SHA-256 |
| --- | --- |
| `verification.json` | `78578b232e1cd9c12bdba608b5143481e95748a9b7c9a8212a1018222a537d75` |
| `junit.xml` | `ab392eb94f96eb299f33d07338cd511e05e2590f4265b37ca205a3f5a0996b38` |

The existing QA allowlist sanitizer validated all four host reports against inventories frozen before execution. Raw streams, fixture values, headers, contacts, tokens, exception text and machine-specific paths are excluded from published evidence.

## Completion boundary

Only T001–T005 are complete: five of 92 tasks, with 87 unchecked tasks preserved. Task IDs, definitions, ownership, dependencies, acceptance criteria, coverage maps and product requirements remain unchanged. The original T001-only authorization notes in earlier handoff/protocol documents remain historical; they do not supersede the later explicit human batch approvals recorded here.

This completes the first setup tooling batch, not all of M0 and not T024 or any MVP user journey. No T006+ work, root Compose lifecycle, PostgreSQL runtime, crash/restore drill or deployment was performed. T-02 remains provisional; T-03 remains conditional pending their required future evidence.
