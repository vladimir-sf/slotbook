import { expect as playwrightExpect, test, type Page, type Route } from "@playwright/test";
import type { components, operations } from "../src/api/schema.js";
import { activity, slot } from "./fixtures/api.js";

// T027: synthetic API v1 fixtures only. Interception lives exclusively in tests.
// Typecheck this file explicitly as well as running the existing typecheck script:
// tsc --noEmit --strict --target ES2022 --module ESNext --moduleResolution Bundler
//     --esModuleInterop --skipLibCheck --types node tests/catalog.spec.ts
const expect = playwrightExpect.configure({ timeout: 1500 });
type Activity = components["schemas"]["Activity"];
type Slot = components["schemas"]["Slot"];
type Read = "Activities_list" | "Activities_detail" | "Activities_slots";
type Body<O extends Read, S extends keyof operations[O]["responses"]> =
  operations[O]["responses"][S] extends { content: { "application/json": infer T } } ? T : never;

const second = {
  ...activity, id: "55555555-5555-4555-8555-555555555555",
  slug: "second-appointment", title: "Second appointment", durationMinutes: 45,
} satisfies Activity;
const fullDescription = `${activity.description}\n<img src=x onerror="window.fixtureMarkupExecuted=true">\n  Internal spaces remain. 👋`;
const currentActivity = { ...activity, description: fullDescription } satisfies Activity;
const offered = [
  { ...slot, startsAt: "2026-11-02T08:15:00Z", endsAt: "2026-11-02T08:45:00Z" },
  { ...slot, startsAt: "2026-11-02T08:30:00Z", endsAt: "2026-11-02T09:00:00Z" },
] satisfies Slot[];

function reply<O extends Read, S extends keyof operations[O]["responses"]>(
  route: Route, operation: O, status: S, body: Body<O, S>,
) {
  void operation;
  return route.fulfill({
    status: Number(status),
    headers: { "Cache-Control": "no-store", "Access-Control-Allow-Origin": "*" },
    json: body,
  });
}

type Handler = (route: Route, url: URL) => Promise<void>;
async function intercept(page: Page, handlers: Partial<Record<Read, Handler>> = {}) {
  const calls: { operation: Read; url: URL; method: string; authorization: string | null }[] = [];
  const unexpected: string[] = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    // Vite module URLs such as /src/api/client.ts are application code, not API traffic.
    if (!url.pathname.startsWith("/api/")) return route.fallback();
    const operation: Read | undefined = url.pathname === "/api/activities" ? "Activities_list"
      : /^\/api\/activities\/[^/]+\/slots$/.test(url.pathname) ? "Activities_slots"
      : /^\/api\/activities\/[^/]+$/.test(url.pathname) ? "Activities_detail" : undefined;
    if (!operation || request.method() !== "GET") {
      unexpected.push("unexpected-api-operation");
      return route.abort();
    }
    calls.push({ operation, url, method: request.method(), authorization: await request.headerValue("authorization") });
    const override = handlers[operation];
    if (override) return override(route, url);
    if (operation === "Activities_list") return reply(route, operation, 200, [activity, second]);
    if (operation === "Activities_slots") return reply(route, operation, 200, offered);
    const slug = decodeURIComponent(url.pathname.split("/").at(-1)!);
    return reply(route, "Activities_detail", 200, slug === second.slug ? second : currentActivity);
  });
  return { calls, unexpected };
}

function gate() {
  let release!: () => void;
  const waiting = new Promise<void>((resolve) => { release = resolve; });
  return { waiting, release };
}

async function openActivity(page: Page, title = activity.title) {
  await expect(page.getByRole("heading", { name: "Choose an appointment", exact: true })).toBeVisible();
  await page.getByRole("button", { name: `View ${title}`, exact: true }).click();
  await expect(page.getByRole("region", { name: "Appointment details", exact: true })).toBeVisible();
}

async function chooseDate(page: Page, date = "2026-11-02") {
  const input = page.getByLabel("Appointment date", { exact: true });
  await expect(input).toBeVisible();
  await input.fill(date);
}

test.describe("T031 catalog and detail", () => {
  test("renders the public catalog from the API with descriptions and durations", async ({ page }) => {
    const api = await intercept(page);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Choose an appointment", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: `View ${activity.title}`, exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: `View ${second.title}`, exact: true })).toBeVisible();
    await expect(page.getByText("30 minutes", { exact: true })).toBeVisible();
    const offering = page.getByRole("article").filter({ has: page.getByRole("button", { name: `View ${activity.title}`, exact: true }) });
    await expect(offering.getByText(activity.description, { exact: true })).toBeVisible();
    expect(api.calls.some((call) => call.operation === "Activities_list")).toBe(true);
  });

  test("distinguishes an empty successful catalog from a failure", async ({ page }) => {
    await intercept(page, { Activities_list: (route) => reply(route, "Activities_list", 200, []) });
    await page.goto("/");
    await expect(page.getByText("No appointment types are available.", { exact: true })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^View / })).toHaveCount(0);
  });

  test("shows catalog loading while the request is unfinished", async ({ page }) => {
    const pending = gate();
    await intercept(page, { Activities_list: async (route) => { await pending.waiting; await reply(route, "Activities_list", 200, [activity]); } });
    try {
      await page.goto("/");
      await expect(page.getByText("Loading appointment types…", { exact: true })).toBeVisible();
      await expect(page.getByText("No appointment types are available.", { exact: true })).toHaveCount(0);
    } finally { pending.release(); }
    await expect(page.getByRole("button", { name: `View ${activity.title}`, exact: true })).toBeVisible();
  });

  for (const failure of [500, 503, "network", "invalid-json", "invalid-shape"] as const) {
    test(`catalog ${failure} has safe failure feedback and no false empty state`, async ({ page }) => {
      await intercept(page, { Activities_list: async (route) => {
        if (failure === "network") return route.abort("failed");
        if (failure === "invalid-json") return route.fulfill({ status: 200, contentType: "application/json", body: "{" });
        if (failure === "invalid-shape") return route.fulfill({ status: 200, json: { unsafe: "UNSAFE_SERVER_DETAIL" } });
        return reply(route, "Activities_list", failure, { code: failure === 500 ? "internal_error" : "service_unavailable", message: "UNSAFE_SERVER_DETAIL" });
      } });
      await page.goto("/");
      await expect(page.getByRole("alert")).toContainText("Could not load appointment types.");
      await expect(page.getByRole("button", { name: "Try again", exact: true })).toBeVisible();
      await expect(page.getByText("No appointment types are available.", { exact: true })).toHaveCount(0);
      await expect(page.getByText("UNSAFE_SERVER_DETAIL", { exact: true })).toHaveCount(0);
    });
  }

  test("retries a failed catalog read explicitly", async ({ page }) => {
    let failing = true;
    await intercept(page, { Activities_list: (route) => failing
      ? reply(route, "Activities_list", 503, { code: "service_unavailable", message: "Unavailable." })
      : reply(route, "Activities_list", 200, [activity]) });
    await page.goto("/");
    await expect(page.getByRole("alert")).toContainText("Could not load appointment types.");
    failing = false;
    await page.getByRole("button", { name: "Try again", exact: true }).click();
    await expect(page.getByRole("button", { name: `View ${activity.title}`, exact: true })).toBeVisible();
  });

  test("fetches current detail and renders full multiline markup literally", async ({ page }) => {
    const api = await intercept(page);
    await page.goto("/");
    await openActivity(page);
    const description = page.getByTestId("activity-description");
    await expect(description).toHaveText(fullDescription);
    expect(await description.textContent()).toBe(fullDescription);
    expect(await description.evaluate((element) => getComputedStyle(element).whiteSpace)).toBe("pre-wrap");
    await expect(description.locator("img, script, b")).toHaveCount(0);
    expect(await page.evaluate(() => Object.hasOwn(window, "fixtureMarkupExecuted"))).toBe(false);
    expect(api.calls.some((call) => call.operation === "Activities_detail" && call.url.pathname.endsWith(activity.slug))).toBe(true);
  });

  test("shows detail loading rather than stale catalog text", async ({ page }) => {
    const pending = gate();
    await intercept(page, { Activities_detail: async (route) => { await pending.waiting; await reply(route, "Activities_detail", 200, currentActivity); } });
    try {
      await page.goto("/"); await openActivity(page);
      await expect(page.getByText("Loading appointment details…", { exact: true })).toBeVisible();
      await expect(page.getByTestId("activity-description")).toHaveCount(0);
    } finally { pending.release(); }
  });

  test("a missing or inactive activity is unavailable and permits another choice", async ({ page }) => {
    await intercept(page, { Activities_detail: (route) => reply(route, "Activities_detail", 404, { code: "not_found", message: "Unavailable." }) });
    await page.goto("/"); await openActivity(page);
    await expect(page.getByRole("alert")).toContainText("This appointment is unavailable.");
    await page.getByRole("button", { name: "Back to appointment types", exact: true }).click();
    await expect(page.getByRole("button", { name: `View ${second.title}`, exact: true })).toBeVisible();
  });

  for (const status of [500, 503] as const) {
    test(`detail ${status} is safe and can be retried without losing context`, async ({ page }) => {
      let failing = true;
      await intercept(page, { Activities_detail: (route) => failing
        ? reply(route, "Activities_detail", status, { code: status === 500 ? "internal_error" : "service_unavailable", message: "UNSAFE_SERVER_DETAIL" })
        : reply(route, "Activities_detail", 200, currentActivity) });
      await page.goto("/"); await openActivity(page);
      await expect(page.getByRole("alert")).toContainText("Could not load appointment details.");
      await expect(page.getByText("UNSAFE_SERVER_DETAIL", { exact: true })).toHaveCount(0);
      failing = false;
      await page.getByRole("button", { name: "Try again", exact: true }).click();
      await expect(page.getByRole("heading", { name: activity.title, exact: true })).toBeVisible();
    });
  }

  test("switching activities cannot display a late response for the old choice", async ({ page }) => {
    const pending = gate();
    await intercept(page, { Activities_detail: async (route, url) => {
      if (url.pathname.endsWith(activity.slug)) { await pending.waiting; await reply(route, "Activities_detail", 200, currentActivity); }
      else await reply(route, "Activities_detail", 200, second);
    } });
    try {
      await page.goto("/"); await openActivity(page);
      await expect(page.getByText("Loading appointment details…", { exact: true })).toBeVisible();
      await page.getByRole("button", { name: "Back to appointment types", exact: true }).click();
      await openActivity(page, second.title);
      await expect(page.getByRole("heading", { name: second.title, exact: true })).toBeVisible();
    } finally { pending.release(); }
    await expect(page.getByRole("heading", { name: activity.title, exact: true })).toHaveCount(0);
  });

  test("retains selected activity context across reload without storing credentials", async ({ page }) => {
    const api = await intercept(page);
    await page.goto("/"); await openActivity(page);
    await expect(page.getByRole("heading", { name: activity.title, exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: activity.title, exact: true })).toBeVisible();
    expect(api.unexpected).toEqual([]);
    expect(api.calls.every((call) => call.method === "GET" && call.authorization === null)).toBe(true);
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    expect(await page.context().cookies()).toEqual([]);
  });
});

test.describe("T032 date and slot discovery", () => {
  test("queries the selected display date and preserves the exact returned UTC choice", async ({ page }) => {
    const api = await intercept(page);
    await page.goto("/"); await openActivity(page); await chooseDate(page);
    const options = page.getByRole("group", { name: "Available slots", exact: true }).getByRole("button");
    await expect(options).toHaveCount(2);
    expect(await options.evaluateAll((buttons) => buttons.map((button) => (button as HTMLButtonElement).value))).toEqual(offered.map((value) => value.startsAt));
    await options.first().click();
    await expect(options.first()).toHaveAttribute("aria-pressed", "true");
    const selected = page.getByRole("region", { name: "Selected time", exact: true });
    await expect(selected.locator("time").first()).toHaveAttribute("datetime", offered[0].startsAt);
    await expect(selected.locator("time").last()).toHaveAttribute("datetime", offered[0].endsAt);
    const request = api.calls.find((call) => call.operation === "Activities_slots")!;
    expect(request.url.searchParams.get("date")).toBe("2026-11-02");
    expect(request.url.searchParams.get("displayTimezone")).toBe("Europe/Vienna");
    await expect(page.getByText("Selecting a time does not reserve it.", { exact: true })).toBeVisible();
    expect(api.unexpected).toEqual([]);
    expect(api.calls.every((call) => call.method === "GET")).toBe(true);
    await expect(page.getByRole("textbox")).toHaveCount(0);
  });

  test("does not request slots until a date is selected", async ({ page }) => {
    const api = await intercept(page);
    await page.goto("/"); await openActivity(page);
    await expect(page.getByText("Choose a date to see available times.", { exact: true })).toBeVisible();
    expect(api.calls.filter((call) => call.operation === "Activities_slots")).toHaveLength(0);
  });

  test("empty server availability allows a different date without inventing slots", async ({ page }) => {
    await intercept(page, { Activities_slots: (route, url) => reply(route, "Activities_slots", 200,
      url.searchParams.get("date") === "2026-11-02" ? [] : offered) });
    await page.goto("/"); await openActivity(page); await chooseDate(page);
    await expect(page.getByText("No available times for this date. Choose another date.", { exact: true })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await chooseDate(page, "2026-11-03");
    await expect(page.getByRole("group", { name: "Available slots", exact: true }).getByRole("button")).toHaveCount(2);
  });

  test("keeps loading distinct from no availability", async ({ page }) => {
    const pending = gate();
    await intercept(page, { Activities_slots: async (route) => { await pending.waiting; await reply(route, "Activities_slots", 200, offered); } });
    try {
      await page.goto("/"); await openActivity(page); await chooseDate(page);
      await expect(page.getByText("Loading available times…", { exact: true })).toBeVisible();
      await expect(page.getByText("No available times for this date. Choose another date.", { exact: true })).toHaveCount(0);
    } finally { pending.release(); }
  });

  for (const failure of [400, 404, 500, 503, "network", "invalid-shape"] as const) {
    test(`slot ${failure} does not masquerade as empty availability`, async ({ page }) => {
      await intercept(page, { Activities_slots: (route) => {
        if (failure === "network") return route.abort("failed");
        if (failure === "invalid-shape") return route.fulfill({ status: 200, json: [{ startsAt: slot.startsAt, attendeeEmail: "synthetic@example.invalid" }] });
        if (failure === 400) return reply(route, "Activities_slots", 400, { code: "validation_failed", message: "UNSAFE_SERVER_DETAIL" });
        if (failure === 404) return reply(route, "Activities_slots", 404, { code: "not_found", message: "UNSAFE_SERVER_DETAIL" });
        return reply(route, "Activities_slots", failure, { code: failure === 500 ? "internal_error" : "service_unavailable", message: "UNSAFE_SERVER_DETAIL" });
      } });
      await page.goto("/"); await openActivity(page); await chooseDate(page);
      await expect(page.getByRole("alert")).toBeVisible();
      await expect(page.getByText("No available times for this date. Choose another date.", { exact: true })).toHaveCount(0);
      await expect(page.getByText("UNSAFE_SERVER_DETAIL", { exact: true })).toHaveCount(0);
      await expect(page.getByRole("group", { name: "Available slots", exact: true })).toHaveCount(0);
      await expect(page.getByLabel("Appointment date", { exact: true })).toHaveValue("2026-11-02");
    });
  }

  test("explicit retry keeps the date and original activity", async ({ page }) => {
    let failing = true;
    const api = await intercept(page, { Activities_slots: (route) => failing
      ? reply(route, "Activities_slots", 503, { code: "service_unavailable", message: "Unavailable." })
      : reply(route, "Activities_slots", 200, offered) });
    await page.goto("/"); await openActivity(page); await chooseDate(page);
    await expect(page.getByRole("alert")).toContainText("Could not load available times.");
    failing = false;
    await page.getByRole("button", { name: "Try again", exact: true }).click();
    await expect(page.getByRole("group", { name: "Available slots", exact: true }).getByRole("button")).toHaveCount(2);
    expect(api.calls.filter((call) => call.operation === "Activities_slots").every((call) => call.url.searchParams.get("date") === "2026-11-02" && call.url.pathname.includes(activity.slug))).toBe(true);
  });

  test("retains the date across reload and choosing another activity", async ({ page }) => {
    await intercept(page);
    await page.goto("/"); await openActivity(page); await chooseDate(page);
    await page.reload();
    await expect(page.getByLabel("Appointment date", { exact: true })).toHaveValue("2026-11-02");
    await page.getByRole("button", { name: "Back to appointment types", exact: true }).click();
    await openActivity(page, second.title);
    await expect(page.getByRole("heading", { name: second.title, exact: true })).toBeVisible();
    await expect(page.getByLabel("Appointment date", { exact: true })).toHaveValue("2026-11-02");
  });

  test("changing date clears the old selection and ignores late old responses", async ({ page }) => {
    const pending = gate();
    await intercept(page, { Activities_slots: async (route, url) => {
      if (url.searchParams.get("date") === "2026-11-03") { await pending.waiting; await reply(route, "Activities_slots", 200, []); }
      else await reply(route, "Activities_slots", 200, offered);
    } });
    try {
      await page.goto("/"); await openActivity(page); await chooseDate(page);
      const options = page.getByRole("group", { name: "Available slots", exact: true }).getByRole("button");
      await expect(options).toHaveCount(2); await options.first().click();
      await chooseDate(page, "2026-11-03");
      await expect(page.getByRole("region", { name: "Selected time", exact: true })).toHaveCount(0);
      await expect(page.getByText("Loading available times…", { exact: true })).toBeVisible();
      await chooseDate(page, "2026-11-04");
      await expect(options).toHaveCount(2);
    } finally { pending.release(); }
    await expect(page.getByLabel("Appointment date", { exact: true })).toHaveValue("2026-11-04");
    await expect(page.getByRole("group", { name: "Available slots", exact: true }).getByRole("button")).toHaveCount(2);
  });

  test("both repeated local labels retain distinct UTC identities and offsets", async ({ page }) => {
    const repeated = [
      { startsAt: "2026-10-25T00:15:00Z", endsAt: "2026-10-25T00:45:00Z" },
      { startsAt: "2026-10-25T01:15:00Z", endsAt: "2026-10-25T01:45:00Z" },
    ] satisfies Slot[];
    await intercept(page, { Activities_slots: (route) => reply(route, "Activities_slots", 200, repeated) });
    await page.goto("/"); await openActivity(page); await chooseDate(page, "2026-10-25");
    const options = page.getByRole("group", { name: "Available slots", exact: true }).getByRole("button");
    await expect(options).toHaveCount(2);
    await expect(options.nth(0)).toContainText("GMT+2");
    await expect(options.nth(1)).toContainText("GMT+1");
    await options.nth(1).click();
    await expect(page.getByRole("region", { name: "Selected time", exact: true }).locator("time").first()).toHaveAttribute("datetime", repeated[1].startsAt);
  });

  test("core discovery controls fit a narrow viewport", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await intercept(page);
    await page.goto("/"); await openActivity(page); await chooseDate(page);
    await expect(page.getByRole("group", { name: "Available slots", exact: true }).getByRole("button").first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
});
