import { useTelemetry } from '../lib/mqtt';
import { T, bool } from '../lib/format';
import { IconWarn } from '../lib/icons';

/* Mirrors the car screen's openpilot alert (alert_text1/2 + status from
   selfdriveState) as a floating banner, styled by severity. Renders nothing
   when the car shows nothing. */
export function OpenpilotAlert() {
  const t = useTelemetry();
  const text1 = String(t.get(T.alert1, '') || '').trim();
  const text2 = String(t.get(T.alert2, '') || '').trim();
  const status = String(t.get(T.alertStatus, 'normal') || 'normal');
  if (!text1 && !text2) return null;
  const cls = status === 'critical' ? 'critical' : status === 'userPrompt' ? 'userPrompt' : '';
  return (
    <div className={`alert-banner ${cls}`} role="alert">
      <IconWarn size={22} aria-hidden="true" />
      <div>
        {text1 && <div className="t1">{text1}</div>}
        {text2 && <div className="t2">{text2}</div>}
      </div>
    </div>
  );
}

/* Derived, dashboard-local cautions from signals we already publish (inline list
   used by scrolling views). Renders nothing when all clear. */
export default function Alerts() {
  const t = useTelemetry();
  const speed = Number(t.get(T.speed_mph, 0)) || 0;
  const moving = speed > 1;
  const temp = Number(t.get(T.cpuTemp));
  const fs = Number(t.get(T.freeSpace));
  const demoted = bool(t.get(T.healthDemoted));
  const commIssue = bool(t.get(T.healthCommIssue));

  const alerts = [];
  if (demoted) alerts.push('openpilot processes demoted (scheduling health tripped)');
  if (commIssue) alerts.push('inter-process communication issue on the comma');
  if (moving && bool(t.get(T.doorOpen))) alerts.push('Door open while moving');
  if (moving && bool(t.get(T.seatbelt))) alerts.push('Seatbelt unlatched');
  if (!Number.isNaN(temp) && temp >= 85) alerts.push(`High device temp ${temp.toFixed(0)}°C`);
  if (!Number.isNaN(fs) && fs < 10) alerts.push(`Low storage ${fs.toFixed(0)}%`);

  if (!alerts.length) return null;
  return (
    <div className="alerts">
      {alerts.map((msg, i) => (
        <div key={i} className="alert"><IconWarn size={17} aria-hidden="true" />{msg}</div>
      ))}
    </div>
  );
}
