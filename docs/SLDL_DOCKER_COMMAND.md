# SLDL Docker Command

The `toolcrate sldl` command allows you to run slsk-batchdl commands directly in the docker container without having to manually manage docker commands.

## Usage

```bash
# Enter interactive shell in container
toolcrate sldl

# Run specific command in container
toolcrate sldl <command to run in docker container>
```

## Examples

### Interactive Shell

```bash
# Enter interactive shell in the container
toolcrate sldl

# Once inside the container, you can run any commands:
# sldl -a "Artist Name" -t "Track Name"
# sldl --help
# ls /config
# cat /config/sldl.conf
# exit
```

**Note**: The interactive shell uses `/bin/bash` and gives you full access to the container environment. This is useful for debugging, exploring the container, or running multiple commands in sequence.

### Direct Command Execution

```bash
# Download a specific track
toolcrate sldl -a "Artist Name" -t "Track Name"

# Download an album
toolcrate sldl -a "Artist Name" -b "Album Name"

# Download from a playlist URL
toolcrate sldl "https://open.spotify.com/playlist/..."

# Show slsk-batchdl help
toolcrate sldl --help

# Check version
toolcrate sldl --version
```

**Note**: The config file argument (`-c /config/sldl.conf`) is automatically included in all commands, so you don't need to specify it manually.

### Advanced Usage

```bash
# Download with specific quality settings
toolcrate sldl -a "Artist Name" -t "Track Name" --min-bitrate 320

# Download from a file list
toolcrate sldl --input /config/download-list.txt

# Download with custom output directory
toolcrate sldl -a "Artist Name" -t "Track Name" --output /data/music
```

## How It Works

1. **Container Detection**: The command automatically searches for containers with 'sldl' in the name
2. **Multiple Container Warning**: If multiple containers are found, it warns you and uses the first one
3. **Auto-Start**: If no container is running, it will attempt to start it using docker-compose
4. **Config File**: Automatically includes `-c /config/sldl.conf` in all commands for proper docker execution
5. **Command Execution**: All arguments are passed to the slsk-batchdl binary inside the container
6. **Volume Mounts**: The container has access to your config and data directories as configured in docker-compose.yml

## Prerequisites

- Docker must be installed and running
- Docker Compose must be available (either `docker-compose` or `docker compose`)
- The docker-compose.yml file must exist in the config directory
- The slsk-batchdl docker image must be available

## Building the Docker Image

If you need to rebuild the slsk-batchdl Docker image (for example, after making changes to the Dockerfile or updating the source code), you can use the convenient make command:

```bash
# Rebuild the slsk-batchdl Docker image
make buildimage
```

This command:
- Rebuilds the image from scratch (using `--no-cache`)
- Uses the current state of the Dockerfile and source code
- Ensures any changes you've made are included in the new image
- Automatically checks that the docker-compose.yml file exists

### When to Rebuild the Image

You should rebuild the image when:
- You've made changes to the slsk-batchdl source code
- You've updated the Dockerfile
- You've pulled updates from the slsk-batchdl repository
- You're experiencing issues that might be resolved with a fresh build

### Manual Docker Commands

If you prefer to use Docker commands directly:

```bash
# Navigate to config directory and rebuild
cd config
docker-compose build --no-cache sldl

# Or rebuild and restart the service
docker-compose up --build --force-recreate sldl
```

## Error Handling

The command provides helpful error messages for common issues:

- **Docker not installed**: "Error: Docker is not installed or not available in PATH."
- **Missing compose file**: "Error: Docker Compose file not found at config/docker-compose.yml"
- **Container start failure**: Shows the actual docker error message
- **Container not found**: "Error response from daemon: No such container: sldl"

## Configuration

The command uses the existing docker-compose.yml configuration in the config directory. Make sure your docker-compose.yml includes:

```yaml
services:
  sldl:
    image: slsk-batchdl:latest
    container_name: sldl
    volumes:
      - ./config:/config
      - ./data:/data
    # ... other configuration
```

## Integration with ToolCrate

The `sldl` command is fully integrated with the ToolCrate CLI:

```bash
# List all available tools (includes sldl)
toolcrate info

# Get help for the sldl command
toolcrate sldl --help

# Use alongside other ToolCrate commands
toolcrate info
toolcrate sldl -a "Artist" -t "Track"
```

## Troubleshooting

### Multiple Containers Warning

If you see a warning like:
```
Warning: Found multiple containers with 'sldl' in name: container1, container2
Using the first one: container1
```

This means you have multiple containers with 'sldl' in their names. The command will use the first one found. To avoid this:
1. Stop unused containers: `docker stop <container-name>`
2. Remove unused containers: `docker rm <container-name>`
3. Or specify which container to use by ensuring only one is running

### Container Won't Start

If the container fails to start, check:
1. Docker is running
2. The slsk-batchdl image is available: `docker images | grep slsk-batchdl`
3. No port conflicts with other containers
4. Sufficient disk space and memory

If the image is missing or outdated, rebuild it:
```bash
make buildimage
```

### Permission Issues

If you encounter permission issues:
1. Check that the volume mounts in docker-compose.yml are correct
2. Ensure the directories exist and are writable
3. Check the PUID/PGID settings in the container configuration

### Command Not Found

If `toolcrate sldl` is not recognized:
1. Make sure you've installed the updated ToolCrate package
2. Verify the installation: `poetry install` or `pip install -e .`
3. Check that the CLI is working: `toolcrate --help`
