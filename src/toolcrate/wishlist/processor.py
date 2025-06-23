#!/usr/bin/env python3
"""Wishlist processor for ToolCrate scheduled downloads."""

import os
import subprocess
import logging
import threading
import queue
import time
import signal
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..config.manager import ConfigManager
from .post_processor import PostProcessor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set log level to INFO

# Remove manual logging configuration to prevent duplicate output
# formatter = logging.Formatter('%(levelname)s - %(message)s')
# handler = logging.StreamHandler()
# handler.setFormatter(formatter)
# logger.addHandler(handler)

# Remove duplicate handler to prevent double output
# for h in logger.handlers[:]:
#     if h is not handler:
#         logger.removeHandler(h)

class WishlistProcessor:
    """Processes wishlist.txt file for scheduled downloads."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the wishlist processor.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, creates a new one.
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.config
        self.wishlist_config = self.config.get('wishlist', {})
        
        # Initialize post-processor
        post_processing_config = self.wishlist_config.get('post_processing', {})
        self.post_processor = PostProcessor(post_processing_config)
        
    def get_wishlist_file_path(self) -> Path:
        """Get the path to the wishlist file."""
        wishlist_path = self.wishlist_config.get('file_path', 'config/wishlist.txt')
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
            with open(wishlist_path, 'w') as f:
                f.write("# ToolCrate Wishlist File\n")
                f.write("# Add playlist URLs or search terms, one per line\n")
                f.write("# Examples:\n")
                f.write("# https://open.spotify.com/playlist/your-playlist-id\n")
                f.write("# https://youtube.com/playlist?list=your-playlist-id\n")
                f.write("# \"Artist Name - Song Title\"\n")
                f.write("# artist:\"Artist Name\" album:\"Album Name\"\n")
                f.write("\n")
            logger.info(f"Created wishlist file at {wishlist_path}")
        
        return wishlist_path
    
    def read_wishlist_entries(self) -> List[str]:
        """Read and parse wishlist entries from the file."""
        wishlist_path = self.ensure_wishlist_file_exists()
        
        entries = []
        try:
            with open(wishlist_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        entries.append(line)
                        logger.debug(f"Added wishlist entry from line {line_num}: {line}")
        except Exception as e:
            logger.error(f"Error reading wishlist file {wishlist_path}: {e}")
            raise
        
        logger.info(f"Found {len(entries)} entries in wishlist")
        return entries
    
    def build_sldl_command(self, entry: str) -> List[str]:
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
        download_dir = self.wishlist_config.get('download_dir', '/library')
        cmd.extend(["-p", download_dir])
        
        # Set index file location
        if self.wishlist_config.get('index_in_playlist_folder', True):
            # Use default behavior - index in playlist folder
            # slsk-batchdl will automatically place index in the playlist folder
            pass
        else:
            # Use a global wishlist index
            cmd.extend(["--index-path", "/data/wishlist-index.sldl"])
        
        # Add wishlist-specific flags
        wishlist_settings = self.wishlist_config.get('settings', {})
        
        # Handle existing file behavior
        skip_existing = wishlist_settings.get('skip_existing', True)  # Default to True (normal behavior)
        check_for_better_quality = self.wishlist_config.get('check_existing_for_better_quality', False)
        
        if not skip_existing or check_for_better_quality:
            # Don't skip existing files if explicitly disabled OR if checking for better quality
            cmd.append("--no-skip-existing")
        
        if wishlist_settings.get('skip_check_pref_cond', False):
            # Skip checking preferred conditions (disables quality upgrades) 
            cmd.append("--skip-check-pref-cond")
        
        if wishlist_settings.get('desperate_search', True):
            # Use relaxed matching
            cmd.append("--desperate")
        
        if wishlist_settings.get('use_ytdlp', True):
            # Enable yt-dlp fallback
            cmd.append("--yt-dlp")
        
        # Add timeout if specified
        search_timeout = wishlist_settings.get('search_timeout')
        if search_timeout:
            cmd.extend(["--search-timeout", str(search_timeout)])
        
        # Add max retries if specified
        max_retries = wishlist_settings.get('max_retries_per_track')
        if max_retries:
            cmd.extend(["--max-retries", str(max_retries)])
        
        # Enable fast search if configured
        if wishlist_settings.get('fast_search', False):
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

        # Keep track of the current process for cleanup
        current_process = None
        
        def cleanup_process():
            """Kill any running sldl processes in the container."""
            try:
                subprocess.run(
                    ["docker", "exec", "sldl", "pkill", "-f", "sldl"],
                    capture_output=True,
                    timeout=5
                )
                logger.info("Cleaned up orphaned sldl processes")
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")

        try:
            # Build the command
            cmd = self.build_sldl_command(entry)
            
            # Execute via docker
            docker_cmd = [
                "docker", "exec", "-i", "sldl"
            ] + cmd
            
            logger.info(f"Executing: {' '.join(docker_cmd)}")
            
            # Run the command with real-time output
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            current_process = process
            
            # Create queues for thread-safe communication
            output_queue = queue.Queue()
            
            def read_stream(stream, stream_name):
                """Read from a stream and put output in queue with stream identifier."""
                try:
                    for line in iter(stream.readline, ''):
                        if line:
                            output_queue.put((stream_name, line.rstrip()))
                except Exception as e:
                    output_queue.put((stream_name, f"Error reading {stream_name}: {e}"))
                finally:
                    # Signal that this stream is done
                    output_queue.put((stream_name, None))
            
            # Start threads to read stdout and stderr concurrently
            stdout_thread = threading.Thread(
                target=read_stream, 
                args=(process.stdout, 'stdout'),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_stream, 
                args=(process.stderr, 'stderr'),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Track which streams are still active
            active_streams = {'stdout', 'stderr'}
            stdout_lines = []
            stderr_lines = []
            
            # Process output in real-time
            while active_streams and process.poll() is None:
                try:
                    # Get output with a short timeout to check process status
                    stream_name, line = output_queue.get(timeout=0.1)
                    
                    if line is None:
                        # Stream finished
                        active_streams.discard(stream_name)
                    else:
                        if stream_name == 'stdout':
                            stdout_lines.append(line)
                            logger.info(f"SLDL: {line}")
                        elif stream_name == 'stderr':
                            stderr_lines.append(line)
                            logger.error(f"SLDL ERROR: {line}")
                            
                except queue.Empty:
                    # No output available, continue to check process status
                    continue
            
            # Process finished, drain any remaining output
            process.wait()  # Ensure process is fully complete
            
            # Get any remaining output from the queue
            while not output_queue.empty():
                try:
                    stream_name, line = output_queue.get_nowait()
                    if line is not None:
                        if stream_name == 'stdout':
                            stdout_lines.append(line)
                            logger.info(f"SLDL: {line}")
                        elif stream_name == 'stderr':
                            stderr_lines.append(line)
                            logger.error(f"SLDL ERROR: {line}")
                except queue.Empty:
                    break
            
            # Wait for threads to complete
            stdout_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)

            return_code = process.returncode
            
            if return_code == 0:
                logger.info(f"Successfully processed wishlist entry: {entry}")
                return True
            else:
                logger.error(f"Failed to process wishlist entry: {entry}")
                logger.error(f"Return code: {return_code}")
                logger.error(f"Command executed: {' '.join(docker_cmd)}")
                return False
                
        except KeyboardInterrupt:
            logger.warning("Interrupted by user, cleaning up...")
            if current_process:
                try:
                    current_process.terminate()
                    current_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    current_process.kill()
                except Exception:
                    pass
            cleanup_process()
            raise  # Re-raise to stop processing
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout processing wishlist entry: {entry}")
            cleanup_process()
            return False
        except Exception as e:
            logger.error(f"Error processing wishlist entry {entry}: {e}")
            cleanup_process()
            return False
    
    def process_all_entries(self) -> Dict[str, Any]:
        """Process all entries in the wishlist.

        Returns:
            Dictionary with processing results
        """
        if not self.wishlist_config.get('enabled', True):
            logger.info("Wishlist processing is disabled")
            return {'status': 'disabled', 'processed': 0, 'failed': 0}

        # Generate wishlist-specific sldl.conf before processing
        try:
            self.config_manager.generate_wishlist_sldl_conf()
            logger.info("Generated wishlist-specific sldl.conf")
        except Exception as e:
            logger.error(f"Failed to generate wishlist sldl.conf: {e}")
            return {'status': 'config_error', 'processed': 0, 'failed': 0}

        entries = self.read_wishlist_entries()
        
        if not entries:
            logger.info("No entries found in wishlist")
            return {'status': 'empty', 'processed': 0, 'failed': 0}
        
        logger.info(f"Starting to process {len(entries)} wishlist entries")
        
        processed = 0
        failed = 0
        results = []
        
        for i, entry in enumerate(entries):
            # Wait for any previous sldl processes to fully exit (except first entry)
            if i > 0:
                logger.info("Waiting for previous sldl process to fully exit...")
                self._wait_for_sldl_processes_to_exit()
            
            success = self.process_wishlist_entry(entry)
            if success:
                processed += 1
            else:
                failed += 1
            
            results.append({
                'entry': entry,
                'success': success
            })
        
        logger.info(f"Wishlist processing complete: {processed} successful, {failed} failed")

        # Run post-processing if enabled
        post_processing_results = self._run_post_processing()

        # Show recent log summary
        self._show_log_summary()

        return {
            'status': 'completed',
            'processed': processed,
            'failed': failed,
            'total': len(entries),
            'results': results,
            'post_processing': post_processing_results
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
            with open(log_path, 'r') as f:
                lines = f.readlines()

            recent_lines = lines[-50:] if len(lines) > 50 else lines

            # Extract key information
            downloads = []
            completed_count = 0
            failed_count = 0

            for line in recent_lines:
                line = line.strip()
                if "Succeeded:" in line or "Succeded:" in line:  # Note: slsk-batchdl has a typo "Succeded"
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
                logger.info(f"📈 Session stats: {completed_count} succeeded, {failed_count} failed")

        except Exception as e:
            logger.debug(f"Could not read log summary: {e}")

    def _wait_for_sldl_processes_to_exit(self, max_wait_time: int = 60):
        """Wait for any running sldl processes in the container to exit.
        
        Args:
            max_wait_time: Maximum time to wait in seconds
        """
        import subprocess
        
        wait_time = 0
        check_interval = 2
        
        while wait_time < max_wait_time:
            try:
                # Check for running sldl processes in the container
                result = subprocess.run(
                    ["docker", "exec", "sldl", "pgrep", "-f", "sldl"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0:
                    # No sldl processes found, safe to continue
                    logger.info("No active sldl processes detected, safe to proceed")
                    return
                
                # sldl processes still running
                process_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                logger.info(f"Found {process_count} active sldl process(es), waiting {check_interval}s...")
                time.sleep(check_interval)
                wait_time += check_interval
                
            except subprocess.TimeoutExpired:
                logger.warning("Timeout checking for sldl processes, proceeding anyway")
                return
            except Exception as e:
                logger.warning(f"Error checking for sldl processes: {e}, proceeding anyway")
                return
        
        logger.warning(f"Timed out waiting for sldl processes to exit after {max_wait_time}s, proceeding anyway")

    def _run_post_processing(self) -> Dict[str, Any]:
        """Run post-processing on downloaded files.
        
        Returns:
            Dictionary with post-processing results
        """
        if not self.post_processor.enabled:
            logger.debug("Post-processing disabled")
            return {'status': 'disabled', 'processed': 0}

        # Check if ffmpeg is available for transcoding
        if self.post_processor.transcode_opus and not self.post_processor.check_ffmpeg_available():
            logger.warning("ffmpeg not available - opus transcoding disabled")
            return {'status': 'error', 'message': 'ffmpeg not available', 'processed': 0}

        # Get download directory and index file paths
        download_dir = Path(self.wishlist_config.get('download_dir', '/library'))
        
        # Determine index file path
        index_path = None
        if self.wishlist_config.get('index_in_playlist_folder', True):
            # Look for index files in subdirectories
            index_files = list(download_dir.rglob("*.sldl"))
            if index_files:
                # Use the most recently modified index file
                index_path = max(index_files, key=lambda p: p.stat().st_mtime)
                logger.debug(f"Using index file: {index_path}")
        else:
            # Use global index
            index_path = Path("/data/wishlist-index.sldl")

        logger.info("Starting post-processing of downloaded files...")
        
        try:
            results = self.post_processor.process_directory(download_dir, index_path)
            
            if results['processed'] > 0:
                logger.info(f"Post-processing completed: {results['processed']} files processed")
                if results['transcoded']:
                    logger.info(f"Transcoded {len(results['transcoded'])} opus files to FLAC")
            else:
                logger.debug("No files needed post-processing")
                
            if results['errors']:
                logger.warning(f"Post-processing errors: {len(results['errors'])}")
                for error in results['errors']:
                    logger.warning(f"  {error}")
            
            return results
            
        except Exception as e:
            error_msg = f"Post-processing failed: {e}"
            logger.error(error_msg)
            return {'status': 'error', 'message': error_msg, 'processed': 0}

    def process_wishlist(self):
        """Process the wishlist file and run sldl for each entry."""
        wishlist_path = self.get_wishlist_file_path()
        if not wishlist_path.exists():
            logger.error(f"Wishlist file not found: {wishlist_path}")
            return False

        with open(wishlist_path, 'r') as f:
            entries = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

        for entry in entries:
            logger.info(f"Processing wishlist entry: {entry}")
            # Run sldl command for this entry
            cmd = ["sldl", "-c", "/config/sldl.conf", "--links-file", str(wishlist_path)]
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
                for line in process.stdout:
                    logger.info(line.strip())
                process.wait()
                if process.returncode != 0:
                    logger.error(f"Error processing {entry}: {process.stderr.read()}")
                    return False
            except Exception as e:
                logger.error(f"Error processing {entry}: {e}")
                return False
        return True


def main():
    """Main entry point for wishlist processing."""
    import argparse
    
    def signal_handler(signum, frame):
        """Handle interrupt signals by cleaning up docker processes."""
        logger.warning("Received interrupt signal, cleaning up Docker processes...")
        try:
            subprocess.run(
                ["docker", "exec", "sldl", "pkill", "-f", "sldl"],
                capture_output=True,
                timeout=5
            )
            logger.info("Docker processes cleaned up")
        except Exception as e:
            logger.debug(f"Error during signal cleanup: {e}")
        exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="ToolCrate Wishlist Processor")
    parser.add_argument("--config", "-c", default="config/toolcrate.yaml",
                       help="Path to the YAML configuration file")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s - %(message)s'
    )
    
    try:
        config_manager = ConfigManager(args.config)
        processor = WishlistProcessor(config_manager)
        
        results = processor.process_all_entries()
        
        print(f"Wishlist processing {results['status']}")
        if results['status'] == 'completed':
            print(f"Processed: {results['processed']}/{results['total']}")
            print(f"Failed: {results['failed']}/{results['total']}")
        
    except Exception as e:
        logger.error(f"Error in wishlist processing: {e}")
        exit(1)


if __name__ == "__main__":
    main()
