"""Tests for the main CLI interface."""

from unittest.mock import patch

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
        assert "sldl: Run commands in slsk-batchdl docker container" in result.output

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
            # Use the CliRunner to avoid sys.argv interference
            result = self.runner.invoke(info, [])

            # Verify the command executed successfully
            assert result.exit_code == 0

            # Verify all expected calls were made (updated to match actual output)
            expected_calls = [
                "ToolCrate - Available Tools:",
                "  - slsk-tool: Soulseek batch download tool",
                "  - shazam-tool: Music recognition tool",
                "  - mdl-tool: Music metadata utility",
                "  - sldl: Run commands in slsk-batchdl docker container",
                "  - schedule: Manage scheduled downloads and cron jobs",
                "  - wishlist-run: View logs and status from scheduled wishlist runs",
                "  - queue: Manage download queue for individual links",
            ]

            # Check that we have the expected number of calls (19 total including detailed help)
            assert mock_echo.call_count == 19

            # Verify the main command descriptions are present
            actual_calls = [call.args[0] for call in mock_echo.call_args_list]
            for expected_call in expected_calls:
                assert expected_call in actual_calls

    def test_main_group_commands_list(self):
        """Test that main group lists available commands."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Commands:" in result.output
        assert "info" in result.output
        assert "sldl" in result.output

    def test_sldl_command_exists(self):
        """Test that sldl command exists."""
        result = self.runner.invoke(main, ["sldl", "--help"])
        # The command should exist, but may fail due to docker dependencies
        # We just check that it's recognized as a valid command
        assert "sldl" in result.output or "docker" in result.output.lower()

    def test_sldl_command_help(self):
        """Test that sldl command shows help information."""
        result = self.runner.invoke(main, ["sldl", "--help"])
        # Should show help or error about docker
        assert result.exit_code in [0, 1]  # May exit with 1 if docker not available

    def test_main_entry_point(self):
        """Test that main can be called as entry point."""
        # Test that the main function exists and is callable
        assert callable(main)

        # Test with empty args (should show help)
        result = self.runner.invoke(main, [])
        assert result.exit_code == 0
