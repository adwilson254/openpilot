#!/usr/bin/env python3
# NOTE: os.nice(19) must only be called inside main(), never at module level.
# The process manager pre-imports every daemon module inside the manager process
# (manager_init -> prepare -> importlib.import_module) BEFORE forking children, so a
# module-level nice() permanently demotes manager and the ENTIRE openpilot stack
# (root cause of the 2026-07 "TAKE CONTROL IMMEDIATELY / Communication Issue" storms).
# Guarded by tests/test_no_module_level_nice.py.
import json
import time
import os

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params

# Local broker (mqttd). Publishes are retained so a late-connecting dashboard gets
# the last known energy state immediately; the data changes on minutes timescales.
MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

# Cloud polling cadence. The Rivian API is an unofficial mobile endpoint -- poll
# gently. One state query per minute is plenty for SoC/range.
ENERGY_FETCH_INTERVAL_S = 60.0
STEP_INTERVAL_S = 5.0

ENERGY_TOPICS = {
    "soc_percent": "openrivian/energy/soc_percent",
    "range_miles": "openrivian/energy/range_miles",
    "charger_state": "openrivian/energy/charger_state",
}


def step(params):
    # Legacy per-tick check kept for compatibility (and as the auth probe):
    # returns True when an account token is present.
    try:
        token_raw = params.get("RivianAccessToken")
        if token_raw:
            return True
        cloudlog.debug("OpenRivian API Daemon: RivianAccessToken not found in params.")
        return False
    except Exception as e:
        cloudlog.warning(f"OpenRivian API Daemon params.get error: {e}")
        return False


def fetch_energy(api, vehicle_id_cache):
    """Fetch SoC/range via the Rivian cloud API. Returns (energy_dict_or_None, vehicle_id).

    vehicle_id is resolved once and cached by the caller; any failure returns None
    for the energy dict and never raises (the daemon must idle gracefully offline).
    """
    try:
        if not api.is_authenticated():
            return None, vehicle_id_cache
        vid = vehicle_id_cache
        if not vid:
            vehicles = api.get_vehicles()
            vid = vehicles[0]["id"] if vehicles else None
            if vid:
                cloudlog.info(f"openriviand: using vehicle id {vid[:8]}…")
        if not vid:
            return None, None
        return api.get_vehicle_state(vid), vid
    except Exception as e:
        cloudlog.warning(f"openriviand: energy fetch failed: {e}")
        return None, vehicle_id_cache


def publish_energy(client, energy):
    """Publish the energy dict to MQTT (retained). Skips None values; never raises."""
    if client is None or not energy:
        return
    for key, topic in ENERGY_TOPICS.items():
        val = energy.get(key)
        if val is None:
            continue
        try:
            client.publish(topic, json.dumps({"value": val}), retain=True)
        except Exception as e:
            cloudlog.debug(f"openriviand: publish {topic} failed: {e}")


def _build_mqtt_client():
    """Best-effort local-broker client; returns None when paho is unavailable.
    connect_async + loop_start lets paho retry in the background, so mqttd being
    down (or toggled off) never blocks or crashes this daemon."""
    if mqtt is None:
        return None
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.connect_async(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        cloudlog.warning(f"openriviand: mqtt client unavailable: {e}")
        return None


def main():
    try:
        os.nice(19)
    except Exception as e:
        cloudlog.warning(f"Failed to set nice value: {e}")

    cloudlog.info("OpenRivian API Daemon started.")
    params = Params()
    client = _build_mqtt_client()

    # Import here (not module level) so the manager preimport stays lightweight and
    # a broken requests/urllib3 install can never take the whole manager down.
    from selfdrive.openrivian.api.rivian_api import RivianAPI

    api = None
    vehicle_id = None
    last_fetch = 0.0

    while True:
        authenticated = step(params)

        now = time.monotonic()
        if authenticated and (now - last_fetch) >= ENERGY_FETCH_INTERVAL_S:
            last_fetch = now
            try:
                if api is None:
                    api = RivianAPI()
                else:
                    # Tokens may have been (re)written by a fresh login on the mici panel.
                    api._load_tokens()
                energy, vehicle_id = fetch_energy(api, vehicle_id)
                publish_energy(client, energy)
            except Exception as e:
                cloudlog.warning(f"openriviand: energy loop error: {e}")

        time.sleep(STEP_INTERVAL_S)


if __name__ == "__main__":
    main()
