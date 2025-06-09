#!/bin/bash
# Docker Test Runner for ToolCrate
# Provides convenient commands for running tests in Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
BUILD_IMAGE=false
CLEAN_AFTER=false
USE_DIND=false
VERBOSE=false

# Function to show usage
show_usage() {
    echo "Docker Test Runner for ToolCrate"
    echo "================================"
    echo ""
    echo "Usage: $0 [OPTIONS] [TEST_TYPE]"
    echo ""
    echo "TEST_TYPE options:"
    echo "  all          - Run all tests (default)"
    echo "  python       - Run Python tests only"
    echo "  shell        - Run shell tests only"
    echo "  unit         - Run unit tests only"
    echo "  integration  - Run integration tests only"
    echo "  coverage     - Run tests with coverage"
    echo "  docker       - Run Docker-specific tests"
    echo "  quick        - Run quick subset of tests"
    echo ""
    echo "OPTIONS:"
    echo "  -b, --build     - Force rebuild of Docker image"
    echo "  -c, --clean     - Clean up after tests"
    echo "  -d, --dind      - Use Docker-in-Docker (more isolated)"
    echo "  -v, --verbose   - Verbose output"
    echo "  -h, --help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 python            # Run Python tests"
    echo "  $0 -b coverage       # Rebuild image and run coverage tests"
    echo "  $0 -c -d integration # Run integration tests with DinD and cleanup"
}

# Function to log messages
log() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
    fi
}

# Function to log errors
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

# Function to log success
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to log warnings
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--build)
            BUILD_IMAGE=true
            shift
            ;;
        -c|--clean)
            CLEAN_AFTER=true
            shift
            ;;
        -d|--dind)
            USE_DIND=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        all|python|shell|unit|integration|coverage|docker|quick)
            TEST_TYPE="$1"
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo -e "${BLUE}=== ToolCrate Docker Test Runner ===${NC}"
    echo "Test type: $TEST_TYPE"
    echo "Build image: $BUILD_IMAGE"
    echo "Clean after: $CLEAN_AFTER"
    echo "Use DinD: $USE_DIND"
    echo ""

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    # Build image if requested
    if [ "$BUILD_IMAGE" = true ]; then
        log "Building Docker testing image..."
        docker build -f Dockerfile.test -t toolcrate:test .
        success "Docker image built successfully"
    fi

    # Run tests
    log "Starting tests..."
    
    if [ "$USE_DIND" = true ]; then
        log "Using Docker-in-Docker mode"
        docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
    else
        log "Using host Docker socket"
        docker-compose -f docker-compose.test.yml run --rm toolcrate-test /workspace/scripts/test-in-docker.sh "$TEST_TYPE"
    fi

    # Check exit code
    if [ $? -eq 0 ]; then
        success "Tests completed successfully!"
    else
        error "Tests failed!"
        exit 1
    fi

    # Clean up if requested
    if [ "$CLEAN_AFTER" = true ]; then
        log "Cleaning up Docker artifacts..."
        docker-compose -f docker-compose.test.yml down -v --remove-orphans
        success "Cleanup completed"
    fi
}

# Run main function
main
