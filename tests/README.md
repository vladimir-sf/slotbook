# T004 — independent QA tooling and final review

Task scope: T004 only, on `feat/quality`, based on the reviewed commit
`53172acbf392db414fb52b2bf7dea2d48e9f622d`. T001 is complete and is T004's only dependency.
The final review includes every new file, dependency lock, security boundary and acceptance
criterion. The human subsequently authorized one local task commit after acceptance passes.
Shared task progress remains Lead-owned; `tasks.md` is unchanged.

## Source and file ownership

| Input | Identity |
| --- | --- |
| Common original baseline | `53172acbf392db414fb52b2bf7dea2d48e9f622d` |
| Frozen API v1 commit | `adc0b83a4408493ac44d3a7571dfd3d25a758679` |
| Specification blob (A-001/A-002/A-003) | `5cc968b5cbf3ac899b6c46973c2cbd31862e7cde` |
| Task-list blob | `b42ddaa241437eb9cfee6b4015d329ebe9f5d6d0` |
| Execution-protocol blob | `b6288225bdb151a9bef769563983a77283f3bdd9` |
| Corrected agent-prompts blob | `e4aca48dfafdb9cd0d6ddd90422504cd8efd6860` |

All 15 new files are QA-owned and directly support T004:

- `requirements.txt`, `requirements.lock`: seven direct tools and 23 total packages, all
  versions and distribution hashes pinned; no Backend application dependencies.
- `pytest.ini`, `conftest.py`: importlib collection, frozen-byte OpenAPI 3.0 fixtures,
  local-only schema references, synthetic HTTPX transport, hashed case IDs and numeric
  traceability. JUnit requires a protected private path and candidate fingerprint.
- `harness/runner.py`, `harness/targets.py`, `harness/evidence.py`: guarded host interfaces,
  target/source/approval checks, exclusive locks, mandatory inventories and redacted evidence.
- `contract/test_schema_fixtures.py`: 80 positive/negative tooling checks; no live API claims.
- `e2e/package.json`, `e2e/package-lock.json`, `e2e/playwright.config.ts`,
  `e2e/harness.spec.ts`: independent Playwright lock, offline 1280/320px browser fixtures and
  report-redirect rejection tests. Raw reports and working files remain outside source/evidence.
- `Dockerfile`, `.dockerignore`: pinned, non-root QA image; build context includes only its
  Dockerfile and hashed lock. Application/test sources and runtime secrets are not copied.
- This README: operating interface and review evidence.

No Backend/Frontend implementation, shared document, CI, Compose or migration changes are
included. The canonical TypeSpec, generated OpenAPI and generated TypeScript remain unchanged.
No credentials, generated secrets, personal checkout paths, raw reports or test artifacts are
included in the commit scope. Synthetic sentinels and `example.invalid` addresses are test data.

## Guarded interfaces

Invoke `tests/.venv/bin/python tests/harness/runner.py` with `check`, `collect`,
`run --suite backend|infrastructure|contract|concurrency|privacy|e2e`, or
`run --milestone T024|T034`. Runtime execution returns exit 2 until T022 supplies lifecycle
adapters and milestone inventories. T004 executes no application lifecycle command.
Exit 0 means checked/passed, 1 means failed/skipped assertions, 2 means guarded/unwired input.

`SLOTBOOK_TEST_MANIFEST` names a local owner-only JSON file outside selected checkouts and
published evidence. The per-run private directory must be resolved, owned by the caller,
mode 0700, with report/config files 0600 and no symlinks. Unknown manifest fields fail.
Never add credentials, DSNs, runtime secrets, contacts or raw payloads to the manifest.
An approval record transcribes external human authorization; JSON cannot grant approval.

| Required manifest key | Meaning |
| --- | --- |
| `version`, `run_id`, `milestone`, `task_ids` | Version 1, unique alphanumeric run, explicit milestone/task subset |
| `baseline`, `revisions` | Reviewed common commit and full spec/tasks/protocol/Lead source commits |
| `contract` | Frozen commit and exact three Git blobs in `targets.CONTRACTS` |
| `components` | Selected clean Backend/Frontend/QA checkouts, commits, contexts, all required lock hashes, image IDs/digests and Linux platform |
| `compose_sha256` | Fingerprint of privately rendered configuration; no raw resolved configuration is published |
| `target` | Exact unique project/network/volume/DB names and distinct assigned API/UI ports |
| `private_dir` | Protected per-run control/report directory outside source/evidence |
| `evidence_plan` | Reviewed suite/command/mandatory hashed-ID inventories |
| `approval` | Matching run/candidate fingerprint, disposable proof, explicitly allowed operations and external approval-reference hash |

Candidate fingerprint: SHA256 of canonical sorted JSON excluding `approval`. Each selected
commit must descend from the common baseline, be clean, preserve the frozen trio, and match
all Backend, Frontend and QA locks (including the separate QA browser lock).
T022's host adapter must independently inspect actual resource labels, identities, images,
mounts and loopback bindings. Its observations cannot be replaced with manifest assertions.
First provisioning requires unused exact names; subsequent operations compare recorded actual
identities. Network/volume fingerprints must include inspected identity metadata, not a reusable
name alone. Restore requires a separate fresh, empty, approved destination and fenced old writers.
Crash/restore/cleanup require explicit named disposable-scope approval.

A host-wide per-user lock uses the fixed system temporary root and exact project, so another
control directory or `TMPDIR` cannot bypass it. Mutations remain serial per target; intentional
races will use separate connections to the same case DB. Containers receive no Docker socket.

Private `journal.json` names raw XML basenames, suites, fixed command IDs, actual exits and
mandatory IDs. Collection rejects missing, zero, duplicate, reduced-inventory or mixed-candidate
results. Skipped mandatory assertions fail verification. Suite-level failures at any depth cannot
be discarded during sanitization. Captured streams, failure values, headers, bodies, attachments,
SQL messages and local paths are removed by constructing allowlisted output.

Runtime collection publishes only `evidence.json` and sanitized `junit.xml` to ignored
`test-results/<run_id>/`, through staging after a final source recheck. Existing runs are refused.
Offline `collect_selftest` publishes `tooling-evidence.json` with explicit `tooling-only`
provenance, input blobs, source hash, actual versions and frozen Python/browser inventories.
It does not invent runtime component/image claims. Upload only validated collector outputs.

## Final validation and review findings

The exact T004 acceptance text requires: "pin QA FROM images by release and digest" and
"Initially verify guard/redaction tests; lifecycle adapters become executable in T022."
It does not explicitly require a successful image build. The former unavailable-daemon
limitation was therefore not a mandatory T004 blocker. At final review, Docker was usable
outside the sandbox; both the supplemental image build and QA-only container checks passed.

Final review corrected three implementation issues: Playwright environment overrides/symlinks
could redirect raw reports, deeply nested suite errors could disappear from sanitized results,
and a candidate could omit its QA browser lock. Added rejection tests first; four Python
regressions failed before the fixes and then passed. Also fixed the lock namespace's reliance
on caller `TMPDIR`. The container run found and corrected repository-root assumptions in the
synthetic test fixtures; the final fixture checks work without application sources or Git.
No mandatory criterion remains unverified for T004's tooling scope.

| Check / exact command | Final result |
| --- | --- |
| `git branch --show-current`; `git rev-parse HEAD`; `git merge-base --is-ancestor 53172acbf392db414fb52b2bf7dea2d48e9f622d HEAD` | Correct task branch/original baseline; reviewed before staging |
| `uv pip install --python tests/.venv/bin/python --require-hashes -r tests/requirements.lock` | 23 pinned packages installed successfully |
| `uv pip check --python tests/.venv/bin/python` | All 23 installed packages compatible |
| `npm --prefix tests/e2e ci --ignore-scripts` under Node 22.21.1/npm 10.9.4 | Lock installs successfully; six packages, audit found zero vulnerabilities |
| From `tests/e2e/`: `npm exec -- playwright install chromium` | Locked Chromium/headless revision 1248 installed |
| `tests/.venv/bin/python -m pytest -c tests/pytest.ini tests/contract` | Exit 0; 80 passed, zero skipped |
| `tests/.venv/bin/python -m pytest -c tests/pytest.ini --collect-only -q` | QA-only collection; no app imports |
| `tests/.venv/bin/python -m ruff check tests/harness tests/conftest.py tests/contract` | Exit 0 |
| `tests/.venv/bin/python -m ruff format --check tests/harness tests/conftest.py tests/contract` | Exit 0 |
| `tests/.venv/bin/python -m compileall -q tests/harness tests/conftest.py tests/contract` | Exit 0 |
| From `tests/e2e/`: `npm run typecheck` under Node 22.21.1 | Exit 0 |
| `npm --prefix tests/e2e run test:list` with private report/candidate environment | Exit 0; four cases |
| `npm --prefix tests/e2e test` with the same environment | Exit 0; four passed, zero skipped |
| `tests/.venv/bin/python tests/harness/runner.py check`, `run --milestone T024`, `collect` without a manifest | Each exit 2 with fixed `qa_guard:manifest_required`, expected refusal |
| `docker info --format '{{.ServerVersion}}'` outside the sandbox | Usable daemon 27.4.0 |
| `docker build -f tests/Dockerfile -t slotbook-quality:t004-review tests` | Exit 0; hashed Linux/arm64 install succeeded |
| `docker run --rm --network none --read-only --tmpfs /tmp:rw,mode=1777 --mount type=bind,source="$PWD/tests",target=/quality,readonly --mount type=bind,source="$PWD/contracts",target=/contracts,readonly -e SLOTBOOK_CONTRACT=/contracts/tsp-output/@typespec/openapi3/openapi.yaml slotbook-quality:t004-review python -m pytest -c /quality/pytest.ini /quality/contract -o cache_dir=/tmp/pytest-cache` | Exit 0; 80 passed as user 65532:65532; no app/DB/network/socket |
| `git diff --exit-code adc0b83a4408493ac44d3a7571dfd3d25a758679 -- contracts/main.tsp contracts/tsp-output/@typespec/openapi3/openapi.yaml frontend/src/api/schema.d.ts` | Exit 0; frozen trio unchanged |
| Full source/untracked-file and lock scans | All 15 paths owned by T004; no sensitive artifacts or machine-specific paths |
| `git diff --check`; `git diff --cached --check` | Required before local commit; staged contents separately reviewed |

Versions: Python 3.12.0 host / 3.12.12 container, Node 22.21.1, npm 10.9.4,
Playwright 1.64.1, Chromium 156.0.8078.4 (revision 1248).
Base index digest (registry verified and successfully pulled/built):
`python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c`.
Built QA image ID: `sha256:5a018f88ebed8f02f95cfdf9b861ba98e37b5f22a6f66b43ed541eaffe2f9fb9`,
platform `linux/arm64`, configured user `65532:65532`.

## Acceptance boundary

All mandatory T004 tooling criteria pass: independent hashed locks and collection, verified
image/browser pins, guarded host interfaces, positive/negative guard and redaction evidence,
private raw output, disabled sensitive recordings and unchanged frozen API/ownership boundaries.
The extra Docker image build and isolated QA container checks also pass.

Compose lifecycle adapters, live component/API/DB verification, clock/fault orchestration,
crash/restore drills, T024/T034 milestone inventories and CI remain outside T004. Offline tooling
assertions are not MVP journey/durability/privacy proof. T-02 stays provisional; T-03 conditional.
Contract changes: **no**. Migration changes: **no**. Shared task status: **unchanged**.
No other task, push, merge or deployment is authorized by this handoff.
