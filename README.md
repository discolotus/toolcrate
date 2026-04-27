# ToolCrate

A unified tool suite for music management and processing. ToolCrate integrates multiple specialized tools into a single, easy-to-use package.

## Features

- Music recognition (powered by Shazam)
- Batch downloading from Soulseek
- Music metadata utilities
- Unified command-line interface

## Installation

```bash
# Install from PyPI
uv tool install toolcrate

# Development installation
git clone https://github.com/username/toolcrate.git
cd toolcrate
uv sync --extra shazam
```

### External Tools Setup

ToolCrate integrates several external tools that are set up by the development installer. The following tools are included:

- **slsk-batchdl (sldl)**: Soulseek batch download tool

If you need to manually set up these tools, you can run:

```bash
# Run the installer
./install.sh
```

For macOS ARM64 (Apple Silicon) users, the installation will automatically:
1. Either build from source using dotnet (if installed)
2. Or download the pre-built binary for macOS ARM64

## Usage

```bash
# Main interface
uv run --extra shazam toolcrate --help

# Direct access to integrated tools
uv run --extra shazam slsk-tool search "artist - title"
uv run --extra shazam shazam-tool identify sample.mp3
uv run --extra shazam mdl-tool get-metadata track.mp3
```

## Requirements

- Python 3.8+
- uv
- External dependencies:
  - For building from source: .NET SDK 6.0+
  - For downloading from Soulseek: valid Soulseek account credentials

## License

MIT
