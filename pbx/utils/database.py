"""
Database backend for PBX features
Provides optional PostgreSQL/SQLite storage for VIP callers, CDR, and other data
"""
import os
import traceback
from pbx.utils.logger import get_logger
from typing import Optional, Dict, List
from datetime import datetime

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
        self.logger.info(f"Initiating database connection (type: {self.db_type})...")
        try:
            if self.db_type == 'postgresql':
                return self._connect_postgresql()
            elif self.db_type == 'sqlite':
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

        host = self.config.get('database.host', 'localhost')
        port = self.config.get('database.port', 5432)
        database = self.config.get('database.name', 'pbx')
        user = self.config.get('database.user', 'pbx')
        
        self.logger.info(f"Connecting to PostgreSQL database...")
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
                password=self.config.get('database.password', '')
            )
            self.enabled = True
            self.logger.info("✓ Successfully connected to PostgreSQL database")
            self.logger.info(f"  Connection established: {host}:{port}/{database}")
            return True
        except Exception as e:
            self.logger.error(f"✗ PostgreSQL connection failed: {e}")
            self.logger.warning("Voicemail and other data will be stored ONLY in file system")
            self.logger.warning("To fix: Ensure PostgreSQL is running and accessible, or run 'python scripts/verify_database.py' for diagnostics")
            return False

    def _connect_sqlite(self) -> bool:
        """Connect to SQLite database"""
        if not SQLITE_AVAILABLE:
            self.logger.error("SQLite not available in this Python installation")
            return False

        db_path = self.config.get('database.path', 'pbx.db')
        self.logger.info(f"Connecting to SQLite database...")
        self.logger.info(f"  Database file: {db_path}")

        try:
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.enabled = True
            self.logger.info(f"✓ Successfully connected to SQLite database")
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

    def _execute_with_context(self, query: str, context: str = "query", params: tuple = None, critical: bool = True) -> bool:
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
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            error_msg = str(e).lower()
            # Check if this is a permission error on existing objects
            # Common patterns across PostgreSQL, MySQL, SQLite
            permission_errors = [
                "must be owner",           # PostgreSQL
                "permission denied",       # PostgreSQL/SQLite
                "access denied",           # MySQL
                "insufficient privileges", # Oracle
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
                return True  # Return True since this is not a critical failure
            elif any(pattern in error_msg for pattern in already_exists_errors):
                # Object already exists - this is fine
                self.logger.debug(f"{context.capitalize()} already exists: {e}")
                return True
            else:
                # This is an actual error - log verbosely
                self.logger.error(f"Error during {context}: {e}")
                self.logger.error(f"  Query: {query}")
                self.logger.error(f"  Parameters: {params}")
                self.logger.error(f"  Database type: {self.db_type}")
                self.logger.error(f"  Traceback: {traceback.format_exc()}")
                if self.connection:
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
            self.logger.error(f"  Enabled: {self.enabled}, Connection: {self.connection is not None}")
            return False
        return self._execute_with_context(query, "query execution", params, critical=True)

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
            self.logger.error(f"  Query: {query}")
            self.logger.error(f"  Parameters: {params}")
            self.logger.error(f"  Database type: {self.db_type}")
            self.logger.error(f"  Traceback: {traceback.format_exc()}")
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
            self.logger.error(f"  Query: {query}")
            self.logger.error(f"  Parameters: {params}")
            self.logger.error(f"  Database type: {self.db_type}")
            self.logger.error(f"  Traceback: {traceback.format_exc()}")
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transcription_text TEXT,
            transcription_confidence FLOAT,
            transcription_language VARCHAR(10),
            transcription_provider VARCHAR(20),
            transcribed_at TIMESTAMP
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transcription_text TEXT,
            transcription_confidence FLOAT,
            transcription_language VARCHAR(10),
            transcription_provider VARCHAR(20),
            transcribed_at TIMESTAMP
        )
        """

        # Registered phones table - tracks phones by MAC (if available) or IP address
        registered_phones_table = """
        CREATE TABLE IF NOT EXISTS registered_phones (
            id SERIAL PRIMARY KEY,
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
        """ if self.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS registered_phones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        # Provisioned devices table - stores phone provisioning configuration
        provisioned_devices_table = """
        CREATE TABLE IF NOT EXISTS provisioned_devices (
            id SERIAL PRIMARY KEY,
            mac_address VARCHAR(20) UNIQUE NOT NULL,
            extension_number VARCHAR(20) NOT NULL,
            vendor VARCHAR(50) NOT NULL,
            model VARCHAR(50) NOT NULL,
            static_ip VARCHAR(50),
            config_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_provisioned TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS provisioned_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address VARCHAR(20) UNIQUE NOT NULL,
            extension_number VARCHAR(20) NOT NULL,
            vendor VARCHAR(50) NOT NULL,
            model VARCHAR(50) NOT NULL,
            static_ip VARCHAR(50),
            config_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_provisioned TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Extensions table - stores user extensions/phone numbers
        extensions_table = """
        CREATE TABLE IF NOT EXISTS extensions (
            id SERIAL PRIMARY KEY,
            number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            password_salt VARCHAR(255),
            allow_external BOOLEAN DEFAULT TRUE,
            voicemail_pin_hash VARCHAR(255),
            voicemail_pin_salt VARCHAR(255),
            ad_synced BOOLEAN DEFAULT FALSE,
            ad_username VARCHAR(100),
            password_changed_at TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            account_locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            password_salt VARCHAR(255),
            allow_external BOOLEAN DEFAULT 1,
            voicemail_pin_hash VARCHAR(255),
            voicemail_pin_salt VARCHAR(255),
            ad_synced BOOLEAN DEFAULT 0,
            ad_username VARCHAR(100),
            password_changed_at TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            account_locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Security audit log table
        security_audit_table = """
        CREATE TABLE IF NOT EXISTS security_audit (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(50) NOT NULL,
            identifier VARCHAR(100) NOT NULL,
            ip_address VARCHAR(45),
            success BOOLEAN DEFAULT TRUE,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS security_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(50) NOT NULL,
            identifier VARCHAR(100) NOT NULL,
            ip_address VARCHAR(45),
            success BOOLEAN DEFAULT 1,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Execute table creation
        success = True
        for table_sql in [vip_table, cdr_table, voicemail_table, registered_phones_table, 
                         provisioned_devices_table, extensions_table, security_audit_table]:
            if not self._execute_with_context(table_sql, "table creation"):
                success = False

        # Create indexes - use permissive execution that handles existing indexes gracefully
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
            "CREATE INDEX IF NOT EXISTS idx_security_audit_event_type ON security_audit(event_type)"
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
            ("transcription_confidence", "FLOAT" if self.db_type == 'postgresql' else "REAL"),
            ("transcription_language", "VARCHAR(10)"),
            ("transcription_provider", "VARCHAR(20)"),
            ("transcribed_at", "TIMESTAMP")
        ]
        
        for column_name, column_type in transcription_columns:
            # Check if column exists
            check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='voicemail_messages' AND column_name=%s
            """ if self.db_type == 'postgresql' else """
            SELECT name FROM pragma_table_info('voicemail_messages') WHERE name=?
            """
            
            try:
                cursor = self.connection.cursor()
                cursor.execute(check_query, (column_name,))
                exists = cursor.fetchone() is not None
                cursor.close()
                
                if not exists:
                    # Add column
                    alter_query = f"ALTER TABLE voicemail_messages ADD COLUMN {column_name} {column_type}"
                    self.logger.info(f"Adding column: {column_name}")
                    self._execute_with_context(alter_query, f"add column {column_name}", critical=False)
                else:
                    self.logger.debug(f"Column {column_name} already exists")
            except Exception as e:
                self.logger.debug(f"Column check/add for {column_name}: {e}")
        
        self.logger.info("Schema migration check complete")


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

    def register_phone(self, extension_number: str, ip_address: str, 
                      mac_address: str = None, user_agent: str = None, 
                      contact_uri: str = None) -> tuple[bool, Optional[str]]:
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
        # First check if this phone is already registered (by MAC or IP)
        existing = None
        if mac_address:
            existing = self.get_by_mac(mac_address, extension_number)
        if not existing:
            existing = self.get_by_ip(ip_address, extension_number)
        
        if existing:
            # Update existing registration
            # Preserve existing values if new values are None (device didn't send them)
            updated_mac = mac_address if mac_address is not None else existing.get('mac_address')
            updated_ip = ip_address if ip_address is not None else existing.get('ip_address')
            updated_user_agent = user_agent if user_agent is not None else existing.get('user_agent')
            updated_contact_uri = contact_uri if contact_uri is not None else existing.get('contact_uri')
            
            query = """
            UPDATE registered_phones 
            SET mac_address = %s, ip_address = %s, user_agent = %s, 
                contact_uri = %s, last_registered = %s
            WHERE id = %s
            """ if self.db.db_type == 'postgresql' else """
            UPDATE registered_phones 
            SET mac_address = ?, ip_address = ?, user_agent = ?, 
                contact_uri = ?, last_registered = ?
            WHERE id = ?
            """
            params = (updated_mac, updated_ip, updated_user_agent, updated_contact_uri, 
                     datetime.now(), existing['id'])
            success = self.db.execute(query, params)
            return (success, updated_mac)
        else:
            # Insert new registration
            query = """
            INSERT INTO registered_phones 
            (mac_address, extension_number, ip_address, user_agent, contact_uri, 
             first_registered, last_registered)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """ if self.db.db_type == 'postgresql' else """
            INSERT INTO registered_phones 
            (mac_address, extension_number, ip_address, user_agent, contact_uri, 
             first_registered, last_registered)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            now = datetime.now()
            params = (mac_address, extension_number, ip_address, user_agent, 
                     contact_uri, now, now)
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
            query = """
            SELECT * FROM registered_phones 
            WHERE mac_address = %s AND extension_number = %s
            """ if self.db.db_type == 'postgresql' else """
            SELECT * FROM registered_phones 
            WHERE mac_address = ? AND extension_number = ?
            """
            return self.db.fetch_one(query, (mac_address, extension_number))
        else:
            query = """
            SELECT * FROM registered_phones WHERE mac_address = %s
            """ if self.db.db_type == 'postgresql' else """
            SELECT * FROM registered_phones WHERE mac_address = ?
            """
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
            query = """
            SELECT * FROM registered_phones 
            WHERE ip_address = %s AND extension_number = %s
            """ if self.db.db_type == 'postgresql' else """
            SELECT * FROM registered_phones 
            WHERE ip_address = ? AND extension_number = ?
            """
            return self.db.fetch_one(query, (ip_address, extension_number))
        else:
            query = """
            SELECT * FROM registered_phones WHERE ip_address = %s
            """ if self.db.db_type == 'postgresql' else """
            SELECT * FROM registered_phones WHERE ip_address = ?
            """
            return self.db.fetch_one(query, (ip_address,))

    def get_by_extension(self, extension_number: str) -> List[Dict]:
        """
        Get all phone registrations for an extension
        
        Args:
            extension_number: Extension number
            
        Returns:
            list: List of phone registration data
        """
        query = """
        SELECT * FROM registered_phones 
        WHERE extension_number = %s
        ORDER BY last_registered DESC
        """ if self.db.db_type == 'postgresql' else """
        SELECT * FROM registered_phones 
        WHERE extension_number = ?
        ORDER BY last_registered DESC
        """
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
        query = """
        DELETE FROM registered_phones WHERE id = %s
        """ if self.db.db_type == 'postgresql' else """
        DELETE FROM registered_phones WHERE id = ?
        """
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
            
        query = """
        UPDATE registered_phones 
        SET extension_number = %s, last_registered = %s
        WHERE mac_address = %s
        """ if self.db.db_type == 'postgresql' else """
        UPDATE registered_phones 
        SET extension_number = ?, last_registered = ?
        WHERE mac_address = ?
        """
        
        params = (new_extension_number, datetime.now(), mac_address)
        success = self.db.execute(query, params)
        
        if success:
            self.logger.info(f"Updated phone {mac_address} to extension {new_extension_number}")
        
        return success

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

    def add(self, number: str, name: str, password_hash: str, email: str = None, 
            allow_external: bool = True, voicemail_pin: str = None, 
            ad_synced: bool = False, ad_username: str = None) -> bool:
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
            
        Returns:
            bool: True if successful
        """
        # Hash the voicemail PIN if provided
        voicemail_pin_hash = None
        voicemail_pin_salt = None
        if voicemail_pin:
            try:
                from pbx.utils.encryption import get_encryption
                enc = get_encryption()
                voicemail_pin_hash, voicemail_pin_salt = enc.hash_password(voicemail_pin)
            except Exception as e:
                self.logger.error(f"Failed to hash voicemail PIN: {e}")
                
        query = """
        INSERT INTO extensions (number, name, email, password_hash, allow_external, voicemail_pin_hash, voicemail_pin_salt, ad_synced, ad_username)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """ if self.db.db_type == 'postgresql' else """
        INSERT INTO extensions (number, name, email, password_hash, allow_external, voicemail_pin_hash, voicemail_pin_salt, ad_synced, ad_username)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        return self.db.execute(query, (number, name, email, password_hash, allow_external, voicemail_pin_hash, voicemail_pin_salt, ad_synced, ad_username))

    def get(self, number: str) -> Optional[Dict]:
        """
        Get extension by number
        
        Args:
            number: Extension number
            
        Returns:
            dict: Extension data or None
        """
        query = """
        SELECT * FROM extensions WHERE number = %s
        """ if self.db.db_type == 'postgresql' else """
        SELECT * FROM extensions WHERE number = ?
        """
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
        query = """
        SELECT * FROM extensions WHERE ad_synced = %s ORDER BY number
        """ if self.db.db_type == 'postgresql' else """
        SELECT * FROM extensions WHERE ad_synced = 1 ORDER BY number
        """
        return self.db.fetch_all(query, (True,)) if self.db.db_type == 'postgresql' else self.db.fetch_all(query)

    def update(self, number: str, name: str = None, email: str = None, 
               password_hash: str = None, allow_external: bool = None,
               voicemail_pin: str = None, ad_synced: bool = None, 
               ad_username: str = None) -> bool:
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
            
        Returns:
            bool: True if successful
        """
        # Build update query dynamically based on provided fields
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s" if self.db.db_type == 'postgresql' else "name = ?")
            params.append(name)
        
        if email is not None:
            updates.append("email = %s" if self.db.db_type == 'postgresql' else "email = ?")
            params.append(email)
        
        if password_hash is not None:
            updates.append("password_hash = %s" if self.db.db_type == 'postgresql' else "password_hash = ?")
            params.append(password_hash)
        
        if allow_external is not None:
            updates.append("allow_external = %s" if self.db.db_type == 'postgresql' else "allow_external = ?")
            params.append(allow_external)
        
        if voicemail_pin is not None:
            # Hash the voicemail PIN before storing
            try:
                from pbx.utils.encryption import get_encryption
                enc = get_encryption()
                voicemail_pin_hash, voicemail_pin_salt = enc.hash_password(voicemail_pin)
                updates.append("voicemail_pin_hash = %s" if self.db.db_type == 'postgresql' else "voicemail_pin_hash = ?")
                params.append(voicemail_pin_hash)
                updates.append("voicemail_pin_salt = %s" if self.db.db_type == 'postgresql' else "voicemail_pin_salt = ?")
                params.append(voicemail_pin_salt)
            except Exception as e:
                self.logger.error(f"Failed to hash voicemail PIN: {e}")
        
        if ad_synced is not None:
            updates.append("ad_synced = %s" if self.db.db_type == 'postgresql' else "ad_synced = ?")
            params.append(ad_synced)
        
        if ad_username is not None:
            updates.append("ad_username = %s" if self.db.db_type == 'postgresql' else "ad_username = ?")
            params.append(ad_username)
        
        if not updates:
            return True  # Nothing to update
        
        # Add updated_at timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        # Add number to params for WHERE clause
        params.append(number)
        
        query = f"""
        UPDATE extensions 
        SET {', '.join(updates)}
        WHERE number = {'%s' if self.db.db_type == 'postgresql' else '?'}
        """
        
        return self.db.execute(query, tuple(params))

    def delete(self, number: str) -> bool:
        """
        Delete an extension
        
        Args:
            number: Extension number
            
        Returns:
            bool: True if successful
        """
        query = """
        DELETE FROM extensions WHERE number = %s
        """ if self.db.db_type == 'postgresql' else """
        DELETE FROM extensions WHERE number = ?
        """
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
        query = """
        SELECT * FROM extensions 
        WHERE number LIKE %s OR name LIKE %s OR email LIKE %s
        ORDER BY number
        """ if self.db.db_type == 'postgresql' else """
        SELECT * FROM extensions 
        WHERE number LIKE ? OR name LIKE ? OR email LIKE ?
        ORDER BY number
        """
        return self.db.fetch_all(query, (search_pattern, search_pattern, search_pattern))


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

    def add_device(self, mac_address: str, extension_number: str, vendor: str, 
                   model: str, static_ip: str = None, config_url: str = None) -> bool:
        """
        Add or update a provisioned device
        
        Args:
            mac_address: MAC address (normalized format)
            extension_number: Extension number
            vendor: Phone vendor
            model: Phone model
            static_ip: Static IP address (optional)
            config_url: Configuration URL (optional)
            
        Returns:
            bool: True if successful
        """
        # Check if device already exists
        existing = self.get_device(mac_address)
        
        if existing:
            # Update existing device
            query = """
            UPDATE provisioned_devices 
            SET extension_number = %s, vendor = %s, model = %s, static_ip = %s,
                config_url = %s, updated_at = %s
            WHERE mac_address = %s
            """ if self.db.db_type == 'postgresql' else """
            UPDATE provisioned_devices 
            SET extension_number = ?, vendor = ?, model = ?, static_ip = ?,
                config_url = ?, updated_at = ?
            WHERE mac_address = ?
            """
            params = (extension_number, vendor, model, static_ip, config_url, 
                     datetime.now(), mac_address)
        else:
            # Insert new device
            query = """
            INSERT INTO provisioned_devices 
            (mac_address, extension_number, vendor, model, static_ip, config_url, 
             created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """ if self.db.db_type == 'postgresql' else """
            INSERT INTO provisioned_devices 
            (mac_address, extension_number, vendor, model, static_ip, config_url, 
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            now = datetime.now()
            params = (mac_address, extension_number, vendor, model, static_ip, 
                     config_url, now, now)
        
        return self.db.execute(query, params)

    def get_device(self, mac_address: str) -> Optional[Dict]:
        """
        Get provisioned device by MAC address
        
        Args:
            mac_address: MAC address (normalized format)
            
        Returns:
            dict: Device data or None
        """
        query = """
        SELECT * FROM provisioned_devices WHERE mac_address = %s
        """ if self.db.db_type == 'postgresql' else """
        SELECT * FROM provisioned_devices WHERE mac_address = ?
        """
        return self.db.fetch_one(query, (mac_address,))

    def get_device_by_extension(self, extension_number: str) -> Optional[Dict]:
        """
        Get provisioned device by extension number
        
        Args:
            extension_number: Extension number
            
        Returns:
            dict: Device data or None
        """
        query = """
        SELECT * FROM provisioned_devices WHERE extension_number = %s
        """ if self.db.db_type == 'postgresql' else """
        SELECT * FROM provisioned_devices WHERE extension_number = ?
        """
        return self.db.fetch_one(query, (extension_number,))

    def get_device_by_ip(self, static_ip: str) -> Optional[Dict]:
        """
        Get provisioned device by static IP address
        
        Args:
            static_ip: Static IP address
            
        Returns:
            dict: Device data or None
        """
        query = """
        SELECT * FROM provisioned_devices WHERE static_ip = %s
        """ if self.db.db_type == 'postgresql' else """
        SELECT * FROM provisioned_devices WHERE static_ip = ?
        """
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

    def remove_device(self, mac_address: str) -> bool:
        """
        Remove a provisioned device
        
        Args:
            mac_address: MAC address
            
        Returns:
            bool: True if successful
        """
        query = """
        DELETE FROM provisioned_devices WHERE mac_address = %s
        """ if self.db.db_type == 'postgresql' else """
        DELETE FROM provisioned_devices WHERE mac_address = ?
        """
        return self.db.execute(query, (mac_address,))

    def mark_provisioned(self, mac_address: str) -> bool:
        """
        Mark device as provisioned (update last_provisioned timestamp)
        
        Args:
            mac_address: MAC address
            
        Returns:
            bool: True if successful
        """
        query = """
        UPDATE provisioned_devices 
        SET last_provisioned = %s
        WHERE mac_address = %s
        """ if self.db.db_type == 'postgresql' else """
        UPDATE provisioned_devices 
        SET last_provisioned = ?
        WHERE mac_address = ?
        """
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
        query = """
        UPDATE provisioned_devices 
        SET static_ip = %s, updated_at = %s
        WHERE mac_address = %s
        """ if self.db.db_type == 'postgresql' else """
        UPDATE provisioned_devices 
        SET static_ip = ?, updated_at = ?
        WHERE mac_address = ?
        """
        return self.db.execute(query, (static_ip, datetime.now(), mac_address))
