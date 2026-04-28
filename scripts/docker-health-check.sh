#!/bin/bash
# Enhanced health check script for ToolCrate Docker containers
# Provides detailed health status and diagnostics

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Health check functions
check_python_import() {
    echo "🐍 Checking Python import..."
    if python3 -c "import toolcrate; print('✅ ToolCrate module imported successfully')" 2>/dev/null; then
        return 0
    else
        echo "❌ Failed to import ToolCrate module"
        return 1
    fi
}

check_cli_availability() {
    echo "🔧 Checking CLI availability..."
    if command -v toolcrate >/dev/null 2>&1; then
        echo "✅ ToolCrate CLI is available"
        return 0
    else
        echo "❌ ToolCrate CLI not found in PATH"
        return 1
    fi
}

check_dependencies() {
    echo "📦 Checking critical dependencies..."
    local deps=("click" "pydantic" "loguru" "yaml" "requests")  # pyyaml imports as 'yaml'
    local failed=0

    for dep in "${deps[@]}"; do
        if python3 -c "import $dep" 2>/dev/null; then
            echo "  ✅ $dep"
        else
            echo "  ❌ $dep"
            failed=1
        fi
    done

    return $failed
}

check_directories() {
    echo "📁 Checking required directories..."
    local dirs=("/app/data" "/app/logs" "/app/config")
    local failed=0
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            echo "  ✅ $dir exists"
        else
            echo "  ❌ $dir missing"
            failed=1
        fi
    done
    
    return $failed
}

check_permissions() {
    echo "🔐 Checking file permissions..."
    local user=$(whoami)
    
    if [ -w "/app/data" ] && [ -w "/app/logs" ]; then
        echo "✅ Write permissions OK for user: $user"
        return 0
    else
        echo "❌ Insufficient write permissions for user: $user"
        return 1
    fi
}

# Main health check
main() {
    echo -e "${GREEN}🏥 ToolCrate Health Check${NC}"
    echo "================================"
    
    local exit_code=0
    
    # Run all checks
    check_python_import || exit_code=1
    check_cli_availability || exit_code=1
    check_dependencies || exit_code=1
    check_directories || exit_code=1
    check_permissions || exit_code=1
    
    echo "================================"
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}🎉 All health checks passed!${NC}"
    else
        echo -e "${RED}❌ Some health checks failed!${NC}"
    fi
    
    return $exit_code
}

# Run health check
main "$@"
