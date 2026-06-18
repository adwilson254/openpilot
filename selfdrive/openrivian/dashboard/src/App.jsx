import { useState, useEffect } from 'react'
import Paho from 'paho-mqtt'
import './App.css'
import settingsUISchema from './assets/settings_ui.json'
import paramsMetadata from './assets/params_metadata.json'

function CelShadedTelemetry({ telemetry }) {
  return (
    <div className="cel-shaded" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', alignContent: 'start' }}>
      <div className="cel-card" style={{ gridColumn: '1 / -1' }}>
        <h2>Live Telemetry</h2>
      </div>

      <div className="cel-card">
        <span className="cel-label">Speed</span>
        <div>
          <span className="cel-value">{telemetry.speed}</span>
          <span className="cel-unit"> mph</span>
        </div>
      </div>

      <div className="cel-card">
        <span className="cel-label">Battery SOC</span>
        <div>
          <span className="cel-value">{telemetry.battery}</span>
          <span className="cel-unit">%</span>
        </div>
      </div>

      <div className="cel-card">
        <span className="cel-label">Gear</span>
        <div>
          <span className="cel-value" style={{color: '#00B4D8'}}>{telemetry.gear}</span>
        </div>
      </div>

      <div className="cel-card">
        <span className="cel-label">Device CPU Temp</span>
        <div>
          <span className="cel-value">{telemetry.cpuTemp}</span>
          <span className="cel-unit">°C</span>
        </div>
      </div>
    </div>
  );
}

function renderItem(item, settings, onUpdateSetting) {
  const meta = paramsMetadata[item.key] || {};
  const value = settings[item.key];

  if (item.widget === 'toggle') {
    return (
      <div key={item.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid #E0E0E0' }}>
        <div style={{ paddingRight: '1rem' }}>
          <div style={{ fontWeight: 'bold' }}>{item.title}</div>
          <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>{item.description}</div>
        </div>
        <button 
          onClick={() => onUpdateSetting(item.key, !value)}
          style={{
            background: value ? '#00D582' : '#333',
            color: '#FFF',
            border: '2px solid #1A1A1A',
            padding: '0.5rem 1rem',
            borderRadius: '24px',
            fontWeight: 'bold',
            cursor: 'pointer',
            minWidth: '80px',
            boxShadow: '2px 2px 0px #1A1A1A',
            transition: 'all 0.1s'
          }}
        >
          {value ? "ON" : "OFF"}
        </button>
      </div>
    );
  }
  else if (item.widget === 'option' || item.widget === 'multiple_button') {
    const options = item.options || meta.options || [];
    if (options.length === 0) return null; // Skip if no options defined
    return (
      <div key={item.key} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0.5rem 0', borderBottom: '1px solid #E0E0E0' }}>
        <div>
          <div style={{ fontWeight: 'bold' }}>{item.title}</div>
          <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>{item.description}</div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
          {options.map(opt => (
            <button
              key={opt.value}
              onClick={() => onUpdateSetting(item.key, opt.value)}
              style={{
                background: value === opt.value ? '#FFD500' : '#FFF',
                color: '#1A1A1A',
                border: '2px solid #1A1A1A',
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                fontWeight: 'bold',
                cursor: 'pointer',
                boxShadow: value === opt.value ? 'inset 2px 2px 0px rgba(0,0,0,0.1)' : '2px 2px 0px #1A1A1A'
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    )
  }
  return null;
}

function DynamicSettingsPanel({ panelId, settings, onUpdateSetting }) {
  const panel = settingsUISchema.panels.find(p => p.id === panelId);
  if (!panel) return null;

  return (
    <div className="cel-shaded" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', alignContent: 'start', paddingBottom: '4rem' }}>
      <div className="cel-card" style={{ width: '100%', boxSizing: 'border-box' }}>
        <h2 style={{ margin: 0 }}>{panel.label}</h2>
        {panel.description && <p style={{ color: '#666', marginTop: '0.5rem', marginBottom: 0 }}>{panel.description}</p>}
      </div>

      {panel.sections.map(section => (
        <div key={section.id} className="cel-card" style={{ width: '100%', alignItems: 'stretch', boxSizing: 'border-box' }}>
          {section.title && <h3 style={{ borderBottom: '2px solid #1A1A1A', paddingBottom: '0.5rem', margin: '0 0 1rem 0' }}>{section.title}</h3>}
          {section.description && <p style={{ color: '#666', marginBottom: '1rem', marginTop: 0 }}>{section.description}</p>}
          
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {section.items.map(item => renderItem(item, settings, onUpdateSetting))}
            
            {/* Render Sub Panels Inline */}
            {section.sub_panels?.map(sub => (
              <div key={sub.id} style={{ marginTop: '1.5rem', padding: '1.5rem', background: '#F4F3ED', borderRadius: '12px', border: '2px solid #1A1A1A' }}>
                <h4 style={{ margin: '0 0 1rem 0' }}>{sub.label}</h4>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {sub.items.map(item => renderItem(item, settings, onUpdateSetting))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function App() {
  const [view, setView] = useState('telemetry');
  const [telemetry, setTelemetry] = useState({
    speed: 0.0,
    battery: 0,
    gear: 'P',
    cpuTemp: 0.0,
  });
  
  const [settings, setSettings] = useState({});
  const [client, setClient] = useState(null);

  useEffect(() => {
    const host = window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname;
    const mqtt = new Paho.Client(host, 9001, "web_dashboard_" + parseInt(Math.random() * 100, 10));
    
    mqtt.onConnectionLost = (res) => {
      console.log("MQTT Connection Lost:", res.errorMessage);
      setTimeout(() => mqtt.connect({ onSuccess }), 3000);
    };

    mqtt.onMessageArrived = (msg) => {
      const topic = msg.destinationName;
      let payload;
      try { payload = JSON.parse(msg.payloadString); } catch(e) { return; }

      if (topic === 'openrivian/vehicle/speed') {
        setTelemetry(prev => ({ ...prev, speed: (payload.value * 2.23694).toFixed(1) }));
      } else if (topic === 'openrivian/vehicle/battery') {
        setTelemetry(prev => ({ ...prev, battery: payload.value }));
      } else if (topic === 'openrivian/vehicle/gear') {
        setTelemetry(prev => ({ ...prev, gear: payload.value }));
      } else if (topic === 'openrivian/device/cpu_temp') {
        setTelemetry(prev => ({ ...prev, cpuTemp: payload.value.toFixed(1) }));
      }
      else if (topic.startsWith('openrivian/settings/status/')) {
        const param = topic.split('/').pop();
        setSettings(prev => ({ ...prev, [param]: payload.value }));
      }
    };

    const onSuccess = () => {
      console.log("MQTT Connected via WebSockets");
      mqtt.subscribe("openrivian/vehicle/#");
      mqtt.subscribe("openrivian/device/#");
      mqtt.subscribe("openrivian/settings/status/#");
      setClient(mqtt);
    };

    mqtt.connect({ onSuccess });
    return () => mqtt.disconnect();
  }, []);

  const handleUpdateSetting = (param, value) => {
    if (client && client.isConnected()) {
      const msg = new Paho.Message(JSON.stringify({ value }));
      msg.destinationName = `openrivian/settings/set/${param}`;
      client.send(msg);
      // Optimistically update local UI state (it will revert after 5s if backend is read-only)
      setSettings(prev => ({ ...prev, [param]: value }));
    }
  };

  return (
    <div className="app-container" style={{ flexDirection: 'row' }}>
      {/* Sidebar Navigation */}
      <div style={{ width: '250px', background: '#1A1A1A', color: '#FFF', display: 'flex', flexDirection: 'column', borderRight: '4px solid #000' }}>
        <div style={{ padding: '1.5rem', background: '#FFD500', color: '#000', borderBottom: '4px solid #000' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 900, textTransform: 'uppercase' }}>OpenRivian</h2>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', padding: '1rem', gap: '0.5rem', overflowY: 'auto' }}>
          <button 
            className={`nav-btn ${view === 'telemetry' ? 'active' : ''}`}
            onClick={() => setView('telemetry')}
            style={{ 
              background: view === 'telemetry' ? '#00D582' : 'transparent',
              color: view === 'telemetry' ? '#000' : '#FFF',
              border: view === 'telemetry' ? '2px solid #000' : '2px solid transparent',
              padding: '0.8rem 1rem', borderRadius: '8px', textAlign: 'left', fontWeight: 'bold', cursor: 'pointer' 
            }}
          >
            Telemetry
          </button>
          
          <div style={{ margin: '1rem 0 0.5rem 0', color: '#888', fontSize: '0.8rem', textTransform: 'uppercase', fontWeight: 'bold', paddingLeft: '1rem' }}>
            Settings
          </div>

          {settingsUISchema.panels.map(panel => (
            <button 
              key={panel.id}
              className={`nav-btn ${view === panel.id ? 'active' : ''}`}
              onClick={() => setView(panel.id)}
              style={{ 
                background: view === panel.id ? '#FFD500' : 'transparent',
                color: view === panel.id ? '#000' : '#FFF',
                border: view === panel.id ? '2px solid #000' : '2px solid transparent',
                padding: '0.8rem 1rem', borderRadius: '8px', textAlign: 'left', fontWeight: 'bold', cursor: 'pointer' 
              }}
            >
              {panel.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', background: '#F4F3ED' }}>
        {view === 'telemetry' ? (
          <CelShadedTelemetry telemetry={telemetry} />
        ) : (
          <DynamicSettingsPanel panelId={view} settings={settings} onUpdateSetting={handleUpdateSetting} />
        )}
      </div>
    </div>
  )
}

export default App
