#!/bin/bash

LOG_DIR="logs"
LOG_FILE="$LOG_DIR/gunicorn.log"

mkdir -p "$LOG_DIR"

echo "----------------------------------------" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Deployment script started" >> "$LOG_FILE"

if pgrep -x gunicorn > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Gunicorn is running. Stopping it..." >> "$LOG_FILE"
    pkill -x gunicorn
    sleep 2
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Gunicorn stopped." >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Gunicorn is not running." >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting Gunicorn..." >> "$LOG_FILE"

gunicorn app:app \
    -w 2 \
    -k gevent \
    --worker-connections 20000 \
    -b 0.0.0.0:9000 \
    --access-logfile "$LOG_FILE" \
    --error-logfile "$LOG_FILE" \
    --daemon

echo "$(date '+%Y-%m-%d %H:%M:%S') - Gunicorn start command issued" >> "$LOG_FILE"
