#!/usr/bin/env python3
# NOTE: os.nice(19) must only be called inside main(), never at module level.
# The process manager pre-imports every daemon module inside the manager process
# (manager_init -> prepare -> importlib.import_module) BEFORE forking children, so a
# module-level nice() permanently demotes manager and the ENTIRE openpilot stack
# (root cause of the 2026-07 "TAKE CONTROL IMMEDIATELY / Communication Issue" storms).
# Guarded by tests/test_no_module_level_nice.py.
import os
import asyncio
import logging
import sys
try:
    from amqtt.broker import Broker
except ImportError:
    Broker = None

# Configure broker to listen on localhost (0.0.0.0) without persistence.
# Keeps everything in RAM to protect EMMC lifespan.
config = {
    'listeners': {
        'default': {
            'type': 'tcp',
            'bind': '0.0.0.0:1883',
            'max_connections': 1000,
        },
        'ws-default': {
            'type': 'ws',
            'bind': '0.0.0.0:9001',
            'max_connections': 1000,
        }
    },
    'sys_interval': 10,
    'auth': {
        'allow-anonymous': True,
    },
    'topic-check': {
        'enabled': False
    }
}

async def run_broker():
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger('amqtt')
    logger.setLevel(logging.WARNING)
    
    print("[*] Starting OpenRivian MQTT Broker Daemon in RAM...")
    broker = Broker(config)
    await broker.start()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        await broker.shutdown()
        print("[*] MQTT Broker shutdown.")

def main():
    # Low priority for THIS daemon only (safe here: we are in the forked child).
    try:
        os.nice(19)
    except Exception:
        pass

    if Broker is None:
        logging.error("Missing amqtt. Gracefully exiting mqttd.")
        return

    try:
        asyncio.run(run_broker())
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    main()
