# Admin Panel Guide

**Last Updated**: December 29, 2025  
**Purpose**: Comprehensive guide for using the PBX web admin panel

## Table of Contents
- [Accessing the Admin Panel](#accessing-the-admin-panel)
- [Admin vs User Interface](#admin-vs-user-interface)
- [Extension Management](#extension-management)
- [Auto Attendant Management](#auto-attendant-management)
- [Voicemail Management](#voicemail-management)
- [Access Control](#access-control)

---

## Accessing the Admin Panel

### URL
Access the admin panel at:
```
https://YOUR_PBX_IP:8080/admin/
```

Or if using reverse proxy:
```
https://pbx.yourcompany.com/admin/
```

### Login
1. Navigate to the admin panel URL
2. Enter your extension number
3. Enter your password
4. Click "Login"

**Note:** Your access level (admin vs user) is determined by your extension configuration.

---

## Admin vs User Interface

The PBX provides different interfaces based on user permissions:

### Admin Users

**Admin extensions see:**
- ✅ Extensions management (add/edit/delete)
- ✅ Auto Attendant configuration
- ✅ Voicemail box management for all users
- ✅ System configuration
- ✅ Call queues and conferences
- ✅ Integration settings
- ✅ Phone and voicemail features

**Admin extensions are configured in** `config.yml`:
```yaml
extensions:
  - number: "1001"
    name: "Admin User"
    is_admin: true  # This grants admin privileges
    email: "admin@company.com"
```

### Regular Users

**Regular user extensions see:**
- ✅ Phone Book (view company directory)
- ✅ Voicemail (access their own voicemail)
- ❌ No administrative features
- ❌ Cannot see or modify other users' settings

**Regular user extensions:**
```yaml
extensions:
  - number: "1002"
    name: "Regular User"
    is_admin: false  # Or omit this field (default is false)
    email: "user@company.com"
```

### Benefits of Separate Interfaces

- **Security**: Regular users cannot access administrative functions
- **Simplicity**: Users only see features they need
- **Compliance**: Better audit trail for administrative changes
- **User Experience**: Cleaner interface for end users

---

## Extension Management

**Admin-only feature**

### Accessing Extension Management

1. Login as admin
2. Click **"Extensions"** tab in navigation bar

### Managing Extensions

**View Extensions:**
- See list of all configured extensions
- View extension details (number, name, email, status)

**Add Extension:**
1. Click **"➕ Add Extension"** button
2. Fill in the form:
   - **Extension Number**: Numeric identifier (e.g., 1003)
   - **Name**: User's full name
   - **Email**: For voicemail notifications
   - **Password**: Secure password for phone registration
   - **Allow External Calls**: Enable/disable external dialing
   - **Admin**: Check if this user should have admin privileges
3. Click **"Add"**

**Edit Extension:**
1. Click **"✏️ Edit"** button next to extension
2. Modify desired fields
3. Click **"Save"**

**Delete Extension:**
1. Click **"🗑️ Delete"** button next to extension
2. Confirm deletion
3. Extension is removed from system

---

## Auto Attendant Management

**Admin-only feature**

### Accessing Auto Attendant Settings

1. Login as admin
2. Click **"Auto Attendant"** tab in navigation bar

### Configuration Options

**General Settings:**

- **Enable Auto Attendant**: Toggle to enable/disable the system
- **Extension Number**: The extension to reach auto attendant (typically `0`)
- **Timeout (seconds)**: How long to wait for DTMF input before repeating (5-60 seconds)
- **Max Retries**: Maximum invalid attempts before transferring to operator (1-10)
- **Operator Extension**: Fallback extension for operator or invalid inputs

Click **"💾 Save Settings"** to apply changes.

### Menu Options

Menu options define what happens when callers press digits.

**Adding a Menu Option:**

1. Click **"➕ Add Menu Option"** button
2. Fill in the form:
   - **Digit**: The digit callers will press (0-9, *, or #)
   - **Destination Extension**: Where to transfer the call
   - **Description**: Human-readable description
3. Click **"Add Menu Option"**

**Example Configuration:**
```
Digit: 1
Destination: 8001
Description: Sales Department

Digit: 2
Destination: 8002
Description: Support Department

Digit: 0
Destination: 1001
Description: Operator
```

**Editing Menu Options:**
1. Click **"✏️ Edit"** button next to menu option
2. Modify fields
3. Click **"Save"**

**Deleting Menu Options:**
1. Click **"🗑️ Delete"** button next to menu option
2. Confirm deletion

### Submenu Support

Create hierarchical menus for complex call routing:

**Creating a Submenu:**
1. Click **"➕ Add Submenu"** button
2. Fill in:
   - **Submenu ID**: Unique identifier (e.g., `sales-submenu`)
   - **Parent Menu**: Select parent menu or leave as root
   - **Description**: Purpose of this submenu
3. Add menu options specific to this submenu

**Example Hierarchical Menu:**
```
Main Menu (0):
  1 → Sales (submenu: sales-menu)
      1 → New Sales (ext: 8011)
      2 → Existing Customers (ext: 8012)
      0 → Return to Main Menu
  2 → Support (submenu: support-menu)
      1 → Technical Support (ext: 8021)
      2 → Billing Support (ext: 8022)
      0 → Return to Main Menu
  0 → Operator (ext: 1001)
```

### Voice Prompts

Voice prompts must be generated before the auto attendant will work:

```bash
# Generate voice prompts
python scripts/generate_tts_prompts.py --company "Your Company Name"

# Verify files were created
ls -lh auto_attendant/*.wav
```

See [VOICE_PROMPTS_GUIDE.md](VOICE_PROMPTS_GUIDE.md) for detailed instructions.

---

## Voicemail Management

### User Voicemail (All Users)

**Accessible by**: All users (for their own voicemail)

1. Click **"Voicemail"** tab
2. View your voicemail messages
3. Listen to, delete, or manage messages

### Admin Voicemail Management

**Admin-only feature** - Manage voicemail boxes for all extensions

#### Accessing Voicemail Management

1. Login as admin
2. Click **"Voicemail"** tab
3. Select an extension from the dropdown menu

#### Mailbox Overview

Once an extension is selected, you'll see:

- **Total Messages**: Count of all voicemail messages
- **Unread Messages**: Count of unread messages
- **Custom Greeting**: Whether a custom greeting is configured

#### Export Voicemail Box

Export all voicemail messages for an extension as a ZIP file. Useful for:
- User leaving the organization
- Archiving messages for compliance
- Backing up important voicemails
- Transferring messages to another system

**To export:**

1. Select the extension
2. Click **"📦 Export All Voicemails"** button
3. Confirm the export
4. A ZIP file will be downloaded containing:
   - All voicemail audio files (.wav format)
   - MANIFEST.txt with detailed message information

**Manifest Contents:**
```
Extension: 1002
Exported: 2025-12-29 10:30:00
Total Messages: 5

Message 1:
  File: voicemail_1002_20251220_143025.wav
  From: John Doe <1001>
  Date: 2025-12-20 14:30:25
  Duration: 45 seconds
  Status: unread
  
Message 2:
  File: voicemail_1002_20251221_090015.wav
  From: External <+15551234567>
  Date: 2025-12-21 09:00:15
  Duration: 32 seconds
  Status: read
```

#### Voicemail Operations

**Listen to Messages:**
- Click the play button to listen
- Audio plays in browser

**Delete Messages:**
1. Select message(s) to delete
2. Click **"🗑️ Delete"** button
3. Confirm deletion

**Mark as Read/Unread:**
- Click to toggle message status

**Download Individual Message:**
- Right-click on message
- Select "Save as" to download .wav file

---

## Access Control

**Admin-only feature**

### Extension-Level Access Control

Control which extensions can access specific features:

**Configurable Permissions:**

1. **Admin Access**: Full system administration
   ```yaml
   is_admin: true
   ```

2. **External Calling**: Allow/deny external calls
   ```yaml
   allow_external: true
   ```

3. **Voicemail Access**: Access to voicemail system
   ```yaml
   voicemail_enabled: true
   ```

4. **Call Recording**: Permission to record calls
   ```yaml
   can_record: true
   ```

5. **Conference Hosting**: Create conference rooms
   ```yaml
   can_host_conference: true
   ```

### Managing Access via Admin Panel

1. Navigate to **Extensions** tab
2. Click **"✏️ Edit"** next to extension
3. Toggle permissions as needed:
   - ☑️ Admin privileges
   - ☑️ Allow external calls
   - ☑️ Enable voicemail
   - ☑️ Allow call recording
   - ☑️ Allow conference hosting
4. Click **"Save"**

### Managing Access via config.yml

```yaml
extensions:
  - number: "1001"
    name: "Admin User"
    is_admin: true
    allow_external: true
    voicemail_enabled: true
    can_record: true
    can_host_conference: true
    
  - number: "1002"
    name: "Regular User"
    is_admin: false
    allow_external: true
    voicemail_enabled: true
    can_record: false
    can_host_conference: false
    
  - number: "1003"
    name: "Restricted User"
    is_admin: false
    allow_external: false  # Internal calls only
    voicemail_enabled: true
    can_record: false
    can_host_conference: false
```

### Role-Based Access Summary

| Feature | Admin | Regular User | Restricted User |
|---------|-------|--------------|-----------------|
| Make internal calls | ✅ | ✅ | ✅ |
| Make external calls | ✅ | ✅ | ❌ |
| Voicemail access | ✅ | ✅ | ✅ |
| Call recording | ✅ | ❌ | ❌ |
| Conference hosting | ✅ | ❌ | ❌ |
| Extension management | ✅ | ❌ | ❌ |
| Auto attendant config | ✅ | ❌ | ❌ |
| System settings | ✅ | ❌ | ❌ |
| View all voicemail boxes | ✅ | ❌ | ❌ |

---

## Additional Features

### Phone Book

**Accessible by**: All users

- View company directory
- Search for colleagues
- See contact information
- Click-to-dial from browser (if WebRTC enabled)

### Call History

**Accessible by**: All users (own calls), Admins (all calls)

- View call history
- See call duration, timestamp
- Caller ID information
- Call outcome (answered, missed, busy)

### System Status

**Admin-only feature**

- View system health
- Check active calls
- Monitor resource usage
- View service status

---

## Tips and Best Practices

### For Administrators

1. **Regular backups**: Export voicemail boxes regularly
2. **Review access**: Periodically audit extension permissions
3. **Monitor logs**: Check for unauthorized access attempts
4. **Update passwords**: Enforce password changes periodically
5. **Test auto attendant**: Verify menu options work after changes

### For All Users

1. **Use strong passwords**: For phone registration security
2. **Check voicemail regularly**: Don't let mailbox fill up
3. **Custom greetings**: Record personal voicemail greeting
4. **Update contact info**: Keep email address current for notifications
5. **Hard refresh after updates**: Press Ctrl+Shift+R if interface looks wrong

---

## Troubleshooting

### Cannot Login

**Check:**
- Extension number is correct
- Password is correct
- PBX service is running: `sudo systemctl status pbx`
- API port is accessible (default: 9000)

**Solution:**
```bash
# Verify extension exists
python scripts/list_extensions_from_db.py

# Reset password if needed
python scripts/reset_extension_password.py 1001 newpassword
```

### Admin Features Not Visible

**Check:**
- Extension has `is_admin: true` in configuration
- Logged in with correct admin extension
- Browser cache cleared (Ctrl+Shift+R)

### Changes Not Saving

**Check:**
- No error messages in browser console (F12)
- PBX service is running
- Database is accessible

**Solution:**
```bash
# Check logs for errors
sudo journalctl -u pbx -n 50

# Restart PBX
sudo systemctl restart pbx
```

### Voicemail Export Not Working

**Check:**
- Extension has voicemail messages
- Sufficient disk space for ZIP creation
- Browser allows downloads

---

## Getting Help

For additional assistance:

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - General troubleshooting
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Integration issues
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation

---

**Last Updated**: December 29, 2025  
**Status**: Production Ready
