#!/usr/bin/env python3
"""Download queue processor for ToolCrate.

This module handles processing of download-queue.txt file, executing downloads
for each link and removing processed entries from the queue.
"""

import fcntl
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class QueueProcessor:
    """Processes download queue entries using slsk-batchdl in Docker."""

    def __init__(self, config_manager):
        """Initialize the queue processor.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config_manager = config_manager
        self.config = config_manager.config
        self.queue_config = self.config.get("queue", {})

        # Set up paths
        self.queue_file_path = Path(config_manager.config_dir) / self.queue_config.get(
            "file_path", "config/download-queue.txt"
        ).replace("config/", "")
        self.lock_file_path = Path(config_manager.config_dir) / self.queue_config.get(
            "lock_file", "config/.queue-lock"
        ).replace("config/", "")
        self.backup_file_path = Path(config_manager.config_dir) / self.queue_config.get(
            "backup_file", "config/download-queue-processed.txt"
        ).replace("config/", "")

        # Ensure queue file exists
        self.queue_file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.queue_file_path.exists():
            self.queue_file_path.touch()
            logger.info(f"Created queue file: {self.queue_file_path}")

    def acquire_lock(self) -> object | None:
        """Acquire a file lock to prevent concurrent processing.

        Returns:
            File handle if lock acquired, None if lock could not be acquired
        """
        try:
            lock_file = open(self.lock_file_path, "w")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.write(
                f"Queue processing started at {datetime.now().isoformat()}\n"
            )
            lock_file.flush()
            logger.info("Acquired queue processing lock")
            return lock_file
        except OSError as e:
            logger.warning(f"Could not acquire queue lock: {e}")
            return None

    def release_lock(self, lock_file):
        """Release the file lock.

        Args:
            lock_file: File handle from acquire_lock()
        """
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                logger.info("Released queue processing lock")
            except Exception as e:
                logger.warning(f"Error releasing lock: {e}")

    def read_queue_entries(self) -> list[str]:
        """Read and parse entries from the download queue file.

        Returns:
            List of non-empty, non-comment lines from the queue file
        """
        if not self.queue_file_path.exists():
            logger.info(f"Queue file does not exist: {self.queue_file_path}")
            return []

        try:
            with open(self.queue_file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Filter out empty lines and comments
            entries = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    entries.append(line)

            logger.info(f"Found {len(entries)} entries in queue file")
            return entries

        except Exception as e:
            logger.error(f"Error reading queue file {self.queue_file_path}: {e}")
            return []

    def build_sldl_command(self, entry: str) -> list[str]:
        """Build the sldl command for a queue entry.

        Args:
            entry: URL or search term to download

        Returns:
            List of command arguments for sldl
        """
        # Base command with standard config file
        cmd = ["sldl", "-c", "/config/sldl.conf"]

        # Add the entry (URL or search term)
        cmd.append(entry)

        # Override download directory to downloads (not library)
        download_dir = self.queue_config.get("download_dir", "/data/downloads")
        cmd.extend(["-p", download_dir])

        # Add queue-specific flags from settings
        queue_settings = self.queue_config.get("settings", {})

        if queue_settings.get("skip_existing", True):
            # Skip existing files (default for queue)
            cmd.append("--skip-existing")

        if queue_settings.get("desperate_search", False):
            # Use relaxed matching if enabled
            cmd.append("--desperate")

        if queue_settings.get("use_ytdlp", True):
            # Enable yt-dlp fallback
            cmd.append("--yt-dlp")

        # Add timeout if specified
        search_timeout = queue_settings.get("search_timeout")
        if search_timeout:
            cmd.extend(["--search-timeout", str(search_timeout)])

        return cmd

    def process_queue_entry(self, entry: str) -> bool:
        """Process a single queue entry.

        Args:
            entry: URL or search term to download

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing queue entry: {entry}")

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
                logger.info(f"Successfully processed queue entry: {entry}")
                if result.stdout:
                    logger.info(f"Command output: {result.stdout}")
                return True
            else:
                logger.error(f"Failed to process queue entry: {entry}")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                logger.error(f"Standard output: {result.stdout}")
                logger.error(f"Command executed: {' '.join(docker_cmd)}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout processing queue entry: {entry}")
            return False
        except Exception as e:
            logger.error(f"Error processing queue entry {entry}: {e}")
            return False

    def backup_processed_entry(self, entry: str):
        """Backup a processed entry to the backup file.

        Args:
            entry: The processed entry to backup
        """
        if not self.queue_config.get("backup_processed", True):
            return

        try:
            with open(self.backup_file_path, "a", encoding="utf-8") as f:
                timestamp = datetime.now().isoformat()
                f.write(f"# Processed at {timestamp}\n{entry}\n\n")
            logger.debug(f"Backed up processed entry: {entry}")
        except Exception as e:
            logger.warning(f"Failed to backup processed entry: {e}")

    def remove_processed_entries(self, processed_entries: list[str]):
        """Remove processed entries from the queue file.

        Args:
            processed_entries: List of entries that were successfully processed
        """
        if not processed_entries:
            return

        try:
            # Read current queue file
            with open(self.queue_file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Remove processed entries while preserving comments and formatting
            remaining_lines = []
            for line in lines:
                stripped_line = line.strip()
                if stripped_line in processed_entries:
                    # Skip this line (remove it)
                    logger.debug(f"Removing processed entry: {stripped_line}")
                    continue
                else:
                    # Keep this line
                    remaining_lines.append(line)

            # Write back the remaining lines
            with open(self.queue_file_path, "w", encoding="utf-8") as f:
                f.writelines(remaining_lines)

            logger.info(
                f"Removed {len(processed_entries)} processed entries from queue file"
            )

        except Exception as e:
            logger.error(f"Error removing processed entries from queue file: {e}")

    def process_all_entries(self) -> dict[str, Any]:
        """Process all entries in the download queue.

        Returns:
            Dictionary with processing results
        """
        if not self.queue_config.get("enabled", True):
            logger.info("Queue processing is disabled")
            return {"status": "disabled", "processed": 0, "failed": 0}

        # Try to acquire lock
        lock_file = self.acquire_lock()
        if not lock_file:
            logger.warning(
                "Could not acquire queue processing lock - another process may be running"
            )
            return {"status": "locked", "processed": 0, "failed": 0}

        try:
            entries = self.read_queue_entries()

            if not entries:
                logger.info("No entries found in download queue")
                return {"status": "empty", "processed": 0, "failed": 0}

            logger.info(f"Starting to process {len(entries)} queue entries")

            processed = 0
            failed = 0
            processed_entries = []
            results = []

            for entry in entries:
                success = self.process_queue_entry(entry)
                if success:
                    processed += 1
                    processed_entries.append(entry)
                    # Backup the processed entry
                    self.backup_processed_entry(entry)
                else:
                    failed += 1

                results.append({"entry": entry, "success": success})

            # Remove successfully processed entries from queue file
            if processed_entries:
                self.remove_processed_entries(processed_entries)

            logger.info(
                f"Queue processing complete: {processed} successful, {failed} failed"
            )

            return {
                "status": "completed",
                "processed": processed,
                "failed": failed,
                "total": len(entries),
                "results": results,
            }

        finally:
            self.release_lock(lock_file)


def main():
    """Main entry point for queue processing."""
    import argparse

    from ..config.manager import ConfigManager

    parser = argparse.ArgumentParser(description="Process download queue")
    parser.add_argument(
        "--config", default="config/toolcrate.yaml", help="Path to configuration file"
    )
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        config_manager = ConfigManager(args.config)
        processor = QueueProcessor(config_manager)

        results = processor.process_all_entries()

        print(f"Queue processing {results['status']}")
        if results["status"] == "completed":
            print(f"Processed: {results['processed']}/{results['total']}")
            print(f"Failed: {results['failed']}/{results['total']}")

    except Exception as e:
        logger.error(f"Error in queue processing: {e}")
        exit(1)


if __name__ == "__main__":
    main()
