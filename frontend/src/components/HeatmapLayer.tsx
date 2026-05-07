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

    const heatPoints: L.HeatLatLngTuple[] = data.points.map(([lat, lon, w]) => [
      lat,
      lon,
      w,
    ]);

    const heatFn = (L as unknown as { heatLayer: (pts: L.HeatLatLngTuple[], opts?: object) => L.Layer }).heatLayer;
    const heat = heatFn(heatPoints, {
      radius: 32,
      blur: 18,
      maxZoom: 17,
      max: 0.04,
      minOpacity: 0.15,
      gradient: {
        0.0: "rgba(0, 0, 255, 0)",
        0.05: "rgba(0, 80, 255, 0.4)",
        0.2: "#00ccff",
        0.4: "#00ff00",
        0.6: "#ffff00",
        0.8: "#ff6600",
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
