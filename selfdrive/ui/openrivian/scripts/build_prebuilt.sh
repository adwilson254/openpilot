#!/usr/bin/env bash
set -e

# OpenRivian On-Device Prebuilt Script
# This natively compiles the code on the Comma, strips out heavy C/C++ files,
# and prepares the fast-booting `pre` branch.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
OPENRIVIAN_ROOT="$(git -C $DIR rev-parse --show-toplevel)"

echo "[-] Navigating to root: $OPENRIVIAN_ROOT"
cd $OPENRIVIAN_ROOT

# Ensure we are on dev branch
git checkout dev

# 1. Native Compilation
echo "[-] Compiling natively on device... this will take a while!"
export PYTHONPATH="$OPENRIVIAN_ROOT"
scons -j$(nproc) --minimal

# 2. Prebuilt Flag
echo "[-] Setting prebuilt flag for fast booting..."
touch prebuilt

# 3. Create pre branch
echo "[-] Creating pristine pre branch..."
git checkout -B pre

# 4. Stripping Source Files to Save Space
echo "[-] Stripping source files (*.c, *.cc, *.cpp, *.o, *.os)..."
find . -name '*.cc' -type f -delete
find . -name '*.cpp' -type f -delete
find . -name '*.c' -type f -delete
find . -name '*.o' -type f -delete
find . -name '*.os' -type f -delete

# 5. Commit stripped changes
echo "[-] Committing prebuilt branch..."
git add -f .
git commit -m "OpenRivian Prebuilt Release"

echo "[-] Prebuilt branch ready! Your Comma will now boot much faster."
