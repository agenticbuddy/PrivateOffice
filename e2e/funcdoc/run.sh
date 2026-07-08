#!/usr/bin/env bash
# One-command funcdoc gate: gen -> template -> smoke -> check, and CLEAN UP after itself.
# The node smoke.mjs uploads is this script's own temporary artifact: on PASS it is DELETED
# (reviewer: verify scripts must not pile test nodes up in storage); on FAIL (smoke or check)
# it is KEPT and its id printed, so the broken workbook can be inspected.
# SUBSET=N is propagated identically to BOTH smoke.mjs and check.py (they must match — see README).
# NODE=<id> builds into an existing node; a pre-existing node is NEVER deleted by this script.
set -uo pipefail
cd "$(dirname "$0")"
BASE=http://localhost:8088
BOT=functions-check.bot.1782967998794@example.com
PW=test1234
export SUBSET="${SUBSET:-0}"          # 0 = full plan, same semantics in smoke.mjs and check.py
PREEXISTING="${NODE:-}"

python3 gen.py >/dev/null
python3 template.py >/dev/null

# smoke prints exactly one JSON line to stdout ({"file": <node-id>, ...}) even when it fails
SMOKE_STATUS=0
SMOKE_OUT=$(node smoke.mjs) || SMOKE_STATUS=$?
echo "$SMOKE_OUT"
NODE_ID=$(echo "$SMOKE_OUT" | tail -n1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('file',''))" 2>/dev/null || true)

if [ "$SMOKE_STATUS" -ne 0 ]; then
  echo "SMOKE FAILED — node kept for debugging: ${NODE_ID:-<none>}" >&2
  exit 1
fi

if python3 check.py "$NODE_ID"; then
  # PASS — remove our own temp node (unless the caller supplied a pre-existing NODE)
  if [ -z "$PREEXISTING" ] && [ -n "$NODE_ID" ]; then
    JAR=$(mktemp)
    curl -s -c "$JAR" -H 'Content-Type: application/json' \
         -d "{\"email\":\"$BOT\",\"password\":\"$PW\"}" "$BASE/api/auth/login" >/dev/null
    CODE=$(curl -s -b "$JAR" -o /dev/null -w '%{http_code}' -X DELETE "$BASE/api/nodes/$NODE_ID")
    rm -f "$JAR"
    if [ "$CODE" = "204" ]; then echo "PASS — temp node $NODE_ID deleted"
    else echo "WARNING: PASS, but cleanup DELETE /api/nodes/$NODE_ID returned HTTP $CODE — remove it manually" >&2
    fi
  else
    echo "PASS — pre-existing node $NODE_ID kept (NODE= was supplied)"
  fi
  exit 0
else
  echo "CHECK FAILED — node kept for debugging: $NODE_ID" >&2
  exit 1
fi
