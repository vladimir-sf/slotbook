"""Prepare the guarded T010 fixture and execute pytest inside the candidate image."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL


def connect(host, password):
    for attempt in range(150):
        try:
            return psycopg.connect(
                host=host,
                user="t010_bootstrap",
                dbname="postgres",
                password=password,
                autocommit=True,
                connect_timeout=2,
            )
        except psycopg.OperationalError:
            if attempt == 149:
                raise
            time.sleep(0.1)


def main():
    os.umask(0o077)
    run = os.environ["SCHEMA_RUN"]
    if not re.fullmatch(r"[a-f0-9]{12}", run):
        raise ValueError("invalid_schema_run")
    host = "slotbook-t010-" + run
    prefix = "slotbook_t010_" + run + "_"
    control = prefix + "control"
    password = Path("/run/schema-password").read_text().strip()
    with connect(host, password) as admin, tempfile.TemporaryDirectory() as private:
        actual = admin.execute(
            "SELECT current_setting('server_version'), "
            "current_setting('server_version_num')::int, "
            "current_setting('fsync'), current_setting('synchronous_commit')"
        ).fetchone()
        if not 160000 <= actual[1] < 170000 or actual[2:] != ("on", "on"):
            raise ValueError("invalid_postgres_version_or_settings")
        for role in ("owner", "runtime", "backup", "outsider"):
            admin.execute(
                sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER {} PASSWORD {}").format(
                    sql.Identifier("t010_" + role),
                    sql.SQL(
                        "CREATEDB CREATEROLE"
                        if role == "owner"
                        else "NOCREATEDB NOCREATEROLE"
                    ),
                    sql.Literal(password),
                )
            )
        admin.execute(
            sql.SQL("CREATE DATABASE {} OWNER t010_owner").format(
                sql.Identifier(control)
            )
        )
        admin.execute(
            sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(control), sql.Literal("slotbook:T010:" + run)
            )
        )
        config = Path(private) / "target.json"
        config.write_text(
            json.dumps(
                {
                    "version": 1,
                    "task": "T010",
                    "run_id": run,
                    "container_id": os.environ["SCHEMA_CONTAINER"],
                    "postgres_image_id": os.environ["SCHEMA_IMAGE"],
                    "owner_url": URL.create(
                        "postgresql+psycopg",
                        username="t010_owner",
                        password=password,
                        host=host,
                        database=control,
                    ).render_as_string(hide_password=False),
                }
            )
        )
        env = {**os.environ, "SLOTBOOK_TEST_DATABASE_CONFIG": str(config)}
        args = [sys.executable, "-m", "pytest", "-q", "-p", "inventory"]
        subprocess.run(
            [*args, "--collect-only"], env=env, cwd="/app", check=True, timeout=60
        )
        subprocess.run(
            [*args, "--junitxml=/verification/pytest.xml"],
            env=env,
            cwd="/app",
            check=True,
            timeout=420,
        )
        leftovers = admin.execute(
            "SELECT 1 FROM pg_database WHERE starts_with(datname, %s) AND datname <> %s",
            (prefix, control),
        ).fetchall()
        if leftovers:
            raise ValueError("postgres_case_databases_leftover")
        Path("/verification/postgres-version").write_text(actual[0])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"schema:pytest_exit={exc.returncode}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:
        print("schema:fixture_setup_or_cleanup_failed", file=sys.stderr)
        raise SystemExit(1) from None
