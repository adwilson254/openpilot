import { useState } from 'react';
import { useTelemetry } from '../lib/mqtt';
import { ageLabel, fmt } from '../lib/format';
import { Sparkline } from '../components/widgets';

// Live, searchable explorer over EVERY received topic — the "dig in" view.
export default function Signals() {
  const t = useTelemetry();
  const [q, setQ] = useState('');

  const topics = Object.keys(t.signals)
    .filter((k) => !k.startsWith('openrivian/settings/'))
    .filter((k) => k.toLowerCase().includes(q.toLowerCase()))
    .sort();

  const display = (v) => (typeof v === 'number' ? fmt(v, 3) : typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v));

  return (
    <div>
      <input className="sig-search" placeholder={`Search ${Object.keys(t.signals).length} live signals…`}
             value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="card" style={{ padding: '8px 16px' }}>
        {topics.length === 0 && <div className="empty">No signals yet. Waiting for telemetry…</div>}
        {topics.map((k) => {
          const s = t.signals[k];
          const hist = t.getHistory(k);
          return (
            <div className="sig-row" key={k}>
              <div>
                <div className="sig-topic">{k.replace('openrivian/', '')}</div>
                <div className="sig-age">updated {ageLabel(s.ts)} ago</div>
              </div>
              <div className="sig-val">{display(s.value)}</div>
              <Sparkline data={hist} color={t.fresh(k) ? 'var(--teal)' : 'var(--text-faint)'} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
