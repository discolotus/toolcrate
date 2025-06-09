# ToolCrate Configuration

This directory contains the configuration files for ToolCrate.

## Files

- `toolcrate.yaml` - Main configuration file in YAML format
- `sldl.conf` - Generated configuration for slsk-batchdl compatibility
- `docker-compose.yml` - Docker Compose configuration
- `.env` - Environment variables for Docker
- `validate-config.py` - Configuration validation script
- `crontabs/` - Cron job configurations

## Usage

### Validate Configuration
```bash
python3 validate-config.py toolcrate.yaml
```

### Update sldl.conf from YAML
After editing `toolcrate.yaml`, regenerate `sldl.conf`:
```bash
# Update tool configs from YAML
make config

# Or re-run the configuration script to regenerate everything
../configure_toolcrate.sh
```

### Docker Deployment
```bash
docker-compose up -d
```

### Cron Jobs
To activate cron jobs:
```bash
# System-wide (requires sudo)
sudo cp crontabs/toolcrate /etc/cron.d/

# User-specific
crontab crontabs/toolcrate
```

## Configuration Sections

### General Settings
- Project name and logging configuration
- Data and log directory paths

### Soulseek (slsk-batchdl)
- Authentication credentials
- Download preferences and quality settings
- Search and performance parameters

### API Integrations
- Spotify API credentials
- YouTube API key

### Automation
- Cron job schedules
- Automated download configurations

### Docker/Containerization
- Mount point configurations
- Environment variables
- Service definitions

## Profiles

The configuration includes several pre-defined profiles:

- `lossless` - High quality lossless audio downloads
- `quick` - Fast downloads with lower quality
- `interactive` - Interactive mode with user prompts

Use profiles with: `slsk-tool --profile lossless <playlist>`
