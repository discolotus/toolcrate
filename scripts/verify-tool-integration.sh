#!/bin/bash
# Script to verify tool integration in ToolCrate (Shazam and slsk-batchdl)

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}ToolCrate Tool Integration Verification${NC}"
echo -e "${BLUE}=======================================${NC}"

# Track overall success
OVERALL_SUCCESS=true

# Function to check and report status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        OVERALL_SUCCESS=false
    fi
}

# 1. Check if we're in the right directory
echo -e "${BLUE}1. Checking project structure...${NC}"
if [ -f "pyproject.toml" ] && [ -d "src/toolcrate" ]; then
    check_status 0 "Project structure verified"
else
    check_status 1 "Not in ToolCrate project root"
    exit 1
fi

# 2. Check git submodules
echo -e "${BLUE}2. Checking git submodules...${NC}"
if [ -f "src/Shazam-Tool/shazam.py" ]; then
    check_status 0 "Shazam-Tool submodule is available"
else
    echo -e "${YELLOW}Shazam-Tool not found, attempting to initialize...${NC}"
    if command -v make &> /dev/null; then
        make setup-submodules &> /dev/null
        if [ -f "src/Shazam-Tool/shazam.py" ]; then
            check_status 0 "Shazam-Tool submodule initialized successfully"
        else
            check_status 1 "Failed to initialize Shazam-Tool submodule"
        fi
    else
        check_status 1 "Make not available and Shazam-Tool not found"
    fi
fi

if [ -f "src/slsk-batchdl/slsk-batchdl.sln" ]; then
    check_status 0 "slsk-batchdl submodule is available"
else
    echo -e "${YELLOW}slsk-batchdl not found, attempting to initialize...${NC}"
    if command -v make &> /dev/null; then
        make setup-submodules &> /dev/null
        if [ -f "src/slsk-batchdl/slsk-batchdl.sln" ]; then
            check_status 0 "slsk-batchdl submodule initialized successfully"
        else
            check_status 1 "Failed to initialize slsk-batchdl submodule"
        fi
    else
        check_status 1 "Make not available and slsk-batchdl not found"
    fi
fi

# 3. Check Python dependencies
echo -e "${BLUE}3. Checking Python dependencies...${NC}"
python3 -c "
import sys
missing_deps = []
optional_deps = []

# Check Shazam dependencies
try:
    import pydub
except ImportError:
    missing_deps.append('pydub')

try:
    import shazamio
except ImportError:
    missing_deps.append('shazamio')

try:
    import yt_dlp
except ImportError:
    missing_deps.append('yt_dlp')

# Check slsk-batchdl dependencies (optional)
try:
    import docker
except ImportError:
    optional_deps.append('docker')

if missing_deps:
    print(f'Missing required dependencies: {missing_deps}')
    sys.exit(1)
else:
    print('All required dependencies available')
    if optional_deps:
        print(f'Optional dependencies missing: {optional_deps}')
    sys.exit(0)
" 2>/dev/null

if [ $? -eq 0 ]; then
    check_status 0 "All required tool dependencies are installed"
else
    echo -e "${YELLOW}Some dependencies missing, attempting to install...${NC}"
    if command -v poetry &> /dev/null && [ -f "pyproject.toml" ]; then
        poetry install --extras all &> /dev/null
        if [ $? -eq 0 ]; then
            check_status 0 "Dependencies installed with Poetry"
        else
            check_status 1 "Failed to install dependencies with Poetry"
        fi
    else
        pip install --user pydub shazamio yt-dlp docker docker-compose &> /dev/null
        if [ $? -eq 0 ]; then
            check_status 0 "Dependencies installed with pip"
        else
            check_status 1 "Failed to install dependencies with pip"
        fi
    fi
fi

# 4. Test Shazam tool import
echo -e "${BLUE}4. Testing Shazam tool import...${NC}"
python3 -c "
import sys
sys.path.insert(0, 'src/Shazam-Tool')
try:
    import shazam
    print('Shazam tool imported successfully')
    sys.exit(0)
except Exception as e:
    print(f'Import failed: {e}')
    sys.exit(1)
" 2>/dev/null

check_status $? "Shazam tool import test"

# 5. Test basic Shazam functionality
echo -e "${BLUE}5. Testing Shazam tool constants...${NC}"
python3 -c "
import sys
sys.path.insert(0, 'src/Shazam-Tool')
try:
    import shazam
    assert hasattr(shazam, 'SEGMENT_LENGTH')
    assert hasattr(shazam, 'DOWNLOADS_DIR')
    assert hasattr(shazam, 'logger')
    assert shazam.SEGMENT_LENGTH == 13 * 1000
    print('All constants verified')
    sys.exit(0)
except Exception as e:
    print(f'Constant verification failed: {e}')
    sys.exit(1)
" 2>/dev/null

check_status $? "Shazam tool constants verification"

# 6. Test Makefile targets
echo -e "${BLUE}6. Testing Makefile targets...${NC}"
if command -v make &> /dev/null; then
    # Test if targets exist
    if make -n setup-submodules &> /dev/null; then
        check_status 0 "Makefile targets are available"
    else
        check_status 1 "Makefile targets not found"
    fi
else
    check_status 1 "Make command not available"
fi

# 7. Test pytest configuration
echo -e "${BLUE}7. Testing pytest configuration...${NC}"
if command -v pytest &> /dev/null; then
    # Run a simple Shazam test
    python3 -m pytest tests/test_shazam_tool.py::TestShazamTool::test_segment_length_constant -v &> /dev/null
    check_status $? "Shazam test execution"

    # Run a simple slsk-batchdl integration test
    python3 -m pytest tests/test_integration.py::TestExternalToolIntegration::test_slsk_tool_integration -v &> /dev/null
    check_status $? "slsk-batchdl integration test execution"
else
    check_status 1 "pytest not available"
fi

# 8. Check ToolCrate CLI integration
echo -e "${BLUE}8. Checking CLI integration...${NC}"
if python3 -c "from src.toolcrate.cli.wrappers import run_shazam; print('CLI wrapper available')" 2>/dev/null; then
    check_status 0 "CLI wrapper function available"
else
    check_status 1 "CLI wrapper function not available"
fi

# 9. Verify installation script enhancements
echo -e "${BLUE}9. Checking installation scripts...${NC}"
if grep -q "setup-submodules" scripts/install.sh && grep -q "shazam" scripts/install.sh && grep -q "slsk" scripts/install.sh; then
    check_status 0 "Installation scripts include tool integration"
else
    check_status 1 "Installation scripts missing tool integration"
fi

# 10. Check Docker availability for slsk-batchdl
echo -e "${BLUE}10. Checking Docker availability...${NC}"
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        check_status 0 "Docker is available and running"
    else
        check_status 1 "Docker is installed but not running"
    fi
else
    check_status 1 "Docker not available (optional for slsk-batchdl)"
fi

# Final summary
echo -e "${BLUE}=========================================${NC}"
if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}🎉 All tool integration checks passed!${NC}"
    echo -e "${GREEN}Both Shazam and slsk-batchdl tools are fully integrated and ready to use.${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "• Run ${YELLOW}'make test-shazam'${NC} to run all Shazam tests"
    echo -e "• Run ${YELLOW}'make test-slsk'${NC} to run all slsk-batchdl tests"
    echo -e "• Use ${YELLOW}'toolcrate shazam-tool --help'${NC} to see Shazam commands"
    echo -e "• Use ${YELLOW}'toolcrate sldl --help'${NC} to see slsk-batchdl commands"
    echo -e "• Try ${YELLOW}'make setup-shazam'${NC} or ${YELLOW}'make setup-slsk'${NC} to ensure everything is set up"
    echo -e "• Build slsk-batchdl binary: ${YELLOW}'make build-slsk'${NC}"
    echo -e "• Build slsk-batchdl Docker image: ${YELLOW}'make docker-slsk'${NC}"
    exit 0
else
    echo -e "${RED}❌ Some integration checks failed.${NC}"
    echo -e "${YELLOW}Please review the errors above and run the suggested fixes.${NC}"
    echo ""
    echo -e "${BLUE}Common fixes:${NC}"
    echo -e "• Run ${YELLOW}'make setup-submodules'${NC} to initialize submodules"
    echo -e "• Run ${YELLOW}'make install-shazam'${NC} to install Shazam dependencies"
    echo -e "• Run ${YELLOW}'make install-slsk'${NC} to install slsk-batchdl dependencies"
    echo -e "• Run ${YELLOW}'make setup-shazam'${NC} for complete Shazam setup"
    echo -e "• Run ${YELLOW}'make setup-slsk'${NC} for complete slsk-batchdl setup"
    exit 1
fi
