"""Tests for wrapper functions in toolcrate.cli.wrappers."""

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, call
import pytest

from toolcrate.cli.wrappers import (
    check_dependency,
    check_docker_image,
    get_project_root,
    run_slsk,
    run_shazam,
    run_mdl
)


class TestCheckDependency:
    """Test cases for check_dependency function."""

    def test_check_dependency_found(self, mock_shutil):
        """Test check_dependency when binary is found."""
        mock_shutil.return_value = "/usr/bin/test-binary"
        
        result = check_dependency("test-binary")
        
        assert result is True
        mock_shutil.assert_called_once_with("test-binary")

    def test_check_dependency_not_found(self, mock_shutil):
        """Test check_dependency when binary is not found."""
        mock_shutil.return_value = None
        
        result = check_dependency("nonexistent-binary")
        
        assert result is False
        mock_shutil.assert_called_once_with("nonexistent-binary")

    def test_check_dependency_custom_binary_name(self, mock_shutil):
        """Test check_dependency with custom binary name."""
        mock_shutil.return_value = "/usr/bin/custom-name"
        
        result = check_dependency("package", "custom-name")
        
        assert result is True
        mock_shutil.assert_called_once_with("custom-name")

    def test_check_dependency_none_binary_name(self, mock_shutil):
        """Test check_dependency with None binary name."""
        mock_shutil.return_value = "/usr/bin/package"
        
        result = check_dependency("package", None)
        
        assert result is True
        mock_shutil.assert_called_once_with("package")


class TestCheckDockerImage:
    """Test cases for check_docker_image function."""

    def test_check_docker_image_exists(self, mock_subprocess):
        """Test check_docker_image when image exists."""
        mock_subprocess.return_value.returncode = 0
        
        result = check_docker_image("test-image")
        
        assert result is True
        mock_subprocess.assert_called_once_with(
            ["docker", "image", "inspect", "test-image"],
            capture_output=True,
            text=True,
            check=False
        )

    def test_check_docker_image_not_exists(self, mock_subprocess):
        """Test check_docker_image when image doesn't exist."""
        mock_subprocess.return_value.returncode = 1
        
        result = check_docker_image("nonexistent-image")
        
        assert result is False

    def test_check_docker_image_docker_not_installed(self):
        """Test check_docker_image when Docker is not installed."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = check_docker_image("test-image")
            assert result is False


class TestGetProjectRoot:
    """Test cases for get_project_root function."""

    def test_get_project_root_found(self, mock_project_root):
        """Test get_project_root when setup.py is found."""
        with patch('os.path.dirname') as mock_dirname, \
             patch('os.path.abspath') as mock_abspath:
            
            # Mock the path traversal
            mock_abspath.return_value = str(mock_project_root / "src" / "toolcrate" / "cli" / "wrappers.py")
            mock_dirname.side_effect = [
                str(mock_project_root / "src" / "toolcrate" / "cli"),
                str(mock_project_root / "src" / "toolcrate"),
                str(mock_project_root / "src"),
                str(mock_project_root)
            ]
            
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.side_effect = lambda: True  # setup.py exists
                
                result = get_project_root()
                
                assert isinstance(result, Path)

    def test_get_project_root_fallback(self):
        """Test get_project_root fallback when setup.py not found."""
        with patch('os.path.dirname') as mock_dirname, \
             patch('os.path.abspath') as mock_abspath:
            
            mock_abspath.return_value = "/some/path/toolcrate/cli/wrappers.py"
            mock_dirname.side_effect = [
                "/some/path/toolcrate/cli",
                "/some/path/toolcrate", 
                "/some/path",
                "/"
            ]
            
            with patch('pathlib.Path.exists', return_value=False):
                result = get_project_root()
                assert isinstance(result, Path)


class TestRunSlsk:
    """Test cases for run_slsk function."""

    def test_run_slsk_local_binary_found(self, mock_file_system, mock_os_execv, mock_logger):
        """Test run_slsk when local binary is found."""
        # Create mock binary
        binary_path = mock_file_system['bin'] / "sldl"
        binary_path.write_text("#!/bin/bash\necho 'mock sldl'")
        binary_path.chmod(0o755)
        
        with patch('sys.argv', ['slsk-tool', 'search', 'test']), \
             patch('toolcrate.cli.wrappers.get_project_root', return_value=mock_file_system['root']), \
             patch('os.access', return_value=True):
            
            run_slsk()
            
            mock_os_execv.assert_called_once_with(
                str(binary_path),
                ["sldl", "search", "test"]
            )

    def test_run_slsk_path_binary_found(self, mock_shutil, mock_os_execvp, mock_logger):
        """Test run_slsk when binary is found in PATH."""
        mock_shutil.return_value = "/usr/bin/sldl"
        
        with patch('sys.argv', ['slsk-tool', 'search', 'test']), \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=False):
            
            mock_root.return_value = Path("/fake/root")
            
            run_slsk()
            
            mock_os_execvp.assert_called_once_with("sldl", ["sldl", "search", "test"])

    def test_run_slsk_docker_image_found(self, mock_subprocess, mock_os_execvp, mock_logger):
        """Test run_slsk when Docker image is found."""
        with patch('sys.argv', ['slsk-tool', 'search', 'test']), \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=True), \
             patch('os.makedirs'):
            
            mock_root.return_value = Path("/fake/root")
            
            run_slsk()
            
            expected_cmd = [
                "docker", "run", "--rm", "-it",
                "-v", f"{os.path.expanduser('~/Music/downloads')}:/downloads",
                "slsk-batchdl", "search", "test"
            ]
            mock_os_execvp.assert_called_once_with("docker", expected_cmd)

    def test_run_slsk_not_found(self, mock_click_echo, mock_sys_exit):
        """Test run_slsk when no binary or image is found."""
        with patch('sys.argv', ['slsk-tool', 'search', 'test']), \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=False):
            
            mock_root.return_value = Path("/fake/root")
            
            run_slsk()
            
            mock_click_echo.assert_called_once_with(
                "Error: slsk-batchdl not found. Please install it or its Docker image."
            )
            mock_sys_exit.assert_called_once_with(1)


class TestRunShazam:
    """Test cases for run_shazam function."""

    def test_run_shazam_python_script_found(self, mock_file_system, mock_subprocess, mock_logger):
        """Test run_shazam when Python script is found."""
        # Create mock script
        script_path = mock_file_system['shazam'] / "shazam.py"
        script_path.write_text("# Mock shazam script")

        with patch('sys.argv', ['shazam-tool', 'scan']), \
             patch('toolcrate.cli.wrappers.get_project_root', return_value=mock_file_system['root']):

            run_shazam()

            expected_cmd = [sys.executable, str(script_path), "scan"]
            mock_subprocess.assert_called_once_with(expected_cmd, check=True)

    def test_run_shazam_shell_script_found(self, mock_file_system, mock_subprocess, mock_logger):
        """Test run_shazam when shell script is found."""
        # Create mock shell script
        script_path = mock_file_system['shazam'] / "run_shazam.sh"
        script_path.write_text("#!/bin/bash\necho 'mock shazam'")
        script_path.chmod(0o755)

        with patch('sys.argv', ['shazam-tool', 'scan']), \
             patch('toolcrate.cli.wrappers.get_project_root', return_value=mock_file_system['root']), \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('os.access', return_value=True):

            # Python script doesn't exist, shell script does
            mock_exists.side_effect = lambda: script_path.name == "run_shazam.sh"

            # Mock subprocess.run to raise error for Python script
            mock_subprocess.side_effect = [
                subprocess.CalledProcessError(1, "cmd"),  # Python script fails
                None  # Shell script succeeds
            ]

            run_shazam()

            # Should try shell script after Python script fails
            assert mock_subprocess.call_count == 2

    def test_run_shazam_path_binary_found(self, mock_shutil, mock_os_execvp, mock_logger):
        """Test run_shazam when binary is found in PATH."""
        mock_shutil.return_value = "/usr/bin/shazam-tool"

        with patch('sys.argv', ['shazam-tool', 'scan']), \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=False):

            mock_root.return_value = Path("/fake/root")

            run_shazam()

            mock_os_execvp.assert_called_once_with("shazam-tool", ["shazam-tool", "scan"])

    def test_run_shazam_docker_image_found(self, mock_subprocess, mock_os_execvp, mock_logger):
        """Test run_shazam when Docker image is found."""
        with patch('sys.argv', ['shazam-tool', 'scan']), \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=True):

            mock_root.return_value = Path("/fake/root")

            run_shazam()

            expected_cmd = [
                "docker", "run", "--rm", "-it",
                "-v", f"{os.path.expanduser('~/Music')}:/music",
                "shazam-tool", "scan"
            ]
            mock_os_execvp.assert_called_once_with("docker", expected_cmd)

    def test_run_shazam_not_found(self, mock_click_echo, mock_sys_exit):
        """Test run_shazam when no script, binary, or image is found."""
        with patch('sys.argv', ['shazam-tool', 'scan']), \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=False):

            mock_root.return_value = Path("/fake/root")

            run_shazam()

            mock_click_echo.assert_called_once_with(
                "Error: shazam-tool not found. Please run setup_tools.sh to install dependencies."
            )
            mock_sys_exit.assert_called_once_with(1)


class TestRunMdl:
    """Test cases for run_mdl function."""

    def test_run_mdl_native_binary_found(self, mock_shutil, mock_os_execvp, mock_logger):
        """Test run_mdl when native binary is found."""
        mock_shutil.return_value = "/usr/bin/mdl-utils"

        with patch('sys.argv', ['mdl-tool', 'get-metadata', 'file.mp3']):
            run_mdl()

            mock_os_execvp.assert_called_once_with(
                "mdl-utils",
                ["mdl-utils", "get-metadata", "file.mp3"]
            )

    def test_run_mdl_python_module_found(self, mock_logger):
        """Test run_mdl when Python module is found."""
        mock_cli = Mock()

        with patch('sys.argv', ['mdl-tool', 'get-metadata', 'file.mp3']), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.mdl_utils.cli', mock_cli):

            run_mdl()

            mock_cli.main.assert_called_once()

    def test_run_mdl_docker_image_found(self, mock_subprocess, mock_os_execvp, mock_logger):
        """Test run_mdl when Docker image is found."""
        with patch('sys.argv', ['mdl-tool', 'get-metadata', 'file.mp3']), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.mdl_utils', side_effect=ImportError), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=True):

            run_mdl()

            expected_cmd = [
                "docker", "run", "--rm", "-it",
                "-v", f"{os.path.expanduser('~/Music')}:/music",
                "mdl-utils", "get-metadata", "file.mp3"
            ]
            mock_os_execvp.assert_called_once_with("docker", expected_cmd)

    def test_run_mdl_not_found(self, mock_click_echo, mock_sys_exit):
        """Test run_mdl when no binary, module, or image is found."""
        with patch('sys.argv', ['mdl-tool', 'get-metadata', 'file.mp3']), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.mdl_utils', side_effect=ImportError), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=False):

            run_mdl()

            mock_click_echo.assert_called_once_with(
                "Error: mdl-utils not found. Please install it or its Docker image."
            )
            mock_sys_exit.assert_called_once_with(1)
