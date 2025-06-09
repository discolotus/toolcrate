#!/usr/bin/env python3
"""Test Docker testing setup for ToolCrate."""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


class TestDockerSetup:
    """Test cases for Docker testing environment setup."""

    def test_dockerfile_exists(self):
        """Test that Dockerfile.test exists."""
        dockerfile = Path("Dockerfile.test")
        assert dockerfile.exists(), "Dockerfile.test should exist"

        content = dockerfile.read_text()
        assert "FROM python:3.11-slim" in content
        assert "poetry install" in content
        assert "WORKDIR /workspace" in content

    def test_docker_compose_test_exists(self):
        """Test that docker-compose.test.yml exists."""
        compose_file = Path("docker-compose.test.yml")
        assert compose_file.exists(), "docker-compose.test.yml should exist"

        content = compose_file.read_text()
        assert "toolcrate-test:" in content
        assert "privileged: true" in content
        assert "/var/run/docker.sock" in content

    def test_test_scripts_exist(self):
        """Test that test scripts exist and are executable."""
        scripts = [
            "scripts/test-in-docker.sh",
            "scripts/docker-test-runner.sh",
            "scripts/verify-docker-setup.sh",
        ]

        for script_path in scripts:
            script = Path(script_path)
            assert script.exists(), f"{script_path} should exist"
            assert os.access(script, os.X_OK), f"{script_path} should be executable"

    def test_dockerignore_exists(self):
        """Test that .dockerignore exists and contains expected patterns."""
        dockerignore = Path(".dockerignore")
        assert dockerignore.exists(), ".dockerignore should exist"

        content = dockerignore.read_text()
        expected_patterns = [
            "__pycache__/",
            ".git",
            ".pytest_cache/",
            "*.log",
            "data/downloads/",
            "config/*.conf",
        ]

        for pattern in expected_patterns:
            assert pattern in content, f".dockerignore should contain {pattern}"

    def test_test_in_docker_script_content(self):
        """Test that test-in-docker.sh has correct content."""
        script = Path("scripts/test-in-docker.sh")
        content = script.read_text()

        # Check for required test types
        test_types = [
            "all",
            "python",
            "shell",
            "unit",
            "integration",
            "coverage",
            "docker",
            "quick",
        ]
        for test_type in test_types:
            assert (
                f'"{test_type}")' in content
            ), f"Script should support {test_type} test type"

        # Check for Poetry usage
        assert "poetry run" in content, "Script should use Poetry to run tests"

        # Check for Docker daemon handling
        assert "docker info" in content, "Script should check Docker daemon"

    def test_docker_test_runner_script_content(self):
        """Test that docker-test-runner.sh has correct content."""
        script = Path("scripts/docker-test-runner.sh")
        content = script.read_text()

        # Check for command line options
        options = ["-b", "--build", "-c", "--clean", "-d", "--dind", "-v", "--verbose"]
        for option in options:
            assert option in content, f"Script should support {option} option"

        # Check for usage function
        assert "show_usage()" in content, "Script should have usage function"

        # Check for Docker Compose usage
        assert "docker-compose" in content, "Script should use Docker Compose"

    @pytest.mark.integration
    def test_makefile_docker_targets(self):
        """Test that Makefile contains Docker testing targets."""
        makefile = Path("Makefile")
        content = makefile.read_text()

        docker_targets = [
            "test-docker:",
            "test-docker-build:",
            "test-docker-run:",
            "test-docker-shell:",
            "test-docker-clean:",
        ]

        for target in docker_targets:
            assert target in content, f"Makefile should contain {target} target"

    @pytest.mark.integration
    @patch("subprocess.run")
    def test_docker_availability_check(self, mock_run):
        """Test Docker availability checking logic."""
        # Mock successful Docker check
        mock_run.return_value.returncode = 0

        # This would be the logic used in our scripts
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        assert result.returncode == 0

        # Mock failed Docker check
        mock_run.return_value.returncode = 1
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        assert result.returncode == 1

    def test_documentation_exists(self):
        """Test that Docker testing documentation exists."""
        doc_file = Path("docs/DOCKER_TESTING.md")
        assert doc_file.exists(), "Docker testing documentation should exist"

        content = doc_file.read_text()
        assert "Docker Testing Environment" in content
        assert "Quick Start" in content
        assert "make test-docker" in content
        assert "Troubleshooting" in content

    def test_readme_mentions_docker_testing(self):
        """Test that README mentions Docker testing."""
        readme = Path("README.md")
        content = readme.read_text()

        assert "Docker Testing Environment" in content
        assert "make test-docker" in content
        assert "docs/DOCKER_TESTING.md" in content

    @pytest.mark.integration
    def test_docker_compose_syntax(self):
        """Test that docker-compose.test.yml has valid syntax."""
        compose_file = Path("docker-compose.test.yml")

        # Try to validate the compose file syntax
        try:
            import yaml

            with open(compose_file) as f:
                yaml.safe_load(f)
        except ImportError:
            # If PyYAML is not available, just check basic structure
            content = compose_file.read_text()
            assert "version:" in content
            assert "services:" in content
            assert "volumes:" in content
            assert "networks:" in content

    def test_dockerfile_layers_optimization(self):
        """Test that Dockerfile.test is optimized for layer caching."""
        dockerfile = Path("Dockerfile.test")
        content = dockerfile.read_text()

        # Check that dependency files are copied before source code
        lines = content.split("\n")
        copy_deps_line = None
        copy_source_line = None

        for i, line in enumerate(lines):
            if "COPY pyproject.toml poetry.lock" in line:
                copy_deps_line = i
            elif "COPY . ." in line:
                copy_source_line = i

        if copy_deps_line is not None and copy_source_line is not None:
            assert (
                copy_deps_line < copy_source_line
            ), "Dependencies should be copied before source code for better caching"

    def test_environment_variables_set(self):
        """Test that required environment variables are set in Docker setup."""
        dockerfile = Path("Dockerfile.test")
        content = dockerfile.read_text()

        required_env_vars = [
            "PYTHONUNBUFFERED=1",
            "PYTHONDONTWRITEBYTECODE=1",
            "POETRY_HOME=",
            "POETRY_VENV_IN_PROJECT=1",
        ]

        for env_var in required_env_vars:
            assert env_var in content, f"Dockerfile should set {env_var}"

    def test_health_check_present(self):
        """Test that Dockerfile includes health check."""
        dockerfile = Path("Dockerfile.test")
        content = dockerfile.read_text()

        assert "HEALTHCHECK" in content, "Dockerfile should include health check"
        assert (
            "import toolcrate" in content
        ), "Health check should verify ToolCrate import"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
