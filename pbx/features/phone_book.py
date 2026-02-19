"""
Phone Book Feature
Provides a centralized phone directory that syncs with Active Directory
and can be pushed to IP phones
"""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger

# Import ExtensionDB for database-based AD sync
try:
    from pbx.utils.database import ExtensionDB

    EXTENSION_DB_AVAILABLE = True
except ImportError:
    EXTENSION_DB_AVAILABLE = False


class PhoneBook:
    """
    Centralized phone directory system

    Manages a phone book that:
    - Stores extension names and numbers
    - Syncs automatically from Active Directory
    - Can be exported in various formats for IP phones
    - Provides API access for management
    """

    def __init__(self, config: dict, database: Any | None = None) -> None:
        """
        Initialize phone book

        Args:
            config: Configuration dictionary
            database: Optional DatabaseBackend instance
        """
        self.logger = get_logger()
        self.config = config
        self.database = database
        self.enabled = config.get("features.phone_book.enabled", False)
        self.auto_sync_from_ad = config.get("features.phone_book.auto_sync_from_ad", True)

        # In-memory cache for quick access
        self.entries = {}  # {extension: entry}

        if self.enabled:
            self.logger.info("Phone book feature enabled")
            if self.auto_sync_from_ad:
                self.logger.info("Phone book will auto-sync from Active Directory")

            # Initialize database table if using database
            if database and database.enabled:
                self._create_table()
                self._load_from_database()
        else:
            self.logger.info("Phone book feature disabled")

    def _create_table(self) -> None:
        """Create phone book table in database"""
        if not self.database or not self.database.enabled:
            return False

        self.logger.info("Creating phone_book table...")

        table_sql = (
            """
        CREATE TABLE IF NOT EXISTS phone_book (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            department VARCHAR(100),
            email VARCHAR(255),
            mobile VARCHAR(50),
            office_location VARCHAR(100),
            ad_synced BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS phone_book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            department VARCHAR(100),
            email VARCHAR(255),
            mobile VARCHAR(50),
            office_location VARCHAR(100),
            ad_synced BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        success = self.database._execute_with_context(table_sql, "phone_book table creation")

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_pb_extension ON phone_book(extension)",
            "CREATE INDEX IF NOT EXISTS idx_pb_name ON phone_book(name)",
            "CREATE INDEX IF NOT EXISTS idx_pb_ad_synced ON phone_book(ad_synced)",
        ]

        for index_sql in indexes:
            self.database._execute_with_context(
                index_sql, "phone_book index creation", critical=False
            )

        if success:
            self.logger.info("Phone book table created successfully")

        return success

    def _load_from_database(self) -> None:
        """Load phone book entries from database"""
        if not self.database or not self.database.enabled:
            return

        try:
            query = "SELECT id, extension, name, department, email, mobile, office_location, ad_synced, created_at, updated_at FROM phone_book ORDER BY name"
            entries = self.database.fetch_all(query)

            self.entries = {}
            for entry in entries:
                self.entries[entry["extension"]] = entry

            self.logger.info(f"Loaded {len(self.entries)} phone book entries from database")
        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error loading phone book from database: {e}")

    def add_entry(
        self,
        extension: str,
        name: str,
        department: str | None = None,
        email: str | None = None,
        mobile: str | None = None,
        office_location: str | None = None,
        ad_synced: bool = False,
    ) -> bool:
        """
        Add or update a phone book entry

        Args:
            extension: Extension number
            name: Display name
            department: Department name (optional)
            email: Email address (optional)
            mobile: Mobile number (optional)
            office_location: Office location (optional)
            ad_synced: Whether this was synced from AD

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        entry = {
            "extension": extension,
            "name": name,
            "department": department,
            "email": email,
            "mobile": mobile,
            "office_location": office_location,
            "ad_synced": ad_synced,
            "updated_at": datetime.now(UTC),
        }

        # Update in-memory cache
        self.entries[extension] = entry

        # Update database if available
        if self.database and self.database.enabled:
            try:
                query = (
                    """
                INSERT INTO phone_book (extension, name, department, email, mobile,
                                       office_location, ad_synced, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (extension) DO UPDATE
                SET name = EXCLUDED.name,
                    department = EXCLUDED.department,
                    email = EXCLUDED.email,
                    mobile = EXCLUDED.mobile,
                    office_location = EXCLUDED.office_location,
                    ad_synced = EXCLUDED.ad_synced,
                    updated_at = EXCLUDED.updated_at
                """
                    if self.database.db_type == "postgresql"
                    else """
                INSERT OR REPLACE INTO phone_book (extension, name, department, email,
                                                   mobile, office_location, ad_synced, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                )

                params = (
                    extension,
                    name,
                    department,
                    email,
                    mobile,
                    office_location,
                    ad_synced,
                    datetime.now(UTC),
                )
                success = self.database.execute(query, params)

                if success:
                    self.logger.info(f"Added/updated phone book entry: {extension} - {name}")
                return success
            except sqlite3.Error as e:
                self.logger.error(f"Error saving phone book entry: {e}")
                return False

        return True

    def remove_entry(self, extension: str) -> bool:
        """
        Remove a phone book entry

        Args:
            extension: Extension number

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        # Remove from cache
        if extension in self.entries:
            del self.entries[extension]

        # Remove from database
        if self.database and self.database.enabled:
            query = (
                "DELETE FROM phone_book WHERE extension = %s"
                if self.database.db_type == "postgresql"
                else "DELETE FROM phone_book WHERE extension = ?"
            )
            return self.database.execute(query, (extension,))

        return True

    def get_entry(self, extension: str) -> dict | None:
        """
        Get a phone book entry

        Args:
            extension: Extension number

        Returns:
            dict: Entry data or None
        """
        if not self.enabled:
            return None

        return self.entries.get(extension)

    def get_all_entries(self) -> list[dict]:
        """
        Get all phone book entries

        Returns:
            list: list of entry dictionaries
        """
        if not self.enabled:
            return []

        return sorted(self.entries.values(), key=lambda x: x["name"])

    def search(self, query: str, max_results: int = 50) -> list[dict]:
        """
        Search phone book entries

        Args:
            query: Search query (name, extension, department)
            max_results: Maximum number of results

        Returns:
            list: Matching entries
        """
        if not self.enabled:
            return []

        query_lower = query.lower()
        results = []

        for entry in self.entries.values():
            if (
                query_lower in entry["name"].lower()
                or query_lower in entry["extension"]
                or (entry.get("department") and query_lower in entry["department"].lower())
            ):
                results.append(entry)
                if len(results) >= max_results:
                    break

        return results

    def sync_from_ad(self, ad_integration: Any, extension_registry: str) -> int:
        """
        Sync phone book from Active Directory

        Args:
            ad_integration: ActiveDirectoryIntegration instance
            extension_registry: ExtensionRegistry instance

        Returns:
            int: Number of entries synced
        """
        if not self.enabled or not self.auto_sync_from_ad:
            return 0

        if not ad_integration or not ad_integration.enabled:
            self.logger.warning("Active Directory integration not available for phone book sync")
            return 0

        self.logger.info("Syncing phone book from Active Directory...")

        synced_count = 0

        # Try to pull from extensions database table first (preferred method)
        # This is the active source that pulls from AD and has the most
        # up-to-date data
        if self.database and self.database.enabled and EXTENSION_DB_AVAILABLE:
            try:
                ext_db = ExtensionDB(self.database)

                # Get all AD-synced extensions from the extensions database
                # table
                ad_extensions = ext_db.get_ad_synced()

                self.logger.info(f"Found {len(ad_extensions)} AD-synced extensions in database")

                for ext_data in ad_extensions:
                    success = self.add_entry(
                        extension=ext_data["number"],
                        name=ext_data["name"],
                        email=ext_data.get("email"),
                        ad_synced=True,
                    )
                    if success:
                        synced_count += 1

                self.logger.info(
                    f"Synced {synced_count} entries from Active Directory (via extensions database)"
                )
                return synced_count

            except (KeyError, TypeError, ValueError) as e:
                # Broad exception catch is intentional - we want to gracefully fall back to
                # extension_registry for ANY database issue (connection,
                # permissions, missing table, etc.)
                self.logger.error(
                    f"Error syncing from extensions database: {type(e).__name__}: {e}"
                )
                self.logger.info("Falling back to extension registry...")

        # Fallback to extension registry (for systems not using database)
        all_extensions = extension_registry.get_all()

        for ext in all_extensions:
            # Only sync AD-synced extensions
            if ext.config.get("ad_synced", False):
                success = self.add_entry(
                    extension=ext.number,
                    name=ext.name,
                    email=ext.config.get("email"),
                    ad_synced=True,
                )
                if success:
                    synced_count += 1

        self.logger.info(
            f"Synced {synced_count} entries from Active Directory (via extension registry)"
        )
        return synced_count

    def export_xml(self) -> str:
        """
        Export phone book as XML (Yealink format)

        Returns:
            str: XML formatted phone book
        """
        if not self.enabled:
            return ""

        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append("<YealinkIPPhoneDirectory>")
        xml_lines.append("  <Title>Company Directory</Title>")

        for entry in sorted(self.entries.values(), key=lambda x: x["name"]):
            xml_lines.append("  <DirectoryEntry>")
            xml_lines.append(f"    <Name>{self._xml_escape(entry['name'])}</Name>")
            xml_lines.append(f"    <Telephone>{self._xml_escape(entry['extension'])}</Telephone>")
            xml_lines.append("  </DirectoryEntry>")

        xml_lines.append("</YealinkIPPhoneDirectory>")
        return "\n".join(xml_lines)

    def export_cisco_xml(self) -> str:
        """
        Export phone book as Cisco XML format

        Returns:
            str: XML formatted phone book for Cisco phones
        """
        if not self.enabled:
            return ""

        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append("<CiscoIPPhoneDirectory>")
        xml_lines.append("  <Title>Company Directory</Title>")
        xml_lines.append("  <Prompt>Select a contact</Prompt>")

        for entry in sorted(self.entries.values(), key=lambda x: x["name"]):
            xml_lines.append("  <DirectoryEntry>")
            xml_lines.append(f"    <Name>{self._xml_escape(entry['name'])}</Name>")
            xml_lines.append(f"    <Telephone>{self._xml_escape(entry['extension'])}</Telephone>")
            xml_lines.append("  </DirectoryEntry>")

        xml_lines.append("</CiscoIPPhoneDirectory>")
        return "\n".join(xml_lines)

    def export_json(self) -> str:
        """
        Export phone book as JSON

        Returns:
            str: JSON formatted phone book
        """
        if not self.enabled:
            return "[]"

        entries = sorted(self.entries.values(), key=lambda x: x["name"])
        return json.dumps(entries, indent=2, default=str)

    def _xml_escape(self, text: str) -> str:
        """Escape text for XML"""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
