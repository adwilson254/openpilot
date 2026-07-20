import { useState, useEffect } from 'react';

export default function Drives() {
  const [routes, setRoutes] = useState([]);
  const [state, setState] = useState('loading'); // loading | ok | error
  const [err, setErr] = useState('');

  useEffect(() => {
    fetch('/routes')
      .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then((data) => {
        data.sort((a, b) => new Date(b.date) - new Date(a.date));
        setRoutes(data); setState('ok');
      })
      .catch((e) => { setErr(e.message); setState('error'); });
  }, []);

  const total = routes.reduce((s, r) => s + (r.size_mb || 0), 0);

  return (
    <div className="grid" style={{ gridTemplateColumns: '1fr' }}>
      <div className="card">
        <div className="spread">
          <h2 style={{ margin: 0 }}>Drive History</h2>
          {state === 'ok' && <span className="pill on">{routes.length} routes · {(total / 1024).toFixed(1)} GB</span>}
        </div>
      </div>

      {state === 'loading' && <div className="empty">Loading routes…</div>}
      {state === 'error' && <div className="empty" style={{ color: 'var(--red)' }}>Could not load routes ({err})</div>}
      {state === 'ok' && routes.length === 0 && <div className="empty">No routes recorded on this device yet.</div>}

      {state === 'ok' && routes.map((r) => (
        <div className="card spread" key={r.id} style={{ padding: 16 }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 17 }}>{r.date}</div>
            <div style={{ color: 'var(--text-faint)', fontSize: 12, fontFamily: 'ui-monospace, monospace', marginTop: 4 }}>{r.id}</div>
          </div>
          <span className="pill off" style={{ fontVariantNumeric: 'tabular-nums' }}>{r.size_mb} MB</span>
        </div>
      ))}
    </div>
  );
}
