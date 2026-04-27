# ToolCrate Configuration Setup Guide

This guide explains how to use the enhanced ToolCrate configuration system with comprehensive YAML configuration and Poetry integration.

## Quick Start

```bash
# Recommended: Use the Make command for initial setup
make init-config

# Alternative: Direct script execution
./configure_toolcrate.sh

# After initial setup, regenerate tool configs from YAML
make config
```

## Configuration Files

The configuration system creates several descriptively named files:

### Primary Configuration Script
- **`configure_toolcrate.sh`** - Main configuration generator script
  - Interactive CLI prompts with sensible defaults
  - Poetry integration with virtual environment fallback
  - Comprehensive slsk-batchdl configuration options
  - Automatic generation of compatible configuration files

### Generated Configuration Files
- **`config/toolcrate.yaml`** - Main YAML configuration file
- **`config/sldl.conf`** - Generated slsk-batchdl compatible configuration
- **`config/docker-compose.yml`** - Docker deployment configuration
- **`config/.env`** - Environment variables for Docker
- **`config/validate-config.py`** - Configuration validation script
- **`config/README.md`** - Detailed configuration documentation

### Testing and Validation
- **`tests/test_config_generator.sh`** - Test script for the configuration generator
- **`src/toolcrate/config/manager.py`** - Python configuration management utility

## Make Commands

The Makefile provides convenient commands for configuration management:

### Configuration Commands
```bash
make init-config              # Run interactive configuration setup (first time)
make config                   # Update tool configs from YAML (regenerate)
make config-validate          # Validate existing configuration
make config-show             # Show current configuration
```

### Initial Configuration Options
```bash
make init-config-poetry       # Force Poetry usage for initial setup
make init-config-venv         # Force virtual environment usage for initial setup
```

## Features

### 🎯 Enhanced slsk-batchdl Integration
- **Complete configuration coverage** - All slsk-batchdl options supported
- **Audio quality preferences** - Bitrate, format, and quality settings
- **Advanced search settings** - Timeout, retries, and performance tuning
- **Fast search configuration** - Optimized download speeds
- **Profile support** - Pre-configured quality profiles (lossless, quick, interactive)

### 🔧 Poetry Integration
- **Automatic Poetry detection** - Uses Poetry when available
- **Virtual environment fallback** - Works without Poetry
- **Dependency management** - Handles PyYAML and other dependencies
- **Make command integration** - Convenient `make config` command

### 📋 Comprehensive Configuration
- **YAML format** - Modern, human-readable configuration
- **Interactive prompts** - Guided setup with defaults
- **Validation** - Built-in configuration validation
- **Docker support** - Ready-to-use Docker Compose configuration
- **Cron integration** - Automated download scheduling

### 🛡️ Robust Error Handling
- **Command-line arguments** - `--use-poetry`, `--no-poetry`, `--help`
- **Environment detection** - Automatic Poetry/venv detection
- **Validation checks** - Configuration syntax and completeness
- **Clear error messages** - Helpful troubleshooting information

## Usage Examples

### Basic Configuration Setup
```bash
# Interactive setup with auto-detection (first time)
make init-config

# Follow the prompts to configure:
# - Project settings and directories
# - Soulseek credentials and preferences
# - Audio quality and format preferences
# - API keys (Spotify, YouTube)
# - Cron job scheduling
# - Docker mount points
```

### Advanced Usage
```bash
# Force Poetry usage
./configure_toolcrate.sh --use-poetry

# Force virtual environment usage
./configure_toolcrate.sh --no-poetry

# Show help
./configure_toolcrate.sh --help
```

### Configuration Management
```bash
# Validate configuration
make config-validate

# Update tool configs from YAML (regenerate sldl.conf, etc.)
make config

# Show current configuration
make config-show

# Test the configuration generator
./test_config_generator.sh
```

## Configuration Sections

### General Settings
- Project name and logging configuration
- Data and log directory paths
- Environment variables

### Soulseek (slsk-batchdl) Settings
- **Authentication**: Username and password
- **Directories**: Download, music library, failed downloads
- **Audio Preferences**: Formats, bitrate, sample rate, quality matching
- **Search Settings**: Timeouts, retries, concurrent downloads
- **Fast Search**: Optimized search configuration
- **Advanced Options**: All slsk-batchdl flags and parameters

### API Integrations
- **Spotify**: Client ID and secret for playlist integration
- **YouTube**: API key for video/playlist processing

### Automation
- **Cron Jobs**: Scheduled download configuration
- **Docker**: Container deployment settings

### Profiles
- **Lossless**: High-quality FLAC/WAV downloads
- **Quick**: Fast MP3 downloads
- **Interactive**: Manual selection mode

## Troubleshooting

### Common Issues
```bash
# Configuration validation errors
make config-validate

# Regenerate configuration files
make init-config

# Update tool configs from YAML
make config

# Test the configuration generator
./test_config_generator.sh

# Check Poetry environment
poetry env info

# Manual virtual environment activation
source .venv/bin/activate
```

### File Permissions
The configuration generator automatically sets appropriate permissions:
- Configuration files: `600` (read/write for owner only)
- Scripts: `755` (executable)
- Documentation: `644` (readable)

## Migration from Old Setup

If you have an existing setup, the new configuration system:
- **Preserves existing configurations** - Prompts before overwriting
- **Validates settings** - Checks for completeness and correctness
- **Provides migration path** - Clear upgrade instructions
- **Maintains compatibility** - Works with existing tools

## Next Steps

After running the configuration generator:

1. **Review generated files** in the `config/` directory
2. **Test your configuration** with `make config-validate`
3. **Run the main installation** with `./install.sh`
4. **Test tool functionality** with `poetry run slsk-tool --help`
5. **Set up automation** if cron jobs were configured

The configuration system provides a solid foundation for using ToolCrate with optimal settings for your specific needs.
