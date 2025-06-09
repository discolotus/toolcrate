#!/bin/bash
# Script to install toolcrate globally with proper path mapping

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Installing toolcrate globally with proper path mapping...${NC}"

# Get the absolute path of the current directory
TOOLCRATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up submodules first
echo -e "${GREEN}Setting up submodules and tools...${NC}"
if command -v make &> /dev/null; then
    make setup-submodules
else
    # Fallback manual setup
    if [ -d ".git" ]; then
        git submodule update --init --recursive
    else
        mkdir -p src
        if [ ! -d "src/slsk-batchdl" ]; then
            git clone https://github.com/discolotus/slsk-batchdl.git src/slsk-batchdl
            cd src/slsk-batchdl && git checkout v2.4.6 && cd ../..
        fi
        if [ ! -d "src/Shazam-Tool" ]; then
            git clone https://github.com/discolotus/Shazam-Tool.git src/Shazam-Tool
            cd src/Shazam-Tool && git checkout main && cd ../..
        fi
    fi
fi

# Check if Poetry is available
if command -v poetry &> /dev/null; then
    echo -e "${GREEN}Using Poetry for installation...${NC}"

    # Install with Poetry (including all tool extras)
    poetry install --extras all

    # Get the virtual environment path
    VENV_PATH=$(poetry env info --path)
    
    if [ -z "$VENV_PATH" ]; then
        echo -e "${RED}Error: Could not determine Poetry virtual environment path${NC}"
        exit 1
    fi
    
    TOOLCRATE_BINARY="${VENV_PATH}/bin/toolcrate"
    
elif [ -d ".venv" ]; then
    echo -e "${GREEN}Using existing virtual environment...${NC}"
    source .venv/bin/activate
    pip install -e .
    # Install tool dependencies
    pip install shazamio pydub yt-dlp
    pip install docker docker-compose || echo "Note: Docker Python packages are optional"
    TOOLCRATE_BINARY="${TOOLCRATE_DIR}/.venv/bin/toolcrate"

else
    echo -e "${GREEN}Creating new virtual environment...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    # Install tool dependencies
    pip install shazamio pydub yt-dlp
    pip install docker docker-compose || echo "Note: Docker Python packages are optional"
    TOOLCRATE_BINARY="${TOOLCRATE_DIR}/.venv/bin/toolcrate"
fi

# Verify the binary exists
if [ ! -f "$TOOLCRATE_BINARY" ]; then
    echo -e "${RED}Error: toolcrate binary not found at $TOOLCRATE_BINARY${NC}"
    exit 1
fi

echo -e "${GREEN}Setting up global access...${NC}"

# Create ~/.local/bin if it doesn't exist
if [ ! -d "$HOME/.local/bin" ]; then
    mkdir -p "$HOME/.local/bin"
fi

# Create the global wrapper script
cat > "$HOME/.local/bin/toolcrate" << EOF
#!/bin/bash
# Global wrapper for toolcrate with proper path mapping

# Set the TOOLCRATE_ROOT environment variable
export TOOLCRATE_ROOT="${TOOLCRATE_DIR}"

# If using Poetry, activate the Poetry environment
if command -v poetry &> /dev/null && [ -f "${TOOLCRATE_DIR}/pyproject.toml" ]; then
    cd "${TOOLCRATE_DIR}"
    exec poetry run toolcrate "\$@"
else
    # Fallback to direct virtual environment activation
    source "${TOOLCRATE_DIR}/.venv/bin/activate"
    exec "${TOOLCRATE_BINARY}" "\$@"
fi
EOF

# Make the script executable
chmod +x "$HOME/.local/bin/toolcrate"

# Check if ~/.local/bin is in PATH
PATH_UPDATED=false
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}Adding ~/.local/bin to your PATH...${NC}"
    
    # Determine which shell config file to update
    SHELL_CONFIG=""
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [[ "$SHELL" == *"bash"* ]]; then
        SHELL_CONFIG="$HOME/.bashrc"
        # Check for .bash_profile on macOS
        if [[ "$(uname)" == "Darwin" ]] && [[ -f "$HOME/.bash_profile" ]]; then
            SHELL_CONFIG="$HOME/.bash_profile"
        fi
    fi
    
    if [[ -n "$SHELL_CONFIG" ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        echo -e "${YELLOW}Added ~/.local/bin to PATH in $SHELL_CONFIG${NC}"
        echo -e "${YELLOW}Please run 'source $SHELL_CONFIG' or restart your terminal to apply changes${NC}"
        PATH_UPDATED=true
    else
        echo -e "${YELLOW}Could not determine your shell configuration file.${NC}"
        echo -e "${YELLOW}Please manually add ~/.local/bin to your PATH.${NC}"
    fi
else
    echo -e "${GREEN}~/.local/bin is already in your PATH${NC}"
    PATH_UPDATED=true
fi

# Create the default toolcrate directory structure in user's home
TOOLCRATE_HOME="$HOME/.toolcrate"
echo -e "${GREEN}Setting up toolcrate directory structure at $TOOLCRATE_HOME...${NC}"

mkdir -p "$TOOLCRATE_HOME"/{config,data,logs}

# Copy default configuration if it doesn't exist
if [ ! -f "$TOOLCRATE_HOME/config/toolcrate.yaml" ] && [ -f "$TOOLCRATE_DIR/config/toolcrate.yaml" ]; then
    echo -e "${GREEN}Copying default configuration...${NC}"
    cp "$TOOLCRATE_DIR/config/toolcrate.yaml" "$TOOLCRATE_HOME/config/"
    
    # Update paths in the copied config to use the user's home directory
    if command -v sed &> /dev/null; then
        sed -i.bak "s|${TOOLCRATE_DIR}|${TOOLCRATE_HOME}|g" "$TOOLCRATE_HOME/config/toolcrate.yaml"
        rm -f "$TOOLCRATE_HOME/config/toolcrate.yaml.bak"
    fi
fi

# Test the installation
echo -e "${GREEN}Testing installation...${NC}"
if command -v toolcrate &> /dev/null; then
    echo -e "${GREEN}✓ Success! Toolcrate is now available globally${NC}"
    echo -e "${GREEN}Testing toolcrate command...${NC}"
    
    # Test with a simple command
    if toolcrate --version &> /dev/null; then
        echo -e "${GREEN}✓ Toolcrate is working correctly${NC}"
    else
        echo -e "${YELLOW}⚠ Toolcrate command found but may have issues${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Toolcrate command not found in PATH${NC}"
    if [ "$PATH_UPDATED" = true ]; then
        echo -e "${YELLOW}Please restart your terminal or run 'source $SHELL_CONFIG'${NC}"
    fi
fi

echo -e "${BLUE}Installation complete!${NC}"
echo -e "${GREEN}Configuration directory: $TOOLCRATE_HOME/config${NC}"
echo -e "${GREEN}Data directory: $TOOLCRATE_HOME/data${NC}"
echo -e "${GREEN}Logs directory: $TOOLCRATE_HOME/logs${NC}"
echo ""
echo -e "${GREEN}You can now run 'toolcrate --help' from any directory${NC}"
echo -e "${GREEN}The toolcrate command will automatically use the correct paths${NC}"

# Show next steps
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Run 'toolcrate info' to see available tools"
echo -e "2. Edit $TOOLCRATE_HOME/config/toolcrate.yaml to configure your settings"
echo -e "3. Run 'make init-config' from the project directory to set up Docker containers"
