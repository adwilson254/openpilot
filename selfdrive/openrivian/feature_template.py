#!/usr/bin/env python3
import os
try:
    os.nice(19)
except Exception:
    pass

import time
import os
from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params

# Example configuration
POLL_RATE_HZ = 1.0

def step(params):
    """
    The core logic of your feature.
    Extracted from the while True loop to allow for unit testing of failure modes.
    """
    try:
        # Example of gracefully handling missing parameters
        some_setting = params.get_bool("MyCustomSetting")
        if not some_setting:
            cloudlog.debug("Feature disabled or missing parameter.")
            return

        # Do your feature logic here...
        pass
        
    except Exception as e:
        # ALWAYS catch exceptions at the top level of your step
        # so you don't crash the entire daemon!
        cloudlog.error(f"MyFeature encountered an error: {e}")

def main():
    """
    Entry point for the background process.
    """
    """

    cloudlog.info("MyFeature daemon started.")
    params = Params()

    # 2. Infinite loop that runs your feature
    while True:
        step(params)
        time.sleep(1.0 / POLL_RATE_HZ)

if __name__ == "__main__":
    main()
