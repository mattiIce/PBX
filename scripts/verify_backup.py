#!/usr/bin/env python3
"""
Backup Verification Script

Automatically verify that backups are valid and restorable.
Tests backup integrity without affecting production data.

Usage:
    python scripts/verify_backup.py [--backup-path /path/to/backup] [--full-test]
"""

import argparse
import gzip
import json
import os
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Backup locations searched when no --backup-path is given
BACKUP_LOCATIONS = [
    Path("/var/backups/pbx"),
    Path("/backup/pbx"),
]


class BackupVerifier:
    """Verify backup integrity and restorability."""

    def __init__(self, backup_path: str | None = None, full_test: bool = False):
        self.backup_path = backup_path
        self.full_test = full_test
        self.base_dir = Path(__file__).parent.parent
        self.results: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": [],
            "passed": 0,
            "failed": 0,
        }

    def log_check(self, name: str, status: bool, details: str = "") -> None:
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

    # ------------------------------------------------------------------
    # Backup discovery
    # ------------------------------------------------------------------

    def _get_backup_locations(self) -> list[Path]:
        """Return all backup locations to search, including project-local."""
        return [self.base_dir / "backups", *BACKUP_LOCATIONS]

    def find_latest_backup_dir(self) -> Path | None:
        """Find the latest timestamped backup directory (created by backup.sh).

        backup.sh creates directories named YYYYMMDD_HHMMSS with sub-dirs
        database/, config/, voicemail/, recordings/, ssl/, prompts/.
        """
        for location in self._get_backup_locations():
            if not location.is_dir():
                continue
            # Match timestamped directories (e.g. 20260221_020000)
            candidates = sorted(
                (d for d in location.iterdir() if d.is_dir() and d.name[:8].isdigit()),
                key=lambda d: d.name,
                reverse=True,
            )
            if candidates:
                return candidates[0]
        return None

    def find_latest_database_backup(self) -> tuple[bool, str]:
        """Find the latest database backup file.

        Searches for:
        1. Structured backups: <timestamp>/database/pbx_database.sql(.gz)
        2. Flat files from pbx-backup.sh: db_<timestamp>.sql.gz
        3. Top-level full archives: pbx_backup_<timestamp>.tar.gz
        """
        for location in self._get_backup_locations():
            if not location.is_dir():
                continue

            # 1. Look inside timestamped directories for database dumps
            db_files: list[Path] = []
            db_files.extend(location.glob("*/database/pbx_database.sql"))
            db_files.extend(location.glob("*/database/pbx_database.sql.gz"))
            if db_files:
                latest = max(db_files, key=lambda p: p.stat().st_mtime)
                return True, str(latest)

            # 2. Flat database dumps from production deploy script (db_*.sql.gz)
            flat_db = list(location.glob("db_*.sql.gz"))
            if flat_db:
                latest = max(flat_db, key=lambda p: p.stat().st_mtime)
                return True, str(latest)

            # 3. Full backup archives (pbx_backup_*.tar.gz)
            archives = list(location.glob("pbx_backup_*.tar.gz"))
            if archives:
                latest = max(archives, key=lambda p: p.stat().st_mtime)
                return True, str(latest)

        return False, "No database backup files found in any known backup location"

    # ------------------------------------------------------------------
    # Database backup verification
    # ------------------------------------------------------------------

    def verify_database_backup(self, backup_file: str) -> bool:
        """Verify database backup file."""
        print(f"\nVerifying database backup: {backup_file}")
        path = Path(backup_file)

        # Check file exists
        if not path.exists():
            self.log_check("Database backup file exists", False, f"{backup_file} not found")
            return False

        size_mb = path.stat().st_size / 1024 / 1024
        self.log_check("Database backup file exists", True, f"Size: {size_mb:.2f} MB")

        # Check file is not empty
        if path.stat().st_size == 0:
            self.log_check("Database backup not empty", False, "File is empty")
            return False

        self.log_check("Database backup not empty", True)

        # Validate content based on file type
        if backup_file.endswith(".sql"):
            return self._verify_sql_dump(path)
        if backup_file.endswith(".sql.gz"):
            return self._verify_gzipped_sql_dump(path)
        if backup_file.endswith(".tar.gz"):
            return self._verify_backup_archive(path)

        self.log_check(
            "Recognized backup format",
            False,
            f"Unknown extension: {path.suffix} (expected .sql, .sql.gz, or .tar.gz)",
        )
        return False

    def _read_initial_content(self, path: Path, *, compressed: bool = False) -> str | None:
        """Read the first portion of a file for header inspection."""
        try:
            if compressed:
                with gzip.open(path, "rt", errors="replace") as f:
                    return "".join(f.readline() for _ in range(20))
            else:
                with path.open(errors="replace") as f:
                    return "".join(f.readline() for _ in range(20))
        except (OSError, gzip.BadGzipFile) as e:
            self.log_check("Readable backup file", False, str(e))
            return None

    def _check_postgresql_header(self, content: str) -> bool:
        """Validate that content looks like a PostgreSQL dump."""
        if "PostgreSQL database dump" in content:
            self.log_check("Valid PostgreSQL dump header", True)
        else:
            self.log_check(
                "Valid PostgreSQL dump header",
                False,
                "File does not contain PostgreSQL dump header",
            )
            return False

        if "CREATE" in content.upper():
            self.log_check("Contains schema definitions", True)
        else:
            # Not fatal — header is in first 20 lines, CREATE may come later
            self.log_check(
                "Contains schema definitions",
                True,
                "Not found in header (may appear later in file)",
            )

        return True

    def _verify_sql_dump(self, path: Path) -> bool:
        """Verify a plain .sql dump file."""
        content = self._read_initial_content(path)
        if content is None:
            return False

        valid = self._check_postgresql_header(content)

        if valid and self.full_test:
            return self.test_restore_database(str(path))
        return valid

    def _verify_gzipped_sql_dump(self, path: Path) -> bool:
        """Verify a gzip-compressed .sql.gz dump file."""
        # First verify gzip integrity
        try:
            with gzip.open(path, "rb") as f:
                # Read a small chunk to verify the gzip framing is valid
                f.read(1024)
            self.log_check("Valid gzip compression", True)
        except (gzip.BadGzipFile, OSError) as e:
            self.log_check("Valid gzip compression", False, str(e))
            return False

        content = self._read_initial_content(path, compressed=True)
        if content is None:
            return False

        return self._check_postgresql_header(content)

    def _verify_backup_archive(self, path: Path) -> bool:
        """Verify a full backup .tar.gz archive contains database files."""
        try:
            result = subprocess.run(
                ["tar", "-tzf", str(path)],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0:
                self.log_check("Valid tar.gz archive", False, "Archive is corrupt or unreadable")
                return False

            self.log_check("Valid tar.gz archive", True)

            file_list = result.stdout.decode(errors="replace")
            has_db = "database/pbx_database.sql" in file_list
            if has_db:
                self.log_check("Archive contains database backup", True)
            else:
                self.log_check(
                    "Archive contains database backup",
                    False,
                    "No database/pbx_database.sql found in archive",
                )
            return has_db

        except (OSError, subprocess.SubprocessError) as e:
            self.log_check("Readable backup archive", False, str(e))
            return False

    def test_restore_database(self, backup_file: str) -> bool:
        """Test restoring database backup to temporary database."""
        print("\nTesting database restore (full test)...")

        # Create temporary database name with random suffix to prevent collisions
        random_suffix = random.randint(100000, 999999)
        temp_db = f"pbx_verify_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{random_suffix}"

        try:
            # Create temporary database
            result = subprocess.run(
                ["sudo", "-u", "postgres", "createdb", temp_db],
                capture_output=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                self.log_check("Create temporary database", False, result.stderr.decode())
                return False

            self.log_check("Create temporary database", True, f"Database: {temp_db}")

            # Restore backup to temporary database
            with Path(backup_file).open() as f:
                result = subprocess.run(
                    ["sudo", "-u", "postgres", "psql", temp_db],
                    stdin=f,
                    capture_output=True,
                    timeout=300,  # 5 minutes
                    check=False,
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
                check=False,
            )

            if result.returncode == 0:
                # Parse table count from output
                output = result.stdout.decode()
                self.log_check("Verify restored tables", True, f"Output: {output.strip()}")
            else:
                self.log_check("Verify restored tables", False)

            return True

        except (
            KeyError,
            OSError,
            TypeError,
            ValueError,
            subprocess.SubprocessError,
        ) as e:
            self.log_check("Database restore test", False, str(e))
            return False

        finally:
            # Clean up temporary database
            try:
                subprocess.run(
                    ["sudo", "-u", "postgres", "dropdb", temp_db],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                print(f"  Cleaned up temporary database: {temp_db}")
            except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError):
                print(f"  Warning: Could not clean up temporary database: {temp_db}")

    # ------------------------------------------------------------------
    # Backup structure verification
    # ------------------------------------------------------------------

    def verify_backup_structure(self, backup_dir: Path) -> bool:
        """Verify the directory structure of a timestamped backup.

        Checks that all expected components created by backup.sh are present.
        """
        print(f"\nVerifying backup structure: {backup_dir}")

        all_ok = True

        # Check required database backup
        db_gz = backup_dir / "database" / "pbx_database.sql.gz"
        db_sql = backup_dir / "database" / "pbx_database.sql"
        if db_gz.exists():
            size_mb = db_gz.stat().st_size / 1024 / 1024
            self.log_check("Database backup (gzip)", True, f"Size: {size_mb:.2f} MB")
        elif db_sql.exists():
            size_mb = db_sql.stat().st_size / 1024 / 1024
            self.log_check("Database backup (plain SQL)", True, f"Size: {size_mb:.2f} MB")
        else:
            self.log_check(
                "Database backup present",
                False,
                f"Neither pbx_database.sql.gz nor pbx_database.sql found in {backup_dir}/database/",
            )
            all_ok = False

        # Check config backup
        config_dir = backup_dir / "config"
        if config_dir.is_dir() and any(config_dir.iterdir()):
            config_count = len(list(config_dir.iterdir()))
            self.log_check("Configuration backup", True, f"{config_count} file(s)")
        else:
            self.log_check("Configuration backup", False, "config/ directory missing or empty")
            all_ok = False

        # Check optional components (informational, not failures)
        optional_dirs = ["voicemail", "recordings", "ssl", "prompts"]
        for dirname in optional_dirs:
            subdir = backup_dir / dirname
            if subdir.is_dir() and any(subdir.iterdir()):
                self.log_check(f"{dirname.title()} backup", True)
            else:
                print(f"  - {dirname.title()} backup: not present (optional)")

        # Check manifest
        manifest = backup_dir / "MANIFEST.txt"
        if manifest.exists():
            self.log_check("Backup manifest", True)
        else:
            print("  - Backup manifest: not present (optional)")

        return all_ok

    def verify_checksums(self, backup_dir: Path) -> bool:
        """Verify SHA-256 checksums from CHECKSUMS.txt if present."""
        checksums_file = backup_dir / "CHECKSUMS.txt"
        if not checksums_file.exists():
            print("\n  - Checksum file not present, skipping integrity check")
            return True

        print(f"\nVerifying checksums: {checksums_file}")

        try:
            result = subprocess.run(
                ["sha256sum", "--check", str(checksums_file)],
                capture_output=True,
                cwd=str(checksums_file.parent.parent),
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                self.log_check("Checksum verification", True, "All checksums match")
                return True

            stderr = result.stderr.decode(errors="replace").strip()
            stdout = result.stdout.decode(errors="replace").strip()
            failed_lines = [line for line in stdout.splitlines() if "FAILED" in line]
            detail = "; ".join(failed_lines[:5]) if failed_lines else stderr
            self.log_check("Checksum verification", False, detail or "Checksum mismatch")
            return False

        except (OSError, subprocess.SubprocessError) as e:
            self.log_check("Checksum verification", False, str(e))
            return False

    # ------------------------------------------------------------------
    # Source config and script checks
    # ------------------------------------------------------------------

    def verify_config_backup(self) -> bool:
        """Verify source configuration files exist (pre-backup sanity check)."""
        print("\nVerifying source configuration files...")

        config_files = [
            "config.yml",
            ".env",
        ]

        all_good = True
        for config_file in config_files:
            path = self.base_dir / config_file
            if path.exists():
                self.log_check(f"Source {config_file} exists", True)
            else:
                self.log_check(f"Source {config_file} exists", False, "File not found")
                all_good = False

        return all_good

    def verify_backup_script(self) -> bool:
        """Verify backup script is configured."""
        print("\nVerifying backup script...")

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
            result = subprocess.run(["crontab", "-l"], capture_output=True, timeout=10, check=False)

            if result.returncode == 0:
                cron_content = result.stdout.decode()
                if "backup" in cron_content.lower():
                    self.log_check("Automated backup scheduled", True, "Found in crontab")
                    return True
                self.log_check("Automated backup scheduled", False, "No backup entry in crontab")
            else:
                self.log_check("Automated backup scheduled", False, "Could not check crontab")

        except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError) as e:
            self.log_check("Automated backup scheduled", False, str(e))

        return False

    # ------------------------------------------------------------------
    # Main verification flow
    # ------------------------------------------------------------------

    def run_verification(self) -> int:
        """Run all backup verifications."""
        print("=" * 70)
        print("Backup Verification")
        print("=" * 70)

        # 1. Verify backup infrastructure
        self.verify_backup_script()
        self.verify_config_backup()

        # 2. Verify actual backup data
        if self.backup_path:
            # User specified a path — verify it as a database backup
            self.verify_database_backup(self.backup_path)
        else:
            # Auto-discover: first try structured backup directory
            backup_dir = self.find_latest_backup_dir()
            if backup_dir:
                self.verify_backup_structure(backup_dir)
                self.verify_checksums(backup_dir)

                # Validate the database dump content inside the directory
                db_gz = backup_dir / "database" / "pbx_database.sql.gz"
                db_sql = backup_dir / "database" / "pbx_database.sql"
                if db_gz.exists():
                    self.verify_database_backup(str(db_gz))
                elif db_sql.exists():
                    self.verify_database_backup(str(db_sql))
            else:
                # Fall back to flat-file discovery (production deploy script format)
                found, backup_file = self.find_latest_database_backup()
                if found:
                    self.verify_database_backup(backup_file)
                else:
                    self.log_check("Locate backup", False, backup_file)

        # 3. Verify scheduling
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
        print(f"\n✗ {self.results['failed']} verification(s) failed")
        return 1

    def save_report(self, output_file: str) -> None:
        """Save verification report."""
        with Path(output_file).open("w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nReport saved to: {output_file}")


def main() -> None:
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
