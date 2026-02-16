"""
Auto Attendant (IVR) System for PBX
Provides automated call answering and menu navigation
"""

import contextlib
import sqlite3
import time
from enum import Enum
from pathlib import Path
from typing import Any

from pbx.utils.logger import get_logger


class AAState(Enum):
    """Auto Attendant states"""

    WELCOME = "welcome"
    MAIN_MENU = "main_menu"
    SUBMENU = "submenu"
    TRANSFERRING = "transferring"
    INVALID = "invalid"
    TIMEOUT = "timeout"
    ENDED = "ended"


class DestinationType(Enum):
    """Destination types for menu options"""

    EXTENSION = "extension"
    SUBMENU = "submenu"
    QUEUE = "queue"
    VOICEMAIL = "voicemail"
    OPERATOR = "operator"


class AutoAttendant:
    """
    Auto Attendant system that answers calls and provides menu options

    Features:
    - Welcome greeting
    - Menu options (press 1 for sales, 2 for support, etc.)
    - DTMF input handling
    - Call transfer to extensions/queues
    - Timeout handling
    - Database persistence for configuration
    """

    def __init__(self, config: Any | None = None, pbx_core: Any | None = None) -> None:
        """
        Initialize Auto Attendant

        Args:
            config: Configuration object
            pbx_core: Reference to PBX core for call transfers
        """
        self.logger = get_logger()
        self.config = config
        self.pbx_core = pbx_core

        # Database connection
        self.db_path = config.get("database", {}).get("path", "pbx.db") if config else "pbx.db"
        self._init_database()

        # Get auto attendant configuration - try database first, then config file
        aa_config = config.get("auto_attendant", {}) if config else {}

        # Load from database if available, otherwise use config defaults
        db_config = self._load_config_from_db()
        if db_config:
            self.enabled = db_config.get("enabled", True)
            self.extension = db_config.get("extension", "0")
            self.timeout = db_config.get("timeout", 10)
            self.max_retries = db_config.get("max_retries", 3)
            self.audio_path = db_config.get("audio_path", "auto_attendant")
        else:
            # Use config file defaults and save to database
            self.enabled = aa_config.get("enabled", True)
            self.extension = aa_config.get("extension", "0")
            self.timeout = aa_config.get("timeout", 10)
            self.max_retries = aa_config.get("max_retries", 3)
            self.audio_path = aa_config.get("audio_path", "auto_attendant")
            self._save_config_to_db()

        # Menu options mapping - load from database
        self.menu_options = {}
        self._load_menu_options_from_db()

        # If no menu options in database, load from config and save
        if not self.menu_options:
            menu_items = aa_config.get("menu_options", [])
            for item in menu_items:
                digit = str(item.get("digit"))
                destination = item.get("destination")
                description = item.get("description", "")
                self.menu_options[digit] = {"destination": destination, "description": description}
            # Save to database
            if self.menu_options:
                for digit, option in self.menu_options.items():
                    self._save_menu_option_to_db(
                        digit, option["destination"], option["description"]
                    )

        # Create audio directory if it doesn't exist
        if not Path(self.audio_path).exists():
            Path(self.audio_path).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created auto attendant audio directory: {self.audio_path}")

        self.logger.info(f"Auto Attendant initialized on extension {self.extension}")
        self.logger.info(f"Menu options: {len(self.menu_options)}")

    def _init_database(self) -> None:
        """Initialize database tables for auto attendant persistence"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create auto_attendant_config table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_attendant_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled BOOLEAN DEFAULT 1,
                    extension TEXT DEFAULT '0',
                    timeout INTEGER DEFAULT 10,
                    max_retries INTEGER DEFAULT 3,
                    audio_path TEXT DEFAULT 'auto_attendant',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create auto_attendant_menu_options table (legacy - kept for backward compatibility)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_attendant_menu_options (
                    digit TEXT PRIMARY KEY,
                    destination TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create new hierarchical menu structure tables
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_attendant_menus (
                    menu_id TEXT PRIMARY KEY,
                    parent_menu_id TEXT,
                    menu_name TEXT NOT NULL,
                    prompt_text TEXT,
                    audio_file TEXT,
                    timeout INTEGER DEFAULT 10,
                    max_retries INTEGER DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_menu_id) REFERENCES auto_attendant_menus(menu_id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_attendant_menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    menu_id TEXT NOT NULL,
                    digit TEXT NOT NULL,
                    destination_type TEXT NOT NULL DEFAULT 'extension',
                    destination_value TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (menu_id) REFERENCES auto_attendant_menus(menu_id) ON DELETE CASCADE,
                    UNIQUE(menu_id, digit)
                )
            """
            )

            # Check if main menu exists, if not create it
            cursor.execute("SELECT COUNT(*) FROM auto_attendant_menus WHERE menu_id = 'main'")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    INSERT INTO auto_attendant_menus (menu_id, parent_menu_id, menu_name, prompt_text)
                    VALUES ('main', NULL, 'Main Menu', 'Main menu options')
                """
                )

            # Migrate legacy menu options to new structure if they exist
            cursor.execute("SELECT COUNT(*) FROM auto_attendant_menu_options")
            legacy_count = cursor.fetchone()[0]

            if legacy_count > 0:
                # Check if already migrated
                cursor.execute(
                    "SELECT COUNT(*) FROM auto_attendant_menu_items WHERE menu_id = 'main'"
                )
                migrated_count = cursor.fetchone()[0]

                if migrated_count == 0:
                    self.logger.info(
                        f"Migrating {legacy_count} legacy menu options to new structure"
                    )
                    cursor.execute(
                        """
                        INSERT INTO auto_attendant_menu_items (menu_id, digit, destination_type, destination_value, description)
                        SELECT 'main', digit, 'extension', destination, description
                        FROM auto_attendant_menu_options
                    """
                    )
                    self.logger.info("Legacy menu options migrated successfully")

            conn.commit()
            conn.close()
            self.logger.info("Auto attendant database tables initialized")
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing auto attendant database: {e}")

    def _load_config_from_db(self) -> dict | None:
        """Load configuration from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT enabled, extension, timeout, max_retries, audio_path FROM auto_attendant_config WHERE id = 1"
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "enabled": bool(row[0]),
                    "extension": row[1],
                    "timeout": row[2],
                    "max_retries": row[3],
                    "audio_path": row[4],
                }
            return None
        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error loading auto attendant config from database: {e}")
            return None

    def _save_config_to_db(self) -> None:
        """Save configuration to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Use INSERT OR REPLACE to handle both insert and update
            cursor.execute(
                """
                INSERT OR REPLACE INTO auto_attendant_config (id, enabled, extension, timeout, max_retries, audio_path, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (self.enabled, self.extension, self.timeout, self.max_retries, self.audio_path),
            )

            conn.commit()
            conn.close()
            self.logger.info("Auto attendant config saved to database")
        except sqlite3.Error as e:
            self.logger.error(f"Error saving auto attendant config to database: {e}")

    def _load_menu_options_from_db(self) -> None:
        """Load menu options from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT digit, destination, description FROM auto_attendant_menu_options"
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                self.menu_options[row[0]] = {"destination": row[1], "description": row[2] or ""}

            if rows:
                self.logger.info(f"Loaded {len(rows)} menu options from database")
        except sqlite3.Error as e:
            self.logger.error(f"Error loading menu options from database: {e}")

    def _save_menu_option_to_db(self, digit: str, destination: str, description: str = "") -> None:
        """Save a menu option to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO auto_attendant_menu_options (digit, destination, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (digit, destination, description),
            )

            conn.commit()
            conn.close()
            self.logger.info(f"Menu option {digit} saved to database")
        except sqlite3.Error as e:
            self.logger.error(f"Error saving menu option to database: {e}")

    def _delete_menu_option_from_db(self, digit: str) -> None:
        """Delete a menu option from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auto_attendant_menu_options WHERE digit = ?", (digit,))
            conn.commit()
            conn.close()
            self.logger.info(f"Menu option {digit} deleted from database")
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting menu option from database: {e}")

    def update_config(self, **kwargs) -> None:
        """Update configuration and persist to database"""
        if "enabled" in kwargs:
            self.enabled = bool(kwargs["enabled"])
        if "extension" in kwargs:
            self.extension = str(kwargs["extension"])
        if "timeout" in kwargs:
            self.timeout = int(kwargs["timeout"])
        if "max_retries" in kwargs:
            self.max_retries = int(kwargs["max_retries"])
        if "audio_path" in kwargs:
            self.audio_path = str(kwargs["audio_path"])

        # Save to database
        self._save_config_to_db()

    def add_menu_option(self, digit: str, destination: str, description: str = "") -> bool:
        """Add or update a menu option and persist to database"""
        if not self.enabled:
            self.logger.error("Cannot add menu option: Auto attendant feature is not enabled")
            return False

        self.menu_options[digit] = {"destination": destination, "description": description}
        self._save_menu_option_to_db(digit, destination, description)
        return True

    def remove_menu_option(self, digit: str) -> bool:
        """Remove a menu option and delete from database"""
        if not self.enabled:
            self.logger.error("Cannot remove menu option: Auto attendant feature is not enabled")
            return False

        if digit in self.menu_options:
            del self.menu_options[digit]
            self._delete_menu_option_from_db(digit)
            return True
        return False

    def is_enabled(self) -> bool:
        """Check if auto attendant is enabled"""
        return self.enabled

    def get_extension(self) -> str:
        """Get the auto attendant extension number"""
        return self.extension

    # ============================================================================
    # Submenu Management Methods
    # ============================================================================

    def create_menu(
        self,
        menu_id: str,
        parent_menu_id: str,
        menu_name: str,
        prompt_text: str = "",
        audio_file: str | None = None,
    ) -> bool:
        """
        Create a new menu (or submenu)

        Args:
            menu_id: Unique identifier for this menu
            parent_menu_id: ID of parent menu (None for top-level)
            menu_name: Display name for the menu
            prompt_text: Text for voice prompt
            audio_file: Optional custom audio file path

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate menu depth to prevent infinite nesting
            if parent_menu_id:
                parent_depth = self._get_menu_depth(parent_menu_id)
                new_depth = parent_depth + 1
                if new_depth >= 5:  # Max 5 levels (main=0, level1=1, level2=2, level3=3, level4=4)
                    self.logger.error("Cannot create menu: maximum depth (5) exceeded")
                    return False

            # Check for circular references
            if parent_menu_id and self._would_create_circular_reference(menu_id, parent_menu_id):
                self.logger.error("Cannot create menu: would create circular reference")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO auto_attendant_menus
                (menu_id, parent_menu_id, menu_name, prompt_text, audio_file)
                VALUES (?, ?, ?, ?, ?)
            """,
                (menu_id, parent_menu_id, menu_name, prompt_text, audio_file),
            )

            conn.commit()
            conn.close()
            self.logger.info(f"Created menu '{menu_id}' under parent '{parent_menu_id}'")
            return True
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Menu '{menu_id}' already exists: {e}")
            return False
        except sqlite3.Error as e:
            self.logger.error(f"Error creating menu: {e}")
            return False

    def update_menu(
        self,
        menu_id: str,
        menu_name: str | None = None,
        prompt_text: str | None = None,
        audio_file: str | None = None,
    ) -> bool:
        """
        Update an existing menu

        Args:
            menu_id: Menu to update
            menu_name: New name (optional)
            prompt_text: New prompt text (optional)
            audio_file: New audio file (optional)

        Returns:
            bool: True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            updates = []
            params = []

            if menu_name is not None:
                updates.append("menu_name = ?")
                params.append(menu_name)
            if prompt_text is not None:
                updates.append("prompt_text = ?")
                params.append(prompt_text)
            if audio_file is not None:
                updates.append("audio_file = ?")
                params.append(audio_file)

            if not updates:
                return True  # Nothing to update

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(menu_id)

            # Field names are hardcoded constants; all values use parameterized placeholders in params list
            cursor.execute(
                f"UPDATE auto_attendant_menus SET {', '.join(updates)} WHERE menu_id = ?",  # nosec B608
                params,
            )

            conn.commit()
            conn.close()
            self.logger.info(f"Updated menu '{menu_id}'")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error updating menu: {e}")
            return False

    def delete_menu(self, menu_id: str) -> bool:
        """
        Delete a menu and all its items (CASCADE)

        Args:
            menu_id: Menu to delete

        Returns:
            bool: True if successful
        """
        try:
            if menu_id == "main":
                self.logger.error("Cannot delete main menu")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if any menu items reference this as a submenu destination
            cursor.execute(
                """
                SELECT COUNT(*) FROM auto_attendant_menu_items
                WHERE destination_type = 'submenu' AND destination_value = ?
            """,
                (menu_id,),
            )
            referencing_count = cursor.fetchone()[0]

            if referencing_count > 0:
                self.logger.error(
                    f"Cannot delete menu '{menu_id}': {referencing_count} items reference it"
                )
                conn.close()
                return False

            # Delete menu (CASCADE will delete items)
            cursor.execute("DELETE FROM auto_attendant_menus WHERE menu_id = ?", (menu_id,))

            conn.commit()
            conn.close()
            self.logger.info(f"Deleted menu '{menu_id}'")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting menu: {e}")
            return False

    def get_menu(self, menu_id: str) -> dict:
        """
        Get menu details

        Args:
            menu_id: Menu identifier

        Returns:
            dict: Menu details or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT menu_id, parent_menu_id, menu_name, prompt_text, audio_file,
                       timeout, max_retries, created_at, updated_at
                FROM auto_attendant_menus WHERE menu_id = ?
            """,
                (menu_id,),
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "menu_id": row[0],
                    "parent_menu_id": row[1],
                    "menu_name": row[2],
                    "prompt_text": row[3],
                    "audio_file": row[4],
                    "timeout": row[5],
                    "max_retries": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                }
            return None
        except sqlite3.Error as e:
            self.logger.error(f"Error getting menu: {e}")
            return None

    def list_menus(self) -> list:
        """
        list all menus

        Returns:
            list: list of menu dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT menu_id, parent_menu_id, menu_name, prompt_text, audio_file
                FROM auto_attendant_menus ORDER BY menu_id
            """
            )
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "menu_id": row[0],
                    "parent_menu_id": row[1],
                    "menu_name": row[2],
                    "prompt_text": row[3],
                    "audio_file": row[4],
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"Error listing menus: {e}")
            return []

    def add_menu_item(
        self,
        menu_id: str,
        digit: str,
        destination_type: str,
        destination_value: str,
        description: str = "",
    ) -> bool:
        """
        Add item to a menu

        Args:
            menu_id: Menu to add item to
            digit: DTMF digit (0-9, *, #)
            destination_type: type from DestinationType enum
            destination_value: Extension, menu_id, etc.
            description: Human-readable description

        Returns:
            bool: True if successful
        """
        try:
            # Validate destination type
            valid_types = [dt.value for dt in DestinationType]
            if destination_type not in valid_types:
                self.logger.error(f"Invalid destination type: {destination_type}")
                return False

            # If submenu, verify it exists
            if destination_type == "submenu" and not self.get_menu(destination_value):
                self.logger.error(f"Submenu '{destination_value}' does not exist")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO auto_attendant_menu_items
                (menu_id, digit, destination_type, destination_value, description, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (menu_id, digit, destination_type, destination_value, description),
            )

            conn.commit()
            conn.close()
            self.logger.info(f"Added menu item {digit} to menu '{menu_id}'")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding menu item: {e}")
            return False

    def remove_menu_item(self, menu_id: str, digit: str) -> bool:
        """
        Remove item from a menu

        Args:
            menu_id: Menu to remove item from
            digit: DTMF digit to remove

        Returns:
            bool: True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM auto_attendant_menu_items WHERE menu_id = ? AND digit = ?",
                (menu_id, digit),
            )
            conn.commit()
            conn.close()
            self.logger.info(f"Removed menu item {digit} from menu '{menu_id}'")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error removing menu item: {e}")
            return False

    def get_menu_items(self, menu_id: str) -> list:
        """
        Get all items for a menu

        Args:
            menu_id: Menu identifier

        Returns:
            list: list of menu item dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT digit, destination_type, destination_value, description
                FROM auto_attendant_menu_items WHERE menu_id = ?
                ORDER BY digit
            """,
                (menu_id,),
            )
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "digit": row[0],
                    "destination_type": row[1],
                    "destination_value": row[2],
                    "description": row[3],
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            self.logger.error(f"Error getting menu items: {e}")
            return []

    def get_menu_tree(self, menu_id: str = "main", depth: int = 0) -> dict:
        """
        Get complete menu hierarchy as a tree

        Args:
            menu_id: Starting menu (default: main)
            depth: Current depth (for recursion)

        Returns:
            dict: Menu tree structure
        """
        if depth > 10:  # Prevent infinite recursion
            return None

        menu = self.get_menu(menu_id)
        if not menu:
            return None

        menu["items"] = []
        items = self.get_menu_items(menu_id)

        for item in items:
            item_copy = item.copy()
            # If this item points to a submenu, recursively get that submenu
            if item["destination_type"] == "submenu":
                submenu = self.get_menu_tree(item["destination_value"], depth + 1)
                if submenu:
                    item_copy["submenu"] = submenu
            menu["items"].append(item_copy)

        return menu

    def _get_menu_depth(self, menu_id: str, current_depth: int = 0) -> int:
        """
        Calculate depth of a menu in the hierarchy

        Args:
            menu_id: Menu to check
            current_depth: Current recursion depth

        Returns:
            int: Depth level (0 = top level, e.g., main menu)
        """
        if current_depth > 10:  # Safety limit
            return current_depth

        menu = self.get_menu(menu_id)
        if not menu or not menu["parent_menu_id"]:
            return current_depth

        return self._get_menu_depth(menu["parent_menu_id"], current_depth + 1)

    def _would_create_circular_reference(self, menu_id: str, parent_menu_id: str) -> bool:
        """
        Check if setting parent would create circular reference

        Args:
            menu_id: Menu being created/updated
            parent_menu_id: Proposed parent

        Returns:
            bool: True if would create circular reference
        """
        if parent_menu_id == menu_id:
            return True

        # Walk up the parent chain
        current = parent_menu_id
        visited = set()
        while current:
            if current == menu_id:
                return True
            if current in visited:  # Already circular
                return True
            visited.add(current)

            menu = self.get_menu(current)
            if not menu:
                break
            current = menu["parent_menu_id"]

        return False

    def start_session(self, call_id: str, from_extension: str) -> dict:
        """
        Start an auto attendant session for a call

        Args:
            call_id: Call identifier
            from_extension: Calling extension

        Returns:
            dict: Initial action with audio file to play
        """
        self.logger.info(
            f"Starting auto attendant session for call {call_id} from {from_extension}"
        )

        # Initialize session state - start in MAIN_MENU to accept DTMF input
        session = {
            "state": AAState.MAIN_MENU,
            "call_id": call_id,
            "from_extension": from_extension,
            "retry_count": 0,
            "last_input_time": time.time(),
            "current_menu_id": "main",  # Track current menu
            "menu_stack": [],  # Navigation history for "go back"
        }

        # Return welcome greeting action
        return {
            "action": "play",
            "file": self._get_audio_file("welcome"),
            "next_state": AAState.MAIN_MENU,
            "session": session,
        }

    def handle_dtmf(self, session: dict, digit: str) -> dict:
        """
        Handle DTMF input during auto attendant session

        Args:
            session: Current session state
            digit: DTMF digit pressed

        Returns:
            dict: Action to take (play audio, transfer, etc.)
        """
        current_state = session.get("state")
        self.logger.debug(f"Auto Attendant DTMF: {digit} in state {current_state}")

        # Update input time
        session["last_input_time"] = time.time()

        # Special digits for navigation (only if not configured as menu options)
        if current_state in (AAState.MAIN_MENU, AAState.SUBMENU):
            # Check if digit is a configured menu option first
            current_menu_id = session.get("current_menu_id", "main")
            menu_items = self.get_menu_items(current_menu_id)
            is_menu_option = any(item["digit"] == digit for item in menu_items)

            # Also check legacy menu_options
            if not is_menu_option and digit in self.menu_options:
                is_menu_option = True

            # If not a menu option, check for special navigation keys
            if not is_menu_option:
                if digit in {"*", "9"}:
                    # Go back to previous menu
                    return self._handle_go_back(session)
                if digit == "#":
                    # Repeat current menu
                    return self._handle_repeat_menu(session)

            # Handle menu input
            return self._handle_menu_input(session, digit)

        if current_state == AAState.INVALID:
            # After invalid input, any key returns to menu
            current_menu_id = session.get("current_menu_id", "main")
            session["state"] = AAState.MAIN_MENU if current_menu_id == "main" else AAState.SUBMENU
            menu_type = "main_menu" if current_menu_id == "main" else current_menu_id
            return {
                "action": "play",
                "file": self._get_audio_file(menu_type),
                "session": session,
            }

        # Default: invalid input
        return self._handle_invalid_input(session)

    def handle_timeout(self, session: dict) -> dict:
        """
        Handle timeout (no input received)

        Args:
            session: Current session state

        Returns:
            dict: Action to take
        """
        self.logger.warning(f"Auto attendant timeout for call {session.get('call_id')}")

        session["retry_count"] += 1

        if session["retry_count"] >= self.max_retries:
            # Too many retries, transfer to operator or disconnect
            session["state"] = AAState.ENDED
            operator_ext = self.config.get("auto_attendant.operator_extension", "1001")

            return {
                "action": "transfer",
                "destination": operator_ext,
                "reason": "timeout",
                "session": session,
            }

        # Play timeout message and return to menu
        session["state"] = AAState.MAIN_MENU
        return {"action": "play", "file": self._get_audio_file("timeout"), "session": session}

    def _handle_menu_input(self, session: dict, digit: str) -> dict:
        """
        Handle menu input (supports both legacy and new hierarchical menus)

        Args:
            session: Current session
            digit: DTMF digit

        Returns:
            dict: Action to take
        """
        current_menu_id = session.get("current_menu_id", "main")

        # Try new hierarchical menu structure first
        menu_items = self.get_menu_items(current_menu_id)

        for item in menu_items:
            if item["digit"] == digit:
                dest_type = item["destination_type"]
                dest_value = item["destination_value"]

                self.logger.info(
                    f"Auto attendant: Menu '{current_menu_id}' digit {digit} -> {dest_type}: {dest_value}"
                )

                # Handle based on destination type
                if dest_type == "submenu":
                    # Navigate to submenu
                    return self._navigate_to_submenu(session, dest_value)

                if dest_type in ["extension", "queue", "operator"]:
                    # Transfer to destination
                    session["state"] = AAState.TRANSFERRING
                    return {"action": "transfer", "destination": dest_value, "session": session}

                if dest_type == "voicemail":
                    # Transfer to voicemail
                    session["state"] = AAState.TRANSFERRING
                    return {
                        "action": "voicemail",
                        "mailbox": dest_value,
                        "session": session,
                    }

        # Fall back to legacy menu_options (for backward compatibility)
        if digit in self.menu_options:
            option = self.menu_options[digit]
            destination = option["destination"]

            self.logger.info(f"Auto attendant: transferring to {destination} (legacy)")
            session["state"] = AAState.TRANSFERRING

            return {"action": "transfer", "destination": destination, "session": session}

        # Invalid option
        return self._handle_invalid_input(session)

    def _navigate_to_submenu(self, session: dict, submenu_id: str) -> dict:
        """
        Navigate to a submenu

        Args:
            session: Current session
            submenu_id: ID of submenu to navigate to

        Returns:
            dict: Action to play submenu prompt
        """
        current_menu_id = session.get("current_menu_id", "main")

        # Save current menu to navigation stack
        if "menu_stack" not in session:
            session["menu_stack"] = []
        session["menu_stack"].append(current_menu_id)

        # Update current menu
        session["current_menu_id"] = submenu_id
        session["state"] = AAState.SUBMENU
        session["retry_count"] = 0  # Reset retry count for new menu

        self.logger.info(f"Navigating to submenu '{submenu_id}'")

        # Get audio file for submenu
        audio_file = self._get_audio_file(submenu_id)

        return {
            "action": "play",
            "file": audio_file,
            "session": session,
        }

    def _handle_go_back(self, session: dict) -> dict:
        """
        Handle "go back" to previous menu

        Args:
            session: Current session

        Returns:
            dict: Action to play previous menu or invalid if already at main menu
        """
        menu_stack = session.get("menu_stack", [])

        if not menu_stack:
            # Already at main menu, can't go back - treat as invalid input
            self.logger.debug("Already at main menu, cannot go back - treating as invalid")
            return self._handle_invalid_input(session)

        # Pop previous menu from stack
        previous_menu_id = menu_stack.pop()
        session["menu_stack"] = menu_stack
        session["current_menu_id"] = previous_menu_id
        session["state"] = AAState.MAIN_MENU if previous_menu_id == "main" else AAState.SUBMENU
        session["retry_count"] = 0

        self.logger.info(f"Going back to menu '{previous_menu_id}'")

        menu_type = "main_menu" if previous_menu_id == "main" else previous_menu_id
        return {
            "action": "play",
            "file": self._get_audio_file(menu_type),
            "session": session,
        }

    def _handle_repeat_menu(self, session: dict) -> dict:
        """
        Repeat current menu

        Args:
            session: Current session

        Returns:
            dict: Action to replay current menu
        """
        current_menu_id = session.get("current_menu_id", "main")
        menu_type = "main_menu" if current_menu_id == "main" else current_menu_id

        self.logger.info(f"Repeating menu '{current_menu_id}'")

        return {
            "action": "play",
            "file": self._get_audio_file(menu_type),
            "session": session,
        }

    def _handle_invalid_input(self, session: dict) -> dict:
        """
        Handle invalid input

        Args:
            session: Current session

        Returns:
            dict: Action to play invalid message
        """
        session["retry_count"] += 1

        if session["retry_count"] >= self.max_retries:
            # Too many invalid attempts
            session["state"] = AAState.ENDED
            operator_ext = self.config.get("auto_attendant.operator_extension", "1001")

            return {
                "action": "transfer",
                "destination": operator_ext,
                "reason": "invalid_input",
                "session": session,
            }

        session["state"] = AAState.INVALID
        return {"action": "play", "file": self._get_audio_file("invalid"), "session": session}

    def _get_audio_file(self, prompt_type: str) -> str:
        """
        Get path to audio file for prompt

        Args:
            prompt_type: type of prompt (welcome, main_menu, invalid, menu_id, etc.)

        Returns:
            str: Path to audio file, or None if not found
        """
        # For submenu, check if there's a custom audio file in the menu record
        if prompt_type not in ["welcome", "main_menu", "invalid", "timeout", "transferring"]:
            menu = self.get_menu(prompt_type)
            if menu and menu.get("audio_file"):
                # Use custom audio file if specified
                if Path(menu["audio_file"]).exists():
                    return menu["audio_file"]

        # Try to find recorded audio file first
        wav_file = Path(self.audio_path) / f"{prompt_type}.wav"
        if Path(wav_file).exists():
            return wav_file

        # If no recorded file, we'll generate tone-based prompt
        # This will be handled by the audio utils
        self.logger.debug(f"No audio file found for {prompt_type}, will use generated prompt")
        return None

    def get_menu_text(self) -> str:
        """
        Get text description of menu options

        Returns:
            str: Text description of menu
        """
        lines = ["Auto Attendant Menu:"]
        for digit, option in sorted(self.menu_options.items()):
            lines.append(f"  Press {digit}: {option['description']}")
        return "\n".join(lines)

    def end_session(self, session: dict) -> None:
        """
        End auto attendant session

        Args:
            session: Session to end
        """
        call_id = session.get("call_id")
        self.logger.info(f"Ending auto attendant session for call {call_id}")
        session["state"] = AAState.ENDED


def generate_auto_attendant_prompts(output_dir: str = "auto_attendant") -> None:
    """
    Generate audio prompts for auto attendant

    NOTE: This function generates tone-based prompts as a fallback.
    For REAL VOICE prompts, use: scripts/generate_espeak_voices.py

    Args:
        output_dir: Directory to save audio files
    """

    from pbx.utils.audio import generate_voice_prompt

    logger = get_logger()

    logger.warning("This function generates TONE prompts (not voice).")
    logger.warning("For REAL VOICE prompts, use: python3 scripts/generate_espeak_voices.py")
    logger.warning("Continuing with tone generation...")

    # Create output directory
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {output_dir}")

    # Define prompts to generate
    prompts = {
        "welcome": "auto_attendant_welcome",
        "main_menu": "auto_attendant_menu",
        "invalid": "invalid_option",
        "timeout": "timeout",
        "transferring": "transferring",
    }

    for prompt_name, prompt_type in prompts.items():
        output_file = Path(output_dir) / f"{prompt_name}.wav"

        try:
            # Generate the prompt
            wav_data = generate_voice_prompt(prompt_type)

            # Write to file
            with open(output_file, "wb") as f:
                f.write(wav_data)

            logger.info(f"Generated {output_file}")
        except OSError as e:
            logger.error(f"Error generating {prompt_name}: {e}")

    logger.info(f"Auto attendant prompts generated in {output_dir}")
    logger.info("NOTE: These are tone-based placeholders (not real voice).")
    logger.info("For REAL VOICE, run: python3 scripts/generate_espeak_voices.py")


def generate_submenu_prompt(
    menu_id: str, prompt_text: str, output_dir: str = "auto_attendant"
) -> str:
    """
    Generate voice prompt for a submenu

    Args:
        menu_id: Menu identifier
        prompt_text: Text to convert to speech
        output_dir: Directory to save audio files

    Returns:
        str: Path to generated audio file, or None if failed
    """
    tmp_mp3_path = None
    try:
        # Try to use gTTS for voice generation
        try:
            import tempfile

            from gtts import gTTS

            logger = get_logger()

            # Create output directory if needed
            if not Path(output_dir).exists():
                Path(output_dir).mkdir(parents=True, exist_ok=True)

            output_file = Path(output_dir) / f"{menu_id}.wav"

            # Generate with gTTS
            tts = gTTS(text=prompt_text, lang="en", slow=False)

            # Save to temporary MP3 first
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
                tts.save(tmp_mp3.name)
                tmp_mp3_path = tmp_mp3.name

            # Convert MP3 to WAV using ffmpeg if available
            try:
                import subprocess

                subprocess.run(
                    [
                        "ffmpeg",
                        "-i",
                        tmp_mp3_path,
                        "-acodec",
                        "pcm_s16le",
                        "-ar",
                        "8000",
                        "-ac",
                        "1",
                        "-y",
                        output_file,
                    ],
                    check=True,
                    capture_output=True,
                )
                # Clean up temp file
                if tmp_mp3_path and Path(tmp_mp3_path).exists():
                    Path(tmp_mp3_path).unlink()
                logger.info(f"Generated submenu prompt: {output_file}")
                return output_file
            except (FileNotFoundError, subprocess.CalledProcessError):
                # ffmpeg not available, just save MP3
                import shutil

                shutil.move(tmp_mp3_path, output_file.replace(".wav", ".mp3"))
                logger.warning(f"ffmpeg not available, saved as MP3: {output_file}.mp3")
                return output_file.replace(".wav", ".mp3")

        except ImportError:
            logger = get_logger()
            logger.warning("gTTS not available for submenu prompt generation")
            return None

    except (OSError, subprocess.SubprocessError) as e:
        # Clean up temp file on error
        if tmp_mp3_path and Path(tmp_mp3_path).exists():
            with contextlib.suppress(OSError):
                Path(tmp_mp3_path).unlink()
        logger = get_logger()
        logger.error(f"Error generating submenu prompt: {e}")
        return None
