#!/bin/bash
set -e

echo "=== ToolCrate Docker Testing Environment ==="
echo "Python version: $(python3 --version)"
echo "Poetry version: $(poetry --version)"
echo "Docker version: $(docker --version)"

# Start cron service for testing cron-related functionality
echo "Starting cron service..."
service cron start
if service cron status >/dev/null 2>&1; then
    echo "✅ Cron service is running"
else
    echo "⚠️  Cron service failed to start"
fi
echo ""

# Check if Docker is accessible
echo "Checking Docker availability..."
if docker info >/dev/null 2>&1; then
    echo "Docker is ready!"
else
    echo "Warning: Docker not accessible, some tests may fail"
fi
echo ""

# Ensure Poetry environment is properly set up
echo "Setting up Poetry environment..."
poetry install --with dev
echo "Poetry environment ready!"

# Verify toolcrate command is available
echo "Verifying toolcrate installation..."
if command -v toolcrate >/dev/null 2>&1; then
    echo "✅ toolcrate command is available globally"
    toolcrate --version 2>/dev/null || echo "toolcrate command found but version check failed"
else
    echo "⚠️  toolcrate command not found globally, will use 'poetry run toolcrate'"
fi

# Verify crontab is available
echo "Verifying crontab availability..."
if command -v crontab >/dev/null 2>&1; then
    echo "✅ crontab command is available"
    # Test crontab functionality
    crontab -l >/dev/null 2>&1 || echo "  (no existing crontab entries)"
else
    echo "⚠️  crontab command not found"
fi
echo ""

# Run the requested test command
case "${1:-all}" in
    "all")
        echo "Running all tests..."
        poetry run python3 tests/test_runner_unified.py all
        ;;
    "python")
        echo "Running Python tests..."
        poetry run pytest tests/ -v
        ;;
    "shell")
        echo "Running shell tests..."
        poetry run python3 tests/test_runner_unified.py shell
        ;;
    "unit")
        echo "Running unit tests..."
        poetry run pytest tests/ -v -m "not integration"
        ;;
    "integration")
        echo "Running integration tests..."
        poetry run pytest tests/test_integration.py -v
        ;;
    "coverage")
        echo "Running tests with coverage..."
        poetry run pytest tests/ --cov=src/toolcrate --cov-report=term-missing --cov-report=html
        ;;
    "docker")
        echo "Running Docker-specific tests..."
        poetry run pytest tests/test_sldl_docker.py tests/test_integration.py -v
        ;;
    "quick")
        echo "Running quick tests..."
        poetry run pytest tests/test_package.py tests/test_main_cli.py -v
        ;;
    *)
        echo "Usage: $0 [all|python|shell|unit|integration|coverage|docker|quick]"
        exit 1
        ;;
esac
