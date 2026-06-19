import { useState, useEffect } from 'react';

export default function DriveHistory() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRoutes() {
      try {
        const response = await fetch('/routes');
        if (!response.ok) throw new Error('Failed to fetch routes');
        const data = await response.json();
        // Sort by date descending
        data.sort((a, b) => new Date(b.date) - new Date(a.date));
        setRoutes(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchRoutes();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div className="cel-card" style={{ flex: 1, padding: '2rem', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ margin: '0 0 1rem 0', fontWeight: 900 }}>Drive History</h2>
        
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>Loading routes...</div>
        ) : error ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#FF3366', fontWeight: 'bold' }}>Error: {error}</div>
        ) : routes.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>No routes found on this device.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto' }}>
            {routes.map(route => (
              <div key={route.id} style={{
                background: '#F5F5F5',
                padding: '1rem',
                borderRadius: '8px',
                border: '2px solid #1A1A1A',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{route.date}</div>
                  <div style={{ color: '#666', fontSize: '0.9rem', marginTop: '0.25rem' }}>{route.id}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ background: '#1A1A1A', color: '#FFF', padding: '0.25rem 0.75rem', borderRadius: '16px', fontSize: '0.9rem', fontWeight: 'bold' }}>
                    {route.size_mb} MB
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
