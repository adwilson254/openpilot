import { useEffect, useRef, useState } from 'react';

export default function Dashcam({ telemetry }) {
  const videoRef = useRef(null);
  const [status, setStatus] = useState('Disconnected');
  const [latency, setLatency] = useState(0);

  useEffect(() => {
    let pc = null;
    let dc = null;
    let pingInterval = null;

    async function startWebRTC() {
      setStatus('Connecting to webrtcd...');
      
      const config = { sdpSemantics: 'unified-plan' };
      pc = new RTCPeerConnection(config);

      pc.addEventListener('track', (evt) => {
        if (evt.track.kind === 'video' && videoRef.current) {
          videoRef.current.srcObject = evt.streams[0];
          setStatus('Connected (Live Feed)');
        }
      });

      try {
        const offer = await pc.createOffer({ offerToReceiveVideo: true });
        await pc.setLocalDescription(offer);

        await new Promise((resolve) => {
          if (pc.iceGatheringState === 'complete') resolve();
          else {
            const checkState = () => {
              if (pc.iceGatheringState === 'complete') {
                pc.removeEventListener('icegatheringstatechange', checkState);
                resolve();
              }
            };
            pc.addEventListener('icegatheringstatechange', checkState);
          }
        });

        const sdpOffer = pc.localDescription;
        
        // POST to our proxy in webd.py
        const response = await fetch('/offer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sdp: sdpOffer.sdp, type: sdpOffer.type }),
        });

        if (!response.ok) throw new Error('Failed to get answer from webrtcd proxy');

        const answer = await response.json();
        await pc.setRemoteDescription(answer);

        // Setup DataChannel for latency pinging (matches bodyteleop behavior)
        dc = pc.createDataChannel('data', { ordered: true });
        dc.onopen = () => {
          pingInterval = setInterval(() => {
            const start = Date.now();
            fetch('/').then(() => {
              setLatency(Date.now() - start);
            });
          }, 1000);
        };
        
      } catch (err) {
        console.error("WebRTC Error:", err);
        setStatus('Error: ' + err.message);
      }
    }

    startWebRTC();

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (dc) dc.close();
      if (pc) {
        pc.getSenders().forEach(sender => sender.track.stop());
        pc.close();
      }
    };
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div className="cel-card" style={{ flex: 1, padding: '1rem', position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', width: '100%' }}>
          <h2 style={{ margin: 0, fontWeight: 900 }}>Live Dashcam</h2>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ fontWeight: 'bold', color: status.includes('Connected') ? '#00D582' : '#FFD500' }}>
              {status}
            </span>
            <span style={{ background: '#1A1A1A', color: '#FFF', padding: '0.25rem 0.75rem', borderRadius: '16px', fontSize: '0.8rem', fontWeight: 'bold' }}>
              {latency}ms
            </span>
          </div>
        </div>

        <div style={{ flex: 1, background: '#000', borderRadius: '8px', border: '3px solid #1A1A1A', overflow: 'hidden', position: 'relative' }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        </div>
      </div>

      {/* Comma 3X Dense Stats Row */}
      <div className="cel-shaded" style={{ padding: 0 }}>
        <div className="cel-card">
          <span className="cel-label">Speed</span>
          <div><span className="cel-value">{telemetry.speed || 0}</span><span className="cel-unit"> mph</span></div>
        </div>
        <div className="cel-card">
          <span className="cel-label">CPU Temp</span>
          <div><span className="cel-value" style={{ color: telemetry.cpuTemp > 80 ? 'red' : 'inherit'}}>{telemetry.cpuTemp || '--'}</span><span className="cel-unit">°C</span></div>
        </div>
        <div className="cel-card">
          <span className="cel-label">Storage Free</span>
          <div><span className="cel-value">{telemetry.freeSpace || '--'}</span><span className="cel-unit">%</span></div>
        </div>
        <div className="cel-card">
          <span className="cel-label">Gear</span>
          <div><span className="cel-value" style={{color: '#00B4D8'}}>{telemetry.gear || 'P'}</span></div>
        </div>
      </div>
    </div>
  );
}
