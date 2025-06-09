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

### Basic Commands

```bash
# Main interface
toolcrate --help

# Direct access to integrated tools
slsk-tool search "artist - title"
shazam-tool identify sample.mp3
mdl-tool get-metadata track.mp3
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

- Python 3.8+
- External dependencies:
  - For building from source: .NET SDK 6.0+
  - For downloading from Soulseek: valid Soulseek account credentials

## License

MIT
