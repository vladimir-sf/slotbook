"""Allowlist-only publication; raw XML, streams, values and paths never leave private storage."""

import hashlib
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from defusedxml.ElementTree import fromstring

from harness.targets import (
    GuardError,
    canonical,
    exact,
    fingerprint,
    matches,
    private_path,
    read_private_json,
    require,
    sha,
    validate_manifest,
)

COMMANDS = {"qa-pytest", "qa-playwright", "backend-static", "backend-pytest"}
SUITES = {
    "harness",
    "backend",
    "infrastructure",
    "contract",
    "concurrency",
    "privacy",
    "e2e",
}


def collect_selftest(provenance, private_dir, evidence_root):
    """Publish offline T004 proof without inventing component images or a runtime candidate.

    Provenance/mandatory inventories are frozen BEFORE executing the tooling checks. Their
    canonical SHA256 is the report's candidate_sha256. No application verification is claimed.
    """
    exact(
        provenance,
        {
            "evidence_class",
            "task",
            "run_id",
            "baseline",
            "contract_revision",
            "input_blobs",
            "source_sha256",
            "versions",
            "inventories",
        },
    )
    require(
        provenance["evidence_class"] == "tooling-only" and provenance["task"] == "T004"
    )
    from harness.targets import BASELINE, FROZEN

    require(
        provenance["baseline"] == BASELINE and provenance["contract_revision"] == FROZEN
    )
    require(matches(provenance["run_id"], r"t004-[a-z0-9]{8,24}"))
    exact(provenance["input_blobs"], {"spec", "tasks", "protocol"})
    require(
        all(matches(v, r"[0-9a-f]{40}") for v in provenance["input_blobs"].values())
    )
    require(sha(provenance["source_sha256"]))
    exact(
        provenance["versions"],
        {"python", "node", "npm", "playwright", "chromium", "browser_revision"},
    )
    require(
        all(
            matches(v, r"[0-9]{1,4}(?:\.[0-9]{1,4}){0,3}")
            for v in provenance["versions"].values()
        )
    )
    exact(provenance["inventories"], {"python", "browser"})
    candidate = hashlib.sha256(canonical(provenance)).hexdigest()
    private = private_path(private_dir, directory=True)
    destination_root = Path(evidence_root).absolute()
    require(
        not destination_root.resolve().is_relative_to(private)
        and not private.is_relative_to(destination_root.resolve()),
        "private_evidence_overlap",
    )
    require(
        not any(p.is_symlink() for p in (destination_root, *destination_root.parents)),
        "unsafe_evidence_path",
    )
    results, commands = [], []
    for name, report_file in (("python", "harness.xml"), ("browser", "e2e.xml")):
        inventory = provenance["inventories"][name]
        exact(inventory, {"required_ids", "exit_code"})
        require(
            type(inventory["exit_code"]) is int and 0 <= inventory["exit_code"] <= 255,
            "invalid_exit",
        )
        report = private_path(private / report_file)
        require(report.stat().st_size <= 10_000_000, "oversized_report")
        rows = sanitize_junit(report.read_bytes(), candidate, inventory["required_ids"])
        results.extend({**r, "suite": name} for r in rows)
        commands.append(
            {
                "command": "qa-pytest" if name == "python" else "qa-playwright",
                "exit_code": inventory["exit_code"],
                "count": len(rows),
            }
        )
    document = {
        "provenance": provenance,
        "candidate_sha256": candidate,
        "commands": commands,
        "cases": results,
        "passed": all(r["outcome"] == "passed" for r in results)
        and all(c["exit_code"] == 0 for c in commands),
    }
    destination_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = destination_root / provenance["run_id"]
    require(
        not destination.exists() and not destination.is_symlink(),
        "evidence_already_exists",
    )
    destination.mkdir(mode=0o700)
    output = destination / "tooling-evidence.json"
    output.write_bytes(canonical(document))
    output.chmod(0o600)
    return document


def case_id(nodeid):
    return "QA-" + hashlib.sha256(nodeid.encode()).hexdigest()


def safe_manifest(m):
    validate_manifest(m)
    return {
        "version": 1,
        "run_id": m["run_id"],
        "milestone": m["milestone"],
        "task_ids": m["task_ids"],
        "candidate_sha256": fingerprint(m),
        "baseline": m["baseline"],
        "revisions": m["revisions"],
        "contract_revision": m["contract"]["revision"],
        "contract_blobs": sorted(m["contract"]["blobs"].values()),
        "compose_sha256": m["compose_sha256"],
        "components": {
            role: {
                "commit": c["commit"],
                "lock_sha256": sorted(c["locks"].values()),
                "image_id": c["image_id"],
                "image_digest": c["image_digest"],
                "platform": c["platform"],
            }
            for role, c in m["components"].items()
        },
        "ports": {k: m["target"][k] for k in ("api_port", "ui_port")},
    }


def sanitize_junit(raw, candidate, required_ids):
    """Only fixed IDs/outcomes survive. Required IDs are the reviewed producer inventory.

    IDs hash collection nodeids, never display names/parameters; associations have numeric grammar.
    Raw suite counts are untrusted: counts are recomputed from actual cases.
    """
    require(
        sha(candidate) and required_ids and len(set(required_ids)) == len(required_ids),
        "invalid_inventory",
    )
    require(
        all(matches(i, r"QA-[0-9a-f]{64}") for i in required_ids), "invalid_inventory"
    )
    require(len(raw) <= 10_000_000, "oversized_report")
    try:
        root = fromstring(raw)
    except Exception:
        raise GuardError("invalid_xml") from None
    require(root.tag in {"testsuite", "testsuites"}, "invalid_xml")
    require(list(root.iter("testsuite")), "missing_results")
    # Suite-level teardown/setup failures must never disappear during redaction.
    parents = {child: parent for parent in root.iter() for child in parent}
    require(
        all(
            parents[node].tag == "testcase"
            for node in root.iter()
            if node.tag in {"error", "failure", "skipped"}
        ),
        "suite_error",
    )
    results = []
    for case in root.iter("testcase"):
        props = case.findall("./properties/property")
        values = {}
        for prop in props:
            key = prop.get("name")
            if key in {"evidence_id", "candidate_sha256", "associations"}:
                require(key not in values, "duplicate_property")
                values[key] = prop.get("value", "")
        require(values.get("candidate_sha256") == candidate, "mixed_candidate")
        identity = values.get("evidence_id")
        require(identity in required_ids, "unknown_case")
        associations = (
            values.get("associations", "").split(",")
            if values.get("associations")
            else []
        )
        require(
            all(
                matches(
                    a,
                    r"(?:FR-[0-9]{3}|SC-[0-9]{3}|RP-[0-9]{2}|US[1-5]\.[0-9]{1,2}|T[0-9]{3})",
                )
                for a in associations
            ),
            "unsafe_association",
        )
        states = [
            tag for tag in ("failure", "error", "skipped") if case.find(tag) is not None
        ]
        require(len(states) <= 1, "invalid_outcome")
        outcome = (
            {"failure": "failed", "error": "error", "skipped": "skipped"}.get(
                states[0], "passed"
            )
            if states
            else "passed"
        )
        results.append(
            {"id": identity, "outcome": outcome, "associations": associations}
        )
    require(results, "zero_cases")
    require(len({r["id"] for r in results}) == len(results), "duplicate_case")
    require({r["id"] for r in results} == set(required_ids), "missing_cases")
    return results


def collect(m, evidence_root, *, recheck=lambda: None):
    """Read one private journal; atomically publish a new, immutable, sanitized run directory.

    journal.json: {candidate_sha256, reports: [{suite, command, exit_code, file, required_ids}]}.
    Raw reports are explicitly named .xml basenames, never recursively copied.
    """
    validate_manifest(m)
    private = private_path(m["private_dir"], directory=True)
    evidence_root = Path(evidence_root)
    require(not evidence_root.is_symlink(), "unsafe_evidence_path")
    require(
        not any(p.is_symlink() for p in evidence_root.parents), "unsafe_evidence_path"
    )
    require(
        not private.is_relative_to(evidence_root.resolve())
        and not evidence_root.resolve().is_relative_to(private),
        "private_evidence_overlap",
    )
    journal = read_private_json(private / "journal.json")
    exact(journal, {"candidate_sha256", "reports"})
    candidate = fingerprint(m)
    require(journal["candidate_sha256"] == candidate, "mixed_candidate")
    require(
        isinstance(journal["reports"], list) and journal["reports"], "missing_reports"
    )
    cases, commands, suites = [], [], set()
    for report in journal["reports"]:
        exact(report, {"suite", "command", "exit_code", "file", "required_ids"})
        require(
            report["suite"] in SUITES and report["command"] in COMMANDS,
            "unknown_producer",
        )
        require(report["suite"] not in suites, "duplicate_suite")
        suites.add(report["suite"])
        require(
            m["evidence_plan"].get(report["suite"])
            == {"command": report["command"], "required_ids": report["required_ids"]},
            "inventory_mismatch",
        )
        require(
            type(report["exit_code"]) is int and 0 <= report["exit_code"] <= 255,
            "invalid_exit",
        )
        require(matches(report["file"], r"[a-z][a-z0-9_-]*\.xml"), "unsafe_report_path")
        path = private_path(private / report["file"])
        require(path.stat().st_size <= 10_000_000, "oversized_report")
        rows = sanitize_junit(path.read_bytes(), candidate, report["required_ids"])
        cases.extend({**row, "suite": report["suite"]} for row in rows)
        commands.append(
            {
                "command": report["command"],
                "exit_code": report["exit_code"],
                "count": len(rows),
            }
        )
    # T004 has only harness proof. Later milestone inventories are delivered with their tasks.
    require(suites == set(m["evidence_plan"]), "missing_suites")
    require(
        m["milestone"] == "T004" and suites == {"harness"},
        "milestone_inventory_not_wired",
    )
    passed = all(c["outcome"] == "passed" for c in cases) and all(
        c["exit_code"] == 0 for c in commands
    )
    document = {
        "manifest": safe_manifest(m),
        "commands": commands,
        "cases": cases,
        "passed": passed,
        "counts": {
            s: sum(c["outcome"] == s for c in cases)
            for s in ("passed", "failed", "error", "skipped")
        },
    }
    xml = ET.Element(
        "testsuite",
        {
            "name": "sanitized",
            "tests": str(len(cases)),
            "failures": str(document["counts"]["failed"]),
            "errors": str(document["counts"]["error"]),
            "skipped": str(document["counts"]["skipped"]),
        },
    )
    for case in cases:
        node = ET.SubElement(
            xml, "testcase", {"name": case["id"], "classname": case["suite"]}
        )
        if case["outcome"] != "passed":
            tag = {"failed": "failure", "error": "error", "skipped": "skipped"}[
                case["outcome"]
            ]
            ET.SubElement(node, tag, {"message": "assertion_" + case["outcome"]})
    # Build both outputs before creating the publication directory. Never overwrite a run.
    payloads = {
        "evidence.json": canonical(document),
        "junit.xml": ET.tostring(xml, encoding="utf-8"),
    }
    evidence_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = evidence_root / m["run_id"]
    require(
        not destination.exists() and not destination.is_symlink(),
        "evidence_already_exists",
    )
    # Private staging avoids partially written results becoming uploadable evidence.
    with tempfile.TemporaryDirectory(prefix=".collect-", dir=evidence_root) as staging:
        for filename, content in payloads.items():
            path = Path(staging) / filename
            path.write_bytes(content)
            path.chmod(0o600)
        recheck()
        os.rename(staging, destination)
    return document
