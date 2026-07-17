#!/usr/bin/env python3
"""
Unit tests for the OpenRivian crawl controller
(opendbc/sunnypilot/car/rivian/crawl.py).

These exercise the pure state machine + personality save/restore with a fake
Params, covering the safety-critical requirements:
  - crawl cannot be entered by accident (must be engaged + resting at the 20 mph
    floor + a fresh decrease tap + low speed),
  - stepping down 20->5 and back up, exit at 20,
  - exit on disengage,
  - the prior driving personality is saved on entry and restored on exit.

The module is loaded by file path so the test runs under any Python without
importing the full `opendbc` package (whose __init__ needs Python 3.10+).
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_CRAWL_PATH = os.path.normpath(os.path.join(
    _HERE, "..", "..", "..", "opendbc_repo", "opendbc", "sunnypilot", "car", "rivian", "crawl.py"))
_spec = importlib.util.spec_from_file_location("or_crawl", _CRAWL_PATH)
crawl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crawl)

CrawlController = crawl.CrawlController
MPH_TO_MS = crawl.MPH_TO_MS
PERSONALITY_KEY = crawl.PERSONALITY_KEY
PERSONALITY_RELAXED = crawl.PERSONALITY_RELAXED

STANDARD = 1  # driver's personality before crawl (aggressive=0, standard=1, relaxed=2)


class FakeParams:
  """Minimal Params stand-in recording get/put_nonblocking."""
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.puts = []

  def get(self, key, return_default=False):
    return self.values.get(key)

  def put_nonblocking(self, key, val):
    self.values[key] = val
    self.puts.append((key, val))


def mph(ms):
  return ms / MPH_TO_MS


class TestCrawlEntryGate(unittest.TestCase):
  def setUp(self):
    self.p = FakeParams({PERSONALITY_KEY: STANDARD})
    self.c = CrawlController(self.p)

  def _upd(self, **kw):
    base = dict(engaged=True, v_ego_ms=18 * MPH_TO_MS, resting_at_floor=True,
                dec_edge=False, inc_edge=False)
    base.update(kw)
    return self.c.update(**base)

  def test_no_entry_when_not_engaged(self):
    self.assertIsNone(self._upd(engaged=False, dec_edge=True))
    self.assertFalse(self.c.active)

  def test_no_entry_without_decrease_edge(self):
    self.assertIsNone(self._upd(dec_edge=False))
    self.assertFalse(self.c.active)

  def test_no_entry_when_not_resting_at_floor(self):
    # e.g. set speed is at 30 mph; a decrease there must NOT enter crawl
    self.assertIsNone(self._upd(resting_at_floor=False, dec_edge=True))
    self.assertFalse(self.c.active)

  def test_no_entry_when_too_fast(self):
    self.assertIsNone(self._upd(v_ego_ms=40 * MPH_TO_MS, dec_edge=True))
    self.assertFalse(self.c.active)

  def test_entry_only_with_full_gate(self):
    cap = self._upd(dec_edge=True)
    self.assertTrue(self.c.active)
    self.assertAlmostEqual(mph(cap), 19.0, places=3)
    # personality saved and switched to relaxed
    self.assertEqual(self.p.values[PERSONALITY_KEY], PERSONALITY_RELAXED)


class TestCrawlStepping(unittest.TestCase):
  def setUp(self):
    self.p = FakeParams({PERSONALITY_KEY: STANDARD})
    self.c = CrawlController(self.p)
    # enter crawl
    self.c.update(engaged=True, v_ego_ms=18 * MPH_TO_MS, resting_at_floor=True,
                  dec_edge=True, inc_edge=False)

  def step(self, dec=False, inc=False, v=10 * MPH_TO_MS):
    return self.c.update(engaged=True, v_ego_ms=v, resting_at_floor=False,
                         dec_edge=dec, inc_edge=inc)

  def test_step_down_to_floor_and_clamp(self):
    caps = [self.step(dec=True) for _ in range(20)]
    # from 19 stepping down, never below 5 mph
    self.assertAlmostEqual(mph(caps[-1]), 5.0, places=3)
    self.assertTrue(all(mph(c) >= 5.0 - 1e-6 for c in caps))

  def test_step_up_exits_at_20(self):
    # from 19 up one -> 20 -> exit
    out = self.step(inc=True)
    self.assertIsNone(out)
    self.assertFalse(self.c.active)
    # personality restored to the pre-crawl value
    self.assertEqual(self.p.values[PERSONALITY_KEY], STANDARD)

  def test_idle_holds_cap(self):
    a = self.step()
    b = self.step()
    self.assertAlmostEqual(mph(a), 19.0, places=3)
    self.assertAlmostEqual(mph(b), 19.0, places=3)
    self.assertTrue(self.c.active)


class TestCrawlExitRestore(unittest.TestCase):
  def test_disengage_exits_and_restores(self):
    p = FakeParams({PERSONALITY_KEY: STANDARD})
    c = CrawlController(p)
    c.update(engaged=True, v_ego_ms=15 * MPH_TO_MS, resting_at_floor=True,
             dec_edge=True, inc_edge=False)
    self.assertTrue(c.active)
    self.assertEqual(p.values[PERSONALITY_KEY], PERSONALITY_RELAXED)
    # disengage
    out = c.update(engaged=False, v_ego_ms=15 * MPH_TO_MS, resting_at_floor=False,
                   dec_edge=False, inc_edge=False)
    self.assertIsNone(out)
    self.assertFalse(c.active)
    self.assertEqual(p.values[PERSONALITY_KEY], STANDARD)

  def test_reentry_after_exit_saves_current_personality(self):
    # If the driver picked 'aggressive' (0) after a prior crawl, re-entry must
    # save 0 and restore 0 (not a stale value).
    p = FakeParams({PERSONALITY_KEY: 0})
    c = CrawlController(p)
    c.update(engaged=True, v_ego_ms=15 * MPH_TO_MS, resting_at_floor=True, dec_edge=True, inc_edge=False)
    self.assertEqual(p.values[PERSONALITY_KEY], PERSONALITY_RELAXED)
    c.update(engaged=False, v_ego_ms=15 * MPH_TO_MS, resting_at_floor=False, dec_edge=False, inc_edge=False)
    self.assertEqual(p.values[PERSONALITY_KEY], 0)


class TestCrawlNoParams(unittest.TestCase):
  def test_state_machine_without_params(self):
    # params=None must not raise (personality swap simply skipped)
    c = CrawlController(None)
    cap = c.update(engaged=True, v_ego_ms=10 * MPH_TO_MS, resting_at_floor=True,
                   dec_edge=True, inc_edge=False)
    self.assertAlmostEqual(mph(cap), 19.0, places=3)
    c.update(engaged=False, v_ego_ms=10 * MPH_TO_MS, resting_at_floor=False,
             dec_edge=False, inc_edge=False)
    self.assertFalse(c.active)


if __name__ == "__main__":
  unittest.main()
