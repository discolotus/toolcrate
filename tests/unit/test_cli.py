"""Unit tests for the CLI module of toolcrate."""

import unittest

from click.testing import CliRunner

from toolcrate.cli.main import info, main


class TestCLI(unittest.TestCase):
    """Test case for the CLI module."""

    def setUp(self):
        """Set up the test case."""
        self.runner = CliRunner()

    def test_main_command(self):
        """Test the main command."""
        result = self.runner.invoke(main)
        # The main command without arguments doesn't output anything, so it's likely returning
        # an exit code of 2 to indicate that it's expecting a subcommand
        # This is normal behavior for a Click group
        self.assertIn("Usage:", result.output)
        self.assertIn("Commands:", result.output)

    def test_version_option(self):
        """Test the version option."""
        result = self.runner.invoke(main, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("version", result.output.lower())

    def test_info_command(self):
        """Test the info command."""
        result = self.runner.invoke(info)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ToolCrate - Available Tools:", result.output)
        self.assertIn("slsk-tool", result.output)
        self.assertIn("shazam-tool", result.output)
        self.assertIn("mdl-tool", result.output)

    def test_help_option(self):
        """Test the help option."""
        result = self.runner.invoke(main, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ToolCrate - A unified tool suite", result.output)
        self.assertIn("--version", result.output)
        self.assertIn("--help", result.output)
        self.assertIn("info", result.output)


if __name__ == "__main__":
    unittest.main()
