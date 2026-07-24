import { describe, it, expect } from 'vitest';
import { tileUrl, tileFallbackUrl, tileSpan, zoomForSpeed, TILE } from '../lib/geo';
import { createTripStore } from '../lib/trip';
import { sunTimes, isDaytime, dayOfYear } from '../lib/sun';
import { maneuverIcon, IconTurnRight, IconTurnLeft, IconStraight, IconArrive } from '../lib/icons';

describe('map tile helpers', () => {
  it('tileUrl targets the same-origin webd proxy', () => {
    expect(tileUrl(13, 1310, 3166)).toBe('/tiles/13/1310/3166.png');
  });
  it('fallback targets OSM directly', () => {
    expect(tileFallbackUrl(13, 1, 2)).toBe('https://tile.openstreetmap.org/13/1/2.png');
  });
  it('tileSpan covers the viewport with overscan', () => {
    expect(tileSpan(TILE * 3)).toBe(5);
    expect(tileSpan(1)).toBe(3);
  });
  it('zoomForSpeed: close-in parked, wide at highway speed, clamped', () => {
    expect(zoomForSpeed(0)).toBe(16);
    expect(zoomForSpeed(35)).toBe(14);
    expect(zoomForSpeed(80)).toBe(13);
    expect(zoomForSpeed(200)).toBe(13);
    expect(zoomForSpeed(NaN)).toBe(16);
  });
});

describe('trip store (module-level: survives view unmounts)', () => {
  it('accumulates distance, max, engaged time', () => {
    const s = createTripStore();
    s.tick(36, true);   // 36 mph for 1s = 0.01 mi
    s.tick(72, false);
    const snap = s.snapshot();
    expect(snap.distMi).toBeCloseTo(0.03, 5);
    expect(snap.maxMph).toBe(72);
    expect(snap.avgMph).toBe(54);
    expect(snap.engagedS).toBe(1);
  });
  it('reset zeroes the accumulator', () => {
    const s = createTripStore();
    s.tick(10, true);
    s.reset();
    expect(s.snapshot().distMi).toBe(0);
    expect(s.snapshot().engagedS).toBe(0);
  });
  it('treats non-finite speed as 0 (never NaN-poisons the trip)', () => {
    const s = createTripStore();
    s.tick(undefined, false);
    s.tick(NaN, false);
    expect(s.snapshot().distMi).toBe(0);
  });
});

describe('sun calculator (auto day/night)', () => {
  // San Francisco, 2026-06-21 (solstice): sunrise ~05:48, sunset ~20:35 local
  // = ~12:48 / ~03:35 UTC(+1d). Assert within 30 minutes.
  it('solstice sunrise/sunset for SF within tolerance', () => {
    const d = new Date(Date.UTC(2026, 5, 21, 18, 0, 0));
    const t = sunTimes(d, 37.77, -122.42);
    expect(t).not.toBeNull();
    expect(Math.abs(t.riseUTC - 12.8)).toBeLessThan(0.5);
    expect(Math.abs(t.setUTC - 3.6)).toBeLessThan(0.5);
  });
  it('noon local is daytime, midnight is night (SF)', () => {
    expect(isDaytime(new Date(Date.UTC(2026, 5, 21, 20, 0, 0)), 37.77, -122.42)).toBe(true);  // 1pm PDT
    expect(isDaytime(new Date(Date.UTC(2026, 5, 21, 9, 0, 0)), 37.77, -122.42)).toBe(false);  // 2am PDT
  });
  it('falls back to clock hours without a fix', () => {
    const noonLocal = new Date(2026, 5, 21, 12, 0, 0);
    const nightLocal = new Date(2026, 5, 21, 23, 30, 0);
    expect(isDaytime(noonLocal, NaN, NaN)).toBe(true);
    expect(isDaytime(nightLocal, NaN, NaN)).toBe(false);
  });
  it('dayOfYear is 1-based and correct', () => {
    expect(dayOfYear(new Date(Date.UTC(2026, 0, 1)))).toBe(1);
    expect(dayOfYear(new Date(Date.UTC(2026, 11, 31)))).toBe(365);
  });
});

describe('maneuver icon mapping', () => {
  it('buckets Valhalla types', () => {
    expect(maneuverIcon(10)).toBe(IconTurnRight);
    expect(maneuverIcon(15)).toBe(IconTurnLeft);
    expect(maneuverIcon(8)).toBe(IconStraight);
    expect(maneuverIcon(4)).toBe(IconArrive);
  });
});
