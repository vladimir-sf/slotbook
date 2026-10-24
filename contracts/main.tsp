import "@typespec/http";
import "@typespec/openapi3";

using TypeSpec.Http;

@service(#{ title: "SlotBook API" })
@server("http://localhost:8000", "Local API")
@route("/api")
namespace SlotBook {
  model Activity {
    id: string;
    slug: string;
    title: string;
    durationMinutes: int32;
    timezone: string;
    isActive: boolean;
  }

  model Slot {
    startsAt: utcDateTime;
    endsAt: utcDateTime;
  }

  model BookingRequest {
    activityId: string;
    startsAt: utcDateTime;
    attendeeName: string;
    attendeeEmail: string;
  }

  model Booking {
    id: string;
    activityId: string;
    startsAt: utcDateTime;
    endsAt: utcDateTime;
    attendeeName: string;
    attendeeEmail: string;
    status: "confirmed" | "canceled";
  }

  model WeeklyWindow {
    isoWeekday: int32;
    localStart: plainTime;
    localEnd: plainTime;
  }

  model BlockedDate {
    date: plainDate;
  }

  model AdminCredentials {
    email: string;
    password: string;
  }

  model AdminToken {
    accessToken: string;
    tokenType: "bearer";
  }

  model ActivityWrite {
    slug: string;
    title: string;
    durationMinutes: int32;
    timezone: string;
    isActive: boolean;
  }

  @route("/activities")
  namespace Activities {
    @get op list(): Activity[];
    @route("/{slug}") @get op detail(@path slug: string): Activity | NotFoundResponse;
    @route("/{slug}/slots") @get
    op slots(@path slug: string, @query date: plainDate): Slot[] | NotFoundResponse;
  }

  @route("/bookings")
  namespace Bookings {
    @post op create(@body request: BookingRequest):
      (CreatedResponse & Body<Booking>) | ConflictResponse | BadRequestResponse;
  }

  @route("/auth")
  namespace Auth {
    @route("/login") @post
    op login(@body credentials: AdminCredentials): AdminToken | UnauthorizedResponse;
  }

  @useAuth(BearerAuth)
  @route("/admin")
  namespace Admin {
    @route("/activities") @post
    op createActivity(@body activity: ActivityWrite): Activity | BadRequestResponse | UnauthorizedResponse;

    @route("/activities/{id}") @put
    op updateActivity(@path id: string, @body activity: ActivityWrite): Activity | NotFoundResponse | UnauthorizedResponse;

    @route("/activities/{id}/weekly-windows") @put
    op replaceWindows(@path id: string, @body windows: WeeklyWindow[]):
      WeeklyWindow[] | BadRequestResponse | UnauthorizedResponse;

    @route("/activities/{id}/blocked-dates") @post
    op blockDate(@path id: string, @body block: BlockedDate):
      BlockedDate | BadRequestResponse | UnauthorizedResponse;

    @route("/bookings") @get
    op listBookings(): Booking[] | UnauthorizedResponse;

    @route("/bookings/{id}") @delete
    op cancelBooking(@path id: string): NoContentResponse | NotFoundResponse | UnauthorizedResponse;
  }
}
