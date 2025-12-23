#!/bin/bash
# Force Update Server from Repository
# This script pulls the latest code from the repository and updates all files on the server
# Run this on the production server to sync with the repository

set -e  # Exit on error

echo "=========================================="
echo "PBX Server Update Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Warning: Not running as root. Some operations may fail."
    echo "Consider running with: sudo $0"
    echo ""
fi

# Determine the script directory and PBX root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PBX_ROOT="${PBX_ROOT:-/root/PBX}"

echo "PBX Root Directory: $PBX_ROOT"
echo ""

# Navigate to PBX directory
if [ ! -d "$PBX_ROOT" ]; then
    echo "Error: PBX directory not found at $PBX_ROOT"
    echo "Please set PBX_ROOT environment variable or update this script"
    exit 1
fi

cd "$PBX_ROOT"

echo "Current directory: $(pwd)"
echo ""

# Check if this is a git repository
if [ ! -d ".git" ]; then
    echo "Error: Not a git repository. Cannot update from remote."
    exit 1
fi

# Show current status
echo "Current git status:"
git status --short
echo ""

# Check for local modifications
if [ -n "$(git status --porcelain)" ]; then
    echo "WARNING: You have local modifications!"
    echo "The following files will be overwritten:"
    git status --short
    echo ""
    read -p "Do you want to backup and continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Update cancelled."
        exit 1
    fi
    
    # Create backup
    BACKUP_DIR="/tmp/pbx-backup-$(date +%Y%m%d-%H%M%S)"
    echo "Creating backup at $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup modified files
    git status --porcelain | while read status file; do
        if [ -f "$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$BACKUP_DIR/$file"
        fi
    done
    
    echo "Backup created successfully"
    echo ""
fi

# Fetch latest changes
echo "Fetching latest changes from remote..."
git fetch --all
echo ""

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"
echo ""

# Show what will be updated
echo "Changes to be pulled:"
git log HEAD..origin/$CURRENT_BRANCH --oneline
echo ""

# Option 1: Hard reset to match repository exactly
read -p "Choose update method - (1) Hard reset (overwrites ALL changes), (2) Pull and merge: " -r
echo ""

if [ "$REPLY" = "1" ]; then
    echo "Performing hard reset to origin/$CURRENT_BRANCH..."
    echo "WARNING: This will discard ALL local changes!"
    sleep 2
    
    # Stash any local changes (will be dropped)
    git stash push -u -m "Auto-stash before hard reset $(date)"
    
    # Hard reset to match remote exactly
    git reset --hard origin/$CURRENT_BRANCH
    
    # Clean untracked files
    git clean -fd
    
    echo "✓ Hard reset complete"
else
    echo "Performing pull with merge..."
    
    # Try to pull with merge
    if ! git pull origin "$CURRENT_BRANCH"; then
        echo ""
        echo "Error: Pull failed. You may have merge conflicts."
        echo "Please resolve conflicts manually or use hard reset option."
        exit 1
    fi
    
    echo "✓ Pull complete"
fi

echo ""
echo "=========================================="
echo "Verifying Python files..."
echo "=========================================="

# Check all Python files for syntax errors
ERRORS=0
while IFS= read -r -d '' file; do
    if ! python3 -m py_compile "$file" 2>/dev/null; then
        echo "✗ Syntax error in: $file"
        python3 -m py_compile "$file"
        ERRORS=$((ERRORS + 1))
    fi
done < <(find . -name "*.py" -type f ! -path "./.git/*" ! -path "./venv/*" ! -path "./.venv/*" -print0)

if [ $ERRORS -eq 0 ]; then
    echo "✓ All Python files are valid"
else
    echo "✗ Found $ERRORS files with syntax errors"
    echo "Please review the errors above before restarting services"
    exit 1
fi

echo ""
echo "=========================================="
echo "Update Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review the changes: git log -5"
echo "2. Restart the PBX service: systemctl restart pbx"
echo "3. Check service status: systemctl status pbx"
echo "4. Monitor logs: journalctl -u pbx -f"
echo ""

# Ask if user wants to restart service
read -p "Restart PBX service now? (yes/no): " -r
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restarting PBX service..."
    systemctl restart pbx
    echo ""
    echo "Waiting for service to start..."
    sleep 3
    echo ""
    systemctl status pbx --no-pager
    echo ""
    echo "Service restarted. Monitor logs with: journalctl -u pbx -f"
fi

echo ""
echo "Update complete!"
