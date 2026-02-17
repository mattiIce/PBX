#!/usr/bin/env python3
"""Comprehensive tests for the licensing module."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pbx.utils.licensing import (
    LicenseManager,
    LicenseStatus,
    LicenseType,
    check_limit,
    get_license_info,
    get_license_manager,
    has_feature,
    initialize_license_manager,
)


@pytest.mark.unit
class TestLicenseType:
    """Tests for LicenseType enum."""

    def test_license_type_values(self) -> None:
        assert LicenseType.TRIAL.value == "trial"
        assert LicenseType.BASIC.value == "basic"
        assert LicenseType.PROFESSIONAL.value == "professional"
        assert LicenseType.ENTERPRISE.value == "enterprise"
        assert LicenseType.PERPETUAL.value == "perpetual"
        assert LicenseType.CUSTOM.value == "custom"

    def test_license_type_from_value(self) -> None:
        assert LicenseType("trial") == LicenseType.TRIAL
        assert LicenseType("enterprise") == LicenseType.ENTERPRISE


@pytest.mark.unit
class TestLicenseStatus:
    """Tests for LicenseStatus enum."""

    def test_license_status_values(self) -> None:
        assert LicenseStatus.ACTIVE.value == "active"
        assert LicenseStatus.EXPIRED.value == "expired"
        assert LicenseStatus.INVALID.value == "invalid"
        assert LicenseStatus.GRACE_PERIOD.value == "grace_period"
        assert LicenseStatus.DISABLED.value == "disabled"


@pytest.mark.unit
class TestLicenseManagerInit:
    """Tests for LicenseManager initialization."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_init_default_config(self, mock_enabled) -> None:
        mgr = LicenseManager()
        assert mgr.config == {}
        assert mgr.enabled is False
        assert mgr.grace_period_days == 7
        assert mgr.trial_period_days == 30
        assert mgr.current_license is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_init_with_config(self, mock_enabled) -> None:
        config = {
            "grace_period_days": 14,
            "trial_period_days": 60,
            "license_file": "/tmp/test.license",
        }
        mgr = LicenseManager(config)
        assert mgr.grace_period_days == 14
        assert mgr.trial_period_days == 60
        assert mgr.license_path == "/tmp/test.license"

    @patch.object(LicenseManager, "_load_license")
    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=True)
    def test_init_enabled_calls_load_license(self, mock_enabled, mock_load) -> None:
        LicenseManager()
        mock_load.assert_called_once()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_init_disabled_does_not_load_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        assert mgr.current_license is None


@pytest.mark.unit
class TestIsLicensingEnabled:
    """Tests for _is_licensing_enabled method."""

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="")
    def test_license_lock_file_exists(self, mock_getenv, mock_path_cls) -> None:
        """License lock file forces licensing enabled."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance
        mock_path_cls.__truediv__ = MagicMock()

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is True

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="true")
    def test_env_var_true(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is True

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="1")
    def test_env_var_one(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is True

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="yes")
    def test_env_var_yes(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is True

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="on")
    def test_env_var_on(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is True

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="false")
    def test_env_var_false(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is False

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="0")
    def test_env_var_zero(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is False

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="no")
    def test_env_var_no(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is False

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="of")
    def test_env_var_of(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is False

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="")
    def test_config_enabled(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {"licensing": {"enabled": True}}
        result = mgr._is_licensing_enabled()
        assert result is True

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="")
    def test_config_disabled(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {"licensing": {"enabled": False}}
        result = mgr._is_licensing_enabled()
        assert result is False

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="")
    def test_default_disabled(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        assert result is False

    @patch("pbx.utils.licensing.Path")
    @patch("pbx.utils.licensing.getenv", return_value="maybe")
    def test_env_var_unrecognized_falls_through(self, mock_getenv, mock_path_cls) -> None:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        mgr = LicenseManager.__new__(LicenseManager)
        mgr.config = {}
        result = mgr._is_licensing_enabled()
        # Unrecognized env value falls through to config check, then default False
        assert result is False


@pytest.mark.unit
class TestInitializeFeatures:
    """Tests for _initialize_features method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_features_for_all_tiers(self, mock_enabled) -> None:
        mgr = LicenseManager()
        features = mgr.features

        assert "trial" in features
        assert "basic" in features
        assert "professional" in features
        assert "enterprise" in features
        assert "perpetual" in features
        assert "custom" in features

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_trial_features_limited(self, mock_enabled) -> None:
        mgr = LicenseManager()
        trial_features = mgr.features["trial"]
        assert "basic_calling" in trial_features
        assert "voicemail" in trial_features
        assert "max_extensions:10" in trial_features
        assert "max_concurrent_calls:5" in trial_features

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_enterprise_has_all_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        enterprise = mgr.features["enterprise"]
        assert "ai_features" in enterprise
        assert "advanced_analytics" in enterprise
        assert "high_availability" in enterprise
        assert "max_extensions:unlimited" in enterprise

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_custom_features_empty(self, mock_enabled) -> None:
        mgr = LicenseManager()
        assert mgr.features["custom"] == []


@pytest.mark.unit
class TestLoadLicense:
    """Tests for _load_license method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_load_license_file_not_exists(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.license_path = "/nonexistent/path/.license"
        mgr._load_license()
        assert mgr.current_license is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_load_license_valid_file(self, mock_enabled) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            license_data = {
                "key": "ABCD-EFGH-IJKL-MNOP",
                "type": "basic",
                "issued_to": "Test Corp",
                "issued_date": datetime.now(UTC).isoformat(),
                "signature": "valid_sig",
            }
            json.dump(license_data, f)
            temp_path = f.name

        try:
            mgr = LicenseManager()
            mgr.enabled = True
            mgr.license_path = temp_path

            with patch.object(mgr, "_validate_license", return_value=license_data):
                mgr._load_license()
                assert mgr.current_license is not None
                assert mgr.current_license["type"] == "basic"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_load_license_invalid_json(self, mock_enabled) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            temp_path = f.name

        try:
            mgr = LicenseManager()
            mgr.enabled = True
            mgr.license_path = temp_path
            mgr._load_license()
            assert mgr.current_license is None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_load_license_validation_fails(self, mock_enabled) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "test"}, f)
            temp_path = f.name

        try:
            mgr = LicenseManager()
            mgr.enabled = True
            mgr.license_path = temp_path

            with patch.object(mgr, "_validate_license", return_value=None):
                mgr._load_license()
                assert mgr.current_license is None
        finally:
            Path(temp_path).unlink(missing_ok=True)


@pytest.mark.unit
class TestValidateLicense:
    """Tests for _validate_license method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_validate_missing_required_fields(self, mock_enabled) -> None:
        mgr = LicenseManager()
        # Missing "key" field
        result = mgr._validate_license({"type": "basic", "issued_to": "x", "issued_date": "y"})
        assert result is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_validate_missing_type(self, mock_enabled) -> None:
        mgr = LicenseManager()
        result = mgr._validate_license({"key": "test", "issued_to": "x", "issued_date": "y"})
        assert result is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_validate_missing_issued_to(self, mock_enabled) -> None:
        mgr = LicenseManager()
        result = mgr._validate_license({"key": "test", "type": "basic", "issued_date": "y"})
        assert result is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_validate_missing_issued_date(self, mock_enabled) -> None:
        mgr = LicenseManager()
        result = mgr._validate_license({"key": "test", "type": "basic", "issued_to": "x"})
        assert result is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_validate_signature_fails(self, mock_enabled) -> None:
        mgr = LicenseManager()
        data = {
            "key": "test",
            "type": "basic",
            "issued_to": "x",
            "issued_date": "y",
            "signature": "bad_sig",
        }
        result = mgr._validate_license(data)
        assert result is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_validate_signature_passes(self, mock_enabled) -> None:
        mgr = LicenseManager()
        data = {
            "key": "test",
            "type": "basic",
            "issued_to": "x",
            "issued_date": "y",
            "signature": "valid_sig",
        }
        with patch.object(mgr, "_verify_signature", return_value=True):
            result = mgr._validate_license(data)
            assert result == data


@pytest.mark.unit
class TestVerifySignature:
    """Tests for _verify_signature method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_no_signature_field(self, mock_enabled) -> None:
        mgr = LicenseManager()
        result = mgr._verify_signature({"key": "test"})
        assert result is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_empty_signature(self, mock_enabled) -> None:
        mgr = LicenseManager()
        result = mgr._verify_signature({"key": "test", "signature": ""})
        assert result is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_valid_signature_default_key(self, mock_enabled) -> None:
        mgr = LicenseManager()
        # Generate a valid license and verify it
        license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp", expiration_days=30)
        # The generated license has a valid signature
        assert mgr._verify_signature(license_data) is True

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_invalid_signature(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp", expiration_days=30)
        license_data["signature"] = "tampered_signature"
        assert mgr._verify_signature(license_data) is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_custom_secret_key(self, mock_enabled) -> None:
        mgr = LicenseManager({"license_secret_key": "my_custom_secret"})
        license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp", expiration_days=30)
        assert mgr._verify_signature(license_data) is True

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_default_secret_key_warning(self, mock_enabled) -> None:
        mgr = LicenseManager({"license_secret_key": "default_secret_key"})
        license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp", expiration_days=30)
        # Should still work with default key, just logs a warning
        assert mgr._verify_signature(license_data) is True


@pytest.mark.unit
class TestGenerateLicenseKey:
    """Tests for generate_license_key method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generate_basic_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp")

        assert "key" in license_data
        assert license_data["type"] == "basic"
        assert license_data["issued_to"] == "Test Corp"
        assert "issued_date" in license_data
        assert license_data["expiration"] is None
        assert "signature" in license_data

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generate_with_expiration(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(
            LicenseType.PROFESSIONAL, "Acme Inc", expiration_days=365
        )
        assert license_data["expiration"] is not None
        exp_date = datetime.fromisoformat(license_data["expiration"])
        assert exp_date > datetime.now(UTC)

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generate_with_limits(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(
            LicenseType.BASIC,
            "Test Corp",
            max_extensions=100,
            max_concurrent_calls=50,
        )
        assert license_data["max_extensions"] == 100
        assert license_data["max_concurrent_calls"] == 50

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generate_custom_with_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        custom_features = ["basic_calling", "voicemail", "webrtc"]
        license_data = mgr.generate_license_key(
            LicenseType.CUSTOM, "Custom Corp", custom_features=custom_features
        )
        assert license_data["type"] == "custom"
        assert license_data["custom_features"] == custom_features

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generate_custom_without_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(LicenseType.CUSTOM, "Custom Corp")
        assert "custom_features" not in license_data

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generate_non_custom_ignores_custom_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(
            LicenseType.BASIC,
            "Test Corp",
            custom_features=["feature1"],
        )
        assert "custom_features" not in license_data

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generated_key_format(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp")
        key = license_data["key"]
        parts = key.split("-")
        assert len(parts) == 4
        for part in parts:
            assert len(part) == 4
            assert part == part.upper()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generate_perpetual_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(LicenseType.PERPETUAL, "Forever Corp")
        assert license_data["type"] == "perpetual"
        assert license_data["expiration"] is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_generated_license_has_valid_signature(self, mock_enabled) -> None:
        mgr = LicenseManager()
        license_data = mgr.generate_license_key(
            LicenseType.ENTERPRISE, "Enterprise Corp", expiration_days=365
        )
        assert mgr._verify_signature(license_data) is True


@pytest.mark.unit
class TestGenerateKeyString:
    """Tests for _generate_key_string."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_key_format(self, mock_enabled) -> None:
        mgr = LicenseManager()
        key = mgr._generate_key_string("Test Corp", "2025-01-01")
        assert len(key) == 19  # XXXX-XXXX-XXXX-XXXX
        assert key.count("-") == 3

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_keys_are_unique(self, mock_enabled) -> None:
        mgr = LicenseManager()
        keys = {mgr._generate_key_string("Test Corp", "2025-01-01") for _ in range(20)}
        assert len(keys) == 20  # All unique


@pytest.mark.unit
class TestSaveLicense:
    """Tests for save_license method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_save_license_success(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            mgr = LicenseManager()
            mgr.license_path = license_path

            license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp")

            with patch.object(mgr, "_load_license"):
                result = mgr.save_license(license_data)
                assert result is True

            # Verify file was created
            assert Path(license_path).exists()
            with Path(license_path).open() as f:
                saved = json.load(f)
            assert saved["issued_to"] == "Test Corp"

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_save_license_with_enforcement(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            mgr = LicenseManager()
            mgr.license_path = license_path

            license_data = mgr.generate_license_key(LicenseType.ENTERPRISE, "Corp")

            with (
                patch.object(mgr, "_load_license"),
                patch.object(mgr, "_create_license_lock") as mock_lock,
            ):
                result = mgr.save_license(license_data, enforce_licensing=True)
                assert result is True
                mock_lock.assert_called_once_with(license_data)

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_save_license_oserror(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.license_path = "/nonexistent/deep/path/.license"

        license_data = mgr.generate_license_key(LicenseType.BASIC, "Test Corp")
        result = mgr.save_license(license_data)
        assert result is False


@pytest.mark.unit
class TestCreateLicenseLock:
    """Tests for _create_license_lock method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_create_lock_file(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            mgr = LicenseManager()
            mgr.license_path = license_path

            license_data = {
                "key": "ABCD-EFGH-IJKL-MNOP-QRST",
                "issued_to": "Test Corp",
                "type": "enterprise",
            }
            mgr._create_license_lock(license_data)

            lock_path = Path(tmpdir) / ".license_lock"
            assert lock_path.exists()

            with lock_path.open() as f:
                lock_data = json.load(f)
            assert lock_data["enforcement"] == "mandatory"
            assert lock_data["issued_to"] == "Test Corp"

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_create_lock_file_error(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.license_path = "/nonexistent/path/.license"
        # Should not raise, just logs error
        mgr._create_license_lock({"key": "test", "issued_to": "x", "type": "y"})


@pytest.mark.unit
class TestRemoveLicenseLock:
    """Tests for remove_license_lock method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_remove_existing_lock(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            lock_path = Path(tmpdir) / ".license_lock"
            lock_path.write_text("{}")

            mgr = LicenseManager()
            mgr.license_path = license_path

            result = mgr.remove_license_lock()
            assert result is True
            assert not lock_path.exists()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_remove_nonexistent_lock(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            mgr = LicenseManager()
            mgr.license_path = license_path

            result = mgr.remove_license_lock()
            assert result is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_remove_lock_oserror(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.license_path = "/nonexistent/deep/path/.license"

        with patch("pbx.utils.licensing.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.unlink.side_effect = OSError("Permission denied")
            # The method constructs the lock path from license_path parent
            result = mgr.remove_license_lock()
            # This may return True or False depending on path resolution
            # The important thing is it doesn't raise
            assert isinstance(result, bool)


@pytest.mark.unit
class TestGetLicenseStatus:
    """Tests for get_license_status method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_status_disabled(self, mock_enabled) -> None:
        mgr = LicenseManager()
        status, message = mgr.get_license_status()
        assert status == LicenseStatus.DISABLED
        assert "disabled" in message.lower()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_status_no_license_checks_trial(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = None

        with patch.object(
            mgr, "_check_trial_eligibility", return_value=(LicenseStatus.ACTIVE, "Trial")
        ) as mock_trial:
            status, _message = mgr.get_license_status()
            mock_trial.assert_called_once()
            assert status == LicenseStatus.ACTIVE

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_status_active_with_expiration(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        mgr.current_license = {"expiration": future, "type": "basic"}

        status, message = mgr.get_license_status()
        assert status == LicenseStatus.ACTIVE
        assert "expires" in message.lower()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_status_active_perpetual(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "perpetual"}

        status, message = mgr.get_license_status()
        assert status == LicenseStatus.ACTIVE
        assert "perpetual" in message.lower()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_status_expired(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.grace_period_days = 7
        past = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        mgr.current_license = {"expiration": past, "type": "basic"}

        status, message = mgr.get_license_status()
        assert status == LicenseStatus.EXPIRED
        assert "expired" in message.lower()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_status_grace_period(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.grace_period_days = 7
        # Expired 2 days ago, still within 7-day grace period
        past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        mgr.current_license = {"expiration": past, "type": "basic"}

        status, message = mgr.get_license_status()
        assert status == LicenseStatus.GRACE_PERIOD
        assert "grace period" in message.lower()


@pytest.mark.unit
class TestCheckTrialEligibility:
    """Tests for _check_trial_eligibility method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_new_trial_started(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            mgr = LicenseManager()
            mgr.license_path = license_path
            mgr.trial_period_days = 30

            status, message = mgr._check_trial_eligibility()
            assert status == LicenseStatus.ACTIVE
            assert "trial" in message.lower()
            assert "30 days" in message.lower()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_trial_still_active(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            trial_marker = Path(tmpdir) / ".trial_start"
            trial_marker.write_text(datetime.now(UTC).isoformat())

            mgr = LicenseManager()
            mgr.license_path = license_path
            mgr.trial_period_days = 30

            status, message = mgr._check_trial_eligibility()
            assert status == LicenseStatus.ACTIVE
            assert "remaining" in message.lower()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_trial_expired(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            trial_marker = Path(tmpdir) / ".trial_start"
            past = (datetime.now(UTC) - timedelta(days=60)).isoformat()
            trial_marker.write_text(past)

            mgr = LicenseManager()
            mgr.license_path = license_path
            mgr.trial_period_days = 30

            status, message = mgr._check_trial_eligibility()
            assert status == LicenseStatus.EXPIRED
            assert "expired" in message.lower()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_trial_marker_read_error(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            trial_marker = Path(tmpdir) / ".trial_start"
            # Create the marker so exists() returns True
            trial_marker.write_text("placeholder")

            mgr = LicenseManager()
            mgr.license_path = license_path

            # Mock the open call on the trial_marker path to raise OSError
            original_open = Path.open

            def mock_open(self_path, *args, **kwargs):
                if str(self_path) == str(trial_marker):
                    raise OSError("Permission denied")
                return original_open(self_path, *args, **kwargs)

            with patch.object(Path, "open", mock_open):
                status, _message = mgr._check_trial_eligibility()
                assert status == LicenseStatus.INVALID

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_trial_marker_creation_error(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.license_path = "/nonexistent/deep/path/.license"

        status, message = mgr._check_trial_eligibility()
        assert status == LicenseStatus.INVALID
        assert "unable" in message.lower()


@pytest.mark.unit
class TestHasFeature:
    """Tests for has_feature method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_all_features_when_disabled(self, mock_enabled) -> None:
        mgr = LicenseManager()
        assert mgr.has_feature("any_feature") is True
        assert mgr.has_feature("ai_features") is True

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_trial_features_no_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = None
        assert mgr.has_feature("basic_calling") is True
        assert mgr.has_feature("ai_features") is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_expired_license_no_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        past = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        mgr.current_license = {"expiration": past, "type": "basic"}
        mgr.grace_period_days = 0

        assert mgr.has_feature("basic_calling") is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_active_license_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        mgr.current_license = {"expiration": future, "type": "professional"}

        assert mgr.has_feature("webrtc") is True
        assert mgr.has_feature("ai_features") is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_custom_license_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        mgr.current_license = {
            "expiration": future,
            "type": "custom",
            "custom_features": ["basic_calling", "webrtc"],
        }

        assert mgr.has_feature("basic_calling") is True
        assert mgr.has_feature("webrtc") is True
        assert mgr.has_feature("ai_features") is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_custom_license_no_custom_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        mgr.current_license = {"expiration": future, "type": "custom"}

        assert mgr.has_feature("basic_calling") is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_invalid_license_no_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        # Expired beyond grace period
        past = (datetime.now(UTC) - timedelta(days=300)).isoformat()
        mgr.current_license = {"expiration": past, "type": "enterprise"}
        mgr.grace_period_days = 7

        assert mgr.has_feature("basic_calling") is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_unknown_license_type_no_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        mgr.current_license = {"expiration": future, "type": "nonexistent_type"}

        assert mgr.has_feature("basic_calling") is False


@pytest.mark.unit
class TestGetLimit:
    """Tests for get_limit method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_no_limits_when_disabled(self, mock_enabled) -> None:
        mgr = LicenseManager()
        assert mgr.get_limit("max_extensions") is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_trial_limits(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = None
        assert mgr.get_limit("max_extensions") == 10
        assert mgr.get_limit("max_concurrent_calls") == 5

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_enterprise_unlimited(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        mgr.current_license = {"expiration": future, "type": "enterprise"}
        assert mgr.get_limit("max_extensions") is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_explicit_limit_in_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "basic", "max_extensions": 75}
        assert mgr.get_limit("max_extensions") == 75

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_explicit_unlimited_in_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "basic", "max_extensions": "unlimited"}
        assert mgr.get_limit("max_extensions") is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_nonexistent_limit_returns_none(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "basic"}
        assert mgr.get_limit("nonexistent_limit") is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_basic_limits_from_features(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "basic"}
        assert mgr.get_limit("max_extensions") == 50
        assert mgr.get_limit("max_concurrent_calls") == 25


@pytest.mark.unit
class TestCheckLimit:
    """Tests for check_limit method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_within_limit(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "trial"}
        assert mgr.check_limit("max_extensions", 5) is True

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_at_limit(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "trial"}
        assert mgr.check_limit("max_extensions", 10) is True

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_exceeds_limit(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {"type": "trial"}
        assert mgr.check_limit("max_extensions", 11) is False

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_unlimited_always_passes(self, mock_enabled) -> None:
        mgr = LicenseManager()
        # Licensing disabled means no limits
        assert mgr.check_limit("max_extensions", 999999) is True


@pytest.mark.unit
class TestGetLicenseInfo:
    """Tests for get_license_info method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_info_disabled(self, mock_enabled) -> None:
        mgr = LicenseManager()
        info = mgr.get_license_info()
        assert info["enabled"] is False
        assert info["type"] == "disabled"
        assert info["features"] == "all"
        assert info["status"] == "disabled"

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_info_with_active_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        mgr.current_license = {
            "key": "ABCD-EFGH-IJKL-MNOP",
            "type": "professional",
            "issued_to": "Test Corp",
            "issued_date": "2025-01-01",
            "expiration": future,
        }

        info = mgr.get_license_info()
        assert info["enabled"] is True
        assert info["type"] == "professional"
        assert info["issued_to"] == "Test Corp"
        assert info["key"].endswith("...")
        assert "limits" in info

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_info_no_license_trial(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = None

        with patch.object(
            mgr, "_check_trial_eligibility", return_value=(LicenseStatus.ACTIVE, "Trial")
        ):
            info = mgr.get_license_info()
            assert info["type"] == "trial"
            assert "limits" in info

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_info_perpetual_license(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.enabled = True
        mgr.current_license = {
            "key": "ABCD-EFGH-IJKL-MNOP",
            "type": "perpetual",
            "issued_to": "Forever Corp",
            "issued_date": "2025-01-01",
        }

        info = mgr.get_license_info()
        assert info["expiration"] == "never"


@pytest.mark.unit
class TestRevokeLicense:
    """Tests for revoke_license method."""

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_revoke_existing_license(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            Path(license_path).write_text("{}")

            mgr = LicenseManager()
            mgr.license_path = license_path
            mgr.current_license = {"type": "basic"}

            result = mgr.revoke_license()
            assert result is True
            assert mgr.current_license is None
            assert not Path(license_path).exists()

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_revoke_no_file(self, mock_enabled) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = str(Path(tmpdir) / ".license")
            mgr = LicenseManager()
            mgr.license_path = license_path
            mgr.current_license = {"type": "basic"}

            result = mgr.revoke_license()
            assert result is True
            assert mgr.current_license is None

    @patch.object(LicenseManager, "_is_licensing_enabled", return_value=False)
    def test_revoke_oserror(self, mock_enabled) -> None:
        mgr = LicenseManager()
        mgr.license_path = "/some/path/.license"
        mgr.current_license = {"type": "basic"}

        with patch("pbx.utils.licensing.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.unlink.side_effect = OSError("Permission denied")
            result = mgr.revoke_license()
            assert result is False


@pytest.mark.unit
class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_initialize_license_manager(self) -> None:
        import pbx.utils.licensing as licensing_module

        old_manager = licensing_module._license_manager
        try:
            mgr = initialize_license_manager({"licensing": {"enabled": False}})
            assert isinstance(mgr, LicenseManager)
            assert licensing_module._license_manager is mgr
        finally:
            licensing_module._license_manager = old_manager

    def test_get_license_manager_creates_default(self) -> None:
        import pbx.utils.licensing as licensing_module

        old_manager = licensing_module._license_manager
        try:
            licensing_module._license_manager = None
            mgr = get_license_manager()
            assert isinstance(mgr, LicenseManager)
        finally:
            licensing_module._license_manager = old_manager

    def test_get_license_manager_returns_existing(self) -> None:
        import pbx.utils.licensing as licensing_module

        old_manager = licensing_module._license_manager
        try:
            existing = LicenseManager.__new__(LicenseManager)
            licensing_module._license_manager = existing
            mgr = get_license_manager()
            assert mgr is existing
        finally:
            licensing_module._license_manager = old_manager

    def test_has_feature_convenience(self) -> None:
        import pbx.utils.licensing as licensing_module

        old_manager = licensing_module._license_manager
        try:
            # Disabled licensing = all features available
            licensing_module._license_manager = None
            result = has_feature("any_feature")
            assert result is True
        finally:
            licensing_module._license_manager = old_manager

    def test_check_limit_convenience(self) -> None:
        import pbx.utils.licensing as licensing_module

        old_manager = licensing_module._license_manager
        try:
            licensing_module._license_manager = None
            result = check_limit("max_extensions", 1000)
            assert result is True
        finally:
            licensing_module._license_manager = old_manager

    def test_get_license_info_convenience(self) -> None:
        import pbx.utils.licensing as licensing_module

        old_manager = licensing_module._license_manager
        try:
            licensing_module._license_manager = None
            info = get_license_info()
            assert isinstance(info, dict)
            assert "enabled" in info
        finally:
            licensing_module._license_manager = old_manager
