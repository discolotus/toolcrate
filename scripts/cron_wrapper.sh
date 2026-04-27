#!/bin/bash

# Set up logging
LOG_DIR="/tmp/toolcrate"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cron.log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log "Error: Docker is not running"
        return 1
    fi
    return 0
}

# Function to check if sldl container is running
check_sldl_container() {
    if ! docker ps | grep -q "sldl"; then
        log "Error: sldl container is not running"
        return 1
    fi
    return 0
}

# Set up environment
export PATH="/usr/local/bin:$PATH"
export TOOLCRATE_SKIP_VENV_CHECK=1

# Change to project directory
cd /Users/tleo/code/toolcrate || {
    log "Error: Could not change to project directory"
    exit 1
}

# Activate virtual environment if using Poetry
if command -v poetry >/dev/null 2>&1; then
    eval "$(poetry env use python)"
    eval "$(poetry env info --path)/bin/activate"
else
    # Try to activate standard venv if it exists
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
fi

# Check Docker and container status
if ! check_docker; then
    log "Docker check failed"
    exit 1
fi

if ! check_sldl_container; then
    log "sldl container check failed"
    exit 1
fi

# Execute the command passed as argument
log "Executing: $*"
"$@" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "Command completed successfully"
else
    log "Command failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE 