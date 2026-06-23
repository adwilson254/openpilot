import { useTelemetry } from '../lib/mqtt';
import { T, fmt, bool } from '../lib/format';
import { Tile, Ring, StatusChip } from '../components/widgets';

export default function Device() {
  const t = useTelemetry();
  const temp = Number(t.get(T.cpuTemp));
  const tempTone = temp >= 85 ? 'red' : temp >= 70 ? 'amber' : 'teal';
  return (
    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      <div className="card" style={{ display: 'grid', placeItems: 'center' }}>
        <Ring value={t.get(T.mem)} label="Memory Used" tone="var(--blue)" />
      </div>
      <div className="card" style={{ display: 'grid', placeItems: 'center' }}>
        <Ring value={t.get(T.freeSpace)} label="Free Storage" tone="var(--teal)" />
      </div>
      <Tile label="CPU Temp" value={fmt(t.get(T.cpuTemp), 0)} unit="°C" tone={tempTone} />
      <Tile label="Panda Voltage" value={fmt(t.get(T.voltage), 1)} unit=" V" />
      <Tile label="Power Draw" value={fmt(t.get(T.powerDraw), 1)} unit=" W" />
      <div className="card">
        <h2>Processes</h2>
        <div className="spread" style={{ padding: '8px 0' }}><span>camerad</span><StatusChip on={bool(t.get(T.cameradRunning))} labelOn="RUNNING" labelOff="STOPPED" warn={!bool(t.get(T.cameradRunning))} /></div>
        <div className="spread" style={{ padding: '8px 0' }}><span>Ignition</span><StatusChip on={bool(t.get(T.ignition))} labelOn="ON" labelOff="OFF" /></div>
      </div>
    </div>
  );
}
