"""Comprehensive tests for pbx/features/auto_attendant.py"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _patch_logger():
    """Patch the logger used by the auto_attendant module."""
    with patch("pbx.features.auto_attendant.get_logger") as mock_logger_fn:
        mock_logger_fn.return_value = MagicMock()
        yield


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_aa.db")


@pytest.fixture
def aa_config(tmp_db, tmp_path):
    """Provide a mock config object for AutoAttendant."""
    config = MagicMock()

    audio_dir = str(tmp_path / "auto_attendant")

    def config_get(key, default=None):
        mapping = {
            "database": {"path": tmp_db},
            "auto_attendant": {
                "enabled": True,
                "extension": "0",
                "timeout": 10,
                "max_retries": 3,
                "audio_path": audio_dir,
                "menu_options": [
                    {"digit": "1", "destination": "1001", "description": "Sales"},
                    {"digit": "2", "destination": "1002", "description": "Support"},
                ],
            },
            "auto_attendant.operator_extension": "1001",
        }
        return mapping.get(key, default)

    config.get.side_effect = config_get
    return config


@pytest.fixture
def auto_attendant(aa_config):
    """Provide an AutoAttendant instance."""
    from pbx.features.auto_attendant import AutoAttendant

    return AutoAttendant(config=aa_config)


# =============================================================================
# AAState and DestinationType Enum Tests
# =============================================================================


@pytest.mark.unit
class TestEnums:
    """Tests for AAState and DestinationType enums."""

    def test_aa_state_values(self) -> None:
        from pbx.features.auto_attendant import AAState

        assert AAState.WELCOME.value == "welcome"
        assert AAState.MAIN_MENU.value == "main_menu"
        assert AAState.SUBMENU.value == "submenu"
        assert AAState.TRANSFERRING.value == "transferring"
        assert AAState.INVALID.value == "invalid"
        assert AAState.TIMEOUT.value == "timeout"
        assert AAState.ENDED.value == "ended"

    def test_destination_type_values(self) -> None:
        from pbx.features.auto_attendant import DestinationType

        assert DestinationType.EXTENSION.value == "extension"
        assert DestinationType.SUBMENU.value == "submenu"
        assert DestinationType.QUEUE.value == "queue"
        assert DestinationType.VOICEMAIL.value == "voicemail"
        assert DestinationType.OPERATOR.value == "operator"


# =============================================================================
# AutoAttendant Init Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantInit:
    """Tests for AutoAttendant initialization."""

    def test_init_with_config(self, auto_attendant) -> None:
        assert auto_attendant.enabled is True
        assert auto_attendant.extension == "0"
        assert auto_attendant.timeout == 10
        assert auto_attendant.max_retries == 3

    def test_init_menu_options_loaded(self, auto_attendant) -> None:
        assert "1" in auto_attendant.menu_options
        assert auto_attendant.menu_options["1"]["destination"] == "1001"
        assert "2" in auto_attendant.menu_options

    def test_init_no_config(self, tmp_path):
        """Test init with None config uses defaults."""
        from pbx.features.auto_attendant import AutoAttendant

        aa = AutoAttendant(config=None)
        assert aa.enabled is True
        assert aa.extension == "0"
        assert aa.timeout == 10
        assert aa.max_retries == 3

    def test_init_creates_audio_directory(self, auto_attendant) -> None:
        assert Path(auto_attendant.audio_path).exists()

    def test_init_db_tables_created(self, auto_attendant, tmp_db) -> None:
        import sqlite3

        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "auto_attendant_config" in tables
        assert "auto_attendant_menu_options" in tables
        assert "auto_attendant_menus" in tables
        assert "auto_attendant_menu_items" in tables

    def test_init_main_menu_created(self, auto_attendant, tmp_db) -> None:
        import sqlite3

        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM auto_attendant_menus WHERE menu_id = 'main'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1

    def test_init_loads_config_from_db_on_second_run(self, aa_config, tmp_db) -> None:
        from pbx.features.auto_attendant import AutoAttendant

        # First init saves config to db
        _aa1 = AutoAttendant(config=aa_config)

        # Second init should load from db
        aa2 = AutoAttendant(config=aa_config)
        assert aa2.enabled is True
        assert aa2.extension == "0"

    def test_init_db_error_handled(self, tmp_path) -> None:
        from pbx.features.auto_attendant import AutoAttendant

        config = MagicMock()
        # Point to an invalid path
        config.get.side_effect = lambda key, default=None: {
            "database": {"path": "/nonexistent/path/db.sqlite"},
            "auto_attendant": {},
        }.get(key, default)

        # Should not raise
        _aa = AutoAttendant(config=config)


# =============================================================================
# Config Management Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantConfigManagement:
    """Tests for configuration management."""

    def test_update_config_enabled(self, auto_attendant) -> None:
        auto_attendant.update_config(enabled=False)
        assert auto_attendant.enabled is False

    def test_update_config_extension(self, auto_attendant) -> None:
        auto_attendant.update_config(extension="99")
        assert auto_attendant.extension == "99"

    def test_update_config_timeout(self, auto_attendant) -> None:
        auto_attendant.update_config(timeout=30)
        assert auto_attendant.timeout == 30

    def test_update_config_max_retries(self, auto_attendant) -> None:
        auto_attendant.update_config(max_retries=5)
        assert auto_attendant.max_retries == 5

    def test_update_config_audio_path(self, auto_attendant) -> None:
        auto_attendant.update_config(audio_path="/new/path")
        assert auto_attendant.audio_path == "/new/path"

    def test_update_config_multiple(self, auto_attendant) -> None:
        auto_attendant.update_config(enabled=False, timeout=20)
        assert auto_attendant.enabled is False
        assert auto_attendant.timeout == 20

    def test_is_enabled(self, auto_attendant) -> None:
        assert auto_attendant.is_enabled() is True
        auto_attendant.enabled = False
        assert auto_attendant.is_enabled() is False

    def test_get_extension(self, auto_attendant) -> None:
        assert auto_attendant.get_extension() == "0"


# =============================================================================
# Menu Option Management Tests (Legacy)
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantLegacyMenuOptions:
    """Tests for legacy menu option management."""

    def test_add_menu_option(self, auto_attendant) -> None:
        result = auto_attendant.add_menu_option("3", "1003", "Billing")
        assert result is True
        assert "3" in auto_attendant.menu_options
        assert auto_attendant.menu_options["3"]["destination"] == "1003"

    def test_add_menu_option_disabled(self, auto_attendant) -> None:
        auto_attendant.enabled = False
        result = auto_attendant.add_menu_option("3", "1003", "Billing")
        assert result is False

    def test_remove_menu_option(self, auto_attendant) -> None:
        auto_attendant.add_menu_option("3", "1003", "Billing")
        result = auto_attendant.remove_menu_option("3")
        assert result is True
        assert "3" not in auto_attendant.menu_options

    def test_remove_menu_option_nonexistent(self, auto_attendant) -> None:
        result = auto_attendant.remove_menu_option("9")
        assert result is False

    def test_remove_menu_option_disabled(self, auto_attendant) -> None:
        auto_attendant.enabled = False
        result = auto_attendant.remove_menu_option("1")
        assert result is False

    def test_get_menu_text(self, auto_attendant) -> None:
        text = auto_attendant.get_menu_text()
        assert "Auto Attendant Menu:" in text
        assert "Sales" in text
        assert "Support" in text


# =============================================================================
# Hierarchical Menu Management Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantMenuManagement:
    """Tests for hierarchical menu management."""

    def test_create_menu(self, auto_attendant) -> None:
        result = auto_attendant.create_menu("support", "main", "Support Menu", "Press 1 for...")
        assert result is True

    def test_create_menu_with_audio_file(self, auto_attendant) -> None:
        result = auto_attendant.create_menu(
            "billing", "main", "Billing Menu", audio_file="/path/to/billing.wav"
        )
        assert result is True

    def test_create_menu_duplicate(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant.create_menu("support", "main", "Support Again")
        assert result is False

    def test_create_menu_max_depth_exceeded(self, auto_attendant) -> None:
        # Create a chain of 5 levels
        auto_attendant.create_menu("l1", "main", "Level 1")
        auto_attendant.create_menu("l2", "l1", "Level 2")
        auto_attendant.create_menu("l3", "l2", "Level 3")
        auto_attendant.create_menu("l4", "l3", "Level 4")

        # Level 5 should fail (depth >= 5)
        result = auto_attendant.create_menu("l5", "l4", "Level 5")
        assert result is False

    def test_create_menu_circular_reference(self, auto_attendant) -> None:
        auto_attendant.create_menu("a", "main", "Menu A")
        # Try to create a menu that would create a circular reference
        result = auto_attendant.create_menu("main", "a", "Main under A")
        # This tests the IntegrityError path since "main" already exists
        assert result is False

    def test_would_create_circular_reference_self(self, auto_attendant) -> None:
        result = auto_attendant._would_create_circular_reference("a", "a")
        assert result is True

    def test_would_create_circular_reference_chain(self, auto_attendant) -> None:
        auto_attendant.create_menu("a", "main", "A")
        auto_attendant.create_menu("b", "a", "B")
        # Check if making "main" parent of something pointing to "main"
        result = auto_attendant._would_create_circular_reference("main", "b")
        assert result is True

    def test_would_not_create_circular_reference(self, auto_attendant) -> None:
        auto_attendant.create_menu("a", "main", "A")
        result = auto_attendant._would_create_circular_reference("c", "a")
        assert result is False

    def test_update_menu(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant.update_menu("support", menu_name="Support Updated")
        assert result is True
        menu = auto_attendant.get_menu("support")
        assert menu["menu_name"] == "Support Updated"

    def test_update_menu_prompt_text(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant.update_menu("support", prompt_text="New prompt")
        assert result is True

    def test_update_menu_audio_file(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant.update_menu("support", audio_file="/new/audio.wav")
        assert result is True

    def test_update_menu_nothing_to_update(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant.update_menu("support")
        assert result is True  # Nothing to update, returns True

    def test_delete_menu(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant.delete_menu("support")
        assert result is True

    def test_delete_main_menu_forbidden(self, auto_attendant) -> None:
        result = auto_attendant.delete_menu("main")
        assert result is False

    def test_delete_menu_with_references(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        auto_attendant.add_menu_item("main", "3", "submenu", "support", "Support")
        result = auto_attendant.delete_menu("support")
        assert result is False

    def test_get_menu(self, auto_attendant) -> None:
        menu = auto_attendant.get_menu("main")
        assert menu is not None
        assert menu["menu_id"] == "main"
        assert menu["menu_name"] == "Main Menu"

    def test_get_menu_nonexistent(self, auto_attendant) -> None:
        menu = auto_attendant.get_menu("nonexistent")
        assert menu is None

    def test_list_menus(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        menus = auto_attendant.list_menus()
        assert len(menus) >= 2  # main + support
        menu_ids = [m["menu_id"] for m in menus]
        assert "main" in menu_ids
        assert "support" in menu_ids


@pytest.mark.unit
class TestAutoAttendantMenuItems:
    """Tests for menu item management."""

    def test_add_menu_item_extension(self, auto_attendant) -> None:
        result = auto_attendant.add_menu_item("main", "1", "extension", "1001", "Sales")
        assert result is True

    def test_add_menu_item_queue(self, auto_attendant) -> None:
        result = auto_attendant.add_menu_item("main", "2", "queue", "sales_queue", "Sales Queue")
        assert result is True

    def test_add_menu_item_voicemail(self, auto_attendant) -> None:
        result = auto_attendant.add_menu_item("main", "3", "voicemail", "1001", "Voicemail")
        assert result is True

    def test_add_menu_item_operator(self, auto_attendant) -> None:
        result = auto_attendant.add_menu_item("main", "0", "operator", "1001", "Operator")
        assert result is True

    def test_add_menu_item_submenu(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant.add_menu_item("main", "3", "submenu", "support", "Support")
        assert result is True

    def test_add_menu_item_invalid_type(self, auto_attendant) -> None:
        result = auto_attendant.add_menu_item("main", "5", "invalid_type", "1001")
        assert result is False

    def test_add_menu_item_submenu_nonexistent(self, auto_attendant) -> None:
        result = auto_attendant.add_menu_item("main", "5", "submenu", "nonexistent")
        assert result is False

    def test_remove_menu_item(self, auto_attendant) -> None:
        auto_attendant.add_menu_item("main", "1", "extension", "1001", "Sales")
        result = auto_attendant.remove_menu_item("main", "1")
        assert result is True

    def test_get_menu_items(self, auto_attendant) -> None:
        auto_attendant.add_menu_item("main", "1", "extension", "1001", "Sales")
        auto_attendant.add_menu_item("main", "2", "extension", "1002", "Support")
        items = auto_attendant.get_menu_items("main")
        assert len(items) >= 2

    def test_get_menu_items_empty(self, auto_attendant) -> None:
        auto_attendant.create_menu("empty_menu", "main", "Empty")
        items = auto_attendant.get_menu_items("empty_menu")
        assert items == []


@pytest.mark.unit
class TestAutoAttendantMenuTree:
    """Tests for menu tree retrieval."""

    def test_get_menu_tree_basic(self, auto_attendant) -> None:
        tree = auto_attendant.get_menu_tree()
        assert tree is not None
        assert tree["menu_id"] == "main"
        assert "items" in tree

    def test_get_menu_tree_with_submenu(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        auto_attendant.add_menu_item("main", "3", "submenu", "support", "Support")
        auto_attendant.add_menu_item("support", "1", "extension", "2001", "Tech Support")

        tree = auto_attendant.get_menu_tree()
        submenu_item = next(
            (i for i in tree["items"] if i.get("destination_type") == "submenu"), None
        )
        assert submenu_item is not None
        assert "submenu" in submenu_item

    def test_get_menu_tree_max_depth(self, auto_attendant) -> None:
        result = auto_attendant.get_menu_tree(depth=11)
        assert result is None

    def test_get_menu_tree_nonexistent(self, auto_attendant) -> None:
        result = auto_attendant.get_menu_tree(menu_id="nonexistent")
        assert result is None

    def test_get_menu_depth(self, auto_attendant) -> None:
        assert auto_attendant._get_menu_depth("main") == 0
        auto_attendant.create_menu("l1", "main", "L1")
        assert auto_attendant._get_menu_depth("l1") == 1
        auto_attendant.create_menu("l2", "l1", "L2")
        assert auto_attendant._get_menu_depth("l2") == 2

    def test_get_menu_depth_safety_limit(self, auto_attendant) -> None:
        depth = auto_attendant._get_menu_depth("main", current_depth=11)
        assert depth == 11


# =============================================================================
# Session Management Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantSession:
    """Tests for session management."""

    def test_start_session(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        result = auto_attendant.start_session("call_001", "5551234")
        assert result["action"] == "play"
        assert result["next_state"] == AAState.MAIN_MENU
        assert "session" in result
        session = result["session"]
        assert session["call_id"] == "call_001"
        assert session["state"] == AAState.MAIN_MENU
        assert session["current_menu_id"] == "main"
        assert session["menu_stack"] == []

    def test_end_session(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        result = auto_attendant.start_session("call_001", "5551234")
        session = result["session"]
        auto_attendant.end_session(session)
        assert session["state"] == AAState.ENDED


# =============================================================================
# DTMF Handling Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantDTMF:
    """Tests for DTMF input handling."""

    def _start_session(self, auto_attendant):
        result = auto_attendant.start_session("call_001", "5551234")
        return result["session"]

    def test_handle_dtmf_valid_legacy_option(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = self._start_session(auto_attendant)
        result = auto_attendant.handle_dtmf(session, "1")
        assert result["action"] == "transfer"
        assert result["destination"] == "1001"
        assert session["state"] == AAState.TRANSFERRING

    def test_handle_dtmf_invalid_option(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = self._start_session(auto_attendant)
        _result = auto_attendant.handle_dtmf(session, "7")
        assert session["state"] == AAState.INVALID

    def test_handle_dtmf_star_go_back_at_main(self, auto_attendant) -> None:
        """At main menu with no stack, star treats as invalid."""
        from pbx.features.auto_attendant import AAState

        session = self._start_session(auto_attendant)
        _result = auto_attendant.handle_dtmf(session, "*")
        # At main menu with empty stack, invalid input
        assert session["retry_count"] >= 1

    def test_handle_dtmf_hash_repeat_menu(self, auto_attendant) -> None:
        session = self._start_session(auto_attendant)
        result = auto_attendant.handle_dtmf(session, "#")
        assert result["action"] == "play"

    def test_handle_dtmf_max_retries_transfers_to_operator(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = self._start_session(auto_attendant)
        # First invalid attempt -> retry_count 1, state INVALID
        auto_attendant.handle_dtmf(session, "7")
        # Any key in INVALID state returns to menu
        auto_attendant.handle_dtmf(session, "1")
        # Second invalid attempt -> retry_count 2, state INVALID
        auto_attendant.handle_dtmf(session, "7")
        auto_attendant.handle_dtmf(session, "1")
        # Third invalid attempt -> retry_count 3 >= max_retries -> transfer
        result = auto_attendant.handle_dtmf(session, "7")

        assert result["action"] == "transfer"
        assert result["destination"] == "1001"
        assert session["state"] == AAState.ENDED

    def test_handle_dtmf_in_invalid_state(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = self._start_session(auto_attendant)
        session["state"] = AAState.INVALID
        result = auto_attendant.handle_dtmf(session, "1")
        # Should return to menu
        assert result["action"] == "play"

    def test_handle_dtmf_submenu_navigation(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        auto_attendant.create_menu("support", "main", "Support")
        auto_attendant.add_menu_item("main", "3", "submenu", "support", "Support Menu")

        session = self._start_session(auto_attendant)
        _result = auto_attendant.handle_dtmf(session, "3")
        assert session["state"] == AAState.SUBMENU
        assert session["current_menu_id"] == "support"
        assert "main" in session["menu_stack"]

    def test_handle_dtmf_submenu_go_back(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        auto_attendant.create_menu("support", "main", "Support")
        auto_attendant.add_menu_item("main", "3", "submenu", "support", "Support Menu")

        session = self._start_session(auto_attendant)
        auto_attendant.handle_dtmf(session, "3")  # go to support submenu

        # Now go back with *
        _result = auto_attendant.handle_dtmf(session, "*")
        assert session["current_menu_id"] == "main"
        assert session["state"] == AAState.MAIN_MENU

    def test_handle_dtmf_submenu_go_back_with_9(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        auto_attendant.create_menu("support", "main", "Support")
        auto_attendant.add_menu_item("main", "3", "submenu", "support", "Support Menu")

        session = self._start_session(auto_attendant)
        auto_attendant.handle_dtmf(session, "3")  # go to support submenu

        _result = auto_attendant.handle_dtmf(session, "9")
        assert session["current_menu_id"] == "main"

    def test_handle_dtmf_submenu_extension_transfer(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        auto_attendant.create_menu("support", "main", "Support")
        auto_attendant.add_menu_item("main", "3", "submenu", "support")
        auto_attendant.add_menu_item("support", "1", "extension", "2001", "Tech")

        session = self._start_session(auto_attendant)
        auto_attendant.handle_dtmf(session, "3")  # go to support
        result = auto_attendant.handle_dtmf(session, "1")  # select tech
        assert result["action"] == "transfer"
        assert result["destination"] == "2001"

    def test_handle_dtmf_voicemail_destination(self, auto_attendant) -> None:
        auto_attendant.add_menu_item("main", "4", "voicemail", "1001", "Leave voicemail")

        session = self._start_session(auto_attendant)
        result = auto_attendant.handle_dtmf(session, "4")
        assert result["action"] == "voicemail"
        assert result["mailbox"] == "1001"

    def test_handle_dtmf_queue_destination(self, auto_attendant) -> None:
        auto_attendant.add_menu_item("main", "5", "queue", "sales_queue", "Sales")

        session = self._start_session(auto_attendant)
        result = auto_attendant.handle_dtmf(session, "5")
        assert result["action"] == "transfer"
        assert result["destination"] == "sales_queue"

    def test_handle_dtmf_operator_destination(self, auto_attendant) -> None:
        auto_attendant.add_menu_item("main", "0", "operator", "1001", "Operator")

        session = self._start_session(auto_attendant)
        result = auto_attendant.handle_dtmf(session, "0")
        assert result["action"] == "transfer"
        assert result["destination"] == "1001"

    def test_handle_dtmf_default_state(self, auto_attendant) -> None:
        """Test DTMF handling in an unexpected state."""
        from pbx.features.auto_attendant import AAState

        session = self._start_session(auto_attendant)
        session["state"] = AAState.TRANSFERRING  # unusual state
        result = auto_attendant.handle_dtmf(session, "1")
        # Should handle as invalid
        assert result["action"] == "play"

    def test_handle_dtmf_in_invalid_state_submenu(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        auto_attendant.create_menu("support", "main", "Support")

        session = self._start_session(auto_attendant)
        session["state"] = AAState.INVALID
        session["current_menu_id"] = "support"
        _result = auto_attendant.handle_dtmf(session, "1")
        assert session["state"] == AAState.SUBMENU


# =============================================================================
# Timeout Handling Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantTimeout:
    """Tests for timeout handling."""

    def test_handle_timeout(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        result = auto_attendant.start_session("call_001", "5551234")
        session = result["session"]

        result = auto_attendant.handle_timeout(session)
        assert result["action"] == "play"
        assert session["retry_count"] == 1

    def test_handle_timeout_max_retries(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        result = auto_attendant.start_session("call_001", "5551234")
        session = result["session"]

        for _ in range(3):
            result = auto_attendant.handle_timeout(session)

        assert result["action"] == "transfer"
        assert result["reason"] == "timeout"
        assert session["state"] == AAState.ENDED


# =============================================================================
# Audio File Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantAudioFiles:
    """Tests for audio file retrieval."""

    def test_get_audio_file_no_file(self, auto_attendant) -> None:
        result = auto_attendant._get_audio_file("welcome")
        assert result is None

    def test_get_audio_file_wav_exists(self, auto_attendant) -> None:
        # Create a wav file
        wav_path = Path(auto_attendant.audio_path) / "welcome.wav"
        wav_path.write_bytes(b"fake wav")
        result = auto_attendant._get_audio_file("welcome")
        assert result == wav_path

    def test_get_audio_file_submenu_custom(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        # Create a custom audio file path and update menu
        custom_audio = Path(auto_attendant.audio_path) / "custom_support.wav"
        custom_audio.write_bytes(b"custom audio")
        auto_attendant.update_menu("support", audio_file=str(custom_audio))

        result = auto_attendant._get_audio_file("support")
        assert result == str(custom_audio)

    def test_get_audio_file_submenu_no_custom(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        result = auto_attendant._get_audio_file("support")
        assert result is None


# =============================================================================
# Navigate to Submenu Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantNavigateSubmenu:
    """Tests for submenu navigation."""

    def test_navigate_to_submenu(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        auto_attendant.create_menu("support", "main", "Support")

        session = {
            "state": AAState.MAIN_MENU,
            "current_menu_id": "main",
            "menu_stack": [],
            "retry_count": 5,
        }

        _result = auto_attendant._navigate_to_submenu(session, "support")
        assert session["current_menu_id"] == "support"
        assert session["state"] == AAState.SUBMENU
        assert session["retry_count"] == 0
        assert "main" in session["menu_stack"]

    def test_handle_go_back_empty_stack(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = {
            "state": AAState.MAIN_MENU,
            "current_menu_id": "main",
            "menu_stack": [],
            "retry_count": 0,
        }

        _result = auto_attendant._handle_go_back(session)
        # Empty stack means can't go back, treats as invalid
        assert session["retry_count"] >= 1

    def test_handle_go_back_with_stack(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = {
            "state": AAState.SUBMENU,
            "current_menu_id": "support",
            "menu_stack": ["main"],
            "retry_count": 0,
        }

        _result = auto_attendant._handle_go_back(session)
        assert session["current_menu_id"] == "main"
        assert session["state"] == AAState.MAIN_MENU

    def test_handle_repeat_menu_main(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = {
            "state": AAState.MAIN_MENU,
            "current_menu_id": "main",
        }

        result = auto_attendant._handle_repeat_menu(session)
        assert result["action"] == "play"

    def test_handle_repeat_menu_submenu(self, auto_attendant) -> None:
        from pbx.features.auto_attendant import AAState

        session = {
            "state": AAState.SUBMENU,
            "current_menu_id": "support",
        }

        result = auto_attendant._handle_repeat_menu(session)
        assert result["action"] == "play"


# =============================================================================
# Database Error Handling Tests
# =============================================================================


@pytest.mark.unit
class TestAutoAttendantDbErrors:
    """Tests for database error handling in various methods."""

    def test_save_config_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            # Should not raise
            auto_attendant._save_config_to_db()

    def test_load_config_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant._load_config_from_db()
            assert result is None

    def test_load_menu_options_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            auto_attendant.menu_options = {}
            auto_attendant._load_menu_options_from_db()
            assert auto_attendant.menu_options == {}

    def test_save_menu_option_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            auto_attendant._save_menu_option_to_db("1", "1001", "Sales")

    def test_delete_menu_option_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            auto_attendant._delete_menu_option_from_db("1")

    def test_create_menu_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.create_menu("new", "main", "New Menu")
            assert result is False

    def test_update_menu_db_error(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.update_menu("support", menu_name="Updated")
            assert result is False

    def test_delete_menu_db_error(self, auto_attendant) -> None:
        auto_attendant.create_menu("support", "main", "Support")
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.delete_menu("support")
            assert result is False

    def test_get_menu_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.get_menu("main")
            assert result is None

    def test_list_menus_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.list_menus()
            assert result == []

    def test_add_menu_item_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.add_menu_item("main", "1", "extension", "1001")
            assert result is False

    def test_remove_menu_item_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.remove_menu_item("main", "1")
            assert result is False

    def test_get_menu_items_db_error(self, auto_attendant) -> None:
        with patch("sqlite3.connect", side_effect=Exception("db error")):
            result = auto_attendant.get_menu_items("main")
            assert result == []


# =============================================================================
# Prompt Generation Functions Tests
# =============================================================================


@pytest.mark.unit
class TestGeneratePrompts:
    """Tests for prompt generation functions."""

    def test_generate_auto_attendant_prompts(self, tmp_path) -> None:
        from pbx.features.auto_attendant import generate_auto_attendant_prompts

        output_dir = str(tmp_path / "prompts")

        with patch("pbx.utils.audio.generate_voice_prompt") as mock_gen:
            mock_gen.return_value = b"fake wav data"
            generate_auto_attendant_prompts(output_dir)

            assert Path(output_dir).exists()
            assert mock_gen.call_count == 5  # welcome, main_menu, invalid, timeout, transferring

    def test_generate_auto_attendant_prompts_error(self, tmp_path) -> None:
        from pbx.features.auto_attendant import generate_auto_attendant_prompts

        output_dir = str(tmp_path / "prompts")

        with patch("pbx.utils.audio.generate_voice_prompt") as mock_gen:
            mock_gen.side_effect = OSError("generation failed")
            # Should not raise
            generate_auto_attendant_prompts(output_dir)

    def test_generate_submenu_prompt_no_gtts(self, tmp_path) -> None:
        from pbx.features.auto_attendant import generate_submenu_prompt

        output_dir = str(tmp_path / "prompts")

        with patch.dict("sys.modules", {"gtts": None}):
            result = generate_submenu_prompt("support", "Support menu", output_dir)
            # gTTS not available, returns None
            assert result is None
