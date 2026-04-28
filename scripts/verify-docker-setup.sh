#!/bin/bash
# Verify Docker Testing Setup for ToolCrate
# This script checks if the Docker testing environment is properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Function to log errors
error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

# Function to log success
success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Function to log warnings
warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

echo -e "${BLUE}=== ToolCrate Docker Testing Setup Verification ===${NC}"
echo ""

# Check if Docker is installed and running
log "Checking Docker installation..."
if ! command -v docker >/dev/null 2>&1; then
    error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    error "Docker is not running. Please start Docker and try again."
    exit 1
fi

success "Docker is installed and running"

# Check Docker Compose
log "Checking Docker Compose..."
if ! docker compose version >/dev/null 2>&1; then
    warning "Docker Compose plugin not found, trying docker-compose..."
    if ! command -v docker-compose >/dev/null 2>&1; then
        error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
fi

success "Docker Compose is available"

# Check required files
log "Checking required files..."
required_files=(
    "Dockerfile.test"
    "docker-compose.test.yml"
    "scripts/test-in-docker.sh"
    "scripts/docker-test-runner.sh"
    ".dockerignore"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    error "Missing required files:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    exit 1
fi

success "All required files are present"

# Check script permissions
log "Checking script permissions..."
scripts=(
    "scripts/test-in-docker.sh"
    "scripts/docker-test-runner.sh"
    "scripts/verify-docker-setup.sh"
)

for script in "${scripts[@]}"; do
    if [ -f "$script" ] && [ ! -x "$script" ]; then
        warning "$script is not executable, fixing..."
        chmod +x "$script"
    fi
done

success "Script permissions are correct"

# Test Docker connectivity
log "Testing Docker Hub connectivity..."
if docker pull hello-world >/dev/null 2>&1; then
    success "Docker Hub connectivity is working"
    docker rmi hello-world >/dev/null 2>&1 || true
else
    warning "Docker Hub connectivity issues detected. You may need to:"
    echo "  - Check your internet connection"
    echo "  - Configure Docker proxy settings"
    echo "  - Login to Docker Hub: docker login"
fi

# Check available resources
log "Checking system resources..."
available_space=$(df -h . | awk 'NR==2 {print $4}')
log "Available disk space: $available_space"

if command -v free >/dev/null 2>&1; then
    available_memory=$(free -h | awk 'NR==2{printf "%.1fG", $7/1024}')
    log "Available memory: $available_memory"
fi

# Test basic Docker functionality
log "Testing basic Docker functionality..."
if docker run --rm hello-world >/dev/null 2>&1; then
    success "Basic Docker functionality works"
else
    error "Basic Docker functionality test failed"
    exit 1
fi

# Check if we can build the test image
log "Testing Docker image build (this may take a while)..."
if docker build -f Dockerfile.test -t toolcrate:test-verify . >/dev/null 2>&1; then
    success "Docker test image builds successfully"
    
    # Test running the container
    log "Testing container execution..."
    if docker run --rm toolcrate:test-verify python -c "import toolcrate; print('ToolCrate import successful')" >/dev/null 2>&1; then
        success "Container execution test passed"
    else
        warning "Container execution test failed - ToolCrate may not be properly installed"
    fi
    
    # Clean up test image
    docker rmi toolcrate:test-verify >/dev/null 2>&1 || true
else
    warning "Docker test image build failed. This may be due to:"
    echo "  - Network connectivity issues"
    echo "  - Missing dependencies"
    echo "  - Insufficient disk space"
    echo ""
    echo "You can still use the testing environment when connectivity is restored."
fi

echo ""
echo -e "${GREEN}=== Verification Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Build the testing image: make test-docker-build"
echo "2. Run all tests: make test-docker"
echo "3. Run specific tests: make test-docker-run TEST=python"
echo "4. Open interactive shell: make test-docker-shell"
echo ""
echo "For more information, see: docs/DOCKER_TESTING.md"
