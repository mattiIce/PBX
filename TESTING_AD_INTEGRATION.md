# Testing AD Integration - Quick Start Guide

## Question: How do I test that AD integration has completed successfully?

This guide provides step-by-step instructions to test and verify Active Directory integration.

## Prerequisites

Before testing, ensure you have:
- [ ] Active Directory server accessible
- [ ] Service account credentials
- [ ] Users in AD with `telephoneNumber` attribute set
- [ ] `ldap3` Python library installed: `pip install ldap3`
- [ ] Database configured (SQLite or PostgreSQL)

## Step 1: Test AD Connection and Configuration

Run the comprehensive AD integration test:

```bash
python scripts/test_ad_integration.py
```

**What it tests:**
- ✓ Configuration is valid and complete
- ✓ Required dependencies (ldap3) are installed
- ✓ Connection to AD server succeeds
- ✓ Authentication with bind credentials works
- ✓ User search and discovery functions
- ✓ User attributes are retrieved correctly
- ✓ Extensions can be synced without conflicts
- ✓ Overall integration readiness

**Expected output:**
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
```

**If tests fail:**
- Check server address and credentials in `config.yml`
- Verify network connectivity to AD server
- Ensure service account has read permissions
- Review error messages for specific issues

## Step 2: Run AD User Sync (Dry Run)

Test what would be synced without making changes:

```bash
python scripts/sync_ad_users.py --dry-run
```

**What to look for:**
- Number of users found in AD
- List of users that would be synced
- Any users that would be skipped (missing phone numbers, etc.)
- Extension number mappings

**Example output:**
```
Found 15 users in Active Directory

Synchronizing users...
Creating extension 5551234 for user cmattinson
Creating extension 5555678 for user bsautter
...

Synchronization Complete: 15 users would be synchronized
```

## Step 3: Perform Actual Sync

Run the real sync to create extensions:

```bash
python scripts/sync_ad_users.py
```

**What happens:**
- ✅ Connects to database (or falls back to config.yml)
- ✅ Searches AD for users with phone numbers
- ✅ Creates new extensions in database
- ✅ Updates existing extensions
- ✅ Marks all synced extensions with `ad_synced=true`
- ✅ Stores AD username for tracking

**Success indicators:**
```
✓ Connected to database - extensions will be synced to database

Synchronizing users...
Creating extension 5551234 for user cmattinson (password: 8472)
Creating extension 5555678 for user bsautter (password: 3159)
...

======================================================================
Synchronization Complete: 15 users synchronized
======================================================================
```

## Step 4: Verify Extensions in Database

List all synced extensions:

```bash
# List all extensions
python scripts/list_extensions_from_db.py

# List only AD-synced extensions
python scripts/list_extensions_from_db.py --ad-only
```

**Expected output:**
```
================================================================================
All Extensions (15 total)
================================================================================

Number     Name                      Email                          Ext    AD  
--------------------------------------------------------------------------------
5551234    Codi Mattinson            cmattinson@albl.com            Yes    Yes 
5555678    Bill Sautter              bsautter@albl.com              Yes    Yes 
...

Total: 15 extensions
  - 15 synced from Active Directory
  - 0 created manually
```

**Verify:**
- [ ] Extension numbers match AD phone numbers
- [ ] Names and emails are correct
- [ ] "AD" column shows "Yes" for synced extensions
- [ ] External calls enabled as expected

## Step 5: View in Admin Web Interface

1. **Start the PBX:**
   ```bash
   python main.py
   ```

2. **Open admin panel:**
   ```
   http://localhost:8080/admin/
   ```

3. **Go to Extensions tab**

4. **Verify AD-synced extensions:**
   - Should see all synced extensions listed
   - Each has a green "AD" badge next to the number
   - Status shows "Online" when registered, "Offline" when not
   - External calling permission displayed

![Extensions with AD badge](example-screenshot-here)

## Step 6: Test SIP Registration

Test that synced extensions can register with the PBX:

1. **Configure a SIP phone:**
   - Server: `192.168.1.14` (your PBX IP)
   - Extension: `5551234` (from AD sync)
   - Password: Check logs or database for generated password

2. **Register the phone**
   - Watch PBX logs for registration success
   - Check admin interface - status should change to "Online"

3. **Make a test call:**
   - Call another extension
   - Verify audio works in both directions
   - Check call logs

## Step 7: Test Extension Management

Verify you can manage AD-synced extensions:

1. **Edit an AD-synced extension:**
   - Click "✏️ Edit" in admin interface
   - Change name or email
   - Save changes
   - Verify changes persist

2. **Note:** Password can be changed for AD-synced users
3. **Note:** Extensions will be re-synced from AD on next sync run

## Step 8: Test Sync Updates

Verify updates work correctly:

1. **Change user info in AD:**
   - Update displayName or email for a test user

2. **Run sync again:**
   ```bash
   python scripts/sync_ad_users.py
   ```

3. **Verify updates:**
   ```bash
   python scripts/list_extensions_from_db.py --ad-only
   ```

4. **Check admin interface:**
   - Updated information should be reflected

## Step 9: Test User Deactivation

Verify removed users are deactivated:

1. **Remove telephoneNumber from a test user in AD**

2. **Run sync:**
   ```bash
   python scripts/sync_ad_users.py
   ```

3. **Check logs for:**
   ```
   Deactivating extension 5551234 (user removed from AD)
   ```

4. **Verify in database:**
   - Extension still exists
   - `allow_external` set to false
   - `ad_synced` still true (for tracking)

## Troubleshooting

### Issue: Test script fails to connect

**Error:** `✗ Failed to connect to Active Directory`

**Solutions:**
- Check server address in config.yml
- Verify network connectivity: `ping 192.168.1.22`
- Test SSL certificate if using ldaps://
- Try non-SSL temporarily: `ldap://server:389`

### Issue: No users found

**Error:** `No users found in Active Directory`

**Solutions:**
- Verify user_search_base is correct
- Check users have telephoneNumber attribute set
- Ensure service account has read permissions
- Test LDAP search manually with ldapsearch

### Issue: Extensions not in database

**Error:** Extensions created but not visible in database

**Solutions:**
- Check database connection: `python scripts/verify_database.py`
- Verify sync used database (check logs for "Syncing to database")
- Run migration: `python scripts/migrate_extensions_to_db.py`
- List extensions: `python scripts/list_extensions_from_db.py`

### Issue: Duplicate extensions

**Problem:** Extension exists in both config.yml and database

**Solution:**
- Database takes precedence - extensions in config.yml are ignored
- This is normal and expected behavior
- You can optionally remove extensions from config.yml

## Success Checklist

Use this checklist to verify complete AD integration:

- [ ] `test_ad_integration.py` passes all tests
- [ ] Dry run shows expected users
- [ ] Actual sync completes successfully
- [ ] Extensions visible in database (`list_extensions_from_db.py`)
- [ ] Extensions show "AD" badge in admin interface
- [ ] Test SIP phone registers successfully
- [ ] Test calls work between extensions
- [ ] Extension edits persist correctly
- [ ] AD updates sync to database
- [ ] Removed users get deactivated (not deleted)
- [ ] Logs show no errors

✓ **AD Integration is working correctly!**

## Ongoing Monitoring

### Daily Operations

1. **Check sync logs:**
   ```bash
   tail -f logs/pbx.log | grep "AD\|sync"
   ```

2. **Review synced extensions:**
   ```bash
   python scripts/list_extensions_from_db.py --ad-only
   ```

3. **Monitor for errors:**
   - Connection failures
   - Authentication issues
   - Sync failures

### Weekly Tasks

1. **Verify sync is running** (if scheduled):
   ```bash
   systemctl status pbx-ad-sync.timer  # if using systemd timer
   ```

2. **Review deactivated users:**
   - Check why users were deactivated
   - Verify intentional removals
   - Re-enable if needed

3. **Audit AD-synced extensions:**
   - Compare with AD user list
   - Verify all active users have extensions
   - Check for orphaned extensions

### Monthly Tasks

1. **Test full sync process:**
   - Run test_ad_integration.py
   - Perform full sync
   - Verify results

2. **Review security:**
   - Check service account permissions
   - Audit password changes
   - Review access logs

3. **Database maintenance:**
   - Backup database
   - Check disk space
   - Optimize if needed

## Scheduling Automatic Syncs

### Using Cron (Linux)

```bash
# Edit crontab
crontab -e

# Add line to sync daily at 2 AM
0 2 * * * cd /path/to/PBX && python scripts/sync_ad_users.py >> logs/ad_sync.log 2>&1
```

### Using systemd Timer (Linux)

See [AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md#scheduling-automatic-sync) for complete setup.

### Using Task Scheduler (Windows)

See [AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md#scheduling-automatic-sync) for complete setup.

## Additional Resources

- **AD Sync Guide:** [AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md)
- **Database Storage:** [EXTENSION_DATABASE_GUIDE.md](EXTENSION_DATABASE_GUIDE.md)
- **API Documentation:** [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Testing Guide:** [TESTING_GUIDE.md](TESTING_GUIDE.md)

## Support

If you encounter issues:
1. Run `python scripts/test_ad_integration.py --verbose`
2. Check logs at `logs/pbx.log`
3. Review this guide
4. Check GitHub issues

---

**Summary:** You now have a complete, working AD integration that:
- ✅ Automatically syncs users from Active Directory
- ✅ Stores extensions in database (not config.yml)
- ✅ Shows AD-synced indicators in admin interface
- ✅ Allows manual edits to synced extensions
- ✅ Handles user updates and removals gracefully
- ✅ Provides comprehensive testing and verification tools
