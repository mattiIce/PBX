#!/usr/bin/env python3
"""
Database initialization script for PBX system (wrapper)

This is a compatibility wrapper that executes the main script in ../../scripts/
"""
import sys
import os

if __name__ == "__main__":
    # Get the path to the main script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script_path = os.path.join(script_dir, '..', '..', 'scripts', 'init_database.py')
    
    # Execute the main script
    with open(main_script_path, 'r') as f:
        exec(f.read())
