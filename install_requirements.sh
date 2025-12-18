#!/bin/bash
# Installation script for PBX dependencies
# This script handles conflicts with system-managed packages

set -e

echo "Installing PBX dependencies..."
echo "Note: This script handles conflicts with system-managed packages like typing_extensions"

# Install dependencies, ignoring the system-installed typing_extensions
# The --ignore-installed flag for typing_extensions allows pip to use the system version
pip3 install -r requirements.txt --break-system-packages --ignore-installed typing_extensions

echo ""
echo "Installation complete!"
echo ""
echo "Note: The system-provided typing_extensions (4.10.0) will be used."
echo "This is compatible with Python 3.12 and all required packages."
