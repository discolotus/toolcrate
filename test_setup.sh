#!/bin/bash
# Test script for the setup.sh script

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing ToolCrate Setup Script${NC}"
echo -e "${BLUE}==============================${NC}"

# Create a temporary test directory
TEST_DIR="/tmp/toolcrate_test_$(date +%s)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo -e "${GREEN}Created test directory: $TEST_DIR${NC}"

# Create a virtual environment for testing
echo -e "${GREEN}Creating test virtual environment...${NC}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Copy the setup script
cp "$OLDPWD/setup.sh" .
cp "$OLDPWD/config_manager.py" .

# Create test input file
cat > test_input.txt << 'EOF'
test-project
info
/tmp/toolcrate_test_data
/tmp/toolcrate_test_logs
testuser
testpass
/tmp/toolcrate_test_data/downloads
/tmp/toolcrate_test_data/music
flac,mp3
320
2500
48000
2
6000
49998
y
y
y
n
test_client_id
test_client_secret
test_youtube_key
y
0 2 * * *
https://open.spotify.com/playlist/test
/tmp/toolcrate_test_data
/tmp/toolcrate_test_config
EOF

echo -e "${GREEN}Running setup script with test input...${NC}"

# Run the setup script with test input
if ./setup.sh < test_input.txt; then
    echo -e "${GREEN}✅ Setup script completed successfully!${NC}"
else
    echo -e "${RED}❌ Setup script failed!${NC}"
    exit 1
fi

# Verify created files
echo -e "\n${GREEN}Verifying created files...${NC}"

expected_files=(
    "config/toolcrate.yaml"
    "config/sldl.conf"
    "config/docker-compose.yml"
    "config/.env"
    "config/validate-config.py"
    "config/README.md"
    "config/crontabs/toolcrate"
)

all_files_exist=true
for file in "${expected_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file${NC}"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = true ]; then
    echo -e "\n${GREEN}✅ All expected files were created!${NC}"
else
    echo -e "\n${RED}❌ Some files are missing!${NC}"
    exit 1
fi

# Test configuration validation
echo -e "\n${GREEN}Testing configuration validation...${NC}"
if [ -n "$VIRTUAL_ENV" ] && command -v python &> /dev/null; then
    cd config
    if python validate-config.py toolcrate.yaml; then
        echo -e "${GREEN}✅ Configuration validation passed!${NC}"
    else
        echo -e "${RED}❌ Configuration validation failed!${NC}"
        exit 1
    fi
    cd ..
else
    echo -e "${RED}❌ Virtual environment not active or Python not found!${NC}"
    exit 1
fi

# Test config manager (should be using virtual environment)
echo -e "\n${GREEN}Testing config manager...${NC}"
if [ -n "$VIRTUAL_ENV" ] && command -v python &> /dev/null; then
    echo -e "${GREEN}Using virtual environment: $VIRTUAL_ENV${NC}"

    if python config_manager.py --config config/toolcrate.yaml validate; then
        echo -e "${GREEN}✅ Config manager validation passed!${NC}"
    else
        echo -e "${RED}❌ Config manager validation failed!${NC}"
        exit 1
    fi

    # Test sldl.conf generation
    if python config_manager.py --config config/toolcrate.yaml generate-sldl; then
        echo -e "${GREEN}✅ sldl.conf generation passed!${NC}"
    else
        echo -e "${RED}❌ sldl.conf generation failed!${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Virtual environment not active or Python not found!${NC}"
    exit 1
fi

# Show sample configuration content
echo -e "\n${GREEN}Sample configuration content:${NC}"
echo -e "${BLUE}--- toolcrate.yaml (first 20 lines) ---${NC}"
head -20 config/toolcrate.yaml

echo -e "\n${BLUE}--- sldl.conf (first 15 lines) ---${NC}"
head -15 config/sldl.conf

echo -e "\n${BLUE}--- cron job ---${NC}"
cat config/crontabs/toolcrate

# Cleanup
echo -e "\n${GREEN}Cleaning up test directory...${NC}"
cd "$OLDPWD"
rm -rf "$TEST_DIR"

echo -e "\n${GREEN}✅ All tests passed! Setup script is working correctly.${NC}"
echo -e "${BLUE}The setup script creates a comprehensive YAML-based configuration${NC}"
echo -e "${BLUE}with all the requested features:${NC}"
echo -e "  📄 YAML configuration format"
echo -e "  🔧 Complete slsk-batchdl settings coverage"
echo -e "  ⏰ Cron job configuration"
echo -e "  📁 Mount location settings"
echo -e "  🐳 Docker deployment support"
echo -e "  ✅ Configuration validation"
echo -e "  🔄 Automatic sldl.conf generation"
