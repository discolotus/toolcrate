#!/usr/bin/env python3
"""Script to run all tests for toolcrate."""

import argparse
import os
import sys
import unittest


def main():
    """Run all tests or a specific test suite."""
    parser = argparse.ArgumentParser(description="Run toolcrate tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Ensure that the toolcrate package can be imported
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Initialize the test suite
    loader = unittest.TestLoader()
    all_tests = unittest.TestSuite()

    # Load test modules based on options
    if args.unit or not (args.unit or args.integration):
        unit_tests = loader.discover("tests/unit", pattern="test_*.py")
        all_tests.addTest(unit_tests)
        print(f"Discovered {unit_tests.countTestCases()} unit tests")

    if args.integration or not (args.unit or args.integration):
        integration_tests = loader.discover("tests/integration", pattern="test_*.py")
        all_tests.addTest(integration_tests)
        print(f"Discovered {integration_tests.countTestCases()} integration tests")

    # Run tests with appropriate verbosity
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(all_tests)

    # Return non-zero exit code if any tests failed
    if not result.wasSuccessful():
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
