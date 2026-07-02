"""Validate the mqtt2params write-protection against the REAL device param store.

Loads the actual /data/params/d values captured from the vehicle and confirms the
hardened whitelist behaves correctly on genuine state: dangerous params that exist on
the device (calibration blob, model cache, OBD, offroad flags) are never published or
writable, while normal user settings are.

Skipped unless ORV_PARAMS_DIR points at a real param dir (the parity container mounts
it; see run_parity.sh). Never required in the lightweight CI lane or on a bare machine.
"""
import os

import pytest

from selfdrive.openrivian import mqtt2params

PARAMS_DIR = os.environ.get("ORV_PARAMS_DIR")

pytestmark = pytest.mark.skipif(
    not PARAMS_DIR or not os.path.isdir(PARAMS_DIR),
    reason="set ORV_PARAMS_DIR to a real /data/params/d to run",
)

DANGEROUS = ["CalibrationParams", "ObdMultiplexingEnabled", "Offroad_Recalibration",
             "ModelManager_ModelsCache", "ModelRunnerTypeCache"]


def _load_real_params():
    out = {}
    for name in os.listdir(PARAMS_DIR):
        p = os.path.join(PARAMS_DIR, name)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                out[name] = f.read()
    return out


def test_device_actually_has_dangerous_state():
    real = _load_real_params()
    # Sanity: the real device carries calibration state (else the test proves nothing).
    assert "CalibrationParams" in real, "expected real device param store with CalibrationParams"


def test_dangerous_device_params_never_published(fake_params, fake_mqtt_client, monkeypatch):
    real = _load_real_params()
    fake_params.store = dict(real)
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    monkeypatch.setattr(mqtt2params, "last_published_values", {})

    mqtt2params.publish_all_params(fake_mqtt_client)
    published = {t.split("/")[-1] for t in fake_mqtt_client.topics()}

    leaked = [k for k in DANGEROUS if k in real and k in published]
    assert not leaked, f"dangerous real device params leaked to MQTT: {leaked}"
    assert published, "expected some safe params published from real device state"


def test_dangerous_device_params_not_writable(fake_params, fake_mqtt_client, monkeypatch):
    import json
    real = _load_real_params()
    fake_params.store = dict(real)
    monkeypatch.setattr(mqtt2params, "params", fake_params)
    before = dict(fake_params.store)

    for key in DANGEROUS:
        msg = type("M", (), {"topic": f"openrivian/settings/set/{key}",
                             "payload": json.dumps({"value": "x"}).encode()})()
        mqtt2params.on_message(fake_mqtt_client, None, msg)

    # No dangerous param value changed.
    for key in DANGEROUS:
        assert fake_params.store.get(key) == before.get(key), f"{key} was modified via MQTT"
