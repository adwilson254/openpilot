"""Behavioral tests for the MQTT bridge daemons (cereal2mqtt, mqtt2params, mqttd)."""
import json
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
    cereal2mqtt.publish_safely(fake_mqtt_client, "t/x", 1.23456789)
    topic, payload, retain = fake_mqtt_client.published[0]
    assert topic == "t/x"
    assert payload == {"value": round(1.23456789, 4)}
    assert retain is False


def test_publish_safely_swallows_client_errors():
    class Boom:
        def publish(self, *_a, **_k):
            raise RuntimeError("broker down")
    # Must not raise — telemetry failures should never crash the daemon.
    cereal2mqtt.publish_safely(Boom(), "t/x", 1)


class _FakeSubMaster:
    def __init__(self, updated, getter):
        self.updated = updated
        self._getter = getter

    def __getitem__(self, key):
        return self._getter(key)


def _carstate_only_submaster(cs):
    keys = ['carState', 'controlsState', 'radarState', 'managerState',
            'deviceState', 'pandaStates', 'liveLocationKalman']
    updated = {k: (k == 'carState') for k in keys}
    return _FakeSubMaster(updated, lambda _key: cs)


def test_publish_state_maps_carstate(fake_mqtt_client):
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
# mqtt2params: whitelist enforcement (security-relevant) + typed writes + dedupe
# --------------------------------------------------------------------------- #
def _msg(topic, value):
    return types.SimpleNamespace(topic=topic, payload=json.dumps({"value": value}).encode())


def test_on_message_rejects_non_whitelisted_param(monkeypatch, fake_params, fake_mqtt_client):
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    monkeypatch.setattr(mqtt2params, "PARAMS_WHITELIST", ["AllowedToggle"])
    mqtt2params.on_message(fake_mqtt_client, None, _msg("openrivian/settings/set/DangerousKey", True))
    # Nothing written, nothing echoed back.
    assert fake_params.store == {}
    assert fake_mqtt_client.published == []


def test_on_message_writes_whitelisted_types(monkeypatch, fake_params, fake_mqtt_client):
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    monkeypatch.setattr(mqtt2params, "PARAMS_WHITELIST", ["BoolKey", "NumKey", "StrKey"])

    mqtt2params.on_message(fake_mqtt_client, None, _msg("openrivian/settings/set/BoolKey", True))
    mqtt2params.on_message(fake_mqtt_client, None, _msg("openrivian/settings/set/NumKey", 42))
    mqtt2params.on_message(fake_mqtt_client, None, _msg("openrivian/settings/set/StrKey", "hello"))

    assert fake_params.get_bool("BoolKey") is True
    assert fake_params.get("NumKey") == b"42"
    assert fake_params.get("StrKey") == b"hello"
    # Each accepted write is echoed to a status topic for the UI.
    assert "openrivian/settings/status/BoolKey" in fake_mqtt_client.topics()


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
