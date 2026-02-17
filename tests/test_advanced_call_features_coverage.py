"""
Tests for Advanced Call Features
Comprehensive coverage of AdvancedCallFeatures (whisper, barge-in, monitor)
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.advanced_call_features import AdvancedCallFeatures


@pytest.mark.unit
class TestAdvancedCallFeaturesInit:
    """Test AdvancedCallFeatures initialization"""

    @patch("pbx.features.advanced_call_features.get_logger")
    def test_init_enabled_with_supervisors(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with enabled config and supervisor permissions"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001", "1002"],
                        },
                        {
                            "supervisor_id": "sup2",
                            "monitored_extensions": ["*"],
                        },
                    ],
                }
            }
        }
        acf = AdvancedCallFeatures(config)

        assert acf.enabled is True
        assert acf.monitored_calls == {}
        assert "sup1" in acf.supervisor_permissions
        assert acf.supervisor_permissions["sup1"] == {"1001", "1002"}
        assert acf.supervisor_permissions["sup2"] == {"*"}
        mock_get_logger.return_value.info.assert_called()

    @patch("pbx.features.advanced_call_features.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with disabled config"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": False,
                }
            }
        }
        acf = AdvancedCallFeatures(config)

        assert acf.enabled is False
        assert acf.supervisor_permissions == {}

    @patch("pbx.features.advanced_call_features.get_logger")
    def test_init_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with None config"""
        acf = AdvancedCallFeatures(None)

        assert acf.enabled is False
        assert acf.config == {}
        assert acf.monitored_calls == {}

    @patch("pbx.features.advanced_call_features.get_logger")
    def test_init_empty_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with empty config"""
        acf = AdvancedCallFeatures({})

        assert acf.enabled is False

    @patch("pbx.features.advanced_call_features.get_logger")
    def test_init_no_config_arg(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with no config argument (default)"""
        acf = AdvancedCallFeatures()

        assert acf.enabled is False
        assert acf.config == {}

    @patch("pbx.features.advanced_call_features.get_logger")
    def test_init_missing_features_key(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with config missing 'features' key"""
        acf = AdvancedCallFeatures({"other_key": True})

        assert acf.enabled is False

    @patch("pbx.features.advanced_call_features.get_logger")
    def test_init_supervisors_empty_extensions(self, mock_get_logger: MagicMock) -> None:
        """Test init with supervisor having no monitored_extensions"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {"supervisor_id": "sup1"},
                    ],
                }
            }
        }
        acf = AdvancedCallFeatures(config)

        assert acf.supervisor_permissions["sup1"] == set()


@pytest.mark.unit
class TestAdvancedCallFeaturesCanMonitor:
    """Test AdvancedCallFeatures.can_monitor"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001", "1002"],
                        },
                        {
                            "supervisor_id": "sup_all",
                            "monitored_extensions": ["*"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_can_monitor_allowed_extension(self) -> None:
        """Test supervisor can monitor allowed extension"""
        assert self.acf.can_monitor("sup1", "1001") is True
        assert self.acf.can_monitor("sup1", "1002") is True

    def test_can_monitor_denied_extension(self) -> None:
        """Test supervisor cannot monitor unlisted extension"""
        assert self.acf.can_monitor("sup1", "1003") is False

    def test_can_monitor_wildcard(self) -> None:
        """Test supervisor with wildcard can monitor any extension"""
        assert self.acf.can_monitor("sup_all", "1001") is True
        assert self.acf.can_monitor("sup_all", "9999") is True

    def test_can_monitor_unknown_supervisor(self) -> None:
        """Test unknown supervisor cannot monitor"""
        assert self.acf.can_monitor("unknown", "1001") is False


@pytest.mark.unit
class TestAdvancedCallFeaturesWhisper:
    """Test AdvancedCallFeatures.start_whisper"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001", "1002"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_start_whisper_success(self) -> None:
        """Test starting whisper mode successfully"""
        result = self.acf.start_whisper("call-1", "sup1", "1001")

        assert result["call_id"] == "call-1"
        assert result["mode"] == "whisper"
        assert result["status"] == "active"
        assert "call-1" in self.acf.monitored_calls
        assert self.acf.monitored_calls["call-1"]["mode"] == "whisper"
        assert self.acf.monitored_calls["call-1"]["audio_mode"] == "supervisor_to_agent_only"

    def test_start_whisper_not_enabled(self) -> None:
        """Test whisper when feature is not enabled"""
        with patch("pbx.features.advanced_call_features.get_logger"):
            acf = AdvancedCallFeatures({"features": {"advanced_call_features": {"enabled": False}}})

        result = acf.start_whisper("call-1", "sup1", "1001")

        assert "error" in result
        assert "not enabled" in result["error"]

    def test_start_whisper_permission_denied(self) -> None:
        """Test whisper with unauthorized supervisor"""
        result = self.acf.start_whisper("call-1", "sup1", "9999")

        assert "error" in result
        assert "Permission denied" in result["error"]

    def test_start_whisper_unknown_supervisor(self) -> None:
        """Test whisper with unknown supervisor"""
        result = self.acf.start_whisper("call-1", "unknown_sup", "1001")

        assert "error" in result
        assert "Permission denied" in result["error"]

    def test_start_whisper_records_timestamp(self) -> None:
        """Test whisper records start timestamp"""
        self.acf.start_whisper("call-1", "sup1", "1001")

        info = self.acf.monitored_calls["call-1"]
        assert isinstance(info["started_at"], datetime)
        assert info["started_at"].tzinfo is not None


@pytest.mark.unit
class TestAdvancedCallFeaturesBargeIn:
    """Test AdvancedCallFeatures.start_barge_in"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_start_barge_in_success(self) -> None:
        """Test starting barge-in mode successfully"""
        result = self.acf.start_barge_in("call-1", "sup1", "1001")

        assert result["call_id"] == "call-1"
        assert result["mode"] == "barge"
        assert result["status"] == "active"
        assert self.acf.monitored_calls["call-1"]["mode"] == "barge"
        assert self.acf.monitored_calls["call-1"]["audio_mode"] == "three_way_conference"

    def test_start_barge_in_not_enabled(self) -> None:
        """Test barge-in when feature is not enabled"""
        with patch("pbx.features.advanced_call_features.get_logger"):
            acf = AdvancedCallFeatures({"features": {"advanced_call_features": {"enabled": False}}})

        result = acf.start_barge_in("call-1", "sup1", "1001")

        assert "error" in result

    def test_start_barge_in_permission_denied(self) -> None:
        """Test barge-in with unauthorized extension"""
        result = self.acf.start_barge_in("call-1", "sup1", "9999")

        assert "error" in result
        assert "Permission denied" in result["error"]

    def test_start_barge_in_records_supervisor(self) -> None:
        """Test barge-in records supervisor ID"""
        self.acf.start_barge_in("call-1", "sup1", "1001")

        info = self.acf.monitored_calls["call-1"]
        assert info["supervisor_id"] == "sup1"
        assert info["agent_extension"] == "1001"


@pytest.mark.unit
class TestAdvancedCallFeaturesMonitor:
    """Test AdvancedCallFeatures.start_monitor"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_start_monitor_success(self) -> None:
        """Test starting silent monitor successfully"""
        result = self.acf.start_monitor("call-1", "sup1", "1001")

        assert result["call_id"] == "call-1"
        assert result["mode"] == "monitor"
        assert result["status"] == "active"
        assert self.acf.monitored_calls["call-1"]["audio_mode"] == "supervisor_listen_only"

    def test_start_monitor_not_enabled(self) -> None:
        """Test monitor when feature is not enabled"""
        with patch("pbx.features.advanced_call_features.get_logger"):
            acf = AdvancedCallFeatures({"features": {"advanced_call_features": {"enabled": False}}})

        result = acf.start_monitor("call-1", "sup1", "1001")

        assert "error" in result

    def test_start_monitor_permission_denied(self) -> None:
        """Test monitor with unauthorized supervisor"""
        result = self.acf.start_monitor("call-1", "sup1", "9999")

        assert "error" in result
        assert "Permission denied" in result["error"]


@pytest.mark.unit
class TestAdvancedCallFeaturesStopMonitoring:
    """Test AdvancedCallFeatures.stop_monitoring"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_stop_monitoring_active_call(self) -> None:
        """Test stopping monitoring on an active call"""
        self.acf.start_whisper("call-1", "sup1", "1001")

        result = self.acf.stop_monitoring("call-1")

        assert result is True
        assert "call-1" not in self.acf.monitored_calls

    def test_stop_monitoring_nonexistent_call(self) -> None:
        """Test stopping monitoring on a call that is not monitored"""
        result = self.acf.stop_monitoring("nonexistent")

        assert result is False

    def test_stop_monitoring_removes_from_dict(self) -> None:
        """Test that stopping removes the call from monitored_calls"""
        self.acf.start_barge_in("call-1", "sup1", "1001")
        assert "call-1" in self.acf.monitored_calls

        self.acf.stop_monitoring("call-1")

        assert "call-1" not in self.acf.monitored_calls

    def test_stop_monitoring_idempotent(self) -> None:
        """Test stopping monitoring twice returns False on second call"""
        self.acf.start_monitor("call-1", "sup1", "1001")
        self.acf.stop_monitoring("call-1")

        result = self.acf.stop_monitoring("call-1")

        assert result is False


@pytest.mark.unit
class TestAdvancedCallFeaturesGetMonitoringInfo:
    """Test AdvancedCallFeatures.get_monitoring_info"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_get_monitoring_info_exists(self) -> None:
        """Test getting monitoring info for a monitored call"""
        self.acf.start_whisper("call-1", "sup1", "1001")

        result = self.acf.get_monitoring_info("call-1")

        assert result is not None
        assert result["mode"] == "whisper"
        assert result["supervisor_id"] == "sup1"
        assert result["agent_extension"] == "1001"

    def test_get_monitoring_info_not_found(self) -> None:
        """Test getting monitoring info for unmonitored call"""
        result = self.acf.get_monitoring_info("nonexistent")

        assert result is None


@pytest.mark.unit
class TestAdvancedCallFeaturesListMonitoredCalls:
    """Test AdvancedCallFeatures.list_monitored_calls"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001", "1002"],
                        },
                        {
                            "supervisor_id": "sup2",
                            "monitored_extensions": ["1003"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_list_all_monitored_calls(self) -> None:
        """Test listing all monitored calls without filter"""
        self.acf.start_whisper("call-1", "sup1", "1001")
        self.acf.start_barge_in("call-2", "sup2", "1003")

        result = self.acf.list_monitored_calls()

        assert len(result) == 2
        call_ids = {c["call_id"] for c in result}
        assert "call-1" in call_ids
        assert "call-2" in call_ids

    def test_list_monitored_calls_filtered_by_supervisor(self) -> None:
        """Test listing monitored calls filtered by supervisor"""
        self.acf.start_whisper("call-1", "sup1", "1001")
        self.acf.start_barge_in("call-2", "sup2", "1003")

        result = self.acf.list_monitored_calls("sup1")

        assert len(result) == 1
        assert result[0]["call_id"] == "call-1"
        assert result[0]["supervisor_id"] == "sup1"

    def test_list_monitored_calls_empty(self) -> None:
        """Test listing when no calls are monitored"""
        result = self.acf.list_monitored_calls()

        assert result == []

    def test_list_monitored_calls_contains_duration(self) -> None:
        """Test that listed calls include duration"""
        self.acf.start_whisper("call-1", "sup1", "1001")

        result = self.acf.list_monitored_calls()

        assert len(result) == 1
        assert "duration" in result[0]
        assert result[0]["duration"] >= 0

    def test_list_monitored_calls_contains_mode(self) -> None:
        """Test that listed calls include the correct mode"""
        self.acf.start_whisper("call-1", "sup1", "1001")
        self.acf.start_barge_in("call-2", "sup1", "1002")

        result = self.acf.list_monitored_calls("sup1")

        modes = {c["mode"] for c in result}
        assert "whisper" in modes
        assert "barge" in modes

    def test_list_monitored_calls_no_match_for_supervisor(self) -> None:
        """Test listing when no calls match the supervisor filter"""
        self.acf.start_whisper("call-1", "sup1", "1001")

        result = self.acf.list_monitored_calls("sup2")

        assert result == []


@pytest.mark.unit
class TestAdvancedCallFeaturesPermissions:
    """Test AdvancedCallFeatures permission management"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_add_supervisor_permission_new(self) -> None:
        """Test adding permissions for a new supervisor"""
        result = self.acf.add_supervisor_permission("sup1", ["1001", "1002"])

        assert result is True
        assert self.acf.supervisor_permissions["sup1"] == {"1001", "1002"}

    def test_add_supervisor_permission_existing(self) -> None:
        """Test adding permissions to an existing supervisor"""
        self.acf.add_supervisor_permission("sup1", ["1001"])
        result = self.acf.add_supervisor_permission("sup1", ["1002", "1003"])

        assert result is True
        assert self.acf.supervisor_permissions["sup1"] == {"1001", "1002", "1003"}

    def test_add_supervisor_permission_disabled(self) -> None:
        """Test adding permissions when feature is disabled"""
        with patch("pbx.features.advanced_call_features.get_logger"):
            acf = AdvancedCallFeatures({"features": {"advanced_call_features": {"enabled": False}}})

        result = acf.add_supervisor_permission("sup1", ["1001"])

        assert result is False

    def test_add_supervisor_permission_wildcard(self) -> None:
        """Test adding wildcard permission"""
        result = self.acf.add_supervisor_permission("sup1", ["*"])

        assert result is True
        assert "*" in self.acf.supervisor_permissions["sup1"]

    def test_remove_supervisor_permission_success(self) -> None:
        """Test removing permissions from a supervisor"""
        self.acf.add_supervisor_permission("sup1", ["1001", "1002", "1003"])

        result = self.acf.remove_supervisor_permission("sup1", ["1002"])

        assert result is True
        assert "1002" not in self.acf.supervisor_permissions["sup1"]
        assert "1001" in self.acf.supervisor_permissions["sup1"]
        assert "1003" in self.acf.supervisor_permissions["sup1"]

    def test_remove_supervisor_permission_nonexistent_supervisor(self) -> None:
        """Test removing permissions for a supervisor that does not exist"""
        result = self.acf.remove_supervisor_permission("unknown", ["1001"])

        assert result is False

    def test_remove_supervisor_permission_disabled(self) -> None:
        """Test removing permissions when feature is disabled"""
        with patch("pbx.features.advanced_call_features.get_logger"):
            acf = AdvancedCallFeatures({"features": {"advanced_call_features": {"enabled": False}}})

        result = acf.remove_supervisor_permission("sup1", ["1001"])

        assert result is False

    def test_remove_supervisor_permission_nonexistent_extension(self) -> None:
        """Test removing an extension that is not in the set"""
        self.acf.add_supervisor_permission("sup1", ["1001"])

        result = self.acf.remove_supervisor_permission("sup1", ["9999"])

        assert result is True
        assert self.acf.supervisor_permissions["sup1"] == {"1001"}


@pytest.mark.unit
class TestAdvancedCallFeaturesStatistics:
    """Test AdvancedCallFeatures.get_statistics"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001", "1002"],
                        },
                        {
                            "supervisor_id": "sup2",
                            "monitored_extensions": ["1003"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_statistics_no_active_calls(self) -> None:
        """Test statistics with no active monitoring sessions"""
        stats = self.acf.get_statistics()

        assert stats["enabled"] is True
        assert stats["active_monitoring_sessions"] == 0
        assert stats["supervisors"] == 2
        assert stats["mode_breakdown"] == {}

    def test_statistics_with_active_calls(self) -> None:
        """Test statistics with active monitoring sessions"""
        self.acf.start_whisper("call-1", "sup1", "1001")
        self.acf.start_barge_in("call-2", "sup1", "1002")
        self.acf.start_monitor("call-3", "sup2", "1003")

        stats = self.acf.get_statistics()

        assert stats["active_monitoring_sessions"] == 3
        assert stats["mode_breakdown"]["whisper"] == 1
        assert stats["mode_breakdown"]["barge"] == 1
        assert stats["mode_breakdown"]["monitor"] == 1

    def test_statistics_after_stop(self) -> None:
        """Test statistics after stopping a monitoring session"""
        self.acf.start_whisper("call-1", "sup1", "1001")
        self.acf.stop_monitoring("call-1")

        stats = self.acf.get_statistics()

        assert stats["active_monitoring_sessions"] == 0
        assert stats["mode_breakdown"] == {}

    def test_statistics_disabled(self) -> None:
        """Test statistics when feature is disabled"""
        with patch("pbx.features.advanced_call_features.get_logger"):
            acf = AdvancedCallFeatures({"features": {"advanced_call_features": {"enabled": False}}})

        stats = acf.get_statistics()

        assert stats["enabled"] is False
        assert stats["active_monitoring_sessions"] == 0
        assert stats["supervisors"] == 0

    def test_statistics_multiple_same_mode(self) -> None:
        """Test mode breakdown with multiple calls of the same mode"""
        self.acf.start_whisper("call-1", "sup1", "1001")
        self.acf.start_whisper("call-2", "sup1", "1002")

        stats = self.acf.get_statistics()

        assert stats["mode_breakdown"]["whisper"] == 2


@pytest.mark.unit
class TestAdvancedCallFeaturesOverwriteMonitoring:
    """Test overwriting monitoring state for the same call_id"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "advanced_call_features": {
                    "enabled": True,
                    "supervisors": [
                        {
                            "supervisor_id": "sup1",
                            "monitored_extensions": ["1001"],
                        },
                    ],
                }
            }
        }
        with patch("pbx.features.advanced_call_features.get_logger"):
            self.acf = AdvancedCallFeatures(config)

    def test_overwrite_whisper_with_barge(self) -> None:
        """Test that starting barge-in on a whispered call overwrites"""
        self.acf.start_whisper("call-1", "sup1", "1001")
        self.acf.start_barge_in("call-1", "sup1", "1001")

        info = self.acf.get_monitoring_info("call-1")
        assert info["mode"] == "barge"

    def test_overwrite_monitor_with_whisper(self) -> None:
        """Test that starting whisper on a monitored call overwrites"""
        self.acf.start_monitor("call-1", "sup1", "1001")
        self.acf.start_whisper("call-1", "sup1", "1001")

        info = self.acf.get_monitoring_info("call-1")
        assert info["mode"] == "whisper"
