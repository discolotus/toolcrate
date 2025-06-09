"""Tests for the sldl docker command functionality."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from toolcrate.cli.main import main
from toolcrate.cli.wrappers import run_sldl_docker_command


class TestSldlDockerCommand:
    """Test cases for the sldl docker command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_command_no_docker(self, mock_get_root, mock_check_dep):
        """Test sldl command when docker is not available."""
        mock_check_dep.return_value = False
        mock_get_root.return_value = Path("/fake/root")

        result = self.runner.invoke(main, ["sldl", "--version"])
        assert result.exit_code == 1
        assert "Docker is not installed" in result.output

    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_command_no_compose_file(self, mock_get_root, mock_check_dep):
        """Test sldl command when docker-compose.yml is missing."""
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")

        result = self.runner.invoke(main, ["sldl", "--version"])
        assert result.exit_code == 1
        assert "Docker Compose file not found" in result.output

    @patch("toolcrate.cli.wrappers.os.execvp")
    @patch("toolcrate.cli.wrappers.subprocess.run")
    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_command_container_running(self, mock_get_root, mock_check_dep, mock_subprocess, mock_execvp):
        """Test sldl command when container is already running."""
        # Setup mocks
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")

        # Mock compose file exists and config manager
        with patch("pathlib.Path.exists", return_value=True), \
             patch("toolcrate.config.manager.ConfigManager.generate_sldl_conf") as mock_generate_conf:
            # Mock container is running
            mock_result = MagicMock()
            mock_result.stdout = "sldl"
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result

            # Test the function directly to avoid execvp
            run_sldl_docker_command({}, ["--help"])

            # Verify docker exec was called
            mock_execvp.assert_called_once()
            args = mock_execvp.call_args[0]
            assert args[0] == "docker"
            assert "docker" in args[1]
            assert "exec" in args[1]
            assert "sldl" in args[1]
            assert "-c" in args[1]
            assert "/config/sldl.conf" in args[1]
            assert "--help" in args[1]

    @patch("toolcrate.cli.wrappers.os.execvp")
    @patch("toolcrate.cli.wrappers.subprocess.run")
    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_command_no_args_interactive_shell(self, mock_get_root, mock_check_dep, mock_subprocess, mock_execvp):
        """Test sldl command with no args enters interactive shell."""
        # Setup mocks
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")

        # Mock compose file exists and config manager
        with patch("pathlib.Path.exists", return_value=True), \
             patch("toolcrate.config.manager.ConfigManager.generate_sldl_conf") as mock_generate_conf:
            # Mock container is running
            mock_result = MagicMock()
            mock_result.stdout = "sldl"
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result

            # Test the function directly with no args
            run_sldl_docker_command({}, [])

            # Verify docker exec was called with bash shell
            mock_execvp.assert_called_once()
            args = mock_execvp.call_args[0]
            assert args[0] == "docker"
            assert "docker" in args[1]
            assert "exec" in args[1]
            assert "sldl" in args[1]
            assert "/bin/bash" in args[1]

    @patch("toolcrate.cli.wrappers.subprocess.run")
    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_command_start_container(self, mock_get_root, mock_check_dep, mock_subprocess):
        """Test sldl command when container needs to be started."""
        # Setup mocks
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")
        
        # Mock compose file exists and config manager
        with patch("pathlib.Path.exists", return_value=True), \
             patch("toolcrate.config.manager.ConfigManager.generate_sldl_conf") as mock_generate_conf:
            # Mock container not running, then successful start
            mock_results = [
                MagicMock(stdout="", returncode=0),  # Container not running
                MagicMock(returncode=0),  # Successful start
                MagicMock(stdout="sldl", returncode=0),  # Container now running
            ]
            mock_subprocess.side_effect = mock_results

            with patch("toolcrate.cli.wrappers.os.execvp") as mock_execvp:
                run_sldl_docker_command({}, ["--help"])
                
                # Verify container start was attempted
                assert mock_subprocess.call_count >= 2
                # Verify docker exec was called
                mock_execvp.assert_called_once()

    def test_sldl_command_integration(self):
        """Test sldl command integration with main CLI."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "sldl" in result.output

    @patch("toolcrate.cli.wrappers.check_dependency")
    def test_sldl_command_no_args_interactive(self, mock_check_dep):
        """Test that sldl command with no args attempts interactive shell."""
        mock_check_dep.return_value = False  # Will exit early due to no docker

        result = self.runner.invoke(main, ["sldl"])
        # Should exit with error due to no docker, but command should be recognized
        assert result.exit_code == 1

    def test_sldl_command_docstring(self):
        """Test that sldl command has proper docstring."""
        result = self.runner.invoke(main, ["sldl", "--help"])
        # Should show help or error, but command should be recognized
        assert "sldl" in result.output.lower() or "docker" in result.output.lower()

    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_command_with_args(self, mock_get_root, mock_check_dep):
        """Test sldl command with arguments."""
        mock_check_dep.return_value = False
        mock_get_root.return_value = Path("/fake/root")
        
        result = self.runner.invoke(main, ["sldl", "-a", "artist", "-t", "track"])
        assert result.exit_code == 1
        assert "Docker is not installed" in result.output

    def test_run_sldl_docker_command_function_exists(self):
        """Test that the run_sldl_docker_command function exists and is callable."""
        assert callable(run_sldl_docker_command)

    @patch("toolcrate.cli.wrappers.check_dependency")
    def test_run_sldl_docker_command_params_handling(self, mock_check_dep):
        """Test that run_sldl_docker_command handles parameters correctly."""
        mock_check_dep.return_value = False

        # Should handle empty params and args gracefully
        with pytest.raises(SystemExit):
            run_sldl_docker_command({}, [])

        with pytest.raises(SystemExit):
            run_sldl_docker_command({}, ["--help"])

    @patch("toolcrate.cli.wrappers.os.execvp")
    @patch("toolcrate.cli.wrappers.subprocess.run")
    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    @patch("click.echo")
    def test_sldl_command_multiple_containers_warning(self, mock_echo, mock_get_root, mock_check_dep, mock_subprocess, mock_execvp):
        """Test warning when multiple containers with 'sldl' in name are found."""
        # Setup mocks
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")

        # Mock compose file exists and config manager
        with patch("pathlib.Path.exists", return_value=True), \
             patch("toolcrate.config.manager.ConfigManager.generate_sldl_conf") as mock_generate_conf:
            # Mock multiple containers running
            mock_result = MagicMock()
            mock_result.stdout = "sldl\nslsk-batchdl-sldl-1\nanother-sldl-container"
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result

            # Test the function directly
            run_sldl_docker_command({}, ["--version"])

            # Verify warning was displayed
            warning_calls = [call for call in mock_echo.call_args_list if "Warning" in str(call)]
            assert len(warning_calls) > 0

            # Verify docker exec was called with the first container
            mock_execvp.assert_called_once()
            args = mock_execvp.call_args[0]
            assert args[0] == "docker"
            assert "sldl" in args[1]  # Should use the first container name
            assert "-c" in args[1]
            assert "/config/sldl.conf" in args[1]

    @patch("toolcrate.cli.wrappers.os.execvp")
    @patch("toolcrate.cli.wrappers.subprocess.run")
    @patch("toolcrate.cli.wrappers.check_dependency")
    @patch("toolcrate.cli.wrappers.get_project_root")
    def test_sldl_command_always_includes_config(self, mock_get_root, mock_check_dep, mock_subprocess, mock_execvp):
        """Test that config file argument is always included in commands."""
        # Setup mocks
        mock_check_dep.return_value = True
        mock_get_root.return_value = Path("/fake/root")

        # Mock compose file exists and config manager
        with patch("pathlib.Path.exists", return_value=True), \
             patch("toolcrate.config.manager.ConfigManager.generate_sldl_conf") as mock_generate_conf:
            # Mock container is running
            mock_result = MagicMock()
            mock_result.stdout = "sldl"
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result

            # Test with playlist URL
            run_sldl_docker_command({}, ["https://example.com/playlist"])

            # Verify config argument is included
            mock_execvp.assert_called_once()
            args = mock_execvp.call_args[0]
            cmd_args = args[1]

            # Check that -c and /config/sldl.conf are present and in the right order
            config_index = cmd_args.index("-c")
            assert cmd_args[config_index + 1] == "/config/sldl.conf"
            assert "https://example.com/playlist" in cmd_args

            # Verify the config args come before user args
            playlist_index = cmd_args.index("https://example.com/playlist")
            assert config_index < playlist_index
