import { useState, useEffect } from 'react';
import Paho from 'paho-mqtt';
import './App.css';
import settingsUISchema from './assets/settings_ui.json';
import paramsMetadata from './assets/params_metadata.json';
import Dashcam from './Dashcam';

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

function SettingsView({ activeCategory, setActiveCategory, settings, onUpdateSetting }) {
  const categories = Object.keys(settingsUISchema).filter(k => k !== "Device");
  
  const currentCategoryData = settingsUISchema[activeCategory];
  if (!currentCategoryData) return <div>Select a category</div>;

  return (
    <div className="app-layout">
      {/* Sidebar Navigation */}
      <div className="app-sidebar">
        {categories.map(cat => (
          <div 
            key={cat}
            className={`nav-item ${activeCategory === cat ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat)}
          >
            {settingsUISchema[cat].icon && <span style={{fontSize: '1.2rem'}}>{settingsUISchema[cat].icon}</span>}
            {settingsUISchema[cat].title || cat}
          </div>
        ))}
      </div>

      {/* Main Settings Content */}
      <div className="app-main">
        <div className="app-content">
          <div className="cel-card" style={{ width: '100%', marginBottom: '2rem' }}>
            <h1 style={{ margin: 0, fontWeight: 900 }}>{currentCategoryData.title || activeCategory}</h1>
          </div>
          
          <div className="cel-card" style={{ width: '100%', padding: '2rem' }}>
            {currentCategoryData.items.map(item => {
              if (item.key) return renderItem(item, settings, onUpdateSetting);
              return null;
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [telemetry, setTelemetry] = useState({ speed: 0, battery: 0, gear: 'P', cpuTemp: 0 });
  const [settings, setSettings] = useState({});
  const [mqttClient, setMqttClient] = useState(null);
  
  // Tab Routing: "dashcam", "settings", "history", "controls"
  const [activeTab, setActiveTab] = useState("dashcam");
  const [activeCategory, setActiveCategory] = useState("Steering");

  useEffect(() => {
    const host = window.location.hostname === 'localhost' ? '192.168.0.233' : window.location.hostname;
    
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
        
        if (topic === "openrivian/telemetry") {
          setTelemetry(prev => ({ ...prev, ...payload }));
        } else if (topic.startsWith("openrivian/settings/status/")) {
          const paramKey = topic.split('/').pop();
          setSettings(prev => ({ ...prev, [paramKey]: payload.value }));
        }
      } catch (e) {
        console.error("Error parsing MQTT message:", e);
      }
    };

    client.connect({
      onSuccess: () => {
        console.log("Connected to MQTT Broker");
        client.subscribe("openrivian/telemetry");
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
      
      setSettings(prev => ({ ...prev, [key]: value }));
    }
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
        {activeTab === 'dashcam' && <Dashcam telemetry={telemetry} />}
        {activeTab === 'settings' && (
          <SettingsView 
            activeCategory={activeCategory} 
            setActiveCategory={setActiveCategory} 
            settings={settings} 
            onUpdateSetting={handleUpdateSetting} 
          />
        )}
        {activeTab === 'history' && (
          <div className="app-main" style={{ justifyContent: 'center', alignItems: 'center' }}>
            <h1 style={{ color: '#1A1A1A' }}>Drive History Maps</h1>
            <p>Coming soon...</p>
          </div>
        )}
        {activeTab === 'controls' && (
          <div className="app-main" style={{ justifyContent: 'center', alignItems: 'center' }}>
            <h1 style={{ color: '#1A1A1A' }}>OpenRivian Controls</h1>
            <p>Coming soon...</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
