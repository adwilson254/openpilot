import { useState } from 'react';
import { useTelemetry } from '../lib/mqtt';
import { T, fmt, bool, gearLabel } from '../lib/format';
import RivianTruck from '../components/RivianTruck';
import { Tile, StatusChip, Ring } from '../components/widgets';

export default function Drive() {
  const t = useTelemetry();
  const [sasquatch, setSasquatch] = useState(false);
  const speed = Number(t.get(T.speed_mph, 0)) || 0;
  const adasOn = bool(t.get(T.adasActive)) || bool(t.get(T.adasEnabled));
  const charging = bool(t.get(T.charging));
  const lead = t.get(T.leadDist);
  const hasLead = typeof lead === 'number' && lead >= 0;
  const corner = (k) => fmt(Number(t.get(k)) || 0, 0);

  return (
    <div className="grid" style={{ gridTemplateColumns: '1fr' }}>
      <div className="hero">
        <div className="card hero-truck">
          <div className="spread">
            <div className="hero-readout">
              <span className="hero-speed">{fmt(speed, 0)}</span>
              <span className="hero-unit">MPH</span>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="val yellow" style={{ fontSize: 44, fontWeight: 800 }}>{gearLabel(t.get(T.gear))}</div>
              <StatusChip on={adasOn} labelOn="OPENPILOT ENGAGED" labelOff="OPENPILOT READY" />
            </div>
          </div>

          <RivianTruck speed={speed} sasquatch={sasquatch} glow charging={charging} />

          <div className="row" style={{ justifyContent: 'center', marginTop: 6 }}>
            <button className={`opt-btn ${sasquatch ? 'sel' : ''}`} onClick={() => setSasquatch((s) => !s)}>
              🦶 Sasquatch {sasquatch ? 'ON' : 'OFF'}
            </button>
          </div>

          <div className="corner-wheels">
            <div className="corner"><div className="label">FL</div><div className="v">{corner(T.wsFL)}</div></div>
            <div className="corner"><div className="label">FR</div><div className="v">{corner(T.wsFR)}</div></div>
            <div className="corner"><div className="label">RL</div><div className="v">{corner(T.wsRL)}</div></div>
            <div className="corner"><div className="label">RR</div><div className="v">{corner(T.wsRR)}</div></div>
          </div>

          <div className="row" style={{ justifyContent: 'center', marginTop: 14, gap: 24 }}>
            <div className={`blinker l ${bool(t.get(T.leftBlinker)) ? 'on' : ''}`} />
            <span style={{ color: 'var(--text-faint)', fontSize: 12, letterSpacing: 1 }}>SIGNALS</span>
            <div className={`blinker r ${bool(t.get(T.rightBlinker)) ? 'on' : ''}`} />
          </div>
        </div>

        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', alignContent: 'start' }}>
          <div className="card" style={{ gridColumn: '1 / -1', display: 'grid', placeItems: 'center' }}>
            <Ring value={t.get(T.soc)} label="State of Charge" tone="var(--teal)" />
          </div>
          <Tile label="Cruise Set" value={fmt(t.get(T.cruiseSpeed), 0)} unit=" mph" tone="yellow" />
          <Tile label="Lead Gap" value={hasLead ? fmt(lead, 1) : '—'} unit={hasLead ? ' m' : ''} tone="blue" />
          <Tile label="Accel" value={fmt(t.get(T.aEgo), 2)} unit=" m/s²" />
          <Tile label="Ignition" value={bool(t.get(T.ignition)) ? 'ON' : 'OFF'} tone={bool(t.get(T.ignition)) ? 'teal' : 'dim'} />
        </div>
      </div>
    </div>
  );
}
