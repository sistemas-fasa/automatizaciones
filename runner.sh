#!/usr/bin/env bash
set -Eeuo pipefail

: "${JOB_NAME:?JOB_NAME es obligatorio}"
: "${JOB_COMMAND:?JOB_COMMAND es obligatorio}"

timeout_seconds="${JOB_TIMEOUT_SECONDS:-1800}"
lock_file="${JOB_LOCK_FILE:-/data/locks/${JOB_NAME}.lock}"

mkdir -p "$(dirname "${lock_file}")"
exec flock --nonblock "${lock_file}" \
  timeout --signal=TERM --kill-after=30 "${timeout_seconds}" \
  bash -lc "${JOB_COMMAND}"
