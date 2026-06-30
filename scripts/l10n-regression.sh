#!/usr/bin/env bash
# Deterministic localization + layout regression: deep walk -> checker -> report.
# Usage: scripts/l10n-regression.sh [candidate_out_dir]
# Stack must be up (./scripts/up.sh). Report -> .qa/ru-term-inventory/regression/report.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INV="$ROOT/.qa/ru-term-inventory"
CAND="${1:-$INV/rendered-candidate}"
GOLDEN="$INV/rendered"
EXPECT="$INV/expectations.json"
( cd "$ROOT/e2e" && node scripts/editor-l10n-rendered.mjs \
    --locales=en,ru --apps=writer,calc,impress --out="$CAND" --screenshots=main )
args=(--candidate "$CAND" --out "$INV/regression")
[ -d "$GOLDEN" ] && args+=(--golden "$GOLDEN")
[ -f "$EXPECT" ] && args+=(--expect "$EXPECT")
python3 "$ROOT/scripts/l10n-regression-check.py" "${args[@]}"
