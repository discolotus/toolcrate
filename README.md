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
- **Shazam-Tool**: Music recognition tool

If you need to manually set up these tools, you can run:

```bash
# Run the installation script
./install.sh
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

### Using sldl (Soulseek Batch Downloader)

ToolCrate integrates slsk-batchdl via Docker for cross-platform compatibility. The first time you run the tool, it will:

1. Create a configuration directory at `~/.config/sldl`
2. Prompt for your Soulseek username and password
3. Build and start a persistent Docker container 

The tool maintains downloaded files in `~/Music/downloads`, organized by source (Spotify, YouTube, etc.).

```bash
# Search and download a song
toolcrate sldl "Artist - Song Title"

# Download from a Spotify playlist
toolcrate sldl "https://open.spotify.com/playlist/your_playlist_id"

# Download an album interactively (with selection menu)
toolcrate sldl "Artist - Album Name" -at

# Process multiple links from a text file (one link per line)
toolcrate sldl --links-file ~/path/to/urls.txt

# Set or update Soulseek credentials
toolcrate sldl --set-credentials

# Recreate the container (in case of issues)
toolcrate sldl --recreate
```

The tool automatically creates appropriate download directories for playlist content:
- Spotify playlists: `~/Music/downloads/spotify/playlist-name/`
- YouTube playlists: `~/Music/downloads/youtube/playlist-name/`

For more advanced usage, refer to the [slsk-batchdl documentation](https://github.com/fiso64/slsk-batchdl).

## Running Tests

ToolCrate includes a test suite with both unit and integration tests. The easiest way to run the tests is to use the provided shell script, which automatically activates the virtual environment:

```bash
# Using the shell script (recommended)
./run_tests.sh                # Run all tests
./run_tests.sh --unit         # Run only unit tests
./run_tests.sh --integration  # Run only integration tests
./run_tests.sh --verbose      # Run with verbose output
./run_tests.sh --pytest       # Run tests using pytest instead of the custom runner
```

Alternatively, you can run the tests manually after activating the virtual environment:

```bash
# Using the provided Python script
source .venv/bin/activate
python -m tests.run_tests        # Run all tests
python -m tests.run_tests --unit  # Run only unit tests
python -m tests.run_tests --integration  # Run only integration tests

# Using pytest
source .venv/bin/activate
pytest                      # Run all tests
pytest tests/unit/          # Run only unit tests
pytest tests/integration/   # Run only integration tests
pytest -v                   # Run with verbose output
deactivate
```

## Requirements

- Python 3.11 or 3.12 (Python 3.13 is not supported due to compatibility issues with certain dependencies)
- External dependencies:
  - For building from source: .NET SDK 6.0+
  - For downloading from Soulseek: valid Soulseek account credentials
  - For Shazam-Tool: FFmpeg
  - For testing: pytest (optional)

### Known Issues

- **Python 3.13 Compatibility**: The Shazam-Tool has known issues with Python 3.13 due to the removal of the `audioop` module, which is used by some of its dependencies.

## License

MIT
