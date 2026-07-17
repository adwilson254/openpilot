"""
OpenRivian crawl controller (Rivian R1T, harness-upgrade longitudinal path).

WHAT
  Lets an ENGAGED Rivian creep below the normal 20 mph ACC set-speed floor, in
  1 mph steps down to a 5 mph floor, for construction zones / heavy stop-and-go.
  The set speed IS the cap the longitudinal planner tracks (on the harness path
  carstate_ext writes ret.cruiseState.speed = set_speed), so lowering the floor
  lowers the speed the car will hold.

WHY THIS IS SAFE / NOT A FIRMWARE CHANGE
  - openpilot longitudinal already retains control below 20 mph once engaged
    (validated on route 00000034: engaged down to 5.4 mph, controlsAllowed the
    whole time). The Rivian 20 mph limit is only the stock-ACC *engage* threshold
    and, on the harness path, the MIN_SET_SPEED clamp in carstate_ext. Crawl only
    lowers that software clamp. It does NOT touch panda/safety (accel limits are
    unchanged and already permit low-speed operation). Python-only.

ENTRY IS TIGHTLY GATED (can't be entered by accident, can't be reached by
cycling any selector):
    * openpilot longitudinal must be ENGAGED, and
    * the set speed must already be RESTING at the 20 mph floor, and
    * a fresh SHORT-PRESS of DECREASE (right thumbwheel tilt-left) must arrive, and
    * the vehicle must be slow (<= ENTRY_V_MAX_MPH).
  A held long-press produces only one decrease edge (at its start), so ramping
  down from a high set speed cannot fall through the floor into crawl; only a
  deliberate, separate tap while already resting at 20 mph arms it.

WHILE ACTIVE
  - Each further DECREASE tap steps the cap down 1 mph (floored at 5 mph).
  - Each INCREASE tap steps it up 1 mph; reaching 20 mph EXITS crawl.
  - Driving personality is switched to RELAXED (gentler follow/jerk) and the
    driver's prior personality is restored on exit.

EXIT
  - Cap raised back to 20 mph (increase), OR openpilot longitudinal disengaged.
  - Either restores the prior personality and returns to the normal 20 mph floor.

NOTE (restart behavior): the saved personality is kept in memory only, because
adding a persisted Params key would require a C++ (compiled) change and break the
Python-only / auto-deploy path. If the car process restarts *while crawl is
active*, personality stays at RELAXED (a safe default) until the driver reselects
it. This is a rare edge case and errs on the safe side.
"""
from __future__ import annotations

# Local copy of the conversion so this module has no heavy imports and stays
# unit-testable in isolation. Equals opendbc Conversions.MPH_TO_MS.
MPH_TO_MS = 0.44704

FLOOR_MPH = 5.0          # lowest crawl cap
CEIL_MPH = 20.0          # normal ACC floor (== carstate_ext MIN_SET_SPEED); crawl lives strictly below
STEP_MPH = 1.0           # per-tap step
ENTRY_V_MAX_MPH = 22.0   # cannot arm crawl above this speed (no highway entry)

FLOOR_MS = FLOOR_MPH * MPH_TO_MS
CEIL_MS = CEIL_MPH * MPH_TO_MS
STEP_MS = STEP_MPH * MPH_TO_MS
ENTRY_V_MAX_MS = ENTRY_V_MAX_MPH * MPH_TO_MS
EPS_MS = 0.05            # ~0.1 mph tolerance for float compares

PERSONALITY_KEY = "LongitudinalPersonality"
PERSONALITY_RELAXED = 2  # log.LongitudinalPersonality: aggressive=0, standard=1, relaxed=2


class CrawlController:
  def __init__(self, params=None):
    # params: an openpilot Params()-like object (get/put_nonblocking). May be None
    # in unit tests that only exercise the state machine.
    self._params = params
    self.active = False
    self.cap_ms = CEIL_MS
    self._saved_personality = None

  def update(self, *, engaged: bool, v_ego_ms: float, resting_at_floor: bool,
             dec_edge: bool, inc_edge: bool) -> float | None:
    """Advance the crawl state machine one frame.

    Returns the set-speed cap (m/s) to apply when crawl is active, or None when
    crawl is inactive (caller keeps the normal 20 mph floor clamp).
    """
    # Disengaging openpilot longitudinal always exits crawl and restores the mode.
    if not engaged:
      if self.active:
        self._exit()
      return None

    if not self.active:
      # Strict entry gate. Nothing else can enter crawl.
      if dec_edge and resting_at_floor and v_ego_ms <= ENTRY_V_MAX_MS:
        self.active = True
        self.cap_ms = CEIL_MS - STEP_MS   # 20 -> 19 on entry
        self._enter()                     # save prior personality, switch to relaxed
        return self.cap_ms
      return None

    # Active: step the cap on taps.
    if dec_edge:
      self.cap_ms = max(FLOOR_MS, self.cap_ms - STEP_MS)
    elif inc_edge:
      self.cap_ms += STEP_MS
      if self.cap_ms >= CEIL_MS - EPS_MS:
        # Reached the normal floor again -> leave crawl, restore mode.
        self._exit()
        return None

    return self.cap_ms

  def _enter(self) -> None:
    if self._params is None:
      return
    try:
      # return_default=True so we get the configured value even if never set.
      self._saved_personality = self._params.get(PERSONALITY_KEY, return_default=True)
      self._params.put_nonblocking(PERSONALITY_KEY, PERSONALITY_RELAXED)
    except Exception:
      # Never let a params hiccup break longitudinal; just skip the mode swap.
      self._saved_personality = None

  def _exit(self) -> None:
    self.active = False
    self.cap_ms = CEIL_MS
    if self._params is None or self._saved_personality is None:
      self._saved_personality = None
      return
    try:
      self._params.put_nonblocking(PERSONALITY_KEY, self._saved_personality)
    finally:
      self._saved_personality = None
