"""
Find Me/Follow Me Call Routing
Ring multiple devices sequentially or simultaneously
"""

import json
from datetime import datetime

from pbx.utils.logger import get_logger


class FindMeFollowMe:
    """Find Me/Follow Me call routing system"""

    def __init__(self, config=None, database=None):
        """Initialize Find Me/Follow Me"""
        self.logger = get_logger()
        self.config = config or {}
        self.database = database
        self.enabled = (
            self.config.get("features", {}).get("find_me_follow_me", {}).get("enabled", False)
        )

        # User configurations
        self.user_configs = {}  # extension -> FMFM config

        # Initialize database schema if database is available
        if self.database and self.database.enabled:
            self._initialize_schema()

        if self.enabled:
            self.logger.info("Find Me/Follow Me system initialized")
            self._load_configs()

    def _initialize_schema(self):
        """Initialize database schema for FMFM"""
        if not self.database or not self.database.enabled:
            return

        # FMFM configurations table
        # Boolean default value varies by database type
        bool_default = "TRUE" if self.database.db_type == "postgresql" else "1"
        fmfm_table = f"""
        CREATE TABLE IF NOT EXISTS fmfm_configs (
            extension VARCHAR(20) PRIMARY KEY,
            mode VARCHAR(20) NOT NULL CHECK (mode IN ('sequential', 'simultaneous')),
            enabled BOOLEAN DEFAULT {bool_default},
            destinations TEXT NOT NULL,
            no_answer_destination VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        try:
            cursor = self.database.connection.cursor()
            cursor.execute(fmfm_table)
            self.database.connection.commit()
            cursor.close()
            self.logger.debug("FMFM database schema initialized")
        except Exception as e:
            self.logger.error(f"Error initializing FMFM schema: {e}")

    def _load_configs(self):
        """Load FMFM configurations from database or config file"""
        # First try to load from database
        if self.database and self.database.enabled:
            self._load_from_database()

        # Also load from config file (for backward compatibility)
        configs = self.config.get("features", {}).get("find_me_follow_me", {}).get("users", [])
        for cfg in configs:
            # Only add if not already in database
            if cfg["extension"] not in self.user_configs:
                self.user_configs[cfg["extension"]] = cfg

    def _load_from_database(self):
        """Load FMFM configurations from database"""
        if not self.database or not self.database.enabled:
            return

        try:
            cursor = self.database.connection.cursor()
            cursor.execute("""
                SELECT extension, mode, enabled, destinations, no_answer_destination, updated_at
                FROM fmfm_configs
            """)

            rows = cursor.fetchall()
            for row in rows:
                extension, mode, enabled, destinations_json, no_answer, updated_at = row

                # Parse destinations from JSON
                try:
                    destinations = json.loads(destinations_json)
                except json.JSONDecodeError:
                    self.logger.warning(
                        f"Invalid JSON in destinations for extension {extension}, skipping"
                    )
                    destinations = []

                config = {
                    "extension": extension,
                    "mode": mode,
                    "enabled": bool(enabled),
                    "destinations": destinations,
                    "updated_at": updated_at,
                }

                if no_answer:
                    config["no_answer_destination"] = no_answer

                self.user_configs[extension] = config

            cursor.close()
            self.logger.info(f"Loaded {len(rows)} FMFM configurations from database")
        except Exception as e:
            self.logger.error(f"Error loading FMFM configs from database: {e}")

    def _save_to_database(self, extension: str):
        """
        Save FMFM configuration to database

        Note: Uses SQL CURRENT_TIMESTAMP for updated_at field instead of
        datetime.now() to ensure compatibility between PostgreSQL and SQLite,
        and to avoid timezone and datetime adapter issues.
        """
        if not self.database or not self.database.enabled:
            return False

        if extension not in self.user_configs:
            return False

        config = self.user_configs[extension]

        try:
            cursor = self.database.connection.cursor()

            # Convert destinations to JSON
            destinations_json = json.dumps(config.get("destinations", []))

            # Upsert (insert or update)
            if self.database.db_type == "postgresql":
                cursor.execute(
                    """
                    INSERT INTO fmfm_configs (extension, mode, enabled, destinations, no_answer_destination, updated_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (extension) DO UPDATE SET
                        mode = EXCLUDED.mode,
                        enabled = EXCLUDED.enabled,
                        destinations = EXCLUDED.destinations,
                        no_answer_destination = EXCLUDED.no_answer_destination,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        extension,
                        config.get("mode", "sequential"),
                        config.get("enabled", True),
                        destinations_json,
                        config.get("no_answer_destination"),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO fmfm_configs (extension, mode, enabled, destinations, no_answer_destination, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        extension,
                        config.get("mode", "sequential"),
                        1 if config.get("enabled", True) else 0,
                        destinations_json,
                        config.get("no_answer_destination"),
                    ),
                )

            self.database.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.logger.error(f"Error saving FMFM config to database: {e}")
            return False

    def _delete_from_database(self, extension: str):
        """Delete FMFM configuration from database"""
        if not self.database or not self.database.enabled:
            return False

        try:
            cursor = self.database.connection.cursor()

            if self.database.db_type == "postgresql":
                cursor.execute("DELETE FROM fmfm_configs WHERE extension = %s", (extension,))
            else:
                cursor.execute("DELETE FROM fmfm_configs WHERE extension = ?", (extension,))

            self.database.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.logger.error(f"Error deleting FMFM config from database: {e}")
            return False

    def set_config(self, extension: str, config: dict) -> bool:
        """
        set Find Me/Follow Me configuration for an extension

        Args:
            extension: Extension number
            config: FMFM configuration
                Required: mode ('sequential' or 'simultaneous')
                Required: destinations (list of numbers with ring_time)
                Optional: enabled, no_answer_destination

        Returns:
            True if successful
        """
        if not self.enabled:
            self.logger.error(
                f"Cannot set FMFM config for {extension}: Find Me/Follow Me feature is not enabled globally"
            )
            return False

        required_fields = ["mode", "destinations"]
        if not all(field in config for field in required_fields):
            self.logger.error(f"Missing required FMFM fields for {extension}")
            return False

        if config["mode"] not in ["sequential", "simultaneous"]:
            self.logger.error(f"Invalid FMFM mode: {config['mode']}")
            return False

        self.user_configs[extension] = {**config, "extension": extension}

        # Add timestamp only if no database (otherwise database generates it)
        if not (self.database and self.database.enabled):
            self.user_configs[extension]["updated_at"] = datetime.now()

        # Save to database if one is configured
        if self.database and self.database.enabled:
            save_result = self._save_to_database(extension)
            if not save_result:
                # Remove from memory if database save failed
                del self.user_configs[extension]
                self.logger.error(f"Failed to save FMFM config to database for {extension}")
                return False

        self.logger.info(
            f"set FMFM config for {extension}: {config['mode']} mode with {len(config['destinations'])} destinations"
        )
        return True

    def get_config(self, extension: str) -> dict | None:
        """Get FMFM configuration for an extension"""
        return self.user_configs.get(extension)

    def get_ring_strategy(self, extension: str, call_id: str) -> dict:
        """
        Get ringing strategy for a call

        Args:
            extension: Called extension
            call_id: Call identifier

        Returns:
            Ring strategy information
        """
        if not self.enabled:
            return {"strategy": "normal", "destinations": [extension]}

        config = self.get_config(extension)
        if not config or not config.get("enabled", True):
            return {"strategy": "normal", "destinations": [extension]}

        mode = config["mode"]
        destinations = config["destinations"]

        if mode == "sequential":
            # Ring destinations one at a time
            ring_plan = []
            for dest in destinations:
                ring_plan.append(
                    {
                        "destination": dest["number"],
                        "ring_time": dest.get("ring_time", 20),
                        "order": "sequential",
                    }
                )

            return {
                "strategy": "sequential",
                "destinations": ring_plan,
                "no_answer_destination": config.get("no_answer_destination"),
                "call_id": call_id,
            }

        elif mode == "simultaneous":
            # Ring all destinations at once
            ring_plan = []
            max_ring_time = 0
            for dest in destinations:
                ring_time = dest.get("ring_time", 30)
                ring_plan.append({"destination": dest["number"], "ring_time": ring_time})
                max_ring_time = max(max_ring_time, ring_time)

            return {
                "strategy": "simultaneous",
                "destinations": ring_plan,
                "max_ring_time": max_ring_time,
                "no_answer_destination": config.get("no_answer_destination"),
                "call_id": call_id,
            }

        return {"strategy": "normal", "destinations": [extension]}

    def add_destination(self, extension: str, number: str, ring_time: int = 20) -> bool:
        """Add a destination to an extension's FMFM list"""
        if extension not in self.user_configs:
            # Create new config
            self.user_configs[extension] = {
                "extension": extension,
                "mode": "sequential",
                "destinations": [],
                "enabled": True,
            }

        config = self.user_configs[extension]
        original_destinations = config["destinations"].copy()
        config["destinations"].append({"number": number, "ring_time": ring_time})

        # Save to database if one is configured
        if self.database and self.database.enabled:
            save_result = self._save_to_database(extension)
            if not save_result:
                # Revert the change if database save failed
                config["destinations"] = original_destinations
                self.logger.error(f"Failed to save FMFM config to database for {extension}")
                return False

        self.logger.info(f"Added FMFM destination for {extension}: {number}")
        return True

    def remove_destination(self, extension: str, number: str) -> bool:
        """Remove a destination from an extension's FMFM list"""
        if extension not in self.user_configs:
            return False

        config = self.user_configs[extension]
        original_destinations = config["destinations"].copy()
        original_count = len(config["destinations"])
        config["destinations"] = [d for d in config["destinations"] if d["number"] != number]

        removed = original_count - len(config["destinations"])
        if removed > 0:
            # Save to database if one is configured
            if self.database and self.database.enabled:
                save_result = self._save_to_database(extension)
                if not save_result:
                    # Revert the change if database save failed
                    config["destinations"] = original_destinations
                    self.logger.error(f"Failed to save FMFM config to database for {extension}")
                    return False

            self.logger.info(f"Removed {removed} FMFM destination(s) for {extension}: {number}")
            return True

        return False

    def enable_fmfm(self, extension: str) -> bool:
        """Enable FMFM for an extension"""
        if extension in self.user_configs:
            self.user_configs[extension]["enabled"] = True

            # Save to database if one is configured
            if self.database and self.database.enabled:
                save_result = self._save_to_database(extension)
                if not save_result:
                    # Revert the change if database save failed
                    self.user_configs[extension]["enabled"] = False
                    self.logger.error(f"Failed to save FMFM config to database for {extension}")
                    return False

            self.logger.info(f"Enabled FMFM for {extension}")
            return True
        return False

    def disable_fmfm(self, extension: str) -> bool:
        """Disable FMFM for an extension"""
        if extension in self.user_configs:
            self.user_configs[extension]["enabled"] = False

            # Save to database if one is configured
            if self.database and self.database.enabled:
                save_result = self._save_to_database(extension)
                if not save_result:
                    # Revert the change if database save failed
                    self.user_configs[extension]["enabled"] = True
                    self.logger.error(f"Failed to save FMFM config to database for {extension}")
                    return False

            self.logger.info(f"Disabled FMFM for {extension}")
            return True
        return False

    def delete_config(self, extension: str) -> bool:
        """Delete FMFM configuration for an extension"""
        if extension in self.user_configs:
            # Save a backup in case we need to restore
            backup_config = self.user_configs[extension].copy()
            del self.user_configs[extension]

            # Delete from database if one is configured
            if self.database and self.database.enabled:
                delete_result = self._delete_from_database(extension)
                if not delete_result:
                    # Restore from backup if database delete failed
                    self.user_configs[extension] = backup_config
                    self.logger.error(f"Failed to delete FMFM config from database for {extension}")
                    return False

            self.logger.info(f"Deleted FMFM config for {extension}")
            return True
        return False

    def list_extensions_with_fmfm(self) -> list[str]:
        """list extensions with FMFM configured"""
        return [ext for ext, cfg in self.user_configs.items() if cfg.get("enabled", True)]

    def get_statistics(self) -> dict:
        """Get FMFM statistics"""
        sequential_count = sum(
            1
            for cfg in self.user_configs.values()
            if cfg.get("mode") == "sequential" and cfg.get("enabled", True)
        )
        simultaneous_count = sum(
            1
            for cfg in self.user_configs.values()
            if cfg.get("mode") == "simultaneous" and cfg.get("enabled", True)
        )

        return {
            "enabled": self.enabled,
            "total_configs": len(self.user_configs),
            "sequential_configs": sequential_count,
            "simultaneous_configs": simultaneous_count,
        }
