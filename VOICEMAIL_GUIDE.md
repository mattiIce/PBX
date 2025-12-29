# Voicemail System Guide

**Last Updated**: December 29, 2025  
**Status**: ✅ Production-Ready  
**Purpose**: Complete guide for voicemail system setup, configuration, and usage

## Table of Contents
- [Overview](#overview)
- [Database Setup](#database-setup)
- [Email Notifications](#email-notifications)
- [Transcription Service](#transcription-service)
- [Custom Greetings](#custom-greetings)
- [User Guide](#user-guide)
- [Troubleshooting](#troubleshooting)

---

## Overview

The PBX voicemail system provides comprehensive voicemail functionality with:

- **Database Storage**: Metadata stored in PostgreSQL/SQLite with audio files on disk
- **Email Notifications**: Instant email alerts with audio attachments
- **Transcription**: Automatic speech-to-text (OpenAI, Google Cloud, or FREE offline Vosk)
- **Custom Greetings**: Users can record personal greetings via phone
- **IVR Menu**: Interactive voice response for message management
- **Daily Reminders**: Automated reminders for unread messages

### Storage Architecture

**Hybrid Approach (Industry Standard)**:
- **Database**: Stores voicemail metadata (caller ID, timestamp, duration, read status)
- **File System**: Stores actual audio WAV files

**Benefits**:
- Keeps database lightweight and fast
- Avoids storing large BLOBs in database
- Allows efficient querying of metadata
- Preserves audio file accessibility

---

## Database Setup

### Quick Verification

To verify your database is properly configured:

```bash
python scripts/verify_database.py
```

This checks:
- PostgreSQL/SQLite driver installation
- Database configuration
- Database connectivity
- Table existence
- Current voicemail count

### PostgreSQL (Recommended for Production)

**1. Install PostgreSQL**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server
sudo postgresql-setup initdb
sudo systemctl start postgresql
```

**2. Create Database and User**:
```bash
sudo -u postgres psql
```

Then in the PostgreSQL prompt:
```sql
CREATE DATABASE pbx_system;
CREATE USER pbx_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;
\q
```

**3. Configure config.yml**:
```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  name: pbx_system
  user: pbx_user
  password: ${DATABASE_PASSWORD}  # Use environment variables for security
```

**4. Install Python Driver**:
```bash
pip install psycopg2-binary
```

**5. Verify Connection**:
```bash
python scripts/verify_database.py
```

### SQLite (Recommended for Development/Testing)

**1. Configure config.yml**:
```yaml
database:
  type: sqlite
  path: pbx.db
```

**2. No additional installation needed** - SQLite is included with Python

**3. Verify Configuration**:
```bash
python scripts/verify_database.py
```

### Database Schema

The `voicemail_messages` table:

```sql
CREATE TABLE voicemail_messages (
    id                 SERIAL PRIMARY KEY,
    message_id         VARCHAR(100) UNIQUE NOT NULL,  -- Unique identifier
    extension_number   VARCHAR(20) NOT NULL,           -- Recipient extension
    caller_id          VARCHAR(50),                    -- Caller's number/ID
    file_path          VARCHAR(255),                   -- Path to WAV file
    duration           INTEGER,                        -- Duration in seconds
    listened           BOOLEAN DEFAULT FALSE,          -- Read status
    transcription      TEXT,                           -- Transcribed text
    transcription_confidence REAL,                    -- Confidence score
    created_at         TIMESTAMP DEFAULT NOW()         -- When received
);
```

### How Voicemails Are Stored

**When a voicemail is saved**:

1. **Audio File** written to disk:
   ```
   voicemail/{extension}/caller_20251229_143022.wav
   ```

2. **Metadata Record** inserted into database:
   ```sql
   INSERT INTO voicemail_messages 
   (message_id, extension_number, caller_id, file_path, duration, listened, created_at)
   VALUES (...)
   ```

---

## Email Notifications

### Configuration

**1. SMTP Server Settings**

Edit `config.yml`:

```yaml
voicemail:
  email_notifications: true
  no_answer_timeout: 30  # Seconds before routing to voicemail
  
  smtp:
    host: "smtp.gmail.com"      # Your SMTP server
    port: 587                    # SMTP port (587 for TLS, 465 for SSL)
    use_tls: true               # Enable TLS encryption
    username: "your-email@gmail.com"
    password: "${SMTP_PASSWORD}"  # Use environment variable
```

**2. Email Settings**

```yaml
  email:
    from_address: "pbx@yourcompany.com"
    from_name: "Company Voicemail"
    subject_template: "New Voicemail from {caller_id} - {timestamp}"
    include_attachment: true
    send_immediately: true
```

**3. Daily Reminders**

```yaml
  reminders:
    enabled: true
    time: "09:00"  # 9:00 AM
    unread_only: true
```

**4. Extension Email Addresses**

Add email addresses to each extension:

```yaml
extensions:
  - number: "1001"
    name: "John Doe"
    password: "password1001"
    email: "john.doe@company.com"  # Email for voicemail notifications
  
  - number: "1002"
    name: "Jane Smith"
    password: "password1002"
    email: "jane.smith@company.com"
```

### How It Works

**No-Answer Routing:**

1. User A calls Extension 1001
2. Extension 1001 rings for 30 seconds (configurable)
3. If not answered, call is automatically routed to voicemail
4. Caller hears greeting: "Please leave a message after the tone"
5. A beep tone signals the start of recording
6. Caller leaves their message
7. Message is saved when caller hangs up
8. Email notification sent immediately to extension owner

**Email Notification Content:**

**Subject:** `New Voicemail from 1002 - 2025-12-29 14:30:15`

**Body:**
```
Hello,

You have received a new voicemail message.

Message Details:
  Extension: 1001
  From: 1002
  Received: 2025-12-29 14:30:15
  Duration: 0:45
  
[If transcription enabled:]
Transcription:
"Hi, this is John from the sales department. I wanted to follow up on..."

To listen to this message, please dial *1001

Best regards,
Company Voicemail
```

**Attachment:** Audio file (WAV format) of the voicemail message

**Daily Reminders:**

If reminders are enabled, users receive a daily email at the configured time:

**Subject:** `Voicemail Reminder: 3 Unread Messages`

**Body:**
```
Hello,

You have 3 unread voicemail messages in your mailbox (Extension 1001):

1. From: 1002, Received: 2025-12-29 14:30:15
2. From: 1003, Received: 2025-12-29 16:45:22
3. From: 1004, Received: 2025-12-30 09:12:05

Please check your voicemail by dialing *1001

Best regards,
Company Voicemail
```

---

## Transcription Service

### Overview

The voicemail transcription feature automatically converts voicemail messages to text using speech-to-text APIs. Transcriptions are stored in the database and can be included in email notifications.

**Key Features:**
- **Automatic Transcription**: Voicemails transcribed when saved
- **Multiple Providers**: OpenAI Whisper, Google Cloud, or FREE offline Vosk
- **Database Storage**: Transcriptions stored with confidence scores
- **Email Integration**: Transcriptions included in email notifications
- **Language Support**: Configurable language for transcription
- **High Accuracy**: Modern speech-to-text engines provide excellent accuracy

### Supported Providers

**OpenAI Whisper API:**
- **Model**: `whisper-1`
- **Accuracy**: Excellent for various accents and background noise
- **Cost**: Pay-per-use (check OpenAI pricing)
- **Setup**: Requires OpenAI API key
- **Library**: `openai` Python package

**Google Cloud Speech-to-Text:**
- **Model**: Optimized for phone call audio
- **Accuracy**: Very high with confidence scores
- **Cost**: Pay-per-use (check Google Cloud pricing)
- **Setup**: Requires Google Cloud credentials
- **Library**: `google-cloud-speech` Python package

**Vosk (FREE, Offline) - RECOMMENDED:**
- **Model**: Open-source speech recognition
- **Accuracy**: Good for most voicemail transcription needs
- **Cost**: FREE - No API costs
- **Setup**: Download language model
- **Library**: `vosk` Python package
- **Privacy**: Audio never leaves your server (fully offline)

### Installation

**Choose one provider:**

**For OpenAI Whisper:**
```bash
pip install openai
```

**For Google Cloud Speech-to-Text:**
```bash
pip install google-cloud-speech
```

**For Vosk (FREE, Offline):**
```bash
pip install vosk
```

### Configuration

#### OpenAI Setup

1. Sign up at [OpenAI](https://openai.com/)
2. Generate an API key from your account dashboard
3. Add the API key to your environment:
```bash
export TRANSCRIPTION_API_KEY="your-openai-api-key"
```

4. Edit `config.yml`:
```yaml
features:
  voicemail_transcription:
    enabled: true
    provider: openai
    api_key: ${TRANSCRIPTION_API_KEY}
    language: en-US
    include_in_email: true
```

#### Google Cloud Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Speech-to-Text API
3. Create a service account and download the JSON key file
4. Set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

5. Edit `config.yml`:
```yaml
features:
  voicemail_transcription:
    enabled: true
    provider: google
    language: en-US
    include_in_email: true
```

#### Vosk Setup (FREE, Offline) - RECOMMENDED

1. Download a language model from https://alphacephei.com/vosk/models

**Small Model (40 MB) - Fast, Good for Most Uses:**
```bash
mkdir -p models
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
rm vosk-model-small-en-us-0.15.zip
cd ..
```

**Large Model (1.8 GB) - More Accurate:**
```bash
mkdir -p models
cd models
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
unzip vosk-model-en-us-0.22.zip
rm vosk-model-en-us-0.22.zip
cd ..
```

**Other Languages**: Visit https://alphacephei.com/vosk/models for Spanish, French, German, Russian, Chinese, and more!

2. Edit `config.yml`:
```yaml
features:
  voicemail_transcription:
    enabled: true
    provider: vosk
    vosk_model_path: models/vosk-model-small-en-us-0.15
    include_in_email: true
```

### Testing Transcription

**Test with a sample voicemail:**

```bash
python scripts/test_transcription.py voicemail/1001/sample_message.wav
```

**Check transcription in database:**

```bash
python scripts/list_voicemails.py 1001
```

---

## Custom Greetings

### Overview

Users can record, review, and manage their custom voicemail greetings directly through the voicemail IVR system. This provides a complete self-service experience without administrator intervention.

### Features

- **Record**: Record a personal greeting via phone
- **Review**: Listen to the recorded greeting before saving
- **Re-record**: Record again if not satisfied
- **Delete**: Remove custom greeting and use system default
- **Save**: Permanently save the custom greeting

### How to Record a Custom Greeting

**Step-by-Step Instructions:**

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

### IVR Menu Structure

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

### Recording Specifications

- **Maximum Duration**: 2 minutes (120 seconds)
- **Audio Format**: G.711 μ-law (PCMU) at 8kHz
- **Storage Location**: `voicemail/{extension}/greeting.wav`
- **Automatic Timeout**: Recording stops after 2 minutes

### Default vs Custom Greetings

**System Default Greeting:**
When no custom greeting exists:
- "You have reached extension {number}. Please leave a message after the tone."

**Custom Greeting:**
When a custom greeting is recorded:
- System plays user's recorded audio
- More personal and professional
- Can include specific instructions or information

### API Integration

**Check for Custom Greeting:**

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

**Programmatic Greeting Management:**

```python
# Save greeting via code
audio_data = b'...'  # WAV audio data
success = mailbox.save_greeting(audio_data)

# Delete greeting via code
mailbox.delete_greeting()

# Get greeting path
path = mailbox.get_greeting_path()
```

---

## User Guide

### Accessing Your Voicemail

To check your voicemail messages, dial `*` followed by your extension number (e.g., `*1001`).

### Interactive Voicemail Menu

**1. Welcome & Authentication**
- System announces the number of new messages
- Enter your 4-digit PIN followed by `#`
- After 3 failed attempts, the system will disconnect

**2. Main Menu**
- Press `1` - Listen to your messages
- Press `2` - Access options menu (record greeting, change settings)
- Press `*` - Exit voicemail system

**3. Message Playback**
While listening to a message:
- Press `1` - Repeat current message
- Press `2` - Save message (mark as read)
- Press `3` - Delete message
- Press `#` - Skip to next message
- Press `*` - Return to main menu

**4. Options Menu**
- Press `1` - Record custom greeting
- Press `2` - Change PIN
- Press `*` - Return to main menu

### Managing Messages via Admin Panel

Administrators can manage voicemail boxes through the web admin panel:

1. Login to admin panel: `https://your-pbx/admin/`
2. Navigate to: **Voicemail** tab
3. Select an extension from the dropdown

**Features:**
- View all voicemail messages
- Listen to messages
- Delete messages
- Export voicemail box (all messages as ZIP)
- View message details (caller, date, duration)

---

## Troubleshooting

### Database Issues

**Problem**: Voicemail messages not saving to database

**Solutions:**
1. Verify database connection:
   ```bash
   python scripts/verify_database.py
   ```

2. Check database credentials in config.yml

3. Ensure database tables are created:
   ```bash
   python scripts/init_database.py
   ```

4. Check logs for errors:
   ```bash
   tail -f logs/pbx.log | grep -i voicemail
   ```

### Email Notification Issues

**Problem**: Email notifications not being sent

**Solutions:**
1. Verify SMTP configuration in config.yml

2. Test SMTP connection:
   ```bash
   python scripts/test_email.py your-email@example.com
   ```

3. Check extension has email address configured

4. Verify `email_notifications: true` in config.yml

5. Check SMTP server logs and firewall rules

### Transcription Issues

**Problem**: Voicemails not being transcribed

**Solutions:**

**For OpenAI:**
1. Verify API key is set correctly
2. Check internet connection
3. Verify API usage limits not exceeded

**For Google Cloud:**
1. Verify credentials file exists and is readable
2. Check API is enabled in Google Cloud Console
3. Verify service account has proper permissions

**For Vosk:**
1. Verify model path is correct in config.yml
2. Check model directory exists and contains required files
3. Ensure sufficient disk space for model
4. Verify vosk library is installed: `pip show vosk`

**General:**
```bash
# Test transcription
python scripts/test_transcription.py voicemail/1001/test.wav

# Check logs
tail -f logs/pbx.log | grep -i transcription
```

### Custom Greeting Issues

**Problem**: Greeting not saving

**Solutions:**
1. Ensure you press `#` to finish recording
2. Make sure you're in the review menu (you should hear review options)
3. Verify storage directory exists and is writable:
   ```bash
   ls -la voicemail/1001/
   chmod 755 voicemail/1001/
   ```
4. Check logs for errors:
   ```bash
   tail -f logs/pbx.log | grep -i greeting
   ```

**Problem**: Can't hear recording during review

**Solutions:**
1. Verify recording was actually saved
2. Check audio file format is correct (8kHz, PCMU)
3. Test file with media player:
   ```bash
   ffplay voicemail/1001/greeting.wav
   ```

### Audio Quality Issues

**Problem**: Poor audio quality in voicemail recordings

**Solutions:**
1. Check codec configuration (should be G.711)
2. Verify network quality (QoS settings)
3. Ensure sufficient bandwidth for RTP
4. Check for packet loss in network
5. Review RTP port range configuration

### Storage Issues

**Problem**: Running out of disk space

**Solutions:**
1. Implement voicemail retention policy
2. Archive old voicemails
3. Compress audio files (if not already compressed)
4. Monitor disk usage:
   ```bash
   du -sh voicemail/
   df -h
   ```

5. Set up automatic cleanup:
   ```bash
   # Delete voicemails older than 90 days
   find voicemail -name "*.wav" -mtime +90 -delete
   ```

---

## Additional Resources

- **[ADMIN_PANEL_GUIDE.md](ADMIN_PANEL_GUIDE.md)** - Admin panel voicemail management
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - General troubleshooting
- **[PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)** - Production deployment
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation

---

**Last Updated**: December 29, 2025  
**Status**: Production Ready
