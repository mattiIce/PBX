# Voicemail Custom Greeting Guide

**Date**: December 8, 2025  
**Feature**: Custom Voicemail Greeting Recording via IVR Menu

## Overview

Users can now record, review, and manage their custom voicemail greetings directly through the voicemail IVR system. This provides a complete self-service experience without requiring administrator intervention.

## Features

### Custom Greeting Management
- **Record**: Record a personal greeting via phone
- **Review**: Listen to the recorded greeting before saving
- **Re-record**: Record again if not satisfied with the greeting
- **Delete**: Remove custom greeting and use system default
- **Save**: Permanently save the custom greeting

### User Experience
- Simple menu-driven interface
- Clear voice prompts for each step
- Ability to review before committing
- Option to return to default greeting

## How to Record a Custom Greeting

### Step-by-Step Instructions

1. **Access Voicemail**
   - Dial `*97` (or your system's voicemail access number)
   - You will hear: "Please enter your PIN followed by pound"

2. **Enter Your PIN**
   - Enter your voicemail PIN digits
   - Press `#` to confirm
   - You will hear: "You have X new messages. Press 1 to listen, 2 for options, * to exit"

3. **Access Options Menu**
   - Press `2` for options
   - You will hear: "Press 1 to record greeting, * to return to main menu"

4. **Start Recording**
   - Press `1` to record greeting
   - You will hear: "Record your greeting after the tone. Press # when finished."
   - After the beep, speak your greeting message
   - Press `#` when you finish speaking

5. **Review Your Greeting**
   - You will hear: "Greeting recorded. Press 1 to listen, 2 to re-record, 3 to delete and use default, * to save and return to main menu"
   
   **Options:**
   - Press `1`: Listen to your recorded greeting
   - Press `2`: Re-record the greeting (starts over from step 4)
   - Press `3`: Delete the custom greeting and use system default
   - Press `*`: Save the greeting and return to main menu

6. **Complete**
   - If you press `*` to save, you will hear: "Greeting saved. You have X new messages..."
   - Your custom greeting is now active

## IVR Menu Structure

```
Main Menu
  └─ Press 2 → Options Menu
                 └─ Press 1 → Start Recording Greeting
                              └─ Press # → Review Menu
                                           ├─ Press 1: Play greeting
                                           ├─ Press 2: Re-record
                                           ├─ Press 3: Delete greeting
                                           └─ Press *: Save greeting
                 └─ Press * → Return to Main Menu
```

## Technical Details

### Recording Specifications
- **Maximum Duration**: 2 minutes (120 seconds)
- **Audio Format**: G.711 μ-law (PCMU) at 8kHz
- **Storage Location**: `voicemail/{extension}/greeting.wav`
- **Automatic Timeout**: Recording stops after 2 minutes

### File Management
- Greeting files are stored per-extension
- Only one custom greeting per extension
- Re-recording overwrites previous greeting
- Deleting greeting removes file and uses system default

### State Management
The IVR maintains proper state transitions:
- `STATE_MAIN_MENU` → `STATE_OPTIONS_MENU` → `STATE_RECORDING_GREETING` → `STATE_GREETING_REVIEW` → `STATE_MAIN_MENU`

## Default vs Custom Greetings

### System Default Greeting
When no custom greeting exists, the system plays:
- "You have reached extension {number}. Please leave a message after the tone."

### Custom Greeting
When a custom greeting is recorded:
- System plays user's recorded audio
- More personal and professional
- Can include specific instructions or information

## API Integration

### Check for Custom Greeting

```python
from pbx.features.voicemail import VoicemailSystem

vm_system = VoicemailSystem(storage_path='voicemail')
mailbox = vm_system.get_mailbox('1001')

if mailbox.has_custom_greeting():
    greeting_path = mailbox.get_greeting_path()
    print(f"Custom greeting exists at: {greeting_path}")
else:
    print("Using default greeting")
```

### Programmatic Greeting Management

```python
# Save greeting via code
audio_data = b'...'  # WAV audio data
success = mailbox.save_greeting(audio_data)

# Delete greeting via code
mailbox.delete_greeting()

# Get greeting path
path = mailbox.get_greeting_path()
```

## Troubleshooting

### Greeting Not Saving
**Problem**: Greeting doesn't save after pressing *

**Solutions**:
- Ensure you press `#` to finish recording
- Make sure you're in the review menu (you should hear review options)
- Verify storage directory exists and is writable
- Check logs: `logs/pbx.log` for errors

### Can't Hear Recording During Review
**Problem**: Silence when pressing 1 to play back greeting

**Solutions**:
- Ensure recording wasn't empty (press `#` too quickly)
- Verify RTP audio is working properly
- Check that recorder captured audio data
- Review logs for playback errors

### PIN Entry Issues
**Problem**: IVR doesn't respond after entering PIN

**Solutions**:
- Ensure you press `#` after entering PIN digits
- Verify PIN is configured correctly in config.yml
- Check call state is still active
- Review logs for state transition issues

### Recording Timeout
**Problem**: Recording stops automatically

**Solution**: The system has a 2-minute maximum recording time. Keep greetings concise (15-30 seconds recommended).

## Best Practices

### Greeting Content
1. **Identify Yourself**: State your name or extension
2. **Set Expectations**: "I'll return your call within 24 hours"
3. **Provide Alternatives**: "For urgent matters, press 0 for operator"
4. **Be Brief**: Keep greetings under 30 seconds
5. **Update Regularly**: Change greeting when on vacation or out of office

### Example Greetings

**Professional**:
> "You've reached John Smith at extension 1001. I'm either on another call or away from my desk. Please leave your name, number, and a brief message, and I'll return your call within 24 hours. For immediate assistance, press 0 to reach our operator."

**Brief**:
> "Hi, this is John Smith. Please leave a message and I'll get back to you soon. Thanks!"

**Out of Office**:
> "You've reached John Smith. I'm out of the office until Monday, January 15th. For urgent matters, please contact Jane Doe at extension 1002. Otherwise, leave a message and I'll respond when I return."

## Security Considerations

### PIN Protection
- Always use a secure PIN (not 1234 or 0000)
- Never share your voicemail PIN
- Change PIN regularly

### Recording Privacy
- Greeting files are stored per-extension with file system permissions
- Only the extension owner (with correct PIN) can modify greetings
- Audio data is stored on server file system, not in database

## Integration with Call Flow

When a call goes to voicemail:

1. System checks if extension has custom greeting
2. If custom greeting exists:
   - Plays custom greeting audio file
   - Plays beep tone
   - Starts recording voicemail
3. If no custom greeting:
   - Plays system default greeting
   - Plays beep tone
   - Starts recording voicemail

## Database Schema

Greeting metadata is stored in the database (if database is enabled):

```sql
-- Extension configuration includes greeting flag
SELECT has_custom_greeting FROM extensions WHERE extension_number = '1001';

-- Greeting files themselves are stored on file system
-- Path: voicemail/{extension}/greeting.wav
```

## Configuration

No special configuration needed. Greeting recording is enabled by default when voicemail is enabled.

### Config.yml Settings
```yaml
voicemail:
  enabled: true
  storage_path: "voicemail"  # Base path for voicemail and greetings
  
  # Maximum recording time in seconds (default: 120)
  max_greeting_duration: 120
  
  # IVR timeout in seconds (default: 60)
  ivr_timeout: 60
```

## Testing

Run the greeting menu tests:
```bash
python3 tests/test_voicemail_greeting_menu.py
```

Expected output:
```
============================================================
Running Voicemail Greeting Menu Tests
============================================================

Testing access to options menu...
✓ Successfully accessed options menu
Testing start greeting recording...
✓ Successfully started greeting recording
Testing finish greeting recording...
✓ Successfully finished greeting recording
Testing greeting review playback...
✓ Successfully requested greeting playback
Testing greeting re-record...
✓ Successfully started re-recording
Testing greeting deletion...
✓ Successfully deleted greeting
Testing greeting save...
✓ Successfully saved greeting
Testing complete greeting workflow...
✓ Successfully completed greeting workflow
Testing return to main menu from options...
✓ Successfully returned to main menu

============================================================
Results: 9 passed, 0 failed
============================================================
```

## Administrative Tasks

### List Extensions with Custom Greetings
```bash
find voicemail/ -name "greeting.wav" -type f
```

### Backup All Greetings
```bash
tar -czf greetings_backup.tar.gz voicemail/*/greeting.wav
```

### Restore Greetings
```bash
tar -xzf greetings_backup.tar.gz
```

### Delete All Custom Greetings (Reset to Default)
```bash
find voicemail/ -name "greeting.wav" -type f -delete
```

## Changelog

### Version 1.0 (December 8, 2025)
- ✅ Added custom greeting recording via IVR
- ✅ Added greeting review menu (play, re-record, delete, save)
- ✅ Added greeting playback during review
- ✅ Added greeting deletion to revert to default
- ✅ Implemented proper state management
- ✅ Added comprehensive test suite
- ✅ Fixed IVR session handling for greeting recording
- ✅ Added temporary storage for greeting review

## Debugging and Logging

### VM IVR Dedicated Logging

The Voicemail IVR system has its own dedicated log file separate from the main PBX logs, making it easier to troubleshoot voicemail-specific issues.

**Log File Location**: `logs/vm_ivr.log`

All voicemail IVR activity is logged to this dedicated file, including:
- PIN entry and verification
- IVR state transitions
- DTMF digit processing
- Menu navigation
- Message playback
- Voicemail actions (delete, save, etc.)
- Greeting recording and management
- Debug PIN logging (when DEBUG_VM_PIN=true)

**Benefits**:
- ✅ Easier troubleshooting - all VM IVR logs in one place
- ✅ Reduced noise - main PBX log is cleaner
- ✅ Better analysis - can analyze voicemail patterns separately
- ✅ Improved debugging - sensitive PIN data stays in dedicated log

**Viewing VM IVR Logs**:

```bash
# View recent VM IVR activity
tail -f logs/vm_ivr.log

# View last 50 lines
tail -50 logs/vm_ivr.log

# Search for specific extension
grep "extension 1001" logs/vm_ivr.log

# Search for PIN failures
grep "INVALID" logs/vm_ivr.log

# View greeting-related activity
grep "greeting" logs/vm_ivr.log
```

### PIN Debug Logging

For troubleshooting DTMF PIN recognition issues, enable detailed debug logging:

**⚠️ Security Warning**: This feature logs sensitive PIN data and should **ONLY** be used for testing and troubleshooting purposes. **DO NOT enable this in production environments.**

#### Enable Debug Logging

**Method 1: Using .env file (Recommended)**

Add to your `.env` file in the PBX root directory:

```bash
DEBUG_VM_PIN=true
```

Then restart the PBX:

```bash
python main.py
```

**Method 2: Inline environment variable**

```bash
DEBUG_VM_PIN=true python main.py
```

**Method 3: Export environment variable**

```bash
export DEBUG_VM_PIN=true
python main.py
```

#### What Gets Logged

When `DEBUG_VM_PIN=true` is set, you'll see detailed logging in `logs/vm_ivr.log`:

**Initialization Warning**:
```
[VM IVR] ⚠️  PIN DEBUG LOGGING ENABLED for extension 1001 - TESTING ONLY!
[VM IVR] ⚠️  Set DEBUG_VM_PIN=false to disable sensitive PIN logging
```

**Per-Digit Collection**:
```
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '1' collected, current PIN buffer: '1'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '2' collected, current PIN buffer: '12'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '3' collected, current PIN buffer: '123'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '4' collected, current PIN buffer: '1234'
```

**PIN Verification**:
```
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Entered PIN: '1234'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Expected PIN: '1234'
[VM IVR PIN] PIN verification result: VALID
```

#### Disable Debug Logging

```bash
# In .env file, set:
DEBUG_VM_PIN=false

# Or remove the line entirely, then restart
python main.py

# Or unset the environment variable
unset DEBUG_VM_PIN
```

#### Use Cases for Debug Logging

1. **DTMF Detection Issues**: Verify which digits are actually being received by the IVR
2. **PIN Configuration Problems**: Confirm the expected PIN matches what you configured
3. **Timing Issues**: See if digits are being lost or duplicated
4. **SIP INFO vs In-band DTMF**: Identify which DTMF method is working

#### Diagnosing Common Issues

**Issue: PIN buffer not accumulating**

If the buffer shows only '1' for each digit press (not accumulating to '12', '123', etc.):
- Indicates the IVR instance may be getting recreated
- Or the entered_pin is being reset between digits
- This is a bug that needs investigation

**Issue: Digits missing from buffer**

If some digits don't appear in the sequence (e.g., '1', '3', '4' but skipping '2'):
- DTMF transmission lost packets
- Phone DTMF duration too short
- Try in-band DTMF instead of SIP INFO
- Check phone DTMF configuration

**Issue: Digits duplicated**

If digits appear multiple times (e.g., '11', '112', '1123'):
- DTMF debouncing issue
- May need to adjust debounce timing
- Check if phone is sending duplicate DTMF events

**Issue: First digit lost**

If the first digit you press doesn't appear in PIN buffer:
- This was fixed in a recent update
- Ensure you're running the latest version
- The voicemail IVR now captures the first digit when transitioning from WELCOME state to PIN_ENTRY state

### Regular Logging (Without Debug)

Even without `DEBUG_VM_PIN` enabled, you still get useful (non-sensitive) logging in `logs/vm_ivr.log`:

```
[VM IVR PIN] # pressed, entered_pin length: 4
[VM IVR PIN] PIN verification result: VALID
```

or

```
[VM IVR PIN] # pressed, entered_pin length: 4
[VM IVR PIN] PIN verification result: INVALID
[VM IVR PIN] ✗ Invalid PIN attempt 1/3
```

This shows you:
- How many digits were entered
- Whether verification passed or failed
- Number of failed attempts

### Log Rotation

The `vm_ivr.log` file will grow over time. Consider implementing log rotation using:

**Linux logrotate (recommended for production)**:

```
# /etc/logrotate.d/pbx-vm-ivr
/path/to/PBX/logs/vm_ivr.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pbx pbx
}
```

## Support

For issues or questions:
1. Check logs: `logs/vm_ivr.log` (dedicated VM IVR log)
2. Check logs: `logs/pbx.log` (main PBX log)
3. Enable debug logging: `DEBUG_VM_PIN=true` for PIN issues
4. Review test results: Run test suite
5. Verify file permissions on voicemail directory
6. Check RTP audio configuration
7. Review SIP trace logs if calls aren't connecting
8. See [DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md) for DTMF troubleshooting

## Related Documentation

- [VOICEMAIL_EMAIL_GUIDE.md](VOICEMAIL_EMAIL_GUIDE.md) - Email notifications
- [VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md) - Database configuration
- [VOICEMAIL_TRANSCRIPTION_GUIDE.md](VOICEMAIL_TRANSCRIPTION_GUIDE.md) - Transcription features
- [VOICE_PROMPTS_GUIDE.md](VOICE_PROMPTS_GUIDE.md) - Voice prompt customization
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - REST API reference

---

**Built with ❤️ for creating robust voicemail systems**
