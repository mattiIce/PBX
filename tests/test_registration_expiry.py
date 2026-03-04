"""Tests for registration expiration enforcement."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.extensions import Extension, ExtensionRegistry


@pytest.mark.unit
class TestExtensionExpiration:
    """Tests for Extension.is_expired() and expiration tracking."""

    def test_register_sets_expires_at(self) -> None:
        ext = Extension("1001", "Test", {})
        ext.register(("10.0.0.1", 5060), expires=3600)

        assert ext.registered is True
        assert ext.expires_at is not None
        assert ext.expires_at > datetime.now(UTC)

    def test_register_with_custom_expires(self) -> None:
        ext = Extension("1001", "Test", {})
        ext.register(("10.0.0.1", 5060), expires=120)

        expected_min = datetime.now(UTC) + timedelta(seconds=119)
        expected_max = datetime.now(UTC) + timedelta(seconds=121)
        assert expected_min < ext.expires_at < expected_max

    def test_is_expired_returns_false_before_expiry(self) -> None:
        ext = Extension("1001", "Test", {})
        ext.register(("10.0.0.1", 5060), expires=3600)

        assert ext.is_expired() is False

    def test_is_expired_returns_true_after_expiry(self) -> None:
        ext = Extension("1001", "Test", {})
        ext.register(("10.0.0.1", 5060), expires=3600)
        # Manually set expires_at to the past
        ext.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        assert ext.is_expired() is True

    def test_is_expired_returns_true_when_not_registered(self) -> None:
        ext = Extension("1001", "Test", {})
        assert ext.is_expired() is True

    def test_unregister_clears_expires_at(self) -> None:
        ext = Extension("1001", "Test", {})
        ext.register(("10.0.0.1", 5060), expires=3600)
        ext.unregister()

        assert ext.expires_at is None
        assert ext.registered is False

    def test_re_register_updates_expires_at(self) -> None:
        ext = Extension("1001", "Test", {})
        ext.register(("10.0.0.1", 5060), expires=60)
        first_expires = ext.expires_at

        ext.register(("10.0.0.2", 5060), expires=7200)
        assert ext.expires_at > first_expires
        assert ext.address == ("10.0.0.2", 5060)


@pytest.mark.unit
class TestExtensionRegistryExpires:
    """Tests for ExtensionRegistry passing expires through."""

    def test_register_passes_expires(self) -> None:
        config = MagicMock()
        config.get.return_value = False
        registry = ExtensionRegistry(config)

        ext = Extension("1001", "Test", {})
        registry.extensions["1001"] = ext

        result = registry.register("1001", ("10.0.0.1", 5060), expires=1800)

        assert result is True
        assert ext.registered is True
        assert ext.expires_at is not None
        expected = datetime.now(UTC) + timedelta(seconds=1799)
        assert ext.expires_at > expected

    def test_register_default_expires(self) -> None:
        config = MagicMock()
        config.get.return_value = False
        registry = ExtensionRegistry(config)

        ext = Extension("1001", "Test", {})
        registry.extensions["1001"] = ext

        result = registry.register("1001", ("10.0.0.1", 5060))

        assert result is True
        expected = datetime.now(UTC) + timedelta(seconds=3599)
        assert ext.expires_at > expected
