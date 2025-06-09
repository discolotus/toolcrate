"""Tests for mount path change detection and container rebuilding."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from toolcrate.config.manager import ConfigManager


class TestMountDetection:
    """Test cases for mount path change detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir(exist_ok=True)

        # Create a test config
        self.test_config = {
            "project": {"name": "test-toolcrate"},
            "mounts": {
                "config": {"host_path": "./config", "container_path": "/config"},
                "data": {"host_path": "./data", "container_path": "/data"},
            },
            "environment": {"TZ": "UTC", "PUID": 1000, "PGID": 1000},
        }

        # Write test config
        config_file = self.config_dir / "toolcrate.yaml"
        with open(config_file, "w") as f:
            yaml.dump(self.test_config, f)

        self.config_manager = ConfigManager(config_file)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_generate_docker_compose(self):
        """Test docker-compose.yml generation."""
        self.config_manager.generate_docker_compose()

        docker_compose_path = self.config_dir / "docker-compose.yml"
        assert docker_compose_path.exists()

        with open(docker_compose_path) as f:
            content = f.read()

        # Check that relative paths are used
        assert "- ./config:/config" in content
        assert "- ./data:/data" in content
        assert "device: ./config" in content
        assert "device: ./data" in content

    def test_mount_paths_unchanged(self):
        """Test that no rebuild happens when mount paths are unchanged."""
        # Generate initial docker-compose.yml
        self.config_manager.generate_docker_compose()

        with patch("builtins.print") as mock_print:
            self.config_manager.check_mount_changes()

            # Should print that no rebuild is needed
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Mount paths unchanged" in call for call in print_calls)

    def test_mount_paths_changed(self):
        """Test that rebuild happens when mount paths change."""
        # Generate initial docker-compose.yml with relative paths
        self.config_manager.generate_docker_compose()

        # Change the config to use absolute paths
        self.test_config["mounts"]["config"]["host_path"] = "/absolute/config"
        self.test_config["mounts"]["data"]["host_path"] = "/absolute/data"

        config_file = self.config_dir / "toolcrate.yaml"
        with open(config_file, "w") as f:
            yaml.dump(self.test_config, f)

        # Reload config
        self.config_manager.config = None

        with (
            patch("builtins.print") as mock_print,
            patch("subprocess.run") as mock_subprocess,
        ):

            self.config_manager.check_mount_changes()

            # Should print that mount paths changed
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Mount paths changed" in call for call in print_calls)

            # Should attempt to stop containers
            assert mock_subprocess.called

    def test_no_existing_docker_compose(self):
        """Test behavior when no docker-compose.yml exists."""
        with patch("builtins.print") as mock_print:
            self.config_manager.check_mount_changes()

            # Should generate new docker-compose.yml
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any(
                "No existing docker-compose.yml found" in call for call in print_calls
            )

            # Should create the file
            docker_compose_path = self.config_dir / "docker-compose.yml"
            assert docker_compose_path.exists()

    def test_docker_compose_content_structure(self):
        """Test that generated docker-compose.yml has correct structure."""
        self.config_manager.generate_docker_compose()

        docker_compose_path = self.config_dir / "docker-compose.yml"
        with open(docker_compose_path) as f:
            content = f.read()

        # Check for required sections
        assert "services:" in content
        assert "toolcrate:" in content
        assert "sldl:" in content
        assert "networks:" in content
        assert "volumes:" in content

        # Check for environment variables
        assert "TZ=UTC" in content
        assert "PUID=1000" in content
        assert "PGID=1000" in content

        # Check for container names
        assert "container_name: toolcrate" in content
        assert "container_name: sldl" in content

    def test_absolute_paths_in_docker_compose(self):
        """Test docker-compose generation with absolute paths."""
        # Change to absolute paths
        self.test_config["mounts"]["config"]["host_path"] = "/absolute/config"
        self.test_config["mounts"]["data"]["host_path"] = "/absolute/data"

        config_file = self.config_dir / "toolcrate.yaml"
        with open(config_file, "w") as f:
            yaml.dump(self.test_config, f)

        # Reload config
        self.config_manager.config = None
        self.config_manager.generate_docker_compose()

        docker_compose_path = self.config_dir / "docker-compose.yml"
        with open(docker_compose_path) as f:
            content = f.read()

        # Check that absolute paths are used
        assert "- /absolute/config:/config" in content
        assert "- /absolute/data:/data" in content
        assert "device: /absolute/config" in content
        assert "device: /absolute/data" in content

    @patch("subprocess.run")
    def test_container_stop_error_handling(self, mock_subprocess):
        """Test error handling when stopping containers fails."""
        # Generate initial docker-compose.yml
        self.config_manager.generate_docker_compose()

        # Change mount paths to trigger rebuild
        self.test_config["mounts"]["config"]["host_path"] = "/new/config"
        config_file = self.config_dir / "toolcrate.yaml"
        with open(config_file, "w") as f:
            yaml.dump(self.test_config, f)

        # Reload config
        self.config_manager.config = None

        # Mock subprocess to raise an exception
        mock_subprocess.side_effect = Exception("Docker error")

        with patch("builtins.print") as mock_print:
            # Should not crash, just show warning
            self.config_manager.check_mount_changes()

            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any(
                "Warning: Could not stop containers" in call for call in print_calls
            )
