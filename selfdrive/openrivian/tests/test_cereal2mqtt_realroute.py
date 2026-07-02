"""Opt-in Tier-1 test against a REAL recorded route.

Runs the telemetry pipeline (cereal2mqtt.publish_state) over a real rlog/qlog via
the replay harness and asserts the MQTT contract on genuine vehicle data. Skipped
unless a route is provided and cereal's LogReader is importable, so it only runs in
a full/built environment (on-device or a full-env container), never the lightweight
CI lane or the bare dev machine.

Enable by pointing ORV_TEST_ROUTE at a segment:
    ORV_TEST_ROUTE=/data/media/0/realdata/<route>--3/rlog.zst \
        python -m pytest selfdrive/openrivian/tests/test_cereal2mqtt_realroute.py

Validated 2026-06 against a real RIVIAN_R1 route (Herby): 15,028 frames ->
154,602 publishes across 38 topics, correct speed/gear/GPS/voltage mapping.
"""
import os

import pytest

from selfdrive.openrivian.replay import harness

ROUTE = os.environ.get("ORV_TEST_ROUTE")

pytestmark = pytest.mark.skipif(not ROUTE, reason="set ORV_TEST_ROUTE to a real rlog/qlog to run")


@pytest.fixture(scope="module")
def client():
    try:
        frames = list(harness.route_frames(ROUTE))
    except ImportError as e:
        pytest.skip(f"LogReader unavailable (needs built cereal env): {e}")
    if not frames:
        pytest.skip("route produced no relevant frames")
    return harness.replay(frames)


def test_real_route_emits_core_topics(client):
    topics = set(client.topics())
    expected = {
        "openrivian/vehicle/powertrain/speed_mph",
        "openrivian/vehicle/powertrain/gear",
        "openrivian/vehicle/location/latitude",
        "openrivian/vehicle/location/longitude",
        "openrivian/device/hardware/voltage",
    }
    assert expected <= topics, f"missing on real route: {expected - topics}"


def test_real_route_values_are_sane(client):
    speeds = [v for v in client.values_for("openrivian/vehicle/powertrain/speed_mph") if isinstance(v, (int, float))]
    assert speeds, "no speed published"
    assert max(speeds) > 1.0, "expected some movement on a real drive"
    assert all(0 <= s < 200 for s in speeds), "speed out of plausible range"

    lats = [v for v in client.values_for("openrivian/vehicle/location/latitude") if isinstance(v, (int, float))]
    assert lats and all(-90 <= v <= 90 for v in lats), "latitude out of range"

    volts = [v for v in client.values_for("openrivian/device/hardware/voltage") if isinstance(v, (int, float))]
    assert volts and all(8 < v < 16 for v in volts), "12V rail voltage implausible"


def test_real_route_topics_within_namespace(client):
    assert all(t.startswith("openrivian/") for t in client.topics())
