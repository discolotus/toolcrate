# GitHub Actions Workflows and Branch Protection

This document describes the comprehensive GitHub Actions workflows and branch protection setup for the ToolCrate project.

## Overview

The ToolCrate project uses a robust CI/CD pipeline with multiple workflows to ensure code quality, security, and reliability before merging changes into the `develop` branch.

## Branch Strategy

- **`main`**: Production-ready code
- **`develop`**: Integration branch for new features (protected)
- **Feature branches**: Individual feature development
- **PR workflow**: All changes to `develop` must go through Pull Requests

## Workflows

### 1. Continuous Integration (`ci.yml`)

**Triggers**: Push to `main`/`develop`, PRs to `main`/`develop`

**Jobs**:
- **Code Quality Checks**: Black formatting, isort, ruff linting, mypy type checking
- **Test Suite**: Unit tests, integration tests, Python tests, shell tests
- **Test Coverage**: Coverage reporting with Codecov integration
- **Docker Build Check**: Verify both production and test images build successfully
- **Security Scan**: Trivy vulnerability scanning
- **All Checks**: Final validation that all jobs passed

### 2. Pull Request Checks (`pr-checks.yml`)

**Triggers**: PRs to `main`/`develop` (opened, synchronized, reopened, ready_for_review)

**Jobs**:
- **Draft Check**: Skip checks for draft PRs
- **PR Validation**: Title/description length validation
- **Quick Tests**: Fast smoke tests for immediate feedback
- **Breaking Changes**: Detect potential API breaking changes
- **File Checks**: Large file detection, sensitive file scanning
- **Dependency Check**: Poetry lock validation, security vulnerability scanning

### 3. Docker Build and Push (`docker-build.yml`)

**Triggers**: Push to `main`/`develop`/`augment-feature-dev`, PRs to `main`/`develop`

**Jobs**:
- **Build and Push**: Multi-platform Docker image building (linux/amd64, linux/arm64)
- **Image Testing**: Verify built images work correctly
- **Registry Push**: Push to GitHub Container Registry
- **Docker Compose Update**: Update compose files to use registry images

### 4. Docker Tests (`test-docker.yml`)

**Triggers**: Push to `main`/`develop`/`augment-feature-dev`, PRs to `main`/`develop`

**Jobs**:
- **Matrix Testing**: Run different test types (python, shell, unit, integration, quick)
- **Docker Environment**: Test in containerized environment
- **Artifact Upload**: Save test results and coverage reports

### 5. Develop Branch Protection (`develop-branch.yml`)

**Triggers**: Push/PRs to `develop`

**Jobs**:
- **Comprehensive Tests**: Multi-Python version testing (3.11, 3.12)
- **Performance Tests**: CLI response time and import performance
- **Documentation Validation**: README links, example configs, doc consistency
- **Security Compliance**: Secret scanning, credential detection, license validation
- **Deployment Readiness**: Multi-image builds, version consistency checks

### 6. Branch Protection Enforcement (`branch-protection.yml`)

**Triggers**: PRs to `develop`, manual workflow dispatch

**Jobs**:
- **Required Checks**: Validate PR requirements and list mandatory checks
- **Setup Protection**: Automated branch protection rule configuration
- **Workflow Validation**: Ensure all workflow files are present and configured
- **Security Check**: Validate workflow permissions and secret usage

## Required Status Checks

Before merging to `develop`, these checks must pass:

1. ✅ **Continuous Integration / All Checks Passed**
2. ✅ **Pull Request Checks / PR Checks Summary**
3. ✅ **Build and Push Docker Production Image / build-and-push**
4. ✅ **Docker Tests / test-docker**
5. ✅ **Develop Branch Protection / develop-validation-summary**
6. ✅ **Branch Protection Enforcement / required-checks**

## Branch Protection Rules

The `develop` branch is protected with:

- **Required PR reviews**: 1 approving review
- **Dismiss stale reviews**: When new commits are pushed
- **Require status checks**: All checks must pass
- **Up-to-date branches**: Must be current with develop
- **Conversation resolution**: All discussions must be resolved
- **No force pushes**: Prevents history rewriting
- **No deletions**: Prevents accidental branch deletion

## Setup Instructions

### Automatic Setup

Run the setup script to configure branch protection:

```bash
./scripts/setup-branch-protection.sh
```

This script will:
1. Check GitHub CLI installation and authentication
2. Verify the develop branch exists (create if needed)
3. Apply branch protection rules automatically
4. Verify the configuration

### Manual Setup

If automatic setup fails, configure manually:

1. Go to repository Settings → Branches
2. Add rule for `develop` branch
3. Enable required settings (see script output for details)
4. Add all required status checks

### Workflow Dispatch

You can manually trigger branch protection setup:

1. Go to Actions → Branch Protection Enforcement
2. Click "Run workflow"
3. Check "Setup branch protection rules"
4. Run the workflow

## Development Workflow

### Creating a Feature

1. Create feature branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. Make changes and commit:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/your-feature-name
   ```

3. Create PR to `develop` branch

### PR Process

1. **Create PR**: Target `develop` branch
2. **Automated Checks**: Wait for all workflows to complete
3. **Code Review**: Get at least 1 approving review
4. **Address Feedback**: Make changes if requested
5. **Final Checks**: Ensure all status checks are green
6. **Merge**: Use "Squash and merge" or "Merge commit"

### Common Issues

**❌ Status checks failing**:
- Check workflow logs in Actions tab
- Fix code quality issues (formatting, linting)
- Ensure tests pass locally first
- Update dependencies if needed

**❌ PR validation failing**:
- Ensure PR title is 10-100 characters
- Add meaningful description (20+ characters)
- Resolve any file size or security issues

**❌ Docker build failing**:
- Test Docker builds locally
- Check Dockerfile syntax
- Verify all dependencies are available

## Monitoring and Maintenance

### Workflow Status

Monitor workflow health:
- Check Actions tab regularly
- Review failed workflows promptly
- Update workflows as project evolves

### Performance

Track workflow performance:
- Monitor execution times
- Optimize slow jobs
- Use caching effectively

### Security

Maintain security:
- Review secret usage
- Update dependencies regularly
- Monitor security scan results

## Troubleshooting

### Common Commands

```bash
# Test locally before pushing
make test
make format
make lint
make test-docker

# Check workflow syntax
gh workflow list
gh workflow view ci.yml

# Manual branch protection setup
gh api repos/OWNER/REPO/branches/develop/protection --method PUT --input protection.json
```

### Getting Help

1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Run local tests to reproduce issues
4. Check GitHub CLI authentication: `gh auth status`

## Contributing

When modifying workflows:

1. Test changes in feature branch first
2. Update this documentation
3. Ensure backward compatibility
4. Get review from maintainers

---

For more information, see:
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [ToolCrate Testing Guide](./DOCKER_TESTING.md)
