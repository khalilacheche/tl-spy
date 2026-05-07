import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";
import type { HeatmapData } from "../types.ts";

interface Props {
  data: HeatmapData;
}

export default function HeatmapLayer({ data }: Props) {
  const map = useMap();

  useEffect(() => {
    if (!data.features.length) return;

    const maxProb = Math.max(...data.features.map((f) => f.properties.probability), 0.001);

    const points: L.HeatLatLngTuple[] = data.features
      .filter((f) => f.properties.probability > 0)
      .map((f) => [
        f.geometry.coordinates[1],
        f.geometry.coordinates[0],
        f.properties.probability / maxProb,
      ]);

    const heat = (L as unknown as { heatLayer: (latlngs: L.HeatLatLngTuple[], opts?: object) => L.Layer }).heatLayer(points, {
      radius: 35,
      blur: 25,
      maxZoom: 17,
      max: 1.0,
      gradient: {
        0.0: "#000080",
        0.25: "#0000ff",
        0.5: "#00ff00",
        0.75: "#ffff00",
        1.0: "#ff0000",
      },
    });

    heat.addTo(map);
    return () => {
      map.removeLayer(heat);
    };
  }, [data, map]);

  return null;
}
