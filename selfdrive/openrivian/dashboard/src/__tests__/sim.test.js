import { describe, it, expect } from 'vitest';
import { simSnapshot } from '../lib/sim';
import { T } from '../lib/format';
import drive from '../assets/sim_drive.json';

const tl = {
  hz: 1,
  topics: [T.speed_mph, T.lat],
  frames: [[10, 35.0], [20, 35.1], [30, 35.2], [40, 35.3], [50, 35.4]],
};

describe('sim replay of recorded drive', () => {
  it('maps a frame to topic values', () => {
    const s = simSnapshot(tl, 0);
    expect(s[T.speed_mph]).toBe(10);
    expect(s[T.lat]).toBe(35.0);
  });

  it('loops seamlessly (5 frames @1Hz wraps at t=5)', () => {
    expect(simSnapshot(tl, 5)[T.speed_mph]).toBe(simSnapshot(tl, 0)[T.speed_mph]);
  });

  it('returns empty snapshot for an empty/missing timeline', () => {
    expect(simSnapshot(null, 0)).toEqual({});
    expect(simSnapshot({ hz: 1, topics: [], frames: [] }, 0)).toEqual({});
  });
});

describe('synthetic engagement overlay (display-only)', () => {
  it('always reports adasEnabled true', () => {
    for (const t of [0, 1, 2, 3, 4]) expect(simSnapshot(tl, t)[T.adasEnabled]).toBe(true);
  });

  it('engages self-drive over the middle of the loop and not at the ends', () => {
    expect(simSnapshot(tl, 0)[T.adasActive]).toBe(false); // phase 0.0
    expect(simSnapshot(tl, 2)[T.adasActive]).toBe(true);  // phase 0.4
    expect(simSnapshot(tl, 4)[T.adasActive]).toBe(false); // phase 0.8
  });

  it('the loop exercises both engaged and disengaged states', () => {
    const actives = [0, 1, 2, 3, 4].map((t) => simSnapshot(tl, t)[T.adasActive]);
    expect(actives).toContain(true);
    expect(actives).toContain(false);
  });
});

describe('bundled real Rivian drive', () => {
  it('has the expected compact shape and real telemetry', () => {
    expect(drive.hz).toBeGreaterThan(0);
    expect(Array.isArray(drive.topics)).toBe(true);
    expect(drive.topics).toContain(T.speed_mph);
    expect(drive.topics).toContain(T.lat);
    expect(drive.frames.length).toBeGreaterThan(100);
    // a real drive reaches a real speed
    const si = drive.topics.indexOf(T.speed_mph);
    const maxSpeed = Math.max(...drive.frames.map((r) => r[si]).filter((v) => typeof v === 'number'));
    expect(maxSpeed).toBeGreaterThan(10);
  });
});
