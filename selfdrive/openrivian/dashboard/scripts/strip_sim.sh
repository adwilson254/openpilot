#!/usr/bin/env bash
# Remove the dashboard simulator for PRODUCTION (the dev branch the vehicle runs).
#
# The simulator (real-drive replay + synthetic engaged-state overlay) exists only to
# preview/test the UI off-vehicle, and is already inert on a vehicle (it requires
# ?sim=1, never opens an MQTT connection, and publish() is a no-op in sim). This script
# is the belt-and-suspenders step run during dev-test -> dev promotion so the simulator
# and its recorded-drive data are physically absent from the production build. Sim then
# only works on feature branches and dev-test.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # dashboard/
cd "$DIR"

rm -f src/assets/sim_drive.json src/__tests__/sim.test.js

# Replace the simulator with permanently-disabled stubs so the bundle still builds
# (mqtt.jsx imports these). With simEnabled() === false, the replay branch is dead code
# and Vite drops it; no recorded-drive data ships.
cat > src/lib/sim.js <<'EOF'
// Simulator REMOVED for production (dev). It exists only on feature branches / dev-test.
// These permanently-disabled stubs keep the bundle building; there is no simulator and
// no recorded-drive data in this build.
export function simEnabled() { return false; }
export function simSnapshot() { return {}; }
export async function loadSimTimeline() { return { hz: 5, topics: [], frames: [] }; }
EOF

echo "[strip_sim] simulator removed; sim.js stubbed (permanently disabled for production)."
