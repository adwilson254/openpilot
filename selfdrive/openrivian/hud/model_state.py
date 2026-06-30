"""
Extract modelV2 + liveCalibration into a JSON-serializable dict for the browser
model overlay. The browser ports the comma 3X projection (web/projection.js +
web/model.js); here we just ship the raw 3D model, calibration, camera identity,
and lead info so projection is resolution-independent.

Mirrors the data consumed by selfdrive/ui/onroad/model_renderer.py and the
camera/calibration setup in augmented_road_view.py.
"""
from __future__ import annotations

CALIBRATED = "calibrated"


def _xyz(obj, nd: int = 3) -> dict:
    return {
        "x": [round(float(v), nd) for v in obj.x],
        "y": [round(float(v), nd) for v in obj.y],
        "z": [round(float(v), nd) for v in obj.z],
    }


def _flist(seq, nd: int = 4):
    return [round(float(v), nd) for v in (seq or [])]


def build_model_state(msgs: dict, camera_offset: float = 0.0):
    m = msgs.get("modelV2")
    lc = msgs.get("liveCalibration")
    if m is None or lc is None:
        return None

    cal_status = str(getattr(lc, "calStatus", "uncalibrated"))
    rpy = _flist(getattr(lc, "rpyCalib", []), 5)
    if len(rpy) != 3:
        return {"type": "model", "calibrated": False, "calStatus": cal_status}

    height = _flist(getattr(lc, "height", []), 4)
    wfd = _flist(getattr(lc, "wideFromDeviceEuler", []), 5)

    ds = msgs.get("deviceState")
    rcs = msgs.get("roadCameraState")
    cp = msgs.get("carParams")
    ss = msgs.get("selfdriveState")
    cs = msgs.get("carState")
    lp = msgs.get("longitudinalPlan")
    rs = msgs.get("radarState")

    long_control = bool(getattr(cp, "openpilotLongitudinalControl", False)) if cp is not None else False
    experimental = bool(getattr(ss, "experimentalMode", False)) if ss is not None else False
    v_ego = float(getattr(cs, "vEgo", 0.0)) if cs is not None else 0.0

    # active camera selection (mirror augmented_road_view._switch_stream_if_needed)
    stream = "road"
    if experimental and v_ego < 10.0:
        stream = "wide"
    elif v_ego > 15.0:
        stream = "road"

    leads = []
    if long_control and rs is not None:
        for ld in (rs.leadOne, rs.leadTwo):
            if getattr(ld, "status", False):
                leads.append({
                    "dRel": round(float(ld.dRel), 2),
                    "yRel": round(float(ld.yRel), 2),
                    "vRel": round(float(ld.vRel), 2),
                })

    return {
        "type": "model",
        "calibrated": cal_status == CALIBRATED,
        "calStatus": cal_status,
        "rpy": rpy,
        "height": height[0] if height else 1.22,
        "wideFromDeviceEuler": wfd if len(wfd) == 3 else [0.0, 0.0, 0.0],
        "deviceType": str(getattr(ds, "deviceType", "unknown")) if ds is not None else "unknown",
        "sensor": str(getattr(rcs, "sensor", "unknown")) if rcs is not None else "unknown",
        "stream": stream,
        "longControl": long_control,
        "experimentalMode": experimental,
        "allowThrottle": bool(getattr(lp, "allowThrottle", True)) if lp is not None else True,
        "cameraOffset": camera_offset,
        "position": _xyz(m.position),
        "laneLines": [_xyz(ll) for ll in m.laneLines],
        "laneLineProbs": [round(float(p), 3) for p in m.laneLineProbs],
        "roadEdges": [_xyz(re) for re in m.roadEdges],
        "roadEdgeStds": [round(float(s), 3) for s in m.roadEdgeStds],
        "accelerationX": [round(float(v), 3) for v in m.acceleration.x],
        "leads": leads,
    }
