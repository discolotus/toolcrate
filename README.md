# ToolCrate

A unified tool suite for music management and processing. ToolCrate integrates multiple specialized tools into a single, easy-to-use package.

## Features

- **Music Recognition**: Powered by Shazam-Tool for identifying songs from audio files
- **Batch Downloading**: Soulseek integration via slsk-batchdl for downloading music collections
- **Unified CLI**: Single command-line interface for all tools
- **Configuration Management**: Centralized YAML configuration with example templates
- **Wishlist & Queue**: Automated scheduled downloading with cron support

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (package manager)
- FFmpeg (for audio processing)
- Docker (optional, for containerized sldl)
- Valid Soulseek account for downloading

## Installation

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/discolotus/toolcrate.git
cd toolcrate

# Install with uv
uv sync

# Run
uv run toolcrate --help
```

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Configuration

Copy the example configuration files and edit them with your credentials:

```bash
mkdir -p ~/.config/toolcrate
cp examples/sldl.conf.example ~/.config/toolcrate/sldl.conf
cp examples/toolcrate.conf.example ~/.config/toolcrate/toolcrate.conf
```

Or run the interactive setup:

```bash
make init-config
```

### Configuration File Locations

ToolCrate looks for configuration files in this order:

1. `~/.config/toolcrate/` (Linux/macOS) or `%APPDATA%/toolcrate/` (Windows)
2. Current working directory
3. Project root directory

## Usage

```bash
# Show available commands
uv run toolcrate --help

# Show version
uv run toolcrate --version
```

### Soulseek Downloads (sldl)

```bash
uv run toolcrate sldl "Artist - Song Title"
uv run toolcrate sldl "https://open.spotify.com/playlist/your_playlist_id"
uv run toolcrate sldl --links-file urls.txt
```

### Music Recognition (Shazam)

```bash
uv run toolcrate shazam identify audio_file.mp3
uv run toolcrate shazam video video_file.mp4
```

### Wishlist & Scheduled Downloads

```bash
# Add items to config/wishlist.txt, then schedule:
uv run toolcrate schedule daily       # Daily at 2 AM
uv run toolcrate schedule hourly      # Every hour
uv run toolcrate schedule enable
uv run toolcrate schedule install

# Monitor
uv run toolcrate wishlist-run logs
uv run toolcrate wishlist-run status
```

### Download Queue

```bash
uv run toolcrate queue add "https://open.spotify.com/playlist/..."
uv run toolcrate queue list
uv run toolcrate queue run
```

See [docs/WISHLIST_SCHEDULING.md](docs/WISHLIST_SCHEDULING.md) and [docs/DOWNLOAD_QUEUE.md](docs/DOWNLOAD_QUEUE.md) for details.

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
├── docs/                   # Documentation
├── Dockerfile              # Container image
├── docker-compose.yml      # Docker Compose config
└── pyproject.toml          # Project configuration
```

### Setup

```bash
uv sync                     # Install all dependencies (including dev)
uv run pre-commit install   # Install git hooks
```

### Testing

```bash
make test                   # Run all tests
make test-python            # Python tests only
make test-unit              # Unit tests
make test-coverage          # Tests with coverage report
make test-docker            # Run tests in Docker
```

### Code Quality

```bash
make format                 # Format with ruff
make lint                   # Lint with ruff + mypy
make check                  # Format + lint
```

### Submodule Issues

```bash
git submodule update --init --recursive   # Initialize submodules
git submodule update --remote --merge     # Update to latest
git submodule status                      # Check status
```

## Docker

```bash
# Build image
docker build -t toolcrate .

# Run with docker-compose
docker-compose up
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `make check` and `make test`
5. Submit a pull request

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) — Soulseek batch download tool
- [Shazam-Tool](https://github.com/in0vik/Shazam-Tool) — Music recognition tool
