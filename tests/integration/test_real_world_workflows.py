"""Integration tests for real-world workflows that users actually run."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestRealURLProcessing(unittest.TestCase):
    """Test processing of real URLs from major music platforms."""

    def setUp(self):
        """Set up test fixtures with real URLs."""
        self.real_urls = {
            # Well-known public playlists that are guaranteed to be accessible
            "spotify_top50_global": "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF",  # Top 50 Global
            "youtube_music_trending": "https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",  # YouTube Music Trending
            "soundcloud_public": "https://soundcloud.com/discover",
            # Test URLs for validation
            "youtube_video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - definitely public
            "spotify_track": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",  # Mr. Brightside - public track
        }

    @patch("toolcrate.cli.wrappers.os.execvp")
    @patch("toolcrate.cli.wrappers.subprocess.run")
    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    @patch("pathlib.Path.exists")
    def test_spotify_playlist_command_execution(
        self, mock_exists, mock_get_root, mock_check_dep, mock_subprocess, mock_execvp
    ):
        """Test that Spotify playlist URLs are properly processed."""
        # Setup mocks
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")
        mock_exists.return_value = True

        # Mock container running
        mock_result = MagicMock()
        mock_result.stdout = "sldl"
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with patch("toolcrate.config.manager.ConfigManager.generate_sldl_conf"):
            from toolcrate.cli.wrappers import run_sldl_docker_command

            # Test with real Spotify URL
            run_sldl_docker_command({}, [self.real_urls["spotify_top50_global"]])

            # Verify docker exec was called
            mock_execvp.assert_called_once()
            args = mock_execvp.call_args[0]
            cmd_args = args[1]

            # Should include the Spotify URL
            self.assertIn(self.real_urls["spotify_top50_global"], cmd_args)
            # Should include config file
            self.assertIn("-c", cmd_args)
            self.assertIn("/config/sldl.conf", cmd_args)

    @patch("toolcrate.cli.wrappers.os.execvp")
    @patch("toolcrate.cli.wrappers.subprocess.run")
    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    @patch("pathlib.Path.exists")
    def test_youtube_playlist_command_execution(
        self, mock_exists, mock_get_root, mock_check_dep, mock_subprocess, mock_execvp
    ):
        """Test that YouTube playlist URLs are properly processed."""
        # Setup mocks
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")
        mock_exists.return_value = True

        # Mock container running
        mock_result = MagicMock()
        mock_result.stdout = "sldl"
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with patch("toolcrate.config.manager.ConfigManager.generate_sldl_conf"):
            from toolcrate.cli.wrappers import run_sldl_docker_command

            # Test with real YouTube URL
            run_sldl_docker_command({}, [self.real_urls["youtube_music_trending"]])

            # Verify docker exec was called
            mock_execvp.assert_called_once()
            args = mock_execvp.call_args[0]
            cmd_args = args[1]

            # Should include the YouTube URL
            self.assertIn(self.real_urls["youtube_music_trending"], cmd_args)
            # Should include config file
            self.assertIn("-c", cmd_args)
            self.assertIn("/config/sldl.conf", cmd_args)

    def test_links_file_processing_with_real_urls(self):
        """Test processing a file with multiple real URLs."""
        # Create a temporary file with real URLs
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# Real URLs for testing\n")
            f.write(f"{self.real_urls['spotify_top50_global']}\n")
            f.write(f"{self.real_urls['youtube_video']}\n")
            f.write("# Comment line should be ignored\n")
            f.write(f"{self.real_urls['spotify_track']}\n")
            temp_file = f.name

        try:
            # Test that the command recognizes the --links-file option
            result = subprocess.run(
                ["toolcrate", "sldl", "--links-file", temp_file],
                capture_output=True,
                text=True,
                check=False,
            )

            # Should not show "unknown option" error
            self.assertNotIn("No such option", result.stdout)
            self.assertNotIn("Unrecognized option", result.stdout)
            # May fail due to docker, but option should be recognized

        finally:
            os.unlink(temp_file)


class TestWishlistWorkflow(unittest.TestCase):
    """Test complete wishlist processing workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_wishlist_content = """# Test wishlist file
# Spotify playlists
https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF

# YouTube playlists
https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj

# Search terms
Artist Name - Song Title
Another Artist - Another Song
"""

    @patch("toolcrate.wishlist.processor.WishlistProcessor.read_wishlist_entries")
    @patch("toolcrate.wishlist.processor.WishlistProcessor.process_wishlist_entry")
    def test_wishlist_processor_handles_mixed_content(
        self, mock_process_entry, mock_read_entries
    ):
        """Test that wishlist processor handles URLs and search terms."""
        # Mock reading entries
        mock_read_entries.return_value = [
            "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF",
            "https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
            "Artist Name - Song Title",
        ]

        # Mock successful processing
        mock_process_entry.return_value = True

        try:
            from toolcrate.config.manager import ConfigManager
            from toolcrate.wishlist.processor import WishlistProcessor

            # Create processor with mocked config
            with patch.object(ConfigManager, "__init__", return_value=None):
                processor = WishlistProcessor.__new__(WishlistProcessor)
                processor.wishlist_config = {"enabled": True}
                processor.config_manager = MagicMock()

                # Test processing
                result = processor.process_all_entries()

                # Should process all entries
                self.assertEqual(mock_process_entry.call_count, 3)
                self.assertEqual(result["processed"], 3)
                self.assertEqual(result["failed"], 0)

        except ImportError:
            self.skipTest("WishlistProcessor not available")

    def test_wishlist_run_command_structure(self):
        """Test that wishlist-run command has proper structure."""
        result = subprocess.run(
            ["toolcrate", "wishlist-run", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should show help or recognize command
        self.assertNotIn("No such command", result.stdout)


class TestSchedulingWorkflow(unittest.TestCase):
    """Test complete scheduling workflow."""

    @patch("toolcrate.cli.schedule.add_toolcrate_jobs_to_crontab")
    @patch("toolcrate.config.manager.ConfigManager")
    def test_schedule_add_hourly_workflow(
        self, mock_config_manager, mock_add_to_crontab
    ):
        """Test adding hourly schedule workflow."""
        # Mock successful crontab addition
        mock_add_to_crontab.return_value = True

        # Mock config manager
        mock_config_instance = MagicMock()
        mock_config_manager.return_value = mock_config_instance
        mock_config_instance.config = {"cron": {"enabled": True, "jobs": []}}

        try:
            from click.testing import CliRunner
            from toolcrate.cli.schedule import hourly

            runner = CliRunner()
            result = runner.invoke(hourly, [])

            # Should execute without errors
            self.assertEqual(result.exit_code, 0)

        except ImportError:
            self.skipTest("Schedule module not available")

    def test_cron_manager_functions_exist(self):
        """Test that cron manager functions can be imported."""
        try:
            from toolcrate.scripts.cron_manager import (
                add_download_wishlist_cron,
                add_identify_tracks_cron,
                remove_scheduled_job,
            )

            # Functions should be callable
            self.assertTrue(callable(add_identify_tracks_cron))
            self.assertTrue(callable(add_download_wishlist_cron))
            self.assertTrue(callable(remove_scheduled_job))

        except ImportError as e:
            self.fail(f"Could not import cron manager functions: {e}")


class TestQueueWorkflow(unittest.TestCase):
    """Test complete download queue workflow."""

    def test_queue_processor_can_be_imported(self):
        """Test that queue processor can be imported."""
        import importlib.util

        spec = importlib.util.find_spec("toolcrate.queue.processor")
        self.assertIsNotNone(spec, "QueueProcessor module not found")

        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Should be able to import without errors
            self.assertTrue(hasattr(module, "QueueProcessor"))
        except ImportError as e:
            self.fail(f"Could not import QueueProcessor: {e}")

    @patch("toolcrate.queue.processor.QueueProcessor.read_queue_entries")
    @patch("toolcrate.queue.processor.QueueProcessor.process_queue_entry")
    def test_queue_processor_handles_urls(self, mock_process_entry, mock_read_entries):
        """Test that queue processor handles URLs properly."""
        # Mock reading entries
        mock_read_entries.return_value = [
            "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF",
            "https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
        ]

        # Mock successful processing
        mock_process_entry.return_value = True

        try:
            from toolcrate.config.manager import ConfigManager
            from toolcrate.queue.processor import QueueProcessor

            # Create processor with mocked config
            with patch.object(ConfigManager, "__init__", return_value=None):
                processor = QueueProcessor.__new__(QueueProcessor)
                processor.queue_config = {"enabled": True}
                processor.config_manager = MagicMock()

                # Mock lock acquisition
                with patch.object(processor, "acquire_lock", return_value=MagicMock()):
                    with patch.object(processor, "remove_processed_entries"):
                        with patch.object(processor, "backup_processed_entry"):
                            # Test processing
                            result = processor.process_all_entries()

                            # Should process all entries
                            self.assertEqual(mock_process_entry.call_count, 2)
                            self.assertEqual(result["processed"], 2)
                            self.assertEqual(result["failed"], 0)

        except ImportError:
            self.skipTest("QueueProcessor not available")


if __name__ == "__main__":
    unittest.main()
