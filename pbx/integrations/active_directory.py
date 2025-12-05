"""
Active Directory / LDAP Integration
Provides SSO, user provisioning, and group-based permissions
"""
from pbx.utils.logger import get_logger
from typing import Optional, Dict, List
import re
import secrets

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
            
            # Search for user - escape username to prevent LDAP injection
            from ldap3.utils.conv import escape_filter_chars
            safe_username = escape_filter_chars(username)
            search_filter = f"(&(objectClass=user)(sAMAccountName={safe_username}))"
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

    def sync_users(self, extension_registry=None, extension_db=None, phone_provisioning=None):
        """
        Synchronize users from Active Directory

        Args:
            extension_registry: Optional ExtensionRegistry instance for live updates
            extension_db: Optional ExtensionDB instance for database storage
            phone_provisioning: Optional PhoneProvisioning instance to trigger phone reboots

        Returns:
            int: Number of users synchronized
        """
        if not self.enabled or not self.auto_provision or not LDAP3_AVAILABLE:
            return 0

        if not self.connect():
            self.logger.error("Failed to connect to Active Directory")
            return 0

        try:
            self.logger.info("Starting user synchronization from Active Directory...")
            
            # Get user search base
            user_search_base = self.config.get('integrations.active_directory.user_search_base', self.base_dn)
            
            # Search for all users with telephoneNumber attribute
            # Using objectClass=user and filtering for accounts with phone numbers
            search_filter = '(&(objectClass=user)(telephoneNumber=*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
            
            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName', 'mail', 'telephoneNumber', 'memberOf']
            )
            
            if not self.connection.entries:
                self.logger.warning("No users found in Active Directory")
                return 0
            
            self.logger.info(f"Found {len(self.connection.entries)} users in Active Directory")
            
            # Use database if available, otherwise fall back to config.yml
            use_database = extension_db is not None
            
            if use_database:
                self.logger.info("Syncing to database")
            else:
                self.logger.info("Syncing to config.yml (database not available)")
                # Get PBX config for updating extensions
                from pbx.utils.config import Config
                pbx_config = Config(self.config.get('config_file', 'config.yml'))
            
            synced_count = 0
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            # Track extension numbers for deactivation check
            ad_extension_numbers = set()
            
            for entry in self.connection.entries:
                try:
                    username = str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else None
                    display_name = str(entry.displayName) if hasattr(entry, 'displayName') else username
                    email = str(entry.mail) if hasattr(entry, 'mail') else None
                    phone_number = str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') else None
                    
                    # Skip if no username or phone number
                    if not username or not phone_number:
                        self.logger.debug(f"Skipping user {username}: missing required fields")
                        skipped_count += 1
                        continue
                    
                    # Use phone number as extension number (Option A)
                    # Clean phone number to get just digits (remove spaces, dashes, etc.)
                    extension_number = re.sub(r'[^0-9]', '', phone_number)
                    
                    # Validate extension number
                    if not extension_number or len(extension_number) < 3:
                        self.logger.warning(f"Skipping user {username}: invalid extension number from phone {phone_number}")
                        skipped_count += 1
                        continue
                    
                    ad_extension_numbers.add(extension_number)
                    
                    # Check if extension exists (database or config depending on mode)
                    if use_database:
                        existing_ext = extension_db.get(extension_number)
                    else:
                        existing_ext = pbx_config.get_extension(extension_number)
                    
                    if existing_ext:
                        # Update existing extension
                        self.logger.debug(f"Updating extension {extension_number} for user {username}")
                        
                        if use_database:
                            # Update in database
                            success = extension_db.update(
                                number=extension_number,
                                name=display_name,
                                email=email,
                                ad_synced=True,
                                ad_username=username
                                # Don't update password - keep existing
                            )
                        else:
                            # Update in config.yml
                            success = pbx_config.update_extension(
                                number=extension_number,
                                name=display_name,
                                email=email
                                # Don't update password - keep existing
                            )
                            if success:
                                # Mark as AD-synced in config
                                existing_ext['ad_synced'] = True
                        
                        if success:
                            updated_count += 1
                            synced_count += 1
                            
                            # Update in live registry if provided
                            if extension_registry:
                                ext = extension_registry.get(extension_number)
                                if ext:
                                    ext.name = display_name
                                    if email:
                                        ext.config['email'] = email
                                    ext.config['ad_synced'] = True
                        else:
                            self.logger.warning(f"Failed to update extension {extension_number}")
                    else:
                        # Create new extension with random 4-digit password
                        # Note: 4-digit passwords meet user requirement but provide limited security
                        # Consider using longer passwords for production environments
                        random_password = ''.join([str(secrets.randbelow(10)) for _ in range(4)])
                        
                        # Log extension creation without exposing password
                        self.logger.info(f"Creating extension {extension_number} for user {username}")
                        # Password can be retrieved from database or reset via admin interface
                        
                        if use_database:
                            # Add to database
                            # TODO: Implement proper password hashing (bcrypt/PBKDF2) for production
                            password_hash = random_password
                            success = extension_db.add(
                                number=extension_number,
                                name=display_name,
                                email=email or None,
                                password_hash=password_hash,
                                allow_external=True,
                                voicemail_pin=None,
                                ad_synced=True,
                                ad_username=username
                            )
                        else:
                            # Add to config.yml
                            success = pbx_config.add_extension(
                                number=extension_number,
                                name=display_name,
                                email=email or '',
                                password=random_password,
                                allow_external=True
                            )
                            if success:
                                # Mark newly created extension as AD-synced
                                new_ext_config = pbx_config.get_extension(extension_number)
                                if new_ext_config:
                                    new_ext_config['ad_synced'] = True
                        
                        if success:
                            created_count += 1
                            synced_count += 1
                            
                            # Add to live registry if provided
                            if extension_registry:
                                from pbx.features.extensions import Extension
                                new_ext = Extension(
                                    extension_number,
                                    display_name,
                                    {
                                        'number': extension_number,
                                        'name': display_name,
                                        'email': email or '',
                                        'password': random_password,
                                        'allow_external': True,
                                        'ad_synced': True
                                    }
                                )
                                extension_registry.extensions[extension_number] = new_ext
                        else:
                            self.logger.warning(f"Failed to create extension {extension_number}")
                    
                    # TODO: Map AD groups to PBX roles/permissions
                    # This is marked for future implementation per user request
                    # groups = [str(g) for g in entry.memberOf] if hasattr(entry, 'memberOf') else []
                    
                except Exception as e:
                    user_desc = username if username else "unknown"
                    self.logger.error(f"Error syncing user {user_desc}: {e}")
                    continue
            
            # Deactivate extensions for users removed from AD
            deactivated_count = 0
            if self.config.get('integrations.active_directory.deactivate_removed_users', True):
                self.logger.info("Checking for removed users to deactivate...")
                
                if use_database:
                    # Get all AD-synced extensions from database
                    all_extensions = extension_db.get_ad_synced()
                else:
                    # Get all extensions from config
                    all_extensions = pbx_config.get_extensions()
                
                for ext in all_extensions:
                    ext_number = ext.get('number')
                    # Only check extensions that could be AD-synced (numeric, reasonable length)
                    if ext_number and ext_number.isdigit() and len(ext_number) >= 3:
                        if ext_number not in ad_extension_numbers:
                            # Check if extension has AD metadata marker
                            if ext.get('ad_synced', False):
                                self.logger.info(f"Deactivating extension {ext_number} (user removed from AD)")
                                # Mark as inactive instead of deleting
                                # Keep ad_synced=True so we know it was previously managed by AD
                                
                                if use_database:
                                    extension_db.update(
                                        number=ext_number,
                                        allow_external=False
                                    )
                                else:
                                    pbx_config.update_extension(
                                        number=ext_number,
                                        allow_external=False
                                    )
                                
                                if extension_registry:
                                    registry_ext = extension_registry.get(ext_number)
                                    if registry_ext:
                                        registry_ext.config['allow_external'] = False
                                        # Keep ad_synced=True to maintain history
                                deactivated_count += 1
            
            # Save all changes (only needed for config.yml mode)
            if not use_database:
                pbx_config.save()
            
            self.logger.info(
                f"User synchronization complete: "
                f"{synced_count} total, {created_count} created, {updated_count} updated, "
                f"{deactivated_count} deactivated, {skipped_count} skipped"
            )
            
            # Trigger phone reboots if provisioning is available and users were updated
            # This ensures phones fetch fresh config with updated display names from AD
            if phone_provisioning and (updated_count > 0 or created_count > 0):
                self.logger.info("Triggering phone reboots to update display names from AD sync...")
                reboot_config = self.config.get('integrations.active_directory.reboot_phones_after_sync', False)
                
                if reboot_config:
                    # Find extensions that have provisioned devices and were updated
                    devices_to_reboot = []
                    for device in phone_provisioning.get_all_devices():
                        if device.extension_number in ad_extension_numbers:
                            devices_to_reboot.append(device.extension_number)
                    
                    if devices_to_reboot:
                        self.logger.info(f"Rebooting {len(devices_to_reboot)} phones to apply AD name changes")
                        # Note: This requires SIP server to be available
                        # The actual reboot will be triggered via SIP NOTIFY in the API handler
                    else:
                        self.logger.info("No provisioned devices found for updated extensions")
                else:
                    self.logger.info("Automatic phone reboot is disabled. Set 'integrations.active_directory.reboot_phones_after_sync: true' to enable")
                    self.logger.info("To manually update phone display names, reboot phones or call: POST /api/phones/reboot")
            
            return synced_count
            
        except Exception as e:
            self.logger.error(f"Error synchronizing users from Active Directory: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def get_user_groups(self, username: str):
        """
        Get Active Directory groups for a user

        Args:
            username: Username

        Returns:
            list: List of group names
        """
        if not self.enabled or not LDAP3_AVAILABLE:
            return []

        if not self.connect():
            return []

        try:
            self.logger.info(f"Getting groups for user: {username}")
            
            # Search for user - escape username to prevent LDAP injection
            from ldap3.utils.conv import escape_filter_chars
            safe_username = escape_filter_chars(username)
            search_filter = f"(&(objectClass=user)(sAMAccountName={safe_username}))"
            user_search_base = self.config.get('integrations.active_directory.user_search_base', self.base_dn)
            
            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['memberOf']
            )
            
            if not self.connection.entries:
                self.logger.warning(f"User not found: {username}")
                return []
            
            user_entry = self.connection.entries[0]
            
            # Extract group names from DNs
            groups = []
            if hasattr(user_entry, 'memberOf'):
                for group_dn in user_entry.memberOf:
                    # Extract CN from DN (e.g., "CN=Sales,OU=Groups,DC=domain,DC=local" -> "Sales")
                    dn_str = str(group_dn)
                    if dn_str.startswith('CN='):
                        cn_end = dn_str.find(',')
                        if cn_end > 0:
                            group_name = dn_str[3:cn_end]
                            groups.append(group_name)
            
            self.logger.info(f"Found {len(groups)} groups for user {username}")
            return groups
            
        except Exception as e:
            self.logger.error(f"Error getting groups for user {username}: {e}")
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
            
            # Escape query to prevent LDAP injection
            from ldap3.utils.conv import escape_filter_chars
            safe_query = escape_filter_chars(query)
            
            # Build search filter for multiple attributes
            search_filter = (
                f"(&(objectClass=user)"
                f"(|(cn=*{safe_query}*)(displayName=*{safe_query}*)"
                f"(mail=*{safe_query}*)(telephoneNumber=*{safe_query}*)))"
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
        if not self.enabled or not LDAP3_AVAILABLE:
            return None

        if not self.connect():
            return None

        try:
            self.logger.info(f"Getting photo for user: {username}")
            
            # Search for user - escape username to prevent LDAP injection
            from ldap3.utils.conv import escape_filter_chars
            safe_username = escape_filter_chars(username)
            search_filter = f"(&(objectClass=user)(sAMAccountName={safe_username}))"
            user_search_base = self.config.get('integrations.active_directory.user_search_base', self.base_dn)
            
            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['thumbnailPhoto']
            )
            
            if not self.connection.entries:
                self.logger.warning(f"User not found: {username}")
                return None
            
            user_entry = self.connection.entries[0]
            
            # Return photo bytes if available
            if hasattr(user_entry, 'thumbnailPhoto') and user_entry.thumbnailPhoto.value:
                photo_data = user_entry.thumbnailPhoto.value
                self.logger.info(f"Retrieved photo for user {username} ({len(photo_data)} bytes)")
                return photo_data
            else:
                self.logger.info(f"No photo available for user {username}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error getting photo for user {username}: {e}")
            return None
