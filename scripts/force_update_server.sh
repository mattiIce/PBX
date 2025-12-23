#!/bin/bash
# Quick Force Update - No prompts, just sync
# Use this for automated updates or when you're sure you want to overwrite everything

set -e

PBX_ROOT="${PBX_ROOT:-/root/PBX}"
cd "$PBX_ROOT"

echo "Force updating PBX from repository..."

# Backup current state
BACKUP_DIR="/tmp/pbx-backup-$(date +%Y%m%d-%H%M%S)"
echo "Creating backup at $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"
cp -r . "$BACKUP_DIR/" 2>/dev/null || true

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

# Fetch and hard reset
git fetch --all
git reset --hard origin/"$CURRENT_BRANCH"
git clean -fd

echo "✓ Repository synced"

# Verify syntax
echo "Verifying Python files..."
ERROR_COUNT=0
while IFS= read -r -d '' file; do
    if ! python3 -m py_compile "$file" 2>/dev/null; then
        echo "✗ Error in: $file"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
done < <(find . -name "*.py" -type f ! -path "./.git/*" ! -path "./venv/*" -print0)

if [ $ERROR_COUNT -eq 0 ]; then
    echo "✓ All files valid"
    echo "Restarting service..."
    systemctl restart pbx
    echo ""
    echo "=========================================="
    echo "✓ Update Complete"
    echo "=========================================="
    echo ""
    echo "⚠️  IMPORTANT: Clear your browser cache!"
    echo "   Press Ctrl+Shift+R (or Cmd+Shift+R on Mac)"
    echo "   when accessing the admin panel"
    echo ""
    echo "See BROWSER_CACHE_FIX.md for details"
    echo ""
    exit 0
else
    echo "✗ Found $ERROR_COUNT errors - NOT restarting service"
    exit 1
fi
