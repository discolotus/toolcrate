"""Integration tests for the toolcrate CLI."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestToolcrateCommand(unittest.TestCase):
    """Integration tests for the toolcrate command."""

    def test_help_option(self):
        """Test that the --help option works."""
        result = subprocess.run(
            ["toolcrate", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage: toolcrate [OPTIONS] COMMAND [ARGS]...", result.stdout)
        self.assertIn("ToolCrate - A unified tool suite", result.stdout)

    def test_version_option(self):
        """Test that the --version option works."""
        result = subprocess.run(
            ["toolcrate", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertRegex(result.stdout, r"version \d+\.\d+\.\d+")

    def test_info_command(self):
        """Test that the info command works."""
        result = subprocess.run(
            ["toolcrate", "info"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ToolCrate - Available Tools:", result.stdout)
        self.assertIn("slsk-tool:", result.stdout)
        self.assertIn("shazam-tool:", result.stdout)


class TestRealWorldCommands(unittest.TestCase):
    """Test real-world command scenarios that users would actually run."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_urls = {
            "spotify_playlist": "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF",  # Top 50 Global
            "youtube_playlist": "https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",  # YouTube Music Trending
            "soundcloud_track": "https://soundcloud.com/artist/track-name",  # Placeholder
            "youtube_video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll
        }

    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_spotify_playlist_command_structure(
        self, mock_get_root, mock_check_dep
    ):
        """Test that sldl command properly structures Spotify playlist commands."""
        mock_check_dep.return_value = (
            False  # No docker, will exit early but we can check structure
        )
        mock_get_root.return_value = Path("/fake/root")

        result = subprocess.run(
            ["toolcrate", "sldl", self.test_urls["spotify_playlist"]],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should recognize the command but fail due to no docker
        self.assertIn("Docker", result.stdout)
        # Command should be recognized (not "No such command")
        self.assertNotIn("No such command", result.stdout)

    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_youtube_playlist_command_structure(
        self, mock_get_root, mock_check_dep
    ):
        """Test that sldl command properly structures YouTube playlist commands."""
        mock_check_dep.return_value = False
        mock_get_root.return_value = Path("/fake/root")

        result = subprocess.run(
            ["toolcrate", "sldl", self.test_urls["youtube_playlist"]],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should recognize the command but fail due to no docker
        self.assertIn("Docker", result.stdout)
        self.assertNotIn("No such command", result.stdout)

    def test_sldl_help_command(self):
        """Test that sldl --help works and shows expected options."""
        result = subprocess.run(
            ["toolcrate", "sldl", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should either show help or docker error, but command should be recognized
        self.assertTrue(
            "sldl" in result.stdout.lower() or "docker" in result.stdout.lower(),
            f"Expected sldl help or docker error, got: {result.stdout}",
        )

    def test_links_file_option_recognition(self):
        """Test that --links-file option is recognized."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# Test URLs file\n")
            f.write(f"{self.test_urls['spotify_playlist']}\n")
            f.write(f"{self.test_urls['youtube_video']}\n")
            temp_file = f.name

        try:
            result = subprocess.run(
                ["toolcrate", "sldl", "--links-file", temp_file],
                capture_output=True,
                text=True,
                check=False,
            )

            # Should recognize the option but may fail due to docker
            self.assertNotIn("No such option", result.stdout)
            self.assertNotIn("Unrecognized option", result.stdout)
        finally:
            os.unlink(temp_file)


class TestSchedulingCommands(unittest.TestCase):
    """Test scheduling and cron management commands."""

    def test_schedule_command_exists(self):
        """Test that schedule command exists and shows help."""
        result = subprocess.run(
            ["toolcrate", "schedule", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("schedule", result.stdout.lower())

    def test_schedule_add_command_structure(self):
        """Test that schedule add command has proper structure."""
        result = subprocess.run(
            ["toolcrate", "schedule", "add", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should show help for add command
        self.assertEqual(result.returncode, 0)
        self.assertIn("add", result.stdout.lower())

    def test_schedule_hourly_convenience_command(self):
        """Test that hourly convenience command exists."""
        result = subprocess.run(
            ["toolcrate", "schedule", "hourly", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should show help for hourly command
        self.assertEqual(result.returncode, 0)
        self.assertIn("hourly", result.stdout.lower())

    def test_schedule_daily_convenience_command(self):
        """Test that daily convenience command exists."""
        result = subprocess.run(
            ["toolcrate", "schedule", "daily", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should show help for daily command
        self.assertEqual(result.returncode, 0)
        self.assertIn("daily", result.stdout.lower())


class TestWishlistCommands(unittest.TestCase):
    """Test wishlist processing commands."""

    def test_wishlist_run_command_exists(self):
        """Test that wishlist-run command exists."""
        result = subprocess.run(
            ["toolcrate", "wishlist-run", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should show help or recognize command
        self.assertNotIn("No such command", result.stdout)

    @patch("toolcrate.wishlist.processor.WishlistProcessor")
    def test_wishlist_processor_can_be_imported(self, mock_processor):  # noqa: ARG002
        """Test that wishlist processor can be imported and instantiated."""
        import importlib.util

        spec = importlib.util.find_spec("toolcrate.wishlist.processor")
        self.assertIsNotNone(spec, "WishlistProcessor module not found")

        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Should be able to import without errors
            self.assertTrue(hasattr(module, "WishlistProcessor"))
        except ImportError as e:
            self.fail(f"Could not import WishlistProcessor: {e}")


class TestQueueCommands(unittest.TestCase):
    """Test download queue management commands."""

    def test_queue_command_exists(self):
        """Test that queue command exists."""
        result = subprocess.run(
            ["toolcrate", "queue", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should show help or recognize command
        self.assertNotIn("No such command", result.stdout)

    def test_queue_add_command_structure(self):
        """Test that queue add command has proper structure."""
        result = subprocess.run(
            ["toolcrate", "queue", "add", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should show help for add command
        self.assertNotIn("No such command", result.stdout)


class TestEnvironmentSetup(unittest.TestCase):
    """Test that the environment is properly set up."""

    def test_src_directory_structure(self):
        """Test that the src directory has the expected structure."""
        # Get the project root directory (assuming tests are in project root)
        project_root = Path(__file__).parent.parent.parent

        # Check that the src directory exists
        src_dir = project_root / "src"
        self.assertTrue(src_dir.exists(), "src directory missing")

        # Check that the required tool directories exist
        self.assertTrue(
            (src_dir / "toolcrate").exists(), "src/toolcrate directory missing"
        )

        # Check for tool repositories (these might not exist in CI environment)
        print(f"Checking for slsk-batchdl in {src_dir}")
        print(f"Checking for Shazam-Tool in {src_dir}")

        # Just print info about these, don't make them hard requirements
        if (src_dir / "slsk-batchdl").exists():
            print("slsk-batchdl repository exists")

        if (src_dir / "Shazam-Tool").exists():
            print("Shazam-Tool repository exists")

    def test_config_directory_structure(self):
        """Test that config directory structure is correct."""
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config"

        # Config directory should exist
        self.assertTrue(config_dir.exists(), "config directory missing")


if __name__ == "__main__":
    unittest.main()
