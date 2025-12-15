# Integration Interaction UI - User Guide

## Overview

After running `setup_integrations.py`, you can now **interact with** the configured integrations directly from the PBX admin interface. This guide shows you where to find these interactive features.

## Accessing the Integration Features

### 1. Open Source Integrations Overview Tab

Navigate to: **Admin Panel → Integrations → Open Source (Free)**

This tab shows:
- ✅ Status of each integration (enabled/disabled)
- 🚀 Quick Setup buttons to enable integrations with default settings
- ⚡ Quick Action buttons to jump directly to each integration's interaction page

### 2. Jitsi Meet Video Conferencing

Navigate to: **Admin Panel → Integrations → Jitsi (Video)**

#### What You Can Do:
- **Create Instant Meetings**: Generate a meeting URL immediately
  - Optionally specify a custom room name
  - Get a shareable meeting link
  - Copy URL to clipboard or open directly

- **Schedule Meetings**: Plan meetings for the future
  - Set meeting subject
  - Specify duration (15-480 minutes)
  - Get meeting URL to share with participants

#### Example Use Case:
1. Click "🚀 Create Instant Meeting"
2. Optional: Enter room name like "sales-team"
3. Click "Create Instant Meeting" button
4. Copy the meeting URL and share with participants
5. Click "🚀 Join Now" to open the meeting

### 3. Matrix Team Messaging

Navigate to: **Admin Panel → Integrations → Matrix (Chat)**

#### What You Can Do:
- **Send Messages**: Send text messages to Matrix rooms
  - Choose notification room, voicemail room, or custom room
  - Enter your message
  - Send instantly to your team

- **Send Test Notifications**: Verify Matrix integration is working
  - Sends a timestamped test message
  - Confirms bot connectivity

- **Create Rooms**: Set up new Matrix rooms
  - Specify room name
  - Add optional topic/description
  - Get room ID for configuration

#### Example Use Case:
1. Select "Notification Room" from dropdown
2. Enter message: "Testing PBX integration! 👋"
3. Click "📤 Send Message"
4. Check your Matrix client (Element, etc.) to see the message

### 4. EspoCRM Contact Management

Navigate to: **Admin Panel → Integrations → EspoCRM (CRM)**

#### What You Can Do:
- **Search Contacts**: Find existing contacts
  - Search by phone number, email, or name
  - View full contact details
  - See CRM ID for reference

- **Create Contacts**: Add new contacts to CRM
  - Enter first name, last name
  - Add phone and/or email
  - Optional: Company and title
  - Immediately synced to EspoCRM

#### Example Use Case:
1. Select "Phone Number" search type
2. Enter: "+1-555-0100"
3. Click "🔍 Search Contact"
4. View contact details if found, or create new contact

## Quick Start Workflow

### First Time Setup:
1. **Run setup script** (you already did this):
   ```bash
   python3 scripts/setup_integrations.py --interactive
   ```

2. **Access Admin Panel**: http://your-pbx-server:8080/admin

3. **Navigate to Integrations**:
   - Click "Integrations" in the sidebar
   - Click "Open Source (Free)"

4. **Enable Integration**:
   - Check the box next to the integration you want
   - It will be enabled with default settings

5. **Configure (Optional)**:
   - Click "Configure" button
   - Update server URLs, API keys, etc.
   - Click "Save Configuration"

6. **Start Using**:
   - Use the interactive sections on each integration's tab
   - Create meetings, send messages, search contacts

## Configuration Tips

### Jitsi:
- **Default**: Uses public meet.jit.si server (free, instant)
- **Production**: Self-host Jitsi for privacy and control
- **JWT**: Optional authentication for secure rooms

### Matrix:
- **Default**: Uses public matrix.org homeserver
- **Bot Account**: Create a dedicated bot user for PBX
- **Room IDs**: Get room IDs from Element → Room Settings → Advanced

### EspoCRM:
- **API URL**: Point to your EspoCRM installation
- **API Key**: Generate in EspoCRM → Administration → API Users
- **Features**: Auto-log calls, screen pop, contact sync

## Troubleshooting

### "Integration not enabled" error:
- Go to configuration tab
- Check the "Enable" checkbox
- Save configuration
- Try again

### "Failed to create/send" error:
- Verify server URLs are correct
- Check API keys/passwords in .env file
- Test connection using "Test Connection" button
- Review logs for detailed error messages

### Jitsi meetings not opening:
- Verify server URL in configuration
- Check if HTTPS is required for your server
- Try using public meet.jit.si first

### Matrix messages not sending:
- Verify bot credentials are correct
- Check room IDs start with "!" character
- Ensure bot is joined to the room
- Check MATRIX_BOT_PASSWORD in .env file

### EspoCRM contacts not found:
- Verify API URL ends with /api/v1
- Check ESPOCRM_API_KEY in .env file
- Test API connectivity directly
- Ensure contact exists in CRM

## Benefits of This Integration

### Before:
❌ Could only configure integrations
❌ Had to use separate tools to interact
❌ No way to test from admin panel
❌ Manual workflow for everything

### After:
✅ Configure AND interact from one place
✅ Test integrations instantly
✅ Quick actions for common tasks
✅ Streamlined workflow
✅ All free and open source

## Next Steps

1. **Test Each Integration**:
   - Create a test meeting in Jitsi
   - Send a test message in Matrix
   - Search for a contact in EspoCRM

2. **Customize Configuration**:
   - Update server URLs if using self-hosted
   - Set API keys in .env file
   - Configure room IDs for Matrix

3. **Use in Production**:
   - Create meetings for team calls
   - Send notifications to Matrix
   - Log customer calls in CRM

## Support

For detailed documentation, see:
- `OPEN_SOURCE_INTEGRATIONS.md` - Complete integration guide
- `INTEGRATION_TROUBLESHOOTING_GUIDE.md` - Troubleshooting tips
- API endpoints documentation in code

For issues or questions, check the repository issues or create a new one.

---

**Total Cost**: $0/year (vs $3,726+/user for proprietary solutions)

**All integrations are FREE and OPEN SOURCE!** 🎉
