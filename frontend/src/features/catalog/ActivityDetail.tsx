import { useEffect, useState } from "react";
import { ApiFailure, getActivity, type Activity } from "../../api/client";
import Availability from "./Availability";

type State = { kind: "loading" | "error" | "unavailable" } | { kind: "ready"; activity: Activity };

export default function ActivityDetail({ slug, onBack }: { slug: string; onBack: () => void }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    getActivity(slug, controller.signal).then((activity) => {
      if (!controller.signal.aborted) setState(activity.isActive ? { kind: "ready", activity } : { kind: "unavailable" });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ kind: error instanceof ApiFailure && error.kind === "not-found" ? "unavailable" : "error" });
    });
    return () => controller.abort();
  }, [slug, attempt]);

  return <section aria-label="Appointment details" style={{ overflowWrap: "anywhere" }}>
    <button type="button" onClick={onBack}>Back to appointment types</button>
    {state.kind === "loading" && <p role="status">Loading appointment details…</p>}
    {state.kind === "unavailable" && <p role="alert">This appointment is unavailable. Choose another appointment type.</p>}
    {state.kind === "error" && <>
      <p role="alert">Could not load appointment details. Please try again.</p>
      <button type="button" onClick={() => setAttempt((value) => value + 1)}>Try again</button>
    </>}
    {state.kind === "ready" && <>
      <h2>{state.activity.title}</h2>
      <p data-testid="activity-description" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{state.activity.description}</p>
      <p>{state.activity.durationMinutes} minutes</p>
      <p>Activity timezone: {state.activity.timezone}</p>
      <Availability key={state.activity.slug} activity={state.activity} />
    </>}
  </section>;
}
