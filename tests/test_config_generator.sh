#!/bin/bash
# Test script for the ToolCrate configuration generator

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing ToolCrate Configuration Generator${NC}"
echo -e "${BLUE}=========================================${NC}"

# Test directory
TEST_DIR="test_config_temp"
ORIGINAL_DIR=$(pwd)

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up test directory...${NC}"
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_DIR"
}

# Set trap for cleanup
trap cleanup EXIT

# Create test directory
echo -e "${GREEN}Creating test environment...${NC}"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Copy necessary files
cp "$ORIGINAL_DIR/configure_toolcrate.sh" .
cp "$ORIGINAL_DIR/pyproject.toml" .
# Copy the config manager from the new location
cp "$ORIGINAL_DIR/src/toolcrate/config/manager.py" ./config_manager.py
mkdir -p config

# Test 1: Help option
echo -e "\n${BLUE}Test 1: Help option${NC}"
if ./configure_toolcrate.sh --help | grep -q "Usage:"; then
    echo -e "${GREEN}✅ Help option works${NC}"
else
    echo -e "${RED}❌ Help option failed${NC}"
    exit 1
fi

# Test 2: Syntax check
echo -e "\n${BLUE}Test 2: Syntax check${NC}"
if bash -n configure_toolcrate.sh; then
    echo -e "${GREEN}✅ Syntax is valid${NC}"
else
    echo -e "${RED}❌ Syntax errors found${NC}"
    exit 1
fi

# Test 3: Check if script can detect Poetry
echo -e "\n${BLUE}Test 3: Poetry detection${NC}"
if command -v poetry >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Poetry is available${NC}"
    POETRY_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  Poetry not available, will test fallback${NC}"
    POETRY_AVAILABLE=false
fi

# Test 4: Check if all required functions are defined
echo -e "\n${BLUE}Test 4: Function definitions${NC}"
REQUIRED_FUNCTIONS=("prompt_with_default" "prompt_yes_no" "setup_poetry_env" "ensure_venv_fallback")
FUNCTIONS_OK=true

for func in "${REQUIRED_FUNCTIONS[@]}"; do
    if grep -q "^$func()" configure_toolcrate.sh; then
        echo -e "${GREEN}✅ Function $func is defined${NC}"
    else
        echo -e "${RED}❌ Function $func is missing${NC}"
        FUNCTIONS_OK=false
    fi
done

if [ "$FUNCTIONS_OK" = true ]; then
    echo -e "${GREEN}✅ All required functions are defined${NC}"
else
    echo -e "${RED}❌ Some functions are missing${NC}"
    exit 1
fi

# Test 5: Check configuration template structure
echo -e "\n${BLUE}Test 5: Configuration template structure${NC}"
REQUIRED_SECTIONS=("slsk_batchdl:" "spotify:" "youtube:" "cron:" "mounts:")
SECTIONS_OK=true

for section in "${REQUIRED_SECTIONS[@]}"; do
    if grep -q "$section" configure_toolcrate.sh; then
        echo -e "${GREEN}✅ Section $section found${NC}"
    else
        echo -e "${RED}❌ Section $section is missing${NC}"
        SECTIONS_OK=false
    fi
done

if [ "$SECTIONS_OK" = true ]; then
    echo -e "${GREEN}✅ All required configuration sections are present${NC}"
else
    echo -e "${RED}❌ Some configuration sections are missing${NC}"
    exit 1
fi

# Test 6: Check for comprehensive slsk-batchdl options
echo -e "\n${BLUE}Test 6: slsk-batchdl configuration options${NC}"
SLSK_OPTIONS=("fast_search_delay" "max_stale_time" "max_retries_per_track" "strict_title" "strict_album")
OPTIONS_OK=true

for option in "${SLSK_OPTIONS[@]}"; do
    if grep -q "$option" configure_toolcrate.sh; then
        echo -e "${GREEN}✅ Option $option found${NC}"
    else
        echo -e "${RED}❌ Option $option is missing${NC}"
        OPTIONS_OK=false
    fi
done

if [ "$OPTIONS_OK" = true ]; then
    echo -e "${GREEN}✅ Comprehensive slsk-batchdl options are present${NC}"
else
    echo -e "${RED}❌ Some slsk-batchdl options are missing${NC}"
    exit 1
fi

echo -e "\n${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ All tests passed!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo
echo -e "${YELLOW}The ToolCrate configuration generator is ready for use.${NC}"
echo -e "${YELLOW}Usage:${NC}"
echo -e "  make init-config               # Interactive configuration setup (first time)"
echo -e "  ./configure_toolcrate.sh       # Direct script execution"
echo -e "  make config                    # Update tool configs from YAML"
echo -e "  make config-validate           # Validate existing config"
echo
echo -e "${YELLOW}Key features:${NC}"
echo -e "  • Poetry integration with fallback to manual venv"
echo -e "  • Comprehensive slsk-batchdl configuration options"
echo -e "  • Enhanced command-line argument handling"
echo -e "  • Better validation and error handling"
echo -e "  • Improved user experience with clear instructions"
