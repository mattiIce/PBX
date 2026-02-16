"""
Operator Console / Receptionist Features
Provides advanced call handling for receptionists and front desk staff
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pbx.core.call import CallState
from pbx.utils.logger import get_logger


class OperatorConsole:
    """Operator console for receptionists"""

    def __init__(self, config: dict, pbx_core: Any | None) -> None:
        """
        Initialize operator console

        Args:
            config: Configuration dictionary
            pbx_core: Reference to PBX core system
        """
        self.logger = get_logger()
        self.config = config
        self.pbx_core = pbx_core
        self.enabled = config.get("features.operator_console.enabled", False)
        self.operator_extensions = config.get("features.operator_console.operator_extensions", [])
        self.enable_call_screening = config.get(
            "features.operator_console.enable_call_screening", True
        )
        self.enable_call_announce = config.get(
            "features.operator_console.enable_call_announce", True
        )
        self.blf_monitoring = config.get("features.operator_console.blf_monitoring", True)

        # Track BLF (Busy Lamp Field) status for all extensions
        self.blf_status = {}  # {extension: status}

        # Call screening queue
        self.screening_queue = []  # list of calls waiting for screening

        # VIP caller database
        self.vip_db_path = config.get("features.operator_console.vip_db_path", "vip_callers.json")
        self.vip_callers = self._load_vip_database()

        if self.enabled:
            self.logger.info(f"Operator console enabled for extensions: {self.operator_extensions}")

    def is_operator(self, extension: str) -> bool:
        """
        Check if extension is an operator

        Args:
            extension: Extension number

        Returns:
            bool: True if extension is operator
        """
        return extension in self.operator_extensions

    def get_blf_status(self, extension: str) -> str:
        """
        Get BLF status for an extension

        Args:
            extension: Extension number

        Returns:
            str: Status (available, busy, ringing, dnd, offline)
        """
        if not self.blf_monitoring:
            return "unknown"

        # Query extension status from PBX
        ext_obj = self.pbx_core.extension_registry.get(extension)
        if not ext_obj:
            return "offline"

        if not ext_obj.registered:
            return "offline"

        # Check if extension is on a call
        active_calls = self.pbx_core.call_manager.get_active_calls()
        for call in active_calls:
            if extension in (call.from_extension, call.to_extension):
                from pbx.core.call import CallState

                if call.state == CallState.RINGING:
                    return "ringing"
                if call.state == CallState.CONNECTED:
                    return "busy"

        # Check presence status if available
        if hasattr(self.pbx_core, "presence_system"):
            status = self.pbx_core.presence_system.get_status(extension)
            if status == "dnd":
                return "dnd"

        return "available"

    def get_all_blf_status(self) -> dict[str, str]:
        """
        Get BLF status for all extensions

        Returns:
            dict: {extension: status}
        """
        if not self.blf_monitoring:
            return {}

        status_map = {}
        extensions = self.pbx_core.extension_registry.get_all()

        for ext in extensions:
            status_map[ext.number] = self.get_blf_status(ext.number)

        return status_map

    def screen_call(self, call_id: str, operator_extension: str) -> bool:
        """
        Operator answers call for screening before transferring

        Args:
            call_id: Call identifier
            operator_extension: Operator's extension

        Returns:
            bool: True if screening started
        """
        if not self.enabled or not self.enable_call_screening:
            return False

        if not self.is_operator(operator_extension):
            self.logger.warning(f"Extension {operator_extension} is not authorized as operator")
            return False

        call = self.pbx_core.call_manager.get_call(call_id)
        if not call:
            self.logger.warning(f"Call {call_id} not found")
            return False

        self.logger.info(f"Operator {operator_extension} screening call {call_id}")

        # Add call to screening queue
        self.screening_queue.append(
            {
                "call_id": call_id,
                "operator": operator_extension,
                "started_at": datetime.now(UTC),
                "original_destination": call.to_extension,
            }
        )

        # Intercept the call - put original destination on hold
        if call.state in (CallState.RINGING, CallState.CALLING):
            # Call hasn't been answered yet, redirect to operator
            original_destination = call.to_extension
            call.to_extension = operator_extension

            # Store original destination for later transfer
            if not hasattr(call, "screening_info"):
                call.screening_info = {}
            call.screening_info["original_destination"] = original_destination
            call.screening_info["operator"] = operator_extension
            call.screening_info["is_screening"] = True

            self.logger.info(
                f"Redirected call {call_id} from {original_destination} to operator {operator_extension}"
            )
            return True
        if call.state == CallState.CONNECTED:
            # Call already connected, put it on hold and notify operator
            call.hold()
            self.logger.info(f"Put call {call_id} on hold for operator screening")
            return True

        return False

    def announce_and_transfer(self, call_id: str, announcement: str, target_extension: str) -> bool:
        """
        Announce caller to recipient before transferring

        Args:
            call_id: Call identifier
            announcement: Announcement text (e.g., "Call from John Smith")
            target_extension: Extension to transfer to

        Returns:
            bool: True if successful
        """
        if not self.enabled or not self.enable_call_announce:
            return False

        call = self.pbx_core.call_manager.get_call(call_id)
        if not call:
            self.logger.warning(f"Call {call_id} not found for announced transfer")
            return False

        self.logger.info(f"Announcing call {call_id} to {target_extension}: {announcement}")

        # Step 1: Place original call on hold
        call.hold()

        # Step 2: Store announcement for the target
        # In a real implementation, this would:
        # - Create a new call to the target extension
        # - Play the announcement (using TTS or pre-recorded message)
        # - Wait for target to accept or reject
        # - Complete the transfer if accepted, or return to operator if rejected

        if not hasattr(call, "transfer_info"):
            call.transfer_info = {}

        call.transfer_info["announcement"] = announcement
        call.transfer_info["target_extension"] = target_extension
        call.transfer_info["transfer_type"] = "announced"
        call.transfer_info["initiated_at"] = datetime.now(UTC).isoformat()

        # Use the existing transfer mechanism
        # In a production system, this would wait for target acknowledgment
        # For now, we log the announcement and proceed with transfer
        self.logger.info(
            f"Announcement logged: '{announcement}' for transfer to {target_extension}"
        )

        # Attempt the transfer (the actual SIP transfer would happen in the
        # call manager)
        try:
            # Resume the call and transfer it
            call.resume()
            # The actual transfer would be handled by the SIP server
            # This is a placeholder for the transfer mechanism
            call.transfer_target = target_extension
            self.logger.info(f"Transfer initiated for call {call_id} to {target_extension}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to transfer call {call_id}: {e}")
            call.resume()  # Resume call with operator if transfer fails
            return False

    def park_and_page(
        self, call_id: str, page_message: str, page_method: str = "log"
    ) -> str | None:
        """
        Park call and page staff member

        Args:
            call_id: Call identifier
            page_message: Page message
            page_method: Paging method ('log', 'multicast', 'sip', 'email')

        Returns:
            str: Park slot number or None
        """
        if not self.enabled:
            return None

        self.logger.info(f"Parking call {call_id} and paging: {page_message}")

        # Park the call
        if hasattr(self.pbx_core, "parking_system"):
            slot = self.pbx_core.parking_system.park_call(call_id)
            if slot:
                # Send page notification based on configured method
                self._send_page_notification(page_message, slot, page_method)
                return slot

        return None

    def _send_page_notification(self, message: str, park_slot: str, method: str = "log") -> None:
        """
        Send page notification via configured method

        Args:
            message: Page message
            park_slot: Park slot number
            method: Notification method
        """
        full_message = f"{message} - Retrieve call at {park_slot}"

        if method == "log":
            # Log-based paging (default)
            self.logger.info(f"PAGE: {full_message}")

        elif method == "multicast":
            # Multicast paging to speakers
            # In production, this would send RTP stream to multicast address
            multicast_addr = self.config.get(
                "features.operator_console.paging.multicast_address", "224.0.1.1"
            )
            multicast_port = self.config.get(
                "features.operator_console.paging.multicast_port", 5004
            )
            self.logger.info(
                f"Would send multicast page to {multicast_addr}:{multicast_port}: {full_message}"
            )

        elif method == "sip":
            # SIP-based paging
            paging_uri = self.config.get(
                "features.operator_console.paging.sip_uri", "sip:page-all@pbx.local"
            )
            self.logger.info(f"Would send SIP page to {paging_uri}: {full_message}")

        elif method == "email":
            # Email notification (if voicemail system with email is configured)
            if hasattr(self.pbx_core, "voicemail_system"):
                # Would send email notification
                self.logger.info(f"Would send email page: {full_message}")

        else:
            self.logger.warning(f"Unknown paging method: {method}")

        # Store page in history for tracking
        if not hasattr(self, "page_history"):
            self.page_history = []

        self.page_history.append(
            {
                "message": full_message,
                "method": method,
                "timestamp": datetime.now(UTC).isoformat(),
                "park_slot": park_slot,
            }
        )

    def get_directory(self, search_query: str | None = None) -> list[dict]:
        """
        Get company directory for quick lookup

        Args:
            search_query: Optional search query

        Returns:
            list: list of directory entries
        """
        extensions = self.pbx_core.extension_registry.get_all()
        directory = []

        for ext in extensions:
            entry = {
                "extension": ext.number,
                "name": ext.name,
                "status": self.get_blf_status(ext.number),
                "registered": ext.registered,
            }

            # Add email if available
            if hasattr(ext, "config") and ext.config:
                entry["email"] = ext.config.get("email")

            # Filter by search query if provided
            if search_query:
                query_lower = search_query.lower()
                if query_lower in ext.number or query_lower in ext.name.lower():
                    directory.append(entry)
            else:
                directory.append(entry)

        return sorted(directory, key=lambda x: x["name"])

    def _load_vip_database(self) -> dict:
        """
        Load VIP caller database from JSON file

        Returns:
            dict: VIP caller database
        """
        if Path(self.vip_db_path).exists():
            try:
                with open(self.vip_db_path) as f:
                    return json.load(f)
            except (OSError, ValueError, json.JSONDecodeError) as e:
                self.logger.error(f"Failed to load VIP database: {e}")
                return {}
        return {}

    def _save_vip_database(self) -> bool:
        """Save VIP caller database to JSON file"""
        try:
            with open(self.vip_db_path, "w") as f:
                json.dump(self.vip_callers, f, indent=2)
            return True
        except (OSError, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to save VIP database: {e}")
            return False

    def mark_vip_caller(
        self,
        caller_id: str,
        priority_level: int = 1,
        name: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """
        Mark a caller as VIP for priority handling

        Args:
            caller_id: Caller identifier (phone number)
            priority_level: Priority level (1=VIP, 2=VVIP, 3=Executive)
            name: Optional caller name
            notes: Optional notes about the caller

        Returns:
            bool: True if marked successfully
        """
        if not caller_id:
            return False

        # Normalize caller ID (remove formatting)
        caller_id = caller_id.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

        vip_entry = {
            "caller_id": caller_id,
            "priority_level": priority_level,
            "name": name,
            "notes": notes,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        self.vip_callers[caller_id] = vip_entry
        self._save_vip_database()

        self.logger.info(f"Marked {caller_id} as VIP (priority {priority_level})")
        return True

    def unmark_vip_caller(self, caller_id: str) -> bool:
        """
        Remove VIP status from a caller

        Args:
            caller_id: Caller identifier

        Returns:
            bool: True if removed successfully
        """
        caller_id = caller_id.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

        if caller_id in self.vip_callers:
            del self.vip_callers[caller_id]
            self._save_vip_database()
            self.logger.info(f"Removed VIP status from {caller_id}")
            return True
        return False

    def get_vip_caller(self, caller_id: str) -> dict | None:
        """
        Get VIP caller information

        Args:
            caller_id: Caller identifier

        Returns:
            dict: VIP caller information or None
        """
        caller_id = caller_id.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
        return self.vip_callers.get(caller_id)

    def is_vip_caller(self, caller_id: str) -> bool:
        """
        Check if caller is marked as VIP

        Args:
            caller_id: Caller identifier

        Returns:
            bool: True if caller is VIP
        """
        return self.get_vip_caller(caller_id) is not None

    def list_vip_callers(self) -> list[dict]:
        """
        list all VIP callers

        Returns:
            list: list of VIP caller entries
        """
        return list(self.vip_callers.values())

    def get_call_queue_status(self) -> dict:
        """
        Get status of all call queues for operator dashboard

        Returns:
            dict: Queue statistics
        """
        if not hasattr(self.pbx_core, "call_queue_system"):
            return {}

        queue_system = self.pbx_core.call_queue_system
        status = {}

        for queue in queue_system.queues.values():
            status[queue.number] = {
                "name": queue.name,
                "calls_waiting": queue.get_queue_depth(),
                "available_agents": len(
                    [a for a in queue.agents.values() if a.status == "available"]
                ),
                "longest_wait": queue.get_longest_wait_time(),
            }

        return status
