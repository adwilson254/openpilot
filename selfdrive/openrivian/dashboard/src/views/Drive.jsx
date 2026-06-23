import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { useTrip, hms } from '../lib/trip';
import { T, fmt, bool, gearLabel } from '../lib/format';
import RivianTruck from '../components/RivianTruck';
import { Tile, StatusChip, Ring } from '../components/widgets';

export default function Drive() {
  const t = useTelemetry();
  const p = usePrefs();
  const { trip, reset } = useTrip();
  const speedMph = Number(t.get(T.speed_mph, 0)) || 0;
  const spd = p.speed(speedMph);
  const adasOn = bool(t.get(T.adasActive)) || bool(t.get(T.adasEnabled));
  const lead = t.get(T.leadDist);
  const hasLead = typeof lead === 'number' && lead >= 0;
  const cruise = p.speed(Number(t.get(T.cruiseSpeed, 0)) || 0);
  const tripDist = p.dist(trip.distMi);
  const tripMax = p.speed(trip.maxMph);
  const tripAvg = p.speed(trip.avgMph);
  const engagedPct = trip.durS > 0 ? (trip.engagedS / trip.durS) * 100 : 0;

  return (
    <div className="grid" style={{ gridTemplateColumns: '1fr' }}>
      <div className="hero">
        <div className="card hero-truck">
          <div className="spread">
            <div className="hero-readout">
              <span className="hero-speed">{fmt(spd.v, 0)}</span>
              <span className="hero-unit">{spd.u}</span>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="val yellow" style={{ fontSize: 44, fontWeight: 800 }}>{gearLabel(t.get(T.gear))}</div>
              <StatusChip on={adasOn} labelOn="OPENPILOT ENGAGED" labelOff="OPENPILOT READY" />
            </div>
          </div>
          <RivianTruck />
        </div>

        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', alignContent: 'start' }}>
          <div className="card" style={{ gridColumn: '1 / -1', display: 'grid', placeItems: 'center' }}>
            <Ring value={t.get(T.soc)} label="State of Charge" tone="var(--teal)" />
          </div>
          <Tile label="Cruise Set" value={fmt(cruise.v, 0)} unit={` ${cruise.u}`} tone="yellow" />
          <Tile label="Lead Gap" value={hasLead ? fmt(lead, 1) : '—'} unit={hasLead ? ' m' : ''} tone="blue"
                spark={t.getHistory(T.leadDist)} sparkColor="var(--blue)" />
          <Tile label="Accel" value={fmt(t.get(T.aEgo), 2)} unit=" m/s²"
                spark={t.getHistory(T.aEgo)} sparkColor="var(--teal)" />
          <Tile label="Ignition" value={bool(t.get(T.ignition)) ? 'ON' : 'OFF'} tone={bool(t.get(T.ignition)) ? 'teal' : 'dim'} />
        </div>
      </div>

      <div className="card">
        <div className="spread">
          <h2 style={{ margin: 0 }}>This Drive</h2>
          <button className="opt-btn" onClick={reset}>Reset</button>
        </div>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', marginTop: 12 }}>
          <div className="tile"><span className="label">Distance</span><span className="val">{fmt(tripDist.v, 1)}<small> {tripDist.u}</small></span></div>
          <div className="tile"><span className="label">Duration</span><span className="val">{hms(trip.durS)}</span></div>
          <div className="tile"><span className="label">Avg</span><span className="val">{fmt(tripAvg.v, 0)}<small> {tripAvg.u}</small></span></div>
          <div className="tile"><span className="label">Max</span><span className="val yellow">{fmt(tripMax.v, 0)}<small> {tripMax.u}</small></span></div>
          <div className="tile"><span className="label">Engaged</span><span className="val teal">{fmt(engagedPct, 0)}<small>%</small></span></div>
        </div>
      </div>
    </div>
  );
}
