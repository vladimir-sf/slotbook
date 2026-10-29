import type { operations } from "./schema";

export type Activity = operations["Activities_detail"]["responses"][200]["content"]["application/json"];
export type Slot = operations["Activities_slots"]["responses"][200]["content"]["application/json"][number];
export type SlotQuery = operations["Activities_slots"]["parameters"]["query"];
type PublicRead = "Activities_list" | "Activities_detail" | "Activities_slots";
type Success<O extends PublicRead> = operations[O]["responses"][200]["content"]["application/json"];

export class ApiFailure extends Error {
  constructor(public readonly kind: "unavailable" | "not-found" | "invalid-request" | "invalid-response") {
    super("The requested information could not be loaded.");
    this.name = "ApiFailure";
  }
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// These guards check the consumed representation, including unexpected fields.
// Eligibility, schedule rules and input-policy validation remain server-owned.
function isActivity(value: unknown): value is Activity {
  const keys = ["id", "slug", "title", "description", "durationMinutes", "timezone", "isActive"] satisfies (keyof Activity)[];
  return object(value) && Object.keys(value).every((key) => keys.some((allowed) => allowed === key))
    && typeof value.id === "string" && typeof value.slug === "string"
    && typeof value.title === "string" && typeof value.description === "string"
    && typeof value.timezone === "string" && typeof value.isActive === "boolean"
    && typeof value.durationMinutes === "number" && Number.isFinite(value.durationMinutes);
}

function isActivityList(value: unknown): value is Success<"Activities_list"> {
  return Array.isArray(value) && value.every(isActivity);
}

function utcInstant(value: unknown): value is string {
  return typeof value === "string" && value.endsWith("Z") && Number.isFinite(Date.parse(value));
}

function isSlotList(value: unknown): value is Success<"Activities_slots"> {
  const keys = ["startsAt", "endsAt"] satisfies (keyof Slot)[];
  return Array.isArray(value) && value.every((item: unknown) => object(item)
    && Object.keys(item).every((key) => keys.some((allowed) => allowed === key))
    && utcInstant(item.startsAt) && utcInstant(item.endsAt));
}

async function read<O extends PublicRead>(
  operation: O, path: string, valid: (value: unknown) => value is Success<O>, signal?: AbortSignal,
): Promise<Success<O>> {
  try {
    // T008 supplies the public origin at build time. Local Vite development has
    // a conventional real-API default; there is no fixture/mock transport here.
    const origin = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");
    const base = new URL(origin);
    if (!["http:", "https:"].includes(base.protocol) || base.origin !== origin || base.username || base.password) {
      throw new ApiFailure("unavailable");
    }
    const response = await fetch(new URL(path, base), {
      method: "GET", headers: { Accept: "application/json" },
      credentials: "omit", cache: "no-store", redirect: "error", signal,
    });
    if (response.status !== 200) {
      if (response.status === 404 && operation !== "Activities_list") throw new ApiFailure("not-found");
      if (response.status === 400 && operation === "Activities_slots") throw new ApiFailure("invalid-request");
      throw new ApiFailure("unavailable");
    }
    const body: unknown = await response.json();
    if (!valid(body)) throw new ApiFailure("invalid-response");
    return body;
  } catch (error) {
    if (signal?.aborted) throw error;
    if (error instanceof ApiFailure) throw error;
    // Never expose response bodies, framework validation details or transport errors.
    throw new ApiFailure("unavailable");
  }
}

export function listActivities(signal?: AbortSignal) {
  return read("Activities_list", "/api/activities", isActivityList, signal);
}

export function getActivity(slug: string, signal?: AbortSignal) {
  return read("Activities_detail", `/api/activities/${encodeURIComponent(slug)}`, isActivity, signal);
}

export function getSlots(slug: string, query: SlotQuery, signal?: AbortSignal) {
  const params = new URLSearchParams({ date: query.date });
  if (query.displayTimezone !== undefined) params.set("displayTimezone", query.displayTimezone);
  return read("Activities_slots", `/api/activities/${encodeURIComponent(slug)}/slots?${params}`, isSlotList, signal);
}
