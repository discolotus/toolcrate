#!/bin/bash
# ToolCrate Development Setup Script

set -e

echo "Setting up ToolCrate development environment..."

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Install dependencies
echo "Installing dependencies..."
uv sync

# Initialize git submodules
echo "Initializing git submodules..."
git submodule update --init --recursive

# Create config directory structure
echo "Creating config directories..."
mkdir -p ~/.config/toolcrate

# Copy example configuration files if they don't exist
if [ ! -f ~/.config/toolcrate/sldl.conf ]; then
    echo "Copying example sldl.conf..."
    cp examples/sldl.conf.example ~/.config/toolcrate/sldl.conf
    echo "Please edit ~/.config/toolcrate/sldl.conf with your Soulseek credentials"
fi

if [ ! -f ~/.config/toolcrate/toolcrate.conf ]; then
    echo "Copying example toolcrate.conf..."
    cp examples/toolcrate.conf.example ~/.config/toolcrate/toolcrate.conf
fi

# Make scripts executable
chmod +x scripts/*.sh

# Run tests to verify setup
echo "Running tests to verify setup..."
uv run pytest tests/ -v --tb=short

echo ""
echo "Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit ~/.config/toolcrate/sldl.conf with your Soulseek credentials"
echo "2. Run 'uv run toolcrate --help' to see available commands"
echo ""
echo "Useful commands:"
echo "  uv run pytest              # Run tests"
echo "  uv run ruff format src/    # Format code"
echo "  uv run mypy src/           # Type checking"
echo "  make test                  # Run all tests via Makefile"
