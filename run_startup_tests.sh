#!/bin/bash
#
# Startup Test Runner for PBX System
# Run this script on server startup to test the system and log failures
#
# Usage:
#   ./run_startup_tests.sh
#
# This script will:
#   1. Run all PBX tests
#   2. Log failures to test_failures.log
#   3. Commit the log file to git
#   4. Push changes to remote repository (if git credentials are configured)
#

echo "========================================================================"
echo "PBX System - Startup Test Runner"
echo "========================================================================"
echo "Started at: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Check if run_tests.py exists
if [ ! -f "run_tests.py" ]; then
    echo "❌ Error: run_tests.py not found in $SCRIPT_DIR"
    exit 1
fi

# Run the tests
echo "Running PBX system tests..."
echo ""
python3 run_tests.py

# Capture exit code
EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "Completed at: $(date)"
echo "Exit code: $EXIT_CODE"
echo "========================================================================"

# Return the exit code from run_tests.py
exit $EXIT_CODE
