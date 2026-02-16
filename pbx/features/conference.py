"""
Conference calling system
"""

from typing import Any

from pbx.utils.logger import get_logger


class ConferenceRoom:
    """Represents a conference room"""

    def __init__(self, room_number: str, max_participants: int = 10) -> None:
        """
        Initialize conference room

        Args:
            room_number: Room identifier
            max_participants: Maximum number of participants
        """
        self.room_number = room_number
        self.max_participants = max_participants
        self.participants = []
        self.logger = get_logger()

    def add_participant(self, extension: str, call_id: str) -> bool:
        """
        Add participant to conference

        Args:
            extension: Extension number
            call_id: Call ID

        Returns:
            True if added successfully
        """
        if len(self.participants) >= self.max_participants:
            self.logger.warning(f"Conference room {self.room_number} is full")
            return False

        participant = {"extension": extension, "call_id": call_id, "muted": False}

        self.participants.append(participant)
        self.logger.info(f"Added {extension} to conference {self.room_number}")
        return True

    def remove_participant(self, extension: str) -> bool:
        """
        Remove participant from conference

        Args:
            extension: Extension number

        Returns:
            True if removed
        """
        for i, participant in enumerate(self.participants):
            if participant["extension"] == extension:
                self.participants.pop(i)
                self.logger.info(f"Removed {extension} from conference {self.room_number}")
                return True
        return False

    def mute_participant(self, extension: str) -> bool:
        """Mute participant"""
        for participant in self.participants:
            if participant["extension"] == extension:
                participant["muted"] = True
                return True
        return False

    def unmute_participant(self, extension: str) -> bool:
        """Unmute participant"""
        for participant in self.participants:
            if participant["extension"] == extension:
                participant["muted"] = False
                return True
        return False

    def get_participant_count(self) -> int:
        """Get number of participants"""
        return len(self.participants)

    def is_empty(self) -> bool:
        """Check if conference is empty"""
        return len(self.participants) == 0


class ConferenceSystem:
    """Manages conference rooms"""

    def __init__(self) -> None:
        """Initialize conference system"""
        self.rooms = {}
        self.logger = get_logger()

    def create_room(self, room_number: str, max_participants: int = 10) -> Any:
        """
        Create conference room

        Args:
            room_number: Room identifier
            max_participants: Maximum participants

        Returns:
            ConferenceRoom object
        """
        if room_number not in self.rooms:
            self.rooms[room_number] = ConferenceRoom(room_number, max_participants)
            self.logger.info(f"Created conference room {room_number}")
        return self.rooms[room_number]

    def get_room(self, room_number: str) -> Any | None:
        """
        Get conference room

        Args:
            room_number: Room identifier

        Returns:
            ConferenceRoom object or None
        """
        return self.rooms.get(room_number)

    def join_conference(self, room_number: str, extension: str, call_id: str) -> bool:
        """
        Join conference

        Args:
            room_number: Room identifier
            extension: Extension number
            call_id: Call ID

        Returns:
            True if joined successfully
        """
        room = self.get_room(room_number)
        if not room:
            room = self.create_room(room_number)

        return room.add_participant(extension, call_id)

    def leave_conference(self, room_number: str, extension: str) -> bool:
        """
        Leave conference

        Args:
            room_number: Room identifier
            extension: Extension number

        Returns:
            True if left successfully
        """
        room = self.get_room(room_number)
        if room:
            result = room.remove_participant(extension)

            # Clean up empty rooms
            if room.is_empty():
                del self.rooms[room_number]
                self.logger.info(f"Removed empty conference room {room_number}")

            return result
        return False

    def get_active_rooms(self) -> list:
        """Get all active conference rooms"""
        return list(self.rooms.values())
