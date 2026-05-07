import { useState, useEffect } from "react";
import type { SightingRecord, Stop, LineRisk } from "../types.ts";

interface Props {
  lineRisks: LineRisk[];
}

function riskColor(risk: number): string {
  if (risk >= 0.7) return "#ff4444";
  if (risk >= 0.4) return "#ffaa00";
  if (risk >= 0.15) return "#ffdd44";
  return "#66bb6a";
}

function riskLabel(risk: number): string {
  if (risk >= 0.7) return "HIGH";
  if (risk >= 0.4) return "MED";
  if (risk >= 0.15) return "LOW";
  return "OK";
}

export default function Sidebar({ lineRisks }: Props) {
  const [stops, setStops] = useState<Stop[]>([]);
  const [sightings, setSightings] = useState<SightingRecord[]>([]);
  const [selectedStop, setSelectedStop] = useState("");
  const [filter, setFilter] = useState("");

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

  const filteredRisks = lineRisks.filter((lr) =>
    lr.line.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="sidebar">
      {lineRisks.length > 0 && (
        <div className="line-ranking">
          <h2>Line Risk</h2>
          <input
            type="text"
            className="line-filter"
            placeholder="Filter lines..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="risk-list">
            {filteredRisks.map((lr) => (
              <div key={lr.line} className="risk-row">
                <span className="risk-line-name">{lr.line}</span>
                <div className="risk-bar-bg">
                  <div
                    className="risk-bar-fill"
                    style={{
                      width: `${Math.round(lr.risk * 100)}%`,
                      background: riskColor(lr.risk),
                    }}
                  />
                </div>
                <span className="risk-badge" style={{ color: riskColor(lr.risk) }}>
                  {riskLabel(lr.risk)}
                </span>
              </div>
            ))}
            {filteredRisks.length === 0 && (
              <p style={{ color: "#666", fontSize: "0.8rem" }}>No matching lines</p>
            )}
          </div>
        </div>
      )}

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
