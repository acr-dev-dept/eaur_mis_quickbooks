#!/usr/bin/env bash
# kill_celery_flower.sh
# Stops Flower and Celery workers (graceful TERM, then SIGKILL if needed).
# Usage: ./kill_celery_flower.sh

set -u

# seconds to wait after TERM before sending KILL
GRACE_PERIOD=8

info() { printf '%s\n' "$*"; }

# helper: send TERM then wait then KILL
stop_procs() {
  local pattern="$1"
  local nice_name="$2"

  # find PIDs (pgrep -f uses full commandline, supports regexp)
  local pids
  pids=$(pgrep -f -- "${pattern}" || true)

  if [ -z "$pids" ]; then
    info "No ${nice_name} processes found (pattern: ${pattern})."
    return 0
  fi

  info "Found ${nice_name} PIDs: ${pids}"
  info "Sending TERM to ${nice_name}..."
  # send TERM
  echo "${pids}" | xargs -r kill -TERM

  # wait up to GRACE_PERIOD seconds for them to exit
  local waited=0
  while [ $waited -lt $GRACE_PERIOD ]; do
    sleep 1
    waited=$((waited + 1))
    # re-check
    local still
    still=$(pgrep -f -- "${pattern}" || true)
    if [ -z "$still" ]; then
      info "${nice_name} stopped cleanly."
      return 0
    fi
    info "Waiting... (${waited}/${GRACE_PERIOD})"
  done

  # if still alive, force kill
  local remaining
  remaining=$(pgrep -f -- "${pattern}" || true)
  if [ -n "$remaining" ]; then
    info "Forcing KILL on ${nice_name} PIDs: ${remaining}"
    echo "${remaining}" | xargs -r kill -9
    sleep 1
    if pgrep -f -- "${pattern}" > /dev/null; then
      info "Warning: some ${nice_name} processes still present after SIGKILL."
    else
      info "${nice_name} killed."
    fi
  fi
}

# Stop Flower first (common port 5555, but match process name too)
stop_procs 'flower' 'Flower'

# Stop celery workers (match celery worker/beat/process)
stop_procs 'celery' 'Celery workers'

info "Done."
