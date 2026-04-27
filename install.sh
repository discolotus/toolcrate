#!/usr/bin/env bash
set -euo pipefail

printf 'Setting up ToolCrate...\n'

TOOLCRATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TOOLCRATE_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

if [ -d ".git" ]; then
  git submodule update --init --recursive
fi

toolcrate tools install

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

for command in toolcrate slsk-tool shazam-tool mdl-tool; do
  target="$LOCAL_BIN/$command"
  source_path="$TOOLCRATE_DIR/.venv/bin/$command"
  {
    printf '#!/usr/bin/env bash\n'
    printf 'set -euo pipefail\n'
    printf 'source %q\n' "$TOOLCRATE_DIR/.venv/bin/activate"
    printf 'exec %q "$@"\n' "$source_path"
  } > "$target"
  chmod +x "$target"
done

printf '\nInstallation complete.\n'
printf 'ToolCrate commands were written to: %s\n' "$LOCAL_BIN"
printf 'Managed external tools were written to: %s\n' "$(toolcrate tools status | sed -n 's/^Managed bin:    //p')"
