"""
Call management and session handling
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any


class CallState(Enum):
    """Call states"""

    IDLE = "idle"
    CALLING = "calling"
    RINGING = "ringing"
    CONNECTED = "connected"
    HOLD = "hold"
    TRANSFERRING = "transferring"
    ENDED = "ended"


class Call:
    """Represents a call session"""

    def __init__(self, call_id: str, from_extension: str, to_extension: str) -> None:
        """
        Initialize call

        Args:
            call_id: Unique call identifier
            from_extension: Calling extension
            to_extension: Called extension
        """
        self.call_id: str = call_id
        self.from_extension: str = from_extension
        self.to_extension: str = to_extension
        self.state: CallState = CallState.IDLE
        self.start_time: datetime | None = None
        self.answer_time: datetime | None = None
        self.end_time: datetime | None = None
        self.rtp_ports: tuple[int, int] | None = None
        self.recording: bool = False
        self.on_hold: bool = False
        self.caller_rtp: dict[str, Any] | None = None  # Caller's RTP endpoint info
        self.caller_addr: tuple[str, int] | None = None  # Caller's SIP address
        self.callee_rtp: dict[str, Any] | None = None  # Callee's RTP endpoint info
        self.callee_addr: tuple[str, int] | None = None  # Callee's SIP address
        self.original_invite: Any | None = None  # Original INVITE message from caller
        self.callee_invite: Any | None = None  # INVITE sent to callee (for CANCEL reference)
        self.no_answer_timer: Any | None = None  # Timer for routing to voicemail
        self.routed_to_voicemail: bool = False  # Flag to track if routed to VM
        self.transferred: bool = False  # Flag to track if call has been transferred
        self.transfer_destination: str | None = None  # Destination extension for transfer

        # Voicemail access attributes
        self.voicemail_access: bool = False  # Flag indicating voicemail access call
        self.voicemail_extension: str | None = None  # Target extension for voicemail access
        self.voicemail_ivr: Any | None = None  # VoicemailIVR instance for interactive menus

        # Auto attendant attributes
        self.auto_attendant_active: bool = False  # Flag indicating auto attendant call
        self.aa_session: dict[str, Any] | None = None  # Auto attendant session data

        # DTMF handling attributes
        # Queue for out-of-band DTMF digits (SIP INFO)
        self.dtmf_info_queue: list[str] = []

    def start(self) -> None:
        """Start the call"""
        self.state = CallState.CALLING
        self.start_time = datetime.now(UTC)

    def ring(self) -> None:
        """set call state to ringing"""
        self.state = CallState.RINGING

    def connect(self) -> None:
        """Connect the call"""
        self.state = CallState.CONNECTED
        self.answer_time = datetime.now(UTC)

    def hold(self) -> None:
        """Put call on hold"""
        self.state = CallState.HOLD
        self.on_hold = True

    def resume(self) -> None:
        """Resume call from hold"""
        self.state = CallState.CONNECTED
        self.on_hold = False

    def end(self) -> None:
        """End the call"""
        self.state = CallState.ENDED
        self.end_time = datetime.now(UTC)

    def get_duration(self) -> float:
        """Get call duration in seconds"""
        if not self.start_time:
            return 0

        end = self.end_time or datetime.now(UTC)
        return (end - self.start_time).total_seconds()

    def __str__(self) -> str:
        return f"Call {self.call_id}: {self.from_extension} -> {self.to_extension} ({self.state.value})"


class CallManager:
    """Manages active calls"""

    MAX_HISTORY_SIZE = 10000

    def __init__(self) -> None:
        """Initialize call manager"""
        self.active_calls: dict[str, Call] = {}
        self.call_history: list[Call] = []

    def create_call(self, call_id: str, from_extension: str, to_extension: str) -> Call:
        """
        Create new call

        Args:
            call_id: Unique call identifier
            from_extension: Calling extension
            to_extension: Called extension

        Returns:
            Call object
        """
        call = Call(call_id, from_extension, to_extension)
        self.active_calls[call_id] = call
        return call

    def get_call(self, call_id: str) -> Call | None:
        """
        Get call by ID

        Args:
            call_id: Call identifier

        Returns:
            Call object or None
        """
        return self.active_calls.get(call_id)

    def end_call(self, call_id: str) -> bool:
        """
        End call

        Args:
            call_id: Call identifier

        Returns:
            True if call was ended
        """
        call = self.active_calls.get(call_id)
        if call:
            call.end()
            self.call_history.append(call)
            # Prevent unbounded memory growth in long-running systems
            if len(self.call_history) > self.MAX_HISTORY_SIZE:
                self.call_history = self.call_history[-self.MAX_HISTORY_SIZE:]
            del self.active_calls[call_id]
            return True
        return False

    def get_active_calls(self) -> list[Call]:
        """Get all active calls"""
        return list(self.active_calls.values())

    def get_extension_calls(self, extension: str) -> list[Call]:
        """
        Get calls for an extension

        Args:
            extension: Extension number

        Returns:
            list of Call objects
        """
        calls = [
            call
            for call in self.active_calls.values()
            if extension in (call.from_extension, call.to_extension)
        ]
        return calls
