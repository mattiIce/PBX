"""
WebRTC Video Conferencing Support
Provides HD video calls from browser using free aiortc library
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from pbx.utils.logger import get_logger

# Try to import aiortc (free WebRTC library)
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from aiortc.contrib.media import MediaRecorder, MediaPlayer
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False


class WebRTCVideoConferencing:
    """WebRTC Video Conferencing Manager using aiortc (free)"""
    
    def __init__(self, config=None):
        """Initialize video conferencing system"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('features', {}).get('webrtc_video', {}).get('enabled', False)
        self.video_sessions = {}  # session_id -> RTCPeerConnection
        self.conference_rooms = {}  # room_id -> list of session_ids
        
        if self.enabled and not AIORTC_AVAILABLE:
            self.logger.warning("WebRTC video enabled but aiortc not installed. Install with: pip install aiortc")
        elif self.enabled:
            self.logger.info("WebRTC video conferencing initialized (using aiortc)")
    
    async def create_video_session(self, session_id: str, room_id: Optional[str] = None) -> Dict:
        """
        Create a new video session
        
        Args:
            session_id: Unique session identifier
            room_id: Optional conference room ID for multi-party video
            
        Returns:
            Session information dictionary
        """
        if not self.enabled:
            return {'error': 'WebRTC video not enabled'}
        
        if not AIORTC_AVAILABLE:
            return {'error': 'aiortc library not available'}
        
        try:
            # Create peer connection
            pc = RTCPeerConnection()
            self.video_sessions[session_id] = {
                'peer_connection': pc,
                'room_id': room_id,
                'created_at': datetime.now(),
                'video_enabled': True,
                'audio_enabled': True
            }
            
            # Add to conference room if specified
            if room_id:
                if room_id not in self.conference_rooms:
                    self.conference_rooms[room_id] = []
                self.conference_rooms[room_id].append(session_id)
            
            self.logger.info(f"Created video session {session_id}" + 
                           (f" in room {room_id}" if room_id else ""))
            
            return {
                'session_id': session_id,
                'room_id': room_id,
                'status': 'created'
            }
        except Exception as e:
            self.logger.error(f"Error creating video session: {e}")
            return {'error': str(e)}
    
    async def handle_offer(self, session_id: str, sdp: str) -> Optional[str]:
        """
        Handle WebRTC offer and generate answer
        
        Args:
            session_id: Session identifier
            sdp: SDP offer from client
            
        Returns:
            SDP answer or None on error
        """
        if session_id not in self.video_sessions:
            self.logger.error(f"Session {session_id} not found")
            return None
        
        try:
            session = self.video_sessions[session_id]
            pc = session['peer_connection']
            
            # Set remote description
            await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type='offer'))
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            return pc.localDescription.sdp
        except Exception as e:
            self.logger.error(f"Error handling video offer: {e}")
            return None
    
    def toggle_video(self, session_id: str, enabled: bool) -> bool:
        """Toggle video on/off for a session"""
        if session_id in self.video_sessions:
            self.video_sessions[session_id]['video_enabled'] = enabled
            self.logger.info(f"Video {'enabled' if enabled else 'disabled'} for session {session_id}")
            return True
        return False
    
    def toggle_audio(self, session_id: str, enabled: bool) -> bool:
        """Toggle audio on/off for a session"""
        if session_id in self.video_sessions:
            self.video_sessions[session_id]['audio_enabled'] = enabled
            self.logger.info(f"Audio {'enabled' if enabled else 'disabled'} for session {session_id}")
            return True
        return False
    
    def get_room_participants(self, room_id: str) -> List[str]:
        """Get list of participants in a conference room"""
        return self.conference_rooms.get(room_id, [])
    
    async def end_session(self, session_id: str):
        """End a video session"""
        if session_id in self.video_sessions:
            session = self.video_sessions[session_id]
            
            # Remove from conference room
            if session['room_id']:
                room_id = session['room_id']
                if room_id in self.conference_rooms:
                    self.conference_rooms[room_id].remove(session_id)
                    if not self.conference_rooms[room_id]:
                        del self.conference_rooms[room_id]
            
            # Close peer connection
            if AIORTC_AVAILABLE:
                await session['peer_connection'].close()
            
            del self.video_sessions[session_id]
            self.logger.info(f"Ended video session {session_id}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a video session"""
        if session_id in self.video_sessions:
            session = self.video_sessions[session_id]
            return {
                'session_id': session_id,
                'room_id': session['room_id'],
                'video_enabled': session['video_enabled'],
                'audio_enabled': session['audio_enabled'],
                'created_at': session['created_at'].isoformat()
            }
        return None
    
    def get_statistics(self) -> Dict:
        """Get video conferencing statistics"""
        return {
            'active_sessions': len(self.video_sessions),
            'active_rooms': len(self.conference_rooms),
            'enabled': self.enabled,
            'aiortc_available': AIORTC_AVAILABLE
        }
