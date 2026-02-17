"""Comprehensive tests for pbx.utils.database module."""

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from pbx.utils.database import (
    DatabaseBackend,
    ExtensionDB,
    ProvisionedDevicesDB,
    RegisteredPhonesDB,
    VIPCallerDB,
    get_database,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(overrides: dict | None = None) -> MagicMock:
    """Return a mock config with sensible defaults."""
    store: dict = {
        "database.type": "sqlite",
        "database.host": "localhost",
        "database.port": 5432,
        "database.name": "pbx",
        "database.user": "pbx",
        "database.password": "secret",
        "database.path": ":memory:",
    }
    if overrides:
        store.update(overrides)

    config = MagicMock()
    config.get = MagicMock(side_effect=lambda key, default=None: store.get(key, default))
    return config


def _make_enabled_backend(db_type: str = "sqlite") -> DatabaseBackend:
    """Return a DatabaseBackend with mocked internals that is marked as enabled."""
    config = _make_config({"database.type": db_type})
    with patch("pbx.utils.database.get_logger"):
        backend = DatabaseBackend(config)
    backend.enabled = True
    backend.connection = MagicMock()
    backend._autocommit = db_type == "postgresql"
    backend.db_type = db_type
    return backend


# ===========================================================================
# DatabaseBackend tests
# ===========================================================================


@pytest.mark.unit
class TestDatabaseBackendInit:
    """Tests for DatabaseBackend.__init__."""

    @patch("pbx.utils.database.get_logger")
    def test_init_sqlite_default(self, mock_get_logger: MagicMock) -> None:
        config = _make_config()
        db = DatabaseBackend(config)
        assert db.db_type == "sqlite"
        assert db.connection is None
        assert db.enabled is False
        assert db._autocommit is False

    @patch("pbx.utils.database.get_logger")
    def test_init_postgresql_available(self, mock_get_logger: MagicMock) -> None:
        config = _make_config({"database.type": "postgresql"})
        with patch("pbx.utils.database.POSTGRES_AVAILABLE", True):
            db = DatabaseBackend(config)
        assert db.db_type == "postgresql"

    @patch("pbx.utils.database.get_logger")
    def test_init_postgresql_not_available_falls_back(self, mock_get_logger: MagicMock) -> None:
        config = _make_config({"database.type": "postgresql"})
        with patch("pbx.utils.database.POSTGRES_AVAILABLE", False):
            db = DatabaseBackend(config)
        # Should fall back to sqlite
        assert db.db_type == "sqlite"

    @patch("pbx.utils.database.get_logger")
    def test_init_sqlite_not_available(self, mock_get_logger: MagicMock) -> None:
        config = _make_config({"database.type": "sqlite"})
        with patch("pbx.utils.database.SQLITE_AVAILABLE", False):
            db = DatabaseBackend(config)
        assert db.enabled is False


@pytest.mark.unit
class TestDatabaseBackendConnect:
    """Tests for DatabaseBackend.connect."""

    @patch("pbx.utils.database.get_logger")
    def test_connect_sqlite_success(self, mock_get_logger: MagicMock) -> None:
        config = _make_config()
        db = DatabaseBackend(config)
        mock_conn = MagicMock()
        with patch("pbx.utils.database.sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            mock_sqlite.Row = sqlite3.Row
            mock_sqlite.Error = sqlite3.Error
            result = db.connect()
        assert result is True
        assert db.enabled is True
        assert db.connection is mock_conn

    @patch("pbx.utils.database.get_logger")
    def test_connect_sqlite_failure(self, mock_get_logger: MagicMock) -> None:
        config = _make_config()
        db = DatabaseBackend(config)
        with patch("pbx.utils.database.sqlite3") as mock_sqlite:
            mock_sqlite.connect.side_effect = sqlite3.Error("oops")
            mock_sqlite.Error = sqlite3.Error
            result = db.connect()
        assert result is False
        assert db.enabled is False

    @patch("pbx.utils.database.get_logger")
    def test_connect_postgresql_success(self, mock_get_logger: MagicMock) -> None:
        config = _make_config({"database.type": "postgresql"})
        mock_psycopg2 = MagicMock()
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        with patch("pbx.utils.database.POSTGRES_AVAILABLE", True):
            db = DatabaseBackend(config)
        with patch.dict("sys.modules", {"psycopg2": mock_psycopg2, "psycopg2.extras": MagicMock()}):
            with patch("pbx.utils.database.POSTGRES_AVAILABLE", True):
                # Patch psycopg2 at module level using create=True
                with patch("pbx.utils.database.psycopg2", mock_psycopg2, create=True):
                    result = db.connect()
        assert result is True
        assert db.enabled is True
        assert db._autocommit is True

    @patch("pbx.utils.database.get_logger")
    def test_connect_postgresql_driver_not_available(self, mock_get_logger: MagicMock) -> None:
        config = _make_config({"database.type": "postgresql"})
        with patch("pbx.utils.database.POSTGRES_AVAILABLE", True):
            db = DatabaseBackend(config)
        with patch("pbx.utils.database.POSTGRES_AVAILABLE", False):
            result = db.connect()
        assert result is False

    @patch("pbx.utils.database.get_logger")
    def test_connect_postgresql_connection_error(self, mock_get_logger: MagicMock) -> None:
        config = _make_config({"database.type": "postgresql"})
        mock_psycopg2 = MagicMock()
        mock_psycopg2.connect.side_effect = KeyError("bad config")
        with patch("pbx.utils.database.POSTGRES_AVAILABLE", True):
            db = DatabaseBackend(config)
        with patch("pbx.utils.database.POSTGRES_AVAILABLE", True):
            with patch("pbx.utils.database.psycopg2", mock_psycopg2, create=True):
                result = db.connect()
        assert result is False

    @patch("pbx.utils.database.get_logger")
    def test_connect_unsupported_type(self, mock_get_logger: MagicMock) -> None:
        config = _make_config({"database.type": "mysql"})
        db = DatabaseBackend(config)
        db.db_type = "mysql"
        result = db.connect()
        assert result is False

    @patch("pbx.utils.database.get_logger")
    def test_connect_generic_exception(self, mock_get_logger: MagicMock) -> None:
        config = _make_config()
        db = DatabaseBackend(config)
        with patch("pbx.utils.database.sqlite3") as mock_sqlite:
            mock_sqlite.connect.side_effect = RuntimeError("unexpected")
            mock_sqlite.Error = sqlite3.Error
            result = db.connect()
        assert result is False

    @patch("pbx.utils.database.get_logger")
    def test_connect_sqlite_not_available(self, mock_get_logger: MagicMock) -> None:
        config = _make_config()
        db = DatabaseBackend(config)
        with patch("pbx.utils.database.SQLITE_AVAILABLE", False):
            result = db.connect()
        assert result is False


@pytest.mark.unit
class TestDatabaseBackendDisconnect:
    """Tests for DatabaseBackend.disconnect."""

    def test_disconnect_with_connection(self) -> None:
        db = _make_enabled_backend()
        mock_conn = db.connection
        db.disconnect()
        mock_conn.close.assert_called_once()
        assert db.connection is None
        assert db.enabled is False

    def test_disconnect_without_connection(self) -> None:
        db = _make_enabled_backend()
        db.connection = None
        db.disconnect()
        assert db.enabled is True  # unchanged since connection was None


@pytest.mark.unit
class TestDatabaseBackendExecuteWithContext:
    """Tests for DatabaseBackend._execute_with_context."""

    def test_returns_false_when_disabled(self) -> None:
        db = _make_enabled_backend()
        db.enabled = False
        assert db._execute_with_context("SELECT 1") is False

    def test_returns_false_when_no_connection(self) -> None:
        db = _make_enabled_backend()
        db.connection = None
        assert db._execute_with_context("SELECT 1") is False

    def test_successful_execution_without_params(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        result = db._execute_with_context("CREATE TABLE foo (id INT)")
        assert result is True
        mock_cursor.execute.assert_called_once_with("CREATE TABLE foo (id INT)")
        mock_cursor.close.assert_called_once()

    def test_successful_execution_with_params(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        result = db._execute_with_context("INSERT INTO t VALUES (?)", "insert", ("val",))
        assert result is True
        mock_cursor.execute.assert_called_once_with("INSERT INTO t VALUES (?)", ("val",))

    def test_commits_when_not_autocommit(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        db._execute_with_context("INSERT INTO t VALUES (1)")
        db.connection.commit.assert_called_once()

    def test_no_commit_when_autocommit(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        db._execute_with_context("INSERT INTO t VALUES (1)")
        db.connection.commit.assert_not_called()

    def test_permission_error_non_critical_returns_true(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("permission denied for table")
        result = db._execute_with_context("CREATE INDEX ...", "index creation", critical=False)
        assert result is True
        db.connection.rollback.assert_called_once()

    def test_already_exists_error_returns_true(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("index already exists")
        result = db._execute_with_context("CREATE INDEX ...", "index creation", critical=True)
        assert result is True

    def test_actual_error_returns_false(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("disk I/O error")
        result = db._execute_with_context("SELECT 1", "query")
        assert result is False
        db.connection.rollback.assert_called_once()

    def test_actual_error_no_rollback_when_autocommit(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("disk I/O error")
        result = db._execute_with_context("SELECT 1", "query")
        assert result is False
        db.connection.rollback.assert_not_called()


@pytest.mark.unit
class TestDatabaseBackendExecute:
    """Tests for DatabaseBackend.execute."""

    def test_execute_when_not_enabled(self) -> None:
        db = _make_enabled_backend()
        db.enabled = False
        result = db.execute("INSERT INTO t VALUES (1)")
        assert result is False

    def test_execute_when_no_connection(self) -> None:
        db = _make_enabled_backend()
        db.connection = None
        result = db.execute("INSERT INTO t VALUES (1)")
        assert result is False

    def test_execute_delegates_to_execute_with_context(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        result = db.execute("INSERT INTO t VALUES (?)", ("val",))
        assert result is True


@pytest.mark.unit
class TestDatabaseBackendExecuteScript:
    """Tests for DatabaseBackend.execute_script."""

    def test_execute_script_not_enabled(self) -> None:
        db = _make_enabled_backend()
        db.enabled = False
        assert db.execute_script("SELECT 1;") is False

    def test_execute_script_no_connection(self) -> None:
        db = _make_enabled_backend()
        db.connection = None
        assert db.execute_script("SELECT 1;") is False

    def test_execute_script_sqlite(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        result = db.execute_script("CREATE TABLE a (id INT);\nCREATE TABLE b (id INT);")
        assert result is True
        mock_cursor.executescript.assert_called_once()
        db.connection.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_execute_script_sqlite_autocommit(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = True
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        result = db.execute_script("CREATE TABLE a (id INT);")
        assert result is True
        db.connection.commit.assert_not_called()

    def test_execute_script_postgresql(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        script = "-- comment\nCREATE TABLE a (id INT);\n\nCREATE TABLE b (id INT);"
        result = db.execute_script(script)
        assert result is True
        assert mock_cursor.execute.call_count == 2
        mock_cursor.close.assert_called_once()

    def test_execute_script_postgresql_no_autocommit(self) -> None:
        db = _make_enabled_backend("postgresql")
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        script = "CREATE TABLE a (id INT);"
        result = db.execute_script(script)
        assert result is True
        db.connection.commit.assert_called_once()

    def test_execute_script_error(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.executescript.side_effect = sqlite3.Error("syntax error")
        result = db.execute_script("INVALID SQL;")
        assert result is False
        db.connection.rollback.assert_called_once()

    def test_execute_script_error_autocommit(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = True
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.executescript.side_effect = sqlite3.Error("syntax error")
        result = db.execute_script("INVALID SQL;")
        assert result is False
        db.connection.rollback.assert_not_called()


@pytest.mark.unit
class TestDatabaseBackendFetchOne:
    """Tests for DatabaseBackend.fetch_one."""

    def test_fetch_one_not_enabled(self) -> None:
        db = _make_enabled_backend()
        db.enabled = False
        assert db.fetch_one("SELECT 1") is None

    def test_fetch_one_no_connection(self) -> None:
        db = _make_enabled_backend()
        db.connection = None
        assert db.fetch_one("SELECT 1") is None

    def test_fetch_one_sqlite_with_row(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        # Simulate a sqlite3.Row-like object with key access
        mock_row = MagicMock()
        mock_row.keys.return_value = ["id", "name"]
        mock_row.__getitem__ = lambda self, k: {"id": 1, "name": "test"}[k]
        mock_row.__iter__ = lambda self: iter(["id", "name"])
        mock_cursor.fetchone.return_value = mock_row
        result = db.fetch_one("SELECT * FROM t WHERE id = ?", (1,))
        assert result == {"id": 1, "name": "test"}

    def test_fetch_one_sqlite_no_row(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        result = db.fetch_one("SELECT * FROM t WHERE id = ?", (999,))
        assert result is None

    def test_fetch_one_postgresql_with_row(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1, "name": "test"}
        mock_rdc = MagicMock()
        with patch("pbx.utils.database.RealDictCursor", mock_rdc, create=True):
            result = db.fetch_one("SELECT * FROM t WHERE id = %s", (1,))
        assert result == {"id": 1, "name": "test"}

    def test_fetch_one_without_params(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        db.fetch_one("SELECT 1")
        mock_cursor.execute.assert_called_once_with("SELECT 1")

    def test_fetch_one_error(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("fail")
        result = db.fetch_one("SELECT * FROM t")
        assert result is None
        db.connection.rollback.assert_called_once()

    def test_fetch_one_error_autocommit(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_rdc = MagicMock()
        # Make cursor() raise when called with cursor_factory
        db.connection.cursor.side_effect = sqlite3.Error("fail")
        with patch("pbx.utils.database.RealDictCursor", mock_rdc, create=True):
            result = db.fetch_one("SELECT * FROM t")
        assert result is None
        db.connection.rollback.assert_not_called()


@pytest.mark.unit
class TestDatabaseBackendFetchAll:
    """Tests for DatabaseBackend.fetch_all."""

    def test_fetch_all_not_enabled(self) -> None:
        db = _make_enabled_backend()
        db.enabled = False
        assert db.fetch_all("SELECT 1") == []

    def test_fetch_all_no_connection(self) -> None:
        db = _make_enabled_backend()
        db.connection = None
        assert db.fetch_all("SELECT 1") == []

    def test_fetch_all_sqlite_with_rows(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        # Simulate sqlite3.Row-like objects
        mock_row1 = MagicMock()
        mock_row1.keys.return_value = ["id"]
        mock_row1.__getitem__ = lambda self, k: {"id": 1}[k]
        mock_row1.__iter__ = lambda self: iter(["id"])
        mock_row2 = MagicMock()
        mock_row2.keys.return_value = ["id"]
        mock_row2.__getitem__ = lambda self, k: {"id": 2}[k]
        mock_row2.__iter__ = lambda self: iter(["id"])
        mock_cursor.fetchall.return_value = [mock_row1, mock_row2]
        result = db.fetch_all("SELECT * FROM t")
        assert result == [{"id": 1}, {"id": 2}]

    def test_fetch_all_postgresql_with_rows(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        mock_rdc = MagicMock()
        with patch("pbx.utils.database.RealDictCursor", mock_rdc, create=True):
            result = db.fetch_all("SELECT * FROM t")
        assert result == [{"id": 1}, {"id": 2}]

    def test_fetch_all_with_params(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        db.fetch_all("SELECT * FROM t WHERE x = ?", ("val",))
        mock_cursor.execute.assert_called_once_with("SELECT * FROM t WHERE x = ?", ("val",))

    def test_fetch_all_without_params(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        db.fetch_all("SELECT * FROM t")
        mock_cursor.execute.assert_called_once_with("SELECT * FROM t")

    def test_fetch_all_error(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("fail")
        result = db.fetch_all("SELECT * FROM t")
        assert result == []
        db.connection.rollback.assert_called_once()

    def test_fetch_all_error_autocommit(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_rdc = MagicMock()
        db.connection.cursor.side_effect = sqlite3.Error("fail")
        with patch("pbx.utils.database.RealDictCursor", mock_rdc, create=True):
            result = db.fetch_all("SELECT * FROM t")
        assert result == []
        db.connection.rollback.assert_not_called()


@pytest.mark.unit
class TestDatabaseBackendBuildTableSQL:
    """Tests for DatabaseBackend._build_table_sql."""

    def test_postgresql_replacements(self) -> None:
        db = _make_enabled_backend("postgresql")
        template = "id {SERIAL}, active {BOOLEAN_TRUE}, disabled {BOOLEAN_FALSE}"
        result = db._build_table_sql(template)
        assert "SERIAL PRIMARY KEY" in result
        assert "TRUE" in result
        assert "FALSE" in result

    def test_sqlite_replacements(self) -> None:
        db = _make_enabled_backend()
        template = "id {SERIAL}, active {BOOLEAN_TRUE}, disabled {BOOLEAN_FALSE}"
        result = db._build_table_sql(template)
        assert "INTEGER PRIMARY KEY AUTOINCREMENT" in result
        assert "1" in result
        assert "0" in result


@pytest.mark.unit
class TestDatabaseBackendCreateTables:
    """Tests for DatabaseBackend.create_tables."""

    def test_create_tables_not_enabled(self) -> None:
        db = _make_enabled_backend()
        db.enabled = False
        assert db.create_tables() is False

    def test_create_tables_success(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        with patch.object(db, "_migrate_schema"):
            result = db.create_tables()
        assert result is True

    def test_create_tables_partial_failure(self) -> None:
        db = _make_enabled_backend()
        call_count = [0]

        def side_effect(query, context="query", params=None, critical=True):
            call_count[0] += 1
            # Fail on the first table creation
            if call_count[0] == 1:
                return False
            return True

        with patch.object(db, "_execute_with_context", side_effect=side_effect):
            with patch.object(db, "_migrate_schema"):
                result = db.create_tables()
        assert result is False


@pytest.mark.unit
class TestDatabaseBackendMigrateSchema:
    """Tests for DatabaseBackend._migrate_schema."""

    def test_migrate_schema_column_exists(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        # Column already exists
        mock_cursor.fetchone.return_value = {"name": "transcription_text"}
        with patch.object(db, "_apply_framework_migrations"):
            db._migrate_schema()
        # _execute_with_context should not be called for ALTER TABLE
        # because all columns "exist"

    def test_migrate_schema_column_not_exists(self) -> None:
        db = _make_enabled_backend()
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        with patch.object(db, "_execute_with_context", return_value=True) as mock_exec:
            with patch.object(db, "_apply_framework_migrations"):
                db._migrate_schema()
        # Should be called for each missing column (5 transcription + 4 extensions + 1 device_type)
        assert mock_exec.call_count >= 10

    def test_migrate_schema_error_handling(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("fail")
        with patch.object(db, "_apply_framework_migrations"):
            # Should not raise
            db._migrate_schema()
        db.connection.rollback.assert_called()


@pytest.mark.unit
class TestDatabaseBackendApplyFrameworkMigrations:
    """Tests for DatabaseBackend._apply_framework_migrations."""

    def test_apply_framework_migrations_success(self) -> None:
        db = _make_enabled_backend()
        mock_manager = MagicMock()
        mock_manager.apply_migrations.return_value = True
        mock_register = MagicMock()
        mock_migration_module = MagicMock()
        mock_migration_module.MigrationManager = MagicMock(return_value=mock_manager)
        mock_migration_module.register_all_migrations = mock_register
        with patch.dict("sys.modules", {"pbx.utils.migrations": mock_migration_module}):
            db._apply_framework_migrations()
        mock_migration_module.MigrationManager.assert_called_once_with(db)
        mock_register.assert_called_once_with(mock_manager)
        mock_manager.apply_migrations.assert_called_once()

    def test_apply_framework_migrations_partial_failure(self) -> None:
        db = _make_enabled_backend()
        mock_manager = MagicMock()
        mock_manager.apply_migrations.return_value = False
        mock_migration_module = MagicMock()
        mock_migration_module.MigrationManager = MagicMock(return_value=mock_manager)
        mock_migration_module.register_all_migrations = MagicMock()
        with patch.dict("sys.modules", {"pbx.utils.migrations": mock_migration_module}):
            db._apply_framework_migrations()
        # Should not raise, just log warning

    def test_apply_framework_migrations_exception(self) -> None:
        db = _make_enabled_backend()
        # Simulate an import error inside the method
        with patch.dict("sys.modules", {"pbx.utils.migrations": None}):
            # Should not raise
            db._apply_framework_migrations()


# ===========================================================================
# VIPCallerDB tests
# ===========================================================================


@pytest.mark.unit
class TestVIPCallerDB:
    """Tests for VIPCallerDB."""

    def _make_vip_db(self, db_type: str = "sqlite") -> tuple[VIPCallerDB, DatabaseBackend]:
        backend = _make_enabled_backend(db_type)
        with patch("pbx.utils.database.get_logger"):
            vip_db = VIPCallerDB(backend)
        return vip_db, backend

    def test_add_vip_sqlite(self) -> None:
        vip_db, backend = self._make_vip_db()
        backend.execute = MagicMock(return_value=True)
        result = vip_db.add_vip("+15551234567", priority_level=2, name="Boss", notes="VIP")
        assert result is True
        backend.execute.assert_called_once()
        args = backend.execute.call_args
        assert "INSERT OR REPLACE" in args[0][0]
        assert args[0][1][0] == "+15551234567"

    def test_add_vip_postgresql(self) -> None:
        vip_db, backend = self._make_vip_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        result = vip_db.add_vip("+15551234567")
        assert result is True
        args = backend.execute.call_args
        assert "ON CONFLICT" in args[0][0]

    def test_remove_vip_sqlite(self) -> None:
        vip_db, backend = self._make_vip_db()
        backend.execute = MagicMock(return_value=True)
        assert vip_db.remove_vip("+15551234567") is True
        args = backend.execute.call_args
        assert "DELETE FROM vip_callers" in args[0][0]
        assert "?" in args[0][0]

    def test_remove_vip_postgresql(self) -> None:
        vip_db, backend = self._make_vip_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        assert vip_db.remove_vip("+15551234567") is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_get_vip_sqlite(self) -> None:
        vip_db, backend = self._make_vip_db()
        backend.fetch_one = MagicMock(return_value={"caller_id": "+15551234567"})
        result = vip_db.get_vip("+15551234567")
        assert result == {"caller_id": "+15551234567"}

    def test_get_vip_postgresql(self) -> None:
        vip_db, backend = self._make_vip_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        result = vip_db.get_vip("+15551234567")
        assert result is None

    def test_list_vips_no_filter(self) -> None:
        vip_db, backend = self._make_vip_db()
        backend.fetch_all = MagicMock(return_value=[{"caller_id": "a"}, {"caller_id": "b"}])
        result = vip_db.list_vips()
        assert len(result) == 2
        args = backend.fetch_all.call_args
        assert "ORDER BY priority_level" in args[0][0]

    def test_list_vips_with_priority_sqlite(self) -> None:
        vip_db, backend = self._make_vip_db()
        backend.fetch_all = MagicMock(return_value=[])
        vip_db.list_vips(priority_level=1)
        args = backend.fetch_all.call_args
        assert "priority_level = ?" in args[0][0]

    def test_list_vips_with_priority_postgresql(self) -> None:
        vip_db, backend = self._make_vip_db("postgresql")
        backend.fetch_all = MagicMock(return_value=[])
        vip_db.list_vips(priority_level=2)
        args = backend.fetch_all.call_args
        assert "priority_level = %s" in args[0][0]

    def test_is_vip_true(self) -> None:
        vip_db, backend = self._make_vip_db()
        backend.fetch_one = MagicMock(return_value={"caller_id": "+15551234567"})
        assert vip_db.is_vip("+15551234567") is True

    def test_is_vip_false(self) -> None:
        vip_db, backend = self._make_vip_db()
        backend.fetch_one = MagicMock(return_value=None)
        assert vip_db.is_vip("+15551234567") is False


# ===========================================================================
# RegisteredPhonesDB tests
# ===========================================================================


@pytest.mark.unit
class TestRegisteredPhonesDB:
    """Tests for RegisteredPhonesDB."""

    def _make_phones_db(
        self, db_type: str = "sqlite"
    ) -> tuple[RegisteredPhonesDB, DatabaseBackend]:
        backend = _make_enabled_backend(db_type)
        with patch("pbx.utils.database.get_logger"):
            phones_db = RegisteredPhonesDB(backend)
        return phones_db, backend

    def test_register_phone_new_insert(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        success, mac = phones_db.register_phone("1001", "192.168.1.10", "AA:BB:CC:DD:EE:FF")
        assert success is True
        assert mac == "AA:BB:CC:DD:EE:FF"

    def test_register_phone_update_existing_by_mac(self) -> None:
        phones_db, backend = self._make_phones_db()
        existing = {
            "id": 1,
            "extension_number": "1001",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "ip_address": "192.168.1.10",
            "user_agent": "Phone/1.0",
            "contact_uri": "sip:1001@192.168.1.10",
        }

        def fetch_one_side_effect(query, params=None):
            if "mac_address" in query and "extension_number" in query:
                return existing
            if "ip_address" in query and "extension_number" not in query:
                return None
            return None

        backend.fetch_one = MagicMock(side_effect=fetch_one_side_effect)
        backend.execute = MagicMock(return_value=True)
        success, mac = phones_db.register_phone(
            "1001", "192.168.1.10", "AA:BB:CC:DD:EE:FF", "Phone/2.0"
        )
        assert success is True
        assert mac == "AA:BB:CC:DD:EE:FF"

    def test_register_phone_new_insert_no_mac(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        success, mac = phones_db.register_phone("1001", "192.168.1.10")
        assert success is True
        assert mac is None

    def test_register_phone_reprovisioning_deletes_old(self) -> None:
        phones_db, backend = self._make_phones_db()
        old_by_mac = {
            "id": 10,
            "extension_number": "1002",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "ip_address": "192.168.1.10",
        }
        call_idx = [0]

        def fetch_one_side_effect(query, params=None):
            call_idx[0] += 1
            # First calls: get_by_mac (old ext), get_by_ip (old ext) for reprovision check
            if call_idx[0] == 1:
                return old_by_mac  # mac registered to different ext
            if call_idx[0] == 2:
                return None  # ip not registered to different ext
            # After delete: check get_by_mac for current ext
            if call_idx[0] == 3:
                return None
            if call_idx[0] == 4:
                return None  # get_by_ip for current ext
            return None

        backend.fetch_one = MagicMock(side_effect=fetch_one_side_effect)
        backend.execute = MagicMock(return_value=True)
        success, mac = phones_db.register_phone("1001", "192.168.1.10", "AA:BB:CC:DD:EE:FF")
        assert success is True
        # Should have called execute for delete + insert
        assert backend.execute.call_count >= 2

    def test_register_phone_reprovisioning_by_ip(self) -> None:
        phones_db, backend = self._make_phones_db()
        old_by_ip = {
            "id": 20,
            "extension_number": "1003",
            "ip_address": "192.168.1.10",
            "mac_address": None,
        }
        call_idx = [0]

        def fetch_one_side_effect(query, params=None):
            call_idx[0] += 1
            if call_idx[0] == 1:
                return None  # no mac match (no mac provided)
            if call_idx[0] == 2:
                return old_by_ip  # ip registered to different ext
            if call_idx[0] == 3:
                return None  # get_by_ip for current ext after delete
            return None

        backend.fetch_one = MagicMock(side_effect=fetch_one_side_effect)
        backend.execute = MagicMock(return_value=True)
        success, mac = phones_db.register_phone("1001", "192.168.1.10")
        assert success is True

    def test_register_phone_update_preserves_existing_values(self) -> None:
        phones_db, backend = self._make_phones_db()
        existing = {
            "id": 5,
            "extension_number": "1001",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "ip_address": "192.168.1.10",
            "user_agent": "OldAgent",
            "contact_uri": "sip:old@example.com",
        }

        call_idx = [0]

        def fetch_one_side_effect(query, params=None):
            call_idx[0] += 1
            if call_idx[0] == 1:
                return None  # get_by_mac without ext (old check) - no mac provided
            if call_idx[0] == 2:
                return None  # get_by_ip without ext (old check)
            if call_idx[0] == 3:
                return existing  # get_by_ip with ext
            return None

        backend.fetch_one = MagicMock(side_effect=fetch_one_side_effect)
        backend.execute = MagicMock(return_value=True)

        # Pass None for user_agent and contact_uri to test preservation
        success, mac = phones_db.register_phone("1001", "192.168.1.10", None, None, None)
        assert success is True

    def test_register_phone_postgresql_syntax(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        success, mac = phones_db.register_phone("1001", "192.168.1.10", "AA:BB:CC:DD:EE:FF")
        assert success is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_get_by_mac_without_extension(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value={"mac_address": "AA:BB:CC:DD:EE:FF"})
        result = phones_db.get_by_mac("AA:BB:CC:DD:EE:FF")
        assert result is not None

    def test_get_by_mac_with_extension(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value=None)
        result = phones_db.get_by_mac("AA:BB:CC:DD:EE:FF", "1001")
        assert result is None
        args = backend.fetch_one.call_args
        assert "extension_number" in args[0][0]

    def test_get_by_mac_postgresql(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        phones_db.get_by_mac("AA:BB:CC:DD:EE:FF")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_get_by_mac_with_extension_postgresql(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        phones_db.get_by_mac("AA:BB:CC:DD:EE:FF", "1001")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_get_by_ip_without_extension(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value={"ip_address": "192.168.1.10"})
        result = phones_db.get_by_ip("192.168.1.10")
        assert result is not None

    def test_get_by_ip_with_extension(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value=None)
        result = phones_db.get_by_ip("192.168.1.10", "1001")
        assert result is None

    def test_get_by_ip_postgresql(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        phones_db.get_by_ip("192.168.1.10")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_get_by_ip_with_extension_postgresql(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        phones_db.get_by_ip("192.168.1.10", "1001")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_get_by_extension(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_all = MagicMock(return_value=[{"extension_number": "1001"}])
        result = phones_db.get_by_extension("1001")
        assert len(result) == 1

    def test_get_by_extension_postgresql(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.fetch_all = MagicMock(return_value=[])
        phones_db.get_by_extension("1001")
        args = backend.fetch_all.call_args
        assert "%s" in args[0][0]

    def test_list_all(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_all = MagicMock(return_value=[{"id": 1}, {"id": 2}])
        result = phones_db.list_all()
        assert len(result) == 2

    def test_remove_phone_sqlite(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.execute = MagicMock(return_value=True)
        assert phones_db.remove_phone(1) is True
        args = backend.execute.call_args
        assert "?" in args[0][0]

    def test_remove_phone_postgresql(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        assert phones_db.remove_phone(1) is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_update_phone_extension_success(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.execute = MagicMock(return_value=True)
        result = phones_db.update_phone_extension("AA:BB:CC:DD:EE:FF", "1002")
        assert result is True

    def test_update_phone_extension_no_mac(self) -> None:
        phones_db, backend = self._make_phones_db()
        result = phones_db.update_phone_extension("", "1002")
        assert result is False

    def test_update_phone_extension_postgresql(self) -> None:
        phones_db, backend = self._make_phones_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        phones_db.update_phone_extension("AA:BB:CC:DD:EE:FF", "1002")
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_cleanup_incomplete_registrations_none_found(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value={"count": 0})
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is True
        assert count == 0

    def test_cleanup_incomplete_registrations_some_found(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value={"count": 3})
        backend.execute = MagicMock(return_value=True)
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is True
        assert count == 3

    def test_cleanup_incomplete_registrations_delete_fails(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value={"count": 2})
        backend.execute = MagicMock(return_value=False)
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is False
        assert count == 2

    def test_cleanup_incomplete_registrations_null_result(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(return_value=None)
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is True
        assert count == 0

    def test_cleanup_incomplete_registrations_exception(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.fetch_one = MagicMock(side_effect=sqlite3.Error("fail"))
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is False
        assert count == 0

    def test_clear_all_success(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.execute = MagicMock(return_value=True)
        assert phones_db.clear_all() is True

    def test_clear_all_failure(self) -> None:
        phones_db, backend = self._make_phones_db()
        backend.execute = MagicMock(return_value=False)
        assert phones_db.clear_all() is False


# ===========================================================================
# ExtensionDB tests
# ===========================================================================


@pytest.mark.unit
class TestExtensionDB:
    """Tests for ExtensionDB."""

    def _make_ext_db(self, db_type: str = "sqlite") -> tuple[ExtensionDB, DatabaseBackend]:
        backend = _make_enabled_backend(db_type)
        with patch("pbx.utils.database.get_logger"):
            ext_db = ExtensionDB(backend)
        return ext_db, backend

    def test_hash_voicemail_pin_empty(self) -> None:
        ext_db, _ = self._make_ext_db()
        result = ext_db._hash_voicemail_pin("")
        assert result == (None, None)

    def test_hash_voicemail_pin_none(self) -> None:
        ext_db, _ = self._make_ext_db()
        result = ext_db._hash_voicemail_pin(None)
        assert result == (None, None)

    def test_hash_voicemail_pin_success(self) -> None:
        ext_db, _ = self._make_ext_db()
        mock_enc = MagicMock()
        mock_enc.hash_password.return_value = ("hashed", "salt")
        mock_encryption_module = MagicMock()
        mock_encryption_module.get_encryption = MagicMock(return_value=mock_enc)
        with patch.dict("sys.modules", {"pbx.utils.encryption": mock_encryption_module}):
            result = ext_db._hash_voicemail_pin("1234")
        assert result == ("hashed", "salt")

    def test_hash_voicemail_pin_failure(self) -> None:
        ext_db, _ = self._make_ext_db()
        # Make the import inside _hash_voicemail_pin raise
        mock_encryption_module = MagicMock()
        mock_encryption_module.get_encryption = MagicMock(side_effect=ImportError("no module"))
        with patch.dict("sys.modules", {"pbx.utils.encryption": mock_encryption_module}):
            result = ext_db._hash_voicemail_pin("1234")
        assert result == (None, None)

    def test_add_extension_no_pin(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.add("1001", "Test User", "hashval")
        assert result is True
        backend.execute.assert_called_once()

    def test_add_extension_with_pin(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        mock_enc = MagicMock()
        mock_enc.hash_password.return_value = ("pinhash", "pinsalt")
        mock_encryption_module = MagicMock()
        mock_encryption_module.get_encryption = MagicMock(return_value=mock_enc)
        with patch.dict("sys.modules", {"pbx.utils.encryption": mock_encryption_module}):
            result = ext_db.add("1001", "Test User", "hashval", voicemail_pin="1234")
        assert result is True

    def test_add_extension_pin_hash_failure(self) -> None:
        ext_db, backend = self._make_ext_db()
        mock_encryption_module = MagicMock()
        mock_encryption_module.get_encryption = MagicMock(side_effect=Exception("fail"))
        with patch.dict("sys.modules", {"pbx.utils.encryption": mock_encryption_module}):
            result = ext_db.add("1001", "Test User", "hashval", voicemail_pin="1234")
        assert result is False

    def test_add_extension_postgresql(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        result = ext_db.add("1001", "Test User", "hashval")
        assert result is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_add_extension_all_params(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.add(
            "1001",
            "Test User",
            "hashval",
            email="test@example.com",
            allow_external=False,
            ad_synced=True,
            ad_username="testuser",
            is_admin=True,
        )
        assert result is True

    def test_get_extension(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"number": "1001"})
        result = ext_db.get("1001")
        assert result == {"number": "1001"}

    def test_get_extension_postgresql(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        ext_db.get("1001")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_get_all(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_all = MagicMock(return_value=[{"number": "1001"}, {"number": "1002"}])
        result = ext_db.get_all()
        assert len(result) == 2

    def test_get_ad_synced_sqlite(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_all = MagicMock(return_value=[])
        ext_db.get_ad_synced()
        args = backend.fetch_all.call_args
        assert "ad_synced = 1" in args[0][0]

    def test_get_ad_synced_postgresql(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.fetch_all = MagicMock(return_value=[])
        ext_db.get_ad_synced()
        args = backend.fetch_all.call_args
        assert "ad_synced = %s" in args[0][0]
        assert args[0][1] == (True,)

    def test_update_no_fields(self) -> None:
        ext_db, backend = self._make_ext_db()
        result = ext_db.update("1001")
        assert result is True  # Nothing to update

    def test_update_name(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", name="New Name")
        assert result is True
        backend.execute.assert_called_once()

    def test_update_email(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", email="new@example.com")
        assert result is True

    def test_update_password(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", password_hash="newhash")
        assert result is True

    def test_update_allow_external(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", allow_external=False)
        assert result is True

    def test_update_voicemail_pin_success(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        mock_enc = MagicMock()
        mock_enc.hash_password.return_value = ("newhash", "newsalt")
        mock_encryption_module = MagicMock()
        mock_encryption_module.get_encryption = MagicMock(return_value=mock_enc)
        with patch.dict("sys.modules", {"pbx.utils.encryption": mock_encryption_module}):
            result = ext_db.update("1001", voicemail_pin="5678")
        assert result is True

    def test_update_voicemail_pin_hash_failure(self) -> None:
        ext_db, backend = self._make_ext_db()
        mock_encryption_module = MagicMock()
        mock_encryption_module.get_encryption = MagicMock(side_effect=Exception("fail"))
        with patch.dict("sys.modules", {"pbx.utils.encryption": mock_encryption_module}):
            result = ext_db.update("1001", voicemail_pin="5678")
        assert result is False

    def test_update_ad_synced(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", ad_synced=True)
        assert result is True

    def test_update_ad_username(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", ad_username="aduser")
        assert result is True

    def test_update_is_admin(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", is_admin=True)
        assert result is True

    def test_update_multiple_fields(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", name="New Name", email="new@example.com", is_admin=True)
        assert result is True

    def test_update_query_contains_set_clause(self) -> None:
        """The update method builds a query with literal {', '.join(updates)} template.
        Verify the query string and params are passed to db.execute."""
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", name="New Name")
        assert result is True
        args = backend.execute.call_args
        # The query is a non-f-string template containing literal braces
        assert "UPDATE extensions" in args[0][0]
        # Params should include name and number
        assert "New Name" in args[0][1]
        assert "1001" in args[0][1]

    def test_update_postgresql_builds_correct_params(self) -> None:
        """For postgresql, the update method uses %s placeholders."""
        ext_db, backend = self._make_ext_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        result = ext_db.update("1001", name="New Name")
        assert result is True
        args = backend.execute.call_args
        # Verify the query contains UPDATE
        assert "UPDATE extensions" in args[0][0]
        # Params should include name value and number
        params = args[0][1]
        assert "New Name" in params
        assert "1001" in params

    def test_delete_sqlite(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.execute = MagicMock(return_value=True)
        assert ext_db.delete("1001") is True
        args = backend.execute.call_args
        assert "?" in args[0][0]

    def test_delete_postgresql(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        assert ext_db.delete("1001") is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_search_sqlite(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_all = MagicMock(return_value=[])
        ext_db.search("test")
        args = backend.fetch_all.call_args
        assert "LIKE ?" in args[0][0]
        assert args[0][1] == ("%test%", "%test%", "%test%")

    def test_search_postgresql(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.fetch_all = MagicMock(return_value=[])
        ext_db.search("test")
        args = backend.fetch_all.call_args
        assert "LIKE %s" in args[0][0]


@pytest.mark.unit
class TestExtensionDBConfig:
    """Tests for ExtensionDB.get_config / set_config."""

    def _make_ext_db(self, db_type: str = "sqlite") -> tuple[ExtensionDB, DatabaseBackend]:
        backend = _make_enabled_backend(db_type)
        with patch("pbx.utils.database.get_logger"):
            ext_db = ExtensionDB(backend)
        return ext_db, backend

    def test_get_config_not_found(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value=None)
        result = ext_db.get_config("missing_key", "default_val")
        assert result == "default_val"

    def test_get_config_string_type(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(
            return_value={"config_value": "hello", "config_type": "string"}
        )
        result = ext_db.get_config("key")
        assert result == "hello"

    def test_get_config_int_type(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"config_value": "42", "config_type": "int"})
        result = ext_db.get_config("key")
        assert result == 42

    def test_get_config_int_type_empty_value(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"config_value": "", "config_type": "int"})
        result = ext_db.get_config("key", "default")
        assert result == "default"

    def test_get_config_bool_type_true(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(
            return_value={"config_value": "true", "config_type": "bool"}
        )
        result = ext_db.get_config("key")
        assert result is True

    def test_get_config_bool_type_yes(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"config_value": "yes", "config_type": "bool"})
        result = ext_db.get_config("key")
        assert result is True

    def test_get_config_bool_type_one(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"config_value": "1", "config_type": "bool"})
        result = ext_db.get_config("key")
        assert result is True

    def test_get_config_bool_type_false(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(
            return_value={"config_value": "false", "config_type": "bool"}
        )
        result = ext_db.get_config("key")
        assert result is False

    def test_get_config_bool_type_empty(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"config_value": "", "config_type": "bool"})
        result = ext_db.get_config("key", "default")
        assert result == "default"

    def test_get_config_json_type(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(
            return_value={"config_value": '{"a": 1}', "config_type": "json"}
        )
        result = ext_db.get_config("key")
        assert result == {"a": 1}

    def test_get_config_json_type_empty(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"config_value": "", "config_type": "json"})
        result = ext_db.get_config("key", "default")
        assert result == "default"

    def test_get_config_string_empty_value_returns_default(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(
            return_value={"config_value": "", "config_type": "string"}
        )
        result = ext_db.get_config("key", "default")
        assert result == "default"

    def test_get_config_parse_error_returns_default(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(
            return_value={"config_value": "not_a_number", "config_type": "int"}
        )
        result = ext_db.get_config("key", "default")
        assert result == "default"

    def test_get_config_json_parse_error_returns_default(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(
            return_value={"config_value": "{invalid json", "config_type": "json"}
        )
        result = ext_db.get_config("key", "default")
        assert result == "default"

    def test_get_config_postgresql_syntax(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        ext_db.get_config("key")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_set_config_new_key_string(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value=None)  # key doesn't exist
        backend.execute = MagicMock(return_value=True)
        result = ext_db.set_config("key", "value")
        assert result is True
        args = backend.execute.call_args
        assert "INSERT INTO system_config" in args[0][0]

    def test_set_config_existing_key(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value={"config_key": "key"})
        backend.execute = MagicMock(return_value=True)
        result = ext_db.set_config("key", "new_value")
        assert result is True
        args = backend.execute.call_args
        assert "UPDATE system_config" in args[0][0]

    def test_set_config_json_type(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        result = ext_db.set_config("key", {"a": 1}, config_type="json")
        assert result is True
        args = backend.execute.call_args
        assert '{"a": 1}' in args[0][1]

    def test_set_config_bool_type_true(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        result = ext_db.set_config("key", True, config_type="bool")
        assert result is True

    def test_set_config_bool_type_false(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        result = ext_db.set_config("key", False, config_type="bool")
        assert result is True

    def test_set_config_serialization_error(self) -> None:
        ext_db, backend = self._make_ext_db()
        # Create an object that json.dumps will fail on
        obj = object()
        result = ext_db.set_config("key", obj, config_type="json")
        assert result is False

    def test_set_config_postgresql_syntax(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        ext_db.set_config("key", "value")
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_set_config_existing_postgresql(self) -> None:
        ext_db, backend = self._make_ext_db("postgresql")
        backend.fetch_one = MagicMock(return_value={"config_key": "key"})
        backend.execute = MagicMock(return_value=True)
        ext_db.set_config("key", "new_value")
        args = backend.execute.call_args
        assert "UPDATE system_config" in args[0][0]
        assert "%s" in args[0][0]

    def test_set_config_with_updated_by(self) -> None:
        ext_db, backend = self._make_ext_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        result = ext_db.set_config("key", "value", updated_by="admin")
        assert result is True


# ===========================================================================
# ProvisionedDevicesDB tests
# ===========================================================================


@pytest.mark.unit
class TestProvisionedDevicesDB:
    """Tests for ProvisionedDevicesDB."""

    def _make_prov_db(
        self, db_type: str = "sqlite"
    ) -> tuple[ProvisionedDevicesDB, DatabaseBackend]:
        backend = _make_enabled_backend(db_type)
        with patch("pbx.utils.database.get_logger"):
            prov_db = ProvisionedDevicesDB(backend)
        return prov_db, backend

    def test_add_device_new_insert(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        with patch("pbx.utils.database.detect_device_type", return_value="phone"):
            result = prov_db.add_device("AA:BB:CC:DD:EE:FF", "1001", "cisco", "7960")
        assert result is True
        args = backend.execute.call_args
        assert "INSERT INTO provisioned_devices" in args[0][0]

    def test_add_device_update_existing(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_one = MagicMock(return_value={"mac_address": "AA:BB:CC:DD:EE:FF"})
        backend.execute = MagicMock(return_value=True)
        with patch("pbx.utils.database.detect_device_type", return_value="phone"):
            result = prov_db.add_device("AA:BB:CC:DD:EE:FF", "1001", "cisco", "7960")
        assert result is True
        args = backend.execute.call_args
        assert "UPDATE provisioned_devices" in args[0][0]

    def test_add_device_with_explicit_device_type(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        result = prov_db.add_device(
            "AA:BB:CC:DD:EE:FF", "1001", "grandstream", "ht801", device_type="ata"
        )
        assert result is True

    def test_add_device_postgresql_new(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        with patch("pbx.utils.database.detect_device_type", return_value="phone"):
            result = prov_db.add_device("AA:BB:CC:DD:EE:FF", "1001", "cisco", "7960")
        assert result is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_add_device_postgresql_update(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.fetch_one = MagicMock(return_value={"mac_address": "AA:BB:CC:DD:EE:FF"})
        backend.execute = MagicMock(return_value=True)
        with patch("pbx.utils.database.detect_device_type", return_value="phone"):
            result = prov_db.add_device("AA:BB:CC:DD:EE:FF", "1001", "cisco", "7960")
        assert result is True
        args = backend.execute.call_args
        assert "UPDATE" in args[0][0]
        assert "%s" in args[0][0]

    def test_add_device_with_all_params(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_one = MagicMock(return_value=None)
        backend.execute = MagicMock(return_value=True)
        result = prov_db.add_device(
            "AA:BB:CC:DD:EE:FF",
            "1001",
            "cisco",
            "7960",
            device_type="phone",
            static_ip="10.0.0.1",
            config_url="http://example.com/config",
        )
        assert result is True

    def test_get_device_sqlite(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_one = MagicMock(return_value={"mac_address": "AA:BB:CC:DD:EE:FF"})
        result = prov_db.get_device("AA:BB:CC:DD:EE:FF")
        assert result is not None

    def test_get_device_postgresql(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        prov_db.get_device("AA:BB:CC:DD:EE:FF")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_get_device_by_extension_sqlite(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_one = MagicMock(return_value={"extension_number": "1001"})
        result = prov_db.get_device_by_extension("1001")
        assert result is not None

    def test_get_device_by_extension_postgresql(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        prov_db.get_device_by_extension("1001")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_get_device_by_ip_sqlite(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_one = MagicMock(return_value={"static_ip": "10.0.0.1"})
        result = prov_db.get_device_by_ip("10.0.0.1")
        assert result is not None

    def test_get_device_by_ip_postgresql(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.fetch_one = MagicMock(return_value=None)
        prov_db.get_device_by_ip("10.0.0.1")
        args = backend.fetch_one.call_args
        assert "%s" in args[0][0]

    def test_list_all(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_all = MagicMock(return_value=[{"id": 1}])
        result = prov_db.list_all()
        assert len(result) == 1

    def test_list_by_type_sqlite(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_all = MagicMock(return_value=[])
        prov_db.list_by_type("phone")
        args = backend.fetch_all.call_args
        assert "device_type = ?" in args[0][0]

    def test_list_by_type_postgresql(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.fetch_all = MagicMock(return_value=[])
        prov_db.list_by_type("ata")
        args = backend.fetch_all.call_args
        assert "device_type = %s" in args[0][0]

    def test_list_atas(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_all = MagicMock(return_value=[])
        prov_db.list_atas()
        args = backend.fetch_all.call_args
        assert args[0][1] == ("ata",)

    def test_list_phones(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.fetch_all = MagicMock(return_value=[])
        prov_db.list_phones()
        args = backend.fetch_all.call_args
        assert args[0][1] == ("phone",)

    def test_detect_device_type_phone(self) -> None:
        prov_db, backend = self._make_prov_db()
        with patch("pbx.utils.database.detect_device_type", return_value="phone"):
            result = prov_db._detect_device_type("cisco", "7960")
        assert result == "phone"

    def test_detect_device_type_ata(self) -> None:
        prov_db, backend = self._make_prov_db()
        with patch("pbx.utils.database.detect_device_type", return_value="ata"):
            result = prov_db._detect_device_type("grandstream", "ht801")
        assert result == "ata"

    def test_remove_device_sqlite(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.execute = MagicMock(return_value=True)
        assert prov_db.remove_device("AA:BB:CC:DD:EE:FF") is True
        args = backend.execute.call_args
        assert "?" in args[0][0]

    def test_remove_device_postgresql(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        assert prov_db.remove_device("AA:BB:CC:DD:EE:FF") is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_mark_provisioned_sqlite(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.execute = MagicMock(return_value=True)
        assert prov_db.mark_provisioned("AA:BB:CC:DD:EE:FF") is True
        args = backend.execute.call_args
        assert "last_provisioned" in args[0][0]
        assert "?" in args[0][0]

    def test_mark_provisioned_postgresql(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        assert prov_db.mark_provisioned("AA:BB:CC:DD:EE:FF") is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]

    def test_set_static_ip_sqlite(self) -> None:
        prov_db, backend = self._make_prov_db()
        backend.execute = MagicMock(return_value=True)
        assert prov_db.set_static_ip("AA:BB:CC:DD:EE:FF", "10.0.0.1") is True
        args = backend.execute.call_args
        assert "static_ip" in args[0][0]

    def test_set_static_ip_postgresql(self) -> None:
        prov_db, backend = self._make_prov_db("postgresql")
        backend.execute = MagicMock(return_value=True)
        assert prov_db.set_static_ip("AA:BB:CC:DD:EE:FF", "10.0.0.1") is True
        args = backend.execute.call_args
        assert "%s" in args[0][0]


# ===========================================================================
# get_database global function tests
# ===========================================================================


@pytest.mark.unit
class TestGetDatabase:
    """Tests for the get_database() global function."""

    def test_get_database_creates_instance(self) -> None:
        import pbx.utils.database as db_module

        original = db_module._database
        try:
            db_module._database = None
            config = _make_config()
            with patch("pbx.utils.database.get_logger"):
                result = get_database(config)
            assert result is not None
            assert isinstance(result, DatabaseBackend)
        finally:
            db_module._database = original

    def test_get_database_returns_existing_instance(self) -> None:
        import pbx.utils.database as db_module

        original = db_module._database
        try:
            mock_db = MagicMock(spec=DatabaseBackend)
            db_module._database = mock_db
            result = get_database()
            assert result is mock_db
        finally:
            db_module._database = original

    def test_get_database_returns_none_without_config(self) -> None:
        import pbx.utils.database as db_module

        original = db_module._database
        try:
            db_module._database = None
            result = get_database()
            assert result is None
        finally:
            db_module._database = original

    def test_get_database_does_not_recreate_if_exists(self) -> None:
        import pbx.utils.database as db_module

        original = db_module._database
        try:
            mock_db = MagicMock(spec=DatabaseBackend)
            db_module._database = mock_db
            config = _make_config()
            result = get_database(config)
            # Should return existing, not create new
            assert result is mock_db
        finally:
            db_module._database = original


# ===========================================================================
# Edge case / integration-style tests
# ===========================================================================


@pytest.mark.unit
class TestDatabaseBackendEdgeCases:
    """Additional edge case tests."""

    def test_execute_with_context_already_exists_with_rollback(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("unique constraint violation")
        result = db._execute_with_context("INSERT ...", "insert", critical=True)
        assert result is True  # "unique constraint" matches already_exists
        db.connection.rollback.assert_called_once()

    def test_execute_with_context_must_be_owner_non_critical(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("must be owner of table foo")
        result = db._execute_with_context("ALTER TABLE ...", "alter", critical=False)
        assert result is True

    def test_execute_with_context_access_denied_non_critical(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("access denied for user")
        result = db._execute_with_context("DROP TABLE ...", "drop", critical=False)
        assert result is True

    def test_execute_with_context_insufficient_privileges_non_critical(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("insufficient privileges")
        result = db._execute_with_context("CREATE INDEX ...", "index", critical=False)
        assert result is True

    def test_execute_with_context_duplicate_already_exists(self) -> None:
        db = _make_enabled_backend()
        db._autocommit = True
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("duplicate key value")
        result = db._execute_with_context("INSERT ...", "insert", critical=True)
        assert result is True
        db.connection.rollback.assert_not_called()

    def test_postgresql_fetch_one_uses_real_dict_cursor(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1}
        mock_rdc = MagicMock()
        with patch("pbx.utils.database.RealDictCursor", mock_rdc, create=True):
            db.fetch_one("SELECT 1")
            db.connection.cursor.assert_called_with(cursor_factory=mock_rdc)

    def test_postgresql_fetch_all_uses_real_dict_cursor(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_rdc = MagicMock()
        with patch("pbx.utils.database.RealDictCursor", mock_rdc, create=True):
            db.fetch_all("SELECT 1")
            db.connection.cursor.assert_called_with(cursor_factory=mock_rdc)

    def test_execute_script_postgresql_skips_comments_and_empty_lines(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        script = "-- This is a comment\n\n-- Another comment\nSELECT 1;\n\n-- end"
        result = db.execute_script(script)
        assert result is True
        # Only one statement should be executed
        assert mock_cursor.execute.call_count == 1

    def test_build_table_sql_no_placeholders(self) -> None:
        db = _make_enabled_backend()
        result = db._build_table_sql("CREATE TABLE test (id INT)")
        assert result == "CREATE TABLE test (id INT)"

    def test_migrate_schema_postgresql_query_syntax(self) -> None:
        db = _make_enabled_backend("postgresql")
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"column_name": "transcription_text"}
        with patch.object(db, "_apply_framework_migrations"):
            db._migrate_schema()
        # Verify PostgreSQL-style queries were used
        calls = mock_cursor.execute.call_args_list
        assert any("information_schema" in str(c) for c in calls)

    def test_cleanup_incomplete_registrations_key_error(self) -> None:
        backend_obj = _make_enabled_backend()
        with patch("pbx.utils.database.get_logger"):
            phones_db = RegisteredPhonesDB(backend_obj)
        backend_obj.fetch_one = MagicMock(side_effect=KeyError("missing"))
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is False
        assert count == 0

    def test_cleanup_incomplete_registrations_type_error(self) -> None:
        backend_obj = _make_enabled_backend()
        with patch("pbx.utils.database.get_logger"):
            phones_db = RegisteredPhonesDB(backend_obj)
        backend_obj.fetch_one = MagicMock(side_effect=TypeError("bad type"))
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is False
        assert count == 0

    def test_set_config_type_error_during_serialization(self) -> None:
        """Test that TypeError during value serialization returns False."""
        backend = _make_enabled_backend()
        with patch("pbx.utils.database.get_logger"):
            ext_db = ExtensionDB(backend)
        # A set cannot be serialized to string easily
        result = ext_db.set_config("key", {1, 2, 3}, config_type="json")
        assert result is False

    def test_get_config_attribute_error_returns_default(self) -> None:
        """Test that AttributeError during parsing returns default."""
        backend = _make_enabled_backend()
        with patch("pbx.utils.database.get_logger"):
            ext_db = ExtensionDB(backend)
        # bool type with non-string value that doesn't have .lower()
        backend.fetch_one = MagicMock(
            return_value={"config_value": 123, "config_type": "bool"}
        )
        result = ext_db.get_config("key", "default")
        # 123 is truthy and not a string, so the isinstance check fails -> returns default
        assert result == "default"

    def test_get_config_bool_non_string_truthy_value(self) -> None:
        """Test bool type with non-None non-string that is not isinstance(str)."""
        backend = _make_enabled_backend()
        with patch("pbx.utils.database.get_logger"):
            ext_db = ExtensionDB(backend)
        backend.fetch_one = MagicMock(
            return_value={"config_value": None, "config_type": "bool"}
        )
        result = ext_db.get_config("key", "default")
        assert result == "default"

    def test_execute_with_context_permission_error_critical_is_actual_error(self) -> None:
        """Permission error with critical=True should NOT be treated as permission error."""
        db = _make_enabled_backend()
        db._autocommit = False
        mock_cursor = MagicMock()
        db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("permission denied for table")
        # With critical=True, permission errors are NOT specially handled
        # The code checks `not critical and any(...)` - so critical=True skips this path
        # Then checks already_exists patterns... "permission denied" doesn't match those
        # So it falls through to the actual error path
        result = db._execute_with_context("CREATE TABLE ...", "table creation", critical=True)
        assert result is False

    def test_update_phone_extension_execute_failure(self) -> None:
        """Test update_phone_extension when execute returns False."""
        backend_obj = _make_enabled_backend()
        with patch("pbx.utils.database.get_logger"):
            phones_db = RegisteredPhonesDB(backend_obj)
        backend_obj.execute = MagicMock(return_value=False)
        result = phones_db.update_phone_extension("AA:BB:CC:DD:EE:FF", "1002")
        assert result is False

    def test_cleanup_incomplete_registrations_value_error(self) -> None:
        backend_obj = _make_enabled_backend()
        with patch("pbx.utils.database.get_logger"):
            phones_db = RegisteredPhonesDB(backend_obj)
        backend_obj.fetch_one = MagicMock(side_effect=ValueError("bad value"))
        success, count = phones_db.cleanup_incomplete_registrations()
        assert success is False
        assert count == 0
