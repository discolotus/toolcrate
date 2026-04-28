# Docker Testing Environment

ToolCrate includes a comprehensive Docker-based testing environment that provides isolated, reproducible testing with Docker-in-Docker support.

## 🐳 Available Images

### Registry Images (Recommended)
Pre-built images are automatically built and pushed to GitHub Container Registry:

- `ghcr.io/discolotus/toolcrate/toolcrate-test:latest` - Latest stable build
- `ghcr.io/discolotus/toolcrate/toolcrate-test:main` - Main branch build
- `ghcr.io/discolotus/toolcrate/toolcrate-test:augment-feature-dev` - Development branch build

### Local Build
You can also build the image locally using `Dockerfile.test`.

## 🚀 Quick Start

### Using Pre-built Registry Image (Fastest)
```bash
# Pull the latest pre-built image
make test-docker-pull

# Run tests using registry image
make test-docker-registry
```

### Building Locally
```bash
# Build the Docker test image
make test-docker-build

# Run all tests
make test-docker

# Open interactive shell
make test-docker-shell
```

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `make test-docker` | Run all tests in Docker container |
| `make test-docker-build` | Build Docker testing image locally |
| `make test-docker-pull` | Pull pre-built image from registry |
| `make test-docker-registry` | Use registry image for testing (faster) |
| `make test-docker-run TEST=<type>` | Run specific test type |
| `make test-docker-shell` | Open interactive shell in container |
| `make test-docker-clean` | Clean Docker testing artifacts |

### Test Types for `make test-docker-run`
- `all` - All tests (Python + shell)
- `python` - Python tests only
- `shell` - Shell script tests only
- `unit` - Unit tests only
- `integration` - Integration tests only
- `coverage` - Tests with coverage report
- `docker` - Docker-specific tests
- `quick` - Quick subset of tests

## 🛠️ Container Features

The Docker test environment includes:

- **Python 3.12.3** with Poetry for dependency management
- **Docker-in-Docker** support for testing Docker functionality
- **Cron service** for testing scheduled tasks
- **ToolCrate CLI** pre-installed and globally available
- **All project dependencies** installed via Poetry
- **Test utilities** (pytest, coverage, etc.)

## 🔧 Container Environment

### Pre-installed Tools
- Python 3.12.3 (with `python` symlink)
- Poetry 2.1.3+
- Docker CE with Docker Compose
- Cron service
- Git, curl, wget, make
- Text editors (vim, nano)

### Environment Variables
- `PYTHONPATH=/workspace/src`
- `POETRY_VENV_IN_PROJECT=1`
- `DOCKER_TLS_CERTDIR=/certs`

### Mounted Volumes
- Project directory: `/workspace`
- Test artifacts: `/workspace/htmlcov`
- Poetry cache: `/root/.cache/pypoetry`

## 🎯 Usage Examples

### Run Specific Tests
```bash
# Run only Python tests
make test-docker-run TEST=python

# Run integration tests
make test-docker-run TEST=integration

# Run with coverage
make test-docker-run TEST=coverage
```

### Interactive Development
```bash
# Open shell in container
make test-docker-shell

# Inside container:
toolcrate --help
crontab -l
poetry run pytest tests/ -v
```

### Using Registry Image
```bash
# Pull latest image
docker pull ghcr.io/discolotus/toolcrate/toolcrate-test:latest

# Run tests directly
docker run --rm --privileged \
  -v $(pwd):/workspace \
  ghcr.io/discolotus/toolcrate/toolcrate-test:latest \
  /workspace/scripts/test-in-docker.sh all
```

## 🔄 CI/CD Integration

### GitHub Actions
The repository includes GitHub Actions that:

1. **Build and Push** (`docker-build.yml`):
   - Builds Docker image on changes to `Dockerfile.test`
   - Pushes to GitHub Container Registry
   - Supports multi-platform builds (amd64, arm64)
   - Tests the built image

2. **Test with Docker** (`test-docker.yml`):
   - Runs tests using pre-built registry images
   - Matrix testing across different test types
   - Uploads test artifacts

### Triggering Builds
Images are automatically built when:
- `Dockerfile.test` is modified
- `pyproject.toml` or `poetry.lock` changes
- Workflow files are updated
- Manual workflow dispatch

## 🧹 Cleanup

```bash
# Clean all Docker testing artifacts
make test-docker-clean

# Remove specific images
docker rmi toolcrate:test
docker rmi ghcr.io/discolotus/toolcrate/toolcrate-test:latest
```

## 🐛 Troubleshooting

### Common Issues

1. **Docker not accessible in container**
   - This is expected in some environments
   - Tests will show warning but continue

2. **Permission issues**
   - Container runs as root for Docker-in-Docker support
   - Files created in container may need permission fixes

3. **Image not found**
   - Use `make test-docker-pull` to get latest registry image
   - Fall back to `make test-docker-build` for local build

### Debug Commands
```bash
# Check container status
docker ps -a

# View container logs
docker logs <container-id>

# Inspect image
docker image inspect toolcrate:test
```

## 📚 Related Documentation

- [Testing Guide](testing.md)
- [Development Setup](../README.md#development)
- [CI/CD Workflows](../.github/workflows/)
