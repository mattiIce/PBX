"""
WebRTC Browser Calling Support
Provides WebRTC signaling and integration with PBX SIP infrastructure
"""
import json
import uuid
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Set, Callable
from pbx.utils.logger import get_logger


class WebRTCSession:
    """Represents a WebRTC session"""
    
    def __init__(self, session_id: str, extension: str, peer_connection_id: Optional[str] = None):
        """
        Initialize WebRTC session
        
        Args:
            session_id: Unique session identifier
            extension: Extension number associated with this session
            peer_connection_id: Optional peer connection identifier
        """
        self.session_id = session_id
        self.extension = extension
        self.peer_connection_id = peer_connection_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.state = 'new'  # new, connecting, connected, disconnected
        self.local_sdp = None
        self.remote_sdp = None
        self.ice_candidates = []
        self.call_id = None
        self.metadata = {}
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'extension': self.extension,
            'peer_connection_id': self.peer_connection_id,
            'state': self.state,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'call_id': self.call_id
        }


class WebRTCSignalingServer:
    """
    WebRTC Signaling Server
    
    Handles WebRTC signaling between browser clients and PBX
    - Session management
    - SDP offer/answer exchange
    - ICE candidate exchange
    - Integration with SIP infrastructure
    """
    
    def __init__(self, config=None):
        """
        Initialize WebRTC signaling server
        
        Args:
            config: Configuration object
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # WebRTC configuration
        self.enabled = self._get_config('features.webrtc.enabled', False)
        self.stun_servers = self._get_config('features.webrtc.stun_servers', [
            'stun:stun.l.google.com:19302',
            'stun:stun1.l.google.com:19302'
        ])
        self.turn_servers = self._get_config('features.webrtc.turn_servers', [])
        self.ice_transport_policy = self._get_config('features.webrtc.ice_transport_policy', 'all')
        self.session_timeout = self._get_config('features.webrtc.session_timeout', 300)  # 5 minutes
        
        # Sessions
        self.sessions: Dict[str, WebRTCSession] = {}
        self.extension_sessions: Dict[str, Set[str]] = {}  # extension -> set of session_ids
        self.lock = threading.Lock()
        
        # Callbacks
        self.on_session_created: Optional[Callable] = None
        self.on_session_closed: Optional[Callable] = None
        self.on_offer_received: Optional[Callable] = None
        self.on_answer_received: Optional[Callable] = None
        
        # Cleanup thread
        self.running = False
        self.cleanup_thread = None
        
        if self.enabled:
            self.logger.info("WebRTC signaling server enabled")
            self._start_cleanup_thread()
        else:
            self.logger.info("WebRTC signaling server disabled")
    
    def _get_config(self, key: str, default=None):
        """Get configuration value"""
        if hasattr(self.config, 'get'):
            return self.config.get(key, default)
        return default
    
    def _start_cleanup_thread(self):
        """Start session cleanup thread"""
        self.running = True
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="WebRTCCleanup",
            daemon=True
        )
        self.cleanup_thread.start()
        self.logger.info("Started WebRTC session cleanup thread")
    
    def stop(self):
        """Stop the WebRTC signaling server"""
        self.logger.info("Stopping WebRTC signaling server...")
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        self.logger.info("WebRTC signaling server stopped")
    
    def _cleanup_worker(self):
        """Worker thread for cleaning up stale sessions"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            self._cleanup_stale_sessions()
    
    def _cleanup_stale_sessions(self):
        """Remove stale sessions that have timed out"""
        with self.lock:
            now = datetime.now()
            stale_sessions = []
            
            for session_id, session in self.sessions.items():
                age = (now - session.last_activity).total_seconds()
                if age > self.session_timeout:
                    stale_sessions.append(session_id)
            
            for session_id in stale_sessions:
                session = self.sessions.get(session_id)
                if session:
                    self.logger.info(f"Cleaning up stale WebRTC session: {session_id} (extension: {session.extension})")
                    self._remove_session(session_id)
    
    def create_session(self, extension: str) -> WebRTCSession:
        """
        Create a new WebRTC session
        
        Args:
            extension: Extension number
            
        Returns:
            WebRTCSession object
        """
        if not self.enabled:
            raise RuntimeError("WebRTC is not enabled")
        
        session_id = str(uuid.uuid4())
        session = WebRTCSession(session_id, extension)
        
        with self.lock:
            self.sessions[session_id] = session
            
            # Track sessions by extension
            if extension not in self.extension_sessions:
                self.extension_sessions[extension] = set()
            self.extension_sessions[extension].add(session_id)
        
        self.logger.info(f"Created WebRTC session: {session_id} (extension: {extension})")
        
        if self.on_session_created:
            try:
                self.on_session_created(session)
            except Exception as e:
                self.logger.error(f"Error in session created callback: {e}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[WebRTCSession]:
        """Get session by ID"""
        with self.lock:
            return self.sessions.get(session_id)
    
    def get_extension_sessions(self, extension: str) -> list:
        """Get all sessions for an extension"""
        with self.lock:
            session_ids = self.extension_sessions.get(extension, set())
            return [self.sessions[sid] for sid in session_ids if sid in self.sessions]
    
    def close_session(self, session_id: str) -> bool:
        """
        Close a WebRTC session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was closed, False if not found
        """
        with self.lock:
            return self._remove_session(session_id)
    
    def _remove_session(self, session_id: str) -> bool:
        """Remove session (internal, assumes lock is held)"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Remove from sessions
        del self.sessions[session_id]
        
        # Remove from extension tracking
        extension = session.extension
        if extension in self.extension_sessions:
            self.extension_sessions[extension].discard(session_id)
            if not self.extension_sessions[extension]:
                del self.extension_sessions[extension]
        
        self.logger.info(f"Closed WebRTC session: {session_id} (extension: {extension})")
        
        if self.on_session_closed:
            try:
                self.on_session_closed(session)
            except Exception as e:
                self.logger.error(f"Error in session closed callback: {e}")
        
        return True
    
    def handle_offer(self, session_id: str, sdp: str) -> bool:
        """
        Handle SDP offer from client
        
        Args:
            session_id: Session identifier
            sdp: SDP offer
            
        Returns:
            True if offer was accepted
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.warning(f"Received offer for unknown session: {session_id}")
            return False
        
        session.local_sdp = sdp
        session.state = 'connecting'
        session.update_activity()
        
        self.logger.info(f"Received SDP offer for session: {session_id}")
        self.logger.debug(f"SDP offer: {sdp[:100]}...")
        
        if self.on_offer_received:
            try:
                self.on_offer_received(session, sdp)
            except Exception as e:
                self.logger.error(f"Error in offer received callback: {e}")
        
        return True
    
    def handle_answer(self, session_id: str, sdp: str) -> bool:
        """
        Handle SDP answer from client
        
        Args:
            session_id: Session identifier
            sdp: SDP answer
            
        Returns:
            True if answer was accepted
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.warning(f"Received answer for unknown session: {session_id}")
            return False
        
        session.remote_sdp = sdp
        session.state = 'connected'
        session.update_activity()
        
        self.logger.info(f"Received SDP answer for session: {session_id}")
        self.logger.debug(f"SDP answer: {sdp[:100]}...")
        
        if self.on_answer_received:
            try:
                self.on_answer_received(session, sdp)
            except Exception as e:
                self.logger.error(f"Error in answer received callback: {e}")
        
        return True
    
    def add_ice_candidate(self, session_id: str, candidate: Dict) -> bool:
        """
        Add ICE candidate for session
        
        Args:
            session_id: Session identifier
            candidate: ICE candidate dictionary
            
        Returns:
            True if candidate was added
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.warning(f"Received ICE candidate for unknown session: {session_id}")
            return False
        
        session.ice_candidates.append(candidate)
        session.update_activity()
        
        self.logger.debug(f"Added ICE candidate for session: {session_id}")
        return True
    
    def get_ice_servers_config(self) -> Dict:
        """
        Get ICE servers configuration for client
        
        Returns:
            Dictionary with ICE servers configuration
        """
        ice_servers = []
        
        # Add STUN servers
        for stun_url in self.stun_servers:
            ice_servers.append({'urls': stun_url})
        
        # Add TURN servers
        for turn_config in self.turn_servers:
            ice_servers.append({
                'urls': turn_config.get('url'),
                'username': turn_config.get('username'),
                'credential': turn_config.get('credential')
            })
        
        return {
            'iceServers': ice_servers,
            'iceTransportPolicy': self.ice_transport_policy
        }
    
    def get_sessions_info(self) -> list:
        """Get information about all active sessions"""
        with self.lock:
            return [session.to_dict() for session in self.sessions.values()]
    
    def set_session_call_id(self, session_id: str, call_id: str) -> bool:
        """Associate a call ID with a session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.call_id = call_id
        session.update_activity()
        self.logger.info(f"Associated call {call_id} with WebRTC session {session_id}")
        return True
    
    def set_session_metadata(self, session_id: str, key: str, value) -> bool:
        """Set metadata for a session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.metadata[key] = value
        session.update_activity()
        return True
    
    def get_session_metadata(self, session_id: str, key: str, default=None):
        """Get metadata from a session"""
        session = self.get_session(session_id)
        if not session:
            return default
        
        return session.metadata.get(key, default)


class WebRTCGateway:
    """
    WebRTC to SIP Gateway
    
    Translates between WebRTC and SIP protocols
    - Converts WebRTC SDP to SIP SDP
    - Handles media negotiation
    - Manages RTP/SRTP bridging
    """
    
    def __init__(self, pbx_core=None):
        """
        Initialize WebRTC gateway
        
        Args:
            pbx_core: PBX core instance
        """
        self.logger = get_logger()
        self.pbx_core = pbx_core
        self.logger.info("WebRTC to SIP gateway initialized")
    
    def webrtc_to_sip_sdp(self, webrtc_sdp: str) -> str:
        """
        Convert WebRTC SDP to SIP-compatible SDP
        
        Args:
            webrtc_sdp: WebRTC SDP
            
        Returns:
            SIP-compatible SDP
        """
        # This is a simplified conversion
        # In production, would need proper SDP parsing and transformation
        # - Convert DTLS-SRTP to SRTP or RTP
        # - Handle codec negotiation
        # - Adjust media attributes
        
        # For now, pass through with minimal changes
        # TODO: Implement full SDP transformation
        self.logger.debug("Converting WebRTC SDP to SIP SDP")
        return webrtc_sdp
    
    def sip_to_webrtc_sdp(self, sip_sdp: str) -> str:
        """
        Convert SIP SDP to WebRTC-compatible SDP
        
        Args:
            sip_sdp: SIP SDP
            
        Returns:
            WebRTC-compatible SDP
        """
        # This is a simplified conversion
        # In production, would need proper SDP parsing and transformation
        # - Add DTLS-SRTP support
        # - Handle codec negotiation
        # - Add WebRTC-specific attributes
        
        # For now, pass through with minimal changes
        # TODO: Implement full SDP transformation
        self.logger.debug("Converting SIP SDP to WebRTC SDP")
        return sip_sdp
    
    def initiate_call(self, session_id: str, target_extension: str) -> Optional[str]:
        """
        Initiate a call from WebRTC client to extension
        
        Args:
            session_id: WebRTC session ID
            target_extension: Target extension number
            
        Returns:
            Call ID if successful, None otherwise
        """
        if not self.pbx_core:
            self.logger.error("PBX core not available for call initiation")
            return None
        
        # TODO: Implement call initiation through PBX core
        # This would:
        # 1. Get WebRTC session
        # 2. Create SIP call to target extension
        # 3. Bridge WebRTC and SIP media
        # 4. Return call ID
        
        self.logger.info(f"Initiating call from WebRTC session {session_id} to {target_extension}")
        call_id = str(uuid.uuid4())
        
        return call_id
    
    def receive_call(self, session_id: str, call_id: str) -> bool:
        """
        Route incoming call to WebRTC client
        
        Args:
            session_id: WebRTC session ID
            call_id: Incoming call ID
            
        Returns:
            True if call was routed successfully
        """
        if not self.pbx_core:
            self.logger.error("PBX core not available for call routing")
            return False
        
        # TODO: Implement incoming call routing
        # This would:
        # 1. Get WebRTC session
        # 2. Notify client of incoming call
        # 3. Bridge WebRTC and SIP media when answered
        
        self.logger.info(f"Routing incoming call {call_id} to WebRTC session {session_id}")
        
        return True
