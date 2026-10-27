import { expect, test } from "@playwright/test";
import Ajv from "ajv";
import addFormats from "ajv-formats";
import { chmodSync, mkdtempSync, readFileSync, statSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import type { OpenAPIV3 } from "openapi-types";
import { parse } from "yaml";
import type { components, operations } from "../src/api/schema.js";
import { privateReportDirectory } from "../playwright.config.js";
import {
  activity, booking, bookingRequest, presentBooking, removedBooking,
  responseFixtures, weeklyWindows,
} from "./fixtures/api.js";

// Read the committed frozen output directly. No compilation or regeneration.
const contract: OpenAPIV3.Document = parse(readFileSync(new URL(
  "../../contracts/tsp-output/@typespec/openapi3/openapi.yaml", import.meta.url,
), "utf8"));
const contractId = "urn:slotbook:frozen-api-v1";
// OpenAPI 3.0 has annotation keywords outside JSON Schema; retain all validation
// keywords, including nullable, formats and additionalProperties. Never coerce,
// remove fields or fill defaults: invalid fixtures must fail unchanged.
const validator = new Ajv({ strict: false });
addFormats(validator);
validator.addFormat("int32", { type: "number", validate: (value) => Number.isInteger(value) && value >= -2147483648 && value <= 2147483647 });
validator.addSchema(contract, contractId);
const pointer = (part: string) => part.replaceAll("~", "~0").replaceAll("/", "~1");
const contractOperations = new Map<string, { operation: OpenAPIV3.OperationObject; pointer: string }>();
for (const [path, item] of Object.entries(contract.paths)) {
  for (const method of ["get", "post", "put", "delete"] as const) {
    const operation = item?.[method];
    if (operation?.operationId) {
      contractOperations.set(operation.operationId, { operation, pointer: `/paths/${pointer(path)}/${method}` });
    }
  }
}

function matchesSchema(location: string, value: unknown): boolean {
  return validator.compile({ $ref: `${contractId}#${location}` })(value) === true;
}

function matchesResponse(
  operationId: string,
  status: number,
  response: { headers: Record<string, unknown>; content?: Record<string, unknown> },
): boolean {
  const entry = contractOperations.get(operationId);
  const schema = entry?.operation.responses[String(status)];
  if (!entry || !schema || "$ref" in schema) return false;
  const location = `${entry.pointer}/responses/${status}`;
  for (const [name, header] of Object.entries(schema.headers ?? {})) {
    if ("$ref" in header) return false;
    const value = response.headers[name];
    if (value === undefined && header.required) return false;
    if (value !== undefined && !matchesSchema(`${location}/headers/${pointer(name)}/schema`, value)) return false;
  }
  const bodySchema = schema.content?.["application/json"]?.schema;
  if (!bodySchema) return response.content === undefined;
  return response.content !== undefined
    && Object.keys(response.content).length === 1
    && matchesSchema(`${location}/content/application~1json/schema`, response.content["application/json"]);
}

test("T003 frozen API v1 has a nonempty fixture baseline for all 18 operations", () => {
  expect(contract.info.version === "1.0.0", "T003_API_VERSION").toBe(true);
  expect(contractOperations.size === 18, "T003_OPERATION_COUNT").toBe(true);
  expect(responseFixtures.length > 0, "T003_NONEMPTY_FIXTURES").toBe(true);
  const covered = new Set(responseFixtures.map((fixture) => fixture.operationId));
  expect([...contractOperations.keys()].every((id) => covered.has(id as keyof operations)), "T003_OPERATION_COVERAGE").toBe(true);
});

for (const fixture of responseFixtures) {
  test(`T003 response fixture ${fixture.id}`, () => {
    // Boolean assertions keep raw values and validator diagnostics out of reports.
    expect(matchesResponse(fixture.operationId, fixture.status, fixture.response), "T003_RESPONSE_SCHEMA").toBe(true);
  });
}

test("T003 generated request types and contact discriminators match frozen schemas", () => {
  expect(matchesSchema("/components/schemas/BookingRequest", bookingRequest), "T003_REQUEST_SCHEMA").toBe(true);
  expect(matchesSchema("/components/schemas/AdminBooking", presentBooking), "T003_PRESENT_SCHEMA").toBe(true);
  expect(matchesSchema("/components/schemas/AdminBooking", removedBooking), "T003_REMOVED_SCHEMA").toBe(true);
  expect(matchesSchema("/components/schemas/WeeklyWindow", weeklyWindows[0]), "T003_WINDOW_SCHEMA").toBe(true);
});

// These deliberate compile failures prove test files participate in typechecking.
// TypeScript cannot enforce UUIDs, dates, numeric constraints or exact spread
// shapes; the runtime negative cases below check those against frozen OpenAPI.
const invalidStatus: components["schemas"]["BookingSummary"] = {
  ...booking,
  // @ts-expect-error API v1 has no pending BookingSummary status.
  status: "pending",
};
const invalidRequest: components["schemas"]["BookingRequest"] = {
  ...bookingRequest,
  // @ts-expect-error End time is server-derived and is not a request property.
  endsAt: booking.endsAt,
};
void invalidStatus;
void invalidRequest;

const invalidPayloads: { id: string; schema: string; value: unknown }[] = [
  { id: "missing-description", schema: "Activity", value: { ...activity, description: undefined } },
  { id: "empty-description", schema: "Activity", value: { ...activity, description: "" } },
  { id: "overlong-description", schema: "Activity", value: { ...activity, description: "a".repeat(2001) } },
  { id: "invalid-duration", schema: "Activity", value: { ...activity, durationMinutes: 20 } },
  { id: "invalid-uuid", schema: "Activity", value: { ...activity, id: "invalid" } },
  { id: "naive-instant", schema: "Slot", value: { startsAt: "2026-11-02T09:00:00", endsAt: booking.endsAt } },
  { id: "invalid-email", schema: "BookingRequest", value: { ...bookingRequest, attendeeEmail: "invalid" } },
  { id: "blank-name", schema: "BookingRequest", value: { ...bookingRequest, attendeeName: " " } },
  { id: "client-derived-end", schema: "BookingRequest", value: invalidRequest },
  { id: "public-contact-leak", schema: "BookingSummary", value: { ...booking, attendeeEmail: bookingRequest.attendeeEmail } },
  { id: "public-pending-status", schema: "BookingSummary", value: invalidStatus },
  { id: "removed-contact-leak", schema: "AdminBooking", value: { ...removedBooking, contact: { state: "removed", attendeeName: bookingRequest.attendeeName } } },
  { id: "incomplete-present-contact", schema: "AdminBooking", value: { ...presentBooking, contact: { state: "present" } } },
  { id: "invalid-weekday", schema: "WeeklyWindow", value: { ...weeklyWindows[0], isoWeekday: 8 } },
  { id: "offset-window-clock", schema: "WeeklyWindow", value: { ...weeklyWindows[0], localStart: "09:10+01:00" } },
  { id: "invalid-block-date", schema: "BlockedDate", value: { date: "2026-02-30" } },
];
for (const invalid of invalidPayloads) {
  test(`T003 rejects ${invalid.id}`, () => {
    expect(matchesSchema(`/components/schemas/${invalid.schema}`, invalid.value), "T003_INVALID_PAYLOAD_REJECTED").toBe(false);
  });
}

test("T003 rejects undeclared statuses, wrong error codes and missing or invalid headers", () => {
  const created = responseFixtures.find((fixture) => fixture.id === "created")!;
  expect(matchesResponse("Bookings_create", 422, created.response), "T003_UNDECLARED_STATUS").toBe(false);
  expect(matchesResponse("Bookings_create", 201, { ...created.response, headers: { "Cache-Control": "no-store" } }), "T003_REQUIRED_EXPIRY").toBe(false);
  expect(matchesResponse("Bookings_create", 201, { ...created.response, headers: { ...created.response.headers, "Cache-Control": "public" } }), "T003_NO_STORE").toBe(false);
  expect(matchesResponse("Bookings_create", 202, { headers: { ...created.response.headers, "Retry-After": -1 }, content: { "application/json": { state: "pending", expiresAt: created.response.headers["X-Attempt-Expires-At"] } } }), "T003_RETRY_AFTER").toBe(false);
  expect(matchesResponse("Bookings_create", 410, { headers: created.response.headers, content: { "application/json": { code: "attempt_invalidated_by_restore", message: "Contact the host." } } }), "T003_DISTINCT_EXPIRY_CODE").toBe(false);
  expect(matchesResponse("Auth_logout", 204, { headers: { "Cache-Control": "no-store" }, content: { "application/json": {} } }), "T003_EMPTY_204").toBe(false);
  expect(matchesResponse("Auth_login", 401, { headers: { "Cache-Control": "no-store" }, content: { "application/json": { code: "unauthorized", message: "Sign in again." } } }), "T003_BEARER_CHALLENGE").toBe(false);
});

test("T003 report directories are private and cannot resolve into the checkout", () => {
  const directory = privateReportDirectory();
  expect((statSync(directory).mode & 0o077) === 0, "T003_REPORT_PERMISSIONS").toBe(true);
  expect(privateReportDirectory(directory) === directory, "T003_QA_REPORT_OVERRIDE").toBe(true);
  expect(() => privateReportDirectory("relative"), "T003_RELATIVE_REPORT_REJECTED").toThrow("T003_REPORT_DIRECTORY_OUTSIDE_CHECKOUT_REQUIRED");
  expect(() => privateReportDirectory(resolve(".")), "T003_CHECKOUT_REPORT_REJECTED").toThrow("T003_REPORT_DIRECTORY_OUTSIDE_CHECKOUT_REQUIRED");
  const shared = mkdtempSync(resolve(tmpdir(), "slotbook-report-shared-"));
  chmodSync(shared, 0o755);
  expect(() => privateReportDirectory(shared), "T003_SHARED_DIRECTORY_REJECTED").toThrow("T003_OWNER_ONLY_REPORT_DIRECTORY_REQUIRED");
  const link = resolve(mkdtempSync(resolve(tmpdir(), "slotbook-report-link-")), "checkout");
  symlinkSync(resolve("."), link, "dir");
  expect(() => privateReportDirectory(link), "T003_SYMLINK_REPORT_REJECTED").toThrow("T003_REPORT_DIRECTORY_OUTSIDE_CHECKOUT_REQUIRED");
});

test("T003 Chromium renders the public frontend entry point", async ({ page }) => {
  await page.route("**/api/activities", (route) => route.fulfill({
    status: 200, headers: { "Cache-Control": "no-store", "Access-Control-Allow-Origin": "*" }, json: [],
  }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Choose an appointment", exact: true })).toBeVisible();
  await expect(page.getByText("No appointment types are available.", { exact: true })).toBeVisible();
});
