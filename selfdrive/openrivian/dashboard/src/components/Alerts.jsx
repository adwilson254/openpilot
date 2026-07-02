import { useTelemetry } from '../lib/mqtt';
import { T, bool } from '../lib/format';

// Surfaces actionable conditions from signals we already publish. Renders nothing
// when all clear.
export default function Alerts() {
  const t = useTelemetry();
  const speed = Number(t.get(T.speed_mph, 0)) || 0;
  const moving = speed > 1;
  const temp = Number(t.get(T.cpuTemp));
  const fs = Number(t.get(T.freeSpace));

  const alerts = [];
  if (moving && bool(t.get(T.doorOpen))) alerts.push(['warn', 'Door open while moving']);
  if (moving && bool(t.get(T.seatbelt))) alerts.push(['warn', 'Seatbelt unlatched']);
  if (bool(t.get(T.leftBlinker)) && bool(t.get(T.leftBsm))) alerts.push(['caution', 'Vehicle in left blind spot']);
  if (bool(t.get(T.rightBlinker)) && bool(t.get(T.rightBsm))) alerts.push(['caution', 'Vehicle in right blind spot']);
  if (!Number.isNaN(temp) && temp >= 85) alerts.push(['warn', `High device temp ${temp.toFixed(0)}°C`]);
  if (!Number.isNaN(fs) && fs < 10) alerts.push(['warn', `Low storage ${fs.toFixed(0)}%`]);

  if (!alerts.length) return null;
  return (
    <div className="alerts">
      {alerts.map(([lvl, msg], i) => (
        <div key={i} className={`alert ${lvl}`}><span>⚠</span>{msg}</div>
      ))}
    </div>
  );
}
