"""Shared test harness for the OpenRivian unit tests.

The OpenRivian daemons import `cereal` and `openpilot.common.*` at module load
(some, like mqtt2params, even construct `Params()` at import time). Those modules
require a built/compiled openpilot environment that is not present in the lightweight
CI test job. This conftest installs hermetic mocks for them so every test file in this
directory can import the daemons in any environment.

Scope: pytest only auto-loads this conftest for tests under selfdrive/openrivian/tests,
so it does not affect the rest of the repo. test_dependencies.py is intentionally run
as a standalone process (not via pytest) so its real-environment package check is not
shadowed by these mocks.
"""
import sys
import types
import json as _json
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fake Params: dict-backed, mirrors the subset of the openpilot Params API the
# OpenRivian daemons use.
# ---------------------------------------------------------------------------
class FakeParams:
    def __init__(self):
        self.store: dict[str, bytes] = {}

    def get(self, key, *_a, **_k):
        return self.store.get(key)

    def get_bool(self, key, *_a, **_k):
        return self.store.get(key) == b"1"

    def put(self, key, val):
        if isinstance(val, str):
            val = val.encode("utf-8")
        self.store[key] = val

    def put_bool(self, key, val):
        self.store[key] = b"1" if val else b"0"

    def remove(self, key):
        self.store.pop(key, None)


def _install_mock_modules():
    # cereal + cereal.messaging
    cereal = sys.modules.setdefault("cereal", types.ModuleType("cereal"))
    messaging = types.ModuleType("cereal.messaging")

    class _SubMaster:
        def __init__(self, *_a, **_k):
            self.updated = {}

        def update(self, *_a, **_k):
            pass

        def __getitem__(self, _key):
            return MagicMock()

    messaging.SubMaster = _SubMaster
    messaging.PubMaster = MagicMock
    messaging.sub_sock = lambda *_a, **_k: MagicMock()
    messaging.drain_sock = lambda *_a, **_k: []
    sys.modules["cereal.messaging"] = messaging
    cereal.messaging = messaging

    # openpilot.common.{params,swaglog,realtime}
    op = sys.modules.setdefault("openpilot", types.ModuleType("openpilot"))
    common = sys.modules.setdefault("openpilot.common", types.ModuleType("openpilot.common"))
    op.common = common

    params_mod = types.ModuleType("openpilot.common.params")
    params_mod.Params = FakeParams
    sys.modules["openpilot.common.params"] = params_mod
    common.params = params_mod

    swaglog = types.ModuleType("openpilot.common.swaglog")
    swaglog.cloudlog = MagicMock()
    sys.modules["openpilot.common.swaglog"] = swaglog
    common.swaglog = swaglog

    realtime = types.ModuleType("openpilot.common.realtime")
    realtime.Ratekeeper = MagicMock()
    sys.modules["openpilot.common.realtime"] = realtime
    common.realtime = realtime

    # amqtt is only installed in the full CI env (it requires py>=3.10). mqttd imports
    # amqtt.broker.Broker at module load, so provide a stand-in when it is unavailable.
    try:
        import amqtt.broker  # noqa: F401
    except Exception:
        amqtt = types.ModuleType("amqtt")
        amqtt_broker = types.ModuleType("amqtt.broker")
        amqtt_broker.Broker = MagicMock
        sys.modules["amqtt"] = amqtt
        sys.modules["amqtt.broker"] = amqtt_broker
        amqtt.broker = amqtt_broker


_install_mock_modules()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_params():
    return FakeParams()


class RecordingMQTTClient:
    """Stand-in for a paho client that records publish()/subscribe() calls."""
    def __init__(self):
        self.published: list[tuple[str, object, bool]] = []
        self.subscriptions: list[str] = []
        self.on_connect = None
        self.on_message = None

    def publish(self, topic, payload, retain=False):
        try:
            payload = _json.loads(payload)
        except Exception:
            pass
        self.published.append((topic, payload, retain))

    def subscribe(self, topic):
        self.subscriptions.append(topic)

    def topics(self):
        return [t for t, _p, _r in self.published]

    def value_for(self, topic):
        for t, p, _r in self.published:
            if t == topic:
                return p["value"] if isinstance(p, dict) and "value" in p else p
        return None


@pytest.fixture
def fake_mqtt_client():
    return RecordingMQTTClient()
