# SlotBook MVP — Product Requirements Document

## Goal
A host defines appointment types and weekly working hours. A guest can see available time slots
and book a meeting without creating an account. The host can review/cancel appointments.

## Actors
- Guest: browse activities, view free slots for a date, create a booking.
- Admin: log in, create/edit activities, set weekly windows, view/cancel bookings, block days.

## User stories and acceptance criteria

### Activity catalog
- Public activity list contains active activities with name, slug, duration (minutes), timezone.
- Each activity has a unique slug and a positive duration divisible by 15.

### Availability
- Host defines weekly windows (ISO weekday 1=Monday ... 7=Sunday) in activity's IANA timezone.
- Guest requests a date and sees slots at 15-minute start increments that fit fully in a window.
- Past slots, blocked dates and slots overlapping confirmed bookings are excluded.
- Daylight-saving changes MUST be computed by timezone-aware logic, not a hard-coded UTC offset.
- API sends timestamps with explicit UTC offsets; frontend formats in a chosen IANA timezone.

### Booking
- Guest supplies name, email and start timestamp for an existing, available slot.
- Server derives end timestamp from activity duration. Client cannot prescribe it.
- `POST /api/bookings` succeeds with `201`, returning a booking ID and status.
- A duplicate/concurrent/conflicting request returns `409`, not two confirmed bookings.
- Invalid or past slots return `400`; input errors are safely explained.
- Guest data is not exposed in public activity/slots responses.

### Admin
- Single seeded administrator for MVP; no public admin sign-up.
- Admin login issues a short-lived bearer token. Secrets loaded from environment.
- Protected admin operations reject missing/invalid credentials with `401`.
- Admin can create/update activities, edit weekly availability, block dates, view bookings, cancel bookings.

## Non-functional requirements
- Database migration and one-command local Docker Compose startup.
- End-to-end flow: browse -> select -> book -> confirmation.
- Unit tests for date logic, integration tests for booking transaction, E2E for user journeys.
- Dockerfiles for frontend/backend, GitHub Actions CI, clear developer README.
- Data deletion policy before public deployment; avoid retaining guest contact info in logs.

## Out of scope for MVP
- Google Calendar sync, OAuth login, team/multi-tenant support, payments, email sending,
  invitations, real-time WebSockets, advanced recurring exceptions, production observability.

## Open decisions (resolve in Spec Kit clarify)
- Should blocked days apply to all activities or per activity? Default: per activity.
- Should guest cancellation be offered? Default: admin-only cancellation in MVP.
- Booking horizon? Default: next 60 days.
- Min notice? Default: 1 hour.
- DST edge policy: define treatment of ambiguous and nonexistent local times before implementing
  affected availability behavior; fixed UTC offsets must not substitute for IANA timezone rules.
- Authentication detail: approve token lifetime and browser storage strategy. Preserve hashed
  passwords, environment-provided secrets, and short-lived bearer authentication.
- API validation: reconcile status codes and error bodies with TypeSpec before implementation;
  invalid slot queries and invalid activity updates currently lack a declared bad-request branch.
  Do not invent implementation-only error responses.
- Local startup: approve migration execution and repeatable synthetic admin/activity seeding,
  including credential configuration. Preserve documented one-command Compose startup.

These remain clarification/planning questions, not approved choices. Future feature `spec.md`
and design artifacts must carry these decisions and the existing acceptance criteria forward
with traceable references. Booking concurrency and interval verification are detailed in
`docs/ADR-0002-booking-concurrency.md`; authentication design remains in `docs/ARCHITECTURE.md`.
