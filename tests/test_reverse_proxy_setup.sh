#!/bin/bash
# Test script for reverse proxy setup script
# This validates the bash syntax and basic structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SETUP_SCRIPT="$REPO_ROOT/scripts/setup_reverse_proxy.sh"

echo "Testing reverse proxy setup script..."
echo "Script location: $SETUP_SCRIPT"

# Test 1: Check if script exists
if [ ! -f "$SETUP_SCRIPT" ]; then
    echo "FAIL: Script not found at $SETUP_SCRIPT"
    exit 1
fi
echo "✓ Script file exists"

# Test 2: Check bash syntax
if ! bash -n "$SETUP_SCRIPT"; then
    echo "FAIL: Script has syntax errors"
    exit 1
fi
echo "✓ Script syntax is valid"

# Test 3: Check for required functions
required_functions=(
    "is_port_80_in_use"
    "has_nginx_processes"
    "check_port_80"
    "manage_nginx_service"
)

for func in "${required_functions[@]}"; do
    if ! grep -q "^${func}()" "$SETUP_SCRIPT" && ! grep -q "^${func} ()" "$SETUP_SCRIPT"; then
        echo "FAIL: Required function '$func' not found"
        exit 1
    fi
    echo "✓ Function '$func' exists"
done

# Test 4: Check for Apache handling logic
if ! grep -q "apache2\|httpd" "$SETUP_SCRIPT"; then
    echo "FAIL: Script doesn't handle Apache servers"
    exit 1
fi
echo "✓ Script includes Apache handling"

# Test 5: Check for user prompts for stopping service
if ! grep -q 'read -p.*Stop.*y/n' "$SETUP_SCRIPT"; then
    echo "FAIL: Script doesn't prompt user to stop conflicting service"
    exit 1
fi
echo "✓ Script prompts user for service stop confirmation"

# Test 6: Check for systemctl stop command with variable
if ! grep -q 'systemctl stop "\$service_name"' "$SETUP_SCRIPT" && ! grep -q 'systemctl stop \$service_name' "$SETUP_SCRIPT" && ! grep -q 'systemctl stop.*"$service_name"' "$SETUP_SCRIPT"; then
    echo "FAIL: Script doesn't stop the conflicting service with proper variable substitution"
    exit 1
fi
echo "✓ Script can stop conflicting service"

# Test 7: Check for proper error handling
if ! grep -q "Port 80 is still in use after stopping" "$SETUP_SCRIPT"; then
    echo "FAIL: Script doesn't verify port is freed after stopping service"
    exit 1
fi
echo "✓ Script verifies port is freed after stopping service"

echo ""
echo "All tests passed! ✓"
echo ""
echo "Summary:"
echo "- Script syntax is valid"
echo "- All required functions are present"
echo "- Apache/httpd handling is implemented"
echo "- User confirmation prompts are in place"
echo "- Service stop functionality is implemented"
echo "- Port verification after service stop is implemented"
