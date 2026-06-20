import React, { useState } from 'react';
import './DesignShowcase.css';

export default function DesignShowcase({ onExit }) {
  const [activeMockup, setActiveMockup] = useState(4);

  return (
    <div className="showcase-container">
      <div className="showcase-controls">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button 
            onClick={onExit} 
            style={{ background: 'transparent', border: '1px solid #555', color: '#ccc', padding: '0.5rem', borderRadius: '4px', cursor: 'pointer' }}
          >
            ← Exit Showcase
          </button>
          <h3>Rivian UI Concept Selector</h3>
        </div>
        <div className="button-group">
          <button 
            className={activeMockup === 1 ? 'active' : ''} 
            onClick={() => setActiveMockup(1)}
          >
            1: Center Hologram + Edge Grid
          </button>
          <button 
            className={activeMockup === 2 ? 'active' : ''} 
            onClick={() => setActiveMockup(2)}
          >
            2: Split-Screen Technical
          </button>
          <button 
            className={activeMockup === 3 ? 'active' : ''} 
            onClick={() => setActiveMockup(3)}
          >
            3: Hologram over Data Grid
          </button>
          <button 
            className={activeMockup === 4 ? 'active' : ''} 
            onClick={() => setActiveMockup(4)}
          >
            4: Ultimate Hybrid (2+3)
          </button>
          <button 
            className={activeMockup === 5 ? 'active' : ''} 
            onClick={() => setActiveMockup(5)}
            style={{ borderLeft: '2px solid #555', marginLeft: '0.5rem', paddingLeft: '1rem' }}
          >
            5: Center Holo + Dense Grid (Combo 1+2)
          </button>
          <button 
            className={activeMockup === 6 ? 'active' : ''} 
            onClick={() => setActiveMockup(6)}
          >
            6: Liquid Ghibli (Orig 1+2)
          </button>
        </div>
      </div>

      <div className="showcase-frame">
        {activeMockup === 1 && <ComboCenterHologram />}
        {activeMockup === 2 && <ComboSplitScreen />}
        {activeMockup === 3 && <ComboHologramGrid />}
        {activeMockup === 4 && <ComboUltimateHybrid />}
        {activeMockup === 5 && <HybridCombo1And2 />}
        {activeMockup === 6 && <HybridOriginal1And2 />}
      </div>
    </div>
  );
}

// Reusable Hologram Component
function IsometricTruck() {
  return (
    <div className="isometric-truck-container">
      <div className="truck-body">
        <div className="cab"></div>
        <div className="bed"></div>
        <div className="chassis"></div>
        <div className="wheel fl"></div>
        <div className="wheel fr"></div>
        <div className="wheel rl"></div>
        <div className="wheel rr"></div>
      </div>
    </div>
  );
}

// Option 1: Center Hologram, Edges are Camp Kitchen Grid
function ComboCenterHologram() {
  return (
    <div className="mockup-container combo-center-hologram">
      <div className="camp-grid-col left-col">
        <div className="camp-tile">
          <span className="label">FL SPEED</span>
          <span className="value yellow">45 <small>MPH</small></span>
        </div>
        <div className="camp-tile">
          <span className="label">RL SPEED</span>
          <span className="value yellow">45 <small>MPH</small></span>
        </div>
        <div className="camp-tile highlight">
          <span className="label">ADAS</span>
          <span className="value">READY</span>
        </div>
      </div>
      
      <div className="center-hologram-stage">
        <IsometricTruck />
        <div className="holo-callout top-left">Torque: 240 Nm</div>
        <div className="holo-callout top-right">Torque: 240 Nm</div>
        <div className="holo-callout bottom-left">Pitch: 3°</div>
        <div className="holo-callout bottom-right">Roll: 1°</div>
      </div>

      <div className="camp-grid-col right-col">
        <div className="camp-tile">
          <span className="label">FR SPEED</span>
          <span className="value yellow">45 <small>MPH</small></span>
        </div>
        <div className="camp-tile">
          <span className="label">RR SPEED</span>
          <span className="value yellow">45 <small>MPH</small></span>
        </div>
        <div className="camp-tile">
          <span className="label">BATTERY</span>
          <span className="value green">68%</span>
        </div>
      </div>
    </div>
  );
}

// Option 2: Split Screen (Left: Camp Grid, Right: Hologram)
function ComboSplitScreen() {
  return (
    <div className="mockup-container combo-split-screen">
      <div className="split-left">
        <div className="camp-grid-dense">
          <div className="camp-tile large-tile">
            <span className="label">SPEED</span>
            <span className="value giant">84</span>
          </div>
          <div className="camp-tile">
            <span className="label">GEAR</span>
            <span className="value yellow">D</span>
          </div>
          <div className="camp-tile">
            <span className="label">RANGE</span>
            <span className="value">315 mi</span>
          </div>
          <div className="camp-tile">
            <span className="label">ELEVATION</span>
            <span className="value">1450m</span>
          </div>
          <div className="camp-tile">
            <span className="label">TIRES FL/FR</span>
            <span className="value">38 / 38</span>
          </div>
          <div className="camp-tile">
            <span className="label">TIRES RL/RR</span>
            <span className="value">40 / 40</span>
          </div>
        </div>
      </div>
      
      <div className="split-right">
        <div className="hologram-wrapper">
          <div className="holo-title">TORQUE VECTORING</div>
          <IsometricTruck />
          <div className="holo-data-bar">
            <span>FRONT: 35%</span>
            <span>REAR: 65%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Option 3: Hologram over Data Grid
function ComboHologramGrid() {
  return (
    <div className="mockup-container combo-holo-grid">
      <div className="background-grid">
        {/* Render a grid of faint data points */}
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="faint-tile">
            <div className="line"></div>
            <div className="line short"></div>
          </div>
        ))}
      </div>
      
      <div className="foreground-hologram">
        <IsometricTruck />
        
        {/* Camp style tiles attached directly to the hologram */}
        <div className="camp-tile attached fl-tile">
          <span className="label">FL SPEED</span>
          <span className="value yellow">38</span>
        </div>
        <div className="camp-tile attached fr-tile">
          <span className="label">FR SPEED</span>
          <span className="value yellow">38</span>
        </div>
        <div className="camp-tile attached rl-tile">
          <span className="label">RL SPEED</span>
          <span className="value yellow">39</span>
        </div>
        <div className="camp-tile attached rr-tile">
          <span className="label">RR SPEED</span>
          <span className="value yellow">39</span>
        </div>
      </div>
      
      <div className="bottom-bar-camp">
         <div className="camp-tile wide">
            <span className="label">SYSTEM STATUS</span>
            <span className="value green">NOMINAL</span>
         </div>
      </div>
    </div>
  );
}

// Option 4: The Ultimate Hybrid (Split Screen + Grid Backdrop + Attached Tiles)
function ComboUltimateHybrid() {
  return (
    <div className="mockup-container combo-ultimate-hybrid">
      <div className="background-grid">
        {/* Render a grid of faint data points for the entire background */}
        {Array.from({ length: 16 }).map((_, i) => (
          <div key={i} className="faint-tile">
            <div className="line"></div>
            <div className="line short"></div>
          </div>
        ))}
      </div>

      <div className="hybrid-content">
        <div className="split-left">
          <div className="camp-grid-dense">
            <div className="camp-tile large-tile">
              <span className="label">SPEED</span>
              <span className="value giant">84 <small style={{fontSize:'1.5rem'}}>MPH</small></span>
            </div>
            <div className="camp-tile highlight">
              <span className="label">ADAS</span>
              <span className="value">READY</span>
            </div>
            <div className="camp-tile">
              <span className="label">RANGE</span>
              <span className="value">315 mi</span>
            </div>
            <div className="camp-tile">
              <span className="label">GEAR</span>
              <span className="value yellow">D</span>
            </div>
            <div className="camp-tile">
              <span className="label">ELEVATION</span>
              <span className="value">1450m</span>
            </div>
          </div>
        </div>
        
        <div className="split-right">
          <div className="foreground-hologram hybrid-holo">
            <div className="holo-title" style={{position:'absolute', top: '-60px'}}>TORQUE VECTORING</div>
            <IsometricTruck />
            
            {/* Camp style tiles attached directly to the hologram */}
            <div className="camp-tile attached fl-tile">
              <span className="label">FL SPEED</span>
              <span className="value yellow">38</span>
            </div>
            <div className="camp-tile attached fr-tile">
              <span className="label">FR SPEED</span>
              <span className="value yellow">38</span>
            </div>
            <div className="camp-tile attached rl-tile">
              <span className="label">RL SPEED</span>
              <span className="value yellow">39</span>
            </div>
            <div className="camp-tile attached rr-tile">
              <span className="label">RR SPEED</span>
              <span className="value yellow">39</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Option 5: Hybrid of Combo 1 (Center Holo) and Combo 2 (Split Screen Dense Grid)
function HybridCombo1And2() {
  return (
    <div className="mockup-container combo-center-hologram">
      <div className="camp-grid-dense" style={{ width: '350px', paddingRight: '2rem' }}>
        <div className="camp-tile large-tile">
          <span className="label">SPEED</span>
          <span className="value giant">84 <small style={{fontSize:'1.5rem'}}>MPH</small></span>
        </div>
        <div className="camp-tile">
          <span className="label">GEAR</span>
          <span className="value yellow">D</span>
        </div>
        <div className="camp-tile">
          <span className="label">RANGE</span>
          <span className="value">315 mi</span>
        </div>
      </div>
      
      <div className="center-hologram-stage" style={{ flex: 1 }}>
        <IsometricTruck />
        <div className="holo-callout top-left">FL: 38 MPH</div>
        <div className="holo-callout top-right">FR: 38 MPH</div>
        <div className="holo-callout bottom-left">RL: 39 MPH</div>
        <div className="holo-callout bottom-right">RR: 39 MPH</div>
      </div>

      <div className="camp-grid-col right-col" style={{ width: '250px' }}>
        <div className="camp-tile">
          <span className="label">ELEVATION</span>
          <span className="value">1450m</span>
        </div>
        <div className="camp-tile highlight">
          <span className="label">ADAS</span>
          <span className="value">READY</span>
        </div>
        <div className="camp-tile">
          <span className="label">BATTERY</span>
          <span className="value green">68%</span>
        </div>
      </div>
    </div>
  );
}

// Option 6: Hybrid of Original 1 (Liquid Glass Dock) and Original 2 (Studio Ghibli Organic)
function HybridOriginal1And2() {
  return (
    <div className="mockup-container studio-ghibli" style={{ background: 'linear-gradient(135deg, #1a221f 0%, #2a3a32 100%)', flexDirection: 'row' }}>
      <div className="vertical-dock" style={{ 
        width: '80px', 
        background: 'rgba(255, 255, 255, 0.05)', 
        backdropFilter: 'blur(20px)', 
        borderRadius: '40px', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        padding: '2rem 0', 
        gap: '2rem',
        marginRight: '1rem',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div className="dock-icon active" style={{fontSize:'1.5rem', opacity:1}}>🏠</div>
        <div className="dock-icon" style={{fontSize:'1.5rem', opacity:0.5}}>🎵</div>
        <div className="dock-icon" style={{fontSize:'1.5rem', opacity:0.5}}>📍</div>
        <div className="dock-icon" style={{fontSize:'1.5rem', opacity:0.5}}>🚙</div>
        <div className="dock-icon" style={{fontSize:'1.5rem', opacity:0.5}}>⚙️</div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="top-bar-organic">
          <div className="mode-badge">🧭 TRAIL MODE</div>
          <div className="climate-info">21°C</div>
          <div className="time-info">11:14 AM</div>
        </div>

        <div className="ghibli-grid" style={{ flex: 1 }}>
          <div className="organic-panel left-panel" style={{ background: 'rgba(188, 94, 76, 0.4)', backdropFilter: 'blur(20px)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div className="ghibli-stat">
              <label>RANGE</label>
              <div className="value yellow">310 MI</div>
            </div>
            <div className="ghibli-stat">
              <label>BATT</label>
              <div className="value green">82%</div>
            </div>
          </div>

          <div className="center-illustration" style={{ background: 'rgba(222, 184, 135, 0.2)', backdropFilter: 'blur(20px)', border: '4px solid rgba(255,255,255,0.1)' }}>
            <div className="truck-graphic" style={{fontSize:'8rem'}}>🚙</div>
            <div className="center-stats" style={{ background: 'rgba(42, 58, 50, 0.8)' }}>
              <div className="mph">58 MPH</div>
              <div className="gear">GEAR D</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
