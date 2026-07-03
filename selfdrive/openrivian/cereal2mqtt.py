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

# Add openpilot root to python path so we can import cereal
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import cereal.messaging as messaging

# MQTT Configuration
MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

# Publish-rate policy ---------------------------------------------------------
# The loop ticks at BASE_TICK_HZ; each topic self-gates via publish_safely():
#   - HIGH_RATE_HZ  : motion/dynamics (accel, speed, steering) -- stream fast.
#   - NORMAL_RATE_HZ: default for numeric telemetry.
#   - on-change     : states/flags -- publish only when the value changes (with a
#                     periodic heartbeat), and retain so late subscribers get current
#                     state immediately. Floats are compared after 4 dp rounding, which
#                     acts as a deadband so noise doesn't defeat change-detection.
BASE_TICK_HZ = 20.0
HIGH_RATE_HZ = 20.0
NORMAL_RATE_HZ = 2.0
HEARTBEAT_S = 30.0
SLEEP_DUR = 1.0 / BASE_TICK_HZ

# Topics that stream at HIGH_RATE_HZ (vehicle dynamics).
HIGH_RATE_TOPICS = {
    "openrivian/vehicle/dynamics/accel_x",
    "openrivian/vehicle/dynamics/accel_y",
    "openrivian/vehicle/dynamics/accel_z",
    "openrivian/vehicle/powertrain/a_ego",
    "openrivian/vehicle/powertrain/speed_ms",
    "openrivian/vehicle/powertrain/speed_mph",
    "openrivian/vehicle/controls/steering_angle_deg",
}

# Topics published only when their (rounded) value changes. Booleans, enums and other
# slow-changing states -- publishing these every tick is wasteful.
ON_CHANGE_TOPICS = {
    "openrivian/vehicle/powertrain/standstill",
    "openrivian/vehicle/powertrain/gear",
    "openrivian/vehicle/powertrain/charging",
    "openrivian/vehicle/powertrain/ignition",
    "openrivian/vehicle/controls/gas_pressed",
    "openrivian/vehicle/controls/brake_pressed",
    "openrivian/vehicle/controls/left_blinker",
    "openrivian/vehicle/controls/right_blinker",
    "openrivian/vehicle/body/door_open",
    "openrivian/vehicle/body/seatbelt_unlatched",
    "openrivian/vehicle/adas/left_blindspot",
    "openrivian/vehicle/adas/right_blindspot",
    "openrivian/vehicle/adas/cruise_enabled",
    "openrivian/vehicle/adas/cruise_available",
    "openrivian/adas/enabled",
    "openrivian/adas/active",
    "openrivian/device/hardware/camerad_running",
}

# Per-topic publish bookkeeping: topic -> (last_value, last_publish_monotonic).
_pub_state: dict = {}


def _should_publish(topic, val, now):
    last = _pub_state.get(topic)
    if topic in ON_CHANGE_TOPICS:
        if last is None:
            return True
        last_val, last_ts = last
        if val != last_val:
            return True
        return (now - last_ts) >= HEARTBEAT_S  # periodic heartbeat
    # rate-limited
    hz = HIGH_RATE_HZ if topic in HIGH_RATE_TOPICS else NORMAL_RATE_HZ
    if last is None:
        return True
    return (now - last[1]) >= (1.0 / hz)

# ----------------------------------------------------------------------------

# Cereal services this bridge subscribes to. Module-level so the replay harness
# can build a matching SubMaster without duplicating the list.
SUBSCRIPTIONS = ['carState', 'deviceState', 'liveLocationKalman', 'pandaStates',
                 'controlsState', 'radarState', 'managerState', 'accelerometer']

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
        now = time.monotonic()
        # Per-topic rate / on-change gating (see policy above).
        if not _should_publish(topic, val, now):
            return
        retain = topic in ON_CHANGE_TOPICS  # retain state topics so late subscribers see current value
        client.publish(topic, json.dumps({"value": val}), retain=retain)
        _pub_state[topic] = (val, now)
    except Exception as e:
        logging.debug(f"Failed to publish {topic}: {e}")

def build_client():
    # Be explicit about the callback API version. paho-mqtt 2.x still defaults to
    # VERSION1 but emits a DeprecationWarning on every start (noisy in device logs),
    # and a future paho 3.x may drop the implicit default entirely. Passing it
    # explicitly keeps our VERSION1-style callbacks valid and future-proof.
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

def publish_state(client, sm):
    # Translate one round of cereal messages into MQTT topics. Factored out of the
    # main loop so the carState->topic mapping is unit-testable without a broker.
    # Actual publish cadence per topic is governed by publish_safely() (rate/on-change).

    # --- ACCELEROMETER (raw IMU, high-rate) ---
    if sm.updated.get('accelerometer'):
        acc = sm['accelerometer']
        # openpilot sensor event: accelerometer.acceleration.v = [x, y, z] (m/s^2)
        try:
            v = acc.acceleration.v
            if len(v) >= 3:
                publish_safely(client, "openrivian/vehicle/dynamics/accel_x", float(v[0]))
                publish_safely(client, "openrivian/vehicle/dynamics/accel_y", float(v[1]))
                publish_safely(client, "openrivian/vehicle/dynamics/accel_z", float(v[2]))
        except Exception as e:
            logging.debug(f"accelerometer decode failed: {e}")

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
        # Longitudinal acceleration (derived) -- high-rate lane alongside raw IMU above.
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

        # EV Charging State
        if hasattr(cs, 'charging'):
            publish_safely(client, "openrivian/vehicle/powertrain/charging", cs.charging)

        # ADAS & Blindspot Data
        if hasattr(cs, 'leftBlindspot'):
            publish_safely(client, "openrivian/vehicle/adas/left_blindspot", cs.leftBlindspot)
        if hasattr(cs, 'rightBlindspot'):
            publish_safely(client, "openrivian/vehicle/adas/right_blindspot", cs.rightBlindspot)
        if hasattr(cs, 'cruiseState'):
            publish_safely(client, "openrivian/vehicle/adas/cruise_enabled", getattr(cs.cruiseState, 'enabled', False))
            publish_safely(client, "openrivian/vehicle/adas/cruise_speed_mph", getattr(cs.cruiseState, 'speed', 0.0) * 2.23694)
            publish_safely(client, "openrivian/vehicle/adas/cruise_available", getattr(cs.cruiseState, 'available', False))

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

def main():

    logging.basicConfig(level=logging.INFO)
    logging.info("[*] Starting Cereal to MQTT Bridge...")

    if mqtt is None:
        logging.error("Missing paho-mqtt. Gracefully exiting cereal2mqtt.")
        return

    client = build_client()
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
    sm = messaging.SubMaster(SUBSCRIPTIONS)

    logging.info("[*] Subscribed to Cereal sockets. Entering publish loop...")
    while True:
        sm.update(0)  # non-blocking update
        publish_state(client, sm)
        time.sleep(SLEEP_DUR)

if __name__ == '__main__':
    main()
