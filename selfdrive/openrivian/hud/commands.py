"""
WebSocket command handler shared by webuid.py and replay.py.

Handles touch-control messages from the browser:
  {"type": "getParams"}                         -> {"type":"params","items":[...]}
  {"type": "setParam", "key": K, "value": V}    -> broadcast {"type":"param",...}
"""
from __future__ import annotations

import json


def make_command_handler(params_bridge, builder):
    async def handler(cmd: dict, server, ws):
        ctype = cmd.get("type")

        if ctype == "getParams":
            await ws.send_str(json.dumps({"type": "params", "items": params_bridge.curated()}))

        elif ctype == "setParam":
            key = cmd.get("key")
            value = cmd.get("value")
            ok = params_bridge.set(key, value)
            # keep the live HUD unit in sync when the user flips metric/imperial
            if ok and key == "IsMetric" and isinstance(value, bool) and builder is not None:
                builder.is_metric = value
            await server.broadcast({"type": "param", "key": key, "value": params_bridge.get(key), "ok": ok})

    return handler
