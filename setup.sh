#!/bin/bash
# Comprehensive setup script for toolcrate with YAML configuration

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}ToolCrate Comprehensive Setup${NC}"
echo -e "${BLUE}=============================${NC}"

# Get the absolute path of the current directory
TOOLCRATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${TOOLCRATE_DIR}/config"
CRON_DIR="${CONFIG_DIR}/crontabs"

# Function to ensure virtual environment is active
ensure_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -f "${TOOLCRATE_DIR}/.venv/bin/activate" ]; then
            echo -e "${GREEN}Activating existing virtual environment...${NC}"
            source "${TOOLCRATE_DIR}/.venv/bin/activate"
        else
            echo -e "${GREEN}Creating Python virtual environment...${NC}"
            python3 -m venv "${TOOLCRATE_DIR}/.venv"
            source "${TOOLCRATE_DIR}/.venv/bin/activate"
            pip install --upgrade pip
        fi
    else
        echo -e "${GREEN}Virtual environment already active: $VIRTUAL_ENV${NC}"
    fi
}

# Ensure we're using a virtual environment
ensure_venv

# Function to prompt for input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "${prompt} [${default}]: " input
        if [ -z "$input" ]; then
            input="$default"
        fi
    else
        read -p "${prompt}: " input
    fi
    
    eval "$var_name='$input'"
}

# Function to prompt for yes/no with default
prompt_yes_no() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    while true; do
        if [ "$default" = "y" ]; then
            read -p "${prompt} [Y/n]: " input
            input=${input:-y}
        else
            read -p "${prompt} [y/N]: " input
            input=${input:-n}
        fi
        
        case $input in
            [Yy]* ) eval "$var_name=true"; break;;
            [Nn]* ) eval "$var_name=false"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# Create necessary directories
echo -e "${GREEN}Creating configuration directories...${NC}"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CRON_DIR"
mkdir -p "${TOOLCRATE_DIR}/data"
mkdir -p "${TOOLCRATE_DIR}/logs"

# Check if configuration already exists
if [ -f "${CONFIG_DIR}/toolcrate.yaml" ]; then
    echo -e "${YELLOW}Configuration file already exists.${NC}"
    prompt_yes_no "Do you want to overwrite the existing configuration?" "n" "overwrite"
    if [ "$overwrite" = "false" ]; then
        echo -e "${BLUE}Setup cancelled. Existing configuration preserved.${NC}"
        exit 0
    fi
fi

echo -e "${GREEN}Gathering configuration information...${NC}"
echo -e "${YELLOW}Press Enter to use default values shown in brackets.${NC}"
echo

# General ToolCrate Settings
echo -e "${BLUE}=== General ToolCrate Settings ===${NC}"
prompt_with_default "Project name" "toolcrate" "project_name"
prompt_with_default "Log level (debug, info, warning, error)" "info" "log_level"
prompt_with_default "Data directory" "${TOOLCRATE_DIR}/data" "data_dir"
prompt_with_default "Log directory" "${TOOLCRATE_DIR}/logs" "log_dir"

# Soulseek Settings
echo -e "\n${BLUE}=== Soulseek (slsk-batchdl) Settings ===${NC}"
prompt_with_default "Soulseek username" "" "slsk_username"
prompt_with_default "Soulseek password" "" "slsk_password"
prompt_with_default "Download directory" "${data_dir}/downloads" "download_dir"
prompt_with_default "Music library directory (for skip checking)" "${data_dir}/music" "music_dir"
prompt_with_default "Preferred audio formats (comma-separated)" "flac,mp3" "preferred_formats"
prompt_with_default "Minimum bitrate" "200" "min_bitrate"
prompt_with_default "Maximum bitrate" "2500" "max_bitrate"
prompt_with_default "Maximum sample rate" "48000" "max_sample_rate"
prompt_with_default "Concurrent downloads" "2" "concurrent_downloads"
prompt_with_default "Search timeout (ms)" "6000" "search_timeout"
prompt_with_default "Listen port" "49998" "listen_port"
prompt_yes_no "Enable fast search" "y" "fast_search"
prompt_yes_no "Skip existing files" "y" "skip_existing"
prompt_yes_no "Write index file" "y" "write_index"
prompt_yes_no "Interactive mode by default" "n" "interactive_mode"

# Spotify API Settings
echo -e "\n${BLUE}=== Spotify API Settings ===${NC}"
echo -e "${YELLOW}Get these from: https://developer.spotify.com/dashboard${NC}"
prompt_with_default "Spotify Client ID" "" "spotify_client_id"
prompt_with_default "Spotify Client Secret" "" "spotify_client_secret"

# YouTube API Settings
echo -e "\n${BLUE}=== YouTube API Settings ===${NC}"
echo -e "${YELLOW}Get this from: https://console.developers.google.com${NC}"
prompt_with_default "YouTube API Key" "" "youtube_api_key"

# Cron Job Settings
echo -e "\n${BLUE}=== Cron Job Settings ===${NC}"
prompt_yes_no "Set up automated downloads with cron" "n" "setup_cron"

if [ "$setup_cron" = "true" ]; then
    prompt_with_default "Cron schedule (e.g., '0 2 * * *' for daily at 2 AM)" "0 2 * * *" "cron_schedule"
    prompt_with_default "Playlist URL for automated downloads" "" "cron_playlist"
fi

# Mount Settings (for Docker/containerized environments)
echo -e "\n${BLUE}=== Mount and Path Settings ===${NC}"
prompt_with_default "Host data mount point (for Docker)" "${TOOLCRATE_DIR}/data" "host_data_mount"
prompt_with_default "Host config mount point (for Docker)" "${TOOLCRATE_DIR}/config" "host_config_mount"

echo -e "\n${GREEN}Creating configuration files...${NC}"

# Create main YAML configuration file
cat > "${CONFIG_DIR}/toolcrate.yaml" << EOF
# ToolCrate Configuration File
# Generated on $(date)

# General Settings
general:
  project_name: "${project_name}"
  log_level: "${log_level}"
  data_directory: "${data_dir}"
  log_directory: "${log_dir}"

# Soulseek (slsk-batchdl) Configuration
slsk_batchdl:
  # Authentication
  username: "${slsk_username}"
  password: "${slsk_password}"

  # Directories
  parent_dir: "${download_dir}"
  skip_music_dir: "${music_dir}"
  index_file_path: "${data_dir}/index.sldl"
  m3u_file_path: "${data_dir}/playlist.m3u"
  failed_album_path: "${data_dir}/failed"
  log_file_path: "${log_dir}/sldl.log"

  # Audio Format Preferences
  preferred_conditions:
    formats: [$(echo "$preferred_formats" | sed 's/,/, /g' | sed 's/\([^,]*\)/"\1"/g')]
    min_bitrate: ${min_bitrate}
    max_bitrate: ${max_bitrate}
    max_sample_rate: ${max_sample_rate}
    length_tolerance: 3
    strict_title: true
    strict_album: true

  # Necessary Conditions (fallback)
  necessary_conditions:
    formats: ["mp3", "flac", "ogg", "m4a", "opus", "wav", "aac", "alac"]

  # Search and Download Settings
  concurrent_processes: ${concurrent_downloads}
  search_timeout: ${search_timeout}
  listen_port: ${listen_port}
  fast_search: ${fast_search}
  fast_search_delay: 300
  fast_search_min_up_speed: 1.0
  skip_existing: ${skip_existing}
  write_index: ${write_index}
  interactive_mode: ${interactive_mode}

  # Advanced Settings
  max_tracks: 999999
  offset: 0
  max_stale_time: 30000
  unknown_error_retries: 2
  max_retries_per_track: 30
  searches_per_time: 34
  search_renew_time: 220
  min_shares_aggregate: 2
  aggregate_length_tol: 3

  # Flags
  album: false
  aggregate: false
  album_art_only: false
  desperate_search: false
  no_remove_special_chars: false
  artist_maybe_wrong: false
  yt_parse: false
  remove_ft: false
  remove_brackets: false
  reverse: false
  use_ytdlp: false
  remove_tracks_from_source: false
  get_deleted: false
  deleted_only: false
  remove_single_character_search_terms: false
  relax: false
  no_modify_share_count: false
  use_random_login: false
  no_browse_folder: false
  skip_check_cond: false
  skip_check_pref_cond: false
  no_progress: false
  write_playlist: false
  parallel_album_search: false
  extract_artist: false

  # Album Settings
  set_album_min_track_count: true
  set_album_max_track_count: false
  min_album_track_count: -1
  max_album_track_count: -1
  album_track_count_max_retries: 5
  parallel_album_search_processes: 5

  # String Settings
  time_unit: "s"
  name_format: ""
  invalid_replace_str: " "
  ytdlp_argument: ""
  parse_title_template: ""

# Spotify API Configuration
spotify:
  client_id: "${spotify_client_id}"
  client_secret: "${spotify_client_secret}"
  token: ""
  refresh_token: ""

# YouTube API Configuration
youtube:
  api_key: "${youtube_api_key}"

# Cron Job Configuration
cron:
  enabled: ${setup_cron}
EOF

if [ "$setup_cron" = "true" ]; then
cat >> "${CONFIG_DIR}/toolcrate.yaml" << EOF
  jobs:
    - name: "automated_download"
      schedule: "${cron_schedule}"
      command: "slsk-tool"
      args: ["${cron_playlist}", "-c", "/config", "-p", "/data", "--index-path", "/data/index.sldl"]
      description: "Automated playlist download"
EOF
else
cat >> "${CONFIG_DIR}/toolcrate.yaml" << EOF
  jobs: []
EOF
fi

cat >> "${CONFIG_DIR}/toolcrate.yaml" << EOF

# Mount Configuration (for Docker/containerized environments)
mounts:
  data:
    host_path: "${host_data_mount}"
    container_path: "/data"
    description: "Data directory mount"
  config:
    host_path: "${host_config_mount}"
    container_path: "/config"
    description: "Configuration directory mount"

# Environment Variables
environment:
  TZ: "UTC"
  PUID: 1000
  PGID: 1000

# Profiles (can be activated with --profile flag)
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

  interactive:
    description: "Interactive mode with user prompts"
    settings:
      interactive_mode: true
      max_stale_time: 9999999
EOF

echo -e "${GREEN}Created: ${CONFIG_DIR}/toolcrate.yaml${NC}"

# Generate sldl.conf file for slsk-batchdl compatibility
echo -e "${GREEN}Generating sldl.conf for slsk-batchdl compatibility...${NC}"

cat > "${CONFIG_DIR}/sldl.conf" << EOF
# sldl.conf - Generated from toolcrate.yaml on $(date)
# This file is automatically generated. Edit toolcrate.yaml instead.

# Authentication
username = ${slsk_username}
password = ${slsk_password}

# Directories
parent-dir = ${download_dir}
skip-music-dir = ${music_dir}
index-path = ${data_dir}/index.sldl
m3u-path = ${data_dir}/playlist.m3u
failed-album-path = ${data_dir}/failed
log-path = ${log_dir}/sldl.log

# Audio Format Preferences
pref-format = ${preferred_formats}
pref-min-bitrate = ${min_bitrate}
pref-max-bitrate = ${max_bitrate}
pref-max-sample-rate = ${max_sample_rate}
pref-length-tol = 3
pref-strict-title = true
pref-strict-album = true

# Search and Download Settings
concurrent-processes = ${concurrent_downloads}
search-timeout = ${search_timeout}
listen-port = ${listen_port}
fast-search = ${fast_search}
fast-search-delay = 300
fast-search-min-up-speed = 1.0
skip-existing = ${skip_existing}
write-index = ${write_index}
interactive = ${interactive_mode}

# Advanced Settings
max-stale-time = 30000
unknown-error-retries = 2
max-retries-per-track = 30
searches-per-time = 34
search-renew-time = 220
min-shares-aggregate = 2
aggregate-length-tol = 3

# String Settings
time-format = s
invalid-replace-str = " "

# Spotify API (if configured)
EOF

if [ -n "$spotify_client_id" ]; then
cat >> "${CONFIG_DIR}/sldl.conf" << EOF
spotify-id = ${spotify_client_id}
spotify-secret = ${spotify_client_secret}
EOF
fi

if [ -n "$youtube_api_key" ]; then
cat >> "${CONFIG_DIR}/sldl.conf" << EOF
yt-key = ${youtube_api_key}
EOF
fi

cat >> "${CONFIG_DIR}/sldl.conf" << EOF

# Profiles
[lossless]
pref-format = flac,wav,alac
pref-min-bitrate = 1000

[quick]
pref-format = mp3
pref-min-bitrate = 128
pref-max-bitrate = 320
fast-search = true

[interactive]
interactive = true
max-stale-time = 9999999
EOF

echo -e "${GREEN}Created: ${CONFIG_DIR}/sldl.conf${NC}"

# Create cron job file if requested
if [ "$setup_cron" = "true" ]; then
    echo -e "${GREEN}Creating cron job configuration...${NC}"

    cat > "${CRON_DIR}/toolcrate" << EOF
# ToolCrate Automated Downloads
# Generated on $(date)
#
# Format: minute hour day month weekday command
# Example schedules:
# 0 2 * * *     - Daily at 2 AM
# 0 2 * * 0     - Weekly on Sunday at 2 AM
# 0 2 1 * *     - Monthly on 1st at 2 AM
# */30 * * * *  - Every 30 minutes

${cron_schedule} sldl "${cron_playlist}" -c /config -p /data --index-path /data/index.sldl
EOF

    echo -e "${GREEN}Created: ${CRON_DIR}/toolcrate${NC}"
    echo -e "${YELLOW}To activate cron jobs, copy the file to your system:${NC}"
    echo -e "${YELLOW}  sudo cp ${CRON_DIR}/toolcrate /etc/cron.d/${NC}"
    echo -e "${YELLOW}  Or add to your user crontab: crontab ${CRON_DIR}/toolcrate${NC}"
fi

# Create Docker Compose file for containerized deployment
echo -e "${GREEN}Creating Docker Compose configuration...${NC}"

cat > "${CONFIG_DIR}/docker-compose.yml" << EOF
# Docker Compose configuration for ToolCrate
# Generated on $(date)

services:
  toolcrate:
    image: toolcrate:latest
    container_name: toolcrate
    environment:
      - TZ=UTC
      - PUID=1000
      - PGID=1000
    volumes:
      - ${host_config_mount}:/config
      - ${host_data_mount}:/data
    restart: unless-stopped
    networks:
      - toolcrate-network

  sldl:
    image: slsk-batchdl:latest
    container_name: sldl
    environment:
      - TZ=UTC
      - PUID=1000
      - PGID=1000
    volumes:
      - ${host_config_mount}:/config
      - ${host_data_mount}:/data
    restart: unless-stopped
    networks:
      - toolcrate-network
    depends_on:
      - toolcrate

networks:
  toolcrate-network:
    driver: bridge

volumes:
  config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${host_config_mount}
  data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${host_data_mount}
EOF

echo -e "${GREEN}Created: ${CONFIG_DIR}/docker-compose.yml${NC}"

# Create environment file for Docker
cat > "${CONFIG_DIR}/.env" << EOF
# Environment variables for Docker Compose
# Generated on $(date)

# Timezone
TZ=UTC

# User/Group IDs (recommended for Linux hosts)
PUID=1000
PGID=1000

# Mount paths
HOST_CONFIG_PATH=${host_config_mount}
HOST_DATA_PATH=${host_data_mount}

# Application settings
PROJECT_NAME=${project_name}
LOG_LEVEL=${log_level}
EOF

echo -e "${GREEN}Created: ${CONFIG_DIR}/.env${NC}"

# Create a configuration validation script
cat > "${CONFIG_DIR}/validate-config.py" << 'EOF'
#!/usr/bin/env python3
"""Configuration validation script for ToolCrate."""

import os
import sys

# Check if we're in a virtual environment
if not os.environ.get('VIRTUAL_ENV'):
    print("❌ Virtual environment not active!")
    print("Please activate the virtual environment first:")
    print("  source .venv/bin/activate")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed in virtual environment.")
    print("Install with: pip install PyYAML")
    sys.exit(1)

import sys
from pathlib import Path

def validate_config(config_path):
    """Validate the ToolCrate YAML configuration."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        errors = []
        warnings = []

        # Check required sections
        required_sections = ['general', 'slsk_batchdl', 'spotify', 'youtube', 'cron', 'mounts']
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")

        # Validate slsk_batchdl settings
        if 'slsk_batchdl' in config:
            slsk = config['slsk_batchdl']

            if not slsk.get('username'):
                warnings.append("Soulseek username not configured")
            if not slsk.get('password'):
                warnings.append("Soulseek password not configured")

            # Check numeric values
            numeric_fields = ['concurrent_processes', 'search_timeout', 'listen_port']
            for field in numeric_fields:
                if field in slsk and not isinstance(slsk[field], int):
                    errors.append(f"Field {field} must be an integer")

        # Validate directory paths
        if 'general' in config:
            for dir_field in ['data_directory', 'log_directory']:
                if dir_field in config['general']:
                    path = Path(config['general'][dir_field])
                    if not path.exists():
                        warnings.append(f"Directory does not exist: {path}")

        # Print results
        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"  - {error}")

        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"  - {warning}")

        if not errors and not warnings:
            print("✅ Configuration is valid!")

        return len(errors) == 0

    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        return False

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "toolcrate.yaml"
    is_valid = validate_config(config_path)
    sys.exit(0 if is_valid else 1)
EOF

chmod +x "${CONFIG_DIR}/validate-config.py"
echo -e "${GREEN}Created: ${CONFIG_DIR}/validate-config.py${NC}"

# Create README for configuration
cat > "${CONFIG_DIR}/README.md" << EOF
# ToolCrate Configuration

This directory contains the configuration files for ToolCrate.

## Files

- \`toolcrate.yaml\` - Main configuration file in YAML format
- \`sldl.conf\` - Generated configuration for slsk-batchdl compatibility
- \`docker-compose.yml\` - Docker Compose configuration
- \`.env\` - Environment variables for Docker
- \`validate-config.py\` - Configuration validation script
- \`crontabs/\` - Cron job configurations

## Usage

### Validate Configuration
\`\`\`bash
python3 validate-config.py toolcrate.yaml
\`\`\`

### Update sldl.conf from YAML
After editing \`toolcrate.yaml\`, regenerate \`sldl.conf\`:
\`\`\`bash
# Re-run the setup script to regenerate
../setup.sh
\`\`\`

### Docker Deployment
\`\`\`bash
docker-compose up -d
\`\`\`

### Cron Jobs
To activate cron jobs:
\`\`\`bash
# System-wide (requires sudo)
sudo cp crontabs/toolcrate /etc/cron.d/

# User-specific
crontab crontabs/toolcrate
\`\`\`

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

- \`lossless\` - High quality lossless audio downloads
- \`quick\` - Fast downloads with lower quality
- \`interactive\` - Interactive mode with user prompts

Use profiles with: \`slsk-tool --profile lossless <playlist>\`
EOF

echo -e "${GREEN}Created: ${CONFIG_DIR}/README.md${NC}"

# Set proper permissions
chmod 600 "${CONFIG_DIR}/toolcrate.yaml" "${CONFIG_DIR}/sldl.conf"  # Protect config files with credentials
chmod 644 "${CONFIG_DIR}/docker-compose.yml" "${CONFIG_DIR}/.env" "${CONFIG_DIR}/README.md"
if [ -f "${CRON_DIR}/toolcrate" ]; then
    chmod 644 "${CRON_DIR}/toolcrate"
fi

# Install PyYAML if needed (in virtual environment)
echo -e "\n${GREEN}Checking Python dependencies...${NC}"
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}❌ Virtual environment not active! This should not happen.${NC}"
    exit 1
fi

if ! python -c "import yaml" 2>/dev/null; then
    echo -e "${YELLOW}Installing PyYAML in virtual environment...${NC}"
    pip install PyYAML
else
    echo -e "${GREEN}PyYAML already installed in virtual environment${NC}"
fi

# Validate the generated configuration
echo -e "\n${GREEN}Validating configuration...${NC}"
if [ -n "$VIRTUAL_ENV" ] && command -v python &> /dev/null; then
    cd "$CONFIG_DIR"
    if python validate-config.py toolcrate.yaml; then
        echo -e "${GREEN}✅ Configuration validation passed!${NC}"
    else
        echo -e "${YELLOW}⚠️  Configuration validation found issues. Please review.${NC}"
    fi
    cd "$TOOLCRATE_DIR"
else
    echo -e "${YELLOW}Virtual environment not active or Python not found. Skipping configuration validation.${NC}"
fi

# Summary
echo -e "\n${BLUE}=============================${NC}"
echo -e "${BLUE}Setup Complete!${NC}"
echo -e "${BLUE}=============================${NC}"
echo
echo -e "${GREEN}Configuration files created in: ${CONFIG_DIR}${NC}"
echo -e "${GREEN}Data directory: ${data_dir}${NC}"
echo -e "${GREEN}Log directory: ${log_dir}${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Review and edit ${CONFIG_DIR}/toolcrate.yaml if needed"
echo -e "2. Run the main installation: ./install.sh"
echo -e "3. Always activate virtual environment: source .venv/bin/activate"
echo -e "4. Test your configuration: slsk-tool --help"

if [ "$setup_cron" = "true" ]; then
    echo -e "4. Activate cron jobs: sudo cp ${CRON_DIR}/toolcrate /etc/cron.d/"
fi

echo
echo -e "${YELLOW}Configuration files:${NC}"
echo -e "  📄 ${CONFIG_DIR}/toolcrate.yaml - Main YAML configuration"
echo -e "  📄 ${CONFIG_DIR}/sldl.conf - slsk-batchdl compatible config"
echo -e "  🐳 ${CONFIG_DIR}/docker-compose.yml - Docker deployment"
echo -e "  🔧 ${CONFIG_DIR}/.env - Environment variables"
echo -e "  ✅ ${CONFIG_DIR}/validate-config.py - Configuration validator"
echo -e "  📚 ${CONFIG_DIR}/README.md - Configuration documentation"

if [ "$setup_cron" = "true" ]; then
    echo -e "  ⏰ ${CRON_DIR}/toolcrate - Cron job configuration"
fi

echo
echo -e "${YELLOW}Usage examples (remember to activate virtual environment first):${NC}"
echo -e "  source .venv/bin/activate"
echo -e "  slsk-tool 'artist - song title'"
echo -e "  slsk-tool --config ${CONFIG_DIR}/sldl.conf 'playlist-url'"
echo -e "  slsk-tool --profile lossless 'album search'"
echo -e "  python config_manager.py validate"
echo -e "  docker-compose -f ${CONFIG_DIR}/docker-compose.yml up -d"

echo
echo -e "${GREEN}Happy downloading! 🎵${NC}"
