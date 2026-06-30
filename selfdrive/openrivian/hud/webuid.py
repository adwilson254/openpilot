#!/usr/bin/env python3
"""
On-device HUD daemon: bridges live cereal -> WebSocket on :8200, and serves the
web HUD. Run on the comma device (e.g. via manager or manually). Connect from a
phone/laptop on the same network at http://<device-ip>:8200.

Local development uses replay.py instead (this module imports cereal.messaging,
which needs the on-device runtime).
"""
from __future__ import annotations

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _p in (_HERE, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hud_state import HudStateBuilder       # noqa: E402
from server import HudServer                # noqa: E402
from params_bridge import ParamsBridge      # noqa: E402
from commands import make_command_handler   # noqa: E402
from model_state import build_model_state    # noqa: E402
from video import make_video_producer        # noqa: E402

WEB_DIR = os.path.join(_HERE, "web")

# Services consumed by the HUD (chrome + model overlay).
SERVICES = ["carState", "selfdriveState", "controlsState", "deviceState",
            "carParams", "modelV2", "radarState", "liveCalibration",
            "roadCameraState", "longitudinalPlan"]


def _make_producer(builder: HudStateBuilder, rate_hz: float = 20.0):
    async def producer(server):
        import cereal.messaging as messaging
        sm = messaging.SubMaster(SERVICES)
        dt = 1.0 / rate_hz
        while True:
            sm.update(0)
            msgs = {s: sm[s] for s in SERVICES if sm.seen[s]}
            await server.broadcast(builder.build(msgs))
            model = build_model_state(msgs)
            if model is not None:
                await server.broadcast(model)
            await asyncio.sleep(dt)

    return producer


def main():
    try:
        os.nice(19)
    except Exception:
        pass

    is_metric = False
    try:
        from openpilot.common.params import Params
        is_metric = Params().get_bool("IsMetric")
    except Exception:
        pass

    builder = HudStateBuilder(is_metric=is_metric)
    params_bridge = ParamsBridge()
    server = HudServer(WEB_DIR, on_command=make_command_handler(params_bridge, builder))
    server.add_producer(_make_producer(builder))
    server.add_producer(make_video_producer(os.environ.get("HUD_CAM", "road")))

    port = int(os.environ.get("HUD_PORT", "8200"))
    print(f"[webuid] OpenRivian HUD serving on :{port}")
    server.run(port=port)


if __name__ == "__main__":
    main()
