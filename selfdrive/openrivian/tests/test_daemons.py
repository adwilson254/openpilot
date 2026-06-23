"""Smoke + lightweight behavioral tests for the OpenRivian daemons.

Relies on the hermetic mocks installed by conftest.py so the daemons import without a
built openpilot/cereal environment.
"""
import importlib
import pathlib

import pytest

DAEMON_FILES = [
    "selfdrive/openrivian/cereal2mqtt.py",
    "selfdrive/openrivian/mqttd.py",
    "selfdrive/openrivian/mqtt2params.py",
    "selfdrive/openrivian/webd.py",
    "selfdrive/openrivian/api/openriviand.py",
]

ALL_MODULES = [
    "selfdrive.openrivian.cereal2mqtt",
    "selfdrive.openrivian.mqttd",
    "selfdrive.openrivian.mqtt2params",
    "selfdrive.openrivian.webd",
    "selfdrive.openrivian.api.openriviand",
    "selfdrive.openrivian.api.rivian_api",
]

BRIDGE_FILES = ["cereal2mqtt.py", "mqttd.py", "mqtt2params.py", "webd.py"]


@pytest.mark.parametrize("module", ALL_MODULES)
def test_daemon_imports(module):
    assert importlib.import_module(module) is not None


def test_bridges_do_not_depend_on_rivian_api():
    # The MQTT/web daemons must run without the Rivian API module so a broken or
    # unauthenticated API never takes telemetry/dashboard down with it.
    for fname in BRIDGE_FILES:
        src = pathlib.Path("selfdrive/openrivian", fname).read_text()
        assert "openrivian.api" not in src, f"{fname} should not import the Rivian API package"


def test_unauthenticated_api_step_is_graceful(fake_params):
    from selfdrive.openrivian.api import openriviand
    # No RivianAccessToken in params -> must complete a step without raising.
    openriviand.step(fake_params)


def test_all_daemons_set_low_priority():
    for f in DAEMON_FILES:
        assert "os.nice(19)" in pathlib.Path(f).read_text(), f"{f} missing os.nice(19)"
