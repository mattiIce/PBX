#!/usr/bin/env python3
"""
Backup Verification Script

Automatically verify that backups are valid and restorable.
Tests backup integrity without affecting production data.

Usage:
    python scripts/verify_backup.py [--backup-path /path/to/backup] [--full-test]
"""

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple


class BackupVerifier:
    """Verify backup integrity and restorability."""

    def __init__(self, backup_path: str = None, full_test: bool = False):
        self.backup_path = backup_path
        self.full_test = full_test
        self.base_dir = Path(__file__).parent.parent
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "passed": 0,
            "failed": 0,
        }

    def log_check(self, name: str, status: bool, details: str = ""):
        """Log a check result."""
        self.results["checks"].append(
            {"name": name, "status": "pass" if status else "fail", "details": details}
        )

        if status:
            self.results["passed"] += 1
            print(f"✓ {name}")
        else:
            self.results["failed"] += 1
            print(f"✗ {name}: {details}")

        if details and status:
            print(f"  {details}")

    def find_latest_backup(self) -> Tuple[bool, str]:
        """Find the latest backup file."""
        # Check common backup locations
        backup_locations = [
            self.base_dir / "backups",
            Path("/var/backups/pbx"),
            Path("/backup/pbx"),
        ]

        for location in backup_locations:
            if location.exists():
                # Find .sql or .tar.gz files
                backup_files = list(location.glob("*.sql")) + list(location.glob("*.tar.gz"))
                if backup_files:
                    # Get most recent
                    latest = max(backup_files, key=lambda p: p.stat().st_mtime)
                    return True, str(latest)

        return False, "No backup files found"

    def verify_database_backup(self, backup_file: str) -> bool:
        """Verify database backup file."""
        print(f"\nVerifying database backup: {backup_file}")

        # Check file exists
        if not Path(backup_file).exists():
            self.log_check("Backup file exists", False, f"{backup_file} not found")
            return False

        self.log_check(
            "Backup file exists",
            True,
            f"Size: {Path(backup_file).stat().st_size / 1024 / 1024:.2f} MB",
        )

        # Check file is not empty
        if Path(backup_file).stat().st_size == 0:
            self.log_check("Backup file not empty", False, "File is empty")
            return False

        self.log_check("Backup file not empty", True)

        # For SQL backups, check basic structure
        if backup_file.endswith(".sql"):
            try:
                with open(backup_file, "r") as f:
                    first_lines = [next(f) for _ in range(10)]
                    content = "".join(first_lines)

                    # Check for PostgreSQL dump header
                    if "PostgreSQL database dump" in content:
                        self.log_check("Valid PostgreSQL dump", True)
                    else:
                        self.log_check("Valid PostgreSQL dump", False, "Missing dump header")
                        return False

                    # Check for table definitions
                    if "CREATE TABLE" in content or "CREATE" in content:
                        self.log_check("Contains schema", True)
                    else:
                        self.log_check("Contains schema", False, "No CREATE statements found")

            except Exception as e:
                self.log_check("Readable backup file", False, str(e))
                return False

        # Full test: Try to restore to temporary database
        if self.full_test and backup_file.endswith(".sql"):
            return self.test_restore_database(backup_file)

        return True

    def test_restore_database(self, backup_file: str) -> bool:
        """Test restoring database backup to temporary database."""
        print("\nTesting database restore (full test)...")

        # Create temporary database name with random suffix to prevent collisions
        random_suffix = random.randint(100000, 999999)
        temp_db = f"pbx_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random_suffix}"

        try:
            # Create temporary database
            result = subprocess.run(
                ["sudo", "-u", "postgres", "createdb", temp_db], capture_output=True, timeout=30
            )

            if result.returncode != 0:
                self.log_check("Create temporary database", False, result.stderr.decode())
                return False

            self.log_check("Create temporary database", True, f"Database: {temp_db}")

            # Restore backup to temporary database
            with open(backup_file, "r") as f:
                result = subprocess.run(
                    ["sudo", "-u", "postgres", "psql", temp_db],
                    stdin=f,
                    capture_output=True,
                    timeout=300,  # 5 minutes
                )

            if result.returncode != 0:
                self.log_check("Restore backup", False, "Restore failed")
                return False

            self.log_check("Restore backup", True)

            # Verify restored data
            result = subprocess.run(
                [
                    "sudo",
                    "-u",
                    "postgres",
                    "psql",
                    temp_db,
                    "-c",
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';",
                ],
                capture_output=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Parse table count from output
                output = result.stdout.decode()
                self.log_check("Verify restored tables", True, f"Output: {output.strip()}")
            else:
                self.log_check("Verify restored tables", False)

            return True

        except Exception as e:
            self.log_check("Database restore test", False, str(e))
            return False

        finally:
            # Clean up temporary database
            try:
                subprocess.run(
                    ["sudo", "-u", "postgres", "dropdb", temp_db], capture_output=True, timeout=30
                )
                print(f"  Cleaned up temporary database: {temp_db}")
            except Exception:
                print(f"  Warning: Could not clean up temporary database: {temp_db}")

    def verify_config_backup(self) -> bool:
        """Verify configuration backup."""
        print("\nVerifying configuration files...")

        config_files = [
            "config.yml",
            ".env",
        ]

        all_good = True
        for config_file in config_files:
            path = self.base_dir / config_file
            if path.exists():
                self.log_check(f"{config_file} exists", True)
            else:
                self.log_check(f"{config_file} exists", False, "File not found")
                all_good = False

        return all_good

    def verify_backup_script(self) -> bool:
        """Verify backup script is configured."""
        print("\nVerifying backup configuration...")

        backup_script = self.base_dir / "scripts" / "backup.sh"
        if not backup_script.exists():
            self.log_check("Backup script exists", False, "scripts/backup.sh not found")
            return False

        self.log_check("Backup script exists", True)

        # Check if executable
        if os.access(backup_script, os.X_OK):
            self.log_check("Backup script executable", True)
        else:
            self.log_check("Backup script executable", False, "Script not executable")

        return True

    def check_backup_schedule(self) -> bool:
        """Check if automated backups are scheduled."""
        print("\nChecking backup schedule...")

        # Check for cron job
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, timeout=10)

            if result.returncode == 0:
                cron_content = result.stdout.decode()
                if "backup.sh" in cron_content:
                    self.log_check("Automated backup scheduled", True, "Found in crontab")
                    return True
                else:
                    self.log_check("Automated backup scheduled", False, "Not found in crontab")
            else:
                self.log_check("Automated backup scheduled", False, "Could not check crontab")

        except Exception as e:
            self.log_check("Automated backup scheduled", False, str(e))

        return False

    def run_verification(self) -> int:
        """Run all backup verifications."""
        print("=" * 70)
        print("Backup Verification")
        print("=" * 70)

        # Find backup to verify
        if self.backup_path:
            backup_file = self.backup_path
        else:
            found, backup_file = self.find_latest_backup()
            if not found:
                print(f"✗ {backup_file}")
                return 1

        # Run checks
        self.verify_backup_script()
        self.verify_config_backup()
        self.verify_database_backup(backup_file)
        self.check_backup_schedule()

        # Summary
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")

        if self.results["failed"] == 0:
            print("\n✓ All backup verifications passed")
            return 0
        else:
            print(f"\n✗ {self.results['failed']} verification(s) failed")
            return 1

    def save_report(self, output_file: str):
        """Save verification report."""
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nReport saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Backup Verification Tool")
    parser.add_argument("--backup-path", help="Path to specific backup file to verify")
    parser.add_argument(
        "--full-test", action="store_true", help="Perform full restore test (requires sudo access)"
    )
    parser.add_argument("--report", help="Save verification report to file")
    args = parser.parse_args()

    verifier = BackupVerifier(backup_path=args.backup_path, full_test=args.full_test)

    exit_code = verifier.run_verification()

    if args.report:
        verifier.save_report(args.report)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
