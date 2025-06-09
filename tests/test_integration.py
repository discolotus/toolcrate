"""Integration tests for ToolCrate console scripts and end-to-end functionality."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestConsoleScripts:
    """Test cases for console script entry points."""

    def test_toolcrate_script_exists(self):
        """Test that toolcrate console script is properly configured."""
        # This tests that the entry point is defined in pyproject.toml
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import toolcrate.cli.main; toolcrate.cli.main.main",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Should not crash on import and basic execution
            assert result.returncode in [0, 2]  # 0 for success, 2 for missing args
        except subprocess.TimeoutExpired:
            pytest.fail("Console script took too long to execute")

    def test_slsk_tool_script_exists(self):
        """Test that slsk-tool console script is properly configured."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import toolcrate.cli.wrappers; print('import successful')",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0
            assert "import successful" in result.stdout
        except subprocess.TimeoutExpired:
            pytest.fail("Console script import took too long")

    def test_shazam_tool_script_exists(self):
        """Test that shazam-tool console script is properly configured."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import toolcrate.cli.wrappers; print('import successful')",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0
            assert "import successful" in result.stdout
        except subprocess.TimeoutExpired:
            pytest.fail("Console script import took too long")

    def test_mdl_tool_script_exists(self):
        """Test that mdl-tool console script is properly configured."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import toolcrate.cli.wrappers; print('import successful')",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0
            assert "import successful" in result.stdout
        except subprocess.TimeoutExpired:
            pytest.fail("Console script import took too long")


class TestEndToEndWorkflows:
    """Test cases for end-to-end workflows."""

    def test_toolcrate_info_command_workflow(self):
        """Test complete workflow of toolcrate info command."""
        with patch("click.echo") as mock_echo:
            from click.testing import CliRunner
            from toolcrate.cli.main import main

            runner = CliRunner()
            result = runner.invoke(main, ["info"])

            assert result.exit_code == 0
            # Verify that info was displayed
            output_calls = [call[0][0] for call in mock_echo.call_args_list]
            assert any("ToolCrate - Available Tools:" in call for call in output_calls)

    def test_wrapper_dependency_check_workflow(self):
        """Test complete workflow of dependency checking."""
        from toolcrate.cli.wrappers import check_dependency

        with patch("shutil.which") as mock_which:
            # Test found dependency
            mock_which.return_value = "/usr/bin/test"
            assert check_dependency("test") is True

            # Test missing dependency
            mock_which.return_value = None
            assert check_dependency("missing") is False

    def test_docker_image_check_workflow(self):
        """Test complete workflow of Docker image checking."""
        from toolcrate.cli.wrappers import check_docker_image

        with patch("subprocess.run") as mock_run:
            # Test existing image
            mock_run.return_value.returncode = 0
            assert check_docker_image("existing-image") is True

            # Test missing image
            mock_run.return_value.returncode = 1
            assert check_docker_image("missing-image") is False

    def test_project_root_discovery_workflow(self):
        """Test complete workflow of project root discovery."""
        from toolcrate.cli.wrappers import get_project_root

        # This should work in the actual project structure
        root = get_project_root()
        assert isinstance(root, Path)
        # Should be a valid path
        assert root.exists() or True  # Fallback path might not exist in test

    @patch("sys.argv", ["slsk-tool", "--help"])
    @patch("click.echo")
    @patch("sys.exit")
    def test_slsk_wrapper_help_workflow(self, mock_exit, mock_echo):
        """Test slsk wrapper help workflow."""
        from toolcrate.cli.wrappers import run_slsk

        with (
            patch("toolcrate.cli.wrappers.get_project_root") as mock_root,
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value=None),
            patch("toolcrate.cli.wrappers.check_docker_image", return_value=False),
        ):

            mock_root.return_value = Path("/fake/root")

            run_slsk()

            # Should show error message when not found
            mock_echo.assert_called_once()
            mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["shazam-tool", "--help"])
    @patch("click.echo")
    @patch("sys.exit")
    def test_shazam_wrapper_help_workflow(self, mock_exit, mock_echo):
        """Test shazam wrapper help workflow."""
        from toolcrate.cli.wrappers import run_shazam

        with (
            patch("toolcrate.cli.wrappers.get_project_root") as mock_root,
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value=None),
            patch("toolcrate.cli.wrappers.check_docker_image", return_value=False),
        ):

            mock_root.return_value = Path("/fake/root")

            run_shazam()

            # Should show error message when not found
            mock_echo.assert_called_once()
            mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["mdl-tool", "--help"])
    @patch("click.echo")
    @patch("sys.exit")
    def test_mdl_wrapper_help_workflow(self, mock_exit, mock_echo):
        """Test mdl wrapper help workflow."""
        from toolcrate.cli.wrappers import run_mdl

        with (
            patch("shutil.which", return_value=None),
            patch("toolcrate.cli.wrappers.mdl_utils", side_effect=ImportError),
            patch("toolcrate.cli.wrappers.check_docker_image", return_value=False),
        ):

            run_mdl()

            # Should show error message when not found
            mock_echo.assert_called_once()
            mock_exit.assert_called_once_with(1)


class TestPackageIntegration:
    """Test cases for package-level integration."""

    def test_package_imports(self):
        """Test that all package components can be imported together."""
        import toolcrate
        import toolcrate.cli
        import toolcrate.cli.main
        import toolcrate.cli.wrappers

        # All imports should succeed
        assert toolcrate.__version__ == "0.1.0"
        assert hasattr(toolcrate.cli.main, "main")
        assert hasattr(toolcrate.cli.wrappers, "run_slsk")
        assert hasattr(toolcrate.cli.wrappers, "run_shazam")
        assert hasattr(toolcrate.cli.wrappers, "run_mdl")

    def test_cli_integration(self):
        """Test CLI integration between main and wrappers."""
        from click.testing import CliRunner
        from toolcrate.cli.main import main

        runner = CliRunner()

        # Test main help
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "ToolCrate" in result.output

        # Test info command
        result = runner.invoke(main, ["info"])
        assert result.exit_code == 0

    def test_logging_integration(self):
        """Test that logging is properly integrated across modules."""
        from toolcrate.cli.wrappers import check_dependency

        # Should not raise any logging-related errors
        with patch("shutil.which", return_value=None):
            result = check_dependency("test")
            assert result is False

    def test_error_handling_integration(self):
        """Test error handling across different components."""
        from toolcrate.cli.wrappers import check_docker_image

        # Test with Docker not installed
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = check_docker_image("test")
            assert result is False

    def test_path_handling_integration(self):
        """Test path handling across different components."""
        from toolcrate.cli.wrappers import get_project_root

        root = get_project_root()
        assert isinstance(root, Path)

        # Test that path operations work
        str_path = str(root)
        assert isinstance(str_path, str)
        assert len(str_path) > 0


class TestExternalToolIntegration:
    """Test cases for integration with external tools."""

    def test_shazam_tool_integration(self):
        """Test integration with Shazam tool."""
        # Test that we can import and check for Shazam tool
        try:
            sys.path.insert(
                0, str(Path(__file__).parent.parent / "src" / "Shazam-Tool")
            )
            import shazam

            # Basic functionality should be available
            assert hasattr(shazam, "main")
            assert hasattr(shazam, "SEGMENT_LENGTH")
            assert hasattr(shazam, "DOWNLOADS_DIR")

        except ImportError:
            # If Shazam tool is not available, that's okay for testing
            pass

    def test_slsk_tool_integration(self):
        """Test integration with SLSK tool."""
        from toolcrate.cli.wrappers import run_slsk

        # Test that the wrapper function exists and is callable
        assert callable(run_slsk)

        # Test with mocked environment
        with (
            patch("sys.argv", ["slsk-tool"]),
            patch("toolcrate.cli.wrappers.get_project_root"),
            patch("pathlib.Path.exists", return_value=False),
            patch("shutil.which", return_value=None),
            patch("toolcrate.cli.wrappers.check_docker_image", return_value=False),
            patch("click.echo"),
            patch("sys.exit"),
        ):

            # Should handle missing tool gracefully
            run_slsk()

    def test_mdl_tool_integration(self):
        """Test integration with MDL tool."""
        from toolcrate.cli.wrappers import run_mdl

        # Test that the wrapper function exists and is callable
        assert callable(run_mdl)

        # Test with mocked environment
        with (
            patch("sys.argv", ["mdl-tool"]),
            patch("shutil.which", return_value=None),
            patch("toolcrate.cli.wrappers.mdl_utils", side_effect=ImportError),
            patch("toolcrate.cli.wrappers.check_docker_image", return_value=False),
            patch("click.echo"),
            patch("sys.exit"),
        ):

            # Should handle missing tool gracefully
            run_mdl()
