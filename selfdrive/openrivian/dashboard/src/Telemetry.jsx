import React from 'react';
import './Telemetry.css';

// Reusable Hologram Component
function IsometricTruck() {
  return (
    <div className="isometric-truck-container">
      <div className="truck-body">
        <div className="cab"></div>
        <div className="bed"></div>
        <div className="chassis"></div>
        <div className="wheel fl"></div>
        <div className="wheel fr"></div>
        <div className="wheel rl"></div>
        <div className="wheel rr"></div>
      </div>
    </div>
  );
}

export default function Telemetry({ telemetry }) {
  // Mapping missing telemetry to safe fallbacks
  const speed = telemetry?.speed ?? 0;
  const gear = telemetry?.gear ?? 'P';
  const battery = telemetry?.battery ?? 0;
  const adas = telemetry?.adasActive ? 'ACTIVE' : 'READY';
  const fl = telemetry?.flSpeed ?? speed;
  const fr = telemetry?.frSpeed ?? speed;
  const rl = telemetry?.rlSpeed ?? speed;
  const rr = telemetry?.rrSpeed ?? speed;

  return (
    <div className="mockup-container combo-center-hologram">
      <div className="camp-grid-dense" style={{ width: '350px', paddingRight: '2rem' }}>
        <div className="camp-tile large-tile">
          <span className="label">SPEED</span>
          <span className="value giant">{speed} <small style={{fontSize:'1.5rem'}}>MPH</small></span>
        </div>
        <div className="camp-tile">
          <span className="label">GEAR</span>
          <span className="value yellow">{gear}</span>
        </div>
        <div className="camp-tile">
          <span className="label">BATTERY</span>
          <span className="value green">{battery}%</span>
        </div>
      </div>
      
      <div className="center-hologram-stage" style={{ flex: 1 }}>
        <IsometricTruck />
        <div className="holo-callout top-left">FL: {fl}</div>
        <div className="holo-callout top-right">FR: {fr}</div>
        <div className="holo-callout bottom-left">RL: {rl}</div>
        <div className="holo-callout bottom-right">RR: {rr}</div>
      </div>

      <div className="camp-grid-col right-col" style={{ width: '250px' }}>
        <div className="camp-tile">
          <span className="label">CPU TEMP</span>
          <span className="value">{telemetry?.cpuTemp ?? 0}°C</span>
        </div>
        <div className="camp-tile highlight">
          <span className="label">ADAS</span>
          <span className="value">{adas}</span>
        </div>
        <div className="camp-tile">
          <span className="label">STORAGE</span>
          <span className="value">{telemetry?.freeSpace ?? 0}%</span>
        </div>
      </div>
    </div>
  );
}
