import "@typespec/http";
import "@typespec/openapi";
import "@typespec/openapi3";

using TypeSpec.Http;
using TypeSpec.OpenAPI;

/**
 * SlotBook API v1 (1.0.0), human-approved and frozen on 2026-10-25.
 * Based on the approved C-002 contract review, technical baseline 5f1ce85 and
 * amendments A-001/A-002/A-003. Contract freeze does not authorize implementation.
 * Lead coordinates changes under approved change control; material API changes need
 * human approval. Frontend/Backend must not independently edit the canonical contract
 * or generated API artifacts.
 * All response instants are RFC 3339 UTC Z; explicit-offset input is normalized to UTC,
 * and naive input is rejected. Only JSON bodies are supported; 204 has no body.
 * Never log request/response bodies, Authorization, Idempotency-Key or validator inputs.
 * Configure CORS for explicit frontend origins, allow Authorization/Idempotency-Key and
 * expose X-Preserved-Booking-Count, X-Attempt-Expires-At and Retry-After.
 * No auth cookies, guest accounts, guest cancellation or external integrations.
 * T-02 remains provisional pending PostgreSQL concurrency/crash/timeout/idempotency tests;
 * T-03 remains conditional on validated contact-free backup and hosting controls.
 */
@useAuth(NoAuth)
@service(#{ title: "SlotBook API" })
@info(#{ version: "1.0.0" })
@server("http://localhost:8000", "Local API")
namespace SlotBook {
  @format("uuid")
  scalar Id extends string;

  /** Supported IANA timezone identifier, validated against server timezone data. */
  scalar IanaTimezone extends string;

  /**
   * After outer whitespace trimming: 1–2000 Unicode code points, multiline literal plain
   * text. Preserve internal whitespace/line breaks; never truncate or interpret markup.
   * Input is trimmed before length validation; raw surrounding whitespace is not counted.
   * Runtime must count Unicode code points, not UTF-16 code units.
   */
  scalar ActivityDescription extends string;

  /** Positive integer divisible by 15; enforced by both schema and server validation. */
  @minValue(15)
  @extension("multipleOf", 15)
  scalar ActivityDuration extends int32;

  /** Nonblank name; preserve the exact submitted string for retry matching. */
  @pattern("\\S")
  scalar AttendeeName extends string;

  /** Syntactically valid email; no delivery check or additional identity normalization. */
  @format("email")
  scalar Email extends string;

  /** Public random restore epoch, a canonical lowercase UUID; not a credential. */
  @format("uuid")
  @pattern("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
  scalar AttemptGeneration extends string;

  /**
   * Echo the context generation verbatim, then '.', then canonical unpadded base64url
   * encoding of 32 cryptographically random bytes (43 characters). Generate before first
   * submission, keep private in memory, reuse only with original details. Never put in URLs.
   * The server HMAC verifier is never an accepted credential.
   */
  @pattern("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$")
  scalar BookingAttemptKey extends string;

  /** Canonical saved/read description, after the documented input trimming step. */
  @minLength(1)
  @maxLength(2000)
  scalar NormalizedActivityDescription extends ActivityDescription;

  @extension("additionalProperties", false)
  model ActivityWrite {
    slug: string;
    title: string;
    description: ActivityDescription;
    durationMinutes: ActivityDuration;
    timezone: IanaTimezone;
    isActive: boolean;
    ...Record<never>;
  }

  @extension("additionalProperties", false)
  model Activity {
    ...OmitProperties<ActivityWrite, "description">;
    description: NormalizedActivityDescription;
    id: Id;
  }

  /** Contact-free UTC interval; display labels/offsets are derived in the chosen IANA zone. */
  @extension("additionalProperties", false)
  model Slot {
    startsAt: utcDateTime;
    endsAt: utcDateTime;
    ...Record<never>;
  }

  /**
   * Unknown fields are rejected, including endsAt. Derive end from current activity duration.
   * Match activity UUID and UTC start canonically; name/email remain exact submitted strings.
   * JSON/type-invalid submissions bind a versioned raw-body digest, never stored raw bytes.
   */
  @extension("additionalProperties", false)
  model BookingRequest {
    activityId: Id;
    startsAt: utcDateTime;
    attendeeName: AttendeeName;
    attendeeEmail: Email;
    ...Record<never>;
  }

  /**
   * EVERY public success is contact-free, including the first confirmation. Start/end remain
   * immutable after booking. canceledAt is null iff status is confirmed; otherwise it is the
   * original cancellation instant. Retries return current status, never revive a canceled booking.
   */
  @extension("additionalProperties", false)
  model BookingSummary {
    id: Id;
    activityId: Id;
    startsAt: utcDateTime;
    endsAt: utcDateTime;
    status: "confirmed" | "canceled";
    canceledAt: utcDateTime | null;
    ...Record<never>;
  }

  @extension("additionalProperties", false)
  model PresentContacts {
    state: "present";
    attendeeName: AttendeeName;
    attendeeEmail: Email;
    ...Record<never>;
  }

  /** No attendee fields or fake identities; also used after contact-free restore. */
  @extension("additionalProperties", false)
  model RemovedContacts {
    state: "removed";
    ...Record<never>;
  }

  @discriminated(#{ envelope: "none", discriminatorPropertyName: "state" })
  union BookingContact {
    present: PresentContacts,
    removed: RemovedContacts,
  }

  /**
   * Protected history. Suppress contacts before serialization at/after recorded end +720h,
   * or first cancellation +720h when canceled, even if automatic deletion fails. Repeated
   * cancellation/config edits/retries never reset the anchor; restores may remove contacts earlier.
   */
  @extension("additionalProperties", false)
  model AdminBooking {
    ...BookingSummary;
    contact: BookingContact;
  }

  /**
   * ISO local clock without offset: HH:mm, optionally :ss and fractional seconds.
   * Retains local-clock precision without imposing a quarter-hour/minute restriction.
   * Explicit pattern avoids plainTime's emitted `format: time`, which RFC 3339 validators
   * interpret as requiring a timezone even though working-window clocks have none.
   */
  @pattern("^(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9](?:\\.[0-9]+)?)?$")
  scalar LocalClock extends string;

  /**
   * Same activity/weekday: end > start within one local day, no duplicate/overlap/overnight
   * windows. Touching is allowed but never merged. Times retain offset-free local-clock precision and
   * need not align to quarter hours. Invalid replacement changes nothing.
   */
  @extension("additionalProperties", false)
  model WeeklyWindow {
    @minValue(1) @maxValue(7) isoWeekday: int32;
    localStart: LocalClock;
    localEnd: LocalClock;
    ...Record<never>;
  }

  /** One activity-local date; other activities and existing bookings remain unchanged. */
  @extension("additionalProperties", false)
  model BlockedDate {
    date: plainDate;
    ...Record<never>;
  }

  @extension("additionalProperties", false)
  model AdminCredentials {
    email: Email;
    password: string;
    ...Record<never>;
  }

  /**
   * Opaque bearer kept only in browser memory (no browser storage/URL). Server-enforced
   * fixed 60 elapsed minutes from login; active use never extends it; no refresh/renewal.
   * Reload requires login. At expiry clear/lock protected state, retain only non-sensitive
   * config drafts, and require credentials plus explicit resubmission of failed writes.
   */
  @extension("additionalProperties", false)
  model AdminToken {
    accessToken: string;
    tokenType: "bearer";
    expiresAt: utcDateTime;
    ...Record<never>;
  }

  @extension("additionalProperties", false)
  model AttemptContext {
    generation: AttemptGeneration;
    ...Record<never>;
  }

  /** Admitted but unfinished at the verified read; no promised background worker. */
  @extension("additionalProperties", false)
  model AttemptPending {
    state: "pending";
    expiresAt: utcDateTime;
    ...Record<never>;
  }

  /** Safe field guidance only; never echo submitted values or raw framework validation objects. */
  @extension("additionalProperties", false)
  model FieldError {
    /** Dotted contracted input path (array indexes allowed); unknown field names use "$". */
    path: string;

    /** Stable field reason: required, invalid, unknown_field, overlap or duplicate. */
    code: "required" | "invalid" | "unknown_field" | "overlap" | "duplicate";

    message: string;
    ...Record<never>;
  }

  @extension("additionalProperties", false)
  model SafeError<Code extends string> {
    code: Code;

    /** Safe human-readable text without contacts, tokens, original attempt values or stack traces. */
    message: string;

    ...Record<never>;
  }

  @extension("additionalProperties", false)
  model ApiError<Code extends string> {
    ...SafeError<Code>;
    fields?: FieldError[];
  }

  model NoStore {
    @header("Cache-Control") cacheControl: "no-store";
  }

  model Ok<T> {
    ...NoStore;
    @statusCode statusCode: 200;
    @body body: T;
  }

  model MutationOk<T> {
    ...Ok<T>;

    /** Nonnegative affected-confirmed-booking count; warn while preserving their intervals/status. */
    @header("X-Preserved-Booking-Count")
    @minValue(0)
    preservedBookingCount: int32;
  }

  model EmptySuccess {
    ...NoStore;
    @statusCode statusCode: 204;
  }

  @error
  model ErrorResponse<
    Status extends int32,
    Code extends string,
    Detail extends {} = SafeError<Code>
  > {
    ...NoStore;
    @statusCode statusCode: Status;
    @body body: Detail;
  }

  alias ValidationError = ErrorResponse<
    400,
    "validation_failed",
    ApiError<"validation_failed">
  >;
  alias NotFoundError = ErrorResponse<404, "not_found">;
  alias SlugConflictError = ErrorResponse<
    409,
    "slug_conflict",
    ApiError<"slug_conflict">
  >;
  alias InternalError = ErrorResponse<500, "internal_error">;
  alias UnavailableError = ErrorResponse<503, "service_unavailable">;
  alias ServiceErrors = InternalError | UnavailableError;

  /** Authenticate BEFORE protected resource lookup/body validation, including malformed JSON. */
  @error
  model UnauthorizedError {
    ...ErrorResponse<401, "unauthorized">;
    @header("WWW-Authenticate") wwwAuthenticate: "Bearer";
  }

  /** Optional only because malformed keys/unverified receipts cannot prove admission. */
  @error
  model BookingError<
    Status extends int32,
    Code extends string,
    Detail extends {} = SafeError<Code>
  > {
    ...ErrorResponse<Status, Code, Detail>;

    /** Original E is REQUIRED when receipt is verified; omit if unknown. Never reset on retry. */
    @header("X-Attempt-Expires-At")
    @encode("rfc3339")
    attemptExpiresAt?: utcDateTime;
  }

  alias BookingInputCodes =
    | "validation_failed"
    | "slot_ineligible"
    | "notice_required"
    | "horizon_exceeded";
  alias BookingInputError = BookingError<
    400,
    BookingInputCodes,
    ApiError<BookingInputCodes>
  >;
  /** attempt_mismatch is generic with no fields/original details/result/booking identity. */
  alias BookingConflictError = BookingError<
    409,
    "slot_unavailable" | "attempt_mismatch"
  >;
  /** Prior-generation key after separately approved unrecoverable restore; no age/admission claim. */
  alias RestoreInvalidatedError = ErrorResponse<
    409,
    "attempt_invalidated_by_restore"
  >;
  /** No provable committed receipt: omit expiry header, no pending/confirmation/rollback assertion. */
  alias AdmissionUnverifiedError = ErrorResponse<503, "admission_unverified">;
  alias ExecutionUnverifiedError = BookingError<503, "execution_unverified">;

  @error
  model ExpiredAttemptError {
    ...ErrorResponse<410, "attempt_expired">;

    @header("X-Attempt-Expires-At")
    @encode("rfc3339")
    attemptExpiresAt: utcDateTime;
  }

  model BookingCreated {
    ...NoStore;
    @statusCode statusCode: 201;

    @header("X-Attempt-Expires-At")
    @encode("rfc3339")
    attemptExpiresAt: utcDateTime;

    @body body: BookingSummary;
  }

  model BookingReplayed {
    ...Ok<BookingSummary>;

    @header("X-Attempt-Expires-At")
    @encode("rfc3339")
    attemptExpiresAt: utcDateTime;
  }

  model BookingPending {
    ...NoStore;
    @statusCode statusCode: 202;

    @header("X-Attempt-Expires-At")
    @encode("rfc3339")
    attemptExpiresAt: utcDateTime;

    /** Integer seconds until an explicit same-key retry is suggested; not automatic replay. */
    @header("Retry-After") @minValue(0) retryAfter: int32;

    /** expiresAt must equal X-Attempt-Expires-At. No booking ID/contact/original payload. */
    @body body: AttemptPending;
  }

  @route("/api/activities")
  namespace Activities {
    /** Active activities only, including mandatory full descriptions. */
    @get op list(): Ok<Activity[]> | ServiceErrors;

    /** Missing/inactive activity returns not_found; no contacts. */
    @route("/{slug}")
    @get
    op detail(@path slug: string): Ok<Activity> | NotFoundError | ServiceErrors;

    /**
     * date groups starts by selected displayTimezone (defaults to activity zone when omitted).
     * Include every relevant activity-local date; sort/deduplicate by UTC start. Browser starts
     * with detected visitor zone, fallback activity zone, and permits manual IANA selection.
     * Eligibility uses activity-local windows/blocks, exact local minutes 00/15/30/45 and zero
     * seconds/fractions, independently of display zone/window opening. Full elapsed [start,end)
     * fits one continuous real portion of one window, end may equal boundary. Skip nonexistent
     * local starts; offer both eligible repeated instants with distinct offsets in display.
     * Never shift missing boundaries, bridge excluded portions, extend/merge windows or round.
     * At fresh time N: N+1h <= start <= N+1440h, inclusive; only start is horizon-constrained.
     * Omit past/blocked/inactive/occupied/ineligible slots; 200 [] differs from load failure.
     * A 30m activity in 09:10–10:00 permits 09:15/09:30; 09:10–09:40 permits none.
     */
    @route("/{slug}/slots")
    @get
    op slots(
      @path slug: string,
      @query date: plainDate,
      @query displayTimezone?: IanaTimezone,
    ): Ok<Slot[]> | ValidationError | NotFoundError | ServiceErrors;
  }

  @route("/api/booking-attempts")
  namespace BookingAttempts {
    /**
     * Public generation only, no booking/guest lookup. Failure blocks NEW attempt creation;
     * retain an existing private key/details for explicit recovery. Routine missing state fails
     * readiness; never rotate generation on normal restart/transient failure.
     */
    @route("/context")
    @get
    op getContext(): Ok<AttemptContext> | ServiceErrors;
  }

  @route("/api/bookings")
  namespace Bookings {
    /**
     * A-002: admit only when original binding and DB-generated wall-clock T/E commit durably;
     * E=T+24 elapsed hours, NOT commit metadata/HTTP/ACK/retry time. Stamp T late after key
     * contention/preparation; never restamp a committed attempt. Delayed COMMIT consumes
     * validity; commit at/after E is already expired, with no execution/pending/result access.
     * Rollback admits nothing through that transaction; uncertain COMMIT stays unverified.
     * Revalidate current availability, local quarter-hour grid, full-window fit, blocks and
     * inclusive 1h/1440h start bounds after lock waits using fresh database wall-clock time.
     * DB exclusion prevents same-activity confirmed overlap, allowing adjacency. Configuration
     * writes/cancellation serialize with booking eligibility. Execution commits booking/contact/
     * result together; no confirmation until known committed. Split protocol remains T-02 provisional.
     * Same key + matching details: return stable rejection or same booking/current status;
     * completed success replays 200 without eligibility reevaluation or revival. Distinct
     * competing keys: one 201/one 409 slot_unavailable. Before E mismatch is generic 409.
     * Pending 202 ONLY on fallback/contention after proven committed matching unexpired
     * unfinished admission. Roll back failed lock/deadlock/timeout transactions before fresh
     * committed-state classification. Missing proof yields phase-specific unverified 503.
     * At/after E current-generation key returns 410 before binding/result access; tombstones
     * prevent reuse. Normal restarts preserve original generation/T/E/binding/results.
     * A-003: separately approved unrecoverable, fenced restore may invalidate old generations
     * (even unexpired) with 409 attempt_invalidated_by_restore, distinct from 410. It proves no
     * age/admission/booking failure. Unknown/expired/invalidated outcomes direct host verification;
     * no automatic new key or blind resubmission. Retrying requires original details and key;
     * no key-only/contact lookup. Lost browser memory uses host verification.
     * Known admitted terminal errors carry original expiry; unverified admission/restore loss
     * omit it. 500/503 on a mutation never by themselves prove rejection or rollback.
     * Malformed JSON/type/unknown fields map to 400 validation_failed, never framework 422/HTML.
     */
    @post
    op create(
      @header("Idempotency-Key") idempotencyKey: BookingAttemptKey,
      @body request: BookingRequest,
    ):
      | BookingCreated
      | BookingReplayed
      | BookingPending
      | BookingInputError
      | BookingConflictError
      | RestoreInvalidatedError
      | ExpiredAttemptError
      | AdmissionUnverifiedError
      | ExecutionUnverifiedError
      | ServiceErrors;
  }

  @route("/api/auth")
  namespace Auth {
    /** Single seeded admin; generic invalid credentials; no sign-up/refresh/automatic write replay. */
    @route("/login")
    @post
    op login(@body credentials: AdminCredentials):
      | Ok<AdminToken>
      | ValidationError
      | UnauthorizedError
      | ServiceErrors;

    /** Revoke the presented session verifier and clear browser memory. Expired/invalid bearer is 401. */
    @useAuth(BearerAuth)
    @route("/session")
    @delete
    op logout(): EmptySuccess | UnauthorizedError | ServiceErrors;
  }

  /**
   * Bearer required on EVERY operation. Authenticate before body/query/path validation or
   * existence lookup. Recheck expiry at protected authorization time after lock waits.
   * Invalid IDs (including malformed UUIDs) return validation_failed after auth; valid missing
   * IDs return not_found. Internal/unavailable mutation outcomes remain unverified until resolved.
   */
  @useAuth(BearerAuth)
  @route("/api/admin")
  namespace Admin {
    /** Include inactive offerings so existing configuration can be managed. */
    @route("/activities")
    @get
    op listActivities(): Ok<Activity[]> | UnauthorizedError | ServiceErrors;

    /** Validate description/duration/IANA zone/unique slug; preserve existing 200 success status. */
    @route("/activities")
    @post
    op createActivity(@body activity: ActivityWrite):
      | Ok<Activity>
      | ValidationError
      | UnauthorizedError
      | SlugConflictError
      | ServiceErrors;

    /**
     * Preserve all existing start/end/status for title/description/slug/duration/zone/active changes.
     * New rules apply only to new attempts; warn using affected-confirmed-booking count.
     */
    @route("/activities/{id}")
    @put
    op updateActivity(@path id: Id, @body activity: ActivityWrite):
      | MutationOk<Activity>
      | ValidationError
      | UnauthorizedError
      | NotFoundError
      | SlugConflictError
      | ServiceErrors;

    @route("/activities/{id}/weekly-windows")
    @get
    op getWindows(@path id: Id):
      | Ok<WeeklyWindow[]>
      | ValidationError
      | UnauthorizedError
      | NotFoundError
      | ServiceErrors;

    /** Atomic replacement, including empty set; reject invalid set without partial changes. Preserve bookings. */
    @route("/activities/{id}/weekly-windows")
    @put
    op replaceWindows(@path id: Id, @body windows: WeeklyWindow[]):
      | MutationOk<WeeklyWindow[]>
      | ValidationError
      | UnauthorizedError
      | NotFoundError
      | ServiceErrors;

    @route("/activities/{id}/blocked-dates")
    @get
    op getBlockedDates(@path id: Id):
      | Ok<BlockedDate[]>
      | ValidationError
      | UnauthorizedError
      | NotFoundError
      | ServiceErrors;

    /** Per-activity local date; same block returns existing state; never mutate/cancel bookings. No unblock feature. */
    @route("/activities/{id}/blocked-dates")
    @post
    op blockDate(@path id: Id, @body block: BlockedDate):
      | MutationOk<BlockedDate>
      | ValidationError
      | UnauthorizedError
      | NotFoundError
      | ServiceErrors;

    /** All confirmed/canceled history; present/removed contacts according to current deadline check. */
    @route("/bookings")
    @get
    op listBookings(): Ok<AdminBooking[]> | UnauthorizedError | ServiceErrors;

    /**
     * Confirmed -> canceled; repeated/concurrent cancellation is successful 204 no-op acknowledging
     * current canceled state. Preserve original canceledAt and its 720h deletion anchor; no contact
     * restoration. Free otherwise eligible slots; other bookings unaffected. Missing ID is 404,
     * invalid ID 400 after authentication. Cancellation is administrator-only; no guest operation.
     */
    @route("/bookings/{id}")
    @delete
    op cancelBooking(@path id: Id):
      | EmptySuccess
      | ValidationError
      | NotFoundError
      | UnauthorizedError
      | ServiceErrors;
  }

  @extension("additionalProperties", false)
  model HealthStatus {
    status: "ok";
    ...Record<never>;
  }

  @extension("additionalProperties", false)
  model ReadyStatus {
    status: "ready";
    ...Record<never>;
  }

  namespace Operations {
    /** Shallow liveness only; no guest/credential/database detail. Does not prove MVP behavior. */
    @route("/health")
    @get
    op health():
      | Ok<{
          status: "ok";
          ...Record<never>;
        }>
      | ServiceErrors;

    /**
     * Ready only when DB/schema/durability/generation/retention-worker checks pass. Otherwise
     * generic service_unavailable, with no public operator inventory/connection/credential detail.
     * Detailed worker failures are operator CLI output, not a public diagnostic endpoint.
     */
    @route("/ready")
    @get
    op ready():
      | Ok<{
          status: "ready";
          ...Record<never>;
        }>
      | ServiceErrors;
  }
}
