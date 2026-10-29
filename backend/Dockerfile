# T007 backend image / QA handoff. Build context is backend/, working directory /app.
# Build: docker build --platform linux/arm64 -t slotbook-backend:t007 backend
# The verified multi-platform index also contains linux/amd64; verify that target
# separately before claiming it. Pin changes require a reviewed rebuild and smoke.
FROM python:3.12.15-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70

ENV TZ=UTC \
    PYTHONTZPATH="" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp \
    MYPY_CACHE_DIR=/tmp/mypy-cache \
    RUFF_CACHE_DIR=/tmp/ruff-cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"

WORKDIR /app

# Pip itself comes from the immutable Python image. No unpinned apt installs or
# source-build dependencies: a missing compatible hashed wheel fails the build.
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.lock \
    && python -m pip check

# The default-deny .dockerignore admits component source/config only, never local
# environments, runtime credentials, reports, control files or database dumps.
COPY . .

# This image-only preflight is not an application test switch or HTTP control.
# Every normal command validates the configured timezone source before exec;
# invoking slotbook-entrypoint without arguments reports safe runtime versions.
COPY --chmod=0555 <<'PY' /usr/local/bin/slotbook-entrypoint
#!/usr/local/bin/python
import importlib.metadata
import importlib.resources
import json
import os
import platform
from pathlib import Path
import sys
import zoneinfo


def validate():
    try:
        import tzdata

        if os.environ.get("TZ") != "UTC":
            raise ValueError
        if os.environ.get("PYTHONTZPATH") != "" or zoneinfo.TZPATH:
            raise ValueError
        expected = next(
            line.split("==", 1)[1].split()[0]
            for line in Path("/app/requirements.lock").read_text().splitlines()
            if line.startswith("tzdata==")
        )
        version = importlib.metadata.version("tzdata")
        if version != expected:
            raise ValueError
        source = importlib.resources.files("tzdata.zoneinfo")
        if not source.joinpath("UTC").is_file():
            raise ValueError
        for name in ("UTC", "Europe/Vienna", "Australia/Lord_Howe", "Pacific/Apia"):
            zoneinfo.ZoneInfo.no_cache(name)
        return {
            "python": platform.python_version(),
            "tzdata": version,
            "iana": tzdata.IANA_VERSION,
            "timezone_source": "tzdata",
        }
    except (ImportError, LookupError, OSError, StopIteration, ValueError):
        print("image_timezone_configuration_invalid", file=sys.stderr)
        raise SystemExit(78) from None


versions = validate()
if len(sys.argv) == 1:
    print(json.dumps(versions, sort_keys=True))
else:
    try:
        os.execvp(sys.argv[1], sys.argv[1:])
    except OSError:
        print("image_command_unavailable", file=sys.stderr)
        raise SystemExit(127) from None
PY

# Same immutable image supplies API and tooling. No source or Docker-socket mount
# is needed; read-only rootfs plus a writable /tmp supports tests/static checks.
USER 65532:65532
# Keep generated caches and raw test output in a disposable build mount; none
# become image layers. Runtime verification supplies its own writable /tmp.
RUN --mount=type=tmpfs,target=/tmp slotbook-entrypoint \
    && python -c 'from app.main import app; assert app is not None' \
    && python -m ruff check app tests \
    && python -m ruff format --check app tests \
    && python -m mypy app \
    && python -m pytest -q \
    && python - <<'CHECKS'
import os
import subprocess
import sys


def rejected(args, env):
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 78, "timezone_guard_did_not_reject"
    assert result.stderr.strip() == "image_timezone_configuration_invalid"
    assert not result.stdout, "timezone_guard_unexpected_output"


for override in ({"TZ": "Europe/Vienna"}, {"PYTHONTZPATH": "/usr/share/zoneinfo"}):
    rejected(["slotbook-entrypoint", "python", "-c", "raise AssertionError"],
             {**os.environ, **override})
for injection in (
    "sys.modules['tzdata'] = None; ",
    "from pathlib import Path; from unittest.mock import patch; "
    "patch('importlib.resources.files', return_value=Path('/missing-synthetic-tzdata')).start(); ",
):
    code = ("import runpy, sys; " + injection + "sys.argv = ['slotbook-entrypoint']; "
            "runpy.run_path('/usr/local/bin/slotbook-entrypoint', run_name='__main__')")
    rejected([sys.executable, "-c", code], os.environ)
print("4 image timezone rejection checks passed")
CHECKS

# Runtime: uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
# Port 8000 is internal; QA assigns unused loopback-only published ports. There
# is no reload, automatic migration, seed, database initialization or test hook.
# Current liveness only: GET /health. Readiness remains T021, not /health proof.
# Health CLI (inside a running API container):
# python -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2); assert r.status == 200'
# Version/source check: docker run --rm IMAGE slotbook-entrypoint
# Checks: docker run --rm --network none --read-only --tmpfs /tmp:rw,mode=1777 IMAGE python -m pytest -q
# Static checks replace the final command with python -m ruff check app tests,
# python -m ruff format --check app tests, or python -m mypy app.
#
# Reserved CLI handoff (NOT IMPLEMENTED by T007; must currently fail nonzero):
# T009: alembic upgrade head (one separate migration job, never per API replica).
# T017: python -m app.cli.seed (explicit synthetic dev/test seed only).
# T020: python -m app.workers.retention / python -m app.cli.retention_status.
# T021: python -m app.cli.readiness (future DB/schema/worker preflight).
# T072/T073: python -m app.cli.backup / python -m app.cli.restore.
# Their owning tasks must publish flags, guarded runtime inputs and exact exits
# before QA wires them. No CLI is stubbed or reported as ready here. Secrets and
# DSNs are runtime-only; never build args, image ENV, source or CLI output. API
# and worker will share the same approved DB at runtime. Restore needs separate
# approval and fencing; normal startup never invokes it or rotates generation.
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2); assert r.status == 200"]
ENTRYPOINT ["slotbook-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
