"""Tests for the OpenRivian process-manager gate (F8)."""
from selfdrive.openrivian.process_gating import openrivian_enabled


class _CP:
    def __init__(self, brand):
        self.brand = brand


def test_disabled_by_default_on_non_rivian(fake_params):
    assert openrivian_enabled(False, fake_params, _CP("toyota")) is False
    assert openrivian_enabled(True, fake_params, _CP("toyota")) is False


def test_manual_toggle_enables_on_non_rivian(fake_params):
    fake_params.put_bool("OpenRivianEnabled", True)
    assert openrivian_enabled(False, fake_params, _CP("toyota")) is True


def test_auto_enables_and_persists_on_rivian(fake_params):
    assert fake_params.get_bool("OpenRivianEnabled") is False
    assert openrivian_enabled(True, fake_params, _CP("rivian")) is True
    # The choice is persisted so the stack stays available offroad too.
    assert fake_params.get_bool("OpenRivianEnabled") is True


def test_missing_brand_attribute_is_safe(fake_params):
    assert openrivian_enabled(False, fake_params, object()) is False


# Per-service toggles ---------------------------------------------------------
from selfdrive.openrivian.process_gating import service_enabled, SERVICE_DISABLE_KEYS


def test_service_enabled_default_on_for_rivian(fake_params):
    # With the master gate on (rivian), every service is enabled by default.
    for svc in SERVICE_DISABLE_KEYS:
        assert service_enabled(svc)(True, fake_params, _CP("rivian")) is True


def test_service_disable_flag_disables_only_that_service(fake_params):
    fake_params.put_bool("OpenRivianTelemetryDisabled", True)  # disable cereal2mqtt only
    assert service_enabled("cereal2mqtt")(True, fake_params, _CP("rivian")) is False
    # The others stay enabled -- each service is independent.
    assert service_enabled("mqttd")(True, fake_params, _CP("rivian")) is True
    assert service_enabled("webd")(True, fake_params, _CP("rivian")) is True
    assert service_enabled("openriviand")(True, fake_params, _CP("rivian")) is True
    assert service_enabled("mqtt2params")(True, fake_params, _CP("rivian")) is True


def test_service_gate_respects_master_gate(fake_params):
    # Master gate off (non-rivian, no opt-in) -> service disabled regardless of its flag.
    assert service_enabled("mqttd")(True, fake_params, _CP("toyota")) is False


def test_every_daemon_has_a_disable_key():
    assert set(SERVICE_DISABLE_KEYS) == {"openriviand", "mqttd", "cereal2mqtt", "mqtt2params", "webd"}
