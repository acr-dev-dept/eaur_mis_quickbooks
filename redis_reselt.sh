#!/usr/bin/env bash
set -euo pipefail

########################################
# CONFIGURATION (ADJUST AS NEEDED)
########################################

APP_NAME="application.config_files.celery_app.celery"                   # Celery app name (e.g. app, main, wsgi)
CELERY_SERVICE="celery"               # systemd service name
REDIS_SERVICE="redis-server"          # redis or redis-server
REDIS_DB="0"                          # Redis DB index used by Celery
REDIS_CLI="/usr/bin/redis-cli"
CELERY_BIN="/home/eaur/eaur_mis_quickbooks/venv/bin/celery"

########################################
# UTILITY FUNCTIONS
########################################

log() {
  echo "[`date '+%Y-%m-%d %H:%M:%S'`] $1"
}

require_root() {
  if [[ "$EUID" -ne 0 ]]; then
    log "ERROR: This script must be run as root."
    exit 1
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

########################################
# PRE-FLIGHT CHECKS
########################################

require_root

for cmd in "$REDIS_CLI" "$CELERY_BIN" systemctl; do
  if ! command_exists "$cmd"; then
    log "ERROR: Required command not found: $cmd"
    exit 1
  fi
done

########################################
# EXECUTION
########################################

log "Starting Redis + Celery reset procedure"

log "Stopping Celery service..."
systemctl stop "$CELERY_SERVICE"

log "Purging pending Celery tasks..."
$CELERY_BIN -A "$APP_NAME" purge -f || log "WARNING: Celery purge failed (may already be empty)"

log "Selecting Redis DB $REDIS_DB..."
$REDIS_CLI SELECT "$REDIS_DB" >/dev/null

log "Flushing Redis DB asynchronously..."
$REDIS_CLI FLUSHDB ASYNC

log "Restarting Redis service..."
systemctl restart "$REDIS_SERVICE"

log "Waiting for Redis to become ready..."
sleep 3

log "Restarting Celery service..."
systemctl start "$CELERY_SERVICE"

########################################
# POST-CHECKS
########################################

log "Validating Redis connectivity..."
$REDIS_CLI PING | grep -q PONG || {
  log "ERROR: Redis did not respond correctly"
  exit 1
}

log "Validating Celery worker status..."
$CELERY_BIN -A "$APP_NAME" inspect ping >/dev/null || {
  log "WARNING: Celery workers may not be fully ready yet"
}

log "Redis + Celery reset completed successfully"
exit 0
