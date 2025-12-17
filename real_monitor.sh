#!/bin/bash

LOG_FILE="/logs/gunicorn.log"
LINES=100

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file does not exist -> $LOG_FILE"
    exit 1
fi

echo "Showing last $LINES lines of $LOG_FILE"
echo "----------------------------------------"

# Show last 100 lines
tail -n "$LINES" "$LOG_FILE"

echo ""
echo "Streaming new log entries (Ctrl+C to stop)"
echo "----------------------------------------"

# Follow log in real time
tail -n 0 -f "$LOG_FILE"
