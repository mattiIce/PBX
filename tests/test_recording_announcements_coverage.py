#!/usr/bin/env python3
"""
Comprehensive tests for Recording Announcements (pbx/features/recording_announcements.py)
Covers RecordingAnnouncements class.
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest


@pytest.mark.unit
class TestRecordingAnnouncementsInit:
    """Tests for RecordingAnnouncements initialization"""

    def test_init_defaults_no_config(self) -> None:
        """Test initialization with no config"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements()

        assert ra.enabled is False
        assert ra.announcement_type == "both"
        assert ra.audio_path == "audio/recording_announcement.wav"
        assert (
            ra.announcement_text == "This call may be recorded for quality and training purposes."
        )
        assert ra.require_consent is False
        assert ra.consent_timeout == 10
        assert ra.announcements_played == 0
        assert ra.consent_accepted == 0
        assert ra.consent_declined == 0

    def test_init_with_none_config(self) -> None:
        """Test initialization with explicit None config"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements(config=None)

        assert ra.config == {}
        assert ra.enabled is False

    def test_init_with_none_database(self) -> None:
        """Test initialization with None database"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements(database=None)

        assert ra.database is None

    def test_init_enabled_with_config(self) -> None:
        """Test initialization with full config enabled"""
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": True,
                    "type": "caller",
                    "audio_path": "/custom/announcement.wav",
                    "text": "Custom announcement text",
                    "require_consent": True,
                    "consent_timeout_seconds": 30,
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements(config=config)

        assert ra.enabled is True
        assert ra.announcement_type == "caller"
        assert ra.audio_path == "/custom/announcement.wav"
        assert ra.announcement_text == "Custom announcement text"
        assert ra.require_consent is True
        assert ra.consent_timeout == 30
        mock_logger.info.assert_any_call("Recording announcements initialized")

    def test_init_enabled_logs_type_and_consent(self) -> None:
        """Test that enabled init logs announcement type and consent setting"""
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": True,
                    "type": "callee",
                    "require_consent": True,
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            RecordingAnnouncements(config=config)

        mock_logger.info.assert_any_call("  type: callee")
        mock_logger.info.assert_any_call("  Require consent: True")

    def test_init_with_database_enabled_initializes_schema(self) -> None:
        """Test that schema is initialized when database is available"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        config = {}

        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            _ra = RecordingAnnouncements(config=config, database=mock_db)

        # Should have called cursor.execute for table creation and index
        assert mock_cursor.execute.call_count == 2
        mock_db.connection.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_init_with_database_disabled_skips_schema(self) -> None:
        """Test that schema is not initialized when database is disabled"""
        mock_db = MagicMock()
        mock_db.enabled = False

        config = {}

        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            _ra = RecordingAnnouncements(config=config, database=mock_db)

        mock_db.connection.cursor.assert_not_called()

    def test_init_schema_postgresql(self) -> None:
        """Test schema initialization for postgresql"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        config = {}

        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            RecordingAnnouncements(config=config, database=mock_db)

        # Should use SERIAL PRIMARY KEY for postgresql
        first_execute_arg = mock_cursor.execute.call_args_list[0][0][0]
        assert "SERIAL PRIMARY KEY" in first_execute_arg

    def test_init_schema_sqlite(self) -> None:
        """Test schema initialization for sqlite"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        config = {}

        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            RecordingAnnouncements(config=config, database=mock_db)

        first_execute_arg = mock_cursor.execute.call_args_list[0][0][0]
        assert "AUTOINCREMENT" in first_execute_arg

    def test_init_schema_error_handling(self) -> None:
        """Test schema initialization error is handled gracefully"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("db error")

        config = {}

        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.recording_announcements import RecordingAnnouncements

            # Should not raise
            _ra = RecordingAnnouncements(config=config, database=mock_db)

        mock_logger.error.assert_called_once()
        assert (
            "Error initializing recording announcements schema" in mock_logger.error.call_args[0][0]
        )


@pytest.mark.unit
class TestRecordingAnnouncementsCheckAudioFile:
    """Tests for _check_audio_file"""

    def test_check_audio_file_exists(self) -> None:
        """Test check when audio file exists"""
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": True,
                    "audio_path": "/path/to/audio.wav",
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            mock_path_cls.return_value.exists.return_value = True
            from pbx.features.recording_announcements import RecordingAnnouncements

            RecordingAnnouncements(config=config)

        mock_logger.info.assert_any_call("  Announcement audio: /path/to/audio.wav")

    def test_check_audio_file_not_exists(self) -> None:
        """Test check when audio file does not exist"""
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": True,
                    "audio_path": "/missing/audio.wav",
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            RecordingAnnouncements(config=config)

        mock_logger.warning.assert_any_call("  Announcement audio not found: /missing/audio.wav")


@pytest.mark.unit
class TestRecordingAnnouncementsShouldAnnounce:
    """Tests for should_announce method"""

    def _make_ra(self, enabled=True, announcement_type="both", require_consent=False):
        """Helper to create RecordingAnnouncements instance"""
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": enabled,
                    "type": announcement_type,
                    "require_consent": require_consent,
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger_fn.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            return RecordingAnnouncements(config=config)

    def test_should_announce_disabled(self) -> None:
        """Test should_announce returns False when disabled"""
        ra = self._make_ra(enabled=False)

        assert ra.should_announce("inbound", "automatic") is False

    def test_should_announce_require_consent(self) -> None:
        """Test should_announce returns True when consent required"""
        ra = self._make_ra(require_consent=True)

        assert ra.should_announce("inbound", "automatic") is True
        assert ra.should_announce("outbound", "on_demand") is True

    def test_should_announce_both_type_inbound(self) -> None:
        """Test should_announce with type 'both' on inbound"""
        ra = self._make_ra(announcement_type="both")

        assert ra.should_announce("inbound", "automatic") is True

    def test_should_announce_both_type_outbound(self) -> None:
        """Test should_announce with type 'both' on outbound"""
        ra = self._make_ra(announcement_type="both")

        assert ra.should_announce("outbound", "automatic") is True

    def test_should_announce_caller_type_inbound(self) -> None:
        """Test should_announce with type 'caller' on inbound"""
        ra = self._make_ra(announcement_type="caller")

        assert ra.should_announce("inbound", "automatic") is True

    def test_should_announce_caller_type_outbound(self) -> None:
        """Test should_announce with type 'caller' on outbound (should be False)"""
        ra = self._make_ra(announcement_type="caller")

        assert ra.should_announce("outbound", "automatic") is False

    def test_should_announce_callee_type_outbound(self) -> None:
        """Test should_announce with type 'callee' on outbound"""
        ra = self._make_ra(announcement_type="callee")

        assert ra.should_announce("outbound", "automatic") is True

    def test_should_announce_callee_type_inbound(self) -> None:
        """Test should_announce with type 'callee' on inbound (should be False)"""
        ra = self._make_ra(announcement_type="callee")

        assert ra.should_announce("inbound", "automatic") is False

    def test_should_announce_unknown_type_inbound(self) -> None:
        """Test should_announce with unknown announcement type"""
        ra = self._make_ra(announcement_type="unknown")

        assert ra.should_announce("inbound", "automatic") is False

    def test_should_announce_on_demand_recording(self) -> None:
        """Test should_announce with on_demand recording type"""
        ra = self._make_ra(announcement_type="both")

        assert ra.should_announce("inbound", "on_demand") is True


@pytest.mark.unit
class TestRecordingAnnouncementsPlayAnnouncement:
    """Tests for play_announcement method"""

    def _make_ra(self, enabled=True):
        """Helper to create RecordingAnnouncements instance"""
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": enabled,
                    "require_consent": False,
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger_fn.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            return RecordingAnnouncements(config=config)

    def test_play_announcement_disabled(self) -> None:
        """Test play_announcement when disabled"""
        ra = self._make_ra(enabled=False)

        result = ra.play_announcement("call-123")

        assert result == {"error": "Recording announcements not enabled"}

    def test_play_announcement_success(self) -> None:
        """Test successful announcement playback"""
        ra = self._make_ra(enabled=True)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            result = ra.play_announcement("call-123", party="both")

        assert result["call_id"] == "call-123"
        assert result["announcement_played"] is True
        assert result["party"] == "both"
        assert result["text"] == "This call may be recorded for quality and training purposes."
        assert "timestamp" in result
        assert ra.announcements_played == 1

    def test_play_announcement_with_audio_file(self) -> None:
        """Test announcement with existing audio file"""
        ra = self._make_ra(enabled=True)
        ra.audio_path = "/path/to/audio.wav"

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            result = ra.play_announcement("call-456")

        assert result["audio_file"] == "/path/to/audio.wav"

    def test_play_announcement_no_audio_file(self) -> None:
        """Test announcement without audio file"""
        ra = self._make_ra(enabled=True)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            result = ra.play_announcement("call-789")

        assert result["audio_file"] is None

    def test_play_announcement_increments_counter(self) -> None:
        """Test that playing announcement increments counter"""
        ra = self._make_ra(enabled=True)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            ra.play_announcement("call-1")
            ra.play_announcement("call-2")
            ra.play_announcement("call-3")

        assert ra.announcements_played == 3

    def test_play_announcement_default_party(self) -> None:
        """Test announcement with default party parameter"""
        ra = self._make_ra(enabled=True)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            result = ra.play_announcement("call-123")

        assert result["party"] == "both"

    def test_play_announcement_caller_party(self) -> None:
        """Test announcement with caller party"""
        ra = self._make_ra(enabled=True)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            result = ra.play_announcement("call-123", party="caller")

        assert result["party"] == "caller"


@pytest.mark.unit
class TestRecordingAnnouncementsLogAnnouncement:
    """Tests for _log_announcement method"""

    def _make_ra_with_db(self, db_type="sqlite"):
        """Helper to create RA with mock db"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = db_type
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        config = {}

        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements(config=config, database=mock_db)

        # Reset mock after init
        mock_db.connection.cursor.reset_mock()
        mock_cursor.reset_mock()
        mock_db.connection.commit.reset_mock()

        return ra, mock_db, mock_cursor

    def test_log_announcement_sqlite(self) -> None:
        """Test logging announcement with sqlite"""
        ra, mock_db, mock_cursor = self._make_ra_with_db("sqlite")

        ra._log_announcement("call-1", "both", True, False, None, False)

        mock_cursor.execute.assert_called_once()
        query = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO recording_announcements_log" in query
        assert "?" in query
        mock_db.connection.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_log_announcement_postgresql(self) -> None:
        """Test logging announcement with postgresql"""
        ra, _mock_db, mock_cursor = self._make_ra_with_db("postgresql")

        ra._log_announcement("call-1", "caller", True, True, True, False)

        mock_cursor.execute.assert_called_once()
        query = mock_cursor.execute.call_args[0][0]
        assert "%s" in query

    def test_log_announcement_no_database(self) -> None:
        """Test logging announcement with no database"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements()

        # Should not raise
        ra._log_announcement("call-1", "both", True, False, None, False)

    def test_log_announcement_database_disabled(self) -> None:
        """Test logging announcement with disabled database"""
        mock_db = MagicMock()
        mock_db.enabled = False

        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements(database=mock_db)

        ra._log_announcement("call-1", "both", True, False, None, False)

        mock_db.connection.cursor.assert_not_called()

    def test_log_announcement_db_error(self) -> None:
        """Test logging announcement with db error"""
        ra, _mock_db, mock_cursor = self._make_ra_with_db("sqlite")
        mock_cursor.execute.side_effect = sqlite3.Error("db error")

        # Should not raise
        ra._log_announcement("call-1", "both", True, False, None, False)

        ra.logger.error.assert_called()

    def test_log_announcement_sqlite_consent_values(self) -> None:
        """Test sqlite boolean conversion for consent values"""
        ra, _mock_db, mock_cursor = self._make_ra_with_db("sqlite")

        ra._log_announcement("call-1", "caller", True, True, True, False)

        args = mock_cursor.execute.call_args[0][1]
        assert args[2] == 1  # announcement_played = True -> 1
        assert args[3] == 1  # consent_required = True -> 1
        assert args[4] == 1  # consent_given = True -> 1
        assert args[5] == 0  # consent_timeout = False -> 0

    def test_log_announcement_sqlite_consent_false(self) -> None:
        """Test sqlite boolean conversion for consent_given=False"""
        ra, _mock_db, mock_cursor = self._make_ra_with_db("sqlite")

        ra._log_announcement("call-1", "caller", True, True, False, False)

        args = mock_cursor.execute.call_args[0][1]
        assert args[4] == 0  # consent_given = False -> 0

    def test_log_announcement_sqlite_consent_none(self) -> None:
        """Test sqlite boolean conversion for consent_given=None"""
        ra, _mock_db, mock_cursor = self._make_ra_with_db("sqlite")

        ra._log_announcement("call-1", "caller", True, True, None, False)

        args = mock_cursor.execute.call_args[0][1]
        assert args[4] is None  # consent_given = None -> None


@pytest.mark.unit
class TestRecordingAnnouncementsRequestConsent:
    """Tests for request_consent method"""

    def _make_ra(self, enabled=True, require_consent=True):
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": enabled,
                    "require_consent": require_consent,
                    "consent_timeout_seconds": 15,
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger_fn.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            return RecordingAnnouncements(config=config)

    def test_request_consent_not_required(self) -> None:
        """Test request_consent when consent not required"""
        ra = self._make_ra(require_consent=False)

        result = ra.request_consent("call-123")

        assert result == {"consent": "not_required"}

    def test_request_consent_disabled(self) -> None:
        """Test request_consent when disabled"""
        ra = self._make_ra(enabled=False)

        result = ra.request_consent("call-123")

        assert result == {"consent": "not_required"}

    def test_request_consent_success(self) -> None:
        """Test successful consent request"""
        ra = self._make_ra(enabled=True, require_consent=True)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            result = ra.request_consent("call-123")

        assert result["call_id"] == "call-123"
        assert result["consent_requested"] is True
        assert result["timeout_seconds"] == 15
        assert "announcement" in result
        assert "instructions" in result
        assert "timestamp" in result

    def test_request_consent_plays_announcement(self) -> None:
        """Test that request_consent plays announcement to caller"""
        ra = self._make_ra(enabled=True, require_consent=True)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            result = ra.request_consent("call-123")

        assert result["announcement"]["party"] == "caller"
        assert ra.announcements_played == 1


@pytest.mark.unit
class TestRecordingAnnouncementsRecordConsentResponse:
    """Tests for record_consent_response method"""

    def _make_ra(self):
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": True,
                    "require_consent": True,
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger_fn.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            return RecordingAnnouncements(config=config)

    def test_record_consent_accepted(self) -> None:
        """Test recording accepted consent"""
        ra = self._make_ra()

        result = ra.record_consent_response("call-123", True)

        assert result is True
        assert ra.consent_accepted == 1
        assert ra.consent_declined == 0

    def test_record_consent_declined(self) -> None:
        """Test recording declined consent"""
        ra = self._make_ra()

        result = ra.record_consent_response("call-123", False)

        assert result is True
        assert ra.consent_accepted == 0
        assert ra.consent_declined == 1

    def test_record_consent_multiple(self) -> None:
        """Test recording multiple consent responses"""
        ra = self._make_ra()

        ra.record_consent_response("call-1", True)
        ra.record_consent_response("call-2", True)
        ra.record_consent_response("call-3", False)

        assert ra.consent_accepted == 2
        assert ra.consent_declined == 1

    def test_record_consent_logs_accepted(self) -> None:
        """Test that accepted consent is logged"""
        ra = self._make_ra()

        ra.record_consent_response("call-123", True)

        ra.logger.info.assert_any_call("Call call-123: Recording consent accepted")

    def test_record_consent_logs_declined(self) -> None:
        """Test that declined consent is logged"""
        ra = self._make_ra()

        ra.record_consent_response("call-123", False)

        ra.logger.info.assert_any_call("Call call-123: Recording consent declined")


@pytest.mark.unit
class TestRecordingAnnouncementsGetAnnouncementConfig:
    """Tests for get_announcement_config method"""

    def test_get_config_disabled(self) -> None:
        """Test getting config when disabled"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements()

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            config = ra.get_announcement_config()

        assert config["enabled"] is False
        assert config["type"] == "both"
        assert config["require_consent"] is False
        assert config["audio_exists"] is False

    def test_get_config_enabled_with_audio(self) -> None:
        """Test getting config when enabled with audio"""
        cfg = {
            "features": {
                "recording_announcements": {
                    "enabled": True,
                    "type": "caller",
                    "require_consent": True,
                    "audio_path": "/path/audio.wav",
                    "text": "Custom text",
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger_fn.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = True
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements(config=cfg)

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            config = ra.get_announcement_config()

        assert config["enabled"] is True
        assert config["type"] == "caller"
        assert config["require_consent"] is True
        assert config["audio_file"] == "/path/audio.wav"
        assert config["text"] == "Custom text"
        assert config["audio_exists"] is True


@pytest.mark.unit
class TestRecordingAnnouncementsUpdateText:
    """Tests for update_announcement_text method"""

    def test_update_text(self) -> None:
        """Test updating announcement text"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements()

        result = ra.update_announcement_text("New announcement text")

        assert result is True
        assert ra.announcement_text == "New announcement text"

    def test_update_text_logs(self) -> None:
        """Test that updating text logs the new text"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements()

        ra.update_announcement_text("Updated text")

        mock_logger.info.assert_called_with("Updated announcement text: Updated text")


@pytest.mark.unit
class TestRecordingAnnouncementsSetAudioFile:
    """Tests for set_audio_file method"""

    def test_set_audio_file_exists(self) -> None:
        """Test setting audio file that exists"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements()

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            result = ra.set_audio_file("/new/audio.wav")

        assert result is True
        assert ra.audio_path == "/new/audio.wav"

    def test_set_audio_file_not_exists(self) -> None:
        """Test setting audio file that does not exist"""
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            ra = RecordingAnnouncements()

        original_path = ra.audio_path

        with patch("pbx.features.recording_announcements.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            result = ra.set_audio_file("/missing/audio.wav")

        assert result is False
        assert ra.audio_path == original_path  # unchanged


@pytest.mark.unit
class TestRecordingAnnouncementsGetStateRequirements:
    """Tests for get_state_requirements method"""

    def _make_ra(self):
        with patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.recording_announcements import RecordingAnnouncements

            return RecordingAnnouncements()

    def test_two_party_state_california(self) -> None:
        """Test California (two-party consent)"""
        ra = self._make_ra()
        result = ra.get_state_requirements("CA")

        assert result["state"] == "CA"
        assert result["consent_type"] == "two_party"
        assert result["notification_required"] is True
        assert "penalty" in result

    def test_two_party_state_florida(self) -> None:
        """Test Florida (two-party consent)"""
        ra = self._make_ra()
        result = ra.get_state_requirements("FL")

        assert result["consent_type"] == "two_party"

    def test_two_party_state_illinois(self) -> None:
        """Test Illinois (two-party consent)"""
        ra = self._make_ra()
        result = ra.get_state_requirements("IL")

        assert result["consent_type"] == "two_party"

    def test_two_party_state_washington(self) -> None:
        """Test Washington (two-party consent)"""
        ra = self._make_ra()
        result = ra.get_state_requirements("WA")

        assert result["consent_type"] == "two_party"

    def test_one_party_state_texas(self) -> None:
        """Test Texas (one-party consent)"""
        ra = self._make_ra()
        result = ra.get_state_requirements("TX")

        assert result["state"] == "TX"
        assert result["consent_type"] == "one_party"
        assert result["notification_required"] is False
        assert "recommendation" in result

    def test_one_party_state_new_york(self) -> None:
        """Test New York (one-party consent)"""
        ra = self._make_ra()
        result = ra.get_state_requirements("NY")

        assert result["consent_type"] == "one_party"

    def test_one_party_state_ohio(self) -> None:
        """Test Ohio (one-party consent)"""
        ra = self._make_ra()
        result = ra.get_state_requirements("OH")

        assert result["consent_type"] == "one_party"

    def test_unknown_state(self) -> None:
        """Test unknown state code"""
        ra = self._make_ra()
        result = ra.get_state_requirements("XX")

        assert result["state"] == "XX"
        assert result["consent_type"] == "unknown"
        assert result["notification_required"] is True  # safe default

    def test_empty_state_code(self) -> None:
        """Test empty state code"""
        ra = self._make_ra()
        result = ra.get_state_requirements("")

        assert result["consent_type"] == "unknown"

    def test_all_two_party_states(self) -> None:
        """Test all two-party consent states"""
        ra = self._make_ra()
        two_party_states = ["CA", "CT", "FL", "IL", "MD", "MA", "MT", "NH", "PA", "WA"]

        for state in two_party_states:
            result = ra.get_state_requirements(state)
            assert result["consent_type"] == "two_party", f"{state} should be two-party"


@pytest.mark.unit
class TestRecordingAnnouncementsGetStatistics:
    """Tests for get_statistics method"""

    def _make_ra(self, enabled=False):
        config = {
            "features": {
                "recording_announcements": {
                    "enabled": enabled,
                }
            }
        }
        with (
            patch("pbx.features.recording_announcements.get_logger") as mock_logger_fn,
            patch("pbx.features.recording_announcements.Path") as mock_path_cls,
        ):
            mock_logger_fn.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = False
            from pbx.features.recording_announcements import RecordingAnnouncements

            return RecordingAnnouncements(config=config)

    def test_get_statistics_initial(self) -> None:
        """Test statistics with no activity"""
        ra = self._make_ra()
        stats = ra.get_statistics()

        assert stats["enabled"] is False
        assert stats["announcements_played"] == 0
        assert stats["consent_requests"] == 0
        assert stats["consent_accepted"] == 0
        assert stats["consent_declined"] == 0
        assert stats["acceptance_rate_percent"] == 0

    def test_get_statistics_with_activity(self) -> None:
        """Test statistics after some activity"""
        ra = self._make_ra(enabled=True)
        ra.announcements_played = 10
        ra.consent_accepted = 7
        ra.consent_declined = 3

        stats = ra.get_statistics()

        assert stats["enabled"] is True
        assert stats["announcements_played"] == 10
        assert stats["consent_requests"] == 10
        assert stats["consent_accepted"] == 7
        assert stats["consent_declined"] == 3
        assert stats["acceptance_rate_percent"] == 70.0

    def test_get_statistics_no_consent_requests(self) -> None:
        """Test statistics when no consent requests made (avoid division by zero)"""
        ra = self._make_ra()
        ra.announcements_played = 5
        ra.consent_accepted = 0
        ra.consent_declined = 0

        stats = ra.get_statistics()

        assert stats["acceptance_rate_percent"] == 0

    def test_get_statistics_acceptance_rate_rounding(self) -> None:
        """Test that acceptance rate is properly rounded"""
        ra = self._make_ra()
        ra.consent_accepted = 1
        ra.consent_declined = 2

        stats = ra.get_statistics()

        assert stats["acceptance_rate_percent"] == 33.33

    def test_get_statistics_all_accepted(self) -> None:
        """Test statistics when all consent is accepted"""
        ra = self._make_ra()
        ra.consent_accepted = 5
        ra.consent_declined = 0

        stats = ra.get_statistics()

        assert stats["acceptance_rate_percent"] == 100.0

    def test_get_statistics_all_declined(self) -> None:
        """Test statistics when all consent is declined"""
        ra = self._make_ra()
        ra.consent_accepted = 0
        ra.consent_declined = 5

        stats = ra.get_statistics()

        assert stats["acceptance_rate_percent"] == 0
