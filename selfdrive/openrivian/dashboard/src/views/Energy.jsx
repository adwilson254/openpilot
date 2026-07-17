import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { T, fmt, bool } from '../lib/format';
import { Tile, Ring, StatusChip } from '../components/widgets';

export default function Energy() {
  const t = useTelemetry();
  const p = usePrefs();
  const charging = bool(t.get(T.charging));
  const soc = t.get(T.soc);
  const sp = p.speed(Number(t.get(T.speed_mph, 0)) || 0);
  return (
    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      <div className="card" style={{ gridColumn: 'span 2', display: 'grid', placeItems: 'center', minWidth: 0 }}>
        <Ring value={soc} label="State of Charge" tone={charging ? 'var(--teal)' : 'var(--yellow)'} size={240} />
        <StatusChip on={charging} labelOn="CHARGING" labelOff="NOT CHARGING" />
      </div>
      <Tile label="Battery (Rivian Cloud)" value={fmt(t.get(T.energySoc), 0)} unit=" %" />
      <Tile label="Range (Rivian Cloud)" value={fmt(t.get(T.energyRange), 0)} unit=" mi" />
      <Tile label="Charger" value={t.get(T.energyCharger, '—')} />
      <Tile label="12V Battery" value={fmt(t.get(T.voltage), 1)} unit=" V" />
      <Tile label="Device Power Draw" value={fmt(t.get(T.powerDraw), 1)} unit=" W" />
      <Tile label="Ignition" value={bool(t.get(T.ignition)) ? 'ON' : 'OFF'} tone={bool(t.get(T.ignition)) ? 'teal' : 'dim'} />
      <Tile label="Speed" value={fmt(sp.v, 0)} unit={` ${sp.u}`} />

      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h2>Sources</h2>
        <p style={{ color: 'var(--text-faint)', fontSize: 14, margin: 0 }}>
          The big ring uses the CAN-decoded state of charge when the car port publishes it.
          Battery/Range/Charger tiles come from the Rivian cloud API via <code>openriviand</code>
          (updates about once a minute when logged in — log in from the car's OpenRivian settings
          panel). Charge rate from CAN (<code>0x550</code>) is still to be decoded.
        </p>
      </div>
    </div>
  );
}
