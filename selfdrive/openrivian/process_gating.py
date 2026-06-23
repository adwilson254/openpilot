"""Process-manager gating for the OpenRivian telemetry stack.

Kept in a tiny, dependency-free module so the gating logic is unit-testable without
importing the full process_config (which pulls in cereal/sunnypilot/heavy modules).
"""


def openrivian_enabled(started, params, CP) -> bool:
    """Gate for the OpenRivian daemons (openriviand, mqttd, cereal2mqtt,
    mqtt2params, webd).

    Auto-enables (and persists) on Rivian-brand vehicles so the broker/dashboard
    remain available offroad too; otherwise honors the manual OpenRivianEnabled
    toggle. This keeps the daemons from running on non-Rivian cars or before opt-in.
    """
    if getattr(CP, "brand", "") == "rivian":
        if not params.get_bool("OpenRivianEnabled"):
            params.put_bool("OpenRivianEnabled", True)
        return True
    return params.get_bool("OpenRivianEnabled")
