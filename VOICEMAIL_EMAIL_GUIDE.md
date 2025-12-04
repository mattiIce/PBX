# Voicemail-to-Email Guide

This guide explains how to configure and use the voicemail-to-email functionality in the PBX system.

## Overview

The PBX system includes comprehensive voicemail-to-email functionality that:
- **Instantly emails** voicemail notifications when messages are received
- **Includes audio attachment** of the voicemail message
- **Provides all message details** (caller ID, timestamp, duration)
- **Routes calls to voicemail** automatically when not answered (configurable timeout)
- **Sends daily reminders** for unread voicemails

## Configuration

### 1. SMTP Server Settings

Edit `config.yml` and configure your SMTP server:

```yaml
voicemail:
  email_notifications: true
  no_answer_timeout: 30  # Seconds before routing to voicemail
  
  smtp:
    host: "192.168.1.75"  # Your SMTP server
    port: 587             # SMTP port (587 for TLS, 465 for SSL)
    use_tls: true         # Enable TLS encryption
    username: "cmattinson"
    password: "G0N@vyBuyC@n3$"
```

### 2. Email Settings

Configure the email sender and template:

```yaml
  email:
    from_address: "Voicemail@albl.com"
    from_name: "ABCo Voicemail"
    subject_template: "New Voicemail from {caller_id} - {timestamp}"
    include_attachment: true
    send_immediately: true
```

### 3. Daily Reminders

Enable daily reminders for unread voicemails:

```yaml
  reminders:
    enabled: true
    time: "09:00"  # 9:00 AM
    unread_only: true
```

### 4. Extension Email Addresses

Add email addresses to each extension:

```yaml
extensions:
  - number: "1001"
    name: "Office Extension 1"
    password: "password1001"
    email: "ext1001@albl.com"  # Email for voicemail notifications
  
  - number: "1002"
    name: "Office Extension 2"
    password: "password1002"
    email: "ext1002@albl.com"
```

## How It Works

### No-Answer Routing

1. User A calls Extension 1001
2. Extension 1001 rings for 30 seconds (configurable)
3. If not answered, call is automatically routed to voicemail
4. Caller hears a greeting prompt: "Please leave a message after the tone"
5. A beep tone signals the start of recording
6. Caller leaves their message
7. Message is saved when caller hangs up
8. Email notification sent immediately to extension owner

### Email Notification

When a voicemail is received, an email is sent containing:

**Subject:** `New Voicemail from 1002 - 2025-12-03 14:30:15`

**Body:**
```
Hello,

You have received a new voicemail message.

Message Details:
  Extension: 1001
  From: 1002
  Received: 2025-12-03 14:30:15
  Duration: 0:45

To listen to this message, please dial *1001

Best regards,
ABCo Voicemail
```

**Attachment:** Audio file (WAV format) of the voicemail message

### Daily Reminders

If reminders are enabled, users receive a daily email at the configured time:

**Subject:** `Voicemail Reminder: 3 Unread Messages`

**Body:**
```
Hello,

You have 3 unread voicemail messages in your mailbox (Extension 1001):

1. From: 1002, Received: 2025-12-03 14:30:15
2. From: 1003, Received: 2025-12-03 16:45:22
3. From: 1004, Received: 2025-12-04 09:12:05

Please check your voicemail by dialing *1001

Best regards,
ABCo Voicemail
```

## Accessing Your Voicemail

To check your voicemail messages, dial `*` followed by your extension number (e.g., `*1001`).

### Interactive Voicemail Menu

When you access your voicemail, you'll be guided through an interactive menu system:

1. **Welcome & Authentication**
   - System announces the number of new messages
   - Enter your 4-digit PIN followed by `#`
   - After 3 failed attempts, the system will disconnect

2. **Main Menu**
   - Press `1` - Listen to your messages
   - Press `2` - Access options menu (record greeting, change settings)
   - Press `*` - Exit voicemail system

3. **Message Playback Menu** (while listening to messages)
   - Press `1` - Replay the current message
   - Press `2` - Skip to next message
   - Press `3` - Delete the current message
   - Press `*` - Return to main menu

4. **Options Menu**
   - Press `1` - Record a custom voicemail greeting
   - Press `*` - Return to main menu

5. **Recording Greeting**
   - Record your greeting after the tone
   - Press `#` when finished recording
   - Your custom greeting will be played to callers when they leave you a voicemail

### Example Session

```
1. Dial *1001 from your phone
2. System: [Tone prompt indicating message count]
3. System: [Tone prompt requesting PIN]
4. You: Enter 1234# (your PIN)
5. System: [Main menu tone]
6. You: Press 1 to listen to messages
7. System: [Plays first voicemail message]
8. System: [Message menu tone]
9. You: Press 2 to hear next message
10. System: [Plays second voicemail message]
11. You: Press 3 to delete this message
12. System: [Message deleted confirmation]
13. You: Press * to return to main menu
14. You: Press * again to exit
15. System: [Goodbye tone]
```

## Recording Your Custom Greeting

### Overview
You can record a personalized voicemail greeting that will be played to callers when they leave you a message. This allows you to create a professional, personalized message instead of using the default system greeting.

### How to Record a Custom Greeting

1. **Access Your Voicemail**
   - Dial `*` followed by your extension number (e.g., `*1001`)
   - Enter your 4-digit PIN followed by `#`

2. **Navigate to Options Menu**
   - From the main menu, press `2` to access options

3. **Start Recording**
   - Press `1` to record your greeting
   - Listen for the tone indicating recording has started
   - Speak your greeting message (maximum 30 seconds)
   - Examples:
     - "Hi, you've reached John Smith. I'm unable to take your call right now. Please leave a message and I'll get back to you as soon as possible."
     - "You've reached extension 1001. Please leave your name, number, and a brief message after the beep."

4. **Finish Recording**
   - Press `#` when you're done recording
   - Your greeting will be saved automatically

5. **Return to Main Menu**
   - Press `*` to return to the main menu
   - Press `*` again to exit the voicemail system

### Tips for a Good Greeting
- Speak clearly and at a moderate pace
- Include your name and/or extension number
- Keep it professional and concise (10-20 seconds is ideal)
- Let callers know you'll return their call
- Re-record if you're not satisfied with the first attempt

### Using Your Custom Greeting
Once recorded, your custom greeting will automatically play to callers when:
- They call your extension and you don't answer
- The call is routed to voicemail after the configured timeout (default: 30 seconds)

### Reverting to Default Greeting
To use the default system greeting again, you would need to delete your custom greeting file from the voicemail directory or contact your system administrator.

## Testing

### Test Email Configuration

1. Verify SMTP settings are correct
2. Start the PBX system: `python main.py`
3. Make a test call to an extension and let it go unanswered
4. Check the recipient's email for the voicemail notification

### Test No-Answer Routing

1. Call an extension from another extension
2. Let it ring without answering
3. After 30 seconds (or configured timeout), the call should route to voicemail
4. You can leave a test message
5. Check that the email notification is received

### Troubleshooting

**Email not received:**
- Check SMTP server address and port
- Verify username and password are correct
- Ensure TLS settings match your server requirements
- Check firewall rules allow outbound SMTP connections
- Review logs at `logs/pbx.log` for error messages

**Call doesn't route to voicemail:**
- Verify `no_answer_timeout` is set in config.yml
- Check that voicemail feature is enabled: `features.voicemail: true`
- Ensure extension has valid configuration

**Reminders not sent:**
- Check that `reminders.enabled: true`
- Verify reminder time format is correct (HH:MM)
- System must be running at the scheduled reminder time

## Email Security

For production use, consider:
- Using application-specific passwords (e.g., Gmail App Passwords)
- Enabling TLS/SSL encryption (`use_tls: true`)
- Restricting SMTP access to trusted networks
- Using a dedicated email account for PBX notifications

## Advanced Configuration

### Custom Email Templates

You can customize the subject line with these placeholders:
- `{caller_id}` - Caller's extension number
- `{timestamp}` - When the voicemail was received
- `{extension}` - Extension that received the voicemail

Example:
```yaml
subject_template: "[PBX] Missed call from {caller_id} on {timestamp}"
```

### Reminder Schedule

Reminders are sent once daily at the specified time. To change the schedule:

```yaml
reminders:
  enabled: true
  time: "17:00"  # Send at 5 PM instead
```

### Disable Attachments

To send emails without audio attachments (useful for large files or bandwidth constraints):

```yaml
email:
  include_attachment: false
```

## Support

For issues or questions, check:
- System logs: `logs/pbx.log`
- Test email configuration: `python tests/test_voicemail_email.py`
- GitHub issues: https://github.com/mattiIce/PBX/issues
