import { useTelemetry } from '../lib/mqtt';
import { T, fmt, bool } from '../lib/format';

// Top-down R1T silhouette, bound to live telemetry: front wheels steer with the wheel
// angle, per-corner wheel-speed labels, turn-signal corners blink, blind-spot side strips,
// brake bar glows, charge-port glows, and a center lane line scrolls with speed.
// Pure SVG/CSS — no images, no dependencies.
const Wheel = ({ cx, cy }) => (
  <rect x={cx - 13} y={cy - 27} width="26" height="54" rx="9" className="td-tire" />
);

const CornerSpeed = ({ x, y, value }) => (
  <g className="td-wlabel">
    <rect x={x - 18} y={y - 13} width="36" height="26" rx="8" />
    <text x={x} y={y}>{value}</text>
  </g>
);

export default function RivianTruck() {
  const t = useTelemetry();
  const speed = Number(t.get(T.speed_mph, 0)) || 0;
  const steer = Number(t.get(T.steerAngle, 0)) || 0;
  const vsteer = Math.max(-30, Math.min(30, steer * 0.35)); // visual front-wheel turn
  const moving = speed > 0.5;
  const laneDur = moving ? Math.max(0.3, 2.6 - speed / 40) : 0;
  const wheel = (k) => fmt(Number(t.get(k)) || 0, 0);

  const lBlink = bool(t.get(T.leftBlinker));
  const rBlink = bool(t.get(T.rightBlinker));
  const brake = bool(t.get(T.brake));
  const lBsm = bool(t.get(T.leftBsm));
  const rBsm = bool(t.get(T.rightBsm));
  const charging = bool(t.get(T.charging));

  return (
    <div className="td-stage">
      <svg viewBox="0 0 300 520" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="tdPaint" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#cfd4da" />
            <stop offset="0.5" stopColor="#ffffff" />
            <stop offset="1" stopColor="#cfd4da" />
          </linearGradient>
          <linearGradient id="tdGlass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2b3a47" />
            <stop offset="1" stopColor="#11161b" />
          </linearGradient>
          <filter id="tdGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="2.6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* road + scrolling lane line */}
        <line x1="14" y1="0" x2="14" y2="520" stroke="#1c2026" strokeWidth="3" />
        <line x1="286" y1="0" x2="286" y2="520" stroke="#1c2026" strokeWidth="3" />
        <line className="td-lane" x1="150" y1="-40" x2="150" y2="560" stroke="#3a4048" strokeWidth="6"
              strokeDasharray="22 30" style={{ animationDuration: `${laneDur}s`, animationPlayState: moving ? 'running' : 'paused' }} />

        {/* blind-spot side strips */}
        {lBsm && <rect className="td-bsm" x="40" y="150" width="7" height="230" rx="3.5" />}
        {rBsm && <rect className="td-bsm" x="253" y="150" width="7" height="230" rx="3.5" />}

        <g className="td-car">
          {/* wheels (rear fixed; front steer) */}
          <Wheel cx={72} cy={380} /><Wheel cx={228} cy={380} />
          <g transform={`rotate(${vsteer} 72 150)`}><Wheel cx={72} cy={150} /></g>
          <g transform={`rotate(${vsteer} 228 150)`}><Wheel cx={228} cy={150} /></g>

          {/* body */}
          <rect x="60" y="50" width="180" height="420" rx="38" fill="url(#tdPaint)" stroke="#aeb4bb" strokeWidth="1.5" />
          {/* hood crease */}
          <path d="M96 70 Q150 60 204 70" fill="none" stroke="#dfe3e7" strokeWidth="2" />
          {/* mirrors */}
          <rect x="44" y="176" width="16" height="11" rx="4" fill="#e7eaee" stroke="#aeb4bb" />
          <rect x="240" y="176" width="16" height="11" rx="4" fill="#e7eaee" stroke="#aeb4bb" />
          {/* panoramic glass roof */}
          <rect x="80" y="176" width="140" height="96" rx="20" fill="url(#tdGlass)" />
          {/* bed */}
          <rect x="74" y="286" width="152" height="170" rx="14" fill="#15171b" />
          <rect x="84" y="298" width="132" height="148" rx="9" fill="none" stroke="#23272e" strokeWidth="2" />
          <line x1="150" y1="300" x2="150" y2="444" stroke="#23272e" strokeWidth="1.5" />

          {/* front light bar + headlights */}
          <rect x="74" y="55" width="152" height="6" rx="3" fill="#ffffff" filter="url(#tdGlow)" />
          {/* rear tail bar */}
          <rect x="78" y="459" width="144" height="7" rx="3.5" fill={brake ? '#ff5252' : '#7a1f1f'}
                filter={brake ? 'url(#tdGlow)' : undefined} className={brake ? 'td-brake' : ''} />

          {/* turn-signal corners */}
          <rect className={`td-blink ${lBlink ? 'on' : ''}`} x="62" y="58" width="20" height="7" rx="3.5" />
          <rect className={`td-blink ${rBlink ? 'on' : ''}`} x="218" y="58" width="20" height="7" rx="3.5" />
          <rect className={`td-blink ${lBlink ? 'on' : ''}`} x="62" y="458" width="20" height="8" rx="4" />
          <rect className={`td-blink ${rBlink ? 'on' : ''}`} x="218" y="458" width="20" height="8" rx="4" />

          {/* charge port (front-left fender) */}
          {charging && <circle cx="66" cy="120" r="6" fill="#00d6a0" filter="url(#tdGlow)" className="td-charge" />}

          {/* per-corner wheel-speed labels, outboard of each wheel */}
          <CornerSpeed x={37} y={150} value={wheel(T.wsFL)} />
          <CornerSpeed x={263} y={150} value={wheel(T.wsFR)} />
          <CornerSpeed x={37} y={380} value={wheel(T.wsRL)} />
          <CornerSpeed x={263} y={380} value={wheel(T.wsRR)} />
        </g>
      </svg>
    </div>
  );
}
