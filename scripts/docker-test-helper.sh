#!/bin/bash
# Docker Test Helper Script
# Automatically chooses between registry image and local build

set -e

REGISTRY_IMAGE="ghcr.io/discolotus/toolcrate/toolcrate-test"
LOCAL_IMAGE="toolcrate:test"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}ToolCrate Docker Test Helper${NC}"
echo -e "${BLUE}===========================${NC}"

# Function to check if image exists
check_image_exists() {
    local image=$1
    if docker image inspect "$image" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to check if registry image is available
check_registry_available() {
    local image=$1
    if docker manifest inspect "$image" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to pull registry image
pull_registry_image() {
    local tag=${1:-latest}
    local image="$REGISTRY_IMAGE:$tag"
    
    echo -e "${BLUE}Pulling registry image: $image${NC}"
    if docker pull "$image"; then
        echo -e "${GREEN}✅ Successfully pulled registry image${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Failed to pull registry image${NC}"
        return 1
    fi
}

# Function to build local image
build_local_image() {
    echo -e "${BLUE}Building local Docker image...${NC}"
    if docker build -f Dockerfile.test -t "$LOCAL_IMAGE" .; then
        echo -e "${GREEN}✅ Successfully built local image${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to build local image${NC}"
        return 1
    fi
}

# Function to run tests with specified image
run_tests() {
    local image=$1
    local test_type=${2:-all}
    
    echo -e "${BLUE}Running tests with image: $image${NC}"
    echo -e "${BLUE}Test type: $test_type${NC}"
    
    docker run --rm \
        --privileged \
        -v "$(pwd):/workspace" \
        -w /workspace \
        "$image" \
        /workspace/scripts/test-in-docker.sh "$test_type"
}

# Main logic
main() {
    local test_type=${1:-all}
    local force_build=${2:-false}
    local selected_image=""
    
    if [ "$force_build" = "true" ]; then
        echo -e "${YELLOW}Forcing local build...${NC}"
        if build_local_image; then
            selected_image="$LOCAL_IMAGE"
        else
            echo -e "${RED}❌ Local build failed${NC}"
            exit 1
        fi
    else
        # Try registry image first
        echo -e "${BLUE}Checking for registry image...${NC}"
        
        # Try different tags in order of preference
        for tag in "latest" "main" "augment-feature-dev"; do
            local registry_image="$REGISTRY_IMAGE:$tag"
            echo -e "${BLUE}Trying $registry_image...${NC}"
            
            if check_registry_available "$registry_image"; then
                echo -e "${GREEN}✅ Registry image available: $registry_image${NC}"
                if pull_registry_image "$tag"; then
                    selected_image="$registry_image"
                    break
                fi
            fi
        done
        
        # If no registry image worked, try local image
        if [ -z "$selected_image" ]; then
            echo -e "${YELLOW}No registry image available, checking local image...${NC}"
            
            if check_image_exists "$LOCAL_IMAGE"; then
                echo -e "${GREEN}✅ Local image found${NC}"
                selected_image="$LOCAL_IMAGE"
            else
                echo -e "${YELLOW}No local image found, building...${NC}"
                if build_local_image; then
                    selected_image="$LOCAL_IMAGE"
                else
                    echo -e "${RED}❌ Failed to build local image${NC}"
                    exit 1
                fi
            fi
        fi
    fi
    
    # Run tests with selected image
    echo -e "${GREEN}Using image: $selected_image${NC}"
    run_tests "$selected_image" "$test_type"
}

# Help function
show_help() {
    echo "Usage: $0 [TEST_TYPE] [--force-build]"
    echo ""
    echo "TEST_TYPE options:"
    echo "  all         - Run all tests (default)"
    echo "  python      - Run Python tests only"
    echo "  shell       - Run shell tests only"
    echo "  unit        - Run unit tests only"
    echo "  integration - Run integration tests only"
    echo "  coverage    - Run tests with coverage"
    echo "  docker      - Run Docker-specific tests"
    echo "  quick       - Run quick subset of tests"
    echo ""
    echo "Options:"
    echo "  --force-build  - Force local build instead of using registry image"
    echo "  --help, -h     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests with best available image"
    echo "  $0 python            # Run Python tests"
    echo "  $0 unit --force-build # Run unit tests with local build"
}

# Parse arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

test_type="all"
force_build="false"

for arg in "$@"; do
    case $arg in
        --force-build)
            force_build="true"
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        all|python|shell|unit|integration|coverage|docker|quick)
            test_type="$arg"
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main "$test_type" "$force_build"
