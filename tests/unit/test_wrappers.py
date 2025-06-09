"""Unit tests for the wrapper utility functions."""

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from toolcrate.cli.wrappers import (
    check_dependency,
    check_docker_image,
    get_project_root,
)


class TestWrapperUtils(unittest.TestCase):
    """Test case for the wrapper utility functions."""

    @patch("toolcrate.cli.wrappers.shutil.which")
    def test_check_dependency_exists(self, mock_which):
        """Test check_dependency when the dependency exists."""
        mock_which.return_value = "/usr/bin/sample"
        self.assertTrue(check_dependency("sample"))
        mock_which.assert_called_once_with("sample")

    @patch("toolcrate.cli.wrappers.shutil.which")
    def test_check_dependency_not_exists(self, mock_which):
        """Test check_dependency when the dependency does not exist."""
        mock_which.return_value = None
        self.assertFalse(check_dependency("sample"))
        mock_which.assert_called_once_with("sample")

    @patch("toolcrate.cli.wrappers.shutil.which")
    def test_check_dependency_with_binary_name(self, mock_which):
        """Test check_dependency with a specific binary name."""
        mock_which.return_value = "/usr/bin/different-binary"
        self.assertTrue(check_dependency("tool", binary_name="different-binary"))
        mock_which.assert_called_once_with("different-binary")

    @patch("toolcrate.cli.wrappers.subprocess.run")
    def test_check_docker_image_exists(self, mock_run):
        """Test check_docker_image when the image exists."""
        # Configure the mock to return a successful exit code
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        self.assertTrue(check_docker_image("sample-image"))
        mock_run.assert_called_once_with(
            ["docker", "image", "inspect", "sample-image"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("toolcrate.cli.wrappers.subprocess.run")
    def test_check_docker_image_not_exists(self, mock_run):
        """Test check_docker_image when the image does not exist."""
        # Configure the mock to return a failed exit code
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_run.return_value = mock_process

        self.assertFalse(check_docker_image("missing-image"))
        mock_run.assert_called_once_with(
            ["docker", "image", "inspect", "missing-image"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("toolcrate.cli.wrappers.subprocess.run")
    def test_check_docker_image_docker_not_installed(self, mock_run):
        """Test check_docker_image when Docker is not installed."""
        mock_run.side_effect = FileNotFoundError()

        self.assertFalse(check_docker_image("any-image"))
        mock_run.assert_called_once()

    @patch("toolcrate.cli.wrappers.os.path.dirname")
    @patch("toolcrate.cli.wrappers.os.path.abspath")
    @patch("toolcrate.cli.wrappers.Path")
    def test_get_project_root(self, mock_path_class, mock_abspath, mock_dirname):
        """Test get_project_root function."""
        # Setup mocks for the path operations
        mock_dirname.return_value = "/mock/path"
        mock_abspath.return_value = "/mock/path/file.py"

        # Create the mock path objects
        mock_file_dir = MagicMock()
        mock_parent1 = MagicMock()
        mock_parent2 = MagicMock()

        # Setup the path hierarchy
        mock_path_class.return_value = mock_file_dir
        mock_file_dir.parent = mock_parent1
        mock_parent1.parent = mock_parent2
        mock_parent2.parent = mock_parent2  # Root is its own parent

        # Setup the setup.py check
        mock_file_dir.__truediv__.return_value.exists.return_value = False
        mock_parent1.__truediv__.return_value.exists.return_value = (
            True  # Parent1 has setup.py
        )

        # Call the function
        result = get_project_root()

        # The function should return parent1 since it has setup.py
        self.assertEqual(result, mock_parent1)


if __name__ == "__main__":
    unittest.main()
