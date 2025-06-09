#!/bin/bash
# ToolCrate Installation Script
# This script installs ToolCrate and its dependencies

set -e

echo "🚀 Installing ToolCrate..."

# Check if Poetry is available
if command -v poetry >/dev/null 2>&1; then
    echo "✅ Poetry found, installing with Poetry..."
    poetry install --only=main
    echo "✅ ToolCrate installed successfully with Poetry!"
else
    echo "📦 Poetry not found, installing with pip..."
    pip install -e .
    echo "✅ ToolCrate installed successfully with pip!"
fi

echo ""
echo "🎉 Installation complete!"
echo "💡 You can now use 'toolcrate --help' to get started."
