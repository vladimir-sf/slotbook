"""T006 tooling jobs. Raw subprocess output stays private; only allowlisted evidence is printed.

Run the same entry point locally and on GitHub. This does not provision app/DB targets,
invoke the future lifecycle harness, or claim product/runtime acceptance.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CI_DIR = Path(__file__).resolve().parent
FROZEN = "adc0b83a4408493ac44d3a7571dfd3d25a758679"
BLOBS = {
    "contracts/main.tsp": "b5076047fef868a17590d00e5c93753d8e67f044",
    "contracts/tsp-output/@typespec/openapi3/openapi.yaml": "3ad47840cc0dd120d070599e9fad218230f4a845",
    "frontend/src/api/schema.d.ts": "4b6a9b438f9ed60e8e271acd2b901a9376c738be",
}
MINIMUM_CASES = {"backend": 7, "frontend": 54, "qa": 80, "qa-browser": 4}
LOCKS = {
    "contract": ["contracts/package-lock.json", "frontend/package-lock.json"],
    "backend": ["backend/requirements.lock"],
    "frontend": ["frontend/package-lock.json"],
    "qa": ["tests/requirements.lock", "tests/e2e/package-lock.json"],
}


class CiError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise CiError(code)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def check_inventory(expected, rows, minimum):
    require(isinstance(expected, list) and len(expected) >= minimum, "missing_cases")
    require(
        all(
            isinstance(i, str) and re.fullmatch(r"QA-[0-9a-f]{64}", i) for i in expected
        ),
        "invalid_ids",
    )
    require(len(expected) == len(set(expected)), "duplicate_inventory")
    require(isinstance(rows, list) and rows, "zero_results")
    require(
        all(set(row) == {"id", "outcome"} and row["id"] in expected for row in rows),
        "unknown_case",
    )
    require(len({r["id"] for r in rows}) == len(rows), "duplicate_result")
    require({r["id"] for r in rows} == set(expected), "missing_results")
    require(all(r["outcome"] == "passed" for r in rows), "failed_or_skipped_cases")
    return rows


def junit_rows(raw, candidate):
    require(
        len(raw) <= 10_000_000 and not re.search(rb"<!DOCTYPE|<!ENTITY", raw, re.I),
        "unsafe_xml",
    )
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise CiError("invalid_xml") from None
    # All original text/attributes except validated provenance and outcomes are discarded.
    require(root.tag in {"testsuites", "testsuite"}, "invalid_xml")
    parents = {child: parent for parent in root.iter() for child in parent}
    require(
        all(
            parents[n].tag == "testcase"
            for n in root.iter()
            if n.tag in {"error", "failure", "skipped"}
        ),
        "suite_error",
    )
    rows = []
    for case in root.iter("testcase"):
        props = case.findall("./properties/property")
        identities = [p.get("value") for p in props if p.get("name") == "evidence_id"]
        candidates = [
            p.get("value") for p in props if p.get("name") == "candidate_sha256"
        ]
        require(len(identities) == 1 and candidates == [candidate], "mixed_candidate")
        outcome = "passed"
        for tag in ("failure", "error", "skipped"):
            if case.find(tag) is not None:
                outcome = tag
        rows.append({"id": identities[0], "outcome": outcome})
    return rows


def source_fingerprint(root):
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    )
    paths = {p.decode() for p in result.stdout.split(b"\0") if p}
    # Include this task's not-yet-committed CI source in local verification too.
    paths.update(
        str(p.relative_to(root))
        for p in (root / ".github").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    return digest(
        json_bytes({p: digest((root / p).read_bytes()) for p in sorted(paths)})
    )


class Job:
    def __init__(self, lane, root=ROOT):
        self.root = root
        self.lane = lane
        os.umask(0o077)
        self.private = Path(
            tempfile.mkdtemp(prefix="slotbook-ci-", dir=os.environ.get("RUNNER_TEMP"))
        ).resolve()
        require(
            not self.private.is_relative_to(root.resolve()),
            "private_directory_in_source",
        )
        self.private.chmod(0o700)
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not re.search(
                r"TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE_KEY|AUTHORIZATION", k, re.I
            )
        }
        for key in list(self.env):
            if key.startswith("PLAYWRIGHT_") or key in {
                "GITHUB_ENV",
                "GITHUB_OUTPUT",
                "GITHUB_PATH",
                "GITHUB_STEP_SUMMARY",
                "PYTEST_ADDOPTS",
                "PYTEST_PLUGINS",
                "NODE_OPTIONS",
            }:
                del self.env[key]
        self.env.update(TZ="UTC", PYTHONTZPATH="", PYTHONPATH=str(CI_DIR), CI="true")
        self.report = {
            "scope": "T006-tooling-only",
            "lane": lane,
            "checks": [],
            "suites": {},
            "versions": {},
            "deferred": [
                "PostgreSQL/runtime: T022/T087",
                "product acceptance: later story tasks",
            ],
        }
        self.report["run_id"] = uuid.uuid4().hex
        self.report["contract_revision"] = FROZEN
        self.report["input_blobs"] = {}
        for name, path in {
            "tasks": "specs/001-appointment-scheduling/tasks.md",
            "protocol": "docs/EXECUTION_PROTOCOL.md",
        }.items():
            raw = (root / path).read_bytes()
            self.report["input_blobs"][name] = hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()
        self.source = source_fingerprint(root)
        self.report["source_sha256"] = self.source
        head = (
            self.command("source-commit", ["git", "rev-parse", "HEAD"]).decode().strip()
        )
        require(re.fullmatch(r"[0-9a-f]{40}", head), "invalid_commit")
        self.report["commit"] = head
        self.report["lock_sha256"] = {
            p: digest((root / p).read_bytes()) for p in LOCKS[lane]
        }
        self.candidate = digest(
            json_bytes(
                {
                    "source": self.source,
                    "commit": head,
                    "lane": lane,
                    "locks": self.report["lock_sha256"],
                    "run": self.report["run_id"],
                }
            )
        )
        self.report["candidate_sha256"] = self.candidate
        self.env.update(
            SLOTBOOK_CANDIDATE_SHA256=self.candidate,
            SLOTBOOK_CI_LANE=lane,
            SLOTBOOK_CI_PRIVATE=str(self.private),
            SLOTBOOK_QA_PRIVATE_DIR=str(self.private),
            SLOTBOOK_FRONTEND_REPORT_DIR=str(self.private),
        )

    def command(self, label, argv, cwd=None, extra_env=None, timeout=600):
        require(re.fullmatch(r"[a-z][a-z0-9-]{0,45}", label), "invalid_command_id")
        output = self.private / (label + ".log")
        require(not output.exists(), "duplicate_command")
        env = {**self.env, **(extra_env or {})}
        with output.open("xb") as stream:
            try:
                result = subprocess.run(
                    [str(a) for a in argv],
                    cwd=cwd or self.root,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                )
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
        self.report["checks"].append({"id": label, "exit_code": code})
        print(f"ci:{label}:exit={code}", flush=True)
        require(code == 0, "command_failed")
        return output.read_bytes()

    def frozen(self, label):
        for path, expected in BLOBS.items():
            raw = (self.root / path).read_bytes()
            blob = hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()
            require(blob == expected, "frozen_contract_drift")
        self.command(label, ["git", "diff", "--exit-code", FROZEN, "--", *BLOBS])

    def runtimes(self):
        require(sys.version_info[:2] == (3, 12), "python_3_12_required")
        hosted = os.environ.get("GITHUB_ACTIONS") == "true"
        if hosted:
            require(platform.python_version() == "3.12.12", "python_pin_mismatch")
        self.report["execution"] = "github-hosted" if hosted else "local"
        self.report["versions"]["python"] = platform.python_version()
        require(
            platform.machine() in {"x86_64", "AMD64", "arm64", "aarch64"},
            "unknown_architecture",
        )
        image_os, image_version = (
            os.environ.get("ImageOS", "local"),
            os.environ.get("ImageVersion", "local"),
        )
        require(
            re.fullmatch(r"[a-zA-Z0-9_.-]{1,50}", image_os)
            and re.fullmatch(r"[a-zA-Z0-9_.-]{1,50}", image_version),
            "unsafe_runner_metadata",
        )
        self.report["runner"] = {
            "label": "ubuntu-24.04" if hosted else "local",
            "image_os": image_os,
            "image_version": image_version,
            "architecture": platform.machine(),
        }
        if self.lane != "backend":
            node = self.command("node-version", ["node", "--version"]).decode().strip()
            npm = self.command("npm-version", ["npm", "--version"]).decode().strip()
            require(node == "v22.22.0" and npm == "10.9.4", "node_npm_pin_mismatch")
            self.report["versions"].update(node=node[1:], npm=npm)

    def python_environment(self, component):
        venv = self.private / "venv"
        self.command("python-venv", [sys.executable, "-m", "venv", venv])
        python = venv / "bin/python"
        self.command(
            "python-locked-install",
            [
                python,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--require-hashes",
                "-r",
                self.root / component / "requirements.lock",
            ],
        )
        self.command("python-dependencies", [python, "-m", "pip", "check"])
        return python

    def npm_install(self, component, label):
        self.command(
            label + "-npm-ci",
            ["npm", "ci", "--ignore-scripts", "--no-fund"],
            cwd=self.root / component,
        )
        self.command(
            label + "-npm-audit",
            ["npm", "audit", "--audit-level=low"],
            cwd=self.root / component,
        )

    def pytest(self, python, qa=False):
        inventory = self.private / "pytest-inventory.json"
        self.env["SLOTBOOK_CI_INVENTORY"] = str(inventory)
        cwd = self.root if qa else self.root / "backend"
        args = [python, "-m", "pytest", "-q", "-p", "inventory"]
        if qa:
            args += ["-c", "tests/pytest.ini", "tests/contract"]
        self.command("python-collect", [*args, "--collect-only"], cwd=cwd)
        expected = json.loads(inventory.read_text())
        require(len(expected) >= MINIMUM_CASES[self.lane], "missing_cases")
        self.command(
            "python-tests",
            [*args, "--junitxml=" + str(self.private / "pytest.xml")],
            cwd=cwd,
        )
        rows = junit_rows((self.private / "pytest.xml").read_bytes(), self.candidate)
        self.report["suites"]["python"] = check_inventory(
            expected, rows, MINIMUM_CASES[self.lane]
        )

    def browser(self, component):
        cwd = self.root / component
        reporter = str(CI_DIR / "browser-reporter.cjs")
        if component == "frontend":
            # The Frontend-owned test command requires this loopback port and refuses reuse.
            with socket.socket() as probe:
                try:
                    probe.bind(("127.0.0.1", 4173))
                except OSError:
                    raise CiError("frontend_test_port_in_use") from None
        self.command(
            "browser-install",
            ["npm", "exec", "--", "playwright", "install", "--with-deps", "chromium"],
            cwd=cwd,
        )
        self.command(
            "browser-collect",
            [
                "npm",
                "exec",
                "--",
                "playwright",
                "test",
                "--list",
                "--reporter=" + reporter,
            ],
            cwd=cwd,
            extra_env={"SLOTBOOK_CI_PHASE": "collect"},
        )
        expected = json.loads((self.private / "browser-inventory.json").read_text())
        minimum = MINIMUM_CASES["qa-browser" if self.lane == "qa" else "frontend"]
        require(len(expected) >= minimum, "missing_cases")
        self.command(
            "browser-tests",
            ["npm", "test", "--", "--reporter=" + reporter],
            cwd=cwd,
            extra_env={"SLOTBOOK_CI_PHASE": "execute"},
        )
        actual = json.loads((self.private / "browser-results.json").read_text())
        require(
            actual["candidate"] == self.candidate and actual["ids"] == expected,
            "mixed_browser_inventory",
        )
        require(actual["status"] == "passed", "browser_suite_failed")
        self.report["suites"]["browser"] = check_inventory(
            expected, actual["rows"], minimum
        )
        script = """const fs=require('fs'),path=require('path');const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const registry=JSON.parse(fs.readFileSync(path.join(path.dirname(require.resolve('playwright-core/package.json')),'browsers.json'))).browsers.find(x=>x.name==='chromium');
console.log(JSON.stringify({playwright:require('playwright/package.json').version,chromium:b.version(),revision:registry.revision}));await b.close()})().catch(()=>process.exit(1));"""
        versions = json.loads(
            self.command("browser-versions", ["node", "-e", script], cwd=cwd)
        )
        require(
            set(versions) == {"playwright", "chromium", "revision"}
            and all(re.fullmatch(r"[0-9.]{1,30}", v) for v in versions.values()),
            "unsafe_browser_metadata",
        )
        self.report["versions"].update(versions)

    def execute(self):
        self.runtimes()
        self.frozen("frozen-before")
        if self.lane == "contract":
            self.npm_install("contracts", "contracts")
            self.npm_install("frontend", "frontend-tools")
            self.command(
                "contract-generation",
                ["bash", "scripts/check-contract.sh", "--self-test"],
            )
        elif self.lane == "backend":
            python = self.python_environment("backend")
            cwd = self.root / "backend"
            self.command(
                "backend-ruff", [python, "-m", "ruff", "check", "app", "tests"], cwd=cwd
            )
            self.command(
                "backend-format",
                [python, "-m", "ruff", "format", "--check", "app", "tests"],
                cwd=cwd,
            )
            self.command("backend-mypy", [python, "-m", "mypy", "app"], cwd=cwd)
            self.pytest(python)
            versions = json.loads(
                self.command(
                    "timezone-version",
                    [
                        python,
                        "-c",
                        "import json,tzdata,zoneinfo;assert zoneinfo.TZPATH==();zoneinfo.ZoneInfo('Europe/Vienna');"
                        "print(json.dumps({'tzdata':tzdata.__version__,'iana':tzdata.IANA_VERSION}))",
                    ],
                )
            )
            require(
                set(versions) == {"tzdata", "iana"}
                and all(re.fullmatch(r"[0-9a-z.]{1,20}", v) for v in versions.values()),
                "unsafe_timezone_metadata",
            )
            self.report["versions"].update(versions)
        elif self.lane == "frontend":
            self.npm_install("frontend", "frontend")
            self.command(
                "frontend-typecheck",
                ["npm", "--prefix", "frontend", "run", "typecheck"],
            )
            self.command(
                "frontend-build", ["npm", "--prefix", "frontend", "run", "build"]
            )
            self.browser("frontend")
        else:
            python = self.python_environment("tests")
            output = self.command(
                "ci-regressions",
                [
                    python,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    ".github/ci",
                    "-p",
                    "test_*.py",
                ],
            )
            count = re.search(rb"Ran ([0-9]+) tests?", output)
            require(
                count and int(count[1]) >= 23 and b"skipped=" not in output,
                "missing_ci_regressions",
            )
            self.report["ci_regressions"] = int(count[1])
            self.command(
                "qa-ruff",
                [
                    python,
                    "-m",
                    "ruff",
                    "check",
                    "tests/harness",
                    "tests/conftest.py",
                    "tests/contract",
                    ".github/ci",
                ],
            )
            self.command(
                "qa-format",
                [
                    python,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "tests/harness",
                    "tests/conftest.py",
                    "tests/contract",
                    ".github/ci",
                ],
            )
            self.pytest(python, qa=True)
            self.npm_install("tests/e2e", "qa-browser")
            self.command(
                "qa-typecheck", ["npm", "--prefix", "tests/e2e", "run", "typecheck"]
            )
            self.browser("tests/e2e")
        self.frozen("frozen-after")
        require(
            source_fingerprint(self.root) == self.source, "candidate_source_changed"
        )

    def publish(self, passed):
        # Values are assembled here from fixed labels, validated versions, hashes and counts only.
        self.report["passed"] = passed
        base = self.root / "test-results"
        require(not base.is_symlink(), "unsafe_output")
        base.mkdir(mode=0o700, exist_ok=True)
        destination = base / ("ci-" + self.lane + "-" + self.candidate[:16])
        destination.mkdir(mode=0o700)
        output = destination / "verification.json"
        require(not output.is_symlink(), "unsafe_output")
        output.write_bytes(json_bytes(self.report))
        output.chmod(0o600)
        print(
            json.dumps(
                {
                    "lane": self.lane,
                    "passed": passed,
                    "counts": {k: len(v) for k, v in self.report["suites"].items()},
                    "versions": self.report["versions"],
                },
                sort_keys=True,
            )
        )
        if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(summary).open("a") as file:
                file.write(
                    "T006 tooling-only result\n\n```json\n"
                    + json_bytes(self.report).decode()
                    + "\n```\n"
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lane", choices=LOCKS)
    args = parser.parse_args()
    job = None
    passed = False
    try:
        job = Job(args.lane)
        job.execute()
        passed = True
    except Exception:
        # No exception strings, raw subprocess output, validator values or paths reach CI logs.
        print("ci:verification_failed", flush=True)
    if job is not None:
        try:
            job.publish(passed)
        except Exception:
            print("ci:evidence_publication_failed", flush=True)
            return 1
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
