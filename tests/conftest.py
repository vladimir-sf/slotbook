"""Independent QA fixtures. Never import Backend modules or infer developer API targets."""

import os
import hashlib
from pathlib import Path

import httpx
import pytest
import yaml
from openapi_schema_validator import OAS30Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4

from harness.evidence import case_id
from harness.targets import CONTRACTS, GuardError, private_path, require, sha


@pytest.fixture(scope="session")
def contract():
    override = os.environ.get("SLOTBOOK_CONTRACT")
    path = (
        Path(override)
        if override
        else Path(__file__).resolve().parents[1]
        / "contracts/tsp-output/@typespec/openapi3/openapi.yaml"
    )
    raw = path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    require(
        blob == CONTRACTS["contracts/tsp-output/@typespec/openapi3/openapi.yaml"],
        "contract_drift",
    )
    document = yaml.safe_load(raw)
    require(document["openapi"].startswith("3.0."), "unsupported_schema")
    return document


@pytest.fixture(scope="session")
def validate_schema(contract):
    # Local registry only: no implicit network $ref retrieval or parallel handwritten DTOs.
    uri = "urn:slotbook:frozen-api"
    registry = Registry().with_resource(
        uri, Resource.from_contents(contract, default_specification=DRAFT4)
    )

    def validate(name, value):
        schema = {"$ref": f"{uri}#/components/schemas/{name}"}
        OAS30Validator(
            schema, registry=registry, format_checker=OAS30Validator.FORMAT_CHECKER
        ).validate(value)

    return validate


@pytest.fixture
def http_client():
    """Only in-memory MockTransport at T004; live origins require the T022 guarded runner."""
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"status": "ok"})
        ),
        base_url="http://fixture.invalid",
        trust_env=False,
        timeout=5,
    ) as client:
        yield client


def pytest_configure(config):
    report = config.option.xmlpath
    if report:
        try:
            private = private_path(
                os.environ["SLOTBOOK_QA_PRIVATE_DIR"], directory=True
            )
            destination = Path(report).absolute()
            require(
                destination.parent == private and not destination.is_symlink(),
                "private_report_required",
            )
            qa_root = Path(__file__).resolve().parent
            source_root = (
                qa_root.parent if (qa_root.parent / ".git").exists() else qa_root
            )
            require(
                not private.resolve().is_relative_to(source_root),
                "private_source_overlap",
            )
            candidate = os.environ["SLOTBOOK_CANDIDATE_SHA256"]
            require(sha(candidate), "candidate_required")
            os.umask(0o077)
        except (KeyError, GuardError, OSError):
            raise pytest.UsageError(
                "qa_guard:private_report_and_candidate_required"
            ) from None


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
    for item in items:
        item.user_properties.append(("evidence_id", case_id(item.nodeid)))
        item.user_properties.append(
            ("candidate_sha256", os.environ.get("SLOTBOOK_CANDIDATE_SHA256", ""))
        )
        associations = [
            str(a) for mark in item.iter_markers("associations") for a in mark.args
        ]
        item.user_properties.append(("associations", ",".join(associations)))
