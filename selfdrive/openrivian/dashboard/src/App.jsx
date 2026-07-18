import { useState, useEffect, useRef, useCallback } from 'react';
import './theme.css';
import { useTelemetry, ALIVE_TOPIC } from './lib/mqtt';
import { usePrefs } from './lib/prefs';
import { T, fmt, bool } from './lib/format';
import { isDaytime } from './lib/sun';
import {
  IconDrive, IconMap, IconEnergy, IconTruck, IconMore, IconGear, IconPulse,
  IconCamp, IconDrives, IconDevice, IconSignals, IconSettings, IconClose, IconChevronR,
} from './lib/icons';
import { OpenpilotAlert } from './components/Alerts';
import Drive from './views/Drive';
import MapTab from './views/Location';
import Energy from './views/Energy';
import Vehicle from './views/Vehicle';
import Camp from './views/Camp';
import Device from './views/Device';
import Drives from './views/Drives';
import Signals from './views/Signals';
import Settings from './views/Settings';

/* Information architecture:
   - Dock (always visible): Drive · Map · Energy · Truck · More
   - Drive/Map are full-bleed canvases; the rest scroll.
   - "More" opens a sheet with the secondary destinations. Everything remains
     hash-routable so deep links and the back button keep working. */

const DOCK = [
  { id: 'drive', label: 'DRIVE', icon: IconDrive, view: Drive, canvas: true },
  { id: 'map', label: 'MAP', icon: IconMap, view: MapTab, canvas: true },
  { id: 'energy', label: 'ENERGY', icon: IconEnergy, view: Energy },
  { id: 'truck', label: 'TRUCK', icon: IconTruck, view: Vehicle },
];
const MORE = [
  { id: 'camp', label: 'Camp Mode', icon: IconCamp, view: Camp },
  { id: 'drives', label: 'Drive History', icon: IconDrives, view: Drives },
  { id: 'device', label: 'Device Health', icon: IconDevice, view: Device },
  { id: 'signals', label: 'Signals Explorer', icon: IconSignals, view: Signals },
  { id: 'settings', label: 'Vehicle Settings', icon: IconSettings, view: Settings, hint: 'read-only' },
];
const ALL = [...DOCK, ...MORE];
const IDS = ALL.map((v) => v.id);
const LEGACY = { vehicle: 'truck', adas: 'drive', location: 'map' }; // old hash names

function initialTab() {
  const h = window.location.hash.replace('#', '');
  if (IDS.includes(h)) return h;
  if (LEGACY[h]) return LEGACY[h];
  try { const s = localStorage.getItem('orv.tab'); if (IDS.includes(s)) return s; } catch { /* noop */ }
  return 'drive';
}

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 5000);
    return () => clearInterval(id);
  }, []);
  let h = now.getHours();
  const ap = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  return <span className="clock">{h}:{String(now.getMinutes()).padStart(2, '0')} {ap}</span>;
}

function ConnBadge() {
  const t = useTelemetry();
  const { status } = t;
  if (status === 'sim') return <span className="chip"><span className="dot" style={{ background: 'var(--yellow)' }} /> SIMULATED</span>;
  const bridgeAlive = t.get(ALIVE_TOPIC);
  const live = status === 'live' && bridgeAlive !== false;
  const label = status === 'connecting' ? 'CONNECTING…'
    : status !== 'live' ? 'OFFLINE'
    : bridgeAlive === false ? 'BRIDGE DOWN' : 'LIVE';
  return (
    <span className={`chip ${label === 'BRIDGE DOWN' ? 'caution' : ''}`}>
      <span className={`dot ${live ? 'pulse' : 'off'}`} />{label}
    </span>
  );
}

function HealthChip() {
  const t = useTelemetry();
  const demoted = bool(t.get(T.healthDemoted));
  const comm = bool(t.get(T.healthCommIssue));
  if (demoted || comm) {
    return <span className="chip caution"><IconPulse size={14} aria-hidden="true" />{demoted ? 'SCHED' : 'COMM'} FAULT</span>;
  }
  return <span className="chip"><IconPulse size={14} aria-hidden="true" />SYSTEM OK</span>;
}

function SocPill() {
  const t = useTelemetry();
  const soc = t.get(T.energySoc, t.get(T.soc)); // cloud first, CAN when decoded
  const range = t.get(T.energyRange);
  const has = soc !== undefined && soc !== null;
  const pct = has ? Math.max(0, Math.min(100, Number(soc))) : 0;
  return (
    <span className="soc-pill" aria-label={has ? `Battery ${fmt(soc, 0)} percent` : 'Battery unknown'}>
      <span className="soc-bar"><i style={{ width: `${pct}%` }} /></span>
      {has ? `${fmt(soc, 0)}%` : '—'}
      {range !== undefined && range !== null && (
        <span style={{ color: 'var(--text-faint)', fontWeight: 700, fontSize: 12 }}>· {fmt(range, 0)} mi</span>
      )}
    </span>
  );
}

/* Sheet with basic focus management: focus moves in on open, Esc closes,
   backdrop is a real button. */
function Sheet({ title, onClose, children }) {
  const ref = useRef(null);
  useEffect(() => {
    const prev = document.activeElement;
    ref.current?.querySelector('button, input, [tabindex]')?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => { window.removeEventListener('keydown', onKey); prev?.focus?.(); };
  }, [onClose]);
  return (
    <>
      <button className="sheet-backdrop" onClick={onClose} aria-label="Close panel" />
      <div className="sheet" role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <div className="sheet-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><IconClose size={20} /></button>
        </div>
        <div className="sheet-body">{children}</div>
      </div>
    </>
  );
}

function AppSettingsSheet({ onClose }) {
  const { units, setUnits, host, setHost, valhalla, setValhalla, theme, setTheme } = usePrefs();
  const [draft, setDraft] = useState(host);
  const [vDraft, setVDraft] = useState(valhalla);
  const save = () => { setHost(draft.trim()); window.location.reload(); };
  return (
    <Sheet title="App Settings" onClose={onClose}>
      <div className="microlabel" style={{ marginBottom: 8 }}>Theme</div>
      <div className="seg" style={{ marginBottom: 20 }}>
        {['auto', 'day', 'night'].map((v) => (
          <button key={v} className={`opt-btn ${theme === v ? 'sel' : ''}`} onClick={() => setTheme(v)}>
            {v[0].toUpperCase() + v.slice(1)}
          </button>
        ))}
      </div>
      <div className="microlabel" style={{ marginBottom: 8 }}>Units</div>
      <div className="seg" style={{ marginBottom: 20 }}>
        <button className={`opt-btn ${units === 'imperial' ? 'sel' : ''}`} onClick={() => setUnits('imperial')}>Imperial</button>
        <button className={`opt-btn ${units === 'metric' ? 'sel' : ''}`} onClick={() => setUnits('metric')}>Metric</button>
      </div>
      <div className="microlabel" style={{ marginBottom: 8 }}>Comma host / IP</div>
      <div className="row" style={{ marginBottom: 20 }}>
        <input className="sig-search" style={{ margin: 0, flex: 1 }} placeholder={window.location.hostname}
               value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Comma host or IP" />
        <button className="opt-btn sel" onClick={save}>Save</button>
      </div>
      <div className="microlabel" style={{ marginBottom: 8 }}>Valhalla routing endpoint</div>
      <input className="sig-search" style={{ margin: 0 }} placeholder="https://valhalla1.openstreetmap.de"
             value={vDraft} onChange={(e) => setVDraft(e.target.value)} onBlur={() => setValhalla(vDraft.trim())}
             aria-label="Valhalla routing endpoint" />
    </Sheet>
  );
}

export default function App() {
  const t = useTelemetry();
  const prefs = usePrefs();
  const [tab, setTabState] = useState(initialTab);
  const [moreOpen, setMoreOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const current = ALL.find((v) => v.id === tab) || DOCK[0];
  const View = current.view;
  const inMore = MORE.some((v) => v.id === tab);

  const setTab = useCallback((id) => {
    setTabState(id);
    setMoreOpen(false);
    try { localStorage.setItem('orv.tab', id); } catch { /* noop */ }
  }, []);

  useEffect(() => {
    if (window.location.hash.replace('#', '') !== tab) window.location.hash = tab;
  }, [tab]);
  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash.replace('#', '');
      if (IDS.includes(h)) setTabState(h);
      else if (LEGACY[h]) setTabState(LEGACY[h]);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // Theme: manual pref wins; auto follows the sun at the truck's position.
  const lat = Number(t.get(T.lat)), lon = Number(t.get(T.lon));
  useEffect(() => {
    const apply = () => {
      const eff = prefs.theme === 'auto'
        ? (isDaytime(new Date(), lat, lon) ? 'day' : 'night')
        : prefs.theme;
      document.documentElement.dataset.theme = eff;
    };
    apply();
    const id = setInterval(apply, 60000);
    return () => clearInterval(id);
  }, [prefs.theme, lat, lon]);

  // Density: simplify the drive canvas while moving.
  const speed = Number(t.get(T.speed_mph, 0)) || 0;
  const density = speed > 5 ? 'driving' : 'parked';

  return (
    <div className="shell" data-density={density}>
      <header className="strip">
        <Clock />
        <ConnBadge />
        <HealthChip />
        <span className="spacer" />
        <SocPill />
        <button className="icon-btn" style={{ width: 52, height: 52 }} title="App settings"
                aria-label="App settings" onClick={() => setSettingsOpen(true)}>
          <IconGear size={24} />
        </button>
      </header>

      <OpenpilotAlert />
      <main className={`content ${current.canvas ? '' : 'scroll'}`}>
        <View />
      </main>

      <nav className="dock" aria-label="Primary">
        {DOCK.map((v) => {
          const Ic = v.icon;
          return (
            <button key={v.id} className={`dock-btn ${tab === v.id ? 'active' : ''}`}
                    aria-current={tab === v.id ? 'page' : undefined} onClick={() => setTab(v.id)}>
              <Ic aria-hidden="true" />{v.label}
            </button>
          );
        })}
        <button className={`dock-btn ${inMore || moreOpen ? 'active' : ''}`}
                aria-expanded={moreOpen} onClick={() => setMoreOpen(true)}>
          <IconMore aria-hidden="true" />MORE
        </button>
      </nav>

      {moreOpen && (
        <Sheet title="More" onClose={() => setMoreOpen(false)}>
          {MORE.map((v) => {
            const Ic = v.icon;
            return (
              <button key={v.id} className="sheet-item" onClick={() => setTab(v.id)}>
                <Ic size={22} aria-hidden="true" />
                <span className="grow">{v.label}</span>
                {v.hint && <span className="hint">{v.hint}</span>}
                <IconChevronR size={18} aria-hidden="true" />
              </button>
            );
          })}
        </Sheet>
      )}
      {settingsOpen && <AppSettingsSheet onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
