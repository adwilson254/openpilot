import { haversine } from './geo';

// Decode a Valhalla / Google encoded polyline (Valhalla uses precision 6).
export function decodePolyline(str, precision = 6) {
  let index = 0, lat = 0, lon = 0;
  const coords = [], factor = 10 ** precision;
  while (index < str.length) {
    let result = 1, shift = 0, b;
    do { b = str.charCodeAt(index++) - 63 - 1; result += b << shift; shift += 5; } while (b >= 0x1f);
    lat += (result & 1) ? ~(result >> 1) : (result >> 1);
    result = 1; shift = 0;
    do { b = str.charCodeAt(index++) - 63 - 1; result += b << shift; shift += 5; } while (b >= 0x1f);
    lon += (result & 1) ? ~(result >> 1) : (result >> 1);
    coords.push([lat / factor, lon / factor]);
  }
  return coords;
}

// --- Route providers -----------------------------------------------------
// Each returns a normalized nav object:
//   { provider, route:[[lat,lon]…], maneuvers:[{type,instruction,distanceM,timeS,street,shapeIndex}],
//     summary:{distanceM,timeS}, chargeStops?:[…] }

async function planValhalla(base, from, to) {
  const url = `${base.replace(/\/$/, '')}/route`;
  const body = {
    locations: [{ lat: from[0], lon: from[1] }, { lat: to[0], lon: to[1] }],
    costing: 'auto',
    directions_options: { units: 'kilometers' },
  };
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`Valhalla HTTP ${res.status}`);
  const data = await res.json();
  const leg = data?.trip?.legs?.[0];
  if (!leg) throw new Error('No route returned');
  return {
    provider: 'valhalla',
    route: decodePolyline(leg.shape, 6),
    maneuvers: (leg.maneuvers || []).map((m) => ({
      type: m.type,
      instruction: m.instruction,
      distanceM: (m.length || 0) * 1000,
      timeS: m.time || 0,
      street: (m.street_names || []).join(', '),
      shapeIndex: m.begin_shape_index || 0,
    })),
    summary: { distanceM: (data.trip.summary.length || 0) * 1000, timeS: data.trip.summary.time || 0 },
  };
}

// Pluggable entry point. Rivian (planTripMultiStop) will register here once its query
// is finalized, returning the same normalized shape (+ chargeStops).
export async function planRoute(provider, opts) {
  if (provider === 'valhalla') return planValhalla(opts.valhallaBase, opts.from, opts.to);
  throw new Error(`route provider '${provider}' not implemented`);
}

// Live progress along a planned route given current position.
export function navProgress(nav, pos) {
  if (!nav?.route?.length || !pos) return null;
  let best = 0, bestD = Infinity;
  for (let i = 0; i < nav.route.length; i++) {
    const d = haversine(nav.route[i], pos);
    if (d < bestD) { bestD = d; best = i; }
  }
  let remaining = 0;
  for (let i = best; i < nav.route.length - 1; i++) remaining += haversine(nav.route[i], nav.route[i + 1]);
  const next = nav.maneuvers.find((m) => m.shapeIndex > best) || nav.maneuvers[nav.maneuvers.length - 1];
  let toNext = 0;
  if (next) for (let i = best; i < next.shapeIndex && i < nav.route.length - 1; i++) toNext += haversine(nav.route[i], nav.route[i + 1]);
  return { nearestIndex: best, offRouteM: bestD, distanceRemainingM: remaining, next, distToNextM: toNext };
}
