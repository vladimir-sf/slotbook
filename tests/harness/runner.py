"""T004 host interface. T022 will supply lifecycle adapters and milestone inventories.

SLOTBOOK_TEST_MANIFEST must name an owner-only JSON file outside tracked source.
check validates an immutable candidate; run additionally requires target observation in T022.
collect publishes only validated evidence from the private journal. No shell/raw streams printed.
Exit 0 = verified; 1 = actual failed/skipped assertions; 2 = guard/setup/unwired interface.
"""

import argparse
import os
import sys
from pathlib import Path

# Supports the exact documented direct-script entry point without application imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.evidence import collect  # noqa: E402
from harness.targets import (  # noqa: E402
    GuardError,
    authorize,
    private_path,
    read_private_json,
    require,
    run_lock,
    validate_manifest,
    verify_sources,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("collect")
    run = commands.add_parser("run")
    selection = run.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--suite",
        choices=[
            "backend",
            "infrastructure",
            "contract",
            "concurrency",
            "privacy",
            "e2e",
        ],
    )
    selection.add_argument("--milestone", choices=["T024", "T034"])
    args = parser.parse_args(argv)
    try:
        location = os.environ.get("SLOTBOOK_TEST_MANIFEST")
        require(location, "manifest_required")
        m = validate_manifest(read_private_json(location))
        # Configuration is private, never inside published evidence or a selected checkout.
        private = private_path(m["private_dir"], directory=True)
        for c in m["components"].values():
            root = Path(c["checkout"]).resolve()
            require(
                not private.resolve().is_relative_to(root)
                and not Path(location).resolve().is_relative_to(root),
                "private_source_overlap",
            )
        require(args.command in m["approval"]["operations"], "operation_not_approved")
        if args.command != "run":
            authorize(m, args.command)
        with run_lock(private, m["target"]["project"]):
            verify_sources(m)
            if args.command == "run":
                if args.milestone:
                    require(args.milestone == m["milestone"], "milestone_mismatch")
                raise GuardError("lifecycle_adapters_deferred_to_T022")
            if args.command == "collect":
                qa = Path(m["components"]["qa"]["checkout"])
                result = collect(
                    m, qa / "test-results", recheck=lambda: verify_sources(m)
                )
                print("evidence_passed" if result["passed"] else "evidence_failed")
                return 0 if result["passed"] else 1
        print("candidate_checked")
        return 0
    except GuardError as exc:
        print("qa_guard:" + str(exc), file=sys.stderr)
    except Exception:
        # JSON/XML/OS/git errors may contain credentials or raw paths; retain no exception text.
        print("qa_guard:invalid_private_input", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
