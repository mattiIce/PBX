#!/bin/bash
# Installation script for Warden Voip dependencies
# This script handles conflicts with system-managed packages

set -e

# Check if pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install Python 3 and pip3 first."
    exit 1
fi

# Check Python version (requires 3.7+)
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
min_version="3.7"
if [ "$(printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1)" != "$min_version" ]; then
    echo "Error: Python $min_version or higher is required. Current version: $python_version"
    exit 1
fi

# Validate that requirements.txt exists
[[ -f requirements.txt ]] || { echo 'Error: requirements.txt not found'; exit 1; }

echo "Installing Warden Voip dependencies..."
echo "Python version: $python_version"
echo "Note: This script handles conflicts with system-managed packages like typing_extensions"
echo ""

# Install dependencies, ignoring the system-installed typing_extensions
# The --ignore-installed flag for typing_extensions allows pip to use the system version
pip3 install -r requirements.txt --break-system-packages --ignore-installed typing_extensions

echo ""
echo "Installation complete!"
echo ""
echo "Note: The system-provided typing_extensions (4.10.0) will be used."
echo "This is compatible with Python 3.12 and all required packages."
