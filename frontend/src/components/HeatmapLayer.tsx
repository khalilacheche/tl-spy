import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";
import type { SimUpdate } from "../types.ts";

interface Props {
  data: SimUpdate;
}

export default function HeatmapLayer({ data }: Props) {
  const map = useMap();
  const layerRef = useRef<L.Layer | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }

    if (!data.points.length) return;

    const maxW = Math.max(...data.points.map((p) => p[2]), 0.001);

    const heatPoints: L.HeatLatLngTuple[] = data.points.map(([lat, lon, w]) => [
      lat,
      lon,
      w / maxW,
    ]);

    const heatFn = (L as unknown as { heatLayer: (pts: L.HeatLatLngTuple[], opts?: object) => L.Layer }).heatLayer;
    const heat = heatFn(heatPoints, {
      radius: 30,
      blur: 20,
      maxZoom: 17,
      max: 1.0,
      gradient: {
        0.0: "rgba(0, 0, 128, 0)",
        0.1: "#0000ff",
        0.3: "#00ccff",
        0.5: "#00ff00",
        0.7: "#ffff00",
        1.0: "#ff0000",
      },
    });

    heat.addTo(map);
    layerRef.current = heat;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [data, map]);

  return null;
}
