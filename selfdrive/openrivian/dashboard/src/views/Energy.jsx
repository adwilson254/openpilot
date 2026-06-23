import { useTelemetry } from '../lib/mqtt';
import { T, fmt, bool } from '../lib/format';
import { Tile, Ring, StatusChip } from '../components/widgets';

export default function Energy() {
  const t = useTelemetry();
  const charging = bool(t.get(T.charging));
  const soc = t.get(T.soc);
  return (
    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      <div className="card" style={{ gridColumn: 'span 2', display: 'grid', placeItems: 'center', minWidth: 0 }}>
        <Ring value={soc} label="State of Charge" tone={charging ? 'var(--teal)' : 'var(--yellow)'} size={240} />
        <StatusChip on={charging} labelOn="CHARGING" labelOff="NOT CHARGING" />
      </div>
      <Tile label="Pack Voltage (12V)" value={fmt(t.get(T.voltage), 1)} unit=" V" />
      <Tile label="Device Power Draw" value={fmt(t.get(T.powerDraw), 1)} unit=" W" />
      <Tile label="Ignition" value={bool(t.get(T.ignition)) ? 'ON' : 'OFF'} tone={bool(t.get(T.ignition)) ? 'teal' : 'dim'} />
      <Tile label="Speed" value={fmt(t.get(T.speed_mph), 0)} unit=" mph" />

      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h2>Not yet wired</h2>
        <p style={{ color: 'var(--text-faint)', fontSize: 14, margin: 0 }}>
          Charge rate and range estimate aren't published yet — SOC/charging depend on the
          Rivian car port decoding them, and charge rate is the diagnosed <code>0x550</code> signal.
          These tiles light up automatically once <code>cereal2mqtt</code> publishes them.
        </p>
      </div>
    </div>
  );
}
