/*
 * Projection math ported from the comma 3X UI:
 *   selfdrive/ui/onroad/augmented_road_view.py  (_calc_frame_matrix)
 *   selfdrive/ui/onroad/model_renderer.py        (_map_line_to_polygon, _map_to_screen)
 *   common/transformations/camera.py + orientation.py
 *
 * Projects 3D model points (car/calib frame) to 2D screen coordinates in the
 * content area, so the path/lanes overlay lines up with the road camera.
 */
window.Projection = (function () {
  "use strict";

  // view_frame_from_device_frame (camera.py): transpose of device_frame_from_view_frame
  const VIEW_FROM_DEVICE = [[0, 1, 0], [0, 0, 1], [1, 0, 0]];

  // DEVICE_CAMERAS intrinsics (focal length + principal point = width/2, height/2)
  const SENSORS = {
    os04c10: { fl: 1141.5, cx: 672, cy: 380, ecamFl: 425.25 },   // comma four (mici)
    ar0231:  { fl: 2648.0, cx: 964, cy: 604, ecamFl: 567.0 },    // comma 3/3X
    ox03c10: { fl: 2648.0, cx: 964, cy: 604, ecamFl: 567.0 },
  };
  const DEFAULT_SENSOR = "ar0231";

  function mul(A, B) {
    const C = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    for (let i = 0; i < 3; i++)
      for (let j = 0; j < 3; j++) {
        let s = 0;
        for (let k = 0; k < 3; k++) s += A[i][k] * B[k][j];
        C[i][j] = s;
      }
    return C;
  }

  function vec(A, v) {
    return [
      A[0][0] * v[0] + A[0][1] * v[1] + A[0][2] * v[2],
      A[1][0] * v[0] + A[1][1] * v[1] + A[1][2] * v[2],
      A[2][0] * v[0] + A[2][1] * v[1] + A[2][2] * v[2],
    ];
  }

  // euler2rot: Rz(yaw) * Ry(pitch) * Rx(roll)  (transformations.py euler2rot_single)
  function euler2rot(e) {
    const cx = Math.cos(e[0]), sx = Math.sin(e[0]);
    const cy = Math.cos(e[1]), sy = Math.sin(e[1]);
    const cz = Math.cos(e[2]), sz = Math.sin(e[2]);
    const Rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]];
    const Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]];
    const Rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]];
    return mul(mul(Rz, Ry), Rx);
  }

  // matches numpy np.clip semantics (min(max(v,lo),hi)); when lo>hi returns hi
  function clamp(v, lo, hi) { return Math.min(Math.max(v, lo), hi); }

  // Build the 3x3 that maps [x,y,z] (calib frame) -> homogeneous screen coords.
  // W,H = content-area size; X,Y = content-area top-left offset within the stage.
  function calcTransform(model, W, H, X, Y) {
    const s = SENSORS[model.sensor] || SENSORS[DEFAULT_SENSOR];
    const isWide = model.stream === "wide";
    const fl = isWide ? s.ecamFl : s.fl;
    const cx = s.cx, cy = s.cy;
    const intrinsic = [[fl, 0, cx], [0, fl, cy], [0, 0, 1]];

    const deviceFromCalib = euler2rot(model.rpy);
    let viewFromCalib;
    if (isWide) {
      const wideFromDevice = euler2rot(model.wideFromDeviceEuler || [0, 0, 0]);
      viewFromCalib = mul(mul(VIEW_FROM_DEVICE, wideFromDevice), deviceFromCalib);
    } else {
      viewFromCalib = mul(VIEW_FROM_DEVICE, deviceFromCalib);
    }
    // Derive zoom to COVER the content area. For the comma 3X AR camera this is
    // ~1.1 (matching the device's hardcoded road zoom); for the comma four os04c10
    // (smaller cx) it grows so the narrower camera still fills the 3X frame and the
    // vanishing point stays centered (device hardcodes 1.1/2.0 assuming AR sizing).
    const margin = 5;
    const coverZoom = Math.max((W / 2 + margin) / cx, (H / 2 + margin) / cy);
    const zoom = isWide ? Math.max(2.0, coverZoom) : coverZoom;
    const calibTransform = mul(intrinsic, viewFromCalib);

    const kep = vec(calibTransform, [1000.0, 0.0, 0.0]);
    const maxXOff = cx * zoom - W / 2 - margin;
    const maxYOff = cy * zoom - H / 2 - margin;
    let xOff = 0, yOff = 0;
    if (Math.abs(kep[2]) > 1e-6) {
      xOff = clamp((kep[0] / kep[2] - cx) * zoom, -maxXOff, maxXOff);
      yOff = clamp((kep[1] / kep[2] - cy) * zoom, -maxYOff, maxYOff);
    }
    const videoTransform = [
      [zoom, 0, (W / 2 + X - xOff) - cx * zoom],
      [0, zoom, (H / 2 + Y - yOff) - cy * zoom],
      [0, 0, 1],
    ];
    return mul(videoTransform, calibTransform);
  }

  function project(T, x, y, z) {
    const p = vec(T, [x, y, z]);
    if (Math.abs(p[2]) < 1e-6) return null;
    return [p[0] / p[2], p[1] / p[2]];
  }

  function pathLenIdx(xs, dist) {
    let idx = 0;
    for (let i = 0; i < xs.length; i++) {
      if (xs[i] <= dist) idx = i; else break;
    }
    return idx;
  }

  // Port of model_renderer._map_line_to_polygon: returns a closed polygon
  // (left edge forward + right edge back) in screen coords, or null.
  function mapLine(T, xs, ys, zs, yOff, zOff, maxIdx, maxDist) {
    const bx = [], by = [], bz = [];
    const N = Math.min(maxIdx + 1, xs.length);
    for (let i = 0; i < N; i++) { bx.push(xs[i]); by.push(ys[i]); bz.push(zs[i]); }
    if (maxIdx > 0 && maxIdx < xs.length - 1) {
      const x0 = xs[maxIdx], x1 = xs[maxIdx + 1];
      const t = (x1 - x0) !== 0 ? (maxDist - x0) / (x1 - x0) : 0;
      bx.push(maxDist);
      by.push(ys[maxIdx] + t * (ys[maxIdx + 1] - ys[maxIdx]));
      bz.push(zs[maxIdx] + t * (zs[maxIdx + 1] - zs[maxIdx]));
    }
    const left = [], right = [];
    for (let i = 0; i < bx.length; i++) {
      if (bx[i] < 0) continue;
      const lp = project(T, bx[i], by[i] - yOff, bz[i] + zOff);
      const rp = project(T, bx[i], by[i] + yOff, bz[i] + zOff);
      if (!lp || !rp) continue;
      left.push(lp);
      right.push(rp);
    }
    if (left.length < 2) return null;
    return left.concat(right.reverse());
  }

  // Camera-image display transform (camera pixels -> screen), matching the
  // model overlay so video and path align. Returns {zoom, tx, ty} for an affine
  // ctx.setTransform(zoom,0,0,zoom,tx,ty). Mirrors calcTransform's video_transform.
  function videoTransform(model, W, H, X, Y) {
    const s = SENSORS[model.sensor] || SENSORS[DEFAULT_SENSOR];
    const isWide = model.stream === "wide";
    const fl = isWide ? s.ecamFl : s.fl;
    const cx = s.cx, cy = s.cy;
    const deviceFromCalib = euler2rot(model.rpy);
    let viewFromCalib;
    if (isWide) {
      viewFromCalib = mul(mul(VIEW_FROM_DEVICE, euler2rot(model.wideFromDeviceEuler || [0, 0, 0])), deviceFromCalib);
    } else {
      viewFromCalib = mul(VIEW_FROM_DEVICE, deviceFromCalib);
    }
    const margin = 5;
    const coverZoom = Math.max((W / 2 + margin) / cx, (H / 2 + margin) / cy);
    const zoom = isWide ? Math.max(2.0, coverZoom) : coverZoom;
    const calibTransform = mul([[fl, 0, cx], [0, fl, cy], [0, 0, 1]], viewFromCalib);
    const kep = vec(calibTransform, [1000.0, 0.0, 0.0]);
    const maxXOff = cx * zoom - W / 2 - margin;
    const maxYOff = cy * zoom - H / 2 - margin;
    let xOff = 0, yOff = 0;
    if (Math.abs(kep[2]) > 1e-6) {
      xOff = clamp((kep[0] / kep[2] - cx) * zoom, -maxXOff, maxXOff);
      yOff = clamp((kep[1] / kep[2] - cy) * zoom, -maxYOff, maxYOff);
    }
    return { zoom: zoom, tx: (W / 2 + X - xOff) - cx * zoom, ty: (H / 2 + Y - yOff) - cy * zoom };
  }

  return { calcTransform, videoTransform, project, pathLenIdx, mapLine, euler2rot, mul, vec, SENSORS, VIEW_FROM_DEVICE };
})();
