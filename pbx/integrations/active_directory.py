"""
Active Directory / LDAP Integration
Provides SSO, user provisioning, and group-based permissions
"""

import re
import secrets

from pbx.utils.logger import get_logger

try:
    from ldap3 import ALL, SUBTREE, Connection, Server
    from ldap3.core.exceptions import LDAPException

    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False
    LDAPException = Exception  # Fallback so type references don't break


class ActiveDirectoryIntegration:
    """Active Directory / LDAP integration handler"""

    def __init__(self, config: dict) -> None:
        """
        Initialize Active Directory integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get("integrations.active_directory.enabled", False)
        self.ldap_server = config.get(
            "integrations.active_directory.server",
            config.get("integrations.active_directory.ldap_server"),
        )
        self.base_dn = config.get("integrations.active_directory.base_dn")
        self.bind_dn = config.get("integrations.active_directory.bind_dn")
        self.bind_password = config.get("integrations.active_directory.bind_password")
        self.use_ssl = config.get("integrations.active_directory.use_ssl", True)
        self.auto_provision = config.get("integrations.active_directory.auto_provision", False)
        self.connection: object | None = None
        self.server: object | None = None

        if self.enabled:
            if not LDAP3_AVAILABLE:
                self.logger.error(
                    "Active Directory integration requires 'ldap3' library. Install with: pip install ldap3"
                )
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

            # Create server object with connection timeout
            self.server = Server(
                self.ldap_server,
                get_info=ALL,
                use_ssl=self.use_ssl,
                connect_timeout=10,
            )

            # Create connection with receive timeout
            self.connection = Connection(
                self.server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True,
                raise_exceptions=True,
                receive_timeout=10,
            )

            if self.connection.bound:
                self.logger.info("Successfully connected to Active Directory")
                return True
            self.logger.error("Failed to bind to Active Directory")
            return False

        except LDAPException as e:
            self.logger.error(f"LDAP error connecting to Active Directory: {e}")
            self.connection = None
            return False
        except (OSError, ValueError) as e:
            self.logger.error(f"Error connecting to Active Directory: {e}")
            self.connection = None
            return False

    def authenticate_user(self, username: str, password: str) -> dict | None:
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
            user_search_base = self.config.get(
                "integrations.active_directory.user_search_base", self.base_dn
            )

            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["sAMAccountName", "displayName", "mail", "telephoneNumber", "memberOf"],
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
                raise_exceptions=True,
                receive_timeout=10,
            )

            if user_conn.bound:
                self.logger.info(f"User authenticated successfully: {username}")
                user_conn.unbind()

                # Return user information
                return {
                    "username": str(user_entry.sAMAccountName),
                    "display_name": (
                        str(user_entry.displayName)
                        if hasattr(user_entry, "displayName")
                        else username
                    ),
                    "email": str(user_entry.mail) if hasattr(user_entry, "mail") else None,
                    "phone": (
                        str(user_entry.telephoneNumber)
                        if hasattr(user_entry, "telephoneNumber")
                        else None
                    ),
                    "groups": (
                        [str(g) for g in user_entry.memberOf]
                        if hasattr(user_entry, "memberOf")
                        else []
                    ),
                }
            self.logger.warning(f"Authentication failed for user: {username}")
            return None

        except LDAPException as e:
            self.logger.error(f"LDAP error authenticating user {username}: {e}")
            return None
        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error authenticating user {username}: {e}")
            return None

    def sync_users(
        self,
        extension_registry: object | None = None,
        extension_db: object | None = None,
        phone_provisioning: object | None = None,
    ) -> dict | int:
        """
        Synchronize users from Active Directory

        Args:
            extension_registry: Optional ExtensionRegistry instance for live updates
            extension_db: Optional ExtensionDB instance for database storage
            phone_provisioning: Optional PhoneProvisioning instance to trigger phone reboots

        Returns:
            int: Number of users synchronized
        """
        import sys
        print(f"[AD-DEBUG] sync_users called: enabled={self.enabled}, auto_provision={self.auto_provision}, ldap3={LDAP3_AVAILABLE}", file=sys.stderr, flush=True)

        if not self.enabled or not self.auto_provision or not LDAP3_AVAILABLE:
            print(f"[AD-DEBUG] SKIPPED: enabled={self.enabled}, auto_provision={self.auto_provision}, ldap3={LDAP3_AVAILABLE}", file=sys.stderr, flush=True)
            return 0

        if not self.connect():
            print("[AD-DEBUG] FAILED TO CONNECT", file=sys.stderr, flush=True)
            return 0

        try:
            print("[AD-DEBUG] Starting LDAP search...", file=sys.stderr, flush=True)

            # Get user search base
            user_search_base = self.config.get(
                "integrations.active_directory.user_search_base", self.base_dn
            )
            print(f"[AD-DEBUG] Search base: {user_search_base}", file=sys.stderr, flush=True)

            # Determine which AD attribute holds the extension number
            extension_attr = self.config.get(
                "integrations.active_directory.extension_attribute", "telephoneNumber"
            )
            print(f"[AD-DEBUG] Extension attr: {extension_attr}", file=sys.stderr, flush=True)

            # Search for enabled users that have the extension attribute set
            # Also search for ipPhone as a fallback if using telephoneNumber
            if extension_attr == "telephoneNumber":
                phone_filter = "(|(telephoneNumber=*)(ipPhone=*))"
            else:
                phone_filter = f"({extension_attr}=*)"
            search_filter = f"(&(objectClass=user){phone_filter}(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"

            search_attrs = [
                "sAMAccountName", "displayName", "mail",
                "telephoneNumber", "ipPhone", "memberOf",
            ]
            # Include the configured attribute if it's custom
            if extension_attr not in search_attrs:
                search_attrs.append(extension_attr)

            print(f"[AD-DEBUG] LDAP filter: {search_filter}", file=sys.stderr, flush=True)
            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=search_attrs,
            )
            print(f"[AD-DEBUG] LDAP returned {len(self.connection.entries)} entries", file=sys.stderr, flush=True)

            if not self.connection.entries:
                print("[AD-DEBUG] No entries found, returning 0", file=sys.stderr, flush=True)
                return {"synced_count": 0, "extensions_to_reboot": []}

            self.logger.info(f"Found {len(self.connection.entries)} users in Active Directory")

            # Use database if available, otherwise fall back to config.yml
            use_database = extension_db is not None

            if use_database:
                self.logger.info("Syncing to database")
            else:
                self.logger.info("Syncing to config.yml (database not available)")
                # Get PBX config for updating extensions
                from pbx.utils.config import Config

                pbx_config = Config(self.config.get("config_file", "config.yml"))

            synced_count = 0
            created_count = 0
            updated_count = 0
            skipped_count = 0

            # Track extension numbers for deactivation check
            ad_extension_numbers = set()

            for entry in self.connection.entries:
                try:
                    username = (
                        str(entry.sAMAccountName) if hasattr(entry, "sAMAccountName") else None
                    )
                    display_name = (
                        str(entry.displayName) if hasattr(entry, "displayName") else username
                    )
                    email = str(entry.mail) if hasattr(entry, "mail") else None

                    # Get extension number: try configured attribute, then
                    # ipPhone, then telephoneNumber
                    phone_number = None
                    has_ext_attr = hasattr(entry, extension_attr)
                    has_ipphone = hasattr(entry, "ipPhone")
                    has_telephone = hasattr(entry, "telephoneNumber")
                    ext_val = entry[extension_attr].value if has_ext_attr else None
                    ip_val = entry.ipPhone.value if has_ipphone else None
                    tel_val = entry.telephoneNumber.value if has_telephone else None
                    print(f"[AD-DEBUG] User {username}: ext_attr={ext_val}, ipPhone={ip_val}, tel={tel_val}", file=sys.stderr, flush=True)

                    if has_ext_attr and ext_val:
                        phone_number = str(entry[extension_attr])
                    elif has_ipphone and ip_val:
                        phone_number = str(entry.ipPhone)
                    elif has_telephone and tel_val:
                        phone_number = str(entry.telephoneNumber)

                    # Skip if no username or phone number
                    if not username or not phone_number:
                        print(f"[AD-DEBUG] SKIP {username}: no phone number", file=sys.stderr, flush=True)
                        skipped_count += 1
                        continue

                    # Clean phone number to get just digits (remove spaces,
                    # dashes, etc.)
                    extension_number = re.sub(r"[^0-9]", "", phone_number)
                    print(f"[AD-DEBUG] User {username}: phone={phone_number} -> ext={extension_number}", file=sys.stderr, flush=True)

                    # Validate extension number
                    if not extension_number or len(extension_number) < 3:
                        self.logger.warning(
                            f"Skipping user {username}: invalid extension number from phone {phone_number}"
                        )
                        skipped_count += 1
                        continue

                    ad_extension_numbers.add(extension_number)
                    print(f"[AD-DEBUG] User {username}: ext={extension_number}, use_db={use_database}", file=sys.stderr, flush=True)

                    # Get user's AD groups and map to PBX permissions
                    user_groups = (
                        [str(g) for g in entry.memberOf] if hasattr(entry, "memberOf") else []
                    )
                    permissions = self._map_groups_to_permissions(user_groups)

                    # Check if extension exists (database or config depending
                    # on mode)
                    if use_database:
                        existing_ext = extension_db.get(extension_number)
                    else:
                        existing_ext = pbx_config.get_extension(extension_number)

                    print(f"[AD-DEBUG] User {username}: existing_ext={existing_ext is not None} ({type(existing_ext).__name__})", file=sys.stderr, flush=True)

                    if existing_ext:
                        # Update existing extension
                        self.logger.debug(
                            f"Updating extension {extension_number} for user {username}"
                        )

                        if use_database:
                            # Update in database with explicit parameters
                            # Note: Only update known fields; database will
                            # ignore unknown permission fields
                            success = extension_db.update(
                                number=extension_number,
                                name=display_name,
                                email=email,
                                ad_synced=True,
                                ad_username=username,
                                # Don't update password - keep existing
                            )
                            print(f"[AD-DEBUG] User {username}: DB update result={success}", file=sys.stderr, flush=True)

                            # Store permissions in extension config if update succeeded
                            # Database may not have columns for all permissions, so we store them
                            # in the system_config table keyed by extension number
                            if success and permissions and hasattr(extension_db, "set_config"):
                                config_key = f"ext.{extension_number}.ad_permissions"
                                try:
                                    extension_db.set_config(
                                        config_key,
                                        permissions,
                                        config_type="json",
                                        updated_by="ad_sync",
                                    )
                                except (OSError, TypeError, ValueError) as perm_err:
                                    self.logger.warning(
                                        f"Could not persist AD permissions for "
                                        f"extension {extension_number}: {perm_err}"
                                    )
                        else:
                            # Update in config.yml
                            success = pbx_config.update_extension(
                                number=extension_number,
                                name=display_name,
                                email=email,
                                # Don't update password - keep existing
                            )
                            if success:
                                # Mark as AD-synced and apply permissions in
                                # config
                                existing_ext["ad_synced"] = True
                                for perm_key, perm_value in permissions.items():
                                    existing_ext[perm_key] = perm_value

                        if success:
                            updated_count += 1
                            synced_count += 1

                            # Update in live registry if provided
                            if extension_registry:
                                ext = extension_registry.get(extension_number)
                                if ext:
                                    ext.name = display_name
                                    if email:
                                        ext.config["email"] = email
                                    ext.config["ad_synced"] = True
                                    # Apply permissions to live registry
                                    for perm_key, perm_value in permissions.items():
                                        ext.config[perm_key] = perm_value

                            # Log permissions if any were applied
                            if permissions:
                                perm_list = ", ".join([k for k, v in permissions.items() if v])
                                self.logger.info(
                                    f"Applied permissions to extension {extension_number}: {perm_list}"
                                )
                        else:
                            self.logger.warning(f"Failed to update extension {extension_number}")
                    else:
                        # Create new extension with random 4-digit password
                        # Note: 4-digit passwords meet user requirement but provide limited security
                        # Consider using longer passwords for production
                        # environments
                        random_password = "".join([str(secrets.randbelow(10)) for _ in range(4)])

                        # Log extension creation without exposing password
                        self.logger.info(
                            f"Creating extension {extension_number} for user {username}"
                        )
                        # Password can be retrieved from database or reset via
                        # admin interface

                        # Build extension data with permissions
                        ext_data = {
                            "number": extension_number,
                            "name": display_name,
                            "email": email or None,
                            "password_hash": random_password,
                            "allow_external": True,
                            "voicemail_pin": None,
                            "ad_synced": True,
                            "ad_username": username,
                        }

                        # Add permissions to extension data
                        ext_data.update(permissions)

                        if use_database:
                            # Add to database
                            # NOTE: For production, use FIPS-compliant hashing via pbx.utils.encryption.FIPSEncryption.hash_password()
                            # Currently storing plain password; system supports
                            # both plain and hashed passwords
                            success = extension_db.add(**ext_data)
                            print(f"[AD-DEBUG] User {username}: DB add result={success}", file=sys.stderr, flush=True)
                        else:
                            # Add to config.yml
                            success = pbx_config.add_extension(
                                number=extension_number,
                                name=display_name,
                                email=email or "",
                                password=random_password,
                                allow_external=True,
                            )
                            if success:
                                # Mark newly created extension as AD-synced and
                                # apply permissions
                                new_ext_config = pbx_config.get_extension(extension_number)
                                if new_ext_config:
                                    new_ext_config["ad_synced"] = True
                                    for perm_key, perm_value in permissions.items():
                                        new_ext_config[perm_key] = perm_value

                        if success:
                            created_count += 1
                            synced_count += 1

                            # Add to live registry if provided
                            if extension_registry:
                                from pbx.features.extensions import Extension

                                ext_config = {
                                    "number": extension_number,
                                    "name": display_name,
                                    "email": email or "",
                                    "password": random_password,
                                    "allow_external": True,
                                    "ad_synced": True,
                                }
                                # Apply permissions to config
                                ext_config.update(permissions)

                                new_ext = Extension(extension_number, display_name, ext_config)
                                extension_registry.extensions[extension_number] = new_ext

                            # Log permissions if any were applied
                            if permissions:
                                perm_list = ", ".join([k for k, v in permissions.items() if v])
                                self.logger.info(
                                    f"Applied permissions to new extension {extension_number}: {perm_list}"
                                )
                        else:
                            self.logger.warning(f"Failed to create extension {extension_number}")

                except (KeyError, TypeError, ValueError) as e:
                    user_desc = username or "unknown"
                    import traceback
                    print(f"[AD-DEBUG] ERROR syncing user {user_desc}: {e}", file=sys.stderr, flush=True)
                    traceback.print_exc(file=sys.stderr)
                    continue

            # Deactivate extensions for users removed from AD
            deactivated_count = 0
            if self.config.get("integrations.active_directory.deactivate_removed_users", True):
                self.logger.info("Checking for removed users to deactivate...")

                if use_database:
                    # Get all AD-synced extensions from database
                    all_extensions = extension_db.get_ad_synced()
                else:
                    # Get all extensions from config
                    all_extensions = pbx_config.get_extensions()

                for ext in all_extensions:
                    ext_number = ext.get("number")
                    # Only check extensions that could be AD-synced (numeric,
                    # reasonable length)
                    if (
                        ext_number
                        and ext_number.isdigit()
                        and len(ext_number) >= 3
                        and ext_number not in ad_extension_numbers
                        and ext.get("ad_synced", False)
                    ):
                        self.logger.info(
                            f"Deactivating extension {ext_number} (user removed from AD)"
                        )
                        # Mark as inactive instead of deleting
                        # Keep ad_synced=True so we know it was
                        # previously managed by AD

                        if use_database:
                            extension_db.update(number=ext_number, allow_external=False)
                        else:
                            pbx_config.update_extension(number=ext_number, allow_external=False)

                        if extension_registry:
                            registry_ext = extension_registry.get(ext_number)
                            if registry_ext:
                                registry_ext.config["allow_external"] = False
                                # Keep ad_synced=True to maintain
                                # history
                        deactivated_count += 1

            # Save all changes (only needed for config.yml mode)
            if not use_database:
                pbx_config.save()

            self.logger.info(
                "User synchronization complete: "
                f"{synced_count} total, {created_count} created, {updated_count} updated, "
                f"{deactivated_count} deactivated, {skipped_count} skipped"
            )

            # Automatically trigger phone reboots if provisioning is available and users were updated
            # This ensures phones fetch fresh config with updated display names
            # from AD
            if phone_provisioning and (updated_count > 0 or created_count > 0):
                self.logger.info(
                    "Auto-provisioning: Automatically triggering phone reboots to update display names from AD sync..."
                )

                # Find extensions that have provisioned devices and were updated
                # Use set for O(1) lookup performance with many devices
                ad_extension_set = set(ad_extension_numbers)
                devices_to_reboot = [
                    device.extension_number
                    for device in phone_provisioning.get_all_devices()
                    if device.extension_number in ad_extension_set
                ]

                if devices_to_reboot:
                    self.logger.info(
                        f"Auto-provisioning: Will reboot {len(devices_to_reboot)} phones to apply AD name changes"
                    )
                    # Store the extensions to reboot for later trigger
                    # This will be picked up by the sync caller to trigger
                    # actual reboots
                    return {"synced_count": synced_count, "extensions_to_reboot": devices_to_reboot}
                self.logger.info(
                    "Auto-provisioning: No provisioned devices found for updated extensions"
                )

            return {"synced_count": synced_count, "extensions_to_reboot": []}

        except (KeyError, LDAPException, TypeError, ValueError) as e:
            self.logger.error(f"Error synchronizing users from Active Directory: {e}")
            import traceback

            traceback.print_exc()
            return {"synced_count": 0, "extensions_to_reboot": []}

    def _map_groups_to_permissions(self, user_groups: list[str]) -> dict[str, bool]:
        """
        Map AD groups to PBX permissions based on configuration

        Args:
            user_groups: list of AD group names or DNs

        Returns:
            dict: Permissions dictionary (e.g., {'admin': True, 'external_calling': True})
        """
        permissions = {}

        # Get group permissions configuration
        group_permissions_config = self.config.get(
            "integrations.active_directory.group_permissions", {}
        )

        if not group_permissions_config:
            self.logger.debug("No group permissions configured")
            return permissions

        # Normalize user groups to both DN and CN formats for flexible matching
        normalized_user_groups = set()
        for group in user_groups:
            normalized_user_groups.add(group)  # Add full DN
            # Also add just the CN part for easier matching
            if group.startswith("CN="):
                cn_end = group.find(",")
                if cn_end > 0:
                    cn_name = group[3:cn_end]
                    normalized_user_groups.add(cn_name)

        # Check each configured group mapping
        for group_dn, perms in group_permissions_config.items():
            # Extract CN from configured group DN for flexible matching
            if group_dn.startswith("CN="):
                cn_end = group_dn.find(",")
                if cn_end > 0:
                    config_group_cn = group_dn[3:cn_end]
                else:
                    config_group_cn = group_dn
            else:
                config_group_cn = group_dn

            # Check if user is in this group (match by DN or CN)
            if group_dn in normalized_user_groups or config_group_cn in normalized_user_groups:
                self.logger.debug(f"User is member of configured group: {group_dn}")
                # Apply permissions from this group
                if isinstance(perms, list):
                    for perm in perms:
                        # set boolean True value for granted permissions
                        permissions[perm] = True
                        self.logger.debug(f"  Granted permission: {perm}")

        return permissions

    def get_user_groups(self, username: str) -> list[str]:
        """
        Get Active Directory groups for a user

        Args:
            username: Username

        Returns:
            list: list of group names
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
            user_search_base = self.config.get(
                "integrations.active_directory.user_search_base", self.base_dn
            )

            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["memberOf"],
            )

            if not self.connection.entries:
                self.logger.warning(f"User not found: {username}")
                return []

            user_entry = self.connection.entries[0]

            # Extract group names from DNs
            groups = []
            if hasattr(user_entry, "memberOf"):
                for group_dn in user_entry.memberOf:
                    # Extract CN from DN (e.g.,
                    # "CN=Sales,OU=Groups,DC=domain,DC=local" -> "Sales")
                    dn_str = str(group_dn)
                    if dn_str.startswith("CN="):
                        cn_end = dn_str.find(",")
                        if cn_end > 0:
                            group_name = dn_str[3:cn_end]
                            groups.append(group_name)

            self.logger.info(f"Found {len(groups)} groups for user {username}")
            return groups

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error getting groups for user {username}: {e}")
            return []

    def search_users(self, query: str, max_results: int = 50) -> list[dict]:
        """
        Search for users in Active Directory

        Args:
            query: Search query (name, phone, email)
            max_results: Maximum number of results

        Returns:
            list: list of user dictionaries
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
                "(&(objectClass=user)"
                f"(|(cn=*{safe_query}*)(displayName=*{safe_query}*)"
                f"(mail=*{safe_query}*)(telephoneNumber=*{safe_query}*)))"
            )

            user_search_base = self.config.get(
                "integrations.active_directory.user_search_base", self.base_dn
            )

            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["sAMAccountName", "displayName", "mail", "telephoneNumber"],
                size_limit=max_results,
            )

            results = [
                {
                    "username": str(entry.sAMAccountName),
                    "display_name": (
                        str(entry.displayName)
                        if hasattr(entry, "displayName")
                        else str(entry.sAMAccountName)
                    ),
                    "email": str(entry.mail) if hasattr(entry, "mail") else None,
                    "phone": (
                        str(entry.telephoneNumber) if hasattr(entry, "telephoneNumber") else None
                    ),
                }
                for entry in self.connection.entries
            ]

            self.logger.info(f"Found {len(results)} users matching: {query}")
            return results

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error searching users: {e}")
            return []

    def get_user_photo(self, username: str) -> bytes | None:
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
            user_search_base = self.config.get(
                "integrations.active_directory.user_search_base", self.base_dn
            )

            self.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["thumbnailPhoto"],
            )

            if not self.connection.entries:
                self.logger.warning(f"User not found: {username}")
                return None

            user_entry = self.connection.entries[0]

            # Return photo bytes if available
            if hasattr(user_entry, "thumbnailPhoto") and user_entry.thumbnailPhoto.value:
                photo_data = user_entry.thumbnailPhoto.value
                self.logger.info(f"Retrieved photo for user {username} ({len(photo_data)} bytes)")
                return photo_data
            self.logger.info(f"No photo available for user {username}")
            return None

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error getting photo for user {username}: {e}")
            return None
