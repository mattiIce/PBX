#!/bin/bash
# Emergency Server Recovery Script
# Use this when server is completely broken after manual edits

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  PBX EMERGENCY RECOVERY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  WARNING: This will DISCARD ALL local changes on the server"
echo "⚠️  This includes any manual edits you made"
echo ""
echo "This script will:"
echo "  1. Backup current state to /tmp"
echo "  2. Reset ALL files to match repository"
echo "  3. Clear Python cache"
echo "  4. Restart PBX service"
echo ""

# Confirm
read -p "Continue with recovery? (type 'yes' to proceed): " -r
if [[ ! $REPLY == "yes" ]]; then
    echo "Recovery cancelled"
    exit 0
fi

echo ""
echo "Starting recovery..."
echo ""

# Determine PBX directory
PBX_DIR="${PBX_DIR:-/root/PBX}"

if [ ! -d "$PBX_DIR" ]; then
    echo "❌ Error: PBX directory not found at $PBX_DIR"
    echo "   Set PBX_DIR environment variable if in different location"
    exit 1
fi

cd "$PBX_DIR"

# Step 1: Backup
echo "Step 1/5: Creating backup..."
BACKUP_DIR="/tmp/pbx-broken-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r . "$BACKUP_DIR/" 2>/dev/null || true
echo "✓ Backup created at: $BACKUP_DIR"
echo ""

# Step 2: Show what will be reset
echo "Step 2/5: Checking current state..."
GIT_STATUS=$(git status --porcelain)
if [ -n "$GIT_STATUS" ]; then
    echo "⚠️  The following files will be reset:"
    echo "$GIT_STATUS" | head -20
    STATUS_COUNT=$(echo "$GIT_STATUS" | wc -l)
    if [ "$STATUS_COUNT" -gt 20 ]; then
        echo "... and $(($STATUS_COUNT - 20)) more files"
    fi
else
    echo "✓ No local changes detected"
fi
echo ""

# Step 3: Reset to repository
echo "Step 3/5: Resetting to repository state..."
git fetch --all
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $BRANCH"
echo "Resetting to: origin/$BRANCH"
git reset --hard "origin/$BRANCH"
git clean -fd
echo "✓ Repository state restored"
echo ""

# Step 4: Clear Python cache
echo "Step 4/5: Clearing Python bytecode cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Cache cleared"
echo ""

# Step 5: Restart service
echo "Step 5/5: Restarting PBX service..."
systemctl stop pbx 2>&1 || echo "  (service was not running)"
sleep 2
systemctl start pbx
sleep 2
echo ""

# Check status
echo "════════════════════════════════════════════════════════════════"
echo "  RECOVERY COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""

systemctl status pbx --no-pager || true

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  VERIFICATION STEPS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "1. Check for errors in logs:"
echo "   journalctl -u pbx -n 50 | grep -i error"
echo ""
echo "2. Test web interface:"
echo "   - Open browser to your PBX"
echo "   - Navigate to /admin/login.html"
echo "   - Login with your credentials"
echo ""
echo "3. If still broken, run diagnostics:"
echo "   bash scripts/diagnose_server.sh"
echo ""
echo "Backup of old state: $BACKUP_DIR"
echo ""
