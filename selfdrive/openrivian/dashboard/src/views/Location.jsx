import { useEffect, useMemo, useRef, useState } from 'react';
import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { T, fmt } from '../lib/format';
import { TILE, lon2fx, lat2fy, fx2lon, fy2lat, mi } from '../lib/geo';
import { planRoute, navProgress } from '../lib/nav';
import { hms } from '../lib/trip';

const TILE_URL = 'https://tile.openstreetmap.org';
const DEFAULT = [37.7749, -122.4194];

export default function MapView() {
  const t = useTelemetry();
  const p = usePrefs();
  const lat = Number(t.get(T.lat));
  const lon = Number(t.get(T.lon));
  const bearing = Number(t.get(T.bearing, 0)) || 0;
  const hasFix = Number.isFinite(lat) && Number.isFinite(lon);

  const wrapRef = useRef(null);
  const [size, setSize] = useState({ w: 640, h: 440 });
  const [zoom, setZoom] = useState(13);
  const [dest, setDest] = useState(null);
  const [nav, setNav] = useState(null);
  const [routing, setRouting] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    const el = wrapRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const center = hasFix ? [lat, lon] : DEFAULT;
  const z = zoom, w = size.w, h = size.h;
  const originX = lon2fx(center[1], z) * TILE - w / 2;
  const originY = lat2fy(center[0], z) * TILE - h / 2;
  const project = (la, lo) => [lon2fx(lo, z) * TILE - originX, lat2fy(la, z) * TILE - originY];

  const tiles = [];
  const ntiles = 2 ** z;
  for (let tx = Math.floor(originX / TILE); tx <= Math.floor((originX + w) / TILE); tx++) {
    for (let ty = Math.floor(originY / TILE); ty <= Math.floor((originY + h) / TILE); ty++) {
      if (ty < 0 || ty >= ntiles) continue;
      const wx = ((tx % ntiles) + ntiles) % ntiles;
      tiles.push({ key: `${tx}_${ty}`, x: tx * TILE - originX, y: ty * TILE - originY, url: `${TILE_URL}/${z}/${wx}/${ty}.png` });
    }
  }

  const routeTo = async (to) => {
    const from = [Number(t.get(T.lat)), Number(t.get(T.lon))];
    if (!Number.isFinite(from[0])) { setErr('No GPS fix yet'); return; }
    setRouting(true); setErr('');
    try {
      setNav(await planRoute('valhalla', { valhallaBase: p.valhalla, from, to }));
    } catch (e) { setErr(String(e.message || e)); setNav(null); }
    finally { setRouting(false); }
  };

  const onMapClick = (e) => {
    const r = wrapRef.current.getBoundingClientRect();
    const la = fy2lat((originY + (e.clientY - r.top)) / TILE, z);
    const lo = fx2lon((originX + (e.clientX - r.left)) / TILE, z);
    setDest([la, lo]); routeTo([la, lo]);
  };

  const prog = useMemo(() => (nav && hasFix ? navProgress(nav, [lat, lon]) : null), [nav, hasFix, lat, lon]);

  // trail from history (zip lat/lon by index)
  const lats = t.getHistory(T.lat), lons = t.getHistory(T.lon);
  const trail = [];
  for (let i = Math.max(0, lats.length - lons.length); i < lats.length; i++) {
    const lo = lons[lons.length - (lats.length - i)];
    if (lo !== undefined) trail.push(project(lats[i], lo));
  }

  const destPx = dest ? project(dest[0], dest[1]) : null;
  const routePx = nav ? nav.route.map(([la, lo]) => project(la, lo)) : null;
  const remMi = prog ? p.dist(mi(prog.distanceRemainingM)) : null;
  const toNext = prog ? p.dist(mi(prog.distToNextM)) : null;

  return (
    <div className="grid" style={{ gridTemplateColumns: '1fr', gap: 16 }}>
      <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
        <div ref={wrapRef} className="map-wrap" onClick={onMapClick}>
          <div className="map-tiles">
            {tiles.map((t2) => (
              <img key={t2.key} className="map-tile" src={t2.url} alt="" width={TILE} height={TILE}
                   style={{ transform: `translate(${t2.x}px, ${t2.y}px)` }} draggable={false} />
            ))}
          </div>
          <svg className="map-ovl" viewBox={`0 0 ${w} ${h}`} width={w} height={h}>
            {trail.length > 1 && (
              <polyline points={trail.map((q) => q.join(',')).join(' ')} fill="none" stroke="var(--blue)" strokeOpacity="0.5" strokeWidth="3" />
            )}
            {routePx && (
              <>
                <polyline points={routePx.map((q) => q.join(',')).join(' ')} fill="none" stroke="#0b0c0e" strokeWidth="8" strokeLinejoin="round" strokeLinecap="round" />
                <polyline points={routePx.map((q) => q.join(',')).join(' ')} fill="none" stroke="var(--teal)" strokeWidth="5" strokeLinejoin="round" strokeLinecap="round" />
              </>
            )}
            {destPx && (
              <g transform={`translate(${destPx[0]}, ${destPx[1]})`}>
                <path d="M0 0 C-9 -16 -9 -26 0 -26 C9 -26 9 -16 0 0 Z" fill="var(--yellow)" stroke="#0b0c0e" strokeWidth="1.5" />
                <circle cx="0" cy="-18" r="3.5" fill="#0b0c0e" />
              </g>
            )}
            <g transform={`translate(${w / 2}, ${h / 2}) rotate(${bearing})`}>
              <circle r="11" fill="rgba(54,182,255,0.25)" />
              <path d="M0 -12 L8 9 L0 4 L-8 9 Z" fill="var(--blue)" stroke="#fff" strokeWidth="1.2" />
            </g>
          </svg>

          <div className="map-controls">
            <button className="icon-btn" onClick={(e) => { e.stopPropagation(); setZoom((v) => Math.min(18, v + 1)); }}>+</button>
            <button className="icon-btn" onClick={(e) => { e.stopPropagation(); setZoom((v) => Math.max(3, v - 1)); }}>−</button>
          </div>
          <div className="map-attr">© OpenStreetMap · routing: Valhalla</div>
          {!hasFix && <div className="map-hint">No GPS fix — showing default location</div>}
        </div>
      </div>

      {/* Nav panel */}
      <div className="card">
        <div className="spread">
          <h2 style={{ margin: 0 }}>Navigation</h2>
          <div className="row">
            {dest && <button className="opt-btn" onClick={() => { setDest(null); setNav(null); setErr(''); }}>Clear</button>}
            {dest && <button className="opt-btn sel" onClick={() => routeTo(dest)} disabled={routing}>{routing ? 'Routing…' : 'Re-route'}</button>}
          </div>
        </div>
        {!dest && <p style={{ color: 'var(--text-faint)', marginTop: 10 }}>Tap the map to drop a destination and route there with Valhalla.</p>}
        {err && <p style={{ color: 'var(--red)', marginTop: 10 }}>Routing error: {err}</p>}
        {nav && prog && (
          <>
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', marginTop: 12 }}>
              <div className="tile"><span className="label">Remaining</span><span className="val">{fmt(remMi.v, 1)}<small> {remMi.u}</small></span></div>
              <div className="tile"><span className="label">ETA</span><span className="val">{hms(nav.summary.timeS)}</span></div>
              <div className="tile"><span className="label">Next in</span><span className="val yellow">{fmt(toNext.v, 1)}<small> {toNext.u}</small></span></div>
            </div>
            <div className="card" style={{ marginTop: 12, background: 'var(--surface-2)' }}>
              <div className="setting-title">{prog.next ? prog.next.instruction : 'Arriving'}</div>
            </div>
            <div style={{ maxHeight: 220, overflowY: 'auto', marginTop: 8 }}>
              {nav.maneuvers.map((m, i) => (
                <div className="spread" key={i} style={{ padding: '8px 2px', borderBottom: '1px solid var(--line-soft)' }}>
                  <span style={{ fontSize: 14 }}>{m.instruction}</span>
                  <span className="sig-age">{fmt(p.dist(mi(m.distanceM)).v, 1)} {p.dist(0).u}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Compass + coords */}
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <div className="card" style={{ display: 'grid', placeItems: 'center' }}>
          <svg viewBox="0 0 120 120" width="120" height="120">
            <circle cx="60" cy="60" r="54" fill="none" stroke="var(--surface-3)" strokeWidth="3" />
            <g transform={`rotate(${bearing} 60 60)`} style={{ transition: 'transform 0.4s' }}>
              <path d="M60 18 L70 70 L60 62 L50 70 Z" fill="var(--yellow)" />
            </g>
            <text x="60" y="14" fill="var(--text-faint)" fontSize="11" fontWeight="800" textAnchor="middle">N</text>
          </svg>
          <div className="tile" style={{ alignItems: 'center' }}><span className="label">Heading</span><span className="val">{fmt(bearing, 0)}<small>°</small></span></div>
        </div>
        <div className="tile card"><span className="label">Latitude</span><span className="val">{hasFix ? fmt(lat, 5) : '—'}</span></div>
        <div className="tile card"><span className="label">Longitude</span><span className="val">{hasFix ? fmt(lon, 5) : '—'}</span></div>
      </div>
    </div>
  );
}
