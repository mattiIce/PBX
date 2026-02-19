"""
Data Residency Controls
Geographic data storage options for compliance
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pbx.utils.logger import get_logger


class StorageRegion(Enum):
    """Storage region enumeration"""

    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    EU_CENTRAL = "eu-central"
    ASIA_PACIFIC = "asia-pacific"
    CANADA = "canada"
    UK = "uk"


class DataCategory(Enum):
    """Data category for residency"""

    CALL_RECORDINGS = "call_recordings"
    VOICEMAIL = "voicemail"
    CDR = "cdr"
    USER_DATA = "user_data"
    SYSTEM_LOGS = "system_logs"
    CONFIGURATION = "configuration"


class DataResidencyControls:
    """
    Data Residency Controls

    Geographic data storage management for compliance (GDPR, etc.).
    Features:
    - Region-specific data storage
    - Data classification
    - Cross-border transfer controls
    - Compliance reporting
    - Data localization enforcement
    """

    def __init__(self, config: Any | None = None) -> None:
        """Initialize data residency controls"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        residency_config = self.config.get("features", {}).get("data_residency", {})
        self.enabled = residency_config.get("enabled", False)
        self.default_region = StorageRegion(residency_config.get("default_region", "us-east"))
        self.strict_mode = residency_config.get("strict_mode", False)

        # Region configurations
        self.region_configs: dict[str, dict] = {}
        self._initialize_default_regions()

        # Data category mappings
        self.category_regions: dict[DataCategory, StorageRegion] = {}

        # Statistics
        self.total_storage_operations = 0
        self.blocked_operations = 0
        self.cross_region_transfers = 0

        self.logger.info("Data residency controls initialized")
        self.logger.info(f"  Default region: {self.default_region.value}")
        self.logger.info(f"  Strict mode: {self.strict_mode}")
        self.logger.info(f"  Enabled: {self.enabled}")

    def _initialize_default_regions(self) -> None:
        """Initialize default region configurations"""
        regions = [
            ("us-east", "US East", "/var/pbx/data/us-east"),
            ("us-west", "US West", "/var/pbx/data/us-west"),
            ("eu-west", "EU West", "/var/pbx/data/eu-west"),
            ("eu-central", "EU Central", "/var/pbx/data/eu-central"),
        ]

        for region_id, name, path in regions:
            self.region_configs[region_id] = {
                "name": name,
                "storage_path": path,
                "database_server": None,
                "compliance_tags": [],
            }

    def configure_region(self, region: str, config: dict) -> bool:
        """
        Configure storage region

        Args:
            region: Region identifier
            config: Region configuration
        """
        if not self.enabled:
            self.logger.error(
                "Cannot configure region: Data residency controls feature is not enabled"
            )
            return False

        self.region_configs[region] = config

        self.logger.info(f"Configured region: {region}")
        self.logger.info(f"  Storage path: {config.get('storage_path')}")
        self.logger.info(f"  Database: {config.get('database_server')}")
        return True

    def set_category_region(self, category: DataCategory, region: StorageRegion) -> bool:
        """
        set storage region for data category

        Args:
            category: Data category
            region: Storage region
        """
        if not self.enabled:
            self.logger.error(
                "Cannot set category region: Data residency controls feature is not enabled"
            )
            return False

        self.category_regions[category] = region

        self.logger.info(f"set {category.value} to store in {region.value}")
        return True

    def get_storage_location(self, category: str, user_region: str | None = None) -> dict:
        """
        Get storage location for data

        Args:
            category: Data category
            user_region: User's region (for user-specific data)

        Returns:
            dict: Storage location information
        """
        data_category = DataCategory(category)

        # Determine region
        if data_category in self.category_regions:
            region = self.category_regions[data_category]
        elif user_region:
            region = StorageRegion(user_region)
        else:
            region = self.default_region

        region_config = self.region_configs.get(region.value, {})

        return {
            "region": region.value,
            "storage_path": region_config.get("storage_path"),
            "database_server": region_config.get("database_server"),
            "compliance_tags": region_config.get("compliance_tags", []),
        }

    def validate_storage_operation(
        self, category: str, target_region: str, user_region: str | None = None
    ) -> dict:
        """
        Validate if storage operation is allowed

        Args:
            category: Data category
            target_region: Target storage region
            user_region: User's region

        Returns:
            dict: Validation result
        """
        self.total_storage_operations += 1

        # In strict mode, enforce data residency
        if self.strict_mode and user_region and target_region != user_region:
            self.blocked_operations += 1
            return {
                "allowed": False,
                "reason": "Cross-region storage not allowed in strict mode",
            }

        # Check for EU data protection rules
        if user_region in ["eu-west", "eu-central", "uk"] and target_region not in [
            "eu-west",
            "eu-central",
            "uk",
        ]:
            self.blocked_operations += 1
            return {"allowed": False, "reason": "EU data cannot be stored outside EU (GDPR)"}

        return {"allowed": True}

    def transfer_data_between_regions(
        self,
        data_id: str,
        category: str,
        from_region: str,
        to_region: str,
        justification: str | None = None,
    ) -> dict:
        """
        Transfer data between regions

        Args:
            data_id: Data identifier
            category: Data category
            from_region: Source region
            to_region: Destination region
            justification: Transfer justification

        Returns:
            dict: Transfer result
        """
        # Validate transfer
        validation = self.validate_storage_operation(category, to_region)

        if not validation["allowed"]:
            return {"success": False, "error": validation["reason"]}

        # Implement actual data transfer between regions
        try:
            from pbx.utils.database import get_database

            db = get_database()

            if db and db.enabled and db.connection:
                self.logger.info(f"Executing data transfer: {data_id}")
                self.logger.info(f"  From: {from_region} -> To: {to_region}")
                self.logger.info(f"  Category: {category}")

                # Resolve source and destination storage paths from region configs
                source_config = self.region_configs.get(from_region, {})
                dest_config = self.region_configs.get(to_region, {})

                source_base = source_config.get("storage_path")
                dest_base = dest_config.get("storage_path")

                if not source_base or not dest_base:
                    self.logger.error(
                        f"Missing storage path: source={source_base}, dest={dest_base}"
                    )
                    transfer_successful = False
                else:
                    import shutil
                    from pathlib import Path

                    source_dir = Path(source_base) / category
                    dest_dir = Path(dest_base) / category

                    # Ensure destination directory exists
                    dest_dir.mkdir(parents=True, exist_ok=True)

                    # Copy files matching the data_id from source to destination
                    source_files = (
                        list(source_dir.glob(f"{data_id}*")) if source_dir.exists() else []
                    )

                    if source_files:
                        for source_file in source_files:
                            dest_file = dest_dir / source_file.name
                            shutil.copy2(source_file, dest_file)
                            self.logger.info(f"  Copied: {source_file} -> {dest_file}")
                    else:
                        # No files on disk; fall back to database record transfer
                        self.logger.info(
                            f"  No files found at {source_dir} for {data_id}, "
                            "transferring database records"
                        )

                    # Transfer database records between regions
                    try:
                        placeholder = "%s"

                        # Read the record from the source region table
                        select_query = (
                            f"SELECT * FROM data_residency_records "  # nosec B608
                            f"WHERE data_id = {placeholder} AND region = {placeholder}"
                        )
                        record = db.fetch_one(select_query, (data_id, from_region))

                        if record:
                            # Insert or update in destination region
                            upsert_query = (
                                f"INSERT INTO data_residency_records "  # nosec B608
                                f"(data_id, category, region, transferred_at) "
                                f"VALUES ({placeholder}, {placeholder}, "
                                f"{placeholder}, {placeholder})"
                            )
                            db.execute(
                                upsert_query,
                                (data_id, category, to_region, datetime.now(UTC).isoformat()),
                            )
                            self.logger.info(f"  Database record transferred to {to_region}")
                    except Exception as db_err:
                        self.logger.warning(f"  Database record transfer skipped: {db_err}")

                    transfer_successful = True
            else:
                self.logger.warning("Database not available for data transfer")
                transfer_successful = False
        except Exception as e:
            self.logger.error(f"Data transfer failed: {e}")
            transfer_successful = False

        if not transfer_successful:
            return {"success": False, "error": "Data transfer operation failed"}

        self.cross_region_transfers += 1

        # Log transfer for compliance
        transfer_log = {
            "data_id": data_id,
            "category": category,
            "from_region": from_region,
            "to_region": to_region,
            "justification": justification,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "completed",
        }

        # Store transfer log
        if not hasattr(self, "transfer_history"):
            self.transfer_history = []
        self.transfer_history.append(transfer_log)

        self.logger.info(f"Data transfer completed: {from_region} -> {to_region}")
        self.logger.info(f"  Category: {category}")
        self.logger.info(f"  Justification: {justification}")

        return {"success": True, "transfer_log": transfer_log}

    def get_compliance_report(self, start_date: datetime, end_date: datetime) -> dict:
        """
        Generate compliance report

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            dict: Compliance report
        """
        # Query actual storage operations and transfers from history

        # Initialize transfer history if not present
        if not hasattr(self, "transfer_history"):
            self.transfer_history = []

        # Filter transfers within date range
        transfers_in_period = [
            t
            for t in self.transfer_history
            if start_date <= datetime.fromisoformat(t["timestamp"]) <= end_date
        ]

        # Aggregate by region
        transfers_by_region = {}
        for transfer in transfers_in_period:
            from_region = transfer["from_region"]
            to_region = transfer["to_region"]

            if from_region not in transfers_by_region:
                transfers_by_region[from_region] = {"outbound": 0, "inbound": 0}
            if to_region not in transfers_by_region:
                transfers_by_region[to_region] = {"outbound": 0, "inbound": 0}

            transfers_by_region[from_region]["outbound"] += 1
            transfers_by_region[to_region]["inbound"] += 1

        # Aggregate by category
        transfers_by_category = {}
        for transfer in transfers_in_period:
            category = transfer["category"]
            transfers_by_category[category] = transfers_by_category.get(category, 0) + 1

        report = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_operations": self.total_storage_operations,
                "blocked_operations": self.blocked_operations,
                "cross_region_transfers": len(transfers_in_period),
                "total_all_time_transfers": self.cross_region_transfers,
            },
            "by_region": transfers_by_region,
            "by_category": transfers_by_category,
            "transfers": transfers_in_period,
            "compliance_status": "compliant",
        }

        return report

    def get_data_location_map(self) -> dict:
        """Get map of where data is stored"""
        location_map = {}

        for category, region in self.category_regions.items():
            location_map[category.value] = {
                "region": region.value,
                "config": self.region_configs.get(region.value, {}),
            }

        return location_map

    def get_statistics(self) -> dict:
        """Get data residency statistics"""
        return {
            "enabled": self.enabled,
            "default_region": self.default_region.value,
            "strict_mode": self.strict_mode,
            "configured_regions": len(self.region_configs),
            "category_mappings": len(self.category_regions),
            "total_storage_operations": self.total_storage_operations,
            "blocked_operations": self.blocked_operations,
            "cross_region_transfers": self.cross_region_transfers,
        }


# Global instance
_data_residency = None


def get_data_residency(config: Any | None = None) -> DataResidencyControls:
    """Get or create data residency controls instance"""
    global _data_residency
    if _data_residency is None:
        _data_residency = DataResidencyControls(config)
    return _data_residency
