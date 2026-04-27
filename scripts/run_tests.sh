#!/bin/bash
# Script to run tests for ToolCrate

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --unit         Run only unit tests"
    echo "  --integration  Run only integration tests"
    echo "  --verbose, -v  Run with verbose output"
    echo "  --coverage     Run with coverage report"
    echo "  --help, -h     Show this help message"
}

UNIT_ONLY=false
INTEGRATION_ONLY=false
VERBOSE=false
COVERAGE=false
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit) UNIT_ONLY=true; shift ;;
        --integration) INTEGRATION_ONLY=true; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        --coverage) COVERAGE=true; shift ;;
        --help|-h) show_usage; exit 0 ;;
        *) PYTEST_ARGS+=("$1"); shift ;;
    esac
done

PYTEST_CMD="uv run pytest"

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

[ "$VERBOSE" = true ] && PYTEST_CMD="$PYTEST_CMD -v"

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/toolcrate --cov-report=html --cov-report=term"
    echo -e "${YELLOW}Coverage report will be generated in htmlcov/...${NC}"
fi

[ ${#PYTEST_ARGS[@]} -gt 0 ] && PYTEST_CMD="$PYTEST_CMD ${PYTEST_ARGS[*]}"

echo -e "${BLUE}Command: $PYTEST_CMD${NC}"
$PYTEST_CMD
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed.${NC}"
fi

exit $exit_code
