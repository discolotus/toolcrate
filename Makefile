# ToolCrate Makefile for unified testing with Poetry

.PHONY: help test test-all test-python test-shell test-unit test-integration test-coverage test-quick clean install setup dev-install format lint check init-config config config-validate config-generate-sldl config-show

# Default target
help:
	@echo "ToolCrate Commands (Poetry-based)"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Install Poetry and setup project"
	@echo "  make install        - Install dependencies with Poetry"
	@echo "  make dev-install    - Install with dev dependencies"
	@echo ""
	@echo "Configuration:"
	@echo "  make init-config    - Run interactive configuration setup (first time)"
	@echo "  make config         - Update tool configs from YAML (regenerate)"
	@echo "  make config-validate - Validate existing configuration"
	@echo "  make config-show    - Show current configuration"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests (Python + shell)"
	@echo "  make test-all       - Same as 'make test'"
	@echo "  make test-python    - Run Python tests only"
	@echo "  make test-shell     - Run shell tests only"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage  - Run Python tests with coverage"
	@echo "  make test-quick     - Run quick subset of tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format         - Format code with black and isort"
	@echo "  make lint           - Lint code with ruff and mypy"
	@echo "  make check          - Run all quality checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean test artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make setup          # Initial project setup"
	@echo "  make init-config    # Initial configuration setup"
	@echo "  make config         # Update configs from YAML"
	@echo "  make test           # Run all tests"
	@echo "  make format         # Format code"
	@echo "  make lint           # Lint code"

# Setup Poetry and project
setup:
	@echo "Setting up Poetry and project..."
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "Installing Poetry..."; \
		curl -sSL https://install.python-poetry.org | python3 -; \
	fi
	poetry install --with dev
	@echo "✅ Setup complete!"
	@echo "💡 Use 'poetry run <command>' or 'make <target>' for commands."
	@echo "💡 Or activate manually: source $$(poetry env info --path)/bin/activate"

# Install dependencies
install:
	poetry install

# Install with dev dependencies
dev-install:
	poetry install --with dev

# Testing commands (using Poetry)
test:
	poetry run python tests/test_runner_unified.py all

test-all: test

# Run Python tests only
test-python:
	poetry run pytest tests/ -v

# Run shell tests only
test-shell:
	poetry run python tests/test_runner_unified.py shell

# Run unit tests only
test-unit:
	poetry run pytest tests/ -v -m "not integration"

# Run integration tests only
test-integration:
	poetry run pytest tests/test_integration.py -v

# Run tests with coverage
test-coverage:
	poetry run pytest tests/ --cov=src/toolcrate --cov-report=term-missing --cov-report=html

# Run quick subset of tests
test-quick:
	poetry run pytest tests/test_package.py tests/test_main_cli.py -v

# Code quality commands
format:
	poetry run black src/ tests/
	poetry run isort src/ tests/

lint:
	poetry run ruff check src/ tests/
	poetry run mypy src/

check: format lint
	@echo "✅ All quality checks passed!"

# Clean test artifacts
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build and publish
build:
	poetry build

publish:
	poetry publish

# Legacy support for the original test runner
test-legacy:
	poetry run python tests/test_runner.py all

# Run specific test module (usage: make test-module MODULE=wrappers)
test-module:
	@if [ -z "$(MODULE)" ]; then \
		echo "Usage: make test-module MODULE=<module_name>"; \
		echo "Example: make test-module MODULE=wrappers"; \
		exit 1; \
	fi
	poetry run python tests/test_runner_unified.py module:$(MODULE)

# Poetry shortcuts
shell:
	@echo "Poetry 2.0+ doesn't include 'shell' by default."
	@echo "Use one of these alternatives:"
	@echo ""
	@echo "Option 1 (Recommended): Use 'poetry run' for commands"
	@echo "  poetry run python script.py"
	@echo "  poetry run pytest"
	@echo ""
	@echo "Option 2: Activate environment manually"
	@echo "  source $$(poetry env info --path)/bin/activate"
	@echo ""
	@echo "Option 3: Install shell plugin"
	@echo "  poetry self add poetry-plugin-shell"
	@echo "  poetry shell"

activate:
	@echo "To activate the Poetry environment, run:"
	@echo "source $$(poetry env info --path)/bin/activate"

show:
	poetry show

update:
	poetry update

# Configuration management commands

# Initial configuration setup (interactive)
init-config:
	@echo "Running ToolCrate initial configuration setup..."
	./configure_toolcrate.sh

# Update tool configurations from YAML (regenerate configs)
config:
	@echo "Updating tool configurations from YAML..."
	@if [ ! -f "config/toolcrate.yaml" ]; then \
		echo "❌ No configuration found. Run 'make init-config' first."; \
		exit 1; \
	fi
	poetry run python -m toolcrate.config.manager generate-sldl
	@echo "✅ Tool configurations updated from config/toolcrate.yaml"

config-validate:
	@echo "Validating ToolCrate configuration..."
	poetry run python -m toolcrate.config.manager validate

config-show:
	@echo "Showing current ToolCrate configuration..."
	poetry run python -m toolcrate.config.manager show

# Initial configuration shortcuts with different options
init-config-poetry:
	@echo "Running ToolCrate configuration setup with Poetry..."
	./configure_toolcrate.sh --use-poetry

init-config-venv:
	@echo "Running ToolCrate configuration setup with virtual environment..."
	./configure_toolcrate.sh --no-poetry
