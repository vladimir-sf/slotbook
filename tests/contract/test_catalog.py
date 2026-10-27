"""T026: discovery assertion authoring against frozen API v1, NOT live API proof.

Default: python -m pytest -c tests/pytest.ini tests/contract/test_catalog.py
Live: SLOTBOOK_CATALOG_MODE=live python -m pytest -c tests/pytest.ini \
    tests/contract/test_catalog.py

These modes collect separate inventories, with no skips, xfails or mock fallback. Default
cases use independently supplied HTTP responses and deliberate violations to test the
oracles. They never use conftest's MockTransport http_client or import Backend code.

Live mode requires the future guarded host runner's catalog_live_target fixture. It must
return {manifest, observed, prepare}; observed comes from actual host inspection, not
environment assertions. prepare(case) is a context manager for private synthetic seed /
clock / fault setup and cleanup UNDER this module's exclusive target lock. No public test
route is permitted. The selected immutable candidate must authorize T026/run; T004 source,
approval, target and evidence guards still apply. HTTP uses only the manifest's assigned
loopback API port, with no redirects, proxies, authentication or injected transport.

The scenario names below are the seed/fault handoff: prepare EXACTLY the expected public
projection, with additional nonpublic inactive activities, guest contacts and credentials
using PRIVATE_SENTINELS. For each case freeze N at 00:00Z on the day before its query date
(2026-10-22 for non-slot or invalid-date cases). For notice-excludes-all alone use
2026-10-23T07:00:00Z and a 09:15–09:45 activity-local window (start is only 15m away).
empty-catalog has no active activities; missing slugs do not exist, inactive slugs are
stored inactive. Empty-slot variants isolate the named reason. default/explicit-zone share
one Friday schedule, 00:15–00:45 and 23:15–23:45; visitor-date uses Friday 09:15–09:45
and Saturday 08:30–09:00, spanning two activity dates. repeated-hour uses the 02:15–02:45
Sunday window, with both Vienna folds as separate continuous portions;
spring-gap uses the wholly nonexistent 02:10–02:40 window. window-grid/window-too-short
are 09:10–10:00 / 09:10–09:40. 500/503 require Backend-owned private fault injection.
The live fixture is intentionally absent until real runtime infrastructure is available.
Missing infrastructure is an ERROR, never an expected-red behavioral result or a pass.

T030 must run EVERY live case against its real Backend before completion. T033 must rerun
them against the immutable combined candidate after T024. These contract assertions do
not prove persistence, UI rendering, concurrency, deletion, backups or real log redaction.
Only prepared guest sentinels and closed response shapes are checked here; arbitrary
unseeded personal text cannot be classified by a schema. Public descriptions may contain
legitimate public contact-like text. No full availability engine is duplicated in QA.
"""

import copy
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
import json
import os
from pathlib import Path

import httpx
from jsonschema import ValidationError
from openapi_schema_validator import OAS30Validator
import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4

from harness.targets import (
    GuardError,
    authorize,
    private_path,
    require,
    run_lock,
    verify_sources,
)

pytestmark = pytest.mark.associations(
    "T026", "FR-001", "FR-002", "FR-003", "FR-007", "FR-019", "FR-022"
)

LIST = "/api/activities"
DETAIL = LIST + "/{slug}"
SLOTS = DETAIL + "/slots"
# Independent reviewed inventory, NOT derived from the responses being tested.
STATUSES = {
    LIST: {200, 500, 503},
    DETAIL: {200, 404, 500, 503},
    SLOTS: {200, 400, 404, 500, 503},
}
ERROR_CODES = {
    400: "validation_failed",
    404: "not_found",
    500: "internal_error",
    503: "service_unavailable",
}
DESCRIPTION = 'First line — 🪐\n  <script>literal & "quoted"</script>\nFinal line.'
PRIVATE_SENTINELS = (
    "Synthetic Private Guest 026",
    "guest026@example.invalid",
    "synthetic-credential-026",
    "00000000-0000-4000-8000-000000000026",  # private booking, not public activity
)
ACTIVITY = {
    "id": "00000000-0000-4000-8000-000000000001",
    "slug": "synthetic-consultation",
    "title": "Synthetic consultation",
    "description": DESCRIPTION,
    "durationMinutes": 30,
    "timezone": "Europe/Vienna",
    "isActive": True,
}
LONG_ACTIVITY = {**ACTIVITY, "description": "🪐" * 1998 + "\nX"}


@dataclass(frozen=True)
class Case:
    name: str
    operation: str
    status: int
    expected: object
    slug: str = "synthetic-consultation"
    query: tuple = ()

    @property
    def path(self):
        return self.operation.replace("{slug}", self.slug)


def slots(*starts):
    """Handwritten UTC examples, each a half-hour interval; no schedule calculation."""
    return [{"startsAt": start, "endsAt": end} for start, end in starts]


GRID = slots(
    ("2026-10-23T07:15:00Z", "2026-10-23T07:45:00Z"),
    ("2026-10-23T07:30:00Z", "2026-10-23T08:00:00Z"),
)
DEFAULT = slots(
    ("2026-10-22T22:15:00Z", "2026-10-22T22:45:00Z"),
    ("2026-10-23T21:15:00Z", "2026-10-23T21:45:00Z"),
)
VISITOR = slots(
    ("2026-10-23T07:15:00Z", "2026-10-23T07:45:00Z"),
    ("2026-10-24T06:30:00Z", "2026-10-24T07:00:00Z"),
)
FOLDS = slots(
    ("2026-10-25T00:15:00Z", "2026-10-25T00:45:00Z"),
    ("2026-10-25T01:15:00Z", "2026-10-25T01:45:00Z"),
)
DATE_QUERY = (("date", "2026-10-23"),)

CASES = [
    Case("active-catalog", LIST, 200, [ACTIVITY]),
    Case("empty-catalog", LIST, 200, []),
    Case("list-full-2000-codepoints", LIST, 200, [LONG_ACTIVITY]),
    Case("full-literal-detail", DETAIL, 200, ACTIVITY),
    Case("detail-full-2000-codepoints", DETAIL, 200, LONG_ACTIVITY),
    Case("missing-detail", DETAIL, 404, None, slug="missing"),
    Case("inactive-detail", DETAIL, 404, None, slug="inactive"),
    Case("window-grid", SLOTS, 200, GRID, query=DATE_QUERY),
    Case("window-too-short", SLOTS, 200, [], query=DATE_QUERY),
    Case("blocked-date", SLOTS, 200, [], query=DATE_QUERY),
    Case("fully-occupied", SLOTS, 200, [], query=DATE_QUERY),
    Case("notice-excludes-all", SLOTS, 200, [], query=DATE_QUERY),
    Case("no-windows", SLOTS, 200, [], query=DATE_QUERY),
    Case("default-activity-zone", SLOTS, 200, DEFAULT, query=DATE_QUERY),
    Case(
        "explicit-activity-zone",
        SLOTS,
        200,
        DEFAULT,
        query=(*DATE_QUERY, ("displayTimezone", "Europe/Vienna")),
    ),
    Case(
        "visitor-date-two-activity-dates",
        SLOTS,
        200,
        VISITOR,
        query=(*DATE_QUERY, ("displayTimezone", "America/Los_Angeles")),
    ),
    Case(
        "repeated-hour-distinct-instants",
        SLOTS,
        200,
        FOLDS,
        query=(("date", "2026-10-25"), ("displayTimezone", "Europe/Vienna")),
    ),
    Case("spring-gap", SLOTS, 200, [], query=(("date", "2026-03-29"),)),
    Case("missing-slots", SLOTS, 404, None, slug="missing", query=DATE_QUERY),
    Case("inactive-slots", SLOTS, 404, None, slug="inactive", query=DATE_QUERY),
]
BAD_QUERIES = {
    "missing-date": (),
    "empty-date": (("date", ""),),
    "impossible-date": (("date", "2026-02-30"),),
    "malformed-date": (("date", "not-a-date"),),
    "timestamp-as-date": (("date", "2026-10-23T00:00:00Z"),),
    "invalid-zone": (*DATE_QUERY, ("displayTimezone", "Not/A_Zone")),
    "empty-zone": (*DATE_QUERY, ("displayTimezone", "")),
    "offset-as-zone": (*DATE_QUERY, ("displayTimezone", "+02:00")),
    "private-value-in-query": (*DATE_QUERY, ("displayTimezone", PRIVATE_SENTINELS[1])),
}
CASES += [
    Case(name, SLOTS, 400, None, query=query) for name, query in BAD_QUERIES.items()
]
CASES += [
    Case(
        f"{label}-{status}",
        operation,
        status,
        None,
        query=DATE_QUERY if operation == SLOTS else (),
    )
    for label, operation in (("list", LIST), ("detail", DETAIL), ("slots", SLOTS))
    for status in (500, 503)
]
BY_NAME = {case.name: case for case in CASES}
# One positive control for EVERY declared operation/status, including each error union.
RESPONSE_CASES = [
    next(
        case for case in CASES if case.operation == operation and case.status == status
    )
    for operation, statuses in STATUSES.items()
    for status in sorted(statuses)
]


def check(condition, code):
    __tracebackhide__ = True
    if not condition:
        raise AssertionError("catalog:" + code)


def schema_check(contract, pointer, value, code):
    __tracebackhide__ = True
    uri = "urn:slotbook:catalog-api-v1"
    registry = Registry().with_resource(
        uri, Resource.from_contents(contract, default_specification=DRAFT4)
    )
    try:
        # Enter the immutable document at its operation schema, so relative $refs
        # resolve at its root without network retrieval or private validator APIs.
        OAS30Validator(
            {"$ref": uri + pointer},
            registry=registry,
            format_checker=OAS30Validator.FORMAT_CHECKER,
        ).validate(value)
    except ValidationError:
        raise AssertionError("catalog:" + code) from None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def assert_response(contract, case, response):
    """Same assertions in authoring and live modes; failures expose only fixed codes."""
    __tracebackhide__ = True
    check(
        response.request.method == "GET" and response.request.url.path == case.path,
        "request_path",
    )
    check(
        list(response.request.url.params.multi_items()) == list(case.query),
        "request_query",
    )
    check(response.status_code == case.status, "expected_status")
    operation = contract["paths"][case.operation]["get"]
    check(str(response.status_code) in operation["responses"], "undeclared_status")
    spec = operation["responses"][str(response.status_code)]
    path_pointer = case.operation.replace("~", "~0").replace("/", "~1")
    pointer = f"#/paths/{path_pointer}/get/responses/{response.status_code}"
    for name, header in spec.get("headers", {}).items():
        check(not header.get("required") or name in response.headers, "required_header")
        if name in response.headers:
            schema_check(
                contract,
                pointer + "/headers/" + name + "/schema",
                response.headers[name],
                "header_schema",
            )
    check("set-cookie" not in response.headers, "auth_cookie")
    check(
        not any(
            value in header
            for value in PRIVATE_SENTINELS
            for header in response.headers.values()
        ),
        "private_header",
    )
    check(
        response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        == "application/json",
        "json_content_type",
    )
    try:
        body = json.loads(response.content, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError):
        raise AssertionError("catalog:json_body") from None
    schema_check(
        contract, pointer + "/content/application~1json/schema", body, "body_schema"
    )
    text = json.dumps(body, ensure_ascii=False)
    check(not any(value in text for value in PRIVATE_SENTINELS), "private_value")
    if case.status != 200:
        check(body["code"] == ERROR_CODES[case.status], "error_code")
        messages = [
            body["message"],
            *(field["message"] for field in body.get("fields", [])),
        ]
        check(all(message.strip() for message in messages), "empty_error_message")
        query_values = [
            value for _, value in case.query if value and value != "2026-10-23"
        ]
        check(
            not any(value in message for value in query_values for message in messages),
            "reflected_query",
        )
        check(
            not any(
                value.lower() in text.lower()
                for value in (
                    "Traceback (most recent",
                    "SELECT ",
                    "postgresql://",
                    "Authorization:",
                    "Idempotency-Key:",
                )
            ),
            "diagnostic_value",
        )
        check(
            all(
                field["path"] in {"date", "displayTimezone", "$"}
                for field in body.get("fields", [])
            ),
            "unsafe_field_path",
        )
        return
    # Exact independently prepared projections catch truncation, markup interpretation,
    # timezone/default mistakes, inactive rows, omitted/extra/duplicated/moved UTC slots.
    check(body == case.expected, "public_projection")
    if case.operation == SLOTS:
        starts = []
        for slot in body:
            check(
                slot["startsAt"].endswith("Z") and slot["endsAt"].endswith("Z"), "utc_z"
            )
            start, end = (
                datetime.fromisoformat(slot[key]) for key in ("startsAt", "endsAt")
            )
            check(start < end, "positive_interval")
            starts.append(start)
        check(starts == sorted(set(starts)), "ordered_unique_slots")


def response_for(case, *, body=None, status=None, headers=None, raw=None):
    """Independent response input, NOT a backend emulator or live transport."""
    if body is None:
        body = (
            copy.deepcopy(case.expected)
            if case.status == 200
            else {
                "code": ERROR_CODES[case.status],
                "message": "The request could not be completed.",
            }
        )
    request = httpx.Request(
        "GET", "http://fixture.invalid" + case.path, params=case.query
    )
    return httpx.Response(
        case.status if status is None else status,
        request=request,
        headers={"Cache-Control": "no-store", "Content-Type": "application/json"}
        if headers is None
        else headers,
        content=json.dumps(body, ensure_ascii=False).encode() if raw is None else raw,
    )


def mode(value):
    if value not in {"authoring", "live"}:
        raise pytest.UsageError("catalog_guard:unknown_mode")
    return value


def runtime_provider(request):
    try:
        return request.getfixturevalue("catalog_live_target")
    except pytest.FixtureLookupError:
        raise GuardError("catalog_runtime_provider_required") from None


@contextmanager
def live_client(target, case):
    """Only a host-observed immutable disposable candidate can reach real HTTP."""
    require(
        isinstance(target, dict) and set(target) == {"manifest", "observed", "prepare"},
        "catalog_runtime_target_required",
    )
    m = target["manifest"]
    authorize(m, "run", target["observed"])
    require(
        "T026" in m["task_ids"] and m["milestone"] == "T034", "catalog_scope_required"
    )
    require(callable(target["prepare"]), "catalog_preparation_required")
    private = private_path(m["private_dir"], directory=True)
    require(
        all(
            not private.is_relative_to(Path(c["checkout"]).resolve())
            for c in m["components"].values()
        ),
        "private_source_overlap",
    )
    with run_lock(private, m["target"]["project"]):
        verify_sources(m)
        try:
            # Keep the reviewed oracle independent of mutable seed-adapter inputs.
            with target["prepare"](copy.deepcopy(case)):
                # No environment URL and no ability for the fixture to inject MockTransport.
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{m['target']['api_port']}",
                    transport=httpx.HTTPTransport(retries=0, trust_env=False),
                    trust_env=False,
                    follow_redirects=False,
                    timeout=5,
                ) as client:
                    yield client
        finally:
            verify_sources(m)


class CatalogLive:
    """Collected ONLY with SLOTBOOK_CATALOG_MODE=live; no skips or expected-failure masks."""

    @pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
    def test_real_backend(self, contract, guarded_catalog_live_client, case):
        __tracebackhide__ = True
        try:
            response = guarded_catalog_live_client.get(case.path, params=case.query)
        except httpx.HTTPError:
            pytest.fail("catalog_guard:live_connection_failed", pytrace=False)
        assert_response(contract, case, response)


@pytest.fixture
def guarded_catalog_live_client(request, case):
    __tracebackhide__ = True
    try:
        target = runtime_provider(request)
        with live_client(target, case) as client:
            yield client
    except Exception:
        # Missing runtime inputs are setup errors, distinct from behavioral assertions.
        # OS/git/provider exceptions can contain private paths or inputs. Never echo them.
        pytest.fail("catalog_guard:runtime_unavailable_or_unapproved", pytrace=False)


class CatalogAuthoring:
    pytestmark = pytest.mark.schema

    def test_frozen_operation_inventory(self, contract):
        assert len(BY_NAME) == len(CASES)
        assert {(c.operation, c.status) for c in CASES} == {
            (op, status) for op, statuses in STATUSES.items() for status in statuses
        }
        for path, statuses in STATUSES.items():
            operation = contract["paths"][path]["get"]
            assert set(operation["responses"]) == {str(status) for status in statuses}
            assert not operation.get("security")
            for response in operation["responses"].values():
                assert response["headers"]["Cache-Control"] == {
                    "required": True,
                    "schema": {"type": "string", "enum": ["no-store"]},
                }
        params = {p["name"]: p for p in contract["paths"][SLOTS]["get"]["parameters"]}
        assert (
            params["date"]["required"] and params["date"]["schema"]["format"] == "date"
        )
        assert params["displayTimezone"]["required"] is False
        assert (
            params["displayTimezone"]["schema"]["$ref"]
            == "#/components/schemas/IanaTimezone"
        )

    @pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
    def test_controlled_response_oracle(self, contract, case):
        assert_response(contract, case, response_for(case))

    @pytest.mark.parametrize(
        "case", RESPONSE_CASES, ids=lambda case: f"{case.operation}-{case.status}"
    )
    @pytest.mark.parametrize("header", ["missing", "cacheable"])
    def test_each_response_requires_no_store(self, contract, case, header):
        assert_response(contract, case, response_for(case))
        headers = {"Content-Type": "application/json"}
        if header == "cacheable":
            headers["Cache-Control"] = "public, max-age=3600"
        with pytest.raises(
            AssertionError, match="^catalog:(required_header|header_schema)$"
        ):
            assert_response(contract, case, response_for(case, headers=headers))

    @pytest.mark.parametrize(
        "case", RESPONSE_CASES, ids=lambda case: f"{case.operation}-{case.status}"
    )
    def test_each_response_rejects_guest_fields(self, contract, case):
        good = response_for(case)
        assert_response(contract, case, good)
        body = good.json()
        row = body[0] if isinstance(body, list) else body
        row["attendeeEmail"] = PRIVATE_SENTINELS[1]
        with pytest.raises(AssertionError, match="^catalog:body_schema$"):
            assert_response(contract, case, response_for(case, body=body))

    @pytest.mark.parametrize("value", PRIVATE_SENTINELS)
    def test_private_headers_cannot_bypass_body_privacy(self, contract, value):
        case = BY_NAME["active-catalog"]
        response = response_for(case)
        assert_response(contract, case, response)
        response.headers["X-Debug"] = value
        with pytest.raises(AssertionError, match="^catalog:private_header$"):
            assert_response(contract, case, response)

    @pytest.mark.parametrize(
        "case",
        [case for case in RESPONSE_CASES if case.status != 200],
        ids=lambda case: f"{case.operation}-{case.status}",
    )
    def test_error_union_rejects_another_operations_code(self, contract, case):
        assert_response(contract, case, response_for(case))
        wrong = {"code": "slot_unavailable", "message": "Try another slot."}
        with pytest.raises(AssertionError, match="^catalog:body_schema$"):
            assert_response(contract, case, response_for(case, body=wrong))

    @pytest.mark.parametrize(
        "case", RESPONSE_CASES, ids=lambda case: f"{case.operation}-{case.status}"
    )
    @pytest.mark.parametrize("status", [202, 204, 400, 401, 404, 422, 500, 503])
    def test_success_and_failure_are_never_interchanged(self, contract, case, status):
        # Include status==expected: a wrong body must still fail the frozen union.
        assert_response(contract, case, response_for(case))
        body = (
            []
            if case.status != 200
            else {"code": "service_unavailable", "message": "Unavailable."}
        )
        with pytest.raises(
            AssertionError, match="^catalog:(expected_status|body_schema)$"
        ):
            assert_response(
                contract, case, response_for(case, status=status, body=body)
            )

    @pytest.mark.parametrize(
        "name,field,value",
        [
            ("full-literal-detail", "description", DESCRIPTION[:10]),
            ("full-literal-detail", "description", DESCRIPTION.replace("\n", " ")),
            (
                "full-literal-detail",
                "description",
                DESCRIPTION.replace("<script>", "&lt;script&gt;"),
            ),
            ("full-literal-detail", "description", ""),
            ("detail-full-2000-codepoints", "description", "🪐" * 2001),
            ("detail-full-2000-codepoints", "description", "🪐" * 1000),
            ("full-literal-detail", "durationMinutes", 0),
            ("full-literal-detail", "durationMinutes", 16),
            ("full-literal-detail", "id", "not-a-uuid"),
            ("full-literal-detail", "timezone", "+02:00"),
            ("active-catalog", "isActive", False),
            ("active-catalog", "description", DESCRIPTION[:10]),
            ("active-catalog", "timezone", "Not/A_Zone"),
        ],
    )
    def test_activity_schema_and_full_projection_violations(
        self, contract, name, field, value
    ):
        case = BY_NAME[name]
        assert_response(contract, case, response_for(case))
        body = copy.deepcopy(case.expected)
        (body[0] if isinstance(body, list) else body)[field] = value
        with pytest.raises(
            AssertionError, match="^catalog:(body_schema|public_projection)$"
        ):
            assert_response(contract, case, response_for(case, body=body))

    @pytest.mark.parametrize(
        "kind",
        [
            "unsorted",
            "duplicate",
            "omitted",
            "extra",
            "wrong-date",
            "offset",
            "naive",
            "reversed",
            "booking-id",
        ],
    )
    def test_slot_projection_violations(self, contract, kind):
        case = BY_NAME["window-grid"]
        assert_response(contract, case, response_for(case))
        body = copy.deepcopy(case.expected)
        if kind == "unsorted":
            body.reverse()
        elif kind == "duplicate":
            body.append(copy.deepcopy(body[0]))
        elif kind == "omitted":
            body.pop()
        elif kind == "extra":
            body.append(
                {"startsAt": "2026-10-23T07:10:00Z", "endsAt": "2026-10-23T07:40:00Z"}
            )
        elif kind == "wrong-date":
            body[0]["startsAt"] = "2026-10-24T07:15:00Z"
        elif kind in {"offset", "naive"}:
            body[0]["startsAt"] = "2026-10-23T07:15:00" + (
                "+00:00" if kind == "offset" else ""
            )
        elif kind == "reversed":
            body[0]["endsAt"] = "2026-10-23T07:00:00Z"
        else:
            body[0]["bookingId"] = PRIVATE_SENTINELS[3]
        with pytest.raises(
            AssertionError, match="^catalog:(body_schema|public_projection)$"
        ):
            assert_response(contract, case, response_for(case, body=body))

    @pytest.mark.parametrize(
        "name,wrong",
        [
            ("default-activity-zone", VISITOR),
            ("explicit-activity-zone", VISITOR),
            ("visitor-date-two-activity-dates", DEFAULT),
            ("repeated-hour-distinct-instants", FOLDS[:1]),
            ("spring-gap", FOLDS),
            ("window-too-short", GRID),
            ("empty-catalog", [ACTIVITY]),
        ],
    )
    def test_wrong_timezone_default_empty_or_fold_cannot_pass(
        self, contract, name, wrong
    ):
        case = BY_NAME[name]
        assert_response(contract, case, response_for(case))
        with pytest.raises(AssertionError, match="^catalog:public_projection$"):
            assert_response(contract, case, response_for(case, body=wrong))

    @pytest.mark.parametrize(
        "value",
        [
            *PRIVATE_SENTINELS,
            "Traceback (most recent call last)",
            "SELECT attendee_email FROM private.contacts",
            "postgresql://private",
            "Authorization: synthetic",
            "Idempotency-Key: synthetic",
            "Not/A_Zone",
        ],
    )
    def test_errors_reject_private_diagnostic_and_reflected_values(
        self, contract, value
    ):
        case = BY_NAME["invalid-zone"]
        assert_response(contract, case, response_for(case))
        body = {"code": "validation_failed", "message": value}
        with pytest.raises(
            AssertionError,
            match="^catalog:(private_value|reflected_query|diagnostic_value)$",
        ):
            assert_response(contract, case, response_for(case, body=body))

    def test_optional_safe_field_errors(self, contract):
        case = BY_NAME["invalid-zone"]
        body = {
            "code": "validation_failed",
            "message": "Invalid query.",
            "fields": [
                {
                    "path": "displayTimezone",
                    "code": "invalid",
                    "message": "Choose a supported IANA timezone.",
                }
            ],
        }
        assert_response(contract, case, response_for(case, body=body))
        for key, value in (
            ("path", PRIVATE_SENTINELS[1]),
            ("message", PRIVATE_SENTINELS[0]),
            ("code", "invalid_zone"),
        ):
            wrong = copy.deepcopy(body)
            wrong["fields"][0][key] = value
            with pytest.raises(
                AssertionError, match="^catalog:(private_value|body_schema)$"
            ):
                assert_response(contract, case, response_for(case, body=wrong))

    @pytest.mark.parametrize("field", ["message", "path"])
    def test_error_fields_cannot_reflect_query_values(self, contract, field):
        case = BY_NAME["invalid-zone"]
        body = {
            "code": "validation_failed",
            "message": "Invalid query.",
            "fields": [
                {
                    "path": "displayTimezone",
                    "code": "invalid",
                    "message": "Choose a supported IANA timezone.",
                }
            ],
        }
        assert_response(contract, case, response_for(case, body=body))
        body["fields"][0][field] = "Not/A_Zone"
        with pytest.raises(
            AssertionError, match="^catalog:(reflected_query|unsafe_field_path)$"
        ):
            assert_response(contract, case, response_for(case, body=body))

    @pytest.mark.parametrize(
        "raw",
        [
            b"<html>unavailable</html>",
            b"null",
            b"{",
            b'{"code":"not_found","message":"safe","code":"service_unavailable"}',
        ],
    )
    def test_malformed_or_duplicate_json_is_not_empty_success(self, contract, raw):
        case = BY_NAME["empty-catalog"]
        with pytest.raises(AssertionError, match="^catalog:(json_body|body_schema)$"):
            assert_response(contract, case, response_for(case, raw=raw))

    @pytest.mark.parametrize(
        "headers",
        [
            {"Cache-Control": "no-store", "Content-Type": "text/html"},
            {
                "Cache-Control": "no-store",
                "Content-Type": "application/json",
                "Set-Cookie": "synthetic=1",
            },
        ],
    )
    def test_html_and_cookies_are_rejected(self, contract, headers):
        case = BY_NAME["active-catalog"]
        with pytest.raises(
            AssertionError, match="^catalog:(json_content_type|auth_cookie)$"
        ):
            assert_response(contract, case, response_for(case, headers=headers))

    def test_header_names_and_json_charset_are_not_overconstrained(self, contract):
        case = BY_NAME["active-catalog"]
        headers = {
            "cache-control": "no-store",
            "content-type": "application/json ; charset=utf-8",
        }
        assert_response(contract, case, response_for(case, headers=headers))

    def test_requests_keep_required_and_optional_queries_distinct(self, contract):
        case = BY_NAME["default-activity-zone"]
        check("displayTimezone" not in dict(case.query), "default_query")
        response = response_for(case)
        response.request = httpx.Request(
            "GET",
            "http://fixture.invalid" + case.path,
            params=(*case.query, ("displayTimezone", "UTC")),
        )
        with pytest.raises(AssertionError, match="^catalog:request_query$"):
            assert_response(contract, case, response)

    def test_live_guard_rejects_missing_target_before_http(self, monkeypatch):
        def forbidden(*args, **kwargs):
            raise AssertionError("HTTP must not start before guards")

        monkeypatch.setattr(httpx, "Client", forbidden)
        for target in (None, {}, {"manifest": {}, "observed": {}, "prepare": None}):
            with pytest.raises(GuardError):
                with live_client(target, CASES[0]):
                    pytest.fail("unguarded_live_target")

    def test_unknown_mode_cannot_fall_back(self):
        with pytest.raises(pytest.UsageError, match="^catalog_guard:unknown_mode$"):
            mode("unexpected")

    def test_utc_policy_is_stronger_than_openapi_date_time(self, contract):
        # OpenAPI accepts an offset instant. The documented v1 UTC-Z policy still must
        # reject it independently, even if an expected projection were accidentally offset.
        original = BY_NAME["window-grid"]
        body = copy.deepcopy(original.expected)
        body[0]["startsAt"] = "2026-10-23T07:15:00+00:00"
        case = replace(original, expected=body)
        with pytest.raises(AssertionError, match="^catalog:utc_z$"):
            assert_response(contract, case, response_for(case))

    @pytest.mark.parametrize("kind", ["reversed", "unsorted", "duplicate"])
    def test_interval_and_order_guards_are_independent_of_projection(
        self, contract, kind
    ):
        original = BY_NAME["window-grid"]
        body = copy.deepcopy(original.expected)
        if kind == "reversed":
            body[0]["endsAt"] = "2026-10-23T07:00:00Z"
        elif kind == "unsorted":
            body.reverse()
        else:
            body.append(copy.deepcopy(body[0]))
        case = replace(original, expected=body)
        with pytest.raises(
            AssertionError, match="^catalog:(positive_interval|ordered_unique_slots)$"
        ):
            assert_response(contract, case, response_for(case))


if mode(os.environ.get("SLOTBOOK_CATALOG_MODE", "authoring")) == "live":
    TestCatalogLive = CatalogLive
else:
    TestCatalogAuthoring = CatalogAuthoring
