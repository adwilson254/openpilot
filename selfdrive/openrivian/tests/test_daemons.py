#!/usr/bin/env python3
import sys
import types
from unittest.mock import patch, MagicMock, AsyncMock

# Define a custom exception to break out of infinite loops
class LoopBreakException(Exception):
    pass

# Create mock module tree for openpilot and cereal
def create_mock_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

# Mock cereal
cereal = create_mock_module('cereal')
messaging = create_mock_module('cereal.messaging')
class MockSubMaster:
    def __init__(self, *args, **kwargs):
        self.updated = {
            'carState': False,
            'controlsState': False,
            'radarState': False,
            'managerState': False,
            'deviceState': False,
            'pandaStates': False,
            'liveLocationKalman': False
        }
    def update(self, *args, **kwargs):
        pass
    def __getitem__(self, key):
        return MagicMock()

messaging.SubMaster = MockSubMaster
messaging.PubMaster = MagicMock()

# Mock openpilot.common
openpilot = create_mock_module('openpilot')
openpilot_common = create_mock_module('openpilot.common')
openpilot_common_swaglog = create_mock_module('openpilot.common.swaglog')
openpilot_common_swaglog.cloudlog = MagicMock()

openpilot_common_params = create_mock_module('openpilot.common.params')
class MockParams:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def put(self, key, value):
        self.store[key] = value

openpilot_common_params.Params = MockParams

openpilot_common_realtime = create_mock_module('openpilot.common.realtime')
openpilot_common_realtime.Ratekeeper = MagicMock()

def test_missing_api_isolation():
    print("Testing MQTT and Web services without API (Isolation Test)...")
    
    # Hide the API module
    import sys
    sys.modules['selfdrive.openrivian.api'] = None
    sys.modules['selfdrive.openrivian.api.rivian_api'] = None
    sys.modules['selfdrive.openrivian.api.openriviand'] = None
    
    try:
        from selfdrive.openrivian import cereal2mqtt
        from selfdrive.openrivian import mqttd
        from selfdrive.openrivian import mqtt2params
        from selfdrive.openrivian import webd
        print(" -> All MQTT and Web modules successfully imported without API dependency.")
    except Exception as e:
        print(f"FAILED Isolation Test: {e}")
        sys.exit(1)
        
    # Restore modules
    del sys.modules['selfdrive.openrivian.api']
    del sys.modules['selfdrive.openrivian.api.rivian_api']
    del sys.modules['selfdrive.openrivian.api.openriviand']

def test_unauthenticated_api():
    print("Testing openriviand unauthenticated state...")
    try:
        from selfdrive.openrivian.api import openriviand
        class MockParams:
            def get(self, key):
                return None
        # Execute one step
        openriviand.step(MockParams())
        print(" -> openriviand completed step with missing RivianAccessToken gracefully.")
    except Exception as e:
        print(f"FAILED Unauthenticated API Test: {e}")
        sys.exit(1)

def test_nice_priorities():
    print("Testing os.nice(19) priority in all daemons...")
    import os
    daemons = [
        "selfdrive/openrivian/cereal2mqtt.py",
        "selfdrive/openrivian/mqttd.py",
        "selfdrive/openrivian/mqtt2params.py",
        "selfdrive/openrivian/webd.py",
        "selfdrive/openrivian/api/openriviand.py",
    ]
    for d in daemons:
        try:
            with open(d, "r") as f:
                content = f.read()
                if "os.nice(19)" not in content:
                    print(f"FAILED Priority Test: os.nice(19) not found in {d}")
                    sys.exit(1)
        except FileNotFoundError:
            pass
    print(" -> All daemons have os.nice(19) to protect self-drive compute.")

def test_build_mqtt_clients():
    # Constructs the REAL paho-mqtt client (paho is intentionally not mocked) so this
    # test fails loudly if the installed/pinned paho version stops supporting the API
    # the bridges rely on. Import-only tests cannot catch that.
    print("Testing real paho-mqtt client construction against the installed version...")
    from selfdrive.openrivian import cereal2mqtt
    from selfdrive.openrivian import mqtt2params
    for mod in (cereal2mqtt, mqtt2params):
        if mod.mqtt is None:
            print(f"FAILED Client Test: paho-mqtt not importable in {mod.__name__}")
            sys.exit(1)
        try:
            client = mod.build_client()
        except Exception as e:
            print(f"FAILED Client Test: build_client() raised in {mod.__name__}: {e}")
            sys.exit(1)
        if client is None:
            print(f"FAILED Client Test: build_client() returned None in {mod.__name__}")
            sys.exit(1)
    print(" -> cereal2mqtt and mqtt2params construct paho clients OK with the installed version.")

# We don't need to mock paho.mqtt because we added it via uv add
# But we do need to mock its functions to raise LoopBreakException
def run_tests():
    print("Testing imports to verify dependencies and syntax...")
    
    try:
        from selfdrive.openrivian import cereal2mqtt
        print("cereal2mqtt OK")
        
        from selfdrive.openrivian import mqttd
        print("mqttd OK")
        
        from selfdrive.openrivian import mqtt2params
        print("mqtt2params OK")
        
        from selfdrive.openrivian import webd
        print("webd OK")
        
        from selfdrive.openrivian.api import openriviand
        print("openriviand OK")
        
        from selfdrive.openrivian.api import rivian_api
        print("rivian_api OK")
        
    except Exception as e:
        print(f"FAILED: {e}")
        import sys
        sys.exit(1)
        
    # Run the isolation tests
    test_missing_api_isolation()
    test_unauthenticated_api()
    test_nice_priorities()
    test_build_mqtt_clients()
        
    print("ALL TESTS PASSED.")

if __name__ == '__main__':
    run_tests()
