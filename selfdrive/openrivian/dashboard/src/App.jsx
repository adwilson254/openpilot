import { useState, useEffect } from 'react';
import Paho from 'paho-mqtt';
import './App.css';
import settingsUISchema from './assets/settings_ui.json';
import paramsMetadata from './assets/params_metadata.json';
import Telemetry from './Telemetry';
import DriveHistory from './DriveHistory';
import Controls from './Controls';

function renderItem(item, settings, onUpdateSetting) {
  const meta = paramsMetadata[item.key] || {};
  const value = settings[item.key];

  if (item.widget === 'toggle') {
    return (
      <div key={item.key} className="setting-row">
        <div style={{ paddingRight: '1rem' }}>
          <div className="setting-title">{item.title}</div>
          <div className="setting-desc">{item.description}</div>
        </div>
        <button 
          className="cel-button"
          onClick={() => onUpdateSetting(item.key, !value)}
          style={{
            background: value ? '#00D582' : '#333',
            color: '#FFF',
            minWidth: '80px',
          }}
        >
          {value ? "ON" : "OFF"}
        </button>
      </div>
    );
  }
  else if (item.widget === 'option' || item.widget === 'multiple_button') {
    const options = item.options || meta.options || [];
    if (options.length === 0) return null;
    return (
      <div key={item.key} className="setting-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.5rem' }}>
        <div>
          <div className="setting-title">{item.title}</div>
          <div className="setting-desc">{item.description}</div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
          {options.map(opt => (
            <button
              key={opt.value}
              className="cel-button"
              onClick={() => onUpdateSetting(item.key, opt.value)}
              style={{
                background: value === opt.value ? '#FFD500' : '#FFF',
                color: '#1A1A1A',
              }}
            >
              {opt.label || opt.value}
            </button>
          ))}
        </div>
      </div>
    );
  }
  return null;
}

function SettingsView({ activePanelId, setActivePanelId, settings, onUpdateSetting }) {
  const panels = settingsUISchema.panels || [];
  
  const currentPanel = panels.find(p => p.id === activePanelId);

  return (
    <div className="app-layout">
      {/* Sidebar Navigation */}
      <div className="app-sidebar">
        {panels.map(panel => (
          <div 
            key={panel.id}
            className={`nav-item ${activePanelId === panel.id ? 'active' : ''}`}
            onClick={() => setActivePanelId(panel.id)}
          >
            {panel.label}
          </div>
        ))}
      </div>

      {/* Main Settings Content */}
      <div className="app-main">
        <div className="app-content">
          {!currentPanel ? <div>Select a category</div> : (
            <>
              <div className="cel-card" style={{ width: '100%', marginBottom: '2rem' }}>
                <h1 style={{ margin: 0, fontWeight: 900 }}>{currentPanel.label}</h1>
                {currentPanel.description && <p style={{ color: '#666', marginTop: '0.5rem' }}>{currentPanel.description}</p>}
              </div>
              
              <div className="cel-card" style={{ width: '100%', padding: '2rem' }}>
                {currentPanel.sections?.map(section => (
                  <div key={section.id} style={{ marginBottom: '2rem' }}>
                    {section.title && <h2 style={{ borderBottom: '2px solid #1A1A1A', paddingBottom: '0.5rem', marginBottom: '1rem' }}>{section.title}</h2>}
                    {section.items?.map(item => {
                      if (item.key) return renderItem(item, settings, onUpdateSetting);
                      return null;
                    })}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  const [telemetry, setTelemetry] = useState({ speed: 0, battery: 0, gear: 'P', cpuTemp: 0 });
  const [settings, setSettings] = useState({});
  const [mqttClient, setMqttClient] = useState(null);
  
  // Tab Routing: "telemetry", "settings", "history", "controls"
  const [activeTab, setActiveTab] = useState("telemetry");
  const [activePanelId, setActivePanelId] = useState("steering");

  useEffect(() => {
    // Check URL params first (e.g. ?host=192.168.2.232), then fallback to truck IP if localhost
    const urlParams = new URLSearchParams(window.location.search);
    const hostParam = urlParams.get('host');
    const host = hostParam ? hostParam : (window.location.hostname === 'localhost' ? '192.168.0.233' : window.location.hostname);
    
    const client = new Paho.Client(host, Number(9001), "clientId-" + Math.random().toString(16).substr(2, 8));

    client.onConnectionLost = (responseObject) => {
      if (responseObject.errorCode !== 0) {
        console.error("MQTT Connection Lost:", responseObject.errorMessage);
      }
    };

    client.onMessageArrived = (message) => {
      try {
        const topic = message.destinationName;
        const payload = JSON.parse(message.payloadString);
        
        // Settings Mapping
        if (topic.startsWith("openrivian/settings/status/")) {
          const paramKey = topic.split('/').pop();
          setSettings(prev => ({ ...prev, [paramKey]: payload.value }));
        }
        // Telemetry Mapping
        else if (topic === "openrivian/vehicle/powertrain/speed_mph") {
          setTelemetry(prev => ({ ...prev, speed: Math.round(payload.value) }));
        }
        else if (topic === "openrivian/vehicle/powertrain/gear") {
          setTelemetry(prev => ({ ...prev, gear: payload.value }));
        }
        else if (topic === "openrivian/vehicle/powertrain/soc") {
          setTelemetry(prev => ({ ...prev, battery: Math.round(payload.value) }));
        }
        else if (topic === "openrivian/device/hardware/cpu_temp_c") {
          setTelemetry(prev => ({ ...prev, cpuTemp: Math.round(payload.value) }));
        }
        else if (topic === "openrivian/device/hardware/free_space_percent") {
          setTelemetry(prev => ({ ...prev, freeSpace: payload.value.toFixed(1) }));
        }
      } catch (e) {
        console.error("Error parsing MQTT message:", e);
      }
    };

    client.connect({
      onSuccess: () => {
        console.log("Connected to MQTT Broker");
        client.subscribe("openrivian/vehicle/#");
        client.subscribe("openrivian/device/#");
        client.subscribe("openrivian/settings/status/#");
      },
      onFailure: (e) => console.error("MQTT Connection Failed", e)
    });

    setMqttClient(client);

    return () => {
      if (client.isConnected()) {
        client.disconnect();
      }
    };
  }, []);

  const handleUpdateSetting = (key, value) => {
    if (mqttClient && mqttClient.isConnected()) {
      const message = new Paho.Message(JSON.stringify({ value }));
      message.destinationName = `openrivian/settings/set/${key}`;
      mqttClient.send(message);
    }
    
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw' }}>
      
      {/* Top Bar Navigation */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        gap: '1rem', 
        padding: '1rem', 
        background: '#121212', 
        borderBottom: '3px solid #1A1A1A',
        zIndex: 100 
      }}>
        {['dashcam', 'settings', 'history', 'controls'].map(tab => (
          <button 
            key={tab}
            className="cel-button"
            onClick={() => setActiveTab(tab)}
            style={{
              background: activeTab === tab ? '#FFD500' : '#333',
              color: activeTab === tab ? '#000' : '#FFF',
              textTransform: 'capitalize'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Main Routing Area */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'telemetry' && <Telemetry telemetry={telemetry} />}
        {activeTab === 'settings' && (
          <SettingsView 
            activePanelId={activePanelId} 
            setActivePanelId={setActivePanelId} 
            settings={settings} 
            onUpdateSetting={handleUpdateSetting} 
          />
        )}
        {activeTab === 'history' && <DriveHistory />}
        {activeTab === 'controls' && <Controls mqttClient={mqttClient} />}
      </div>
    </div>
  );
}

export default App;
