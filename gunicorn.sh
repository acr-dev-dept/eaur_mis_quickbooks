if pgrep -f gunicorn > /dev/null; then
    echo "Gunicorn is running. Stopping it..."
    pkill -f gunicorn
    echo "Gunicorn stopped."
else
    echo "Gunicorn is not running."
fi

echo "Starting Gunicorn..."

gunicorn app:app -w 2 -k gevent --worker-connections 20000 -b 0.0.0.0:9000 --daemon
echo "Gunicorn started."