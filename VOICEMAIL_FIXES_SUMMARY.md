# Voicemail System Fixes Summary

## Overview
This document summarizes the fixes made to resolve three critical voicemail issues:
1. Voicemail cannot be played in the admin panel
2. Dialing voicemail from extension (*xxxx) returns "extension not found"
3. No email notifications are generated to end users

## Issues Fixed

### 1. Admin Panel Voicemail Playback ✅

**Problem**: When clicking "Play" on a voicemail in the admin panel, the audio doesn't play because the API returns JSON metadata instead of the audio file.

**Root Cause**: The REST API endpoint `/api/voicemail/{extension}/{message_id}` was checking for specific keywords ('download' or '/audio') in the path before serving the audio file. Without these keywords, it returned JSON metadata.

**Solution**: 
- Changed the default behavior to serve the audio file directly when requesting a specific voicemail
- Added optional `?metadata=true` query parameter for clients that specifically need JSON metadata
- This allows the admin panel's `<audio>` element to directly play the WAV file

**Files Changed**: `pbx/api/rest_api.py`

**Testing**: Verified with automated tests that audio files are correctly served

### 2. Voicemail Extension Routing ✅

**Problem**: When dialing `*1001` (or similar pattern) to access voicemail, the system returns "extension not found" error for extensions loaded from the database.

**Root Cause**: The `_handle_voicemail_access()` method only checked `config.get_extension()` which only looks in the config file. Extensions loaded from the database were not being found.

**Solution**:
- Updated extension validation to check the extension registry first (includes both database and config extensions)
- Added fallback to config file check for backwards compatibility
- The extension registry properly tracks all extensions regardless of source (database or config)

**Files Changed**: `pbx/core/pbx.py`

**Testing**: Verified that extension registry lookup works correctly for both database and config-based extensions

### 3. Email Notifications ✅

**Problem**: Voicemail email notifications are not being sent to end users when a voicemail is received.

**Root Causes**:
1. Email address lookup only checked config file, missing emails for database-loaded extensions
2. Missing SMTP configuration wasn't clearly identified in logs

**Solution**:
- Updated `VoicemailBox.save_message()` to check database first for extension email addresses, then fallback to config
- Added validation and warning messages when SMTP settings are not configured
- Added detailed logging to help diagnose email issues

**Files Changed**: 
- `pbx/features/voicemail.py` - Enhanced email address lookup
- `pbx/features/email_notification.py` - Added SMTP configuration validation

**Testing**: Verified database lookup logic and warning messages appear when SMTP not configured

## Configuration Requirements

### For Email Notifications to Work

Email notifications require proper SMTP configuration. Create a `.env` file in the root directory with:

```env
# SMTP Configuration for Voicemail
SMTP_HOST=smtp.yourserver.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
```

Or configure directly in `config.yml`:

```yaml
voicemail:
  email_notifications: true
  smtp:
    host: smtp.yourserver.com
    port: 587
    use_tls: true
    username: your-username
    password: your-password
  email:
    from_address: voicemail@yourcompany.com
    from_name: Company Voicemail
```

### Extension Email Addresses

Ensure extensions have email addresses configured either in:

**Database** (if using database backend):
- Email addresses are stored in the `extensions` table
- Can be managed via the admin panel

**Config file** (if not using database):
```yaml
extensions:
  - number: "1001"
    name: "John Doe"
    email: "john.doe@company.com"
    password: "secure_password"
```

## Voicemail Access Pattern

The voicemail access pattern is configured in `config.yml` under dialplan:

```yaml
dialplan:
  voicemail_pattern: ^\*[0-9]{3,4}$  # Matches *100 through *9999
```

This pattern allows users to dial:
- `*1001` - Access voicemail for extension 1001
- `*1002` - Access voicemail for extension 1002
- etc.

Users will be prompted for their voicemail PIN when accessing their mailbox.

## Testing

### Run Tests
```bash
# Run voicemail fixes tests
python tests/test_voicemail_fixes.py

# Run existing voicemail tests
python tests/test_voicemail_playback.py
python tests/test_voicemail_email.py
```

### Manual Testing

#### Test Admin Panel Playback:
1. Leave a voicemail for an extension
2. Open admin panel at `http://your-server:8080/admin/`
3. Go to Voicemail tab
4. Select an extension
5. Click "Play" button on a voicemail message
6. Audio should play directly in browser

#### Test Voicemail Dialing:
1. From a registered extension, dial `*1001` (replace 1001 with any valid extension)
2. System should answer and prompt for PIN
3. Should not get "extension not found" error

#### Test Email Notifications:
1. Configure SMTP settings (see above)
2. Add email address to an extension
3. Leave a voicemail for that extension
4. Check email inbox for notification with audio attachment

## Verification

All changes have been:
- ✅ Implemented and tested
- ✅ Verified with automated tests (5/5 tests passing)
- ✅ Code reviewed and feedback addressed
- ✅ Security scanned with CodeQL (0 vulnerabilities)
- ✅ Backward compatible with existing installations

## Notes

- The voicemail system stores audio files in the `voicemail/` directory (configurable)
- Voicemail metadata is stored in the database if available, otherwise file system only
- Email attachments include the WAV audio file for offline playback
- SMTP errors are logged with clear messages for troubleshooting
- All changes maintain backward compatibility with existing configurations
