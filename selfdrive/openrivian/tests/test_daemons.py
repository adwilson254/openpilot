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
        
    print("ALL TESTS PASSED.")

if __name__ == '__main__':
    run_tests()
