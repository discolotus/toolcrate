"""Test runner and utilities for ToolCrate tests."""

import sys
import pytest
from pathlib import Path


def run_all_tests():
    """Run all tests with appropriate configuration."""
    test_dir = Path(__file__).parent
    
    # Configure pytest arguments
    pytest_args = [
        str(test_dir),
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "-x",  # Stop on first failure
        "--disable-warnings",  # Disable warnings for cleaner output
    ]
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    return exit_code


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
    """Check test coverage for the package."""
    try:
        import coverage
        
        # Start coverage
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests
        exit_code = run_all_tests()
        
        # Stop coverage and report
        cov.stop()
        cov.save()
        
        print("\nCoverage Report:")
        cov.report()
        
        return exit_code
        
    except ImportError:
        print("Coverage package not installed. Install with: pip install coverage")
        return run_all_tests()


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
            print("Usage: python test_runner.py [all|unit|integration|coverage|module:<name>]")
            exit_code = 1
    else:
        # Default to running all tests
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
