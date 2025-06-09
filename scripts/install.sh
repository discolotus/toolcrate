#!/bin/bash
# Script to install toolcrate with a Python virtual environment

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up toolcrate...${NC}"

# Get the absolute path of the current directory
TOOLCRATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check Python version
echo -e "${GREEN}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 || ($PYTHON_MAJOR -eq 3 && "$PYTHON_MINOR" -lt 11) || ($PYTHON_MAJOR -eq 3 && "$PYTHON_MINOR" -gt 12) ]]; then
    echo -e "${RED}Error: toolcrate requires Python 3.11 or 3.12${NC}"
    echo -e "${RED}Current Python version: ${PYTHON_VERSION}${NC}"
    echo -e "${YELLOW}Please install Python 3.11 or 3.12 and try again${NC}"
    exit 1
else
    echo -e "${GREEN}Using Python ${PYTHON_VERSION}${NC}"
fi

# Create Python virtual environment in .venv directory
if [ ! -d ".venv" ]; then
    echo -e "${GREEN}Creating Python virtual environment in .venv...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
else
    echo -e "${GREEN}Virtual environment already exists, activating...${NC}"
    source .venv/bin/activate
fi

# Create src directory if it doesn't exist
mkdir -p src/bin

# Try to initialize git submodules if in a git repository
if [ -d ".git" ]; then
    echo -e "${GREEN}Attempting to set up git submodules...${NC}"
    git submodule update --init --recursive
else
    echo -e "${GREEN}Not a git repository, cloning tools directly...${NC}"
    
    # Handle slsk-batchdl
    if [ ! -d "src/slsk-batchdl" ]; then
        echo -e "${GREEN}Cloning slsk-batchdl...${NC}"
        git clone https://github.com/discolotus/slsk-batchdl.git src/slsk-batchdl
        cd src/slsk-batchdl && git checkout v2.4.6 && cd ../../
    fi

    # Handle Shazam-Tool
    if [ ! -d "src/Shazam-Tool" ]; then
        echo -e "${GREEN}Cloning Shazam-Tool...${NC}"
        git clone https://github.com/discolotus/Shazam-Tool.git src/Shazam-Tool
        cd src/Shazam-Tool && git checkout main && cd ../../
    fi
fi

# Check if we're on macOS ARM64
if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    echo -e "${GREEN}Detected macOS ARM64${NC}"
    
    # Check if dotnet is available
    if command -v dotnet &> /dev/null; then
        echo -e "${GREEN}Building sldl for macOS ARM64...${NC}"
        cd src/slsk-batchdl && dotnet publish -c Release -r osx-arm64 --self-contained -o ../bin/ && cd ../../
        chmod +x src/bin/sldl
    else
        echo -e "${GREEN}dotnet not found, downloading pre-built binary...${NC}"
        curl -L -o src/sldl_osx-arm64.zip https://github.com/discolotus/slsk-batchdl/releases/download/v2.4.6/sldl_osx-arm64.zip
        unzip src/sldl_osx-arm64.zip -d src/bin/
        chmod +x src/bin/sldl
        rm src/sldl_osx-arm64.zip
    fi
fi

# Install required dependencies
echo -e "${GREEN}Installing toolcrate package and dependencies...${NC}"

# Use pip to install in development mode
pip install -e .

# Install Shazam-Tool dependencies
echo -e "${GREEN}Installing Shazam-Tool dependencies...${NC}"
pip install shazamio pydub yt-dlp ShazamApi

echo -e "${GREEN}Setting up global access to toolcrate...${NC}"

# Method 1: Create a wrapper script in ~/.local/bin
WRAPPER_WORKS=false
echo -e "${GREEN}Method 1: Creating wrapper script in ~/.local/bin...${NC}"

if [ ! -d "$HOME/.local/bin" ]; then
    mkdir -p "$HOME/.local/bin"
fi

# Create the entrypoint script
cat > "$HOME/.local/bin/toolcrate" << EOF
#!/bin/bash
# Global entrypoint for toolcrate

# Set the TOOLCRATE_ROOT environment variable to point to the project directory
export TOOLCRATE_ROOT="${TOOLCRATE_DIR}"

# Activate virtual environment and run the command
source "${TOOLCRATE_DIR}/.venv/bin/activate"
"${TOOLCRATE_DIR}/.venv/bin/toolcrate" "\$@"
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
        
        # Source the shell config file to apply changes immediately
        echo -e "${GREEN}Sourcing ${SHELL_CONFIG} to apply PATH changes...${NC}"
        if [[ "$SHELL" == *"zsh"* ]]; then
            source "$SHELL_CONFIG" || echo -e "${YELLOW}Could not source ${SHELL_CONFIG}, you'll need to run 'source ${SHELL_CONFIG}' manually${NC}"
        else
            . "$SHELL_CONFIG" || echo -e "${YELLOW}Could not source ${SHELL_CONFIG}, you'll need to run 'source ${SHELL_CONFIG}' manually${NC}"
        fi
        
        # Verify if PATH update worked
        if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
            echo -e "${GREEN}PATH was successfully updated, ~/.local/bin is now in your PATH${NC}"
            PATH_UPDATED=true
        else
            echo -e "${YELLOW}PATH update did not take effect in the current shell${NC}"
            echo -e "${YELLOW}Please manually run 'source ${SHELL_CONFIG}' to update your PATH${NC}"
        fi
    else
        echo -e "${YELLOW}Could not determine your shell configuration file.${NC}"
        echo -e "${YELLOW}Please manually add ~/.local/bin to your PATH to use toolcrate globally.${NC}"
    fi
else
    echo -e "${GREEN}~/.local/bin is already in your PATH${NC}"
    PATH_UPDATED=true
fi

# Test if the wrapper script works after updating PATH
if [ "$PATH_UPDATED" = true ]; then
    echo -e "${GREEN}Testing if toolcrate wrapper script is accessible...${NC}"
    if command -v toolcrate &> /dev/null; then
        echo -e "${GREEN}✓ Success! Toolcrate is now available globally via the wrapper script${NC}"
        echo -e "${GREEN}You can run 'toolcrate --help' from any directory${NC}"
        WRAPPER_WORKS=true
    else
        echo -e "${YELLOW}⚠ Toolcrate wrapper script is not accessible despite PATH update${NC}"
    fi
fi

# Method 2: Only create a symlink in /usr/local/bin if the wrapper method doesn't work
if [ "$WRAPPER_WORKS" = false ]; then
    echo -e "${GREEN}Method 2: Creating symlink in /usr/local/bin (may require sudo password)...${NC}"
    if [ -d "/usr/local/bin" ]; then
        # Create a wrapper script in the project directory
        mkdir -p "${TOOLCRATE_DIR}/bin"
        cat > "${TOOLCRATE_DIR}/bin/toolcrate_wrapper" << EOF
#!/bin/bash
# Wrapper script for toolcrate

# Set the TOOLCRATE_ROOT environment variable to point to the project directory
export TOOLCRATE_ROOT="${TOOLCRATE_DIR}"

# Activate virtual environment and run the command
source "${TOOLCRATE_DIR}/.venv/bin/activate"
"${TOOLCRATE_DIR}/.venv/bin/toolcrate" "\$@"
EOF
        
        # Make the script executable
        chmod +x "${TOOLCRATE_DIR}/bin/toolcrate_wrapper"
        
        # Create a symlink in /usr/local/bin
        sudo ln -sf "${TOOLCRATE_DIR}/bin/toolcrate_wrapper" /usr/local/bin/toolcrate
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Created symlink in /usr/local/bin/toolcrate${NC}"
            echo -e "${GREEN}You can now use toolcrate from anywhere without needing to activate the virtual environment${NC}"
            
            # Test if the symlink works
            if command -v toolcrate &> /dev/null; then
                echo -e "${GREEN}✓ Success! Toolcrate is now available globally via the symlink${NC}"
            else
                echo -e "${YELLOW}⚠ Toolcrate symlink is not accessible${NC}"
            fi
        else
            echo -e "${YELLOW}Failed to create symlink in /usr/local/bin${NC}"
            echo -e "${YELLOW}You can still use toolcrate via ~/.local/bin/toolcrate once your PATH is updated${NC}"
        fi
    else
        echo -e "${YELLOW}/usr/local/bin does not exist on your system${NC}"
        echo -e "${YELLOW}You can still use toolcrate via ~/.local/bin/toolcrate once your PATH is updated${NC}"
    fi
else
    echo -e "${GREEN}Skipping symlink creation as the wrapper script is working correctly${NC}"
fi

echo -e "${BLUE}Installation complete!${NC}"
echo -e "${GREEN}To activate the virtual environment, run:${NC}"
echo -e "    source .venv/bin/activate"
echo -e "${GREEN}You can now use toolcrate from anywhere by typing:${NC}"
echo -e "    toolcrate --help" 