"""
Database backend for PBX features
Provides optional PostgreSQL/SQLite storage for VIP callers, CDR, and other data
"""
from pbx.utils.logger import get_logger
from typing import Optional, Dict, List, Any
from datetime import datetime
import json

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False


class DatabaseBackend:
    """
    Database backend supporting PostgreSQL and SQLite
    Provides unified interface for database operations
    """

    def __init__(self, config: dict):
        """
        Initialize database backend

        Args:
            config: Database configuration
        """
        self.logger = get_logger()
        self.config = config
        self.db_type = config.get('database.type', 'sqlite')
        self.connection = None
        self.enabled = False

        if self.db_type == 'postgresql' and not POSTGRES_AVAILABLE:
            self.logger.error("PostgreSQL requested but psycopg2 not installed. Install with: pip install psycopg2-binary")
            self.db_type = 'sqlite'

        if self.db_type == 'sqlite' and not SQLITE_AVAILABLE:
            self.logger.error("SQLite not available")
            return

        self.logger.info(f"Database backend: {self.db_type}")

    def connect(self) -> bool:
        """
        Connect to database

        Returns:
            bool: True if connected successfully
        """
        try:
            if self.db_type == 'postgresql':
                return self._connect_postgresql()
            elif self.db_type == 'sqlite':
                return self._connect_sqlite()
            return False
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            return False

    def _connect_postgresql(self) -> bool:
        """Connect to PostgreSQL database"""
        if not POSTGRES_AVAILABLE:
            return False

        try:
            self.connection = psycopg2.connect(
                host=self.config.get('database.host', 'localhost'),
                port=self.config.get('database.port', 5432),
                database=self.config.get('database.name', 'pbx'),
                user=self.config.get('database.user', 'pbx'),
                password=self.config.get('database.password', '')
            )
            self.enabled = True
            self.logger.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            return False

    def _connect_sqlite(self) -> bool:
        """Connect to SQLite database"""
        if not SQLITE_AVAILABLE:
            return False

        try:
            db_path = self.config.get('database.path', 'pbx.db')
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.enabled = True
            self.logger.info(f"Connected to SQLite database: {db_path}")
            return True
        except Exception as e:
            self.logger.error(f"SQLite connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.enabled = False
            self.logger.info("Database disconnected")

    def execute(self, query: str, params: tuple = None) -> bool:
        """
        Execute a query (INSERT, UPDATE, DELETE)

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            bool: True if successful
        """
        if not self.enabled or not self.connection:
            return False

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.logger.error(f"Query execution error: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """
        Fetch single row

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            dict: Row data or None
        """
        if not self.enabled or not self.connection:
            return None

        try:
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = self.connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            row = cursor.fetchone()
            cursor.close()

            if row:
                return dict(row) if self.db_type == 'postgresql' else {k: row[k] for k in row.keys()}
            return None
        except Exception as e:
            self.logger.error(f"Fetch one error: {e}")
            return None

    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Fetch all rows

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            list: List of row dictionaries
        """
        if not self.enabled or not self.connection:
            return []

        try:
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = self.connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            rows = cursor.fetchall()
            cursor.close()

            if self.db_type == 'postgresql':
                return [dict(row) for row in rows]
            else:
                return [{k: row[k] for k in row.keys()} for row in rows]
        except Exception as e:
            self.logger.error(f"Fetch all error: {e}")
            return []

    def create_tables(self):
        """Create database tables if they don't exist"""
        if not self.enabled:
            return False

        self.logger.info("Creating database tables...")

        # VIP Callers table
        vip_table = """
        CREATE TABLE IF NOT EXISTS vip_callers (
            id SERIAL PRIMARY KEY,
            caller_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255),
            priority_level INTEGER DEFAULT 1,
            notes TEXT,
            special_routing VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS vip_callers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255),
            priority_level INTEGER DEFAULT 1,
            notes TEXT,
            special_routing VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Call Detail Records table
        cdr_table = """
        CREATE TABLE IF NOT EXISTS call_records (
            id SERIAL PRIMARY KEY,
            call_id VARCHAR(100) UNIQUE NOT NULL,
            from_extension VARCHAR(20),
            to_extension VARCHAR(20),
            caller_id VARCHAR(50),
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration INTEGER,
            status VARCHAR(20),
            recording_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS call_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id VARCHAR(100) UNIQUE NOT NULL,
            from_extension VARCHAR(20),
            to_extension VARCHAR(20),
            caller_id VARCHAR(50),
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration INTEGER,
            status VARCHAR(20),
            recording_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Voicemail messages table
        voicemail_table = """
        CREATE TABLE IF NOT EXISTS voicemail_messages (
            id SERIAL PRIMARY KEY,
            message_id VARCHAR(100) UNIQUE NOT NULL,
            extension_number VARCHAR(20) NOT NULL,
            caller_id VARCHAR(50),
            file_path VARCHAR(255),
            duration INTEGER,
            listened BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS voicemail_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id VARCHAR(100) UNIQUE NOT NULL,
            extension_number VARCHAR(20) NOT NULL,
            caller_id VARCHAR(50),
            file_path VARCHAR(255),
            duration INTEGER,
            listened BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Execute table creation
        success = True
        for table_sql in [vip_table, cdr_table, voicemail_table]:
            if not self.execute(table_sql):
                success = False

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_vip_caller_id ON vip_callers(caller_id)",
            "CREATE INDEX IF NOT EXISTS idx_vip_priority ON vip_callers(priority_level)",
            "CREATE INDEX IF NOT EXISTS idx_cdr_call_id ON call_records(call_id)",
            "CREATE INDEX IF NOT EXISTS idx_cdr_from ON call_records(from_extension)",
            "CREATE INDEX IF NOT EXISTS idx_cdr_start_time ON call_records(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_vm_extension ON voicemail_messages(extension_number)",
            "CREATE INDEX IF NOT EXISTS idx_vm_listened ON voicemail_messages(listened)"
        ]

        for index_sql in indexes:
            self.execute(index_sql)

        if success:
            self.logger.info("Database tables created successfully")
        else:
            self.logger.error("Failed to create some database tables")

        return success


class VIPCallerDB:
    """VIP Caller database operations"""

    def __init__(self, db: DatabaseBackend):
        """
        Initialize VIP caller database

        Args:
            db: Database backend instance
        """
        self.db = db
        self.logger = get_logger()

    def add_vip(self, caller_id: str, priority_level: int = 1, name: str = None, notes: str = None) -> bool:
        """Add or update VIP caller"""
        query = """
        INSERT INTO vip_callers (caller_id, priority_level, name, notes, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (caller_id) DO UPDATE
        SET priority_level = EXCLUDED.priority_level,
            name = EXCLUDED.name,
            notes = EXCLUDED.notes,
            updated_at = EXCLUDED.updated_at
        """ if self.db.db_type == 'postgresql' else """
        INSERT OR REPLACE INTO vip_callers (caller_id, priority_level, name, notes, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """

        params = (caller_id, priority_level, name, notes, datetime.now())
        return self.db.execute(query, params)

    def remove_vip(self, caller_id: str) -> bool:
        """Remove VIP caller"""
        query = "DELETE FROM vip_callers WHERE caller_id = %s" if self.db.db_type == 'postgresql' else \
                "DELETE FROM vip_callers WHERE caller_id = ?"
        return self.db.execute(query, (caller_id,))

    def get_vip(self, caller_id: str) -> Optional[Dict]:
        """Get VIP caller information"""
        query = "SELECT * FROM vip_callers WHERE caller_id = %s" if self.db.db_type == 'postgresql' else \
                "SELECT * FROM vip_callers WHERE caller_id = ?"
        return self.db.fetch_one(query, (caller_id,))

    def list_vips(self, priority_level: int = None) -> List[Dict]:
        """List all VIP callers"""
        if priority_level:
            query = "SELECT * FROM vip_callers WHERE priority_level = %s ORDER BY name" if self.db.db_type == 'postgresql' else \
                    "SELECT * FROM vip_callers WHERE priority_level = ? ORDER BY name"
            return self.db.fetch_all(query, (priority_level,))
        else:
            query = "SELECT * FROM vip_callers ORDER BY priority_level, name"
            return self.db.fetch_all(query)

    def is_vip(self, caller_id: str) -> bool:
        """Check if caller is VIP"""
        return self.get_vip(caller_id) is not None
