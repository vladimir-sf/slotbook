"""T022 STATIC preparation only. This module contains no lifecycle executor.

The self-check renders four Compose variants with private synthetic inputs; no daemon,
image build/pull, migration, seed or runtime verification is attempted. Selected-context
helpers are preparation interfaces, not evidence that an image or target was inspected.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from harness.targets import (
    canonical,
    fingerprint,
    git,
    private_path,
    require,
    validate_manifest,
    verify_sources,
)

POSTGRES = "postgres:16.15@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab"
SERVICES = {"db", "migrate", "seed", "backend", "retention", "frontend"}
FILES = (
    "docker-compose.yml",
    "tests/compose.integration.yml",
    "tests/compose.test.yml",
    "tests/compose.faults.yml",
)
DEPENDENCIES = (
    ("migrate", "db", "service_healthy"),
    ("seed", "migrate", "service_completed_successfully"),
    ("backend", "seed", "service_completed_successfully"),
    ("retention", "seed", "service_completed_successfully"),
    ("frontend", "backend", "service_healthy"),
    ("frontend", "retention", "service_healthy"),
)


def selected_environment(manifest):
    """Resolve only verified clean candidate contexts, never the caller's sibling defaults.

    Future runtime wiring must ALSO inspect actual image/resource identities and hold the
    target lock. This function neither authorizes nor executes any lifecycle command.
    """
    validate_manifest(manifest)
    require("T022" in manifest["task_ids"], "compose_scope_required")
    verify_sources(manifest)
    components = manifest["components"]
    require(
        len({c["platform"] for c in components.values()}) == 1,
        "compose_platform_mismatch",
    )
    env = {}
    for role, component in components.items():
        root = Path(component["checkout"]).resolve()
        context = (root / component["context"]).resolve()
        require(
            context.is_relative_to(root) and context.is_dir(), "compose_context_invalid"
        )
        env[f"SLOTBOOK_{role.upper()}_CONTEXT"] = str(context)
        env[f"SLOTBOOK_{role.upper()}_IMAGE"] = (
            f"slotbook-{role}:qa-{component['commit']}"
        )
    qa = Path(components["qa"]["checkout"]).resolve()
    contract = (qa / "contracts").resolve()
    require(
        contract.is_relative_to(qa) and contract.is_dir(), "compose_context_invalid"
    )
    target = manifest["target"]
    env.update(
        SLOTBOOK_CONTRACT_CONTEXT=str(contract),
        SLOTBOOK_PROJECT=target["project"],
        SLOTBOOK_DATABASE=target["database"],
        SLOTBOOK_RUN_ID=manifest["run_id"],
        SLOTBOOK_CANDIDATE_SHA256=fingerprint(manifest),
        SLOTBOOK_API_PORT=str(target["api_port"]),
        SLOTBOOK_UI_PORT=str(target["ui_port"]),
        SLOTBOOK_BROWSER_API_ORIGIN=f"http://127.0.0.1:{target['api_port']}",
        SLOTBOOK_PLATFORM=components["qa"]["platform"],
    )
    return env


def validate_configuration(config, env, variant, root):
    """Validate captured `compose config --format json`; NEVER print it or its errors."""
    require(
        variant in {"ordinary", "integration", "qa", "faults"},
        "compose_variant_invalid",
    )
    services = config["services"]
    test_profile = variant in {"qa", "faults"}
    require(
        set(services) == SERVICES | ({"qa"} if test_profile else set()),
        "compose_service_inventory",
    )
    require(config["name"] == env["SLOTBOOK_PROJECT"], "compose_project_mismatch")
    require(
        env["SLOTBOOK_API_PORT"] != env["SLOTBOOK_UI_PORT"], "compose_port_collision"
    )
    for key in ("SLOTBOOK_API_PORT", "SLOTBOOK_UI_PORT"):
        require(
            env[key].isdigit() and 1024 <= int(env[key]) <= 65535,
            "compose_port_invalid",
        )
    for service, dependency, condition in DEPENDENCIES:
        require(
            services[service]["depends_on"][dependency]["condition"] == condition,
            "compose_dependency_invalid",
        )
    db = services["db"]
    require(
        db["healthcheck"]["test"]
        == ["CMD-SHELL", 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'],
        "compose_database_probe",
    )
    require(db["image"] == POSTGRES and not db.get("ports"), "compose_database_invalid")
    require(
        db["environment"]["POSTGRES_DB"] == env["SLOTBOOK_DATABASE"],
        "compose_database_invalid",
    )
    required_settings = {
        "fsync=on",
        "synchronous_commit=on",
        "full_page_writes=on",
        "timezone=UTC",
        "default_transaction_isolation=read committed",
        "log_statement=none",
        "log_min_messages=panic",
        "log_min_error_statement=panic",
        "log_parameter_max_length=0",
        "log_parameter_max_length_on_error=0",
    }
    require(
        db["command"][0] == "postgres"
        and set(db["command"][2::2]) == required_settings
        and db["command"][1::2] == ["-c"] * len(required_settings),
        "compose_database_settings",
    )
    require(
        db["volumes"]
        == [
            {
                "type": "volume",
                "source": "pgdata",
                "target": "/var/lib/postgresql/data",
                "volume": {},
            }
        ],
        "compose_database_storage",
    )
    require(
        config["networks"]["default"]["internal"] is True, "compose_network_invalid"
    )
    require(
        config["networks"]["default"]["name"] == env["SLOTBOOK_PROJECT"] + "_default",
        "compose_network_invalid",
    )
    require(
        config["volumes"]["pgdata"]["name"] == env["SLOTBOOK_PROJECT"] + "_pgdata",
        "compose_volume_invalid",
    )
    require(
        services["migrate"]["command"] == ["alembic", "upgrade", "head"],
        "compose_migration_invalid",
    )
    require(
        "DATABASE_URL" not in services["migrate"]["environment"],
        "compose_migration_identity",
    )
    require(
        services["migrate"]["environment"]["MIGRATION_DATABASE_URL"]
        != services["backend"]["environment"]["DATABASE_URL"],
        "compose_migration_identity",
    )
    require(
        services["seed"]["command"] == ["python", "-m", "app.cli.seed"],
        "compose_seed_invalid",
    )
    require(
        services["backend"]["healthcheck"]["test"]
        == ["CMD", "python", "-m", "app.cli.readiness"],
        "compose_readiness_invalid",
    )
    require(
        services["retention"]["healthcheck"]["test"]
        == ["CMD", "python", "-m", "app.cli.retention_status"],
        "compose_readiness_invalid",
    )
    if variant != "faults":
        require(
            services["backend"]["command"]
            == [
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--no-access-log",
            ],
            "compose_server_invalid",
        )
        require(
            services["retention"]["command"]
            == ["python", "-m", "app.workers.retention"],
            "compose_worker_invalid",
        )
    labels = {
        "slotbook.disposable": "true",
        "slotbook.run": env["SLOTBOOK_RUN_ID"],
        "slotbook.candidate": env["SLOTBOOK_CANDIDATE_SHA256"],
    }
    for name, service in services.items():
        require(
            not any(
                service.get(key)
                for key in (
                    "privileged",
                    "container_name",
                    "pid",
                    "network_mode",
                    "use_api_socket",
                    "entrypoint",
                )
            ),
            "compose_unsafe_service",
        )
        require(
            service.get("platform") == env["SLOTBOOK_PLATFORM"],
            "compose_platform_mismatch",
        )
        require(set(service["networks"]) == {"default"}, "compose_network_invalid")
        require(
            service.get("logging", {}).get("driver") == "none", "compose_raw_logging"
        )
        if variant != "ordinary":
            require(service.get("labels") == labels, "compose_labels_invalid")
        else:
            require(
                service.get("labels", {}).get("slotbook.disposable") != "true",
                "compose_test_labels_in_runtime",
            )
        require(service.get("restart", "no") == "no", "compose_restart_invalid")
        if name != "db":
            require(
                service["read_only"] is True
                and service["cap_drop"] == ["ALL"]
                and "no-new-privileges:true" in service["security_opt"],
                "compose_privileges_invalid",
            )
        if name in {"migrate", "seed", "backend", "retention"}:
            context = (
                root / "backend"
                if variant == "ordinary"
                else Path(env["SLOTBOOK_BACKEND_CONTEXT"])
            )
            require(
                service["build"]["context"] == str(context)
                and service["image"] == env["SLOTBOOK_BACKEND_IMAGE"],
                "compose_backend_context",
            )
        if name in {"backend", "frontend"}:
            port = "8000" if name == "backend" else "5173"
            published = env[
                "SLOTBOOK_API_PORT" if name == "backend" else "SLOTBOOK_UI_PORT"
            ]
            require(
                len(service["ports"]) == 1
                and service["ports"][0]["host_ip"] == "127.0.0.1"
                and str(service["ports"][0]["target"]) == port
                and service["ports"][0]["published"] == published,
                "compose_ports_invalid",
            )
        else:
            require(not service.get("ports"), "compose_ports_invalid")
        mounts = service.get("volumes", [])
        if name not in {"db", "qa"}:
            if variant == "faults" and name in {"backend", "retention"}:
                require(
                    len(mounts) == 1
                    and mounts[0]["target"] == "/run/slotbook-control"
                    and mounts[0]["source"] == env["SLOTBOOK_CONTROL_DIR"]
                    and mounts[0].get("bind", {}).get("create_host_path", False)
                    is False,
                    "compose_control_mount",
                )
                module = env[
                    "SLOTBOOK_TEST_SERVER_MODULE"
                    if name == "backend"
                    else "SLOTBOOK_TEST_WORKER_MODULE"
                ]
                require(
                    module
                    == (
                        "tests.support.server"
                        if name == "backend"
                        else "tests.support.worker"
                    ),
                    "compose_test_entrypoint",
                )
                require(
                    service["command"] == ["python", "-m", module],
                    "compose_test_entrypoint",
                )
            else:
                require(not mounts, "compose_stale_mount")
    if variant != "ordinary":
        require(
            config["networks"]["default"]["labels"] == labels
            and config["volumes"]["pgdata"]["labels"] == labels,
            "compose_labels_invalid",
        )
    frontend = services["frontend"]
    context = (
        root / "frontend"
        if variant == "ordinary"
        else Path(env["SLOTBOOK_FRONTEND_CONTEXT"])
    )
    require(
        frontend["build"]["context"] == str(context)
        and frontend["image"] == env["SLOTBOOK_FRONTEND_IMAGE"],
        "compose_frontend_context",
    )
    origin = "http://127.0.0.1:" + env["SLOTBOOK_API_PORT"]
    require(
        frontend["build"]["args"]["VITE_API_BASE_URL"] == origin
        and frontend["environment"]["VITE_API_BASE_URL"] == origin,
        "compose_browser_origin",
    )
    if test_profile:
        qa = services["qa"]
        require(
            qa["image"] == env["SLOTBOOK_QA_IMAGE"]
            and qa["build"]["context"] == env["SLOTBOOK_QA_CONTEXT"],
            "compose_qa_context",
        )
        require(
            qa["command"]
            == [
                "python",
                "-m",
                "pytest",
                "-c",
                "/quality/pytest.ini",
                "/quality/contract",
                "-m",
                "not harness and not schema",
            ],
            "compose_qa_live_required",
        )
        require(
            qa["profiles"] == ["qa"]
            and qa["user"] == env["SLOTBOOK_QA_UID"] + ":" + env["SLOTBOOK_QA_GID"]
            and env["SLOTBOOK_QA_UID"] != "0",
            "compose_qa_identity",
        )
        require(
            qa["environment"]["SLOTBOOK_API_BASE_URL"] == "http://backend:8000"
            and qa["environment"]["SLOTBOOK_CATALOG_MODE"] == "live",
            "compose_qa_live_required",
        )
        mounts = {m["target"]: m for m in qa["volumes"]}
        require(
            set(mounts) == {"/quality", "/contracts", "/run/qa-private"},
            "compose_qa_mounts",
        )
        for target, variable in (
            ("/quality", "SLOTBOOK_QA_CONTEXT"),
            ("/contracts", "SLOTBOOK_CONTRACT_CONTEXT"),
            ("/run/qa-private", "SLOTBOOK_QA_REPORT_DIR"),
        ):
            require(
                mounts[target]["type"] == "bind"
                and mounts[target]["source"] == env[variable]
                and mounts[target].get("bind", {}).get("create_host_path", False)
                is False,
                "compose_qa_mounts",
            )
        require(
            mounts["/quality"]["read_only"] and mounts["/contracts"]["read_only"],
            "compose_qa_mounts",
        )


def synthetic_environment(private):
    """NON-RUNTIME input, intentionally no image/target acceptance or real credentials."""
    private_path(private, directory=True)
    env = {k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ}
    env.update(
        SLOTBOOK_PROJECT="slotbook-qa-static022",
        SLOTBOOK_RUN_ID="static022",
        SLOTBOOK_DATABASE="slotbook_qa_static022",
        SLOTBOOK_CANDIDATE_SHA256="0" * 64,
        SLOTBOOK_PLATFORM="linux/arm64",
        SLOTBOOK_API_PORT="48122",
        SLOTBOOK_UI_PORT="48123",
        SLOTBOOK_BROWSER_API_ORIGIN="http://127.0.0.1:48122",
        SLOTBOOK_POSTGRES_USER="synthetic_migrator",
        SLOTBOOK_POSTGRES_PASSWORD="synthetic-only",
        SLOTBOOK_DATABASE_URL="postgresql+psycopg://synthetic_runtime:synthetic-only@db:5432/slotbook_qa_static022",
        SLOTBOOK_MIGRATION_DATABASE_URL="postgresql+psycopg://synthetic_migrator:synthetic-only@db:5432/slotbook_qa_static022",
        SLOTBOOK_BACKEND_IMAGE="slotbook-backend:static-only",
        SLOTBOOK_FRONTEND_IMAGE="slotbook-frontend:static-only",
        SLOTBOOK_QA_IMAGE="slotbook-qa:static-only",
        SLOTBOOK_QA_UID="1000",
        SLOTBOOK_QA_GID="1000",
        SLOTBOOK_TEST_SERVER_MODULE="tests.support.server",
        SLOTBOOK_TEST_WORKER_MODULE="tests.support.worker",
    )
    for key, name in (
        ("BACKEND_CONTEXT", "selected-backend/backend"),
        ("FRONTEND_CONTEXT", "selected-frontend/frontend"),
        ("QA_CONTEXT", "selected-qa/tests"),
        ("CONTRACT_CONTEXT", "selected-qa/contracts"),
        ("QA_REPORT_DIR", "reports"),
        ("CONTROL_DIR", "control"),
    ):
        path = private / name
        path.mkdir(mode=0o700, parents=True)
        env["SLOTBOOK_" + key] = str(path)
    for key, name in (
        ("RUNTIME_ENV_FILE", "runtime.env"),
        ("SEED_ENV_FILE", "seed.env"),
    ):
        path = private / name
        path.write_text("# synthetic static-check only\n")
        path.chmod(0o600)
        env["SLOTBOOK_" + key] = str(path)
    return env


def static_check(root):
    """Docker Compose schema/interpolation/merge validation; config commands ONLY."""
    root = root.resolve()
    os.umask(0o077)
    private = Path(tempfile.mkdtemp(prefix="slotbook-compose-static-")).resolve()
    require(not private.is_relative_to(root), "private_source_overlap")
    env = synthetic_environment(private)
    watched = (*FILES, "tests/harness/compose.py", "tests/harness/runner.py")
    inputs = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in watched}
    version = subprocess.run(
        ["docker", "compose", "version", "--short"],
        env=env,
        capture_output=True,
        timeout=15,
    )
    require(version.returncode == 0, "compose_cli_unavailable")
    text = version.stdout.decode().strip().removeprefix("v")
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)[a-zA-Z0-9.-]*", text)
    require(
        match and tuple(map(int, match.groups())) >= (2, 24, 4), "compose_cli_version"
    )
    report = {
        "task": "T022",
        "status": "partial-static-preparation",
        "evidence_class": "synthetic-configuration-only",
        "runtime_verified": False,
        "blocked_by": ["T017", "T020", "T021"],
        "compose_version": text,
        "source_sha256": inputs,
        "checks": [],
        "source_commit": git(root, "rev-parse", "HEAD"),
        "input_blobs": {
            p: git(root, "hash-object", p)
            for p in (
                "specs/001-appointment-scheduling/tasks.md",
                "docs/EXECUTION_PROTOCOL.md",
            )
        },
    }
    for variant in ("ordinary", "integration", "qa", "faults"):
        files = [FILES[0]]
        if variant != "ordinary":
            files.append(FILES[1])
        if variant in {"qa", "faults"}:
            files.append(FILES[2])
        if variant == "faults":
            files.append(FILES[3])
        args = [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "--project-directory",
            str(root),
        ]
        for path in files:
            args.extend(["-f", str(root / path)])
        if variant in {"qa", "faults"}:
            args.extend(["--profile", "qa"])
        args.extend(["config", "--format", "json"])
        result = subprocess.run(args, env=env, capture_output=True, timeout=30)
        (private / (variant + ".stdout")).write_bytes(result.stdout)
        (private / (variant + ".stderr")).write_bytes(result.stderr)
        require(result.returncode == 0, "compose_config_invalid")
        config = json.loads(result.stdout)
        validate_configuration(config, env, variant, root)
        report["checks"].append(
            {
                "id": "compose-config-" + variant,
                "exit_code": 0,
                "services": len(config["services"]),
                "config_sha256": hashlib.sha256(result.stdout).hexdigest(),
            }
        )
    # Actual parser refusals distinguish missing private configuration / test-entrypoint
    # handoffs from a valid static model. No lifecycle command is ever constructed.
    for key in ("SLOTBOOK_POSTGRES_PASSWORD", "SLOTBOOK_TEST_SERVER_MODULE"):
        missing = {name: value for name, value in env.items() if name != key}
        result = subprocess.run(args, env=missing, capture_output=True, timeout=30)
        (private / (key + ".stderr")).write_bytes(result.stderr)
        require(
            result.returncode != 0 and key.encode() in result.stderr,
            "compose_missing_input_not_rejected",
        )
        report["checks"].append(
            {
                "id": "missing-" + key.lower(),
                "exit_code": result.returncode,
                "expected": "nonzero",
                "passed": True,
            }
        )
    require(
        inputs
        == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in watched},
        "compose_source_changed",
    )
    base = root / "test-results"
    require(not base.is_symlink(), "unsafe_evidence_path")
    destination = base / ("t022-static-" + uuid.uuid4().hex[:16])
    destination.mkdir(mode=0o700, parents=True)
    (destination / "verification.json").write_bytes(canonical(report))
    print(
        json.dumps(
            {
                "status": report["status"],
                "configurations": 4,
                "runtime_verified": False,
                "evidence": str(destination.relative_to(root) / "verification.json"),
            },
            sort_keys=True,
        )
    )
    return report
