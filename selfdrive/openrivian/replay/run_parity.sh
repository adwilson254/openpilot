#!/usr/bin/env bash
# Tier 3 -- run the OpenRivian test suite inside a Linux/arm64 container for
# OS parity with the comma. Native arm64 on Apple Silicon (no emulation).
#
# Usage:  selfdrive/openrivian/replay/run_parity.sh
set -euo pipefail

# Resolve repo root (this script lives in selfdrive/openrivian/replay).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

if command -v docker >/dev/null 2>&1; then
  CONTAINER_CLI="docker"
elif command -v podman >/dev/null 2>&1; then
  CONTAINER_CLI="podman"
else
  echo "Neither docker nor podman found. Install one (Apple Silicon build) and retry." >&2
  echo "The container runs as native arm64 Linux -- no QEMU, near-native speed." >&2
  exit 1
fi
echo "[*] Using container engine: $CONTAINER_CLI"

IMAGE="openrivian-parity"
echo "[*] Building $IMAGE (linux/arm64)..."
"$CONTAINER_CLI" build --platform linux/arm64 \
  -f selfdrive/openrivian/replay/Dockerfile.parity \
  -t "$IMAGE" .

echo "[*] Running suite in container..."

# Mount real device data captured from the comma (params store + recorded route) if
# present, so the suite can exercise the daemons against genuine state. Stored outside
# the repo under "Kiro Artifacts/comma_data" (override with ORV_DATA_DIR). When mounted,
# ORV_PARAMS_DIR enables test_mqtt2params_realparams.py and ORV_TEST_ROUTE the real-route
# test (the latter still needs a cereal-capable image; it skips in this lightweight one).
ORV_DATA_DIR="${ORV_DATA_DIR:-$ROOT/../Kiro Artifacts/comma_data}"
MOUNTS=()
ENVS=()
if [ -d "$ORV_DATA_DIR/params/d" ]; then
  echo "    + mounting real params from: $ORV_DATA_DIR/params/d"
  MOUNTS+=(-v "$ORV_DATA_DIR/params/d:/mnt/params:ro")
  ENVS+=(-e ORV_PARAMS_DIR=/mnt/params)
else
  echo "    (no real data at $ORV_DATA_DIR/params/d -- real-data tests will skip)"
fi

"$CONTAINER_CLI" run --rm --platform linux/arm64 "${MOUNTS[@]}" "${ENVS[@]}" "$IMAGE"
