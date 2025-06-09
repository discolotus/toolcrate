#!/bin/bash

# ToolCrate Development Setup Script
# This script sets up the development environment for ToolCrate with full tool integration

set -e

echo "🔧 Setting up ToolCrate development environment with full tool integration..."

# Check if Poetry is installed
if ! command -v poetry >/dev/null 2>&1; then
    echo "❌ Poetry is not installed. Please install Poetry first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$PYTHON_VERSION" < "3.9" ]]; then
    echo "❌ Python 3.9+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Check for Make
if ! command -v make >/dev/null 2>&1; then
    echo "❌ Make is not installed. Please install make and try again."
    exit 1
fi

# Initialize git submodules using Makefile
echo "🔗 Setting up git submodules and tools..."
make setup-submodules

# Install dependencies with full tool support
echo "📦 Installing dependencies with full tool support..."
poetry install --with dev --extras all

# Create config directory structure
echo "📁 Creating config directories..."
mkdir -p ~/.config/toolcrate

# Copy example configuration files if they don't exist
if [ ! -f ~/.config/toolcrate/sldl.conf ]; then
    echo "📋 Copying example sldl.conf..."
    cp examples/sldl.conf.example ~/.config/toolcrate/sldl.conf
    echo "⚠️  Please edit ~/.config/toolcrate/sldl.conf with your Soulseek credentials"
fi

if [ ! -f ~/.config/toolcrate/toolcrate.conf ]; then
    echo "📋 Copying example toolcrate.conf..."
    cp examples/toolcrate.conf.example ~/.config/toolcrate/toolcrate.conf
fi

# Verify tool integration
echo "🎵 Verifying Shazam tool integration..."
if [ -f "src/Shazam-Tool/shazam.py" ]; then
    echo "✅ Shazam tool source code is available"
else
    echo "❌ Shazam tool source code not found"
    exit 1
fi

echo "🔧 Verifying slsk-batchdl tool integration..."
if [ -f "src/slsk-batchdl/slsk-batchdl.sln" ]; then
    echo "✅ slsk-batchdl tool source code is available"
else
    echo "❌ slsk-batchdl tool source code not found"
    exit 1
fi

# Test tool dependencies
echo "🔍 Testing tool dependencies..."
poetry run python -c "
import sys
missing_deps = []

# Test Shazam dependencies
try:
    import pydub, shazamio, yt_dlp
    print('✅ Shazam dependencies available')
except ImportError as e:
    missing_deps.append(f'Shazam: {e}')

# Test slsk-batchdl dependencies (optional)
try:
    import docker
    print('✅ Docker Python library available')
except ImportError:
    print('⚠️ Docker Python library not available (optional)')

if missing_deps:
    for dep in missing_deps:
        print(f'❌ Missing: {dep}')
    sys.exit(1)
else:
    print('✅ All required dependencies are available')
"

# Make scripts executable
echo "🔐 Making scripts executable..."
chmod +x scripts/*.sh

# Run tests to verify setup
echo "🧪 Running tests to verify setup..."
poetry run pytest tests/ -v --tb=short

# Run tool-specific tests
echo "🎵 Running Shazam tool tests..."
make test-shazam || echo "⚠️ Some Shazam tests may fail if external services are unavailable"

echo "🔧 Running slsk-batchdl tool tests..."
make test-slsk || echo "⚠️ Some slsk-batchdl tests may fail if Docker is not available"

echo ""
echo "✅ Development environment setup complete with full tool integration!"
echo ""
echo "Next steps:"
echo "1. Edit ~/.config/toolcrate/sldl.conf with your Soulseek credentials"
echo "2. Run 'poetry shell' to activate the virtual environment"
echo "3. Run 'toolcrate --help' to see available commands"
echo "4. Test tools: 'toolcrate shazam-tool --help' and 'toolcrate sldl --help'"
echo ""
echo "Useful commands:"
echo "  make test                   # Run all tests"
echo "  make test-shazam           # Run Shazam tool tests"
echo "  make test-slsk             # Run slsk-batchdl tool tests"
echo "  make setup-shazam          # Re-setup Shazam tool if needed"
echo "  make setup-slsk            # Re-setup slsk-batchdl tool if needed"
echo "  make build-slsk            # Build slsk-batchdl binary from source"
echo "  make docker-slsk           # Build slsk-batchdl Docker image"
echo "  poetry run pytest          # Run tests with Poetry"
echo "  make format                # Format code"
echo "  make lint                  # Lint code"
echo "  ./scripts/run_tests.sh     # Run tests with script"
echo ""
echo "Tool commands:"
echo "  toolcrate shazam-tool download <url>    # Download and analyze audio"
echo "  toolcrate shazam-tool scan              # Process downloaded files"
echo "  toolcrate shazam-tool recognize <file>  # Recognize specific file"
echo "  toolcrate sldl -a 'Artist' -t 'Track'  # Download specific track"
echo "  toolcrate sldl                          # Enter interactive shell"