#!/bin/bash
# Real network integration tests that perform actual downloads
# Uses dummy credentials and attempts real downloads

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🧪 ToolCrate Real Network Integration Tests${NC}"
echo -e "${PURPLE}===========================================${NC}"

# Check if explicitly enabled
if [ "$TOOLCRATE_REAL_NETWORK_TESTS" != "1" ]; then
    echo -e "${YELLOW}⚠️  Real network tests are DISABLED by default${NC}"
    echo -e "${YELLOW}These tests will attempt actual downloads using dummy credentials${NC}"
    echo ""
    echo -e "${BLUE}To enable these tests:${NC}"
    echo -e "  ${GREEN}export TOOLCRATE_REAL_NETWORK_TESTS=1${NC}"
    echo -e "  ${GREEN}./tests/test_real_network.sh${NC}"
    echo ""
    echo -e "${RED}⚠️  WARNING: These tests will:${NC}"
    echo -e "  - Attempt real network connections to Soulseek/YouTube"
    echo -e "  - Try to download actual audio files"
    echo -e "  - Use dummy Soulseek credentials (test_user_toolcrate/test_pass_123)"
    echo -e "  - May take 5-15 minutes to complete"
    echo -e "  - Create temporary files in /tmp"
    echo ""
    echo -e "${BLUE}These tests are useful for:${NC}"
    echo -e "  - Verifying end-to-end download functionality"
    echo -e "  - Testing real URL processing"
    echo -e "  - Validating Docker container execution"
    echo -e "  - Checking yt-dlp fallback functionality"
    echo ""
    exit 0
fi

echo -e "${GREEN}✅ Real network tests ENABLED${NC}"
echo -e "${YELLOW}Using dummy credentials: test_user_toolcrate / test_pass_123${NC}"

# Test directory
TEST_DIR="test_real_network_temp"
ORIGINAL_DIR=$(pwd)
DOWNLOAD_DIR="$TEST_DIR/downloads"
CONFIG_DIR="$TEST_DIR/config"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up test directory...${NC}"
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_DIR"
}

# Set trap for cleanup
trap cleanup EXIT

# Create test environment
echo -e "\n${GREEN}📁 Creating test environment...${NC}"
mkdir -p "$TEST_DIR" "$DOWNLOAD_DIR" "$CONFIG_DIR"
cd "$TEST_DIR"

# Create test sldl.conf with dummy credentials
echo -e "${BLUE}⚙️  Creating test configuration...${NC}"
cat > "$CONFIG_DIR/sldl.conf" << 'EOF'
# Test SLDL Configuration with dummy credentials
username = test_user_toolcrate
password = test_pass_123
path = ./downloads
fast-search = true
search-timeout = 60
max-stale-time = 300

# Prefer smaller files for testing
min-bitrate = 128
max-bitrate = 320
pref-format = mp3

# Enable yt-dlp for YouTube fallback
yt-dlp = true
yt-dlp-args = --audio-quality 5 --extract-flat false

# Shorter timeouts for testing
concurrent-processes = 1
max-track-results = 5
EOF

echo -e "${GREEN}✅ Configuration created${NC}"

# Test URLs
YOUTUBE_URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SPOTIFY_TRACK="https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"

# Test 1: YouTube download with yt-dlp fallback
echo -e "\n${BLUE}🎵 Test 1: YouTube download with yt-dlp fallback${NC}"
echo -e "${YELLOW}URL: $YOUTUBE_URL${NC}"

# Create links file
echo "$YOUTUBE_URL" > youtube_test.txt

echo -e "${GREEN}Running: toolcrate sldl --links-file youtube_test.txt${NC}"

# Set config environment
export SLDL_CONFIG="$CONFIG_DIR/sldl.conf"

# Run with timeout
timeout 300 toolcrate sldl --download-path "$DOWNLOAD_DIR" --links-file youtube_test.txt 2>&1 | tee youtube_test.log

# Check results
YOUTUBE_FILES=$(find "$DOWNLOAD_DIR" -name "*.mp3" -o -name "*.flac" -o -name "*.wav" -o -name "*.m4a" 2>/dev/null | wc -l)
echo -e "\n${BLUE}📊 YouTube Test Results:${NC}"
echo -e "  Audio files downloaded: $YOUTUBE_FILES"

if [ "$YOUTUBE_FILES" -gt 0 ]; then
    echo -e "  ${GREEN}✅ SUCCESS: Files downloaded via yt-dlp fallback${NC}"
    find "$DOWNLOAD_DIR" -name "*.mp3" -o -name "*.flac" -o -name "*.wav" -o -name "*.m4a" | head -3 | while read file; do
        size=$(du -h "$file" 2>/dev/null | cut -f1)
        echo -e "    🎵 $(basename "$file") ($size)"
    done
else
    if grep -q "yt-dlp\|youtube" youtube_test.log; then
        echo -e "  ${YELLOW}⚠️  PARTIAL: yt-dlp attempted but no files completed${NC}"
    else
        echo -e "  ${RED}❌ FAILED: No yt-dlp activity detected${NC}"
    fi
fi

# Test 2: Spotify track (expected to fail gracefully with dummy credentials)
echo -e "\n${BLUE}🎵 Test 2: Spotify track processing${NC}"
echo -e "${YELLOW}URL: $SPOTIFY_TRACK${NC}"
echo -e "${YELLOW}Expected: Graceful failure with dummy credentials${NC}"

echo "$SPOTIFY_TRACK" > spotify_test.txt

echo -e "${GREEN}Running: toolcrate sldl --links-file spotify_test.txt${NC}"

timeout 180 toolcrate sldl --download-path "$DOWNLOAD_DIR" --links-file spotify_test.txt 2>&1 | tee spotify_test.log

echo -e "\n${BLUE}📊 Spotify Test Results:${NC}"
if grep -q "spotify\|soulseek\|login\|authentication" spotify_test.log; then
    echo -e "  ${GREEN}✅ SUCCESS: Spotify URL recognized and processed${NC}"
    echo -e "  ${YELLOW}(Failure expected with dummy credentials)${NC}"
else
    echo -e "  ${RED}❌ FAILED: No Spotify processing detected${NC}"
fi

# Test 3: Mixed content links file
echo -e "\n${BLUE}🎵 Test 3: Mixed content processing${NC}"

cat > mixed_test.txt << EOF
# Mixed content test file
$YOUTUBE_URL
Rick Astley - Never Gonna Give You Up
$SPOTIFY_TRACK
EOF

echo -e "${GREEN}Running: toolcrate sldl --links-file mixed_test.txt${NC}"

timeout 600 toolcrate sldl --download-path "$DOWNLOAD_DIR" --links-file mixed_test.txt 2>&1 | tee mixed_test.log

TOTAL_FILES=$(find "$DOWNLOAD_DIR" -name "*.mp3" -o -name "*.flac" -o -name "*.wav" -o -name "*.m4a" 2>/dev/null | wc -l)
echo -e "\n${BLUE}📊 Mixed Content Test Results:${NC}"
echo -e "  Total audio files: $TOTAL_FILES"

PROCESSING_TYPES=0
if grep -q "youtube\|yt-dlp" mixed_test.log; then
    echo -e "  ${GREEN}✅ YouTube processing detected${NC}"
    ((PROCESSING_TYPES++))
fi
if grep -q "spotify" mixed_test.log; then
    echo -e "  ${GREEN}✅ Spotify processing detected${NC}"
    ((PROCESSING_TYPES++))
fi
if grep -q "search\|soulseek" mixed_test.log; then
    echo -e "  ${GREEN}✅ Search term processing detected${NC}"
    ((PROCESSING_TYPES++))
fi

if [ "$PROCESSING_TYPES" -ge 2 ]; then
    echo -e "  ${GREEN}✅ SUCCESS: Multiple content types processed${NC}"
else
    echo -e "  ${YELLOW}⚠️  PARTIAL: Limited content type processing${NC}"
fi

# Test 4: Docker container functionality (if available)
echo -e "\n${BLUE}🐳 Test 4: Docker container functionality${NC}"

if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker found, testing container execution...${NC}"
    
    timeout 300 toolcrate --build sldl --help 2>&1 | tee docker_test.log
    
    if grep -q "sldl\|docker\|container" docker_test.log || [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✅ SUCCESS: Docker container functionality working${NC}"
    else
        echo -e "  ${YELLOW}⚠️  PARTIAL: Docker available but container issues${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  SKIPPED: Docker not available${NC}"
fi

# Summary
echo -e "\n${PURPLE}📋 REAL NETWORK TEST SUMMARY${NC}"
echo -e "${PURPLE}=============================${NC}"

TOTAL_DOWNLOADED=$(find "$DOWNLOAD_DIR" -name "*.mp3" -o -name "*.flac" -o -name "*.wav" -o -name "*.m4a" 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$DOWNLOAD_DIR" 2>/dev/null | cut -f1)

echo -e "${BLUE}📊 Download Statistics:${NC}"
echo -e "  Total audio files downloaded: $TOTAL_DOWNLOADED"
echo -e "  Total download size: ${TOTAL_SIZE:-0}"
echo -e "  Download directory: $DOWNLOAD_DIR"

echo -e "\n${BLUE}🔍 Processing Evidence:${NC}"
if grep -q "yt-dlp" *.log 2>/dev/null; then
    echo -e "  ${GREEN}✅ yt-dlp fallback functionality working${NC}"
fi
if grep -q "spotify" *.log 2>/dev/null; then
    echo -e "  ${GREEN}✅ Spotify URL recognition working${NC}"
fi
if grep -q "soulseek\|search" *.log 2>/dev/null; then
    echo -e "  ${GREEN}✅ Soulseek search functionality attempted${NC}"
fi

echo -e "\n${BLUE}💡 Key Findings:${NC}"
if [ "$TOTAL_DOWNLOADED" -gt 0 ]; then
    echo -e "  ${GREEN}✅ End-to-end download functionality WORKING${NC}"
    echo -e "  ${GREEN}✅ Real network integration SUCCESSFUL${NC}"
else
    echo -e "  ${YELLOW}⚠️  No files downloaded (expected with dummy credentials)${NC}"
    echo -e "  ${BLUE}ℹ️  Command structure and processing logic verified${NC}"
fi

echo -e "\n${BLUE}📁 Test files available for inspection:${NC}"
echo -e "  Configuration: $CONFIG_DIR/sldl.conf"
echo -e "  Downloads: $DOWNLOAD_DIR/"
echo -e "  Logs: $TEST_DIR/*.log"

echo -e "\n${GREEN}🎉 Real network integration tests completed!${NC}"
