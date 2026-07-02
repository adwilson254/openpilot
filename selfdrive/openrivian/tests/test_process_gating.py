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
