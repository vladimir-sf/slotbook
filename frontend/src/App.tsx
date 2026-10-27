import { useEffect, useState } from "react";
import Catalog from "./features/catalog/Catalog";
import ActivityDetail from "./features/catalog/ActivityDetail";

function activityFromUrl() {
  return new URLSearchParams(window.location.search).get("activity") || null;
}

export default function App() {
  const [selectedSlug, setSelectedSlug] = useState(activityFromUrl);
  useEffect(() => {
    const restore = () => setSelectedSlug(activityFromUrl());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  function navigate(slug: string | null) {
    const url = new URL(window.location.href);
    if (slug === null) url.searchParams.delete("activity");
    else url.searchParams.set("activity", slug);
    window.history.pushState(null, "", url);
    setSelectedSlug(slug);
  }

  return (
    <main className="shell">
      <header className="brand">SlotBook</header>
      <section style={{ padding: "32px 0" }}>
        <h1 style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", letterSpacing: "-0.04em", overflowWrap: "anywhere" }}>Choose an appointment</h1>
        <p>Choose an appointment type to view its details and available times.</p>
      </section>
      {selectedSlug === null
        ? <Catalog onSelect={navigate} />
        : <ActivityDetail key={selectedSlug} slug={selectedSlug} onBack={() => navigate(null)} />}
    </main>
  );
}
