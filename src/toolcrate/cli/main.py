#!/usr/bin/env python3
"""Main CLI entry point for ToolCrate."""

import sys
import click

from .wrappers import run_sldl_docker_command, run_shazam, run_slsk
from .schedule import schedule
from .wishlist_run import wishlist_run
from .queue import queue


@click.group()
@click.version_option()
@click.option('--build', is_flag=True, help='Rebuild docker containers before running commands')
@click.pass_context
def main(ctx, build):
    """ToolCrate - A unified tool suite for music management and processing."""
    # Store the build flag in the context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj['build'] = build


@main.command()
def info():
    """Show information about available tools."""
    click.echo("ToolCrate - Available Tools:")
    click.echo("  - slsk-tool: Soulseek batch download tool")
    click.echo("  - shazam-tool: Music recognition tool")
    click.echo("  - mdl-tool: Music metadata utility")
    click.echo("  - sldl: Run commands in slsk-batchdl docker container")
    click.echo("  - schedule: Manage scheduled downloads and cron jobs")
    click.echo("    • toolcrate schedule add -s '<cron>' [--type wishlist|download] - Add scheduled job")
    click.echo("    • toolcrate schedule hourly/daily [--type wishlist|download] - Easy scheduling")
    click.echo("    • toolcrate schedule edit -n <name> -s '<cron>' - Edit existing schedule")
    click.echo("    • toolcrate schedule remove -n <name> - Remove scheduled job")
    click.echo("    • toolcrate schedule list - Show all scheduled jobs")
    click.echo("  - wishlist-run: View logs and status from scheduled wishlist runs")
    click.echo("    • toolcrate wishlist-run logs - Show recent logs")
    click.echo("    • toolcrate wishlist-run status - Show run status and summary")
    click.echo("    • toolcrate wishlist-run tail - Follow logs in real-time")
    click.echo("  - queue: Manage download queue for individual links")
    click.echo("    • toolcrate queue add <link> - Add link to queue")
    click.echo("    • toolcrate queue list - Show current queue")
    click.echo("    • toolcrate queue run - Process queue immediately")


@main.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.pass_context
def sldl(ctx):
    """Run commands in the slsk-batchdl docker container.

    When called without arguments, enters an interactive shell in the container.
    When called with arguments, executes the slsk-batchdl command with those arguments.
    The config file path (-c /config/sldl.conf) is automatically included.

    Examples:
        toolcrate sldl                           # Enter interactive shell
        toolcrate --build sldl                   # Rebuild container and enter shell
        toolcrate sldl --help                    # Show slsk-batchdl help
        toolcrate sldl -a "artist" -t "track"    # Download specific track
        toolcrate --build sldl <playlist-url>    # Rebuild container and download from playlist
        toolcrate sldl --version                 # Show slsk-batchdl version
    """
    # Get the build flag from the parent context
    build_flag = ctx.obj.get('build', False) if ctx.obj else False

    # Pass all arguments to the docker command runner
    run_sldl_docker_command(ctx.params, ctx.args, build=build_flag)


# Add the schedule command group
main.add_command(schedule)

# Add the wishlist-run command group
main.add_command(wishlist_run)

# Add the queue command group
main.add_command(queue)


@main.group(name="slsk-tool")
def slsk_tool_group():
    """Run Soulseek batch download tool."""
    pass

@slsk_tool_group.command(name="setup")
def slsk_tool_setup():
    """Setup the Soulseek batch download tool container and credentials."""
    click.echo("Setting up Soulseek batch download tool...")
    
    # Check Docker is installed
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        click.echo("Docker is installed and available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("Error: Docker is not installed or not in PATH")
        click.echo("Please install Docker Desktop and try again")
        return 1
    
    # Ensure config directory exists
    user_config_dir = Path.home() / ".config" / "sldl"
    os.makedirs(user_config_dir, exist_ok=True)
    user_conf_file_path = user_config_dir / "sldl.conf"
    
    # Prompt for credentials
    click.echo("Please enter your Soulseek credentials:")
    username = click.prompt("Soulseek username", type=str)
    password = click.prompt("Soulseek password", type=str, hide_input=True)
    
    # Create or update config file
    config_lines = []
    if user_conf_file_path.exists():
        with open(user_conf_file_path, 'r') as f:
            for line in f:
                if not line.strip().startswith("username =") and not line.strip().startswith("password ="):
                    config_lines.append(line.strip())
    else:
        # Basic config if none exists
        config_lines = [
            "# Default sldl.conf for toolcrate",
            "download-dir = /downloads",
            "interactive-mode = true",
            "fast-search = true",
            "max-retries-per-track = 20",
            "min-bitrate = 192",
            'name-format = "[%(artist)s] %(title)s"',
            "listen-port = 50000"
        ]
    
    # Add credentials
    config_lines.append(f"username = {username}")
    config_lines.append(f"password = {password}")
    
    # Write config file
    with open(user_conf_file_path, 'w') as f:
        f.write("\n".join(config_lines))
    
    click.echo(f"Credentials saved to {user_conf_file_path}")
    
    # Setup download directory
    default_download_dir = os.path.expanduser("~/Music/downloads")
    download_dir = click.prompt(
        "Enter download directory path",
        default=default_download_dir,
        type=str
    )
    
    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    click.echo(f"Download directory {download_dir} created/verified")
    
    # Ask if user wants to recreate container
    if click.confirm("Do you want to build and start the container now?", default=True):
        root_dir = get_project_root()
        success = recreate_slsk_container(root_dir)
        if success:
            click.echo("Container setup complete - you can now use 'soulseek run' commands")
        else:
            click.echo("Container setup failed - please check Docker is running and try again")
            return 1
    
    return 0

@slsk_tool_group.command(name="run", context_settings=dict(ignore_unknown_options=True))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def slsk_tool_run(args):
    """Run sldl with the provided arguments."""
    sys.argv = [sys.argv[0]] + list(args)
    run_slsk()

@slsk_tool_group.command(name="batch-download")
@click.option("--playlist-file", type=click.Path(exists=True), help="Path to file containing playlist URLs")
@click.option("--config-file", type=click.Path(), help="Path to sldl config file (defaults to sldl.conf in project root)")
@click.option("--log-file", type=click.Path(), help="Name of log file (will be saved in the logs directory)")
def batch_download(playlist_file, config_file, log_file):
    """Process a list of Spotify playlists from a text file and download them using sldl."""
    import time
    import logging
    from pathlib import Path
    import os
    import subprocess
    import re  # For extracting playlist IDs
    from datetime import datetime
    import requests
    
    # Configure logging
    logs_dir = Path("logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    if not log_file:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_file = logs_dir / f"batch_download_{timestamp}.log"
    else:
        log_file = logs_dir / log_file
    
    # Set up logging to file
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Log start time
    logging.info(f"=== Batch download started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # Get project directory
    project_dir = Path.cwd()
    
    # Configure paths
    if not playlist_file:
        playlist_file = project_dir / "playlists.txt"
    else:
        playlist_file = Path(playlist_file)
    
    if not config_file:
        config_file = project_dir / "sldl.conf"
    else:
        config_file = Path(config_file)
    
    # Try default config location if specified file doesn't exist
    default_config = project_dir / "sldl.conf"
    
    # Output configuration
    click.echo(f"Batch download configuration:")
    click.echo(f"  Playlist file: {playlist_file}")
    click.echo(f"  Config file: {config_file}")
    click.echo(f"  Log file: {log_file}")
    
    # Ensure logs directory exists
    logs_dir = project_dir / "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Set log file path in logs directory
    if log_file:
        # If user specified a log file, use just the filename part and put it in logs directory
        log_filename = os.path.basename(log_file)
        log_file = logs_dir / log_filename
    else:
        # Default log file with timestamp to avoid overwriting
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_file = logs_dir / f"batch_download_{timestamp}.log"
    
    not_found_file = logs_dir / "not_found_songs.txt"
    
    click.echo(f"Log file will be saved to: {log_file}")
    
    # Check if we need to create a default config file
    if not config_file.exists() and not default_config.exists():
        click.echo(f"No config file found. Creating template config at {default_config}")
        
        # Create a template config file
        template_config = """# sldl config file
# Generated automatically by toolcrate

# Soulseek credentials
username = your_username
password = your_password

# Download settings
download_dir = /downloads
timeout = 30
max_results = 25
download_timeout = 300
min_bitrate = 320
max_size = 20

# Logging
log_level = INFO
"""
        try:
            with open(default_config, "w") as f:
                f.write(template_config)
            
            config_file = default_config
            click.echo(f"Created template config file at {default_config}")
            click.echo("Please edit this file to add your Soulseek credentials before running again.")
            return 1
        except Exception as e:
            click.echo(f"Error creating config file: {e}")
            return 1
    
    # Ensure config file exists - first check the specified path, then try default location
    if not config_file.exists() and config_file != default_config:
        click.echo(f"Warning: Specified config file {config_file} not found, trying default location {default_config}")
        if default_config.exists():
            config_file = default_config
            click.echo(f"Using default config file at {default_config}")
        else:
            click.echo(f"Error: Config file not found at {default_config}")
            return 1
    elif not config_file.exists():
        click.echo(f"Error: Config file not found at {config_file}")
        return 1
    
    click.echo(f"Using config file: {config_file}")
    
    # Ensure config directory exists in slsk-batchdl
    slsk_config_dir = project_dir / "src" / "slsk-batchdl" / "config"
    os.makedirs(slsk_config_dir, exist_ok=True)
    
    # Create a symlink or copy the config file to the slsk-batchdl/config directory
    slsk_config_file = slsk_config_dir / "sldl.conf"
    
    # Always ensure we have the latest config file in the Docker config directory
    if os.path.exists(slsk_config_file):
        if os.path.islink(slsk_config_file):
            # Remove existing symlink
            os.remove(slsk_config_file)
        else:
            # Backup existing file only if it's different from our source
            if os.path.exists(config_file) and not os.path.samefile(slsk_config_file, config_file):
                backup_file = slsk_config_file.with_suffix('.conf.bak')
                try:
                    shutil.copy2(slsk_config_file, backup_file)
                    click.echo(f"Backed up existing config to {backup_file}")
                except Exception as e:
                    click.echo(f"Warning: Could not backup existing config: {e}")
            os.remove(slsk_config_file)
    
    # Copy the config file to the Docker directory
    try:
        # Try to create a symlink first (works on Linux/macOS)
        absolute_config_path = os.path.abspath(config_file)
        click.echo(f"Using config from: {absolute_config_path}")
        
        try:
            os.symlink(absolute_config_path, slsk_config_file)
            click.echo(f"Created symlink from {config_file} to {slsk_config_file}")
        except (OSError, NotImplementedError):
            # Fallback to copy if symlink fails (e.g., on Windows)
            shutil.copy2(config_file, slsk_config_file)
            click.echo(f"Copied {config_file} to {slsk_config_file}")
    except Exception as e:
        click.echo(f"Warning: Could not link/copy config file to Docker directory: {e}")
        click.echo("Will attempt to pass config directly to Docker container")
    
    # Check if Docker is running
    try:
        docker_check = subprocess.run(["pgrep", "-f", "docker"], capture_output=True)
        if docker_check.returncode != 0:
            click.echo("Docker daemon is not running. Attempting to start it...")
            subprocess.run(["open", "-a", "Docker"])
            
            # Wait for Docker to start
            for i in range(1, 13):
                time.sleep(5)
                docker_check = subprocess.run(["pgrep", "-f", "docker"], capture_output=True)
                if docker_check.returncode == 0:
                    click.echo("Docker daemon started successfully")
                    break
                click.echo(f"Waiting for Docker to start... ({i}/12)")
            
            if docker_check.returncode != 0:
                click.echo("Error: Failed to start Docker daemon")
                return 1
            
            # Give Docker a moment to fully initialize
            time.sleep(10)
    except Exception as e:
        click.echo(f"Error checking Docker status: {e}")
        return 1
    
    # Check if Docker container is running
    try:
        # First check if the container exists (regardless of state)
        docker_container_ls = subprocess.run(
            ["docker", "container", "ls", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        # Check if any container with "sldl" in the name exists
        existing_container = False
        container_name = None
        for line in docker_container_ls.stdout.splitlines():
            if "sldl" in line.lower():
                existing_container = True
                container_name = line.strip()
                break
        
        if existing_container:
            click.echo(f"Found existing sldl container: {container_name}")
            
            # Check if it's running
            docker_ps = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            
            container_running = container_name in docker_ps.stdout
            
            if not container_running:
                click.echo(f"Starting container using docker compose...")
                # Find the docker-compose directory
                root_dir = get_project_root()
                compose_dir = root_dir / "src" / "slsk-batchdl"
                
                # Change directory and run docker compose up
                current_dir = os.getcwd()
                os.chdir(compose_dir)
                
                subprocess.run(["docker", "compose", "up", "-d"], check=True)
                
                # Restore original directory
                os.chdir(current_dir)
                
                click.echo("Container started with docker compose up")
                time.sleep(5)  # Give it time to start
        else:
            click.echo("No existing sldl container found, creating a new one...")
            
            # Check if slsk-batchdl image exists
            docker_images = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}"],
                capture_output=True,
                text=True
            )
            
            # Look for various possible image names
            image_names = ["slsk-batchdl", "slsk-batchdl-sldl", "sldl"]
            image_exists = False
            image_name = None
            
            for name in image_names:
                if name in docker_images.stdout:
                    image_exists = True
                    image_name = name
                    break
            
            if not image_exists:
                # Try to build the image
                click.echo("No sldl image found. Attempting to build from Dockerfile...")
                
                dockerfile_path = project_dir / "src" / "slsk-batchdl" / "Dockerfile"
                if os.path.exists(dockerfile_path):
                    try:
                        click.echo(f"Building Docker image from {dockerfile_path}...")
                        subprocess.run(
                            ["docker", "build", "-t", "slsk-batchdl", "-f", str(dockerfile_path), "."],
                            cwd=str(project_dir / "src" / "slsk-batchdl"),
                            check=True
                        )
                        image_name = "slsk-batchdl"
                        click.echo("Successfully built Docker image")
                    except subprocess.CalledProcessError as e:
                        click.echo(f"Error building Docker image: {e}")
                        return 1
                else:
                    click.echo(f"Error: Dockerfile not found at {dockerfile_path}")
                    click.echo("Please build the Docker image manually with: docker build -t slsk-batchdl ./src/slsk-batchdl")
                    return 1
            
            # Prepare directories
            slsk_config_dir = project_dir / "src" / "slsk-batchdl" / "config"
            os.makedirs(slsk_config_dir, exist_ok=True)
            
            data_dir = project_dir / "src" / "slsk-batchdl" / "data"
            os.makedirs(data_dir, exist_ok=True)
            
            # Start the container using docker run
            container_name = "sldl"
            click.echo(f"Starting container {container_name} with image {image_name}...")
            
            run_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", "50000:50000",  # Port forwarding for Soulseek
                "-v", f"{os.path.abspath(slsk_config_dir)}:/config",
                "-v", f"{os.path.abspath(data_dir)}:/data",
                image_name
            ]
            
            try:
                subprocess.run(run_cmd, check=True)
                click.echo(f"Container {container_name} started successfully")
                time.sleep(5)  # Give it time to initialize
            except subprocess.CalledProcessError as e:
                # Check if container already exists but couldn't be started
                click.echo(f"Error starting container: {e}")
                click.echo("Trying to remove container if it exists but is not running...")
                
                try:
                    subprocess.run(["docker", "rm", container_name], check=False)
                    # Try running it again
                    subprocess.run(run_cmd, check=True)
                    click.echo(f"Container {container_name} started successfully on second attempt")
                    time.sleep(5)
                except subprocess.CalledProcessError as e2:
                    click.echo(f"Error on second attempt: {e2}")
                    return 1
    except Exception as e:
        click.echo(f"Error managing Docker container: {e}")
        return 1
    
    # Read playlists from file
    with open(playlist_file, "r") as f:
        playlists = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    
    playlist_count = min(len(playlists), 100)  # Process up to 100 playlists
    
    click.echo(f"Found {playlist_count} playlists to process:")
    for i, playlist in enumerate(playlists[:playlist_count]):
        click.echo(f"Playlist {i+1}: {playlist}")
    
    # Process each playlist
    for i, playlist in enumerate(playlists[:playlist_count]):
        logging.info(f"Processing playlist {i+1}/{playlist_count}: {playlist}")
        click.echo(f"\nProcessing playlist {i+1}/{playlist_count}: {playlist}")
        
        # Create organized directory structure for downloads
        download_base_dir = os.path.expanduser("~/Music/downloads")
        playlist_name = None
        playlist_type = None
        
        # Determine playlist source and extract name
        if "spotify.com" in playlist:
            playlist_type = "spotify"
            # Get actual Spotify playlist name
            playlist_name = get_spotify_playlist_name(playlist)
        elif "youtube.com" in playlist or "youtu.be" in playlist:
            playlist_type = "youtube"
            # Get actual YouTube playlist name
            playlist_name = get_youtube_playlist_name(playlist)
        else:
            playlist_type = "other"
            playlist_name = f"playlist-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create directory structure
        custom_download_dir = os.path.join(download_base_dir, playlist_type, playlist_name)
        os.makedirs(custom_download_dir, exist_ok=True)
        logging.info(f"Created download directory: {custom_download_dir}")
        click.echo(f"Download directory: {custom_download_dir}")
        
        # Call sldl for this playlist
        try:
            # Determine if we need to mount the config directory
            if container_running:  # Check if container is already running
                # First try to use the local config file that was symlinked/copied
                if os.path.exists(slsk_config_file):
                    # Create container path for playlist downloads
                    container_download_dir = f"/downloads/{playlist_type}/{playlist_name}"
                    
                    # Create a temporary script to update config and run command
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.sh') as script:
                        script.write('#!/bin/sh\n')
                        # Ensure directories exist
                        script.write(f'mkdir -p {container_download_dir}\n')
                        script.write(f'chmod 777 {container_download_dir}\n')
                        
                        # Create temporary config with custom download directory
                        script.write('cp /config/sldl.conf /tmp/temp_sldl.conf\n')
                        script.write('grep -v "download-dir" /tmp/temp_sldl.conf > /tmp/sldl.conf.new\n')
                        script.write('grep -v "path =" /tmp/sldl.conf.new > /tmp/sldl.conf.newer\n')
                        script.write(f'echo "path = {container_download_dir}" >> /tmp/sldl.conf.newer\n')
                        script.write('cat /tmp/sldl.conf.newer > /tmp/temp_sldl.conf\n')
                        
                        # Special handling for Spotify and YouTube URLs
                        if 'spotify.com' in playlist:
                            script.write(f'cd {container_download_dir} && sldl --config /tmp/temp_sldl.conf --input-type spotify "{playlist}"\n')
                        elif 'youtube.com' in playlist or 'youtu.be' in playlist:
                            script.write(f'cd {container_download_dir} && sldl --config /tmp/temp_sldl.conf --input-type youtube "{playlist}"\n')
                        else:
                            script.write(f'cd {container_download_dir} && sldl --config /tmp/temp_sldl.conf "{playlist}"\n')
                        
                        script_path = script.name
                    
                    # Make script executable
                    os.chmod(script_path, 0o755)
                    
                    # Copy script to container
                    try:
                        subprocess.run(
                            ["docker", "cp", script_path, f"{container_name}:/tmp/run_playlist.sh"],
                            check=True
                        )
                        
                        # Execute script in container
                        click.echo(f"Executing search for playlist {i+1}/{playlist_count}: {playlist}")
                        process = subprocess.run(
                            ["docker", "exec", "-it", container_name, "sh", "/tmp/run_playlist.sh"],
                            check=False  # Don't check result to avoid Python error on Ctrl+C
                        )
                        
                        # Clean up
                        os.unlink(script_path)
                    except Exception as e:
                        logging.error(f"Error executing script in container: {e}")
                        click.echo(f"Error: {e}")
                        
                else:
                    # Fall back to existing implementation if needed
                    logging.warning("Config file not found in container, falling back to default approach")
                    click.echo("Warning: Using default approach (may not use custom directory structure)")
                    
                    # If that failed, try to copy the file directly
                    container_config_path = "/tmp/sldl.conf"
                    try:
                        subprocess.run(
                            ["docker", "cp", str(config_file), f"{container_name}:{container_config_path}"],
                            check=True
                        )
                        click.echo(f"Copied config file to Docker container at {container_config_path}")
                        
                        cmd = [
                            "docker", "exec", container_name,
                            "sldl", "--config", container_config_path, playlist
                        ]
                    except Exception as e:
                        click.echo(f"Warning: Failed to copy config to container: {e}")
                        # Fall back to default config path
                        cmd = [
                            "docker", "exec", container_name,
                            "sldl", "--config", "/config/sldl.conf", playlist
                        ]
                        click.echo("Falling back to default config location. This may not work.")
            
            MAX_RETRIES = 2
            retry_count = 0
            success = False
            
            while retry_count <= MAX_RETRIES and not success:
                try:
                    # Add timeout to prevent hanging indefinitely
                    result = subprocess.run(
                        cmd,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    
                    # Check container health after command
                    container_check = subprocess.run(
                        ["docker", "container", "inspect", container_name, "--format", "{{.State.Status}}"],
                        capture_output=True,
                        text=True
                    )
                    
                    container_status = container_check.stdout.strip()
                    
                    # Log command details
                    with open(log_file, "a") as log:
                        log.write(f"--- Processing {playlist} (Attempt {retry_count+1}) ---\n")
                        log.write(f"Command: {' '.join(cmd)}\n")
                        log.write(f"Container status: {container_status}\n")
                        log.write(f"Exit code: {result.returncode}\n")
                        log.write("--- STDOUT ---\n")
                        log.write(result.stdout)
                        log.write("\n--- STDERR ---\n")
                        log.write(result.stderr)
                        log.write("\n-------------\n\n")
                    
                    # Handle different error scenarios
                    if result.returncode != 0:
                        # Log more detailed error information
                        if "Input error" in result.stdout:
                            click.echo(f"Input error detected: {result.stdout.strip()}")
                            
                            # If we're getting "Unknown argument: --search" 
                            if "Unknown argument: --search" in result.stdout:
                                # This shouldn't happen anymore, but just in case
                                cmd = [c for c in cmd if c != "--search"]
                                click.echo("Fixed command by removing --search parameter")
                                # Don't count this as a retry, just fix the command and try again
                                continue
                            
                            # Input errors related to URL formats
                            if "url" in result.stdout.lower():
                                if "spotify" in result.stdout.lower():
                                    # Fix Spotify URL command
                                    cmd = [c for c in cmd if c != "--input-type" and c != "spotify"]
                                    # Insert these options near the start, after the executable and config
                                    insert_pos = cmd.index("sldl") + 3  # After sldl and --config and config path
                                    cmd.insert(insert_pos, "--input-type")
                                    cmd.insert(insert_pos + 1, "spotify")
                                    click.echo("Fixed command for Spotify URL")
                                    continue  # Try again with fixed command
                                    
                                elif "youtube" in result.stdout.lower():
                                    # Fix YouTube URL command
                                    cmd = [c for c in cmd if c != "--input-type" and c != "youtube"]
                                    # Insert these options near the start, after the executable and config
                                    insert_pos = cmd.index("sldl") + 3  # After sldl and --config and config path
                                    cmd.insert(insert_pos, "--input-type")
                                    cmd.insert(insert_pos + 1, "youtube")
                                    click.echo("Fixed command for YouTube URL")
                                    continue  # Try again with fixed command
                        if "No such container" in result.stderr:
                            # Container disappeared, try to restart it
                            click.echo(f"Container disappeared. Attempting to restart with docker compose...")
                            
                            # Find the docker-compose directory
                            root_dir = get_project_root()
                            compose_dir = root_dir / "src" / "slsk-batchdl"
                            
                            # Change directory and restart with docker compose
                            current_dir = os.getcwd()
                            os.chdir(compose_dir)
                            
                            # First down to ensure clean state
                            subprocess.run(["docker", "compose", "down"], check=False, capture_output=True)
                            
                            # Then up to start fresh
                            restart_result = subprocess.run(
                                ["docker", "compose", "up", "-d"],
                                capture_output=True,
                                text=True
                            )
                            
                            # Restore original directory
                            os.chdir(current_dir)
                            
                            if restart_result.returncode != 0:
                                # Container couldn't be restarted, it may need to be recreated
                                raise Exception(f"Failed to restart container: {restart_result.stderr}")
                            
                            click.echo(f"Container restarted with docker compose. Waiting 10 seconds...")
                            time.sleep(10)
                        elif "executable file not found" in result.stderr:
                            # sldl command not found in container
                            click.echo("Error: sldl command not found in container. The container might be misconfigured.")
                            click.echo("Check the Docker image and ensure it contains the sldl binary.")
                            raise Exception("sldl command not found in container")
                        else:
                            click.echo(f"Command failed with exit code {result.returncode}")
                            click.echo("Error details:")
                            click.echo(result.stderr)
                            
                            # If this is the last retry, show more diagnostic information
                            if retry_count == MAX_RETRIES:
                                click.echo("Collecting diagnostic information...")
                                diag_cmd = ["docker", "logs", container_name]
                                diag_result = subprocess.run(diag_cmd, capture_output=True, text=True)
                                
                                with open(log_file, "a") as log:
                                    log.write("=== DIAGNOSTIC INFO ===\n")
                                    log.write(f"Docker logs for {container_name}:\n")
                                    log.write(diag_result.stdout)
                                    log.write(diag_result.stderr)
                                    log.write("======================\n\n")
                                
                                click.echo(f"Diagnostic information saved to {log_file}")
                    else:
                        # Command succeeded
                        success = True
                        click.echo(f"Successfully processed playlist {playlist}")
                
                except subprocess.TimeoutExpired:
                    click.echo(f"Command timed out after 300 seconds. Attempting to kill and restart...")
                    
                    # Kill the hanging command but keep the container
                    try:
                        # Find and kill the process in the container
                        kill_cmd = ["docker", "exec", container_name, "pkill", "-f", "sldl"]
                        subprocess.run(kill_cmd, check=False)
                        
                        # Wait a moment for cleanup
                        time.sleep(5)
                        
                        with open(log_file, "a") as log:
                            log.write(f"Command timed out for playlist {playlist}. Killed process.\n")
                    except Exception as e:
                        click.echo(f"Error killing hanging process: {e}")
                
                except Exception as e:
                    # General exception handling
                    click.echo(f"Error executing command: {e}")
                    
                    with open(log_file, "a") as log:
                        log.write(f"Error during command execution: {str(e)}\n")
                    
                    # Check if container is still running
                    try:
                        container_check = subprocess.run(
                            ["docker", "container", "inspect", container_name, "--format", "{{.State.Status}}"],
                            capture_output=True,
                            text=True
                        )
                        
                        if "running" not in container_check.stdout:
                            click.echo(f"Container is not running. Attempting to restart with docker compose...")
                            
                            # Find the docker-compose directory
                            root_dir = get_project_root()
                            compose_dir = root_dir / "src" / "slsk-batchdl"
                            
                            # Change directory and restart with docker compose
                            current_dir = os.getcwd()
                            os.chdir(compose_dir)
                            
                            # Start with docker compose up
                            subprocess.run(["docker", "compose", "up", "-d"], check=False)
                            
                            # Restore original directory
                            os.chdir(current_dir)
                            
                            click.echo("Container restarted with docker compose")
                            time.sleep(10)
                    except Exception as e2:
                        click.echo(f"Error checking container status: {e2}")
                
                retry_count += 1
                
                if not success and retry_count <= MAX_RETRIES:
                    click.echo(f"Retrying command (attempt {retry_count+1}/{MAX_RETRIES+1})...")
                    time.sleep(5)  # Wait before retry
            
            if not success:
                click.echo(f"Failed to process playlist {playlist} after {MAX_RETRIES+1} attempts.")
                click.echo(f"Check the log file at {log_file} for details.")
                
                # Log as not found so it gets included in the not found list
                with open(log_file, "a") as log:
                    log.write(f"All downloads failed: {playlist}\n")
            
            # Add delay between playlists
            if i < playlist_count - 1:
                click.echo("Waiting 10 seconds before processing next playlist...")
                time.sleep(10)
                
        except Exception as e:
            click.echo(f"Error processing playlist {playlist}: {e}")
    
    # Extract songs that were not found
    click.echo("Extracting songs that were not found during the search...")
    
    # Create the not found songs file with a header
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    not_found_file = logs_dir / f"not_found_songs_{timestamp}.txt"
    
    with open(not_found_file, "w") as nf:
        nf.write(f"# Songs not found during batch download on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        nf.write("# From playlists:\n")
        
        for playlist in playlists[:playlist_count]:
            nf.write(f"# - {playlist}\n")
        
        nf.write("\n")
    
    # Extract not found songs from log file
    try:
        with open(log_file, "r") as log:
            log_content = log.read()
            
        # Use a regular expression to find not found songs
        not_found_songs = set()
        for match in re.finditer(r"Not found: (.*?)$|All downloads failed: (.*?)$", log_content, re.MULTILINE):
            song = match.group(1) or match.group(2)
            if song:
                not_found_songs.add(song)
        
        # Write the sorted list to the not found file
        with open(not_found_file, "a") as nf:
            for song in sorted(not_found_songs):
                nf.write(f"{song}\n")
        
        not_found_count = len(not_found_songs)
        click.echo(f"Found {not_found_count} songs that could not be downloaded")
        click.echo(f"List saved to {not_found_file}")
        
    except Exception as e:
        click.echo(f"Error extracting not found songs: {e}")
    
    # Log end time
    with open(log_file, "a") as log:
        log.write(f"=== Batch download completed at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    return 0

@slsk_tool_group.command(name="diagnose")
@click.option("--container-name", default="sldl", help="Name of the Docker container to diagnose")
def diagnose_docker(container_name):
    """Diagnose Docker container issues."""
    click.echo(f"Diagnosing Docker container '{container_name}'...")
    
    # Check if Docker is installed
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        click.echo("✅ Docker is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("❌ Docker is not installed or not in PATH")
        click.echo("Please install Docker Desktop and try again")
        return 1
    
    # Check if Docker daemon is running
    try:
        docker_ps = subprocess.run(["docker", "ps"], check=True, capture_output=True)
        click.echo("✅ Docker daemon is running")
    except subprocess.CalledProcessError:
        click.echo("❌ Docker daemon is not running")
        click.echo("Please start Docker Desktop and try again")
        return 1
    
    # Check if container exists
    try:
        inspect_cmd = ["docker", "container", "inspect", container_name]
        result = subprocess.run(inspect_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"❌ Container '{container_name}' does not exist")
            click.echo("Run 'slsk-tool setup' to create the container")
            return 1
        click.echo(f"✅ Container '{container_name}' exists")
    except subprocess.CalledProcessError:
        click.echo(f"❌ Container '{container_name}' does not exist")
        click.echo("Run 'slsk-tool setup' to create the container")
        return 1
    
    # Check if container is running
    try:
        status_cmd = ["docker", "container", "inspect", container_name, "--format", "{{.State.Status}}"]
        status_result = subprocess.run(status_cmd, capture_output=True, text=True)
        
        if status_result.returncode == 0:
            status = status_result.stdout.strip()
            if status == "running":
                click.echo(f"✅ Container '{container_name}' is running")
            else:
                click.echo(f"❌ Container '{container_name}' is not running (status: {status})")
                click.echo(f"Run 'docker start {container_name}' to start it")
                
                # Ask if user wants to start the container
                if click.confirm("Do you want to start the container now?", default=True):
                    # Find the docker-compose directory
                    root_dir = get_project_root()
                    compose_dir = root_dir / "src" / "slsk-batchdl"
                    
                    # Change directory and run docker compose up
                    current_dir = os.getcwd()
                    os.chdir(compose_dir)
                    
                    start_result = subprocess.run(
                        ["docker", "compose", "up", "-d"],
                        capture_output=True,
                        text=True
                    )
                    
                    # Restore original directory
                    os.chdir(current_dir)
                    
                    if start_result.returncode == 0:
                        click.echo(f"✅ Container started with docker compose up")
                    else:
                        click.echo(f"❌ Failed to start container: {start_result.stderr}")
                        return 1
    except subprocess.CalledProcessError:
        click.echo(f"❌ Failed to get container status")
        return 1
    
    # Check config directory in container
    try:
        config_cmd = ["docker", "exec", container_name, "ls", "-la", "/config"]
        config_result = subprocess.run(config_cmd, capture_output=True, text=True)
        if config_result.returncode == 0:
            click.echo("✅ Container has access to /config directory")
            
            # Check if sldl.conf exists
            if "sldl.conf" in config_result.stdout:
                click.echo("✅ sldl.conf found in container config directory")
            else:
                click.echo("❌ sldl.conf not found in container config directory")
                
                # Copy sldl.conf to container
                user_config_dir = Path.home() / ".config" / "sldl"
                user_conf_file_path = user_config_dir / "sldl.conf"
                if user_conf_file_path.exists():
                    if click.confirm("Do you want to copy your config file to the container?", default=True):
                        copy_cmd = ["docker", "cp", str(user_conf_file_path), f"{container_name}:/config/sldl.conf"]
                        copy_result = subprocess.run(copy_cmd, capture_output=True, text=True)
                        if copy_result.returncode == 0:
                            click.echo("✅ Config file copied to container")
                        else:
                            click.echo(f"❌ Failed to copy config file: {copy_result.stderr}")
                else:
                    click.echo("❌ No config file found at ~/.config/sldl/sldl.conf")
                    click.echo("Run 'slsk-tool setup' to create a configuration file")
        else:
            click.echo("❌ Container does not have access to /config directory")
            click.echo(f"Error: {config_result.stderr}")
    except subprocess.CalledProcessError:
        click.echo("❌ Error checking container config directory")
    
    # Check downloads directory in container
    try:
        downloads_cmd = ["docker", "exec", container_name, "ls", "-la", "/downloads"]
        downloads_result = subprocess.run(downloads_cmd, capture_output=True, text=True)
        if downloads_result.returncode == 0:
            click.echo("✅ Container has access to /downloads directory")
        else:
            click.echo("❌ Container does not have access to /downloads directory")
            click.echo(f"Error: {downloads_result.stderr}")
            
            # Try to create the downloads directory
            if click.confirm("Do you want to create the /downloads directory in the container?", default=True):
                mkdir_cmd = ["docker", "exec", container_name, "mkdir", "-p", "/downloads"]
                mkdir_result = subprocess.run(mkdir_cmd, capture_output=True, text=True)
                if mkdir_result.returncode == 0:
                    chmod_cmd = ["docker", "exec", container_name, "chmod", "777", "/downloads"]
                    chmod_result = subprocess.run(chmod_cmd, capture_output=True, text=True)
                    if chmod_result.returncode == 0:
                        click.echo("✅ Created /downloads directory with permissions 777")
                    else:
                        click.echo(f"❌ Failed to set permissions on /downloads: {chmod_result.stderr}")
                else:
                    click.echo(f"❌ Failed to create /downloads directory: {mkdir_result.stderr}")
    except subprocess.CalledProcessError:
        click.echo("❌ Error checking container downloads directory")
    
    # Check if sldl binary is available
    try:
        sldl_cmd = ["docker", "exec", container_name, "which", "sldl"]
        sldl_result = subprocess.run(sldl_cmd, capture_output=True, text=True)
        if sldl_result.returncode == 0:
            click.echo("✅ sldl binary found in container")
        else:
            click.echo("❌ sldl binary not found in container")
            click.echo("The container image may be incorrectly built")
            
            # Ask if user wants to recreate container
            if click.confirm("Do you want to recreate the container?", default=True):
                root_dir = get_project_root()
                success = recreate_slsk_container(root_dir)
                if success:
                    click.echo("✅ Container recreated successfully")
                else:
                    click.echo("❌ Failed to recreate container")
                    return 1
    except subprocess.CalledProcessError:
        click.echo("❌ Error checking sldl binary in container")
    
    click.echo("\nDiagnostics complete.")
    return 0

@main.group(name="shazam-tool")
def shazam_tool_group():
    """Run Shazam music recognition tool."""
    pass

@shazam_tool_group.command(name="download")
@click.argument("url")
@click.option("--analyze", is_flag=True, help="Analyze the downloaded audio for recognition")
def shazam_download(url, analyze):
    """Download audio from a URL (YouTube or SoundCloud)."""
    args = ["download", url]
    if analyze:
        args.append("--analyze")
    sys.argv = [sys.argv[0]] + args
    run_shazam()

@shazam_tool_group.command(name="scan")
@click.option("--analyze", is_flag=True, help="Analyze the downloaded audio for recognition")
def shazam_scan(analyze):
    """Process all downloaded files."""
    args = ["scan"]
    if analyze:
        args.append("--analyze")
    sys.argv = [sys.argv[0]] + args
    run_shazam()

@shazam_tool_group.command(name="recognize")
@click.argument("file")
def shazam_recognize(file):
    """Process a specific audio file for recognition."""
    sys.argv = [sys.argv[0], "recognize", file]
    run_shazam()

@shazam_tool_group.command(name="setup")
def shazam_setup():
    """Set up the Shazam tool environment."""
    sys.argv = [sys.argv[0], "setup"]
    run_shazam()

@main.command(name="mdl-tool")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def mdl_tool(args):
    """Run music metadata utility."""
    sys.argv = [sys.argv[0]] + list(args)
    run_mdl()

def diagnose_docker_container(container_name, log_file=None):
    """Perform diagnostics on a Docker container and optionally log results."""
    click.echo(f"Performing diagnostics on container '{container_name}'...")
    
    diagnostics = {
        "container_status": None,
        "container_details": None,
        "logs": None,
        "filesystem": None,
        "processes": None,
        "network": None
    }
    
    try:
        # Check container status
        status_cmd = ["docker", "container", "inspect", container_name, "--format", "{{.State.Status}}"]
        status_result = subprocess.run(status_cmd, capture_output=True, text=True)
        diagnostics["container_status"] = status_result.stdout.strip() if status_result.returncode == 0 else "Error"
        
        # Get container details
        details_cmd = ["docker", "container", "inspect", container_name]
        details_result = subprocess.run(details_cmd, capture_output=True, text=True)
        if details_result.returncode == 0:
            try:
                diagnostics["container_details"] = json.loads(details_result.stdout)
            except json.JSONDecodeError:
                diagnostics["container_details"] = details_result.stdout
        
        # Get container logs
        logs_cmd = ["docker", "logs", container_name]
        logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
        diagnostics["logs"] = logs_result.stdout if logs_result.returncode == 0 else "Error: " + logs_result.stderr
        
        # Check filesystem in container
        fs_cmd = ["docker", "exec", container_name, "ls", "-la", "/"]
        fs_result = subprocess.run(fs_cmd, capture_output=True, text=True)
        diagnostics["filesystem"] = fs_result.stdout if fs_result.returncode == 0 else "Error: " + fs_result.stderr
        
        # Check config directory
        config_cmd = ["docker", "exec", container_name, "ls", "-la", "/config"]
        config_result = subprocess.run(config_cmd, capture_output=True, text=True)
        diagnostics["config_dir"] = config_result.stdout if config_result.returncode == 0 else "Error: " + config_result.stderr
        
        # Check running processes
        ps_cmd = ["docker", "exec", container_name, "ps", "-ef"]
        ps_result = subprocess.run(ps_cmd, capture_output=True, text=True)
        diagnostics["processes"] = ps_result.stdout if ps_result.returncode == 0 else "Error: " + ps_result.stderr
        
        # Check network
        net_cmd = ["docker", "exec", container_name, "netstat", "-an"]
        net_result = subprocess.run(net_cmd, capture_output=True, text=True)
        if net_result.returncode != 0:
            # Try alternative network check if netstat is not available
            net_cmd = ["docker", "exec", container_name, "ip", "addr"]
            net_result = subprocess.run(net_cmd, capture_output=True, text=True)
        diagnostics["network"] = net_result.stdout if net_result.returncode == 0 else "Error: " + net_result.stderr
        
        # Print diagnostic summary
        click.echo(f"Container status: {diagnostics['container_status']}")
        
        if diagnostics['container_status'] == 'running':
            click.echo("Container is running")
            
            # Check if config directory is accessible
            if "Error" not in diagnostics["config_dir"]:
                click.echo("Config directory is accessible")
                
                # Check for sldl.conf in config directory
                if "sldl.conf" in diagnostics["config_dir"]:
                    click.echo("sldl.conf found in config directory")
                else:
                    click.echo("WARNING: sldl.conf not found in config directory")
            else:
                click.echo("WARNING: Config directory is not accessible")
        else:
            click.echo(f"WARNING: Container is not running (status: {diagnostics['container_status']})")
        
        # Log complete diagnostics
        if log_file:
            with open(log_file, "a") as log:
                log.write("\n=== DOCKER CONTAINER DIAGNOSTICS ===\n")
                log.write(f"Container: {container_name}\n")
                log.write(f"Status: {diagnostics['container_status']}\n")
                log.write("\n--- CONTAINER LOGS ---\n")
                log.write(diagnostics["logs"][:2000])  # Limit to first 2000 chars
                log.write("\n--- FILESYSTEM ---\n")
                log.write(diagnostics["filesystem"])
                log.write("\n--- CONFIG DIRECTORY ---\n")
                log.write(diagnostics["config_dir"])
                log.write("\n--- PROCESSES ---\n")
                log.write(diagnostics["processes"])
                log.write("\n--- NETWORK ---\n")
                log.write(diagnostics["network"])
                log.write("\n================================\n\n")
            
            click.echo(f"Full diagnostics written to {log_file}")
        
        return diagnostics
        
    except Exception as e:
        click.echo(f"Error during diagnostics: {e}")
        if log_file:
            with open(log_file, "a") as log:
                log.write(f"\n=== DIAGNOSTIC ERROR ===\n")
                log.write(f"Error performing diagnostics on container {container_name}: {str(e)}\n")
        return {"error": str(e)}

def check_docker_health(container_name):
    """Check if a Docker container is healthy and running."""
    try:
        # Check if container exists
        exists_cmd = ["docker", "container", "inspect", container_name]
        exists_result = subprocess.run(exists_cmd, capture_output=True, text=True)
        
        if exists_result.returncode != 0:
            return False, f"Container '{container_name}' does not exist"
        
        # Check if container is running
        status_cmd = ["docker", "container", "inspect", container_name, "--format", "{{.State.Status}}"]
        status_result = subprocess.run(status_cmd, capture_output=True, text=True)
        
        if status_result.returncode != 0 or status_result.stdout.strip() != "running":
            return False, f"Container '{container_name}' is not running (status: {status_result.stdout.strip()})"
        
        # Check if sldl is available in the container
        sldl_cmd = ["docker", "exec", container_name, "which", "sldl"]
        sldl_result = subprocess.run(sldl_cmd, capture_output=True, text=True)
        
        if sldl_result.returncode != 0:
            return False, "sldl command not found in container"
        
        return True, "Container is healthy"
        
    except Exception as e:
        return False, f"Error checking container health: {e}"

@main.command()
@click.argument('url')
def download(url):
    """Download audio from a YouTube or SoundCloud URL.
    
    If the URL is a playlist, it will be downloaded to ~/Music/downloads/playlist-name/
    If it's a single track, it will be downloaded to ~/Music/downloads/
    """
    downloader = AudioDownloader(output_path=str(Path.home() / "Music" / "downloads"))
    result = downloader.download(url)
    
    if result:
        click.echo(f"✅ Download complete! Files saved to: {result}")
    else:
        click.echo("❌ Download failed. Please check the URL and try again.")

@main.command(name="sldl", context_settings=dict(ignore_unknown_options=True))
@click.option("--download-path", type=click.Path(file_okay=False, dir_okay=True), help="Path where downloads will be saved")
@click.option("--links-file", type=click.Path(exists=True, file_okay=True, dir_okay=False), help="Path to a text file containing links to process one by one")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def sldl_command(download_path, links_file, args):
    """Run Soulseek batch download tool.
    
    Downloads will be saved to the specified path or ~/Music/downloads by default.
    
    You can also provide a text file containing links (one per line) with --links-file
    to process multiple downloads sequentially.
    
    If run without any arguments, opens a shell in the container.
    """
    # Extract any --download-path from args if specified there as well
    new_args = []
    download_path_specified = False
    links_file_specified = False
    i = 0
    while i < len(args):
        if args[i] == "--download-path" and i + 1 < len(args):
            # If download_path is not already set from the option, set it
            if not download_path:
                download_path = args[i+1]
            download_path_specified = True
            i += 2  # Skip both --download-path and its value
        elif args[i] == "--links-file" and i + 1 < len(args):
            # If links_file is not already set from the option, set it
            if not links_file:
                links_file = args[i+1]
            links_file_specified = True
            i += 2  # Skip both --links-file and its value
        else:
            new_args.append(args[i])
            i += 1
    
    # Set sys.argv for compatibility with any code expecting it
    sys.argv = [sys.argv[0]] + new_args
    
    # Run the command with the specified download path and links file
    # Only open shell if there are no arguments and no links file
    run_slsk(download_path=download_path, links_file=links_file, open_shell=len(new_args) == 0 and not links_file)

@main.group(name="schedule")
def schedule_group():
    """Manage scheduled jobs for toolcrate commands."""
    pass

@schedule_group.command(name="add")
@click.argument("file_type", type=click.Choice(["wishlist", "dj-sets"]))
@click.option("--frequency", type=click.Choice(["hourly", "daily", "weekly"]), default="hourly",
              help="How often to run the job (default: hourly)")
@click.option("--custom-schedule", help="Custom cron schedule (e.g., '*/30 * * * *' for every 30 minutes)")
def schedule_add(file_type, frequency, custom_schedule):
    """Add a scheduled job to run toolcrate commands regularly.
    
    FILE_TYPE can be:
    - wishlist: Process wishlist.txt file
    - dj-sets: Process dj-sets.txt file
    """
    from toolcrate.scripts.cron_manager import add_identify_tracks_cron, add_download_wishlist_cron
    
    # Use custom schedule if provided
    if custom_schedule:
        schedule = custom_schedule
    else:
        schedule = frequency
        
    if file_type == "wishlist":
        result = add_download_wishlist_cron(schedule)
    else:  # dj-sets
        result = add_identify_tracks_cron(file_type, schedule)
    
    return 0 if result else 1

@schedule_group.command(name="remove")
@click.argument("file_type", type=click.Choice(["wishlist", "dj-sets"]))
def schedule_remove(file_type):
    """Remove a scheduled job.
    
    FILE_TYPE can be:
    - wishlist: Remove wishlist processing job
    - dj-sets: Remove DJ sets processing job
    """
    from toolcrate.scripts.cron_manager import remove_scheduled_job
    
    if file_type == "wishlist":
        result = remove_scheduled_job("download-wishlist")
    else:  # dj-sets
        result = remove_scheduled_job(f"identify-tracks-{file_type}")
    
    return 0 if result else 1

@schedule_group.command(name="list")
def schedule_list():
    """List all scheduled jobs for toolcrate commands.
    
    This will show all cron jobs related to toolcrate commands.
    """
    from toolcrate.scripts.cron_manager import list_scheduled_jobs
    
    result = list_scheduled_jobs()
    return 0 if result else 1

if __name__ == "__main__":
    main()
