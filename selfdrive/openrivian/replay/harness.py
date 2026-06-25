"""Process-replay harness for the OpenRivian telemetry bridge (Tier 1).

This drives ``cereal2mqtt.publish_state`` with a stream of message snapshots and
records every MQTT publish it produces. Two message sources are supported:

  * synthetic  -- deterministic generated frames (no vehicle, no build needed);
                  runs anywhere, including this Mac and CI.
  * route log  -- a real comma ``rlog``/``qlog`` via cereal's LogReader; used when
                  a recorded drive is available for the highest-fidelity check.

The same ``publish_state`` runs over both, so a synthetic-validated pipeline
behaves identically when you later drop in a real route.

CLI:
    python -m selfdrive.openrivian.replay.harness --synthetic --frames 20
    python -m selfdrive.openrivian.replay.harness --route /path/to/rlog.bz2
"""
from __future__ import annotations

import json
import math
import sys
import types
from collections import defaultdict


# ---------------------------------------------------------------------------
# Make cereal2mqtt importable without a built openpilot. publish_state itself
# never touches cereal.messaging (only main() does), so a stub import is enough.
# When run under pytest the conftest already installs richer mocks; this is the
# standalone path.
# ---------------------------------------------------------------------------
def _ensure_importable():
    try:
        import cereal.messaging  # noqa: F401
        return
    except Exception:
        pass
    cereal = sys.modules.setdefault("cereal", types.ModuleType("cereal"))
    messaging = types.ModuleType("cereal.messaging")
    messaging.SubMaster = object
    messaging.PubMaster = object
    sys.modules["cereal.messaging"] = messaging
    cereal.messaging = messaging


# ---------------------------------------------------------------------------
# Attribute-access view over plain dicts/lists so synthetic frames look like the
# capnp structs publish_state expects (supports hasattr / nested fields / lists).
# ---------------------------------------------------------------------------
def wrap(value):
    if isinstance(value, dict):
        return _Obj(value)
    if isinstance(value, (list, tuple)):
        return [wrap(v) for v in value]
    return value


class _Obj:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, wrap(v))


class FakeSubMaster:
    """Mimics the slice of SubMaster that publish_state uses."""

    def __init__(self, services):
        self._services = list(services)
        self._data = {}
        self.updated = defaultdict(bool)

    def set_frame(self, msgs: dict):
        # Only the services present in this snapshot are marked updated, exactly
        # like a real non-blocking SubMaster.update(0).
        self.updated = {s: (s in msgs) for s in self._services}
        for k, v in msgs.items():
            self._data[k] = wrap(v)

    def update(self, *_a, **_k):
        pass

    def __getitem__(self, key):
        return self._data.get(key)


class RecordingClient:
    """Stand-in MQTT client: records publishes and decodes the JSON envelope."""

    def __init__(self):
        self.published = []  # list[(topic, value)]

    def publish(self, topic, payload, retain=False):
        try:
            payload = json.loads(payload)
            value = payload.get("value") if isinstance(payload, dict) else payload
        except Exception:
            value = payload
        self.published.append((topic, value))

    # convenience views -----------------------------------------------------
    def topics(self):
        return [t for t, _ in self.published]

    def values_for(self, topic):
        return [v for t, v in self.published if t == topic]

    def last(self, topic):
        vals = self.values_for(topic)
        return vals[-1] if vals else None


# ---------------------------------------------------------------------------
# Synthetic source -- deterministic drive: accelerates, turns, loops near SF.
# ---------------------------------------------------------------------------
def synthetic_frames(n=20, hz=2.0):
    for i in range(n):
        t = i / hz
        v = max(0.0, 13.4 + 6.0 * math.sin(t / 5.0))  # m/s
        yield {
            "carState": {
                "vEgo": v,
                "aEgo": math.cos(t / 5.0),
                "standstill": v < 0.1,
                "gasPressed": v > 13.0,
                "brakePressed": v < 1.0,
                "steeringAngleDeg": 8.0 * math.sin(t / 7.0),
                "steeringTorque": 0.4 * math.sin(t / 7.0),
                "steeringTorqueEps": 0.5 * math.sin(t / 7.0),
                "wheelSpeeds": {"fl": v, "fr": v, "rl": v * 0.99, "rr": v * 0.99},
                "gearShifter": "drive",
                "doorOpen": False,
                "seatbeltUnlatched": False,
                "leftBlinker": (i % 8) == 0,
                "rightBlinker": False,
                "fuelGauge": 0.72,
            },
            "controlsState": {"enabled": True, "activeDEPRECATED": v > 5.0},
            "radarState": {"leadOne": {"status": v > 5.0, "dRel": 42.0 - v, "vRel": -1.5}},
            "managerState": {"processes": [{"name": "camerad", "running": True}]},
            "deviceState": {
                "cpuTempC": [55.0 + 3.0 * math.sin(t)],
                "memoryUsagePercent": 48,
                "freeSpacePercent": 61,
                "powerDrawW": 22.0 + 4.0 * math.sin(t / 3.0),
            },
            "pandaStates": [{"ignitionLine": True, "ignitionCan": False, "voltage": 12450}],
            "liveLocationKalman": {
                "positionGeodetic": {
                    "valid": True,
                    "value": [37.7749 + 0.002 * math.sin(t / 30), -122.4194 + 0.002 * math.cos(t / 30), 60.0],
                },
                "calibratedOrientationNED": {"valid": True, "value": [(t * 6) % 360, 0.0, 0.0]},
            },
        }


# ---------------------------------------------------------------------------
# Route-log source -- real recorded drive. Requires a built cereal/tools env.
# ---------------------------------------------------------------------------
def route_frames(path):
    """Yield one single-service snapshot per relevant message in a route log."""
    # Depending on how the env is rooted, LogReader is reachable as either
    # openpilot.tools.lib.logreader (upstream layout) or tools.lib.logreader
    # (this repo's flat layout). Try both.
    try:
        from openpilot.tools.lib.logreader import LogReader  # noqa: WPS433
    except ImportError:
        from tools.lib.logreader import LogReader  # noqa: WPS433

    import selfdrive.openrivian.cereal2mqtt as c2m
    wanted = set(c2m.SUBSCRIPTIONS)
    for msg in LogReader(path):
        which = msg.which()
        if which in wanted:
            yield {which: getattr(msg, which)}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def replay(frames, client=None):
    """Run publish_state over an iterable of snapshots; return the RecordingClient."""
    _ensure_importable()
    import selfdrive.openrivian.cereal2mqtt as c2m

    client = client or RecordingClient()
    sm = FakeSubMaster(c2m.SUBSCRIPTIONS)
    for frame in frames:
        # Real capnp structs already support attribute access; only dict frames
        # need wrapping, which FakeSubMaster.set_frame handles.
        sm.set_frame(frame)
        c2m.publish_state(client, sm)
    return client


def _main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="OpenRivian telemetry replay harness")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--synthetic", action="store_true", help="use generated frames (default)")
    src.add_argument("--route", help="path to a recorded rlog/qlog")
    ap.add_argument("--frames", type=int, default=20, help="synthetic frame count")
    args = ap.parse_args(argv)

    if args.route:
        client = replay(route_frames(args.route))
    else:
        client = replay(synthetic_frames(args.frames))

    topics = sorted(set(client.topics()))
    print(f"replayed -> {len(client.published)} publishes across {len(topics)} topics")
    for tpc in topics:
        print(f"  {tpc:55s} = {client.last(tpc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
