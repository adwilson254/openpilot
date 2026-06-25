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
"$CONTAINER_CLI" run --rm --platform linux/arm64 "$IMAGE"
