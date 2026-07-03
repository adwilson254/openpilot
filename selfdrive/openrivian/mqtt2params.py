#!/usr/bin/env python3
import os
try:
    os.nice(19)
except Exception:
    pass

import time
import json
import logging
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from openpilot.common.params import Params

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

params = Params()

_HERE = os.path.dirname(__file__)
PARAMS_META_PATH = os.path.abspath(os.path.join(_HERE, "../../sunnypilot/sunnylink/params_metadata.json"))
SETTINGS_UI_PATH = os.path.abspath(os.path.join(_HERE, "dashboard/src/assets/settings_ui.json"))

# This daemon is READ-ONLY: it publishes current param values to MQTT and never writes
# params back. This exposure denylist governs what must NEVER be published to the broker
# -- persistent state/blobs and device identity (calibration, model, driver monitoring,
# tokens, serials) that should not leave the device. (Historically this was a *write*
# denylist: a too-broad whitelist once let params like CalibrationParams be set over
# MQTT, which corrupts persistent state that survives reboots and can brick engagement
# with a "take over" alert. Removing the write path eliminates that risk at the source;
# the denylist stays as defense-in-depth against leaking sensitive params.)
DENY_EXACT = {
    "CalibrationParams", "LiveCalibration", "LiveParameters", "LiveTorqueParameters",
    "LiveDelay", "ControlsReady", "FirmwareQueryDone", "CompletedTrainingVersion",
    "HasAcceptedTerms", "DongleId", "HardwareSerial", "IsOnroad", "IsOffroad",
    "ObdMultiplexingEnabled", "ObdMultiplexingChanged", "AlwaysOnDM",
}
DENY_PREFIX = ("Offroad_", "ModelManager_", "ModelRunnerType", "Live", "CarParams", "Calibration", "Camera")


def _is_safe_to_publish(key):
    return key not in DENY_EXACT and not key.startswith(DENY_PREFIX)


def _ui_exposed_keys(path):
    """Keys the dashboard settings UI actually exposes (settings_ui.json)."""
    keys = set()

    def walk(o):
        if isinstance(o, dict):
            k = o.get("key")
            if isinstance(k, str):
                keys.add(k)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    with open(path, "r") as f:
        walk(json.load(f))
    return keys


def _build_whitelist():
    try:
        with open(PARAMS_META_PATH, "r") as f:
            known = set(json.load(f).keys())
    except Exception as e:
        logging.error(f"Failed to load params metadata: {e}")
        return []
    # Only publish params the dashboard UI actually offers; fall back to all known
    # params if the UI schema is unavailable. Either way, strip the exposure denylist.
    try:
        allowed = _ui_exposed_keys(SETTINGS_UI_PATH) & known
    except Exception as e:
        logging.warning(f"settings_ui.json unavailable ({e}); restricting to denylist-filtered metadata")
        allowed = known
    return sorted(k for k in allowed if _is_safe_to_publish(k))


PARAMS_WHITELIST = _build_whitelist()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("[+] Connected to MQTT broker for Settings Publish (read-only)")
        # Read-only: publish current states. We never subscribe to 'set' topics, so
        # nothing can write params back through this bridge.
        publish_all_params(client)
    else:
        logging.error(f"[-] Failed to connect: {rc}")

last_published_values = {}

def publish_all_params(client):
    for param in PARAMS_WHITELIST:
        # Get raw bytes safely
        try:
            val_bytes = params.get(param)
        except Exception as e:
            # params.get raises UnknownKeyName if the param is not defined in params_keys.h
            logging.debug(f"Skipping unknown param: {param}")
            continue
        val = None
        
        if val_bytes is not None:
            if isinstance(val_bytes, bytes):
                # Try to decode boolean/string
                val_str = val_bytes.decode('utf-8', errors='ignore')
                if val_str == "1":
                    val = True
                elif val_str == "0":
                    val = False
                else:
                    try:
                        val = float(val_str)
                    except ValueError:
                        val = val_str
            else:
                # Some Params wrappers may return parsed JSON or native types
                val = val_bytes
                    
        # Only publish if the value has changed since last time, to avoid spamming 1400 messages every 5 seconds
        if last_published_values.get(param) != val:
            client.publish(f"openrivian/settings/status/{param}", json.dumps({"value": val}, default=str), retain=True)
            last_published_values[param] = val

def build_client():
    # Be explicit about the callback API version. paho-mqtt 2.x still defaults to
    # VERSION1 but emits a DeprecationWarning on every start (noisy in device logs),
    # and a future paho 3.x may drop the implicit default entirely. Passing it
    # explicitly keeps our VERSION1-style callbacks valid and future-proof.
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

def main():

    logging.basicConfig(level=logging.INFO)
    logging.info("[*] Starting Settings Publish Bridge (read-only)...")

    if mqtt is None:
        logging.error("Missing paho-mqtt. Gracefully exiting mqtt2params.")
        return

    client = build_client()
    client.on_connect = on_connect
    # Read-only by design: no on_message handler is registered and we never subscribe
    # to 'set' topics, so this bridge cannot write params.

    connected = False
    while not connected:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            connected = True
        except ConnectionRefusedError:
            time.sleep(2)

    # Loop forever, periodically publishing current param values.
    client.loop_start()

    while True:
        publish_all_params(client)
        time.sleep(5)  # Poll params every 5 seconds to reflect changes made from the car UI

if __name__ == '__main__':
    main()
