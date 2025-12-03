"""
Call management and session handling
"""
from datetime import datetime
from enum import Enum


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
    
    def __init__(self, call_id, from_extension, to_extension):
        """
        Initialize call
        
        Args:
            call_id: Unique call identifier
            from_extension: Calling extension
            to_extension: Called extension
        """
        self.call_id = call_id
        self.from_extension = from_extension
        self.to_extension = to_extension
        self.state = CallState.IDLE
        self.start_time = None
        self.answer_time = None
        self.end_time = None
        self.rtp_ports = None
        self.recording = False
        self.on_hold = False
        self.caller_rtp = None  # Caller's RTP endpoint info
        self.caller_addr = None  # Caller's SIP address
        self.callee_rtp = None  # Callee's RTP endpoint info
        self.callee_addr = None  # Callee's SIP address
        self.original_invite = None  # Original INVITE message from caller
        self.no_answer_timer = None  # Timer for routing to voicemail
        self.routed_to_voicemail = False  # Flag to track if routed to VM
        
    def start(self):
        """Start the call"""
        self.state = CallState.CALLING
        self.start_time = datetime.now()
    
    def ring(self):
        """Set call state to ringing"""
        self.state = CallState.RINGING
    
    def connect(self):
        """Connect the call"""
        self.state = CallState.CONNECTED
        self.answer_time = datetime.now()
    
    def hold(self):
        """Put call on hold"""
        self.state = CallState.HOLD
        self.on_hold = True
    
    def resume(self):
        """Resume call from hold"""
        self.state = CallState.CONNECTED
        self.on_hold = False
    
    def end(self):
        """End the call"""
        self.state = CallState.ENDED
        self.end_time = datetime.now()
    
    def get_duration(self):
        """Get call duration in seconds"""
        if not self.start_time:
            return 0
        
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def __str__(self):
        return f"Call {self.call_id}: {self.from_extension} -> {self.to_extension} ({self.state.value})"


class CallManager:
    """Manages active calls"""
    
    def __init__(self):
        """Initialize call manager"""
        self.active_calls = {}
        self.call_history = []
    
    def create_call(self, call_id, from_extension, to_extension):
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
    
    def get_call(self, call_id):
        """
        Get call by ID
        
        Args:
            call_id: Call identifier
            
        Returns:
            Call object or None
        """
        return self.active_calls.get(call_id)
    
    def end_call(self, call_id):
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
            del self.active_calls[call_id]
            return True
        return False
    
    def get_active_calls(self):
        """Get all active calls"""
        return list(self.active_calls.values())
    
    def get_extension_calls(self, extension):
        """
        Get calls for an extension
        
        Args:
            extension: Extension number
            
        Returns:
            List of Call objects
        """
        calls = []
        for call in self.active_calls.values():
            if call.from_extension == extension or call.to_extension == extension:
                calls.append(call)
        return calls
