#!/usr/bin/env python3
"""
Automated Disaster Recovery (DR) Testing Script

This script automates disaster recovery testing procedures to ensure backup
and restore processes work correctly in a production environment.

Usage:
    python scripts/test_disaster_recovery.py --test-type full
    python scripts/test_disaster_recovery.py --test-type database-only
    python scripts/test_disaster_recovery.py --test-type config-only --dry-run
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DRTestConfig:
    """DR test configuration"""

    test_type: str = "full"  # full, database-only, config-only, files-only
    backup_dir: str = "/var/backups/pbx-dr-test"
    restore_dir: str = "/tmp/pbx-dr-restore"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "pbx_system"
    db_user: str = "pbx_user"
    dry_run: bool = False
    skip_cleanup: bool = False


@dataclass
class DRTestResults:
    """DR test results"""

    test_type: str
    timestamp: str
    duration: float
    overall_success: bool
    backup_results: dict[str, Any]
    restore_results: dict[str, Any]
    verification_results: dict[str, Any]
    rto_seconds: float  # Recovery Time Objective
    rpo_seconds: float  # Recovery Point Objective
    errors: list[str]
    warnings: list[str]


class DisasterRecoveryTester:
    """Automated DR testing"""

    def __init__(self, config: DRTestConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.results = {
            "backup": {},
            "restore": {},
            "verification": {},
            "errors": [],
            "warnings": [],
        }
        self.start_time = None
        self.backup_completed_time = None
        self.restore_completed_time = None

    def run_command(self, cmd: list[str], check: bool = True) -> tuple[bool, str, str]:
        """Run a shell command and return status and output"""
        if self.config.dry_run:
            self.logger.info(f"[DRY RUN] Would execute: {' '.join(cmd)}")
            return True, "Dry run - command not executed", ""

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=300)
            return True, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out after 300 seconds"
        except (OSError, subprocess.SubprocessError) as e:
            return False, "", str(e)

    def test_database_backup(self) -> bool:
        """Test database backup"""
        self.logger.info("Testing database backup...")

        try:
            # Create backup directory
            Path(self.config.backup_dir).mkdir(parents=True, exist_ok=True)

            # Backup filename with timestamp
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_file = Path(self.config.backup_dir) / f"pbx_db_backup_{timestamp}.sql"

            # Run pg_dump
            cmd = [
                "pg_dump",
                "-h",
                self.config.db_host,
                "-p",
                str(self.config.db_port),
                "-U",
                self.config.db_user,
                "-d",
                self.config.db_name,
                "-F",
                "c",  # Custom format (compressed)
                "-f",
                backup_file,
                "-v",
            ]

            success, _stdout, stderr = self.run_command(cmd)

            if success or self.config.dry_run:
                if not self.config.dry_run:
                    # Verify backup file exists and has content
                    if Path(backup_file).exists():
                        file_size = Path(backup_file).stat().st_size
                        self.results["backup"]["database"] = {
                            "success": True,
                            "file": backup_file,
                            "size_bytes": file_size,
                            "size_mb": round(file_size / 1024 / 1024, 2),
                        }
                        self.logger.info(
                            f"Database backup successful: {file_size / 1024 / 1024:.2f} MB"
                        )
                        return True
                    self.results["errors"].append("Database backup file not created")
                    return False
                self.results["backup"]["database"] = {"success": True, "dry_run": True}
                return True
            self.results["errors"].append(f"Database backup failed: {stderr}")
            return False

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.results["errors"].append(f"Database backup exception: {e!s}")
            return False

    def test_config_backup(self) -> bool:
        """Test configuration backup"""
        self.logger.info("Testing configuration backup...")

        try:
            config_backup_dir = Path(self.config.backup_dir) / "config"
            config_backup_dir.mkdir(parents=True, exist_ok=True)

            # Files to backup
            config_files = [
                "config.yml",
                ".env",
                "pbx.service",
                "auto_attendant/*.yml",
                "provisioning_templates/*",
            ]

            backed_up_files = []
            for pattern in config_files:
                # Handle glob patterns
                if "*" in pattern:
                    files = list(Path().glob(pattern))
                    for file in files:
                        if file.exists():
                            dest = Path(config_backup_dir) / file.name
                            if not self.config.dry_run:
                                shutil.copy2(file, dest)
                            backed_up_files.append(str(file))
                elif Path(pattern).exists():
                    dest = Path(config_backup_dir) / Path(pattern).name
                    if not self.config.dry_run:
                        shutil.copy2(pattern, dest)
                    backed_up_files.append(pattern)

            self.results["backup"]["config"] = {
                "success": True,
                "files_backed_up": len(backed_up_files),
                "files": backed_up_files,
            }
            self.logger.info(f"Configuration backup successful: {len(backed_up_files)} files")
            return True

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.results["errors"].append(f"Configuration backup failed: {e!s}")
            return False

    def test_voicemail_backup(self) -> bool:
        """Test voicemail and recordings backup"""
        self.logger.info("Testing voicemail/recordings backup...")

        try:
            data_backup_dir = Path(self.config.backup_dir) / "data"
            data_backup_dir.mkdir(parents=True, exist_ok=True)

            # Directories to backup
            data_dirs = ["voicemail", "recordings", "voicemail_prompts", "moh"]

            total_size = 0
            backed_up_dirs = []

            for dir_name in data_dirs:
                if Path(dir_name).exists() and Path(dir_name).is_dir():
                    dest = Path(data_backup_dir) / dir_name
                    if not self.config.dry_run:
                        shutil.copytree(dir_name, dest, dirs_exist_ok=True)

                        # Calculate size
                        for entry in dest.rglob("*"):
                            if entry.is_file():
                                total_size += entry.stat().st_size

                    backed_up_dirs.append(dir_name)

            self.results["backup"]["data"] = {
                "success": True,
                "directories_backed_up": len(backed_up_dirs),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
            }
            self.logger.info(f"Data backup successful: {total_size / 1024 / 1024:.2f} MB")
            return True

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.results["errors"].append(f"Data backup failed: {e!s}")
            return False

    def test_database_restore(self) -> bool:
        """Test database restore"""
        self.logger.info("Testing database restore...")

        try:
            # Find latest backup
            if self.config.dry_run:
                self.logger.info("[DRY RUN] Would restore latest database backup")
                self.results["restore"]["database"] = {"success": True, "dry_run": True}
                return True

            backup_files = sorted(Path(self.config.backup_dir).glob("pbx_db_backup_*.sql"))
            if not backup_files:
                self.results["errors"].append("No database backup found")
                return False

            latest_backup = str(backup_files[-1])
            self.logger.info(f"Restoring from: {latest_backup}")

            # Create test database (validate name to prevent injection)
            test_db_name = f"{self.config.db_name}_dr_test"
            # Validate database name - only allow alphanumeric and underscore
            if not all(c.isalnum() or c == "_" for c in test_db_name):
                self.results["errors"].append("Invalid database name for DR test")
                return False

            # Drop test database if exists
            cmd_drop = [
                "psql",
                "-h",
                self.config.db_host,
                "-p",
                str(self.config.db_port),
                "-U",
                self.config.db_user,
                "-c",
                f"DROP DATABASE IF EXISTS {test_db_name};",
            ]
            self.run_command(cmd_drop, check=False)

            # Create test database
            cmd_create = [
                "psql",
                "-h",
                self.config.db_host,
                "-p",
                str(self.config.db_port),
                "-U",
                self.config.db_user,
                "-c",
                f"CREATE DATABASE {test_db_name};",
            ]
            success, stdout, stderr = self.run_command(cmd_create)

            if not success:
                self.results["errors"].append(f"Failed to create test database: {stderr}")
                return False

            # Restore backup
            cmd_restore = [
                "pg_restore",
                "-h",
                self.config.db_host,
                "-p",
                str(self.config.db_port),
                "-U",
                self.config.db_user,
                "-d",
                test_db_name,
                "-v",
                latest_backup,
            ]
            success, stdout, stderr = self.run_command(cmd_restore, check=False)

            # Verify restore
            cmd_verify = [
                "psql",
                "-h",
                self.config.db_host,
                "-p",
                str(self.config.db_port),
                "-U",
                self.config.db_user,
                "-d",
                test_db_name,
                "-t",
                "-c",
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';",
            ]
            success, stdout, stderr = self.run_command(cmd_verify)

            if success:
                table_count = int(stdout.strip())
                self.results["restore"]["database"] = {
                    "success": True,
                    "backup_file": latest_backup,
                    "test_database": test_db_name,
                    "table_count": table_count,
                }
                self.logger.info(f"Database restore successful: {table_count} tables")

                # Cleanup test database
                if not self.config.skip_cleanup:
                    cmd_cleanup = [
                        "psql",
                        "-h",
                        self.config.db_host,
                        "-p",
                        str(self.config.db_port),
                        "-U",
                        self.config.db_user,
                        "-c",
                        f"DROP DATABASE {test_db_name};",
                    ]
                    self.run_command(cmd_cleanup, check=False)

                return True
            self.results["errors"].append(f"Database restore verification failed: {stderr}")
            return False

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.results["errors"].append(f"Database restore failed: {e!s}")
            return False

    def test_config_restore(self) -> bool:
        """Test configuration restore"""
        self.logger.info("Testing configuration restore...")

        try:
            config_backup_dir = Path(self.config.backup_dir) / "config"

            if not Path(config_backup_dir).exists():
                self.results["errors"].append("Configuration backup directory not found")
                return False

            # Create restore directory
            restore_config_dir = Path(self.config.restore_dir) / "config"
            restore_config_dir.mkdir(parents=True, exist_ok=True)

            # Restore files
            restored_files = []
            for file in config_backup_dir.iterdir():
                dest = restore_config_dir / file.name
                if not self.config.dry_run:
                    shutil.copy2(file, dest)
                restored_files.append(file.name)

            self.results["restore"]["config"] = {
                "success": True,
                "files_restored": len(restored_files),
                "restore_directory": restore_config_dir,
            }
            self.logger.info(f"Configuration restore successful: {len(restored_files)} files")
            return True

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.results["errors"].append(f"Configuration restore failed: {e!s}")
            return False

    def verify_backup_integrity(self) -> bool:
        """Verify backup integrity"""
        self.logger.info("Verifying backup integrity...")

        try:
            verification_results = {
                "database_backup_exists": False,
                "config_backup_exists": False,
                "data_backup_exists": False,
                "all_valid": False,
            }

            # Check database backup
            db_backups = list(Path(self.config.backup_dir).glob("pbx_db_backup_*.sql"))
            if db_backups:
                verification_results["database_backup_exists"] = True
                # Check backup file is not empty
                if Path(str(db_backups[-1]).stat().st_size) > 1000:  # At least 1KB
                    verification_results["database_backup_valid"] = True

            # Check config backup
            config_dir = Path(self.config.backup_dir) / "config"
            if config_dir.exists() and any(config_dir.iterdir()):
                verification_results["config_backup_exists"] = True

            # Check data backup
            data_dir = Path(self.config.backup_dir) / "data"
            if Path(data_dir).exists():
                verification_results["data_backup_exists"] = True

            # Overall verification
            verification_results["all_valid"] = (
                verification_results.get("database_backup_valid", False)
                and verification_results["config_backup_exists"]
                and verification_results["data_backup_exists"]
            )

            self.results["verification"] = verification_results
            return verification_results["all_valid"]

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.results["errors"].append(f"Verification failed: {e!s}")
            return False

    def calculate_rto_rpo(self) -> tuple[float, float]:
        """Calculate Recovery Time Objective and Recovery Point Objective"""
        # RTO: Time from start of restore to completion
        if self.backup_completed_time and self.restore_completed_time:
            rto = self.restore_completed_time - self.backup_completed_time
        else:
            rto = 0

        # RPO: Time between backup completion and disaster (simulated as current time)
        if self.backup_completed_time:
            rpo = time.time() - self.backup_completed_time
        else:
            rpo = 0

        return rto, rpo

    def run_full_dr_test(self) -> DRTestResults:
        """Run complete DR test"""
        self.logger.info("=" * 70)
        self.logger.info("Starting Disaster Recovery Test")
        self.logger.info("=" * 70)

        self.start_time = time.time()
        overall_success = True

        # Phase 1: Backup
        self.logger.info("\nPhase 1: BACKUP")
        self.logger.info("-" * 70)

        if self.config.test_type in ["full", "database-only"] and not self.test_database_backup():
            overall_success = False
        if self.config.test_type in ["full", "config-only"] and not self.test_config_backup():
            overall_success = False
        if self.config.test_type in ["full", "files-only"] and not self.test_voicemail_backup():
            overall_success = False

        self.backup_completed_time = time.time()

        # Phase 2: Restore
        self.logger.info("\nPhase 2: RESTORE")
        self.logger.info("-" * 70)

        if self.config.test_type in ["full", "database-only"] and not self.test_database_restore():
            overall_success = False
        if self.config.test_type in ["full", "config-only"] and not self.test_config_restore():
            overall_success = False

        self.restore_completed_time = time.time()

        # Phase 3: Verification
        self.logger.info("\nPhase 3: VERIFICATION")
        self.logger.info("-" * 70)

        if not self.verify_backup_integrity():
            overall_success = False

        # Calculate metrics
        duration = time.time() - self.start_time
        rto, rpo = self.calculate_rto_rpo()

        # Compile results
        results = DRTestResults(
            test_type=self.config.test_type,
            timestamp=datetime.now(UTC).isoformat(),
            duration=duration,
            overall_success=overall_success,
            backup_results=self.results["backup"],
            restore_results=self.results["restore"],
            verification_results=self.results["verification"],
            rto_seconds=rto,
            rpo_seconds=rpo,
            errors=self.results["errors"],
            warnings=self.results["warnings"],
        )

        return results


def print_results(results: DRTestResults) -> None:
    """Print formatted test results"""
    print("\n" + "=" * 70)
    print("DISASTER RECOVERY TEST RESULTS")
    print("=" * 70)
    print(f"Test Type: {results.test_type}")
    print(f"Timestamp: {results.timestamp}")
    print(f"Duration: {results.duration:.2f}s")
    print()

    print("Backup Results:")
    for component, result in results.backup_results.items():
        status = "✅" if result.get("success") else "❌"
        print(f"  {status} {component.upper()}: {result}")
    print()

    print("Restore Results:")
    for component, result in results.restore_results.items():
        status = "✅" if result.get("success") else "❌"
        print(f"  {status} {component.upper()}: {result}")
    print()

    print("Verification Results:")
    for check, result in results.verification_results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}: {result}")
    print()

    print("Recovery Metrics:")
    print(f"  RTO (Recovery Time Objective): {results.rto_seconds:.2f}s")
    print(f"  RPO (Recovery Point Objective): {results.rpo_seconds:.2f}s")
    print()

    if results.errors:
        print("Errors:")
        for error in results.errors:
            print(f"  ❌ {error}")
        print()

    if results.warnings:
        print("Warnings:")
        for warning in results.warnings:
            print(f"  ⚠️  {warning}")
        print()

    # Overall result
    print("=" * 70)
    if results.overall_success:
        print("✅ DISASTER RECOVERY TEST PASSED")
        print("   All components backed up and restored successfully")
        print(f"   RTO: {results.rto_seconds:.1f}s, RPO: {results.rpo_seconds:.1f}s")
    else:
        print("❌ DISASTER RECOVERY TEST FAILED")
        print(f"   {len(results.errors)} error(s) detected")
        print("   Review errors above and fix issues")
    print("=" * 70 + "\n")


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Automated Disaster Recovery Testing Tool")
    parser.add_argument(
        "--test-type",
        choices=["full", "database-only", "config-only", "files-only"],
        default="full",
        help="Type of DR test to run (default: full)",
    )
    parser.add_argument(
        "--backup-dir", default="/var/backups/pbx-dr-test", help="Directory for test backups"
    )
    parser.add_argument(
        "--restore-dir", default="/tmp/pbx-dr-restore", help="Directory for test restores"
    )
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument("--db-name", default="pbx_system", help="Database name")
    parser.add_argument("--db-user", default="pbx_user", help="Database user")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--skip-cleanup", action="store_true", help="Skip cleanup of test databases and files"
    )
    parser.add_argument("--save-report", help="Save results to JSON file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Create config
    config = DRTestConfig(
        test_type=args.test_type,
        backup_dir=args.backup_dir,
        restore_dir=args.restore_dir,
        db_host=args.db_host,
        db_name=args.db_name,
        db_user=args.db_user,
        dry_run=args.dry_run,
        skip_cleanup=args.skip_cleanup,
    )

    # Run test
    tester = DisasterRecoveryTester(config)

    try:
        results = tester.run_full_dr_test()
        print_results(results)

        # Save report if requested
        if args.save_report:
            with Path(args.save_report).open("w") as f:
                json.dump(asdict(results), f, indent=2)
            print(f"Results saved to {args.save_report}")

        # Exit with appropriate code
        sys.exit(0 if results.overall_success else 1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
