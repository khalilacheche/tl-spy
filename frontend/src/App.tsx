import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import HeatmapLayer from "./components/HeatmapLayer.tsx";
import StopMarkers from "./components/StopMarkers.tsx";
import Sidebar from "./components/Sidebar.tsx";
import { useHeatmap } from "./hooks/useHeatmap.ts";

const LAUSANNE_CENTER: [number, number] = [46.5197, 6.6323];

export default function App() {
  const heatmapData = useHeatmap();

  return (
    <div className="app">
      <header className="header">
        <h1>TL Spy</h1>
        <span className={`status ${heatmapData ? "live" : ""}`}>
          {heatmapData ? "Live" : "Connecting..."}
        </span>
      </header>
      <div className="map-container">
        <MapContainer
          center={LAUSANNE_CENTER}
          zoom={14}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {heatmapData && <HeatmapLayer data={heatmapData} />}
          {heatmapData && <StopMarkers data={heatmapData} />}
        </MapContainer>
        <Sidebar />
      </div>
    </div>
  );
}
