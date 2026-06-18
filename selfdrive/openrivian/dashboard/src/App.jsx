import { useState, useEffect } from 'react'
import Paho from 'paho-mqtt'
import './App.css'

function CelShadedView({ telemetry, settings, onUpdateSetting }) {
  return (
    <div className="cel-shaded">
      {/* Telemetry Section */}
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

      {/* Settings Section */}
      <div className="cel-card" style={{ gridColumn: '1 / -1', marginTop: '2rem' }}>
        <h2>Vehicle Settings</h2>
      </div>

      {Object.entries(settings).map(([key, value]) => (
        <div className="cel-card" key={key} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="cel-label" style={{ margin: 0 }}>{key}</span>
          <button 
            className="toggle-btn"
            style={{
              background: value ? '#00D582' : '#333',
              color: '#FFF',
              border: 'none',
              padding: '0.8rem 1.5rem',
              borderRadius: '24px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
            onClick={() => onUpdateSetting(key, !value)}
          >
            {value ? "ON" : "OFF"}
          </button>
        </div>
      ))}
    </div>
  )
}

function App() {
  const [telemetry, setTelemetry] = useState({
    speed: 0.0,
    battery: 0,
    gear: 'P',
    cpuTemp: 0.0,
  });
  
  const [settings, setSettings] = useState({});
  const [client, setClient] = useState(null);

  useEffect(() => {
    // Determine the host (if running locally, use 127.0.0.1, if on network use window.location.hostname)
    const host = window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname;
    
    const mqtt = new Paho.Client(host, 9001, "web_dashboard_" + parseInt(Math.random() * 100, 10));
    
    mqtt.onConnectionLost = (res) => {
      console.log("MQTT Connection Lost:", res.errorMessage);
      setTimeout(() => mqtt.connect({ onSuccess }), 3000);
    };

    mqtt.onMessageArrived = (msg) => {
      const topic = msg.destinationName;
      let payload;
      try {
        payload = JSON.parse(msg.payloadString);
      } catch(e) { return; }

      // Handle Telemetry
      if (topic === 'openrivian/vehicle/speed') {
        setTelemetry(prev => ({ ...prev, speed: (payload.value * 2.23694).toFixed(1) })); // m/s to mph
      } else if (topic === 'openrivian/vehicle/battery') {
        setTelemetry(prev => ({ ...prev, battery: payload.value }));
      } else if (topic === 'openrivian/vehicle/gear') {
        setTelemetry(prev => ({ ...prev, gear: payload.value }));
      } else if (topic === 'openrivian/device/cpu_temp') {
        setTelemetry(prev => ({ ...prev, cpuTemp: payload.value.toFixed(1) }));
      }
      
      // Handle Settings Status
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

    return () => {
      mqtt.disconnect();
    };
  }, []);

  const handleUpdateSetting = (param, value) => {
    if (client && client.isConnected()) {
      const msg = new Paho.Message(JSON.stringify({ value }));
      msg.destinationName = `openrivian/settings/set/${param}`;
      client.send(msg);
      // Optimistically update local UI state
      setSettings(prev => ({ ...prev, [param]: value }));
    }
  };

  return (
    <div className="app-container">
      <div className="layout-switcher" style={{background: '#FFD500', color: '#000'}}>
        <h3 style={{margin: 0, padding: '0.5rem'}}>OpenRivian Dashboard</h3>
      </div>
      <CelShadedView 
        telemetry={telemetry} 
        settings={settings} 
        onUpdateSetting={handleUpdateSetting} 
      />
    </div>
  )
}

export default App
