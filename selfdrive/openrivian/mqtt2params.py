#!/usr/bin/env python3
import time
import json
import logging
import paho.mqtt.client as mqtt

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from openpilot.common.params import Params

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

params = Params()

PARAMS_META_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../sunnypilot/sunnylink/params_metadata.json"))
try:
    with open(PARAMS_META_PATH, "r") as f:
        metadata = json.load(f)
        PARAMS_WHITELIST = list(metadata.keys())
except Exception as e:
    logging.error(f"Failed to load params metadata: {e}")
    PARAMS_WHITELIST = []

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
        if param_name not in PARAMS_WHITELIST:
            logging.warning(f"Attempted to set non-whitelisted param: {param_name}")
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
        # Get raw bytes
        val_bytes = params.get(param)
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

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("[*] Starting Settings Sync Bridge...")

    client = mqtt.Client()
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
