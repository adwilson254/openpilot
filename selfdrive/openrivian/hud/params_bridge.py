"""
Parameter read/write bridge for the HUD touch controls.

Reuses the same whitelist as selfdrive/openrivian/mqtt2params.py
(sunnypilot/sunnylink/params_metadata.json) so only known params can be set.

On-device it uses openpilot's Params. For local dev (where Params isn't
available) it falls back to an in-memory store so the toggles still work in
the replay demo.
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
# selfdrive/openrivian/hud -> repo root is three levels up
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
_META_PATH = os.path.join(_REPO_ROOT, "sunnypilot", "sunnylink", "params_metadata.json")

# Curated, driver-facing toggles surfaced in the HUD settings panel.
# Filtered against the whitelist at load so we never show an unknown key.
CURATED = [
    ("ExperimentalMode", "Experimental Mode", "bool"),
    ("AlphaLongitudinalEnabled", "openpilot Longitudinal (alpha)", "bool"),
    ("AlwaysOnDM", "Always-On Driver Monitoring", "bool"),
    ("DisengageOnAccelerator", "Disengage On Gas", "bool"),
    ("IsMetric", "Metric Units", "bool"),
]


class ParamsBridge:
    def __init__(self):
        try:
            with open(_META_PATH) as f:
                self.whitelist = set(json.load(f).keys())
        except Exception:
            self.whitelist = set()

        self._params = None
        self._mem: dict = {}
        try:
            from openpilot.common.params import Params  # type: ignore
            self._params = Params()
            self.live = True
        except Exception:
            self.live = False

    def _allowed(self, key: str) -> bool:
        # if whitelist failed to load, allow only curated keys
        if self.whitelist:
            return key in self.whitelist
        return key in {k for k, _, _ in CURATED}

    def get(self, key: str):
        if self.live:
            try:
                raw = self._params.get(key)
                if raw is None:
                    return None
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", "ignore")
                if raw in ("0", "1"):
                    return raw == "1"
                return raw
            except Exception:
                return None
        return self._mem.get(key)

    def set(self, key: str, value) -> bool:
        if not self._allowed(key):
            return False
        if self.live:
            try:
                if isinstance(value, bool):
                    self._params.put_bool(key, value)
                else:
                    self._params.put(key, str(value))
                return True
            except Exception:
                return False
        self._mem[key] = value
        return True

    def curated(self) -> list:
        items = []
        for key, label, typ in CURATED:
            if self.whitelist and key not in self.whitelist:
                continue
            items.append({"key": key, "label": label, "type": typ, "value": self.get(key)})
        return items
