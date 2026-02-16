"""
Test Find Me/Follow Me database persistence
"""

import tempfile
from pathlib import Path

from pbx.features.find_me_follow_me import FindMeFollowMe
from pbx.utils.database import DatabaseBackend


class TestFMFMPersistence:
    """Test FMFM configuration persistence"""

    def setup_method(self) -> None:
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.config = {
            "database.type": "sqlite",
            "database.path": self.temp_db.name,
            "features": {"find_me_follow_me": {"enabled": True}},
        }

        self.database = DatabaseBackend(self.config)
        self.database.connect()

    def teardown_method(self) -> None:
        """Clean up test database"""
        if hasattr(self, "database") and self.database.connection:
            self.database.connection.close()
        if Path(self.temp_db.name).exists():
            Path(self.temp_db.name).unlink(missing_ok=True)

    def test_database_persistence(self) -> None:
        """Test that FMFM configs are saved and loaded from database"""
        # Create first instance and add config
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)

        config = {
            "mode": "sequential",
            "destinations": [
                {"number": "1001", "ring_time": 20},
                {"number": "1002", "ring_time": 15},
            ],
            "enabled": True,
            "no_answer_destination": "2000",
        }

        success = fmfm1.set_config("1000", config)
        assert success, "Config should be saved successfully"
        # Create second instance to verify persistence
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)

        loaded_config = fmfm2.get_config("1000")
        assert loaded_config is not None, "Config should be loaded from database"
        assert loaded_config["mode"] == "sequential"
        assert len(loaded_config["destinations"]) == 2
        assert loaded_config["destinations"][0]["number"] == "1001"
        assert loaded_config["no_answer_destination"] == "2000"

    def test_add_destination_persistence(self) -> None:
        """Test that adding destinations persists to database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)

        fmfm1.add_destination("1000", "1001", 20)
        fmfm1.add_destination("1000", "1002", 15)

        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)

        config = fmfm2.get_config("1000")
        assert config is not None
        assert len(config["destinations"]) == 2

    def test_remove_destination_persistence(self) -> None:
        """Test that removing destinations persists to database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)

        config = {
            "mode": "sequential",
            "destinations": [
                {"number": "1001", "ring_time": 20},
                {"number": "1002", "ring_time": 15},
            ],
            "enabled": True,
        }
        fmfm1.set_config("1000", config)

        # Remove a destination
        fmfm1.remove_destination("1000", "1001")

        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)

        loaded_config = fmfm2.get_config("1000")
        assert loaded_config is not None
        assert len(loaded_config["destinations"]) == 1
        assert loaded_config["destinations"][0]["number"] == "1002"

    def test_enable_disable_persistence(self) -> None:
        """Test that enable/disable persists to database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)

        config = {
            "mode": "sequential",
            "destinations": [{"number": "1001", "ring_time": 20}],
            "enabled": True,
        }
        fmfm1.set_config("1000", config)

        # Disable
        fmfm1.disable_fmfm("1000")

        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)

        loaded_config = fmfm2.get_config("1000")
        assert loaded_config is not None
        assert not loaded_config["enabled"]
        # Enable again
        fmfm2.enable_fmfm("1000")

        # Create third instance
        fmfm3 = FindMeFollowMe(config=self.config, database=self.database)

        loaded_config = fmfm3.get_config("1000")
        assert loaded_config["enabled"]

    def test_delete_config_persistence(self) -> None:
        """Test that delete removes config from database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)

        config = {
            "mode": "sequential",
            "destinations": [{"number": "1001", "ring_time": 20}],
            "enabled": True,
        }
        fmfm1.set_config("1000", config)

        # Verify it exists
        assert fmfm1.get_config("1000") is not None
        # Delete
        fmfm1.delete_config("1000")

        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)

        loaded_config = fmfm2.get_config("1000")
        assert loaded_config is None, "Config should be deleted from database"

    def test_simultaneous_mode_persistence(self) -> None:
        """Test that simultaneous mode configs persist correctly"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)

        config = {
            "mode": "simultaneous",
            "destinations": [
                {"number": "1001", "ring_time": 30},
                {"number": "1002", "ring_time": 30},
                {"number": "1003", "ring_time": 30},
            ],
            "enabled": True,
        }
        fmfm1.set_config("1000", config)

        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)

        loaded_config = fmfm2.get_config("1000")
        assert loaded_config is not None
        assert loaded_config["mode"] == "simultaneous"
        assert len(loaded_config["destinations"]) == 3
