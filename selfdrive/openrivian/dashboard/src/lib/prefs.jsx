/* App preferences (units + comma host), persisted in localStorage. Exports a provider
   and a hook — the lint rule below is noise for that standard pattern. */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback } from 'react';

const PrefsCtx = createContext(null);

const read = (k, d) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
const write = (k, v) => { try { localStorage.setItem(k, v); } catch { /* noop */ } };

export function PrefsProvider({ children }) {
  const [units, setUnitsState] = useState(() => read('orv.units', 'imperial'));
  const [host, setHostState] = useState(() => read('orv.host', ''));
  const [valhalla, setValhallaState] = useState(() => read('orv.valhalla', 'https://valhalla1.openstreetmap.de'));

  const setUnits = useCallback((u) => { write('orv.units', u); setUnitsState(u); }, []);
  const setHost = useCallback((h) => { write('orv.host', h); setHostState(h); }, []);
  const setValhalla = useCallback((v) => { write('orv.valhalla', v); setValhallaState(v); }, []);

  const metric = units === 'metric';
  const api = {
    units, setUnits, host, setHost, valhalla, setValhalla,
    speed: (mph) => (metric ? { v: (mph || 0) * 1.60934, u: 'km/h' } : { v: mph || 0, u: 'mph' }),
    temp: (c) => (metric ? { v: c, u: '°C' } : { v: (c || 0) * 9 / 5 + 32, u: '°F' }),
    dist: (mi) => (metric ? { v: (mi || 0) * 1.60934, u: 'km' } : { v: mi || 0, u: 'mi' }),
  };
  return <PrefsCtx.Provider value={api}>{children}</PrefsCtx.Provider>;
}

export function usePrefs() {
  const c = useContext(PrefsCtx);
  if (!c) throw new Error('usePrefs must be used within PrefsProvider');
  return c;
}
