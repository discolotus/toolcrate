#!/bin/bash

# ToolCrate Development Setup Script
# This script sets up the development environment for ToolCrate

set -e

echo "🔧 Setting up ToolCrate development environment..."

# Check if Poetry is installed
if ! command -v poetry >/dev/null 2>&1; then
    echo "❌ Poetry is not installed. Please install Poetry first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$PYTHON_VERSION" < "3.8" ]]; then
    echo "❌ Python 3.8+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Install dependencies
echo "📦 Installing dependencies..."
poetry install

# Initialize git submodules
echo "🔗 Initializing git submodules..."
git submodule update --init --recursive

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

# Make scripts executable
echo "🔐 Making scripts executable..."
chmod +x scripts/*.sh

# Run tests to verify setup
echo "🧪 Running tests to verify setup..."
poetry run pytest tests/ -v --tb=short

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit ~/.config/toolcrate/sldl.conf with your Soulseek credentials"
echo "2. Run 'poetry shell' to activate the virtual environment"
echo "3. Run 'toolcrate --help' to see available commands"
echo ""
echo "Useful commands:"
echo "  poetry run pytest          # Run tests"
echo "  poetry run black src/      # Format code"
echo "  poetry run mypy src/       # Type checking"
echo "  ./scripts/run_tests.sh     # Run tests with script" 