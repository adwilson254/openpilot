import { useMemo, useState } from 'react';
import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { T, fmt } from '../lib/format';
import { mi } from '../lib/geo';
import { planRoute, navProgress } from '../lib/nav';
import { hms } from '../lib/trip';
import MapCanvas from '../components/MapCanvas';
import { ManeuverIcon, IconPin, IconClose } from '../lib/icons';

/* The Map tab: interactive full-bleed map.
   Tap to drop a destination -> Valhalla route -> turn card + maneuver list.
   All floating panels live inside the content row (never over strip/dock). */

export default function MapTab() {
  const t = useTelemetry();
  const p = usePrefs();
  const lat = Number(t.get(T.lat));
  const lon = Number(t.get(T.lon));
  const hasFix = Number.isFinite(lat) && Number.isFinite(lon);

  const [dest, setDest] = useState(null);
  const [nav, setNav] = useState(null);
  const [etaAt, setEtaAt] = useState(null); // arrival Date, fixed at route time
  const [routing, setRouting] = useState(false);
  const [err, setErr] = useState('');
  const [listOpen, setListOpen] = useState(false);

  const routeTo = async (to) => {
    if (!hasFix) { setErr('No GPS fix yet'); return; }
    setRouting(true); setErr('');
    try {
      const planned = await planRoute('valhalla', { valhallaBase: p.valhalla, from: [lat, lon], to });
      setNav(planned);
      setEtaAt(new Date(Date.now() + planned.summary.timeS * 1000));
    } catch (e) { setErr(String(e.message || e)); setNav(null); setEtaAt(null); }
    finally { setRouting(false); }
  };
  const onPick = (pt) => { setDest(pt); routeTo(pt); };
  const clearAll = () => { setDest(null); setNav(null); setEtaAt(null); setErr(''); setListOpen(false); };

  const prog = useMemo(
    () => (nav && hasFix ? navProgress(nav, [lat, lon]) : null),
    [nav, hasFix, lat, lon],
  );
  const remaining = prog ? p.dist(mi(prog.distanceRemainingM)) : null;
  const toNext = prog ? p.dist(mi(prog.distToNextM)) : null;

  return (
    <MapCanvas interactive trail nav={nav} dest={dest} onPick={onPick}>
      <div className="drive-cards">
        {/* active guidance card */}
        {nav && prog && (
          <section className="card turncard" aria-label="Next maneuver">
            {prog.next
              ? <ManeuverIcon type={prog.next.type} size={48} style={{ color: 'var(--yellow)' }} aria-hidden="true" />
              : <IconPin size={48} style={{ color: 'var(--yellow)' }} aria-hidden="true" />}
            <div className="dist">{toNext ? fmt(toNext.v, 1) : '—'} <small>{toNext?.u.toUpperCase()}</small></div>
            <div className="street">{prog.next ? prog.next.instruction : 'Arriving'}</div>
            <div className="eta">
              <span><b>{hms(nav.summary.timeS)}</b></span>
              <span><b>{remaining ? fmt(remaining.v, 1) : '—'}</b> {remaining?.u}</span>
              {etaAt && <span>arrive <b>{etaAt.getHours() % 12 || 12}:{String(etaAt.getMinutes()).padStart(2, '0')}</b></span>}
            </div>
            <div className="row" style={{ gridColumn: '1 / -1', marginTop: 10 }}>
              <button className="opt-btn" onClick={() => setListOpen((v) => !v)} aria-expanded={listOpen}>
                {listOpen ? 'Hide turns' : 'All turns'}
              </button>
              <button className="opt-btn" onClick={() => routeTo(dest)} disabled={routing}>{routing ? 'Routing…' : 'Re-route'}</button>
              <button className="opt-btn" onClick={clearAll} aria-label="End navigation"><IconClose size={16} /></button>
            </div>
          </section>
        )}

        {/* maneuver list */}
        {nav && listOpen && (
          <section className="card" aria-label="All maneuvers"
                   style={{ position: 'absolute', right: 'calc(clamp(14px, 2vw, 28px) + 68px)', top: 244, bottom: 16, width: 'clamp(250px, 20vw, 300px)', overflowY: 'auto' }}>
            {nav.maneuvers.map((m, i) => {
              const d = p.dist(mi(m.distanceM));
              return (
                <div className="spread" key={i} style={{ padding: '10px 2px', borderBottom: '1px solid var(--line-soft)' }}>
                  <span className="row" style={{ gap: 10, flexWrap: 'nowrap' }}>
                    <ManeuverIcon type={m.type} size={18} style={{ color: 'var(--text-dim)', flexShrink: 0 }} aria-hidden="true" />
                    <span style={{ fontSize: 13.5, fontWeight: 600 }}>{m.instruction}</span>
                  </span>
                  <span className="sig-age" style={{ whiteSpace: 'nowrap' }}>{fmt(d.v, 1)} {d.u}</span>
                </div>
              );
            })}
          </section>
        )}

        {/* idle hint / status */}
        {!nav && (
          <div className="tripchips" role="status">
            <span className="chip"><IconPin size={13} aria-hidden="true" />{routing ? 'ROUTING…' : 'TAP THE MAP TO SET A DESTINATION'}</span>
            {err && <span className="chip caution">{err.toUpperCase()}</span>}
          </div>
        )}
        {nav && err && (
          <div className="tripchips" role="status"><span className="chip caution">{err.toUpperCase()}</span></div>
        )}
      </div>
    </MapCanvas>
  );
}
