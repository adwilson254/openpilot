import { useState } from 'react';
import { useTelemetry } from '../lib/mqtt';
import settingsUISchema from '../assets/settings_ui.json';
import paramsMetadata from '../assets/params_metadata.json';

function Item({ item, value, onSet }) {
  const meta = paramsMetadata[item.key] || {};
  if (item.widget === 'toggle') {
    const on = value === true || value === 1 || value === '1';
    return (
      <div className="setting-row">
        <div>
          <div className="setting-title">{item.title}</div>
          {item.description && <div className="setting-desc">{item.description}</div>}
        </div>
        <div className={`switch ${on ? 'on' : ''}`} role="switch" aria-checked={on}
             onClick={() => onSet(item.key, !on)}><i /></div>
      </div>
    );
  }
  if (item.widget === 'option' || item.widget === 'multiple_button') {
    const options = item.options || meta.options || [];
    if (!options.length) return null;
    return (
      <div className="setting-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 10 }}>
        <div>
          <div className="setting-title">{item.title}</div>
          {item.description && <div className="setting-desc">{item.description}</div>}
        </div>
        <div className="row">
          {options.map((opt) => (
            <button key={opt.value} className={`opt-btn ${value === opt.value ? 'sel' : ''}`}
                    onClick={() => onSet(item.key, opt.value)}>{opt.label || opt.value}</button>
          ))}
        </div>
      </div>
    );
  }
  return null;
}

export default function Settings() {
  const t = useTelemetry();
  const panels = settingsUISchema.panels || [];
  const [active, setActive] = useState(panels[0]?.id);
  const panel = panels.find((p) => p.id === active);
  const val = (key) => t.get(`openrivian/settings/status/${key}`);
  const onSet = (key, value) => t.publishSetting(key, value);

  return (
    <div>
      <div className="row" style={{ marginBottom: 16, overflowX: 'auto', paddingBottom: 4 }}>
        {panels.map((p) => (
          <button key={p.id} className={`opt-btn ${active === p.id ? 'sel' : ''}`} onClick={() => setActive(p.id)}>
            {p.label}
          </button>
        ))}
      </div>

      {!panel ? <div className="empty">Select a category</div> : (
        <div className="card">
          <h2 style={{ fontSize: 18, textTransform: 'none', letterSpacing: 0, color: 'var(--text)' }}>{panel.label}</h2>
          {panel.description && <p style={{ color: 'var(--text-faint)', marginTop: 0 }}>{panel.description}</p>}
          {(panel.sections || []).map((sec) => (
            <div key={sec.id} style={{ marginTop: 18 }}>
              {sec.title && <div style={{ fontWeight: 800, color: 'var(--yellow)', fontSize: 13, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 4 }}>{sec.title}</div>}
              {(sec.items || []).filter((i) => i.key).map((i) => (
                <Item key={i.key} item={i} value={val(i.key)} onSet={onSet} />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
