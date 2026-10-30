"""T022 partial static preparation; none of these assertions proves runtime behavior."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from harness import compose, runner
from harness.targets import GuardError

pytestmark = [pytest.mark.harness, pytest.mark.associations("T022")]
ROOT = Path(__file__).resolve().parents[2]


def test_six_runtime_services_have_explicit_startup_dependencies():
    document = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = document["services"]
    assert set(services) == {
        "db",
        "migrate",
        "seed",
        "backend",
        "retention",
        "frontend",
    }
    for service, dependency, condition in (
        ("migrate", "db", "service_healthy"),
        ("seed", "migrate", "service_completed_successfully"),
        ("backend", "seed", "service_completed_successfully"),
        ("retention", "seed", "service_completed_successfully"),
        ("frontend", "backend", "service_healthy"),
        ("frontend", "retention", "service_healthy"),
    ):
        assert services[service]["depends_on"][dependency]["condition"] == condition


# Hand-authored normalized config fixtures. These test guards only; the real Compose
# parser/merge semantics are checked separately by runner.py static-check, never mocked
# into runtime evidence. CI / QA containers do not require a Docker daemon or CLI.
@pytest.fixture
def environment(tmp_path):
    private = (tmp_path / "private").resolve()
    private.mkdir(mode=0o700)
    return compose.synthetic_environment(private)


def configuration(env, variant="qa"):
    labels = {
        "slotbook.disposable": "true",
        "slotbook.run": env["SLOTBOOK_RUN_ID"],
        "slotbook.candidate": env["SLOTBOOK_CANDIDATE_SHA256"],
    }
    backend = {
        "image": env["SLOTBOOK_BACKEND_IMAGE"],
        "build": {"context": env["SLOTBOOK_BACKEND_CONTEXT"]},
        "platform": "linux/arm64",
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "logging": {"driver": "none"},
        "networks": {"default": {}},
        "labels": labels,
    }
    services = {
        name: copy.deepcopy(backend)
        for name in ("migrate", "seed", "backend", "retention", "frontend", "qa")
    }
    services["db"] = {
        "image": compose.POSTGRES,
        "platform": "linux/arm64",
        "networks": {"default": {}},
        "labels": labels,
        "logging": {"driver": "none"},
        "environment": {"POSTGRES_DB": env["SLOTBOOK_DATABASE"]},
        "volumes": [
            {
                "type": "volume",
                "source": "pgdata",
                "target": "/var/lib/postgresql/data",
                "volume": {},
            }
        ],
    }
    settings = [
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
    ]
    services["db"]["command"] = [
        "postgres",
        *(part for setting in settings for part in ("-c", setting)),
    ]
    services["db"]["healthcheck"] = {
        "test": ["CMD-SHELL", 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"']
    }
    dependencies = {
        "migrate": {"db": {"condition": "service_healthy"}},
        "seed": {"migrate": {"condition": "service_completed_successfully"}},
        "backend": {"seed": {"condition": "service_completed_successfully"}},
        "retention": {"seed": {"condition": "service_completed_successfully"}},
        "frontend": {
            "backend": {"condition": "service_healthy"},
            "retention": {"condition": "service_healthy"},
        },
    }
    for name, deps in dependencies.items():
        services[name]["depends_on"] = deps
    services["migrate"].update(
        command=["alembic", "upgrade", "head"],
        environment={"MIGRATION_DATABASE_URL": env["SLOTBOOK_MIGRATION_DATABASE_URL"]},
    )
    services["seed"]["command"] = ["python", "-m", "app.cli.seed"]
    services["backend"].update(
        command=[
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--no-access-log",
        ],
        environment={"DATABASE_URL": env["SLOTBOOK_DATABASE_URL"]},
        healthcheck={"test": ["CMD", "python", "-m", "app.cli.readiness"]},
        ports=[
            {
                "host_ip": "127.0.0.1",
                "target": 8000,
                "published": env["SLOTBOOK_API_PORT"],
            }
        ],
    )
    services["retention"].update(
        command=["python", "-m", "app.workers.retention"],
        healthcheck={"test": ["CMD", "python", "-m", "app.cli.retention_status"]},
    )
    services["frontend"].update(
        image=env["SLOTBOOK_FRONTEND_IMAGE"],
        build={
            "context": env["SLOTBOOK_FRONTEND_CONTEXT"],
            "args": {"VITE_API_BASE_URL": env["SLOTBOOK_BROWSER_API_ORIGIN"]},
        },
        environment={"VITE_API_BASE_URL": env["SLOTBOOK_BROWSER_API_ORIGIN"]},
        ports=[
            {
                "host_ip": "127.0.0.1",
                "target": 5173,
                "published": env["SLOTBOOK_UI_PORT"],
            }
        ],
    )
    qa = services["qa"]
    qa.update(
        image=env["SLOTBOOK_QA_IMAGE"],
        build={"context": env["SLOTBOOK_QA_CONTEXT"]},
        profiles=["qa"],
        user="1000:1000",
        environment={
            "SLOTBOOK_API_BASE_URL": "http://backend:8000",
            "SLOTBOOK_CATALOG_MODE": "live",
        },
        command=[
            "python",
            "-m",
            "pytest",
            "-c",
            "/quality/pytest.ini",
            "/quality/contract",
            "-m",
            "not harness and not schema",
        ],
    )
    qa["volumes"] = [
        {
            "type": "bind",
            "source": env[variable],
            "target": target,
            "read_only": target != "/run/qa-private",
            "bind": {"create_host_path": False},
        }
        for target, variable in (
            ("/quality", "SLOTBOOK_QA_CONTEXT"),
            ("/contracts", "SLOTBOOK_CONTRACT_CONTEXT"),
            ("/run/qa-private", "SLOTBOOK_QA_REPORT_DIR"),
        )
    ]
    if variant == "faults":
        for name, module in (
            ("backend", "tests.support.server"),
            ("retention", "tests.support.worker"),
        ):
            services[name]["command"] = ["python", "-m", module]
            services[name]["volumes"] = [
                {
                    "type": "bind",
                    "source": env["SLOTBOOK_CONTROL_DIR"],
                    "target": "/run/slotbook-control",
                    "bind": {},
                }
            ]
    return {
        "name": env["SLOTBOOK_PROJECT"],
        "services": services,
        "networks": {
            "default": {
                "internal": True,
                "name": env["SLOTBOOK_PROJECT"] + "_default",
                "labels": labels,
            }
        },
        "volumes": {
            "pgdata": {"name": env["SLOTBOOK_PROJECT"] + "_pgdata", "labels": labels}
        },
    }


@pytest.mark.parametrize(
    "path,value,code",
    [
        (
            ("services", "db", "healthcheck", "test"),
            ["CMD", "true"],
            "compose_database_probe",
        ),
        (("name",), "developer-default", "compose_project_mismatch"),
        (("services", "db", "image"), "postgres:16-alpine", "compose_database_invalid"),
        (
            ("services", "db", "ports"),
            [{"published": "5432"}],
            "compose_database_invalid",
        ),
        (
            ("services", "db", "command"),
            ["postgres", "-c", "fsync=off"],
            "compose_database_settings",
        ),
        (("services", "db", "volumes"), [], "compose_database_storage"),
        (("networks", "default", "internal"), False, "compose_network_invalid"),
        (
            ("volumes", "pgdata", "name"),
            "shared-development-data",
            "compose_volume_invalid",
        ),
        (
            ("services", "backend", "depends_on", "seed", "condition"),
            "service_started",
            "compose_dependency_invalid",
        ),
        (("services", "seed", "command"), ["true"], "compose_seed_invalid"),
        (
            ("services", "backend", "healthcheck", "test"),
            ["CMD", "true"],
            "compose_readiness_invalid",
        ),
        (
            ("services", "retention", "healthcheck", "test"),
            ["CMD", "true"],
            "compose_readiness_invalid",
        ),
        (
            ("services", "backend", "ports"),
            [{"host_ip": "0.0.0.0", "target": 8000, "published": "48122"}],
            "compose_ports_invalid",
        ),
        (
            ("services", "backend", "build", "context"),
            "/synthetic-wrong-backend",
            "compose_backend_context",
        ),
        (
            ("services", "backend", "volumes"),
            [{"target": "/app", "source": "/stale-development"}],
            "compose_stale_mount",
        ),
        (
            ("services", "frontend", "volumes"),
            [{"target": "/app/node_modules"}],
            "compose_stale_mount",
        ),
        (
            ("services", "frontend", "build", "args", "VITE_API_BASE_URL"),
            "http://backend:8000",
            "compose_browser_origin",
        ),
        (
            ("services", "frontend", "environment", "VITE_API_BASE_URL"),
            "http://127.0.0.1:49999",
            "compose_browser_origin",
        ),
        (("services", "backend", "labels"), {}, "compose_labels_invalid"),
        (("services", "backend", "privileged"), True, "compose_unsafe_service"),
        (("services", "backend", "network_mode"), "host", "compose_unsafe_service"),
        (("services", "backend", "entrypoint"), ["sh"], "compose_unsafe_service"),
        (("services", "backend", "restart"), "always", "compose_restart_invalid"),
        (
            ("services", "backend", "logging"),
            {"driver": "json-file"},
            "compose_raw_logging",
        ),
        (("services", "qa", "read_only"), False, "compose_privileges_invalid"),
        (
            ("services", "qa", "environment", "SLOTBOOK_CATALOG_MODE"),
            "authoring",
            "compose_qa_live_required",
        ),
        (("services", "qa", "command"), ["true"], "compose_qa_live_required"),
        (("services", "qa", "user"), "0:0", "compose_qa_identity"),
        (("services", "qa", "build", "context"), "/stale-qa", "compose_qa_context"),
    ],
)
def test_controlled_unsafe_configurations_fail_closed(environment, path, value, code):
    config = configuration(environment)
    compose.validate_configuration(config, environment, "qa", ROOT)
    node = config
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(GuardError, match="^" + code + "$"):
        compose.validate_configuration(config, environment, "qa", ROOT)


def test_faults_mount_only_private_control_and_reserved_test_modules(environment):
    config = configuration(environment, "faults")
    compose.validate_configuration(config, environment, "faults", ROOT)
    config["services"]["backend"]["volumes"][0]["source"] = "/var/run/docker.sock"
    with pytest.raises(GuardError, match="compose_control_mount"):
        compose.validate_configuration(config, environment, "faults", ROOT)
    config = configuration(environment, "faults")
    config["services"]["backend"]["command"] = ["uvicorn", "app.main:app"]
    with pytest.raises(GuardError, match="compose_test_entrypoint"):
        compose.validate_configuration(config, environment, "faults", ROOT)


def test_shared_ports_and_migration_identity_are_rejected(environment):
    config = configuration(environment)
    env = {**environment, "SLOTBOOK_UI_PORT": environment["SLOTBOOK_API_PORT"]}
    with pytest.raises(GuardError, match="compose_port_collision"):
        compose.validate_configuration(config, env, "qa", ROOT)
    config["services"]["migrate"]["environment"]["MIGRATION_DATABASE_URL"] = (
        environment["SLOTBOOK_DATABASE_URL"]
    )
    with pytest.raises(GuardError, match="compose_migration_identity"):
        compose.validate_configuration(config, environment, "qa", ROOT)


def test_private_qa_mounts_are_read_only_and_never_auto_created(environment):
    for attribute in ("read_only", "create_host_path"):
        config = configuration(environment)
        mount = config["services"]["qa"]["volumes"][0]
        if attribute == "read_only":
            mount[attribute] = False
        else:
            mount["bind"][attribute] = True
        with pytest.raises(GuardError, match="compose_qa_mounts"):
            compose.validate_configuration(config, environment, "qa", ROOT)


def test_environment_discards_ambient_secrets_urls_and_compose_overrides(
    tmp_path, monkeypatch
):
    for key in (
        "COMPOSE_FILE",
        "COMPOSE_PROFILES",
        "DOCKER_HOST",
        "SLOTBOOK_POSTGRES_PASSWORD",
        "SLOTBOOK_TEST_MANIFEST",
    ):
        monkeypatch.setenv(key, "synthetic-private-sentinel")
    private = (tmp_path / "private").resolve()
    private.mkdir(mode=0o700)
    env = compose.synthetic_environment(private)
    assert "synthetic-private-sentinel" not in json.dumps(env)
    assert "COMPOSE_FILE" not in env and "DOCKER_HOST" not in env
    for key in ("SLOTBOOK_RUNTIME_ENV_FILE", "SLOTBOOK_SEED_ENV_FILE"):
        assert Path(env[key]).stat().st_mode & 0o077 == 0


def test_selected_contexts_reject_dirty_source_before_rendering(monkeypatch):
    monkeypatch.setattr(compose, "validate_manifest", lambda m: m)

    def dirty(_):
        raise GuardError("dirty_source")

    monkeypatch.setattr(compose, "verify_sources", dirty)
    with pytest.raises(GuardError, match="dirty_source"):
        compose.selected_environment({"task_ids": ["T022"]})


def test_selected_contexts_are_from_verified_candidates_not_qa_siblings(
    tmp_path, monkeypatch
):
    components = {}
    for role, context in (
        ("backend", "backend"),
        ("frontend", "frontend"),
        ("qa", "tests"),
    ):
        checkout = (tmp_path / ("selected-" + role)).resolve()
        (checkout / context).mkdir(parents=True)
        components[role] = {
            "checkout": str(checkout),
            "context": context,
            "commit": "a" * 40,
            "platform": "linux/arm64",
        }
    (Path(components["qa"]["checkout"]) / "contracts").mkdir()
    m = {
        "task_ids": ["T022"],
        "components": components,
        "run_id": "static022",
        "target": {
            "project": "slotbook-qa-static022",
            "database": "slotbook_qa_static022",
            "api_port": 48122,
            "ui_port": 48123,
        },
    }
    monkeypatch.setattr(compose, "validate_manifest", lambda m: m)
    seen = []
    monkeypatch.setattr(compose, "verify_sources", lambda m: seen.append(m))
    env = compose.selected_environment(m)
    assert seen == [m]
    assert env["SLOTBOOK_BACKEND_CONTEXT"] == str(
        Path(components["backend"]["checkout"]) / "backend"
    )
    assert env["SLOTBOOK_FRONTEND_CONTEXT"] == str(
        Path(components["frontend"]["checkout"]) / "frontend"
    )
    assert env["SLOTBOOK_BROWSER_API_ORIGIN"] == "http://127.0.0.1:48122"
    components["backend"]["platform"] = "linux/amd64"
    with pytest.raises(GuardError, match="compose_platform_mismatch"):
        compose.selected_environment(m)


def test_static_check_cli_does_not_require_manifest_or_echo_private_errors(
    monkeypatch, capsys
):
    monkeypatch.delenv("SLOTBOOK_TEST_MANIFEST", raising=False)

    def unavailable(_):
        raise FileNotFoundError("synthetic-private-sentinel")

    monkeypatch.setattr(compose, "static_check", unavailable)
    assert runner.main(["static-check"]) == 2
    assert capsys.readouterr().err.strip() == "qa_guard:invalid_private_input"


def test_ordinary_source_has_no_test_controls_and_integration_clears_dev_mounts():
    base = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    assert base["x-slotbook-preparation"]["status"] == "partial-static-only"
    assert base["x-slotbook-preparation"]["blocked_by"] == ["T017", "T020", "T021"]
    for name, service in base["services"].items():
        if name != "db":
            assert not service.get("volumes")
    assert "slotbook-control" not in (ROOT / "docker-compose.yml").read_text()
    integration = (ROOT / "tests/compose.integration.yml").read_text()
    assert "volumes: !reset []" in integration and "ports: !override" in integration
    assert (
        "SLOTBOOK_BACKEND_CONTEXT:?" in integration
        and "SLOTBOOK_FRONTEND_CONTEXT:?" in integration
    )
    assert "profiles: [qa]" in (ROOT / "tests/compose.test.yml").read_text()
