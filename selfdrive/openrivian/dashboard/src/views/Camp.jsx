import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { T, fmt, bool } from '../lib/format';
import Campfire from '../components/Campfire';
import { Tile } from '../components/widgets';

export default function Camp() {
  const t = useTelemetry();
  const p = usePrefs();
  const parked = bool(t.get(T.standstill)) || String(t.get(T.gear, '')).toLowerCase().includes('park');
  const tp = p.temp(Number(t.get(T.cpuTemp)));
  return (
    <div className="grid" style={{ gridTemplateColumns: '1fr' }}>
      <div className="card" style={{ textAlign: 'center', background: 'radial-gradient(600px 300px at 50% 90%, rgba(255,138,30,0.10), var(--surface))' }}>
        <h2 style={{ textAlign: 'center' }}>Camp Mode</h2>
        <Campfire />
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-dim)', marginTop: 6 }}>
          {parked ? 'Parked — enjoy the campfire' : 'Rolling…'}
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
        <Tile label="Battery" value={fmt(t.get(T.soc), 0)} unit="%" tone="teal" />
        <Tile label="12V" value={fmt(t.get(T.voltage), 1)} unit=" V" />
        <Tile label="Device Power" value={fmt(t.get(T.powerDraw), 1)} unit=" W" />
        <Tile label="CPU Temp" value={fmt(tp.v, 0)} unit={tp.u} tone="amber" />
        <Tile label="Cabin Gear" value={String(t.get(T.gear, '—')).toUpperCase().slice(0, 4)} tone="yellow" />
      </div>
    </div>
  );
}
