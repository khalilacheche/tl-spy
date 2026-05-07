import { useState } from "react";

interface Props {
  simTime: number;
  speed: number;
  agents: number;
  onSpeedChange: (speed: number) => void;
}

const SPEED_STEPS = [1, 2, 5, 10, 20, 50];

export default function SimControls({ simTime, speed, agents, onSpeedChange }: Props) {
  const [localSpeed, setLocalSpeed] = useState(speed);

  const clock = new Date(simTime * 1000);
  const timeStr = clock.toLocaleTimeString("fr-CH", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const dateStr = clock.toLocaleDateString("fr-CH", {
    day: "2-digit",
    month: "short",
  });

  const handleSpeedChange = (val: number) => {
    setLocalSpeed(val);
    onSpeedChange(val);
  };

  const currentIdx = SPEED_STEPS.indexOf(
    SPEED_STEPS.reduce((prev, curr) =>
      Math.abs(curr - localSpeed) < Math.abs(prev - localSpeed) ? curr : prev
    )
  );

  return (
    <div className="sim-controls">
      <div className="sim-clock">
        <div className="clock-time">{timeStr}</div>
        <div className="clock-date">{dateStr}</div>
      </div>
      <div className="speed-control">
        <label>Speed</label>
        <input
          type="range"
          min={0}
          max={SPEED_STEPS.length - 1}
          value={currentIdx}
          onChange={(e) => handleSpeedChange(SPEED_STEPS[parseInt(e.target.value)])}
        />
        <span className="speed-label">{localSpeed}x</span>
      </div>
      <div className="agent-count">{agents} agents</div>
    </div>
  );
}
