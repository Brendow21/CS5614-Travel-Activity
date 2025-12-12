#!/bin/sh
# Increase file descriptors
ulimit -n 1048576

# Start Gunicorn with 1 worker
exec gunicorn --workers 1 --bind 0.0.0.0:8000 travel_activity.wsgi:application
