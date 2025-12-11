# Admin Extension Access Control

## Overview

The PBX system now supports role-based access control for the admin web panel. Extensions can be designated as "admin extensions" to access all management features, while regular extensions have limited access to only phone and voicemail features.

## Features

### For All Extensions
All authenticated extensions have access to:
- 📞 **WebRTC Phone**: Make calls directly from the browser
- 📧 **Visual Voicemail**: View and manage their own voicemail messages

### For Admin Extensions Only
Admin extensions additionally have access to:
- 👥 **Extension Management**: Add, edit, delete extensions
- ☎️ **Registered Phones**: View all registered SIP devices
- ⚙️ **Phone Provisioning**: Configure auto-provisioning for IP phones
- 🤖 **Auto Attendant**: Configure IVR menus and routing
- 📈 **Analytics & Statistics**: View call analytics and trends
- 📡 **QoS Monitoring**: Monitor call quality metrics
- 🚨 **Emergency Contacts**: Manage emergency notification contacts
- 🎵 **Codec Configuration**: Configure audio/video codecs
- 🔧 **System Configuration**: Modify system settings
- 📋 **Dashboard**: View full system overview and statistics

## Database Schema

The `extensions` table now includes an `is_admin` field:

```sql
-- PostgreSQL
ALTER TABLE extensions ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

-- SQLite
ALTER TABLE extensions ADD COLUMN is_admin BOOLEAN DEFAULT 0;
```

This column is automatically added via schema migration when the PBX starts with database enabled.

## Managing Admin Extensions

### Via Admin Panel

1. **Creating a New Admin Extension:**
   - Navigate to Extensions tab
   - Click "➕ Add Extension"
   - Fill in extension details
   - Check the "Admin Privileges" checkbox
   - Click "Add Extension"

2. **Granting Admin Privileges to Existing Extension:**
   - Navigate to Extensions tab
   - Find the extension in the list
   - Click "✏️ Edit" button
   - Check the "Admin Privileges" checkbox
   - Click "Update Extension"

3. **Identifying Admin Extensions:**
   - Admin extensions display a gold "👑 Admin" badge next to their extension number
   - Example: `1001 👑 Admin`

### Via API

**Add new admin extension:**
```bash
curl -X POST http://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1001",
    "name": "Admin User",
    "email": "admin@company.com",
    "password": "SecurePassword123",
    "voicemail_pin": "1234",
    "allow_external": true,
    "is_admin": true
  }'
```

**Grant admin privileges to existing extension:**
```bash
curl -X PUT http://localhost:8080/api/extensions/1001 \
  -H "Content-Type: application/json" \
  -d '{
    "is_admin": true
  }'
```

**Check extension admin status:**
```bash
curl http://localhost:8080/api/extensions
```

Look for the `is_admin` field in the response:
```json
[
  {
    "number": "1001",
    "name": "Admin User",
    "email": "admin@company.com",
    "is_admin": true,
    ...
  }
]
```

### Via Database

If you have direct database access:

```sql
-- PostgreSQL or SQLite
-- Grant admin privileges
UPDATE extensions SET is_admin = TRUE WHERE number = '1001';

-- Revoke admin privileges
UPDATE extensions SET is_admin = FALSE WHERE number = '1001';

-- List all admin extensions
SELECT number, name, email FROM extensions WHERE is_admin = TRUE;
```

## Security Considerations

1. **Principle of Least Privilege**: Only grant admin privileges to users who need full system access.

2. **First Admin**: When setting up a new system, at least one extension should be designated as admin to manage the system.

3. **Audit Trail**: Admin actions should be logged for security auditing (future enhancement).

4. **Password Requirements**: Admin extensions should use strong passwords (minimum 8 characters enforced).

5. **Voicemail PIN**: All extensions require a 4-6 digit voicemail PIN for authentication.

## Migration from Previous Versions

If you're upgrading from a version without admin access control:

1. The `is_admin` column will be automatically added to the `extensions` table when the PBX starts.

2. **All existing extensions will have `is_admin = FALSE` by default.**

3. You must manually grant admin privileges to at least one extension:
   ```sql
   UPDATE extensions SET is_admin = TRUE WHERE number = '1001';
   ```
   Or use the API/Admin Panel methods described above.

4. After granting admin privileges, restart the PBX or reload extensions:
   ```bash
   # The admin panel will reflect changes immediately after the update
   ```

## Future Enhancements (Planned)

The following features are planned for future releases:

- **Authentication System**: Login page requiring extension number and password
- **Session Management**: Secure token-based session handling
- **API Authentication**: Protect admin API endpoints with auth middleware
- **UI Role-Based Rendering**: Show/hide features based on authenticated user's role
- **Audit Logging**: Track all admin actions with timestamps and user identification
- **Multiple Admin Roles**: Fine-grained permissions (e.g., "can manage extensions" vs "can configure system")

## Troubleshooting

### Issue: Cannot access admin features
**Solution**: Verify the extension has `is_admin = TRUE` in the database:
```sql
SELECT number, name, is_admin FROM extensions WHERE number = 'YOUR_EXTENSION';
```

### Issue: is_admin field not found
**Solution**: The database schema migration may not have run. Restart the PBX to trigger automatic migration, or manually add the column:
```sql
ALTER TABLE extensions ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
```

### Issue: All extensions show as admin
**Solution**: Check database values. Run:
```sql
SELECT number, name, is_admin FROM extensions;
```

## Related Documentation

- [EXTENSION_DATABASE_GUIDE.md](EXTENSION_DATABASE_GUIDE.md) - Extension database management
- [DATABASE_MIGRATION_GUIDE.md](DATABASE_MIGRATION_GUIDE.md) - Database migration procedures
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - REST API reference

## Support

For issues or questions about admin access control:
1. Check the database schema with `python scripts/verify_database.py`
2. Review PBX logs for migration messages
3. Consult the troubleshooting section above
4. Open an issue on GitHub with detailed error messages
