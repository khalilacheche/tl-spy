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
    coordinates: [number, number];
  };
}

export interface HeatmapData {
  type: "FeatureCollection";
  features: StopFeature[];
}

export interface LineRisk {
  line: string;
  risk: number;
  agents: number;
}

export interface SimUpdate {
  points: [number, number, number][]; // [lat, lon, weight][]
  sim_time: number;
  speed: number;
  agents: number;
  groups: number;
  line_risks: LineRisk[];
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

export interface TransitLine {
  name: string;
  color: string;
  weight: number;
  opacity: number;
  coords: [number, number][];
}
