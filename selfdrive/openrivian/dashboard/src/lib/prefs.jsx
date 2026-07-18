/* App preferences (units + comma host), persisted in localStorage. Exports a provider
   and a hook — the lint rule below is noise for that standard pattern. */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback } from 'react';

const PrefsCtx = createContext(null);

const read = (k, d) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
const write = (k, v) => { try { localStorage.setItem(k, v); } catch { /* noop */ } };

// Unit converters preserve "unknown": a missing reading must render as a dash,
// never as a fabricated number (the old (c||0)*9/5+32 turned "no data" into 32°F).
const known = (v) => v !== undefined && v !== null && !Number.isNaN(Number(v));

export function PrefsProvider({ children }) {
  const [units, setUnitsState] = useState(() => read('orv.units', 'imperial'));
  const [host, setHostState] = useState(() => read('orv.host', ''));
  const [valhalla, setValhallaState] = useState(() => read('orv.valhalla', 'https://valhalla1.openstreetmap.de'));
  const [theme, setThemeState] = useState(() => read('orv.theme', 'auto')); // auto | day | night

  const setUnits = useCallback((u) => { write('orv.units', u); setUnitsState(u); }, []);
  const setHost = useCallback((h) => { write('orv.host', h); setHostState(h); }, []);
  const setValhalla = useCallback((v) => { write('orv.valhalla', v); setValhallaState(v); }, []);
  const setTheme = useCallback((v) => { write('orv.theme', v); setThemeState(v); }, []);

  const metric = units === 'metric';
  const api = {
    units, setUnits, host, setHost, valhalla, setValhalla, theme, setTheme,
    speed: (mph) => (metric
      ? { v: known(mph) ? Number(mph) * 1.60934 : undefined, u: 'km/h' }
      : { v: known(mph) ? Number(mph) : undefined, u: 'mph' }),
    temp: (c) => (metric
      ? { v: known(c) ? Number(c) : undefined, u: '°C' }
      : { v: known(c) ? Number(c) * 9 / 5 + 32 : undefined, u: '°F' }),
    dist: (mi) => (metric
      ? { v: known(mi) ? Number(mi) * 1.60934 : undefined, u: 'km' }
      : { v: known(mi) ? Number(mi) : undefined, u: 'mi' }),
  };
  return <PrefsCtx.Provider value={api}>{children}</PrefsCtx.Provider>;
}

export function usePrefs() {
  const c = useContext(PrefsCtx);
  if (!c) throw new Error('usePrefs must be used within PrefsProvider');
  return c;
}
