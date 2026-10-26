"""T006 negative-path and workflow-policy checks; no application or service imports."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

spec = importlib.util.spec_from_file_location(
    "ci_checks", Path(__file__).with_name("checks.py")
)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
IDENTITY = "QA-" + "a" * 64
CANDIDATE = "b" * 64


class EvidenceTests(unittest.TestCase):
    def test_real_positive_inventory(self):
        self.assertEqual(
            checks.check_inventory(
                [IDENTITY], [{"id": IDENTITY, "outcome": "passed"}], 1
            ),
            [{"id": IDENTITY, "outcome": "passed"}],
        )

    def test_zero_inventory(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory([], [], 1)

    def test_missing_mandatory_inventory(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory(
                [IDENTITY], [{"id": IDENTITY, "outcome": "passed"}], 2
            )

    def test_missing_execution(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory([IDENTITY], [], 1)

    def test_duplicate_inventory(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory(
                [IDENTITY, IDENTITY], [{"id": IDENTITY, "outcome": "passed"}], 1
            )

    def test_duplicate_execution(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory(
                [IDENTITY], [{"id": IDENTITY, "outcome": "passed"}] * 2, 1
            )

    def test_unknown_case(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory(
                [IDENTITY], [{"id": "QA-" + "c" * 64, "outcome": "passed"}], 1
            )

    def test_skipped_mandatory_case(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory(
                [IDENTITY], [{"id": IDENTITY, "outcome": "skipped"}], 1
            )

    def test_failed_assertion(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory(
                [IDENTITY], [{"id": IDENTITY, "outcome": "failed"}], 1
            )

    def test_sensitive_id(self):
        with self.assertRaises(checks.CiError):
            checks.check_inventory(["synthetic@example.invalid"], [], 1)

    def report(self, *, candidate=CANDIDATE, outcome=""):
        return (
            f'<testsuite hostname="synthetic-secret"><testcase name="synthetic-secret">'
            f'<properties><property name="evidence_id" value="{IDENTITY}"/>'
            f'<property name="candidate_sha256" value="{candidate}"/>'
            f"</properties>{outcome}<system-out>synthetic-secret</system-out></testcase></testsuite>"
        ).encode()

    def test_junit_redaction(self):
        rows = checks.junit_rows(self.report(), CANDIDATE)
        self.assertNotIn("synthetic-secret", json.dumps(rows))
        self.assertEqual(rows, [{"id": IDENTITY, "outcome": "passed"}])

    def test_failed_junit_retains_failure_without_value(self):
        rows = checks.junit_rows(
            self.report(outcome='<failure message="synthetic-secret"/>'), CANDIDATE
        )
        self.assertEqual(rows[0]["outcome"], "failure")
        self.assertNotIn("synthetic-secret", json.dumps(rows))

    def test_mixed_candidate(self):
        with self.assertRaises(checks.CiError):
            checks.junit_rows(self.report(candidate="c" * 64), CANDIDATE)

    def test_xml_entity_refused(self):
        with self.assertRaises(checks.CiError):
            checks.junit_rows(
                b'<!DOCTYPE x [<!ENTITY a "secret">]><testsuite>&a;</testsuite>',
                CANDIDATE,
            )

    def test_malformed_xml_refused(self):
        with self.assertRaises(checks.CiError):
            checks.junit_rows(b"not XML", CANDIDATE)

    def test_nested_suite_error(self):
        raw = b"<testsuites><testsuite><testsuite><error>synthetic-secret</error></testsuite></testsuite></testsuites>"
        with self.assertRaises(checks.CiError):
            checks.junit_rows(raw, CANDIDATE)

    def test_raw_child_output_stays_private(self):
        with tempfile.TemporaryDirectory() as temp:
            job = checks.Job.__new__(checks.Job)
            job.root = Path(temp)
            job.private = Path(temp)
            job.env = dict(os.environ)
            job.report = {"checks": []}
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                raw = job.command(
                    "probe", [sys.executable, "-c", "print('synthetic-secret')"]
                )
            self.assertIn(b"synthetic-secret", raw)
            self.assertNotIn("synthetic-secret", out.getvalue())
            self.assertEqual(job.report["checks"], [{"id": "probe", "exit_code": 0}])

    def test_nonzero_child_never_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            job = checks.Job.__new__(checks.Job)
            job.root = job.private = Path(temp)
            job.env = dict(os.environ)
            job.report = {"checks": []}
            with (
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises(checks.CiError),
            ):
                job.command("negative", [sys.executable, "-c", "raise SystemExit(7)"])
            self.assertEqual(job.report["checks"][0]["exit_code"], 7)

    def test_cli_errors_do_not_echo_private_input(self):
        with (
            patch.object(sys, "argv", ["checks.py", "qa"]),
            patch.object(checks, "Job", side_effect=ValueError("synthetic-secret")),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            self.assertEqual(checks.main(), 1)
        self.assertNotIn("synthetic-secret", out.getvalue())


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load(
            (checks.ROOT / ".github/workflows/ci.yml").read_text(),
            Loader=yaml.BaseLoader,
        )

    def test_read_only_and_unprivileged_triggers(self):
        self.assertEqual(
            set(self.workflow["on"]), {"push", "pull_request", "workflow_dispatch"}
        )
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})

    def test_independent_four_lane_matrix(self):
        job = self.workflow["jobs"]["tooling"]
        self.assertEqual(
            job["strategy"]["matrix"]["lane"], ["contract", "backend", "frontend", "qa"]
        )
        self.assertEqual(job["runs-on"], "ubuntu-24.04")
        self.assertEqual(job["strategy"]["fail-fast"], "false")

    def test_pinned_actions_and_no_credentials_or_uploads(self):
        for step in self.workflow["jobs"]["tooling"]["steps"]:
            if "uses" in step:
                self.assertRegex(
                    step["uses"],
                    r"^actions/(checkout|setup-python|setup-node)@[0-9a-f]{40}$",
                )
            self.assertNotIn("continue-on-error", step)
        checkout = self.workflow["jobs"]["tooling"]["steps"][0]
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        self.assertEqual(checkout["with"]["fetch-depth"], "0")
        text = json.dumps(self.workflow)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("upload-artifact", text)
        self.assertNotIn("deploy", text)

    def test_exact_toolchains_and_no_caches(self):
        steps = self.workflow["jobs"]["tooling"]["steps"]
        self.assertEqual(steps[1]["with"]["python-version"], "3.12.12")
        self.assertEqual(steps[2]["with"]["node-version"], "22.22.0")
        self.assertEqual(steps[2]["with"]["package-manager-cache"], "false")


if __name__ == "__main__":
    unittest.main()
