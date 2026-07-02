"""Topic contract for the telemetry bridge (daemon side).

cereal2mqtt publishes a fixed set of MQTT topic strings that the dashboard's
`lib/format.js` T-map consumes. The two live on different branches and can drift
silently -- a renamed/removed topic breaks the UI with nothing failing. This test
freezes the daemon's published topic set so any change is a conscious, reviewed
edit. The same list is mirrored on the dashboard side as `daemon_topics.json`.

When you intentionally add/rename a topic in cereal2mqtt.py, update EXPECTED_TOPICS
here AND selfdrive/openrivian/dashboard/src/__tests__/daemon_topics.json.
"""
import pathlib
import re

from selfdrive.openrivian.replay import harness

SOURCE = pathlib.Path("selfdrive/openrivian/cereal2mqtt.py")

# Frozen contract -- the complete set of topics cereal2mqtt may publish.
EXPECTED_TOPICS = {
    "openrivian/adas/active",
    "openrivian/adas/enabled",
    "openrivian/adas/radar/lead_one_d_rel",
    "openrivian/adas/radar/lead_one_v_rel",
    "openrivian/device/hardware/camerad_running",
    "openrivian/device/hardware/cpu_temp_c",
    "openrivian/device/hardware/free_space_percent",
    "openrivian/device/hardware/memory_usage_percent",
    "openrivian/device/hardware/voltage",
    "openrivian/device/power/draw_w",
    "openrivian/vehicle/adas/cruise_available",
    "openrivian/vehicle/adas/cruise_enabled",
    "openrivian/vehicle/adas/cruise_speed_mph",
    "openrivian/vehicle/adas/left_blindspot",
    "openrivian/vehicle/adas/right_blindspot",
    "openrivian/vehicle/body/door_open",
    "openrivian/vehicle/body/seatbelt_unlatched",
    "openrivian/vehicle/controls/brake_pressed",
    "openrivian/vehicle/controls/gas_pressed",
    "openrivian/vehicle/controls/left_blinker",
    "openrivian/vehicle/controls/right_blinker",
    "openrivian/vehicle/controls/steering_angle_deg",
    "openrivian/vehicle/controls/steering_torque",
    "openrivian/vehicle/controls/steering_torque_eps",
    "openrivian/vehicle/location/altitude",
    "openrivian/vehicle/location/bearing",
    "openrivian/vehicle/location/latitude",
    "openrivian/vehicle/location/longitude",
    "openrivian/vehicle/powertrain/a_ego",
    "openrivian/vehicle/powertrain/charging",
    "openrivian/vehicle/powertrain/engine_rpm",
    "openrivian/vehicle/powertrain/gear",
    "openrivian/vehicle/powertrain/ignition",
    "openrivian/vehicle/powertrain/soc",
    "openrivian/vehicle/powertrain/speed_mph",
    "openrivian/vehicle/powertrain/speed_ms",
    "openrivian/vehicle/powertrain/standstill",
    "openrivian/vehicle/powertrain/wheel_speed_fl",
    "openrivian/vehicle/powertrain/wheel_speed_fr",
    "openrivian/vehicle/powertrain/wheel_speed_rl",
    "openrivian/vehicle/powertrain/wheel_speed_rr",
}


def _topics_in_source():
    return set(re.findall(r'"(openrivian/[a-z0-9_/]+)"', SOURCE.read_text()))


def test_source_topics_match_contract():
    found = _topics_in_source()
    added = found - EXPECTED_TOPICS
    removed = EXPECTED_TOPICS - found
    assert not added, f"cereal2mqtt publishes new topics not in the contract: {sorted(added)}"
    assert not removed, f"contract topics no longer published by cereal2mqtt: {sorted(removed)}"


def test_replayed_topics_are_within_contract():
    # Every topic the harness actually emits must be part of the declared contract.
    client = harness.replay(harness.synthetic_frames(n=10))
    emitted = set(client.topics())
    assert emitted, "replay emitted no topics"
    assert emitted <= EXPECTED_TOPICS, f"emitted topics outside contract: {sorted(emitted - EXPECTED_TOPICS)}"
