#!/usr/bin/env python3
import time
import json
import logging
import paho.mqtt.client as mqtt

# Add openpilot root to python path so we can import cereal
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import cereal.messaging as messaging

# MQTT Configuration
MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883
PUBLISH_FREQ_HZ = 2.0  # Decimate high-freq CAN to 2 Hz for MQTT to avoid flooding
SLEEP_DUR = 1.0 / PUBLISH_FREQ_HZ

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("[+] Connected to local MQTT broker!")
    else:
        logging.error(f"[-] Failed to connect to MQTT broker, return code {rc}")

def publish_safely(client, topic, payload):
    try:
        # Convert objects to standard JSON serializable format if needed
        val = payload
        if isinstance(val, float):
            val = round(val, 4)
        client.publish(topic, json.dumps({"value": val}), retain=False)
    except Exception as e:
        logging.debug(f"Failed to publish {topic}: {e}")

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("[*] Starting Cereal to MQTT Bridge...")

    client = mqtt.Client()
    client.on_connect = on_connect
    
    # Attempt to connect to the local broker. We loop because mqttd might still be starting up.
    connected = False
    while not connected:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            connected = True
        except ConnectionRefusedError:
            logging.info("[!] MQTT broker not ready. Retrying in 2 seconds...")
            time.sleep(2)

    client.loop_start()

    # Set up SubMaster
    # Subscribing to high-value sockets
    sm = messaging.SubMaster(['carState', 'deviceState', 'liveLocationKalman', 'pandaStates', 'controlsState', 'radarState', 'managerState'])

    logging.info("[*] Subscribed to Cereal sockets. Entering publish loop...")
    while True:
        sm.update(0)  # non-blocking update
        
        # --- CAR STATE ---
        if sm.updated['carState']:
            cs = sm['carState']
            # Powertrain & Driving Metrics
            publish_safely(client, "openrivian/vehicle/powertrain/speed_ms", cs.vEgo)
            publish_safely(client, "openrivian/vehicle/powertrain/speed_mph", cs.vEgo * 2.23694)
            publish_safely(client, "openrivian/vehicle/powertrain/standstill", cs.standstill)
            publish_safely(client, "openrivian/vehicle/controls/gas_pressed", cs.gasPressed)
            publish_safely(client, "openrivian/vehicle/controls/brake_pressed", cs.brakePressed)
            publish_safely(client, "openrivian/vehicle/controls/steering_angle_deg", cs.steeringAngleDeg)
            
            # Motor Torque / Steering Torque
            if hasattr(cs, 'steeringTorque'):
                publish_safely(client, "openrivian/vehicle/controls/steering_torque", cs.steeringTorque)
            if hasattr(cs, 'steeringTorqueEps'):
                publish_safely(client, "openrivian/vehicle/controls/steering_torque_eps", cs.steeringTorqueEps)
            if hasattr(cs, 'aEgo'):
                publish_safely(client, "openrivian/vehicle/powertrain/a_ego", cs.aEgo)
            if hasattr(cs, 'engineRpmDEPRECATED'):
                publish_safely(client, "openrivian/vehicle/powertrain/engine_rpm", cs.engineRpmDEPRECATED)

            # Wheel Speeds
            if hasattr(cs, 'wheelSpeeds'):
                ws = cs.wheelSpeeds
                if hasattr(ws, 'fl'): publish_safely(client, "openrivian/vehicle/powertrain/wheel_speed_fl", ws.fl)
                if hasattr(ws, 'fr'): publish_safely(client, "openrivian/vehicle/powertrain/wheel_speed_fr", ws.fr)
                if hasattr(ws, 'rl'): publish_safely(client, "openrivian/vehicle/powertrain/wheel_speed_rl", ws.rl)
                if hasattr(ws, 'rr'): publish_safely(client, "openrivian/vehicle/powertrain/wheel_speed_rr", ws.rr)

            # Gear
            gear_str = str(cs.gearShifter) if hasattr(cs, 'gearShifter') else "unknown"
            publish_safely(client, "openrivian/vehicle/powertrain/gear", gear_str)
            
            # Doors & Seatbelts
            publish_safely(client, "openrivian/vehicle/body/door_open", cs.doorOpen)
            publish_safely(client, "openrivian/vehicle/body/seatbelt_unlatched", cs.seatbeltUnlatched)
            
            # Turn Signals
            publish_safely(client, "openrivian/vehicle/controls/left_blinker", cs.leftBlinker)
            publish_safely(client, "openrivian/vehicle/controls/right_blinker", cs.rightBlinker)

            # Battery / Fuel (If available on CAN)
            if hasattr(cs, 'fuelGauge') and cs.fuelGauge > 0:
                publish_safely(client, "openrivian/vehicle/powertrain/soc", cs.fuelGauge * 100.0)

        # --- CONTROLS STATE (ADAS) ---
        if sm.updated['controlsState']:
            ctrl = sm['controlsState']
            if hasattr(ctrl, 'enabled'):
                publish_safely(client, "openrivian/adas/enabled", ctrl.enabled)
            if hasattr(ctrl, 'activeDEPRECATED'):
                publish_safely(client, "openrivian/adas/active", ctrl.activeDEPRECATED)
            
        # --- RADAR STATE ---
        if sm.updated['radarState']:
            rs = sm['radarState']
            if hasattr(rs, 'leadOne') and hasattr(rs.leadOne, 'status') and rs.leadOne.status:
                publish_safely(client, "openrivian/adas/radar/lead_one_d_rel", rs.leadOne.dRel)
                publish_safely(client, "openrivian/adas/radar/lead_one_v_rel", rs.leadOne.vRel)
            else:
                publish_safely(client, "openrivian/adas/radar/lead_one_d_rel", -1)

        # --- MANAGER STATE (Camera Health) ---
        if sm.updated['managerState']:
            ms = sm['managerState']
            if hasattr(ms, 'processes'):
                for p in ms.processes:
                    if p.name == "camerad":
                        publish_safely(client, "openrivian/device/hardware/camerad_running", p.running)
                        break

        # --- DEVICE STATE (Comma hardware) ---
        if sm.updated['deviceState']:
            ds = sm['deviceState']
            if len(ds.cpuTempC) > 0:
                publish_safely(client, "openrivian/device/hardware/cpu_temp_c", ds.cpuTempC[0])
            publish_safely(client, "openrivian/device/hardware/memory_usage_percent", ds.memoryUsagePercent)
            publish_safely(client, "openrivian/device/hardware/free_space_percent", ds.freeSpacePercent)
            
            # Power Metrics
            publish_safely(client, "openrivian/device/power/draw_w", ds.powerDrawW)

        # --- PANDA STATE ---
        if sm.updated['pandaStates'] and len(sm['pandaStates']) > 0:
            ps = sm['pandaStates'][0]
            # Handle both ignitionLine and ignitionCan depending on openpilot version
            ignition = False
            if hasattr(ps, 'ignitionLine'): ignition = ignition or ps.ignitionLine
            if hasattr(ps, 'ignitionCan'): ignition = ignition or ps.ignitionCan
            publish_safely(client, "openrivian/vehicle/powertrain/ignition", ignition)
            publish_safely(client, "openrivian/device/hardware/voltage", ps.voltage / 1000.0)

        # --- LOCATION ---
        if sm.updated['liveLocationKalman']:
            llk = sm['liveLocationKalman']
            if hasattr(llk, 'positionGeodetic') and llk.positionGeodetic.valid:
                # latitude, longitude, altitude
                publish_safely(client, "openrivian/vehicle/location/latitude", llk.positionGeodetic.value[0])
                publish_safely(client, "openrivian/vehicle/location/longitude", llk.positionGeodetic.value[1])
                publish_safely(client, "openrivian/vehicle/location/altitude", llk.positionGeodetic.value[2])
            
            if hasattr(llk, 'calibratedOrientationNED') and llk.calibratedOrientationNED.valid:
                # Heading/Bearing
                publish_safely(client, "openrivian/vehicle/location/bearing", llk.calibratedOrientationNED.value[0])

        time.sleep(SLEEP_DUR)

if __name__ == '__main__':
    main()
