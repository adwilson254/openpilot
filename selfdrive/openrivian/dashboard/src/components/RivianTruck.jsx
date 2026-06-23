// Stylized R1T side profile. Wheels spin with speed; "sasquatch" raises the body and
// swaps to chunky off-road tires; headlight/charge glow reflects state. Pure SVG/CSS.
function Wheel({ cx, tire, moving, spin, sasquatch }) {
  return (
    <g transform={`translate(${cx}, ${150 + (sasquatch ? 6 : 0)})`}>
      <circle r={tire} className="tire" />
      <circle r={tire - 9} className="rim" />
      <g className="spokes" style={moving ? { animation: `spin ${spin}s linear infinite` } : undefined}>
        {[0, 60, 120, 180, 240, 300].map((a) => (
          <rect key={a} x={-2.2} y={-(tire - 12)} width={4.4} height={tire - 16} rx={2}
                transform={`rotate(${a})`} className="spoke" />
        ))}
        <circle r={6} className="hub" />
      </g>
    </g>
  );
}

export default function RivianTruck({ speed = 0, sasquatch = false, glow = false, charging = false }) {
  const spin = Math.max(0.18, 1.6 - Math.min(Math.abs(speed), 90) / 60); // seconds/rev
  const moving = Math.abs(speed) > 0.5;
  const lift = sasquatch ? -14 : 0;
  const tire = sasquatch ? 44 : 36;

  return (
    <div className={`truck-stage ${glow ? 'glow' : ''}`}>
      <svg viewBox="0 0 460 220" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3a4049" />
            <stop offset="1" stopColor="#21262d" />
          </linearGradient>
          <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2b3a47" />
            <stop offset="1" stopColor="#11161b" />
          </linearGradient>
        </defs>

        {/* terrain / road */}
        <line x1="10" y1="196" x2="450" y2="196" className={`ground ${sasquatch ? 'rugged' : ''}`} />

        <g transform={`translate(0, ${lift})`}>
          {/* bed + cab body */}
          <path d="M40 150 L40 118 Q40 110 50 110 L150 110 L188 74 Q193 68 202 68 L300 68
                   Q310 68 313 76 L330 110 L410 116 Q424 118 424 132 L424 150 Z"
                fill="url(#body)" stroke="#454c55" strokeWidth="1.5" />
          {/* cabin glass */}
          <path d="M196 78 L290 78 Q297 78 300 84 L312 108 L196 108 Z" fill="url(#glass)" />
          {/* bed line */}
          <line x1="150" y1="112" x2="150" y2="150" stroke="#1a1e23" strokeWidth="2" />
          {/* signature vertical headlight bar */}
          <rect x="414" y="120" width="8" height="20" rx="3" className="headlight" />
          {/* roof rack hint */}
          <line x1="200" y1="70" x2="288" y2="70" stroke="#4a525c" strokeWidth="3" strokeLinecap="round" />
          {/* charge port glow */}
          {charging && <circle cx="58" cy="126" r="7" className="charge-port" />}
        </g>

        <Wheel cx={110} tire={tire} moving={moving} spin={spin} sasquatch={sasquatch} />
        <Wheel cx={360} tire={tire} moving={moving} spin={spin} sasquatch={sasquatch} />
      </svg>
    </div>
  );
}
