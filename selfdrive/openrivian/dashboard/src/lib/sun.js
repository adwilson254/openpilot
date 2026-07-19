// Daytime test for automatic day/night theming. NOAA-style approximation:
// accurate to a few minutes, which is plenty for switching a UI theme.
// Pure functions, no deps, unit-tested.

const rad = (d) => (d * Math.PI) / 180;
const deg = (r) => (r * 180) / Math.PI;

// Day of year, 1-based.
export function dayOfYear(date) {
  const start = Date.UTC(date.getUTCFullYear(), 0, 0);
  return Math.floor((date.getTime() - start) / 86400000);
}

// Returns { riseUTC, setUTC } as fractional hours (UTC) for the given date/place,
// or null for polar day/night. Zenith 90.833° (official sunrise/sunset).
export function sunTimes(date, lat, lon) {
  const N = dayOfYear(date);
  const lngHour = lon / 15;

  const calc = (rising) => {
    const t = N + ((rising ? 6 : 18) - lngHour) / 24;
    const M = 0.9856 * t - 3.289;
    let L = M + 1.916 * Math.sin(rad(M)) + 0.02 * Math.sin(rad(2 * M)) + 282.634;
    L = ((L % 360) + 360) % 360;
    let RA = deg(Math.atan(0.91764 * Math.tan(rad(L))));
    RA = ((RA % 360) + 360) % 360;
    RA += (Math.floor(L / 90) - Math.floor(RA / 90)) * 90;
    RA /= 15;
    const sinDec = 0.39782 * Math.sin(rad(L));
    const cosDec = Math.cos(Math.asin(sinDec));
    const cosH = (Math.cos(rad(90.833)) - sinDec * Math.sin(rad(lat))) / (cosDec * Math.cos(rad(lat)));
    if (cosH > 1 || cosH < -1) return null; // polar night / midnight sun
    let H = rising ? 360 - deg(Math.acos(cosH)) : deg(Math.acos(cosH));
    H /= 15;
    const T = H + RA - 0.06571 * t - 6.622;
    let UT = T - lngHour;
    return ((UT % 24) + 24) % 24;
  };

  const riseUTC = calc(true);
  const setUTC = calc(false);
  if (riseUTC === null || setUTC === null) return null;
  return { riseUTC, setUTC };
}

// True when the sun is up at `date` for lat/lon. Falls back to local clock
// (7:00-19:00 = day) when there is no GPS fix.
export function isDaytime(date, lat, lon) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    const h = date.getHours();
    return h >= 7 && h < 19;
  }
  const t = sunTimes(date, lat, lon);
  const nowUTC = date.getUTCHours() + date.getUTCMinutes() / 60;
  if (!t) {
    // Polar edge case: pick by season-ish heuristic (sun never crosses zenith).
    return lat > 0 ? date.getUTCMonth() >= 3 && date.getUTCMonth() <= 8
                   : date.getUTCMonth() < 3 || date.getUTCMonth() > 8;
  }
  const { riseUTC, setUTC } = t;
  return riseUTC < setUTC
    ? nowUTC >= riseUTC && nowUTC < setUTC
    : nowUTC >= riseUTC || nowUTC < setUTC; // set wraps past midnight UTC
}
