export interface StopFeature {
  type: "Feature";
  properties: {
    id: string;
    name: string;
    probability: number;
    lines: string[];
  };
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lon, lat]
  };
}

export interface HeatmapData {
  type: "FeatureCollection";
  features: StopFeature[];
}

export interface Stop {
  id: string;
  name: string;
  lat: number;
  lon: number;
  lines: string[];
}

export interface SightingRecord {
  stop_id: string;
  timestamp: number;
  direction: string | null;
  line: string | null;
}
