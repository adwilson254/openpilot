/* The telemetry store keeps a ref-backed ring buffer of recent values for sparklines.
   It is intentionally read during render (the provider re-renders on every message, so
   the buffer is always current), and this module deliberately exports both the provider
   and its hook — the lint rule below is noise for this pattern. */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import Paho from 'paho-mqtt';
import { simEnabled, simSnapshot } from './sim';

const TelemetryContext = createContext(null);

const HISTORY_LEN = 90;   // samples kept per topic for sparklines
const STALE_MS = 5000;    // older than this => considered stale

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
    // Demo mode: feed synthetic values into the same store (no broker needed).
    if (simEnabled()) {
      const t0 = Date.now();
      const tick = () => {
        const t = (Date.now() - t0) / 1000;
        const snap = simSnapshot(t);
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
      const id = setInterval(tick, 200); // 5 Hz
      return () => clearInterval(id);
    }

    let active = true;
    let timer = null;

    const onMessage = (msg) => {
      let value;
      try { value = JSON.parse(msg.payloadString).value; }
      catch { value = msg.payloadString; }
      const topic = msg.destinationName;
      setSignals((prev) => ({ ...prev, [topic]: { value, ts: Date.now() } }));
      if (typeof value === 'number') {
        const h = histRef.current[topic] || (histRef.current[topic] = []);
        h.push(value);
        if (h.length > HISTORY_LEN) h.shift();
      }
    };

    const scheduleReconnect = () => {
      if (active) timer = setTimeout(connect, 2500); // auto-reconnect (was missing before)
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
    return () => {
      active = false;
      clearTimeout(timer);
      try { if (clientRef.current?.isConnected()) clientRef.current.disconnect(); } catch { /* noop */ }
    };
  }, []);

  const publish = useCallback((topic, obj) => {
    const c = clientRef.current;
    if (!c || !c.isConnected()) return false;
    const m = new Paho.Message(JSON.stringify(obj));
    m.destinationName = topic;
    c.send(m);
    return true;
  }, []);

  const publishSetting = useCallback((key, value) => publish(`openrivian/settings/set/${key}`, { value }), [publish]);

  const api = {
    signals,
    status,
    publish,
    publishSetting,
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
