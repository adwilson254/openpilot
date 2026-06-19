#!/usr/bin/env python3
import time
from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params

def main():
    cloudlog.info("OpenRivian API Daemon started.")
    params = Params()

    while True:
        # Check if we are authenticated
        try:
            token_raw = params.get("RivianAccessToken")
            if token_raw:
                token = token_raw.decode('utf-8') if isinstance(token_raw, bytes) else str(token_raw)
                pass # TODO: In future iterations, we will fetch ABRP routes here.
        except Exception as e:
            cloudlog.warning(f"OpenRivian API Daemon params.get error: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    main()
