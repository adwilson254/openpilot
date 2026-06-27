import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { T, fmt, bool } from '../lib/format';
import { Tile, StatusChip } from '../components/widgets';

function SteeringWheel({ angle = 0 }) {
  return (
    <svg viewBox="0 0 120 120" width="150" height="150">
      <g className="steer-wheel" style={{ transform: `rotate(${angle}deg)` }}>
        <circle cx="60" cy="60" r="46" fill="none" stroke="var(--surface-3)" strokeWidth="9" />
        <circle cx="60" cy="60" r="46" fill="none" stroke="var(--yellow)" strokeWidth="9"
                strokeDasharray="6 290" transform="rotate(-90 60 60)" />
        <circle cx="60" cy="60" r="11" fill="var(--surface-3)" />
        <rect x="56" y="60" width="8" height="40" rx="4" fill="var(--surface-3)" />
        <rect x="22" y="56" width="34" height="8" rx="4" fill="var(--surface-3)" />
        <rect x="64" y="56" width="34" height="8" rx="4" fill="var(--surface-3)" />
      </g>
    </svg>
  );
}

export default function Vehicle() {
  const t = useTelemetry();
  const p = usePrefs();
  const angle = Number(t.get(T.steerAngle, 0)) || 0;
  const sp = p.speed(Number(t.get(T.speed_mph, 0)) || 0);
  return (
    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      <div className="card" style={{ display: 'grid', placeItems: 'center', gap: 8 }}>
        <SteeringWheel angle={angle} />
        <div className="tile" style={{ alignItems: 'center' }}>
          <span className="label">Steering Angle</span>
          <span className="val">{fmt(angle, 1)}<small>°</small></span>
        </div>
      </div>

      <Tile label="Steering Torque" value={fmt(t.get(T.steerTorque), 2)} />
      <Tile label="EPS Torque" value={fmt(t.get(T.steerTorqueEps), 2)} />
      <Tile label="Acceleration" value={fmt(t.get(T.aEgo), 2)} unit=" m/s²" />
      <Tile label="Speed" value={fmt(sp.v, 0)} unit={` ${sp.u}`} />
      <Tile label="Standstill" value={bool(t.get(T.standstill)) ? 'YES' : 'NO'} tone="dim" />

      <div className="card">
        <h2>Wheel Speeds</h2>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {[['FL', T.wsFL], ['FR', T.wsFR], ['RL', T.wsRL], ['RR', T.wsRR]].map(([k, topic]) => (
            <div className="corner" key={k}><div className="label">{k}</div><div className="v">{fmt(t.get(topic), 0)}</div></div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>Pedals & Body</h2>
        <div className="spread" style={{ padding: '8px 0' }}><span>Gas</span><StatusChip on={bool(t.get(T.gas))} labelOn="PRESSED" labelOff="—" /></div>
        <div className="spread" style={{ padding: '8px 0' }}><span>Brake</span><StatusChip on={bool(t.get(T.brake))} labelOn="PRESSED" labelOff="—" warn={bool(t.get(T.brake))} /></div>
        <div className="spread" style={{ padding: '8px 0' }}><span>Door</span><StatusChip on={bool(t.get(T.doorOpen))} labelOn="OPEN" labelOff="CLOSED" warn={bool(t.get(T.doorOpen))} /></div>
        <div className="spread" style={{ padding: '8px 0' }}><span>Seatbelt</span><StatusChip on={bool(t.get(T.seatbelt))} labelOn="UNLATCHED" labelOff="OK" warn={bool(t.get(T.seatbelt))} /></div>
      </div>

      <div className="card">
        <h2>Blind Spot</h2>
        <div className="spread" style={{ padding: '8px 0' }}><span>Left</span><StatusChip on={bool(t.get(T.leftBsm))} labelOn="VEHICLE" labelOff="CLEAR" warn={bool(t.get(T.leftBsm))} /></div>
        <div className="spread" style={{ padding: '8px 0' }}><span>Right</span><StatusChip on={bool(t.get(T.rightBsm))} labelOn="VEHICLE" labelOff="CLEAR" warn={bool(t.get(T.rightBsm))} /></div>
        <div className="spread" style={{ padding: '8px 0' }}><span>Blinkers</span>
          <span className="row">
            <span className={`blinker l ${bool(t.get(T.leftBlinker)) ? 'on' : ''}`} />
            <span className={`blinker r ${bool(t.get(T.rightBlinker)) ? 'on' : ''}`} />
          </span>
        </div>
      </div>
    </div>
  );
}
