import { describe, it, expect } from 'vitest';
import { T } from '../lib/format';
import daemonTopics from './daemon_topics.json';

const DAEMON = new Set(daemonTopics.topics);

describe('topic contract (UI <-> cereal2mqtt)', () => {
  it('T-map values are well-formed and unique', () => {
    const values = Object.values(T);
    for (const v of values) {
      expect(typeof v).toBe('string');
      expect(v.startsWith('openrivian/')).toBe(true);
    }
    expect(new Set(values).size).toBe(values.length); // no duplicate topics
  });

  it('every topic the UI reads is published by the daemon', () => {
    const orphans = Object.entries(T)
      .filter(([, topic]) => !DAEMON.has(topic))
      .map(([key, topic]) => `${key} -> ${topic}`);
    expect(orphans, `UI reads topics the daemon never publishes:\n${orphans.join('\n')}`).toEqual([]);
  });

  it('every daemon topic is consumed by the UI (T-map has no blind spots)', () => {
    // engine_rpm (the one known extra) was removed from the daemon: it read a
    // deprecated field that is meaningless on an EV. The sets now match exactly;
    // if the daemon grows a topic the UI doesn't know, this surfaces it.
    const consumed = new Set(Object.values(T));
    const unused = [...DAEMON].filter((t) => !consumed.has(t));
    expect(unused).toEqual([]);
  });
});
