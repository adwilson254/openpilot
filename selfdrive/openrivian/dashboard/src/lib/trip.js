import { useEffect, useRef, useState } from 'react';
import { useTelemetry } from './mqtt';
import { T, bool } from './format';

// Client-side trip computer: integrates the live stream once per second into session
// stats (no backend / odometer needed). Distance from speed; engaged time from ADAS.
export function useTrip() {
  const t = useTelemetry();
  const tRef = useRef(t);
  useEffect(() => { tRef.current = t; });
  const acc = useRef({ dist: 0, max: 0, sum: 0, n: 0, engaged: 0, start: 0 });
  const [trip, setTrip] = useState({ distMi: 0, maxMph: 0, avgMph: 0, durS: 0, engagedS: 0 });

  useEffect(() => {
    if (!acc.current.start) acc.current.start = Date.now();
    const id = setInterval(() => {
      const tt = tRef.current;
      const r = acc.current;
      const sp = Number(tt.get(T.speed_mph, 0)) || 0;
      r.dist += sp / 3600;            // mph over 1s -> miles
      r.max = Math.max(r.max, sp);
      r.sum += sp; r.n += 1;
      if (bool(tt.get(T.adasActive)) || bool(tt.get(T.adasEnabled))) r.engaged += 1;
      setTrip({
        distMi: r.dist, maxMph: r.max,
        avgMph: r.n ? r.sum / r.n : 0,
        durS: (Date.now() - r.start) / 1000,
        engagedS: r.engaged,
      });
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const reset = () => {
    acc.current = { dist: 0, max: 0, sum: 0, n: 0, engaged: 0, start: Date.now() };
    setTrip({ distMi: 0, maxMph: 0, avgMph: 0, durS: 0, engagedS: 0 });
  };

  return { trip, reset };
}

export function hms(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}
