"""Comprehensive tests for pbx/utils/migrations.py database migration system."""

from unittest.mock import MagicMock, call, patch

import pytest

from pbx.utils.migrations import MigrationManager, register_all_migrations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_backend(db_type: str = "sqlite") -> MagicMock:
    """Return a mock database backend configured for the given db_type."""
    db = MagicMock()
    db.db_type = db_type
    db.execute.return_value = None
    db.execute_script.return_value = None
    db.fetch_one.return_value = None
    db.fetch_all.return_value = []
    return db


# ===========================================================================
# MigrationManager.__init__
# ===========================================================================


@pytest.mark.unit
class TestMigrationManagerInit:
    """Tests for MigrationManager initialization."""

    @patch("pbx.utils.migrations.get_logger")
    def test_init_sets_db(self, mock_get_logger: MagicMock) -> None:
        """db attribute must be set to the provided backend."""
        db = _make_db_backend()
        mgr = MigrationManager(db)
        assert mgr.db is db

    @patch("pbx.utils.migrations.get_logger")
    def test_init_sets_logger(self, mock_get_logger: MagicMock) -> None:
        """Logger must be obtained from get_logger."""
        db = _make_db_backend()
        mgr = MigrationManager(db)
        mock_get_logger.assert_called_once()
        assert mgr.logger is mock_get_logger.return_value

    @patch("pbx.utils.migrations.get_logger")
    def test_init_empty_migrations(self, mock_get_logger: MagicMock) -> None:
        """migrations list must start empty."""
        db = _make_db_backend()
        mgr = MigrationManager(db)
        assert mgr.migrations == []


# ===========================================================================
# MigrationManager._build_migration_sql
# ===========================================================================


@pytest.mark.unit
class TestBuildMigrationSQL:
    """Tests for SQL template placeholder replacement."""

    @patch("pbx.utils.migrations.get_logger")
    def test_postgresql_serial(self, mock_get_logger: MagicMock) -> None:
        """{SERIAL} should expand to 'SERIAL PRIMARY KEY' for PostgreSQL."""
        mgr = MigrationManager(_make_db_backend("postgresql"))
        result = mgr._build_migration_sql("id {SERIAL}")
        assert "SERIAL PRIMARY KEY" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_sqlite_serial(self, mock_get_logger: MagicMock) -> None:
        """{SERIAL} should expand to 'INTEGER PRIMARY KEY AUTOINCREMENT' for SQLite."""
        mgr = MigrationManager(_make_db_backend("sqlite"))
        result = mgr._build_migration_sql("id {SERIAL}")
        assert "INTEGER PRIMARY KEY AUTOINCREMENT" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_postgresql_boolean_true(self, mock_get_logger: MagicMock) -> None:
        """{BOOLEAN_TRUE} should expand to 'TRUE' for PostgreSQL."""
        mgr = MigrationManager(_make_db_backend("postgresql"))
        result = mgr._build_migration_sql("DEFAULT {BOOLEAN_TRUE}")
        assert "DEFAULT TRUE" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_sqlite_boolean_true(self, mock_get_logger: MagicMock) -> None:
        """{BOOLEAN_TRUE} should expand to '1' for SQLite."""
        mgr = MigrationManager(_make_db_backend("sqlite"))
        result = mgr._build_migration_sql("DEFAULT {BOOLEAN_TRUE}")
        assert "DEFAULT 1" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_postgresql_boolean_false(self, mock_get_logger: MagicMock) -> None:
        """{BOOLEAN_FALSE} should expand to 'FALSE' for PostgreSQL."""
        mgr = MigrationManager(_make_db_backend("postgresql"))
        result = mgr._build_migration_sql("DEFAULT {BOOLEAN_FALSE}")
        assert "DEFAULT FALSE" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_sqlite_boolean_false(self, mock_get_logger: MagicMock) -> None:
        """{BOOLEAN_FALSE} should expand to '0' for SQLite."""
        mgr = MigrationManager(_make_db_backend("sqlite"))
        result = mgr._build_migration_sql("DEFAULT {BOOLEAN_FALSE}")
        assert "DEFAULT 0" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_postgresql_bytea(self, mock_get_logger: MagicMock) -> None:
        """{BYTEA} should expand to 'BYTEA' for PostgreSQL."""
        mgr = MigrationManager(_make_db_backend("postgresql"))
        result = mgr._build_migration_sql("col {BYTEA}")
        assert "col BYTEA" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_sqlite_bytea(self, mock_get_logger: MagicMock) -> None:
        """{BYTEA} should expand to 'BLOB' for SQLite."""
        mgr = MigrationManager(_make_db_backend("sqlite"))
        result = mgr._build_migration_sql("col {BYTEA}")
        assert "col BLOB" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_text_placeholder(self, mock_get_logger: MagicMock) -> None:
        """{TEXT} should always expand to 'TEXT'."""
        for db_type in ("sqlite", "postgresql"):
            mgr = MigrationManager(_make_db_backend(db_type))
            result = mgr._build_migration_sql("col {TEXT}")
            assert "col TEXT" in result

    @patch("pbx.utils.migrations.get_logger")
    def test_multiple_placeholders(self, mock_get_logger: MagicMock) -> None:
        """Multiple different placeholders should all be replaced."""
        mgr = MigrationManager(_make_db_backend("postgresql"))
        template = "id {SERIAL}, active {BOOLEAN_TRUE}, data {BYTEA}, notes {TEXT}"
        result = mgr._build_migration_sql(template)
        assert "SERIAL PRIMARY KEY" in result
        assert "TRUE" in result
        assert "BYTEA" in result
        assert "TEXT" in result
        assert "{" not in result

    @patch("pbx.utils.migrations.get_logger")
    def test_no_placeholders(self, mock_get_logger: MagicMock) -> None:
        """Plain SQL without placeholders should pass through unchanged."""
        mgr = MigrationManager(_make_db_backend("sqlite"))
        sql = "CREATE TABLE foo (id INTEGER, name TEXT)"
        assert mgr._build_migration_sql(sql) == sql


# ===========================================================================
# MigrationManager.register_migration
# ===========================================================================


@pytest.mark.unit
class TestRegisterMigration:
    """Tests for registering migrations."""

    @patch("pbx.utils.migrations.get_logger")
    def test_register_single_migration(self, mock_get_logger: MagicMock) -> None:
        """Registering one migration adds it to the list."""
        mgr = MigrationManager(_make_db_backend())
        mgr.register_migration(1, "first", "CREATE TABLE t1 (id INT)")
        assert len(mgr.migrations) == 1
        assert mgr.migrations[0] == {
            "version": 1,
            "name": "first",
            "sql": "CREATE TABLE t1 (id INT)",
        }

    @patch("pbx.utils.migrations.get_logger")
    def test_register_multiple_migrations(self, mock_get_logger: MagicMock) -> None:
        """Multiple registrations append in order."""
        mgr = MigrationManager(_make_db_backend())
        mgr.register_migration(1, "first", "SQL1")
        mgr.register_migration(2, "second", "SQL2")
        assert len(mgr.migrations) == 2
        assert mgr.migrations[0]["version"] == 1
        assert mgr.migrations[1]["version"] == 2

    @patch("pbx.utils.migrations.get_logger")
    def test_register_preserves_sql(self, mock_get_logger: MagicMock) -> None:
        """SQL content must be stored verbatim."""
        mgr = MigrationManager(_make_db_backend())
        sql = "CREATE TABLE IF NOT EXISTS test (col TEXT NOT NULL)"
        mgr.register_migration(42, "test_migration", sql)
        assert mgr.migrations[0]["sql"] == sql


# ===========================================================================
# MigrationManager.init_migrations_table
# ===========================================================================


@pytest.mark.unit
class TestInitMigrationsTable:
    """Tests for creating the schema_migrations tracking table."""

    @patch("pbx.utils.migrations.get_logger")
    def test_postgresql_uses_varchar(self, mock_get_logger: MagicMock) -> None:
        """PostgreSQL SQL should use VARCHAR(255)."""
        db = _make_db_backend("postgresql")
        mgr = MigrationManager(db)
        result = mgr.init_migrations_table()
        assert result is True
        sql_arg = db.execute.call_args[0][0]
        assert "VARCHAR(255)" in sql_arg

    @patch("pbx.utils.migrations.get_logger")
    def test_sqlite_uses_text(self, mock_get_logger: MagicMock) -> None:
        """SQLite SQL should use TEXT."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        result = mgr.init_migrations_table()
        assert result is True
        sql_arg = db.execute.call_args[0][0]
        assert "TEXT" in sql_arg

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_true_on_success(self, mock_get_logger: MagicMock) -> None:
        """Must return True when table creation succeeds."""
        mgr = MigrationManager(_make_db_backend())
        assert mgr.init_migrations_table() is True

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_false_on_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        """Must return False on Exception."""
        db = _make_db_backend()
        db.execute.side_effect = Exception("table locked")
        mgr = MigrationManager(db)
        assert mgr.init_migrations_table() is False

    @patch("pbx.utils.migrations.get_logger")
    def test_logs_info_on_success(self, mock_get_logger: MagicMock) -> None:
        """Must log info message on success."""
        mgr = MigrationManager(_make_db_backend())
        mgr.init_migrations_table()
        mgr.logger.info.assert_called_with("Migrations table initialized")

    @patch("pbx.utils.migrations.get_logger")
    def test_logs_error_on_failure(self, mock_get_logger: MagicMock) -> None:
        """Must log error on Exception."""
        db = _make_db_backend()
        db.execute.side_effect = Exception("boom")
        mgr = MigrationManager(db)
        mgr.init_migrations_table()
        mgr.logger.error.assert_called_once()


# ===========================================================================
# MigrationManager.get_current_version
# ===========================================================================


@pytest.mark.unit
class TestGetCurrentVersion:
    """Tests for reading the current schema version."""

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_version_from_db(self, mock_get_logger: MagicMock) -> None:
        """Must return the max_version from the database."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 5}
        mgr = MigrationManager(db)
        assert mgr.get_current_version() == 5

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_zero_when_no_rows(self, mock_get_logger: MagicMock) -> None:
        """Must return 0 when fetch_one returns None."""
        db = _make_db_backend()
        db.fetch_one.return_value = None
        mgr = MigrationManager(db)
        assert mgr.get_current_version() == 0

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_zero_when_max_version_is_none(self, mock_get_logger: MagicMock) -> None:
        """Must return 0 when max_version value is None (empty table)."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": None}
        mgr = MigrationManager(db)
        assert mgr.get_current_version() == 0

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_zero_on_key_error(self, mock_get_logger: MagicMock) -> None:
        """Must return 0 on KeyError."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"wrong_key": 3}
        mgr = MigrationManager(db)
        assert mgr.get_current_version() == 0

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_zero_on_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        """Must return 0 on Exception."""
        db = _make_db_backend()
        db.fetch_one.side_effect = Exception("no such table")
        mgr = MigrationManager(db)
        assert mgr.get_current_version() == 0

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_zero_on_type_error(self, mock_get_logger: MagicMock) -> None:
        """Must return 0 on TypeError."""
        db = _make_db_backend()
        db.fetch_one.side_effect = TypeError("unexpected")
        mgr = MigrationManager(db)
        assert mgr.get_current_version() == 0

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_zero_on_value_error(self, mock_get_logger: MagicMock) -> None:
        """Must return 0 on ValueError."""
        db = _make_db_backend()
        db.fetch_one.side_effect = ValueError("bad value")
        mgr = MigrationManager(db)
        assert mgr.get_current_version() == 0

    @patch("pbx.utils.migrations.get_logger")
    def test_logs_warning_on_error(self, mock_get_logger: MagicMock) -> None:
        """Must log a warning when version cannot be fetched."""
        db = _make_db_backend()
        db.fetch_one.side_effect = Exception("oops")
        mgr = MigrationManager(db)
        mgr.get_current_version()
        mgr.logger.warning.assert_called_once()


# ===========================================================================
# MigrationManager.apply_migrations
# ===========================================================================


@pytest.mark.unit
class TestApplyMigrations:
    """Tests for applying pending migrations."""

    @patch("pbx.utils.migrations.get_logger")
    def test_no_pending_returns_true(self, mock_get_logger: MagicMock) -> None:
        """Must return True when there are no pending migrations."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 5}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "old", "SQL1")
        assert mgr.apply_migrations() is True

    @patch("pbx.utils.migrations.get_logger")
    def test_applies_single_migration(self, mock_get_logger: MagicMock) -> None:
        """Must execute_script for a single pending migration."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "create_users", "CREATE TABLE users (id INT)")
        result = mgr.apply_migrations()
        assert result is True
        db.execute_script.assert_called_once_with("CREATE TABLE users (id INT)")

    @patch("pbx.utils.migrations.get_logger")
    def test_records_migration_version_sqlite(self, mock_get_logger: MagicMock) -> None:
        """Must INSERT migration record with ? placeholders for SQLite."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "first", "SQL")
        mgr.apply_migrations()
        # The second execute call records the migration (first is init_migrations_table)
        record_call = db.execute.call_args_list[-1]
        sql_arg = record_call[0][0]
        assert "?" in sql_arg
        assert record_call[0][1] == (1, "first")

    @patch("pbx.utils.migrations.get_logger")
    def test_records_migration_version_postgresql(self, mock_get_logger: MagicMock) -> None:
        """Must INSERT migration record with %s placeholders for PostgreSQL."""
        db = _make_db_backend("postgresql")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "first", "SQL")
        mgr.apply_migrations()
        record_call = db.execute.call_args_list[-1]
        sql_arg = record_call[0][0]
        assert "%s" in sql_arg
        assert record_call[0][1] == (1, "first")

    @patch("pbx.utils.migrations.get_logger")
    def test_applies_only_newer_migrations(self, mock_get_logger: MagicMock) -> None:
        """Must skip migrations at or below the current version."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 2}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        mgr.register_migration(3, "three", "SQL3")
        mgr.register_migration(4, "four", "SQL4")
        mgr.apply_migrations()
        assert db.execute_script.call_count == 2
        db.execute_script.assert_any_call("SQL3")
        db.execute_script.assert_any_call("SQL4")

    @patch("pbx.utils.migrations.get_logger")
    def test_applies_up_to_target_version(self, mock_get_logger: MagicMock) -> None:
        """Must stop at the specified target_version."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        mgr.register_migration(3, "three", "SQL3")
        mgr.apply_migrations(target_version=2)
        assert db.execute_script.call_count == 2
        db.execute_script.assert_any_call("SQL1")
        db.execute_script.assert_any_call("SQL2")

    @patch("pbx.utils.migrations.get_logger")
    def test_migrations_applied_in_order(self, mock_get_logger: MagicMock) -> None:
        """Migrations must be applied in ascending version order."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        # Register out of order
        mgr.register_migration(3, "three", "SQL3")
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        mgr.apply_migrations()
        calls = db.execute_script.call_args_list
        assert calls[0][0][0] == "SQL1"
        assert calls[1][0][0] == "SQL2"
        assert calls[2][0][0] == "SQL3"

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_false_on_error(self, mock_get_logger: MagicMock) -> None:
        """Must return False when migration execution raises an error."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        db.execute_script.side_effect = Exception("syntax error")
        mgr = MigrationManager(db)
        mgr.register_migration(1, "bad", "INVALID SQL")
        assert mgr.apply_migrations() is False

    @patch("pbx.utils.migrations.get_logger")
    def test_logs_error_on_failure(self, mock_get_logger: MagicMock) -> None:
        """Must log error when migration fails."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        db.execute_script.side_effect = Exception("fail")
        mgr = MigrationManager(db)
        mgr.register_migration(1, "bad", "INVALID SQL")
        mgr.apply_migrations()
        mgr.logger.error.assert_called_once()

    @patch("pbx.utils.migrations.get_logger")
    def test_logs_no_pending(self, mock_get_logger: MagicMock) -> None:
        """Must log 'No pending migrations' when all are applied."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 10}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "old", "SQL")
        mgr.apply_migrations()
        mgr.logger.info.assert_any_call("No pending migrations")

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_true_with_empty_migrations_list(self, mock_get_logger: MagicMock) -> None:
        """Must return True when there are no registered migrations at all."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        assert mgr.apply_migrations() is True

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_false_on_key_error(self, mock_get_logger: MagicMock) -> None:
        """Must return False on KeyError during migration."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        db.execute_script.side_effect = KeyError("missing")
        mgr = MigrationManager(db)
        mgr.register_migration(1, "bad", "SQL")
        assert mgr.apply_migrations() is False

    @patch("pbx.utils.migrations.get_logger")
    def test_target_version_zero_still_runs_applicable(self, mock_get_logger: MagicMock) -> None:
        """target_version=0 (falsy) should behave as None (apply all)."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        # target_version=0 is falsy, so the filter won't be applied
        mgr.apply_migrations(target_version=0)
        assert db.execute_script.call_count == 2


# ===========================================================================
# MigrationManager.get_migration_status
# ===========================================================================


@pytest.mark.unit
class TestGetMigrationStatus:
    """Tests for retrieving migration status."""

    @patch("pbx.utils.migrations.get_logger")
    def test_all_pending(self, mock_get_logger: MagicMock) -> None:
        """All migrations must show 'pending' when none are applied."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 0}
        db.fetch_all.return_value = []
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        status = mgr.get_migration_status()
        assert len(status) == 2
        assert all(s["status"] == "pending" for s in status)
        assert all(s["applied_at"] is None for s in status)

    @patch("pbx.utils.migrations.get_logger")
    def test_all_applied(self, mock_get_logger: MagicMock) -> None:
        """All migrations must show 'applied' when all are recorded."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 2}
        db.fetch_all.return_value = [
            {"version": 1, "name": "one", "applied_at": "2025-01-01T00:00:00"},
            {"version": 2, "name": "two", "applied_at": "2025-01-02T00:00:00"},
        ]
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        status = mgr.get_migration_status()
        assert len(status) == 2
        assert all(s["status"] == "applied" for s in status)
        assert status[0]["applied_at"] == "2025-01-01T00:00:00"
        assert status[1]["applied_at"] == "2025-01-02T00:00:00"

    @patch("pbx.utils.migrations.get_logger")
    def test_mixed_status(self, mock_get_logger: MagicMock) -> None:
        """Some migrations applied, some pending."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 1}
        db.fetch_all.return_value = [
            {"version": 1, "name": "one", "applied_at": "2025-01-01T00:00:00"},
        ]
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        status = mgr.get_migration_status()
        assert len(status) == 2
        assert status[0]["status"] == "applied"
        assert status[1]["status"] == "pending"

    @patch("pbx.utils.migrations.get_logger")
    def test_status_sorted_by_version(self, mock_get_logger: MagicMock) -> None:
        """Status list must be sorted by version number."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 0}
        db.fetch_all.return_value = []
        mgr = MigrationManager(db)
        mgr.register_migration(3, "three", "SQL3")
        mgr.register_migration(1, "one", "SQL1")
        mgr.register_migration(2, "two", "SQL2")
        status = mgr.get_migration_status()
        versions = [s["version"] for s in status]
        assert versions == [1, 2, 3]

    @patch("pbx.utils.migrations.get_logger")
    def test_returns_empty_on_error(self, mock_get_logger: MagicMock) -> None:
        """Must return empty list on error from fetch_all."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 0}
        db.fetch_all.side_effect = Exception("fail")
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        status = mgr.get_migration_status()
        assert status == []

    @patch("pbx.utils.migrations.get_logger")
    def test_logs_error_on_failure(self, mock_get_logger: MagicMock) -> None:
        """Must log error when status retrieval fails."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 0}
        db.fetch_all.side_effect = Exception("fail")
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        mgr.get_migration_status()
        mgr.logger.error.assert_called_once()

    @patch("pbx.utils.migrations.get_logger")
    def test_empty_migrations_list(self, mock_get_logger: MagicMock) -> None:
        """Must return empty list when no migrations are registered."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 0}
        db.fetch_all.return_value = []
        mgr = MigrationManager(db)
        status = mgr.get_migration_status()
        assert status == []

    @patch("pbx.utils.migrations.get_logger")
    def test_handles_none_from_fetch_all(self, mock_get_logger: MagicMock) -> None:
        """Must handle None returned from fetch_all (no rows)."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 0}
        db.fetch_all.return_value = None
        mgr = MigrationManager(db)
        mgr.register_migration(1, "one", "SQL1")
        status = mgr.get_migration_status()
        assert len(status) == 1
        assert status[0]["status"] == "pending"

    @patch("pbx.utils.migrations.get_logger")
    def test_status_includes_name(self, mock_get_logger: MagicMock) -> None:
        """Each status entry must include the migration name."""
        db = _make_db_backend()
        db.fetch_one.return_value = {"max_version": 0}
        db.fetch_all.return_value = []
        mgr = MigrationManager(db)
        mgr.register_migration(1, "Create users table", "SQL1")
        status = mgr.get_migration_status()
        assert status[0]["name"] == "Create users table"


# ===========================================================================
# register_all_migrations (module-level function)
# ===========================================================================


@pytest.mark.unit
class TestRegisterAllMigrations:
    """Tests for the register_all_migrations function."""

    @patch("pbx.utils.migrations.get_logger")
    def test_registers_all_eleven_migrations(self, mock_get_logger: MagicMock) -> None:
        """Must register exactly 11 migrations (1000-1010)."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        assert len(mgr.migrations) == 11

    @patch("pbx.utils.migrations.get_logger")
    def test_migration_versions_are_sequential(self, mock_get_logger: MagicMock) -> None:
        """Migration versions must be 1000 through 1010."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        versions = sorted(m["version"] for m in mgr.migrations)
        assert versions == list(range(1000, 1011))

    @patch("pbx.utils.migrations.get_logger")
    def test_migration_names(self, mock_get_logger: MagicMock) -> None:
        """All migration names must be set."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        names = {m["version"]: m["name"] for m in mgr.migrations}
        assert names[1000] == "AI Features Framework"
        assert names[1001] == "Video Conferencing Framework"
        assert names[1002] == "Emergency Services Framework"
        assert names[1003] == "Analytics & Reporting Framework"
        assert names[1004] == "Integration Framework"
        assert names[1005] == "Mobile Framework"
        assert names[1006] == "Advanced Call Features Framework"
        assert names[1007] == "SIP Trunking Framework"
        assert names[1008] == "Collaboration Framework"
        assert names[1009] == "Compliance Framework"
        assert names[1010] == "Click-to-Dial Framework"

    @patch("pbx.utils.migrations.get_logger")
    def test_all_migrations_have_sql(self, mock_get_logger: MagicMock) -> None:
        """Every migration must have non-empty SQL."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        for migration in mgr.migrations:
            assert migration["sql"] is not None
            assert len(migration["sql"].strip()) > 0

    @patch("pbx.utils.migrations.get_logger")
    def test_sqlite_sql_contains_no_placeholders(self, mock_get_logger: MagicMock) -> None:
        """After building for SQLite, no {SERIAL} etc. placeholders should remain."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        placeholders = ["{SERIAL}", "{BOOLEAN_TRUE}", "{BOOLEAN_FALSE}", "{BYTEA}", "{TEXT}"]
        for migration in mgr.migrations:
            for placeholder in placeholders:
                assert placeholder not in migration["sql"], (
                    f"Placeholder {placeholder} found in migration {migration['version']}"
                )

    @patch("pbx.utils.migrations.get_logger")
    def test_postgresql_sql_contains_no_placeholders(self, mock_get_logger: MagicMock) -> None:
        """After building for PostgreSQL, no placeholders should remain."""
        db = _make_db_backend("postgresql")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        placeholders = ["{SERIAL}", "{BOOLEAN_TRUE}", "{BOOLEAN_FALSE}", "{BYTEA}", "{TEXT}"]
        for migration in mgr.migrations:
            for placeholder in placeholders:
                assert placeholder not in migration["sql"], (
                    f"Placeholder {placeholder} found in migration {migration['version']}"
                )

    @patch("pbx.utils.migrations.get_logger")
    def test_sqlite_uses_autoincrement(self, mock_get_logger: MagicMock) -> None:
        """SQLite migrations must use AUTOINCREMENT for primary keys."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        for migration in mgr.migrations:
            if "CREATE TABLE" in migration["sql"]:
                assert "AUTOINCREMENT" in migration["sql"]

    @patch("pbx.utils.migrations.get_logger")
    def test_postgresql_uses_serial(self, mock_get_logger: MagicMock) -> None:
        """PostgreSQL migrations must use SERIAL PRIMARY KEY."""
        db = _make_db_backend("postgresql")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        for migration in mgr.migrations:
            if "CREATE TABLE" in migration["sql"]:
                assert "SERIAL PRIMARY KEY" in migration["sql"]


@pytest.mark.unit
class TestRegisterAllMigrationsTableNames:
    """Tests verifying that specific tables are created by each migration."""

    @patch("pbx.utils.migrations.get_logger")
    def _get_migration_sql(self, version: int, mock_get_logger: MagicMock) -> str:
        """Helper: register all and return SQL for a specific version."""
        db = _make_db_backend("sqlite")
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        for m in mgr.migrations:
            if m["version"] == version:
                return m["sql"]
        raise ValueError(f"Migration {version} not found")

    def test_1000_ai_features_tables(self) -> None:
        """Migration 1000 must create AI feature tables."""
        sql = self._get_migration_sql(1000)
        assert "speech_analytics_configs" in sql
        assert "ai_assistant_configs" in sql
        assert "voice_biometrics" in sql
        assert "call_quality_predictions" in sql

    def test_1001_video_conferencing_tables(self) -> None:
        """Migration 1001 must create video conferencing tables."""
        sql = self._get_migration_sql(1001)
        assert "video_conference_rooms" in sql
        assert "video_conference_participants" in sql
        assert "video_codec_configs" in sql

    def test_1002_emergency_services_tables(self) -> None:
        """Migration 1002 must create emergency services tables."""
        sql = self._get_migration_sql(1002)
        assert "nomadic_e911_locations" in sql
        assert "e911_location_updates" in sql
        assert "multi_site_e911_configs" in sql

    def test_1003_analytics_reporting_tables(self) -> None:
        """Migration 1003 must create analytics tables."""
        sql = self._get_migration_sql(1003)
        assert "bi_integration_configs" in sql
        assert "call_tags" in sql
        assert "call_tag_assignments" in sql

    def test_1004_integration_tables(self) -> None:
        """Migration 1004 must create integration tables."""
        sql = self._get_migration_sql(1004)
        assert "hubspot_integration" in sql
        assert "zendesk_integration" in sql
        assert "integration_activity_log" in sql

    def test_1005_mobile_tables(self) -> None:
        """Migration 1005 must create mobile tables."""
        sql = self._get_migration_sql(1005)
        assert "mobile_app_installations" in sql
        assert "mobile_number_portability" in sql

    def test_1006_advanced_call_features_tables(self) -> None:
        """Migration 1006 must create advanced call feature tables."""
        sql = self._get_migration_sql(1006)
        assert "call_blending_configs" in sql
        assert "voicemail_drop_templates" in sql
        assert "call_recording_analytics" in sql

    def test_1007_sip_trunking_tables(self) -> None:
        """Migration 1007 must create SIP trunking tables."""
        sql = self._get_migration_sql(1007)
        assert "trunk_geographic_regions" in sql
        assert "dns_srv_configs" in sql
        assert "sbc_configs" in sql

    def test_1008_collaboration_tables(self) -> None:
        """Migration 1008 must create collaboration tables."""
        sql = self._get_migration_sql(1008)
        assert "team_messaging_channels" in sql
        assert "team_messaging_members" in sql
        assert "team_messages" in sql
        assert "shared_files" in sql

    def test_1009_compliance_tables(self) -> None:
        """Migration 1009 must create compliance tables."""
        sql = self._get_migration_sql(1009)
        assert "soc2_controls" in sql
        assert "data_residency_configs" in sql

    def test_1010_click_to_dial_tables(self) -> None:
        """Migration 1010 must create click-to-dial tables."""
        sql = self._get_migration_sql(1010)
        assert "click_to_dial_configs" in sql
        assert "click_to_dial_history" in sql


@pytest.mark.unit
class TestRegisterAllMigrationsCanApply:
    """Integration-style tests: register_all_migrations + apply_migrations together."""

    @patch("pbx.utils.migrations.get_logger")
    def test_apply_all_from_scratch(self, mock_get_logger: MagicMock) -> None:
        """Applying all migrations from version 0 must succeed."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        result = mgr.apply_migrations()
        assert result is True
        assert db.execute_script.call_count == 11

    @patch("pbx.utils.migrations.get_logger")
    def test_apply_partial_from_midpoint(self, mock_get_logger: MagicMock) -> None:
        """Applying migrations from version 1005 should apply 1006-1010 (5 migrations)."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 1005}
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        result = mgr.apply_migrations()
        assert result is True
        assert db.execute_script.call_count == 5

    @patch("pbx.utils.migrations.get_logger")
    def test_apply_with_target_version(self, mock_get_logger: MagicMock) -> None:
        """Applying with target_version=1003 from version 0 should apply 4 migrations."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 0}
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        result = mgr.apply_migrations(target_version=1003)
        assert result is True
        assert db.execute_script.call_count == 4

    @patch("pbx.utils.migrations.get_logger")
    def test_already_up_to_date(self, mock_get_logger: MagicMock) -> None:
        """Applying when already at latest version should be a no-op."""
        db = _make_db_backend("sqlite")
        db.fetch_one.return_value = {"max_version": 1010}
        mgr = MigrationManager(db)
        register_all_migrations(mgr)
        result = mgr.apply_migrations()
        assert result is True
        assert db.execute_script.call_count == 0
