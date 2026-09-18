#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TMP=$(mktemp -d)
BIN="$TMP/bin"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$BIN"
printf '%s\n' '#!/bin/sh' 'exit 0' > "$BIN/cron"
printf '%s\n' '#!/bin/sh' 'sleep 5' > "$BIN/tail"
chmod 0755 "$BIN/cron" "$BIN/tail"
set +e
timeout 1 env PATH="$BIN:/usr/bin:/bin" DATA_ROOT="$TMP/data" "$ROOT/scheduler-entrypoint.sh" cron -f
rc=$?
set -e
test "$rc" -eq 124
echo 'scheduler cron hold test: PASS'
