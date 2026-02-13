"""
Tests for graceful degradation when PostgreSQL is unavailable.

These tests verify the PBX system degrades gracefully when the
PostgreSQL backend is not available, falling back to SQLite.
"""

import os
import sys
from unittest import TestCase, mock
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.utils.database import DatabaseBackend, POSTGRES_AVAILABLE


class TestPostgreSQLGracefulDegradation(TestCase):
    """Test graceful fallback to SQLite when PostgreSQL unavailable."""

    def test_fallback_to_sqlite_when_postgres_unavailable(self):
        """Should fall back to SQLite when PostgreSQL driver missing."""
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
            result = db.connect()
            self.assertIsInstance(result, bool)
        else:
            self.assertEqual(db.db_type, "sqlite")

    def test_sqlite_fallback_functional(self):
        """SQLite fallback should be fully functional."""
        config = {"database.type": "sqlite", "database.path": ":memory:"}
        db = DatabaseBackend(config)
        result = db.connect()
        self.assertTrue(result)
        self.assertTrue(db.enabled)

        db.create_tables()
        db.execute(
            "INSERT INTO system_config (config_key, config_value, config_type) VALUES (?, ?, ?)",
            ("test_key", "test_value", "string"),
        )
        result = db.fetch_one(
            "SELECT config_value FROM system_config WHERE config_key = ?",
            ("test_key",),
        )
        self.assertIsNotNone(result)
        db.disconnect()

    def test_operations_without_database(self):
        """Core PBX operations should work even without database."""
        config = {"database.type": "invalid"}
        db = DatabaseBackend(config)
        self.assertIsNone(db.fetch_one("SELECT 1"))
        self.assertEqual(db.fetch_all("SELECT 1"), [])
        self.assertFalse(db.execute("INSERT INTO nonexistent VALUES (1)"))

    def test_postgresql_import_error_graceful(self):
        """ImportError for psycopg2 should not crash the system."""
        from pbx.utils.database import POSTGRES_AVAILABLE
        self.assertIsInstance(POSTGRES_AVAILABLE, bool)

    def test_database_reconnection_after_degradation(self):
        """Database should handle reconnection after degradation."""
        config = {"database.type": "sqlite", "database.path": ":memory:"}
        db = DatabaseBackend(config)
        db.connect()
        self.assertTrue(db.enabled)

        db.disconnect()
        self.assertFalse(db.enabled)

        db.connect()
        self.assertTrue(db.enabled)
        db.disconnect()

    def test_execute_with_context_non_critical_errors(self):
        """Non-critical execution errors should be handled gracefully."""
        config = {"database.type": "sqlite", "database.path": ":memory:"}
        db = DatabaseBackend(config)
        db.connect()
        db.create_tables()

        result = db._execute_with_context(
            "CREATE INDEX IF NOT EXISTS idx_test ON system_config(config_key)",
            "index creation",
            critical=False,
        )
        self.assertTrue(result)

        result = db._execute_with_context(
            "CREATE INDEX IF NOT EXISTS idx_test ON system_config(config_key)",
            "index creation",
            critical=False,
        )
        self.assertTrue(result)
        db.disconnect()
