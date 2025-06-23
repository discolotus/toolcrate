#!/bin/bash
# Cron wrapper script for ToolCrate
# This script ensures proper environment setup for cron jobs

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_ROOT" || exit 1

# Set up environment variables
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Set up logging
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# Get current timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log the start of execution
echo "[$TIMESTAMP] Starting cron job: $*" >> "$LOG_DIR/cron.log"

# Execute the command and capture output
if "$@" >> "$LOG_DIR/cron.log" 2>&1; then
    echo "[$TIMESTAMP] Cron job completed successfully: $*" >> "$LOG_DIR/cron.log"
    exit 0
else
    EXIT_CODE=$?
    echo "[$TIMESTAMP] Cron job failed with exit code $EXIT_CODE: $*" >> "$LOG_DIR/cron.log"
    exit $EXIT_CODE
fi 