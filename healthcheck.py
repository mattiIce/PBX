#!/usr/bin/env python3
"""
Health check script for PBX Docker container.
Tests both port availability and HTTP health endpoint.
"""

import socket
import sys
import urllib.request


def check_port(host, port, timeout=5):
    """Check if port is open"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
        return True
    except Exception:
        return False


def check_http_health(url, timeout=5):
    """Check HTTP health endpoint"""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def main():
    """Run health checks"""
    # Check if HTTP API port is listening
    if not check_port("localhost", 9000, timeout=3):
        print("ERROR: HTTP API port 9000 not responding", file=sys.stderr)
        sys.exit(1)

    # Check HTTP health endpoint
    if not check_http_health("http://localhost:9000/health", timeout=3):
        print("ERROR: Health endpoint not responding", file=sys.stderr)
        sys.exit(1)

    # All checks passed
    sys.exit(0)


if __name__ == "__main__":
    main()
