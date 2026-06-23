import { fmt } from '../lib/format';

export function Tile({ label, value, unit, tone = '', sub, spark, sparkColor }) {
  return (
    <div className="card tile">
      <span className="label">{label}</span>
      <span className={`val ${tone}`}>
        {value}{unit && <small>{unit}</small>}
      </span>
      {sub && <span style={{ color: 'var(--text-faint)', fontSize: 13 }}>{sub}</span>}
      {spark && spark.length > 1 && (
        <div style={{ marginTop: 4 }}>
          <Sparkline data={spark} color={sparkColor || 'var(--text-faint)'} width={130} height={26} />
        </div>
      )}
    </div>
  );
}

export function StatusChip({ on, labelOn, labelOff, warn }) {
  const cls = warn ? 'warn' : on ? 'on' : 'off';
  return <span className={`pill ${cls}`}>{on ? labelOn : labelOff}</span>;
}

// Radial SOC / percentage ring
export function Ring({ value, label, unit = '%', tone = 'var(--teal)', size = 200 }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  const r = 80, c = 2 * Math.PI * r;
  const has = value !== undefined && value !== null && !Number.isNaN(Number(value));
  return (
    <div style={{ width: size, height: size, position: 'relative' }}>
      <svg viewBox="0 0 200 200" width="100%" height="100%">
        <circle cx="100" cy="100" r={r} fill="none" stroke="var(--surface-3)" strokeWidth="14" />
        <circle cx="100" cy="100" r={r} fill="none" stroke={tone} strokeWidth="14"
                strokeLinecap="round" strokeDasharray={c}
                strokeDashoffset={has ? c * (1 - pct / 100) : c}
                transform="rotate(-90 100 100)"
                style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center' }}>
        <div>
          <div style={{ fontSize: 40, fontWeight: 800, fontVariantNumeric: 'tabular-nums' }}>
            {has ? fmt(value, 0) : '—'}<span style={{ fontSize: 18, color: 'var(--text-dim)' }}>{has ? unit : ''}</span>
          </div>
          <div style={{ fontSize: 12, letterSpacing: 1.5, color: 'var(--text-faint)', fontWeight: 700, textTransform: 'uppercase' }}>{label}</div>
        </div>
      </div>
    </div>
  );
}

export function Sparkline({ data = [], color = 'var(--teal)', width = 90, height = 28 }) {
  if (!data || data.length < 2) return <svg width={width} height={height} />;
  const min = Math.min(...data), max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / span) * (height - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg width={width} height={height}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.8"
                strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
