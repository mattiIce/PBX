"""
Click-to-Dial Framework
Web and application-based dialing with WebRTC integration
"""

import sqlite3
import uuid
from datetime import UTC, datetime

from pbx.utils.logger import get_logger
from typing import Any


class ClickToDialEngine:
    """
    Click-to-dial framework
    Enables dialing from web interfaces and applications
    """

    def __init__(self, db_backend: Any | None, config: dict, pbx_core: Any | None =None) -> None:
        """
        Initialize click-to-dial engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
            pbx_core: PBXCore instance (optional, for call integration)
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.pbx_core = pbx_core
        self.enabled = config.get("click_to_dial.enabled", True)

        self.logger.info("Click-to-Dial Framework initialized")

    def get_config(self, extension: str) -> dict | None:
        """
        Get click-to-dial configuration for extension

        Args:
            extension: Extension number

        Returns:
            Configuration dict or None
        """
        try:
            result = self.db.execute(
                (
                    "SELECT * FROM click_to_dial_configs WHERE extension = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT * FROM click_to_dial_configs WHERE extension = %s"
                ),
                (extension,),
            )

            if result and result[0]:
                row = result[0]
                return {
                    "extension": row[1],
                    "enabled": bool(row[2]),
                    "default_caller_id": row[3],
                    "auto_answer": bool(row[4]),
                    "browser_notification": bool(row[5]),
                }
            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get click-to-dial config: {e}")
            return None

    def update_config(self, extension: str, config: dict) -> bool:
        """
        Update click-to-dial configuration

        Args:
            extension: Extension number
            config: Configuration dictionary

        Returns:
            bool: True if successful
        """
        try:
            existing = self.get_config(extension)

            if existing:
                # Update
                self.db.execute(
                    (
                        """UPDATE click_to_dial_configs
                       SET enabled = ?, default_caller_id = ?, auto_answer = ?,
                           browser_notification = ?
                       WHERE extension = ?"""
                        if self.db.db_type == "sqlite"
                        else """UPDATE click_to_dial_configs
                       SET enabled = %s, default_caller_id = %s, auto_answer = %s,
                           browser_notification = %s
                       WHERE extension = %s"""
                    ),
                    (
                        config.get("enabled", True),
                        config.get("default_caller_id"),
                        config.get("auto_answer", False),
                        config.get("browser_notification", True),
                        extension,
                    ),
                )
            else:
                # Insert
                self.db.execute(
                    (
                        """INSERT INTO click_to_dial_configs
                       (extension, enabled, default_caller_id, auto_answer, browser_notification)
                       VALUES (?, ?, ?, ?, ?)"""
                        if self.db.db_type == "sqlite"
                        else """INSERT INTO click_to_dial_configs
                       (extension, enabled, default_caller_id, auto_answer, browser_notification)
                       VALUES (%s, %s, %s, %s, %s)"""
                    ),
                    (
                        extension,
                        config.get("enabled", True),
                        config.get("default_caller_id"),
                        config.get("auto_answer", False),
                        config.get("browser_notification", True),
                    ),
                )

            self.logger.info(f"Updated click-to-dial config for {extension}")
            return True

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to update click-to-dial config: {e}")
            return False

    def initiate_call(self, extension: str, destination: str, source: str = "web") -> str | None:
        """
        Initiate click-to-dial call
        Integrates with PBX call handling to create actual SIP calls

        Args:
            extension: Calling extension
            destination: Destination number
            source: Call source (web, app, crm, etc.)

        Returns:
            Call ID or None
        """
        call_id = f"c2d-{extension}-{int(datetime.now(UTC).timestamp())}"

        try:
            # Log call initiation in database
            self.db.execute(
                (
                    """INSERT INTO click_to_dial_history
                   (extension, destination, call_id, source, status)
                   VALUES (?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO click_to_dial_history
                   (extension, destination, call_id, source, status)
                   VALUES (%s, %s, %s, %s, %s)"""
                ),
                (extension, destination, call_id, source, "initiated"),
            )

            # Integrate with PBX call handling if available
            if self.pbx_core and hasattr(self.pbx_core, "call_manager"):
                try:
                    # Create SIP call through CallManager
                    # This follows the same pattern as WebRTC call initiation
                    sip_call_id = str(uuid.uuid4())
                    call = self.pbx_core.call_manager.create_call(
                        call_id=sip_call_id, from_extension=extension, to_extension=destination
                    )

                    # Start the call
                    call.start()

                    # Update call status to indicate PBX integration succeeded
                    self.update_call_status(call_id, "ringing")

                    self.logger.info(
                        f"Click-to-dial call created via PBX: {extension} -> {destination} "
                        f"(source: {source}, sip_call_id: {sip_call_id})"
                    )
                except (KeyError, TypeError, ValueError) as e:
                    self.logger.warning(f"PBX call integration failed, using framework mode: {e}")
                    # Fall back to framework logging only
                    self.logger.info(
                        f"Click-to-dial call initiated (framework mode): {extension} -> {destination} ({source})"
                    )
            else:
                # Framework mode - log only, no actual call creation
                self.logger.info(
                    f"Click-to-dial call initiated (framework mode): {extension} -> {destination} ({source})"
                )

            return call_id

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to initiate click-to-dial call: {e}")
            return None

    def update_call_status(
        self, call_id: str, status: str, connected_at: datetime | None = None
    ) -> bool:
        """
        Update click-to-dial call status

        Args:
            call_id: Call identifier
            status: New status
            connected_at: Connection timestamp

        Returns:
            bool: True if successful
        """
        try:
            if connected_at:
                self.db.execute(
                    (
                        """UPDATE click_to_dial_history
                       SET status = ?, connected_at = ?
                       WHERE call_id = ?"""
                        if self.db.db_type == "sqlite"
                        else """UPDATE click_to_dial_history
                       SET status = %s, connected_at = %s
                       WHERE call_id = %s"""
                    ),
                    (status, connected_at, call_id),
                )
            else:
                self.db.execute(
                    (
                        """UPDATE click_to_dial_history
                       SET status = ?
                       WHERE call_id = ?"""
                        if self.db.db_type == "sqlite"
                        else """UPDATE click_to_dial_history
                       SET status = %s
                       WHERE call_id = %s"""
                    ),
                    (status, call_id),
                )

            return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to update call status: {e}")
            return False

    def get_call_history(self, extension: str, limit: int = 100) -> list[dict]:
        """
        Get click-to-dial call history for extension

        Args:
            extension: Extension number
            limit: Maximum number of records

        Returns:
            list of call history dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT * FROM click_to_dial_history
                   WHERE extension = ?
                   ORDER BY initiated_at DESC LIMIT ?"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM click_to_dial_history
                   WHERE extension = %s
                   ORDER BY initiated_at DESC LIMIT %s"""
                ),
                (extension, limit),
            )

            history = []
            for row in result or []:
                history.append(
                    {
                        "destination": row[2],
                        "call_id": row[3],
                        "source": row[4],
                        "initiated_at": row[5],
                        "connected_at": row[6],
                        "status": row[7],
                    }
                )

            return history

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get call history: {e}")
            return []

    def get_all_configs(self) -> list[dict]:
        """
        Get all click-to-dial configurations

        Returns:
            list of configuration dictionaries
        """
        try:
            result = self.db.execute("SELECT * FROM click_to_dial_configs ORDER BY extension")

            configs = []
            for row in result or []:
                configs.append(
                    {
                        "extension": row[1],
                        "enabled": bool(row[2]),
                        "default_caller_id": row[3],
                        "auto_answer": bool(row[4]),
                        "browser_notification": bool(row[5]),
                    }
                )

            return configs

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get all click-to-dial configs: {e}")
            return []
