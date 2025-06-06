"""Test runner and utilities for ToolCrate tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_shell_tests():
    """Run shell script tests."""
    project_root = Path(__file__).parent.parent
    tests_dir = Path(__file__).parent
    shell_tests = []

    # Find shell test scripts in tests directory
    for script in tests_dir.glob("test_*.sh"):
        shell_tests.append(script)

    # Look for shell test scripts in project root (legacy)
    for script in project_root.glob("test_*.sh"):
        if script not in shell_tests:
            shell_tests.append(script)

    # Look for shell test scripts in subdirectories
    for script in project_root.glob("**/test_*.sh"):
        if script not in shell_tests:
            shell_tests.append(script)

    if not shell_tests:
        print("No shell tests found.")
        return 0

    print(f"Running {len(shell_tests)} shell test(s)...")

    overall_exit_code = 0
    for test_script in shell_tests:
        print(f"\n{'='*60}")
        print(f"Running shell test: {test_script.name}")
        print(f"{'='*60}")

        try:
            # Make script executable
            os.chmod(test_script, 0o755)

            # Run the shell test
            result = subprocess.run(
                [str(test_script)],
                cwd=project_root,
                capture_output=False,  # Let output go to console
                text=True,
            )

            if result.returncode == 0:
                print(f"✅ Shell test {test_script.name} PASSED")
            else:
                print(
                    f"❌ Shell test {test_script.name} FAILED (exit code: {result.returncode})"
                )
                overall_exit_code = 1

        except Exception as e:
            print(f"❌ Error running shell test {test_script.name}: {e}")
            overall_exit_code = 1

    return overall_exit_code


def run_python_tests():
    """Run Python tests with appropriate configuration."""
    test_dir = Path(__file__).parent

    # Configure pytest arguments
    pytest_args = [
        str(test_dir),
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "--disable-warnings",  # Disable warnings for cleaner output
        "--continue-on-collection-errors",  # Continue even if some tests fail to collect
    ]

    # Run tests
    exit_code = pytest.main(pytest_args)
    return exit_code


def run_all_tests():
    """Run all tests (both Python and shell)."""
    print("=" * 80)
    print("RUNNING ALL TESTS (PYTHON + SHELL)")
    print("=" * 80)

    # Run Python tests first
    print("\n" + "=" * 60)
    print("RUNNING PYTHON TESTS")
    print("=" * 60)
    python_exit_code = run_python_tests()

    # Run shell tests
    print("\n" + "=" * 60)
    print("RUNNING SHELL TESTS")
    print("=" * 60)
    shell_exit_code = run_shell_tests()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Python tests: {'✅ PASSED' if python_exit_code == 0 else '❌ FAILED'}")
    print(f"Shell tests:  {'✅ PASSED' if shell_exit_code == 0 else '❌ FAILED'}")

    overall_result = python_exit_code or shell_exit_code
    print(f"Overall:      {'✅ PASSED' if overall_result == 0 else '❌ FAILED'}")
    print("=" * 80)

    return overall_result


def run_specific_test_module(module_name):
    """Run tests for a specific module."""
    test_dir = Path(__file__).parent
    test_file = test_dir / f"test_{module_name}.py"

    if not test_file.exists():
        print(f"Test file {test_file} does not exist")
        return 1

    pytest_args = [
        str(test_file),
        "-v",
        "--tb=short",
    ]

    exit_code = pytest.main(pytest_args)
    return exit_code


def run_integration_tests():
    """Run only integration tests."""
    test_dir = Path(__file__).parent

    pytest_args = [
        str(test_dir / "test_integration.py"),
        "-v",
        "--tb=short",
    ]

    exit_code = pytest.main(pytest_args)
    return exit_code


def run_unit_tests():
    """Run only unit tests (excluding integration tests)."""
    test_dir = Path(__file__).parent

    pytest_args = [
        str(test_dir),
        "-v",
        "--tb=short",
        "--ignore=" + str(test_dir / "test_integration.py"),
    ]

    exit_code = pytest.main(pytest_args)
    return exit_code


def check_test_coverage():
    """Check test coverage for Python tests only."""
    try:
        import coverage

        # Start coverage
        cov = coverage.Coverage()
        cov.start()

        # Run Python tests only (coverage doesn't apply to shell tests)
        exit_code = run_python_tests()

        # Stop coverage and report
        cov.stop()
        cov.save()

        print("\nCoverage Report:")
        cov.report()

        return exit_code

    except ImportError:
        print("Coverage package not installed. Install with: pip install coverage")
        return run_python_tests()


def run_quick_tests():
    """Run a quick subset of tests for development."""
    test_dir = Path(__file__).parent

    # Run only fast unit tests, skip integration and shell tests
    pytest_args = [
        str(test_dir / "test_package.py"),
        str(test_dir / "test_main_cli.py"),
        "-v",
        "--tb=short",
        "--disable-warnings",
    ]

    exit_code = pytest.main(pytest_args)
    return exit_code


def print_usage():
    """Print usage information."""
    print("ToolCrate Unified Test Runner")
    print("=" * 40)
    print("Usage: python test_runner.py [command]")
    print()
    print("Commands:")
    print("  all         - Run all tests (Python + shell)")
    print("  python      - Run Python tests only")
    print("  shell       - Run shell tests only")
    print("  unit        - Run unit tests only")
    print("  integration - Run integration tests only")
    print("  coverage    - Run Python tests with coverage")
    print("  quick       - Run quick subset of tests")
    print("  module:<name> - Run specific test module")
    print()
    print("Examples:")
    print("  python test_runner.py all")
    print("  python test_runner.py python")
    print("  python test_runner.py shell")
    print("  python test_runner.py module:wrappers")
    print("  python test_runner.py coverage")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "all":
            exit_code = run_all_tests()
        elif command == "integration":
            exit_code = run_integration_tests()
        elif command == "unit":
            exit_code = run_unit_tests()
        elif command == "coverage":
            exit_code = check_test_coverage()
        elif command.startswith("module:"):
            module_name = command.split(":", 1)[1]
            exit_code = run_specific_test_module(module_name)
        else:
            print(
                "Usage: python test_runner.py [all|unit|integration|coverage|module:<name>]"
            )
            exit_code = 1
    else:
        # Default to running all tests
        exit_code = run_all_tests()

    sys.exit(exit_code)
