#!/bin/bash
# Script to run tests for toolcrate with the virtual environment activated

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "${SCRIPT_DIR}/.venv/bin/activate"

# Check if pytest is installed
if ! pip show pytest > /dev/null 2>&1; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    pip install pytest
fi

echo -e "${GREEN}Running tests...${NC}"

# Use pytest if available, fall back to our custom test runner
if [ "$1" == "--pytest" ] || [ "$2" == "--pytest" ] || [ "$3" == "--pytest" ]; then
    # Remove the --pytest flag
    args=("$@")
    new_args=()
    for arg in "${args[@]}"; do
        if [ "$arg" != "--pytest" ]; then
            new_args+=("$arg")
        fi
    done
    
    # Run pytest with any remaining arguments
    echo -e "${GREEN}Running tests with pytest...${NC}"
    python -m pytest "${new_args[@]}"
else
    # Run our custom test runner with all arguments
    echo -e "${GREEN}Running tests with custom runner...${NC}"
    python -m tests.run_tests "$@"
fi

# Store the exit code
exit_code=$?

# Deactivate the virtual environment
deactivate

# Exit with the test runner's exit code
exit $exit_code 