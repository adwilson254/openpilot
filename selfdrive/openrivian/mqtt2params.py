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

# Hard safety denylist: params that must NEVER be writable over MQTT, regardless of
# what the UI schema or metadata contains. These are persistent state/blobs in
# /data/params that, if overwritten with the wrong value/type, corrupt calibration,
# the model, driver monitoring, or device identity -- and that corruption survives
# branch switches and reboots. (A too-broad whitelist here previously allowed e.g.
# CalibrationParams to be set, which can brick engagement with a "take over" alert.)
DENY_EXACT = {
    "CalibrationParams", "LiveCalibration", "LiveParameters", "LiveTorqueParameters",
    "LiveDelay", "ControlsReady", "FirmwareQueryDone", "CompletedTrainingVersion",
    "HasAcceptedTerms", "DongleId", "HardwareSerial", "IsOnroad", "IsOffroad",
    "ObdMultiplexingEnabled", "ObdMultiplexingChanged", "AlwaysOnDM",
}
DENY_PREFIX = ("Offroad_", "ModelManager_", "ModelRunnerType", "Live", "CarParams", "Calibration", "Camera")


def _is_safe_to_write(key):
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
    # Only allow params the dashboard UI actually offers; fall back to all known
    # params if the UI schema is unavailable. Either way, strip the safety denylist.
    try:
        allowed = _ui_exposed_keys(SETTINGS_UI_PATH) & known
    except Exception as e:
        logging.warning(f"settings_ui.json unavailable ({e}); restricting to denylist-filtered metadata")
        allowed = known
    return sorted(k for k in allowed if _is_safe_to_write(k))


PARAMS_WHITELIST = _build_whitelist()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("[+] Connected to MQTT broker for Settings Sync")
        client.subscribe("openrivian/settings/set/#")
        # Publish initial states
        publish_all_params(client)
    else:
        logging.error(f"[-] Failed to connect: {rc}")

def on_message(client, userdata, msg):
    try:
        param_name = msg.topic.split("/")[-1]
        
        # Only allow setting whitelisted params to prevent dangerous overwrites
        if param_name not in PARAMS_WHITELIST or not _is_safe_to_write(param_name):
            logging.warning(f"Attempted to set non-whitelisted/protected param: {param_name}")
            return
            
        payload = json.loads(msg.payload.decode())
        val = payload.get("value")
        
        # Writes Enabled
        logging.info(f"Writing Param '{param_name}' to {val}")
        if isinstance(val, bool):
            params.put_bool(param_name, val)
        elif isinstance(val, (int, float)):
            params.put(param_name, str(val).encode('utf-8'))
        elif isinstance(val, str):
            params.put(param_name, val.encode('utf-8'))
        
        # Echo the new status back to MQTT so UI updates
        client.publish(f"openrivian/settings/status/{param_name}", json.dumps({"value": val}), retain=True)
        
    except Exception as e:
        logging.error(f"Failed to set param {msg.topic}: {e}")

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
    logging.info("[*] Starting Settings Sync Bridge...")

    if mqtt is None:
        logging.error("Missing paho-mqtt. Gracefully exiting mqtt2params.")
        return

    client = build_client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    connected = False
    while not connected:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            connected = True
        except ConnectionRefusedError:
            time.sleep(2)

    # Loop forever, listening for sets and occasionally polling for changes
    client.loop_start()
    
    while True:
        publish_all_params(client)
        time.sleep(5)  # Poll params every 5 seconds to catch changes made from the UI in the car

if __name__ == '__main__':
    main()
