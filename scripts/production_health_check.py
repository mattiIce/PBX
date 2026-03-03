#!/usr/bin/env python3
"""
Enhanced Production Health Check Script

Performs comprehensive health checks on all PBX components:
- Service availability
- Database connectivity
- Redis connectivity
- Port availability (SIP, RTP, API)
- Disk space
- Memory usage
- SSL certificate validity
- Configuration validation

Usage:
    python scripts/production_health_check.py [--json] [--critical-only]

Exit codes:
    0 - All checks passed
    1 - Critical failures detected
    2 - Warnings detected (non-critical)
"""

import argparse
import json
import os
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import redis
except ImportError:
    redis = None

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class HealthCheck:
    """Production health check for PBX system."""

    def __init__(self, json_output: bool = False, critical_only: bool = False) -> None:
        self.json_output = json_output
        self.critical_only = critical_only
        self.results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": [],
            "summary": {"passed": 0, "failed": 0, "warnings": 0},
        }
        self.base_dir = Path(__file__).parent.parent

    def log(self, message: str, status: str, level: str = "info") -> None:
        """Log a check result."""
        result = {"name": message, "status": status, "level": level}
        self.results["checks"].append(result)

        if status == "pass":
            self.results["summary"]["passed"] += 1
            if not self.json_output and (not self.critical_only or level == "critical"):
                print(f"{GREEN}✓{RESET} {message}")
        elif status == "fail":
            self.results["summary"]["failed"] += 1
            if not self.json_output:
                print(f"{RED}✗{RESET} {message}")
        elif status == "warn":
            self.results["summary"]["warnings"] += 1
            if not self.json_output and not self.critical_only:
                print(f"{YELLOW}⚠{RESET} {message}")

    def check_port(self, host: str, port: int, timeout: int = 5) -> bool:
        """Check if a port is open."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((host, port))
            return True
        except OSError:
            return False

    def check_service_ports(self) -> None:
        """Check if required service ports are listening."""
        if not self.json_output:
            print(f"\n{BLUE}=== Service Ports ==={RESET}")

        ports = [
            ("SIP Server", 5060, "critical"),
            ("HTTP API", 9000, "critical"),
            ("HTTPS API", 8443, "warning"),
        ]

        for name, port, level in ports:
            if self.check_port("localhost", port, timeout=2):
                self.log(f"{name} (port {port})", "pass", level)
            else:
                self.log(f"{name} (port {port}) - Not accessible", "fail", level)

    def check_database(self) -> None:
        """Check database connectivity."""
        if not self.json_output:
            print(f"\n{BLUE}=== Database ==={RESET}")

        if psycopg2 is None:
            self.log("PostgreSQL driver not installed", "warn", "warning")
            return

        # Try to get DB credentials from environment
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "pbx_system"),
            "user": os.getenv("DB_USER", "pbx_user"),
            "password": os.getenv("DB_PASSWORD", ""),
        }

        try:
            conn = psycopg2.connect(**db_config, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            self.log("Database connectivity", "pass", "critical")
            if not self.critical_only and not self.json_output:
                print(f"  Version: {version[:50]}")
        except (KeyError, TypeError, ValueError, OSError) as e:
            self.log(f"Database connection failed: {e!s}", "fail", "critical")

    def check_redis(self) -> None:
        """Check Redis connectivity."""
        if not self.json_output and not self.critical_only:
            print(f"\n{BLUE}=== Redis ==={RESET}")

        if redis is None:
            self.log("Redis client not installed", "warn", "warning")
            return

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")

        try:
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                socket_connect_timeout=5,
                decode_responses=True,
            )
            r.ping()
            self.log("Redis connectivity", "pass", "warning")
        except Exception as e:
            self.log(f"Redis connection failed: {e!s}", "warn", "warning")

    def check_disk_space(self) -> None:
        """Check available disk space."""
        if not self.json_output and not self.critical_only:
            print(f"\n{BLUE}=== Disk Space ==={RESET}")

        try:
            import shutil

            total, _used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100

            if free_percent < 10:
                self.log(f"Disk space critically low: {free_percent:.1f}% free", "fail", "critical")
            elif free_percent < 20:
                self.log(f"Disk space low: {free_percent:.1f}% free", "warn", "warning")
            else:
                self.log(f"Disk space: {free_percent:.1f}% free", "pass", "info")
        except OSError as e:
            self.log(f"Could not check disk space: {e!s}", "warn", "warning")

    def check_memory(self) -> None:
        """Check available memory."""
        if not self.json_output and not self.critical_only:
            print(f"\n{BLUE}=== Memory ==={RESET}")

        try:
            with Path("/proc/meminfo").open() as f:
                meminfo = {line.split()[0].rstrip(":"): int(line.split()[1]) for line in f}

            mem_total = meminfo.get("MemTotal", 0)
            mem_available = meminfo.get("MemAvailable", 0)

            if mem_total > 0:
                available_percent = (mem_available / mem_total) * 100

                if available_percent < 10:
                    self.log(
                        f"Memory critically low: {available_percent:.1f}% available",
                        "fail",
                        "critical",
                    )
                elif available_percent < 20:
                    self.log(f"Memory low: {available_percent:.1f}% available", "warn", "warning")
                else:
                    self.log(f"Memory: {available_percent:.1f}% available", "pass", "info")
        except (KeyError, OSError, TypeError, ValueError) as e:
            self.log(f"Could not check memory: {e!s}", "warn", "warning")

    def check_ssl_certificate(self) -> None:
        """Check SSL certificate validity."""
        if not self.json_output and not self.critical_only:
            print(f"\n{BLUE}=== SSL Certificate ==={RESET}")

        cert_paths = [
            self.base_dir / "certs" / "server.crt",
            self.base_dir / "server.crt",
        ]
        # Expand glob pattern for Let's Encrypt certificates
        cert_paths.extend(Path("/etc/letsencrypt/live").glob("*/fullchain.pem"))

        cert_found = False
        for cert_path in cert_paths:
            if cert_path.exists():
                cert_found = True
                try:
                    # Basic validation - just check if file is readable
                    # Full certificate validation would require the cryptography module
                    with cert_path.open("rb") as f:
                        f.read()
                    self.log(f"SSL certificate found at {cert_path}", "pass", "warning")
                    break
                except OSError as e:
                    self.log(f"Could not validate certificate: {e!s}", "warn", "warning")
                    break

        if not cert_found:
            self.log("No SSL certificate found", "warn", "warning")

    def check_config_files(self) -> None:
        """Check configuration files exist and are valid."""
        if not self.json_output and not self.critical_only:
            print(f"\n{BLUE}=== Configuration ==={RESET}")

        # Check config.yml
        config_file = self.base_dir / "config.yml"
        if config_file.exists():
            self.log("config.yml exists", "pass", "critical")
            try:
                import yaml

                with config_file.open() as f:
                    yaml.safe_load(f)
                self.log("config.yml is valid YAML", "pass", "critical")
            except OSError as e:
                self.log(f"config.yml is invalid: {e!s}", "fail", "critical")
        else:
            self.log("config.yml not found", "fail", "critical")

        # Check .env file
        env_file = self.base_dir / ".env"
        if env_file.exists():
            self.log(".env file exists", "pass", "warning")
        else:
            self.log(".env file not found (optional)", "warn", "info")

    def run_all_checks(self) -> None:
        """Run all health checks."""
        self.check_service_ports()
        self.check_database()
        self.check_redis()
        self.check_disk_space()
        self.check_memory()
        self.check_ssl_certificate()
        self.check_config_files()

    def print_summary(self) -> int:
        """Print summary of results."""
        if self.json_output:
            print(json.dumps(self.results, indent=2))
        else:
            print(f"\n{BLUE}=== Summary ==={RESET}")
            print(f"{GREEN}Passed:{RESET} {self.results['summary']['passed']}")
            print(f"{RED}Failed:{RESET} {self.results['summary']['failed']}")
            print(f"{YELLOW}Warnings:{RESET} {self.results['summary']['warnings']}")

            if self.results["summary"]["failed"] > 0:
                print(f"\n{RED}Status: UNHEALTHY (critical failures detected){RESET}")
                return 1
            if self.results["summary"]["warnings"] > 0:
                print(f"\n{YELLOW}Status: DEGRADED (warnings detected){RESET}")
                return 2
            print(f"\n{GREEN}Status: HEALTHY{RESET}")
            return 0

        # Return exit code based on failures
        if self.results["summary"]["failed"] > 0:
            return 1
        if self.results["summary"]["warnings"] > 0:
            return 2
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="PBX Production Health Check")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--critical-only", action="store_true", help="Only show critical checks")
    args = parser.parse_args()

    health_check = HealthCheck(json_output=args.json, critical_only=args.critical_only)
    health_check.run_all_checks()
    exit_code = health_check.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
