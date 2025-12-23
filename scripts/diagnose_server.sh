#!/bin/bash
# Server Diagnostics Script
# Run this to diagnose issues with the PBX server

echo "════════════════════════════════════════════════════════════════"
echo "  PBX SERVER DIAGNOSTICS"
echo "════════════════════════════════════════════════════════════════"
echo ""

PBX_DIR="${PBX_DIR:-/root/PBX}"

if [ ! -d "$PBX_DIR" ]; then
    echo "❌ Error: PBX directory not found at $PBX_DIR"
    exit 1
fi

cd "$PBX_DIR"

# 1. Git Status
echo "1. GIT STATUS"
echo "─────────────────────────────────────────────────────────────────"
git status --short | head -20
if [ $(git status --porcelain 2>/dev/null | wc -l) -gt 20 ]; then
    echo "... and $(($(git status --porcelain | wc -l) - 20)) more files modified"
fi
echo ""

# 2. Current Branch
echo "2. CURRENT BRANCH"
echo "─────────────────────────────────────────────────────────────────"
git branch --show-current
echo ""

# 3. Recent Commits
echo "3. RECENT COMMITS"
echo "─────────────────────────────────────────────────────────────────"
git log -5 --oneline
echo ""

# 4. Service Status
echo "4. SERVICE STATUS"
echo "─────────────────────────────────────────────────────────────────"
systemctl status pbx --no-pager | head -20
echo ""

# 5. Recent Error Logs
echo "5. RECENT ERROR LOGS (last 30 lines)"
echo "─────────────────────────────────────────────────────────────────"
journalctl -u pbx -n 30 --no-pager | grep -i -E "(error|syntax|fail|exception)" || echo "No errors found in recent logs"
echo ""

# 6. Python Syntax Check (sample files)
echo "6. PYTHON SYNTAX CHECK (sample files)"
echo "─────────────────────────────────────────────────────────────────"
ERROR_COUNT=0
CHECKED=0
for file in $(find pbx -name "*.py" -type f | head -10); do
    CHECKED=$((CHECKED + 1))
    if ! python3 -m py_compile "$file" 2>/dev/null; then
        echo "❌ Syntax error in: $file"
        python3 -m py_compile "$file" 2>&1 | head -3
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
done

if [ $ERROR_COUNT -eq 0 ]; then
    echo "✓ Checked $CHECKED files - all valid"
else
    echo "✗ Found $ERROR_COUNT files with syntax errors out of $CHECKED checked"
fi
echo ""

# 7. Web Interface Files
echo "7. WEB INTERFACE FILES"
echo "─────────────────────────────────────────────────────────────────"
if [ -f "admin/index.html" ]; then
    echo "✓ admin/index.html exists ($(wc -l < admin/index.html) lines)"
else
    echo "❌ admin/index.html missing"
fi

if [ -f "admin/css/admin.css" ]; then
    echo "✓ admin/css/admin.css exists ($(wc -l < admin/css/admin.css) lines)"
else
    echo "❌ admin/css/admin.css missing"
fi

if [ -f "admin/js/admin.js" ]; then
    echo "✓ admin/js/admin.js exists ($(wc -l < admin/js/admin.js) lines)"
else
    echo "❌ admin/js/admin.js missing"
fi
echo ""

# 8. Port Listening
echo "8. LISTENING PORTS"
echo "─────────────────────────────────────────────────────────────────"
if command -v netstat >/dev/null 2>&1; then
    netstat -tlnp 2>/dev/null | grep -E ":(80|443|5060|8080)" || echo "No PBX ports listening"
elif command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep -E ":(80|443|5060|8080)" || echo "No PBX ports listening"
else
    echo "Cannot check listening ports (netstat/ss not available)"
fi
echo ""

# 9. Disk Space
echo "9. DISK SPACE"
echo "─────────────────────────────────────────────────────────────────"
df -h "$PBX_DIR" | tail -1
echo ""

# 10. Summary
echo "════════════════════════════════════════════════════════════════"
echo "  DIAGNOSTIC SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo ""

SERVICE_STATUS=$(systemctl is-active pbx 2>/dev/null || echo "unknown")
if [ "$SERVICE_STATUS" = "active" ]; then
    echo "Service Status: ✓ RUNNING"
else
    echo "Service Status: ✗ NOT RUNNING ($SERVICE_STATUS)"
fi

if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "Local Changes: ⚠️  YES (files differ from repository)"
else
    echo "Local Changes: ✓ NO (matches repository)"
fi

if [ $ERROR_COUNT -gt 0 ]; then
    echo "Syntax Errors: ✗ YES ($ERROR_COUNT found)"
else
    echo "Syntax Errors: ✓ NO"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

if [ "$SERVICE_STATUS" != "active" ] || [ -n "$(git status --porcelain 2>/dev/null)" ] || [ $ERROR_COUNT -gt 0 ]; then
    echo "⚠️  ISSUES DETECTED"
    echo ""
    echo "Recommended action:"
    echo "  bash scripts/emergency_recovery.sh"
    echo ""
else
    echo "✓ No major issues detected"
    echo ""
    echo "If you're still experiencing problems:"
    echo "  1. Check web browser console for JavaScript errors"
    echo "  2. Verify network connectivity to server"
    echo "  3. Check firewall settings"
    echo ""
fi
