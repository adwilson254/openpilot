// Demo / design-preview simulator. Enabled with ?sim=1 so the dashboard can be viewed
// on a laptop without a comma device / MQTT broker. It REPLAYS a real recorded Rivian
// drive (src/assets/sim_drive.json, captured from the vehicle) on a loop.
//
// SAFETY: this only runs in ?sim=1 mode, which never connects to or publishes to an
// MQTT broker (see mqtt.jsx) -- it feeds the local display store only. It therefore
// cannot reach, control, or engage a real vehicle. The ADAS engagement below is a
// SYNTHETIC overlay (the source drive was fully manual) purely so the dashboard's
// "self-drive engaged" UI can be exercised off-vehicle. It is display-only.
import { T } from './format';

export function simEnabled() {
  return new URLSearchParams(window.location.search).get('sim') === '1';
}

let _timeline = null;

// Lazily load the recorded drive only in sim mode (kept out of the main bundle via
// dynamic import). Returns { hz, topics, frames }.
export async function loadSimTimeline() {
  if (_timeline) return _timeline;
  const mod = await import('../assets/sim_drive.json');
  _timeline = mod.default || mod;
  return _timeline;
}

// Synthetic, display-only engagement window: engage self-drive over the middle of the
// loop so the engaged-state UI is testable. NOT real control -- see file header.
function engagement(frameIndex, total) {
  const phase = total ? frameIndex / total : 0;
  return { enabled: true, active: phase > 0.3 && phase < 0.7 };
}

// Map the looped frame at time t (seconds) to a flat { topic: value } snapshot.
export function simSnapshot(tl, t) {
  if (!tl || !tl.frames.length) return {};
  const n = tl.frames.length;
  const i = ((Math.floor(t * tl.hz) % n) + n) % n; // wrap -> seamless loop
  const row = tl.frames[i];
  const snap = {};
  for (let j = 0; j < tl.topics.length; j++) {
    if (row[j] !== null && row[j] !== undefined) snap[tl.topics[j]] = row[j];
  }
  // Overlay synthetic (display-only) engagement so the self-drive UI is exercised.
  const eng = engagement(i, n);
  snap[T.adasEnabled] = eng.enabled;
  snap[T.adasActive] = eng.active;
  return snap;
}
