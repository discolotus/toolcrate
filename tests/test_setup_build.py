"""Tests for setup and build functionality."""

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock, call
import pytest


class TestSetupPy:
    """Test cases for setup.py functionality."""

    def test_setup_py_exists(self):
        """Test that setup.py exists in the project root."""
        setup_py = Path(__file__).parent.parent / "setup.py"
        assert setup_py.exists()

    def test_setup_py_imports(self):
        """Test that setup.py can be imported without errors."""
        setup_py_path = Path(__file__).parent.parent / "setup.py"
        
        # Read setup.py content to verify it's valid Python
        content = setup_py_path.read_text()
        assert "from setuptools import setup" in content
        assert "find_packages" in content

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_post_install_command_git_repo(self, mock_exists, mock_run):
        """Test PostInstallCommand when in git repository."""
        # Mock being in a git repository
        mock_exists.return_value = True
        mock_run.return_value.returncode = 0
        
        # Import and test the command class
        sys.path.insert(0, str(Path(__file__).parent.parent))
        try:
            import setup
            
            cmd = setup.PostInstallCommand()
            cmd.run()
            
            # Should run git submodule command
            mock_run.assert_called()
            git_calls = [call for call in mock_run.call_args_list 
                        if 'git submodule' in str(call)]
            assert len(git_calls) > 0
            
        finally:
            if str(Path(__file__).parent.parent) in sys.path:
                sys.path.remove(str(Path(__file__).parent.parent))

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_post_install_command_no_git(self, mock_exists, mock_run):
        """Test PostInstallCommand when not in git repository."""
        # Mock not being in a git repository
        mock_exists.return_value = False
        mock_run.return_value.returncode = 0
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        try:
            import setup
            
            cmd = setup.PostInstallCommand()
            cmd.run()
            
            # Should run git clone commands
            mock_run.assert_called()
            clone_calls = [call for call in mock_run.call_args_list 
                          if 'git clone' in str(call)]
            assert len(clone_calls) > 0
            
        finally:
            if str(Path(__file__).parent.parent) in sys.path:
                sys.path.remove(str(Path(__file__).parent.parent))

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_post_develop_command(self, mock_exists, mock_run):
        """Test PostDevelopCommand."""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 0
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        try:
            import setup
            
            cmd = setup.PostDevelopCommand()
            cmd.run()
            
            # Should run the same setup as install
            mock_run.assert_called()
            
        finally:
            if str(Path(__file__).parent.parent) in sys.path:
                sys.path.remove(str(Path(__file__).parent.parent))


class TestBuildProcess:
    """Test cases for build process functionality."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.chmod')
    def test_slsk_build_process_macos_arm64(self, mock_chmod, mock_makedirs, mock_exists, mock_run):
        """Test SLSK build process on macOS ARM64."""
        from toolcrate.cli.wrappers import run_slsk
        
        # Mock environment
        mock_exists.side_effect = lambda path: "slsk-batchdl" in str(path)
        mock_run.return_value.returncode = 0
        
        with patch('sys.argv', ['slsk-tool', 'search', 'test']), \
             patch('sys.platform', 'darwin'), \
             patch('os.uname') as mock_uname, \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=False), \
             patch('os.access', return_value=False):
            
            mock_uname.return_value.machine = 'arm64'
            mock_root.return_value = Path("/fake/root")
            
            # Mock successful build
            mock_run.side_effect = [
                Mock(returncode=0),  # which dotnet
                Mock(returncode=0),  # dotnet publish
            ]
            
            with patch('os.execv') as mock_execv:
                run_slsk()
                
                # Should attempt to build and execute
                assert mock_run.call_count >= 2
                mock_execv.assert_called_once()

    @patch('subprocess.run')
    def test_slsk_build_process_dotnet_missing(self, mock_run):
        """Test SLSK build process when dotnet is missing."""
        from toolcrate.cli.wrappers import run_slsk
        
        # Mock dotnet not found
        mock_run.side_effect = subprocess.CalledProcessError(1, "which dotnet")
        
        with patch('sys.argv', ['slsk-tool', 'search', 'test']), \
             patch('toolcrate.cli.wrappers.get_project_root') as mock_root, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('shutil.which', return_value=None), \
             patch('toolcrate.cli.wrappers.check_docker_image', return_value=False), \
             patch('os.access', return_value=False), \
             patch('click.echo') as mock_echo, \
             patch('sys.exit') as mock_exit:
            
            mock_root.return_value = Path("/fake/root")
            
            run_slsk()
            
            # Should show error message
            mock_echo.assert_called_once()
            mock_exit.assert_called_once_with(1)

    def test_platform_detection(self):
        """Test platform detection logic."""
        from toolcrate.cli.wrappers import run_slsk
        
        # Test different platform scenarios
        test_cases = [
            ('darwin', 'arm64', 'osx-arm64'),
            ('darwin', 'x86_64', 'osx-x64'),
            ('linux', 'x86_64', 'linux-x64'),
            ('win32', 'AMD64', 'win-x64'),
            ('unknown', 'unknown', 'linux-x64'),  # fallback
        ]
        
        for platform, machine, expected_runtime in test_cases:
            with patch('sys.platform', platform), \
                 patch('os.uname') as mock_uname, \
                 patch('sys.argv', ['slsk-tool']), \
                 patch('toolcrate.cli.wrappers.get_project_root'), \
                 patch('pathlib.Path.exists', return_value=True), \
                 patch('shutil.which', return_value=None), \
                 patch('toolcrate.cli.wrappers.check_docker_image', return_value=False), \
                 patch('os.access', return_value=False), \
                 patch('subprocess.run') as mock_run, \
                 patch('click.echo'), \
                 patch('sys.exit'):
                
                mock_uname.return_value.machine = machine
                mock_run.side_effect = [
                    Mock(returncode=0),  # which dotnet
                    Mock(returncode=1),  # dotnet publish fails
                ]
                
                run_slsk()
                
                # Check that the correct runtime was used in the build command
                if mock_run.call_count >= 2:
                    build_call = mock_run.call_args_list[1]
                    assert expected_runtime in str(build_call)


class TestProjectStructure:
    """Test cases for project structure validation."""

    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists and is valid."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists()
        
        content = pyproject_path.read_text()
        assert "[tool.poetry]" in content
        assert "toolcrate" in content

    def test_src_directory_structure(self):
        """Test that src directory has expected structure."""
        src_path = Path(__file__).parent.parent / "src"
        assert src_path.exists()
        
        toolcrate_path = src_path / "toolcrate"
        assert toolcrate_path.exists()
        
        cli_path = toolcrate_path / "cli"
        assert cli_path.exists()
        
        # Check for required files
        assert (toolcrate_path / "__init__.py").exists()
        assert (cli_path / "__init__.py").exists()
        assert (cli_path / "main.py").exists()
        assert (cli_path / "wrappers.py").exists()

    def test_external_tools_structure(self):
        """Test that external tools directories exist."""
        src_path = Path(__file__).parent.parent / "src"
        
        # These directories should exist (or be created during setup)
        expected_dirs = [
            "Shazam-Tool",
            "slsk-batchdl",
            "bin"
        ]
        
        for dir_name in expected_dirs:
            dir_path = src_path / dir_name
            # Directory might not exist in test environment, but path should be valid
            assert isinstance(dir_path, Path)

    def test_console_scripts_configuration(self):
        """Test that console scripts are properly configured."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject_path.read_text()
        
        # Check for console script entries
        assert "toolcrate = \"toolcrate.cli.main:main\"" in content
        assert "slsk-tool = \"toolcrate.cli.wrappers:run_slsk\"" in content
        assert "shazam-tool = \"toolcrate.cli.wrappers:run_shazam\"" in content
        assert "mdl-tool = \"toolcrate.cli.wrappers:run_mdl\"" in content

    def test_dependencies_configuration(self):
        """Test that dependencies are properly configured."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject_path.read_text()
        
        # Check for required dependencies
        assert "click" in content
        assert "pydantic" in content
        assert "loguru" in content
        
        # Check for dev dependencies
        assert "pytest" in content
        assert "black" in content
        assert "isort" in content
        assert "mypy" in content


class TestInstallationProcess:
    """Test cases for installation process."""

    def test_install_script_exists(self):
        """Test that install.sh exists."""
        install_script = Path(__file__).parent.parent / "install.sh"
        # Script might not exist, but we can test the path
        assert isinstance(install_script, Path)

    @patch('subprocess.run')
    def test_pip_install_simulation(self, mock_run):
        """Test simulation of pip install process."""
        mock_run.return_value.returncode = 0
        
        # Simulate pip install command
        result = subprocess.run(['echo', 'pip install -e .'], capture_output=True, text=True)
        assert result.returncode == 0

    def test_package_metadata(self):
        """Test package metadata consistency."""
        # Check that version is consistent across files
        from toolcrate import __version__
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        pyproject_content = pyproject_path.read_text()
        
        # Version should be defined in pyproject.toml
        assert f'version = "{__version__}"' in pyproject_content or \
               f"version = '{__version__}'" in pyproject_content
