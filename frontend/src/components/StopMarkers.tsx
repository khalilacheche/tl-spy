import { CircleMarker, Popup } from "react-leaflet";
import type { HeatmapData } from "../types.ts";

interface Props {
  data: HeatmapData;
}

export default function StopMarkers({ data }: Props) {
  return (
    <>
      {data.features.map((feature) => {
        const { id, name, probability, lines } = feature.properties;
        const [lon, lat] = feature.geometry.coordinates;
        const pct = (probability * 100).toFixed(1);

        return (
          <CircleMarker
            key={id}
            center={[lat, lon]}
            radius={6}
            pathOptions={{
              color: "#fff",
              weight: 1,
              fillColor: probability > 0.05 ? "#ef4444" : "#3b82f6",
              fillOpacity: 0.8,
            }}
          >
            <Popup>
              <strong>{name}</strong>
              <br />
              Lines: {lines.join(", ")}
              <br />
              Probability: {pct}%
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
