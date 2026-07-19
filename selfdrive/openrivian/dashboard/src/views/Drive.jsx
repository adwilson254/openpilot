import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { useTrip } from '../lib/trip';
import { T, fmt, bool } from '../lib/format';
import { GearStrip } from '../components/widgets';
import MapCanvas from '../components/MapCanvas';
import { IconRecenter } from '../lib/icons';

/* The Drive canvas: full-bleed map with floating cards.
   - Cards live in fixed corners inside the content row (the dock and status
     strip are separate grid rows), so nothing can render over the chrome.
   - data-density="driving" (set on the shell at >5 mph) enlarges the speed and
     hides the parked-only chips via CSS.
   - Read-only surface: the only interactive element here is the trip reset,
     deliberately small-surface; panning/destinations live in the Map tab. */

export default function Drive() {
  const t = useTelemetry();
  const p = usePrefs();
  const { trip, reset } = useTrip();

  const speedMph = Number(t.get(T.speed_mph, 0)) || 0;
  const spd = p.speed(speedMph);
  const enabled = bool(t.get(T.adasEnabled));
  const active = bool(t.get(T.adasActive));
  const cruiseAvail = bool(t.get(T.cruiseAvail));
  const cruiseSet = Number(t.get(T.cruiseSpeed));
  const cruise = p.speed(Number.isFinite(cruiseSet) && cruiseSet > 0 ? cruiseSet : undefined);
  const personality = t.get(T.personality);
  const lead = t.get(T.leadDist);
  const hasLead = typeof lead === 'number' && lead >= 0;
  const leadV = t.get(T.leadVRel);
  const tripDist = p.dist(trip.distMi);
  const engagedPct = trip.durS > 0 ? (trip.engagedS / trip.durS) * 100 : 0;

  const bandState = active ? 'on' : enabled ? 'on' : cruiseAvail ? 'ready' : 'off';
  const bandLabel = active || enabled ? 'PILOT ENGAGED' : cruiseAvail ? 'PILOT READY' : 'PILOT OFFLINE';
  const bandSub = active || enabled ? 'lateral + longitudinal' : cruiseAvail ? 'set cruise to engage' : 'no vehicle';

  return (
    <MapCanvas interactive={false} autoZoom>
      <div className="drive-cards">
        {/* trip chips (parked density only, via CSS) */}
        <div className="tripchips">
          <span className="chip">TRIP {fmt(tripDist.v, 1)} {tripDist.u.toUpperCase()}</span>
          <span className="chip"><span className="dot" style={{ background: 'var(--teal)' }} />{fmt(engagedPct, 0)}% PILOTED</span>
          <button className="chip" style={{ cursor: 'pointer' }} onClick={reset} aria-label="Reset trip">
            <IconRecenter size={13} aria-hidden="true" />RESET
          </button>
        </div>

        {/* speed cluster */}
        <section className="card cluster" aria-label="Speed and pilot status">
          <div className="speed-row">
            <div className="speed">{fmt(spd.v, 0, '0')}</div>
            <div className="speed-unit">
              <b>{spd.u.toUpperCase()}</b>
              <GearStrip gear={t.get(T.gear)} />
            </div>
          </div>
          <div className="cluster-meta">
            <span className="statchip"><small>SET</small> {cruise.v !== undefined ? fmt(cruise.v, 0) : '—'}</span>
            {personality && <span className="statchip"><span className="dot" style={{ background: 'var(--teal)' }} /><small>{String(personality).toUpperCase()}</small></span>}
          </div>
          <div className={`engaged-band ${bandState}`}>
            <b>{bandLabel}</b>
            <span>{bandSub}</span>
          </div>
        </section>

        {/* lead vehicle */}
        {hasLead && (
          <section className="card leadcard" aria-label="Lead vehicle">
            <div className="microlabel">Lead vehicle</div>
            <div className="gap">
              <b>{fmt(lead, 0)}</b>
              <span>M{typeof leadV === 'number' ? ` · ${leadV >= 0 ? 'OPENING' : 'CLOSING'} ${fmt(Math.abs(leadV) * 2.23694, 0)} MPH` : ''}</span>
            </div>
            <svg viewBox="0 0 164 56" aria-hidden="true" style={{ width: '100%', marginTop: 6 }}>
              <path d="M28 56 L70 6 M136 56 L94 6" stroke="var(--line)" strokeWidth="2" fill="none" strokeLinecap="round" />
              <rect x="70" y="12" width="24" height="12" rx="4" fill="var(--teal)" opacity="0.9" />
              <path d="M58 50 L106 50" stroke="var(--text-faint)" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </section>
        )}

        {/* blindspot edge flashes */}
        {bool(t.get(T.leftBsm)) && <div className="bs-edge left" aria-hidden="true" />}
        {bool(t.get(T.rightBsm)) && <div className="bs-edge right" aria-hidden="true" />}
      </div>
    </MapCanvas>
  );
}
