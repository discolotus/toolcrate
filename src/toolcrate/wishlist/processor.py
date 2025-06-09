#!/usr/bin/env python3
"""Wishlist processor for ToolCrate scheduled downloads."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


class WishlistProcessor:
    """Processes wishlist.txt file for scheduled downloads."""

    def __init__(self, config_manager: ConfigManager | None = None):
        """Initialize the wishlist processor.

        Args:
            config_manager: Optional ConfigManager instance. If None, creates a new one.
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.config
        self.wishlist_config = self.config.get("wishlist", {})

    def get_wishlist_file_path(self) -> Path:
        """Get the path to the wishlist file."""
        wishlist_path = self.wishlist_config.get("file_path", "config/wishlist.txt")
        if not os.path.isabs(wishlist_path):
            # Make relative to project root
            project_root = self.config_manager.config_dir.parent
            return project_root / wishlist_path
        return Path(wishlist_path)

    def ensure_wishlist_file_exists(self) -> Path:
        """Ensure the wishlist file exists, create if it doesn't."""
        wishlist_path = self.get_wishlist_file_path()

        if not wishlist_path.exists():
            # Create the file with example content
            wishlist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(wishlist_path, "w") as f:
                f.write("# ToolCrate Wishlist File\n")
                f.write("# Add playlist URLs or search terms, one per line\n")
                f.write("# Examples:\n")
                f.write("# https://open.spotify.com/playlist/your-playlist-id\n")
                f.write("# https://youtube.com/playlist?list=your-playlist-id\n")
                f.write('# "Artist Name - Song Title"\n')
                f.write('# artist:"Artist Name" album:"Album Name"\n')
                f.write("\n")
            logger.info(f"Created wishlist file at {wishlist_path}")

        return wishlist_path

    def read_wishlist_entries(self) -> list[str]:
        """Read and parse wishlist entries from the file."""
        wishlist_path = self.ensure_wishlist_file_exists()

        entries = []
        try:
            with open(wishlist_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        entries.append(line)
                        logger.debug(
                            f"Added wishlist entry from line {line_num}: {line}"
                        )
        except Exception as e:
            logger.error(f"Error reading wishlist file {wishlist_path}: {e}")
            raise

        logger.info(f"Found {len(entries)} entries in wishlist")
        return entries

    def build_sldl_command(self, entry: str) -> list[str]:
        """Build the sldl command for a wishlist entry.

        Args:
            entry: The wishlist entry (URL or search term)

        Returns:
            List of command arguments for sldl
        """
        # Base command with wishlist-specific config file
        cmd = ["sldl", "-c", "/config/sldl-wishlist.conf"]

        # Add the entry (URL or search term)
        cmd.append(entry)

        # Override download directory to library
        download_dir = self.wishlist_config.get("download_dir", "/data/library")
        cmd.extend(["-p", download_dir])

        # Set index file location
        if self.wishlist_config.get("index_in_playlist_folder", True):
            # Use default behavior - index in playlist folder
            # slsk-batchdl will automatically place index in the playlist folder
            pass
        else:
            # Use a global wishlist index
            cmd.extend(["--index-path", "/data/wishlist-index.sldl"])

        # Add wishlist-specific flags
        wishlist_settings = self.wishlist_config.get("settings", {})

        if not wishlist_settings.get("skip_existing", False):
            # Don't skip existing files - check them for better quality
            cmd.append("--no-skip-existing")

        if wishlist_settings.get("skip_check_pref_cond", True):
            # Continue searching for preferred conditions even if file exists
            cmd.append("--skip-check-pref-cond")

        if wishlist_settings.get("desperate_search", True):
            # Use relaxed matching
            cmd.append("--desperate")

        if wishlist_settings.get("use_ytdlp", True):
            # Enable yt-dlp fallback
            cmd.append("--yt-dlp")

        # Add timeout if specified
        search_timeout = wishlist_settings.get("search_timeout")
        if search_timeout:
            cmd.extend(["--search-timeout", str(search_timeout)])

        # Add max retries if specified
        max_retries = wishlist_settings.get("max_retries_per_track")
        if max_retries:
            cmd.extend(["--max-retries", str(max_retries)])

        # Enable fast search if configured
        if wishlist_settings.get("fast_search", False):
            cmd.append("--fast-search")

        logger.debug(f"Built sldl command: {' '.join(cmd)}")
        return cmd

    def process_wishlist_entry(self, entry: str) -> bool:
        """Process a single wishlist entry.

        Args:
            entry: The wishlist entry to process

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing wishlist entry: {entry}")

        try:
            # Build the command
            cmd = self.build_sldl_command(entry)

            # Execute via docker
            docker_cmd = ["docker", "exec", "-i", "sldl"] + cmd

            logger.info(f"Executing: {' '.join(docker_cmd)}")

            # Run the command
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout per entry
            )

            if result.returncode == 0:
                logger.info(f"Successfully processed wishlist entry: {entry}")
                if result.stdout:
                    logger.info(f"Command output: {result.stdout}")
                return True
            else:
                logger.error(f"Failed to process wishlist entry: {entry}")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                logger.error(f"Standard output: {result.stdout}")
                logger.error(f"Command executed: {' '.join(docker_cmd)}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout processing wishlist entry: {entry}")
            return False
        except Exception as e:
            logger.error(f"Error processing wishlist entry {entry}: {e}")
            return False

    def process_all_entries(self) -> dict[str, Any]:
        """Process all entries in the wishlist.

        Returns:
            Dictionary with processing results
        """
        if not self.wishlist_config.get("enabled", True):
            logger.info("Wishlist processing is disabled")
            return {"status": "disabled", "processed": 0, "failed": 0}

        # Generate wishlist-specific sldl.conf before processing
        try:
            self.config_manager.generate_wishlist_sldl_conf()
            logger.info("Generated wishlist-specific sldl.conf")
        except Exception as e:
            logger.error(f"Failed to generate wishlist sldl.conf: {e}")
            return {"status": "config_error", "processed": 0, "failed": 0}

        entries = self.read_wishlist_entries()

        if not entries:
            logger.info("No entries found in wishlist")
            return {"status": "empty", "processed": 0, "failed": 0}

        logger.info(f"Starting to process {len(entries)} wishlist entries")

        processed = 0
        failed = 0
        results = []

        for entry in entries:
            success = self.process_wishlist_entry(entry)
            if success:
                processed += 1
            else:
                failed += 1

            results.append({"entry": entry, "success": success})

        logger.info(
            f"Wishlist processing complete: {processed} successful, {failed} failed"
        )

        # Show recent log summary
        self._show_log_summary()

        return {
            "status": "completed",
            "processed": processed,
            "failed": failed,
            "total": len(entries),
            "results": results,
        }

    def _show_log_summary(self):
        """Show a summary of recent activity from the sldl log file."""
        try:
            # Look for the log file in the data directory
            log_path = Path("data/sldl.log")
            if not log_path.exists():
                logger.debug("No sldl.log file found")
                return

            # Read the last 50 lines of the log file
            with open(log_path) as f:
                lines = f.readlines()

            recent_lines = lines[-50:] if len(lines) > 50 else lines

            # Extract key information
            downloads = []
            completed_count = 0
            failed_count = 0

            for line in recent_lines:
                line = line.strip()
                if (
                    "Succeeded:" in line or "Succeded:" in line
                ):  # Note: slsk-batchdl has a typo "Succeded"
                    # Extract filename from log line
                    if "\\..\\" in line:
                        filename = line.split("\\..\\")[-1].split(" [")[0]
                        downloads.append(f"✅ {filename}")
                        completed_count += 1
                elif "Failed:" in line or "SearchAndDownloadException" in line:
                    failed_count += 1
                elif "Completed:" in line and "succeeded" in line:
                    # Extract final summary
                    parts = line.split("Completed: ")
                    if len(parts) > 1:
                        summary = parts[1]
                        logger.info(f"📊 Final summary: {summary}")

            # Show recent downloads
            if downloads:
                logger.info("🎵 Recent successful downloads:")
                for download in downloads[-10:]:  # Show last 10 downloads
                    logger.info(f"   {download}")

            if completed_count > 0 or failed_count > 0:
                logger.info(
                    f"📈 Session stats: {completed_count} succeeded, {failed_count} failed"
                )

        except Exception as e:
            logger.debug(f"Could not read log summary: {e}")


def main():
    """Main entry point for wishlist processing."""
    import argparse

    parser = argparse.ArgumentParser(description="ToolCrate Wishlist Processor")
    parser.add_argument(
        "--config",
        "-c",
        default="config/toolcrate.yaml",
        help="Path to the YAML configuration file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        config_manager = ConfigManager(args.config)
        processor = WishlistProcessor(config_manager)

        results = processor.process_all_entries()

        print(f"Wishlist processing {results['status']}")
        if results["status"] == "completed":
            print(f"Processed: {results['processed']}/{results['total']}")
            print(f"Failed: {results['failed']}/{results['total']}")

    except Exception as e:
        logger.error(f"Error in wishlist processing: {e}")
        exit(1)


if __name__ == "__main__":
    main()
