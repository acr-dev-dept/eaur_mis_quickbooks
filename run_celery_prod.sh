#!/bin/bash
# run_celery_prod_async.sh
# Production-ready Celery setup for EAUR MIS-QuickBooks Integration
# Async tasks with gevent + standalone Beat + Flower

# === CONFIGURATION ===
APP_MODULE="application.tasks.scheduled_tasks.celery"
LOG_DIR="/home/eaur/eaur_mis_quickbooks/logs"
PID_DIR="$LOG_DIR/pids"
FLASK_ENV=${FLASK_ENV:-production}
CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}
FLOWER_PORT=${FLOWER_PORT:-5555}

# Number of concurrent greenlets for async tasks
ASYNC_CONCURRENCY=${ASYNC_CONCURRENCY:-20}

# Redis configuration
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_DB=${REDIS_DB:-0}

# === CREATE LOG AND PID DIRECTORIES ===
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# === FUNCTION TO KILL EXISTING PROCESSES ===
kill_existing() {
    if [ -f "$PID_DIR/$1.pid" ]; then
        PID=$(cat "$PID_DIR/$1.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping $1 (PID: $PID)..."
            kill -TERM $PID 2>/dev/null
            sleep 2
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                echo "Force stopping $1..."
                kill -9 $PID 2>/dev/null
            fi
        fi
        rm -f "$PID_DIR/$1.pid"
    fi
}

# === KILL ALL CELERY PROCESSES ===
echo "=== Stopping all existing Celery processes ==="

# Kill processes using PID files
kill_existing "celery_worker"
kill_existing "celery_beat"
kill_existing "flower"

# Kill any remaining celery processes by name
echo "Checking for remaining Celery processes..."
pkill -9 -f "celery.*worker" 2>/dev/null
pkill -9 -f "celery.*beat" 2>/dev/null
pkill -9 -f "celery.*flower" 2>/dev/null

# Wait for processes to fully terminate
sleep 3

# Verify all processes are stopped
if pgrep -f "celery" > /dev/null; then
    echo "⚠️  Warning: Some Celery processes are still running"
    pgrep -af "celery"
else
    echo "✅ All Celery processes stopped successfully"
fi

# === CLEAR REDIS ===
echo "=== Clearing Redis cache ==="

# Check if redis-cli is available
if command -v redis-cli &> /dev/null; then
    # Clear the specific database
    redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB FLUSHDB
    
    if [ $? -eq 0 ]; then
        echo "✅ Redis database $REDIS_DB cleared successfully"
    else
        echo "⚠️  Failed to clear Redis database"
    fi
    
    # Optional: Clear all Redis databases (uncomment if needed)
    # redis-cli -h $REDIS_HOST -p $REDIS_PORT FLUSHALL
    
    # Verify Redis connection
    redis-cli -h $REDIS_HOST -p $REDIS_PORT PING > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Redis connection verified"
    else
        echo "❌ Redis connection failed"
        exit 1
    fi
else
    echo "⚠️  redis-cli not found. Skipping Redis cleanup."
    echo "   Install with: sudo apt-get install redis-tools"
fi

# === ACTIVATE VIRTUAL ENVIRONMENT ===
echo "=== Activating virtual environment ==="
if [ -f "/home/eaur/eaur_mis_quickbooks/venv/bin/activate" ]; then
    source /home/eaur/eaur_mis_quickbooks/venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found"
    exit 1
fi

# === START CELERY WORKER (async with gevent) ===
echo "=== Starting Celery worker (async with gevent) ==="
celery -A $APP_MODULE worker \
    --pool=gevent \
    --concurrency=$ASYNC_CONCURRENCY \
    --loglevel=info \
    --logfile="$LOG_DIR/celery_worker.log" \
    --pidfile="$PID_DIR/celery_worker.pid" \
    --detach

sleep 5

# Verify worker started
if [ -f "$PID_DIR/celery_worker.pid" ]; then
    WORKER_PID=$(cat "$PID_DIR/celery_worker.pid")
    if ps -p $WORKER_PID > /dev/null 2>&1; then
        echo "✅ Celery worker started successfully (PID: $WORKER_PID)"
    else
        echo "❌ Celery worker failed to start"
        exit 1
    fi
else
    echo "❌ Celery worker PID file not created"
    exit 1
fi

# === START STANDALONE CELERY BEAT ===
echo "=== Starting standalone Celery Beat ==="
celery -A $APP_MODULE beat \
    --loglevel=info \
    --logfile="$LOG_DIR/celery_beat.log" \
    --pidfile="$PID_DIR/celery_beat.pid" \
    --detach

sleep 5

# Verify beat started
if [ -f "$PID_DIR/celery_beat.pid" ]; then
    BEAT_PID=$(cat "$PID_DIR/celery_beat.pid")
    if ps -p $BEAT_PID > /dev/null 2>&1; then
        echo "✅ Celery Beat started successfully (PID: $BEAT_PID)"
    else
        echo "❌ Celery Beat failed to start"
        exit 1
    fi
else
    echo "❌ Celery Beat PID file not created"
    exit 1
fi

# === START FLOWER MONITORING ===
echo "=== Starting Flower ==="
celery -A $APP_MODULE flower \
    --port=$FLOWER_PORT \
    --loglevel=info \
    --pidfile="$PID_DIR/flower.pid" \
    --logfile="$LOG_DIR/flower.log" \
    --detach

sleep 3

# Verify flower started
if [ -f "$PID_DIR/flower.pid" ]; then
    FLOWER_PID=$(cat "$PID_DIR/flower.pid")
    if ps -p $FLOWER_PID > /dev/null 2>&1; then
        echo "✅ Flower started successfully (PID: $FLOWER_PID)"
    else
        echo "⚠️  Flower may have failed to start"
    fi
else
    echo "⚠️  Flower PID file not created"
fi

# === SUMMARY ===
echo ""
echo "============================================"
echo "🚀 CELERY SERVICES STARTED SUCCESSFULLY"
echo "============================================"
echo "Worker:  Running (async mode with $ASYNC_CONCURRENCY greenlets)"
echo "Beat:    Running (standalone scheduler)"
echo "Flower:  Running at http://localhost:$FLOWER_PORT"
echo "Logs:    $LOG_DIR"
echo "PIDs:    $PID_DIR"
echo "============================================"
echo ""
echo "To view logs in real-time:"
echo "  Worker: tail -f $LOG_DIR/celery_worker.log"
echo "  Beat:   tail -f $LOG_DIR/celery_beat.log"
echo "  Flower: tail -f $LOG_DIR/flower.log"
echo ""
echo "To stop all services:"
echo "  pkill -f 'celery'"
echo "============================================"