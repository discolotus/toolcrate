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

# Development installation
git clone https://github.com/discolotus/toolcrate.git
cd toolcrate
pip install -e .
```

### Development Setup with Forked Repositories

For development, this project uses forked versions of external tools to ensure compatibility and control:

```bash
# Clone the main repository
git clone https://github.com/discolotus/toolcrate.git
cd toolcrate

# Run development setup (uses forked repositories)
python setup_dev.py

# Or run individual setup steps:
python setup_dev.py clone      # Clone/update forked repos
python setup_dev.py build      # Build SLSK binary
python setup_dev.py deps       # Install Python dependencies
python setup_dev.py submodules # Update git submodules
```

**Forked Repositories Used:**
- **slsk-batchdl**: https://github.com/discolotus/slsk-batchdl.git
- **Shazam-Tool**: https://github.com/discolotus/Shazam-Tool.git

### External Tools Setup

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

### Basic Commands

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

### Docker Integration

ToolCrate includes Docker integration for slsk-batchdl:

```bash
# Run slsk-batchdl commands in Docker container
toolcrate sldl -a "Artist Name" -t "Track Name"

# Enter interactive shell in container
toolcrate sldl
```

### Wishlist & Scheduled Downloads

ToolCrate supports automated wishlist downloading with scheduling:

```bash
# Add items to config/wishlist.txt, then:
toolcrate schedule daily                    # Daily at 2 AM
toolcrate schedule hourly                   # Every hour
toolcrate schedule enable
toolcrate schedule install

# Test wishlist processing
make wishlist-test

# View wishlist run logs and status
toolcrate wishlist-run logs                    # Show recent logs
toolcrate wishlist-run status                  # Show run summary
toolcrate wishlist-run tail                    # Follow logs in real-time

# Or use convenient make commands
make wishlist-logs                              # Show recent logs
make wishlist-status                            # Show run summary
```

### Download Queue

ToolCrate also supports a download queue for individual links that are processed and removed:

```bash
# Add individual links to the queue
toolcrate queue add "https://open.spotify.com/playlist/..."
toolcrate queue add "Artist - Song Title"

# View current queue
toolcrate queue list

# Process queue immediately
toolcrate queue run

# Set up automatic hourly processing (offset from wishlist)
toolcrate schedule add-queue
toolcrate schedule enable
toolcrate schedule install

# Test queue processing
toolcrate schedule test-queue
```

See [docs/WISHLIST_SCHEDULING.md](docs/WISHLIST_SCHEDULING.md) for detailed documentation.

### Configuration and Setup

```bash
# Initial configuration setup
make init-config

# Update configurations from YAML
make config

# Run tests
make test

# Run tests in Docker (isolated environment)
make test-docker
```

### Docker Testing Environment

ToolCrate includes a comprehensive Docker testing environment that provides:

- **Isolated testing** - Clean, reproducible test environment
- **Docker-in-Docker support** - Test Docker functionality within containers
- **All test types** - Python, shell, unit, integration, coverage tests
- **CI/CD ready** - Perfect for automated testing pipelines

```bash
# Quick start - run all tests in Docker
make test-docker

# Run specific test types
make test-docker-run TEST=python      # Python tests only
make test-docker-run TEST=integration # Integration tests
make test-docker-run TEST=coverage    # Tests with coverage

# Interactive development
make test-docker-shell                # Open shell in container

# Cleanup
make test-docker-clean               # Remove Docker artifacts
```

For detailed information, see [docs/DOCKER_TESTING.md](docs/DOCKER_TESTING.md).

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
