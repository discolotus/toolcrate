#!/bin/bash
# ToolCrate Configuration Generator
# Comprehensive configuration setup script for toolcrate with YAML configuration

# Set up colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command line arguments
show_help() {
    echo -e "${BLUE}ToolCrate Comprehensive Setup${NC}"
    echo -e "${BLUE}=============================${NC}"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo "       make init-config [OPTIONS]"
    echo
    echo "Options:"
    echo "  --use-poetry     Force use of Poetry for dependency management"
    echo "  --no-poetry      Force use of manual virtual environment"
    echo "  --help, -h       Show this help message"
    echo
    echo "This script creates comprehensive YAML configuration files for ToolCrate"
    echo "with full slsk-batchdl integration, cron jobs, and Docker support."
    echo
    echo "Alternative usage:"
    echo "  make init-config         # Run with auto-detection"
    echo "  make init-config-poetry  # Force Poetry usage"
    echo "  make init-config-venv    # Force virtual environment usage"
    echo
    echo "After initial setup, use 'make config' to regenerate tool configs from YAML."
    echo
    exit 0
}

# Parse arguments
USE_POETRY=""
for arg in "$@"; do
    case $arg in
        --use-poetry)
            USE_POETRY="true"
            shift
            ;;
        --no-poetry)
            USE_POETRY="false"
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

echo -e "${BLUE}ToolCrate Comprehensive Setup${NC}"
echo -e "${BLUE}=============================${NC}"
echo -e "${GREEN}Enhanced setup with Poetry integration and comprehensive slsk-batchdl configuration${NC}"
echo

# Get the absolute path of the current directory
TOOLCRATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${TOOLCRATE_DIR}/config"
CRON_DIR="${CONFIG_DIR}/crontabs"

# Function to check if Poetry is available and setup environment
setup_poetry_env() {
    echo -e "${GREEN}Setting up Poetry environment...${NC}"

    # Check if Poetry is installed
    if ! command -v poetry >/dev/null 2>&1; then
        echo -e "${YELLOW}Poetry not found. Installing Poetry...${NC}"
        curl -sSL https://install.python-poetry.org | python3 -

        # Add Poetry to PATH for current session
        export PATH="$HOME/.local/bin:$PATH"

        if ! command -v poetry >/dev/null 2>&1; then
            echo -e "${RED}❌ Poetry installation failed. Please install manually.${NC}"
            echo -e "${YELLOW}Visit: https://python-poetry.org/docs/#installation${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}Installing dependencies with Poetry...${NC}"
    poetry install --with dev

    echo -e "${GREEN}✅ Poetry environment ready!${NC}"
}

# Function to ensure virtual environment is active (fallback)
ensure_venv_fallback() {
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -f "${TOOLCRATE_DIR}/.venv/bin/activate" ]; then
            echo -e "${GREEN}Activating existing virtual environment...${NC}"
            source "${TOOLCRATE_DIR}/.venv/bin/activate"
        else
            echo -e "${GREEN}Creating Python virtual environment...${NC}"
            python3 -m venv "${TOOLCRATE_DIR}/.venv"
            source "${TOOLCRATE_DIR}/.venv/bin/activate"
            pip install --upgrade pip
            pip install PyYAML
        fi
    else
        echo -e "${GREEN}Virtual environment already active: $VIRTUAL_ENV${NC}"
    fi
}

# Determine which environment setup to use
if [ "$USE_POETRY" = "false" ]; then
    echo -e "${YELLOW}Using manual virtual environment setup (--no-poetry specified).${NC}"
    ensure_venv_fallback
elif [ "$USE_POETRY" = "true" ] || (command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]); then
    setup_poetry_env
else
    echo -e "${YELLOW}Poetry not found. Using manual virtual environment setup.${NC}"
    echo -e "${YELLOW}For better experience, install Poetry or run: ./configure_toolcrate.sh --use-poetry${NC}"
    echo -e "${YELLOW}Or use: make init-config-poetry${NC}"
    ensure_venv_fallback
fi

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

# Function to detect existing configuration values
detect_existing_config() {
    local config_file="${CONFIG_DIR}/toolcrate.yaml"
    
    if [ -f "$config_file" ]; then
        echo -e "${BLUE}Existing configuration detected. Using current values as defaults.${NC}"
        
        # Extract current values using grep and sed
        existing_data_dir=$(grep "data_directory:" "$config_file" | sed 's/.*data_directory: *\(.*\)/\1/' | tr -d '"' | head -1)
        existing_download_dir=$(grep "parent_dir:" "$config_file" | sed 's/.*parent_dir: *\(.*\)/\1/' | tr -d '"' | head -1)
        existing_library_dir=$(grep "download_dir:" "$config_file" | grep -v "parent_dir" | sed 's/.*download_dir: *\(.*\)/\1/' | tr -d '"' | head -1)
        existing_skip_dir=$(grep "skip_music_dir:" "$config_file" | sed 's/.*skip_music_dir: *\(.*\)/\1/' | tr -d '"' | head -1)
        existing_username=$(grep "username:" "$config_file" | sed 's/.*username: *\(.*\)/\1/' | tr -d '"' | head -1)
        existing_min_bitrate=$(grep "min_bitrate:" "$config_file" | sed 's/.*min_bitrate: *\(.*\)/\1/' | tr -d '"' | head -1)
        existing_max_sample_rate=$(grep "max_sample_rate:" "$config_file" | sed 's/.*max_sample_rate: *\(.*\)/\1/' | tr -d '"' | head -1)
        existing_concurrent=$(grep "concurrent_processes:" "$config_file" | sed 's/.*concurrent_processes: *\(.*\)/\1/' | tr -d '"' | head -1)
        
        # Set defaults from existing config if found, otherwise use generic defaults
        default_data_dir="${existing_data_dir:-${TOOLCRATE_DIR}/data}"
        default_download_dir="${existing_download_dir:-${default_data_dir}/downloads}"
        default_library_dir="${existing_library_dir:-${default_data_dir}/library}"
        default_skip_dir="${existing_skip_dir:-${default_data_dir}/existing-library}"
        default_username="${existing_username}"
        default_min_bitrate="${existing_min_bitrate:-320}"
        default_max_sample_rate="${existing_max_sample_rate:-192000}"
        default_concurrent="${existing_concurrent:-2}"
        
        echo -e "${GREEN}Using paths from existing configuration:${NC}"
        [ -n "$existing_data_dir" ] && echo -e "  Data: $existing_data_dir"
        [ -n "$existing_download_dir" ] && echo -e "  Downloads: $existing_download_dir"
        [ -n "$existing_library_dir" ] && echo -e "  Library: $existing_library_dir"
        echo
    else
        echo -e "${BLUE}No existing configuration found. Using generic defaults.${NC}"
        
        # Generic defaults for new installations
        default_data_dir="${TOOLCRATE_DIR}/data"
        default_download_dir="${default_data_dir}/downloads"
        default_library_dir="${default_data_dir}/library"
        default_skip_dir="${default_data_dir}/existing-library"
        default_username=""
        default_min_bitrate="320"
        default_max_sample_rate="192000"
        default_concurrent="2"
    fi
}

# Detect existing configuration
detect_existing_config

echo -e "${GREEN}Gathering configuration information...${NC}"
echo -e "${YELLOW}Press Enter to use default values shown in brackets.${NC}"
echo

# General ToolCrate Settings
echo -e "${BLUE}=== General ToolCrate Settings ===${NC}"
prompt_with_default "Project name" "toolcrate" "project_name"
prompt_with_default "Log level (debug, info, warning, error)" "info" "log_level"
prompt_with_default "Data directory" "$default_data_dir" "data_dir"
prompt_with_default "Log directory" "${TOOLCRATE_DIR}/logs" "log_dir"

# Soulseek Settings
echo -e "\n${BLUE}=== Soulseek (slsk-batchdl) Settings ===${NC}"
echo -e "${YELLOW}Basic Authentication and Directories${NC}"
prompt_with_default "Soulseek username" "$default_username" "slsk_username"
prompt_with_default "Soulseek password" "" "slsk_password"
prompt_with_default "Download directory" "$default_download_dir" "download_dir"
prompt_with_default "Music library directory (for skip checking)" "$default_skip_dir" "music_dir"
prompt_with_default "Failed downloads directory" "${data_dir}/failed" "failed_dir"

echo -e "\n${YELLOW}Audio Quality Preferences${NC}"
prompt_with_default "Preferred audio formats (comma-separated)" "flac,mp3" "preferred_formats"
prompt_with_default "Minimum bitrate" "$default_min_bitrate" "min_bitrate"
prompt_with_default "Maximum bitrate" "2500" "max_bitrate"
prompt_with_default "Maximum sample rate" "$default_max_sample_rate" "max_sample_rate"

# Set defaults for advanced audio settings (not prompted to reduce complexity)
length_tolerance="3"
strict_title="true"
strict_album="true"

echo -e "\n${YELLOW}Search and Download Settings${NC}"
prompt_with_default "Concurrent downloads" "$default_concurrent" "concurrent_downloads"

# Set defaults for advanced search settings (not prompted to reduce complexity)
search_timeout="6000"
listen_port="49998"
max_stale_time="30000"
max_retries_per_track="30"
unknown_error_retries="2"

echo -e "\n${YELLOW}Fast Search Settings${NC}"
prompt_yes_no "Enable fast search" "y" "fast_search"

# Set defaults for fast search advanced settings (not prompted to reduce complexity)
fast_search_delay="300"
fast_search_min_up_speed="1.0"

echo -e "\n${YELLOW}General Options${NC}"
prompt_yes_no "Skip existing files (don't re-download files that already exist)" "y" "skip_existing"
prompt_yes_no "Interactive mode by default (manual selection for each track)" "n" "interactive_mode"

# Set defaults for advanced general options (not prompted to reduce complexity)
write_index="true"  # Creates index file to track downloads
remove_tracks_from_source="false"  # Don't remove tracks from playlists after download
desperate_search="false"  # Don't use relaxed matching by default

# API Settings (optional - set to empty by default, can be configured later)
echo -e "\n${BLUE}=== API Settings (Optional) ===${NC}"
echo -e "${YELLOW}These can be configured later by editing config/toolcrate.yaml${NC}"
echo -e "${YELLOW}Spotify API: https://developer.spotify.com/dashboard${NC}"
echo -e "${YELLOW}YouTube API: https://console.developers.google.com${NC}"

# Set empty defaults for API settings (not prompted to reduce complexity)
spotify_client_id=""
spotify_client_secret=""
youtube_api_key=""

# Cron Job Settings
echo -e "\n${BLUE}=== Cron Job Settings ===${NC}"
prompt_yes_no "Set up automated downloads with cron" "n" "setup_cron"

if [ "$setup_cron" = "true" ]; then
    prompt_with_default "Cron schedule (e.g., '0 2 * * *' for daily at 2 AM)" "0 2 * * *" "cron_schedule"
    prompt_with_default "Playlist URL for automated downloads" "" "cron_playlist"
fi

# Mount Settings (for Docker/containerized environments)
echo -e "\n${BLUE}=== Mount and Path Settings ===${NC}"
echo -e "${YELLOW}Docker mount configuration:${NC}"
echo -e "  Default: Use relative paths (./config and ./data)"
echo -e "  Custom: Specify absolute paths for different locations"
echo ""

read -p "Use default relative paths for Docker mounts? [Y/n]: " use_relative_mounts
use_relative_mounts=${use_relative_mounts:-Y}

if [[ "$use_relative_mounts" =~ ^[Yy]$ ]]; then
    host_data_mount="./data"
    host_config_mount="./config"
    echo -e "${GREEN}Using relative paths:${NC}"
    echo -e "  Config: ./config → /config"
    echo -e "  Data: ./data → /data"
else
    prompt_with_default "Host data mount point (for Docker)" "${TOOLCRATE_DIR}/data" "host_data_mount"
    prompt_with_default "Host config mount point (for Docker)" "${TOOLCRATE_DIR}/config" "host_config_mount"
fi

echo -e "\n${GREEN}Creating configuration files...${NC}"

# Create main YAML configuration file
cat > "${CONFIG_DIR}/toolcrate.yaml" << EOF
# ToolCrate Configuration File
# Generated on $(date)
#
# This file contains comprehensive configuration for ToolCrate and its integrated tools.
# Edit this file to customize behavior, then regenerate tool-specific configs with:
#   make config-generate-sldl

# General Settings
general:
  project_name: "${project_name}"
  log_level: "${log_level}"  # debug, info, warning, error
  data_directory: "${data_dir}"  # Main data storage location
  log_directory: "${log_dir}"   # Log files location

# Soulseek (slsk-batchdl) Configuration
# Complete configuration for the slsk-batchdl tool
slsk_batchdl:
  # Authentication - Required for Soulseek network access
  username: "${slsk_username}"
  password: "${slsk_password}"

  # Directory Configuration
  parent_dir: "${download_dir}"           # Where downloaded files are saved
  skip_music_dir: "${music_dir}"          # Directory to check for existing files (skip if found)
  index_file_path: "${data_dir}/index.sldl"     # Tracks download history
  m3u_file_path: "${data_dir}/playlist.m3u"     # Generated playlist file
  failed_album_path: "${failed_dir}"      # Where failed downloads are moved
  log_file_path: "${log_dir}/sldl.log"    # Detailed download logs

  # Audio Quality Preferences (primary matching criteria)
  preferred_conditions:
    formats: [$(echo "$preferred_formats" | sed 's/,/, /g' | sed 's/\([^,]*\)/"\1"/g')]  # Preferred audio formats in order of preference
    min_bitrate: ${min_bitrate}            # Minimum acceptable bitrate (kbps)
    max_bitrate: ${max_bitrate}            # Maximum bitrate to avoid huge files
    max_sample_rate: ${max_sample_rate}    # Maximum sample rate (Hz)
    length_tolerance: ${length_tolerance}   # Acceptable difference in track length (seconds)
    strict_title: ${strict_title}          # Require exact title match
    strict_album: ${strict_album}          # Require exact album match

  # Fallback Conditions (used when preferred conditions can't be met)
  necessary_conditions:
    formats: ["mp3", "flac", "ogg", "m4a", "opus", "wav", "aac", "alac"]  # Any of these formats acceptable

  # Search and Download Performance
  concurrent_processes: ${concurrent_downloads}    # Number of simultaneous downloads
  search_timeout: ${search_timeout}               # How long to wait for search results (ms)
  listen_port: ${listen_port}                     # Port for Soulseek connections
  max_stale_time: ${max_stale_time}              # Max time to wait for stalled downloads (ms)
  max_retries_per_track: ${max_retries_per_track} # Retry attempts per failed track
  unknown_error_retries: ${unknown_error_retries} # Retries for unknown errors

  # Fast Search Configuration (optimizes search speed)
  fast_search: ${fast_search}                     # Enable fast search mode
  fast_search_delay: ${fast_search_delay}         # Delay between fast searches (ms)
  fast_search_min_up_speed: ${fast_search_min_up_speed}  # Minimum upload speed for fast search (MB/s)

  # Download Behavior
  skip_existing: ${skip_existing}                 # Skip files that already exist locally
  write_index: ${write_index}                     # Maintain download history index
  interactive_mode: ${interactive_mode}           # Prompt user for each track selection
  remove_tracks_from_source: ${remove_tracks_from_source}  # Remove tracks from playlists after download
  desperate_search: ${desperate_search}           # Use relaxed matching when strict search fails

  # Advanced Search Settings
  searches_per_time: 34
  search_renew_time: 220
  min_shares_aggregate: 2
  aggregate_length_tol: 3
  max_tracks: 999999
  offset: 0

  # Album Settings
  set_album_min_track_count: true
  set_album_max_track_count: false
  min_album_track_count: -1
  max_album_track_count: -1
  album_track_count_max_retries: 5
  parallel_album_search: false
  parallel_album_search_processes: 5

  # Additional Flags (mostly false by default)
  album: false
  aggregate: false
  album_art_only: false
  no_remove_special_chars: false
  artist_maybe_wrong: false
  yt_parse: false
  remove_ft: false
  remove_brackets: false
  reverse: false
  use_ytdlp: true
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
  extract_artist: false

  # String Settings
  time_unit: "s"
  name_format: ""
  invalid_replace_str: " "
  ytdlp_argument: "--audio-format mp3 --audio-quality 0"
  parse_title_template: ""

# API Integration Configuration
# These are optional and can be configured later for enhanced functionality

# Spotify API Configuration (for playlist and track lookup)
# Get credentials from: https://developer.spotify.com/dashboard
spotify:
  client_id: "${spotify_client_id}"        # Spotify application client ID
  client_secret: "${spotify_client_secret}" # Spotify application client secret
  token: ""                                # OAuth token (auto-generated)
  refresh_token: ""                        # OAuth refresh token (auto-generated)

# YouTube API Configuration (for video and playlist processing)
# Get API key from: https://console.developers.google.com
youtube:
  api_key: "${youtube_api_key}"            # YouTube Data API v3 key

# Wishlist Configuration (for automated wishlist downloads)
wishlist:
  enabled: true
  file_path: "config/wishlist.txt"
  download_dir: "${default_library_dir}"          # Downloads go to library, not downloads
  index_in_playlist_folder: true               # Index files stored in each playlist folder
  check_existing_for_better_quality: true     # Re-check existing files for upgrades
  slower_search: true                          # Allow thorough searches
  post_processing:
    enabled: true                              # Enable post-processing
    transcode_opus: true                       # Convert opus files
    output_format: "flac"                      # Output format: "flac" or "aac"
    aac_bitrate: 320                          # AAC bitrate in kbps (when output_format is "aac")
    flac_compression_level: 8                  # FLAC compression level 0-8 (when output_format is "flac")
    update_index: true                         # Update sldl index after transcoding
    delete_original_opus: true                 # Remove original opus files after transcoding
  settings:
    # Override base settings for wishlist downloads
    preferred_conditions:
      formats: ["flac", "wav", "mp3"]          # Prefer lossless for wishlist
      min_bitrate: 320                         # Higher quality for wishlist
    desperate_search: true                     # Use relaxed matching for wishlist
    skip_existing: true                        # Skip existing files by default
    skip_check_pref_cond: true                # Enable quality checking for upgrades
    listen_port: 49998                        # Use same port as main config

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
    host_path: "${data_dir}"
    container_path: "/data"
    description: "Data directory mount (index files, logs, metadata)"
  downloads:
    host_path: "${download_dir}"
    container_path: "/downloads"
    description: "Regular downloads directory mount"
  library:
    host_path: "${default_library_dir}"
    container_path: "/library"
    description: "Library/wishlist downloads directory mount"
  config:
    host_path: "${CONFIG_DIR}"
    container_path: "/config"
    description: "Configuration directory mount"

# Environment Variables
environment:
  TZ: "UTC"
  PUID: 1000
  PGID: 1000

# Profiles (can be activated with --profile flag)
# Usage: slsk-tool --profile <profile_name> <search_term>
profiles:
  lossless:
    description: "High quality lossless audio downloads"
    settings:
      preferred_conditions:
        formats: ["flac", "wav", "alac"]  # Lossless formats only
        min_bitrate: 1000                 # High bitrate requirement
        max_sample_rate: 192000           # Support high-res audio

  quick:
    description: "Fast downloads with standard quality"
    settings:
      preferred_conditions:
        formats: ["mp3"]                  # MP3 only for speed
        min_bitrate: 128                  # Lower quality for speed
        max_bitrate: 320                  # Standard MP3 range
      fast_search: true                   # Enable fast search
      desperate_search: true              # Use relaxed matching

  interactive:
    description: "Manual selection mode with user prompts"
    settings:
      interactive_mode: true              # Prompt for each track
      max_stale_time: 9999999            # Never timeout in interactive mode
EOF

echo -e "${GREEN}Created: ${CONFIG_DIR}/toolcrate.yaml${NC}"

# Generate sldl.conf file for slsk-batchdl compatibility
echo -e "${GREEN}Generating sldl.conf for slsk-batchdl compatibility...${NC}"

cat > "${CONFIG_DIR}/sldl.conf" << EOF
# sldl.conf - Generated from toolcrate.yaml on $(date)
# This file is automatically generated. Edit toolcrate.yaml instead.
#
# Configuration file for slsk-batchdl (Soulseek batch downloader)
# For more information: https://github.com/fiso64/slsk-batchdl

# Authentication - Required for Soulseek network access
username = ${slsk_username}
password = ${slsk_password}

# Directory Configuration
parent-dir = ${download_dir}              # Main download directory
skip-music-dir = ${music_dir}             # Check this directory to skip existing files
index-path = ${data_dir}/index.sldl       # Download history tracking
m3u-path = ${data_dir}/playlist.m3u       # Generated playlist file
failed-album-path = ${failed_dir}         # Failed downloads location
log-path = ${log_dir}/sldl.log           # Detailed logging

# Audio Quality Preferences
pref-format = ${preferred_formats}                    # Preferred audio formats (comma-separated)
pref-min-bitrate = ${min_bitrate}                     # Minimum acceptable bitrate (kbps)
pref-max-bitrate = ${max_bitrate}                     # Maximum bitrate to avoid huge files
pref-max-sample-rate = ${max_sample_rate}             # Maximum sample rate (Hz)
pref-length-tol = ${length_tolerance}                 # Acceptable track length difference (seconds)
pref-strict-title = ${strict_title}                   # Require exact title match
pref-strict-album = ${strict_album}                   # Require exact album match

# Search and Download Performance
concurrent-processes = ${concurrent_downloads}        # Number of simultaneous downloads
search-timeout = ${search_timeout}                    # Search timeout (milliseconds)
listen-port = ${listen_port}                          # Soulseek connection port
max-stale-time = ${max_stale_time}                   # Max time for stalled downloads (ms)
max-retries-per-track = ${max_retries_per_track}     # Retry attempts per failed track
unknown-error-retries = ${unknown_error_retries}     # Retries for unknown errors

# Fast Search Configuration
fast-search = ${fast_search}                          # Enable optimized search mode
fast-search-delay = ${fast_search_delay}              # Delay between searches (ms)
fast-search-min-up-speed = ${fast_search_min_up_speed} # Min upload speed for fast search (MB/s)

# Download Behavior
skip-existing = ${skip_existing}                      # Skip files that already exist locally
write-index = ${write_index}                          # Maintain download history index
interactive = ${interactive_mode}                     # Prompt user for each track selection
remove-tracks-from-source = ${remove_tracks_from_source} # Remove tracks from playlists after download
desperate-search = ${desperate_search}                # Use relaxed matching when strict search fails

# Advanced Settings
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
#
# Mount paths: ${host_config_mount} → /config, ${host_data_mount} → /data
# Run from project root directory when using relative paths

services:
  sldl:
    build:
      context: ../src/slsk-batchdl
      dockerfile: Dockerfile
    image: slsk-batchdl:latest
    container_name: sldl
    environment:
      - TZ=UTC
      - PUID=1000
      - PGID=1000
    volumes:
      - ${host_config_mount}:/config
      - ${host_data_mount}:/data
    ports:
      - "49998:49998"
    restart: unless-stopped
    networks:
      - toolcrate-network

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
        required_sections = ['general', 'slsk_batchdl', 'spotify', 'youtube', 'wishlist', 'cron', 'mounts']
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
# Update tool configs from YAML
make config

# Or re-run the configuration script to regenerate everything
../configure_toolcrate.sh
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

# Install Python dependencies
echo -e "\n${GREEN}Checking Python dependencies...${NC}"

# Check if we're using Poetry
if command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}Using Poetry for dependency management...${NC}"

    # Ensure dependencies are installed
    if ! poetry run python -c "import yaml" 2>/dev/null; then
        echo -e "${YELLOW}Installing dependencies with Poetry...${NC}"
        poetry install --with dev
    else
        echo -e "${GREEN}Dependencies already installed with Poetry${NC}"
    fi
else
    # Fallback to pip in virtual environment
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
fi

# Validate the generated configuration
echo -e "\n${GREEN}Validating configuration...${NC}"

# Use Poetry if available, otherwise use virtual environment
if command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    cd "$CONFIG_DIR"
    if poetry run python validate-config.py toolcrate.yaml; then
        echo -e "${GREEN}✅ Configuration validation passed!${NC}"
    else
        echo -e "${YELLOW}⚠️  Configuration validation found issues. Please review.${NC}"
    fi
    cd "$TOOLCRATE_DIR"
elif [ -n "$VIRTUAL_ENV" ] && command -v python &> /dev/null; then
    cd "$CONFIG_DIR"
    if python validate-config.py toolcrate.yaml; then
        echo -e "${GREEN}✅ Configuration validation passed!${NC}"
    else
        echo -e "${YELLOW}⚠️  Configuration validation found issues. Please review.${NC}"
    fi
    cd "$TOOLCRATE_DIR"
else
    echo -e "${YELLOW}Poetry or virtual environment not available. Skipping configuration validation.${NC}"
    echo -e "${YELLOW}Run manually: poetry run python config/validate-config.py config/toolcrate.yaml${NC}"
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

# Show appropriate environment activation instructions
if command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    echo -e "3. Use Poetry for commands: poetry run <command>"
    echo -e "   Or activate manually: source \$(poetry env info --path)/bin/activate"
    echo -e "4. Test your configuration: poetry run slsk-tool --help"
else
    echo -e "3. Always activate virtual environment: source .venv/bin/activate"
    echo -e "4. Test your configuration: slsk-tool --help"
fi

if [ "$setup_cron" = "true" ]; then
    echo -e "5. Activate cron jobs: sudo cp ${CRON_DIR}/toolcrate /etc/cron.d/"
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
echo -e "${YELLOW}Usage examples:${NC}"

# Show Poetry examples if available
if command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    echo -e "${BLUE}Using Poetry (recommended):${NC}"
    echo -e "  poetry run slsk-tool 'artist - song title'"
    echo -e "  poetry run slsk-tool --config ${CONFIG_DIR}/sldl.conf 'playlist-url'"
    echo -e "  poetry run slsk-tool --profile lossless 'album search'"
    echo -e "  poetry run python config_manager.py validate"
    echo -e "  make test  # Run all tests"
    echo -e "  make setup  # Setup Poetry environment"
    echo
fi

echo -e "${BLUE}Using virtual environment:${NC}"
echo -e "  source .venv/bin/activate"
echo -e "  slsk-tool 'artist - song title'"
echo -e "  slsk-tool --config ${CONFIG_DIR}/sldl.conf 'playlist-url'"
echo -e "  slsk-tool --profile lossless 'album search'"
echo -e "  python config_manager.py validate"

echo
echo -e "${BLUE}Docker deployment:${NC}"
if [[ "$host_config_mount" == "./config" ]]; then
    echo -e "  ${YELLOW}Note: Using relative paths - run from project root directory${NC}"
    echo -e "  cd ${TOOLCRATE_DIR}"
fi
echo -e "  docker-compose -f ${CONFIG_DIR}/docker-compose.yml up -d"

echo
echo -e "${GREEN}Happy downloading! 🎵${NC}"
