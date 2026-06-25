#!/usr/bin/env bash
# Tier 4 -- replay recorded CAN from a real drive onto a virtual bus, then verify
# the Rivian DBC decoding (the diagnosed-signal work from the can-debug branch)
# WITHOUT touching the truck.
#
# Two complementary tools:
#   1. can_replay.py -- republishes a route's CAN so the car interface/openpilot
#      decode it live, exactly as on the device.
#   2. cabana        -- visual DBC inspector; open the same route and confirm a
#      signal/message decodes to the expected value.
#
# Needs a recorded route (rlog/qlog) or a route id. Set the route below.
#
# Usage:
#   ROUTE="<dongle_id>|<timestamp>" selfdrive/openrivian/replay/run_can_replay.sh
#   ROUTE="/path/to/rlog.bz2"       selfdrive/openrivian/replay/run_can_replay.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

ROUTE="${ROUTE:-}"
if [ -z "$ROUTE" ]; then
  cat <<'EOF'
No ROUTE set. Provide one of:
  ROUTE="<dongle_id>|<timestamp>"   # a route id from your comma account / connect
  ROUTE="/abs/path/to/rlog.bz2"     # a local recorded segment

Then re-run this script. To inspect the same route visually in Cabana:
  ./tools/cabana/cabana "$ROUTE"
and check the Rivian messages/signals decode against selfdrive/car (Rivian DBC).
EOF
  exit 1
fi

echo "[*] Replaying CAN from: $ROUTE"
echo "    (Ctrl-C to stop. Open ./tools/cabana/cabana \"$ROUTE\" in another shell to watch decoding.)"
exec ./tools/replay/can_replay.py "$ROUTE"
