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


# Per-service toggles ---------------------------------------------------------
# Each OpenRivian daemon is gated by the master gate above AND its own persistent
# "disabled" flag, so any single service can be turned off independently (e.g. to
# isolate which one is causing an issue) without touching the others. Default-on: an
# unset flag means enabled. The daemons are loosely coupled (the MQTT publishers just
# retry the broker connection), so disabling any one leaves the rest working.
SERVICE_DISABLE_KEYS = {
    "openriviand": "OpenRivianApiDisabled",
    "mqttd": "OpenRivianBrokerDisabled",
    "cereal2mqtt": "OpenRivianTelemetryDisabled",
    "mqtt2params": "OpenRivianSettingsPublishDisabled",
    "webd": "OpenRivianWebDashboardDisabled",
}


def service_enabled(service):
    """Return a process-manager gate for a single OpenRivian daemon: the master gate
    AND the per-service '<...>Disabled' flag being unset. `service` must be a key of
    SERVICE_DISABLE_KEYS."""
    disable_key = SERVICE_DISABLE_KEYS[service]

    def gate(started, params, CP) -> bool:
        if not openrivian_enabled(started, params, CP):
            return False
        return not params.get_bool(disable_key)

    return gate
