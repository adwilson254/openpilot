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


def test_location_published_only_when_valid():
    frame = next(harness.synthetic_frames(n=1))
    frame["liveLocationKalman"]["positionGeodetic"] = {"valid": False, "value": [1.0, 2.0, 3.0]}
    client = _run(frame)
    assert client.last("openrivian/vehicle/location/latitude") is None
    assert client.last("openrivian/vehicle/location/longitude") is None


def test_location_values_pass_through_when_valid():
    frame = next(harness.synthetic_frames(n=1))
    frame["liveLocationKalman"]["positionGeodetic"] = {"valid": True, "value": [37.5, -122.5, 50.0]}
    client = _run(frame)
    assert client.last("openrivian/vehicle/location/latitude") == 37.5
    assert client.last("openrivian/vehicle/location/longitude") == -122.5


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
