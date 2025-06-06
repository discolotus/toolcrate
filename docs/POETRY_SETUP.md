# Poetry Setup Guide for ToolCrate

This guide explains how to transition from the current virtualenv + pip setup to Poetry for better dependency management, testing, and development workflow.

## Why Poetry?

✅ **Superior dependency resolution** - No more dependency conflicts  
✅ **Lock files** - Reproducible builds across environments  
✅ **Virtual environment management** - Automatic venv handling  
✅ **Modern build system** - PEP 517/518 compliant  
✅ **Development dependencies** - Clear separation of dev vs prod deps  
✅ **Script management** - Clean console script definitions  
✅ **Testing integration** - Better pytest and coverage integration  

## Installation

### 1. Install Poetry

```bash
# Install Poetry (recommended method)
curl -sSL https://install.python-poetry.org | python3 -

# Or using pip (if you prefer)
pip install poetry

# Add Poetry to PATH (if needed)
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Verify Installation

```bash
poetry --version
```

## Quick Start

### 1. Setup Project with Poetry

```bash
# Install dependencies and create virtual environment
make setup

# Or manually:
poetry install --with dev
```

### 2. Use Poetry Environment

**Modern Poetry (2.0+) approach - run commands directly:**
```bash
# Run commands with Poetry (recommended)
poetry run python --version
poetry run pytest tests/

# Or activate manually if needed
source $(poetry env info --path)/bin/activate
```

**Note:** `poetry shell` was removed in Poetry 2.0+. Use `poetry run` instead!

## Testing with Poetry

### Using the Task Runner

```bash
# Run all tests (Python + shell)
python tasks.py test all

# Run only Python tests
python tasks.py test python

# Run only shell tests  
python tasks.py test shell

# Run with coverage
python tasks.py test coverage

# Quick tests for development
python tasks.py test quick
```

### Using Make Commands

```bash
# Run all tests
make test

# Run specific test types
make test-python
make test-shell
make test-unit
make test-integration
make test-coverage
make test-quick

# Run specific module
make test-module MODULE=wrappers
```

### Using Poetry Directly

```bash
# Run pytest with Poetry
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest tests/ --cov=src/toolcrate --cov-report=html

# Run specific test file
poetry run pytest tests/test_wrappers.py -v
```

## Code Quality

### Formatting

```bash
# Format code
python tasks.py format

# Or with make
make format

# Or directly
poetry run black src/ tests/
poetry run isort src/ tests/
```

### Linting

```bash
# Lint code
python tasks.py lint

# Or with make
make lint

# Or directly
poetry run ruff check src/ tests/
poetry run mypy src/
```

### All Quality Checks

```bash
# Run all checks
python tasks.py check
make check
```

## Dependency Management

### Adding Dependencies

```bash
# Add production dependency
poetry add requests

# Add development dependency
poetry add --group dev pytest-mock

# Add with version constraint
poetry add "click>=8.1.0,<9.0.0"
```

### Updating Dependencies

```bash
# Update all dependencies
poetry update

# Update specific dependency
poetry update click

# Show outdated dependencies
poetry show --outdated
```

### Removing Dependencies

```bash
# Remove dependency
poetry remove requests

# Remove dev dependency
poetry remove --group dev pytest-mock
```

## Building and Publishing

### Build Package

```bash
# Build wheel and source distribution
poetry build

# Or with task runner
python tasks.py build
```

### Publish Package

```bash
# Publish to PyPI (configure credentials first)
poetry publish

# Publish to test PyPI
poetry publish --repository testpypi
```

## Migration from Current Setup

### 1. Remove Old Virtual Environment

```bash
# Deactivate current venv
deactivate

# Remove old .venv directory
rm -rf .venv
```

### 2. Install with Poetry

```bash
# Setup with Poetry
make setup

# Or manually
poetry install --with dev
```

### 3. Update Scripts

The project now includes:
- `tasks.py` - Poetry-based task runner
- Updated `Makefile` - Poetry-integrated commands
- `pyproject.toml` - Complete Poetry configuration

### 4. Verify Setup

```bash
# Test the setup
poetry run python -c "import toolcrate; print('✅ Import successful')"

# Run tests
make test-quick
```

## Configuration Files

### pyproject.toml

The `pyproject.toml` file now includes:
- **Dependencies** - Production and development
- **Testing configuration** - pytest, coverage settings
- **Code quality tools** - black, isort, ruff, mypy
- **Build system** - Poetry build backend
- **Scripts** - Console script definitions

### poetry.lock

This file (auto-generated) ensures:
- **Reproducible builds** - Exact dependency versions
- **Conflict resolution** - Poetry resolves all dependencies
- **Security** - Dependency integrity verification

## Workflow Examples

### Daily Development

```bash
# Start development session
poetry shell

# Run tests while developing
python tasks.py test quick

# Format and lint before committing
python tasks.py check

# Run full test suite
make test
```

### CI/CD Pipeline

```bash
# Install dependencies
poetry install --with dev

# Run all tests
poetry run pytest tests/ --cov=src/toolcrate

# Run shell tests
poetry run python tests/test_runner_unified.py shell

# Build package
poetry build
```

## Benefits Realized

1. **No more pip conflicts** - Poetry resolves dependencies properly
2. **Reproducible environments** - Lock file ensures consistency
3. **Cleaner commands** - `poetry run` prefix ensures correct environment
4. **Better testing** - Integrated coverage and pytest configuration
5. **Modern tooling** - Ruff for fast linting, modern mypy configuration
6. **Easy publishing** - Simple `poetry publish` command

## Troubleshooting

### Poetry Not Found

```bash
# Add to shell profile (.bashrc, .zshrc, etc.)
export PATH="$HOME/.local/bin:$PATH"
```

### Virtual Environment Issues

```bash
# Remove and recreate environment
poetry env remove python
poetry install --with dev
```

### Dependency Conflicts

```bash
# Clear cache and reinstall
poetry cache clear pypi --all
poetry install --with dev
```

## Next Steps

1. **Try the new setup**: `make setup && make test`
2. **Use Poetry commands**: `poetry shell`, `poetry add`, etc.
3. **Integrate with IDE**: Configure your IDE to use Poetry's virtual environment
4. **Update CI/CD**: Modify deployment scripts to use Poetry
5. **Remove old files**: Consider removing `setup.py` once fully migrated
