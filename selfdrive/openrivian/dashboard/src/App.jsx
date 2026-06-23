import { useState } from 'react';
import './theme.css';
import { useTelemetry } from './lib/mqtt';
import { usePrefs } from './lib/prefs';
import Alerts from './components/Alerts';
import Drive from './views/Drive';
import Vehicle from './views/Vehicle';
import Energy from './views/Energy';
import Camp from './views/Camp';
import Adas from './views/Adas';
import Location from './views/Location';
import Device from './views/Device';
import Drives from './views/Drives';
import Signals from './views/Signals';
import Settings from './views/Settings';

const TABS = [
  { id: 'drive', label: 'Drive', icon: '🚙', view: Drive },
  { id: 'vehicle', label: 'Vehicle', icon: '🛞', view: Vehicle },
  { id: 'energy', label: 'Energy', icon: '⚡', view: Energy },
  { id: 'camp', label: 'Camp', icon: '🔥', view: Camp },
  { id: 'adas', label: 'ADAS', icon: '🛰️', view: Adas },
  { id: 'map', label: 'Map', icon: '📍', view: Location },
  { id: 'device', label: 'Device', icon: '🖥️', view: Device },
  { id: 'drives', label: 'Drives', icon: '🛣️', view: Drives },
  { id: 'signals', label: 'Signals', icon: '📈', view: Signals },
  { id: 'settings', label: 'Settings', icon: '⚙️', view: Settings },
];

function ConnBadge() {
  const { status } = useTelemetry();
  if (status === 'sim') return <span className="badge"><span className="dot" style={{ background: 'var(--yellow)' }} /> Simulated</span>;
  const live = status === 'live';
  return (
    <span className="badge">
      <span className={`dot ${live ? 'live' : 'off'}`} />
      {live ? 'Live' : status === 'connecting' ? 'Connecting…' : 'Offline'}
    </span>
  );
}

function AppSettings({ onClose }) {
  const { units, setUnits, host, setHost } = usePrefs();
  const [draft, setDraft] = useState(host);
  const save = () => { setHost(draft.trim()); window.location.reload(); };
  return (
    <>
      <div className="app-settings-backdrop" onClick={onClose} />
      <div className="app-settings card">
        <div className="setting-title" style={{ marginBottom: 10 }}>App Settings</div>
        <label className="label">Comma host / IP</label>
        <div className="row" style={{ margin: '6px 0 16px' }}>
          <input className="sig-search" style={{ margin: 0 }} placeholder={window.location.hostname}
                 value={draft} onChange={(e) => setDraft(e.target.value)} />
          <button className="opt-btn sel" onClick={save}>Save</button>
        </div>
        <label className="label">Units</label>
        <div className="row" style={{ marginTop: 6 }}>
          <button className={`opt-btn ${units === 'imperial' ? 'sel' : ''}`} onClick={() => setUnits('imperial')}>Imperial</button>
          <button className={`opt-btn ${units === 'metric' ? 'sel' : ''}`} onClick={() => setUnits('metric')}>Metric</button>
        </div>
      </div>
    </>
  );
}

export default function App() {
  const [tab, setTab] = useState('drive');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const current = TABS.find((t) => t.id === tab) || TABS[0];
  const View = current.view;

  return (
    <div className="app">
      <nav className="rail">
        <div className="brand">
          <div className="brand-mark">R</div>
          <div className="brand-name">OpenRivian<small>COMPANION</small></div>
        </div>
        {TABS.map((t) => (
          <button key={t.id} className={`nav-btn ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            <span className="nav-ic">{t.icon}</span>{t.label}
          </button>
        ))}
      </nav>

      <div className="main">
        <header className="topbar">
          <h1>{current.label}</h1>
          <div className="row">
            <ConnBadge />
            <button className="icon-btn" title="App settings" onClick={() => setSettingsOpen((v) => !v)}>⚙</button>
          </div>
        </header>
        {settingsOpen && <AppSettings onClose={() => setSettingsOpen(false)} />}
        <main className="content">
          <Alerts />
          <View />
        </main>
      </div>

      <nav className="tabbar">
        {TABS.map((t) => (
          <button key={t.id} className={`tb ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            <span className="nav-ic">{t.icon}</span>{t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
