"""
aiohttp server for the OpenRivian web HUD.

Serves the static frontend (web/) and a /ws/state WebSocket that:
  - broadcasts HUD state dicts (type="state") at ~20 Hz, and
  - receives control commands (e.g. {"type":"setParam",...}).

Shared by webuid.py (device) and replay.py (local dev). A "producer"
coroutine pushes state via HudServer.broadcast().
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import os

from aiohttp import web, WSMsgType


class HudServer:
    def __init__(self, web_dir: str, on_command=None):
        self.web_dir = os.path.abspath(web_dir)
        self.on_command = on_command  # async fn(cmd: dict, server: HudServer, ws) -> None
        self.clients: set = set()
        self._latest: dict = {}  # message type -> last JSON string (so new clients sync immediately)
        self._producers: list = []
        self._tasks: list = []

        self.app = web.Application()
        self.app.router.add_get("/ws/state", self._ws_handler)
        self.app.router.add_get("/ws/video", self._ws_video_handler)
        self.app.router.add_get("/", self._index)
        self.app.router.add_get("/{path:.*}", self._static)
        self.app.on_startup.append(self._start_producers)
        self.app.on_cleanup.append(self._stop_producers)
        self.video_clients: set = set()

    # ---- producers (background state sources) ----
    def add_producer(self, coro_factory):
        """coro_factory: async fn(server) that loops and calls server.broadcast()."""
        self._producers.append(coro_factory)

    async def _start_producers(self, _app):
        for factory in self._producers:
            self._tasks.append(asyncio.create_task(factory(self)))

    async def _stop_producers(self, _app):
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass

    # ---- static file serving (no build step required) ----
    async def _index(self, _request):
        return self._serve_file("index.html")

    async def _static(self, request):
        return self._serve_file(request.match_info.get("path", "") or "index.html")

    def _serve_file(self, rel: str):
        full = os.path.abspath(os.path.join(self.web_dir, rel))
        # prevent path traversal; fall back to index.html (SPA-style)
        if not (full == self.web_dir or full.startswith(self.web_dir + os.sep)) or not os.path.isfile(full):
            full = os.path.join(self.web_dir, "index.html")
            if not os.path.isfile(full):
                return web.Response(status=404, text="not found")
        ctype, _ = mimetypes.guess_type(full)
        return web.FileResponse(full, headers={"Cache-Control": "no-store", "Content-Type": ctype or "application/octet-stream"})

    # ---- websocket ----
    async def _ws_handler(self, request):
        ws = web.WebSocketResponse(heartbeat=20.0)
        await ws.prepare(request)
        self.clients.add(ws)
        try:
            for data in self._latest.values():
                await ws.send_str(data)
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_command(msg.data, ws)
                elif msg.type == WSMsgType.ERROR:
                    break
        finally:
            self.clients.discard(ws)
        return ws

    async def _handle_command(self, data: str, ws):
        try:
            cmd = json.loads(data)
        except Exception:
            return
        if self.on_command is not None:
            await self.on_command(cmd, self, ws)

    # ---- video websocket (binary HEVC frames; fed only on-device) ----
    async def _ws_video_handler(self, request):
        ws = web.WebSocketResponse(heartbeat=20.0, max_msg_size=8 * 1024 * 1024)
        await ws.prepare(request)
        self.video_clients.add(ws)
        try:
            async for _msg in ws:  # client doesn't send; just keep the socket open
                pass
        finally:
            self.video_clients.discard(ws)
        return ws

    async def broadcast_video(self, payload: bytes):
        dead = []
        for ws in self.video_clients:
            try:
                await ws.send_bytes(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.video_clients.discard(ws)

    # ---- broadcast ----
    async def broadcast(self, message: dict):
        data = json.dumps(message)
        mtype = message.get("type")
        if mtype:
            self._latest[mtype] = data
        dead = []
        for ws in self.clients:
            try:
                await ws.send_str(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def run(self, host: str = "0.0.0.0", port: int = 8200):
        web.run_app(self.app, host=host, port=port)
