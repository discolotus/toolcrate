#!/usr/bin/env python3
"""Wrapper functions for external tools."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click
from loguru import logger


def check_dependency(name, binary_name=None):
    """Check if a dependency is available in the PATH."""
    if binary_name is None:
        binary_name = name

    return shutil.which(binary_name) is not None


def check_docker_image(image_name):
    """Check if a Docker image is available."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        # Docker not installed
        return False


def get_project_root():
    """Get the project root directory."""
    # Start from the current file's directory
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # Navigate up until we find the project root (where setup.py is)
    while current_dir != current_dir.parent:
        if (current_dir / "setup.py").exists():
            return current_dir
        current_dir = current_dir.parent

    # Fallback to package directory
    return Path(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


def run_slsk():
    """Run the Soulseek batch downloader."""
    args = sys.argv[1:]
    root_dir = get_project_root()

    # Check for local binary in src directory first
    local_binary_paths = [
        root_dir / "src" / "bin" / "sldl",  # Pre-built binary path
        root_dir
        / "src"
        / "slsk-batchdl"
        / "bin"
        / "osx-arm64"
        / "sldl",  # Self-built binary path (macOS ARM64)
    ]

    for path in local_binary_paths:
        if path.exists() and os.access(path, os.X_OK):
            logger.info(f"Using local sldl binary from {path}")
            os.execv(str(path), ["sldl"] + args)
            return

    # Check for native binary in PATH
    if check_dependency("sldl"):
        logger.info("Using sldl binary from PATH")
        os.execvp("sldl", ["sldl"] + args)
        return

    # Check for slsk-batchdl binary in PATH
    if check_dependency("slsk-batchdl"):
        logger.info("Using slsk-batchdl binary from PATH")
        os.execvp("slsk-batchdl", ["slsk-batchdl"] + args)
        return

    # Check for Docker image
    if check_docker_image("slsk-batchdl"):
        logger.info("Using Docker image for slsk-batchdl")
        download_dir = os.path.expanduser("~/Music/downloads")
        os.makedirs(download_dir, exist_ok=True)

        cmd = [
            "docker",
            "run",
            "--rm",
            "-it",
            "-v",
            f"{download_dir}:/downloads",
            "slsk-batchdl",
        ] + args

        os.execvp("docker", cmd)
        return

    # Try to build from source as a last resort
    src_dir = root_dir / "src" / "slsk-batchdl"
    if src_dir.exists():
        try:
            logger.info("Attempting to build sldl from source")
            # Check if dotnet is available
            subprocess.run(["which", "dotnet"], check=True, capture_output=True)

            # Create output directory
            bin_dir = root_dir / "src" / "bin"
            os.makedirs(bin_dir, exist_ok=True)

            # Determine platform
            if sys.platform == "darwin":
                if os.uname().machine == "arm64":
                    runtime = "osx-arm64"
                else:
                    runtime = "osx-x64"
            elif sys.platform == "linux":
                runtime = "linux-x64"
            elif sys.platform == "win32":
                runtime = "win-x64"
            else:
                runtime = "linux-x64"  # Default fallback

            logger.info(f"Building for runtime: {runtime}")

            # Build the project
            subprocess.run(
                f"cd {src_dir} && dotnet publish -c Release -r {runtime} --self-contained -o {bin_dir}",
                shell=True,
                check=True,
            )

            # Make binary executable
            binary_path = bin_dir / "sldl"
            if binary_path.exists():
                os.chmod(binary_path, 0o755)
                logger.info(f"Built sldl at {binary_path}")
                os.execv(str(binary_path), ["sldl"] + args)
                return

        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Failed to build sldl from source")

    # Not found
    click.echo("Error: slsk-batchdl not found. Please install it or its Docker image.")
    sys.exit(1)


def run_shazam():
    """Run the Shazam tool."""
    args = sys.argv[1:]
    root_dir = get_project_root()

    # Check for local Python script in src directory first
    shazam_script = root_dir / "src" / "Shazam-Tool" / "shazam.py"

    if shazam_script.exists():
        logger.info(f"Using Shazam-Tool from {shazam_script}")
        # Prepare command to run the Python script
        cmd = [sys.executable, str(shazam_script)] + args

        # Execute the script in a subprocess
        try:
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError:
            logger.warning("Failed to run Shazam-Tool script")

    # Check for shell script
    shazam_shell = root_dir / "src" / "Shazam-Tool" / "run_shazam.sh"
    if shazam_shell.exists() and os.access(shazam_shell, os.X_OK):
        logger.info(f"Using Shazam-Tool shell script from {shazam_shell}")
        try:
            os.chmod(shazam_shell, 0o755)  # Ensure it's executable
            subprocess.run([str(shazam_shell)] + args, check=True)
            return
        except subprocess.CalledProcessError:
            logger.warning("Failed to run Shazam-Tool shell script")

    # Check for native binary in PATH
    if check_dependency("shazam-tool"):
        logger.info("Using shazam-tool binary from PATH")
        os.execvp("shazam-tool", ["shazam-tool"] + args)
        return

    # Check for Docker image
    if check_docker_image("shazam-tool"):
        logger.info("Using Docker image for shazam-tool")
        args = sys.argv[1:]
        music_dir = os.path.expanduser("~/Music")

        cmd = [
            "docker",
            "run",
            "--rm",
            "-it",
            "-v",
            f"{music_dir}:/music",
            "shazam-tool",
        ] + args

        os.execvp("docker", cmd)
        return

    # Not found
    click.echo(
        "Error: shazam-tool not found. Please run setup_tools.sh to install dependencies."
    )
    sys.exit(1)


def run_mdl():
    """Run the music metadata utility."""
    # Check for native binary first
    if check_dependency("mdl-utils"):
        logger.info("Using native mdl-utils binary")
        args = sys.argv[1:]
        os.execvp("mdl-utils", ["mdl-utils"] + args)
        return

    # Check for Python module
    try:
        from mdl_utils import cli

        logger.info("Using mdl-utils Python module")
        cli.main()
        return
    except ImportError:
        pass

    # Check for Docker image
    if check_docker_image("mdl-utils"):
        logger.info("Using Docker image for mdl-utils")
        args = sys.argv[1:]
        music_dir = os.path.expanduser("~/Music")

        cmd = [
            "docker",
            "run",
            "--rm",
            "-it",
            "-v",
            f"{music_dir}:/music",
            "mdl-utils",
        ] + args

        os.execvp("docker", cmd)
        return

    # Not found
    click.echo("Error: mdl-utils not found. Please install it or its Docker image.")
    sys.exit(1)
