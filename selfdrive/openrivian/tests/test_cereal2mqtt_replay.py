"""Tier-1 process-replay tests for the telemetry bridge.

Drives cereal2mqtt.publish_state through the replay harness with synthetic frames
and asserts the MQTT contract (topic presence + value transforms). The same code
path runs over real route logs via `harness.route_frames(path)` when a recorded
drive is available -- see selfdrive/openrivian/replay/harness.py.
"""
import math

from selfdrive.openrivian.replay import harness


def _run(frame):
    """Replay a single snapshot and return the RecordingClient."""
    return harness.replay([frame])


def test_synthetic_replay_emits_core_topics():
    client = harness.replay(harness.synthetic_frames(n=20))
    topics = set(client.topics())
    expected = {
        "openrivian/vehicle/powertrain/speed_ms",
        "openrivian/vehicle/powertrain/speed_mph",
        "openrivian/vehicle/powertrain/gear",
        "openrivian/vehicle/powertrain/wheel_speed_fl",
        "openrivian/vehicle/location/latitude",
        "openrivian/vehicle/location/longitude",
        "openrivian/vehicle/location/bearing",
        "openrivian/device/hardware/voltage",
        "openrivian/device/hardware/camerad_running",
    }
    missing = expected - topics
    assert not missing, f"replay did not publish: {missing}"


def test_speed_mph_is_ms_times_constant():
    frame = next(harness.synthetic_frames(n=1))
    frame["carState"]["vEgo"] = 10.0
    client = _run(frame)
    assert client.last("openrivian/vehicle/powertrain/speed_ms") == 10.0
    # publish_safely rounds floats to 4 dp
    assert client.last("openrivian/vehicle/powertrain/speed_mph") == round(10.0 * 2.23694, 4)


def test_voltage_is_millivolts_over_1000():
    frame = next(harness.synthetic_frames(n=1))
    frame["pandaStates"] = [{"ignitionLine": True, "ignitionCan": False, "voltage": 12345}]
    client = _run(frame)
    assert client.last("openrivian/device/hardware/voltage") == 12.345


def test_location_published_only_with_gps_fix():
    frame = next(harness.synthetic_frames(n=1))
    frame["gpsLocationExternal"] = {"hasFix": False, "latitude": 1.0, "longitude": 2.0,
                                    "altitude": 3.0, "bearingDeg": 90.0}
    client = _run(frame)
    assert client.last("openrivian/vehicle/location/latitude") is None
    assert client.last("openrivian/vehicle/location/longitude") is None
    assert client.last("openrivian/vehicle/location/bearing") is None


def test_location_values_pass_through_with_fix():
    frame = next(harness.synthetic_frames(n=1))
    frame["gpsLocationExternal"] = {"hasFix": True, "latitude": 37.5, "longitude": -122.5,
                                    "altitude": 50.0, "bearingDeg": 271.25}
    client = _run(frame)
    assert client.last("openrivian/vehicle/location/latitude") == 37.5
    assert client.last("openrivian/vehicle/location/longitude") == -122.5
    assert client.last("openrivian/vehicle/location/altitude") == 50.0
    # bearing is course-over-ground in DEGREES, passed through (not roll/radians --
    # the old liveLocationKalman path published calibratedOrientationNED[0] = roll).
    assert client.last("openrivian/vehicle/location/bearing") == 271.25


def test_bearing_normalized_to_0_360():
    frame = next(harness.synthetic_frames(n=1))
    frame["gpsLocationExternal"] = {"hasFix": True, "latitude": 0.0, "longitude": 0.0,
                                    "altitude": 0.0, "bearingDeg": -10.0}
    client = _run(frame)
    assert client.last("openrivian/vehicle/location/bearing") == 350.0


def test_sched_health_flags_demotion():
    # nice 0 core procs -> healthy; a demoted core proc -> canary trips. Our own
    # daemons (selfdrive.openr*) run nice 19 by design and must NOT trip it.
    frame = next(harness.synthetic_frames(n=1))
    frame["procLog"] = {"procs": [{"name": "selfdrive.selfd", "nice": 0},
                                  {"name": "selfdrive.openr", "nice": 19}]}
    client = _run(frame)
    assert client.last("openrivian/health/sched_demoted") is False
    assert client.last("openrivian/health/sched_nice_max") == 0

    frame["procLog"] = {"procs": [{"name": "selfdrive.selfd", "nice": 19}]}
    client = _run(frame)
    assert client.last("openrivian/health/sched_demoted") is True
    assert client.last("openrivian/health/sched_nice_max") == 19


def test_comm_issue_flag_from_onroad_events():
    frame = next(harness.synthetic_frames(n=1))
    frame["onroadEvents"] = []
    client = _run(frame)
    assert client.last("openrivian/health/comm_issue") is False

    frame["onroadEvents"] = [{"name": "commIssue"}]
    client = _run(frame)
    assert client.last("openrivian/health/comm_issue") is True


def test_lead_absent_publishes_sentinel():
    frame = next(harness.synthetic_frames(n=1))
    frame["radarState"] = {"leadOne": {"status": False, "dRel": 0.0, "vRel": 0.0}}
    client = _run(frame)
    assert client.last("openrivian/adas/radar/lead_one_d_rel") == -1


def test_camerad_running_from_manager_state():
    frame = next(harness.synthetic_frames(n=1))
    frame["managerState"] = {"processes": [{"name": "camerad", "running": True}]}
    client = _run(frame)
    assert client.last("openrivian/device/hardware/camerad_running") is True


def test_only_updated_services_publish():
    # A snapshot containing only carState must not emit device/location topics.
    frame = {"carState": next(harness.synthetic_frames(n=1))["carState"]}
    client = _run(frame)
    topics = set(client.topics())
    assert "openrivian/vehicle/powertrain/speed_ms" in topics
    assert not any(t.startswith("openrivian/device/") for t in topics)
    assert not any(t.startswith("openrivian/vehicle/location/") for t in topics)


def test_replay_is_deterministic():
    a = harness.replay(harness.synthetic_frames(n=10)).published
    b = harness.replay(harness.synthetic_frames(n=10)).published
    assert a == b
