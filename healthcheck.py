#!/usr/bin/env python3
"""Health check script for PBX Docker container"""
import socket
import sys

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect(('localhost', 8880))
    sys.exit(0)
except Exception:
    sys.exit(1)
