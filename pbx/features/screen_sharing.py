"""
Screen Sharing Support
Provides collaborative screen sharing using WebRTC data channels (free)
"""
from datetime import datetime
from typing import Dict, Optional, List
from pbx.utils.logger import get_logger


class ScreenSharingService:
    """Screen sharing service using WebRTC data channels"""
    
    def __init__(self, config=None):
        """Initialize screen sharing service"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('features', {}).get('screen_sharing', {}).get('enabled', False)
        self.sharing_sessions = {}  # session_id -> sharing info
        
        if self.enabled:
            self.logger.info("Screen sharing service initialized")
    
    def start_sharing(self, session_id: str, user_id: str, room_id: Optional[str] = None) -> Dict:
        """
        Start screen sharing session
        
        Args:
            session_id: Unique session identifier
            user_id: User who is sharing
            room_id: Optional room/conference ID
            
        Returns:
            Sharing session information
        """
        if not self.enabled:
            return {'error': 'Screen sharing not enabled'}
        
        self.sharing_sessions[session_id] = {
            'user_id': user_id,
            'room_id': room_id,
            'started_at': datetime.now(),
            'viewers': [],
            'resolution': None,  # Will be set by client
            'frame_rate': None
        }
        
        self.logger.info(f"User {user_id} started screen sharing (session {session_id})")
        
        return {
            'session_id': session_id,
            'status': 'started',
            'user_id': user_id
        }
    
    def stop_sharing(self, session_id: str) -> bool:
        """Stop screen sharing session"""
        if session_id in self.sharing_sessions:
            session = self.sharing_sessions[session_id]
            self.logger.info(f"User {session['user_id']} stopped screen sharing (session {session_id})")
            del self.sharing_sessions[session_id]
            return True
        return False
    
    def add_viewer(self, session_id: str, viewer_id: str) -> bool:
        """Add a viewer to a screen sharing session"""
        if session_id in self.sharing_sessions:
            viewers = self.sharing_sessions[session_id]['viewers']
            if viewer_id not in viewers:
                viewers.append(viewer_id)
                self.logger.info(f"Viewer {viewer_id} joined screen sharing session {session_id}")
            return True
        return False
    
    def remove_viewer(self, session_id: str, viewer_id: str) -> bool:
        """Remove a viewer from a screen sharing session"""
        if session_id in self.sharing_sessions:
            viewers = self.sharing_sessions[session_id]['viewers']
            if viewer_id in viewers:
                viewers.remove(viewer_id)
                self.logger.info(f"Viewer {viewer_id} left screen sharing session {session_id}")
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a screen sharing session"""
        if session_id in self.sharing_sessions:
            session = self.sharing_sessions[session_id]
            return {
                'session_id': session_id,
                'user_id': session['user_id'],
                'room_id': session['room_id'],
                'started_at': session['started_at'].isoformat(),
                'viewer_count': len(session['viewers']),
                'viewers': session['viewers']
            }
        return None
    
    def list_active_sessions(self, room_id: Optional[str] = None) -> List[Dict]:
        """List all active screen sharing sessions"""
        sessions = []
        for session_id, session in self.sharing_sessions.items():
            if room_id is None or session['room_id'] == room_id:
                sessions.append({
                    'session_id': session_id,
                    'user_id': session['user_id'],
                    'room_id': session['room_id'],
                    'viewer_count': len(session['viewers'])
                })
        return sessions
    
    def get_statistics(self) -> Dict:
        """Get screen sharing statistics"""
        total_viewers = sum(len(s['viewers']) for s in self.sharing_sessions.values())
        return {
            'active_sessions': len(self.sharing_sessions),
            'total_viewers': total_viewers,
            'enabled': self.enabled
        }
