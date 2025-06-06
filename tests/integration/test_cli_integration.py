"""Integration tests for the toolcrate CLI."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


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
        self.assertTrue((src_dir / "bin").exists(), "src/bin directory missing")
        
        # Check for tool repositories (these might not exist in CI environment)
        print(f"Checking for slsk-batchdl in {src_dir}")
        print(f"Checking for Shazam-Tool in {src_dir}")
        
        # Just print info about these, don't make them hard requirements
        if (src_dir / "slsk-batchdl").exists():
            print("slsk-batchdl repository exists")
        
        if (src_dir / "Shazam-Tool").exists():
            print("Shazam-Tool repository exists")


if __name__ == "__main__":
    unittest.main() 