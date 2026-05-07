import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import HeatmapLayer from "./components/HeatmapLayer.tsx";
import TransitLines from "./components/TransitLines.tsx";
import SimControls from "./components/SimControls.tsx";
import Sidebar from "./components/Sidebar.tsx";
import { useSimulation } from "./hooks/useHeatmap.ts";

const LAUSANNE_CENTER: [number, number] = [46.5197, 6.6323];

export default function App() {
  const { simData, setSpeed } = useSimulation();

  return (
    <div className="app">
      <header className="header">
        <h1>TL Spy</h1>
        <span className={`status ${simData ? "live" : ""}`}>
          {simData ? "Live" : "Connecting..."}
        </span>
      </header>
      <div className="map-container">
        <MapContainer
          center={LAUSANNE_CENTER}
          zoom={14}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          <TransitLines />
          {simData && simData.points.length > 0 && <HeatmapLayer data={simData} />}
        </MapContainer>
        {simData && (
          <SimControls
            simTime={simData.sim_time}
            speed={simData.speed}
            agents={simData.agents}
            onSpeedChange={setSpeed}
          />
        )}
        <Sidebar />
      </div>
    </div>
  );
}
