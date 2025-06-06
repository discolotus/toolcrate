# ToolCrate

A unified tool suite for music management and processing. ToolCrate integrates multiple specialized tools into a single, easy-to-use package.

## Features

- **Music Recognition**: Powered by Shazam-Tool for identifying songs from audio files
- **Batch Downloading**: Soulseek integration for downloading music collections
- **Unified CLI**: Single command-line interface for all tools
- **Configuration Management**: Centralized configuration with example templates
- **Cross-Platform**: Works on Linux, macOS, and Windows

## Installation

### From PyPI (Recommended)

```bash
pip install toolcrate
```

### Development Installation

**Important**: This repository uses git submodules for external tools. Make sure to clone with submodules included:

#### Method 1: Clone with submodules (Recommended)
```bash
git clone --recurse-submodules https://github.com/yourusername/toolcrate.git
cd toolcrate
poetry install
```

#### Method 2: Clone and initialize submodules separately
```bash
git clone https://github.com/yourusername/toolcrate.git
cd toolcrate
git submodule update --init --recursive
poetry install
```

#### Method 3: Quick setup with automated script
```bash
git clone --recurse-submodules https://github.com/yourusername/toolcrate.git
cd toolcrate
./scripts/setup-dev.sh
```

> **Note**: The external tools (slsk-batchdl and Shazam-Tool) are included as git submodules. Without proper submodule initialization, the integrated tools will not function correctly.

## Configuration

ToolCrate uses configuration files to manage credentials and settings. Example configuration files are provided in the `examples/` directory.

### Initial Setup

1. **Copy example configuration files:**
   ```bash
   # Create config directory
   mkdir -p ~/.config/toolcrate
   
   # Copy and edit configuration files
   cp examples/sldl.conf.example ~/.config/toolcrate/sldl.conf
   cp examples/toolcrate.conf.example ~/.config/toolcrate/toolcrate.conf
   ```

2. **Edit configuration files:**
   - `~/.config/toolcrate/sldl.conf`: Add your Soulseek credentials
   - `~/.config/toolcrate/toolcrate.conf`: Configure download paths and preferences

### Configuration File Locations

ToolCrate looks for configuration files in the following order:
1. `~/.config/toolcrate/` (Linux/macOS) or `%APPDATA%/toolcrate/` (Windows)
2. Current working directory
3. Project root directory

## Usage

### Main Interface

```bash
# Show available commands
toolcrate --help

# Show version information
toolcrate --version
```

### Soulseek Downloads (sldl)

```bash
# Search and download a song
toolcrate sldl "Artist - Song Title"

# Download from a Spotify playlist
toolcrate sldl "https://open.spotify.com/playlist/your_playlist_id"

# Download an album interactively
toolcrate sldl "Artist - Album Name" -at

# Process multiple links from a file
toolcrate sldl --links-file urls.txt
```

### Music Recognition (Shazam)

```bash
# Identify a song from an audio file
toolcrate shazam identify audio_file.mp3

# Process a video file for music recognition
toolcrate shazam video video_file.mp4
```

### Direct Tool Access

You can also access the integrated tools directly:

```bash
slsk-tool search "artist - title"
shazam-tool identify sample.mp3
```

## Development

### Project Structure

```
toolcrate/
├── src/toolcrate/          # Main Python package
├── src/slsk-batchdl/       # Soulseek tool (git submodule)
├── src/Shazam-Tool/        # Shazam tool (git submodule)
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── examples/               # Configuration examples
└── pyproject.toml          # Project configuration
```

### Running Tests

```bash
# Using Poetry (recommended)
poetry run pytest

# Using the test script
./scripts/run_tests.sh

# Run specific test types
poetry run pytest tests/unit/
poetry run pytest tests/integration/
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Sort imports
poetry run isort src/ tests/

# Type checking
poetry run mypy src/
```

## Requirements

- **Python**: 3.8+ (3.11+ recommended)
- **External Tools**:
  - FFmpeg (for audio processing)
  - Docker (optional, for containerized sldl)
- **Credentials**:
  - Valid Soulseek account for downloading
  - Internet connection for Shazam recognition

## Troubleshooting

### Configuration Issues

If you encounter configuration-related errors:

1. Check that configuration files exist in the expected locations
2. Verify that credentials are correctly set in `sldl.conf`
3. Ensure file permissions allow reading the configuration files

### Tool-Specific Issues

- **sldl**: Check Docker installation and Soulseek credentials
- **Shazam**: Verify FFmpeg installation and audio file formats
- **General**: Check Python version compatibility

### Submodule Issues

If you're missing the external tools or getting import errors:

```bash
# Reinitialize submodules
git submodule update --init --recursive

# Force update submodules to latest commits
git submodule update --remote --merge

# Check submodule status
git submodule status
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) - Soulseek batch download tool
- [Shazam-Tool](https://github.com/in0vik/Shazam-Tool) - Music recognition tool
