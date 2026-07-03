"""Behavioral tests for the MQTT bridge daemons (cereal2mqtt, mqtt2params, mqttd)."""
import types

import pytest

from selfdrive.openrivian import cereal2mqtt, mqtt2params, mqttd


# --------------------------------------------------------------------------- #
# F1 guard: real paho client construction with the installed/pinned version.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("mod", [cereal2mqtt, mqtt2params])
def test_build_client_uses_supported_api(mod):
    assert mod.mqtt is not None, f"paho-mqtt not importable in {mod.__name__}"
    assert mod.build_client() is not None


# --------------------------------------------------------------------------- #
# cereal2mqtt.publish_safely + mapping
# --------------------------------------------------------------------------- #
def test_publish_safely_rounds_floats_and_wraps_value(fake_mqtt_client):
    cereal2mqtt._pub_state.clear()
    cereal2mqtt.publish_safely(fake_mqtt_client, "t/x", 1.23456789)
    topic, payload, retain = fake_mqtt_client.published[0]
    assert topic == "t/x"
    assert payload == {"value": round(1.23456789, 4)}
    assert retain is False


def test_publish_safely_swallows_client_errors():
    cereal2mqtt._pub_state.clear()
    class Boom:
        def publish(self, *_a, **_k):
            raise RuntimeError("broker down")
    # Must not raise — telemetry failures should never crash the daemon.
    cereal2mqtt.publish_safely(Boom(), "t/x", 1)


def test_on_change_topic_dedupes_then_publishes_on_change(fake_mqtt_client):
    # State topics publish once, skip while unchanged, then publish again on change.
    cereal2mqtt._pub_state.clear()
    t = "openrivian/vehicle/controls/brake_pressed"  # an ON_CHANGE topic
    cereal2mqtt.publish_safely(fake_mqtt_client, t, True)
    cereal2mqtt.publish_safely(fake_mqtt_client, t, True)   # unchanged -> no republish
    assert fake_mqtt_client.topics().count(t) == 1
    cereal2mqtt.publish_safely(fake_mqtt_client, t, False)  # changed -> publishes
    assert fake_mqtt_client.topics().count(t) == 2
    # ON_CHANGE topics are retained so late subscribers get current state.
    assert all(r is True for (tp, _p, r) in fake_mqtt_client.published if tp == t)


def test_high_rate_topic_gates_by_interval(fake_mqtt_client):
    # Rate-limited topics publish the first sample, then gate rapid repeats.
    cereal2mqtt._pub_state.clear()
    t = "openrivian/vehicle/dynamics/accel_x"  # HIGH_RATE topic
    cereal2mqtt.publish_safely(fake_mqtt_client, t, 1.0)
    cereal2mqtt.publish_safely(fake_mqtt_client, t, 2.0)  # immediate repeat -> gated
    assert fake_mqtt_client.topics().count(t) == 1


class _FakeSubMaster:
    def __init__(self, updated, getter):
        self.updated = updated
        self._getter = getter

    def __getitem__(self, key):
        return self._getter(key)


def _carstate_only_submaster(cs):
    keys = ['carState', 'controlsState', 'radarState', 'managerState',
            'deviceState', 'pandaStates', 'liveLocationKalman', 'accelerometer']
    updated = {k: (k == 'carState') for k in keys}
    return _FakeSubMaster(updated, lambda _key: cs)


def test_publish_state_maps_carstate(fake_mqtt_client):
    cereal2mqtt._pub_state.clear()
    cs = types.SimpleNamespace(
        vEgo=10.0, standstill=False, gasPressed=False, brakePressed=True,
        steeringAngleDeg=1.5, gearShifter="drive", doorOpen=False,
        seatbeltUnlatched=False, leftBlinker=False, rightBlinker=True,
    )
    sm = _carstate_only_submaster(cs)
    cereal2mqtt.publish_state(fake_mqtt_client, sm)

    assert fake_mqtt_client.value_for("openrivian/vehicle/powertrain/speed_ms") == 10.0
    # mph conversion applied and rounded to 4dp
    assert fake_mqtt_client.value_for("openrivian/vehicle/powertrain/speed_mph") == round(10.0 * 2.23694, 4)
    assert fake_mqtt_client.value_for("openrivian/vehicle/controls/brake_pressed") is True
    assert fake_mqtt_client.value_for("openrivian/vehicle/powertrain/gear") == "drive"


# --------------------------------------------------------------------------- #
# mqtt2params: read-only publishing (no write path) + dedupe
# --------------------------------------------------------------------------- #
def test_mqtt2params_is_read_only(monkeypatch, fake_params, fake_mqtt_client):
    # No 'set' handler exists, and connecting never subscribes to a 'set' topic, so a
    # stray/retained MQTT message can never write a param.
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    monkeypatch.setattr(mqtt2params, "PARAMS_WHITELIST", ["SomeToggle"])
    monkeypatch.setattr(mqtt2params, "last_published_values", {})

    assert not hasattr(mqtt2params, "on_message")
    mqtt2params.on_connect(fake_mqtt_client, None, None, 0)
    assert fake_mqtt_client.subscriptions == []
    # Publishing is read-only: it never mutates the param store.
    assert fake_params.store == {}


def test_publish_all_params_dedupes(monkeypatch, fake_params, fake_mqtt_client):
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    monkeypatch.setattr(mqtt2params, "PARAMS_WHITELIST", ["BoolKey"])
    monkeypatch.setattr(mqtt2params, "last_published_values", {})
    fake_params.put_bool("BoolKey", True)

    mqtt2params.publish_all_params(fake_mqtt_client)
    mqtt2params.publish_all_params(fake_mqtt_client)  # unchanged -> no second publish
    assert fake_mqtt_client.topics().count("openrivian/settings/status/BoolKey") == 1


# --------------------------------------------------------------------------- #
# mqttd: RAM-only/anonymous config invariants + graceful missing-dependency
# --------------------------------------------------------------------------- #
def test_mqttd_config_is_ram_only_and_anonymous():
    cfg = mqttd.config
    assert cfg["auth"]["allow-anonymous"] is True          # trusted local network, by design
    assert "1883" in cfg["listeners"]["default"]["bind"]
    # No on-disk persistence configured (protects eMMC).
    assert "persistence" not in cfg


def test_mqttd_exits_gracefully_without_broker(monkeypatch):
    monkeypatch.setattr(mqttd, "Broker", None)
    # Must return cleanly (logs and exits) rather than raising when amqtt is absent.
    mqttd.main()
