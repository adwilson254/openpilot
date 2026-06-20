#!/usr/bin/env python3
import os
try:
    os.nice(19)
except Exception:
    pass

import json
import logging
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None
import cereal.messaging as messaging

import os

def publish_safely(client, topic, value):
    payload = json.dumps({"value": value})
    try:
        client.publish(topic, payload)
    except Exception as e:
        logging.error(f"Failed to publish {topic}: {e}")

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("[*] Starting Dedicated OpenRivian Charging Sniffer...")

    if mqtt is None:
        logging.error("Missing paho-mqtt. Gracefully exiting chargingd.")
        return

    # Connect to local MQTT broker
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect("127.0.0.1", 1883, 60)
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return

    client.loop_start()

    # Subscribe strictly to the raw CAN socket
    sm = messaging.SubMaster(['can'])

    logging.info("[*] Subscribed to CAN socket. Entering sniff loop...")
    while True:
        sm.update()

        # The 'can' socket streams 24/7 as long as the Comma is on, bypassing ignition checks!
        if sm.updated['can']:
            for msg in sm['can']:
                # msg.address represents the CAN Message ID
                # msg.dat represents the raw bytes payload
                
                # --- CAN ID PLACEHOLDER ---
                # Example usage:
                # if msg.address == 0x3F2: 
                #     soc = parse_payload(msg.dat)
                #     publish_safely(client, "openrivian/vehicle/powertrain/soc", soc)
                pass

if __name__ == "__main__":
    main()
