# ToolCrate Setup Guide

This guide covers the comprehensive setup script for ToolCrate with YAML-based configuration.

## Quick Start

```bash
# Run the interactive configuration generator (creates virtual environment automatically)
./configure_toolcrate.sh
# OR use the convenient Make command
make init-config

# Or run the existing installation script
./install.sh

# Always activate virtual environment before using tools
source .venv/bin/activate
```

## ⚠️ Virtual Environment Safety

The setup script **automatically creates and uses a Python virtual environment** to ensure:
- No packages are installed globally
- Dependencies are isolated from your system Python
- Consistent environment across different systems
- Easy cleanup and management

## ToolCrate Configuration Generator Features

The new `configure_toolcrate.sh` script provides a comprehensive configuration system with:

### ✨ Key Features

- **YAML Configuration Format**: Modern, human-readable configuration
- **Interactive CLI Prompts**: Guided setup with sensible defaults
- **Complete slsk-batchdl Coverage**: All configuration options supported
- **Cron Job Management**: Automated download scheduling
- **Docker Support**: Container deployment configurations
- **Configuration Validation**: Built-in validation and error checking
- **Profile System**: Pre-configured settings for different use cases

### 📁 Generated Files

The setup script creates the following structure:

```
config/
├── toolcrate.yaml          # Main YAML configuration
├── sldl.conf              # Generated slsk-batchdl config
├── docker-compose.yml     # Docker deployment
├── .env                   # Environment variables
├── validate-config.py     # Configuration validator
├── README.md              # Configuration documentation
└── crontabs/
    └── toolcrate          # Cron job definitions
```

## Configuration Sections

### General Settings
```yaml
general:
  project_name: "toolcrate"
  log_level: "info"
  data_directory: "/path/to/data"
  log_directory: "/path/to/logs"
```

### Soulseek (slsk-batchdl) Configuration
```yaml
slsk_batchdl:
  # Authentication
  username: "your-username"
  password: "your-password"
  
  # Directories
  parent_dir: "/path/to/downloads"
  skip_music_dir: "/path/to/music"
  
  # Audio Preferences
  preferred_conditions:
    formats: ["flac", "mp3"]
    min_bitrate: 200
    max_bitrate: 2500
    max_sample_rate: 48000
  
  # Search Settings
  concurrent_processes: 2
  search_timeout: 6000
  fast_search: true
  skip_existing: true
```

### API Integrations
```yaml
spotify:
  client_id: "your-spotify-client-id"
  client_secret: "your-spotify-client-secret"

youtube:
  api_key: "your-youtube-api-key"
```

### Cron Jobs
```yaml
cron:
  enabled: true
  jobs:
    - name: "automated_download"
      schedule: "0 2 * * *"  # Daily at 2 AM
      command: "slsk-tool"
      args: ["playlist-url", "-c", "/config", "-p", "/data"]
```

### Docker/Mount Configuration
```yaml
mounts:
  data:
    host_path: "/host/data"
    container_path: "/data"
  config:
    host_path: "/host/config"
    container_path: "/config"
```

### Profiles
```yaml
profiles:
  lossless:
    description: "High quality lossless audio"
    settings:
      preferred_conditions:
        formats: ["flac", "wav", "alac"]
        min_bitrate: 1000
  
  quick:
    description: "Fast downloads with lower quality"
    settings:
      preferred_conditions:
        formats: ["mp3"]
        min_bitrate: 128
        max_bitrate: 320
      fast_search: true
```

## Usage Examples

### Basic Setup
```bash
# Run interactive configuration generator (automatically creates virtual environment)
./configure_toolcrate.sh
# OR use the convenient Make command
make init-config

# Follow the prompts to configure:
# - Project settings
# - Soulseek credentials
# - Download preferences
# - API keys
# - Cron schedules
```

### Virtual Environment Management
```bash
# Activate virtual environment (required for all Python tools)
source .venv/bin/activate

# Check if virtual environment is active
echo $VIRTUAL_ENV

# Deactivate virtual environment
deactivate

# Recreate virtual environment if needed
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install PyYAML
```

### Configuration Management
```bash
# Validate configuration
python3 -m toolcrate.config.manager validate

# Generate sldl.conf from YAML
python3 -m toolcrate.config.manager generate-sldl

# Show current configuration
python3 -m toolcrate.config.manager show
```

### Using Profiles
```bash
# Use lossless profile
slsk-tool --profile lossless "artist - album"

# Use quick profile
slsk-tool --profile quick "playlist-url"

# Interactive mode
slsk-tool --profile interactive "search-term"
```

### Docker Deployment
```bash
# Deploy with Docker Compose
cd config
docker-compose up -d

# View logs
docker-compose logs -f sldl

# Rebuild Docker image (after code changes)
make buildimage

# Rebuild and restart services
cd config
docker-compose up --build --force-recreate sldl
```

### Cron Jobs
```bash
# Install system-wide cron job
sudo cp config/crontabs/toolcrate /etc/cron.d/

# Install user-specific cron job
crontab config/crontabs/toolcrate

# View active cron jobs
crontab -l
```

## Advanced Configuration

### Custom Profiles
Add custom profiles to `toolcrate.yaml`:

```yaml
profiles:
  my_profile:
    description: "My custom settings"
    settings:
      preferred_conditions:
        formats: ["flac"]
        min_bitrate: 1411
      concurrent_processes: 4
      interactive_mode: true
```

### Environment Variables
Set environment variables in `config/.env`:

```bash
# Timezone
TZ=America/New_York

# User/Group IDs (Linux)
PUID=1000
PGID=1000

# Custom paths
CUSTOM_DATA_PATH=/mnt/music
```

### Multiple Cron Jobs
Configure multiple automated downloads:

```yaml
cron:
  enabled: true
  jobs:
    - name: "daily_playlist"
      schedule: "0 2 * * *"
      command: "slsk-tool"
      args: ["daily-playlist-url"]
    
    - name: "weekly_discovery"
      schedule: "0 3 * * 0"
      command: "slsk-tool"
      args: ["--profile", "lossless", "discovery-playlist-url"]
```

## Troubleshooting

### Configuration Validation
```bash
# Check for configuration errors
python3 config/validate-config.py config/toolcrate.yaml

# Common issues:
# - Missing required fields
# - Invalid directory paths
# - Incorrect data types
```

### Regenerating sldl.conf
```bash
# If you edit toolcrate.yaml, regenerate sldl.conf
python3 -m toolcrate.config.manager generate-sldl
```

### Testing Configuration
```bash
# Test the configuration generator
./tests/test_config_generator.sh

# Validate configuration
make config-validate

# Update tool configs from YAML
make config

# Dry run with slsk-tool
slsk-tool --config config/sldl.conf --help
```

## Migration from Old Configuration

If you have an existing `.conf` file, you can:

1. Run the new setup script to create YAML configuration
2. Manually copy settings from old config to `toolcrate.yaml`
3. Regenerate `sldl.conf` using the config manager
4. Validate the new configuration

## Dependencies

The setup script requires:
- Python 3.8+
- PyYAML (automatically installed)
- Bash shell

Optional:
- Docker (for containerized deployment)
- Cron (for scheduled downloads)

## Support

For issues with the configuration generator:
1. Run `./test_config_generator.sh` to verify functionality
2. Check configuration with `make config-validate`
3. Review generated files in the `config/` directory
4. Consult `config/README.md` for detailed configuration help
