#!/usr/bin/env python3
"""
Production Readiness Validation Script

This script performs automated checks to validate that the PBX system
is ready for production deployment. It checks:
- System requirements
- Configuration
- Security settings
- Database connectivity
- Required files and directories
- Service status
- Network connectivity

Usage:
    python scripts/validate_production_readiness.py [--json] [--fix]

Options:
    --json      Output results in JSON format
    --fix       Attempt to fix issues where possible (use with caution)
    --verbose   Show detailed output
"""

import argparse
import json
import platform
import socket
import subprocess
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class ProductionValidator:
    """Validates production readiness of PBX system."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": [],
            "info": [],
        }
        self.base_dir = Path(__file__).parent.parent

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with appropriate formatting."""
        if level == "pass":
            print(f"{GREEN}✓{RESET} {message}")
            self.results["passed"].append(message)
        elif level == "fail":
            print(f"{RED}✗{RESET} {message}")
            self.results["failed"].append(message)
        elif level == "warn":
            print(f"{YELLOW}⚠{RESET} {message}")
            self.results["warnings"].append(message)
        elif level == "info" and self.verbose:
            print(f"{BLUE}ℹ{RESET} {message}")
            self.results["info"].append(message)

    def check_system_requirements(self) -> None:
        """Check system requirements."""
        print(f"\n{BLUE}=== System Requirements ==={RESET}")

        # Check OS
        if platform.system() == "Linux":
            self.log("Operating System: Linux", "pass")
            try:
                with open("/etc/os-release") as f:
                    os_info = f.read()
                    if "Ubuntu" in os_info:
                        self.log("Distribution: Ubuntu detected", "pass")
                    else:
                        self.log("Ubuntu 24.04 LTS recommended for production", "warn")
            except OSError:
                self.log("Could not determine Linux distribution", "warn")
        else:
            self.log(f"Operating System: {platform.system()} (Linux recommended)", "warn")

        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 12):
            self.log(f"Python version: {python_version.major}.{python_version.minor}", "pass")
        else:
            self.log(
                f"Python {python_version.major}.{python_version.minor} detected. "
                "Python 3.13+ required",
                "fail",
            )

        # Check system dependencies
        dependencies = [
            ("espeak", "Text-to-speech engine"),
            ("ffmpeg", "Audio processing"),
        ]
        for cmd, desc in dependencies:
            if self.command_exists(cmd):
                self.log(f"{desc} ({cmd}): Installed", "pass")
            else:
                self.log(f"{desc} ({cmd}): Not found", "fail")

    def check_configuration(self) -> None:
        """Check configuration files."""
        print(f"\n{BLUE}=== Configuration ==={RESET}")

        # Check config.yml exists
        config_path = self.base_dir / "config.yml"
        if config_path.exists():
            self.log("config.yml: Found", "pass")
            # Could add YAML validation here
        else:
            self.log("config.yml: Not found", "fail")

        # Check .env exists
        env_path = self.base_dir / ".env"
        if env_path.exists():
            self.log(".env file: Found", "pass")
        else:
            self.log(".env file: Not found (recommended for production secrets)", "warn")

        # Check test_config.yml is not used in production
        test_config = self.base_dir / "test_config.yml"
        if test_config.exists():
            self.log("test_config.yml should not be used in production", "warn")

    def check_security(self) -> None:
        """Check security configurations."""
        print(f"\n{BLUE}=== Security ==={RESET}")

        # Check SSL certificate
        ssl_cert = self.base_dir / "ssl" / "pbx.crt"
        ssl_key = self.base_dir / "ssl" / "pbx.key"

        if ssl_cert.exists() and ssl_key.exists():
            self.log("SSL certificate and key: Found", "pass")

            # Check key permissions
            if ssl_key.exists():
                stat_info = ssl_key.stat()
                mode = oct(stat_info.st_mode)[-3:]
                if mode in {"600", "400"}:
                    self.log("SSL private key permissions: Secure", "pass")
                else:
                    self.log(f"SSL private key permissions: {mode} (should be 600 or 400)", "warn")
        else:
            self.log("SSL certificate not found (required for HTTPS)", "fail")

        # Check if default passwords might be in use
        config_path = self.base_dir / "config.yml"
        if config_path.exists():
            content = config_path.read_text()
            if "password: password" in content or "password: '1234'" in content:
                self.log("Default passwords detected in config.yml", "fail")
            else:
                self.log("No obvious default passwords in config.yml", "pass")

    def check_database(self) -> None:
        """Check database configuration and connectivity."""
        print(f"\n{BLUE}=== Database ==={RESET}")

        try:
            import yaml

            config_path = self.base_dir / "config.yml"
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)

                db_config = config.get("database", {})
                db_type = db_config.get("type", "sqlite")

                if db_type == "postgresql":
                    self.log("Database type: PostgreSQL (recommended for production)", "pass")

                    # Try to import psycopg2
                    try:
                        import psycopg2

                        self.log("psycopg2 library: Installed", "pass")

                        # Try to connect (if credentials are available)
                        try:
                            host = db_config.get("host", "localhost")
                            port = db_config.get("port", 5432)
                            database = db_config.get("database", "pbx_system")
                            user = db_config.get("user", "pbx_user")
                            password = db_config.get("password", "")

                            if password:
                                conn = psycopg2.connect(
                                    host=host,
                                    port=port,
                                    database=database,
                                    user=user,
                                    password=password,
                                    connect_timeout=5,
                                )
                                conn.close()
                                self.log("Database connectivity: Successful", "pass")
                            else:
                                self.log("Database password not set in config", "warn")
                        except psycopg2.OperationalError as e:
                            self.log(
                                f"Database connectivity: Failed (operational error: {e})", "fail"
                            )
                        except psycopg2.Error as e:
                            self.log(f"Database connectivity: Failed (database error: {e})", "fail")
                        except (KeyError, TypeError, ValueError) as e:
                            self.log(
                                f"Database connectivity: Failed (unexpected error: {e})", "fail"
                            )
                    except ImportError:
                        self.log("psycopg2 library: Not installed", "fail")

                elif db_type == "sqlite":
                    self.log(
                        "Database type: SQLite (PostgreSQL recommended for production)", "warn"
                    )
                else:
                    self.log(f"Database type: Unknown ({db_type})", "fail")
        except (KeyError, TypeError, ValueError) as e:
            self.log(f"Could not check database configuration: {e}", "fail")

    def check_directories(self) -> None:
        """Check required directories exist."""
        print(f"\n{BLUE}=== Directories ==={RESET}")

        required_dirs = [
            ("logs", "Log files"),
            ("voicemail", "Voicemail storage"),
            ("recordings", "Call recordings"),
            ("moh", "Music on hold"),
            ("ssl", "SSL certificates"),
        ]

        for dir_name, description in required_dirs:
            dir_path = self.base_dir / dir_name
            if dir_path.exists():
                self.log(f"{description} directory ({dir_name}): Exists", "pass")
            else:
                self.log(
                    f"{description} directory ({dir_name}): Not found (will be created on startup)",
                    "warn",
                )

    def check_network(self) -> None:
        """Check network configuration."""
        print(f"\n{BLUE}=== Network ==={RESET}")

        # Check if ports are available
        ports_to_check = [
            (5060, "SIP", "udp"),
            (9000, "HTTPS API", "tcp"),
        ]

        for port, service, protocol in ports_to_check:
            if protocol == "tcp":
                if self.is_port_available(port):
                    self.log(f"Port {port} ({service}): Available", "pass")
                else:
                    self.log(f"Port {port} ({service}): In use or blocked", "warn")

    def check_python_packages(self) -> None:
        """Check required Python packages are installed."""
        print(f"\n{BLUE}=== Python Dependencies ==={RESET}")

        critical_packages = [
            ("yaml", "PyYAML"),
            ("cryptography", "cryptography"),
            ("sqlalchemy", "SQLAlchemy"),
            ("flask", "Flask"),
        ]

        for module_name, package_name in critical_packages:
            try:
                __import__(module_name)
                self.log(f"{package_name}: Installed", "pass")
            except ImportError:
                self.log(f"{package_name}: Not installed", "fail")

    def check_service_files(self) -> None:
        """Check systemd service files."""
        print(f"\n{BLUE}=== Service Configuration ==={RESET}")

        service_file = Path("/etc/systemd/system/pbx.service")
        if service_file.exists():
            self.log("Systemd service file: Installed", "pass")

            # Check if service is enabled
            try:
                result = subprocess.run(
                    ["systemctl", "is-enabled", "pbx"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and "enabled" in result.stdout:
                    self.log("PBX service: Enabled for autostart", "pass")
                else:
                    self.log("PBX service: Not enabled for autostart", "warn")
            except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError):
                self.log("Could not check service status", "info")
        else:
            self.log("Systemd service file: Not installed", "warn")

    def check_monitoring(self) -> None:
        """Check monitoring and logging setup."""
        print(f"\n{BLUE}=== Monitoring & Logging ==={RESET}")

        # Check log directory
        log_dir = self.base_dir / "logs"
        if log_dir.exists():
            self.log("Log directory: Exists", "pass")

            # Check if logs are being written
            log_files = list(log_dir.glob("*.log"))
            if log_files:
                self.log(f"Log files: Found {len(log_files)} log file(s)", "pass")
            else:
                self.log("Log files: No logs found (system may not have run yet)", "info")
        else:
            self.log("Log directory: Does not exist", "warn")

        # Check if logrotate is configured
        logrotate_config = Path("/etc/logrotate.d/pbx")
        if logrotate_config.exists():
            self.log("Logrotate configuration: Installed", "pass")
        else:
            self.log("Logrotate configuration: Not found (recommended)", "warn")

    def check_backups(self) -> None:
        """Check backup configuration."""
        print(f"\n{BLUE}=== Backup Configuration ==={RESET}")

        # Check for backup script
        backup_script = self.base_dir / "scripts" / "backup.sh"
        if backup_script.exists():
            self.log("Backup script: Found", "pass")
        else:
            self.log("Backup script: Not found (highly recommended)", "warn")

        # Check for cron jobs
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            if "backup" in result.stdout.lower() or "pbx" in result.stdout.lower():
                self.log("Backup cron job: Configured", "pass")
            else:
                self.log("Backup cron job: Not found (highly recommended)", "warn")
        except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError):
            self.log("Could not check cron jobs", "info")

    def command_exists(self, command: str) -> bool:
        """Check if a command exists."""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("localhost", port))
                return result != 0  # Port is available if connection fails
        except OSError:
            return False

    def run_all_checks(self) -> int:
        """Run all validation checks."""
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}PBX Production Readiness Validation{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}")

        self.check_system_requirements()
        self.check_configuration()
        self.check_security()
        self.check_database()
        self.check_directories()
        self.check_network()
        self.check_python_packages()
        self.check_service_files()
        self.check_monitoring()
        self.check_backups()

        # Summary
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}Summary{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}")
        print(f"{GREEN}Passed:{RESET} {len(self.results['passed'])}")
        print(f"{RED}Failed:{RESET} {len(self.results['failed'])}")
        print(f"{YELLOW}Warnings:{RESET} {len(self.results['warnings'])}")

        if len(self.results["failed"]) == 0:
            print(f"\n{GREEN}✓ All critical checks passed!{RESET}")
            if len(self.results["warnings"]) > 0:
                print(f"{YELLOW}⚠ Please review warnings before production deployment{RESET}")
            return 0
        print(f"\n{RED}✗ {len(self.results['failed'])} critical issues found{RESET}")
        print(f"{RED}Please fix these issues before production deployment{RESET}")
        return 1

    def output_json(self) -> str:
        """Output results in JSON format."""
        return json.dumps(self.results, indent=2)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate PBX system production readiness")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    validator = ProductionValidator(verbose=args.verbose)
    exit_code = validator.run_all_checks()

    if args.json:
        print("\n" + validator.output_json())

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
