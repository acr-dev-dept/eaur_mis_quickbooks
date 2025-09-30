#!/bin/bash
# run_celery_prod_async.sh
# Production-ready Celery setup for EAUR MIS-QuickBooks Integration with async task execution

# === CONFIGURATION ===
APP_MODULE="application.tasks.scheduled_tasks.celery"
LOG_DIR="/home/eaur/eaur_mis_quickbooks/logs"
PID_DIR="$LOG_DIR/pids"
FLASK_ENV=${FLASK_ENV:-production}
CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}
FLOWER_PORT=${FLOWER_PORT:-5555}

# Number of concurrent greenlets (adjust depending on load)
ASYNC_CONCURRENCY=${ASYNC_CONCURRENCY:-50}

# === CREATE LOG AND PID DIRECTORIES ===
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# === FUNCTION TO KILL EXISTING PROCESSES ===
kill_existing() {
    if [ -f "$PID_DIR/$1.pid" ]; then
        PID=$(cat "$PID_DIR/$1.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping $1 (PID: $PID)..."
            kill -9 $PID
        fi
        rm -f "$PID_DIR/$1.pid"
    fi
}

# Stop any running Celery worker, beat, or Flower
kill_existing "celery_worker"
kill_existing "flower"

# === ACTIVATE VIRTUAL ENVIRONMENT ===
source /home/eaur/eaur_mis_quickbooks/venv/bin/activate

# === START CELERY WORKER + BEAT WITH GEVENT POOL ===
echo "Starting Celery worker + beat (async with gevent)..."
celery -A $APP_MODULE worker \
    --beat \
    --loglevel=info \
    --logfile="$LOG_DIR/celery_worker.log" \
    --pidfile="$PID_DIR/celery_worker.pid" \
    --pool=gevent \
    --concurrency=$ASYNC_CONCURRENCY &

sleep 5

# === START FLOWER MONITORING ===
echo "Starting Flower..."
celery -A $APP_MODULE flower \
    --port=$FLOWER_PORT \
    --loglevel=info \
    --pidfile="$PID_DIR/flower.pid" \
    --logfile="$LOG_DIR/flower.log" &

echo "✅ Celery worker + beat started (async mode)."
echo "✅ Flower monitoring started at http://localhost:$FLOWER_PORT"
