#!/usr/bin/env python3
"""Process wishlist or DJ sets file and run shazam-tool on each entry."""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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
    return Path(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


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
        with open(config_file, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse key-value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Expand user paths (~/...)
                    if key in ["download-path", "wishlist", "dj-sets"] and "~" in value:
                        value = os.path.expanduser(value)

                    config[key] = value
    else:
        logger.warning(f"Config file {config_file} not found, using defaults")

    return config


def process_file(args):
    """Process each line in the specified file with shazam-tool."""
    config = read_config_file()

    # Determine which file to process based on file_type
    if args.file_type == "wishlist":
        file_path = config["wishlist"]
        file_type_name = "wishlist"
        show_output = False  # Don't show output for wishlist
    else:  # dj-sets
        file_path = config["dj-sets"]
        file_type_name = "DJ sets"
        show_output = True  # Show output for DJ sets

    if not os.path.exists(file_path):
        logger.error(f"{file_type_name.capitalize()} file not found at {file_path}")
        return 1

    # Create log directory if it doesn't exist
    logs_dir = Path("logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create log file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = logs_dir / f"process_{args.file_type}_{timestamp}.log"

    # Configure file handler for logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    logger.info(f"Processing {file_type_name} from {file_path}")
    logger.info(f"Log file: {log_file}")

    # Read the file
    with open(file_path, "r") as f:
        lines = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    logger.info(f"Found {len(lines)} items in {file_type_name}")

    success_count = 0
    failed_count = 0

    for i, item in enumerate(lines):
        logger.info(f"Processing item {i+1}/{len(lines)}: {item}")
        try:
            # Run toolcrate shazam-tool command
            cmd = ["toolcrate", "shazam-tool"]

            # Add additional arguments if provided
            if args.command:
                cmd.append(args.command)

            # Add the item from file
            cmd.append(item)

            # Add any additional arguments
            if args.extra_args:
                cmd.extend(args.extra_args)

            logger.info(f"Running command: {' '.join(cmd)}")

            # Execute the command
            if show_output:
                # Show real-time output for DJ sets
                print(f"\n=== Processing item {i+1}/{len(lines)}: {item} ===")
                result = subprocess.run(
                    cmd,
                    text=True,
                    check=False,  # Don't raise exception on non-zero exit
                )
                # Log the return code
                logger.info(f"Command exited with code: {result.returncode}")
            else:
                # Capture output silently for wishlist
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,  # Don't raise exception on non-zero exit
                )
                # Log detailed output
                logger.debug(f"Command output: {result.stdout}")

            if result.returncode == 0:
                logger.info(f"Successfully processed: {item}")
                success_count += 1
            else:
                logger.error(f"Failed to process: {item}")
                if not show_output and hasattr(result, "stderr"):
                    logger.error(f"Error: {result.stderr}")
                failed_count += 1

            # Add delay between requests to avoid rate limiting
            if i < len(lines) - 1:  # Don't delay after the last item
                if show_output:
                    print(f"Waiting {args.delay} seconds before next item...")
                time.sleep(args.delay)

        except Exception as e:
            logger.error(f"Error processing item {item}: {e}")
            failed_count += 1

    # Print summary
    logger.info(
        f"Processing complete: {success_count} succeeded, {failed_count} failed"
    )
    print(f"\nProcessing complete: {success_count} succeeded, {failed_count} failed")
    print(f"Log file: {log_file}")

    return 0


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Process wishlist or DJ sets file with shazam-tool"
    )
    parser.add_argument(
        "--file-type",
        choices=["wishlist", "dj-sets"],
        default="wishlist",
        help="Which file to process (default: wishlist)",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="download",
        help="Shazam-tool command to run (default: download)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=5,
        help="Delay in seconds between processing items (default: 5)",
    )
    parser.add_argument(
        "extra_args",
        nargs="*",
        help="Additional arguments to pass to the shazam-tool command",
    )

    args = parser.parse_args()

    return process_file(args)


if __name__ == "__main__":
    sys.exit(main())
