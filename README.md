# ToolCrate

ToolCrate is a command-line toolkit for music management and processing.

The Python package provides the top-level CLI and stable wrapper commands. External tools are installed explicitly into a ToolCrate-managed bin directory, so runtime execution is just normal local binaries and scripts.

## Integrated Tools

- `slsk-tool`: runs `sldl`, the Soulseek batch downloader.
- `shazam-tool`: runs the bundled Shazam recognition tool.
- `mdl-tool`: runs an installed `mdl-utils` command, the `mdl_utils.cli` Python module, or ToolCrate's built-in metadata fallback.

Docker is not part of the runtime path.

## Install

```bash
./install.sh
```

Manual development install:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
git submodule update --init --recursive
toolcrate tools install
```

## Tool Management

Show installed tools and resolution paths:

```bash
toolcrate tools status
```

Run post-install smoke checks:

```bash
toolcrate tools verify
```

Install all managed tools:

```bash
toolcrate tools install
```

Install one tool:

```bash
toolcrate tools install --tool sldl
toolcrate tools install --tool shazam-tool
toolcrate tools install --tool mdl-tool
```

By default, managed tools are written to:

- macOS: `~/Library/Application Support/toolcrate/bin`
- Linux: `~/.local/share/toolcrate/bin`
- Windows: `%LOCALAPPDATA%\toolcrate\bin`

Override this location with `TOOLCRATE_HOME`.

## Requirements

- Python 3.8+
- `ffmpeg` for audio conversion and Shazam workflows
- .NET SDK 6.0+ to build `sldl` from source when no local/prebuilt binary is present
- Soulseek credentials for Soulseek downloads

`toolcrate tools install` will prefer an existing local `src/bin/sldl` runtime directory, then build from `src/slsk-batchdl` with `dotnet`, and on macOS ARM64 can download the upstream `sldl` release archive as a fallback.

## Usage

```bash
toolcrate info
slsk-tool "artist - title"
shazam-tool recognize sample.mp3
mdl-tool --help
```

## Tests

```bash
pytest tests/test_tool_integrations.py
```

These tests use isolated temporary ToolCrate homes and fake tool binaries for repeatability. Use `toolcrate tools verify` for a real local post-install smoke check.
