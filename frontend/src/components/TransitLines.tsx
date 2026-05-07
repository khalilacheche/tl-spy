import { useEffect, useState } from "react";
import { Polyline, Tooltip } from "react-leaflet";
import type { TransitLine } from "../types.ts";

export default function TransitLines() {
  const [lines, setLines] = useState<TransitLine[]>([]);

  useEffect(() => {
    fetch("/api/lines")
      .then((r) => r.json())
      .then((d) => setLines(d.lines))
      .catch(console.error);
  }, []);

  return (
    <>
      {lines.map((line) => (
        <Polyline
          key={line.name}
          positions={line.coords}
          pathOptions={{
            color: line.color,
            weight: line.weight,
            opacity: line.opacity,
          }}
        >
          <Tooltip sticky>{line.name}</Tooltip>
        </Polyline>
      ))}
    </>
  );
}
