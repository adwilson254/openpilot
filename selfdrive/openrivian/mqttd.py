#!/usr/bin/env python3
import asyncio
import logging
import sys
from amqtt.broker import Broker

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
    try:
        asyncio.run(run_broker())
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    main()
