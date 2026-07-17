/* The telemetry store keeps a ref-backed ring buffer of recent values for sparklines.
   It is intentionally read during render (the provider re-renders on every flush, so
   the buffer is always current), and this module deliberately exports both the provider
   and its hook — the lint rule below is noise for this pattern. */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import Paho from 'paho-mqtt';
import { simEnabled, simSnapshot, loadSimTimeline } from './sim';

const TelemetryContext = createContext(null);

const HISTORY_LEN = 90;   // samples kept per topic for sparklines
const STALE_MS = 5000;    // older than this => considered stale
const FLUSH_MS = 100;     // batch window: MQTT messages are buffered and applied to
                          // React state at most once per FLUSH_MS. High-rate topics
                          // arrive at 20 Hz x several topics; one setState per message
                          // was a re-render storm (every consumer re-rendered per
                          // message). 10 fps state flushes keep the UI fluid and cheap.

// Broker liveness contract (cereal2mqtt): retained flag the broker force-publishes
// to false (MQTT Last Will) if the telemetry bridge dies. Without it, retained
// state topics make a dead feed look alive to a late-connecting dashboard.
export const ALIVE_TOPIC = 'openrivian/health/telemetry_alive';

function resolveHost() {
  const p = new URLSearchParams(window.location.search).get('host');
  if (p) return p;
  let saved = '';
  try { saved = localStorage.getItem('orv.host') || ''; } catch { /* noop */ }
  return saved || window.location.hostname || 'localhost';
}

export function TelemetryProvider({ children }) {
  const [signals, setSignals] = useState({}); // topic -> { value, ts }
  const [status, setStatus] = useState(() => (simEnabled() ? 'sim' : 'connecting')); // connecting | live | offline | sim
  const histRef = useRef({}); // topic -> number[]
  const clientRef = useRef(null);

  useEffect(() => {
    // Demo mode: REPLAY the recorded real drive into the same store (no broker).
    // This branch never opens an MQTT connection, so simulated data (including the
    // synthetic engaged state) can never reach or engage a real vehicle.
    if (simEnabled()) {
      let cancelled = false;
      let id = null;
      loadSimTimeline().then((tl) => {
        if (cancelled) return;
        const t0 = Date.now();
        const tick = () => {
          const t = (Date.now() - t0) / 1000;
          const snap = simSnapshot(tl, t);
          const ts = Date.now();
          const next = {};
          for (const [topic, value] of Object.entries(snap)) {
            next[topic] = { value, ts };
            if (typeof value === 'number') {
              const h = histRef.current[topic] || (histRef.current[topic] = []);
              h.push(value);
              if (h.length > HISTORY_LEN) h.shift();
            }
          }
          setSignals((prev) => ({ ...prev, ...next }));
        };
        tick();
        id = setInterval(tick, 1000 / (tl.hz || 5));
      });
      return () => { cancelled = true; if (id) clearInterval(id); };
    }

    let active = true;
    let timer = null;
    let flushTimer = null;
    const pending = {}; // topic -> { value, ts } accumulated since the last flush

    const flush = () => {
      const keys = Object.keys(pending);
      if (!keys.length) return;
      const batch = {};
      for (const k of keys) {
        batch[k] = pending[k];
        delete pending[k];
      }
      setSignals((prev) => ({ ...prev, ...batch }));
    };

    const onMessage = (msg) => {
      let value;
      try { value = JSON.parse(msg.payloadString).value; }
      catch { value = msg.payloadString; }
      const topic = msg.destinationName;
      pending[topic] = { value, ts: Date.now() };
      // History gets every sample (sparklines stay full-rate); React state is batched.
      if (typeof value === 'number') {
        const h = histRef.current[topic] || (histRef.current[topic] = []);
        h.push(value);
        if (h.length > HISTORY_LEN) h.shift();
      }
    };

    const scheduleReconnect = () => {
      if (active) timer = setTimeout(connect, 2500); // auto-reconnect
    };

    function connect() {
      const client = new Paho.Client(resolveHost(), 9001, 'orv-' + Math.random().toString(16).slice(2, 10));
      client.onConnectionLost = () => { if (active) { setStatus('offline'); scheduleReconnect(); } };
      client.onMessageArrived = onMessage;
      client.connect({
        timeout: 5,
        onSuccess: () => { if (active) { setStatus('live'); client.subscribe('openrivian/#'); } },
        onFailure: () => { if (active) { setStatus('offline'); scheduleReconnect(); } },
      });
      clientRef.current = client;
    }

    connect();
    flushTimer = setInterval(flush, FLUSH_MS);
    return () => {
      active = false;
      clearTimeout(timer);
      clearInterval(flushTimer);
      try { if (clientRef.current?.isConnected()) clientRef.current.disconnect(); } catch { /* noop */ }
    };
  }, []);

  // NOTE: there is intentionally no publish API here. The telemetry pipeline is
  // one-way: mqtt2params is read-only (its MQTT write path was removed so a stray
  // broker message can never alter persistent vehicle state), so a dashboard
  // publish would just vanish. Settings render read-only instead.

  const api = {
    signals,
    status,
    get: (topic, fallback = undefined) => (signals[topic] ? signals[topic].value : fallback),
    getHistory: (topic) => histRef.current[topic] || [],
    fresh: (topic) => signals[topic] && Date.now() - signals[topic].ts < STALE_MS,
  };

  return <TelemetryContext.Provider value={api}>{children}</TelemetryContext.Provider>;
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext);
  if (!ctx) throw new Error('useTelemetry must be used within TelemetryProvider');
  return ctx;
}
