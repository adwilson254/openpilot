import { useEffect, useRef, useState } from 'react';
import { useTelemetry } from './mqtt';
import { T, bool } from './format';

// Client-side trip computer: integrates the live stream once per second into
// session stats (no backend / odometer needed). Distance from speed; engaged
// time from ADAS.
//
// The accumulator is a MODULE-LEVEL singleton, not hook state: the view that
// shows it unmounts on every tab switch, and hook-local state silently zeroed
// "This Drive" whenever you visited the map and came back. One store, any
// number of subscribed components, survives navigation (resets only on reload
// or the Reset button).

export function createTripStore() {
  const acc = { dist: 0, max: 0, sum: 0, n: 0, engaged: 0, start: 0 };
  return {
    tick(speedMph, engaged) {
      if (!acc.start) acc.start = Date.now();
      const sp = Number.isFinite(speedMph) ? speedMph : 0;
      acc.dist += sp / 3600; // mph over 1 s -> miles
      acc.max = Math.max(acc.max, sp);
      acc.sum += sp;
      acc.n += 1;
      if (engaged) acc.engaged += 1;
    },
    snapshot() {
      return {
        distMi: acc.dist,
        maxMph: acc.max,
        avgMph: acc.n ? acc.sum / acc.n : 0,
        durS: acc.start ? (Date.now() - acc.start) / 1000 : 0,
        engagedS: acc.engaged,
      };
    },
    reset() {
      acc.dist = 0; acc.max = 0; acc.sum = 0; acc.n = 0; acc.engaged = 0;
      acc.start = Date.now();
    },
  };
}

const STORE = createTripStore();
let tickerRefs = 0;
let tickerId = null;
let readTelemetry = null;

function ensureTicker() {
  tickerRefs += 1;
  if (tickerId) return;
  tickerId = setInterval(() => {
    const t = readTelemetry && readTelemetry();
    if (!t) return;
    const sp = Number(t.get(T.speed_mph, 0)) || 0;
    const engaged = bool(t.get(T.adasActive)) || bool(t.get(T.adasEnabled));
    STORE.tick(sp, engaged);
  }, 1000);
}

function releaseTicker() {
  tickerRefs -= 1;
  if (tickerRefs <= 0 && tickerId) {
    clearInterval(tickerId);
    tickerId = null;
    tickerRefs = 0;
  }
}

export function useTrip() {
  const t = useTelemetry();
  const tRef = useRef(t);
  useEffect(() => { tRef.current = t; });
  const [trip, setTrip] = useState(() => STORE.snapshot());

  useEffect(() => {
    readTelemetry = () => tRef.current; // latest mounted consumer feeds the ticker
    ensureTicker();
    const id = setInterval(() => setTrip(STORE.snapshot()), 1000);
    return () => { clearInterval(id); releaseTicker(); };
  }, []);

  const reset = () => { STORE.reset(); setTrip(STORE.snapshot()); };
  return { trip, reset };
}

export function hms(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}
