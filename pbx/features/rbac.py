"""
Role-Based Access Control (RBAC) System
Manages user roles and permissions for admin panel access
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from pbx.utils.logger import get_logger
from pbx.utils.encryption import FIPSEncryption

logger = get_logger(__name__)


class Permission:
    """Permission definitions"""
    # Dashboard
    VIEW_DASHBOARD = "view_dashboard"
    
    # Extensions
    VIEW_EXTENSIONS = "view_extensions"
    ADD_EXTENSION = "add_extension"
    EDIT_EXTENSION = "edit_extension"
    DELETE_EXTENSION = "delete_extension"
    
    # Calls
    VIEW_CALLS = "view_calls"
    MONITOR_CALLS = "monitor_calls"
    TERMINATE_CALLS = "terminate_calls"
    
    # Recordings
    VIEW_RECORDINGS = "view_recordings"
    DOWNLOAD_RECORDINGS = "download_recordings"
    DELETE_RECORDINGS = "delete_recordings"
    
    # Voicemail
    VIEW_VOICEMAIL = "view_voicemail"
    DELETE_VOICEMAIL = "delete_voicemail"
    
    # Configuration
    VIEW_CONFIG = "view_config"
    EDIT_CONFIG = "edit_config"
    
    # Reports
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    
    # Users & Roles
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    
    # System
    VIEW_LOGS = "view_logs"
    SYSTEM_ADMIN = "system_admin"


class Role:
    """Predefined role types"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AGENT = "agent"
    VIEWER = "viewer"


class RBACManager:
    """Manages roles and permissions"""
    
    # Default role definitions
    ROLE_PERMISSIONS = {
        Role.SUPER_ADMIN: {
            # Super admin has all permissions
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_EXTENSIONS,
            Permission.ADD_EXTENSION,
            Permission.EDIT_EXTENSION,
            Permission.DELETE_EXTENSION,
            Permission.VIEW_CALLS,
            Permission.MONITOR_CALLS,
            Permission.TERMINATE_CALLS,
            Permission.VIEW_RECORDINGS,
            Permission.DOWNLOAD_RECORDINGS,
            Permission.DELETE_RECORDINGS,
            Permission.VIEW_VOICEMAIL,
            Permission.DELETE_VOICEMAIL,
            Permission.VIEW_CONFIG,
            Permission.EDIT_CONFIG,
            Permission.VIEW_REPORTS,
            Permission.EXPORT_REPORTS,
            Permission.VIEW_USERS,
            Permission.MANAGE_USERS,
            Permission.MANAGE_ROLES,
            Permission.VIEW_LOGS,
            Permission.SYSTEM_ADMIN,
        },
        Role.ADMIN: {
            # Admin can do most things except system administration
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_EXTENSIONS,
            Permission.ADD_EXTENSION,
            Permission.EDIT_EXTENSION,
            Permission.DELETE_EXTENSION,
            Permission.VIEW_CALLS,
            Permission.MONITOR_CALLS,
            Permission.VIEW_RECORDINGS,
            Permission.DOWNLOAD_RECORDINGS,
            Permission.VIEW_VOICEMAIL,
            Permission.DELETE_VOICEMAIL,
            Permission.VIEW_CONFIG,
            Permission.EDIT_CONFIG,
            Permission.VIEW_REPORTS,
            Permission.EXPORT_REPORTS,
            Permission.VIEW_USERS,
        },
        Role.SUPERVISOR: {
            # Supervisor can monitor and manage calls/agents
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_EXTENSIONS,
            Permission.VIEW_CALLS,
            Permission.MONITOR_CALLS,
            Permission.VIEW_RECORDINGS,
            Permission.DOWNLOAD_RECORDINGS,
            Permission.VIEW_VOICEMAIL,
            Permission.VIEW_REPORTS,
            Permission.EXPORT_REPORTS,
        },
        Role.AGENT: {
            # Agent has limited access
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_CALLS,
            Permission.VIEW_VOICEMAIL,
        },
        Role.VIEWER: {
            # Viewer can only view information
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_EXTENSIONS,
            Permission.VIEW_CALLS,
            Permission.VIEW_REPORTS,
        }
    }
    
    def __init__(self, config: dict):
        """Initialize RBAC manager"""
        self.config = config
        self.users_file = Path(config.get('rbac.users_file', 'admin_users.json'))
        self.encryption = FIPSEncryption(config)
        self.users = self._load_users()
        self.sessions = {}  # Active sessions: {token: user_data}
    
    def _load_users(self) -> Dict:
        """Load users from file"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading users file: {e}")
        
        # Create default admin user if no users exist
        default_admin = {
            'admin': {
                'username': 'admin',
                'password_hash': self.encryption.hash_password('admin123'),
                'role': Role.SUPER_ADMIN,
                'email': 'admin@localhost',
                'created_at': datetime.now().isoformat(),
                'enabled': True,
                'custom_permissions': []
            }
        }
        self._save_users(default_admin)
        return default_admin
    
    def _save_users(self, users: Dict = None):
        """Save users to file"""
        try:
            if users is None:
                users = self.users
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users file: {e}")
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user
        Args:
            username: Username
            password: Password
        Returns:
            User data if authenticated, None otherwise
        """
        user = self.users.get(username)
        
        if not user or not user.get('enabled', False):
            return None
        
        password_hash = user.get('password_hash')
        if self.encryption.verify_password(password, password_hash):
            return {
                'username': user['username'],
                'role': user['role'],
                'email': user.get('email'),
                'permissions': self.get_user_permissions(username)
            }
        
        return None
    
    def create_user(self, username: str, password: str, role: str, 
                    email: str = None, custom_permissions: List[str] = None) -> bool:
        """
        Create a new user
        Args:
            username: Username
            password: Password
            role: User role
            email: Email address
            custom_permissions: Additional permissions beyond role
        Returns:
            True if successful
        """
        if username in self.users:
            logger.warning(f"User {username} already exists")
            return False
        
        self.users[username] = {
            'username': username,
            'password_hash': self.encryption.hash_password(password),
            'role': role,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'enabled': True,
            'custom_permissions': custom_permissions or []
        }
        
        self._save_users()
        logger.info(f"User {username} created with role {role}")
        return True
    
    def update_user(self, username: str, **kwargs) -> bool:
        """
        Update user properties
        Args:
            username: Username
            **kwargs: Properties to update
        Returns:
            True if successful
        """
        if username not in self.users:
            return False
        
        user = self.users[username]
        
        # Update allowed fields
        if 'password' in kwargs:
            user['password_hash'] = self.encryption.hash_password(kwargs['password'])
        if 'role' in kwargs:
            user['role'] = kwargs['role']
        if 'email' in kwargs:
            user['email'] = kwargs['email']
        if 'enabled' in kwargs:
            user['enabled'] = kwargs['enabled']
        if 'custom_permissions' in kwargs:
            user['custom_permissions'] = kwargs['custom_permissions']
        
        user['updated_at'] = datetime.now().isoformat()
        
        self._save_users()
        logger.info(f"User {username} updated")
        return True
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user
        Args:
            username: Username
        Returns:
            True if successful
        """
        if username not in self.users:
            return False
        
        # Don't allow deleting the last super admin
        super_admins = [u for u in self.users.values() 
                       if u.get('role') == Role.SUPER_ADMIN and u.get('enabled')]
        if len(super_admins) <= 1 and self.users[username].get('role') == Role.SUPER_ADMIN:
            logger.warning("Cannot delete the last super admin")
            return False
        
        del self.users[username]
        self._save_users()
        logger.info(f"User {username} deleted")
        return True
    
    def get_user_permissions(self, username: str) -> Set[str]:
        """
        Get all permissions for a user
        Args:
            username: Username
        Returns:
            Set of permission strings
        """
        user = self.users.get(username)
        if not user:
            return set()
        
        role = user.get('role', Role.VIEWER)
        permissions = self.ROLE_PERMISSIONS.get(role, set()).copy()
        
        # Add custom permissions
        custom = user.get('custom_permissions', [])
        permissions.update(custom)
        
        return permissions
    
    def has_permission(self, username: str, permission: str) -> bool:
        """
        Check if user has a specific permission
        Args:
            username: Username
            permission: Permission to check
        Returns:
            True if user has permission
        """
        permissions = self.get_user_permissions(username)
        return permission in permissions
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (without sensitive data)"""
        return [
            {
                'username': user['username'],
                'role': user['role'],
                'email': user.get('email'),
                'enabled': user.get('enabled', True),
                'created_at': user.get('created_at')
            }
            for user in self.users.values()
        ]
    
    def create_session(self, username: str) -> str:
        """
        Create a session for authenticated user
        Args:
            username: Username
        Returns:
            Session token
        """
        import secrets
        token = secrets.token_urlsafe(32)
        
        self.sessions[token] = {
            'username': username,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }
        
        return token
    
    def validate_session(self, token: str) -> Optional[str]:
        """
        Validate a session token
        Args:
            token: Session token
        Returns:
            Username if valid, None otherwise
        """
        session = self.sessions.get(token)
        if not session:
            return None
        
        # Check if session is expired (24 hours)
        try:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(hours=24):
                del self.sessions[token]
                return None
        except (ValueError, TypeError):
            return None
        
        # Update last activity
        session['last_activity'] = datetime.now().isoformat()
        
        return session['username']
    
    def destroy_session(self, token: str):
        """Destroy a session"""
        if token in self.sessions:
            del self.sessions[token]
