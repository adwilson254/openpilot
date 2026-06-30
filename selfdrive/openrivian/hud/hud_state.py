"""
Shared HUD state mapping for the OpenRivian web HUD.

This is the single source of truth that converts cereal messages into a
JSON-serializable dict consumed by the browser. It is used by both:
  - webuid.py  (on-device, live cereal SubMaster)
  - replay.py  (local dev, decoded rlog.zst)

Logic is ported from the on-device comma 3X UI:
  - selfdrive/ui/onroad/hud_renderer.py  (speeds, set-speed box)
  - selfdrive/ui/ui_state.py             (engagement status)
  - selfdrive/ui/onroad/augmented_road_view.py (border colors)

Phase 1 covers the HUD "chrome": current speed, set/MAX speed, engagement
state + border color, alerts, blinkers. Model/camera overlay is Phase 2.
"""
from __future__ import annotations

# --- constants mirrored from hud_renderer.py / common/constants.py ---
SET_SPEED_NA = 255
KM_TO_MILE = 0.621371
MS_TO_MPH = 2.23694
MS_TO_KPH = 3.6

# UIStatus values (mirror selfdrive/ui/ui_state.py UIStatus)
STATUS_DISENGAGED = "disengaged"
STATUS_ENGAGED = "engaged"
STATUS_OVERRIDE = "override"

# Border colors (mirror augmented_road_view.BORDER_COLORS)
BORDER_COLORS = {
    STATUS_DISENGAGED: "#122839",  # blue
    STATUS_OVERRIDE: "#89928D",    # gray
    STATUS_ENGAGED: "#167F40",     # green
}

# states that map to the OVERRIDE status
OVERRIDE_STATES = ("preEnabled", "overriding")


def _get(msg, attr, default=None):
    """Safe attribute access that works on capnp readers and plain objects."""
    if msg is None:
        return default
    try:
        val = getattr(msg, attr)
    except Exception:
        return default
    return default if val is None else val


class HudStateBuilder:
    """Builds the HUD state dict from {service_name: message_reader}.

    Holds the small amount of latched UI state the on-device HUD keeps
    (the vEgoCluster "seen" latch), so output matches the device.
    """

    def __init__(self, is_metric: bool = False):
        self.is_metric = is_metric
        self._v_ego_cluster_seen = False

    def status(self, ss) -> str:
        if ss is None:
            return STATUS_DISENGAGED
        state = str(_get(ss, "state", "disabled"))
        if state in OVERRIDE_STATES:
            return STATUS_OVERRIDE
        return STATUS_ENGAGED if _get(ss, "enabled", False) else STATUS_DISENGAGED

    def _set_speed(self, cs, ctrl):
        """Returns (display_set_speed|None, cruise_set, cruise_available)."""
        if cs is None:
            return None, False, True
        v_cruise_cluster = float(_get(cs, "vCruiseCluster", 0.0) or 0.0)
        if v_cruise_cluster == 0.0 and ctrl is not None:
            dep = _get(ctrl, "deprecated", None)
            raw = float(_get(dep, "vCruise", 0.0) or 0.0)
        else:
            raw = v_cruise_cluster
        cruise_set = 0 < raw < SET_SPEED_NA
        cruise_available = raw != -1
        set_speed = None
        if cruise_set:
            disp = raw if self.is_metric else raw * KM_TO_MILE
            set_speed = int(round(disp))
        return set_speed, cruise_set, cruise_available

    def _current_speed(self, cs) -> int:
        if cs is None:
            return 0
        v_ego_cluster = float(_get(cs, "vEgoCluster", 0.0) or 0.0)
        self._v_ego_cluster_seen = self._v_ego_cluster_seen or v_ego_cluster != 0.0
        v = v_ego_cluster if self._v_ego_cluster_seen else float(_get(cs, "vEgo", 0.0) or 0.0)
        conv = MS_TO_KPH if self.is_metric else MS_TO_MPH
        return int(round(max(0.0, v * conv)))

    def build(self, msgs: dict) -> dict:
        cs = msgs.get("carState")
        ss = msgs.get("selfdriveState")
        ctrl = msgs.get("controlsState")
        ds = msgs.get("deviceState")

        set_speed, cruise_set, cruise_available = self._set_speed(cs, ctrl)
        status = self.status(ss)

        alert = None
        if ss is not None:
            t1 = str(_get(ss, "alertText1", "") or "")
            t2 = str(_get(ss, "alertText2", "") or "")
            if t1 or t2:
                alert = {
                    "text1": t1,
                    "text2": t2,
                    "status": str(_get(ss, "alertStatus", "normal")),
                    "size": str(_get(ss, "alertSize", "none")),
                }

        started = bool(_get(ds, "started", True)) if ds is not None else True

        return {
            "type": "state",
            "started": started,
            "status": status,
            "borderColor": BORDER_COLORS.get(status, BORDER_COLORS[STATUS_DISENGAGED]),
            "engaged": bool(_get(ss, "enabled", False)),
            "speed": self._current_speed(cs),
            "speedUnit": "km/h" if self.is_metric else "mph",
            "setSpeed": set_speed,
            "cruiseSet": cruise_set,
            "cruiseAvailable": cruise_available,
            "experimentalMode": bool(_get(ss, "experimentalMode", False)),
            "personality": str(_get(ss, "personality", "standard")),
            "leftBlinker": bool(_get(cs, "leftBlinker", False)),
            "rightBlinker": bool(_get(cs, "rightBlinker", False)),
            "brakePressed": bool(_get(cs, "brakePressed", False)),
            "gasPressed": bool(_get(cs, "gasPressed", False)),
            "standstill": bool(_get(cs, "standstill", False)),
            "gear": str(_get(cs, "gearShifter", "unknown")),
            "alert": alert,
        }
