"""
Unit tests for the HUD state mapping (hud_state.HudStateBuilder).

Pure-python: uses SimpleNamespace mocks, so no cereal/runtime needed.
Run directly:  python selfdrive/openrivian/hud/tests/test_hud_state.py
or via pytest:  pytest selfdrive/openrivian/hud/tests/
"""
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hud_state import (  # noqa: E402
    HudStateBuilder,
    STATUS_ENGAGED,
    STATUS_DISENGAGED,
    STATUS_OVERRIDE,
    BORDER_COLORS,
)


def car_state(**kw):
    base = dict(vEgo=0.0, vEgoCluster=0.0, vCruiseCluster=0.0, leftBlinker=False,
                rightBlinker=False, brakePressed=False, gasPressed=False,
                standstill=False, gearShifter="drive")
    base.update(kw)
    return NS(**base)


def selfdrive_state(**kw):
    base = dict(state="disabled", enabled=False, experimentalMode=False,
                alertText1="", alertText2="", alertStatus="normal",
                alertSize="none", personality="standard")
    base.update(kw)
    return NS(**base)


def controls_state(v_cruise=0.0):
    return NS(deprecated=NS(vCruise=v_cruise))


def test_current_speed_imperial():
    b = HudStateBuilder(is_metric=False)
    s = b.build({"carState": car_state(vEgo=10.0, vEgoCluster=10.0)})
    assert s["speed"] == 22  # 10 m/s * 2.23694
    assert s["speedUnit"] == "mph"


def test_current_speed_metric():
    b = HudStateBuilder(is_metric=True)
    s = b.build({"carState": car_state(vEgo=10.0, vEgoCluster=10.0)})
    assert s["speed"] == 36  # 10 m/s * 3.6
    assert s["speedUnit"] == "km/h"


def test_set_speed_from_cluster_imperial():
    b = HudStateBuilder(is_metric=False)
    s = b.build({"carState": car_state(vCruiseCluster=50.0)})  # 50 kph
    assert s["cruiseSet"] is True
    assert s["cruiseAvailable"] is True
    assert s["setSpeed"] == 31  # round(50 * 0.621371)


def test_set_speed_fallback_to_controls_deprecated():
    b = HudStateBuilder(is_metric=True)
    s = b.build({"carState": car_state(vCruiseCluster=0.0), "controlsState": controls_state(v_cruise=80.0)})
    assert s["cruiseSet"] is True
    assert s["setSpeed"] == 80  # metric, no conversion


def test_cruise_unavailable_when_minus_one():
    b = HudStateBuilder()
    s = b.build({"carState": car_state(vCruiseCluster=-1.0)})
    assert s["cruiseAvailable"] is False
    assert s["cruiseSet"] is False
    assert s["setSpeed"] is None


def test_status_and_border_colors():
    b = HudStateBuilder()
    eng = b.build({"selfdriveState": selfdrive_state(state="enabled", enabled=True)})
    assert eng["status"] == STATUS_ENGAGED
    assert eng["borderColor"] == BORDER_COLORS[STATUS_ENGAGED]

    dis = b.build({"selfdriveState": selfdrive_state(state="disabled", enabled=False)})
    assert dis["status"] == STATUS_DISENGAGED
    assert dis["borderColor"] == BORDER_COLORS[STATUS_DISENGAGED]

    ovr = b.build({"selfdriveState": selfdrive_state(state="overriding", enabled=True)})
    assert ovr["status"] == STATUS_OVERRIDE
    assert ovr["borderColor"] == BORDER_COLORS[STATUS_OVERRIDE]


def test_alert_passthrough():
    b = HudStateBuilder()
    s = b.build({"selfdriveState": selfdrive_state(alertText1="Take Control", alertText2="Immediately", alertStatus="critical")})
    assert s["alert"]["text1"] == "Take Control"
    assert s["alert"]["status"] == "critical"


def test_no_messages_defaults():
    b = HudStateBuilder()
    s = b.build({})
    assert s["speed"] == 0
    assert s["status"] == STATUS_DISENGAGED
    assert s["alert"] is None


def test_vego_cluster_latch():
    b = HudStateBuilder(is_metric=True)
    # cluster present -> used
    s1 = b.build({"carState": car_state(vEgo=5.0, vEgoCluster=10.0)})
    assert s1["speed"] == 36  # uses cluster (10 m/s)
    # once seen, latch stays even if cluster reports 0 (matches device behavior)
    s2 = b.build({"carState": car_state(vEgo=5.0, vEgoCluster=0.0)})
    assert s2["speed"] == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")
