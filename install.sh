#!/bin/bash
# ToolCrate installation script (uv-based)

set -e

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Installing ToolCrate...${NC}"

# Get the absolute path of the current directory
TOOLCRATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv is required but was not found.${NC}"
    echo -e "${YELLOW}Install it from https://docs.astral.sh/uv/getting-started/installation/ and re-run this script.${NC}"
    exit 1
fi

# Create src directory if it doesn't exist
mkdir -p src/bin

# Initialize git submodules if in a git repository
if [ -d ".git" ]; then
    echo -e "${GREEN}Setting up git submodules...${NC}"
    git submodule update --init --recursive
else
    echo -e "${GREEN}Not a git repository, cloning tools directly...${NC}"

    if [ ! -d "src/slsk-batchdl" ]; then
        echo -e "${GREEN}Cloning slsk-batchdl...${NC}"
        git clone https://github.com/discolotus/slsk-batchdl.git src/slsk-batchdl
    fi

    if [ ! -d "src/Shazam-Tool" ]; then
        echo -e "${GREEN}Cloning Shazam-Tool...${NC}"
        git clone https://github.com/discolotus/Shazam-Tool.git src/Shazam-Tool
    fi
fi

# Build sldl on macOS ARM64 if dotnet is present
if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    echo -e "${GREEN}Detected macOS ARM64${NC}"

    if command -v dotnet &> /dev/null; then
        echo -e "${GREEN}Building sldl for macOS ARM64...${NC}"
        (cd src/slsk-batchdl && dotnet publish -c Release -r osx-arm64 --self-contained -o ../bin/)
        chmod +x src/bin/sldl
    else
        echo -e "${YELLOW}dotnet not found; skipping native sldl build. Docker image will be used at runtime.${NC}"
    fi
fi

# Install the project with uv
echo -e "${GREEN}Installing toolcrate package and dependencies with uv...${NC}"
uv sync --extra shazam

echo -e "${GREEN}Setting up global access to toolcrate...${NC}"

# Create a wrapper script in ~/.local/bin
WRAPPER_WORKS=false
mkdir -p "$HOME/.local/bin"

cat > "$HOME/.local/bin/toolcrate" << EOF
#!/bin/bash
# Global entrypoint for toolcrate
exec uv run --project "${TOOLCRATE_DIR}" --extra shazam toolcrate "\$@"
EOF
chmod +x "$HOME/.local/bin/toolcrate"

PATH_UPDATED=false
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}Adding ~/.local/bin to your PATH...${NC}"

    SHELL_CONFIG=""
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [[ "$SHELL" == *"bash"* ]]; then
        SHELL_CONFIG="$HOME/.bashrc"
        if [[ "$(uname)" == "Darwin" ]] && [[ -f "$HOME/.bash_profile" ]]; then
            SHELL_CONFIG="$HOME/.bash_profile"
        fi
    fi

    if [[ -n "$SHELL_CONFIG" ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        echo -e "${YELLOW}Added ~/.local/bin to PATH in $SHELL_CONFIG${NC}"
        echo -e "${YELLOW}Run 'source ${SHELL_CONFIG}' (or open a new shell) to apply.${NC}"
        PATH_UPDATED=true
    else
        echo -e "${YELLOW}Could not determine your shell configuration file.${NC}"
        echo -e "${YELLOW}Add ~/.local/bin to your PATH manually to use toolcrate globally.${NC}"
    fi
else
    echo -e "${GREEN}~/.local/bin is already in your PATH${NC}"
    PATH_UPDATED=true
fi

if [ "$PATH_UPDATED" = true ] && command -v toolcrate &> /dev/null; then
    echo -e "${GREEN}✓ toolcrate is available globally${NC}"
    WRAPPER_WORKS=true
fi

# Fall back to /usr/local/bin symlink if the user wrapper isn't picked up
if [ "$WRAPPER_WORKS" = false ] && [ -d "/usr/local/bin" ]; then
    echo -e "${GREEN}Creating fallback symlink in /usr/local/bin (may require sudo)...${NC}"
    mkdir -p "${TOOLCRATE_DIR}/scripts"
    cat > "${TOOLCRATE_DIR}/scripts/toolcrate_wrapper" << EOF
#!/bin/bash
# Wrapper script for toolcrate
exec uv run --project "${TOOLCRATE_DIR}" --extra shazam toolcrate "\$@"
EOF
    chmod +x "${TOOLCRATE_DIR}/scripts/toolcrate_wrapper"
    sudo ln -sf "${TOOLCRATE_DIR}/scripts/toolcrate_wrapper" /usr/local/bin/toolcrate || \
        echo -e "${YELLOW}Failed to create /usr/local/bin/toolcrate symlink.${NC}"
fi

echo -e "${BLUE}Installation complete!${NC}"
echo -e "${GREEN}Run commands inside the project env with:${NC}"
echo -e "    uv run --extra shazam toolcrate --help"
echo -e "${GREEN}Or, once PATH is updated, simply:${NC}"
echo -e "    toolcrate --help"
