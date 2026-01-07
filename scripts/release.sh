#!/bin/bash
#
# Release Script for Warden VoIP PBX
# 
# This script automates the release process:
# - Validates version format
# - Updates version files
# - Creates git tag
# - Generates changelog entry
# - Builds release artifacts
#
# Usage: ./scripts/release.sh <version> [--dry-run]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Print colored message
print_message() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Print error and exit
error_exit() {
    print_message "$RED" "ERROR: $1"
    exit 1
}

# Validate version format (semantic versioning)
validate_version() {
    local version=$1
    if ! [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
        error_exit "Invalid version format: $version. Expected format: X.Y.Z or X.Y.Z-suffix"
    fi
}

# Check if we're on main branch
check_branch() {
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "main" ]; then
        print_message "$YELLOW" "WARNING: Not on main branch (current: $current_branch)"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Check for uncommitted changes
check_uncommitted() {
    if ! git diff-index --quiet HEAD --; then
        error_exit "You have uncommitted changes. Please commit or stash them first."
    fi
}

# Update version files
update_version_files() {
    local version=$1
    local dry_run=$2
    
    print_message "$BLUE" "Updating version to $version..."
    
    if [ "$dry_run" = "true" ]; then
        print_message "$YELLOW" "[DRY RUN] Would update:"
        echo "  - VERSION"
        echo "  - pbx/__version__.py"
        echo "  - pyproject.toml"
        return
    fi
    
    # Update VERSION file
    echo "$version" > "$PROJECT_ROOT/VERSION"
    
    # Update __version__.py
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    local patch=$(echo $version | cut -d. -f3 | cut -d- -f1)
    
    cat > "$PROJECT_ROOT/pbx/__version__.py" << EOF
"""Version information for Warden VoIP PBX."""

__version__ = "$version"
__version_info__ = ($major, $minor, $patch)
EOF
    
    # Update pyproject.toml
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        sed -i "s/^version = .*/version = \"$version\"/" "$PROJECT_ROOT/pyproject.toml"
    fi
    
    print_message "$GREEN" "✓ Version files updated"
}

# Create git tag
create_tag() {
    local version=$1
    local dry_run=$2
    
    local tag="v$version"
    
    if git rev-parse "$tag" >/dev/null 2>&1; then
        error_exit "Tag $tag already exists"
    fi
    
    if [ "$dry_run" = "true" ]; then
        print_message "$YELLOW" "[DRY RUN] Would create tag: $tag"
        return
    fi
    
    print_message "$BLUE" "Creating git tag $tag..."
    git add VERSION pbx/__version__.py pyproject.toml
    git commit -m "Release version $version"
    git tag -a "$tag" -m "Release $version"
    
    print_message "$GREEN" "✓ Git tag created"
}

# Generate changelog entry
generate_changelog() {
    local version=$1
    local dry_run=$2
    
    if [ "$dry_run" = "true" ]; then
        print_message "$YELLOW" "[DRY RUN] Would add changelog entry for $version"
        return
    fi
    
    local date=$(date +%Y-%m-%d)
    local temp_file=$(mktemp)
    
    # Add new version header at the top of changelog
    cat > "$temp_file" << EOF
## [$version] - $date

### Added
- (Add your changes here)

### Changed
- (Add your changes here)

### Fixed
- (Add your changes here)

EOF
    
    # Append existing changelog
    if [ -f "$PROJECT_ROOT/CHANGELOG.md" ]; then
        tail -n +2 "$PROJECT_ROOT/CHANGELOG.md" >> "$temp_file"
        mv "$temp_file" "$PROJECT_ROOT/CHANGELOG.md"
    else
        mv "$temp_file" "$PROJECT_ROOT/CHANGELOG.md"
    fi
    
    print_message "$GREEN" "✓ Changelog entry created (please edit CHANGELOG.md)"
}

# Build release artifacts
build_artifacts() {
    local dry_run=$1
    
    if [ "$dry_run" = "true" ]; then
        print_message "$YELLOW" "[DRY RUN] Would build release artifacts"
        return
    fi
    
    print_message "$BLUE" "Building release artifacts..."
    
    cd "$PROJECT_ROOT"
    
    # Build Python package
    python -m build
    
    print_message "$GREEN" "✓ Release artifacts built in dist/"
}

# Main release process
main() {
    local version=$1
    local dry_run="false"
    
    # Check for dry run flag
    if [ "$2" = "--dry-run" ]; then
        dry_run="true"
        print_message "$YELLOW" "=== DRY RUN MODE ==="
    fi
    
    # Validate inputs
    if [ -z "$version" ]; then
        echo "Usage: $0 <version> [--dry-run]"
        echo ""
        echo "Examples:"
        echo "  $0 1.0.0"
        echo "  $0 1.1.0-beta --dry-run"
        exit 1
    fi
    
    validate_version "$version"
    
    print_message "$BLUE" "=== Release Process for v$version ==="
    
    # Pre-flight checks
    if [ "$dry_run" != "true" ]; then
        check_branch
        check_uncommitted
    fi
    
    # Execute release steps
    update_version_files "$version" "$dry_run"
    generate_changelog "$version" "$dry_run"
    create_tag "$version" "$dry_run"
    
    # Optional: Build artifacts
    if [ "$dry_run" != "true" ]; then
        read -p "Build release artifacts? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            build_artifacts "$dry_run"
        fi
    fi
    
    # Final instructions
    if [ "$dry_run" = "true" ]; then
        print_message "$YELLOW" ""
        print_message "$YELLOW" "Dry run complete. Run without --dry-run to execute."
    else
        print_message "$GREEN" ""
        print_message "$GREEN" "=== Release $version Complete ==="
        print_message "$GREEN" ""
        print_message "$BLUE" "Next steps:"
        echo "  1. Edit CHANGELOG.md to add release notes"
        echo "  2. git push origin main"
        echo "  3. git push origin v$version"
        echo "  4. Create GitHub release at https://github.com/mattiIce/PBX/releases/new"
    fi
}

main "$@"
