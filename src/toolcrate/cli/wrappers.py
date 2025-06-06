#!/usr/bin/env python3
"""Wrapper functions for external tools."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import time
from datetime import datetime
import re
import requests
import unicodedata

import click
from loguru import logger

# Check Python version
if sys.version_info < (3, 11) or sys.version_info >= (3, 13):
    print("Error: ToolCrate requires Python 3.11 or 3.12")
    print(f"Current Python version: {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)


def check_dependency(name, binary_name=None):
    """Check if a dependency is available in the PATH."""
    if binary_name is None:
        binary_name = name
    
    return shutil.which(binary_name) is not None


def check_docker_image(image_name):
    """Check if a Docker image is available."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        # Docker not installed
        return False


def check_docker_container_running(container_prefix):
    """Check if a Docker container with the given prefix is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        container_names = result.stdout.strip().split('\n') if result.stdout.strip() else []
        # Check if any container name starts with the prefix
        return any(name.startswith(container_prefix) for name in container_names)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def ensure_slsk_container_running(root_dir):
    """Ensure the sldl container is running using docker-compose."""
    # Container not running, start it
    slsk_dir = root_dir / "src" / "slsk-batchdl"
    
    try:
        logger.info(f"Starting slsk-batchdl container using docker compose in {slsk_dir}")
        
        # Change directory and run docker compose
        current_dir = os.getcwd()
        os.chdir(slsk_dir)
        
        # Start the container
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            check=True,
            text=True,
        )
        
        # Restore original directory
        os.chdir(current_dir)
        return True
            
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Error starting Docker container: {e}")
        return False


def get_project_root():
    """Get the project root directory."""
    # Start from the current file's directory
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Navigate up until we find the project root (where setup.py is)
    while current_dir != current_dir.parent:
        if (current_dir / "setup.py").exists():
            return current_dir
        current_dir = current_dir.parent
        
    # Fallback to package directory
    return Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def recreate_slsk_container(root_dir):
    """Force recreation of the sldl container."""
    logger.info("Recreating sldl container...")
    slsk_dir = root_dir / "src" / "slsk-batchdl"
    
    if not slsk_dir.exists():
        logger.error(f"slsk-batchdl directory not found at {slsk_dir}")
        return False
    
    try:
        current_dir = os.getcwd()
        os.chdir(slsk_dir)
        
        # Stop and remove existing containers
        subprocess.run(
            ["docker", "compose", "down"],
            check=False,
            capture_output=True
        )
        
        # Start the container
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            check=True
        )
        
        # Restore original directory
        os.chdir(current_dir)
        return True
    except Exception as e:
        logger.error(f"Error recreating container: {e}")
        return False


def sanitize_filename(name):
    """Sanitize a string to be used as a filename or directory name."""
    # Replace any non-alphanumeric characters with underscores, except for common safe characters
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = re.sub(r'[^\w\s.-]', '_', name)
    # Replace multiple spaces/underscores with a single one
    name = re.sub(r'[\s_]+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    return name


def get_spotify_playlist_name(playlist_url):
    """Get the name of a Spotify playlist from its URL."""
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    
    # First try to get name using Spotify's embed API which doesn't require auth
    try:
        # Use Spotify's embed API to get basic playlist info without requiring auth
        embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(embed_url, headers=headers)
        
        if response.status_code == 200:
            # Try multiple regex patterns to extract playlist name 
            patterns = [
                r'<title>(.*?)(\s*[-–]\s*)|</title>',  # Standard title format
                r'<h1[^>]*>(.*?)</h1>',                # H1 tag that might contain the name
                r'data-testid="playlist-name"[^>]*>(.*?)</[^>]*>',  # Modern Spotify data attribute
                r'property="og:title"\s+content="([^"]+)"'  # Open Graph title
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    playlist_name = match.group(1).strip()
                    logger.info(f"Found Spotify playlist name: {playlist_name}")
                    return sanitize_filename(playlist_name)
                    
            # Additional fallback - look for JSON data in the page
            json_data_match = re.search(r'Spotify\.Entity\s*=\s*({.*?});', response.text, re.DOTALL)
            if json_data_match:
                import json
                try:
                    json_str = json_data_match.group(1)
                    data = json.loads(json_str)
                    if 'name' in data:
                        playlist_name = data['name']
                        logger.info(f"Found Spotify playlist name from JSON: {playlist_name}")
                        return sanitize_filename(playlist_name)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logger.warning(f"Error getting Spotify playlist name from embed API: {e}")
    
    # If we couldn't get the name, fall back to using the ID
    logger.warning(f"Could not get playlist name, using ID instead: {playlist_id}")
    return f"spotify-{playlist_id}"


def get_youtube_playlist_name(playlist_url):
    """Get the name of a YouTube playlist from its URL."""
    # Extract playlist ID
    playlist_id = None
    if "list=" in playlist_url:
        playlist_id = playlist_url.split("list=")[1].split("&")[0]
    else:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
    
    # Try to get YouTube playlist name
    try:
        # Use YouTube's oEmbed API to get playlist info
        if playlist_id:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/playlist?list={playlist_id}&format=json"
            response = requests.get(oembed_url)
            
            if response.status_code == 200:
                data = response.json()
                playlist_name = data.get("title", "")
                if playlist_name:
                    logger.info(f"Found YouTube playlist name: {playlist_name}")
                    return sanitize_filename(playlist_name)
    except Exception as e:
        logger.warning(f"Error getting YouTube playlist name: {e}")
    
    # If we couldn't get the name, fall back to using the ID
    logger.warning(f"Could not get YouTube playlist name, using ID instead: {playlist_id}")
    return f"youtube-{playlist_id}"


def read_config_file(config_file=None):
    """Read configuration from a config file.
    
    Args:
        config_file: Path to config file. If None, will look for toolcrate.conf in project root.
        
    Returns:
        Dict with configuration values.
    """
    config = {
        "download-path": os.path.expanduser("~/Music/downloads/sldl"),
        "wishlist": os.path.expanduser("~/Music/downloads/sldl/wishlist.txt"),
        "dj-sets": os.path.expanduser("~/Music/downloads/sldl/dj-sets.txt"),
    }
    
    if config_file is None:
        config_file = get_project_root() / "toolcrate.conf"
    
    if os.path.exists(config_file):
        logger.info(f"Reading configuration from {config_file}")
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse key-value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Expand user paths (~/...)
                    if key in ["download-path", "wishlist", "dj-sets"] and '~' in value:
                        value = os.path.expanduser(value)
                    
                    config[key] = value
    else:
        logger.debug(f"Config file {config_file} not found, using defaults")
    
    return config


def run_slsk(download_path=None, links_file=None, open_shell=False):
    """Run the Soulseek batch downloader.
    
    Args:
        download_path: Path where downloads will be saved (mounted as /data in container)
        links_file: Path to a text file containing links to process one by one
        open_shell: If True, opens a shell in the container instead of running sldl
    """
    args = sys.argv[1:]
    root_dir = get_project_root()
    slsk_dir = root_dir / "src" / "slsk-batchdl"
    
    # Read configuration from file
    config = read_config_file()
    
    # Set default download path from config if not explicitly provided
    if not download_path:
        download_path = config["download-path"]
    
    # Create directories if they don't exist
    os.makedirs(download_path, exist_ok=True)
    logger.info(f"Using download path: {download_path}")
    
    # Create directories for wishlist and dj-sets files
    wishlist_path = config["wishlist"]
    dj_sets_path = config["dj-sets"]
    
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(wishlist_path), exist_ok=True)
    os.makedirs(os.path.dirname(dj_sets_path), exist_ok=True)
    
    # Create empty files if they don't exist
    if not os.path.exists(wishlist_path):
        logger.info(f"Creating empty wishlist file at {wishlist_path}")
        with open(wishlist_path, 'w') as f:
            f.write("# Add your wishlist items here, one per line\n")
    
    if not os.path.exists(dj_sets_path):
        logger.info(f"Creating empty DJ sets file at {dj_sets_path}")
        with open(dj_sets_path, 'w') as f:
            f.write("# Add your DJ sets here, one per line\n")
    
    try:
        # Change directory to the slsk-batchdl repo
        current_dir = os.getcwd()
        os.chdir(slsk_dir)
        
        # Update docker-compose.yml to use the specified download path
        docker_compose_path = slsk_dir / "docker-compose.yml"
        
        if docker_compose_path.exists():
            # Create a backup of the original file
            backup_path = f"{docker_compose_path}.bak"
            if not os.path.exists(backup_path):
                shutil.copy2(docker_compose_path, backup_path)
                logger.info(f"Created backup of docker-compose.yml at {backup_path}")
            
            # Read the docker-compose.yml file
            try:
                import yaml
                with open(docker_compose_path, 'r') as f:
                    docker_compose = yaml.safe_load(f)
                
                # Update the volume mount for the sldl service
                if 'services' in docker_compose and 'sldl' in docker_compose['services']:
                    if 'volumes' not in docker_compose['services']['sldl']:
                        docker_compose['services']['sldl']['volumes'] = []
                    
                    # Remove any existing /data volume mounts
                    volumes = docker_compose['services']['sldl']['volumes']
                    volumes = [v for v in volumes if not v.endswith(':/data')]
                    
                    # Add our new volume mount
                    volumes.append(f"{download_path}:/data")
                    
                    # Also add mounts for wishlist and dj-sets files
                    volumes = [v for v in volumes if not 'wishlist.txt:' in v]
                    volumes = [v for v in volumes if not 'dj-sets.txt:' in v]
                    volumes.append(f"{wishlist_path}:/config/wishlist.txt")
                    volumes.append(f"{dj_sets_path}:/config/dj-sets.txt")
                    
                    # Make sure the config directory is mounted
                    config_mount_exists = False
                    for v in volumes:
                        if ":/config" in v and not v.endswith("/wishlist.txt:/config/wishlist.txt") and not v.endswith("/dj-sets.txt:/config/dj-sets.txt"):
                            config_mount_exists = True
                    
                    if not config_mount_exists:
                        volumes.append(f"{root_dir}/config:/config")
                    
                    docker_compose['services']['sldl']['volumes'] = volumes
                    
                    # Write the updated file
                    with open(docker_compose_path, 'w') as f:
                        yaml.dump(docker_compose, f, default_flow_style=False)
                    
                    logger.info(f"Updated docker-compose.yml with volume mounts")
                else:
                    logger.warning("Could not find sldl service in docker-compose.yml")
            except ImportError:
                logger.warning("PyYAML not installed. Using fallback method to update docker-compose.yml")
                # Fallback approach without PyYAML
                with open(docker_compose_path, 'r') as f:
                    lines = f.readlines()
                
                updated_lines = []
                in_volumes_section = False
                data_volume_updated = False
                wishlist_volume_updated = False
                dj_sets_volume_updated = False
                config_mount_exists = False
                
                for line in lines:
                    if 'volumes:' in line and not in_volumes_section:
                        in_volumes_section = True
                        updated_lines.append(line)
                    elif in_volumes_section and ':/data' in line:
                        # Replace the /data volume line
                        updated_lines.append(f"      - {download_path}:/data\n")
                        data_volume_updated = True
                    elif in_volumes_section and 'wishlist.txt:' in line:
                        # Replace the wishlist volume line
                        updated_lines.append(f"      - {wishlist_path}:/config/wishlist.txt\n")
                        wishlist_volume_updated = True
                    elif in_volumes_section and 'dj-sets.txt:' in line:
                        # Replace the dj-sets volume line
                        updated_lines.append(f"      - {dj_sets_path}:/config/dj-sets.txt\n")
                        dj_sets_volume_updated = True
                    elif in_volumes_section and ':/config' in line and 'wishlist.txt:/config' not in line and 'dj-sets.txt:/config' not in line:
                        # Keep track if we have any config directory mounted
                        config_mount_exists = True
                        updated_lines.append(line)
                    elif in_volumes_section and line.strip() and not line.startswith(' '):
                        # We've left the volumes section
                        # Add any volumes we didn't update
                        if not data_volume_updated:
                            updated_lines.append(f"      - {download_path}:/data\n")
                        if not wishlist_volume_updated:
                            updated_lines.append(f"      - {wishlist_path}:/config/wishlist.txt\n")
                        if not dj_sets_volume_updated:
                            updated_lines.append(f"      - {dj_sets_path}:/config/dj-sets.txt\n")
                        if not config_mount_exists:
                            updated_lines.append(f"      - {root_dir}/config:/config\n")
                        
                        in_volumes_section = False
                        updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                # If we never found a volumes section, add one
                if not in_volumes_section:
                    # Find the sldl service section to add volumes
                    for i, line in enumerate(updated_lines):
                        if 'sldl:' in line:
                            # Find the end of the service section
                            insert_pos = i + 1
                            while insert_pos < len(updated_lines) and updated_lines[insert_pos].startswith(' '):
                                insert_pos += 1
                            # Insert volumes at the end of the service section
                            updated_lines.insert(insert_pos, "    volumes:\n")
                            updated_lines.insert(insert_pos + 1, f"      - {download_path}:/data\n")
                            updated_lines.insert(insert_pos + 2, f"      - {wishlist_path}:/config/wishlist.txt\n")
                            updated_lines.insert(insert_pos + 3, f"      - {dj_sets_path}:/config/dj-sets.txt\n")
                            updated_lines.insert(insert_pos + 4, f"      - {root_dir}/config:/config\n")
                            break
                
                with open(docker_compose_path, 'w') as f:
                    f.writelines(updated_lines)
                
                logger.info(f"Updated docker-compose.yml with volume mounts")
        else:
            logger.warning(f"docker-compose.yml not found at {docker_compose_path}")
        
        # Start the container
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            check=True,
            text=True,
        )

        # Only open shell if explicitly requested
        if open_shell:
            logger.info("Opening shell in container...")
            subprocess.run(
                ["docker", "compose", "exec", "sldl", "sh"],
                check=True
            )
            return 0

        # Process links from file if provided
        if links_file:
            if not os.path.exists(links_file):
                logger.error(f"Links file not found: {links_file}")
                click.echo(f"Error: Links file not found: {links_file}")
                return 1
                
            logger.info(f"Processing links from file: {links_file}")
            with open(links_file, 'r') as f:
                links = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            
            if not links:
                logger.warning(f"No links found in file: {links_file}")
                click.echo(f"Warning: No links found in file: {links_file}")
                return 0
                
            logger.info(f"Found {len(links)} links to process")
            
            # Add default arguments (--yt-dlp) if not already specified
            default_args = ["--yt-dlp", "-c", "/config/sldl.conf"]
            final_args = []
            
            # Check if --yt-dlp or -c already appear in args
            i = 0
            ytdlp_specified = False
            config_specified = False
            
            while i < len(args):
                if args[i] == "--yt-dlp":
                    ytdlp_specified = True
                    final_args.append(args[i])
                    i += 1
                elif args[i] == "-c" or args[i] == "--config":
                    config_specified = True
                    final_args.append(args[i])
                    # Add the config value if it exists
                    if i + 1 < len(args):
                        final_args.append(args[i+1])
                        i += 2
                    else:
                        i += 1
                else:
                    final_args.append(args[i])
                    i += 1
            
            # Add default args if not already specified
            if not ytdlp_specified:
                final_args.append("--yt-dlp")
            if not config_specified:
                final_args.extend(["-c", "/config/sldl.conf"])
            
            # Process each link
            total_links = len(links)
            for i, link in enumerate(links, 1):
                logger.info(f"Processing link {i}/{total_links}: {link}")
                click.echo(f"Processing link {i}/{total_links}: {link}")
                
                try:
                    subprocess.run(
                        ["docker", "compose", "exec", "sldl", "sldl"] + final_args + [link],
                        check=True
                    )
                    logger.info(f"Successfully processed link: {link}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error processing link {link}: {e}")
                    click.echo(f"Error processing link {link}: {e}")
        else:
            # Add default arguments (--yt-dlp) if not already specified
            default_args = ["--yt-dlp", "-c", "/config/sldl.conf"]
            final_args = []
            
            # Check if --yt-dlp or -c already appear in args
            i = 0
            ytdlp_specified = False
            config_specified = False
            
            while i < len(args):
                if args[i] == "--yt-dlp":
                    ytdlp_specified = True
                    final_args.append(args[i])
                    i += 1
                elif args[i] == "-c" or args[i] == "--config":
                    config_specified = True
                    final_args.append(args[i])
                    # Add the config value if it exists
                    if i + 1 < len(args):
                        final_args.append(args[i+1])
                        i += 2
                    else:
                        i += 1
                else:
                    final_args.append(args[i])
                    i += 1
            
            # Add default args if not already specified
            if not ytdlp_specified:
                final_args.append("--yt-dlp")
            if not config_specified:
                final_args.extend(["-c", "/config/sldl.conf"])
            
            logger.info(f"Running sldl with arguments: {final_args}")
            
            # Run sldl command with arguments
            subprocess.run(
                ["docker", "compose", "exec", "sldl", "sldl"] + final_args,
                check=True
            )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running sldl: {e}")
        click.echo(f"Error: {e}")
    finally:
        # Restore original directory
        os.chdir(current_dir)
    
    return 0


def run_shazam():
    """Run the Shazam tool."""
    args = sys.argv[1:]
    root_dir = get_project_root()
    
    # First check for shell script as the preferred method
    shazam_shell = root_dir / "src" / "Shazam-Tool" / "run_shazam.sh"
    if shazam_shell.exists():
        logger.info(f"Using Shazam-Tool shell script from {shazam_shell}")
        try:
            # Ensure script is executable
            os.chmod(shazam_shell, 0o755)
            
            # Change to Shazam-Tool directory to ensure proper virtual environment usage
            current_dir = os.getcwd()
            shazam_dir = shazam_shell.parent
            os.chdir(shazam_dir)
            
            # Run setup if venv doesn't exist
            if not (shazam_dir / "venv").exists():
                logger.info("Setting up Shazam-Tool environment...")
                subprocess.run([str(shazam_shell), "setup"], check=True)
            
            # Run the actual command
            result = subprocess.run([str(shazam_shell)] + args, check=True)
            
            # Restore original directory
            os.chdir(current_dir)
            
            sys.exit(result.returncode)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to run Shazam-Tool shell script: {e}")
            sys.exit(e.returncode)
    
    # Check for native binary in PATH as fallback
    if check_dependency("shazam-tool"):
        logger.info("Using shazam-tool binary from PATH")
        os.execvp("shazam-tool", ["shazam-tool"] + args)
        return
    
    # Check for Docker image as last resort
    if check_docker_image("shazam-tool"):
        logger.info("Using Docker image for shazam-tool")
        music_dir = os.path.expanduser("~/Music")
        
        cmd = [
            "docker", "run", "--rm", "-it",
            "-v", f"{music_dir}:/music",
            "shazam-tool"
        ] + args
        
        os.execvp("docker", cmd)
        return
    
    # Not found
    click.echo("Error: Shazam-Tool not found. Please ensure the tool is properly installed.")
    click.echo("You can try running the setup command: toolcrate shazam-tool setup")
    sys.exit(1)


def run_mdl():
    """Run the Music metadata utility."""
    args = sys.argv[1:]
    
    click.echo("Music metadata utility is not yet implemented.")
    sys.exit(1) 