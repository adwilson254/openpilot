import { useTelemetry } from '../lib/mqtt';
import { T, fmt } from '../lib/format';
import { Tile } from '../components/widgets';

export default function Location() {
  const t = useTelemetry();
  const lat = t.get(T.lat), lon = t.get(T.lon);
  const bearing = Number(t.get(T.bearing, 0)) || 0;
  const hasFix = typeof lat === 'number' && typeof lon === 'number';

  return (
    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      <div className="card" style={{ display: 'grid', placeItems: 'center', gap: 10 }}>
        <svg viewBox="0 0 160 160" width="190" height="190">
          <circle cx="80" cy="80" r="72" fill="none" stroke="var(--surface-3)" strokeWidth="3" />
          {['N', 'E', 'S', 'W'].map((d, i) => (
            <text key={d} x="80" y="22" fill={d === 'N' ? 'var(--yellow)' : 'var(--text-faint)'}
                  fontSize="14" fontWeight="800" textAnchor="middle"
                  transform={`rotate(${i * 90} 80 80)`}>{d}</text>
          ))}
          <g transform={`rotate(${bearing} 80 80)`} style={{ transition: 'transform 0.4s' }}>
            <path d="M80 34 L92 92 L80 82 L68 92 Z" fill="var(--yellow)" />
          </g>
          <circle cx="80" cy="80" r="5" fill="var(--text)" />
        </svg>
        <div className="tile" style={{ alignItems: 'center' }}>
          <span className="label">Heading</span>
          <span className="val">{fmt(bearing, 0)}<small>°</small></span>
        </div>
      </div>

      <Tile label="Latitude" value={hasFix ? fmt(lat, 5) : '—'} />
      <Tile label="Longitude" value={hasFix ? fmt(lon, 5) : '—'} />
      <Tile label="Altitude" value={fmt(t.get(T.alt), 0)} unit=" m" />

      {hasFix && (
        <div className="card" style={{ gridColumn: '1 / -1' }}>
          <a className="plain" href={`https://maps.google.com/?q=${lat},${lon}`} target="_blank" rel="noreferrer">
            Open current location in Maps ↗
          </a>
        </div>
      )}
    </div>
  );
}
