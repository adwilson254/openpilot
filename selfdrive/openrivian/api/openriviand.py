#!/usr/bin/env python3
import time
from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params

def main():
    cloudlog.info("OpenRivian API Daemon started.")
    params = Params()

    while True:
        # Check if we are authenticated
        token_bytes = params.get("RivianAccessToken")
        if token_bytes:
            token = token_bytes.decode('utf-8')
            pass # TODO: In future iterations, we will fetch ABRP routes here.
            
        time.sleep(5)

if __name__ == "__main__":
    main()
