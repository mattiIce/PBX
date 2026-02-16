"""
Extension management and registry
"""

from datetime import UTC, datetime

from pbx.utils.encryption import get_encryption
from pbx.utils.logger import get_logger


class Extension:
    """Represents a registered extension"""

    def __init__(self, number: str, name: str, config: str) -> None:
        """
        Initialize extension

        Args:
            number: Extension number
            name: Display name
            config: Extension configuration dict
        """
        self.number = number
        self.name = name
        self.config = config
        self.registered = False
        self.address = None
        self.registration_time = None

    def register(self, address):
        """
        Register extension

        Args:
            address: Network address (host, port)
        """
        self.registered = True
        self.address = address
        self.registration_time = datetime.now(UTC)

    def unregister(self):
        """Unregister extension"""
        self.registered = False
        self.address = None
        self.registration_time = None

    def __str__(self):
        status = "registered" if self.registered else "unregistered"
        return f"Extension {self.number} ({self.name}) - {status}"


class ExtensionRegistry:
    """Registry of all extensions"""

    def __init__(self, config, database=None) -> None:
        """
        Initialize extension registry

        Args:
            config: Config object
            database: Optional DatabaseBackend instance (for loading from database)
        """
        self.config = config
        self.database = database
        self.logger = get_logger()
        self.extensions = {}

        # Initialize encryption for FIPS-compliant password handling
        fips_mode = config.get("security.fips_mode", False)
        self.encryption = get_encryption(fips_mode)

        # Load extensions (from database if available, otherwise from config)
        self._load_extensions()

    @staticmethod
    def create_extension_from_db(db_extension):
        """
        Create an Extension object from database data

        Args:
            db_extension: Dictionary containing extension data from database

        Returns:
            Extension object
        """
        number = db_extension["number"]
        name = db_extension["name"]

        # Create config dict from database data
        # Note: SQLite stores booleans as 0/1, so we need to convert them
        ext_config = {
            "number": number,
            "name": name,
            "email": db_extension.get("email", ""),
            "password_hash": db_extension.get("password_hash", ""),
            "allow_external": bool(db_extension.get("allow_external", True)),
            "voicemail_pin_hash": db_extension.get("voicemail_pin_hash", ""),
            "ad_synced": bool(db_extension.get("ad_synced", False)),
            "is_admin": bool(db_extension.get("is_admin", False)),
        }

        return Extension(number, name, ext_config)

    def _load_extensions(self):
        """Load extensions from database only (for security)"""
        # SECURITY: Extensions must be loaded from database only.
        # Loading from config.yml is insecure as it exposes passwords in plain
        # text.
        if not self.database or not self.database.enabled:
            self.logger.error(
                "Database is not enabled. Extensions can only be loaded from database."
            )
            self.logger.error(
                "Please enable database in config.yml and run: python scripts/init_database.py"
            )
            self.logger.error(
                "Then add extensions using the admin panel or: python scripts/migrate_extensions_to_db.py"
            )
            return

        try:
            from pbx.utils.database import ExtensionDB

            ext_db = ExtensionDB(self.database)
            db_extensions = ext_db.get_all()

            if db_extensions:
                self.logger.info(f"Loading {len(db_extensions)} extensions from database")
                for ext_data in db_extensions:
                    number = ext_data["number"]
                    name = ext_data["name"]

                    # Create Extension object from database data using helper
                    # method
                    extension = self.create_extension_from_db(ext_data)
                    self.extensions[number] = extension

                    ad_marker = " [AD]" if ext_data.get("ad_synced") else ""
                    self.logger.info(f"Loaded extension {number} ({name}){ad_marker}")
            else:
                self.logger.warning("No extensions found in database")
                self.logger.warning(
                    "Add extensions using the admin panel or run: python scripts/migrate_extensions_to_db.py"
                )
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error loading extensions from database: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    def reload(self):
        """Reload extensions from database or configuration"""
        if not self.database or not self.database.enabled:
            # Only reload config if not using database
            self.config.load()
        self.extensions.clear()
        self._load_extensions()

    def reload_extensions(self):
        """Alias for reload() - reload extensions from database or configuration"""
        self.reload()

    def get(self, number: str):
        """
        Get extension by number

        Args:
            number: Extension number

        Returns:
            Extension object or None
        """
        return self.extensions.get(str(number))

    def get_extension(self, number: str):
        """
        Get extension by number (alias for get() for backward compatibility)

        Args:
            number: Extension number

        Returns:
            Extension object or None
        """
        return self.get(number)

    def register(self, number: str, address) -> bool:
        """
        Register extension

        Args:
            number: Extension number
            address: Network address

        Returns:
            True if registered successfully
        """
        extension = self.get(number)
        if extension:
            extension.register(address)
            # Logging is handled by the caller (pbx.py) to avoid duplicate logs
            return True
        return False

    def unregister(self, number: str) -> bool:
        """
        Unregister extension

        Args:
            number: Extension number

        Returns:
            True if unregistered successfully
        """
        extension = self.get(number)
        if extension:
            extension.unregister()
            self.logger.info(f"Extension {number} unregistered")
            return True
        return False

    def is_registered(self, number: str) -> bool:
        """
        Check if extension is registered

        Args:
            number: Extension number

        Returns:
            True if registered
        """
        extension = self.get(number)
        return extension.registered if extension else False

    def get_registered(self) -> list:
        """
        Get all registered extensions

        Returns:
            list of registered Extension objects
        """
        return [ext for ext in self.extensions.values() if ext.registered]

    def get_registered_count(self):
        """Get count of registered extensions"""
        return len(self.get_registered())

    def get_all(self):
        """Get all extensions"""
        return list(self.extensions.values())

    def authenticate(self, number: str, password: str) -> bool:
        """
        Authenticate extension using FIPS-compliant password verification

        Args:
            number: Extension number
            password: Password

        Returns:
            True if authenticated
        """
        extension = self.get(number)
        if extension:
            config_password = extension.config.get("password")

            # Check if password is already hashed (contains salt)
            password_hash = extension.config.get("password_hash")
            password_salt = extension.config.get("password_salt")

            if password_hash and password_salt:
                # Use FIPS-compliant verification
                try:
                    return self.encryption.verify_password(password, password_hash, password_salt)
                except Exception as e:
                    self.logger.error(f"Error verifying password: {e}")
                    return False
            else:
                # Fallback to plain text comparison (not recommended for production)
                # Use constant-time comparison to prevent timing attacks
                self.logger.warning(
                    f"Extension {number} using plain text password - "
                    "consider migrating to hashed passwords"
                )
                import secrets

                if isinstance(password, str):
                    password = password.encode("utf-8")
                if isinstance(config_password, str):
                    config_password = config_password.encode("utf-8")
                return secrets.compare_digest(password, config_password)
        return False

    def hash_extension_password(self, number: str, password: str) -> bool:
        """
        Hash an extension's password using FIPS-compliant algorithm

        Args:
            number: Extension number
            password: Plain text password

        Returns:
            True if successful
        """
        extension = self.get(number)
        if extension:
            password_hash, password_salt = self.encryption.hash_password(password)
            extension.config["password_hash"] = password_hash
            extension.config["password_salt"] = password_salt
            self.logger.info(f"Hashed password for extension {number}")
            return True
        return False
