"""
Active Directory / LDAP Integration
Provides SSO, user provisioning, and group-based permissions
"""
from pbx.utils.logger import get_logger
from typing import Optional, Dict, List

try:
    import ldap3
    from ldap3 import Server, Connection, ALL, SUBTREE
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False


class ActiveDirectoryIntegration:
    """Active Directory / LDAP integration handler"""

    def __init__(self, config: dict):
        """
        Initialize Active Directory integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get('integrations.active_directory.enabled', False)
        self.ldap_server = config.get('integrations.active_directory.server', 
                                      config.get('integrations.active_directory.ldap_server'))
        self.base_dn = config.get('integrations.active_directory.base_dn')
        self.bind_dn = config.get('integrations.active_directory.bind_dn')
        self.bind_password = config.get('integrations.active_directory.bind_password')
        self.use_ssl = config.get('integrations.active_directory.use_ssl', True)
        self.auto_provision = config.get('integrations.active_directory.auto_provision', False)
        self.connection = None
        self.server = None

        if self.enabled:
            if not LDAP3_AVAILABLE:
                self.logger.error("Active Directory integration requires 'ldap3' library. Install with: pip install ldap3")
                self.enabled = False
            else:
                self.logger.info("Active Directory integration enabled")

    def connect(self) -> bool:
        """
        Connect to Active Directory server

        Returns:
            bool: True if connection successful
        """
        if not self.enabled or not LDAP3_AVAILABLE:
            return False

        if self.connection and self.connection.bound:
            return True

        if not all([self.ldap_server, self.base_dn, self.bind_dn, self.bind_password]):
            self.logger.error("Active Directory credentials not configured properly")
            return False

        try:
            self.logger.info(f"Connecting to Active Directory: {self.ldap_server}")
            
            # Create server object
            self.server = Server(self.ldap_server, get_info=ALL, use_ssl=self.use_ssl)
            
            # Create connection
            self.connection = Connection(
                self.server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True,
                raise_exceptions=True
            )
            
            if self.connection.bound:
                self.logger.info("Successfully connected to Active Directory")
                return True
            else:
                self.logger.error("Failed to bind to Active Directory")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to Active Directory: {e}")
            self.connection = None
            return False

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user against Active Directory

        Args:
            username: Username (SAM account name or UPN)
            password: User's password

        Returns:
            dict: User information if authenticated, None otherwise
        """
        if not self.enabled or not LDAP3_AVAILABLE:
            return None

        if not self.connect():
            return None

        try:
            self.logger.info(f"Authenticating user: {username}")
            
            # Search for user
            search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
            user_search_base = self.config.get('integrations.active_directory.user_search_base', self.base_dn)
            
            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName', 'mail', 'telephoneNumber', 'memberOf']
            )
            
            if not self.connection.entries:
                self.logger.warning(f"User not found: {username}")
                return None
            
            user_entry = self.connection.entries[0]
            user_dn = user_entry.entry_dn
            
            # Attempt to bind with user credentials
            user_conn = Connection(
                self.server,
                user=user_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=True
            )
            
            if user_conn.bound:
                self.logger.info(f"User authenticated successfully: {username}")
                user_conn.unbind()
                
                # Return user information
                return {
                    'username': str(user_entry.sAMAccountName),
                    'display_name': str(user_entry.displayName) if hasattr(user_entry, 'displayName') else username,
                    'email': str(user_entry.mail) if hasattr(user_entry, 'mail') else None,
                    'phone': str(user_entry.telephoneNumber) if hasattr(user_entry, 'telephoneNumber') else None,
                    'groups': [str(g) for g in user_entry.memberOf] if hasattr(user_entry, 'memberOf') else []
                }
            else:
                self.logger.warning(f"Authentication failed for user: {username}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error authenticating user {username}: {e}")
            return None

    def sync_users(self):
        """
        Synchronize users from Active Directory

        Returns:
            int: Number of users synchronized
        """
        if not self.enabled or not self.auto_provision:
            return 0

        self.logger.info("Syncing users from Active Directory...")
        # TODO: Query AD for users and create/update PBX extensions
        # 1. Search for users in specified OU
        # 2. Extract phone number, email, name
        # 3. Create or update PBX extensions
        # 4. Map AD groups to PBX roles

        return 0

    def get_user_groups(self, username: str):
        """
        Get Active Directory groups for a user

        Args:
            username: Username

        Returns:
            list: List of group names
        """
        if not self.enabled:
            return []

        # TODO: Query user's memberOf attribute
        # Return list of group DNs or group names

        return []

    def search_users(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Search for users in Active Directory

        Args:
            query: Search query (name, phone, email)
            max_results: Maximum number of results

        Returns:
            list: List of user dictionaries
        """
        if not self.enabled or not LDAP3_AVAILABLE:
            return []

        if not self.connect():
            return []

        try:
            self.logger.info(f"Searching AD for: {query}")
            
            # Build search filter for multiple attributes
            search_filter = (
                f"(&(objectClass=user)"
                f"(|(cn=*{query}*)(displayName=*{query}*)"
                f"(mail=*{query}*)(telephoneNumber=*{query}*)))"
            )
            
            user_search_base = self.config.get('integrations.active_directory.user_search_base', self.base_dn)
            
            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName', 'mail', 'telephoneNumber'],
                size_limit=max_results
            )
            
            results = []
            for entry in self.connection.entries:
                results.append({
                    'username': str(entry.sAMAccountName),
                    'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else str(entry.sAMAccountName),
                    'email': str(entry.mail) if hasattr(entry, 'mail') else None,
                    'phone': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') else None
                })
            
            self.logger.info(f"Found {len(results)} users matching: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching users: {e}")
            return []

    def get_user_photo(self, username: str):
        """
        Get user's photo from Active Directory

        Args:
            username: Username

        Returns:
            bytes: Photo data (JPEG) or None
        """
        if not self.enabled:
            return None

        # TODO: Query thumbnailPhoto attribute

        return None
