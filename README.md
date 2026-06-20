# OpenRivian `can-debug` Branch

> [!WARNING]
> **DO NOT ATTEMPT TO SELF-DRIVE ON THIS BRANCH.**
> This branch contains experimental CAN packet sniffers, telemetry extraction, and reverse-engineering daemons. These daemons explicitly violate compute-safety guarantees and will actively interfere with or consume resources from OpenPilot's core driving logic.

## Purpose

The `can-debug` branch is an isolated playground strictly for extracting and reverse engineering CAN network signals while the vehicle is parked. It is entirely disconnected from the main `dev` pipeline.

### Daemons Included:
- **`chargingd.py`**: Extracts high-voltage battery states, charging metrics, and BMS data.
- **`rivian_telemetryd.py`**: Interrogates Rivian's proprietary telemetry endpoints for vehicle metrics.
- **`can-decode` utilities**: General DBC parsing and frame extraction tools.

## Testing on the Vehicle

To test these tools on the Comma device:
1. Ensure the vehicle is parked.
2. SSH into the Comma device.
3. Check out this branch and forcefully sync the submodules:
   ```bash
   cd /data/openpilot && git fetch --all && git reset --hard origin/can-debug && git submodule update --init --recursive && sudo systemctl restart comma
   ```
4. Perform your CAN sniffing/debugging.

## Returning to Self-Driving

When you are ready to drive, you **MUST** revert the device back to the safe `dev` branch:
```bash
cd /data/openpilot && git fetch --all && git reset --hard origin/dev && git submodule update --init --recursive && sudo systemctl restart comma
```
