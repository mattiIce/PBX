# Active Directory User Synchronization Guide

This guide explains how to synchronize users from Active Directory to the PBX system, automatically creating and managing extensions.

## Overview

The AD User Sync feature automatically:
- ✅ Creates PBX extensions for AD users with phone numbers
- ✅ Updates existing extensions when AD user information changes
- ✅ Deactivates extensions when users are removed from AD
- ✅ Uses AD `telephoneNumber` as extension number
- ✅ Generates random 4-digit passwords for new extensions
- ✅ Syncs display name and email address

## Configuration

### 1. Prerequisites

Ensure `ldap3` library is installed:
```bash
pip install ldap3
```

### 2. Configure Active Directory Integration

Edit `config.yml` and configure the `integrations.active_directory` section:

```yaml
integrations:
  active_directory:
    enabled: true  # Enable AD integration
    server: ldaps://192.168.1.22:636  # LDAP server (use ldaps:// for SSL)
    base_dn: DC=albl,DC=com  # Your domain's base DN
    user_search_base: CN=Users,DC=albl,DC=com  # Where to search for users
    bind_dn: CN=Administrator,CN=Users,DC=albl,DC=com  # Service account DN
    bind_password: YourPassword  # Service account password
    use_ssl: true  # Use SSL/TLS (recommended)
    auto_provision: true  # Enable automatic user provisioning
    deactivate_removed_users: true  # Disable extensions for removed users
```

### 3. Security Considerations

**IMPORTANT**: For production use:

1. **Use a dedicated service account** instead of Administrator:
   ```yaml
   bind_dn: CN=svc-pbx,OU=Service Accounts,DC=albl,DC=com
   ```

2. **Use environment variables** for sensitive data:
   ```yaml
   bind_password: ${AD_BIND_PASSWORD}  # Set via environment variable
   ```

3. **Grant minimum permissions** to the service account:
   - Read access to user objects
   - Read `telephoneNumber`, `mail`, `displayName`, `sAMAccountName` attributes
   - No write permissions needed

## Usage

### Method 1: Using the Sync Script (Recommended)

The easiest way to sync users is using the provided script:

```bash
# Sync all users
python scripts/sync_ad_users.py

# Dry run (show what would be synced without making changes)
python scripts/sync_ad_users.py --dry-run

# Verbose output for debugging
python scripts/sync_ad_users.py --verbose

# Use different config file
python scripts/sync_ad_users.py --config /path/to/config.yml
```

### Method 2: Programmatically via Python

```python
from pbx.utils.config import Config
from pbx.integrations.active_directory import ActiveDirectoryIntegration
from pbx.features.extensions import ExtensionRegistry

# Load configuration
config = Config('config.yml')

# Create AD integration instance
ad_config = {
    'integrations.active_directory.enabled': config.get('integrations.active_directory.enabled'),
    'integrations.active_directory.server': config.get('integrations.active_directory.server'),
    'integrations.active_directory.base_dn': config.get('integrations.active_directory.base_dn'),
    'integrations.active_directory.bind_dn': config.get('integrations.active_directory.bind_dn'),
    'integrations.active_directory.bind_password': config.get('integrations.active_directory.bind_password'),
    'integrations.active_directory.use_ssl': config.get('integrations.active_directory.use_ssl'),
    'integrations.active_directory.auto_provision': True,
    'config_file': 'config.yml'
}

ad = ActiveDirectoryIntegration(ad_config)

# Initialize extension registry
extension_registry = ExtensionRegistry(config)

# Sync users
synced_count = ad.sync_users(extension_registry=extension_registry)
print(f"Synchronized {synced_count} users")
```

### Method 3: Via REST API (if enabled)

```bash
# Trigger sync via API endpoint
curl -X POST http://localhost:8080/api/admin/sync-ad-users
```

## How It Works

### Storage Location

**Starting with this version, extensions are stored in the database** (not config.yml):
- ✅ Extensions synced from AD are stored in the database
- ✅ Marked with `ad_synced=true` flag
- ✅ AD username tracked for reference
- ✅ Can be viewed/edited in admin web interface
- ✅ Changes persist across restarts
- ✅ No need to edit config.yml manually

See [EXTENSION_DATABASE_GUIDE.md](EXTENSION_DATABASE_GUIDE.md) for complete database documentation.

### User Discovery

The sync process:

1. **Connects to AD** using the configured service account
2. **Searches for users** in the specified OU with these criteria:
   - `objectClass=user` (user accounts)
   - `telephoneNumber=*` (has a phone number)
   - Account is enabled (not disabled)
3. **Extracts attributes**:
   - `sAMAccountName` → Username (stored in database)
   - `displayName` → Extension name
   - `mail` → Email address
   - `telephoneNumber` → Extension number

### Extension Number Mapping

The extension number is derived from the AD `telephoneNumber` attribute:

- **Original phone number**: `(555) 123-4567`
- **Extracted extension**: `5551234567` (digits only)

### Password Generation

For new extensions:
- Generates random 4-digit password (e.g., `8472`)
- **Security Note**: 4-digit passwords provide basic security (10,000 combinations). For production environments with external access, consider:
  - Implementing longer passwords (8+ characters)
  - Using alphanumeric combinations
  - Enforcing password changes on first login
  - Enabling FIPS-compliant password hashing (already supported)
- Passwords are stored in `config.yml` (not logged for security)
- Users should change passwords after initial setup via SIP phone or web interface

### Create vs Update Logic

**Creating New Extensions:**
- AD user has `telephoneNumber` but no matching PBX extension
- Creates extension in database with random 4-digit password
- Sets `ad_synced=true` and stores AD username
- Extension immediately available for SIP registration

**Updating Existing Extensions:**
- Extension number matches AD user's phone number
- Updates: display name, email address, AD username
- Preserves: existing password, registration status
- Database record updated automatically

**Deactivating Removed Users:**
- Extension marked as `ad_synced=true` in database
- User no longer in AD or lost `telephoneNumber`
- Sets `allow_external=false` (disables external calls)
- Does NOT delete the extension (preserves call history and voicemail)
- Extension still visible in admin interface with "AD" badge

## Sync Results

After running sync, you'll see output like:

```
User synchronization complete: 15 total, 3 created, 12 updated, 1 deactivated, 2 skipped
```

- **Total**: Users successfully synced
- **Created**: New extensions created
- **Updated**: Existing extensions updated
- **Deactivated**: Extensions disabled (users removed from AD)
- **Skipped**: Users without required fields (phone number, etc.)

## Testing

### Verify AD Integration Setup

Before syncing users, test that your AD integration is configured correctly:

```bash
# Run the comprehensive AD integration test
python scripts/test_ad_integration.py

# With verbose output for detailed information
python scripts/test_ad_integration.py --verbose
```

The test script will check:
- ✓ Configuration is valid and complete
- ✓ Required dependencies (ldap3) are installed
- ✓ Connection to AD server succeeds
- ✓ Authentication with bind credentials works
- ✓ User search and discovery functions
- ✓ User attributes are retrieved correctly
- ✓ Extensions can be synced without conflicts
- ✓ Overall integration readiness

**Example output:**
```
======================================================================
Test Summary
======================================================================
Total tests: 15
Passed: 13
Failed: 0
Warnings: 2

✓ ALL TESTS PASSED

Active Directory integration is configured correctly!

Next steps:
  1. Run the sync script:
     python scripts/sync_ad_users.py

  2. Verify extensions were created in config.yml

  3. Test SIP registration with a synced extension
```

### Test with Specific Users

The configuration includes test users: `cmattinson` and `bsautter`

1. **Verify users exist in AD:**
   ```bash
   # On Windows AD server
   Get-ADUser -Filter {SamAccountName -eq "cmattinson"} -Properties telephoneNumber, mail
   ```

2. **Run sync:**
   ```bash
   python scripts/sync_ad_users.py
   ```

3. **Check created extensions:**
   ```bash
   # List all extensions from database
   python scripts/list_extensions_from_db.py
   
   # Or list only AD-synced extensions
   python scripts/list_extensions_from_db.py --ad-only
   ```

4. **View in admin interface:**
   - Start PBX: `python main.py`
   - Open: `http://localhost:8080/admin/`
   - Go to **Extensions** tab
   - AD-synced extensions show green "AD" badge

### Verify Sync Completed Successfully

After running the sync, verify it worked:

1. **Check the sync output** - Look for success message:
   ```
   Synchronization Complete: 15 users synchronized
   ```

2. **Verify extensions in config.yml:**
   ```bash
   # Count synced extensions
   grep -c "ad_synced: true" config.yml
   ```

3. **List all synced users:**
   ```bash
   # View synced extensions with details
   grep -B 3 "ad_synced: true" config.yml
   ```

4. **Test authentication** - Try registering a SIP phone with one of the synced extensions

### Troubleshooting

**Connection Failed:**
```
✗ Failed to connect to Active Directory
```
- Check server address (192.168.1.22 or 192.168.1.23)
- Verify SSL certificate if using `ldaps://`
- Test network connectivity: `ping 192.168.1.22`
- Try non-SSL: `ldap://192.168.1.22:389` (not recommended for production)

**Authentication Failed:**
```
Error authenticating to Active Directory
```
- Verify bind DN: `CN=Administrator,CN=Users,DC=albl,DC=com`
- Check password is correct
- Ensure service account is not disabled or expired

**No Users Found:**
```
No users found in Active Directory
```
- Check user search base: `CN=Users,DC=albl,DC=com`
- Verify users have `telephoneNumber` attribute set
- Test LDAP search manually:
  ```bash
  ldapsearch -H ldaps://192.168.1.22 -D "CN=Administrator,CN=Users,DC=albl,DC=com" \
    -W -b "CN=Users,DC=albl,DC=com" "(telephoneNumber=*)"
  ```

## Scheduling Automatic Sync

### Using Cron (Linux)

Add to crontab to sync daily at 2 AM:

```bash
crontab -e

# Add line:
0 2 * * * cd /path/to/PBX && python scripts/sync_ad_users.py >> logs/ad_sync.log 2>&1
```

### Using Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 2:00 AM
4. Action: Start a program
   - Program: `python`
   - Arguments: `scripts/sync_ad_users.py`
   - Start in: `C:\path\to\PBX`

### Using systemd Timer (Linux)

```ini
# /etc/systemd/system/pbx-ad-sync.service
[Unit]
Description=PBX AD User Sync
After=network.target

[Service]
Type=oneshot
User=pbx
WorkingDirectory=/opt/pbx
ExecStart=/usr/bin/python3 scripts/sync_ad_users.py

# /etc/systemd/system/pbx-ad-sync.timer
[Unit]
Description=Daily PBX AD Sync
Requires=pbx-ad-sync.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
systemctl enable --now pbx-ad-sync.timer
```

## Future Enhancements (TODO)

The following features are marked for future implementation:

### Group-Based Permissions

Map AD groups to PBX permissions:

```yaml
integrations:
  active_directory:
    group_permissions:
      CN=PBX_Admins,OU=Groups,DC=albl,DC=com:
        - admin
        - manage_extensions
      CN=Sales,OU=Groups,DC=albl,DC=com:
        - external_calling
        - international_calling
      CN=Support,OU=Groups,DC=albl,DC=com:
        - call_recording
        - call_queues
```

To implement:
1. Add `group_permissions` parsing in `sync_users()`
2. Check user's `memberOf` attribute
3. Apply permissions to extension config

## API Reference

### `ActiveDirectoryIntegration.sync_users(extension_registry=None)`

Synchronizes users from Active Directory to PBX extensions.

**Parameters:**
- `extension_registry` (ExtensionRegistry, optional): Live extension registry to update in real-time

**Returns:**
- `int`: Number of users successfully synchronized

**Raises:**
- No exceptions (logs errors internally)

**Example:**
```python
ad = ActiveDirectoryIntegration(config)
synced = ad.sync_users()
print(f"Synced {synced} users")
```

## Best Practices

1. **Start with dry-run**: Always test with `--dry-run` first
2. **Test with limited users**: Test with `cmattinson` and `bsautter` before full sync
3. **Review logs**: Check `logs/pbx.log` for detailed sync information
4. **Backup config.yml**: Before first sync: `cp config.yml config.yml.backup`
5. **Monitor first sync**: Watch the first sync complete to catch any issues
6. **Schedule regular syncs**: Run daily to keep extensions up-to-date
7. **Use SSL**: Always use `ldaps://` for secure communication
8. **Dedicated service account**: Don't use Administrator account in production

## Security Checklist

- [ ] Using dedicated service account (not Administrator)
- [ ] Service account has minimal permissions (read-only)
- [ ] Using SSL/TLS (`ldaps://`)
- [ ] Bind password stored securely (environment variable or secrets manager)
- [ ] Regular audit of synced users
- [ ] Monitor logs for unauthorized access attempts

## Support

For issues or questions:
1. Check logs: `logs/pbx.log`
2. Run with `--verbose` flag for detailed output
3. Verify AD connectivity and credentials
4. Check user has required attributes in AD
5. Review this documentation

## Configuration Reference

Complete AD integration configuration:

```yaml
integrations:
  active_directory:
    # Enable/disable integration
    enabled: true
    
    # LDAP server (use ldaps:// for SSL)
    server: ldaps://192.168.1.22:636
    
    # Domain base DN
    base_dn: DC=albl,DC=com
    
    # Where to search for users
    user_search_base: CN=Users,DC=albl,DC=com
    
    # Service account credentials
    bind_dn: CN=Administrator,CN=Users,DC=albl,DC=com
    bind_password: Q1g0ng248!
    
    # Use SSL/TLS (recommended)
    use_ssl: true
    
    # Auto-provision extensions
    auto_provision: true
    
    # Deactivate removed users
    deactivate_removed_users: true
    
    # [TODO] Group-based permissions
    # group_permissions:
    #   CN=Admins,OU=Groups,DC=albl,DC=com:
    #     - admin
```

## Example Output

```
======================================================================
Active Directory User Synchronization
======================================================================

Testing connection to Active Directory...
✓ Connected to Active Directory

Configuration:
  Server: ldaps://192.168.1.22:636
  Base DN: DC=albl,DC=com
  User Search Base: CN=Users,DC=albl,DC=com
  Auto-provision: True

Synchronizing users...

2025-12-05 15:00:00 - PBX - INFO - Starting user synchronization from Active Directory...
2025-12-05 15:00:01 - PBX - INFO - Found 15 users in Active Directory
2025-12-05 15:00:01 - PBX - INFO - Creating extension 5551234 for user cmattinson (password: 8472)
2025-12-05 15:00:01 - PBX - INFO - Creating extension 5555678 for user bsautter (password: 3159)
2025-12-05 15:00:02 - PBX - INFO - User synchronization complete: 15 total, 2 created, 13 updated, 0 deactivated, 0 skipped

======================================================================
Synchronization Complete: 15 users synchronized
======================================================================

Next steps:
  1. Review the synced extensions in config.yml
  2. Test SIP registration with one of the synced extensions
  3. Check logs for any errors or warnings

Test users provided: cmattinson, bsautter
Check their extension numbers in config.yml
```
