"""T004 tooling proof only: synthetic schemas and guard/collector failures, no live feature claims."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from jsonschema import ValidationError

from harness import evidence, runner, targets
from harness.targets import BASELINE, CONTRACTS, FROZEN, GuardError, fingerprint

pytestmark = [pytest.mark.harness, pytest.mark.associations("T004")]
QA_ROOT = Path(__file__).resolve().parents[1]
IDENTITY = "00000000-0000-4000-8000-000000000001"
SUMMARY = {
    "id": IDENTITY,
    "activityId": IDENTITY,
    "startsAt": "2026-11-01T09:00:00Z",
    "endsAt": "2026-11-01T09:30:00Z",
    "status": "confirmed",
    "canceledAt": None,
}


@pytest.fixture
def manifest(tmp_path):
    private = (tmp_path / "private").resolve()
    private.mkdir(mode=0o700)
    m = {
        "version": 1,
        "run_id": "synthetic01",
        "milestone": "T004",
        "task_ids": ["T004"],
        "baseline": BASELINE,
        "revisions": {k: BASELINE for k in ("spec", "tasks", "protocol", "lead")},
        "contract": {"revision": FROZEN, "blobs": CONTRACTS},
        "components": {
            role: {
                "checkout": str(tmp_path / ("selected-" + role)),
                "commit": BASELINE,
                "context": context,
                "locks": {
                    path: "1" * 64
                    for path in {
                        "backend": ["backend/requirements.lock"],
                        "frontend": ["frontend/package-lock.json"],
                        "qa": [
                            "tests/requirements.lock",
                            "tests/e2e/package-lock.json",
                        ],
                    }[role]
                },
                "image_id": "sha256:" + "2" * 64,
                "image_digest": "sha256:" + "3" * 64,
                "platform": "linux/arm64",
            }
            for role, context in (
                ("backend", "backend"),
                ("frontend", "frontend"),
                ("qa", "tests"),
            )
        },
        "compose_sha256": "4" * 64,
        "target": {
            "project": "slotbook-qa-synthetic01",
            "database": "slotbook_qa_synthetic01",
            "network": "slotbook-qa-synthetic01_default",
            "volume": "slotbook-qa-synthetic01_pgdata",
            "api_port": 49151,
            "ui_port": 49152,
        },
        "private_dir": str(private),
        "evidence_plan": {
            "harness": {
                "command": "qa-pytest",
                "required_ids": [evidence.case_id("safe-node")],
            }
        },
        "approval": {
            "run_id": "synthetic01",
            "candidate_sha256": "",
            "disposable": True,
            "reference_sha256": "5" * 64,
            "operations": ["check", "collect", "run", "provision"],
        },
    }
    seal(m)
    return m


def seal(m):
    m["approval"]["candidate_sha256"] = fingerprint(m)


def write_private(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


def raw_report(m, *, state=None, secret="synthetic-secret-marker"):
    root = ET.Element("testsuite", {"name": secret, "hostname": secret})
    case = ET.SubElement(
        root, "testcase", {"name": secret, "classname": secret, "file": secret}
    )
    props = ET.SubElement(case, "properties")
    for name, value in {
        "evidence_id": evidence.case_id("safe-node"),
        "candidate_sha256": fingerprint(m),
        "associations": "T004",
        "Authorization": secret,
    }.items():
        ET.SubElement(props, "property", {"name": name, "value": value})
    if state:
        ET.SubElement(case, state, {"message": secret}).text = secret
    ET.SubElement(case, "system-out").text = secret
    ET.SubElement(root, "system-err").text = secret
    return ET.tostring(root)


def prepare_journal(m, raw=None, exit_code=0):
    private = Path(m["private_dir"])
    report = private / "harness.xml"
    report.write_bytes(raw or raw_report(m))
    report.chmod(0o600)
    journal = {
        "candidate_sha256": fingerprint(m),
        "reports": [
            {
                "suite": "harness",
                "command": "qa-pytest",
                "exit_code": exit_code,
                "file": "harness.xml",
                "required_ids": [evidence.case_id("safe-node")],
            }
        ],
    }
    write_private(private / "journal.json", journal)
    return journal


def test_valid_manifest_and_unused_provision(manifest):
    targets.validate_manifest(manifest)
    targets.authorize(manifest, "check")
    targets.authorize(
        manifest, "provision", {"target": manifest["target"], "unused": True}
    )


@pytest.mark.parametrize(
    "path,value",
    [
        (("baseline",), "a" * 40),
        (("target", "project"), "slotbook-development"),
        (("target", "database"), "production"),
        (("target", "volume"), "shared"),
        (("target", "api_port"), 80),
        (("target", "ui_port"), 49151),
        (("approval", "disposable"), False),
        (("approval", "operations"), ["prune"]),
        (("contract", "revision"), BASELINE),
        (("components", "backend", "image_id"), "latest"),
        (("components", "qa", "locks"), {}),
        (("private_dir",), "relative"),
    ],
)
def test_manifest_rejects_unsafe_fields(manifest, path, value):
    location = manifest
    for key in path[:-1]:
        location = location[key]
    location[path[-1]] = value
    seal(manifest)
    with pytest.raises(GuardError):
        targets.validate_manifest(manifest)


def test_candidate_and_approval_are_bound(manifest):
    manifest["compose_sha256"] = "9" * 64
    with pytest.raises(GuardError, match="approval_mismatch"):
        targets.validate_manifest(manifest)


@pytest.mark.parametrize("operation", ["restart", "crash", "restore", "cleanup"])
def test_unapproved_lifecycle_refused(manifest, operation):
    with pytest.raises(GuardError, match="operation_not_approved"):
        targets.authorize(manifest, operation)


def test_disposable_flag_alone_is_insufficient(manifest):
    with pytest.raises(GuardError, match="target_observation_required"):
        targets.authorize(manifest, "run")
    with pytest.raises(GuardError, match="target_in_use"):
        targets.authorize(
            manifest, "provision", {"target": manifest["target"], "unused": False}
        )


def observation(m):
    ids = {
        key: str(i) * 64
        for i, key in enumerate(
            (
                "database_container",
                "backend_container",
                "worker_container",
                "frontend_container",
                "volume",
                "network",
            ),
            1,
        )
    }
    return {
        "target": m["target"],
        "labels": {
            "slotbook.disposable": "true",
            "slotbook.run": m["run_id"],
            "slotbook.candidate": fingerprint(m),
        },
        "resource_ids": ids,
        "recorded_ids": copy.deepcopy(ids),
        "database": m["target"]["database"],
        "loopback_only": True,
        "restore_destination": None,
        "writers_fenced": False,
    }


@pytest.mark.parametrize(
    "field",
    ["target", "labels", "resource_ids", "recorded_ids", "database", "loopback_only"],
)
def test_live_identity_checks_fail_closed(manifest, field):
    observed = observation(manifest)
    targets.authorize(manifest, "run", observed)
    observed[field] = False if field == "loopback_only" else {}
    with pytest.raises(GuardError):
        targets.authorize(manifest, "run", observed)


@pytest.mark.parametrize(
    "unsafe", ["nonempty", "unfenced", "source", "unapproved", "notfresh"]
)
def test_restore_requires_fresh_empty_approved_destination_and_fence(manifest, unsafe):
    manifest["approval"]["operations"].append("restore")
    seen = observation(manifest)
    seen["writers_fenced"] = True
    seen["restore_destination"] = {
        "name": manifest["target"]["database"] + "_restore",
        "empty": True,
        "approved": True,
        "fresh": True,
    }
    targets.authorize(manifest, "restore", seen)
    if unsafe == "unfenced":
        seen["writers_fenced"] = False
    else:
        field, value = {
            "nonempty": ("empty", False),
            "source": ("name", manifest["target"]["database"]),
            "unapproved": ("approved", False),
            "notfresh": ("fresh", False),
        }[unsafe]
        seen["restore_destination"][field] = value
    with pytest.raises(GuardError, match="restore_not_safe"):
        targets.authorize(manifest, "restore", seen)


def test_private_paths_and_exclusive_lock(manifest, tmp_path):
    private = Path(manifest["private_dir"])
    with targets.run_lock(private, manifest["target"]["project"]):
        with pytest.raises(GuardError, match="target_locked"):
            with targets.run_lock(private, manifest["target"]["project"]):
                pytest.fail("second_mutator_admitted")
    link = tmp_path / "linked"
    link.symlink_to(private, target_is_directory=True)
    with pytest.raises(GuardError, match="unsafe_private_path"):
        targets.private_path(link, directory=True)
    private.chmod(0o755)
    with pytest.raises(GuardError, match="unsafe_private_mode"):
        targets.private_path(private, directory=True)


def test_redaction_removes_all_untrusted_text(manifest, tmp_path):
    prepare_journal(manifest, raw_report(manifest, state="failure"))
    result = evidence.collect(manifest, tmp_path / "test-results")
    destination = tmp_path / "test-results" / manifest["run_id"]
    assert not result["passed"]
    assert result["counts"]["failed"] == 1
    assert set(p.name for p in destination.iterdir()) == {"evidence.json", "junit.xml"}
    for path in destination.iterdir():
        assert "synthetic-secret-marker" not in path.read_text()
        assert "Authorization" not in path.read_text()
        assert manifest["private_dir"] not in path.read_text()
        assert all(
            c["checkout"] not in path.read_text()
            for c in manifest["components"].values()
        )
    with pytest.raises(GuardError, match="evidence_already_exists"):
        evidence.collect(manifest, tmp_path / "test-results")


@pytest.mark.parametrize(
    "state,exit_code", [(None, 0), ("skipped", 0), ("error", 0), (None, 3)]
)
def test_evidence_preserves_outcomes_and_exits(manifest, tmp_path, state, exit_code):
    prepare_journal(manifest, raw_report(manifest, state=state), exit_code)
    result = evidence.collect(manifest, tmp_path / "test-results")
    assert result["passed"] is (state is None and exit_code == 0)


@pytest.mark.parametrize(
    "kind,code",
    [
        ("zero", "zero_cases"),
        ("mixed", "mixed_candidate"),
        ("missing", "missing_cases"),
        ("duplicate", "duplicate_case"),
        ("unsafe_association", "unsafe_association"),
        ("entity", "invalid_xml"),
    ],
)
def test_malformed_and_incomplete_reports_never_pass(manifest, kind, code):
    raw = raw_report(manifest)
    required = [evidence.case_id("safe-node")]
    root = ET.fromstring(raw)
    if kind == "zero":
        root.remove(root.find("testcase"))
    elif kind == "mixed":
        root.find(".//property[@name='candidate_sha256']").set("value", "9" * 64)
    elif kind == "missing":
        required.append(evidence.case_id("missing-node"))
    elif kind == "duplicate":
        root.append(copy.deepcopy(root.find("testcase")))
    elif kind == "unsafe_association":
        root.find(".//property[@name='associations']").set(
            "value", "synthetic@example.invalid"
        )
    raw = (
        ET.tostring(root)
        if kind != "entity"
        else b'<!DOCTYPE x [<!ENTITY a "secret">]><testsuite>&a;</testsuite>'
    )
    with pytest.raises(GuardError, match=code):
        evidence.sanitize_junit(raw, fingerprint(manifest), required)


def test_missing_journal_and_path_traversal_fail(manifest, tmp_path):
    with pytest.raises(FileNotFoundError):
        evidence.collect(manifest, tmp_path / "test-results")
    journal = prepare_journal(manifest)
    journal["reports"][0]["file"] = "../outside.xml"
    write_private(Path(manifest["private_dir"]) / "journal.json", journal)
    with pytest.raises(GuardError, match="unsafe_report_path"):
        evidence.collect(manifest, tmp_path / "test-results")
    assert not (tmp_path / "test-results").exists()


def test_frozen_sources_and_dirty_candidates(manifest, tmp_path, monkeypatch):
    # Exercise source checks in isolation; no git/app/Docker dependency in the QA container.
    dirty = False

    def git_fixture(root, *args):
        if args == ("status", "--porcelain", "--untracked-files=all"):
            return "?? changed" if dirty else ""
        if args[0] == "hash-object":
            return CONTRACTS.get(args[1], "a" * 40)
        if args[0] == "rev-parse" and ":" in args[1]:
            return CONTRACTS.get(args[1].split(":", 1)[1], "a" * 40)
        return BASELINE

    monkeypatch.setattr(targets, "git", git_fixture)
    for role, c in manifest["components"].items():
        root = tmp_path / role
        root.mkdir()
        c["checkout"] = str(root)
        for path in c["locks"]:
            file = root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"synthetic lock")
            c["locks"][path] = hashlib.sha256(file.read_bytes()).hexdigest()
    seal(manifest)
    targets.verify_sources(manifest)
    dirty = True
    with pytest.raises(GuardError, match="dirty_source"):
        targets.verify_sources(manifest)


def test_cli_safe_errors_and_no_implicit_target(monkeypatch, capsys):
    monkeypatch.delenv("SLOTBOOK_TEST_MANIFEST", raising=False)
    assert runner.main(["check"]) == 2
    assert capsys.readouterr().err.strip() == "qa_guard:manifest_required"
    monkeypatch.setenv("SLOTBOOK_TEST_MANIFEST", "/synthetic-secret-marker")
    assert runner.main(["collect"]) == 2
    assert "synthetic-secret-marker" not in capsys.readouterr().err


@pytest.mark.parametrize(
    "selection",
    [["--suite", "contract"], ["--milestone", "T024"], ["--milestone", "T034"]],
)
def test_runtime_is_unwired_without_running_any_lifecycle(
    manifest, monkeypatch, capsys, selection
):
    if "--milestone" in selection:
        manifest["milestone"] = selection[1]
        seal(manifest)
    path = write_private(Path(manifest["private_dir"]) / "manifest.json", manifest)
    monkeypatch.setenv("SLOTBOOK_TEST_MANIFEST", str(path))
    monkeypatch.setattr(runner, "verify_sources", lambda _: None)
    assert runner.main(["run", *selection]) == 2
    assert "lifecycle_adapters_deferred_to_T022" in capsys.readouterr().err


@pytest.mark.schema
@pytest.mark.parametrize(
    "name,value",
    [
        ("HealthStatus", {"status": "ok"}),
        ("ReadyStatus", {"status": "ready"}),
        (
            "Slot",
            {"startsAt": "2026-11-01T09:00:00Z", "endsAt": "2026-11-01T09:30:00Z"},
        ),
        ("BookingSummary", SUMMARY),
        ("RemovedContacts", {"state": "removed"}),
        ("AdminBooking", {**SUMMARY, "contact": {"state": "removed"}}),
        ("WeeklyWindow", {"isoWeekday": 1, "localStart": "09:10", "localEnd": "10:00"}),
    ],
)
def test_frozen_positive_schema_fixtures(validate_schema, name, value):
    validate_schema(name, value)


@pytest.mark.schema
@pytest.mark.parametrize(
    "name,value",
    [
        ("HealthStatus", {"status": "ready"}),
        ("ReadyStatus", {"status": "ready", "database": "private"}),
        ("BookingSummary", {**SUMMARY, "attendeeEmail": "qa@example.invalid"}),
        ("RemovedContacts", {"state": "removed", "attendeeName": "Synthetic"}),
        (
            "AdminBooking",
            {
                **SUMMARY,
                "contact": {"state": "removed", "attendeeEmail": "qa@example.invalid"},
            },
        ),
        ("WeeklyWindow", {"isoWeekday": 8, "localStart": "09:10", "localEnd": "10:00"}),
        ("LocalClock", "09:10Z"),
        ("ActivityDuration", 16),
        ("Slot", {"startsAt": "2026-11-01T09:00:00", "endsAt": "2026-11-01T09:30:00Z"}),
    ],
)
def test_frozen_negative_schema_fixtures(validate_schema, name, value):
    with pytest.raises(ValidationError):
        validate_schema(name, value)


def test_httpx_black_box_fixture(http_client, validate_schema):
    response = http_client.get("/health")
    assert response.status_code == 200
    validate_schema("HealthStatus", response.json())


def test_no_application_imports_or_browser_recordings():
    assert "app.main" not in sys.modules and "backend.app" not in sys.modules
    config = (QA_ROOT / "e2e/playwright.config.ts").read_text()
    for setting in (
        "trace: 'off'",
        "screenshot: 'off'",
        "video: 'off'",
        "acceptDownloads: false",
    ):
        assert setting in config


def test_junit_refuses_public_output(tmp_path):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"SLOTBOOK_QA_PRIVATE_DIR", "SLOTBOOK_CANDIDATE_SHA256"}
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "pytest.ini",
            "contract",
            "--collect-only",
            "--junitxml=" + str(tmp_path / "public.xml"),
        ],
        cwd=QA_ROOT,
        env=env,
        capture_output=True,
    )
    assert result.returncode == 4
    assert not (tmp_path / "public.xml").exists()
    assert b"private_report_and_candidate_required" in result.stderr


def test_target_lock_is_shared_across_control_directories(manifest, tmp_path):
    second = tmp_path / "other-control"
    second.mkdir(mode=0o700)
    with targets.run_lock(manifest["private_dir"], manifest["target"]["project"]):
        with pytest.raises(GuardError, match="target_locked"):
            with targets.run_lock(second, manifest["target"]["project"]):
                pytest.fail("parallel_target_mutation")


def test_journal_cannot_reduce_mandatory_inventory(manifest, tmp_path):
    journal = prepare_journal(manifest)
    journal["reports"][0]["required_ids"] = []
    write_private(Path(manifest["private_dir"]) / "journal.json", journal)
    with pytest.raises(GuardError, match="inventory_mismatch"):
        evidence.collect(manifest, tmp_path / "test-results")


def test_changed_sources_prevent_publication(manifest, tmp_path):
    prepare_journal(manifest)

    def changed():
        raise GuardError("source_revision_changed")

    with pytest.raises(GuardError, match="source_revision_changed"):
        evidence.collect(manifest, tmp_path / "test-results", recheck=changed)
    assert not (tmp_path / "test-results" / manifest["run_id"]).exists()


def test_cli_check_and_collect_success(manifest, tmp_path, monkeypatch, capsys):
    qa = tmp_path / "qa-checkout"
    qa.mkdir()
    manifest["components"]["qa"]["checkout"] = str(qa)
    seal(manifest)
    prepare_journal(manifest)
    location = write_private(Path(manifest["private_dir"]) / "manifest.json", manifest)
    monkeypatch.setenv("SLOTBOOK_TEST_MANIFEST", str(location))
    checks = []
    monkeypatch.setattr(runner, "verify_sources", lambda _: checks.append(True))
    assert runner.main(["check"]) == 0
    assert runner.main(["collect"]) == 0
    assert len(checks) == 3  # pre-check, pre-collection and before publication
    assert "evidence_passed" in capsys.readouterr().out
    assert (qa / "test-results" / manifest["run_id"] / "evidence.json").exists()


@pytest.mark.parametrize("unsafe", [None, "version", "mixed", "skipped"])
def test_tooling_evidence_does_not_claim_runtime_candidates(manifest, tmp_path, unsafe):
    provenance = {
        "evidence_class": "tooling-only",
        "task": "T004",
        "run_id": "t004-synthetic01",
        "baseline": BASELINE,
        "contract_revision": FROZEN,
        "input_blobs": {k: "a" * 40 for k in ("spec", "tasks", "protocol")},
        "source_sha256": "b" * 64,
        "versions": {
            "python": "3.12.0",
            "node": "22.21.1",
            "npm": "10.9.4",
            "playwright": "1.64.1",
            "chromium": "156.0.8078.4",
            "browser_revision": "1248",
        },
        "inventories": {
            s: {"required_ids": [evidence.case_id("safe-node")], "exit_code": 0}
            for s in ("python", "browser")
        },
    }
    candidate = hashlib.sha256(targets.canonical(provenance)).hexdigest()
    raw = raw_report(manifest, state="skipped" if unsafe == "skipped" else None)
    raw = raw.replace(fingerprint(manifest).encode(), candidate.encode())
    if unsafe == "mixed":
        raw = raw.replace(candidate.encode(), b"9" * 64)
    for name in ("harness.xml", "e2e.xml"):
        path = Path(manifest["private_dir"]) / name
        path.write_bytes(raw)
        path.chmod(0o600)
    if unsafe == "version":
        provenance["versions"]["python"] = "synthetic@example.invalid"
    if unsafe in {"version", "mixed"}:
        with pytest.raises(GuardError):
            evidence.collect_selftest(
                provenance, manifest["private_dir"], tmp_path / "test-results"
            )
        return
    result = evidence.collect_selftest(
        provenance, manifest["private_dir"], tmp_path / "test-results"
    )
    assert result["passed"] is (unsafe != "skipped")
    assert result["provenance"]["evidence_class"] == "tooling-only"
    assert "components" not in result["provenance"]
    assert "synthetic-secret-marker" not in json.dumps(result)


@pytest.mark.parametrize("outcome", ["error", "failure", "skipped"])
def test_nested_suite_outcomes_cannot_disappear(manifest, outcome):
    root = ET.Element("testsuites")
    outer = ET.SubElement(root, "testsuite")
    inner = ET.SubElement(outer, "testsuite")
    inner.append(ET.fromstring(raw_report(manifest)).find("testcase"))
    ET.SubElement(inner, outcome).text = "synthetic raw diagnostics"
    with pytest.raises(GuardError, match="suite_error"):
        evidence.sanitize_junit(
            ET.tostring(root), fingerprint(manifest), [evidence.case_id("safe-node")]
        )


def test_candidate_cannot_omit_qa_browser_lock(manifest):
    del manifest["components"]["qa"]["locks"]["tests/e2e/package-lock.json"]
    seal(manifest)
    with pytest.raises(GuardError, match="lock_inventory_mismatch"):
        targets.validate_manifest(manifest)


def test_target_lock_cannot_be_bypassed_with_another_tmpdir(manifest, tmp_path):
    alternate = tmp_path / "alternate-tmp"
    alternate.mkdir(mode=0o700)
    program = (
        "import os\nfrom harness.targets import run_lock, GuardError\n"
        "try:\n"
        " with run_lock(os.environ['CONTROL'], os.environ['PROJECT']):\n"
        "  raise SystemExit(1)\n"
        "except GuardError as error:\n"
        " raise SystemExit(0 if str(error) == 'target_locked' else 2)\n"
    )
    env = dict(
        os.environ,
        TMPDIR=str(alternate),
        CONTROL=manifest["private_dir"],
        PROJECT=manifest["target"]["project"],
        PYTHONPATH=str(QA_ROOT),
    )
    with targets.run_lock(manifest["private_dir"], manifest["target"]["project"]):
        result = subprocess.run(
            [sys.executable, "-c", program], cwd=QA_ROOT, env=env, capture_output=True
        )
    assert result.returncode == 0
