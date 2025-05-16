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
pip install toolcrate

# Development installation
git clone https://github.com/username/toolcrate.git
cd toolcrate
pip install -e .
```

### External Tools Setup

ToolCrate integrates several external tools that are set up automatically during installation. The following tools are included:

- **slsk-batchdl (sldl)**: Soulseek batch download tool

If you need to manually set up these tools, you can run:

```bash
# Run the setup script
./setup_tools.sh
```

For macOS ARM64 (Apple Silicon) users, the installation will automatically:
1. Either build from source using dotnet (if installed)
2. Or download the pre-built binary for macOS ARM64

## Usage

```bash
# Main interface
toolcrate --help

# Direct access to integrated tools
slsk-tool search "artist - title"
shazam-tool identify sample.mp3
mdl-tool get-metadata track.mp3
```

## Requirements

- Python 3.8+
- External dependencies:
  - For building from source: .NET SDK 6.0+
  - For downloading from Soulseek: valid Soulseek account credentials

## License

MIT
