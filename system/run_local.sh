#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Add the current directory to the python path
export PYTHONPATH=$PYTHONPATH:.

# --- Configuration ---
LOG_DIR="logs"
CELERY_WORKER_LOG="$LOG_DIR/celery_worker.log"
FLOWER_LOG="$LOG_DIR/flower.log"
DJANGO_LOG="$LOG_DIR/django.log"

# --- Functions ---
start_redis() {
    echo "--- Starting Redis ---"
    if ! sudo service redis-server status > /dev/null 2>&1; then
        sudo service redis-server start
        echo "Redis server started."
    else
        echo "Redis server is already running."
    fi
}

install_dependencies() {
    echo "--- Installing Python dependencies ---"
    sudo python3.8 -m pip install -r requirements.txt
    echo "--- Dependencies installed ---"
}

run_migrations() {
    echo "--- Running Django database migrations ---"
    python3.8 photonix/manage.py migrate
    echo "--- Migrations complete ---"
}

start_services() {
    echo "--- Starting background services ---"
    mkdir -p $LOG_DIR

    # Start Celery Worker
    echo "Starting Celery worker, logging to $CELERY_WORKER_LOG"
    nohup python3.8 -m celery -A photonix worker -l info > "$CELERY_WORKER_LOG" 2>&1 &
    CELERY_PID=$!
    echo "Celery worker started with PID $CELERY_PID"

    # Start Flower
    echo "Starting Flower, logging to $FLOWER_LOG"
    nohup python3.8 -m celery -A photonix flower --listen-address=0.0.0.0 --port=5555 > "$FLOWER_LOG" 2>&1 &
    FLOWER_PID=$!
    echo "Flower started with PID $FLOWER_PID"

    # Start Django Dev Server
    echo "Starting Django development server, logging to $DJANGO_LOG"
    nohup python3.8 photonix/manage.py runserver 0.0.0.0:8000 > "$DJANGO_LOG" 2>&1 &
    DJANGO_PID=$!
    echo "Django server started with PID $DJANGO_PID"

    echo "--- All services started ---"
    echo "View logs in the '$LOG_DIR' directory."
    echo "To see running processes, run: ps aux | grep python3.8"
    echo "To stop all services, run: kill $CELERY_PID $FLOWER_PID $DJANGO_PID"
}


# --- Main Execution ---
start_redis
install_dependencies
run_migrations
start_services

echo "--- Setup complete. Application is running. ---"
