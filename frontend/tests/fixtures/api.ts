import type { components, operations } from "../../src/api/schema.js";

// Synthetic, test-only API v1 data. These types come from the frozen generated
// declarations; none of these fixtures is an application API or live credential.
export const activity = {
  id: "11111111-1111-4111-8111-111111111111",
  slug: "synthetic-consultation",
  title: "Synthetic consultation",
  description: "A synthetic appointment.\nLiteral <b>text</b> and international text: Grüß dich 👋",
  durationMinutes: 30,
  timezone: "Europe/Vienna",
  isActive: true,
} satisfies components["schemas"]["Activity"];

export const slot = {
  startsAt: "2026-11-02T09:00:00Z",
  endsAt: "2026-11-02T09:30:00Z",
} satisfies components["schemas"]["Slot"];

export const booking = {
  id: "22222222-2222-4222-8222-222222222222",
  activityId: activity.id,
  ...slot,
  status: "confirmed",
  canceledAt: null,
} satisfies components["schemas"]["BookingSummary"];

export const bookingRequest = {
  activityId: activity.id,
  startsAt: slot.startsAt,
  attendeeName: "Synthetic Guest",
  attendeeEmail: "synthetic-guest@example.invalid",
} satisfies operations["Bookings_create"]["requestBody"]["content"]["application/json"];

export const removedBooking = {
  ...booking,
  contact: { state: "removed" },
} satisfies components["schemas"]["AdminBooking"];

export const presentBooking = {
  ...booking,
  contact: {
    state: "present",
    attendeeName: bookingRequest.attendeeName,
    attendeeEmail: bookingRequest.attendeeEmail,
  },
} satisfies components["schemas"]["AdminBooking"];

export const weeklyWindows = [
  { isoWeekday: 1, localStart: "09:10:00.125", localEnd: "10:00" },
] satisfies components["schemas"]["WeeklyWindow"][];
export const blockedDate = { date: "2026-11-03" } satisfies components["schemas"]["BlockedDate"];
export const attemptContext = {
  generation: "33333333-3333-4333-8333-333333333333",
} satisfies components["schemas"]["AttemptContext"];

const noStore = { "Cache-Control": "no-store" } as const;
const admitted = { ...noStore, "X-Attempt-Expires-At": "2026-11-02T08:00:00Z" };
const preserved = { ...noStore, "X-Preserved-Booking-Count": 1 };

// A test descriptor wraps the actual generated response type, including headers.
// It does not define a parallel body DTO or a private wire format.
function fixture<O extends keyof operations, S extends keyof operations[O]["responses"]>(
  id: string, operationId: O, status: S, response: operations[O]["responses"][S],
) {
  return { id, operationId, status, response };
}

export const responseFixtures = [
  fixture("catalog", "Activities_list", 200, { headers: noStore, content: { "application/json": [activity] } }),
  fixture("empty-catalog", "Activities_list", 200, { headers: noStore, content: { "application/json": [] } }),
  fixture("detail", "Activities_detail", 200, { headers: noStore, content: { "application/json": activity } }),
  fixture("missing-activity", "Activities_detail", 404, { headers: noStore, content: { "application/json": { code: "not_found", message: "Activity unavailable." } } }),
  fixture("slots", "Activities_slots", 200, { headers: noStore, content: { "application/json": [slot] } }),
  fixture("empty-slots", "Activities_slots", 200, { headers: noStore, content: { "application/json": [] } }),
  fixture("context", "BookingAttempts_getContext", 200, { headers: noStore, content: { "application/json": attemptContext } }),
  fixture("created", "Bookings_create", 201, { headers: admitted, content: { "application/json": booking } }),
  fixture("replayed-canceled", "Bookings_create", 200, { headers: admitted, content: { "application/json": { ...booking, status: "canceled", canceledAt: "2026-11-01T10:00:00Z" } } }),
  fixture("pending", "Bookings_create", 202, { headers: { ...admitted, "Retry-After": 2 }, content: { "application/json": { state: "pending", expiresAt: admitted["X-Attempt-Expires-At"] } } }),
  fixture("validation", "Bookings_create", 400, { headers: noStore, content: { "application/json": { code: "validation_failed", message: "Correct the indicated field.", fields: [{ path: "attendeeEmail", code: "invalid", message: "Enter a valid email." }] } } }),
  fixture("slot-conflict", "Bookings_create", 409, { headers: admitted, content: { "application/json": { code: "slot_unavailable", message: "Choose another slot." } } }),
  fixture("mismatch", "Bookings_create", 409, { headers: admitted, content: { "application/json": { code: "attempt_mismatch", message: "Use the original details." } } }),
  fixture("restore-invalidated", "Bookings_create", 409, { headers: noStore, content: { "application/json": { code: "attempt_invalidated_by_restore", message: "Outcome unverified. Contact the host." } } }),
  fixture("expired", "Bookings_create", 410, { headers: admitted, content: { "application/json": { code: "attempt_expired", message: "Contact the host to verify the outcome." } } }),
  fixture("admission-unverified", "Bookings_create", 503, { headers: noStore, content: { "application/json": { code: "admission_unverified", message: "Outcome unverified." } } }),
  fixture("execution-unverified", "Bookings_create", 503, { headers: admitted, content: { "application/json": { code: "execution_unverified", message: "Outcome unverified." } } }),
  fixture("internal-error", "Bookings_create", 500, { headers: noStore, content: { "application/json": { code: "internal_error", message: "Outcome unverified." } } }),
  fixture("login", "Auth_login", 200, { headers: noStore, content: { "application/json": { accessToken: "synthetic-test-only-not-a-live-token", tokenType: "bearer", expiresAt: "2026-11-01T10:00:00Z" } } }),
  fixture("unauthorized", "Auth_login", 401, { headers: { ...noStore, "WWW-Authenticate": "Bearer" }, content: { "application/json": { code: "unauthorized", message: "Sign in again." } } }),
  fixture("logout", "Auth_logout", 204, { headers: noStore }),
  fixture("admin-catalog", "Admin_listActivities", 200, { headers: noStore, content: { "application/json": [activity, { ...activity, id: "44444444-4444-4444-8444-444444444444", slug: "inactive-synthetic", isActive: false }] } }),
  fixture("activity-created", "Admin_createActivity", 200, { headers: noStore, content: { "application/json": activity } }),
  fixture("activity-updated", "Admin_updateActivity", 200, { headers: preserved, content: { "application/json": activity } }),
  fixture("windows", "Admin_getWindows", 200, { headers: noStore, content: { "application/json": weeklyWindows } }),
  fixture("windows-replaced", "Admin_replaceWindows", 200, { headers: preserved, content: { "application/json": weeklyWindows } }),
  fixture("blocked-dates", "Admin_getBlockedDates", 200, { headers: noStore, content: { "application/json": [blockedDate] } }),
  fixture("date-blocked", "Admin_blockDate", 200, { headers: preserved, content: { "application/json": blockedDate } }),
  fixture("admin-history", "Admin_listBookings", 200, { headers: noStore, content: { "application/json": [presentBooking, removedBooking] } }),
  fixture("canceled", "Admin_cancelBooking", 204, { headers: noStore }),
  fixture("health", "Operations_health", 200, { headers: noStore, content: { "application/json": { status: "ok" } } }),
  fixture("ready", "Operations_ready", 200, { headers: noStore, content: { "application/json": { status: "ready" } } }),
  fixture("unavailable", "Operations_ready", 503, { headers: noStore, content: { "application/json": { code: "service_unavailable", message: "Temporarily unavailable." } } }),
];
