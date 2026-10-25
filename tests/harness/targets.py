"""Private candidate format and host-only target guards. No lifecycle commands in T004.

An approval record transcribes an external human decision; this module cannot grant it.
Observed resource identities must come from the future T022 host adapter, never the manifest.
"""

import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path

BASELINE = "53172acbf392db414fb52b2bf7dea2d48e9f622d"
FROZEN = "adc0b83a4408493ac44d3a7571dfd3d25a758679"
CONTRACTS = {
    "contracts/main.tsp": "b5076047fef868a17590d00e5c93753d8e67f044",
    "contracts/tsp-output/@typespec/openapi3/openapi.yaml": "3ad47840cc0dd120d070599e9fad218230f4a845",
    "frontend/src/api/schema.d.ts": "4b6a9b438f9ed60e8e271acd2b901a9376c738be",
}
OPERATIONS = {
    "check",
    "collect",
    "run",
    "provision",
    "restart",
    "crash",
    "restore",
    "cleanup",
}
LOCKFILES = {
    "backend": {"backend/requirements.lock"},
    "frontend": {"frontend/package-lock.json"},
    "qa": {"tests/requirements.lock", "tests/e2e/package-lock.json"},
}


class GuardError(ValueError):
    """Only fixed safe codes cross the CLI boundary; never interpolate raw input."""


def require(condition, code="invalid_manifest"):
    if not condition:
        raise GuardError(code)


def exact(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys))


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def sha(value):
    return matches(value, r"[0-9a-f]{64}")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def fingerprint(manifest):
    return hashlib.sha256(
        canonical({k: v for k, v in manifest.items() if k != "approval"})
    ).hexdigest()


def private_path(path, *, directory=False):
    """Reject symlinks (including parents), foreign ownership and broad permissions."""
    path = Path(path)
    require(path.is_absolute(), "private_path_required")
    require(
        not any(p.is_symlink() for p in (path, *path.parents)), "unsafe_private_path"
    )
    info = path.stat()
    require(
        info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, "unsafe_private_mode"
    )
    require(
        stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
        "unsafe_private_path",
    )
    return path


def read_private_json(path):
    path = private_path(path)
    require(path.stat().st_size <= 2_000_000, "oversized_private_input")
    return json.loads(path.read_text())


def validate_manifest(m):
    exact(
        m,
        {
            "version",
            "run_id",
            "milestone",
            "task_ids",
            "baseline",
            "revisions",
            "contract",
            "components",
            "compose_sha256",
            "target",
            "private_dir",
            "approval",
            "evidence_plan",
        },
    )
    require(m["version"] == 1 and type(m["version"]) is int)
    require(matches(m["run_id"], r"[a-z0-9]{8,24}"))
    require(m["milestone"] in {"T004", "T024", "T034"})
    require(
        isinstance(m["task_ids"], list)
        and m["task_ids"]
        and all(matches(t, r"T0[0-9]{2}") for t in m["task_ids"])
    )
    require(m["baseline"] == BASELINE)
    exact(m["revisions"], {"spec", "tasks", "protocol", "lead"})
    require(all(matches(v, r"[0-9a-f]{40}") for v in m["revisions"].values()))
    require(m["contract"] == {"revision": FROZEN, "blobs": CONTRACTS}, "contract_drift")
    exact(m["components"], {"backend", "frontend", "qa"})
    for role, c in m["components"].items():
        exact(
            c,
            {
                "checkout",
                "commit",
                "context",
                "locks",
                "image_id",
                "image_digest",
                "platform",
            },
        )
        require(isinstance(c["checkout"], str) and Path(c["checkout"]).is_absolute())
        require(matches(c["commit"], r"[0-9a-f]{40}"))
        require(
            c["context"]
            == {"backend": "backend", "frontend": "frontend", "qa": "tests"}[role]
        )
        require(
            isinstance(c["locks"], dict) and set(c["locks"]) == LOCKFILES[role],
            "lock_inventory_mismatch",
        )
        for path, digest in c["locks"].items():
            require(
                isinstance(path, str)
                and not Path(path).is_absolute()
                and ".." not in Path(path).parts
            )
            require(path.startswith(c["context"] + "/") and sha(digest))
        require(matches(c["image_id"], r"sha256:[0-9a-f]{64}"))
        require(matches(c["image_digest"], r"sha256:[0-9a-f]{64}"))
        require(c["platform"] in {"linux/amd64", "linux/arm64"})
    require(sha(m["compose_sha256"]))
    t = m["target"]
    exact(t, {"project", "database", "network", "volume", "api_port", "ui_port"})
    project = "slotbook-qa-" + m["run_id"]
    require(t["project"] == project and t["database"] == "slotbook_qa_" + m["run_id"])
    require(t["network"] == project + "_default" and t["volume"] == project + "_pgdata")
    require(
        all(
            type(t[p]) is int and 1024 <= t[p] <= 65535 for p in ("api_port", "ui_port")
        )
    )
    require(t["api_port"] != t["ui_port"])
    require(isinstance(m["private_dir"], str) and Path(m["private_dir"]).is_absolute())
    plan = m["evidence_plan"]
    require(
        isinstance(plan, dict)
        and plan
        and set(plan)
        <= {
            "harness",
            "backend",
            "infrastructure",
            "contract",
            "concurrency",
            "privacy",
            "e2e",
        }
    )
    for inventory in plan.values():
        exact(inventory, {"command", "required_ids"})
        require(
            inventory["command"]
            in {"qa-pytest", "qa-playwright", "backend-static", "backend-pytest"}
        )
        ids = inventory["required_ids"]
        require(
            isinstance(ids, list)
            and ids
            and all(matches(i, r"QA-[0-9a-f]{64}") for i in ids)
        )
        require(len(set(ids)) == len(ids), "duplicate_inventory")
    a = m["approval"]
    exact(
        a,
        {"run_id", "candidate_sha256", "operations", "disposable", "reference_sha256"},
    )
    require(
        a["run_id"] == m["run_id"] and a["candidate_sha256"] == fingerprint(m),
        "approval_mismatch",
    )
    require(a["disposable"] is True and sha(a["reference_sha256"]), "approval_required")
    require(
        isinstance(a["operations"], list)
        and a["operations"]
        and set(a["operations"]) <= OPERATIONS
    )
    return m


def authorize(m, operation, observed=None):
    validate_manifest(m)
    require(operation in m["approval"]["operations"], "operation_not_approved")
    if operation in {"check", "collect"}:
        return
    require(isinstance(observed, dict), "target_observation_required")
    # First provisioning: the adapter must inspect the exact names and prove ALL unused.
    if operation == "provision":
        exact(observed, {"target", "unused"})
        require(
            observed["target"] == m["target"] and observed["unused"] is True,
            "target_in_use",
        )
        return
    exact(
        observed,
        {
            "target",
            "labels",
            "resource_ids",
            "recorded_ids",
            "database",
            "loopback_only",
            "restore_destination",
            "writers_fenced",
        },
    )
    require(observed["target"] == m["target"], "target_mismatch")
    require(
        observed["labels"]
        == {
            "slotbook.disposable": "true",
            "slotbook.run": m["run_id"],
            "slotbook.candidate": fingerprint(m),
        },
        "target_labels_mismatch",
    )
    ids = observed["resource_ids"]
    exact(
        ids,
        {
            "database_container",
            "backend_container",
            "worker_container",
            "frontend_container",
            "volume",
            "network",
        },
    )
    require(all(matches(v, r"[0-9a-f]{64}") for v in ids.values()), "unknown_resource")
    require(
        ids == observed["recorded_ids"] and len(set(ids.values())) == len(ids),
        "resource_mismatch",
    )
    require(
        observed["database"] == m["target"]["database"]
        and observed["loopback_only"] is True,
        "database_or_port_mismatch",
    )
    if operation == "restore":
        dest = observed["restore_destination"]
        exact(dest, {"name", "empty", "approved", "fresh"})
        require(
            dest
            == {
                "name": m["target"]["database"] + "_restore",
                "empty": True,
                "approved": True,
                "fresh": True,
            }
            and observed["writers_fenced"] is True,
            "restore_not_safe",
        )


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    require(result.returncode == 0, "source_check_failed")
    return result.stdout.decode().strip()


def verify_sources(m):
    """Called before AND after a future runtime run; accepts no dirty candidate sources."""
    validate_manifest(m)
    for c in m["components"].values():
        root = Path(c["checkout"])
        require(
            git(root, "rev-parse", "HEAD") == c["commit"], "source_revision_changed"
        )
        require(
            not git(root, "status", "--porcelain", "--untracked-files=all"),
            "dirty_source",
        )
        git(root, "merge-base", "--is-ancestor", m["baseline"], c["commit"])
        for path, blob in CONTRACTS.items():
            require(git(root, "hash-object", path) == blob, "contract_drift")
        for path, digest in c["locks"].items():
            file = root / path
            require(file.resolve().is_relative_to(root.resolve()), "unsafe_lock_path")
            require(
                hashlib.sha256(file.read_bytes()).hexdigest() == digest, "lock_changed"
            )
    qa = Path(m["components"]["qa"]["checkout"])
    for name, path in {
        "spec": "specs/001-appointment-scheduling/spec.md",
        "tasks": "specs/001-appointment-scheduling/tasks.md",
        "protocol": "docs/EXECUTION_PROTOCOL.md",
    }.items():
        require(
            git(qa, "rev-parse", f"{m['revisions'][name]}:{path}")
            == git(qa, "hash-object", path),
            "input_revision_changed",
        )
    git(qa, "merge-base", "--is-ancestor", m["baseline"], m["revisions"]["lead"])


@contextmanager
def run_lock(private_dir, project):
    """All control directories for one target share a host/uid lock namespace."""
    private_path(private_dir, directory=True)
    require(matches(project, r"slotbook-qa-[a-z0-9]{8,24}"), "unsafe_lock_target")
    # A caller-specific TMPDIR must not permit two runners to lock one project separately.
    directory = Path("/tmp").resolve() / f"slotbook-qa-locks-{os.getuid()}"
    directory.mkdir(mode=0o700, exist_ok=True)
    private_path(directory, directory=True)
    fd = os.open(
        directory / (project + ".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        info = os.fstat(fd)
        require(
            info.st_uid == os.getuid()
            and info.st_mode & 0o077 == 0
            and stat.S_ISREG(info.st_mode),
            "unsafe_lock",
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GuardError("target_locked") from None
        yield
    finally:
        os.close(fd)
