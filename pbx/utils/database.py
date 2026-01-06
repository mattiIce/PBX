"""
Database backend for PBX features
Provides optional PostgreSQL/SQLite storage for VIP callers, CDR, and other data
"""

import json
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from pbx.utils.device_types import detect_device_type
from pbx.utils.logger import get_logger

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
        self.db_type = config.get("database.type", "sqlite")
        self.connection = None
        self.enabled = False

        if self.db_type == "postgresql" and not POSTGRES_AVAILABLE:
            self.logger.error(
                "PostgreSQL requested but psycopg2 not installed. Install with: pip install psycopg2-binary"
            )
            self.db_type = "sqlite"

        if self.db_type == "sqlite" and not SQLITE_AVAILABLE:
            self.logger.error("SQLite not available")
            return

        self.logger.info(f"Database backend: {self.db_type}")

    def connect(self) -> bool:
        """
        Connect to database

        Returns:
            bool: True if connected successfully
        """
        self.logger.info(
            f"Initiating database connection (type: {
                self.db_type})..."
        )
        try:
            if self.db_type == "postgresql":
                return self._connect_postgresql()
            elif self.db_type == "sqlite":
                return self._connect_sqlite()
            else:
                self.logger.error(f"Unsupported database type: {self.db_type}")
                return False
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            return False

    def _connect_postgresql(self) -> bool:
        """Connect to PostgreSQL database"""
        if not POSTGRES_AVAILABLE:
            self.logger.error("PostgreSQL driver (psycopg2) not available")
            return False

        host = self.config.get("database.host", "localhost")
        port = self.config.get("database.port", 5432)
        database = self.config.get("database.name", "pbx")
        user = self.config.get("database.user", "pbx")

        self.logger.info("Connecting to PostgreSQL database...")
        self.logger.info(f"  Host: {host}")
        self.logger.info(f"  Port: {port}")
        self.logger.info(f"  Database: {database}")
        self.logger.info(f"  User: {user}")

        try:
            self.connection = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=self.config.get("database.password", ""),
            )
            # Enable autocommit mode to prevent transaction state issues
            # This ensures each query is automatically committed and errors don't
            # leave the connection in a failed transaction state
            self.connection.autocommit = True
            self.enabled = True
            self.logger.info("✓ Successfully connected to PostgreSQL database")
            self.logger.info(f"  Connection established: {host}:{port}/{database}")
            return True
        except Exception as e:
            self.logger.error(f"✗ PostgreSQL connection failed: {e}")
            self.logger.warning("Voicemail and other data will be stored ONLY in file system")
            self.logger.warning(
                "To fix: Ensure PostgreSQL is running and accessible, or run 'python scripts/verify_database.py' for diagnostics"
            )
            return False

    def _connect_sqlite(self) -> bool:
        """Connect to SQLite database"""
        if not SQLITE_AVAILABLE:
            self.logger.error("SQLite not available in this Python installation")
            return False

        db_path = self.config.get("database.path", "pbx.db")
        self.logger.info("Connecting to SQLite database...")
        self.logger.info(f"  Database file: {db_path}")

        try:
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            # SQLite doesn't have autocommit attribute by default, so we set it explicitly
            # This ensures consistent behavior when checking autocommit in
            # other methods
            self.connection.autocommit = False
            self.enabled = True
            self.logger.info("✓ Successfully connected to SQLite database")
            self.logger.info(f"  Database path: {os.path.abspath(db_path)}")
            return True
        except Exception as e:
            self.logger.error(f"✗ SQLite connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.enabled = False
            self.logger.info("Database disconnected")

    def _execute_with_context(
        self, query: str, context: str = "query", params: tuple = None, critical: bool = True
    ) -> bool:
        """
        Execute a query with better error context

        Args:
            query: SQL query
            context: Description of the operation (e.g., "table creation", "index creation")
            params: Query parameters
            critical: If False, log permission errors as warnings instead of errors

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
            # Only commit if not in autocommit mode
            if not self.connection.autocommit:
                self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            error_msg = str(e).lower()
            # Check if this is a permission error on existing objects
            # Common patterns across PostgreSQL, MySQL, SQLite
            permission_errors = [
                "must be owner",  # PostgreSQL
                "permission denied",  # PostgreSQL/SQLite
                "access denied",  # MySQL
                "insufficient privileges",  # Oracle
            ]
            already_exists_errors = [
                "already exists",
                "duplicate",
                "unique constraint",
            ]

            if not critical and any(pattern in error_msg for pattern in permission_errors):
                # This is expected when tables/indexes exist but user lacks ownership
                # Log as debug instead of error to avoid alarming users
                self.logger.debug(f"Skipping {context}: {e}")
                if self.connection and not self.connection.autocommit:
                    self.connection.rollback()
                return True  # Return True since this is not a critical failure
            elif any(pattern in error_msg for pattern in already_exists_errors):
                # Object already exists - this is fine
                self.logger.debug(f"{context.capitalize()} already exists: {e}")
                if self.connection and not self.connection.autocommit:
                    self.connection.rollback()
                return True
            else:
                # This is an actual error - log verbosely
                self.logger.error(f"Error during {context}: {e}")
                self.logger.error(f"  Query: {query}")
                self.logger.error(f"  Parameters: {params}")
                self.logger.error(f"  Database type: {self.db_type}")
                self.logger.error(f"  Traceback: {traceback.format_exc()}")
                if self.connection and not self.connection.autocommit:
                    self.connection.rollback()
                return False

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
            self.logger.error("Execute called but database is not enabled or connected")
            self.logger.error(
                f"  Enabled: {
                    self.enabled}, Connection: {
                    self.connection is not None}"
            )
            return False
        return self._execute_with_context(query, "query execution", params, critical=True)

    def execute_script(self, script: str) -> bool:
        """
        Execute a multi-statement SQL script
        Uses executescript for SQLite, splits statements for PostgreSQL

        Args:
            script: SQL script with multiple statements

        Returns:
            bool: True if successful
        """
        if not self.enabled or not self.connection:
            self.logger.error("Execute script called but database is not enabled or connected")
            self.logger.error(
                f"  Enabled: {self.enabled}, Connection: {self.connection is not None}"
            )
            return False

        try:
            if self.db_type == "sqlite":
                # SQLite has executescript for multi-statement execution
                cursor = self.connection.cursor()
                cursor.executescript(script)
                cursor.close()
                if not self.connection.autocommit:
                    self.connection.commit()
            else:
                # PostgreSQL - split and execute individual statements
                # Remove comments and split by semicolon
                statements = []
                current = []
                for line in script.split("\n"):
                    stripped = line.strip()
                    # Skip comments
                    if stripped.startswith("--") or not stripped:
                        continue
                    current.append(line)
                    if ";" in line:
                        statements.append("\n".join(current))
                        current = []

                # Execute each statement
                cursor = self.connection.cursor()
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt:
                        cursor.execute(stmt)
                cursor.close()
                if not self.connection.autocommit:
                    self.connection.commit()

            return True
        except Exception as e:
            self.logger.error(f"Error during script execution: {e}")
            self.logger.error(f"  Script length: {len(script)} characters")
            self.logger.error(f"  Database type: {self.db_type}")
            self.logger.error(f"  Traceback: {traceback.format_exc()}")
            if self.connection and not self.connection.autocommit:
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
            if self.db_type == "postgresql":
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
                return (
                    dict(row) if self.db_type == "postgresql" else {k: row[k] for k in row.keys()}
                )
            return None
        except Exception as e:
            self.logger.error(f"Fetch one error: {e}")
            self.logger.error(f"  Query: {query}")
            self.logger.error(f"  Parameters: {params}")
            self.logger.error(f"  Database type: {self.db_type}")
            self.logger.error(f"  Traceback: {traceback.format_exc()}")
            if self.connection and not self.connection.autocommit:
                self.connection.rollback()
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
            if self.db_type == "postgresql":
                cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = self.connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            rows = cursor.fetchall()
            cursor.close()

            if self.db_type == "postgresql":
                return [dict(row) for row in rows]
            else:
                return [{k: row[k] for k in row.keys()} for row in rows]
        except Exception as e:
            self.logger.error(f"Fetch all error: {e}")
            self.logger.error(f"  Query: {query}")
            self.logger.error(f"  Parameters: {params}")
            self.logger.error(f"  Database type: {self.db_type}")
            self.logger.error(f"  Traceback: {traceback.format_exc()}")
            if self.connection and not self.connection.autocommit:
                self.connection.rollback()
            return []

    def _build_table_sql(self, template: str) -> str:
        """
        Build database-specific SQL from a template

        Converts template placeholders to database-specific syntax.

        Args:
            template: SQL template with placeholders

        Returns:
            Database-specific SQL string
        """
        replacements = {
            "{SERIAL}": (
                "SERIAL PRIMARY KEY"
                if self.db_type == "postgresql"
                else "INTEGER PRIMARY KEY AUTOINCREMENT"
            ),
            "{BOOLEAN_TRUE}": "TRUE" if self.db_type == "postgresql" else "1",
            "{BOOLEAN_FALSE}": "FALSE" if self.db_type == "postgresql" else "0",
        }

        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result

    def create_tables(self):
        """Create database tables if they don't exist"""
        if not self.enabled:
            return False

        self.logger.info("Creating database tables...")

        # VIP Callers table
        vip_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS vip_callers (
            id {SERIAL},
            caller_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255),
            priority_level INTEGER DEFAULT 1,
            notes TEXT,
            special_routing VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Call Detail Records table
        cdr_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS call_records (
            id {SERIAL},
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
        )

        # Voicemail messages table
        voicemail_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS voicemail_messages (
            id {SERIAL},
            message_id VARCHAR(100) UNIQUE NOT NULL,
            extension_number VARCHAR(20) NOT NULL,
            caller_id VARCHAR(50),
            file_path VARCHAR(255),
            duration INTEGER,
            listened BOOLEAN DEFAULT {BOOLEAN_FALSE},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transcription_text TEXT,
            transcription_confidence FLOAT,
            transcription_language VARCHAR(10),
            transcription_provider VARCHAR(20),
            transcribed_at TIMESTAMP
        )
        """
        )

        # Registered phones table - tracks phones by MAC (if available) or IP address
        registered_phones_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS registered_phones (
            id {SERIAL},
            mac_address VARCHAR(20),
            extension_number VARCHAR(20) NOT NULL,
            user_agent VARCHAR(255),
            ip_address VARCHAR(50) NOT NULL,
            first_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            contact_uri VARCHAR(255),
            UNIQUE(mac_address, extension_number),
            UNIQUE(ip_address, extension_number)
        )
        """
        )

        # Provisioned devices table - stores phone provisioning configuration
        provisioned_devices_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS provisioned_devices (
            id {SERIAL},
            mac_address VARCHAR(20) UNIQUE NOT NULL,
            extension_number VARCHAR(20) NOT NULL,
            vendor VARCHAR(50) NOT NULL,
            model VARCHAR(50) NOT NULL,
            device_type VARCHAR(20) DEFAULT 'phone',
            static_ip VARCHAR(50),
            config_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_provisioned TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Extensions table - stores user extensions/phone numbers
        extensions_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS extensions (
            id {SERIAL},
            number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            password_salt VARCHAR(255),
            allow_external BOOLEAN DEFAULT {BOOLEAN_TRUE},
            voicemail_pin_hash VARCHAR(255),
            voicemail_pin_salt VARCHAR(255),
            is_admin BOOLEAN DEFAULT {BOOLEAN_FALSE},
            ad_synced BOOLEAN DEFAULT {BOOLEAN_FALSE},
            ad_username VARCHAR(100),
            password_changed_at TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            account_locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Security audit log table
        security_audit_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS security_audit (
            id {SERIAL},
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(50) NOT NULL,
            identifier VARCHAR(100) NOT NULL,
            ip_address VARCHAR(45),
            success BOOLEAN DEFAULT {BOOLEAN_TRUE},
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Emergency contacts table
        emergency_contacts_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            extension VARCHAR(20),
            phone VARCHAR(50),
            email VARCHAR(255),
            priority INTEGER DEFAULT 1,
            notification_methods TEXT,
            active BOOLEAN DEFAULT {BOOLEAN_TRUE},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Emergency notifications table
        emergency_notifications_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS emergency_notifications (
            id VARCHAR(100) PRIMARY KEY,
            timestamp VARCHAR(50) NOT NULL,
            trigger_type VARCHAR(50) NOT NULL,
            details TEXT,
            contacts_notified TEXT,
            methods_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # System configuration table - stores key-value config pairs
        system_config_table = self._build_table_sql(
            """
        CREATE TABLE IF NOT EXISTS system_config (
            id {SERIAL},
            config_key VARCHAR(100) UNIQUE NOT NULL,
            config_value TEXT,
            config_type VARCHAR(20) DEFAULT 'string',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(20)
        )
        """
        )

        # Execute table creation
        success = True
        for table_sql in [
            vip_table,
            cdr_table,
            voicemail_table,
            registered_phones_table,
            provisioned_devices_table,
            extensions_table,
            security_audit_table,
            emergency_contacts_table,
            emergency_notifications_table,
            system_config_table,
        ]:
            if not self._execute_with_context(table_sql, "table creation"):
                success = False

        # Create indexes - use permissive execution that handles existing
        # indexes gracefully
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_vip_caller_id ON vip_callers(caller_id)",
            "CREATE INDEX IF NOT EXISTS idx_vip_priority ON vip_callers(priority_level)",
            "CREATE INDEX IF NOT EXISTS idx_cdr_call_id ON call_records(call_id)",
            "CREATE INDEX IF NOT EXISTS idx_cdr_from ON call_records(from_extension)",
            "CREATE INDEX IF NOT EXISTS idx_cdr_start_time ON call_records(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_vm_extension ON voicemail_messages(extension_number)",
            "CREATE INDEX IF NOT EXISTS idx_vm_listened ON voicemail_messages(listened)",
            "CREATE INDEX IF NOT EXISTS idx_phones_mac ON registered_phones(mac_address)",
            "CREATE INDEX IF NOT EXISTS idx_phones_extension ON registered_phones(extension_number)",
            "CREATE INDEX IF NOT EXISTS idx_provisioned_mac ON provisioned_devices(mac_address)",
            "CREATE INDEX IF NOT EXISTS idx_provisioned_extension ON provisioned_devices(extension_number)",
            "CREATE INDEX IF NOT EXISTS idx_provisioned_vendor ON provisioned_devices(vendor)",
            "CREATE INDEX IF NOT EXISTS idx_ext_number ON extensions(number)",
            "CREATE INDEX IF NOT EXISTS idx_ext_email ON extensions(email)",
            "CREATE INDEX IF NOT EXISTS idx_ext_ad_synced ON extensions(ad_synced)",
            "CREATE INDEX IF NOT EXISTS idx_security_audit_timestamp ON security_audit(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_security_audit_identifier ON security_audit(identifier)",
            "CREATE INDEX IF NOT EXISTS idx_security_audit_event_type ON security_audit(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_emergency_contacts_active ON emergency_contacts(active)",
            "CREATE INDEX IF NOT EXISTS idx_emergency_contacts_priority ON emergency_contacts(priority)",
            "CREATE INDEX IF NOT EXISTS idx_emergency_notifications_timestamp ON emergency_notifications(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_emergency_notifications_trigger_type ON emergency_notifications(trigger_type)",
        ]

        for index_sql in indexes:
            # Index creation failures are non-critical - indexes may already exist
            # or user may lack permissions on pre-existing tables
            self._execute_with_context(index_sql, "index creation", critical=False)

        # Perform schema migrations for existing tables
        self._migrate_schema()

        if success:
            self.logger.info("Database tables created successfully")
        else:
            self.logger.error("Failed to create some database tables")

        return success

    def _migrate_schema(self):
        """
        Migrate database schema to add new columns
        Safe migrations that handle existing columns gracefully
        """
        self.logger.info("Checking for schema migrations...")

        # Migration: Add transcription columns to voicemail_messages
        transcription_columns = [
            ("transcription_text", "TEXT"),
            ("transcription_confidence", "FLOAT" if self.db_type == "postgresql" else "REAL"),
            ("transcription_language", "VARCHAR(10)"),
            ("transcription_provider", "VARCHAR(20)"),
            ("transcribed_at", "TIMESTAMP"),
        ]

        for column_name, column_type in transcription_columns:
            # Check if column exists
            check_query = (
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='voicemail_messages' AND column_name=%s
            """
                if self.db_type == "postgresql"
                else """
            SELECT name FROM pragma_table_info('voicemail_messages') WHERE name=?
            """
            )

            try:
                cursor = self.connection.cursor()
                cursor.execute(check_query, (column_name,))
                exists = cursor.fetchone() is not None
                cursor.close()

                if not exists:
                    # Add column
                    alter_query = (
                        f"ALTER TABLE voicemail_messages ADD COLUMN {column_name} {column_type}"
                    )
                    self.logger.info(f"Adding column: {column_name}")
                    self._execute_with_context(
                        alter_query, f"add column {column_name}", critical=False
                    )
                else:
                    self.logger.debug(f"Column {column_name} already exists")
            except Exception as e:
                self.logger.debug(f"Column check/add for {column_name}: {e}")
                if self.connection and not self.connection.autocommit:
                    self.connection.rollback()

        # Migration: Add security columns to extensions table
        extensions_columns = [
            ("password_salt", "VARCHAR(255)"),
            ("voicemail_pin_hash", "VARCHAR(255)"),
            ("voicemail_pin_salt", "VARCHAR(255)"),
            (
                "is_admin",
                "BOOLEAN DEFAULT FALSE" if self.db_type == "postgresql" else "BOOLEAN DEFAULT 0",
            ),
        ]

        for column_name, column_type in extensions_columns:
            # Check if column exists
            check_query = (
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='extensions' AND column_name=%s
            """
                if self.db_type == "postgresql"
                else """
            SELECT name FROM pragma_table_info('extensions') WHERE name=?
            """
            )

            try:
                cursor = self.connection.cursor()
                cursor.execute(check_query, (column_name,))
                exists = cursor.fetchone() is not None
                cursor.close()

                if not exists:
                    # Add column
                    alter_query = f"ALTER TABLE extensions ADD COLUMN {column_name} {column_type}"
                    self.logger.info(f"Adding column to extensions: {column_name}")
                    self._execute_with_context(
                        alter_query, f"add column {column_name} to extensions", critical=False
                    )
                else:
                    self.logger.debug(f"Column {column_name} already exists in extensions")
            except Exception as e:
                self.logger.debug(f"Column check/add for {column_name} in extensions: {e}")
                if self.connection and not self.connection.autocommit:
                    self.connection.rollback()

        # Migration: Add device_type column to provisioned_devices table
        device_type_column = ("device_type", "VARCHAR(20) DEFAULT 'phone'")

        # Check if column exists
        check_query = (
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='provisioned_devices' AND column_name=%s
        """
            if self.db_type == "postgresql"
            else """
        SELECT name FROM pragma_table_info('provisioned_devices') WHERE name=?
        """
        )

        try:
            cursor = self.connection.cursor()
            cursor.execute(check_query, (device_type_column[0],))
            exists = cursor.fetchone() is not None
            cursor.close()

            if not exists:
                # Add column
                alter_query = f"ALTER TABLE provisioned_devices ADD COLUMN {device_type_column[0]} {device_type_column[1]}"
                self.logger.info(f"Adding column to provisioned_devices: {device_type_column[0]}")
                self._execute_with_context(
                    alter_query,
                    f"add column {device_type_column[0]} to provisioned_devices",
                    critical=False,
                )
            else:
                self.logger.debug(
                    f"Column {device_type_column[0]} already exists in provisioned_devices"
                )
        except Exception as e:
            self.logger.debug(
                f"Column check/add for {device_type_column[0]} in provisioned_devices: {e}"
            )
            if self.connection and not self.connection.autocommit:
                self.connection.rollback()

        # Apply framework feature migrations
        self._apply_framework_migrations()

        self.logger.info("Schema migration check complete")

    def _apply_framework_migrations(self):
        """Apply framework feature migrations"""
        try:
            from pbx.utils.migrations import MigrationManager, register_all_migrations

            self.logger.info("Applying framework feature migrations...")
            migration_manager = MigrationManager(self)
            register_all_migrations(migration_manager)

            if migration_manager.apply_migrations():
                self.logger.info("✓ Framework migrations applied successfully")
            else:
                self.logger.warning("Some framework migrations may have failed")

        except Exception as e:
            self.logger.error(f"Failed to apply framework migrations: {e}")
            # Don't fail startup if migrations fail
            import traceback

            self.logger.debug(traceback.format_exc())


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

    def add_vip(
        self, caller_id: str, priority_level: int = 1, name: str = None, notes: str = None
    ) -> bool:
        """Add or update VIP caller"""
        query = (
            """
        INSERT INTO vip_callers (caller_id, priority_level, name, notes, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (caller_id) DO UPDATE
        SET priority_level = EXCLUDED.priority_level,
            name = EXCLUDED.name,
            notes = EXCLUDED.notes,
            updated_at = EXCLUDED.updated_at
        """
            if self.db.db_type == "postgresql"
            else """
        INSERT OR REPLACE INTO vip_callers (caller_id, priority_level, name, notes, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
        )

        params = (caller_id, priority_level, name, notes, datetime.now())
        return self.db.execute(query, params)

    def remove_vip(self, caller_id: str) -> bool:
        """Remove VIP caller"""
        query = (
            "DELETE FROM vip_callers WHERE caller_id = %s"
            if self.db.db_type == "postgresql"
            else "DELETE FROM vip_callers WHERE caller_id = ?"
        )
        return self.db.execute(query, (caller_id,))

    def get_vip(self, caller_id: str) -> Optional[Dict]:
        """Get VIP caller information"""
        query = (
            "SELECT * FROM vip_callers WHERE caller_id = %s"
            if self.db.db_type == "postgresql"
            else "SELECT * FROM vip_callers WHERE caller_id = ?"
        )
        return self.db.fetch_one(query, (caller_id,))

    def list_vips(self, priority_level: int = None) -> List[Dict]:
        """List all VIP callers"""
        if priority_level:
            query = (
                "SELECT * FROM vip_callers WHERE priority_level = %s ORDER BY name"
                if self.db.db_type == "postgresql"
                else "SELECT * FROM vip_callers WHERE priority_level = ? ORDER BY name"
            )
            return self.db.fetch_all(query, (priority_level,))
        else:
            query = "SELECT * FROM vip_callers ORDER BY priority_level, name"
            return self.db.fetch_all(query)

    def is_vip(self, caller_id: str) -> bool:
        """Check if caller is VIP"""
        return self.get_vip(caller_id) is not None


class RegisteredPhonesDB:
    """Registered phones database operations"""

    def __init__(self, db: DatabaseBackend):
        """
        Initialize registered phones database

        Args:
            db: Database backend instance
        """
        self.db = db
        self.logger = get_logger()

    def register_phone(
        self,
        extension_number: str,
        ip_address: str,
        mac_address: str = None,
        user_agent: str = None,
        contact_uri: str = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Register or update a phone registration

        Args:
            extension_number: Extension number
            ip_address: IP address of the phone
            mac_address: MAC address (optional, can be None)
            user_agent: User-Agent header from SIP message
            contact_uri: Contact URI from SIP message

        Returns:
            tuple[bool, Optional[str]]: Success status and the actual MAC address stored (or None)
        """
        # First, check if this MAC or IP is registered to a DIFFERENT extension
        # This handles reprovisioning: when a phone is moved from one extension
        # to another
        old_registrations = []
        if mac_address:
            # Check if this MAC is registered to a different extension
            old_by_mac = self.get_by_mac(mac_address)
            if old_by_mac and old_by_mac["extension_number"] != extension_number:
                old_registrations.append(old_by_mac)
                self.logger.info(
                    f"Phone MAC {mac_address} was registered to extension {
                        old_by_mac['extension_number']}, will update to {extension_number}"
                )

        # Check if this IP is registered to a different extension
        old_by_ip = self.get_by_ip(ip_address)
        if old_by_ip and old_by_ip["extension_number"] != extension_number:
            # Only add if it's not already in the list (avoid duplicates if MAC
            # and IP point to same record)
            if not any(r["id"] == old_by_ip["id"] for r in old_registrations):
                old_registrations.append(old_by_ip)
                self.logger.info(
                    f"Phone IP {ip_address} was registered to extension {
                        old_by_ip['extension_number']}, will update to {extension_number}"
                )

        # Delete old registrations to different extensions
        for old_reg in old_registrations:
            delete_query = (
                """
            DELETE FROM registered_phones WHERE id = %s
            """
                if self.db.db_type == "postgresql"
                else """
            DELETE FROM registered_phones WHERE id = ?
            """
            )
            self.db.execute(delete_query, (old_reg["id"],))
            self.logger.info(
                f"Removed old registration: ext={
                    old_reg['extension_number']}, ip={
                    old_reg.get('ip_address')}, mac={
                    old_reg.get('mac_address')}"
            )

        # Now check if this phone is already registered to THIS extension (by
        # MAC or IP)
        existing = None
        if mac_address:
            existing = self.get_by_mac(mac_address, extension_number)
        if not existing:
            existing = self.get_by_ip(ip_address, extension_number)

        if existing:
            # Update existing registration
            # Preserve existing values if new values are None (device didn't
            # send them)
            updated_mac = mac_address if mac_address is not None else existing.get("mac_address")
            updated_ip = ip_address if ip_address is not None else existing.get("ip_address")
            updated_user_agent = (
                user_agent if user_agent is not None else existing.get("user_agent")
            )
            updated_contact_uri = (
                contact_uri if contact_uri is not None else existing.get("contact_uri")
            )

            query = (
                """
            UPDATE registered_phones
            SET mac_address = %s, ip_address = %s, user_agent = %s,
                contact_uri = %s, last_registered = %s
            WHERE id = %s
            """
                if self.db.db_type == "postgresql"
                else """
            UPDATE registered_phones
            SET mac_address = ?, ip_address = ?, user_agent = ?,
                contact_uri = ?, last_registered = ?
            WHERE id = ?
            """
            )
            params = (
                updated_mac,
                updated_ip,
                updated_user_agent,
                updated_contact_uri,
                datetime.now(),
                existing["id"],
            )
            success = self.db.execute(query, params)
            return (success, updated_mac)
        else:
            # Insert new registration
            query = (
                """
            INSERT INTO registered_phones
            (mac_address, extension_number, ip_address, user_agent, contact_uri,
             first_registered, last_registered)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
                if self.db.db_type == "postgresql"
                else """
            INSERT INTO registered_phones
            (mac_address, extension_number, ip_address, user_agent, contact_uri,
             first_registered, last_registered)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            )
            now = datetime.now()
            params = (mac_address, extension_number, ip_address, user_agent, contact_uri, now, now)
            success = self.db.execute(query, params)
            return (success, mac_address)

    def get_by_mac(self, mac_address: str, extension_number: str = None) -> Optional[Dict]:
        """
        Get phone registration by MAC address

        Args:
            mac_address: MAC address
            extension_number: Optional extension filter

        Returns:
            dict: Phone registration data or None
        """
        if extension_number:
            query = (
                """
            SELECT * FROM registered_phones
            WHERE mac_address = %s AND extension_number = %s
            """
                if self.db.db_type == "postgresql"
                else """
            SELECT * FROM registered_phones
            WHERE mac_address = ? AND extension_number = ?
            """
            )
            return self.db.fetch_one(query, (mac_address, extension_number))
        else:
            query = (
                """
            SELECT * FROM registered_phones WHERE mac_address = %s
            """
                if self.db.db_type == "postgresql"
                else """
            SELECT * FROM registered_phones WHERE mac_address = ?
            """
            )
            return self.db.fetch_one(query, (mac_address,))

    def get_by_ip(self, ip_address: str, extension_number: str = None) -> Optional[Dict]:
        """
        Get phone registration by IP address

        Args:
            ip_address: IP address
            extension_number: Optional extension filter

        Returns:
            dict: Phone registration data or None
        """
        if extension_number:
            query = (
                """
            SELECT * FROM registered_phones
            WHERE ip_address = %s AND extension_number = %s
            """
                if self.db.db_type == "postgresql"
                else """
            SELECT * FROM registered_phones
            WHERE ip_address = ? AND extension_number = ?
            """
            )
            return self.db.fetch_one(query, (ip_address, extension_number))
        else:
            query = (
                """
            SELECT * FROM registered_phones WHERE ip_address = %s
            """
                if self.db.db_type == "postgresql"
                else """
            SELECT * FROM registered_phones WHERE ip_address = ?
            """
            )
            return self.db.fetch_one(query, (ip_address,))

    def get_by_extension(self, extension_number: str) -> List[Dict]:
        """
        Get all phone registrations for an extension

        Args:
            extension_number: Extension number

        Returns:
            list: List of phone registration data
        """
        query = (
            """
        SELECT * FROM registered_phones
        WHERE extension_number = %s
        ORDER BY last_registered DESC
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM registered_phones
        WHERE extension_number = ?
        ORDER BY last_registered DESC
        """
        )
        return self.db.fetch_all(query, (extension_number,))

    def list_all(self) -> List[Dict]:
        """
        List all registered phones

        Returns:
            list: List of all phone registrations
        """
        query = """
        SELECT * FROM registered_phones
        ORDER BY last_registered DESC
        """
        return self.db.fetch_all(query)

    def remove_phone(self, phone_id: int) -> bool:
        """
        Remove a phone registration

        Args:
            phone_id: Phone registration ID

        Returns:
            bool: True if successful
        """
        query = (
            """
        DELETE FROM registered_phones WHERE id = %s
        """
            if self.db.db_type == "postgresql"
            else """
        DELETE FROM registered_phones WHERE id = ?
        """
        )
        return self.db.execute(query, (phone_id,))

    def update_phone_extension(self, mac_address: str, new_extension_number: str) -> bool:
        """
        Update the extension number for a phone identified by MAC address.
        This is useful when reprovisioning a phone to a different extension.

        Note: This will update ALL registrations with the given MAC address,
        effectively moving the phone to the new extension.

        Args:
            mac_address: MAC address of the phone to update
            new_extension_number: New extension number to assign

        Returns:
            bool: True if the SQL execution succeeded, False on error.
            Note: Returns True even if no matching rows were found to update.
        """
        if not mac_address:
            self.logger.error("Cannot update phone extension: MAC address is required")
            return False

        query = (
            """
        UPDATE registered_phones
        SET extension_number = %s, last_registered = %s
        WHERE mac_address = %s
        """
            if self.db.db_type == "postgresql"
            else """
        UPDATE registered_phones
        SET extension_number = ?, last_registered = ?
        WHERE mac_address = ?
        """
        )

        params = (new_extension_number, datetime.now(), mac_address)
        success = self.db.execute(query, params)

        if success:
            self.logger.info(f"Updated phone {mac_address} to extension {new_extension_number}")

        return success

    def cleanup_incomplete_registrations(self) -> tuple[bool, int]:
        """
        Remove phone registrations that are missing MAC address, IP address, or extension number.
        Only phones with all three fields (MAC, IP, and Extension) should be retained.
        This is called at startup to ensure data integrity.

        Returns:
            tuple[bool, int]: Success status and count of removed registrations
        """
        try:
            # First, count how many incomplete registrations exist
            count_query = """
            SELECT COUNT(*) as count FROM registered_phones
            WHERE mac_address IS NULL OR mac_address = ''
               OR ip_address IS NULL OR ip_address = ''
               OR extension_number IS NULL OR extension_number = ''
            """
            result = self.db.fetch_one(count_query)
            count = result["count"] if result else 0

            if count == 0:
                self.logger.info("No incomplete phone registrations found")
                return (True, 0)

            # Delete incomplete registrations
            delete_query = """
            DELETE FROM registered_phones
            WHERE mac_address IS NULL OR mac_address = ''
               OR ip_address IS NULL OR ip_address = ''
               OR extension_number IS NULL OR extension_number = ''
            """
            success = self.db.execute(delete_query)

            if success:
                self.logger.info(
                    f"Cleaned up {count} incomplete phone registration(s) from database"
                )
                self.logger.info("Only phones with MAC, IP, and Extension are retained")
            else:
                self.logger.error("Failed to cleanup incomplete phone registrations")

            return (success, count)
        except Exception as e:
            self.logger.error(f"Error cleaning up incomplete phone registrations: {e}")
            return (False, 0)

    def clear_all(self) -> bool:
        """
        Clear all phone registrations from the table.
        This is typically called on server boot to remove stale registrations.

        Returns:
            bool: True if successful
        """
        query = "DELETE FROM registered_phones"
        success = self.db.execute(query)
        if success:
            self.logger.info("Cleared all phone registrations from database")
        return success


class ExtensionDB:
    """Extension database operations"""

    def __init__(self, db: DatabaseBackend):
        """
        Initialize extension database

        Args:
            db: Database backend instance
        """
        self.db = db
        self.logger = get_logger()

    def _hash_voicemail_pin(self, pin: str) -> tuple:
        """
        Hash a voicemail PIN using FIPS-compliant encryption

        Args:
            pin: Voicemail PIN to hash

        Returns:
            tuple: (pin_hash, pin_salt) or (None, None) if hashing fails
        """
        if not pin:
            return None, None

        try:
            from pbx.utils.encryption import get_encryption

            enc = get_encryption()
            pin_hash, pin_salt = enc.hash_password(pin)
            return pin_hash, pin_salt
        except Exception as e:
            self.logger.error(f"Failed to hash voicemail PIN: {e}")
            return None, None

    def add(
        self,
        number: str,
        name: str,
        password_hash: str,
        email: str = None,
        allow_external: bool = True,
        voicemail_pin: str = None,
        ad_synced: bool = False,
        ad_username: str = None,
        is_admin: bool = False,
    ) -> bool:
        """
        Add a new extension

        Args:
            number: Extension number
            name: Display name
            password_hash: Hashed password
            email: Email address (optional)
            allow_external: Allow external calls
            voicemail_pin: Voicemail PIN (optional) - will be stored as hash/salt
            ad_synced: Whether synced from Active Directory
            ad_username: Active Directory username (optional)
            is_admin: Whether extension has admin privileges (optional)

        Returns:
            bool: True if successful
        """
        # Hash the voicemail PIN if provided
        voicemail_pin_hash, voicemail_pin_salt = self._hash_voicemail_pin(voicemail_pin)

        # If PIN was provided but hashing failed, return False
        if voicemail_pin and not voicemail_pin_hash:
            self.logger.error(f"Cannot add extension {number}: voicemail PIN hashing failed")
            return False

        query = (
            """
        INSERT INTO extensions (number, name, email, password_hash, allow_external, voicemail_pin_hash, voicemail_pin_salt, ad_synced, ad_username, is_admin)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
            if self.db.db_type == "postgresql"
            else """
        INSERT INTO extensions (number, name, email, password_hash, allow_external, voicemail_pin_hash, voicemail_pin_salt, ad_synced, ad_username, is_admin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        )

        return self.db.execute(
            query,
            (
                number,
                name,
                email,
                password_hash,
                allow_external,
                voicemail_pin_hash,
                voicemail_pin_salt,
                ad_synced,
                ad_username,
                is_admin,
            ),
        )

    def get(self, number: str) -> Optional[Dict]:
        """
        Get extension by number

        Args:
            number: Extension number

        Returns:
            dict: Extension data or None
        """
        query = (
            """
        SELECT * FROM extensions WHERE number = %s
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM extensions WHERE number = ?
        """
        )
        return self.db.fetch_one(query, (number,))

    def get_all(self) -> List[Dict]:
        """
        Get all extensions

        Returns:
            list: List of all extensions
        """
        query = """
        SELECT * FROM extensions ORDER BY number
        """
        return self.db.fetch_all(query)

    def get_ad_synced(self) -> List[Dict]:
        """
        Get all AD-synced extensions

        Returns:
            list: List of AD-synced extensions
        """
        query = (
            """
        SELECT * FROM extensions WHERE ad_synced = %s ORDER BY number
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM extensions WHERE ad_synced = 1 ORDER BY number
        """
        )
        return (
            self.db.fetch_all(query, (True,))
            if self.db.db_type == "postgresql"
            else self.db.fetch_all(query)
        )

    def update(
        self,
        number: str,
        name: str = None,
        email: str = None,
        password_hash: str = None,
        allow_external: bool = None,
        voicemail_pin: str = None,
        ad_synced: bool = None,
        ad_username: str = None,
        is_admin: bool = None,
    ) -> bool:
        """
        Update an extension

        Args:
            number: Extension number
            name: Display name (optional)
            email: Email address (optional)
            password_hash: Hashed password (optional)
            allow_external: Allow external calls (optional)
            voicemail_pin: Voicemail PIN (optional)
            ad_synced: Whether synced from Active Directory (optional)
            ad_username: Active Directory username (optional)
            is_admin: Whether extension has admin privileges (optional)

        Returns:
            bool: True if successful
        """
        # Build update query dynamically based on provided fields
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s" if self.db.db_type == "postgresql" else "name = ?")
            params.append(name)

        if email is not None:
            updates.append("email = %s" if self.db.db_type == "postgresql" else "email = ?")
            params.append(email)

        if password_hash is not None:
            updates.append(
                "password_hash = %s" if self.db.db_type == "postgresql" else "password_hash = ?"
            )
            params.append(password_hash)

        if allow_external is not None:
            updates.append(
                "allow_external = %s" if self.db.db_type == "postgresql" else "allow_external = ?"
            )
            params.append(allow_external)

        if voicemail_pin is not None:
            # Hash the voicemail PIN before storing
            voicemail_pin_hash, voicemail_pin_salt = self._hash_voicemail_pin(voicemail_pin)

            # If PIN was provided but hashing failed, return False
            if voicemail_pin and not voicemail_pin_hash:
                self.logger.error(f"Cannot update extension {number}: voicemail PIN hashing failed")
                return False

            updates.append(
                "voicemail_pin_hash = %s"
                if self.db.db_type == "postgresql"
                else "voicemail_pin_hash = ?"
            )
            params.append(voicemail_pin_hash)
            updates.append(
                "voicemail_pin_salt = %s"
                if self.db.db_type == "postgresql"
                else "voicemail_pin_salt = ?"
            )
            params.append(voicemail_pin_salt)

        if ad_synced is not None:
            updates.append("ad_synced = %s" if self.db.db_type == "postgresql" else "ad_synced = ?")
            params.append(ad_synced)

        if ad_username is not None:
            updates.append(
                "ad_username = %s" if self.db.db_type == "postgresql" else "ad_username = ?"
            )
            params.append(ad_username)

        if is_admin is not None:
            updates.append("is_admin = %s" if self.db.db_type == "postgresql" else "is_admin = ?")
            params.append(is_admin)

        if not updates:
            return True  # Nothing to update

        # Add updated_at timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")

        # Add number to params for WHERE clause
        params.append(number)

        query = """
        UPDATE extensions
        SET {', '.join(updates)}
        WHERE number = {'%s' if self.db.db_type == 'postgresql' else '?'}
        """  # nosec B608 - updates are validated field names, placeholder is safe

        return self.db.execute(query, tuple(params))

    def delete(self, number: str) -> bool:
        """
        Delete an extension

        Args:
            number: Extension number

        Returns:
            bool: True if successful
        """
        query = (
            """
        DELETE FROM extensions WHERE number = %s
        """
            if self.db.db_type == "postgresql"
            else """
        DELETE FROM extensions WHERE number = ?
        """
        )
        return self.db.execute(query, (number,))

    def search(self, query_str: str) -> List[Dict]:
        """
        Search extensions by number, name, or email

        Args:
            query_str: Search query

        Returns:
            list: List of matching extensions
        """
        search_pattern = f"%{query_str}%"
        query = (
            """
        SELECT * FROM extensions
        WHERE number LIKE %s OR name LIKE %s OR email LIKE %s
        ORDER BY number
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM extensions
        WHERE number LIKE ? OR name LIKE ? OR email LIKE ?
        ORDER BY number
        """
        )
        return self.db.fetch_all(query, (search_pattern, search_pattern, search_pattern))

    def get_config(self, key: str, default=None):
        """
        Get a configuration value by key

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        query = (
            "SELECT config_value, config_type FROM system_config WHERE config_key = %s"
            if self.db.db_type == "postgresql"
            else "SELECT config_value, config_type FROM system_config WHERE config_key = ?"
        )

        result = self.db.fetch_one(query, (key,))
        if result:
            value = result.get("config_value")
            config_type = result.get("config_type")
            # Convert value based on type with error handling
            try:
                if config_type == "int":
                    return int(value) if value else default
                elif config_type == "bool":
                    if value and isinstance(value, str):
                        return value.lower() in ("true", "1", "yes")
                    else:
                        return default
                elif config_type == "json":
                    return json.loads(value) if value else default
                else:
                    return value if value else default
            except (ValueError, json.JSONDecodeError, AttributeError) as e:
                self.logger.warning(
                    f"Error parsing config value for key '{key}': {e}. Returning default."
                )
                return default
        return default

    def set_config(self, key: str, value, config_type: str = "string", updated_by: str = None):
        """
        Set a configuration value

        Args:
            key: Configuration key
            value: Configuration value
            config_type: Type of value (string, int, bool, json)
            updated_by: User who updated the config

        Returns:
            bool: True if successful
        """
        # Convert value to string for storage with error handling
        try:
            if config_type == "json":
                str_value = json.dumps(value)
            elif config_type == "bool":
                str_value = "true" if value else "false"
            else:
                str_value = str(value)
        except (TypeError, ValueError) as e:
            self.logger.error(f"Error serializing config value for key '{key}': {e}")
            return False

        # Check if key exists
        check_query = (
            "SELECT config_key FROM system_config WHERE config_key = %s"
            if self.db.db_type == "postgresql"
            else "SELECT config_key FROM system_config WHERE config_key = ?"
        )

        exists = self.db.fetch_one(check_query, (key,))

        if exists:
            # Update existing
            query = (
                """
            UPDATE system_config
            SET config_value = %s, config_type = %s, updated_at = %s, updated_by = %s
            WHERE config_key = %s
            """
                if self.db.db_type == "postgresql"
                else """
            UPDATE system_config
            SET config_value = ?, config_type = ?, updated_at = ?, updated_by = ?
            WHERE config_key = ?
            """
            )
            return self.db.execute(query, (str_value, config_type, datetime.now(), updated_by, key))
        else:
            # Insert new
            query = (
                """
            INSERT INTO system_config (config_key, config_value, config_type, updated_at, updated_by)
            VALUES (%s, %s, %s, %s, %s)
            """
                if self.db.db_type == "postgresql"
                else """
            INSERT INTO system_config (config_key, config_value, config_type, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?)
            """
            )
            return self.db.execute(query, (key, str_value, config_type, datetime.now(), updated_by))


class ProvisionedDevicesDB:
    """Provisioned devices database operations"""

    def __init__(self, db: DatabaseBackend):
        """
        Initialize provisioned devices database

        Args:
            db: Database backend instance
        """
        self.db = db
        self.logger = get_logger()

    def add_device(
        self,
        mac_address: str,
        extension_number: str,
        vendor: str,
        model: str,
        device_type: str = None,
        static_ip: str = None,
        config_url: str = None,
    ) -> bool:
        """
        Add or update a provisioned device

        Args:
            mac_address: MAC address (normalized format)
            extension_number: Extension number
            vendor: Phone vendor
            model: Phone model
            device_type: Device type ('phone' or 'ata', auto-detected if None)
            static_ip: Static IP address (optional)
            config_url: Configuration URL (optional)

        Returns:
            bool: True if successful
        """
        # Auto-detect device type if not provided
        if device_type is None:
            device_type = self._detect_device_type(vendor, model)

        # Check if device already exists
        existing = self.get_device(mac_address)

        if existing:
            # Update existing device
            query = (
                """
            UPDATE provisioned_devices
            SET extension_number = %s, vendor = %s, model = %s, device_type = %s,
                static_ip = %s, config_url = %s, updated_at = %s
            WHERE mac_address = %s
            """
                if self.db.db_type == "postgresql"
                else """
            UPDATE provisioned_devices
            SET extension_number = ?, vendor = ?, model = ?, device_type = ?,
                static_ip = ?, config_url = ?, updated_at = ?
            WHERE mac_address = ?
            """
            )
            params = (
                extension_number,
                vendor,
                model,
                device_type,
                static_ip,
                config_url,
                datetime.now(),
                mac_address,
            )
        else:
            # Insert new device
            query = (
                """
            INSERT INTO provisioned_devices
            (mac_address, extension_number, vendor, model, device_type, static_ip,
             config_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
                if self.db.db_type == "postgresql"
                else """
            INSERT INTO provisioned_devices
            (mac_address, extension_number, vendor, model, device_type, static_ip,
             config_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            )
            now = datetime.now()
            params = (
                mac_address,
                extension_number,
                vendor,
                model,
                device_type,
                static_ip,
                config_url,
                now,
                now,
            )

        return self.db.execute(query, params)

    def get_device(self, mac_address: str) -> Optional[Dict]:
        """
        Get provisioned device by MAC address

        Args:
            mac_address: MAC address (normalized format)

        Returns:
            dict: Device data or None
        """
        query = (
            """
        SELECT * FROM provisioned_devices WHERE mac_address = %s
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM provisioned_devices WHERE mac_address = ?
        """
        )
        return self.db.fetch_one(query, (mac_address,))

    def get_device_by_extension(self, extension_number: str) -> Optional[Dict]:
        """
        Get provisioned device by extension number

        Args:
            extension_number: Extension number

        Returns:
            dict: Device data or None
        """
        query = (
            """
        SELECT * FROM provisioned_devices WHERE extension_number = %s
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM provisioned_devices WHERE extension_number = ?
        """
        )
        return self.db.fetch_one(query, (extension_number,))

    def get_device_by_ip(self, static_ip: str) -> Optional[Dict]:
        """
        Get provisioned device by static IP address

        Args:
            static_ip: Static IP address

        Returns:
            dict: Device data or None
        """
        query = (
            """
        SELECT * FROM provisioned_devices WHERE static_ip = %s
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM provisioned_devices WHERE static_ip = ?
        """
        )
        return self.db.fetch_one(query, (static_ip,))

    def list_all(self) -> List[Dict]:
        """
        List all provisioned devices

        Returns:
            list: List of all provisioned devices
        """
        query = """
        SELECT * FROM provisioned_devices
        ORDER BY extension_number
        """
        return self.db.fetch_all(query)

    def list_by_type(self, device_type: str) -> List[Dict]:
        """
        List provisioned devices by type

        Args:
            device_type: Device type ('phone' or 'ata')

        Returns:
            list: List of provisioned devices of specified type
        """
        query = (
            """
        SELECT * FROM provisioned_devices
        WHERE device_type = %s
        ORDER BY extension_number
        """
            if self.db.db_type == "postgresql"
            else """
        SELECT * FROM provisioned_devices
        WHERE device_type = ?
        ORDER BY extension_number
        """
        )
        return self.db.fetch_all(query, (device_type,))

    def list_atas(self) -> List[Dict]:
        """
        List all provisioned ATAs

        Returns:
            list: List of all provisioned ATA devices
        """
        return self.list_by_type("ata")

    def list_phones(self) -> List[Dict]:
        """
        List all provisioned phones (excluding ATAs)

        Returns:
            list: List of all provisioned phone devices
        """
        return self.list_by_type("phone")

    def _detect_device_type(self, vendor: str, model: str) -> str:
        """
        Detect device type based on vendor and model

        Args:
            vendor: Device vendor
            model: Device model

        Returns:
            str: 'ata' or 'phone'
        """
        return detect_device_type(vendor, model)

    def remove_device(self, mac_address: str) -> bool:
        """
        Remove a provisioned device

        Args:
            mac_address: MAC address

        Returns:
            bool: True if successful
        """
        query = (
            """
        DELETE FROM provisioned_devices WHERE mac_address = %s
        """
            if self.db.db_type == "postgresql"
            else """
        DELETE FROM provisioned_devices WHERE mac_address = ?
        """
        )
        return self.db.execute(query, (mac_address,))

    def mark_provisioned(self, mac_address: str) -> bool:
        """
        Mark device as provisioned (update last_provisioned timestamp)

        Args:
            mac_address: MAC address

        Returns:
            bool: True if successful
        """
        query = (
            """
        UPDATE provisioned_devices
        SET last_provisioned = %s
        WHERE mac_address = %s
        """
            if self.db.db_type == "postgresql"
            else """
        UPDATE provisioned_devices
        SET last_provisioned = ?
        WHERE mac_address = ?
        """
        )
        return self.db.execute(query, (datetime.now(), mac_address))

    def set_static_ip(self, mac_address: str, static_ip: str) -> bool:
        """
        Set or update static IP for a device

        Args:
            mac_address: MAC address
            static_ip: Static IP address

        Returns:
            bool: True if successful
        """
        query = (
            """
        UPDATE provisioned_devices
        SET static_ip = %s, updated_at = %s
        WHERE mac_address = %s
        """
            if self.db.db_type == "postgresql"
            else """
        UPDATE provisioned_devices
        SET static_ip = ?, updated_at = ?
        WHERE mac_address = ?
        """
        )
        return self.db.execute(query, (static_ip, datetime.now(), mac_address))


# Global instance
_database = None


def get_database(config=None) -> DatabaseBackend:
    """
    Get or create database backend instance.

    Args:
        config: Configuration dict. Required for first initialization.

    Returns:
        DatabaseBackend instance or None if not yet initialized.
        Callers must check for None before using.
    """
    global _database
    if _database is None and config is not None:
        _database = DatabaseBackend(config)
    return _database
