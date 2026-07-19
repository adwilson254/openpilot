// Web-Mercator / slippy-tile math + distance. Pure functions, no deps.
export const TILE = 256;

export const lon2fx = (lon, z) => ((lon + 180) / 360) * 2 ** z;
export const lat2fy = (lat, z) => {
  const r = (lat * Math.PI) / 180;
  return ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * 2 ** z;
};
export const fx2lon = (fx, z) => (fx / 2 ** z) * 360 - 180;
export const fy2lat = (fy, z) => {
  const n = Math.PI * (1 - (2 * fy) / 2 ** z);
  return (Math.atan(Math.sinh(n)) * 180) / Math.PI;
};

// meters between [lat,lon] pairs
export function haversine(a, b) {
  const R = 6371000, toR = Math.PI / 180;
  const dLat = (b[0] - a[0]) * toR, dLon = (b[1] - a[1]) * toR;
  const la1 = a[0] * toR, la2 = b[0] * toR;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export const km = (m) => (m / 1000);
export const mi = (m) => (m / 1609.34);

// --- MapCanvas helpers (pure, unit-tested) ---------------------------------

// Tile source: same-origin webd proxy (cached on the comma). The renderer swaps
// a failed tile to the public upstream once (dev servers without the proxy).
export const tileUrl = (z, x, y) => `/tiles/${z}/${x}/${y}.png`;
export const tileFallbackUrl = (z, x, y) => `https://tile.openstreetmap.org/${z}/${x}/${y}.png`;

// How many tile columns/rows cover a viewport (+2 overscan for panning).
export const tileSpan = (px) => Math.ceil(px / TILE) + 2;

// Follow-mode auto zoom: close-in when parked, wider with speed.
// 0 mph -> 16, ~35 mph -> 14, >=70 mph -> 13 (clamped).
export function zoomForSpeed(mph) {
  const v = Number.isFinite(mph) ? Math.max(0, mph) : 0;
  return Math.round(Math.min(16, Math.max(13, 16 - v / 23)));
}
