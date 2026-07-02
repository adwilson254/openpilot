import { describe, it, expect } from 'vitest';
import { decodePolyline, navProgress, planRoute } from '../lib/nav';

describe('decodePolyline', () => {
  it('decodes the canonical Google reference vector (precision 5)', () => {
    // Well-known example from the encoded-polyline spec.
    const encoded = '_p~iF~ps|U_ulLnnqC_mqNvxq`@';
    const pts = decodePolyline(encoded, 5);
    expect(pts).toHaveLength(3);
    expect(pts[0][0]).toBeCloseTo(38.5, 5);
    expect(pts[0][1]).toBeCloseTo(-120.2, 5);
    expect(pts[1][0]).toBeCloseTo(40.7, 5);
    expect(pts[1][1]).toBeCloseTo(-120.95, 5);
    expect(pts[2][0]).toBeCloseTo(43.252, 5);
    expect(pts[2][1]).toBeCloseTo(-126.453, 5);
  });

  it('returns [] for an empty string', () => {
    expect(decodePolyline('', 6)).toEqual([]);
  });
});

describe('navProgress', () => {
  const nav = {
    route: [[0, 0], [0, 0.001], [0, 0.002], [0, 0.003]], // heading east
    maneuvers: [
      { shapeIndex: 0, instruction: 'Head east' },
      { shapeIndex: 2, instruction: 'Turn left' },
      { shapeIndex: 3, instruction: 'Arrive' },
    ],
  };

  it('returns null without a route or position', () => {
    expect(navProgress(null, [0, 0])).toBeNull();
    expect(navProgress(nav, null)).toBeNull();
  });

  it('snaps to the nearest route vertex', () => {
    const p = navProgress(nav, [0, 0.00105]); // closest to index 1
    expect(p.nearestIndex).toBe(1);
    expect(p.offRouteM).toBeGreaterThanOrEqual(0);
  });

  it('remaining distance decreases as you move along the route', () => {
    const early = navProgress(nav, [0, 0.0002]);
    const late = navProgress(nav, [0, 0.0025]);
    expect(late.distanceRemainingM).toBeLessThan(early.distanceRemainingM);
  });

  it('selects the next maneuver beyond the current index', () => {
    const p = navProgress(nav, [0, 0.0011]); // at index 1
    expect(p.next.instruction).toBe('Turn left'); // first maneuver with shapeIndex > 1
    expect(p.distToNextM).toBeGreaterThan(0);
  });

  it('falls back to the final maneuver near the end', () => {
    const p = navProgress(nav, [0, 0.003]);
    expect(p.next.instruction).toBe('Arrive');
  });
});

describe('planRoute', () => {
  it('rejects an unknown provider', async () => {
    await expect(planRoute('does-not-exist', {})).rejects.toThrow(/not implemented/);
  });
});
