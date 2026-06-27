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
