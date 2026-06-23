import { useTelemetry } from '../lib/mqtt';
import { T, fmt } from '../lib/format';

// Top-down following-distance scope: ego at the bottom, lead car positioned by gap,
// colored by closing rate (vRel < 0 = closing).
const MAX_M = 80;

export default function LeadScope() {
  const t = useTelemetry();
  const d = Number(t.get(T.leadDist));
  const vRel = Number(t.get(T.leadVRel)) || 0;
  const has = typeof d === 'number' && d >= 0 && !Number.isNaN(d);

  const egoY = 270;
  const leadY = egoY - (Math.min(Math.max(d, 0), MAX_M) / MAX_M) * 210;
  const color = !has ? 'var(--text-faint)' : vRel < -1 ? 'var(--red)' : vRel < 0 ? 'var(--amber)' : 'var(--teal)';
  const closing = vRel < -0.2 ? 'Closing' : vRel > 0.2 ? 'Opening' : 'Steady';

  return (
    <div className="card" style={{ display: 'grid', placeItems: 'center' }}>
      <h2 style={{ alignSelf: 'flex-start' }}>Following Distance</h2>
      <svg viewBox="0 0 200 300" width="190" height="285">
        <line x1="40" y1="0" x2="40" y2="300" stroke="#1c2026" strokeWidth="3" />
        <line x1="160" y1="0" x2="160" y2="300" stroke="#1c2026" strokeWidth="3" />
        {/* ego */}
        <rect x="84" y={egoY} width="32" height="24" rx="7" fill="#eef1f3" />
        {has && (
          <>
            <line x1="100" y1={egoY} x2="100" y2={leadY + 22} stroke={color} strokeWidth="2" strokeDasharray="4 6" />
            <rect x="84" y={leadY} width="32" height="22" rx="7" fill={color} />
            <text x="120" y={(egoY + leadY) / 2} fill={color} fontSize="16" fontWeight="800">{fmt(d, 0)} m</text>
          </>
        )}
        {!has && <text x="100" y="140" fill="var(--text-faint)" fontSize="13" textAnchor="middle">No lead detected</text>}
      </svg>
      <div className="row" style={{ gap: 16 }}>
        <span className="pill off">{has ? closing : '—'}</span>
        {has && <span style={{ color, fontWeight: 800 }}>{fmt(vRel, 1)} m/s</span>}
      </div>
    </div>
  );
}
