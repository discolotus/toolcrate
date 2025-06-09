# Docker Testing Environment

This document describes the Docker-based testing environment for ToolCrate, which provides isolated testing with Docker-in-Docker capabilities.

## Overview

The Docker testing environment allows you to:

- **Run tests in isolation** - Clean environment for reproducible tests
- **Test Docker functionality** - Run the slsk-batchdl container inside the test container
- **Support all test types** - Python, shell, unit, integration, coverage tests
- **Easy CI/CD integration** - Consistent testing across different environments

## Quick Start

### Build and Run All Tests

```bash
# Using Make (recommended)
make test-docker

# Using Docker Compose directly
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit toolcrate-test

# Using the test runner script
./scripts/docker-test-runner.sh
```

### Run Specific Test Types

```bash
# Python tests only
make test-docker-run TEST=python

# Integration tests
make test-docker-run TEST=integration

# Tests with coverage
make test-docker-run TEST=coverage

# Quick tests for development
make test-docker-run TEST=quick
```

### Interactive Development

```bash
# Open shell in testing container
make test-docker-shell

# Inside the container, you can run:
poetry run pytest tests/ -v
poetry run python tests/test_runner_unified.py all
toolcrate --help
```

## Available Commands

### Make Commands

| Command | Description |
|---------|-------------|
| `make test-docker` | Run all tests in Docker container |
| `make test-docker-build` | Build Docker testing image |
| `make test-docker-run TEST=<type>` | Run specific test type |
| `make test-docker-shell` | Open interactive shell |
| `make test-docker-clean` | Clean Docker artifacts |
| `make test-docker-dind` | Run with Docker-in-Docker |

### Test Types

| Type | Description |
|------|-------------|
| `all` | All tests (Python + shell) |
| `python` | Python tests only |
| `shell` | Shell script tests only |
| `unit` | Unit tests only |
| `integration` | Integration tests only |
| `coverage` | Tests with coverage report |
| `docker` | Docker-specific tests |
| `quick` | Quick subset for development |

### Script Usage

```bash
# Basic usage
./scripts/docker-test-runner.sh [OPTIONS] [TEST_TYPE]

# Options
-b, --build     # Force rebuild of Docker image
-c, --clean     # Clean up after tests
-d, --dind      # Use Docker-in-Docker
-v, --verbose   # Verbose output
-h, --help      # Show help

# Examples
./scripts/docker-test-runner.sh python
./scripts/docker-test-runner.sh -b -c coverage
./scripts/docker-test-runner.sh -d integration
```

## Docker-in-Docker (DinD)

The testing environment supports two modes:

### Host Docker Socket (Default)
- Mounts `/var/run/docker.sock` from host
- Faster and uses less resources
- Shares Docker daemon with host

### Docker-in-Docker (DinD)
- Runs separate Docker daemon in container
- More isolated but uses more resources
- Better for CI/CD environments

```bash
# Use DinD mode
make test-docker-dind
./scripts/docker-test-runner.sh -d
```

## Files and Structure

```
├── Dockerfile.test              # Main testing container
├── docker-compose.test.yml      # Testing environment orchestration
├── scripts/
│   ├── test-in-docker.sh       # Test runner inside container
│   └── docker-test-runner.sh   # Host-side test runner
└── .dockerignore               # Optimized build context
```

## Container Features

The testing container includes:

- **Python 3.11** with Poetry for dependency management
- **Docker CE** for running containers inside the test environment
- **All testing tools** - pytest, coverage, shell test runners
- **ToolCrate package** installed in development mode
- **Isolated environment** with proper volume mounts

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHONPATH` | Python module search path | `/workspace/src` |
| `DOCKER_TLS_CERTDIR` | Docker TLS certificates | `/certs` |
| `POETRY_VENV_IN_PROJECT` | Create venv in project | `1` |

## Volumes

| Volume | Purpose |
|--------|---------|
| `test-artifacts` | Coverage reports and test outputs |
| `poetry-cache` | Poetry dependency cache |
| `docker-certs-*` | Docker TLS certificates (DinD) |
| `dind-storage` | Docker storage (DinD) |

## Troubleshooting

### Docker Permission Issues

If you get permission errors:

```bash
# On Linux, ensure your user is in docker group
sudo usermod -aG docker $USER
# Then logout and login again

# Or run with sudo (not recommended)
sudo make test-docker
```

### Container Build Failures

```bash
# Clean and rebuild
make test-docker-clean
make test-docker-build

# Check Docker daemon
docker info
```

### Test Failures

```bash
# Run with verbose output
./scripts/docker-test-runner.sh -v python

# Open shell for debugging
make test-docker-shell

# Check logs
docker-compose -f docker-compose.test.yml logs
```

### Resource Issues

```bash
# Clean up Docker system
docker system prune -f

# Check available resources
docker system df
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Tests
on: [push, pull_request]

jobs:
  docker-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Docker Tests
        run: make test-docker
```

### GitLab CI Example

```yaml
docker-tests:
  image: docker:latest
  services:
    - docker:dind
  script:
    - make test-docker
```

## Performance Tips

1. **Use host Docker socket** for faster tests (default mode)
2. **Cache Poetry dependencies** by mounting poetry cache volume
3. **Use .dockerignore** to reduce build context size
4. **Run specific test types** instead of all tests during development
5. **Clean up regularly** with `make test-docker-clean`

## Security Considerations

- The container runs with `privileged: true` for Docker-in-Docker
- Host Docker socket is mounted (default mode)
- Use DinD mode for better isolation in untrusted environments
- Test containers are ephemeral and cleaned up after use
