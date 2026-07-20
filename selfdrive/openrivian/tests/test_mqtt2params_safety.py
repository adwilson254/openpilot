"""Read-only safety tests for mqtt2params.

mqtt2params is a READ-ONLY publisher: it exposes current param values to MQTT and never
writes params back. These tests lock in that guarantee (no 'set' handler, no
subscription) and confirm sensitive persistent state (calibration, model, DM, identity)
is never exposed on the broker. Such params, if they could be written, corrupt state
that survives reboots and can brick engagement with a "take over immediately" alert --
dropping the write path removes that risk at the source.
"""
import pytest

from selfdrive.openrivian import mqtt2params


# Params that must never be exposed on MQTT (persistent safety/calibration/identity state).
DANGEROUS = [
    "CalibrationParams", "LiveCalibration", "LiveParameters", "LiveTorqueParameters",
    "LiveDelay", "CompletedTrainingVersion", "DongleId", "HardwareSerial",
    "Offroad_Recalibration", "Offroad_DriverMonitoringUncertain",
    "ModelManager_ActiveBundle", "ModelManager_ClearCache", "ModelRunnerTypeCache",
    "ObdMultiplexingEnabled",
]


@pytest.mark.parametrize("key", DANGEROUS)
def test_dangerous_params_are_not_safe_to_publish(key):
    assert mqtt2params._is_safe_to_publish(key) is False


@pytest.mark.parametrize("key", DANGEROUS)
def test_dangerous_params_excluded_from_whitelist(key):
    assert key not in mqtt2params.PARAMS_WHITELIST


def test_legit_user_setting_is_publishable():
    # A normal user preference toggle must still be exposed to the dashboard.
    assert mqtt2params._is_safe_to_publish("DisengageOnAccelerator") is True


def test_daemon_has_no_write_handler():
    # Read-only by design: with no on_message handler, there is no path that can write
    # params from an incoming MQTT message.
    assert not hasattr(mqtt2params, "on_message")


def test_on_connect_never_subscribes(fake_params, fake_mqtt_client, monkeypatch):
    # on_connect must publish current state but never subscribe to 'set' topics.
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    monkeypatch.setattr(mqtt2params, "last_published_values", {})
    mqtt2params.on_connect(fake_mqtt_client, None, None, 0)
    assert fake_mqtt_client.subscriptions == []
