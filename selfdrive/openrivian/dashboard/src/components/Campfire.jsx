// Rivian "Camp Mode" style flickering campfire — layered SVG flames + rising embers.
export default function Campfire() {
  return (
    <div className="campfire">
      <svg viewBox="0 0 200 240" width="100%" height="100%">
        <defs>
          <radialGradient id="flameOuter" cx="50%" cy="75%" r="65%">
            <stop offset="0" stopColor="#ffd24d" />
            <stop offset="0.5" stopColor="#ff8a1e" />
            <stop offset="1" stopColor="#ff3b1e" stopOpacity="0.85" />
          </radialGradient>
          <radialGradient id="flameInner" cx="50%" cy="80%" r="60%">
            <stop offset="0" stopColor="#fff6cc" />
            <stop offset="1" stopColor="#ffb627" stopOpacity="0.9" />
          </radialGradient>
          <radialGradient id="halo" cx="50%" cy="60%" r="60%">
            <stop offset="0" stopColor="#ff8a1e" stopOpacity="0.35" />
            <stop offset="1" stopColor="#ff8a1e" stopOpacity="0" />
          </radialGradient>
        </defs>

        <ellipse cx="100" cy="150" rx="95" ry="80" fill="url(#halo)" />

        {/* embers */}
        {[...Array(7)].map((_, i) => (
          <circle key={i} className="ember" cx={70 + i * 10} cy={170}
                  r={1.5 + (i % 3) * 0.7}
                  style={{ animationDelay: `${i * 0.5}s`, animationDuration: `${2.4 + (i % 3) * 0.6}s` }} />
        ))}

        {/* outer flame */}
        <path className="flame flame-outer" fill="url(#flameOuter)"
              d="M100 40 C140 95 138 135 120 170 C150 160 150 120 150 120
                 C168 160 150 205 100 205 C50 205 32 160 50 120 C50 120 50 160 80 170
                 C62 135 60 95 100 40 Z" />
        {/* inner flame */}
        <path className="flame flame-inner" fill="url(#flameInner)"
              d="M100 95 C118 125 116 150 105 172 C124 165 122 140 122 140
                 C130 165 118 192 100 192 C82 192 70 165 78 140 C78 140 76 165 95 172
                 C84 150 82 125 100 95 Z" />

        {/* logs */}
        <g className="logs">
          <rect x="56" y="196" width="88" height="11" rx="5" transform="rotate(-9 100 201)" fill="#5a3a22" />
          <rect x="56" y="200" width="88" height="11" rx="5" transform="rotate(9 100 205)" fill="#6b4326" />
          <rect x="70" y="198" width="60" height="9" rx="4" fill="#7a4e2c" />
        </g>
      </svg>
    </div>
  );
}
