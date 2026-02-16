"""
Recording Retention Policies
Automated management of call recording retention and cleanup
"""

from datetime import UTC, datetime
from pathlib import Path

from pbx.utils.logger import get_logger


class RecordingRetentionManager:
    """Manager for call recording retention policies"""

    def __init__(self, config=None):
        """Initialize retention manager"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        retention_config = self.config.get("features", {}).get("recording_retention", {})
        self.enabled = retention_config.get("enabled", False)
        self.recording_path = retention_config.get("recording_path", "recordings")

        # Default retention policies (in days)
        self.default_retention = retention_config.get("default_retention_days", 90)
        self.critical_retention = retention_config.get("critical_retention_days", 365)
        self.compliance_retention = retention_config.get(
            "compliance_retention_days", 2555
        )  # 7 years

        # Policy rules
        self.retention_policies = {}  # policy_name -> policy
        self.recording_tags = {}  # recording_id -> tags

        # Statistics
        self.last_cleanup = None
        self.deleted_count = 0
        self.archived_count = 0

        if self.enabled:
            self.logger.info("Recording retention manager initialized")
            self.logger.info(f"  Default retention: {self.default_retention} days")
            self.logger.info(f"  Critical retention: {self.critical_retention} days")
            self.logger.info(f"  Compliance retention: {self.compliance_retention} days")
            self._load_policies()

    def _load_policies(self):
        """Load retention policies from config"""
        policies = (
            self.config.get("features", {}).get("recording_retention", {}).get("policies", [])
        )
        for policy in policies:
            self.add_policy(policy)

    def add_policy(self, policy: dict) -> str:
        """
        Add a retention policy

        Args:
            policy: Policy configuration
                Required: name, retention_days
                Optional: tags, extensions, queues

        Returns:
            Policy ID
        """
        if not self.enabled:
            return ""

        policy_id = policy.get("name", f"policy_{len(self.retention_policies)}")
        self.retention_policies[policy_id] = {**policy, "created_at": datetime.now(UTC)}

        self.logger.info(f"Added retention policy: {policy_id} ({policy['retention_days']} days)")
        return policy_id

    def tag_recording(self, recording_id: str, tags: list[str]) -> bool:
        """
        Tag a recording for special handling

        Args:
            recording_id: Recording identifier
            tags: list of tags (e.g., 'critical', 'compliance', 'training')

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        if recording_id not in self.recording_tags:
            self.recording_tags[recording_id] = set()

        self.recording_tags[recording_id].update(tags)
        self.logger.info(f"Tagged recording {recording_id}: {tags}")
        return True

    def get_retention_period(
        self,
        recording_id: str,
        recording_date: datetime,
        extension: str | None = None,
        queue: str | None = None,
    ) -> int:
        """
        Get retention period for a recording

        Args:
            recording_id: Recording identifier
            recording_date: Recording date
            extension: Extension involved (optional)
            queue: Queue involved (optional)

        Returns:
            Retention period in days
        """
        if not self.enabled:
            return self.default_retention

        # Check tags
        tags = self.recording_tags.get(recording_id, set())

        if "compliance" in tags or "legal" in tags:
            return self.compliance_retention

        if "critical" in tags or "important" in tags:
            return self.critical_retention

        # Check policies
        for policy in self.retention_policies.values():
            # Check extension match
            if "extensions" in policy and extension in policy["extensions"]:
                return policy["retention_days"]

            # Check queue match
            if "queues" in policy and queue in policy["queues"]:
                return policy["retention_days"]

            # Check tag match
            if "tags" in policy and any(tag in tags for tag in policy["tags"]):
                return policy["retention_days"]

        return self.default_retention

    def scan_recordings(self) -> dict:
        """
        Scan recording directory and categorize files

        Returns:
            Summary of recordings by status
        """
        if not self.enabled:
            return {"error": "Retention manager not enabled"}

        recording_dir = Path(self.recording_path)
        if not recording_dir.exists():
            return {"error": "Recording directory not found"}

        summary = {"total": 0, "to_keep": 0, "to_delete": 0, "to_archive": 0, "by_age": {}}

        now = datetime.now(UTC)

        for recording_file in recording_dir.glob("**/*.wav"):
            summary["total"] += 1

            # Get file age
            file_mtime = datetime.fromtimestamp(recording_file.stat().st_mtime, tz=UTC)
            age_days = (now - file_mtime).days

            # Categorize by age
            age_bracket = f"{(age_days // 30) * 30}-{((age_days // 30) + 1) * 30} days"
            summary["by_age"][age_bracket] = summary["by_age"].get(age_bracket, 0) + 1

            # Get retention period (using file name as recording_id)
            recording_id = recording_file.stem
            retention_days = self.get_retention_period(recording_id, file_mtime)

            if age_days > retention_days:
                summary["to_delete"] += 1
            elif age_days > (retention_days * 0.8):  # Within 20% of retention
                summary["to_archive"] += 1
            else:
                summary["to_keep"] += 1

        return summary

    def cleanup_old_recordings(self, dry_run: bool = True) -> dict:
        """
        Delete recordings past their retention period

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Cleanup summary
        """
        if not self.enabled:
            return {"error": "Retention manager not enabled"}

        recording_dir = Path(self.recording_path)
        if not recording_dir.exists():
            return {"error": "Recording directory not found"}

        deleted_files = []
        deleted_size = 0
        now = datetime.now(UTC)

        for recording_file in recording_dir.glob("**/*.wav"):
            # Get file age
            file_mtime = datetime.fromtimestamp(recording_file.stat().st_mtime, tz=UTC)
            age_days = (now - file_mtime).days

            # Get retention period
            recording_id = recording_file.stem
            retention_days = self.get_retention_period(recording_id, file_mtime)

            # Check if past retention
            if age_days > retention_days:
                file_size = recording_file.stat().st_size
                deleted_files.append(
                    {"file": str(recording_file), "age_days": age_days, "size": file_size}
                )
                deleted_size += file_size

                if not dry_run:
                    try:
                        recording_file.unlink()
                        self.deleted_count += 1
                    except PermissionError as e:
                        self.logger.error(f"Permission denied deleting {recording_file}: {e}")
                    except FileNotFoundError as e:
                        self.logger.error(
                            f"File not found (already deleted?) {recording_file}: {e}"
                        )
                    except OSError as e:
                        self.logger.error(f"Unexpected error deleting {recording_file}: {e}")

        if not dry_run:
            self.last_cleanup = now
            self.logger.info(
                f"Deleted {len(deleted_files)} recordings ({deleted_size / 1024 / 1024:.2f} MB)"
            )
        else:
            self.logger.info(
                f"Would delete {len(deleted_files)} recordings ({deleted_size / 1024 / 1024:.2f} MB)"
            )

        return {
            "dry_run": dry_run,
            "files_deleted": len(deleted_files),
            "space_freed_mb": deleted_size / 1024 / 1024,
            "files": deleted_files[:100],  # Limit to first 100
        }

    def archive_recordings(self, archive_path: str, age_days: int = 60) -> dict:
        """
        Archive recordings older than specified age

        Args:
            archive_path: Path to archive directory
            age_days: Age threshold for archiving

        Returns:
            Archive summary
        """
        if not self.enabled:
            return {"error": "Retention manager not enabled"}

        recording_dir = Path(self.recording_path)
        archive_dir = Path(archive_path)

        if not recording_dir.exists():
            return {"error": "Recording directory not found"}

        # Create archive directory
        archive_dir.mkdir(parents=True, exist_ok=True)

        archived_files = []
        archived_size = 0
        now = datetime.now(UTC)

        for recording_file in recording_dir.glob("**/*.wav"):
            file_mtime = datetime.fromtimestamp(recording_file.stat().st_mtime, tz=UTC)
            file_age = (now - file_mtime).days

            if file_age > age_days:
                # Move to archive
                archive_file = archive_dir / recording_file.relative_to(recording_dir)
                archive_file.parent.mkdir(parents=True, exist_ok=True)

                try:
                    recording_file.rename(archive_file)
                    file_size = archive_file.stat().st_size
                    archived_files.append(str(recording_file))
                    archived_size += file_size
                    self.archived_count += 1
                except (KeyError, TypeError, ValueError) as e:
                    self.logger.error(f"Error archiving {recording_file}: {e}")

        self.logger.info(f"Archived {len(archived_files)} recordings to {archive_path}")

        return {
            "files_archived": len(archived_files),
            "archive_size_mb": archived_size / 1024 / 1024,
            "archive_path": str(archive_dir),
        }

    def get_statistics(self) -> dict:
        """Get retention manager statistics"""
        scan_result = self.scan_recordings()

        return {
            "enabled": self.enabled,
            "policies": len(self.retention_policies),
            "tagged_recordings": len(self.recording_tags),
            "total_recordings": scan_result.get("total", 0),
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
            "lifetime_deleted": self.deleted_count,
            "lifetime_archived": self.archived_count,
        }
