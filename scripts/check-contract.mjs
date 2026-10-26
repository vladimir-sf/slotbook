#!/usr/bin/env node
/**
 * T005: Lead-owned frozen API v1 verification; not runtime acceptance evidence.
 * Install locked dependencies with npm --prefix contracts ci and npm --prefix frontend ci.
 * Uses their existing locked YAML/Ajv/Redocly/TypeScript tools; no downloads or app writes.
 * Run through check-contract.sh, optionally --self-test for guard regression checks.
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const baseline = "adc0b83a4408493ac44d3a7571dfd3d25a758679";
const frozenFiles = [
  "contracts/main.tsp",
  "contracts/tsp-output/@typespec/openapi3/openapi.yaml",
  "frontend/src/api/schema.d.ts",
];
const selfTest = process.argv.slice(2);
if (
  selfTest.length > 1 ||
  (selfTest.length === 1 && selfTest[0] !== "--self-test")
) {
  console.error("Usage: bash scripts/check-contract.sh [--self-test]");
  process.exit(2);
}
function run(command, args, cwd = root) {
  try {
    return execFileSync(command, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, NO_COLOR: "1" },
      timeout: 120000,
    });
  } catch (error) {
    throw new Error(
      "Command failed (" +
        (error.status ?? error.code ?? error.signal) +
        "): " +
        path.basename(command) +
        " " +
        args.join(" ") +
        " (raw output withheld)",
    );
  }
}
function frozenBytes(name) {
  return run("git", ["show", baseline + ":" + name]);
}
function sameBytes(actual, expected, label) {
  assert.ok(
    actual.equals(expected),
    label + " drifted; use the approved contract-change process",
  );
}
function assertFixtureCount(count) {
  assert.ok(
    Number.isInteger(count) && count >= 60,
    "Expected at least 60 executed schema fixtures; zero/missing coverage fails",
  );
}

let parse, Ajv, addFormats, lint, createConfig, frozenDoc;
const expected = {
  "get /api/activities": [200, 500, 503],
  "get /api/activities/{slug}": [200, 404, 500, 503],
  "get /api/activities/{slug}/slots": [200, 400, 404, 500, 503],
  "get /api/booking-attempts/context": [200, 500, 503],
  "post /api/bookings": [200, 201, 202, 400, 409, 410, 500, 503],
  "post /api/auth/login": [200, 400, 401, 500, 503],
  "delete /api/auth/session": [204, 401, 500, 503],
  "get /api/admin/activities": [200, 401, 500, 503],
  "post /api/admin/activities": [200, 400, 401, 409, 500, 503],
  "put /api/admin/activities/{id}": [200, 400, 401, 404, 409, 500, 503],
  "get /api/admin/activities/{id}/weekly-windows": [
    200, 400, 401, 404, 500, 503,
  ],
  "put /api/admin/activities/{id}/weekly-windows": [
    200, 400, 401, 404, 500, 503,
  ],
  "get /api/admin/activities/{id}/blocked-dates": [
    200, 400, 401, 404, 500, 503,
  ],
  "post /api/admin/activities/{id}/blocked-dates": [
    200, 400, 401, 404, 500, 503,
  ],
  "get /api/admin/bookings": [200, 401, 500, 503],
  "delete /api/admin/bookings/{id}": [204, 400, 401, 404, 500, 503],
  "get /health": [200, 500, 503],
  "get /ready": [200, 500, 503],
};
function checkSurface(doc) {
  let count = 0;
  const ids = new Set();
  for (const [p, item] of Object.entries(doc.paths))
    for (const [method, op] of Object.entries(item)) {
      const key = `${method} ${p}`;
      count++;
      assert.ok(expected[key], key);
      assert.deepEqual(
        Object.keys(op.responses).map(Number),
        expected[key],
        key,
      );
      assert.ok(!ids.has(op.operationId));
      ids.add(op.operationId);
      const protectedOp =
        p.startsWith("/api/admin/") || p === "/api/auth/session";
      const security = op.security ?? doc.security;
      if (protectedOp) assert.deepEqual(security, [{ BearerAuth: [] }], key);
      else
        assert.ok(
          !security ||
            security.length === 0 ||
            JSON.stringify(security) === "[{}]",
          key,
        );
      for (const [status, response] of Object.entries(op.responses)) {
        assert.equal(
          response.headers?.["Cache-Control"]?.required,
          true,
          key + status,
        );
        assert.deepEqual(response.headers["Cache-Control"].schema.enum, [
          "no-store",
        ]);
        if (status === "204") assert.equal(response.content, undefined);
        else assert.ok(response.content["application/json"].schema);
        if (status === "401")
          assert.deepEqual(response.headers["WWW-Authenticate"].schema.enum, [
            "Bearer",
          ]);
      }
    }
  assert.equal(count, 18);
  assert.equal(Object.keys(doc.paths).length, 15);
  const booking = doc.paths["/api/bookings"].post;
  assert.equal(
    booking.parameters.find((p) => p.name === "Idempotency-Key").required,
    true,
  );
  assert.deepEqual(
    booking.parameters.map((p) => [p.name, p.in]),
    [["Idempotency-Key", "header"]],
  );
  for (const status of ["200", "201", "202", "410"]) {
    const h = booking.responses[status].headers["X-Attempt-Expires-At"];
    assert.equal(h.required, true);
    assert.equal(h.schema.format, "date-time");
  }
  assert.equal(booking.responses["202"].headers["Retry-After"].required, true);
  for (const p of [
    "/api/admin/activities/{id}",
    "/api/admin/activities/{id}/weekly-windows",
    "/api/admin/activities/{id}/blocked-dates",
  ]) {
    const op = doc.paths[p].put ?? doc.paths[p].post;
    assert.equal(
      op.responses["200"].headers["X-Preserved-Booking-Count"].required,
      true,
    );
  }
  assert.equal(
    doc.paths["/api/activities/{slug}/slots"].get.parameters.find(
      (p) => p.name === "displayTimezone",
    ).required,
    false,
  );
  assert.deepEqual(
    doc,
    frozenDoc,
    "OpenAPI differs from the frozen API v1 surface",
  );
}
function checkFixtures(doc) {
  const booking = doc.paths["/api/bookings"].post;
  const ajv = new Ajv({
    strict: false,
    allErrors: true,
    validateFormats: true,
  });
  addFormats(ajv);
  const unknownFormats = new Set();
  function collect(v) {
    if (!v || typeof v !== "object") return;
    if (v.format && !ajv.formats[v.format]) unknownFormats.add(v.format);
    for (const x of Object.values(v)) collect(x);
  }
  collect(doc.components);
  for (const format of unknownFormats) {
    assert.ok(["int32"].includes(format), format);
    ajv.addFormat(format, {
      type: "number",
      validate: (n) =>
        Number.isInteger(n) && n >= -2147483648 && n <= 2147483647,
    });
  }
  let assertions = 0;
  function fixture(schema, value, valid = true) {
    const check = ajv.compile({ ...schema, components: doc.components });
    assert.equal(
      check(value),
      valid,
      "schema fixture " + (assertions + 1) + " failed",
    );
    assertions++;
  }
  const model = (name) => ({ $ref: "#/components/schemas/" + name });
  const response = (status) =>
    booking.responses[status].content["application/json"].schema;
  const id = "00000000-0000-4000-8000-000000000001",
    start = "2026-10-26T09:15:00Z",
    end = "2026-10-26T09:45:00Z";
  const request = {
    activityId: id,
    startsAt: start,
    attendeeName: "Synthetic Guest",
    attendeeEmail: "synthetic@example.test",
  };
  fixture(model("BookingRequest"), request);
  fixture(model("BookingRequest"), { ...request, endsAt: end }, false);
  fixture(model("BookingRequest"), { ...request, activityId: "wrong" }, false);
  fixture(
    model("BookingRequest"),
    { ...request, startsAt: "2026-10-26T09:15:00" },
    false,
  );
  fixture(model("BookingRequest"), { ...request, attendeeName: "  " }, false);
  fixture(
    model("BookingRequest"),
    { ...request, attendeeEmail: "invalid" },
    false,
  );
  fixture(
    model("BookingRequest"),
    { activityId: id, startsAt: start, attendeeName: "Synthetic" },
    false,
  );
  const summary = {
    id,
    activityId: id,
    startsAt: start,
    endsAt: end,
    status: "confirmed",
    canceledAt: null,
  };
  for (const status of ["200", "201"]) {
    fixture(response(status), summary);
    fixture(
      response(status),
      { ...summary, attendeeName: "Synthetic Guest" },
      false,
    );
    fixture(
      response(status),
      { ...summary, attendeeEmail: "synthetic@example.test" },
      false,
    );
    fixture(response(status), { ...summary, idempotencyKey: "private" }, false);
  }
  fixture(model("BookingSummary"), {
    ...summary,
    status: "canceled",
    canceledAt: start,
  });
  fixture(model("BookingSummary"), { ...summary, status: "pending" }, false);
  fixture(response("202"), { state: "pending", expiresAt: end });
  fixture(
    response("202"),
    { state: "pending", expiresAt: end, bookingId: id },
    false,
  );
  fixture(
    response("202"),
    {
      state: "pending",
      expiresAt: end,
      attendeeEmail: "synthetic@example.test",
    },
    false,
  );
  fixture(model("AdminBooking"), {
    ...summary,
    contact: {
      state: "present",
      attendeeName: "Synthetic Guest",
      attendeeEmail: "synthetic@example.test",
    },
  });
  fixture(model("AdminBooking"), { ...summary, contact: { state: "removed" } });
  fixture(
    model("AdminBooking"),
    {
      ...summary,
      contact: { state: "removed", attendeeName: "Synthetic Guest" },
    },
    false,
  );
  fixture(
    model("AdminBooking"),
    { ...summary, contact: { state: "present" } },
    false,
  );
  fixture(model("AdminBooking"), { ...summary, contact: null }, false);
  for (const code of [
    "slot_unavailable",
    "attempt_mismatch",
    "attempt_invalidated_by_restore",
  ]) {
    fixture(response("409"), { code, message: "Safe guidance" });
    fixture(
      response("409"),
      {
        code,
        message: "Safe guidance",
        fields: [
          { path: "attendeeName", code: "invalid", message: "unsafe context" },
        ],
      },
      false,
    );
    fixture(
      response("409"),
      { code, message: "Safe guidance", bookingId: id },
      false,
    );
  }
  fixture(response("410"), {
    code: "attempt_expired",
    message: "Contact the host if unknown.",
  });
  fixture(
    response("410"),
    { code: "attempt_invalidated_by_restore", message: "Wrong status" },
    false,
  );
  fixture(
    response("409"),
    { code: "attempt_expired", message: "Wrong status" },
    false,
  );
  for (const code of [
    "admission_unverified",
    "execution_unverified",
    "service_unavailable",
  ])
    fixture(response("503"), {
      code,
      message: "Preserve original key/details.",
    });
  fixture(response("400"), {
    code: "validation_failed",
    message: "Correct inputs",
    fields: [
      { path: "attendeeEmail", code: "invalid", message: "Use a valid email." },
    ],
  });
  fixture(
    response("400"),
    { code: "validation_failed", message: "Correct inputs", input: request },
    false,
  );
  fixture(model("NormalizedActivityDescription"), "A");
  fixture(model("NormalizedActivityDescription"), "😀".repeat(2000));
  fixture(model("NormalizedActivityDescription"), "", false);
  fixture(model("NormalizedActivityDescription"), "😀".repeat(2001), false);
  fixture(model("ActivityWrite"), {
    slug: "sample",
    title: "Sample",
    description: "  A  ",
    durationMinutes: 30,
    timezone: "Europe/Vienna",
    isActive: true,
  });
  fixture(model("WeeklyWindow"), {
    isoWeekday: 1,
    localStart: "09:10:00",
    localEnd: "10:00:00",
  });
  fixture(
    model("WeeklyWindow"),
    { isoWeekday: 8, localStart: "09:10:00", localEnd: "10:00:00" },
    false,
  );
  fixture(model("LocalClock"), "09:10");
  fixture(model("LocalClock"), "09:10:00.123456");
  fixture(model("LocalClock"), "09:10:00Z", false);
  fixture(model("LocalClock"), "09:10:00+01:00", false);
  fixture(model("LocalClock"), "24:00:00", false);
  fixture(model("ActivityDuration"), 30);
  fixture(model("ActivityDuration"), 16, false);
  fixture(model("ActivityDuration"), 0, false);
  assert.equal(
    doc.components.schemas.BookingRequest.additionalProperties,
    false,
  );
  assert.equal(
    doc.components.schemas.BookingSummary.additionalProperties,
    false,
  );
  assert.equal(
    doc.components.schemas.RemovedContacts.additionalProperties,
    false,
  );
  const key = `${id}.${"A".repeat(43)}`;
  fixture(model("BookingAttemptKey"), key);
  fixture(model("BookingAttemptKey"), key + "=", false);
  fixture(model("BookingAttemptKey"), "bad", false);
  // Additional final-review coverage: compile every declared response/request schema.
  for (const item of Object.values(doc.paths))
    for (const op of Object.values(item)) {
      for (const response of Object.values(op.responses))
        for (const media of Object.values(response.content ?? {}))
          ajv.compile({ ...media.schema, components: doc.components });
      for (const media of Object.values(op.requestBody?.content ?? {}))
        ajv.compile({ ...media.schema, components: doc.components });
    }
  fixture(model("AdminToken"), {
    accessToken: "synthetic-not-a-real-token",
    tokenType: "bearer",
    expiresAt: end,
  });
  fixture(
    model("AdminToken"),
    { accessToken: "synthetic-not-a-real-token", tokenType: "bearer" },
    false,
  );
  fixture(
    model("AdminToken"),
    {
      accessToken: "synthetic-not-a-real-token",
      tokenType: "bearer",
      expiresAt: end,
      refreshToken: "not-supported",
    },
    false,
  );
  fixture(model("AttemptContext"), { generation: id });
  fixture(model("AttemptContext"), { generation: id, bookingId: id }, false);
  fixture(
    doc.paths["/health"].get.responses["200"].content["application/json"]
      .schema,
    { status: "ok" },
  );
  fixture(
    doc.paths["/health"].get.responses["200"].content["application/json"]
      .schema,
    { status: "ok", connectionString: "not-allowed" },
    false,
  );
  fixture(
    doc.paths["/ready"].get.responses["200"].content["application/json"].schema,
    { status: "ready" },
  );
  fixture(
    doc.paths["/ready"].get.responses["200"].content["application/json"].schema,
    { status: "ready", overdueContacts: 1 },
    false,
  );
  const unauthorized =
    doc.paths["/api/admin/bookings"].get.responses["401"].content[
      "application/json"
    ].schema;
  fixture(unauthorized, {
    code: "unauthorized",
    message: "Authenticate again.",
  });
  fixture(
    unauthorized,
    {
      code: "unauthorized",
      message: "Authenticate again.",
      attendeeEmail: "synthetic@example.test",
    },
    false,
  );
  const cancel = doc.paths["/api/admin/bookings/{id}"].delete;
  assert.equal(cancel.responses["204"].content, undefined);
  assert.equal(
    cancel.responses["404"].content["application/json"].schema.properties.code
      .enum[0],
    "not_found",
  );
  assert.ok(cancel.description.includes("successful 204 no-op"));
  assert.ok(cancel.description.includes("original canceledAt"));
  const slots = doc.paths["/api/activities/{slug}/slots"].get;
  assert.ok(slots.description.includes("00/15/30/45"));
  assert.ok(slots.description.includes("both eligible repeated"));
  assert.ok(slots.description.includes("N+1h <= start <= N+1440h"));
  assert.equal(
    doc.components.schemas.BookingContact.discriminator.propertyName,
    "state",
  );
  assert.deepEqual(
    Object.keys(doc.components.schemas.BookingSummary.properties).sort(),
    ["id", "activityId", "startsAt", "endsAt", "status", "canceledAt"].sort(),
  );

  assertFixtureCount(assertions);
  return assertions;
}

function checkGuardRegressions(doc) {
  const mutations = [
    ["missing operation", (d) => delete d.paths["/ready"]],
    [
      "extra path",
      (d) => (d.paths["/unexpected"] = structuredClone(d.paths["/health"])),
    ],
    [
      "changed status",
      (d) => delete d.paths["/api/bookings"].post.responses["410"],
    ],
    [
      "changed operation ID",
      (d) => (d.paths["/health"].get.operationId = "Changed"),
    ],
    [
      "unprotected admin",
      (d) => (d.paths["/api/admin/bookings"].get.security = []),
    ],
    [
      "changed auth scheme",
      (d) => (d.components.securitySchemes.BearerAuth.scheme = "basic"),
    ],
    [
      "missing no-store",
      (d) =>
        delete d.paths["/health"].get.responses["200"].headers["Cache-Control"],
    ],
    [
      "missing expiry header",
      (d) =>
        delete d.paths["/api/bookings"].post.responses["201"].headers[
          "X-Attempt-Expires-At"
        ],
    ],
    [
      "missing retry header",
      (d) =>
        delete d.paths["/api/bookings"].post.responses["202"].headers[
          "Retry-After"
        ],
    ],
    [
      "optional key",
      (d) => (d.paths["/api/bookings"].post.parameters[0].required = false),
    ],
  ];
  for (const [label, mutate] of mutations) {
    const changed = structuredClone(doc);
    mutate(changed);
    assert.throws(() => checkSurface(changed), undefined, label + " must fail");
  }
  for (const schema of [
    "BookingSummary",
    "RemovedContacts",
    "AttemptPending",
  ]) {
    const changed = structuredClone(doc);
    changed.components.schemas[schema].additionalProperties = true;
    assert.throws(
      () => checkFixtures(changed),
      undefined,
      schema + " must reject extra private fields",
    );
  }
  assert.throws(
    () => assertFixtureCount(0),
    undefined,
    "zero fixtures must fail",
  );
  for (const file of frozenFiles) {
    const bytes = frozenBytes(file);
    assert.throws(() =>
      sameBytes(
        Buffer.concat([bytes, Buffer.from("\n// drift\n")]),
        bytes,
        file,
      ),
    );
    assert.throws(() => sameBytes(Buffer.alloc(0), bytes, file));
  }
  console.log(
    "PASS: 20 negative guard regressions (surface/security/headers/privacy/zero fixtures/byte drift).",
  );
}

async function main() {
  assert.ok(
    Number(process.versions.node.split(".")[0]) >= 22,
    "Node 22 or newer is required (approved runtime: Node 22)",
  );
  const contractRequire = createRequire(
    path.join(root, "contracts/package.json"),
  );
  const frontendRequire = createRequire(
    path.join(root, "frontend/package.json"),
  );
  try {
    ({ parse } = contractRequire("yaml"));
    Ajv = contractRequire("ajv");
    addFormats = contractRequire("ajv-formats");
    ({ lint, createConfig } = frontendRequire("@redocly/openapi-core"));
  } catch {
    throw new Error(
      "Missing locked tooling; run npm --prefix contracts ci and npm --prefix frontend ci",
    );
  }
  frozenDoc = parse(frozenBytes(frozenFiles[1]).toString("utf8"));
  const original = new Map(
    frozenFiles.map((file) => [file, fs.readFileSync(path.join(root, file))]),
  );
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "slotbook-contract-"));
  try {
    // Same declared build command, with output redirected away from frozen tracked artifacts.
    run("npm", [
      "--prefix",
      "contracts",
      "run",
      "build",
      "--",
      "--output-dir",
      path.join(scratch, "tsp-output"),
      "--warn-as-error",
    ]);
    const generatedOpenapi = path.join(
      scratch,
      "tsp-output/@typespec/openapi3/openapi.yaml",
    );
    const doc = parse(fs.readFileSync(generatedOpenapi, "utf8"));
    const config = await createConfig({
      rules: {
        struct: "error",
        "no-unresolved-refs": "error",
        "operation-operationId-unique": "error",
        "operation-parameters-unique": "error",
        "path-parameters-defined": "error",
        "security-defined": "error",
      },
    });
    const problems = await lint({ ref: generatedOpenapi, config });
    assert.equal(
      problems.length,
      0,
      "OpenAPI lint failed: " + problems.map((p) => p.ruleId).join(", "),
    );
    checkSurface(doc);
    const fixtureCount = checkFixtures(doc);
    console.log(
      "PASS: TypeSpec compile; OpenAPI structure/references; 18 operation/status/security/header matrices; " +
        fixtureCount +
        " schema fixtures.",
    );
    const generatedTypes = path.join(scratch, "schema.d.ts");
    run(process.execPath, [
      path.join(root, "frontend/node_modules/openapi-typescript/bin/cli.js"),
      generatedOpenapi,
      "--output",
      generatedTypes,
    ]);
    fs.writeFileSync(path.join(scratch, "types-check.ts"), TYPE_FIXTURES);
    run(process.execPath, [
      path.join(root, "frontend/node_modules/typescript/bin/tsc"),
      "--noEmit",
      "--strict",
      "--skipLibCheck",
      "false",
      "--target",
      "ES2022",
      "--module",
      "ESNext",
      "--moduleResolution",
      "Bundler",
      path.join(scratch, "types-check.ts"),
    ]);
    sameBytes(
      fs.readFileSync(generatedOpenapi),
      original.get(frozenFiles[1]),
      "Generated OpenAPI",
    );
    sameBytes(
      fs.readFileSync(generatedTypes),
      original.get(frozenFiles[2]),
      "Generated TypeScript",
    );
    for (const file of frozenFiles) {
      sameBytes(
        fs.readFileSync(path.join(root, file)),
        original.get(file),
        "Input changed during verification: " + file,
      );
      sameBytes(
        original.get(file),
        frozenBytes(file),
        "Frozen API v1: " + file,
      );
    }
    // Explicit commit-relative diff includes staged and unstaged drift, even if HEAD moved.
    run("git", ["diff", "--exit-code", baseline, "--", ...frozenFiles]);
    if (selfTest.length) checkGuardRegressions(doc);
    console.log(
      "PASS: generated TypeScript positive/expected-negative checks; byte-for-byte regeneration; git diff --exit-code against frozen API v1 (all three files).",
    );
    console.log(
      "Runtime behavior, T-02 concurrency/crash/idempotency and T-03 privacy/hosting remain unverified by this static gate.",
    );
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}

const TYPE_FIXTURES = `import type {components, operations} from './schema';
type Request = components['schemas']['BookingRequest'];
type Summary = components['schemas']['BookingSummary'];
const request: Request = {activityId:'synthetic',startsAt:'2026-10-26T09:15:00Z',attendeeName:'Synthetic Guest',attendeeEmail:'synthetic@example.test'};
const badRequest: Request = {...request,
  // @ts-expect-error the server owns endsAt
  endsAt:'2026-10-26T09:45:00Z'};
const summary: Summary = {id:'synthetic',activityId:'synthetic',startsAt:'2026-10-26T09:15:00Z',endsAt:'2026-10-26T09:45:00Z',status:'confirmed',canceledAt:null};
const badSummary: Summary = {...summary,
  // @ts-expect-error public booking confirmations cannot contain contacts
  attendeeEmail:'synthetic@example.test'};
declare const booking: components['schemas']['AdminBooking'];
if (booking.contact.state === 'present') {
  const contact: string = booking.contact.attendeeEmail;
} else {
  // @ts-expect-error contact-removed history has no attendee properties
  booking.contact.attendeeEmail;
}
type Pending = operations['Bookings_create']['responses'][202];
const pending: Pending['content']['application/json'] = {state:'pending',expiresAt:'2026-10-27T09:00:00Z'};
const badPending: Pending['content']['application/json'] = {...pending,
  // @ts-expect-error pending is not confirmation
  bookingId:'synthetic'};
type Expired = operations['Bookings_create']['responses'][410]['content']['application/json'];
const expired: Expired = {code:'attempt_expired',message:'Verify unknown outcome with the host.'};
const wrongStatus: Expired = {
  // @ts-expect-error restore invalidation belongs to 409, not 410
  code:'attempt_invalidated_by_restore',message:'Unknown'};

type Protected = operations['Admin_listBookings']['responses'][401]['content']['application/json'];
const unauthorized: Protected = {code:'unauthorized',message:'Authenticate again.'};
const unsafeError: Protected = {...unauthorized,
  // @ts-expect-error error bodies cannot contain guest contacts
  attendeeEmail:'synthetic@example.test'};
const extraSummary: Summary = {...summary,
  // @ts-expect-error public results cannot expose retry credentials
  idempotencyKey:'synthetic'};
// @ts-expect-error pending responses require expiresAt
const incompletePending: Pending['content']['application/json'] = {state:'pending'};
type NoBody = operations['Admin_cancelBooking']['responses'][204];
// @ts-expect-error cancellation success has no JSON body
const cancellationBody: NoBody['content']['application/json'] = {};
`;

await main().catch((error) => {
  console.error("FAIL: " + error.message);
  process.exitCode = 1;
});
