import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useTelemetry } from '../lib/mqtt';
import { T } from '../lib/format';
import {
  TILE, lon2fx, lat2fy, fx2lon, fy2lat,
  tileUrl, tileFallbackUrl, tileSpan, zoomForSpeed,
} from '../lib/geo';
import { IconPlus, IconMinus, IconRecenter } from '../lib/icons';

/*
  MapCanvas — the shared slippy-tile renderer.

  Architecture (why it glides instead of stepping):
  - Tiles mount in an anchored "world" layer whose coordinates are relative to an
    anchor tile (small numbers -> no float-precision artifacts at high zoom).
  - The camera is a ref, not state. A requestAnimationFrame loop lerps it toward
    its target (the truck in follow mode, the drag position otherwise) and writes
    the world layer's transform DIRECTLY on the DOM. React renders only when the
    visible tile set or overlays change, never per frame.
  - GPS arrives at 10 Hz; the lerp interpolates between fixes.

  Modes:
  - follow (default): camera tracks the truck; optional speed-based auto-zoom.
  - free: after a drag, follow disengages and the re-center control appears.

  Tiles come from the comma's own caching proxy (/tiles/...); a failed tile
  swaps once to the public OSM server (covers `vite dev` without the proxy).
  Dark cartography is a CSS filter on the tile layer (see theme.css tokens).
*/

const LERP = 0.18;                 // camera smoothing per frame
const DEFAULT_POS = { lat: 37.7749, lon: -122.4194 };

export default function MapCanvas({
  interactive = true,
  autoZoom = false,
  trail = false,
  nav = null,
  dest = null,
  onPick = null,
  children = null,
}) {
  const t = useTelemetry();
  const lat = Number(t.get(T.lat));
  const lon = Number(t.get(T.lon));
  const bearing = Number(t.get(T.bearing, 0)) || 0;
  const speedMph = Number(t.get(T.speed_mph, 0)) || 0;
  const hasFix = Number.isFinite(lat) && Number.isFinite(lon);

  const wrapRef = useRef(null);
  const worldRef = useRef(null);
  const markerRef = useRef(null);

  const [size, setSize] = useState({ w: 800, h: 500 });
  const [zoom, setZoom] = useState(15);
  const [follow, setFollow] = useState(true);
  const [anchor, setAnchor] = useState(null); // {z, ax, ay} anchor tile indices
  const [trailTick, setTrailTick] = useState(0);

  // Latest inputs for the rAF loop, without re-subscribing it ("latest ref"
  // pattern; written post-render in an effect to keep render pure).
  const stateRef = useRef({});
  useEffect(() => {
    stateRef.current = { lat, lon, hasFix, follow, zoom, size, autoZoom, speedMph, bearing };
  });

  // Camera position (fractional tile coords at current zoom) + its target.
  const camRef = useRef(null);
  const targetRef = useRef(null);
  const anchorRef = useRef(null);

  // Initialize camera/anchor on first fix or zoom change.
  useEffect(() => {
    const pos = hasFix ? { lat, lon } : DEFAULT_POS;
    const fx = lon2fx(pos.lon, zoom), fy = lat2fy(pos.lat, zoom);
    if (!camRef.current || camRef.current.z !== zoom) {
      // preserve geographic camera position across zoom changes
      const geo = camRef.current
        ? { lat: fy2lat(camRef.current.fy, camRef.current.z), lon: fx2lon(camRef.current.fx, camRef.current.z) }
        : pos;
      camRef.current = { fx: lon2fx(geo.lon, zoom), fy: lat2fy(geo.lat, zoom), z: zoom };
      targetRef.current = follow ? { fx, fy } : { fx: camRef.current.fx, fy: camRef.current.fy };
      setAnchor({ z: zoom, ax: Math.floor(camRef.current.fx), ay: Math.floor(camRef.current.fy) });
    }
  }, [zoom, hasFix]); // eslint-disable-line react-hooks/exhaustive-deps

  // Viewport size tracking.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const measure = () => setSize({ w: el.clientWidth || 800, h: el.clientHeight || 500 });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // The animation loop: lerp camera -> write transform. No React work per frame.
  useEffect(() => {
    let raf;
    const step = () => {
      raf = requestAnimationFrame(step);
      const s = stateRef.current;
      const cam = camRef.current;
      if (!cam || !worldRef.current) return;

      if (s.follow && s.hasFix) {
        targetRef.current = { fx: lon2fx(s.lon, cam.z), fy: lat2fy(s.lat, cam.z) };
      }
      const tgt = targetRef.current;
      if (tgt) {
        cam.fx += (tgt.fx - cam.fx) * LERP;
        cam.fy += (tgt.fy - cam.fy) * LERP;
      }

      const a = anchorRef.current;
      if (!a || a.z !== cam.z) return;
      const px = s.size.w / 2 - (cam.fx - a.ax) * TILE;
      const py = s.size.h / 2 - (cam.fy - a.ay) * TILE;
      worldRef.current.style.transform = `translate3d(${px.toFixed(2)}px, ${py.toFixed(2)}px, 0)`;

      // Truck marker lives in world coords; rotate to heading.
      if (markerRef.current && s.hasFix) {
        const mx = (lon2fx(s.lon, cam.z) - a.ax) * TILE;
        const my = (lat2fy(s.lat, cam.z) - a.ay) * TILE;
        markerRef.current.style.transform = `translate(${mx.toFixed(2)}px, ${my.toFixed(2)}px) rotate(${s.bearing.toFixed(1)}deg)`;
      }

      // Re-anchor when the camera strays: keeps tile coords small & tiles fresh.
      if (Math.abs(cam.fx - a.ax) > 2.5 || Math.abs(cam.fy - a.ay) > 2.5) {
        setAnchor({ z: cam.z, ax: Math.floor(cam.fx), ay: Math.floor(cam.fy) });
      }
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, []);

  useEffect(() => { anchorRef.current = anchor; }, [anchor]);

  // Speed-based auto zoom (Drive canvas): only while following.
  useEffect(() => {
    if (!autoZoom || !follow) return undefined;
    const id = setInterval(() => {
      const z = zoomForSpeed(stateRef.current.speedMph);
      setZoom((cur) => (cur === z ? cur : z));
    }, 3000);
    return () => clearInterval(id);
  }, [autoZoom, follow]);

  // Trail overlay refresh (slow tick; history lives in refs).
  useEffect(() => {
    if (!trail) return undefined;
    const id = setInterval(() => setTrailTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [trail]);

  /* ------------------------- interaction ------------------------- */
  const pointers = useRef(new Map());
  const dragState = useRef(null);

  const onPointerDown = (e) => {
    if (!interactive) return;
    wrapRef.current.setPointerCapture?.(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 1) {
      dragState.current = { x: e.clientX, y: e.clientY, moved: false };
    }
  };
  const onPointerMove = (e) => {
    if (!interactive || !pointers.current.has(e.pointerId)) return;
    const prev = pointers.current.get(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pointers.current.size === 1 && dragState.current) {
      const dx = e.clientX - prev.x, dy = e.clientY - prev.y;
      if (Math.abs(e.clientX - dragState.current.x) + Math.abs(e.clientY - dragState.current.y) > 6) {
        dragState.current.moved = true;
        setFollow(false);
      }
      if (dragState.current.moved && camRef.current) {
        const cam = camRef.current;
        targetRef.current = {
          fx: (targetRef.current?.fx ?? cam.fx) - dx / TILE,
          fy: (targetRef.current?.fy ?? cam.fy) - dy / TILE,
        };
      }
    } else if (pointers.current.size === 2) {
      // pinch: discrete zoom steps on threshold (raster tiles zoom in steps)
      const pts = [...pointers.current.values()];
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      const st = dragState.current || {};
      if (st.pinchStart == null) { st.pinchStart = dist; dragState.current = st; }
      else if (dist / st.pinchStart > 1.35) { setZoom((z) => Math.min(19, z + 1)); st.pinchStart = dist; }
      else if (dist / st.pinchStart < 0.74) { setZoom((z) => Math.max(3, z - 1)); st.pinchStart = dist; }
    }
  };
  const onPointerUp = (e) => {
    if (!interactive) return;
    pointers.current.delete(e.pointerId);
    const st = dragState.current;
    if (pointers.current.size === 0 && st && !st.moved && onPick && camRef.current && anchorRef.current) {
      // tap -> geographic coordinates
      const r = wrapRef.current.getBoundingClientRect();
      const cam = camRef.current;
      const fx = cam.fx + (e.clientX - r.left - size.w / 2) / TILE;
      const fy = cam.fy + (e.clientY - r.top - size.h / 2) / TILE;
      onPick([fy2lat(fy, cam.z), fx2lon(fx, cam.z)]);
    }
    if (pointers.current.size === 0) dragState.current = null;
  };
  const onWheel = (e) => {
    if (!interactive) return;
    e.preventDefault();
    setZoom((z) => Math.max(3, Math.min(19, z + (e.deltaY < 0 ? 1 : -1))));
  };

  const recenter = useCallback(() => {
    setFollow(true);
    if (autoZoom) setZoom(zoomForSpeed(stateRef.current.speedMph));
  }, [autoZoom]);

  /* ------------------------- render ------------------------- */
  const tiles = useMemo(() => {
    if (!anchor) return [];
    const cols = tileSpan(size.w), rows = tileSpan(size.h);
    const n = 2 ** anchor.z;
    const out = [];
    for (let dx = -Math.floor(cols / 2); dx <= Math.ceil(cols / 2); dx++) {
      for (let dy = -Math.floor(rows / 2); dy <= Math.ceil(rows / 2); dy++) {
        const tx = anchor.ax + dx, ty = anchor.ay + dy;
        if (ty < 0 || ty >= n) continue;
        const wx = ((tx % n) + n) % n;
        out.push({ key: `${anchor.z}/${tx}/${ty}`, x: (tx - anchor.ax) * TILE, y: (ty - anchor.ay) * TILE, z: anchor.z, wx, wy: ty });
      }
    }
    return out;
  }, [anchor, size.w, size.h]);

  // World-pixel projection relative to the anchor (small numbers).
  const proj = useCallback((la, lo) => {
    if (!anchor) return [0, 0];
    return [(lon2fx(lo, anchor.z) - anchor.ax) * TILE, (lat2fy(la, anchor.z) - anchor.ay) * TILE];
  }, [anchor]);

  const routePts = useMemo(() => {
    if (!nav?.route || !anchor) return null;
    return nav.route.map(([la, lo]) => proj(la, lo).map((v) => v.toFixed(1)).join(',')).join(' ');
  }, [nav, anchor, proj]);

  const trailPts = useMemo(() => {
    if (!trail || !anchor) return null;
    const lats = t.getHistory(T.lat), lons = t.getHistory(T.lon);
    const m = Math.min(lats.length, lons.length);
    if (m < 2) return null;
    return Array.from({ length: m }, (_, i) => {
      const la = lats[lats.length - m + i], lo = lons[lons.length - m + i];
      return proj(la, lo).map((v) => v.toFixed(1)).join(',');
    }).join(' ');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trail, anchor, proj, trailTick]);

  const destPt = dest && anchor ? proj(dest[0], dest[1]) : null;

  const onTileError = (e) => {
    const img = e.currentTarget;
    if (img.dataset.fb) { img.style.visibility = 'hidden'; return; }
    img.dataset.fb = '1';
    const [z, x, y] = img.dataset.tile.split('/');
    img.src = tileFallbackUrl(z, x, y);
  };

  return (
    <div
      ref={wrapRef}
      className={`mapc ${interactive ? 'interactive' : ''}`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onWheel={onWheel}
      role={interactive ? 'application' : 'img'}
      aria-label={interactive ? 'Map. Drag to pan, tap to set a destination.' : 'Map centered on vehicle'}
    >
      <div ref={worldRef} className="mapc-world">
        <div className="mapc-tiles">
          {tiles.map(($) => (
            <img
              key={$.key} className="mapc-tile" alt=""
              style={{ transform: `translate(${$.x}px, ${$.y}px)` }}
              data-tile={`${$.z}/${$.wx}/${$.wy}`}
              src={tileUrl($.z, $.wx, $.wy)}
              onError={onTileError}
              draggable={false} loading="lazy" decoding="async"
            />
          ))}
        </div>
        <svg className="mapc-ovl" width="1" height="1" aria-hidden="true">
          {trailPts && <polyline points={trailPts} fill="none" stroke="var(--blue)" strokeOpacity="0.55" strokeWidth="3" />}
          {routePts && (
            <>
              <polyline points={routePts} fill="none" stroke="var(--canvas)" strokeWidth="10" strokeLinejoin="round" strokeLinecap="round" strokeOpacity="0.85" />
              <polyline points={routePts} fill="none" stroke="var(--yellow)" strokeWidth="5.5" strokeLinejoin="round" strokeLinecap="round" />
            </>
          )}
          {destPt && (
            <g transform={`translate(${destPt[0]}, ${destPt[1]})`}>
              <path d="M0 0 C-10 -18 -10 -29 0 -29 C10 -29 10 -18 0 0 Z" fill="var(--yellow)" stroke="var(--canvas)" strokeWidth="2" />
              <circle cx="0" cy="-20" r="4" fill="var(--canvas)" />
            </g>
          )}
        </svg>
        <div ref={markerRef} className="mapc-marker" style={{ visibility: hasFix ? 'visible' : 'hidden' }} aria-hidden="true">
          <svg viewBox="0 0 44 44">
            <path d="M22 5 L35 38 L22 30 L9 38 Z" fill="var(--yellow)" stroke="var(--canvas)" strokeWidth="2.5" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="mapc-tint" />

      {interactive && (
        <div className="mapc-controls">
          <button className="icon-btn" onClick={() => setZoom((z) => Math.min(19, z + 1))} aria-label="Zoom in"><IconPlus size={22} /></button>
          <button className="icon-btn" onClick={() => setZoom((z) => Math.max(3, z - 1))} aria-label="Zoom out"><IconMinus size={22} /></button>
          {!follow && (
            <button className="icon-btn" onClick={recenter} aria-label="Re-center on vehicle"><IconRecenter size={22} /></button>
          )}
        </div>
      )}
      <div className="mapc-attr">© OpenStreetMap contributors</div>
      {!hasFix && <div className="mapc-hint">No GPS fix — showing default area</div>}
      {children}
    </div>
  );
}
