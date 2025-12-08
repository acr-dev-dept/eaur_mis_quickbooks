# Load .env file
echo "Loading .env file..."
if [ -f /home/eaur/eaur_mis_quickbooks/.env ]; then
    export $(grep -v '^#' /home/eaur/eaur_mis_quickbooks/.env | xargs)
    echo ".env file loaded."
else
    echo ".env file not found!"
fi

# Create logs directory if it doesn't exist
LOG_DIR="/home/eaur/eaur_mis_quickbooks/logs"
mkdir -p "$LOG_DIR"

# Change to project directory to ensure proper imports
cd /home/eaur/eaur_mis_quickbooks

# Restart services
echo "Restarting services..."

echo "Checking and stopping existing Celery processes..."

# Kill Celery worker if running
if pgrep -f "celery worker" > /dev/null; then
    pkill -f "celery worker"
    echo "✅ Celery worker stopped."
else
    echo "⚠️ No running Celery worker found."
fi

# Kill Celery beat if running
if pgrep -f "celery beat" > /dev/null; then
    pkill -f "celery beat"
    echo "✅ Celery beat stopped."
else
    echo "⚠️ No running Celery beat found."
fi

# Kill any Celery process
if pgrep -f "celery" > /dev/null; then
    pkill -f "celery"
    echo "✅ Other Celery processes stopped."
else
    echo "⚠️ No other running Celery processes found."
fi

echo "Starting Celery worker..."
nohup celery -A application.config_files.celery worker --loglevel=info > "$LOG_DIR/celery_worker.log" 2>&1 &
sleep 2
if pgrep -f "celery worker" > /dev/null; then
    echo "✅ Celery worker started successfully."
else
    echo "❌ Failed to start Celery worker."
    echo "Check logs at: $LOG_DIR/celery_worker.log"
fi

echo "Starting Celery beat..."
nohup celery -A application.config_files.celery beat --scheduler redbeat.RedBeatScheduler --loglevel=info > "$LOG_DIR/celery_beat.log" 2>&1 &
sleep 2
if pgrep -f "celery beat" > /dev/null; then
    echo "✅ Celery beat started successfully."
else
    echo "❌ Failed to start Celery beat."
    echo "Check logs at: $LOG_DIR/celery_beat.log"
fi

echo "Checking and restarting Gunicorn..."
if pgrep -f "gunicorn" > /dev/null; then
    pkill -f "gunicorn"
    echo "✅ Gunicorn stopped."
else
    echo "⚠️ No running Gunicorn process found."
fi

nohup gunicorn -b 0.0.0.0:9000 -w 2 app:app > "$LOG_DIR/gunicorn.log" 2>&1 &
sleep 2
if pgrep -f "gunicorn" > /dev/null; then
    echo "✅ Gunicorn started successfully."
else
    echo "❌ Failed to start Gunicorn."
    echo "Check logs at: $LOG_DIR/gunicorn.log"
fi

echo "✅ All services restarted successfully."
echo "Logs are available in: $LOG_DIR/"