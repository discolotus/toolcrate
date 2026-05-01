# ToolCrate Makefile

.PHONY: help test test-all test-python test-shell test-unit test-integration test-coverage test-quick clean install dev-install format lint check init-config config config-validate config-generate-sldl config-generate-wishlist-sldl config-generate-docker config-check-mounts config-show wishlist-test wishlist-run wishlist-run-verbose wishlist-logs wishlist-status test-docker test-docker-build test-docker-run test-docker-shell test-docker-clean

help:
	@echo "ToolCrate Commands"
	@echo "=================="
	@echo ""
	@echo "Setup:"
	@echo "  make install        - Install dependencies with uv"
	@echo "  make dev-install    - Install with dev dependencies"
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
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-python    - Run Python tests only"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage  - Run tests with coverage"
	@echo "  make test-quick     - Run quick subset of tests"
	@echo ""
	@echo "Docker Testing:"
	@echo "  make test-docker    - Run all tests in Docker container"
	@echo "  make test-docker-build - Build Docker image"
	@echo "  make test-docker-run - Run specific test type (TEST=python|unit|integration|coverage)"
	@echo "  make test-docker-shell - Open shell in Docker container"
	@echo "  make test-docker-clean - Clean Docker artifacts"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format         - Format code with ruff"
	@echo "  make lint           - Lint code with ruff and mypy"
	@echo "  make check          - Run all quality checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean build/test artifacts"

# Install production dependencies
install:
	uv sync --no-dev

# Install with dev dependencies
dev-install:
	uv sync

# Testing commands
test:
	uv run python tests/test_runner_unified.py all

test-all: test

test-python:
	uv run pytest tests/ -v

test-shell:
	uv run python tests/test_runner_unified.py shell

test-unit:
	uv run pytest tests/ -v -m "not integration"

test-integration:
	uv run pytest tests/test_integration.py -v

test-coverage:
	uv run pytest tests/ --cov=src/toolcrate --cov-report=term-missing --cov-report=html

test-quick:
	uv run pytest tests/test_package.py tests/test_main_cli.py -v

# Code quality
format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

check: format lint
	@echo "All quality checks passed!"

# Clean build and test artifacts
clean:
	rm -rf .pytest_cache/ htmlcov/ .coverage .mypy_cache/ .ruff_cache/ dist/ build/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build
build:
	uv build

# Configuration management
init-config:
	@echo "Running ToolCrate initial configuration setup..."
	./configure_toolcrate.sh

config:
	@echo "Updating tool configurations from YAML..."
	@if [ ! -f "config/toolcrate.yaml" ]; then \
		echo "No configuration found. Run 'make init-config' first."; \
		exit 1; \
	fi
	uv run python -m toolcrate.config.manager check-mounts
	uv run python -m toolcrate.config.manager generate-sldl
	@echo "Tool configurations updated from config/toolcrate.yaml"

config-validate:
	uv run python -m toolcrate.config.manager validate

config-show:
	uv run python -m toolcrate.config.manager show

config-generate-docker:
	uv run python -m toolcrate.config.manager generate-docker

config-check-mounts:
	uv run python -m toolcrate.config.manager check-mounts

config-generate-wishlist-sldl:
	uv run python -m toolcrate.config.manager generate-wishlist-sldl

# Wishlist commands
wishlist-test:
	uv run toolcrate schedule test

wishlist-run:
	uv run python -m toolcrate.wishlist.processor

wishlist-run-verbose:
	uv run python -m toolcrate.wishlist.processor --verbose

wishlist-logs:
	uv run toolcrate wishlist-run logs

wishlist-status:
	uv run toolcrate wishlist-run status

# Docker commands
test-docker-build:
	docker build -f Dockerfile -t toolcrate:test .

test-docker:
	docker-compose up --build --abort-on-container-exit toolcrate

test-docker-run:
	@if [ -z "$(TEST)" ]; then \
		echo "Usage: make test-docker-run TEST=<test_type>"; \
		echo "Available: python, unit, integration, coverage, quick"; \
		exit 1; \
	fi
	docker-compose run --rm toolcrate uv run pytest tests/ -v -m "$(TEST)"

test-docker-shell:
	docker-compose run --rm toolcrate bash

test-docker-clean:
	docker-compose down -v --remove-orphans
	docker rmi toolcrate:test 2>/dev/null || true

.PHONY: frontend frontend-dev frontend-test

frontend:
	cd src/toolcrate/web/frontend && npm ci && npm run build

frontend-dev:
	cd src/toolcrate/web/frontend && npm ci && npm run dev

frontend-test:
	cd src/toolcrate/web/frontend && npm ci && npm run lint && npm run typecheck && npm run test -- --run && npm run build
