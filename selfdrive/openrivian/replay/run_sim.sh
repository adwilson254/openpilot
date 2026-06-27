#!/usr/bin/env bash
# Tier 2 -- closed-loop validation in the MetaDrive simulator (pure Python, no
# CARLA). Drives the FULL stack (model + controls + your daemons) against a
# synthetic world, so you can watch behavior end-to-end without a vehicle.
#
# Requires the built openpilot environment (scons + model runtime). On macOS the
# model runs on CPU/Metal, so BEHAVIOR is representative but TIMING is not.
#
# Usage:
#   selfdrive/openrivian/replay/run_sim.sh           # keyboard control
#   selfdrive/openrivian/replay/run_sim.sh --joystick
#
# Controls (in the sim window): 2 engage, 1 accel, 2 decel, s disengage, q quit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

echo "[*] Preflight..."
if [ ! -d ".venv" ]; then
  echo "  ! .venv not found. Run tools/setup_dependencies.sh first (installs the uv venv)." >&2
fi
if ! "${ROOT}/.venv/bin/python" -c "import metadrive" 2>/dev/null; then
  echo "  ! metadrive not importable. It ships with the openpilot extras:" >&2
  echo "      uv sync --all-extras   (or: pip install metadrive-simulator)" >&2
fi
if [ ! -f "selfdrive/manager/manager.py" ] && [ ! -f "system/manager/manager.py" ]; then
  echo "  ! manager not found at expected path -- check your tree." >&2
fi

echo "[*] Launching openpilot (background) ..."
./tools/sim/launch_openpilot.sh &
OP_PID=$!
trap 'kill $OP_PID 2>/dev/null || true' EXIT

sleep 5
echo "[*] Starting MetaDrive bridge ..."
exec ./tools/sim/run_bridge.py "$@"
