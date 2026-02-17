"""Unit tests for pbx.features.extensions — Extension and ExtensionRegistry."""

from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestExtension:
    """Tests for the Extension data class."""

    def test_extension_creation(self):
        """Extension stores number, name, config and defaults."""
        from pbx.features.extensions import Extension

        cfg = {"email": "j@example.com", "allow_external": True}
        ext = Extension("1001", "John", cfg)

        assert ext.number == "1001"
        assert ext.name == "John"
        assert ext.config is cfg
        assert ext.registered is False
        assert ext.address is None
        assert ext.registration_time is None

    def test_extension_register_unregister(self):
        """register/unregister toggle registration state."""
        from pbx.features.extensions import Extension

        ext = Extension("1001", "John", {})
        ext.register(("192.168.1.1", 5060))

        assert ext.registered is True
        assert ext.address == ("192.168.1.1", 5060)
        assert ext.registration_time is not None
        assert ext.registration_time.tzinfo is not None  # UTC-aware

        ext.unregister()

        assert ext.registered is False
        assert ext.address is None
        assert ext.registration_time is None

    def test_extension_str(self):
        """__str__ shows registration status."""
        from pbx.features.extensions import Extension

        ext = Extension("1001", "John", {})
        assert "unregistered" in str(ext)

        ext.register(("127.0.0.1", 5060))
        assert "registered" in str(ext)


@pytest.mark.unit
@patch("pbx.features.extensions.get_logger", return_value=MagicMock())
@patch("pbx.features.extensions.get_encryption", return_value=MagicMock())
class TestExtensionRegistry:
    """Tests for ExtensionRegistry."""

    def _make_registry(self, mock_enc, mock_logger):
        """Helper to create a registry with _load_extensions patched out."""
        with patch.object(
            __import__("pbx.features.extensions", fromlist=["ExtensionRegistry"]).ExtensionRegistry,
            "_load_extensions",
        ):
            from pbx.features.extensions import ExtensionRegistry

            config = MagicMock()
            config.get.return_value = False
            registry = ExtensionRegistry(config, database=None)
        return registry

    def test_registry_get(self, mock_enc, mock_logger):
        """get() returns extension by number or None."""
        from pbx.features.extensions import Extension

        registry = self._make_registry(mock_enc, mock_logger)
        ext = Extension("1001", "Alice", {})
        registry.extensions["1001"] = ext

        assert registry.get("1001") is ext
        assert registry.get("9999") is None

    def test_registry_register_unregister(self, mock_enc, mock_logger):
        """register/unregister through the registry."""
        from pbx.features.extensions import Extension

        registry = self._make_registry(mock_enc, mock_logger)
        registry.extensions["1001"] = Extension("1001", "Alice", {})

        assert registry.register("1001", ("10.0.0.1", 5060)) is True
        assert registry.extensions["1001"].registered is True

        assert registry.register("9999", ("10.0.0.1", 5060)) is False

        assert registry.unregister("1001") is True
        assert registry.extensions["1001"].registered is False

    def test_registry_get_registered(self, mock_enc, mock_logger):
        """get_registered/get_registered_count reflect registration state."""
        from pbx.features.extensions import Extension

        registry = self._make_registry(mock_enc, mock_logger)
        for num in ("1001", "1002", "1003"):
            registry.extensions[num] = Extension(num, f"User {num}", {})

        registry.extensions["1001"].register(("10.0.0.1", 5060))
        registry.extensions["1003"].register(("10.0.0.3", 5060))

        assert len(registry.get_registered()) == 2
        assert registry.get_registered_count() == 2

    def test_create_extension_from_db(self, mock_enc, mock_logger):
        """create_extension_from_db converts SQLite 0/1 to booleans."""
        from pbx.features.extensions import ExtensionRegistry

        db_data = {
            "number": "2001",
            "name": "Bob",
            "email": "bob@example.com",
            "password_hash": "hash123",
            "allow_external": 1,
            "voicemail_pin_hash": "pin_hash",
            "ad_synced": 0,
            "is_admin": 0,
        }

        ext = ExtensionRegistry.create_extension_from_db(db_data)

        assert ext.number == "2001"
        assert ext.name == "Bob"
        assert ext.config["allow_external"] is True
        assert ext.config["ad_synced"] is False
        assert ext.config["is_admin"] is False
