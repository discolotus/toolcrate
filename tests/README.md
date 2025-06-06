# ToolCrate Test Suite

This directory contains comprehensive unit tests for the ToolCrate package, covering all features and functionality.

## Test Structure

### Test Files

- **`conftest.py`** - Shared fixtures and test configuration
- **`test_package.py`** - Package metadata and structure tests
- **`test_main_cli.py`** - Main CLI interface tests
- **`test_wrappers.py`** - Wrapper functions tests
- **`test_shazam_tool.py`** - Shazam tool functionality tests
- **`test_integration.py`** - Integration and end-to-end tests
- **`test_setup_build.py`** - Setup and build process tests
- **`test_runner.py`** - Test runner utilities

### Test Categories

#### Unit Tests
- **Package Tests** (`test_package.py`)
  - Package version verification
  - Module import validation
  - Package structure verification
  - Docstring validation

- **CLI Tests** (`test_main_cli.py`)
  - Main CLI group functionality
  - Version option testing
  - Info command testing
  - Help system validation
  - Command argument handling

- **Wrapper Tests** (`test_wrappers.py`)
  - Dependency checking (`check_dependency`)
  - Docker image validation (`check_docker_image`)
  - Project root discovery (`get_project_root`)
  - SLSK tool wrapper (`run_slsk`)
  - Shazam tool wrapper (`run_shazam`)
  - MDL tool wrapper (`run_mdl`)

- **Shazam Tool Tests** (`test_shazam_tool.py`)
  - Audio segmentation functionality
  - Music recognition with Shazam API
  - File processing workflows
  - Download functionality
  - Command-line interface
  - Error handling and retries

#### Integration Tests
- **Console Scripts** (`test_integration.py`)
  - Entry point validation
  - End-to-end workflows
  - Cross-component integration
  - External tool integration

#### Build/Setup Tests
- **Setup Process** (`test_setup_build.py`)
  - setup.py functionality
  - Build process validation
  - Platform detection
  - Project structure verification
  - Installation process simulation

## Features Covered

### Core Package Features
✅ **Package Metadata**
- Version information (`__version__`)
- Package structure validation
- Module imports
- Docstring verification

✅ **Main CLI Interface**
- Click-based CLI group
- Version option (`--version`)
- Info command (`info`)
- Help system
- Command routing

✅ **Wrapper Functions**
- Binary dependency checking
- Docker image validation
- Project root discovery
- Cross-platform path handling

### Tool Wrappers
✅ **SLSK Tool Wrapper** (`run_slsk`)
- Local binary detection
- PATH binary fallback
- Docker image fallback
- Source building (dotnet)
- Platform-specific builds
- Error handling

✅ **Shazam Tool Wrapper** (`run_shazam`)
- Python script execution
- Shell script fallback
- PATH binary fallback
- Docker image fallback
- Error handling

✅ **MDL Tool Wrapper** (`run_mdl`)
- Native binary detection
- Python module fallback
- Docker image fallback
- Error handling

### Shazam Tool Features
✅ **Audio Processing**
- Audio file segmentation
- Segment duration control
- Parallel processing
- File format handling

✅ **Music Recognition**
- Shazam API integration
- Retry logic with backoff
- Error handling
- Result formatting

✅ **Download Functionality**
- YouTube/SoundCloud support
- yt-dlp integration
- File management
- Directory organization

✅ **Command Interface**
- Scan command
- Download command
- Recognize command
- Debug mode
- Argument parsing

### Build and Setup
✅ **Setup Process**
- Git submodule handling
- Direct cloning fallback
- Post-install commands
- Development setup

✅ **Build System**
- .NET Core building
- Platform detection
- Runtime targeting
- Binary management

✅ **Project Structure**
- Directory validation
- File existence checks
- Configuration validation
- Dependency management

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Optional: Install coverage
pip install coverage
```

### Running All Tests
```bash
# Using pytest directly
pytest tests/ -v

# Using the test runner
python tests/test_runner.py all
```

### Running Specific Test Categories
```bash
# Unit tests only
python tests/test_runner.py unit

# Integration tests only
python tests/test_runner.py integration

# Specific module
python tests/test_runner.py module:main_cli
python tests/test_runner.py module:wrappers
python tests/test_runner.py module:shazam_tool
```

### Running with Coverage
```bash
python tests/test_runner.py coverage
```

### Running Individual Test Files
```bash
pytest tests/test_main_cli.py -v
pytest tests/test_wrappers.py -v
pytest tests/test_shazam_tool.py -v
```

## Test Configuration

### Fixtures
The `conftest.py` file provides shared fixtures:
- `temp_dir` - Temporary directory for file operations
- `mock_project_root` - Mock project structure
- `mock_subprocess` - Subprocess mocking
- `mock_file_system` - File system mocking
- `mock_shazam_dependencies` - Shazam tool dependencies
- Various other mocking fixtures

### Mocking Strategy
Tests use extensive mocking to:
- Avoid external dependencies
- Prevent actual file system operations
- Mock subprocess calls
- Simulate different environments
- Control test conditions

### Async Testing
Shazam tool tests use `pytest-asyncio` for testing async functionality:
- Async music recognition
- Retry mechanisms
- Concurrent processing

## Coverage Goals

The test suite aims for comprehensive coverage of:
- ✅ All public functions and methods
- ✅ All CLI commands and options
- ✅ All wrapper functions
- ✅ Error handling paths
- ✅ Platform-specific code
- ✅ Integration points
- ✅ External tool interactions

## Notes

### External Dependencies
Some tests mock external dependencies:
- Shazam API calls
- YouTube/SoundCloud downloads
- Docker operations
- File system operations
- Subprocess calls

### Platform Testing
Tests include platform-specific scenarios:
- macOS ARM64/x64
- Linux x64
- Windows x64
- Platform detection logic

### Error Scenarios
Tests cover various error conditions:
- Missing dependencies
- Network failures
- File system errors
- Invalid inputs
- Build failures

This comprehensive test suite ensures that all ToolCrate features are properly tested and validated.
