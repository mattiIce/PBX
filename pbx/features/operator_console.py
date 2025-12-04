"""
Operator Console / Receptionist Features
Provides advanced call handling for receptionists and front desk staff
"""
from pbx.utils.logger import get_logger
from datetime import datetime
from typing import Dict, List, Optional


class OperatorConsole:
    """Operator console for receptionists"""

    def __init__(self, config: dict, pbx_core):
        """
        Initialize operator console

        Args:
            config: Configuration dictionary
            pbx_core: Reference to PBX core system
        """
        self.logger = get_logger()
        self.config = config
        self.pbx_core = pbx_core
        self.enabled = config.get('features.operator_console.enabled', False)
        self.operator_extensions = config.get('features.operator_console.operator_extensions', [])
        self.enable_call_screening = config.get('features.operator_console.enable_call_screening', True)
        self.enable_call_announce = config.get('features.operator_console.enable_call_announce', True)
        self.blf_monitoring = config.get('features.operator_console.blf_monitoring', True)

        # Track BLF (Busy Lamp Field) status for all extensions
        self.blf_status = {}  # {extension: status}

        # Call screening queue
        self.screening_queue = []  # List of calls waiting for screening

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
            if call.from_extension == extension or call.to_extension == extension:
                from pbx.core.call import CallState
                if call.state == CallState.RINGING:
                    return "ringing"
                elif call.state == CallState.CONNECTED:
                    return "busy"

        # Check presence status if available
        if hasattr(self.pbx_core, 'presence_system'):
            status = self.pbx_core.presence_system.get_status(extension)
            if status == "dnd":
                return "dnd"

        return "available"

    def get_all_blf_status(self) -> Dict[str, str]:
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
            return False

        self.logger.info(f"Operator {operator_extension} screening call {call_id}")

        # Add call to screening queue
        self.screening_queue.append({
            'call_id': call_id,
            'operator': operator_extension,
            'started_at': datetime.now(),
            'original_destination': call.to_extension
        })

        # TODO: Implement call interception and operator connection
        # This would involve:
        # 1. Pause the original call routing
        # 2. Connect operator to caller
        # 3. Allow operator to announce and transfer

        return True

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

        self.logger.info(f"Announcing call {call_id} to {target_extension}: {announcement}")

        # TODO: Implement announced transfer
        # 1. Place original call on hold
        # 2. Call target extension
        # 3. Play announcement (or speak to them)
        # 4. Complete transfer if accepted, otherwise return to operator

        return False

    def park_and_page(self, call_id: str, page_message: str) -> Optional[str]:
        """
        Park call and page staff member

        Args:
            call_id: Call identifier
            page_message: Page message

        Returns:
            str: Park slot number or None
        """
        if not self.enabled:
            return None

        self.logger.info(f"Parking call {call_id} and paging: {page_message}")

        # Park the call
        if hasattr(self.pbx_core, 'call_parking'):
            slot = self.pbx_core.call_parking.park_call(call_id)
            if slot:
                # TODO: Send page notification (could be via speakers, SMS, etc.)
                self.logger.info(f"Paged: '{page_message}' - retrieve call at {slot}")
                return slot

        return None

    def get_directory(self, search_query: str = None) -> List[Dict]:
        """
        Get company directory for quick lookup

        Args:
            search_query: Optional search query

        Returns:
            list: List of directory entries
        """
        extensions = self.pbx_core.extension_registry.get_all()
        directory = []

        for ext in extensions:
            entry = {
                'extension': ext.number,
                'name': ext.name,
                'status': self.get_blf_status(ext.number),
                'registered': ext.registered
            }

            # Add email if available
            if hasattr(ext, 'config') and ext.config:
                entry['email'] = ext.config.get('email')

            # Filter by search query if provided
            if search_query:
                query_lower = search_query.lower()
                if query_lower in ext.number or query_lower in ext.name.lower():
                    directory.append(entry)
            else:
                directory.append(entry)

        return sorted(directory, key=lambda x: x['name'])

    def mark_vip_caller(self, caller_id: str, priority_level: int = 1):
        """
        Mark a caller as VIP for priority handling

        Args:
            caller_id: Caller identifier
            priority_level: Priority level (1=high, 2=medium, 3=normal)

        Returns:
            bool: True if marked
        """
        # TODO: Implement VIP caller database
        # Store VIP status and priority level
        # Future: Integrate with CRM to auto-detect VIP customers

        self.logger.info(f"Marked {caller_id} as VIP (priority {priority_level})")
        return True

    def get_call_queue_status(self) -> Dict:
        """
        Get status of all call queues for operator dashboard

        Returns:
            dict: Queue statistics
        """
        if not hasattr(self.pbx_core, 'call_queue_system'):
            return {}

        queue_system = self.pbx_core.call_queue_system
        status = {}

        for queue in queue_system.queues.values():
            status[queue.number] = {
                'name': queue.name,
                'calls_waiting': queue.get_queue_depth(),
                'available_agents': len([a for a in queue.agents.values()
                                       if a.status == 'available']),
                'longest_wait': queue.get_longest_wait_time()
            }

        return status
