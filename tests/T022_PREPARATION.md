# T022 — partial static preparation

This is **not completed T022** and provides **no runtime integration acceptance**.
Input: published baseline `359741784f98daa589f5113889b878cf9eb0a2cb`, safely fast-forwarded
from the clean QA worktree on `feat/quality`. Preparation prerequisites T004/T008 are complete.
The task list remains unchanged. T017/T020/T021 are absent; T023/T024 remain future gates.
API v1 is frozen at `adc0b83a4408493ac44d3a7571dfd3d25a758679`.

## Implemented static components

- `docker-compose.yml`: six ordinary service definitions, no development bind mounts:
  `db → migrate → seed → backend/retention → frontend`. Conditions require DB health,
  successful one-shot migrations/seed, and both Backend/retention readiness before Frontend.
  The DB probe is only `pg_isready`, never proof of application/schema/worker readiness.
- PostgreSQL `16.15@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab`:
  reviewed T009 index, reverified by content hashes through the official registry. Both AMD64
  and ARM64 config metadata report 16.15. The mutable tag has moved; the reviewed immutable
  index is retained. No image layers were pulled and no platform/runtime claim is made.
  Named persistent storage, fsync/synchronous_commit/full_page_writes on, UTC and READ COMMITTED,
  internal network and no DB host port. SQL/parameter logging is disabled; Docker raw logging
  is disabled. These settings do not prove storage durability, redaction, deletion or backups.
- `compose.integration.yml`: required selected Backend/Frontend contexts, candidate/run labels,
  project-specific network/volume and loopback-only distinct API/UI ports. Compose `!reset`
  removes source/node_modules mounts; `!override` replaces port lists instead of appending.
- `compose.test.yml`: optional `qa` profile, independent QA image/context, internal API address,
  `/quality` and `/contracts` read-only, dedicated private report mount, non-root owner UID/GID,
  no Docker socket or host lifecycle privileges. The command explicitly selects live assertions,
  excluding fixture self-checks. It is **not an accepted/runnable live provider** today.
- `compose.faults.yml`: explicit test-only overlay; ordinary services get no control mount or
  production test switch. Backend-owned test module names must be explicitly supplied; their
  server/worker factories and argv are still unpublished. Protected control is mounted only
  to test Backend/retention processes. Owner UID/GID mapping supports FileClock permissions;
  actual host/container permission behavior remains unverified.
- `harness/compose.py`, `harness/runner.py`: `static-check` invokes only Compose version/config
  commands, using isolated synthetic configuration and private captured streams. It validates
  the actual parser's four resolved variants plus missing-input refusals. Published JSON contains
  hashes, fixed command IDs/counts, static provenance and blockers, never rendered configuration.
  `selected_environment()` requires the existing validated manifest and clean pinned sources
  before resolving component contexts. It does not inspect actual images/resources or build them.
  Existing `check`/`collect` guards are preserved; `run` remains explicitly blocked. There is
  no provision/restart/crash/restore/cleanup executor in this preparation commit.
- `contract/test_compose_preparation.py`: positive structure checks and controlled unsafe
  dependency, DB, context, port, mount, identity, origin, logging and readiness violations.
  These unit fixtures prove guard logic only. Existing T004/T026 regressions remain mandatory.

The initial six-service/dependency test failed against the old three-service scaffold before
implementation (exit 1, one assertion failure); it now passes. No application behavior was added.
Compose parser semantics follow Docker's [startup-order documentation](https://docs.docker.com/compose/how-tos/startup-order/)
and [merge/reset/override documentation](https://docs.docker.com/reference/compose-file/merge/).
The minimum supported syntax version is 2.24.4; local validation uses 2.31.0-desktop.2.

## Configuration and remaining runtime blockers

Ordinary configuration requires explicit `SLOTBOOK_PROJECT`, `SLOTBOOK_DATABASE`,
`SLOTBOOK_PLATFORM`, selected Backend/Frontend image references, assigned API/UI ports,
`SLOTBOOK_BROWSER_API_ORIGIN`, private bootstrap credential, separate migration/runtime DSNs,
and private runtime/seed environment files. No default passwords, developer ports or `.env`
file are read by the static-check command. The historical shared `.env.example` is not a
complete configuration for this scaffold and has not been modified in this QA-only scope.
Do not print resolved Compose configuration; it can contain credentials from those files.

The Frontend receives the **browser-reachable API origin at build time** through T008's
`build.args.VITE_API_BASE_URL`, with the same startup guard value. QA allocation uses
`http://127.0.0.1:<assigned-api-port>`; changing the port requires a new Frontend build/candidate.
An in-network `http://backend:8000` address belongs only to container QA traffic.

Reserved `python -m app.cli.seed`, `app.workers.retention`, `app.cli.retention_status` and
`app.cli.readiness` argv refer to the approved future handoff names. They are **not implemented**
by this commit and cannot be accepted as successful commands. No placeholder returns success,
and liveness `/health` is never substituted for readiness. Before runtime wiring, Backend must
publish their real inputs, flags, exits, synthetic-only seed mode, server/worker factories and
private clock/fault interface. These references must be reconciled with that owner handoff.

Also pending: actual runtime login provisioning with the T009 restricted privilege groups;
private environment/credential validation; immutable candidate image/build inspection; unused
ports/resource collision checks and observed disposable identities; actual provisioning, cold/
repeat startup, migrations, seed, worker preflight and cleanup; host lifecycle adapters and live
provider integration. The optional QA profile's internal URL is configuration only: T026 still
requires the host-verified provider and must not bypass it or substitute MockTransport. T030
must pass the 35 real Backend cases; T033 reruns them against the combined candidate after T024.

There has been no service startup, CLI/migration execution, readiness/API probe, crash, restore,
image build, deployment or claim that the six services work together. This checkpoint does not
clear inherited image/hosting findings, T-02 or T-03. Full T022 runtime completion still requires
all original dependencies and acceptance criteria. Keep T022 unchecked.

## Validation and evidence

Run from the repository root with the isolated QA tools:

```sh
tests/.venv/bin/python tests/harness/runner.py static-check
tests/.venv/bin/python -m pytest -c tests/pytest.ini tests/contract/test_compose_preparation.py
tests/.venv/bin/python -m pytest -c tests/pytest.ini tests/contract
tests/.venv/bin/python -m ruff check tests/harness tests/conftest.py tests/contract .github/ci
tests/.venv/bin/python -m ruff format --check tests/harness tests/conftest.py tests/contract .github/ci
tests/.venv/bin/python -m compileall -q tests/harness tests/contract
```

`static-check` requires a host Compose CLI; it creates no runtime resources and reads no real
manifest/credentials. Temporary selected-context directories, fake image tags and candidate
labels are explicitly synthetic inputs, never candidate/image/target acceptance. Four successful
renders use base; base+integration; base+integration+test+qa profile; and that stack+faults. Two
additional config attempts must reject missing bootstrap password / private test-server handoff.
All raw stdout/stderr stay outside the checkout in a protected temporary directory. Only
`test-results/t022-static-<run>/verification.json` is published, ignored by Git.

The pytest default runs offline QA regressions; it neither requires Docker nor exercises the
live API. Static source-file checks require the repository assets on the host. The optional QA
profile filters those harness/schema checks rather than counting them as live contract evidence.

Before committing, rerun the existing independent CI lanes with their exact locked toolchains:

```sh
python .github/ci/checks.py contract
python .github/ci/checks.py backend
python .github/ci/checks.py frontend
python .github/ci/checks.py qa
git diff --check
git diff --cached --check
```

Local CI results are separate from GitHub-hosted execution, which this task does not trigger.
The final handoff records actual counts, exits, sanitized evidence and the preparation commit.
No dependency locks, Backend/Frontend implementation, component Dockerfiles, frozen TypeSpec,
OpenAPI, generated TypeScript, shared task progress or shared documentation are changed.
