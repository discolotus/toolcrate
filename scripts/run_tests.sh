#!/bin/bash
# Script to run tests for ToolCrate

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the absolute path to the repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --unit         Run only unit tests"
    echo "  --integration  Run only integration tests"
    echo "  --verbose, -v  Run with verbose output"
    echo "  --coverage     Run with coverage report"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 --unit            # Run only unit tests"
    echo "  $0 --integration -v   # Run integration tests with verbose output"
    echo "  $0 --coverage         # Run tests with coverage report"
}

# Parse command line arguments
UNIT_ONLY=false
INTEGRATION_ONLY=false
VERBOSE=false
COVERAGE=false
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            UNIT_ONLY=true
            shift
            ;;
        --integration)
            INTEGRATION_ONLY=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Check if Poetry is available
if command -v poetry >/dev/null 2>&1; then
    echo -e "${BLUE}Using Poetry to run tests...${NC}"
    RUNNER="poetry run"
elif [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
    echo -e "${BLUE}Using virtual environment...${NC}"
    source "$REPO_ROOT/.venv/bin/activate"
    RUNNER=""
else
    echo -e "${RED}Error: Neither Poetry nor virtual environment found.${NC}"
    echo "Please run 'poetry install' or set up a virtual environment."
    exit 1
fi

# Build pytest command
PYTEST_CMD="pytest"

# Add test path based on options
if [ "$UNIT_ONLY" = true ]; then
    PYTEST_CMD="$PYTEST_CMD tests/unit/"
    echo -e "${GREEN}Running unit tests only...${NC}"
elif [ "$INTEGRATION_ONLY" = true ]; then
    PYTEST_CMD="$PYTEST_CMD tests/integration/"
    echo -e "${GREEN}Running integration tests only...${NC}"
else
    PYTEST_CMD="$PYTEST_CMD tests/"
    echo -e "${GREEN}Running all tests...${NC}"
fi

# Add verbose flag if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/toolcrate --cov-report=html --cov-report=term"
    echo -e "${YELLOW}Coverage report will be generated in htmlcov/...${NC}"
fi

# Add any additional pytest arguments
if [ ${#PYTEST_ARGS[@]} -gt 0 ]; then
    PYTEST_CMD="$PYTEST_CMD ${PYTEST_ARGS[*]}"
fi

# Run the tests
echo -e "${BLUE}Command: $RUNNER $PYTEST_CMD${NC}"
$RUNNER $PYTEST_CMD

# Store the exit code
exit_code=$?

# Deactivate virtual environment if we activated it
if [ -n "$VIRTUAL_ENV" ] && [ -z "$POETRY_ACTIVE" ]; then
    deactivate
fi

# Show results
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed.${NC}"
fi

# Exit with the test runner's exit code
exit $exit_code 