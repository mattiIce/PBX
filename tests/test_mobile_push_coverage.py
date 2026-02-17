"""
Comprehensive tests for Mobile Push Notifications feature.

Tests all public classes and methods in pbx/features/mobile_push.py
with maximum code path coverage.
"""

import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestMobilePushNotifications:
    """Tests for MobilePushNotifications class."""

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _make_config(
        enabled: bool = True,
        fcm_credentials_path: str | None = "/fake/creds.json",
    ) -> dict[str, Any]:
        """Build a minimal config dict suitable for MobilePushNotifications."""
        push_section: dict[str, Any] = {"enabled": enabled}
        if fcm_credentials_path is not None:
            push_section["fcm_credentials_path"] = fcm_credentials_path
        return {"features": {"mobile_push": push_section}}

    @staticmethod
    def _make_database(
        db_type: str = "sqlite",
        enabled: bool = True,
    ) -> MagicMock:
        """Return a mock database object with a cursor that supports chaining."""
        db = MagicMock()
        db.enabled = enabled
        db.db_type = db_type

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        db.connection.cursor.return_value = mock_cursor
        return db

    @staticmethod
    def _ensure_firebase_attrs() -> None:
        """Ensure the module has firebase_admin, credentials, messaging attrs.

        When firebase_admin is not installed, these names never get defined
        in the module namespace. We inject MagicMock stubs so that
        ``patch.object`` can find them.
        """
        from pbx.features import mobile_push as mp_module

        if not hasattr(mp_module, "firebase_admin"):
            mp_module.firebase_admin = MagicMock()  # type: ignore[attr-defined]
        if not hasattr(mp_module, "credentials"):
            mp_module.credentials = MagicMock()  # type: ignore[attr-defined]
        if not hasattr(mp_module, "messaging"):
            mp_module.messaging = MagicMock()  # type: ignore[attr-defined]

    def _build_instance(
        self,
        *,
        enabled: bool = True,
        firebase_available: bool = True,
        firebase_init_fails: bool = False,
        config: dict[str, Any] | None = None,
        database: MagicMock | None = None,
        fcm_credentials_path: str | None = "/fake/creds.json",
    ) -> Any:
        """Instantiate MobilePushNotifications with controlled mocks.

        Returns the instance. Patches are applied at module level so that
        the constructor sees the desired state for FIREBASE_AVAILABLE.
        """
        from pbx.features import mobile_push as mp_module
        from pbx.features.mobile_push import MobilePushNotifications

        self._ensure_firebase_attrs()

        cfg = (
            config
            if config is not None
            else self._make_config(
                enabled=enabled,
                fcm_credentials_path=fcm_credentials_path,
            )
        )

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = firebase_available

        try:
            if firebase_available and enabled and fcm_credentials_path:
                with (
                    patch.object(mp_module, "credentials") as _mock_creds,
                    patch.object(mp_module, "firebase_admin") as mock_fb,
                ):
                    if firebase_init_fails:
                        mock_fb.initialize_app.side_effect = RuntimeError("boom")
                    else:
                        mock_fb.initialize_app.return_value = MagicMock(name="firebase_app")
                    instance = MobilePushNotifications(config=cfg, database=database)
            else:
                instance = MobilePushNotifications(config=cfg, database=database)
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

        return instance

    def _with_firebase(self, instance: Any) -> Any:
        """Context-manager-style helper that temporarily sets FIREBASE_AVAILABLE.

        Usage::

            from pbx.features import mobile_push as mp_module

            with self._with_firebase(instance):
                ...

        Returns a context manager that patches FIREBASE_AVAILABLE and messaging.
        """
        # Not a real context manager; callers should use the explicit
        # try/finally pattern shown in the tests below.
        raise NotImplementedError  # pragma: no cover

    # ------------------------------------------------------------------ #
    # __init__ tests
    # ------------------------------------------------------------------ #

    def test_init_defaults_no_config(self) -> None:
        """Init with no config defaults to disabled."""
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications()
        assert instance.enabled is False
        assert instance.config == {}
        assert instance.database is None
        assert instance.firebase_app is None
        assert instance.device_tokens == {}
        assert instance.notification_history == []

    def test_init_disabled(self) -> None:
        """When enabled is False the firebase app should not be created."""
        instance = self._build_instance(enabled=False)
        assert instance.enabled is False
        assert instance.firebase_app is None

    def test_init_enabled_firebase_available(self) -> None:
        """Happy path: enabled + Firebase available + creds path."""
        instance = self._build_instance(enabled=True, firebase_available=True)
        assert instance.enabled is True
        assert instance.firebase_app is not None

    def test_init_enabled_firebase_not_available(self) -> None:
        """When Firebase SDK is not installed, log a warning."""
        instance = self._build_instance(
            enabled=True,
            firebase_available=False,
        )
        assert instance.enabled is True
        assert instance.firebase_app is None

    def test_init_enabled_no_credentials_path(self) -> None:
        """When fcm_credentials_path is missing, firebase_app stays None."""
        instance = self._build_instance(
            enabled=True,
            firebase_available=True,
            fcm_credentials_path=None,
        )
        assert instance.firebase_app is None

    def test_init_firebase_init_fails(self) -> None:
        """If firebase_admin.initialize_app raises, we catch and log."""
        instance = self._build_instance(
            enabled=True,
            firebase_available=True,
            firebase_init_fails=True,
        )
        assert instance.firebase_app is None

    def test_init_with_database_enabled(self) -> None:
        """When a database is provided and enabled, schema + device load runs."""
        db = self._make_database()
        _instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        # At minimum the CREATE TABLE calls + indexes + SELECT for loading
        assert cursor.execute.call_count >= 1
        db.connection.commit.assert_called()

    def test_init_with_database_disabled(self) -> None:
        """Database present but disabled -> skip schema init."""
        db = self._make_database(enabled=False)
        _instance = self._build_instance(enabled=False, database=db)
        db.connection.cursor.assert_not_called()

    # ------------------------------------------------------------------ #
    # _initialize_schema tests
    # ------------------------------------------------------------------ #

    def test_initialize_schema_sqlite(self) -> None:
        """Schema init creates tables and indexes for sqlite."""
        db = self._make_database(db_type="sqlite")
        _instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        # 2 CREATE TABLE + 2 CREATE INDEX = 4 execute calls for schema
        # Then SELECT for _load_devices_from_database
        sql_calls = [str(c) for c in cursor.execute.call_args_list]
        assert len(sql_calls) >= 4

    def test_initialize_schema_postgresql(self) -> None:
        """Schema init creates postgresql-specific tables."""
        db = self._make_database(db_type="postgresql")
        _instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        found_serial = False
        for call in cursor.execute.call_args_list:
            args_str = str(call)
            if "SERIAL" in args_str:
                found_serial = True
                break
        assert found_serial, "PostgreSQL schema should use SERIAL PRIMARY KEY"

    def test_initialize_schema_db_error(self) -> None:
        """sqlite3.Error during schema init is caught and logged."""
        db = self._make_database()
        db.connection.cursor.return_value.execute.side_effect = sqlite3.Error("fail")
        # Should not raise
        instance = self._build_instance(enabled=False, database=db)
        assert instance is not None

    def test_initialize_schema_no_database(self) -> None:
        """_initialize_schema early-returns when database is None."""
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications(config={}, database=None)
        # Just verifying no exception
        instance._initialize_schema()

    def test_initialize_schema_database_not_enabled(self) -> None:
        """_initialize_schema early-returns when database.enabled is False."""
        db = self._make_database(enabled=False)
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications(config={}, database=db)
        instance._initialize_schema()
        db.connection.cursor.assert_not_called()

    # ------------------------------------------------------------------ #
    # _load_devices_from_database tests
    # ------------------------------------------------------------------ #

    def test_load_devices_empty(self) -> None:
        """No rows -> device_tokens remains empty."""
        db = self._make_database()
        instance = self._build_instance(enabled=False, database=db)
        assert instance.device_tokens == {}

    def test_load_devices_with_rows(self) -> None:
        """Rows from database are loaded into device_tokens dict."""
        db = self._make_database()
        now = datetime.now(UTC)
        cursor = db.connection.cursor.return_value

        cursor.fetchall.return_value = [
            ("user1", "token_a", "android", now, now),
            ("user1", "token_b", "ios", now, now),
            ("user2", "token_c", "android", now, now),
        ]

        instance = self._build_instance(enabled=False, database=db)
        assert "user1" in instance.device_tokens
        assert len(instance.device_tokens["user1"]) == 2
        assert "user2" in instance.device_tokens
        assert len(instance.device_tokens["user2"]) == 1

    def test_load_devices_postgresql_uses_true(self) -> None:
        """PostgreSQL path uses WHERE enabled = TRUE."""
        db = self._make_database(db_type="postgresql")
        _instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        found_true = False
        for call in cursor.execute.call_args_list:
            if call.args and "enabled = TRUE" in str(call.args[0]):
                found_true = True
                break
        assert found_true, "PostgreSQL load should use WHERE enabled = TRUE"

    def test_load_devices_sqlite_uses_1(self) -> None:
        """SQLite path uses WHERE enabled = 1."""
        db = self._make_database(db_type="sqlite")
        _instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        found_one = False
        for call in cursor.execute.call_args_list:
            if call.args and "enabled = 1" in str(call.args[0]):
                found_one = True
                break
        assert found_one, "SQLite load should use WHERE enabled = 1"

    def test_load_devices_db_error(self) -> None:
        """sqlite3.Error during load is caught and logged."""
        db = self._make_database()
        cursor = db.connection.cursor.return_value

        def execute_side(sql, *args, **kwargs):
            if "SELECT" in str(sql) and "mobile_devices" in str(sql):
                raise sqlite3.Error("load fail")

        cursor.execute = MagicMock(side_effect=execute_side)
        instance = self._build_instance(enabled=False, database=db)
        # Should not raise; device_tokens should remain empty
        assert instance.device_tokens == {}

    def test_load_devices_no_database(self) -> None:
        """_load_devices_from_database early-returns when database is None."""
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications(config={}, database=None)
        instance._load_devices_from_database()
        assert instance.device_tokens == {}

    # ------------------------------------------------------------------ #
    # _save_device_to_database tests
    # ------------------------------------------------------------------ #

    def test_save_device_no_database(self) -> None:
        """Returns False when no database."""
        instance = self._build_instance(enabled=False)
        result = instance._save_device_to_database("u1", "tok", "android")
        assert result is False

    def test_save_device_database_disabled(self) -> None:
        """Returns False when database is disabled."""
        db = self._make_database(enabled=False)
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications(config={}, database=db)
        result = instance._save_device_to_database("u1", "tok", "android")
        assert result is False

    def test_save_device_sqlite(self) -> None:
        """SQLite save uses INSERT OR REPLACE."""
        db = self._make_database(db_type="sqlite")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()
        db.connection.commit.reset_mock()
        cursor.close.reset_mock()

        result = instance._save_device_to_database("u1", "tok_abc", "ios")
        assert result is True

        sql_used = cursor.execute.call_args[0][0]
        assert "INSERT OR REPLACE" in sql_used
        db.connection.commit.assert_called_once()
        cursor.close.assert_called_once()

    def test_save_device_postgresql(self) -> None:
        """PostgreSQL save uses ON CONFLICT ... DO UPDATE."""
        db = self._make_database(db_type="postgresql")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        result = instance._save_device_to_database("u1", "tok_abc", "android")
        assert result is True

        sql_used = cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql_used

    def test_save_device_db_error(self) -> None:
        """sqlite3.Error during save returns False."""
        db = self._make_database()
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()
        cursor.execute.side_effect = sqlite3.Error("write fail")

        result = instance._save_device_to_database("u1", "tok", "ios")
        assert result is False

    # ------------------------------------------------------------------ #
    # _remove_device_from_database tests
    # ------------------------------------------------------------------ #

    def test_remove_device_no_database(self) -> None:
        """Returns False when no database."""
        instance = self._build_instance(enabled=False)
        assert instance._remove_device_from_database("u1", "tok") is False

    def test_remove_device_database_disabled(self) -> None:
        """Returns False when database is disabled."""
        db = self._make_database(enabled=False)
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications(config={}, database=db)
        assert instance._remove_device_from_database("u1", "tok") is False

    def test_remove_device_sqlite(self) -> None:
        """SQLite remove uses enabled = 0."""
        db = self._make_database(db_type="sqlite")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        result = instance._remove_device_from_database("u1", "tok")
        assert result is True

        sql_used = cursor.execute.call_args[0][0]
        assert "enabled = 0" in sql_used

    def test_remove_device_postgresql(self) -> None:
        """PostgreSQL remove uses enabled = FALSE."""
        db = self._make_database(db_type="postgresql")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        result = instance._remove_device_from_database("u1", "tok")
        assert result is True

        sql_used = cursor.execute.call_args[0][0]
        assert "enabled = FALSE" in sql_used

    def test_remove_device_db_error(self) -> None:
        """sqlite3.Error during remove returns False."""
        db = self._make_database()
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()
        cursor.execute.side_effect = sqlite3.Error("remove fail")

        assert instance._remove_device_from_database("u1", "tok") is False

    # ------------------------------------------------------------------ #
    # _save_notification_to_database tests
    # ------------------------------------------------------------------ #

    def test_save_notification_no_database(self) -> None:
        """Early-returns when no database."""
        instance = self._build_instance(enabled=False)
        # Should not raise
        instance._save_notification_to_database("u1", "call", "Title", "Body", {"key": "val"}, True)

    def test_save_notification_sqlite_success(self) -> None:
        """SQLite path stores success=1."""
        db = self._make_database(db_type="sqlite")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        instance._save_notification_to_database("u1", "call", "Title", "Body", {"key": "val"}, True)
        sql_used = cursor.execute.call_args[0][0]
        assert "INSERT INTO push_notifications" in sql_used
        params = cursor.execute.call_args[0][1]
        # success param should be 1 (sqlite boolean)
        assert params[6] == 1

    def test_save_notification_sqlite_failure(self) -> None:
        """SQLite path stores success=0 on failure."""
        db = self._make_database(db_type="sqlite")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        instance._save_notification_to_database(
            "u1", "call", "Title", "Body", {}, False, "some error"
        )
        params = cursor.execute.call_args[0][1]
        assert params[6] == 0
        assert params[7] == "some error"

    def test_save_notification_postgresql(self) -> None:
        """PostgreSQL path uses %s placeholders."""
        db = self._make_database(db_type="postgresql")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        instance._save_notification_to_database("u1", "voicemail", "VM", "body", {"a": 1}, True)
        sql_used = cursor.execute.call_args[0][0]
        assert "%s" in sql_used

    def test_save_notification_none_data(self) -> None:
        """When data is falsy, data_json should be None."""
        db = self._make_database(db_type="sqlite")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        instance._save_notification_to_database("u1", "call", "T", "B", {}, True)
        params = cursor.execute.call_args[0][1]
        # Empty dict is falsy -> data_json is None
        assert params[4] is None

    def test_save_notification_with_data(self) -> None:
        """Non-empty data is JSON-serialized."""
        db = self._make_database(db_type="sqlite")
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        instance._save_notification_to_database(
            "u1", "call", "T", "B", {"type": "incoming_call"}, True
        )
        params = cursor.execute.call_args[0][1]
        assert params[4] == json.dumps({"type": "incoming_call"})

    def test_save_notification_db_error(self) -> None:
        """sqlite3.Error during save is caught and logged."""
        db = self._make_database()
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()
        cursor.execute.side_effect = sqlite3.Error("save fail")

        # Should not raise
        instance._save_notification_to_database("u1", "call", "T", "B", {}, True)

    def test_save_notification_value_error(self) -> None:
        """ValueError during save is caught and logged."""
        db = self._make_database()
        instance = self._build_instance(enabled=False, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()
        cursor.execute.side_effect = ValueError("bad value")

        # Should not raise
        instance._save_notification_to_database("u1", "call", "T", "B", {"k": "v"}, True)

    # ------------------------------------------------------------------ #
    # register_device tests
    # ------------------------------------------------------------------ #

    def test_register_device_disabled(self) -> None:
        """register_device returns False when not enabled."""
        instance = self._build_instance(enabled=False)
        assert instance.register_device("u1", "tok", "android") is False

    def test_register_device_new_user(self) -> None:
        """Registering a device for a new user creates entry."""
        instance = self._build_instance(enabled=True)
        result = instance.register_device("u1", "tok_1", "ios")

        assert result is True
        assert "u1" in instance.device_tokens
        assert len(instance.device_tokens["u1"]) == 1
        assert instance.device_tokens["u1"][0]["token"] == "tok_1"
        assert instance.device_tokens["u1"][0]["platform"] == "ios"

    def test_register_device_duplicate_updates_last_seen(self) -> None:
        """Re-registering an existing token updates last_seen."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")

        old_last_seen = instance.device_tokens["u1"][0]["last_seen"]
        result = instance.register_device("u1", "tok_1", "android")

        assert result is True
        assert len(instance.device_tokens["u1"]) == 1
        # last_seen should be >= old value
        assert instance.device_tokens["u1"][0]["last_seen"] >= old_last_seen

    def test_register_device_multiple_devices(self) -> None:
        """A user can have multiple device tokens."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")
        instance.register_device("u1", "tok_2", "ios")

        assert len(instance.device_tokens["u1"]) == 2

    def test_register_device_default_platform(self) -> None:
        """Default platform is 'unknown'."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1")

        assert instance.device_tokens["u1"][0]["platform"] == "unknown"

    def test_register_device_calls_save_to_database(self) -> None:
        """New registration triggers _save_device_to_database."""
        db = self._make_database()
        instance = self._build_instance(enabled=True, database=db)

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()
        db.connection.commit.reset_mock()

        instance.register_device("u1", "tok_new", "android")
        # save_device_to_database should have been called
        assert db.connection.cursor.called

    # ------------------------------------------------------------------ #
    # unregister_device tests
    # ------------------------------------------------------------------ #

    def test_unregister_device_unknown_user(self) -> None:
        """Returns False for unknown user."""
        instance = self._build_instance(enabled=True)
        assert instance.unregister_device("unknown", "tok") is False

    def test_unregister_device_unknown_token(self) -> None:
        """Returns False when token does not match."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")

        assert instance.unregister_device("u1", "nonexistent_tok") is False
        assert len(instance.device_tokens["u1"]) == 1

    def test_unregister_device_success(self) -> None:
        """Successfully removes a device token."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")
        instance.register_device("u1", "tok_2", "ios")

        result = instance.unregister_device("u1", "tok_1")
        assert result is True
        assert len(instance.device_tokens["u1"]) == 1
        assert instance.device_tokens["u1"][0]["token"] == "tok_2"

    def test_unregister_device_calls_remove_from_database(self) -> None:
        """Successful unregister calls _remove_device_from_database."""
        db = self._make_database()
        instance = self._build_instance(enabled=True, database=db)
        instance.register_device("u1", "tok_1", "android")

        cursor = db.connection.cursor.return_value
        cursor.execute.reset_mock()

        instance.unregister_device("u1", "tok_1")
        # Should have called execute for the UPDATE
        assert cursor.execute.called

    # ------------------------------------------------------------------ #
    # send_call_notification tests
    # ------------------------------------------------------------------ #

    def test_send_call_notification_disabled(self) -> None:
        """Returns error dict when not enabled."""
        instance = self._build_instance(enabled=False)
        result = instance.send_call_notification("u1", "5551234")
        assert "error" in result

    def test_send_call_notification_no_firebase_app(self) -> None:
        """Returns error when firebase_app is None."""
        instance = self._build_instance(enabled=True)
        instance.firebase_app = None
        result = instance.send_call_notification("u1", "5551234")
        assert "error" in result
        assert "not available" in result["error"]

    def test_send_call_notification_no_devices(self) -> None:
        """Returns error when user has no registered devices."""
        instance = self._build_instance(enabled=True)
        result = instance.send_call_notification("u1", "5551234")
        assert "error" in result
        assert "No devices" in result["error"]

    def test_send_call_notification_with_caller_name(self) -> None:
        """Sends notification with caller_name in body."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance.send_call_notification("u1", "5551234", caller_name="Alice")

            assert result["success"] is True
            assert result["success_count"] == 1
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_call_notification_without_caller_name(self) -> None:
        """Sends notification using caller_id when no caller_name."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance.send_call_notification("u1", "5551234")

            assert result["success"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    # ------------------------------------------------------------------ #
    # send_voicemail_notification tests
    # ------------------------------------------------------------------ #

    def test_send_voicemail_notification_disabled(self) -> None:
        """Returns error when disabled."""
        instance = self._build_instance(enabled=False)
        result = instance.send_voicemail_notification("u1", "msg1", "555", 30)
        assert "error" in result

    def test_send_voicemail_notification_no_firebase(self) -> None:
        """Returns error when firebase_app is None."""
        instance = self._build_instance(enabled=True)
        instance.firebase_app = None
        result = instance.send_voicemail_notification("u1", "msg1", "555", 30)
        assert "error" in result

    def test_send_voicemail_notification_no_devices(self) -> None:
        """Returns error when user has no devices."""
        instance = self._build_instance(enabled=True)
        result = instance.send_voicemail_notification("u1", "msg1", "555", 30)
        assert "error" in result

    def test_send_voicemail_notification_success(self) -> None:
        """Successfully sends voicemail notification."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance.send_voicemail_notification("u1", "msg_42", "5559999", 45)

            assert result["success"] is True
            assert result["success_count"] == 1
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    # ------------------------------------------------------------------ #
    # send_missed_call_notification tests
    # ------------------------------------------------------------------ #

    def test_send_missed_call_notification_disabled(self) -> None:
        """Returns error when disabled."""
        instance = self._build_instance(enabled=False)
        result = instance.send_missed_call_notification("u1", "555")
        assert "error" in result

    def test_send_missed_call_notification_no_firebase(self) -> None:
        """Returns error when firebase_app is None."""
        instance = self._build_instance(enabled=True)
        instance.firebase_app = None
        result = instance.send_missed_call_notification("u1", "555")
        assert "error" in result

    def test_send_missed_call_notification_no_devices(self) -> None:
        """Returns error when user has no devices."""
        instance = self._build_instance(enabled=True)
        result = instance.send_missed_call_notification("u1", "555")
        assert "error" in result

    def test_send_missed_call_notification_with_call_time(self) -> None:
        """Passes explicit call_time through to data."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            call_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance.send_missed_call_notification(
                    "u1", "5551234", call_time=call_time
                )

            assert result["success"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_missed_call_notification_no_call_time(self) -> None:
        """Uses datetime.now(UTC) when call_time is None."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "ios")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance.send_missed_call_notification("u1", "5551234")

            assert result["success"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    # ------------------------------------------------------------------ #
    # _send_notification tests
    # ------------------------------------------------------------------ #

    def test_send_notification_stub_mode_firebase_unavailable(self) -> None:
        """When FIREBASE_AVAILABLE is False, returns stub_mode result."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = None

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = False
        try:
            result = instance._send_notification("u1", "Title", "Body")
            assert result["success"] is False
            assert result["stub_mode"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_stub_mode_no_firebase_app(self) -> None:
        """When firebase_app is None but FIREBASE_AVAILABLE, returns stub."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = None

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            result = instance._send_notification("u1", "Title", "Body")
            assert result["success"] is False
            assert result["stub_mode"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_no_tokens(self) -> None:
        """Returns error when user has no tokens."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            result = instance._send_notification("u1", "Title", "Body")
            assert "error" in result
            assert "No device tokens" in result["error"]
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_success(self) -> None:
        """Happy path: notification sent to all tokens."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")
        instance.register_device("u1", "tok_b", "ios")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 2
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance._send_notification("u1", "Test", "Body", {"type": "test"})

            assert result["success"] is True
            assert result["success_count"] == 2
            assert result["failure_count"] == 0

            # Notification history updated
            assert len(instance.notification_history) == 1
            assert instance.notification_history[0]["user_id"] == "u1"
            assert instance.notification_history[0]["title"] == "Test"
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_with_none_data(self) -> None:
        """data=None is handled (defaults to {})."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance._send_notification("u1", "Test", "Body", data=None)

            assert result["success"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_firebase_value_error(self) -> None:
        """ValueError during send is caught; error result returned."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.MulticastMessage.side_effect = ValueError("bad msg")
                result = instance._send_notification("u1", "Test", "Body", {"type": "test"})

            assert "error" in result
            assert "bad msg" in result["error"]
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_firebase_type_error(self) -> None:
        """TypeError during send is also caught."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.MulticastMessage.side_effect = TypeError("type err")
                result = instance._send_notification("u1", "Test", "Body", {"type": "test"})

            assert "error" in result
            assert "type err" in result["error"]
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_firebase_key_error(self) -> None:
        """KeyError during send is also caught."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.MulticastMessage.side_effect = KeyError("missing")
                result = instance._send_notification("u1", "Test", "Body", {"type": "test"})

            assert "error" in result
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_error_saves_to_database(self) -> None:
        """On error, _save_notification_to_database called with success=False."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        db = self._make_database()
        instance = self._build_instance(enabled=True, database=db)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            with (
                patch.object(mp_module, "messaging") as mock_messaging,
                patch.object(instance, "_save_notification_to_database") as mock_save,
            ):
                mock_messaging.MulticastMessage.side_effect = ValueError("err")
                instance._send_notification("u1", "T", "B", {"type": "missed_call"})

                mock_save.assert_called_once()
                call_args = mock_save.call_args
                assert call_args[0][5] is False  # success=False
                assert call_args[0][6] == "err"  # error_message
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_success_saves_to_database(self) -> None:
        """On success, _save_notification_to_database called with success=True."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        db = self._make_database()
        instance = self._build_instance(enabled=True, database=db)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with (
                patch.object(mp_module, "messaging") as mock_messaging,
                patch.object(instance, "_save_notification_to_database") as mock_save,
            ):
                mock_messaging.send_multicast.return_value = mock_response
                instance._send_notification("u1", "T", "B", {"type": "incoming_call"})

                mock_save.assert_called_once()
                call_args = mock_save.call_args
                assert call_args[0][0] == "u1"
                assert call_args[0][1] == "incoming_call"
                assert call_args[0][5] is True  # success=True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_send_notification_error_with_none_data_type_unknown(self) -> None:
        """Error path with data=None -> notification_type defaults to 'unknown'."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_a", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            with (
                patch.object(mp_module, "messaging") as mock_messaging,
                patch.object(instance, "_save_notification_to_database") as mock_save,
            ):
                mock_messaging.MulticastMessage.side_effect = ValueError("err")
                instance._send_notification("u1", "T", "B", data=None)

                call_args = mock_save.call_args
                assert call_args[0][1] == "unknown"  # notification_type
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    # ------------------------------------------------------------------ #
    # get_user_devices tests
    # ------------------------------------------------------------------ #

    def test_get_user_devices_empty(self) -> None:
        """Returns empty list for unknown user."""
        instance = self._build_instance(enabled=True)
        result = instance.get_user_devices("nonexistent")
        assert result == []

    def test_get_user_devices_returns_formatted_list(self) -> None:
        """Returns properly formatted device list."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")
        instance.register_device("u1", "tok_2", "ios")

        devices = instance.get_user_devices("u1")
        assert len(devices) == 2

        for device in devices:
            assert "platform" in device
            assert "registered_at" in device
            assert "last_seen" in device
            # Verify ISO format strings
            assert isinstance(device["registered_at"], str)
            assert isinstance(device["last_seen"], str)

        platforms = {d["platform"] for d in devices}
        assert platforms == {"android", "ios"}

    def test_get_user_devices_no_token_field(self) -> None:
        """Returned dicts do NOT expose the actual device token."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_secret", "android")

        devices = instance.get_user_devices("u1")
        assert "token" not in devices[0]

    # ------------------------------------------------------------------ #
    # cleanup_stale_devices tests
    # ------------------------------------------------------------------ #

    def test_cleanup_stale_devices_removes_old(self) -> None:
        """Devices older than cutoff are removed."""
        instance = self._build_instance(enabled=True)

        old_time = datetime.now(UTC) - timedelta(days=100)
        new_time = datetime.now(UTC) - timedelta(days=10)

        instance.device_tokens["u1"] = [
            {
                "token": "old_tok",
                "platform": "android",
                "registered_at": old_time,
                "last_seen": old_time,
            },
            {
                "token": "new_tok",
                "platform": "ios",
                "registered_at": new_time,
                "last_seen": new_time,
            },
        ]

        instance.cleanup_stale_devices(days=90)

        assert len(instance.device_tokens["u1"]) == 1
        assert instance.device_tokens["u1"][0]["token"] == "new_tok"

    def test_cleanup_stale_devices_removes_user_if_no_devices(self) -> None:
        """If all devices are stale, the user key is removed."""
        instance = self._build_instance(enabled=True)

        old_time = datetime.now(UTC) - timedelta(days=200)
        instance.device_tokens["u_gone"] = [
            {
                "token": "tok_1",
                "platform": "android",
                "registered_at": old_time,
                "last_seen": old_time,
            },
        ]

        instance.cleanup_stale_devices(days=90)
        assert "u_gone" not in instance.device_tokens

    def test_cleanup_stale_devices_custom_days(self) -> None:
        """Custom days parameter is respected."""
        instance = self._build_instance(enabled=True)

        time_50_days_ago = datetime.now(UTC) - timedelta(days=50)
        instance.device_tokens["u1"] = [
            {
                "token": "tok_1",
                "platform": "android",
                "registered_at": time_50_days_ago,
                "last_seen": time_50_days_ago,
            },
        ]

        # 60 days -> device is NOT stale
        instance.cleanup_stale_devices(days=60)
        assert "u1" in instance.device_tokens

        # 30 days -> device IS stale
        instance.cleanup_stale_devices(days=30)
        assert "u1" not in instance.device_tokens

    def test_cleanup_stale_devices_no_removals(self) -> None:
        """When no devices are stale, nothing changes."""
        instance = self._build_instance(enabled=True)

        recent = datetime.now(UTC) - timedelta(days=1)
        instance.device_tokens["u1"] = [
            {"token": "tok", "platform": "ios", "registered_at": recent, "last_seen": recent},
        ]

        instance.cleanup_stale_devices(days=90)
        assert len(instance.device_tokens["u1"]) == 1

    def test_cleanup_stale_devices_empty(self) -> None:
        """No error when device_tokens is empty."""
        instance = self._build_instance(enabled=True)
        instance.cleanup_stale_devices(days=90)
        assert instance.device_tokens == {}

    def test_cleanup_stale_devices_multiple_users(self) -> None:
        """Cleanup works across multiple users."""
        instance = self._build_instance(enabled=True)

        old_time = datetime.now(UTC) - timedelta(days=120)
        new_time = datetime.now(UTC) - timedelta(days=5)

        instance.device_tokens["u1"] = [
            {
                "token": "tok_old",
                "platform": "android",
                "registered_at": old_time,
                "last_seen": old_time,
            },
        ]
        instance.device_tokens["u2"] = [
            {
                "token": "tok_new",
                "platform": "ios",
                "registered_at": new_time,
                "last_seen": new_time,
            },
        ]

        instance.cleanup_stale_devices(days=90)
        assert "u1" not in instance.device_tokens
        assert "u2" in instance.device_tokens

    # ------------------------------------------------------------------ #
    # get_statistics tests
    # ------------------------------------------------------------------ #

    def test_get_statistics_empty(self) -> None:
        """Stats with no data."""
        instance = self._build_instance(enabled=False)
        stats = instance.get_statistics()

        assert stats["enabled"] is False
        assert isinstance(stats["firebase_available"], bool)
        assert stats["total_users"] == 0
        assert stats["total_devices"] == 0
        assert stats["notifications_24h"] == 0

    def test_get_statistics_with_devices(self) -> None:
        """Stats reflect registered devices."""
        instance = self._build_instance(enabled=True)
        instance.register_device("u1", "tok_1", "android")
        instance.register_device("u1", "tok_2", "ios")
        instance.register_device("u2", "tok_3", "android")

        stats = instance.get_statistics()
        assert stats["enabled"] is True
        assert stats["total_users"] == 2
        assert stats["total_devices"] == 3

    def test_get_statistics_with_recent_notifications(self) -> None:
        """Recent notifications (< 24h) are counted."""
        instance = self._build_instance(enabled=True)

        now = datetime.now(UTC)
        instance.notification_history = [
            {
                "user_id": "u1",
                "title": "T",
                "body": "B",
                "sent_at": now,
                "success_count": 1,
                "failure_count": 0,
            },
            {
                "user_id": "u2",
                "title": "T2",
                "body": "B2",
                "sent_at": now - timedelta(hours=12),
                "success_count": 1,
                "failure_count": 0,
            },
        ]

        stats = instance.get_statistics()
        assert stats["notifications_24h"] == 2

    def test_get_statistics_excludes_old_notifications(self) -> None:
        """Notifications older than 24h are NOT counted."""
        instance = self._build_instance(enabled=True)

        old = datetime.now(UTC) - timedelta(hours=25)
        instance.notification_history = [
            {
                "user_id": "u1",
                "title": "Old",
                "body": "B",
                "sent_at": old,
                "success_count": 1,
                "failure_count": 0,
            },
        ]

        stats = instance.get_statistics()
        assert stats["notifications_24h"] == 0

    # ------------------------------------------------------------------ #
    # send_test_notification tests
    # ------------------------------------------------------------------ #

    def test_send_test_notification_delegates(self) -> None:
        """send_test_notification calls _send_notification with correct args."""
        instance = self._build_instance(enabled=True)

        with patch.object(
            instance,
            "_send_notification",
            return_value={"success": True},
        ) as mock_send:
            result = instance.send_test_notification("u1")

        assert result == {"success": True}
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "u1"
        assert call_args[0][1] == "Test Notification"
        assert "test push notification" in call_args[0][2]
        assert call_args[0][3]["type"] == "test"

    def test_send_test_notification_stub_mode(self) -> None:
        """Test notification in stub mode returns stub result."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = None

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = False
        try:
            result = instance.send_test_notification("u1")
            assert result["stub_mode"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    # ------------------------------------------------------------------ #
    # FIREBASE_AVAILABLE flag tests
    # ------------------------------------------------------------------ #

    def test_firebase_available_flag_exists(self) -> None:
        """Module-level FIREBASE_AVAILABLE flag is a bool."""
        from pbx.features import mobile_push as mp_module

        assert isinstance(mp_module.FIREBASE_AVAILABLE, bool)

    # ------------------------------------------------------------------ #
    # Integration-style scenarios
    # ------------------------------------------------------------------ #

    def test_full_lifecycle(self) -> None:
        """Register -> send notification -> unregister -> verify empty."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()

        # Register
        assert instance.register_device("u1", "tok_1", "android") is True
        assert len(instance.get_user_devices("u1")) == 1

        # Send notification
        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance.send_call_notification("u1", "5551234", "Bob")

            assert result["success"] is True
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

        # Unregister
        assert instance.unregister_device("u1", "tok_1") is True
        assert len(instance.get_user_devices("u1")) == 0

        # Stats show 0 devices, 1 notification
        stats = instance.get_statistics()
        assert stats["total_devices"] == 0

    def test_multiple_notification_types(self) -> None:
        """Send call, voicemail, and missed call notifications in sequence."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_1", "ios")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response

                r1 = instance.send_call_notification("u1", "111")
                r2 = instance.send_voicemail_notification("u1", "m1", "222", 15)
                r3 = instance.send_missed_call_notification("u1", "333")

            assert r1["success"] is True
            assert r2["success"] is True
            assert r3["success"] is True
            assert len(instance.notification_history) == 3
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_notification_history_records_all_fields(self) -> None:
        """notification_history entries contain expected keys."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_1", "android")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 0

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                instance._send_notification("u1", "Title", "Body", {"type": "test"})

            entry = instance.notification_history[0]
            assert entry["user_id"] == "u1"
            assert entry["title"] == "Title"
            assert entry["body"] == "Body"
            assert isinstance(entry["sent_at"], datetime)
            assert entry["success_count"] == 1
            assert entry["failure_count"] == 0
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag

    def test_config_with_empty_features(self) -> None:
        """Config with empty features dict produces disabled instance."""
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications(config={"features": {}})
        assert instance.enabled is False

    def test_config_with_empty_mobile_push(self) -> None:
        """Config with empty mobile_push section defaults to disabled."""
        from pbx.features.mobile_push import MobilePushNotifications

        instance = MobilePushNotifications(config={"features": {"mobile_push": {}}})
        assert instance.enabled is False
        assert instance.fcm_credentials_path is None

    def test_partial_failures_in_multicast(self) -> None:
        """Partial send failures are reported correctly."""
        from pbx.features import mobile_push as mp_module

        self._ensure_firebase_attrs()
        instance = self._build_instance(enabled=True)
        instance.firebase_app = MagicMock()
        instance.register_device("u1", "tok_1", "android")
        instance.register_device("u1", "tok_2", "ios")

        original_flag = mp_module.FIREBASE_AVAILABLE
        mp_module.FIREBASE_AVAILABLE = True
        try:
            mock_response = MagicMock()
            mock_response.success_count = 1
            mock_response.failure_count = 1

            with patch.object(mp_module, "messaging") as mock_messaging:
                mock_messaging.send_multicast.return_value = mock_response
                result = instance._send_notification("u1", "Test", "Body", {"type": "test"})

            assert result["success"] is True
            assert result["success_count"] == 1
            assert result["failure_count"] == 1
        finally:
            mp_module.FIREBASE_AVAILABLE = original_flag
