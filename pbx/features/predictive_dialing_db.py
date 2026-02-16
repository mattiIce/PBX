"""
Database layer for Predictive Dialing
Provides persistence for campaigns, contacts, and call results
"""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger


class PredictiveDialingDatabase:
    """
    Database layer for predictive dialing
    Stores campaigns, contacts, call attempts, and statistics
    """

    def __init__(self, db_backend: Any | None) -> None:
        """
        Initialize database layer

        Args:
            db_backend: DatabaseBackend instance
        """
        self.logger = get_logger()
        self.db = db_backend

    def create_tables(self) -> bool:
        """Create tables for predictive dialing"""
        try:
            if self.db.db_type == "postgresql":
                sql_campaigns = """
                CREATE TABLE IF NOT EXISTS dialing_campaigns (
                    id SERIAL PRIMARY KEY,
                    campaign_id VARCHAR(100) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    dialing_mode VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    max_attempts INTEGER DEFAULT 3,
                    retry_interval INTEGER DEFAULT 3600,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    total_contacts INTEGER DEFAULT 0,
                    contacts_completed INTEGER DEFAULT 0,
                    successful_calls INTEGER DEFAULT 0,
                    failed_calls INTEGER DEFAULT 0
                )
                """

                sql_contacts = """
                CREATE TABLE IF NOT EXISTS dialing_contacts (
                    id SERIAL PRIMARY KEY,
                    campaign_id VARCHAR(100) REFERENCES dialing_campaigns(campaign_id) ON DELETE CASCADE,
                    contact_id VARCHAR(100) NOT NULL,
                    phone_number VARCHAR(50) NOT NULL,
                    data JSONB,
                    status VARCHAR(20) DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    call_result VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(campaign_id, contact_id)
                )
                """

                sql_attempts = """
                CREATE TABLE IF NOT EXISTS dialing_attempts (
                    id SERIAL PRIMARY KEY,
                    campaign_id VARCHAR(100),
                    contact_id VARCHAR(100),
                    call_id VARCHAR(255),
                    attempt_number INTEGER,
                    timestamp TIMESTAMP NOT NULL,
                    result VARCHAR(50),
                    duration INTEGER,
                    agent_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_stats = """
                CREATE TABLE IF NOT EXISTS dialing_statistics (
                    id SERIAL PRIMARY KEY,
                    campaign_id VARCHAR(100) REFERENCES dialing_campaigns(campaign_id) ON DELETE CASCADE,
                    date DATE NOT NULL,
                    calls_made INTEGER DEFAULT 0,
                    connects INTEGER DEFAULT 0,
                    abandons INTEGER DEFAULT 0,
                    avg_connect_time FLOAT,
                    abandon_rate FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(campaign_id, date)
                )
                """
            else:  # SQLite
                sql_campaigns = """
                CREATE TABLE IF NOT EXISTS dialing_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    dialing_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    max_attempts INTEGER DEFAULT 3,
                    retry_interval INTEGER DEFAULT 3600,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT,
                    ended_at TEXT,
                    total_contacts INTEGER DEFAULT 0,
                    contacts_completed INTEGER DEFAULT 0,
                    successful_calls INTEGER DEFAULT 0,
                    failed_calls INTEGER DEFAULT 0
                )
                """

                sql_contacts = """
                CREATE TABLE IF NOT EXISTS dialing_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT,
                    contact_id TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    data TEXT,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_attempt TEXT,
                    call_result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(campaign_id, contact_id),
                    FOREIGN KEY (campaign_id) REFERENCES dialing_campaigns(campaign_id) ON DELETE CASCADE
                )
                """

                sql_attempts = """
                CREATE TABLE IF NOT EXISTS dialing_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT,
                    contact_id TEXT,
                    call_id TEXT,
                    attempt_number INTEGER,
                    timestamp TEXT NOT NULL,
                    result TEXT,
                    duration INTEGER,
                    agent_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_stats = """
                CREATE TABLE IF NOT EXISTS dialing_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT,
                    date TEXT NOT NULL,
                    calls_made INTEGER DEFAULT 0,
                    connects INTEGER DEFAULT 0,
                    abandons INTEGER DEFAULT 0,
                    avg_connect_time REAL,
                    abandon_rate REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(campaign_id, date),
                    FOREIGN KEY (campaign_id) REFERENCES dialing_campaigns(campaign_id) ON DELETE CASCADE
                )
                """

            cursor = self.db.connection.cursor()
            cursor.execute(sql_campaigns)
            cursor.execute(sql_contacts)
            cursor.execute(sql_attempts)
            cursor.execute(sql_stats)
            self.db.connection.commit()

            self.logger.info("Predictive dialing tables created successfully")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Error creating predictive dialing tables: {e}")
            return False

    def save_campaign(self, campaign_data: dict) -> bool:
        """Save a campaign to database"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO dialing_campaigns
                (campaign_id, name, dialing_mode, status, max_attempts, retry_interval)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (campaign_id) DO UPDATE
                SET name = EXCLUDED.name,
                    dialing_mode = EXCLUDED.dialing_mode,
                    status = EXCLUDED.status,
                    max_attempts = EXCLUDED.max_attempts,
                    retry_interval = EXCLUDED.retry_interval
                """
            else:
                sql = """
                INSERT OR REPLACE INTO dialing_campaigns
                (campaign_id, name, dialing_mode, status, max_attempts, retry_interval)
                VALUES (?, ?, ?, ?, ?, ?)
                """

            params = (
                campaign_data["campaign_id"],
                campaign_data["name"],
                campaign_data["dialing_mode"],
                campaign_data["status"],
                campaign_data.get("max_attempts", 3),
                campaign_data.get("retry_interval", 3600),
            )

            cursor.execute(sql, params)
            self.db.connection.commit()
            return True

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error saving campaign: {e}")
            return False

    def save_contact(self, campaign_id: str, contact_data: dict) -> bool:
        """Save a contact to a campaign"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO dialing_contacts
                (campaign_id, contact_id, phone_number, data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (campaign_id, contact_id) DO UPDATE
                SET phone_number = EXCLUDED.phone_number,
                    data = EXCLUDED.data
                """
                params = (
                    campaign_id,
                    contact_data["contact_id"],
                    contact_data["phone_number"],
                    json.dumps(contact_data.get("data", {})),
                )
            else:
                sql = """
                INSERT OR REPLACE INTO dialing_contacts
                (campaign_id, contact_id, phone_number, data)
                VALUES (?, ?, ?, ?)
                """
                params = (
                    campaign_id,
                    contact_data["contact_id"],
                    contact_data["phone_number"],
                    json.dumps(contact_data.get("data", {})),
                )

            cursor.execute(sql, params)
            self.db.connection.commit()
            return True

        except (KeyError, TypeError, ValueError, json.JSONDecodeError, sqlite3.Error) as e:
            self.logger.error(f"Error saving contact: {e}")
            return False

    def save_attempt(self, campaign_id: str, contact_id: str, attempt_data: dict) -> None:
        """Save a call attempt"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO dialing_attempts
                (campaign_id, contact_id, call_id, attempt_number, timestamp, result, duration, agent_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
            else:
                sql = """
                INSERT INTO dialing_attempts
                (campaign_id, contact_id, call_id, attempt_number, timestamp, result, duration, agent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

            params = (
                campaign_id,
                contact_id,
                attempt_data.get("call_id"),
                attempt_data.get("attempt_number"),
                attempt_data.get("timestamp", datetime.now(UTC).isoformat()),
                attempt_data.get("result"),
                attempt_data.get("duration"),
                attempt_data.get("agent_id"),
            )

            cursor.execute(sql, params)

            # Update contact
            if self.db.db_type == "postgresql":
                update_sql = """
                UPDATE dialing_contacts
                SET attempts = attempts + 1,
                    last_attempt = %s,
                    status = %s,
                    call_result = %s
                WHERE campaign_id = %s AND contact_id = %s
                """
            else:
                update_sql = """
                UPDATE dialing_contacts
                SET attempts = attempts + 1,
                    last_attempt = ?,
                    status = ?,
                    call_result = ?
                WHERE campaign_id = ? AND contact_id = ?
                """

            update_params = (
                attempt_data.get("timestamp", datetime.now(UTC).isoformat()),
                attempt_data.get("status", "attempted"),
                attempt_data.get("result"),
                campaign_id,
                contact_id,
            )

            cursor.execute(update_sql, update_params)
            self.db.connection.commit()

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error saving attempt: {e}")

    def update_campaign_stats(self, campaign_id: str, stats: dict) -> None:
        """Update campaign statistics"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                UPDATE dialing_campaigns
                SET total_contacts = %s,
                    contacts_completed = %s,
                    successful_calls = %s,
                    failed_calls = %s
                WHERE campaign_id = %s
                """
            else:
                sql = """
                UPDATE dialing_campaigns
                SET total_contacts = ?,
                    contacts_completed = ?,
                    successful_calls = ?,
                    failed_calls = ?
                WHERE campaign_id = ?
                """

            params = (
                stats.get("total_contacts", 0),
                stats.get("contacts_completed", 0),
                stats.get("successful_calls", 0),
                stats.get("failed_calls", 0),
                campaign_id,
            )

            cursor.execute(sql, params)
            self.db.connection.commit()

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error updating campaign stats: {e}")

    def get_campaign(self, campaign_id: str) -> dict | None:
        """Get campaign by ID"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = "SELECT * FROM dialing_campaigns WHERE campaign_id = %s"
            else:
                sql = "SELECT * FROM dialing_campaigns WHERE campaign_id = ?"

            cursor.execute(sql, (campaign_id,))
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row, strict=False))
            return None

        except sqlite3.Error as e:
            self.logger.error(f"Error getting campaign: {e}")
            return None

    def get_all_campaigns(self) -> list[dict]:
        """Get all campaigns"""
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT * FROM dialing_campaigns ORDER BY created_at DESC")

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row, strict=False)) for row in rows]

        except sqlite3.Error as e:
            self.logger.error(f"Error getting campaigns: {e}")
            return []

    def get_campaign_contacts(self, campaign_id: str) -> list[dict]:
        """Get all contacts for a campaign"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = "SELECT * FROM dialing_contacts WHERE campaign_id = %s ORDER BY created_at"
            else:
                sql = "SELECT * FROM dialing_contacts WHERE campaign_id = ? ORDER BY created_at"

            cursor.execute(sql, (campaign_id,))

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row, strict=False)) for row in rows]

        except sqlite3.Error as e:
            self.logger.error(f"Error getting campaign contacts: {e}")
            return []

    def get_statistics(self, campaign_id: str | None = None) -> dict:
        """Get dialing statistics"""
        try:
            cursor = self.db.connection.cursor()

            if campaign_id:
                # Campaign-specific stats
                if self.db.db_type == "postgresql":
                    sql = "SELECT * FROM dialing_campaigns WHERE campaign_id = %s"
                else:
                    sql = "SELECT * FROM dialing_campaigns WHERE campaign_id = ?"

                cursor.execute(sql, (campaign_id,))
                row = cursor.fetchone()

                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row, strict=False))
                return {}
            # Global stats
            sql = """
                SELECT
                    COUNT(*) as total_campaigns,
                    SUM(total_contacts) as total_contacts,
                    SUM(successful_calls) as successful_calls,
                    SUM(failed_calls) as failed_calls
                FROM dialing_campaigns
                """
            cursor.execute(sql)
            row = cursor.fetchone()

            if row:
                return {
                    "total_campaigns": row[0] or 0,
                    "total_contacts": row[1] or 0,
                    "successful_calls": row[2] or 0,
                    "failed_calls": row[3] or 0,
                }
            return {}

        except sqlite3.Error as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}
