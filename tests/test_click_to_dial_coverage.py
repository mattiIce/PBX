"""Comprehensive tests for click_to_dial feature module."""

import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.click_to_dial import ClickToDialEngine


@pytest.mark.unit
class TestClickToDialInit:
    """Tests for ClickToDialEngine initialization."""

    @patch("pbx.features.click_to_dial.get_logger")
    def test_default_initialization(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        config = {"click_to_dial.enabled": True}
        engine = ClickToDialEngine(db_backend=mock_db, config=config)
        assert engine.db is mock_db
        assert engine.config == config
        assert engine.enabled is True
        assert engine.pbx_core is None

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initialization_with_pbx_core(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_pbx = MagicMock()
        engine = ClickToDialEngine(db_backend=mock_db, config={}, pbx_core=mock_pbx)
        assert engine.pbx_core is mock_pbx

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initialization_disabled(self, mock_logger: MagicMock) -> None:
        engine = ClickToDialEngine(db_backend=MagicMock(), config={})
        assert engine.enabled is True  # Default when key not found in dict.get


@pytest.mark.unit
class TestGetConfig:
    """Tests for get_config method."""

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_config_found(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        row = (1, "1001", True, "+15551234567", False, True)
        mock_db.execute.return_value = [row]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.get_config("1001")
        assert result is not None
        assert result["extension"] == "1001"
        assert result["enabled"] is True
        assert result["default_caller_id"] == "+15551234567"
        assert result["auto_answer"] is False
        assert result["browser_notification"] is True

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_config_not_found(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.get_config("9999")
        assert result is None

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_config_none_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = None
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.get_config("1001")
        assert result is None

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_config_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        row = (1, "1001", True, None, True, False)
        mock_db.execute.return_value = [row]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.get_config("1001")
        assert result is not None
        call_args = mock_db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_config_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Query error")
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.get_config("1001")
        assert result is None

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_config_value_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = ValueError("Bad value")
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.get_config("1001")
        assert result is None


@pytest.mark.unit
class TestUpdateConfig:
    """Tests for update_config method."""

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_existing_config(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        # get_config returns existing config
        existing_row = (1, "1001", True, None, False, True)
        mock_db.execute.return_value = [existing_row]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        new_config = {
            "enabled": True,
            "default_caller_id": "+15559999999",
            "auto_answer": True,
            "browser_notification": False,
        }
        result = engine.update_config("1001", new_config)
        assert result is True
        # Should have called execute twice: once for get_config, once for update
        assert mock_db.execute.call_count == 2

    @patch("pbx.features.click_to_dial.get_logger")
    def test_insert_new_config(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        # get_config returns nothing (no existing)
        mock_db.execute.side_effect = [
            [],  # get_config SELECT
            None,  # INSERT
        ]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        new_config = {
            "enabled": True,
            "default_caller_id": "+15551234567",
        }
        result = engine.update_config("1001", new_config)
        assert result is True

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_config_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        existing_row = (1, "1001", True, None, False, True)
        mock_db.execute.return_value = [existing_row]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.update_config("1001", {"enabled": True})
        assert result is True
        # Check that the UPDATE query used %s
        update_call = mock_db.execute.call_args_list[1]
        assert "%s" in update_call[0][0]

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_config_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Update failed")
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.update_config("1001", {"enabled": True})
        assert result is False

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_config_defaults(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = [[], None]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.update_config("1001", {})
        assert result is True
        # Check defaults were used in the INSERT
        insert_call = mock_db.execute.call_args_list[1]
        params = insert_call[0][1]
        assert params[1] is True  # enabled default
        assert params[3] is False  # auto_answer default
        assert params[4] is True  # browser_notification default


@pytest.mark.unit
class TestInitiateCall:
    """Tests for initiate_call method."""

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initiate_call_framework_mode(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        call_id = engine.initiate_call("1001", "5559999")
        assert call_id is not None
        assert call_id.startswith("c2d-1001-")
        mock_db.execute.assert_called_once()

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initiate_call_with_source(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        call_id = engine.initiate_call("1001", "5559999", source="crm")
        assert call_id is not None
        # Check source was passed in INSERT
        call_args = mock_db.execute.call_args
        assert "crm" in call_args[0][1]

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initiate_call_with_pbx_core(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_pbx = MagicMock()
        mock_call = MagicMock()
        mock_pbx.call_manager.create_call.return_value = mock_call
        engine = ClickToDialEngine(db_backend=mock_db, config={}, pbx_core=mock_pbx)
        call_id = engine.initiate_call("1001", "5559999")
        assert call_id is not None
        mock_pbx.call_manager.create_call.assert_called_once()
        mock_call.start.assert_called_once()

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initiate_call_pbx_core_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_pbx = MagicMock()
        mock_pbx.call_manager.create_call.side_effect = ValueError("Call creation failed")
        engine = ClickToDialEngine(db_backend=mock_db, config={}, pbx_core=mock_pbx)
        call_id = engine.initiate_call("1001", "5559999")
        # Falls back to framework mode
        assert call_id is not None

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initiate_call_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = KeyError("DB key error")
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        call_id = engine.initiate_call("1001", "5559999")
        assert call_id is None

    @patch("pbx.features.click_to_dial.get_logger")
    def test_initiate_call_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        call_id = engine.initiate_call("1001", "5559999")
        assert call_id is not None
        call_args = mock_db.execute.call_args
        assert "%s" in call_args[0][0]


@pytest.mark.unit
class TestUpdateCallStatus:
    """Tests for update_call_status method."""

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_status_without_connected_at(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.update_call_status("c2d-1001-123", "ringing")
        assert result is True
        call_args = mock_db.execute.call_args
        assert call_args[0][1] == ("ringing", "c2d-1001-123")

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_status_with_connected_at(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        connected = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        result = engine.update_call_status("c2d-1001-123", "connected", connected_at=connected)
        assert result is True
        call_args = mock_db.execute.call_args
        assert call_args[0][1] == ("connected", connected, "c2d-1001-123")

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_status_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.update_call_status("c2d-1001-123", "completed")
        assert result is True
        call_args = mock_db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.click_to_dial.get_logger")
    def test_update_status_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Update failed")
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        result = engine.update_call_status("c2d-1001-123", "failed")
        assert result is False


@pytest.mark.unit
class TestGetCallHistory:
    """Tests for get_call_history method."""

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_call_history(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        row1 = (1, "1001", "5559999", "c2d-1001-100", "web", "2026-02-17T10:00:00", None, "initiated")
        row2 = (2, "1001", "5558888", "c2d-1001-101", "crm", "2026-02-17T11:00:00", "2026-02-17T11:00:05", "connected")
        mock_db.execute.return_value = [row1, row2]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        history = engine.get_call_history("1001")
        assert len(history) == 2
        assert history[0]["destination"] == "5559999"
        assert history[0]["source"] == "web"
        assert history[1]["status"] == "connected"

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_call_history_with_limit(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        engine.get_call_history("1001", limit=50)
        call_args = mock_db.execute.call_args
        assert call_args[0][1] == ("1001", 50)

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_call_history_empty(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        history = engine.get_call_history("9999")
        assert history == []

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_call_history_none_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = None
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        history = engine.get_call_history("1001")
        assert history == []

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_call_history_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Query error")
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        history = engine.get_call_history("1001")
        assert history == []

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_call_history_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_db.execute.return_value = []
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        engine.get_call_history("1001")
        call_args = mock_db.execute.call_args
        assert "%s" in call_args[0][0]


@pytest.mark.unit
class TestGetAllConfigs:
    """Tests for get_all_configs method."""

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_all_configs(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        row1 = (1, "1001", True, "+15551111", False, True)
        row2 = (2, "1002", False, None, True, False)
        mock_db.execute.return_value = [row1, row2]
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        configs = engine.get_all_configs()
        assert len(configs) == 2
        assert configs[0]["extension"] == "1001"
        assert configs[0]["enabled"] is True
        assert configs[1]["extension"] == "1002"
        assert configs[1]["enabled"] is False

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_all_configs_empty(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.return_value = []
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        configs = engine.get_all_configs()
        assert configs == []

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_all_configs_none_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.return_value = None
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        configs = engine.get_all_configs()
        assert configs == []

    @patch("pbx.features.click_to_dial.get_logger")
    def test_get_all_configs_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.side_effect = sqlite3.Error("Error")
        engine = ClickToDialEngine(db_backend=mock_db, config={})
        configs = engine.get_all_configs()
        assert configs == []
