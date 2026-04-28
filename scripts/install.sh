#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Setting up ToolCrate...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLCRATE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$TOOLCRATE_DIR"

echo -e "${GREEN}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=${PYTHON_VERSION%%.*}
PYTHON_MINOR=${PYTHON_VERSION#*.}

if [[ "$PYTHON_MAJOR" -lt 3 || ( "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 10 ) ]]; then
  echo -e "${RED}Error: ToolCrate requires Python 3.10 or higher${NC}"
  echo -e "${RED}Current Python version: ${PYTHON_VERSION}${NC}"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo -e "${GREEN}Creating Python virtual environment in .venv...${NC}"
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m ensurepip --upgrade >/dev/null 2>&1 || true
python -m pip install --upgrade pip
python -m pip install -e .

if [ -d ".git" ]; then
  echo -e "${GREEN}Setting up git submodules...${NC}"
  git submodule update --init --recursive
else
  echo -e "${YELLOW}Not a git repository; skipping submodule initialization.${NC}"
fi

echo -e "${GREEN}Installing managed external tools...${NC}"
toolcrate tools install

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

for command in toolcrate slsk-tool shazam-tool mdl-tool; do
  target="$LOCAL_BIN/$command"
  source_path="$TOOLCRATE_DIR/.venv/bin/$command"
  {
    printf '#!/usr/bin/env bash\n'
    printf 'set -euo pipefail\n'
    printf 'export TOOLCRATE_ROOT=%q\n' "$TOOLCRATE_DIR"
    printf 'source %q\n' "$TOOLCRATE_DIR/.venv/bin/activate"
    printf 'exec %q "$@"\n' "$source_path"
  } > "$target"
  chmod +x "$target"
done

echo -e "${BLUE}Installation complete.${NC}"
echo -e "${GREEN}ToolCrate commands were written to: ${LOCAL_BIN}${NC}"
echo -e "${GREEN}Run: toolcrate tools verify${NC}"
