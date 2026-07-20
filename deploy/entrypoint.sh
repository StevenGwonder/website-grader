#!/bin/bash
set -e

# Start nginx in foreground
nginx -g "daemon off;" &

# Start gunicorn (Flask app)
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile - \
    app:app
