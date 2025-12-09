# Remove Extension 1001 from Database

**Date**: December 9, 2025  
**Purpose**: Remove false/test extension 1001 from database

## Overview

Extension 1001 was added as sample data during initial database setup. This guide explains how to remove it from the database.

## Quick Start

### Option 1: Using the Cleanup Script (Recommended)

Run the provided cleanup script:

```bash
# Set database credentials (if not using defaults)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=pbx_system
export DB_USER=pbx_user
export DB_PASSWORD=YourSecurePassword123!

# Run the cleanup script
python scripts/remove_extension_1001.py
```

The script will:
1. Connect to the database
2. Find all references to extension 1001
3. Remove entries from:
   - `vip_callers` table (where it was John Smith from ABC Corp)
   - `extensions` table (if exists)
   - `voicemail_mailboxes` table (if exists)
4. Display what was removed

### Option 2: Manual Database Cleanup

If you prefer to manually remove the data:

```sql
-- Connect to PostgreSQL
psql -U pbx_user -d pbx_system

-- Remove from VIP callers
DELETE FROM vip_callers WHERE direct_extension = '1001';

-- Remove from extensions (if table exists)
DELETE FROM extensions WHERE extension_number = '1001';

-- Remove from voicemail mailboxes (if table exists)
DELETE FROM voicemail_mailboxes WHERE extension = '1001';

-- Commit changes
COMMIT;
```

## What Was Removed

Extension 1001 existed as sample data in the database:

**VIP Callers Entry:**
- Caller ID: +15551234567
- Name: John Smith
- Company: ABC Corp
- Priority: 1
- Direct Extension: 1001
- Skip Queue: True

This was test data created during initial database setup and is no longer needed.

## Prevention

To prevent extension 1001 from being re-added in the future, the `scripts/init_database.py` file has been updated to exclude it from sample data.

## Verification

After running the cleanup, verify extension 1001 is removed:

```bash
# Check for any remaining references
psql -U pbx_user -d pbx_system -c "SELECT * FROM vip_callers WHERE direct_extension = '1001';"
```

Expected result: 0 rows

## Notes

- This cleanup is safe and only removes the test data
- It does not affect any real extensions or production data
- If extension 1001 is currently in use as a real extension, consider reassigning it before running this cleanup

---

**Status**: ✅ Ready to use  
**Last Updated**: December 9, 2025
