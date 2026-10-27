import { useEffect, useState } from "react";
import { listActivities, type Activity } from "../../api/client";

type State = { kind: "loading" } | { kind: "error" } | { kind: "ready"; activities: Activity[] };

export default function Catalog({ onSelect }: { onSelect: (slug: string) => void }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    listActivities(controller.signal).then((activities) => {
      if (!controller.signal.aborted) setState({ kind: "ready", activities });
    }).catch(() => {
      if (!controller.signal.aborted) setState({ kind: "error" });
    });
    return () => controller.abort();
  }, [attempt]);

  return <section aria-label="Appointment types">
    {state.kind === "loading" && <p role="status">Loading appointment types…</p>}
    {state.kind === "error" && <>
      <p role="alert">Could not load appointment types. Please try again.</p>
      <button type="button" onClick={() => setAttempt((value) => value + 1)}>Try again</button>
    </>}
    {state.kind === "ready" && (state.activities.length === 0
      ? <p role="status">No appointment types are available.</p>
      : <ul className="grid" style={{ listStyle: "none", padding: 0 }}>
        {state.activities.map((activity) => <li key={activity.id} style={{ minWidth: 0 }}>
          <article style={{ overflowWrap: "anywhere" }}>
            <h2>{activity.title}</h2>
            <p style={{ whiteSpace: "pre-wrap" }}>{activity.description}</p>
            <p>{activity.durationMinutes} minutes</p>
            <p>Activity timezone: {activity.timezone}</p>
            <button type="button" style={{ maxWidth: "100%", whiteSpace: "normal" }} onClick={() => onSelect(activity.slug)}>
              View {activity.title}
            </button>
          </article>
        </li>)}
      </ul>)}
  </section>;
}
