#!/usr/bin/env python3
# NOTE: os.nice(19) must only be called inside main(), never at module level.
# The process manager pre-imports every daemon module inside the manager process
# (manager_init -> prepare -> importlib.import_module) BEFORE forking children, so a
# module-level nice() permanently demotes manager and the ENTIRE openpilot stack
# (root cause of the 2026-07 "TAKE CONTROL IMMEDIATELY / Communication Issue" storms).
# Guarded by tests/test_no_module_level_nice.py.
import os
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
MID_RATE_HZ = 10.0
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

# Topics that stream at MID_RATE_HZ. Location runs here (gpsLocationExternal
# arrives at 10 Hz): the infotainment map animates the vehicle marker between
# fixes, and 2 Hz makes it visibly step. ~+32 msg/s total on the local broker.
MID_RATE_TOPICS = {
    "openrivian/vehicle/location/latitude",
    "openrivian/vehicle/location/longitude",
    "openrivian/vehicle/location/altitude",
    "openrivian/vehicle/location/bearing",
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
    # openpilot alert mirroring: text/status change rarely, retain for late joiners.
    "openrivian/adas/alert_text1",
    "openrivian/adas/alert_text2",
    "openrivian/adas/alert_status",
    "openrivian/adas/personality",
    "openrivian/device/hardware/camerad_running",
    # Health canaries (see the HEALTH block in publish_state): slow-changing flags,
    # retained so a late-connecting dashboard sees current health immediately.
    "openrivian/health/sched_demoted",
    "openrivian/health/sched_nice_max",
    "openrivian/health/comm_issue",
}

# Scheduling-health watchlist: core openpilot processes that must run at nice 0.
# procLog reports the kernel comm name, truncated to 15 chars, so these are PREFIXES
# of the truncated names (e.g. selfdrived -> "selfdrive.selfd"). The OpenRivian
# daemons are deliberately excluded -- they run at nice 19 by design. Any watched
# process with nice > 0 means the stack got demoted again (the 2026-07 root cause:
# a module-level os.nice(19) inherited through the manager's daemon pre-import).
SCHED_WATCH_PREFIXES = (
    "camerad",
    "pandad",
    "loggerd",
    "selfdrive.selfd",   # selfdrived
    "selfdrive.contr",   # controlsd
    "selfdrive.model",   # modeld
    "selfdrive.locat",   # locationd
    "selfdrive.car.c",   # card
    "selfdrive.ui.ui",   # ui
)

# onroadEvents names that indicate the inter-process comm watchdog is tripping
# (the precursor of the "TAKE CONTROL IMMEDIATELY / Communication Issue" alert).
COMM_ISSUE_EVENTS = {"commIssue", "commIssueAvgFreq"}

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
    hz = HIGH_RATE_HZ if topic in HIGH_RATE_TOPICS else MID_RATE_HZ if topic in MID_RATE_TOPICS else NORMAL_RATE_HZ
    if last is None:
        return True
    return (now - last[1]) >= (1.0 / hz)

# ----------------------------------------------------------------------------

# Cereal services this bridge subscribes to. Module-level so the replay harness
# can build a matching SubMaster without duplicating the list.
# NOTE deliberate service choices (deprecated-field cleanup, 2026-07):
#   - gpsLocationExternal (not liveLocationKalman, which is deprecated upstream):
#     degrees-native lat/lon/alt + bearingDeg + hasFix.
#   - selfdriveState (not controlsState.activeDEPRECATED) for enabled/active.
#   - procLog (0.5 Hz) + onroadEvents (1 Hz) feed the health canaries.
SUBSCRIPTIONS = ['carState', 'deviceState', 'gpsLocationExternal', 'pandaStates',
                 'selfdriveState', 'radarState', 'managerState', 'accelerometer',
                 'procLog', 'onroadEvents']

# Liveness contract with the dashboard: a retained flag that the BROKER flips to
# False for us if this bridge dies (MQTT Last Will), and that we set back to True on
# every (re)connect. Retained state topics otherwise look "fresh" forever to a late
# subscriber, so without this the dashboard cannot tell a live feed from a dead one.
ALIVE_TOPIC = "openrivian/health/telemetry_alive"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("[+] Connected to local MQTT broker!")
        try:
            client.publish(ALIVE_TOPIC, json.dumps({"value": True}), retain=True)
        except Exception as e:
            logging.debug(f"alive publish failed: {e}")
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
        # engine_rpm was dropped: it read carState.engineRpmDEPRECATED, which is
        # meaningless on an EV and slated for removal upstream.

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

    # --- SELFDRIVE STATE (ADAS) ---
    # selfdriveState is the current home of enabled/active (controlsState.enabled /
    # activeDEPRECATED are legacy fields that upstream is removing).
    if sm.updated['selfdriveState']:
        ss = sm['selfdriveState']
        if hasattr(ss, 'enabled'):
            publish_safely(client, "openrivian/adas/enabled", ss.enabled)
        if hasattr(ss, 'active'):
            publish_safely(client, "openrivian/adas/active", ss.active)
        # Alert mirroring for the infotainment dashboard: the car screen's alert
        # text/status, on-change + retained. Empty text publishes too (clears the
        # banner on the dashboard side).
        if hasattr(ss, 'alertText1'):
            publish_safely(client, "openrivian/adas/alert_text1", str(ss.alertText1))
            publish_safely(client, "openrivian/adas/alert_text2", str(getattr(ss, 'alertText2', '')))
            publish_safely(client, "openrivian/adas/alert_status", str(getattr(ss, 'alertStatus', '')))
        if hasattr(ss, 'personality'):
            publish_safely(client, "openrivian/adas/personality", str(ss.personality))

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
    # gpsLocationExternal is degrees-native and carries a real heading (bearingDeg,
    # course over ground). This replaced liveLocationKalman, which (a) is deprecated
    # upstream and (b) we were misreading: calibratedOrientationNED.value[0] is ROLL
    # in radians, not heading -- the old "bearing" topic was publishing sensor noise.
    if sm.updated['gpsLocationExternal']:
        gps = sm['gpsLocationExternal']
        if getattr(gps, 'hasFix', False):
            publish_safely(client, "openrivian/vehicle/location/latitude", gps.latitude)
            publish_safely(client, "openrivian/vehicle/location/longitude", gps.longitude)
            publish_safely(client, "openrivian/vehicle/location/altitude", gps.altitude)
            # Normalize into [0, 360) defensively; receivers may report negative course.
            publish_safely(client, "openrivian/vehicle/location/bearing", float(gps.bearingDeg) % 360.0)

    # --- HEALTH: scheduling canary (procLog, 0.5 Hz) ---
    # Direct regression guard for the 2026-07 incident: if any core openpilot process
    # is running above nice 0, the stack has been demoted and comm/validity storms
    # ("TAKE CONTROL IMMEDIATELY / Communication Issue") will follow under load.
    if sm.updated['procLog']:
        try:
            watched_nices = [int(p.nice) for p in sm['procLog'].procs
                             if str(getattr(p, 'name', '')).startswith(SCHED_WATCH_PREFIXES)]
            if watched_nices:
                publish_safely(client, "openrivian/health/sched_nice_max", max(watched_nices))
                publish_safely(client, "openrivian/health/sched_demoted", max(watched_nices) > 0)
        except Exception as e:
            logging.debug(f"procLog decode failed: {e}")

    # --- HEALTH: inter-process comm watchdog (onroadEvents, 1 Hz) ---
    if sm.updated['onroadEvents']:
        try:
            names = {str(getattr(e, 'name', '')) for e in sm['onroadEvents']}
            publish_safely(client, "openrivian/health/comm_issue", bool(names & COMM_ISSUE_EVENTS))
        except Exception as e:
            logging.debug(f"onroadEvents decode failed: {e}")

def main():
    # Low priority for THIS daemon only (safe here: we are in the forked child).
    try:
        os.nice(19)
    except Exception:
        pass

    logging.basicConfig(level=logging.INFO)
    logging.info("[*] Starting Cereal to MQTT Bridge...")

    if mqtt is None:
        # Do NOT exit: an exit loop's running=False windows raise openpilot's
        # processNotRunning NoEntry and blocked engagement on-vehicle (2026-07-17).
        logging.error("Missing paho-mqtt -- idling (daemon stays up, does nothing).")
        while True:
            time.sleep(60)

    client = build_client()
    client.on_connect = on_connect
    # Last Will: if this process dies or drops off the broker, the broker publishes
    # retained alive=False on our behalf, flipping the dashboard's Live badge.
    client.will_set(ALIVE_TOPIC, json.dumps({"value": False}), retain=True)

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
