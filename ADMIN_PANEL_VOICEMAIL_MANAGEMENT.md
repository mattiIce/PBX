# Voicemail Box Management via Admin Panel

## Overview

The admin panel now provides comprehensive voicemail box management features, including the ability to export entire voicemail boxes when users leave the organization. All voicemail operations can be performed through the web interface without terminal access.

## Accessing Voicemail Management

1. Open the Admin Panel at `http://YOUR_PBX_IP:8080/admin/`
2. Click on the **"Voicemail"** tab in the navigation bar
3. Select an extension from the dropdown menu

## Features

### Mailbox Overview

Once an extension is selected, you'll see:

- **Total Messages**: Count of all voicemail messages
- **Unread Messages**: Count of unread messages
- **Custom Greeting**: Whether a custom greeting is configured

### Export Voicemail Box

Export all voicemail messages for an extension as a ZIP file. This is particularly useful when:
- A user is leaving the organization
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
Voicemail Export Manifest
Extension: 1001
Export Date: 2024-01-15T10:30:00
Total Messages: 5

Message Details:
--------------------------------------------------------------------------------

File: 2015551234_20240115_093000.wav
Caller ID: 2015551234
Timestamp: 2024-01-15 09:30:00
Duration: 45s
Status: Unread
```

### Clear All Messages

Remove all voicemail messages from a mailbox:

1. Select the extension
2. Click **"🗑️ Clear All Messages"** button
3. Confirm the action (requires double confirmation)

**⚠️ Warning**: This action cannot be undone. Consider exporting messages first.

### Voicemail PIN Management

Update the voicemail PIN for an extension:

1. Select the extension
2. Enter a new 4-digit PIN
3. Click **"💾 Update PIN"**

The user will need this PIN to access their voicemail.

### Individual Message Management

For each message, you can:

- **▶ Play**: Listen to the voicemail in your browser
- **⬇ Download**: Download the audio file
- **✓ Mark Read**: Mark the message as read (if unread)
- **🗑 Delete**: Delete a specific message

## API Endpoints

For programmatic access or automation:

### List All Voicemail Boxes
```bash
GET /api/voicemail-boxes
```

Returns statistics for all configured voicemail boxes.

### Get Mailbox Details
```bash
GET /api/voicemail-boxes/{extension}
```

Returns detailed information about a specific mailbox including all messages.

### Export Mailbox
```bash
POST /api/voicemail-boxes/{extension}/export
```

Returns a ZIP file containing all voicemails and a manifest.

**Example using curl:**
```bash
curl -X POST http://YOUR_PBX_IP:8080/api/voicemail-boxes/1001/export \
  -o voicemail_1001_export.zip
```

### Clear All Messages
```bash
DELETE /api/voicemail-boxes/{extension}/clear
```

Deletes all messages from the specified mailbox.

### Custom Greeting Management

#### Upload Custom Greeting
```bash
PUT /api/voicemail-boxes/{extension}/greeting
Content-Type: audio/wav
[Binary WAV data]
```

#### Download Custom Greeting
```bash
GET /api/voicemail-boxes/{extension}/greeting
```

#### Delete Custom Greeting
```bash
DELETE /api/voicemail-boxes/{extension}/greeting
```

### Individual Message Operations

Existing API endpoints for individual message operations:

```bash
# Get messages for extension
GET /api/voicemail/{extension}

# Get specific message audio
GET /api/voicemail/{extension}/{message_id}

# Mark message as read
PUT /api/voicemail/{extension}/{message_id}/mark-read

# Delete specific message
DELETE /api/voicemail/{extension}/{message_id}

# Update voicemail PIN
PUT /api/voicemail/{extension}/pin
Content-Type: application/json
{"pin": "1234"}
```

## Use Cases

### Employee Offboarding

When an employee leaves:

1. Export their voicemail box for archiving
2. Save the ZIP file to your document management system
3. Clear the mailbox or reassign the extension
4. Keep the export for the required retention period

### Compliance and Archiving

For organizations with compliance requirements:

1. Regularly export voicemail boxes
2. Store exports in a secure, backed-up location
3. Maintain exports for the required retention period
4. Document export dates and reasons

### Troubleshooting User Issues

When a user reports missing messages:

1. Export their mailbox to review all messages
2. Check the manifest for message timestamps
3. Verify messages weren't accidentally deleted
4. Restore from backup if needed

### System Migration

When migrating to a new system:

1. Export all voicemail boxes
2. Transfer ZIP files to the new system
3. Import messages into the new system (if supported)
4. Verify all messages transferred correctly

## Best Practices

### Regular Exports

- Schedule regular exports for critical mailboxes
- Archive exports offsite for disaster recovery
- Document your export schedule and retention policy
- Test restore procedures periodically

### Storage Management

- Monitor voicemail storage usage
- Set quotas for mailbox sizes
- Encourage users to delete old messages
- Clear mailboxes of departed employees

### Security

- Limit access to voicemail management
- Audit exports and who performed them
- Encrypt archived voicemail exports
- Follow data retention policies

### User Education

- Train users on voicemail PIN management
- Teach users to delete unneeded messages
- Provide guidance on custom greetings
- Explain backup and archiving policies

## Troubleshooting

### Export Not Working

1. Check disk space on the PBX server
2. Verify voicemail directory permissions
3. Check PBX logs for errors
4. Ensure messages exist in the mailbox
5. Try exporting a smaller mailbox first

### Downloaded ZIP is Corrupted

1. Check network connection stability
2. Try downloading again
3. Verify web browser is up to date
4. Check server logs for transfer errors
5. Try a different browser

### Messages Not Showing Up

1. Verify the correct extension is selected
2. Check if database is enabled and working
3. Verify voicemail directory path
4. Check file permissions on voicemail files
5. Review PBX logs for database errors

### Clear Not Working

1. Check file permissions on voicemail directory
2. Verify database connectivity (if enabled)
3. Check for locked files
4. Review PBX logs for specific errors
5. Try deleting individual messages first

## Technical Details

### File Structure

Voicemail files are stored in:
```
voicemail/
  ├── 1001/
  │   ├── greeting.wav (optional custom greeting)
  │   ├── CallerID_20240115_093000.wav
  │   └── CallerID_20240115_101500.wav
  ├── 1002/
  └── ...
```

### Export ZIP Structure

```
voicemail_1001_20240115_103000.zip
  ├── MANIFEST.txt
  ├── 2015551234_20240115_093000.wav
  ├── 2015551234_20240115_101500.wav
  └── ...
```

### Database Integration

If PostgreSQL database is enabled:
- Voicemail metadata is stored in `voicemail_messages` table
- File paths are stored in database
- Messages are loaded from database first, falling back to filesystem
- Clear operation removes both database records and files

### Storage Considerations

- Each voicemail uses ~50-200 KB depending on duration
- Custom greetings are typically 30-50 KB
- Exports create temporary files (cleaned up automatically)
- Plan for adequate storage based on user count and retention

## Security Considerations

### Data Protection

- Voicemail exports contain sensitive information
- Encrypt exports before transmitting or storing externally
- Follow your organization's data handling policies
- Implement access controls on admin panel

### Audit Trail

- Log all export operations with user and timestamp
- Track who clears mailboxes and when
- Monitor for unusual access patterns
- Review logs regularly for compliance

### Access Control

- Restrict admin panel access to authorized personnel
- Use strong authentication
- Consider implementing MFA for admin access
- Regular review of admin user accounts

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review PBX logs in `/var/log/` or application logs
3. Verify configuration in `config.yml`
4. Consult the main PBX documentation
5. Check GitHub issues for similar problems
