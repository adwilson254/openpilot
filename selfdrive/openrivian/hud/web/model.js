/*
 * Draws the driving-model overlay (path, lane lines, road edges, lead chevrons)
 * onto a canvas, projecting 3D model points with Projection (projection.js).
 * Mirrors selfdrive/ui/onroad/model_renderer.py.
 *
 * The canvas raster is the 2160x1080 comma design space; the model is drawn into
 * the content area (inside the 30px border), matching the on-device layout.
 */
window.HUDModel = (function () {
  "use strict";

  const STAGE_W = 2160, STAGE_H = 1080, BORDER = 30;
  const X = BORDER, Y = BORDER, W = STAGE_W - 2 * BORDER, H = STAGE_H - 2 * BORDER;

  let ctx = null;
  let latest = null;

  function init(canvas) {
    ctx = canvas.getContext("2d");
    requestAnimationFrame(draw);
  }

  function onModel(m) { latest = m; }

  function fillPoly(poly, style) {
    if (!poly || poly.length < 3) return;
    ctx.beginPath();
    ctx.moveTo(poly[0][0], poly[0][1]);
    for (let i = 1; i < poly.length; i++) ctx.lineTo(poly[i][0], poly[i][1]);
    ctx.closePath();
    ctx.fillStyle = style;
    ctx.fill();
  }

  function drawPath(poly, m) {
    if (!poly || poly.length < 3) return;
    let ymin = Infinity, ymax = -Infinity;
    for (const p of poly) { if (p[1] < ymin) ymin = p[1]; if (p[1] > ymax) ymax = p[1]; }
    const g = ctx.createLinearGradient(0, ymax, 0, ymin); // bottom -> top
    if (m.experimentalMode) {
      g.addColorStop(0.0, "rgba(255,255,255,0.35)");
      g.addColorStop(1.0, "rgba(255,255,255,0.05)");
    } else if (m.allowThrottle === false) {
      g.addColorStop(0.0, "rgba(242,242,242,0.40)");
      g.addColorStop(0.5, "rgba(242,242,242,0.35)");
      g.addColorStop(1.0, "rgba(242,242,242,0.00)");
    } else {
      g.addColorStop(0.0, "rgba(13,248,122,0.40)");
      g.addColorStop(0.5, "rgba(114,255,92,0.35)");
      g.addColorStop(1.0, "rgba(114,255,92,0.00)");
    }
    fillPoly(poly, g);
  }

  function drawLead(T, lead) {
    const pt = Projection.project(T, lead.dRel, -lead.yRel, 1.22);
    if (!pt) return;
    const sz = Math.min(Math.max((25 * 30) / (lead.dRel / 3 + 30), 15), 30) * 2.35;
    const x = Math.min(Math.max(pt[0], X), X + W);
    const y = Math.min(pt[1], Y + H);
    // glow
    ctx.beginPath();
    ctx.moveTo(x + sz * 1.35, y + sz);
    ctx.lineTo(x, y);
    ctx.lineTo(x - sz * 1.35, y + sz);
    ctx.closePath();
    ctx.fillStyle = "rgba(218,202,37,0.9)";
    ctx.fill();
    // chevron
    ctx.beginPath();
    ctx.moveTo(x + sz * 1.25, y + sz);
    ctx.lineTo(x, y);
    ctx.lineTo(x - sz * 1.25, y + sz);
    ctx.closePath();
    ctx.fillStyle = "rgba(201,34,49,0.95)";
    ctx.fill();
  }

  function draw() {
    requestAnimationFrame(draw);
    if (!ctx) return;
    ctx.clearRect(0, 0, STAGE_W, STAGE_H);
    const m = latest;
    if (!m || !m.calibrated || !m.position || !m.position.x.length) return;

    ctx.save();
    ctx.beginPath();
    ctx.rect(X, Y, W, H);
    ctx.clip();

    const T = Projection.calcTransform(m, W, H, X, Y);

    const px = m.position.x;
    const maxDist = Math.max(10, Math.min(100, px[px.length - 1] || 0));
    const laneMaxIdx = Projection.pathLenIdx(m.laneLines[0].x, maxDist);

    // lane lines (white, alpha ~ probability)
    for (let i = 0; i < m.laneLines.length; i++) {
      const ll = m.laneLines[i];
      const prob = m.laneLineProbs[i] || 0;
      const poly = Projection.mapLine(T, ll.x, ll.y, ll.z, 0.025 * prob, 0, laneMaxIdx, maxDist);
      fillPoly(poly, "rgba(255,255,255," + Math.min(prob, 0.7).toFixed(3) + ")");
    }

    // road edges (red, alpha ~ 1 - std)
    for (let i = 0; i < m.roadEdges.length; i++) {
      const re = m.roadEdges[i];
      const alpha = Math.max(0, Math.min(1, 1 - (m.roadEdgeStds[i] || 0)));
      const poly = Projection.mapLine(T, re.x, re.y, re.z, 0.025, 0, laneMaxIdx, maxDist);
      fillPoly(poly, "rgba(255,0,0," + alpha.toFixed(3) + ")");
    }

    // path (shorten toward a lead if present)
    let pathMaxDist = maxDist;
    if (m.leads && m.leads.length) {
      const ld = m.leads[0].dRel * 2.0;
      pathMaxDist = Math.max(0, Math.min(maxDist, ld - Math.min(ld * 0.35, 10)));
    }
    const pathMaxIdx = Projection.pathLenIdx(px, pathMaxDist);
    const off = m.cameraOffset || 0;
    const py = off ? m.position.y.map((v) => v + off) : m.position.y;
    const pathPoly = Projection.mapLine(T, m.position.x, py, m.position.z, 0.9, m.height || 1.22, pathMaxIdx, pathMaxDist);
    drawPath(pathPoly, m);

    // leads
    if (m.leads) for (const lead of m.leads) drawLead(T, lead);

    ctx.restore();
  }

  return { init, onModel };
})();
