"""
Tests for PostgreSQL-only database behavior.

These tests verify the PBX system FAILS (not degrades) when the
PostgreSQL backend is not available, since PostgreSQL is the only
supported database.
"""

import sys
from pathlib import Path
from unittest import TestCase, mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pbx.utils.database import POSTGRES_AVAILABLE, DatabaseBackend


class TestPostgreSQLRequired(TestCase):
    """Test that PostgreSQL is the only supported database backend."""

    def test_system_fails_when_postgres_unavailable(self) -> None:
        """Should fail when PostgreSQL driver is missing."""
        config = {
            "database.type": "postgresql",
            "database.host": "localhost",
            "database.port": 5432,
            "database.db": "pbx",
            "database.user": "pbx",
            "database.password": "test",
        }
        db = DatabaseBackend(config)
        if not POSTGRES_AVAILABLE:
            # Without psycopg2, the backend should NOT be enabled
            self.assertFalse(db.enabled)
            self.assertEqual(db.db_type, "postgresql")

    def test_no_sqlite_fallback(self) -> None:
        """System should not fall back to SQLite; it must require PostgreSQL."""
        config = {"database.type": "postgresql", "database.host": "localhost"}
        db = DatabaseBackend(config)
        # db_type must always be postgresql, never sqlite
        self.assertEqual(db.db_type, "postgresql")

    def test_operations_without_database(self) -> None:
        """Operations should return safe defaults when database is unavailable."""
        config = {"database.type": "postgresql"}
        db = DatabaseBackend(config)
        self.assertIsNone(db.fetch_one("SELECT 1"))
        self.assertEqual(db.fetch_all("SELECT 1"), [])
        self.assertFalse(db.execute("INSERT INTO nonexistent VALUES (1)"))

    def test_postgresql_import_error_graceful(self) -> None:
        """ImportError for psycopg2 should not crash the system."""
        from pbx.utils.database import POSTGRES_AVAILABLE

        self.assertIsInstance(POSTGRES_AVAILABLE, bool)

    def test_database_reconnection(self) -> None:
        """Database should handle connect/disconnect cycles."""
        config = {
            "database.type": "postgresql",
            "database.host": "localhost",
            "database.port": 5432,
            "database.db": "pbx",
            "database.user": "pbx",
            "database.password": "test",
        }
        db = DatabaseBackend(config)
        if POSTGRES_AVAILABLE:
            # Even if connect fails due to no server, disconnect should be safe
            db.disconnect()
            self.assertFalse(db.enabled)

    def test_postgresql_connection_failure_does_not_fallback(self) -> None:
        """Failed PostgreSQL connection should not trigger any SQLite fallback."""
        config = {
            "database.type": "postgresql",
            "database.host": "nonexistent-host",
            "database.port": 5432,
            "database.db": "pbx",
            "database.user": "pbx",
            "database.password": "test",
        }
        db = DatabaseBackend(config)
        # db_type remains postgresql even on connection failure
        self.assertEqual(db.db_type, "postgresql")
        self.assertFalse(db.enabled)
