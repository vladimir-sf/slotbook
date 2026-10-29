import { useEffect, useId, useMemo, useState } from "react";
import { ApiFailure, getSlots, type Activity, type Slot } from "../../api/client";

type Result = { key: string } & (
  | { kind: "loading" }
  | { kind: "error"; reason: "unavailable" | "invalid-request" | "not-found" }
  | { kind: "ready"; slots: Slot[] }
);

function visitorTimezone(fallback: string): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || fallback;
  } catch {
    return fallback;
  }
}

export default function Availability({ activity }: { activity: Activity }) {
  const dateId = useId();
  // Only public discovery context belongs in the URL. A slot choice is held in memory.
  const [date, setDate] = useState(() => new URLSearchParams(window.location.search).get("date") || "");
  const [displayTimezone] = useState(() => visitorTimezone(activity.timezone));
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const [choice, setChoice] = useState<{ key: string; slot: Slot } | null>(null);
  const key = JSON.stringify([activity.slug, date, displayTimezone, attempt]);
  const current = result?.key === key ? result : null;
  const selected = choice?.key === key ? choice.slot : null;
  const formatter = useMemo(() => new Intl.DateTimeFormat(undefined, {
    timeZone: displayTimezone, year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit", timeZoneName: "shortOffset",
  }), [displayTimezone]);

  useEffect(() => {
    if (!date) return;
    const controller = new AbortController();
    setResult({ key, kind: "loading" });
    getSlots(activity.slug, { date, displayTimezone }, controller.signal).then((slots) => {
      if (!controller.signal.aborted) setResult({ key, kind: "ready", slots });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        const reason = error instanceof ApiFailure && (error.kind === "not-found" || error.kind === "invalid-request")
          ? error.kind : "unavailable";
        setResult({ key, kind: "error", reason });
      }
    });
    return () => controller.abort();
  }, [activity.slug, date, displayTimezone, key]);

  function changeDate(value: string) {
    setChoice(null);
    setDate(value);
    const url = new URL(window.location.href);
    if (value) url.searchParams.set("date", value);
    else url.searchParams.delete("date");
    window.history.replaceState(null, "", url);
  }

  function retry() {
    setChoice(null);
    setAttempt((value) => value + 1);
  }

  const instant = (value: string) => <time dateTime={value}>{formatter.format(new Date(value))}</time>;

  return <section aria-label="Availability">
    <h3>Choose a date and time</h3>
    <p>Times shown in {displayTimezone}.</p>
    <label htmlFor={dateId}>Appointment date</label>{" "}
    <input id={dateId} type="date" value={date} onChange={(event) => changeDate(event.target.value)}
      style={{ maxWidth: "100%", font: "inherit" }} />
    {!date && <p role="status">Choose a date to see available times.</p>}
    {date && (!current || current.kind === "loading") && <p role="status">Loading available times…</p>}
    {date && current?.kind === "error" && <>
      <p role="alert">{current.reason === "not-found"
        ? "This appointment is unavailable. Choose another appointment type."
        : current.reason === "invalid-request"
          ? "Could not load available times. Check the date and try again."
          : "Could not load available times. Please try again."}</p>
      <button type="button" onClick={retry}>Try again</button>
    </>}
    {date && current?.kind === "ready" && (current.slots.length === 0
      ? <p role="status">No available times for this date. Choose another date.</p>
      : <div role="group" aria-label="Available slots" style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 16 }}>
        {/* Keep the server's order and exact instants: no generated, filtered or rounded slots. */}
        {current.slots.map((slot) => <button type="button" key={slot.startsAt} value={slot.startsAt}
          aria-pressed={selected?.startsAt === slot.startsAt} onClick={() => setChoice({ key, slot })}
          style={{ maxWidth: "100%", whiteSpace: "normal", padding: 12, font: "inherit" }}>
          {instant(slot.startsAt)} – {instant(slot.endsAt)}
        </button>)}
      </div>)}
    {selected && <section aria-label="Selected time">
      <h3>Selected time</h3>
      <p>{instant(selected.startsAt)} – {instant(selected.endsAt)} ({displayTimezone})</p>
    </section>}
    <p>Selecting a time does not reserve it.</p>
  </section>;
}
