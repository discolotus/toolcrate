# ToolCrate Makefile for unified testing with Poetry

.PHONY: help test test-all test-python test-shell test-unit test-integration test-coverage test-quick clean install setup dev-install install-global install-pipx install-docker format lint check init-config config config-validate config-generate-sldl config-generate-wishlist-sldl config-generate-docker config-check-mounts config-show wishlist-test wishlist-run wishlist-run-verbose wishlist-logs wishlist-status test-docker test-docker-build test-docker-run test-docker-shell test-docker-clean test-docker-pull test-docker-registry test-docker-smart cron-add-wishlist

# Default target
help:
	@echo "ToolCrate Commands (Poetry-based)"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Install Poetry and setup project"
	@echo "  make install        - Install dependencies with Poetry"
	@echo "  make dev-install    - Install with dev dependencies"
	@echo "  make install-global - Install globally (makes 'toolcrate' command available anywhere)"
	@echo "  make install-pipx   - Install with pipx (recommended for CLI tools)"
	@echo "  make install-docker - Install in Docker/container environment"
	@echo ""
	@echo "Configuration:"
	@echo "  make init-config    - Run interactive configuration setup (first time)"
	@echo "  make config         - Update tool configs from YAML (regenerate + check mounts)"
	@echo "  make config-validate - Validate existing configuration"
	@echo "  make config-show    - Show current configuration"
	@echo "  make config-generate-docker - Generate docker-compose.yml from YAML"
	@echo "  make config-check-mounts - Check mount changes and rebuild containers"
	@echo ""
	@echo "Wishlist & Scheduling:"
	@echo "  make wishlist-test  - Test wishlist processing without scheduling"
	@echo "  make wishlist-run   - Run wishlist processing once"
	@echo "  make wishlist-run-verbose - Run wishlist processing with detailed output"
	@echo "  make wishlist-logs  - Show recent wishlist run logs"
	@echo "  make wishlist-status - Show wishlist run status and summary"
	@echo "  make config-generate-wishlist-sldl - Generate wishlist-specific sldl.conf"
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
	@echo "Docker Testing:"
	@echo "  make test-docker    - Run all tests in Docker container"
	@echo "  make test-docker-build - Build Docker testing image"
	@echo "  make test-docker-run - Run specific test type in Docker (TEST=all|python|shell|unit|integration|coverage|docker|quick)"
	@echo "  make test-docker-shell - Open shell in Docker testing container"
	@echo "  make test-docker-pull - Pull pre-built image from registry"
	@echo "  make test-docker-registry - Use registry image for testing (faster)"
	@echo "  make test-docker-smart - Smart testing (auto-chooses best image)"
	@echo "  make test-docker-clean - Clean Docker testing artifacts"
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
	@echo "  make wishlist-test  # Test wishlist processing"
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

# Install globally (makes 'toolcrate' command available system-wide)
install-global:
	@echo "Installing ToolCrate globally..."
	pip install --user -e .
	./install_global.sh
	@echo "✅ ToolCrate installed globally!"
	@echo "💡 The 'toolcrate' command should now be available from anywhere."
	@echo "💡 If not found, ensure ~/.local/bin is in your PATH."

# Install globally with pipx (recommended for CLI tools)
install-pipx:
	@echo "Installing ToolCrate with pipx..."
	@if ! command -v pipx >/dev/null 2>&1; then \
		echo "❌ pipx not found. Install with: pip install --user pipx"; \
		echo "   Then run: pipx ensurepath"; \
		exit 1; \
	fi
	pipx install -e .
	@echo "✅ ToolCrate installed with pipx!"
	@echo "💡 The 'toolcrate' command is now available from anywhere."

# Install in Docker/container environment (handles system packages)
install-docker:
	@echo "Installing ToolCrate in Docker/container environment..."
	pip install --break-system-packages -e .
	@echo "✅ ToolCrate installed in container!"
	@echo "💡 The 'toolcrate' command is now available globally in the container."

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
	poetry run python -m toolcrate.config.manager check-mounts
	poetry run python -m toolcrate.config.manager generate-sldl
	@echo "✅ Tool configurations updated from config/toolcrate.yaml"

config-validate:
	@echo "Validating ToolCrate configuration..."
	poetry run python -m toolcrate.config.manager validate

config-show:
	@echo "Showing current ToolCrate configuration..."
	poetry run python -m toolcrate.config.manager show

config-generate-docker:
	@echo "Generating Docker Compose configuration from YAML..."
	poetry run python -m toolcrate.config.manager generate-docker

config-check-mounts:
	@echo "Checking for mount path changes and rebuilding containers if needed..."
	poetry run python -m toolcrate.config.manager check-mounts

config-generate-wishlist-sldl:
	@echo "Generating wishlist-specific sldl.conf from YAML..."
	poetry run python -m toolcrate.config.manager generate-wishlist-sldl

# Wishlist commands
wishlist-init:
	@echo "Creating blank wishlist.txt file..."
	@if [ ! -f "config/wishlist.txt" ]; then \
		mkdir -p config; \
		echo "# ToolCrate Wishlist File" > config/wishlist.txt; \
		echo "# Add playlist URLs or search terms, one per line" >> config/wishlist.txt; \
		echo "# Examples:" >> config/wishlist.txt; \
		echo "# https://open.spotify.com/playlist/your-playlist-id" >> config/wishlist.txt; \
		echo "# https://youtube.com/playlist?list=your-playlist-id" >> config/wishlist.txt; \
		echo '# "Artist Name - Song Title"' >> config/wishlist.txt; \
		echo '# artist:"Artist Name" album:"Album Name"' >> config/wishlist.txt; \
		echo "" >> config/wishlist.txt; \
		echo "✅ Created blank wishlist.txt file at config/wishlist.txt"; \
	else \
		echo "⚠️  wishlist.txt already exists at config/wishlist.txt"; \
	fi

wishlist-test:
	@echo "Testing wishlist processing..."
	poetry run toolcrate schedule test

wishlist-run:
	@echo "Running wishlist processing..."
	@if ! docker ps | grep -q "sldl"; then \
		echo "Docker container 'sldl' is not running. Rebuilding and starting containers..."; \
		docker-compose -f config/docker-compose.yml up -d --build; \
	else \
		echo "Docker container 'sldl' is running."; \
	fi
	poetry run python -m toolcrate.wishlist.processor

wishlist-run-verbose:
	@echo "Running wishlist processing with verbose output..."
	poetry run python -m toolcrate.wishlist.processor --verbose

wishlist-logs:
	@echo "Showing recent wishlist run logs..."
	poetry run toolcrate wishlist-run logs

wishlist-status:
	@echo "Showing wishlist run status and summary..."
	poetry run toolcrate wishlist-run status

# Initial configuration shortcuts with different options
init-config-poetry:
	@echo "Running ToolCrate configuration setup with Poetry..."
	./configure_toolcrate.sh --use-poetry

init-config-venv:
	@echo "Running ToolCrate configuration setup with virtual environment..."
	./configure_toolcrate.sh --no-poetry

# Docker Testing Commands

# Build Docker testing image
test-docker-build:
	@echo "Building Docker testing image..."
	docker build -f Dockerfile.test -t toolcrate:test .

# Build optimized production image
build-docker-optimized:
	@echo "Building optimized Docker production image..."
	docker build -f Dockerfile.optimized -t toolcrate:optimized .

# Build development environment
build-docker-dev:
	@echo "Building Docker development environment..."
	docker-compose -f docker-compose.dev.yml build

# Start development environment
dev-up:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Development environment started!"
	@echo "💡 Access the container: make dev-shell"
	@echo "💡 View logs: make dev-logs"

# Stop development environment
dev-down:
	@echo "Stopping development environment..."
	docker-compose -f docker-compose.dev.yml down

# Access development container shell
dev-shell:
	@echo "Accessing development container shell..."
	docker-compose -f docker-compose.dev.yml exec toolcrate-dev bash

# View development logs
dev-logs:
	@echo "Viewing development logs..."
	docker-compose -f docker-compose.dev.yml logs -f

# Run health check on running container
docker-health-check:
	@echo "Running health check on Docker container..."
	docker run --rm toolcrate:test /workspace/scripts/docker-health-check.sh

# Run all tests in Docker container
test-docker:
	@echo "Running all tests in Docker container..."
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit toolcrate-test

# Run specific test type in Docker (usage: make test-docker-run TEST=python)
test-docker-run:
	@if [ -z "$(TEST)" ]; then \
		echo "Usage: make test-docker-run TEST=<test_type>"; \
		echo "Available test types: all, python, shell, unit, integration, coverage, docker, quick"; \
		exit 1; \
	fi
	@echo "Running $(TEST) tests in Docker container..."
	docker-compose -f docker-compose.test.yml run --rm toolcrate-test /workspace/scripts/test-in-docker.sh $(TEST)

# Open interactive shell in Docker testing container
test-docker-shell:
	@echo "Opening shell in Docker testing container..."
	docker-compose -f docker-compose.test.yml run --rm toolcrate-test bash

# Clean Docker testing artifacts
test-docker-clean:
	@echo "Cleaning Docker testing artifacts..."
	docker-compose -f docker-compose.test.yml down -v --remove-orphans
	docker rmi toolcrate:test 2>/dev/null || true
	docker rmi ghcr.io/discolotus/toolcrate/toolcrate-test:latest 2>/dev/null || true
	docker volume prune -f

# Pull pre-built Docker test image from registry
test-docker-pull:
	@echo "Pulling Docker test image from registry..."
	docker pull ghcr.io/discolotus/toolcrate/toolcrate-test:latest || \
	docker pull ghcr.io/discolotus/toolcrate/toolcrate-test:main || \
	echo "No pre-built image available, use 'make test-docker-build' to build locally"

# Use registry image for testing (faster than building)
test-docker-registry:
	@echo "Running tests with registry image..."
	@if docker image inspect ghcr.io/discolotus/toolcrate/toolcrate-test:latest >/dev/null 2>&1; then \
		echo "Using registry image..."; \
		sed -i.bak 's|image: toolcrate:test|image: ghcr.io/discolotus/toolcrate/toolcrate-test:latest|g' docker-compose.test.yml; \
		sed -i.bak 's|build:|# build:|g' docker-compose.test.yml; \
		docker-compose -f docker-compose.test.yml up --abort-on-container-exit toolcrate-test; \
		mv docker-compose.test.yml.bak docker-compose.test.yml; \
	else \
		echo "Registry image not found, falling back to local build..."; \
		make test-docker; \
	fi

# Smart Docker testing (automatically chooses best image)
test-docker-smart:
	@echo "Running smart Docker tests..."
	./scripts/docker-test-helper.sh $(TEST)

# Run tests with Docker-in-Docker (more isolated)
test-docker-dind:
	@echo "Running tests with Docker-in-Docker..."
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Examples for Docker testing
test-docker-examples:
	@echo "Docker Testing Examples:"
	@echo "========================"
	@echo ""
	@echo "# Build and run all tests:"
	@echo "make test-docker"
	@echo ""
	@echo "# Run only Python tests:"
	@echo "make test-docker-run TEST=python"
	@echo ""
	@echo "# Run integration tests:"
	@echo "make test-docker-run TEST=integration"
	@echo ""
	@echo "# Run tests with coverage:"
	@echo "make test-docker-run TEST=coverage"
	@echo ""
	@echo "# Open shell for debugging:"
	@echo "make test-docker-shell"
	@echo ""
	@echo "# Clean up:"
	@echo "make test-docker-clean"

# New target 'cron-add-wishlist'
cron-add-wishlist:
	poetry run python -c "from toolcrate.scripts.cron_manager import add_download_wishlist_cron; add_download_wishlist_cron()"


