#!/usr/bin/env bash
# Live-apply the PrivateOffice glass theme into the running editor container for fast
# iteration WITHOUT a full image rebuild. The theme is normally folded into the editor's
# own bundle.css at build time (editor/Dockerfile); this script reproduces that against a
# kept-pristine copy so re-runs never stack duplicates. The baked image is the source of truth.
set -euo pipefail
cd "$(dirname "$0")/.."
CID=$(docker compose ps -q editor)
DIST=/usr/share/coolwsd/browser/dist
docker cp editor/branding-privateoffice.css "$CID:/tmp/po-theme.css"
docker exec -u root "$CID" bash -lc "
  cd $DIST
  # keep a pristine bundle.css once, then rebuild = pristine + theme (idempotent re-runs)
  [ -f bundle.css.orig ] || cp bundle.css bundle.css.orig
  cp bundle.css.orig bundle.css
  cat /tmp/po-theme.css >> bundle.css
  echo \"folded theme into bundle.css (\$(wc -l < /tmp/po-theme.css) theme lines)\"
"
echo "done — hard-refresh the editor (bundle.css is cache-busted only by %VERSION%)."
