#!/usr/bin/env bash
# Bring up the stack, building the editor with a per-build cache-bust token (BUILD_ID) tied to the
# CURRENT source state. Use this instead of a bare `docker compose up -d --build`: the editor stamps
# BUILD_ID into coolwsd's ver_suffix (ETag) and onto cool.html asset URLs (?b=), so returning
# browsers reliably refetch changed editor assets. A bare compose build leaves BUILD_ID=dev, which
# makes that cache invalidation a no-op (and can serve stale editor assets after a redeploy).
#
# Usage:
#   ./scripts/up.sh                 # build + (re)start the whole stack
#   ./scripts/up.sh editor          # only the editor service
set -euo pipefail
cd "$(dirname "$0")/.."

BUILD_ID="$(git rev-parse --short HEAD 2>/dev/null || echo dev)"
# Mark uncommitted state so the token never falsely claims to match a committed SHA.
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  BUILD_ID="${BUILD_ID}-dirty"
fi

echo "Bringing up the stack with editor BUILD_ID=${BUILD_ID}"
exec env BUILD_ID="${BUILD_ID}" docker compose up -d --build "$@"
