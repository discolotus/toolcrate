#!/bin/bash

# Setup Branch Protection for ToolCrate Repository
# This script helps configure branch protection rules for the develop branch

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

# Check if gh CLI is installed
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI (gh) is not installed."
        print_status "Please install it from: https://cli.github.com/"
        exit 1
    fi
    
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        print_error "GitHub CLI is not authenticated."
        print_status "Please run: gh auth login"
        exit 1
    fi
    
    print_status "GitHub CLI is installed and authenticated"
}

# Get repository information
get_repo_info() {
    REPO_OWNER=$(gh repo view --json owner --jq '.owner.login')
    REPO_NAME=$(gh repo view --json name --jq '.name')
    print_status "Repository: $REPO_OWNER/$REPO_NAME"
}

# Check if develop branch exists
check_develop_branch() {
    if gh api repos/$REPO_OWNER/$REPO_NAME/branches/develop &> /dev/null; then
        print_status "Develop branch exists"
    else
        print_warning "Develop branch does not exist"
        read -p "Do you want to create the develop branch? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Create develop branch from main
            gh api repos/$REPO_OWNER/$REPO_NAME/git/refs \
                --method POST \
                --field ref="refs/heads/develop" \
                --field sha="$(gh api repos/$REPO_OWNER/$REPO_NAME/git/refs/heads/main --jq '.object.sha')"
            print_status "Develop branch created"
        else
            print_error "Cannot setup branch protection without develop branch"
            exit 1
        fi
    fi
}

# Setup branch protection rules
setup_branch_protection() {
    print_header "Setting up branch protection for develop branch..."
    
    # Define required status checks
    REQUIRED_CHECKS=(
        "Continuous Integration / All Checks Passed"
        "Pull Request Checks / PR Checks Summary"
        "Build and Push Docker Production Image / build-and-push"
        "Docker Tests / test-docker"
        "Develop Branch Protection / develop-validation-summary"
        "Branch Protection Enforcement / required-checks"
    )
    
    # Convert array to JSON format
    CHECKS_JSON=$(printf '%s\n' "${REQUIRED_CHECKS[@]}" | jq -R . | jq -s .)
    
    # Create branch protection rule
    cat > /tmp/branch_protection.json << EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": $CHECKS_JSON
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true
}
EOF

    # Apply branch protection
    if gh api repos/$REPO_OWNER/$REPO_NAME/branches/develop/protection \
        --method PUT \
        --input /tmp/branch_protection.json; then
        print_status "Branch protection rules applied successfully"
    else
        print_error "Failed to apply branch protection rules"
        print_warning "You may need admin permissions to set up branch protection"
        return 1
    fi
    
    # Clean up
    rm -f /tmp/branch_protection.json
}

# Verify branch protection
verify_protection() {
    print_header "Verifying branch protection settings..."
    
    if PROTECTION=$(gh api repos/$REPO_OWNER/$REPO_NAME/branches/develop/protection 2>/dev/null); then
        print_status "Branch protection is active for develop branch"
        
        # Show current settings
        echo "Current protection settings:"
        echo "$PROTECTION" | jq '{
            required_status_checks: .required_status_checks.contexts,
            required_reviews: .required_pull_request_reviews.required_approving_review_count,
            dismiss_stale_reviews: .required_pull_request_reviews.dismiss_stale_reviews,
            allow_force_pushes: .allow_force_pushes.enabled,
            allow_deletions: .allow_deletions.enabled
        }'
    else
        print_warning "Branch protection is not set up for develop branch"
        return 1
    fi
}

# Show manual setup instructions
show_manual_instructions() {
    print_header "Manual Setup Instructions"
    echo
    echo "If the automatic setup failed, you can manually configure branch protection:"
    echo
    echo "1. Go to: https://github.com/$REPO_OWNER/$REPO_NAME/settings/branches"
    echo "2. Click 'Add rule' or edit existing rule for 'develop' branch"
    echo "3. Configure the following settings:"
    echo "   ✅ Require a pull request before merging"
    echo "   ✅ Require approvals (1)"
    echo "   ✅ Dismiss stale PR approvals when new commits are pushed"
    echo "   ✅ Require status checks to pass before merging"
    echo "   ✅ Require branches to be up to date before merging"
    echo "   ✅ Require conversation resolution before merging"
    echo "   ❌ Allow force pushes"
    echo "   ❌ Allow deletions"
    echo
    echo "4. Add these required status checks:"
    for check in "${REQUIRED_CHECKS[@]}"; do
        echo "   - $check"
    done
    echo
}

# Main execution
main() {
    print_header "ToolCrate Branch Protection Setup"
    echo
    
    # Check prerequisites
    check_gh_cli
    get_repo_info
    check_develop_branch
    
    # Setup protection
    if setup_branch_protection; then
        verify_protection
        print_status "✅ Branch protection setup completed successfully!"
        echo
        print_status "The develop branch is now protected and requires:"
        print_status "- At least 1 approving review"
        print_status "- All status checks to pass"
        print_status "- Conversations to be resolved"
        print_status "- No force pushes or deletions"
    else
        print_warning "Automatic setup failed. Showing manual instructions..."
        show_manual_instructions
    fi
    
    echo
    print_header "Next Steps"
    echo "1. Create a test PR to develop branch to verify protection works"
    echo "2. Ensure all team members understand the new workflow"
    echo "3. Update your README.md with the new branching strategy"
    echo
    print_status "Setup complete!"
}

# Run main function
main "$@"
