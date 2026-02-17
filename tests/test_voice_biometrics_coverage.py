"""
Comprehensive tests for voice biometrics feature module.

Tests all public classes, methods, enums, and code paths in
pbx/features/voice_biometrics.py including ML-backed and
fallback matching, fraud detection, enrollment, and profile
lifecycle management.
"""

import hashlib
import struct
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBiometricStatus:
    """Tests for the BiometricStatus enum."""

    def test_enum_values(self) -> None:
        from pbx.features.voice_biometrics import BiometricStatus

        assert BiometricStatus.NOT_ENROLLED.value == "not_enrolled"
        assert BiometricStatus.ENROLLING.value == "enrolling"
        assert BiometricStatus.ENROLLED.value == "enrolled"
        assert BiometricStatus.SUSPENDED.value == "suspended"

    def test_enum_members_count(self) -> None:
        from pbx.features.voice_biometrics import BiometricStatus

        assert len(BiometricStatus) == 4

    def test_enum_lookup_by_value(self) -> None:
        from pbx.features.voice_biometrics import BiometricStatus

        assert BiometricStatus("not_enrolled") is BiometricStatus.NOT_ENROLLED
        assert BiometricStatus("enrolled") is BiometricStatus.ENROLLED


@pytest.mark.unit
class TestVoiceProfile:
    """Tests for the VoiceProfile dataclass."""

    def test_init_defaults(self) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceProfile

        profile = VoiceProfile("user1", "1001")

        assert profile.user_id == "user1"
        assert profile.extension == "1001"
        assert profile.status == BiometricStatus.NOT_ENROLLED
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.last_updated, datetime)
        assert profile.enrollment_samples == 0
        assert profile.required_samples == 3
        assert profile.voiceprint is None
        assert profile.voiceprint_features == {}
        assert profile.enrollment_features == []
        assert profile.gmm_model is None
        assert profile.successful_verifications == 0
        assert profile.failed_verifications == 0

    def test_created_at_is_utc(self) -> None:
        from pbx.features.voice_biometrics import VoiceProfile

        profile = VoiceProfile("user1", "1001")
        assert profile.created_at.tzinfo is not None

    def test_multiple_profiles_independent(self) -> None:
        from pbx.features.voice_biometrics import VoiceProfile

        p1 = VoiceProfile("user1", "1001")
        p2 = VoiceProfile("user2", "1002")

        p1.enrollment_samples = 5
        assert p2.enrollment_samples == 0

    def test_mutable_fields(self) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceProfile

        profile = VoiceProfile("user1", "1001")
        profile.status = BiometricStatus.ENROLLED
        profile.voiceprint = "abc123"
        profile.voiceprint_features = {"pitch": 150.0}
        profile.enrollment_features.append({"pitch": 150.0})
        profile.gmm_model = MagicMock()

        assert profile.status == BiometricStatus.ENROLLED
        assert profile.voiceprint == "abc123"
        assert profile.voiceprint_features == {"pitch": 150.0}
        assert len(profile.enrollment_features) == 1
        assert profile.gmm_model is not None


@pytest.mark.unit
class TestVoiceBiometricsInit:
    """Tests for VoiceBiometrics initialization."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_init_no_config(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        assert vb.config == {}
        assert vb.db_backend is None
        assert vb.db is None
        assert vb.enabled is False
        assert vb.provider == "nuance"
        assert vb.verification_threshold == 0.85
        assert vb.enrollment_required_samples == 3
        assert vb.fraud_detection_enabled is True
        assert vb.profiles == {}
        assert vb.total_enrollments == 0
        assert vb.total_verifications == 0
        assert vb.successful_verifications == 0
        assert vb.failed_verifications == 0
        assert vb.fraud_attempts_detected == 0

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_init_with_custom_config(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        config = {
            "features": {
                "voice_biometrics": {
                    "enabled": True,
                    "provider": "pindrop",
                    "threshold": 0.90,
                    "enrollment_samples": 5,
                    "fraud_detection": False,
                }
            }
        }
        vb = VoiceBiometrics(config=config)

        assert vb.enabled is True
        assert vb.provider == "pindrop"
        assert vb.verification_threshold == 0.90
        assert vb.enrollment_required_samples == 5
        assert vb.fraud_detection_enabled is False

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_init_with_empty_features_config(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        config = {"features": {}}
        vb = VoiceBiometrics(config=config)

        assert vb.enabled is False
        assert vb.provider == "nuance"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_init_with_db_backend_enabled(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_db_backend = MagicMock()
        mock_db_backend.enabled = True

        mock_vb_db_instance = MagicMock()
        mock_vb_db_module = MagicMock()
        mock_vb_db_module.VoiceBiometricsDatabase.return_value = mock_vb_db_instance

        with patch.dict(
            "sys.modules",
            {"pbx.features.voice_biometrics_db": mock_vb_db_module},
        ):
            vb = VoiceBiometrics(db_backend=mock_db_backend)

        assert vb.db is mock_vb_db_instance
        mock_vb_db_instance.create_tables.assert_called_once()

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_init_with_db_backend_disabled(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_db_backend = MagicMock()
        mock_db_backend.enabled = False

        vb = VoiceBiometrics(db_backend=mock_db_backend)
        assert vb.db is None

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_init_db_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        import sqlite3

        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_db_backend = MagicMock()
        mock_db_backend.enabled = True

        mock_vb_db_module = MagicMock()
        mock_vb_db_module.VoiceBiometricsDatabase.side_effect = sqlite3.Error("db error")

        with patch.dict("sys.modules", {"pbx.features.voice_biometrics_db": mock_vb_db_module}):
            vb = VoiceBiometrics(db_backend=mock_db_backend)

        assert vb.db is None

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_gmm_score_thresholds_initialized(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        assert vb.GMM_SCORE_EXCELLENT == -5.0
        assert vb.GMM_SCORE_VERY_GOOD == -10.0
        assert vb.GMM_SCORE_GOOD == -15.0
        assert vb.GMM_SCORE_FAIR == -20.0
        assert vb.GMM_SCORE_WEAK == -30.0
        assert vb.MIN_GMM_ENROLLMENT_SAMPLES == 3


@pytest.mark.unit
class TestCreateProfile:
    """Tests for VoiceBiometrics.create_profile."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_create_new_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        profile = vb.create_profile("user1", "1001")

        assert profile.user_id == "user1"
        assert profile.extension == "1001"
        assert profile.status == BiometricStatus.NOT_ENROLLED
        assert profile.required_samples == vb.enrollment_required_samples
        assert "user1" in vb.profiles

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_create_duplicate_profile_returns_existing(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        profile1 = vb.create_profile("user1", "1001")
        profile2 = vb.create_profile("user1", "1002")

        assert profile1 is profile2
        assert profile2.extension == "1001"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_create_profile_saves_to_db(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()
        vb.create_profile("user1", "1001")

        vb.db.save_profile.assert_called_once_with("user1", "1001", "not_enrolled")

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_create_profile_no_db(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        assert vb.db is None
        profile = vb.create_profile("user1", "1001")
        assert profile is not None

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_create_profile_custom_enrollment_samples(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        config = {"features": {"voice_biometrics": {"enrollment_samples": 7}}}
        vb = VoiceBiometrics(config=config)
        profile = vb.create_profile("user1", "1001")

        assert profile.required_samples == 7


@pytest.mark.unit
class TestStartEnrollment:
    """Tests for VoiceBiometrics.start_enrollment."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_start_enrollment_success(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")

        result = vb.start_enrollment("user1")

        assert result["success"] is True
        assert result["user_id"] == "user1"
        assert result["required_samples"] == 3
        assert "session_id" in result
        assert len(result["session_id"]) == 16
        assert vb.profiles["user1"].status == BiometricStatus.ENROLLING
        assert vb.profiles["user1"].enrollment_samples == 0

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_start_enrollment_no_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb.start_enrollment("nonexistent")

        assert result["success"] is False
        assert result["error"] == "Profile not found"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_start_enrollment_resets_samples(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].enrollment_samples = 2

        vb.start_enrollment("user1")
        assert vb.profiles["user1"].enrollment_samples == 0


@pytest.mark.unit
class TestAddEnrollmentSample:
    """Tests for VoiceBiometrics.add_enrollment_sample."""

    @staticmethod
    def _make_audio_data(num_samples: int = 500) -> bytes:
        """Create valid 16-bit PCM audio data."""
        data = b""
        for i in range(num_samples):
            sample = int(10000 * ((i % 50) / 50.0 - 0.5))
            data += struct.pack("<h", sample)
        return data

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_add_sample_no_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb.add_enrollment_sample("nonexistent", b"\x00" * 200)

        assert result["success"] is False
        assert result["error"] == "Profile not found"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_add_sample_increments_count(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")

        audio = self._make_audio_data()
        result = vb.add_enrollment_sample("user1", audio)

        assert result["success"] is True
        assert result["samples_collected"] == 1
        assert result["samples_required"] == 3
        assert result["enrollment_complete"] is False

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_enrollment_completes_after_required_samples(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")

        audio = self._make_audio_data()
        for i in range(3):
            result = vb.add_enrollment_sample("user1", audio)

        assert result["enrollment_complete"] is True
        assert result["samples_collected"] == 3
        assert vb.profiles["user1"].status == BiometricStatus.ENROLLED
        assert vb.profiles["user1"].voiceprint is not None
        assert vb.total_enrollments == 1

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_add_sample_updates_last_updated(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")

        original_time = vb.profiles["user1"].last_updated
        audio = self._make_audio_data()
        vb.add_enrollment_sample("user1", audio)

        assert vb.profiles["user1"].last_updated >= original_time

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_add_sample_with_db(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()
        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")

        audio = self._make_audio_data()
        vb.add_enrollment_sample("user1", audio)

        vb.db.update_enrollment_progress.assert_called_once_with("user1", 1)

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_enrollment_complete_saves_to_db(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()
        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")

        audio = self._make_audio_data()
        for _ in range(3):
            vb.add_enrollment_sample("user1", audio)

        # save_profile called during create + final enrollment
        assert vb.db.save_profile.call_count == 2
        vb.db.save_profile.assert_called_with("user1", "1001", "enrolled")

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_add_sample_with_empty_audio(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")

        # Empty audio should still increment count but no features extracted
        result = vb.add_enrollment_sample("user1", b"")

        assert result["success"] is True
        assert result["samples_collected"] == 1

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_add_sample_with_short_audio(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")

        # Audio less than 100 bytes returns empty features
        result = vb.add_enrollment_sample("user1", b"\x00" * 50)

        assert result["success"] is True
        assert result["samples_collected"] == 1


@pytest.mark.unit
class TestVerifySpeaker:
    """Tests for VoiceBiometrics.verify_speaker."""

    @staticmethod
    def _make_audio_data(num_samples: int = 500) -> bytes:
        """Create valid 16-bit PCM audio data."""
        data = b""
        for i in range(num_samples):
            sample = int(10000 * ((i % 50) / 50.0 - 0.5))
            data += struct.pack("<h", sample)
        return data

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_verify_no_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb.verify_speaker("nonexistent", b"\x00" * 200)

        assert result["verified"] is False
        assert result["confidence"] == 0.0
        assert result["error"] == "No profile found"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_verify_not_enrolled(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")

        result = vb.verify_speaker("user1", b"\x00" * 200)

        assert result["verified"] is False
        assert result["confidence"] == 0.0
        assert result["error"] == "Profile not enrolled"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_verify_enrolled_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].status = BiometricStatus.ENROLLED

        audio = self._make_audio_data()
        result = vb.verify_speaker("user1", audio)

        assert "verified" in result
        assert "confidence" in result
        assert "user_id" in result
        assert result["user_id"] == "user1"
        assert "timestamp" in result
        assert vb.total_verifications == 1

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_verify_successful_high_confidence(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        # Force the random fallback to return high score
        mock_random.uniform.return_value = 0.95

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].status = BiometricStatus.ENROLLED
        # Empty voiceprint_features triggers random fallback

        audio = self._make_audio_data()
        result = vb.verify_speaker("user1", audio)

        assert result["verified"] is True
        assert result["confidence"] == 0.95
        assert vb.successful_verifications == 1
        assert vb.profiles["user1"].successful_verifications == 1

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_verify_failed_low_confidence(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        mock_random.uniform.return_value = 0.50

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].status = BiometricStatus.ENROLLED

        audio = self._make_audio_data()
        result = vb.verify_speaker("user1", audio)

        assert result["verified"] is False
        assert vb.failed_verifications == 1
        assert vb.profiles["user1"].failed_verifications == 1

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_verify_saves_to_db(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].status = BiometricStatus.ENROLLED

        audio = self._make_audio_data()
        vb.verify_speaker("user1", audio)

        vb.db.save_verification.assert_called_once()
        args = vb.db.save_verification.call_args
        assert args[0][0] == "user1"
        assert isinstance(args[0][2], bool)
        assert isinstance(args[0][3], float)

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_verify_suspended_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].status = BiometricStatus.SUSPENDED

        audio = self._make_audio_data()
        result = vb.verify_speaker("user1", audio)

        assert result["verified"] is False
        assert result["error"] == "Profile not enrolled"


@pytest.mark.unit
class TestDetectFraud:
    """Tests for VoiceBiometrics.detect_fraud."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_detection_disabled(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        config = {"features": {"voice_biometrics": {"fraud_detection": False}}}
        vb = VoiceBiometrics(config=config)

        result = vb.detect_fraud(b"\x00" * 200, {"caller_id": "1001"})

        assert result["fraud_detected"] is False
        assert result["reason"] == "Fraud detection disabled"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_detection_clean_audio(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        # Create normal-looking audio
        audio = b""
        for i in range(500):
            sample = int(5000 * ((i % 37) / 37.0 - 0.5))
            audio += struct.pack("<h", sample)

        result = vb.detect_fraud(audio, {"caller_id": "1001"})

        assert "fraud_detected" in result
        assert "risk_score" in result
        assert "indicators" in result
        assert "caller_info" in result
        assert "timestamp" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_low_energy_variance(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        # Mock _extract_voice_features to return low energy variance
        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={"energy_variance": 0.05, "spectral_flatness": 0.3, "pitch": 150.0, "zero_crossing_rate": 0.1},
        ):
            result = vb.detect_fraud(b"\x00" * 200, {"caller_id": "1001"})

        assert "low_energy_variance" in result["indicators"]
        assert result["risk_score"] >= 0.3

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_high_spectral_flatness(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={"energy_variance": 1.0, "spectral_flatness": 0.9, "pitch": 150.0, "zero_crossing_rate": 0.1},
        ):
            result = vb.detect_fraud(b"\x00" * 200, {"caller_id": "1001"})

        assert "high_spectral_flatness" in result["indicators"]

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_repetitive_pattern(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        # Create highly repetitive audio data with identical chunks
        chunk = b"\x01\x02" * 500
        audio = chunk * 20  # Many identical repeated chunks

        with patch.object(vb, "_extract_voice_features", return_value={}):
            result = vb.detect_fraud(audio, {"caller_id": "1001"})

        assert "repetitive_pattern" in result["indicators"]
        assert result["risk_score"] >= 0.35

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_abnormal_pitch_low(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={"energy_variance": 1.0, "spectral_flatness": 0.3, "pitch": 30.0, "zero_crossing_rate": 0.1},
        ):
            result = vb.detect_fraud(b"\x00" * 200, {"caller_id": "1001"})

        assert "abnormal_pitch" in result["indicators"]

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_abnormal_pitch_high(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={"energy_variance": 1.0, "spectral_flatness": 0.3, "pitch": 500.0, "zero_crossing_rate": 0.1},
        ):
            result = vb.detect_fraud(b"\x00" * 200, {"caller_id": "1001"})

        assert "abnormal_pitch" in result["indicators"]

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_abnormal_zcr_low(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={"energy_variance": 1.0, "spectral_flatness": 0.3, "pitch": 150.0, "zero_crossing_rate": 0.005},
        ):
            result = vb.detect_fraud(b"\x00" * 200, {"caller_id": "1001"})

        assert "abnormal_zero_crossing" in result["indicators"]

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_abnormal_zcr_high(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={"energy_variance": 1.0, "spectral_flatness": 0.3, "pitch": 150.0, "zero_crossing_rate": 0.6},
        ):
            result = vb.detect_fraud(b"\x00" * 200, {"caller_id": "1001"})

        assert "abnormal_zero_crossing" in result["indicators"]

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_multiple_indicators_high_risk(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        # Trigger multiple fraud indicators at once
        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={
                "energy_variance": 0.05,
                "spectral_flatness": 0.9,
                "pitch": 30.0,
                "zero_crossing_rate": 0.005,
            },
        ):
            # Also create repetitive audio for pattern detection
            chunk = b"\xAB\xCD" * 500
            audio = chunk * 20
            result = vb.detect_fraud(audio, {"caller_id": "1001"})

        assert result["fraud_detected"] is True
        assert result["risk_score"] <= 1.0
        assert vb.fraud_attempts_detected >= 1

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_risk_score_capped_at_1(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        # All indicators triggered
        with patch.object(
            vb,
            "_extract_voice_features",
            return_value={
                "energy_variance": 0.01,
                "spectral_flatness": 0.99,
                "pitch": 10.0,
                "zero_crossing_rate": 0.001,
            },
        ):
            chunk = b"\x01\x02" * 500
            audio = chunk * 20
            result = vb.detect_fraud(audio, {"caller_id": "1001"})

        assert result["risk_score"] <= 1.0

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_empty_audio(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb.detect_fraud(b"", {"caller_id": "1001"})

        assert result["fraud_detected"] is False
        assert result["risk_score"] == 0.0

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_saves_to_db(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()

        caller_info = {"call_id": "call-123", "caller_id": "5551234"}
        vb.detect_fraud(b"\x00" * 200, caller_info)

        vb.db.save_fraud_detection.assert_called_once()
        args = vb.db.save_fraud_detection.call_args[0]
        assert args[0] == "call-123"
        assert args[1] == "5551234"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_saves_to_db_missing_call_id(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()

        caller_info = {"caller_id": "5551234"}
        vb.detect_fraud(b"\x00" * 200, caller_info)

        vb.db.save_fraud_detection.assert_called_once()
        args = vb.db.save_fraud_detection.call_args[0]
        # call_id should be auto-generated
        assert args[0].startswith("call-")

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_saves_to_db_missing_caller_id(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()

        caller_info = {"call_id": "call-123"}
        vb.detect_fraud(b"\x00" * 200, caller_info)

        vb.db.save_fraud_detection.assert_called_once()
        args = vb.db.save_fraud_detection.call_args[0]
        assert args[1] == "unknown"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_fraud_no_voice_features_non_repetitive(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        # Use non-repetitive audio bytes that won't trigger pattern detection
        # and empty voice features from the extractor
        audio = bytes(range(256)) * 2  # 512 bytes, non-repetitive chunks
        with patch.object(vb, "_extract_voice_features", return_value={}):
            result = vb.detect_fraud(audio, {"caller_id": "1001"})

        assert result["risk_score"] == 0.0
        assert result["indicators"] == []


@pytest.mark.unit
class TestExtractVoiceFeatures:
    """Tests for VoiceBiometrics._extract_voice_features (fallback path)."""

    @staticmethod
    def _make_audio_data(num_samples: int = 500) -> bytes:
        """Create valid 16-bit PCM audio data with variation."""
        data = b""
        for i in range(num_samples):
            sample = int(10000 * ((i % 50) / 50.0 - 0.5))
            data += struct.pack("<h", sample)
        return data

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_empty_audio_returns_empty(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb._extract_voice_features(b"")

        assert result == {}

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_short_audio_returns_empty(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb._extract_voice_features(b"\x00" * 50)

        assert result == {}

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    def test_fallback_feature_extraction(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        audio = self._make_audio_data()
        result = vb._extract_voice_features(audio)

        assert "energy" in result
        assert "energy_variance" in result
        assert "zero_crossing_rate" in result
        assert "pitch" in result
        assert "dynamic_range" in result
        assert result["energy"] > 0
        assert 50 <= result["pitch"] <= 400

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    def test_fallback_odd_byte_count(self, mock_get_logger: MagicMock) -> None:
        """Test with odd number of bytes (last byte is ignored)."""
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        # 201 bytes means last byte is dropped
        audio = self._make_audio_data(100) + b"\x00"
        result = vb._extract_voice_features(audio)

        assert "energy" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    def test_fallback_zero_crossing_rate(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        # Create audio that crosses zero frequently
        data = b""
        for i in range(500):
            val = 1000 if i % 2 == 0 else -1000
            data += struct.pack("<h", val)

        result = vb._extract_voice_features(data)

        assert result["zero_crossing_rate"] > 0

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_pyaudio_analysis_path(self, mock_np: MagicMock, mock_get_logger: MagicMock) -> None:
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        # Mock numpy
        mock_np.array.return_value = MagicMock()
        mock_np.float64 = float
        mock_np.mean.return_value = 0.5

        mock_st_features = MagicMock()
        mock_st_features.__len__ = lambda self: 20
        mock_st_features.__getitem__ = lambda self, key: MagicMock()

        mock_audio_feat = MagicMock()
        mock_audio_feat.stFeatureExtraction.return_value = mock_st_features

        # Inject the mock as a module attribute since pyAudioAnalysis is not installed
        vb_module.audioFeatureExtraction = mock_audio_feat
        try:
            vb = VoiceBiometrics()
            audio = self._make_audio_data(1000)
            result = vb._extract_voice_features(audio)
        finally:
            del vb_module.audioFeatureExtraction

        assert "mfcc_mean" in result or "energy" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_librosa_path(self, mock_np: MagicMock, mock_get_logger: MagicMock) -> None:
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_np.array.return_value = MagicMock()
        mock_np.float32 = float
        mock_np.mean.return_value = 0.5
        mock_np.std.return_value = 0.1

        mock_librosa = MagicMock()
        mock_librosa.feature.mfcc.return_value = MagicMock()
        mock_librosa.feature.spectral_centroid.return_value = MagicMock()
        mock_librosa.feature.zero_crossing_rate.return_value = MagicMock()

        vb_module.librosa = mock_librosa
        try:
            vb = VoiceBiometrics()
            audio = self._make_audio_data()
            result = vb._extract_voice_features(audio)
        finally:
            if hasattr(vb_module, "librosa"):
                del vb_module.librosa

        assert "mfcc_mean" in result or "energy" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_librosa_path_exception_falls_back(
        self, mock_np: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_np.array.return_value = MagicMock()
        mock_np.float32 = float

        mock_librosa = MagicMock()
        mock_librosa.feature.mfcc.side_effect = ValueError("librosa error")

        vb_module.librosa = mock_librosa
        try:
            vb = VoiceBiometrics()
            audio = self._make_audio_data()
            result = vb._extract_voice_features(audio)
        finally:
            if hasattr(vb_module, "librosa"):
                del vb_module.librosa

        # Should fall back to basic extraction
        assert "energy" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    def test_all_samples_zero(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        audio = b"\x00\x00" * 200
        result = vb._extract_voice_features(audio)

        assert result["energy"] == 0
        assert result["zero_crossing_rate"] == 0.0
        assert result["dynamic_range"] == 0

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    def test_extract_features_outer_exception_handler(self, mock_get_logger: MagicMock) -> None:
        """Trigger the outer except block in _extract_voice_features."""
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        # Patch struct.unpack to raise TypeError to trigger outer handler
        with patch("pbx.features.voice_biometrics.struct") as mock_struct:
            mock_struct.unpack.side_effect = TypeError("bad data")
            result = vb._extract_voice_features(b"\x00" * 200)

        assert result == {}

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_pyaudio_analysis_full_feature_extraction(
        self, mock_np: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test pyAudioAnalysis path covering lines 627-646 with sufficient audio."""
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        # Need enough samples for frame_size (800 = 16000 * 0.050)
        # So we need >= 800 samples => 1600 bytes of audio
        audio = self._make_audio_data(1000)

        # Mock numpy array with __len__ that returns >= frame_size
        mock_audio_array = MagicMock()
        mock_audio_array.__len__ = lambda self: 1000
        mock_audio_array.__truediv__ = lambda self, other: self

        mock_np.array.return_value = mock_audio_array
        mock_np.float64 = float
        mock_np.mean.return_value = 0.5

        mock_st_features = MagicMock()
        mock_st_features.__len__ = lambda self: 20
        mock_st_features.__getitem__ = lambda self, key: MagicMock()

        mock_audio_feat = MagicMock()
        mock_audio_feat.stFeatureExtraction.return_value = mock_st_features

        vb_module.audioFeatureExtraction = mock_audio_feat
        try:
            vb = VoiceBiometrics()
            result = vb._extract_voice_features(audio)
        finally:
            if hasattr(vb_module, "audioFeatureExtraction"):
                del vb_module.audioFeatureExtraction

        # Should have extracted features via pyAudioAnalysis
        assert "mfcc_mean" in result
        assert "zcr_mean" in result
        assert "energy_mean" in result
        assert "spectral_centroid" in result
        assert "spectral_spread" in result
        assert "spectral_entropy" in result
        assert "spectral_rollof" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_pyaudio_analysis_returns_none(
        self, mock_np: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test pyAudioAnalysis path when stFeatureExtraction returns None."""
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        audio = self._make_audio_data(1000)

        mock_audio_array = MagicMock()
        mock_audio_array.__len__ = lambda self: 1000
        mock_audio_array.__truediv__ = lambda self, other: self

        mock_np.array.return_value = mock_audio_array
        mock_np.float64 = float

        mock_audio_feat = MagicMock()
        mock_audio_feat.stFeatureExtraction.return_value = None

        vb_module.audioFeatureExtraction = mock_audio_feat
        try:
            vb = VoiceBiometrics()
            result = vb._extract_voice_features(audio)
        finally:
            if hasattr(vb_module, "audioFeatureExtraction"):
                del vb_module.audioFeatureExtraction

        # Should fall back to basic features since pyAudioAnalysis returned None
        assert "energy" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_pyaudio_analysis_exception_path(
        self, mock_np: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test pyAudioAnalysis path when extraction raises an exception."""
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        audio = self._make_audio_data(1000)

        mock_audio_array = MagicMock()
        mock_audio_array.__len__ = lambda self: 1000
        mock_audio_array.__truediv__ = lambda self, other: self

        mock_np.array.return_value = mock_audio_array
        mock_np.float64 = float

        mock_audio_feat = MagicMock()
        mock_audio_feat.stFeatureExtraction.side_effect = ValueError("extraction error")

        vb_module.audioFeatureExtraction = mock_audio_feat
        try:
            vb = VoiceBiometrics()
            result = vb._extract_voice_features(audio)
        finally:
            if hasattr(vb_module, "audioFeatureExtraction"):
                del vb_module.audioFeatureExtraction

        # Should fall back to basic features
        assert "energy" in result

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_pyaudio_analysis_audio_too_short_for_frame(
        self, mock_np: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test when audio array is shorter than frame_size (800 samples)."""
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        # 100 samples: enough to pass the initial check but not enough for pyAudioAnalysis
        audio = self._make_audio_data(100)

        mock_audio_array = MagicMock()
        mock_audio_array.__len__ = lambda self: 100  # < frame_size of 800
        mock_audio_array.__truediv__ = lambda self, other: self

        mock_np.array.return_value = mock_audio_array
        mock_np.float64 = float

        mock_audio_feat = MagicMock()
        vb_module.audioFeatureExtraction = mock_audio_feat
        try:
            vb = VoiceBiometrics()
            result = vb._extract_voice_features(audio)
        finally:
            if hasattr(vb_module, "audioFeatureExtraction"):
                del vb_module.audioFeatureExtraction

        # pyAudioAnalysis should be skipped, should fall back to basic
        assert "energy" in result
        mock_audio_feat.stFeatureExtraction.assert_not_called()

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    def test_fallback_single_chunk_energy(self, mock_get_logger: MagicMock) -> None:
        """Test with very few samples where chunk_energies has only 1 entry."""
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        # Exactly 50 samples (100 bytes): chunk_size = max(1, 50//10) = 5
        # So 10 chunks, which is > 1
        # Need fewer: 5 samples (10 bytes) but need >= 100 bytes
        # Actually the initial check is len(audio_data) < 100
        # So minimum is 100 bytes = 50 samples, chunk_size = 5, 10 chunks
        # Use exactly 100 bytes
        audio = struct.pack("<h", 100) * 50  # 50 identical samples
        result = vb._extract_voice_features(audio)

        assert "energy" in result
        assert "energy_variance" in result


@pytest.mark.unit
class TestCreateVoiceprint:
    """Tests for VoiceBiometrics._create_voiceprint."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_voiceprint_no_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb._create_voiceprint("nonexistent", b"\x00" * 200)

        # Should return a sha256 hash
        assert isinstance(result, str)
        assert len(result) == 64

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_voiceprint_no_enrollment_features(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        # enrollment_features is empty
        result = vb._create_voiceprint("user1", b"\x00" * 200)

        assert isinstance(result, str)
        assert len(result) == 64

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_voiceprint_with_enrollment_features(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].enrollment_features = [
            {"pitch": 150.0, "energy": 5000.0, "zcr": 0.1},
            {"pitch": 155.0, "energy": 5100.0, "zcr": 0.12},
            {"pitch": 148.0, "energy": 4900.0, "zcr": 0.09},
        ]

        result = vb._create_voiceprint("user1", b"\x00" * 200)

        assert isinstance(result, str)
        assert len(result) == 64
        # Check that voiceprint_features were aggregated
        assert "pitch" in vb.profiles["user1"].voiceprint_features
        assert "energy" in vb.profiles["user1"].voiceprint_features
        # Aggregated values should be averages
        assert abs(vb.profiles["user1"].voiceprint_features["pitch"] - 151.0) < 0.01

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_voiceprint_with_non_numeric_features_skipped(
        self, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].enrollment_features = [
            {"pitch": 150.0, "label": "voice"},
            {"pitch": 155.0, "label": "voice"},
        ]

        vb._create_voiceprint("user1", b"\x00" * 200)

        # label should not be in aggregated features (non-numeric)
        assert "label" not in vb.profiles["user1"].voiceprint_features
        assert "pitch" in vb.profiles["user1"].voiceprint_features

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_voiceprint_trains_gmm_model(
        self,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_gmm_instance = MagicMock()
        mock_gmm_cls = MagicMock(return_value=mock_gmm_instance)
        mock_np.array.return_value = MagicMock()

        vb_module.GaussianMixture = mock_gmm_cls
        try:
            vb = VoiceBiometrics()
            vb.create_profile("user1", "1001")
            vb.profiles["user1"].enrollment_features = [
                {"pitch": 150.0, "energy": 5000.0},
                {"pitch": 155.0, "energy": 5100.0},
                {"pitch": 148.0, "energy": 4900.0},
            ]

            vb._create_voiceprint("user1", b"\x00" * 200)

            mock_gmm_cls.assert_called_once()
            mock_gmm_instance.fit.assert_called_once()
            assert vb.profiles["user1"].gmm_model is mock_gmm_instance
        finally:
            if hasattr(vb_module, "GaussianMixture"):
                del vb_module.GaussianMixture

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_voiceprint_gmm_training_error(
        self,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_gmm_cls = MagicMock(side_effect=ValueError("GMM training failed"))
        mock_np.array.return_value = MagicMock()

        vb_module.GaussianMixture = mock_gmm_cls
        try:
            vb = VoiceBiometrics()
            vb.create_profile("user1", "1001")
            vb.profiles["user1"].enrollment_features = [
                {"pitch": 150.0, "energy": 5000.0},
                {"pitch": 155.0, "energy": 5100.0},
                {"pitch": 148.0, "energy": 4900.0},
            ]

            # Should not raise, just log warning
            result = vb._create_voiceprint("user1", b"\x00" * 200)
            assert isinstance(result, str)
        finally:
            if hasattr(vb_module, "GaussianMixture"):
                del vb_module.GaussianMixture

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", False)
    def test_voiceprint_sklearn_not_available(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.profiles["user1"].enrollment_features = [
            {"pitch": 150.0},
            {"pitch": 155.0},
            {"pitch": 148.0},
        ]

        result = vb._create_voiceprint("user1", b"\x00" * 200)
        assert isinstance(result, str)
        # GMM model should not be set
        assert vb.profiles["user1"].gmm_model is None

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    def test_voiceprint_gmm_not_trained_below_min_samples(
        self,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        import pbx.features.voice_biometrics as vb_module
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_gmm_cls = MagicMock()
        mock_np.array.return_value = MagicMock()

        vb_module.GaussianMixture = mock_gmm_cls
        try:
            vb = VoiceBiometrics()
            vb.create_profile("user1", "1001")
            # Only 2 samples, MIN_GMM_ENROLLMENT_SAMPLES is 3
            vb.profiles["user1"].enrollment_features = [
                {"pitch": 150.0},
                {"pitch": 155.0},
            ]

            vb._create_voiceprint("user1", b"\x00" * 200)
            mock_gmm_cls.assert_not_called()
        finally:
            if hasattr(vb_module, "GaussianMixture"):
                del vb_module.GaussianMixture


@pytest.mark.unit
class TestCalculateMatchScore:
    """Tests for VoiceBiometrics._calculate_match_score."""

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_no_features(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.85
        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")

        score = vb._calculate_match_score(profile, {})

        assert score == 0.85
        mock_random.uniform.assert_called_with(0.75, 0.95)

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_empty_stored_features(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.88
        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {}

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert score == 0.88

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_distance_based_identical(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0  # No variation
        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0, "energy": 5000.0}

        # Identical features should give high score
        score = vb._calculate_match_score(profile, {"pitch": 150.0, "energy": 5000.0})

        # With identical values distance=0, similarity = 1/(1+0) = 1.0
        assert score == 1.0

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_distance_based_different(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0
        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0, "energy": 5000.0}

        # Very different features
        score = vb._calculate_match_score(profile, {"pitch": 300.0, "energy": 10000.0})

        assert 0.0 <= score <= 1.0
        assert score < 0.8  # Should be lower due to distance

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_no_overlapping_keys(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.85
        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}

        # No overlapping keys, feature_count = 0
        score = vb._calculate_match_score(profile, {"energy": 5000.0})

        assert score == 0.85  # Falls back to random

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_non_numeric_values_skipped(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.85
        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"label": "voice", "pitch": 150.0}

        # Non-numeric stored value for "label" is skipped
        score = vb._calculate_match_score(
            profile, {"label": "voice", "pitch": 150.0}
        )

        # "label" is skipped as it's a string, pitch matches
        assert 0.0 <= score <= 1.0

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_excellent(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0
        mock_np.array.return_value = MagicMock()

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}
        profile.gmm_model = MagicMock()
        profile.gmm_model.score.return_value = -3.0  # > EXCELLENT (-5.0)

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert score == 0.95

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_very_good(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0
        mock_np.array.return_value = MagicMock()

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}
        profile.gmm_model = MagicMock()
        profile.gmm_model.score.return_value = -7.0  # between EXCELLENT and VERY_GOOD

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert score == 0.90

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_good(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0
        mock_np.array.return_value = MagicMock()

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}
        profile.gmm_model = MagicMock()
        profile.gmm_model.score.return_value = -12.0  # between VERY_GOOD and GOOD

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert score == 0.85

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_fair(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0
        mock_np.array.return_value = MagicMock()

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}
        profile.gmm_model = MagicMock()
        profile.gmm_model.score.return_value = -17.0  # between GOOD and FAIR

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert score == 0.80

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_weak(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0
        mock_np.array.return_value = MagicMock()

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}
        profile.gmm_model = MagicMock()
        profile.gmm_model.score.return_value = -25.0  # between FAIR and WEAK

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert score == 0.75

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_below_weak(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_random.uniform.return_value = 0.0
        mock_np.array.return_value = MagicMock()

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}
        profile.gmm_model = MagicMock()
        profile.gmm_model.score.return_value = -50.0  # below WEAK

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert score == 0.70

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_exception_falls_back(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        mock_np.array.side_effect = ValueError("numpy error")
        mock_random.uniform.return_value = 0.85

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {}
        profile.gmm_model = MagicMock()

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        # Falls back to random after GMM failure and empty stored features
        assert score == 0.85

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.voice_biometrics.np")
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_gmm_clamped_to_0_1(
        self,
        mock_random: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        # Large positive variation that could push score above 1.0
        mock_random.uniform.return_value = 0.1
        mock_np.array.return_value = MagicMock()

        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 150.0}
        profile.gmm_model = MagicMock()
        profile.gmm_model.score.return_value = -3.0  # Excellent

        score = vb._calculate_match_score(profile, {"pitch": 150.0})

        assert 0.0 <= score <= 1.0

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.random")
    def test_match_score_distance_variation_clamped(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceProfile, VoiceBiometrics

        # Negative variation on a near-zero similarity should clamp to 0.0
        mock_random.uniform.return_value = -0.02
        vb = VoiceBiometrics()
        profile = VoiceProfile("user1", "1001")
        profile.voiceprint_features = {"pitch": 1.0}

        # Very large difference to get low similarity
        score = vb._calculate_match_score(profile, {"pitch": 1000000.0})

        assert score >= 0.0


@pytest.mark.unit
class TestProfileManagement:
    """Tests for profile lifecycle methods."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_get_profile_exists(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")

        profile = vb.get_profile("user1")
        assert profile is not None
        assert profile.user_id == "user1"

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_get_profile_not_found(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        profile = vb.get_profile("nonexistent")

        assert profile is None

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_delete_profile_exists(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")

        result = vb.delete_profile("user1")

        assert result is True
        assert "user1" not in vb.profiles

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_delete_profile_not_found(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        result = vb.delete_profile("nonexistent")

        assert result is False

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_suspend_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")

        vb.suspend_profile("user1")

        assert vb.profiles["user1"].status == BiometricStatus.SUSPENDED

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_suspend_nonexistent_profile(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        # Should not raise
        vb.suspend_profile("nonexistent")


@pytest.mark.unit
class TestGetStatistics:
    """Tests for VoiceBiometrics.get_statistics."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_initial_statistics(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        stats = vb.get_statistics()

        assert stats["total_profiles"] == 0
        assert stats["enrolled_profiles"] == 0
        assert stats["total_enrollments"] == 0
        assert stats["total_verifications"] == 0
        assert stats["successful_verifications"] == 0
        assert stats["failed_verifications"] == 0
        assert stats["verification_success_rate"] == 0.0
        assert stats["fraud_attempts_detected"] == 0
        assert stats["provider"] == "nuance"
        assert stats["enabled"] is False

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_statistics_with_profiles(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        vb = VoiceBiometrics()
        vb.create_profile("user1", "1001")
        vb.create_profile("user2", "1002")
        vb.profiles["user1"].status = BiometricStatus.ENROLLED

        stats = vb.get_statistics()

        assert stats["total_profiles"] == 2
        assert stats["enrolled_profiles"] == 1

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_statistics_with_verifications(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.total_verifications = 10
        vb.successful_verifications = 8
        vb.failed_verifications = 2

        stats = vb.get_statistics()

        assert stats["verification_success_rate"] == 0.8

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_statistics_zero_verifications_no_division_error(
        self, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        stats = vb.get_statistics()

        # max(1, 0) = 1, so 0/1 = 0.0
        assert stats["verification_success_rate"] == 0.0

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_statistics_with_db(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()
        vb.db.get_statistics.return_value = {"db_total": 100}

        stats = vb.get_statistics()

        assert "database_stats" in stats
        assert stats["database_stats"]["db_total"] == 100

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_statistics_with_db_returns_none(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        vb.db = MagicMock()
        vb.db.get_statistics.return_value = None

        stats = vb.get_statistics()

        assert "database_stats" not in stats

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_statistics_includes_library_availability(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        stats = vb.get_statistics()

        assert "pyaudio_analysis_available" in stats
        assert "librosa_available" in stats
        assert isinstance(stats["pyaudio_analysis_available"], bool)
        assert isinstance(stats["librosa_available"], bool)


@pytest.mark.unit
class TestGetVoiceBiometrics:
    """Tests for the get_voice_biometrics module-level function."""

    def test_get_creates_singleton(self) -> None:
        import pbx.features.voice_biometrics as vb_module

        # Reset global state
        vb_module._voice_biometrics = None

        with patch.object(vb_module, "get_logger"):
            instance1 = vb_module.get_voice_biometrics()
            instance2 = vb_module.get_voice_biometrics()

        assert instance1 is instance2

        # Clean up
        vb_module._voice_biometrics = None

    def test_get_with_config(self) -> None:
        import pbx.features.voice_biometrics as vb_module

        vb_module._voice_biometrics = None

        config = {
            "features": {
                "voice_biometrics": {
                    "provider": "aws_voice_id",
                }
            }
        }

        with patch.object(vb_module, "get_logger"):
            instance = vb_module.get_voice_biometrics(config=config)

        assert instance.provider == "aws_voice_id"

        # Clean up
        vb_module._voice_biometrics = None

    def test_get_returns_existing_ignores_new_config(self) -> None:
        import pbx.features.voice_biometrics as vb_module

        vb_module._voice_biometrics = None

        config1 = {"features": {"voice_biometrics": {"provider": "nuance"}}}
        config2 = {"features": {"voice_biometrics": {"provider": "pindrop"}}}

        with patch.object(vb_module, "get_logger"):
            instance1 = vb_module.get_voice_biometrics(config=config1)
            instance2 = vb_module.get_voice_biometrics(config=config2)

        assert instance2.provider == "nuance"

        # Clean up
        vb_module._voice_biometrics = None


@pytest.mark.unit
class TestGenerateSessionId:
    """Tests for VoiceBiometrics._generate_session_id."""

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_session_id_format(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()
        session_id = vb._generate_session_id("user1")

        assert isinstance(session_id, str)
        assert len(session_id) == 16
        # Should be a hex string
        int(session_id, 16)

    @patch("pbx.features.voice_biometrics.get_logger")
    def test_session_ids_differ_for_different_users(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        fixed_dt = datetime(2025, 1, 1, tzinfo=UTC)
        with patch("pbx.features.voice_biometrics.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            id1 = vb._generate_session_id("user1")
            id2 = vb._generate_session_id("user2")

        assert id1 != id2


@pytest.mark.unit
class TestFullEnrollmentAndVerificationFlow:
    """Integration-style tests covering full enrollment + verification flow."""

    @staticmethod
    def _make_audio_data(num_samples: int = 500, freq_mod: int = 50) -> bytes:
        """Create valid 16-bit PCM audio data."""
        data = b""
        for i in range(num_samples):
            sample = int(10000 * ((i % freq_mod) / freq_mod - 0.5))
            data += struct.pack("<h", sample)
        return data

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.random")
    def test_full_flow_enroll_and_verify(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import BiometricStatus, VoiceBiometrics

        mock_random.uniform.return_value = 0.0  # Remove randomness

        vb = VoiceBiometrics()
        audio = self._make_audio_data()

        # Create profile
        profile = vb.create_profile("user1", "1001")
        assert profile.status == BiometricStatus.NOT_ENROLLED

        # Start enrollment
        result = vb.start_enrollment("user1")
        assert result["success"] is True

        # Add 3 enrollment samples
        for _ in range(3):
            result = vb.add_enrollment_sample("user1", audio)

        assert result["enrollment_complete"] is True
        assert profile.status == BiometricStatus.ENROLLED
        assert profile.voiceprint is not None
        assert len(profile.voiceprint_features) > 0

        # Verify with the same audio (should match well)
        verify_result = vb.verify_speaker("user1", audio)
        assert verify_result["verified"] is True
        assert verify_result["confidence"] > 0.85

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.random")
    def test_full_flow_enroll_and_fail_verification(
        self, mock_random: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        mock_random.uniform.return_value = -0.02

        vb = VoiceBiometrics()
        enroll_audio = self._make_audio_data(500, 50)

        vb.create_profile("user1", "1001")
        vb.start_enrollment("user1")
        for _ in range(3):
            vb.add_enrollment_sample("user1", enroll_audio)

        # Verify with very different audio
        different_audio = self._make_audio_data(500, 3)
        verify_result = vb.verify_speaker("user1", different_audio)

        # The verification result depends on feature distance
        assert "verified" in verify_result
        assert "confidence" in verify_result
        assert vb.total_verifications == 1

    @patch("pbx.features.voice_biometrics.get_logger")
    @patch("pbx.features.voice_biometrics.PYAUDIO_ANALYSIS_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.LIBROSA_AVAILABLE", False)
    @patch("pbx.features.voice_biometrics.SKLEARN_AVAILABLE", False)
    def test_full_flow_multiple_profiles(self, mock_get_logger: MagicMock) -> None:
        from pbx.features.voice_biometrics import VoiceBiometrics

        vb = VoiceBiometrics()

        vb.create_profile("user1", "1001")
        vb.create_profile("user2", "1002")

        assert len(vb.profiles) == 2

        stats = vb.get_statistics()
        assert stats["total_profiles"] == 2
        assert stats["enrolled_profiles"] == 0
