"""
Hot-Desking Feature
Allows users to log in from any phone and retain their settings
"""
import threading
from datetime import datetime
from typing import Dict, Optional, List
from pbx.utils.logger import get_logger


class HotDeskSession:
    """Represents a hot desk session"""
    
    def __init__(self, extension: str, device_id: str, ip_address: str):
        """
        Initialize hot desk session
        
        Args:
            extension: Extension number
            device_id: Device identifier (MAC address or UUID)
            ip_address: Device IP address
        """
        self.extension = extension
        self.device_id = device_id
        self.ip_address = ip_address
        self.logged_in_at = datetime.now()
        self.last_activity = datetime.now()
        self.auto_logout_enabled = True
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'extension': self.extension,
            'device_id': self.device_id,
            'ip_address': self.ip_address,
            'logged_in_at': self.logged_in_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'auto_logout_enabled': self.auto_logout_enabled
        }


class HotDeskingSystem:
    """
    Hot-Desking System
    
    Provides:
    - Dynamic extension assignment to devices
    - User login/logout from any phone
    - Session management
    - Auto-logout after inactivity
    - Extension profile migration
    """
    
    def __init__(self, config=None, pbx_core=None):
        """
        Initialize hot-desking system
        
        Args:
            config: Configuration object
            pbx_core: PBX core instance
        """
        self.logger = get_logger()
        self.config = config or {}
        self.pbx_core = pbx_core
        
        # Hot-desking configuration
        self.enabled = self._get_config('features.hot_desking.enabled', False)
        self.auto_logout_timeout = self._get_config('features.hot_desking.auto_logout_timeout', 28800)  # 8 hours
        self.require_pin = self._get_config('features.hot_desking.require_pin', True)
        self.allow_concurrent_logins = self._get_config('features.hot_desking.allow_concurrent_logins', False)
        
        # Active sessions
        self.sessions: Dict[str, HotDeskSession] = {}  # device_id -> session
        self.extension_devices: Dict[str, List[str]] = {}  # extension -> list of device_ids
        self.lock = threading.Lock()
        
        # Cleanup thread
        self.running = False
        self.cleanup_thread = None
        
        if self.enabled:
            self.logger.info("Hot-desking system enabled")
            self._start_cleanup_thread()
        else:
            self.logger.info("Hot-desking system disabled")
    
    def _get_config(self, key: str, default=None):
        """Get configuration value"""
        if hasattr(self.config, 'get'):
            return self.config.get(key, default)
        return default
    
    def _start_cleanup_thread(self):
        """Start auto-logout cleanup thread"""
        self.running = True
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="HotDeskCleanup",
            daemon=True
        )
        self.cleanup_thread.start()
        self.logger.info("Started hot-desking auto-logout thread")
    
    def stop(self):
        """Stop the hot-desking system"""
        self.logger.info("Stopping hot-desking system...")
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        self.logger.info("Hot-desking system stopped")
    
    def _cleanup_worker(self):
        """Worker thread for auto-logout"""
        import time
        while self.running:
            time.sleep(60)  # Check every minute
            self._auto_logout_inactive_sessions()
    
    def _auto_logout_inactive_sessions(self):
        """Automatically log out inactive sessions"""
        with self.lock:
            now = datetime.now()
            sessions_to_logout = []
            
            for device_id, session in self.sessions.items():
                if not session.auto_logout_enabled:
                    continue
                
                inactive_time = (now - session.last_activity).total_seconds()
                if inactive_time > self.auto_logout_timeout:
                    sessions_to_logout.append(device_id)
            
            for device_id in sessions_to_logout:
                session = self.sessions.get(device_id)
                if session:
                    inactive_time = (now - session.last_activity).total_seconds()
                    self.logger.info(f"Auto-logout: {session.extension} from {device_id} (inactive for {inactive_time:.0f}s)")
                    self._logout_internal(device_id)
    
    def login(self, extension: str, device_id: str, ip_address: str, pin: Optional[str] = None) -> bool:
        """
        Log in extension to device
        
        Args:
            extension: Extension number
            device_id: Device identifier
            ip_address: Device IP address
            pin: Optional PIN for authentication
            
        Returns:
            True if login successful, False otherwise
        """
        if not self.enabled:
            self.logger.warning("Hot-desking is not enabled")
            return False
        
        # Verify extension exists
        if self.pbx_core and hasattr(self.pbx_core, 'extension_registry'):
            ext_obj = self.pbx_core.extension_registry.get_extension(extension)
            if not ext_obj:
                self.logger.warning(f"Login failed: Extension {extension} not found")
                return False
            
            # Verify PIN if required
            if self.require_pin:
                if not pin:
                    self.logger.warning(f"Login failed: PIN required for {extension}")
                    return False
                
                # Check voicemail PIN (extensions typically use same PIN)
                voicemail_pin = ext_obj.get('voicemail_pin')
                if voicemail_pin and pin != voicemail_pin:
                    self.logger.warning(f"Login failed: Invalid PIN for {extension}")
                    return False
        else:
            self.logger.warning("Extension registry not available")
            return False
        
        with self.lock:
            # Check if device already has a session
            if device_id in self.sessions:
                existing_session = self.sessions[device_id]
                if existing_session.extension != extension:
                    self.logger.info(f"Logging out {existing_session.extension} from {device_id} before new login")
                    self._logout_internal(device_id)
            
            # Check if extension is already logged in elsewhere
            if not self.allow_concurrent_logins:
                if extension in self.extension_devices and len(self.extension_devices[extension]) > 0:
                    existing_devices = self.extension_devices[extension]
                    self.logger.info(f"Extension {extension} already logged in at {existing_devices}, logging out...")
                    for dev_id in existing_devices.copy():
                        self._logout_internal(dev_id)
            
            # Create new session
            session = HotDeskSession(extension, device_id, ip_address)
            self.sessions[device_id] = session
            
            # Track extension devices
            if extension not in self.extension_devices:
                self.extension_devices[extension] = []
            self.extension_devices[extension].append(device_id)
            
            self.logger.info(f"Hot-desk login: {extension} logged in to {device_id} ({ip_address})")
            
            # Trigger webhook event
            if self.pbx_core and hasattr(self.pbx_core, 'webhook_system'):
                self.pbx_core.webhook_system.trigger_event('hot_desk.login', {
                    'extension': extension,
                    'device_id': device_id,
                    'ip_address': ip_address,
                    'timestamp': session.logged_in_at.isoformat()
                })
            
            return True
    
    def logout(self, device_id: str) -> bool:
        """
        Log out extension from device
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if logout successful, False otherwise
        """
        if not self.enabled:
            return False
        
        with self.lock:
            return self._logout_internal(device_id)
    
    def _logout_internal(self, device_id: str) -> bool:
        """Internal logout (assumes lock is held)"""
        session = self.sessions.get(device_id)
        if not session:
            self.logger.debug(f"Logout failed: No session for device {device_id}")
            return False
        
        extension = session.extension
        
        # Remove session
        del self.sessions[device_id]
        
        # Remove from extension tracking
        if extension in self.extension_devices:
            if device_id in self.extension_devices[extension]:
                self.extension_devices[extension].remove(device_id)
            if not self.extension_devices[extension]:
                del self.extension_devices[extension]
        
        self.logger.info(f"Hot-desk logout: {extension} logged out from {device_id}")
        
        # Trigger webhook event
        if self.pbx_core and hasattr(self.pbx_core, 'webhook_system'):
            self.pbx_core.webhook_system.trigger_event('hot_desk.logout', {
                'extension': extension,
                'device_id': device_id,
                'timestamp': datetime.now().isoformat()
            })
        
        return True
    
    def logout_extension(self, extension: str) -> int:
        """
        Log out extension from all devices
        
        Args:
            extension: Extension number
            
        Returns:
            Number of devices logged out
        """
        if not self.enabled:
            return 0
        
        with self.lock:
            devices = self.extension_devices.get(extension, []).copy()
            count = 0
            
            for device_id in devices:
                if self._logout_internal(device_id):
                    count += 1
            
            return count
    
    def get_session(self, device_id: str) -> Optional[HotDeskSession]:
        """Get session for device"""
        with self.lock:
            return self.sessions.get(device_id)
    
    def get_extension_session(self, extension: str) -> Optional[HotDeskSession]:
        """Get session for extension (first device if multiple)"""
        with self.lock:
            devices = self.extension_devices.get(extension, [])
            if devices:
                return self.sessions.get(devices[0])
            return None
    
    def get_extension_devices(self, extension: str) -> List[str]:
        """Get all devices where extension is logged in"""
        with self.lock:
            return self.extension_devices.get(extension, []).copy()
    
    def is_logged_in(self, extension: str) -> bool:
        """Check if extension is logged in anywhere"""
        with self.lock:
            return extension in self.extension_devices and len(self.extension_devices[extension]) > 0
    
    def update_session_activity(self, device_id: str):
        """Update session activity timestamp"""
        with self.lock:
            session = self.sessions.get(device_id)
            if session:
                session.update_activity()
    
    def set_auto_logout(self, device_id: str, enabled: bool) -> bool:
        """Enable or disable auto-logout for a session"""
        with self.lock:
            session = self.sessions.get(device_id)
            if session:
                session.auto_logout_enabled = enabled
                return True
            return False
    
    def get_active_sessions(self) -> List[Dict]:
        """Get all active sessions"""
        with self.lock:
            return [session.to_dict() for session in self.sessions.values()]
    
    def get_session_count(self) -> int:
        """Get count of active sessions"""
        with self.lock:
            return len(self.sessions)
    
    def get_extension_profile(self, extension: str) -> Optional[Dict]:
        """
        Get extension profile for migration to device
        
        Args:
            extension: Extension number
            
        Returns:
            Extension profile dictionary
        """
        if not self.pbx_core or not hasattr(self.pbx_core, 'extension_registry'):
            return None
        
        ext_obj = self.pbx_core.extension_registry.get_extension(extension)
        if not ext_obj:
            return None
        
        # Return profile (without sensitive data like passwords)
        profile = {
            'extension': extension,
            'name': ext_obj.get('name'),
            'email': ext_obj.get('email'),
            'allow_external': ext_obj.get('allow_external', True),
            'voicemail_enabled': True,  # Assume voicemail is always enabled
            'call_forwarding': ext_obj.get('call_forwarding'),
            'do_not_disturb': ext_obj.get('do_not_disturb', False)
        }
        
        return profile
