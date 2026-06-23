import { useState } from 'react';
import { useTelemetry } from '../lib/mqtt';
import { ageLabel, fmt } from '../lib/format';
import { Sparkline } from '../components/widgets';

const loadPins = () => { try { return JSON.parse(localStorage.getItem('orv.pins') || '[]'); } catch { return []; } };
const display = (v) => (typeof v === 'number' ? fmt(v, 3) : typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v));

function SigRow({ topic, sig, hist, fresh, pinned, onPin }) {
  return (
    <div className="sig-row">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <button className={`pin ${pinned ? 'on' : ''}`} onClick={() => onPin(topic)} title="Pin">{pinned ? '★' : '☆'}</button>
        <div style={{ minWidth: 0 }}>
          <div className="sig-topic">{topic.replace('openrivian/', '')}</div>
          <div className="sig-age">updated {ageLabel(sig.ts)} ago</div>
        </div>
      </div>
      <div className="sig-val">{display(sig.value)}</div>
      <Sparkline data={hist} color={fresh ? 'var(--teal)' : 'var(--text-faint)'} />
    </div>
  );
}

export default function Signals() {
  const t = useTelemetry();
  const [q, setQ] = useState('');
  const [pins, setPins] = useState(loadPins);
  const [collapsed, setCollapsed] = useState({});

  const togglePin = (k) => setPins((prev) => {
    const next = prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k];
    try { localStorage.setItem('orv.pins', JSON.stringify(next)); } catch { /* noop */ }
    return next;
  });
  const toggleGroup = (g) => setCollapsed((c) => ({ ...c, [g]: !c[g] }));

  const topics = Object.keys(t.signals)
    .filter((k) => !k.startsWith('openrivian/settings/'))
    .filter((k) => k.toLowerCase().includes(q.toLowerCase()));

  const groups = {};
  topics.forEach((k) => { const seg = k.split('/')[1] || 'other'; (groups[seg] = groups[seg] || []).push(k); });
  Object.values(groups).forEach((a) => a.sort());
  const groupNames = Object.keys(groups).sort();
  const pinned = topics.filter((k) => pins.includes(k)).sort();

  const exportJson = () => {
    const snap = {};
    Object.entries(t.signals).forEach(([k, v]) => { snap[k] = v.value; });
    const blob = new Blob([JSON.stringify(snap, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `openrivian-signals-${Date.now()}.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const row = (k) => (
    <SigRow key={k} topic={k} sig={t.signals[k]} hist={t.getHistory(k)} fresh={t.fresh(k)}
            pinned={pins.includes(k)} onPin={togglePin} />
  );

  return (
    <div>
      <div className="row" style={{ gap: 10, marginBottom: 16 }}>
        <input className="sig-search" style={{ margin: 0, flex: 1 }}
               placeholder={`Search ${topics.length} live signals…`} value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="opt-btn" onClick={exportJson}>Export JSON</button>
      </div>

      {topics.length === 0 && <div className="empty">Waiting for telemetry…</div>}

      {pinned.length > 0 && (
        <div className="card" style={{ padding: '8px 16px', marginBottom: 16 }}>
          <div className="sig-group" style={{ cursor: 'default' }}>★ Pinned</div>
          {pinned.map(row)}
        </div>
      )}

      {groupNames.map((g) => (
        <div className="card" key={g} style={{ padding: '8px 16px', marginBottom: 12 }}>
          <div className="sig-group" onClick={() => toggleGroup(g)}>
            <span>{collapsed[g] ? '▸' : '▾'} {g}</span>
            <span className="sig-count">{groups[g].length}</span>
          </div>
          {!collapsed[g] && groups[g].map(row)}
        </div>
      ))}
    </div>
  );
}
