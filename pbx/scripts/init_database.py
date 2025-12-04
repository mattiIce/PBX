#!/usr/bin/env python3
"""
Database initialization script for PBX system (wrapper)

This is a compatibility wrapper that calls the main script in ../../scripts/
"""
import sys
import os

# Add the parent directory to the path to import the main script
script_dir = os.path.dirname(os.path.abspath(__file__))
main_script_dir = os.path.join(script_dir, '..', '..', 'scripts')
sys.path.insert(0, main_script_dir)

# Import and run the main initialization script
if __name__ == "__main__":
    import init_database
    # The main script will run when imported due to its __main__ block
