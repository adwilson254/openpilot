/*
 * Camera video plane (Phase 2b) -- decodes the device's HEVC road camera via
 * WebCodecs and draws it behind the model overlay, aligned using the same
 * projection transform (projection.js videoTransform).
 *
 * STATUS: scaffold, validated ON-DEVICE only. The local replay has no encoded
 * camera frames (rlog carries roadEncodeIdx metadata, not roadEncodeData bytes),
 * and there's no ffmpeg here to synthesize one, so the decode path could not be
 * exercised locally. It is intentionally INERT without a video stream: if
 * WebCodecs is unavailable or no frames arrive, the #road gradient shows and the
 * model overlay/HUD are unaffected.
 *
 * Wire format from server (see video.py), little-endian:
 *   byte 0     : frame kind (0 = codec config/header, 1 = key, 2 = delta)
 *   bytes 1..8 : timestamp (uint64, microseconds)
 *   bytes 9..  : payload (Annex-B NAL units; config carries VPS/SPS/PPS)
 */
window.HUDCamera = (function () {
  "use strict";

  const STAGE_W = 2160, STAGE_H = 1080, BORDER = 30;
  const X = BORDER, Y = BORDER, W = STAGE_W - 2 * BORDER, H = STAGE_H - 2 * BORDER;

  const supported = typeof window.VideoDecoder !== "undefined";
  let ctx = null;
  let model = null;
  let decoder = null;
  let configured = false;
  let header = null;
  let ws = null;
  let reconnectTimer = null;

  function init(canvas) {
    ctx = canvas.getContext("2d");
    if (!supported) {
      console.warn("[hud] WebCodecs VideoDecoder unavailable; camera disabled (model overlay + HUD still work)");
      return;
    }
    connect();
  }

  function onModel(m) { model = m; }

  function readU64LE(b, o) {
    let v = 0n;
    for (let i = 0; i < 8; i++) v |= BigInt(b[o + i]) << BigInt(8 * i);
    return v;
  }

  function connect() {
    try {
      ws = new WebSocket("ws://" + location.host + "/ws/video");
      ws.binaryType = "arraybuffer";
    } catch (e) { return; }
    ws.onmessage = onMessage;
    ws.onerror = function () { try { ws.close(); } catch (e) {} };
    ws.onclose = function () {
      if (!reconnectTimer) reconnectTimer = setTimeout(function () { reconnectTimer = null; connect(); }, 1500);
    };
  }

  function ensureDecoder() {
    if (decoder) return;
    decoder = new VideoDecoder({
      output: onFrame,
      error: function (e) { console.warn("[hud] video decoder error:", e && e.message); },
    });
  }

  function onMessage(ev) {
    const buf = new Uint8Array(ev.data);
    if (buf.length < 9) return;
    const kind = buf[0];
    const ts = Number(readU64LE(buf, 1));
    const payload = buf.subarray(9);

    if (kind === 0) { header = payload.slice(); return; } // codec config

    ensureDecoder();
    if (!configured) {
      try {
        // HEVC Main; codec/level may need tuning per device encoder.
        decoder.configure({ codec: "hev1.1.6.L153.B0", optimizeForLatency: true });
        configured = true;
      } catch (e) {
        console.warn("[hud] decoder.configure failed:", e && e.message);
        return;
      }
    }

    let data = payload;
    if (kind === 1 && header) {  // prepend VPS/SPS/PPS to keyframe (Annex-B)
      const merged = new Uint8Array(header.length + payload.length);
      merged.set(header, 0);
      merged.set(payload, header.length);
      data = merged;
    }
    try {
      decoder.decode(new EncodedVideoChunk({ type: kind === 1 ? "key" : "delta", timestamp: ts, data }));
    } catch (e) {
      /* drop until next keyframe */
    }
  }

  function onFrame(frame) {
    try {
      ctx.clearRect(0, 0, STAGE_W, STAGE_H);
      ctx.save();
      ctx.beginPath();
      ctx.rect(X, Y, W, H);
      ctx.clip();
      if (model && model.calibrated && window.Projection && Projection.videoTransform) {
        const v = Projection.videoTransform(model, W, H, X, Y);
        ctx.setTransform(v.zoom, 0, 0, v.zoom, v.tx, v.ty);
        ctx.drawImage(frame, 0, 0);
        ctx.setTransform(1, 0, 0, 1, 0, 0);
      } else {
        const s = Math.max(W / frame.displayWidth, H / frame.displayHeight);
        const dw = frame.displayWidth * s, dh = frame.displayHeight * s;
        ctx.drawImage(frame, X + (W - dw) / 2, Y + (H - dh) / 2, dw, dh);
      }
      ctx.restore();
    } finally {
      frame.close();
    }
  }

  return { init, onModel, supported };
})();
