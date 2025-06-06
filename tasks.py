#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poetry-based task runner for ToolCrate.

This script provides a unified interface for running common development tasks
using Poetry for dependency management and virtual environment handling.

Usage:
    python tasks.py <command> [args]
    
Commands:
    test [type]     - Run tests (all, python, shell, unit, integration, coverage, quick)
    format          - Format code with black and isort
    lint            - Lint code with ruff and mypy
    check           - Run all quality checks
    clean           - Clean build artifacts
    build           - Build the package
    install         - Install dependencies
    shell           - Open Poetry shell
    
Examples:
    python tasks.py test all
    python tasks.py test python
    python tasks.py format
    python tasks.py lint
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, **kwargs):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, **kwargs)


def poetry_run(cmd, **kwargs):
    """Run a command with Poetry."""
    return run_command(["poetry", "run"] + cmd, **kwargs)


def test_command(test_type="all"):
    """Run tests with the specified type."""
    if test_type == "python":
        return poetry_run(["pytest", "tests/", "-v"])
    elif test_type == "shell":
        return poetry_run(["python", "tests/test_runner_unified.py", "shell"])
    elif test_type == "unit":
        return poetry_run(["pytest", "tests/", "-v", "-m", "not integration"])
    elif test_type == "integration":
        return poetry_run(["pytest", "tests/test_integration.py", "-v"])
    elif test_type == "coverage":
        return poetry_run([
            "pytest", "tests/", 
            "--cov=src/toolcrate", 
            "--cov-report=term-missing", 
            "--cov-report=html"
        ])
    elif test_type == "quick":
        return poetry_run([
            "pytest", 
            "tests/test_package.py", 
            "tests/test_main_cli.py", 
            "-v"
        ])
    elif test_type == "all":
        return poetry_run(["python", "tests/test_runner_unified.py", "all"])
    else:
        print(f"❌ Unknown test type: {test_type}")
        print("Available types: all, python, shell, unit, integration, coverage, quick")
        return subprocess.CompletedProcess([], 1)


def format_command():
    """Format code with black and isort."""
    print("Formatting code...")
    result1 = poetry_run(["black", "src/", "tests/"])
    result2 = poetry_run(["isort", "src/", "tests/"])
    return subprocess.CompletedProcess([], max(result1.returncode, result2.returncode))


def lint_command():
    """Lint code with ruff and mypy."""
    print("Linting code...")
    result1 = poetry_run(["ruff", "check", "src/", "tests/"])
    result2 = poetry_run(["mypy", "src/"])
    return subprocess.CompletedProcess([], max(result1.returncode, result2.returncode))


def check_command():
    """Run all quality checks."""
    print("Running all quality checks...")
    format_result = format_command()
    lint_result = lint_command()

    if format_result.returncode == 0 and lint_result.returncode == 0:
        print("All quality checks passed!")
        return subprocess.CompletedProcess([], 0)
    else:
        print("Some quality checks failed!")
        return subprocess.CompletedProcess([], 1)


def clean_command():
    """Clean build artifacts."""
    print("Cleaning build artifacts...")
    artifacts = [
        ".pytest_cache",
        "htmlcov",
        ".coverage",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "*.egg-info",
    ]
    
    for pattern in artifacts:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
                print(f"  Removed directory: {path}")
            elif path.is_file():
                path.unlink()
                print(f"  Removed file: {path}")
    
    # Remove __pycache__ directories
    for pycache in Path(".").rglob("__pycache__"):
        import shutil
        shutil.rmtree(pycache)
        print(f"  Removed: {pycache}")
    
    print("Cleanup complete!")
    return subprocess.CompletedProcess([], 0)


def build_command():
    """Build the package."""
    print("Building package...")
    return run_command(["poetry", "build"])


def install_command():
    """Install dependencies."""
    print("Installing dependencies...")
    return run_command(["poetry", "install", "--with", "dev"])


def shell_command():
    """Open Poetry shell."""
    print("Opening Poetry shell...")
    return run_command(["poetry", "shell"])


def print_help():
    """Print help information."""
    print(__doc__)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_help()
        return 1
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == "test":
        test_type = args[0] if args else "all"
        result = test_command(test_type)
    elif command == "format":
        result = format_command()
    elif command == "lint":
        result = lint_command()
    elif command == "check":
        result = check_command()
    elif command == "clean":
        result = clean_command()
    elif command == "build":
        result = build_command()
    elif command == "install":
        result = install_command()
    elif command == "shell":
        result = shell_command()
    elif command in ["help", "-h", "--help"]:
        print_help()
        return 0
    else:
        print(f"Unknown command: {command}")
        print_help()
        return 1
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
