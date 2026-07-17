#!/usr/bin/env python3
# NOTE: os.nice(19) must only be called inside main(), never at module level.
# The process manager pre-imports every daemon module inside the manager process
# (manager_init -> prepare -> importlib.import_module) BEFORE forking children, so a
# module-level nice() permanently demotes manager and the ENTIRE openpilot stack
# (root cause of the 2026-07 "TAKE CONTROL IMMEDIATELY / Communication Issue" storms).
# Guarded by tests/test_no_module_level_nice.py.
import time
import os
from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params

def step(params):
    # Check if we are authenticated
    try:
        token_raw = params.get("RivianAccessToken")
        if token_raw:
            token = token_raw.decode('utf-8') if isinstance(token_raw, bytes) else str(token_raw)
            pass # TODO: In future iterations, we will fetch ABRP routes here.
        else:
            cloudlog.debug("OpenRivian API Daemon: RivianAccessToken not found in params.")
    except Exception as e:
        cloudlog.warning(f"OpenRivian API Daemon params.get error: {e}")

def main():
    try:
        os.nice(19)
    except Exception as e:
        cloudlog.warning(f"Failed to set nice value: {e}")
        
    cloudlog.info("OpenRivian API Daemon started.")
    params = Params()

    while True:
        step(params)
        time.sleep(5)

if __name__ == "__main__":
    main()
