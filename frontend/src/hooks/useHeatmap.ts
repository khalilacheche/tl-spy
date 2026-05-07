import { useEffect, useRef, useState, useCallback } from "react";
import type { SimUpdate } from "../types.ts";

const API_BASE = "/api";

export function useSimulation() {
  const [simData, setSimData] = useState<SimUpdate | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}${API_BASE}/ws`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        setSimData(JSON.parse(event.data) as SimUpdate);
      } catch {
        // ignore
      }
    };

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const setSpeed = useCallback((speed: number) => {
    fetch(`${API_BASE}/speed?multiplier=${speed}`, { method: "POST" }).catch(console.error);
  }, []);

  return { simData, setSpeed };
}
