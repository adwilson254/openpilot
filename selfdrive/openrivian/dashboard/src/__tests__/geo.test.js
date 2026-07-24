import { describe, it, expect } from 'vitest';
import { lon2fx, lat2fy, fx2lon, fy2lat, haversine, km, mi } from '../lib/geo';

describe('slippy-tile projection', () => {
  it('maps lon/lat to fractional tile coords at z=0 (whole world in one tile)', () => {
    // At z0 the world spans fx,fy in [0,1]; (0,0) lon/lat is the tile center.
    expect(lon2fx(0, 0)).toBeCloseTo(0.5, 6);
    expect(lat2fy(0, 0)).toBeCloseTo(0.5, 6);
    expect(lon2fx(-180, 0)).toBeCloseTo(0, 6);
    expect(lon2fx(180, 0)).toBeCloseTo(1, 6);
  });

  it('is invertible: fx2lon(lon2fx(x)) === x', () => {
    for (const z of [0, 5, 13, 18]) {
      for (const lon of [-179.9, -122.4194, 0, 37.6, 151.2]) {
        expect(fx2lon(lon2fx(lon, z), z)).toBeCloseTo(lon, 6);
      }
      for (const lat of [-66, -33.9, 0, 37.7749, 64]) {
        expect(fy2lat(lat2fy(lat, z), z)).toBeCloseTo(lat, 6);
      }
    }
  });

  it('y increases as latitude decreases (north is up)', () => {
    expect(lat2fy(40, 13)).toBeLessThan(lat2fy(30, 13));
  });
});

describe('haversine', () => {
  it('returns 0 for identical points', () => {
    expect(haversine([37.7749, -122.4194], [37.7749, -122.4194])).toBe(0);
  });

  it('one degree of latitude is ~111 km', () => {
    const d = haversine([0, 0], [1, 0]);
    expect(km(d)).toBeGreaterThan(110);
    expect(km(d)).toBeLessThan(112);
  });

  it('SF -> LA is ~559 km (within 2%)', () => {
    const d = haversine([37.7749, -122.4194], [34.0522, -118.2437]);
    expect(km(d)).toBeGreaterThan(548);
    expect(km(d)).toBeLessThan(570);
  });

  it('is symmetric', () => {
    const a = [40.0, -75.0], b = [41.0, -74.0];
    expect(haversine(a, b)).toBeCloseTo(haversine(b, a), 6);
  });
});

describe('unit helpers', () => {
  it('km and mi convert from meters', () => {
    expect(km(1000)).toBe(1);
    expect(mi(1609.34)).toBeCloseTo(1, 4);
  });
});
