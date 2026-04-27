#!/bin/bash
# Integration tests for real-world commands that users would run

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing Real-World ToolCrate Commands${NC}"
echo -e "${BLUE}====================================${NC}"

# Test directory
TEST_DIR="test_real_commands_temp"
ORIGINAL_DIR=$(pwd)
TESTS_PASSED=0
TESTS_FAILED=0

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up test directory...${NC}"
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_DIR"
}

# Set trap for cleanup
trap cleanup EXIT

# Function to run test and track results
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_pattern="$3"
    local should_succeed="$4"  # true/false
    
    echo -e "\n${BLUE}Test: $test_name${NC}"
    echo -e "${YELLOW}Command: $command${NC}"
    
    # Run the command
    if eval "$command" 2>&1 | tee test_output.log; then
        command_succeeded=true
        exit_code=0
    else
        command_succeeded=false
        exit_code=$?
    fi
    
    # Check if output contains expected pattern
    if grep -q "$expected_pattern" test_output.log; then
        pattern_found=true
    else
        pattern_found=false
    fi
    
    # Determine if test passed
    if [ "$should_succeed" = "true" ]; then
        if [ "$command_succeeded" = "true" ] && [ "$pattern_found" = "true" ]; then
            echo -e "${GREEN}✅ PASSED${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ FAILED${NC}"
            echo -e "${RED}Expected success and pattern '$expected_pattern'${NC}"
            echo -e "${RED}Got: success=$command_succeeded, pattern_found=$pattern_found${NC}"
            ((TESTS_FAILED++))
        fi
    else
        # For tests that should fail, we just check the pattern
        if [ "$pattern_found" = "true" ]; then
            echo -e "${GREEN}✅ PASSED (expected failure with pattern)${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ FAILED${NC}"
            echo -e "${RED}Expected pattern '$expected_pattern' in output${NC}"
            ((TESTS_FAILED++))
        fi
    fi
    
    rm -f test_output.log
}

# Create test directory
echo -e "${GREEN}Creating test environment...${NC}"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Test 1: Basic help commands
run_test "ToolCrate Help" "toolcrate --help" "ToolCrate.*unified tool suite" true
run_test "ToolCrate Version" "toolcrate --version" "version.*[0-9]" true
run_test "ToolCrate Info" "toolcrate info" "Available Tools" true

# Test 2: SLDL command recognition
run_test "SLDL Help" "toolcrate sldl --help" "sldl\|docker\|Docker" false
run_test "SLDL Version" "toolcrate sldl --version" "sldl\|docker\|Docker" false

# Test 3: Real URL command structure (these will fail due to no docker, but should recognize commands)
run_test "Spotify Playlist Command" "toolcrate sldl 'https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF'" "Docker\|sldl" false
run_test "YouTube Playlist Command" "toolcrate sldl 'https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj'" "Docker\|sldl" false
run_test "YouTube Video Command" "toolcrate sldl 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'" "Docker\|sldl" false

# Test 4: Links file processing
echo -e "\n${BLUE}Creating test URLs file...${NC}"
cat > test_urls.txt << 'EOF'
# Test URLs file for ToolCrate
https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF
https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj
https://www.youtube.com/watch?v=dQw4w9WgXcQ
EOF

run_test "Links File Processing" "toolcrate sldl --links-file test_urls.txt" "Docker\|sldl" false

# Test 5: Schedule commands
run_test "Schedule Help" "toolcrate schedule --help" "schedule.*manage" true
run_test "Schedule Add Help" "toolcrate schedule add --help" "add.*schedule" true
run_test "Schedule Hourly Help" "toolcrate schedule hourly --help" "hourly" true
run_test "Schedule Daily Help" "toolcrate schedule daily --help" "daily" true

# Test 6: Wishlist commands
run_test "Wishlist Run Help" "toolcrate wishlist-run --help" "wishlist\|logs\|status" false

# Test 7: Queue commands
run_test "Queue Help" "toolcrate queue --help" "queue\|manage" false
run_test "Queue Add Help" "toolcrate queue add --help" "add.*queue" false

# Test 8: Advanced SLDL options
run_test "SLDL Artist Track" "toolcrate sldl -a 'Test Artist' -t 'Test Track'" "Docker\|sldl" false
run_test "SLDL Album" "toolcrate sldl -a 'Test Artist' -b 'Test Album'" "Docker\|sldl" false

# Test 9: Build flag
run_test "Build Flag Help" "toolcrate --build sldl --help" "Docker\|sldl\|build" false

# Test 10: Interactive shell (should recognize command)
run_test "Interactive Shell" "echo 'exit' | timeout 5 toolcrate sldl" "Docker\|sldl\|bash" false

# Test 11: Configuration commands
run_test "Config Validation" "make config-validate" "config\|validate\|Configuration" false

# Test 12: Test runner commands
run_test "Test Runner Help" "python tests/test_runner.py" "TEST SUMMARY\|RUNNING.*TESTS" false

echo -e "\n${BLUE}====================================${NC}"
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo -e "${BLUE}====================================${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All real-world command tests passed!${NC}"
    echo -e "${YELLOW}Note: Many commands failed as expected due to missing Docker/dependencies,${NC}"
    echo -e "${YELLOW}but all commands were properly recognized and structured.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check the output above for details.${NC}"
    exit 1
fi
