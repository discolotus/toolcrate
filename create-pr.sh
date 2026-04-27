#!/bin/bash

# Script to create PR for GitHub Actions workflows and branch protection
# This script helps overcome OAuth scope limitations when pushing workflow files

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating Pull Request for GitHub Actions Workflows${NC}"
echo "=================================================="

# Check if we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "setup-better-github-actions-workflows-PRs" ]]; then
    echo -e "${RED}Error: Not on the correct branch. Current: $CURRENT_BRANCH${NC}"
    echo "Please switch to: setup-better-github-actions-workflows-PRs"
    exit 1
fi

# Check if changes are committed
if ! git diff --quiet HEAD; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    echo "Please commit your changes first"
    exit 1
fi

# Try to push the branch
echo "Attempting to push branch..."
if git push origin setup-better-github-actions-workflows-PRs; then
    echo -e "${GREEN}✅ Branch pushed successfully${NC}"
else
    echo -e "${RED}❌ Failed to push branch due to OAuth scope limitations${NC}"
    echo ""
    echo "This is expected when pushing workflow files. Here are your options:"
    echo ""
    echo "Option 1: Use GitHub CLI (if you have it installed)"
    echo "  gh auth refresh -s workflow"
    echo "  git push origin setup-better-github-actions-workflows-PRs"
    echo ""
    echo "Option 2: Create PR manually via GitHub web interface"
    echo "  1. Go to: https://github.com/discolotus/toolcrate"
    echo "  2. Click 'Compare & pull request' for your branch"
    echo "  3. Set base branch to 'develop'"
    echo "  4. Use the PR template below"
    echo ""
    echo "Option 3: Use personal access token with workflow scope"
    echo "  1. Create token at: https://github.com/settings/tokens"
    echo "  2. Include 'workflow' scope"
    echo "  3. Update remote: git remote set-url origin https://TOKEN@github.com/discolotus/toolcrate.git"
    echo ""
fi

# Generate PR description
cat > pr-description.md << 'EOF'
# 🎯 Implement Comprehensive GitHub Actions Workflows and Branch Protection

## Overview

This PR implements a comprehensive GitHub Actions workflow system with branch protection for the ToolCrate project. The new system ensures code quality, security, and reliability before merging changes into the develop branch.

## ✨ New Features

### 🔄 GitHub Actions Workflows

- **`ci.yml`**: Core CI pipeline with code quality checks, comprehensive testing, coverage reporting, Docker builds, and security scanning
- **`pr-checks.yml`**: Fast PR validation with title/description checks, quick tests, breaking change detection, and dependency validation
- **`develop-branch.yml`**: Comprehensive develop branch validation with multi-Python testing, performance checks, and deployment readiness
- **`branch-protection.yml`**: Automated branch protection enforcement and setup

### 🛡️ Branch Protection

- **Required Status Checks**: 6 mandatory workflows must pass before merge
- **PR Requirements**: 1 approval, conversation resolution, up-to-date branches
- **Security**: No force pushes or deletions allowed
- **Automated Setup**: Script for easy branch protection configuration

### 🔧 Tools and Scripts

- **`scripts/setup-branch-protection.sh`**: Automated branch protection setup with GitHub CLI
- **Comprehensive Documentation**: Detailed guides for workflows and development process

## 📝 Changes Made

### New Files
- `.github/workflows/ci.yml` - Comprehensive CI pipeline
- `.github/workflows/pr-checks.yml` - PR validation workflow
- `.github/workflows/develop-branch.yml` - Develop branch protection
- `.github/workflows/branch-protection.yml` - Branch protection enforcement
- `scripts/setup-branch-protection.sh` - Automated setup script
- `docs/GITHUB_WORKFLOWS.md` - Workflow documentation
- `WORKFLOW_SETUP_SUMMARY.md` - Implementation summary

### Modified Files
- `.github/workflows/docker-build.yml` - Added develop branch support
- `.github/workflows/test-docker.yml` - Added develop branch support
- `.github/workflows/claude.yml` - Removed failing claude-response job
- `README.md` - Updated contribution guidelines

## 🔍 Required Status Checks

Before merging to develop, these checks must pass:

1. ✅ **Continuous Integration / All Checks Passed**
2. ✅ **Pull Request Checks / PR Checks Summary**
3. ✅ **Build and Push Docker Production Image / build-and-push**
4. ✅ **Docker Tests / test-docker**
5. ✅ **Develop Branch Protection / develop-validation-summary**
6. ✅ **Branch Protection Enforcement / required-checks**

## 🧪 Testing

- [x] All new workflows validated for syntax
- [x] Existing workflows updated to include develop branch
- [x] Setup script tested for branch protection configuration
- [x] Documentation reviewed for completeness

## 📚 Documentation

- **[GitHub Workflows Guide](docs/GITHUB_WORKFLOWS.md)**: Comprehensive workflow documentation
- **[Setup Summary](WORKFLOW_SETUP_SUMMARY.md)**: Implementation details and next steps
- **Updated README**: New contribution guidelines and workflow information

## 🚀 Next Steps

1. **Merge this PR**: This will test the new workflow system
2. **Run setup script**: Execute `./scripts/setup-branch-protection.sh` to enable branch protection
3. **Team onboarding**: Share workflow documentation with contributors

## 🔧 Setup Instructions

After merging, run the automated setup:

```bash
# Setup branch protection (requires GitHub CLI)
./scripts/setup-branch-protection.sh

# Or manually trigger via workflow dispatch:
# Go to Actions → Branch Protection Enforcement → Run workflow
```

## 🎉 Benefits

- **Code Quality**: Automated formatting, linting, type checking
- **Reliability**: Multi-environment testing, Docker integration
- **Security**: Vulnerability scanning, secret detection
- **Developer Experience**: Fast feedback, clear documentation
- **Compliance**: Branch protection, required reviews

---

**Note**: This PR targets the `develop` branch to test the new workflow system. Once merged and validated, the branch protection rules will be automatically enforced for all future PRs.
EOF

echo ""
echo -e "${GREEN}PR Description generated in: pr-description.md${NC}"
echo ""
echo "Files changed in this PR:"
git diff --name-only HEAD~1
echo ""
echo "Commit message:"
git log -1 --pretty=format:"%s"
echo ""
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. If push succeeded, create PR via GitHub CLI or web interface"
echo "2. Use the content from pr-description.md as the PR description"
echo "3. Set base branch to 'develop'"
echo "4. After merging, run: ./scripts/setup-branch-protection.sh"
