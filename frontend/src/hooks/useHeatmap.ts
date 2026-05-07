import { useEffect, useRef, useState } from "react";
import type { HeatmapData } from "../types.ts";

const API_BASE = "/api";

export function useHeatmap() {
  const [data, setData] = useState<HeatmapData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/heatmap`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error);

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}${API_BASE}/ws`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as HeatmapData;
        setData(parsed);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setTimeout(() => {
        // simple reconnect
        window.location.reload();
      }, 5000);
    };

    return () => {
      ws.close();
    };
  }, []);

  return data;
}
