#!/usr/bin/env python3
"""Manage cron jobs for toolcrate commands."""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import logging
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def find_command_path(command):
    """Find the full path to a command executable."""
    return shutil.which(command)

def check_crontab_for_job(job_identifier):
    """Check if a job with the given identifier already exists in crontab."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            # No crontab for user or other error
            return False
        
        # Check if the job identifier exists in the crontab
        return job_identifier in result.stdout
    except Exception as e:
        logger.error(f"Error checking crontab: {e}")
        return False

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
        # Look for config in the home directory first, then project root
        home_config = os.path.expanduser("~/.config/toolcrate/toolcrate.conf")
        if os.path.exists(home_config):
            config_file = home_config
        else:
            # Try to find project root
            current_dir = Path.cwd()
            while current_dir != current_dir.parent:
                if (current_dir / "toolcrate.conf").exists():
                    config_file = current_dir / "toolcrate.conf"
                    break
                current_dir = current_dir.parent
    
    if config_file and os.path.exists(config_file):
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
        logger.debug(f"Config file not found, using defaults")
    
    return config

def add_identify_tracks_cron(file_type, frequency="hourly"):
    """Add a cron job to run identify-tracks with the specified file type and frequency.
    
    Args:
        file_type: Either "wishlist" or "dj-sets"
        frequency: One of "hourly", "daily", "weekly", or a custom cron schedule
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Job identifier for comments in crontab
    job_id = f"# toolcrate-identify-{file_type}"
    
    # Check if the job already exists
    if check_crontab_for_job(job_id):
        print(f"A cron job for identify-{file_type} already exists. Remove it first if you want to change it.")
        return False
    
    # Find the full path to the toolcrate command
    toolcrate_path = find_command_path("toolcrate")
    if not toolcrate_path:
        print("Error: toolcrate command not found in PATH. Make sure it's installed correctly.")
        return False
    
    # Create the cron schedule based on frequency
    if frequency == "hourly":
        schedule = "0 * * * *"  # Run at minute 0 of every hour
    elif frequency == "daily":
        schedule = "0 0 * * *"  # Run at midnight every day
    elif frequency == "weekly":
        schedule = "0 0 * * 0"  # Run at midnight on Sunday
    else:
        # Assume it's a custom cron schedule
        schedule = frequency
    
    # Create the full cron command
    cron_cmd = f"{schedule} {toolcrate_path} identify-tracks --file-type {file_type} download > /tmp/toolcrate-identify-{file_type}.log 2>&1"
    
    # Get current crontab
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False
        )
        
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Create a temporary file with the new crontab
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
            if current_crontab:
                temp.write(current_crontab)
                if not current_crontab.endswith('\n'):
                    temp.write('\n')
            
            # Add the new job with comments
            temp.write(f"{job_id}\n")
            temp.write(f"{cron_cmd}\n")
            temp_path = temp.name
        
        # Install the new crontab
        subprocess.run(
            ["crontab", temp_path],
            check=True
        )
        
        # Remove the temporary file
        os.unlink(temp_path)
        
        print(f"Successfully added cron job to run identify-tracks for {file_type} {frequency}:")
        print(f"Schedule: {schedule}")
        print(f"Command: {toolcrate_path} identify-tracks --file-type {file_type} download")
        print("Output will be logged to /tmp/toolcrate-identify-{file_type}.log")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up cron job: {e}")
        print(f"Error setting up cron job: {e}")
        return False

def add_download_wishlist_cron(frequency="hourly"):
    """Add a cron job to run sldl with the wishlist file.
    
    Args:
        frequency: One of "hourly", "daily", "weekly", or a custom cron schedule
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Job identifier for comments in crontab
    job_id = "# toolcrate-download-wishlist"
    
    # Check if the job already exists
    if check_crontab_for_job(job_id):
        print(f"A cron job for download-wishlist already exists. Remove it first if you want to change it.")
        return False
    
    # Find the full path to the toolcrate command
    toolcrate_path = find_command_path("toolcrate")
    if not toolcrate_path:
        print("Error: toolcrate command not found in PATH. Make sure it's installed correctly.")
        return False
    
    # Get the wishlist file path from config
    config = read_config_file()
    wishlist_path = config["wishlist"]
    
    if not os.path.exists(wishlist_path):
        print(f"Warning: Wishlist file not found at {wishlist_path}. The cron job will be added anyway.")
    
    # Create the cron schedule based on frequency
    if frequency == "hourly":
        schedule = "30 * * * *"  # Run at minute 30 of every hour (offset from identify-tracks)
    elif frequency == "daily":
        schedule = "0 2 * * *"  # Run at 2 AM every day
    elif frequency == "weekly":
        schedule = "0 3 * * 0"  # Run at 3 AM on Sunday
    else:
        # Assume it's a custom cron schedule
        schedule = frequency
    
    # Create the full cron command
    cron_cmd = f"{schedule} {toolcrate_path} sldl --links-file {wishlist_path} > /tmp/toolcrate-download-wishlist.log 2>&1"
    
    # Get current crontab
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False
        )
        
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Create a temporary file with the new crontab
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
            if current_crontab:
                temp.write(current_crontab)
                if not current_crontab.endswith('\n'):
                    temp.write('\n')
            
            # Add the new job with comments
            temp.write(f"{job_id}\n")
            temp.write(f"{cron_cmd}\n")
            temp_path = temp.name
        
        # Install the new crontab
        subprocess.run(
            ["crontab", temp_path],
            check=True
        )
        
        # Remove the temporary file
        os.unlink(temp_path)
        
        print(f"Successfully added cron job to download wishlist items {frequency}:")
        print(f"Schedule: {schedule}")
        print(f"Command: {toolcrate_path} sldl --links-file {wishlist_path}")
        print(f"Wishlist file: {wishlist_path}")
        print("Output will be logged to /tmp/toolcrate-download-wishlist.log")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up cron job: {e}")
        print(f"Error setting up cron job: {e}")
        return False

def remove_scheduled_job(job_type):
    """Remove a cron job for the specified type.
    
    Args:
        job_type: Either "identify-tracks-wishlist", "identify-tracks-djsets", or "download-wishlist"
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Map job_type to job identifier
    if job_type == "identify-tracks-wishlist":
        job_id = "# toolcrate-identify-wishlist"
    elif job_type == "identify-tracks-djsets":
        job_id = "# toolcrate-identify-dj-sets"
    elif job_type == "identify-tracks-dj-sets":  # Alternative format with dash
        job_id = "# toolcrate-identify-dj-sets"
    elif job_type == "download-wishlist":
        job_id = "# toolcrate-download-wishlist"
    else:
        # Handle dynamic job types from the add_identify_tracks_cron function
        if job_type.startswith("identify-tracks-"):
            file_type = job_type.replace("identify-tracks-", "")
            job_id = f"# toolcrate-identify-{file_type}"
        else:
            print(f"Unknown job type: {job_type}")
            return False
    
    # Check if the job exists
    if not check_crontab_for_job(job_id):
        print(f"No cron job found for {job_type}.")
        return False
    
    # Get current crontab
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=True
        )
        
        current_crontab = result.stdout
        
        # Create a temporary file with the modified crontab
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
            # Skip the job we want to remove and the line after it
            lines = current_crontab.splitlines()
            i = 0
            while i < len(lines):
                if job_id in lines[i]:
                    # Skip this line and the next (the actual command)
                    i += 2
                    continue
                
                temp.write(lines[i] + '\n')
                i += 1
                
            temp_path = temp.name
        
        # Install the new crontab
        subprocess.run(
            ["crontab", temp_path],
            check=True
        )
        
        # Remove the temporary file
        os.unlink(temp_path)
        
        print(f"Successfully removed cron job for {job_type}.")
        return True
        
    except Exception as e:
        logger.error(f"Error removing cron job: {e}")
        print(f"Error removing cron job: {e}")
        return False

def list_scheduled_jobs():
    """List all toolcrate scheduled jobs.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print("No crontab found for current user.")
            return True
        
        current_crontab = result.stdout
        
        # Look for toolcrate jobs
        found = False
        lines = current_crontab.splitlines()
        i = 0
        
        print("Toolcrate scheduled jobs:")
        print("----------------------------------")
        
        while i < len(lines):
            line = lines[i]
            if "# toolcrate-" in line and i + 1 < len(lines):
                job_type = line.replace("# toolcrate-", "").strip()
                cron_cmd = lines[i + 1]
                
                # Extract schedule
                schedule_parts = cron_cmd.split()[:5]
                schedule = " ".join(schedule_parts)
                
                # Format job type for display
                if job_type == "identify-wishlist":
                    display_type = "Identify tracks (wishlist)"
                    command_type = "identify-tracks --file-type wishlist"
                elif job_type == "identify-dj-sets":
                    display_type = "Identify tracks (DJ sets)"
                    command_type = "identify-tracks --file-type dj-sets"
                elif job_type == "download-wishlist":
                    display_type = "Download wishlist items"
                    command_type = "download-wishlist"
                else:
                    display_type = job_type
                    command_type = job_type
                
                print(f"Type: {display_type}")
                print(f"Job Type (for removal): {command_type}")
                print(f"Schedule: {schedule}")
                print(f"Command: {' '.join(cron_cmd.split()[5:])}")
                print("----------------------------------")
                
                found = True
                i += 2
            else:
                i += 1
        
        if not found:
            print("No toolcrate scheduled jobs found.")
            
        return True
        
    except Exception as e:
        logger.error(f"Error listing cron jobs: {e}")
        print(f"Error listing cron jobs: {e}")
        return False

# For backward compatibility
remove_identify_tracks_cron = lambda file_type: remove_scheduled_job(f"identify-tracks-{file_type}")
list_identify_tracks_crons = list_scheduled_jobs
# Legacy compatibility (will be removed in future version)
remove_identify_tracks_wishlist = lambda: remove_scheduled_job("identify-tracks-wishlist")
remove_identify_tracks_djsets = lambda: remove_scheduled_job("identify-tracks-djsets")
remove_download_wishlist_cron = lambda: remove_scheduled_job("download-wishlist") 