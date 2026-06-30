#!/usr/bin/env python3
"""
Local replay HUD server (dev only) -- decode a recorded rlog.zst and serve the
exact same HUD WebSocket the device serves, so the browser HUD can be tested on
a laptop/phone before deploying to the vehicle.

Usage (from the OpenRivian repo root, using the project venv):
    python selfdrive/openrivian/hud/replay.py [RLOG_PATH] [--port 8200] [--metric] [--no-loop]

If RLOG_PATH is omitted it defaults to the bundled Kiro Artifacts replay
(route 0000000c--a4cff55fe7, segment 0). Open http://localhost:8200 in Safari/Chrome.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

# --- make sibling modules and `cereal` importable without packaging assumptions ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))            # OpenRivian
_WORKSPACE = os.path.abspath(os.path.join(_REPO_ROOT, ".."))                   # Dev/openrivian
for _p in (_HERE, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hud_state import HudStateBuilder       # noqa: E402
from server import HudServer                # noqa: E402
from params_bridge import ParamsBridge      # noqa: E402
from commands import make_command_handler   # noqa: E402

WEB_DIR = os.path.join(_HERE, "web")
DEFAULT_RLOG = os.path.join(_WORKSPACE, "Kiro Artifacts", "replay_data",
                            "0000000c--a4cff55fe7--0", "rlog.zst")

# services the HUD cares about (Phase 1 subset)
RELEVANT = {"carState", "selfdriveState", "controlsState", "deviceState",
            "carParams", "modelV2", "radarState", "liveCalibration"}


def _decompress(path: str) -> bytes:
    import zstandard
    with open(path, "rb") as fh:
        return zstandard.ZstdDecompressor().stream_reader(fh).read()


def _make_producer(data: bytes, builder: HudStateBuilder, loop_playback: bool, rate_hz: float):
    async def producer(server):
        from cereal import log as capnp_log
        emit_dt_ns = int(1e9 / rate_hz)
        while True:
            latest: dict = {}
            t0 = None
            wall0 = None
            last_emit_ns = None
            for evt in capnp_log.Event.read_multiple_bytes(data, traversal_limit_in_words=2 ** 63 - 1):
                which = evt.which()
                if which in RELEVANT:
                    latest[which] = getattr(evt, which)

                mono = evt.logMonoTime
                if t0 is None:
                    t0 = mono
                    wall0 = time.monotonic()
                    last_emit_ns = mono - emit_dt_ns

                # pace playback to wall-clock so the HUD moves at real speed
                delay = (wall0 + (mono - t0) / 1e9) - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(min(delay, 0.2))

                if mono - last_emit_ns >= emit_dt_ns:
                    state = builder.build(latest)
                    state["source"] = "replay"
                    await server.broadcast(state)
                    last_emit_ns = mono

            if not loop_playback:
                break
            await asyncio.sleep(0.5)  # brief pause, then loop the segment

    return producer


def main():
    ap = argparse.ArgumentParser(description="OpenRivian web HUD - local rlog replay")
    ap.add_argument("rlog", nargs="?", default=DEFAULT_RLOG, help="path to rlog.zst")
    ap.add_argument("--port", type=int, default=int(os.environ.get("HUD_PORT", "8200")))
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--metric", action="store_true", help="display km/h instead of mph")
    ap.add_argument("--rate", type=float, default=20.0, help="HUD update rate (Hz)")
    ap.add_argument("--no-loop", action="store_true", help="play once instead of looping")
    args = ap.parse_args()

    if not os.path.isfile(args.rlog):
        sys.exit(f"rlog not found: {args.rlog}")

    print(f"[hud-replay] decoding {args.rlog} ...")
    data = _decompress(args.rlog)
    print(f"[hud-replay] decompressed {len(data) / 1e6:.1f} MB")

    builder = HudStateBuilder(is_metric=args.metric)
    params_bridge = ParamsBridge()
    server = HudServer(WEB_DIR, on_command=make_command_handler(params_bridge, builder))
    server.add_producer(_make_producer(data, builder, not args.no_loop, args.rate))

    print(f"[hud-replay] serving HUD at http://localhost:{args.port}  (params: {'live' if params_bridge.live else 'in-memory'})")
    server.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
