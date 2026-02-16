"""
Call Parking System
Allows calls to be parked and retrieved from any extension
"""

from datetime import UTC, datetime

from pbx.utils.logger import get_logger


class ParkedCall:
    """Represents a parked call"""

    def __init__(self, call_id, park_number, from_extension, original_destination):
        """
        Initialize parked call

        Args:
            call_id: Call identifier
            park_number: Parking slot number
            from_extension: Extension that parked the call
            original_destination: Original call destination
        """
        self.call_id = call_id
        self.park_number = park_number
        self.from_extension = from_extension
        self.original_destination = original_destination
        self.park_time = datetime.now(UTC)
        self.parker = from_extension

    def get_park_duration(self):
        """Get time parked in seconds"""
        return (datetime.now(UTC) - self.park_time).total_seconds()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "call_id": self.call_id,
            "park_number": self.park_number,
            "from_extension": self.from_extension,
            "original_destination": self.original_destination,
            "parker": self.parker,
            "park_time": self.park_time.isoformat(),
            "duration": self.get_park_duration(),
        }


class CallParkingSystem:
    """Manages call parking"""

    def __init__(
        self, park_range_start=70, park_range_end=79, timeout=120, callback_extension=None
    ):
        """
        Initialize call parking system

        Args:
            park_range_start: Start of parking slot range (e.g., 70)
            park_range_end: End of parking slot range (e.g., 79)
            timeout: Seconds before callback (e.g., 120 = 2 minutes)
            callback_extension: Extension to call back on timeout
        """
        self.park_range_start = park_range_start
        self.park_range_end = park_range_end
        self.timeout = timeout
        self.callback_extension = callback_extension
        self.parked_calls = {}  # park_number -> ParkedCall
        self.logger = get_logger()

    def find_available_slot(self):
        """
        Find next available parking slot

        Returns:
            Park number or None if all slots full
        """
        for slot in range(self.park_range_start, self.park_range_end + 1):
            if slot not in self.parked_calls:
                return slot
        return None

    def park_call(self, call_id, from_extension, original_destination=None):
        """
        Park a call

        Args:
            call_id: Call identifier
            from_extension: Extension parking the call
            original_destination: Original destination of call

        Returns:
            Park number or None if no slots available
        """
        park_number = self.find_available_slot()

        if park_number is None:
            self.logger.warning("No parking slots available")
            return None

        parked_call = ParkedCall(call_id, park_number, from_extension, original_destination)
        self.parked_calls[park_number] = parked_call

        self.logger.info(f"Parked call {call_id} at slot {park_number}")
        return park_number

    def retrieve_call(self, park_number, retrieving_extension):
        """
        Retrieve a parked call

        Args:
            park_number: Parking slot number
            retrieving_extension: Extension retrieving the call

        Returns:
            ParkedCall object or None
        """
        parked_call = self.parked_calls.get(park_number)

        if parked_call:
            del self.parked_calls[park_number]
            self.logger.info(
                f"Retrieved parked call from slot {park_number} by {retrieving_extension}"
            )
            return parked_call

        return None

    def check_timeouts(self):
        """
        Check for timed out parked calls

        Returns:
            list of timed out ParkedCall objects
        """
        timed_out = []

        for park_number, parked_call in list(self.parked_calls.items()):
            if parked_call.get_park_duration() > self.timeout:
                timed_out.append(parked_call)
                del self.parked_calls[park_number]
                self.logger.info(f"Parked call at slot {park_number} timed out")

        return timed_out

    def get_parked_calls(self):
        """
        Get all parked calls

        Returns:
            list of ParkedCall dictionaries
        """
        return [call.to_dict() for call in self.parked_calls.values()]

    def get_parked_call(self, park_number):
        """
        Get specific parked call

        Args:
            park_number: Park slot number

        Returns:
            ParkedCall object or None
        """
        return self.parked_calls.get(park_number)

    def is_slot_available(self, park_number):
        """Check if parking slot is available"""
        return park_number not in self.parked_calls

    def get_available_slots(self):
        """Get list of available parking slots"""
        all_slots = set(range(self.park_range_start, self.park_range_end + 1))
        used_slots = set(self.parked_calls.keys())
        return sorted(all_slots - used_slots)
