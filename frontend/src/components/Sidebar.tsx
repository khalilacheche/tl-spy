import { useState, useEffect } from "react";
import type { SightingRecord, Stop } from "../types.ts";

export default function Sidebar() {
  const [stops, setStops] = useState<Stop[]>([]);
  const [sightings, setSightings] = useState<SightingRecord[]>([]);
  const [selectedStop, setSelectedStop] = useState("");

  useEffect(() => {
    fetch("/api/stops")
      .then((r) => r.json())
      .then((d) => setStops(d.stops))
      .catch(console.error);

    const poll = setInterval(() => {
      fetch("/api/sightings")
        .then((r) => r.json())
        .then((d) => setSightings(d.sightings))
        .catch(console.error);
    }, 5000);

    fetch("/api/sightings")
      .then((r) => r.json())
      .then((d) => setSightings(d.sightings))
      .catch(console.error);

    return () => clearInterval(poll);
  }, []);

  const reportSighting = async () => {
    if (!selectedStop) return;
    await fetch(`/api/sightings?stop_id=${encodeURIComponent(selectedStop)}`, {
      method: "POST",
    });
    setSelectedStop("");
    const res = await fetch("/api/sightings");
    const d = await res.json();
    setSightings(d.sightings);
  };

  const stopNameMap = Object.fromEntries(stops.map((s) => [s.id, s.name]));

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString();
  };

  return (
    <div className="sidebar">
      <h2>Recent Sightings</h2>
      {sightings.length === 0 && (
        <p style={{ color: "#888", fontSize: "0.85rem" }}>
          No sightings yet. Report one below or connect Telegram.
        </p>
      )}
      {sightings
        .slice()
        .reverse()
        .slice(0, 10)
        .map((s, i) => (
          <div key={i} className="sighting-item">
            <span className="stop-name">{stopNameMap[s.stop_id] ?? s.stop_id}</span>
            {s.line && <span> on {s.line}</span>}
            <div className="meta">{formatTime(s.timestamp)}</div>
          </div>
        ))}

      <div className="report-form">
        <h2>Report Sighting</h2>
        <select
          value={selectedStop}
          onChange={(e) => setSelectedStop(e.target.value)}
        >
          <option value="">Select stop...</option>
          {stops
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.lines.join(", ")})
              </option>
            ))}
        </select>
        <button onClick={reportSighting} disabled={!selectedStop}>
          Report Controller Here
        </button>
      </div>
    </div>
  );
}
