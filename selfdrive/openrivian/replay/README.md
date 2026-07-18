# OpenRivian off-vehicle validation toolkit

Validate the OpenRivian daemons and the dashboard pipeline **without a driving
comma**, on an Apple Silicon Mac. The comma (AGNOS) and your Mac are both
**arm64** — the CPU matches; only the OS and a few native/GPU deps differ. These
tiers close those gaps from cheapest/fastest to highest fidelity.

| Tier | What it validates | Needs | Runs on Mac |
|------|-------------------|-------|-------------|
| 0 | Daemon logic, dashboard data layer (hermetic units) | nothing | ✅ now |
| 1 | Telemetry pipeline end-to-end (cereal → MQTT contract) | nothing (synthetic) / a route log (real) | ✅ now |
| 2 | Full stack closed-loop (model + controls + daemons) | built openpilot + MetaDrive | ✅ behavior (not timing) |
| 3 | Linux/arm64 OS parity | Docker Desktop | ✅ native arm64 |
| 4 | Rivian CAN/DBC decoding | a recorded route | ✅ with a log |

## Tier 1 — process replay (recommended, works today)
Drives `cereal2mqtt.publish_state` with message snapshots and records every MQTT
publish, then asserts the topic/value contract. Same code path for synthetic and
real data.

```bash
# synthetic (no vehicle, no build):
python -m selfdrive.openrivian.replay.harness --synthetic --frames 20

# real recorded drive (when you have one):
python -m selfdrive.openrivian.replay.harness --route /path/to/rlog.bz2
```
Tests: `selfdrive/openrivian/tests/test_cereal2mqtt_replay.py` (in CI + local).

**Plugging in a real route:** drop a route id/segment into the same `route_frames()`
source and the existing assertions run against real vehicle data — no code change
to the daemon. This is the moment a recorded drive unlocks the highest-value test.

## Tier 2 — MetaDrive sim
```bash
selfdrive/openrivian/replay/run_sim.sh            # keyboard
selfdrive/openrivian/replay/run_sim.sh --joystick
```
Pure-Python sim (no CARLA). Needs the built env (`tools/setup_dependencies.sh`,
`uv sync --all-extras`). On macOS the model runs on CPU/Metal, so behavior is
representative but timing is not device-accurate.

## Tier 3 — Linux/arm64 parity
```bash
selfdrive/openrivian/replay/run_parity.sh   # auto-detects docker or podman
```
Builds `Dockerfile.parity` and runs the suite as native arm64 Linux (no QEMU).
Catches Linux-only breakage and dependency drift. Mirrors the CI test job.
Works with Docker Desktop or Podman (`podman machine` must be running on macOS).

## Tier 4 — CAN replay + Cabana
```bash
ROUTE="<dongle_id>|<timestamp>" selfdrive/openrivian/replay/run_can_replay.sh
./tools/cabana/cabana "$ROUTE"     # visual DBC inspector, same route
```
Replays recorded CAN onto a virtual bus to verify the Rivian DBC / diagnosed
signals without the truck.

See `Kiro Artifacts/OpenRivian_Testing_Strategy.md` for the full rationale.
