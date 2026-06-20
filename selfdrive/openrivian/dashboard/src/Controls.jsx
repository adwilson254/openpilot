import { useState } from 'react';

export default function Controls({ mqttClient }) {
  const [controlsState, setControlsState] = useState({
    doorsLocked: true,
    climateOn: false,
    frunkOpen: false,
    gearGuardOn: true,
  });

  const toggleControl = (key) => {
    const newVal = !controlsState[key];
    setControlsState(prev => ({ ...prev, [key]: newVal }));
    
    // Publish MQTT command if connected
    if (mqttClient && mqttClient.isConnected()) {
      const topic = `openrivian/command/controls/${key}`;
      const message = new Paho.Message(JSON.stringify({ value: newVal }));
      message.destinationName = topic;
      mqttClient.send(message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%', padding: '1rem' }}>
      <div className="cel-card" style={{ flex: 1, padding: '2rem', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ margin: '0 0 2rem 0', fontWeight: 900 }}>Rivian Controls</h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          
          {/* Locks */}
          <div style={{
            background: '#F5F5F5',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '2px solid #1A1A1A',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <h3 style={{ margin: 0 }}>Door Locks</h3>
            <button 
              className="cel-button"
              onClick={() => toggleControl('doorsLocked')}
              style={{
                background: controlsState.doorsLocked ? '#FF3366' : '#00D582',
                color: '#FFF',
                width: '100%'
              }}
            >
              {controlsState.doorsLocked ? 'LOCKED' : 'UNLOCKED'}
            </button>
          </div>

          {/* Climate */}
          <div style={{
            background: '#F5F5F5',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '2px solid #1A1A1A',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <h3 style={{ margin: 0 }}>Climate</h3>
            <button 
              className="cel-button"
              onClick={() => toggleControl('climateOn')}
              style={{
                background: controlsState.climateOn ? '#00B4D8' : '#333',
                color: '#FFF',
                width: '100%'
              }}
            >
              {controlsState.climateOn ? 'AC ON' : 'OFF'}
            </button>
          </div>

          {/* Frunk */}
          <div style={{
            background: '#F5F5F5',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '2px solid #1A1A1A',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <h3 style={{ margin: 0 }}>Frunk</h3>
            <button 
              className="cel-button"
              onClick={() => toggleControl('frunkOpen')}
              style={{
                background: controlsState.frunkOpen ? '#FFD500' : '#333',
                color: controlsState.frunkOpen ? '#000' : '#FFF',
                width: '100%'
              }}
            >
              {controlsState.frunkOpen ? 'OPEN' : 'CLOSED'}
            </button>
          </div>

          {/* Gear Guard */}
          <div style={{
            background: '#F5F5F5',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '2px solid #1A1A1A',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <h3 style={{ margin: 0 }}>Gear Guard</h3>
            <button 
              className="cel-button"
              onClick={() => toggleControl('gearGuardOn')}
              style={{
                background: controlsState.gearGuardOn ? '#00D582' : '#333',
                color: '#FFF',
                width: '100%'
              }}
            >
              {controlsState.gearGuardOn ? 'ACTIVE' : 'OFF'}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
