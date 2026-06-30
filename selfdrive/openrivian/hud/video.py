"""
On-device HEVC camera producer (Phase 2b).

Reads encoded road-camera frames (roadEncodeData / wideRoadEncodeData) from
cereal and streams them to /ws/video for the browser WebCodecs decoder
(web/camera.js).

DEVICE-ONLY and validated on-device: it imports cereal.messaging and needs the
on-device encoder. The local replay has no encoded frames, so this isn't run by
replay.py. See web/camera.js for the wire format.

Wire format (little-endian): [kind:u8][timestamp_us:u64][payload]
  kind 0 = codec config (VPS/SPS/PPS, Annex-B), 1 = key frame, 2 = delta frame
"""
from __future__ import annotations

import asyncio
import struct

ENCODE_SOCK = {"road": "roadEncodeData", "wide": "wideRoadEncodeData"}


def _pack(kind: int, ts_us: int, payload: bytes) -> bytes:
    return struct.pack("<BQ", kind, ts_us) + payload


def make_video_producer(cam: str = "road"):
    sock = ENCODE_SOCK.get(cam, "roadEncodeData")

    async def producer(server):
        import cereal.messaging as messaging
        sm = messaging.SubMaster([sock])
        header_sent = False
        while True:
            sm.update(0)
            if sm.updated[sock]:
                ed = sm[sock]
                idx = ed.idx
                ts_us = int(getattr(idx, "timestampEof", 0) // 1000)
                # EncodeData.header carries the codec config and accompanies keyframes.
                # (Heuristic: verify against idx.flags / NAL type on-device.)
                has_header = bool(ed.header) and len(ed.header) > 0
                if has_header and (not header_sent):
                    await server.broadcast_video(_pack(0, ts_us, bytes(ed.header)))
                    header_sent = True
                kind = 1 if has_header else 2
                if ed.data and len(ed.data) > 0:
                    await server.broadcast_video(_pack(kind, ts_us, bytes(ed.data)))
            await asyncio.sleep(0.003)

    return producer
