"""Safety tests for mqtt2params write-protection.

A stray/retained MQTT 'settings/set/<param>' message must never be able to corrupt
persistent safety state (calibration, model, DM, offroad alert flags, identity) in
/data/params -- such corruption survives branch switches and reboots and can brick
engagement with a "take over immediately" alert.
"""
import types

import pytest

from selfdrive.openrivian import mqtt2params


# Params that, if writable over MQTT, could corrupt persistent safety/calibration state.
DANGEROUS = [
    "CalibrationParams", "LiveCalibration", "LiveParameters", "LiveTorqueParameters",
    "LiveDelay", "CompletedTrainingVersion", "DongleId", "HardwareSerial",
    "Offroad_Recalibration", "Offroad_DriverMonitoringUncertain",
    "ModelManager_ActiveBundle", "ModelManager_ClearCache", "ModelRunnerTypeCache",
    "ObdMultiplexingEnabled",
]


@pytest.mark.parametrize("key", DANGEROUS)
def test_dangerous_params_are_not_safe_to_write(key):
    assert mqtt2params._is_safe_to_write(key) is False


@pytest.mark.parametrize("key", DANGEROUS)
def test_dangerous_params_excluded_from_whitelist(key):
    assert key not in mqtt2params.PARAMS_WHITELIST


def test_legit_user_setting_is_writable():
    # A normal user preference toggle must remain settable.
    assert mqtt2params._is_safe_to_write("DisengageOnAccelerator") is True


def _msg(topic, value):
    import json
    return types.SimpleNamespace(topic=topic, payload=json.dumps({"value": value}).encode())


def test_on_message_refuses_calibration_write(monkeypatch, fake_params, fake_mqtt_client):
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    # Even if something put it on the whitelist, the denylist guard must block it.
    monkeypatch.setattr(mqtt2params, "PARAMS_WHITELIST", ["CalibrationParams"])
    mqtt2params.on_message(fake_mqtt_client, None, _msg("openrivian/settings/set/CalibrationParams", "garbage"))
    assert fake_params.store == {}
    assert fake_mqtt_client.published == []
