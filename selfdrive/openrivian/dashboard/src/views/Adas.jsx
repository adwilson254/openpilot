import { useTelemetry } from '../lib/mqtt';
import { usePrefs } from '../lib/prefs';
import { T, fmt, bool } from '../lib/format';
import { Tile, StatusChip } from '../components/widgets';
import LeadScope from '../components/LeadScope';

export default function Adas() {
  const t = useTelemetry();
  const p = usePrefs();
  const engaged = bool(t.get(T.adasActive)) || bool(t.get(T.adasEnabled));
  const lead = t.get(T.leadDist);
  const hasLead = typeof lead === 'number' && lead >= 0;
  const setSp = p.speed(Number(t.get(T.cruiseSpeed, 0)) || 0);
  const vSp = p.speed(Number(t.get(T.speed_mph, 0)) || 0);
  return (
    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      <div className="card" style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div className="label" style={{ color: 'var(--text-faint)', letterSpacing: 1.5, fontSize: 12, fontWeight: 700 }}>OPENPILOT</div>
          <div style={{ fontSize: 34, fontWeight: 800, color: engaged ? 'var(--teal)' : 'var(--text-dim)' }}>
            {engaged ? 'ENGAGED' : 'READY'}
          </div>
        </div>
        <StatusChip on={bool(t.get(T.cruiseAvail))} labelOn="CRUISE AVAILABLE" labelOff="CRUISE UNAVAIL" />
      </div>

      <LeadScope />

      <Tile label="Set Speed" value={fmt(setSp.v, 0)} unit={` ${setSp.u}`} tone="yellow" />
      <Tile label="Cruise Enabled" value={bool(t.get(T.cruiseEnabled)) ? 'YES' : 'NO'} tone={bool(t.get(T.cruiseEnabled)) ? 'teal' : 'dim'} />
      <Tile label="Lead Distance" value={hasLead ? fmt(lead, 1) : '—'} unit={hasLead ? ' m' : ''} tone="blue" />
      <Tile label="Lead Rel. Speed" value={hasLead ? fmt(t.get(T.leadVRel), 1) : '—'} unit={hasLead ? ' m/s' : ''} />
      <Tile label="Steering Angle" value={fmt(t.get(T.steerAngle), 1)} unit="°" />
      <Tile label="Vehicle Speed" value={fmt(vSp.v, 0)} unit={` ${vSp.u}`} />
    </div>
  );
}
