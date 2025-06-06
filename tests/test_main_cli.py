"""Tests for the main CLI interface."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from toolcrate.cli.main import info, main


class TestMainCLI:
    """Test cases for the main CLI interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_main_group_exists(self):
        """Test that main CLI group exists and is callable."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "ToolCrate" in result.output
        assert "unified tool suite" in result.output

    def test_main_group_version(self):
        """Test that version option works."""
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        # Version should be displayed

    def test_main_group_docstring(self):
        """Test that main group has proper docstring."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "music management and processing" in result.output

    def test_info_command_exists(self):
        """Test that info command exists."""
        result = self.runner.invoke(main, ["info"])
        assert result.exit_code == 0

    def test_info_command_output(self):
        """Test that info command displays correct information."""
        result = self.runner.invoke(main, ["info"])
        assert result.exit_code == 0
        assert "ToolCrate - Available Tools:" in result.output
        assert "slsk-tool: Soulseek batch download tool" in result.output
        assert "shazam-tool: Music recognition tool" in result.output
        assert "mdl-tool: Music metadata utility" in result.output

    def test_info_command_help(self):
        """Test that info command help works."""
        result = self.runner.invoke(main, ["info", "--help"])
        assert result.exit_code == 0
        assert "Show information about available tools" in result.output

    def test_main_with_no_command(self):
        """Test main CLI with no command shows help."""
        result = self.runner.invoke(main, [])
        assert result.exit_code == 0
        # Should show help or usage information

    def test_main_with_invalid_command(self):
        """Test main CLI with invalid command."""
        result = self.runner.invoke(main, ["invalid-command"])
        assert result.exit_code != 0
        # Should show error for invalid command

    def test_info_command_direct_call(self):
        """Test calling info command directly."""
        with patch("click.echo") as mock_echo:
            info()

            # Verify all expected calls were made
            expected_calls = [
                "ToolCrate - Available Tools:",
                "  - slsk-tool: Soulseek batch download tool",
                "  - shazam-tool: Music recognition tool",
                "  - mdl-tool: Music metadata utility",
            ]

            assert mock_echo.call_count == len(expected_calls)
            for i, expected_call in enumerate(expected_calls):
                assert mock_echo.call_args_list[i][0][0] == expected_call

    def test_main_group_commands_list(self):
        """Test that main group lists available commands."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Commands:" in result.output
        assert "info" in result.output

    def test_main_entry_point(self):
        """Test that main can be called as entry point."""
        # Test that the main function exists and is callable
        assert callable(main)

        # Test with empty args (should show help)
        result = self.runner.invoke(main, [])
        assert result.exit_code == 0
