"""Host-side disposable PostgreSQL orchestration for the Backend schema suite."""

import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import uuid


POSTGRES_IMAGE = (
    "postgres@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab"
)
RUN_LABEL = "slotbook.ci.schema"


def run_backend_suite(job, ci_dir, require):
    image_file = job.private / "backend-image.id"
    job.command(
        "backend-image-build",
        ["docker", "build", "--iidfile", image_file, job.root / "backend"],
    )
    image = image_file.read_text().strip()
    require(re.fullmatch(r"sha256:[a-f0-9]{64}", image), "backend_image_invalid")
    job.report["backend_image"] = image

    run = uuid.uuid4().hex[:12]
    database = "slotbook-t010-" + run
    network = database + "-network"
    client = database + "-tests"
    label = f"{RUN_LABEL}={run}"
    output = job.private / "schema-results"
    output.mkdir(mode=0o700)
    # A separate directory removes the bootstrap credential after the run.
    with tempfile.TemporaryDirectory(dir=job.private) as private:
        password = Path(private) / "password"
        password.write_text(secrets.token_urlsafe(32))
        password.chmod(0o600)
        secret_mount = f"type=bind,src={password},dst=/run/schema-password,readonly"
        job.command(
            "postgres-network-create",
            ["docker", "network", "create", "--internal", "--label", label, network],
        )
        try:
            [network_info] = json.loads(
                job.command(
                    "postgres-network-inspect",
                    ["docker", "network", "inspect", network],
                )
            )
            require(
                network_info["Internal"]
                and network_info["Labels"].get(RUN_LABEL) == run,
                "postgres_network_not_private",
            )
            container = (
                job.command(
                    "postgres-start",
                    [
                        "docker",
                        "run",
                        "--detach",
                        "--rm",
                        "--name",
                        database,
                        "--network",
                        network,
                        "--label",
                        label,
                        "--log-driver",
                        "none",
                        "--tmpfs",
                        "/var/lib/postgresql/data:rw,nosuid,noexec,size=512m",
                        "--mount",
                        secret_mount,
                        "--env",
                        "POSTGRES_PASSWORD_FILE=/run/schema-password",
                        "--env",
                        "POSTGRES_USER=t010_bootstrap",
                        "--env",
                        "POSTGRES_DB=postgres",
                        POSTGRES_IMAGE,
                        "postgres",
                        "-c",
                        "timezone=UTC",
                        "-c",
                        "fsync=on",
                        "-c",
                        "synchronous_commit=on",
                        "-c",
                        "shared_buffers=16MB",
                        "-c",
                        "max_connections=20",
                        "-c",
                        "log_statement=none",
                        "-c",
                        "log_min_error_statement=panic",
                        "-c",
                        "log_parameter_max_length_on_error=0",
                    ],
                )
                .decode()
                .strip()
            )
            [info] = json.loads(
                job.command("postgres-target-inspect", ["docker", "inspect", container])
            )
            require(
                re.fullmatch(r"[a-f0-9]{64}", container)
                and info["Id"] == container
                and info["Name"] == "/" + database
                and info["Config"]["Labels"].get(RUN_LABEL) == run
                and info["Config"]["Image"] == POSTGRES_IMAGE
                and not any((info["NetworkSettings"]["Ports"] or {}).values())
                and set(info["NetworkSettings"]["Networks"]) == {network}
                and info["NetworkSettings"]["Networks"][network]["NetworkID"]
                == network_info["Id"],
                "postgres_target_not_disposable",
            )
            uid, gid = os.getuid(), os.getgid()
            require(uid != 0, "schema_test_runner_requires_non_root")
            job.command(
                "backend-postgres-suite",
                [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    client,
                    "--label",
                    label,
                    "--network",
                    network,
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "--user",
                    f"{uid}:{gid}",
                    "--tmpfs",
                    "/tmp:rw,mode=1777",
                    "--mount",
                    secret_mount,
                    "--mount",
                    f"type=bind,src={output},dst=/verification",
                    "--mount",
                    f"type=bind,src={ci_dir / 'inventory.py'},dst=/ci/inventory.py,readonly",
                    "--mount",
                    f"type=bind,src={ci_dir / 'postgres_client.py'},dst=/ci/postgres_client.py,readonly",
                    "--env",
                    "PYTHONPATH=/ci",
                    "--env",
                    "PYTHONDONTWRITEBYTECODE=1",
                    "--env",
                    "SLOTBOOK_CI_INVENTORY=/verification/inventory.json",
                    "--env",
                    "SLOTBOOK_CI_INTEGRATION_INVENTORY=/verification/integration.json",
                    "--env",
                    "SLOTBOOK_CI_LANE=backend",
                    "--env",
                    f"SLOTBOOK_CANDIDATE_SHA256={job.candidate}",
                    "--env",
                    f"SCHEMA_RUN={run}",
                    "--env",
                    f"SCHEMA_CONTAINER={container}",
                    "--env",
                    f"SCHEMA_IMAGE={POSTGRES_IMAGE.split('@')[1]}",
                    image,
                    "python",
                    "/ci/postgres_client.py",
                ],
            )
        finally:
            # Discover only resources carrying this run's unguessable label.
            ids = (
                job.command(
                    "postgres-cleanup-inventory",
                    ["docker", "ps", "-aq", "--filter", f"label={label}"],
                )
                .decode()
                .split()
            )
            require(
                all(re.fullmatch(r"[a-f0-9]{12,64}", value) for value in ids),
                "postgres_cleanup_inventory_invalid",
            )
            try:
                if ids:
                    job.command(
                        "postgres-containers-remove", ["docker", "rm", "-f", *ids]
                    )
            finally:
                job.command(
                    "postgres-network-remove", ["docker", "network", "rm", network]
                )
    return output
