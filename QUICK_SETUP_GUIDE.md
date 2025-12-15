# Quick Setup Guide - Open Source Integrations

This guide shows you how to quickly enable open-source integrations using the Admin Panel's one-click setup feature.

## Overview

The PBX system includes three powerful, **free** integrations:

1. **Jitsi Meet** - Video conferencing (Zoom alternative)
2. **Matrix** - Team messaging (Slack/Teams alternative)
3. **EspoCRM** - Customer relationship management (Salesforce alternative)

All integrations can be enabled with **just one click** using default settings!

## Quick Setup Steps

### 1. Access the Admin Portal

1. Open your browser and navigate to: `https://your-pbx-server:8080/admin/`
2. Log in with your admin credentials

### 2. Navigate to Integrations

1. Click **"Integrations"** in the left sidebar
2. Click the **"Open Source (Free)"** tab

You'll see cards for each integration with checkboxes and buttons.

### 3. Enable an Integration (One-Click Method)

**Option A: Use the Checkbox**
- Simply **check the box** next to any integration name
- The integration is automatically enabled with default settings!
- A green status badge appears when enabled

**Option B: Use the Quick Setup Button**
- Click the **"Quick Setup"** button on any integration card
- Confirms the integration is enabled with default settings

### 4. Default Settings Applied

When you use quick setup, these defaults are configured:

**Jitsi Meet:**
- ✅ Enabled: true
- Server: https://localhost (local self-hosted server with HTTPS)
- Auto-create rooms: enabled
- **Note:** Requires local Jitsi installation with SSL - see [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md) and [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)

**Matrix:**
- ✅ Enabled: true
- Homeserver: https://localhost:8008 (local Synapse server with HTTPS)
- **Requires:** Local Matrix Synapse installation with SSL and bot username/password to be configured
- **Note:** See [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md) for setup

**EspoCRM:**
- ✅ Enabled: true
- API URL: https://localhost/api/v1 (local CRM installation with HTTPS)
- **Requires:** Local EspoCRM installation with SSL and API key to be configured
- **Security:** HTTPS recommended to protect sensitive customer data
- **Note:** See [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md) for setup

## Additional Configuration (If Needed)

### For Jitsi
⚠️ **Requires local installation with HTTPS!** The quick setup now points to `https://localhost` for a self-hosted Jitsi server with SSL encryption.

**Installation Steps:**
1. See [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md#jitsi-self-hosted-integration-complete-guide) for complete installation guide
2. Install Jitsi Meet on your local server or the same machine as the PBX
3. Configure SSL certificates (see [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md))
4. Quick setup will automatically configure the PBX to use your local server

**Alternative:** If you want to use HTTP for development/testing:
1. Click "Configure" button on the Jitsi card
2. Change server URL to `http://localhost`
3. Click "Save Configuration"

### For Matrix

1. **Create a bot account:**
   - Install Matrix Synapse locally (see [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md))
   - OR use a public server like https://app.element.io
   - Create a new account (e.g., @pbxbot:matrix.org or @pbxbot:localhost)
   - Note the username and password

2. **Set the bot password:**
   - Edit your `.env` file in the PBX root directory
   - Add: `MATRIX_BOT_PASSWORD=your-bot-password`

3. **Configure bot username and rooms:**
   - Click **"Configure"** button on the Matrix card
   - Enter bot username (e.g., @pbxbot:matrix.org)
   - Enter notification room ID (optional)
   - Click **"Save Configuration"**

### For EspoCRM

1. **Install EspoCRM locally** (required)
   - See [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md#espocrm-installation-and-setup) for installation steps
   - Quick setup points to `http://localhost/api/v1` by default

2. **Generate API key:**
   - Log in to EspoCRM
   - Go to Administration → API Users
   - Create API User and copy the API key

3. **Configure in admin panel:**
   - Click **"Configure"** button on the EspoCRM card
   - Enter API URL (e.g., https://crm.yourcompany.com/api/v1)
   - Enter API key
   - Click **"Save Configuration"**

4. **Set API key in .env:**
   - Edit your `.env` file
   - Add: `ESPOCRM_API_KEY=your-api-key`

## Disable an Integration

To disable an integration:

1. Go to Admin Portal → Integrations → Open Source (Free)
2. **Uncheck the box** next to the integration name
3. The integration is disabled immediately
4. Status badge disappears

## Advanced Configuration

For more control over settings:

1. Click the **"Configure"** button instead of "Quick Setup"
2. You'll see the full configuration form with all options
3. Customize server URLs, features, and behaviors
4. Click **"Test Connection"** to verify settings
5. Click **"Save Configuration"** to apply changes

## Status Badges

Look for colored status badges next to integration names:

- 🟢 **Green "● Enabled"** - Integration is active
- (No badge) - Integration is disabled

## Troubleshooting

### Jitsi shows as enabled but not working
- Check if the server URL is correct
- Test by clicking "Configure" → "Test Connection"

### Matrix shows as enabled but can't send messages
- Verify bot password is set in `.env` file
- Check bot username is correct format (@username:server.com)
- Ensure bot account exists and password is correct

### EspoCRM shows as enabled but screen pop doesn't work
- Verify API URL is correct and accessible
- Check API key is valid and set in `.env`
- Test connection using "Configure" → "Test Connection"

### Quick Setup button doesn't work
- Check browser console for errors (F12)
- Ensure you have admin permissions
- Try refreshing the page and logging in again

## Additional Resources

- **[OPENSOURCE_INTEGRATIONS_SUMMARY.md](OPENSOURCE_INTEGRATIONS_SUMMARY.md)** - Complete feature overview
- **[INTEGRATION_QUICK_FIX.md](INTEGRATION_QUICK_FIX.md)** - Fast fixes for common problems
- **[INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md)** - Detailed setup guides
- **[OPEN_SOURCE_INTEGRATIONS.md](OPEN_SOURCE_INTEGRATIONS.md)** - Full integration reference

## Benefits of Quick Setup

✅ **One-Click Enable** - No manual config file editing  
✅ **Local Installation** - Uses self-hosted services for privacy and control  
✅ **Instant Configuration** - Pre-configured with localhost URLs  
✅ **Easy to Customize** - Click "Configure" for advanced options  
✅ **Visual Feedback** - Status badges show what's enabled  
✅ **Reversible** - Uncheck to disable instantly  

## Prerequisites

Before using quick setup, you need to have the following services installed locally with SSL/HTTPS:

### Required Local Installations:

1. **Jitsi Meet** (for video conferencing)
   - Default URL: `https://localhost`
   - Requires SSL certificates
   - Installation guide: [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md#jitsi-self-hosted-integration-complete-guide)
   - SSL setup: [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)

2. **Matrix Synapse** (for team messaging)
   - Default URL: `https://localhost:8008`
   - Requires SSL for secure communications
   - Installation guide: [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md#matrix-synapse-proper-startup)
   - SSL setup: [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)

3. **EspoCRM** (for CRM functionality)
   - Default URL: `https://localhost/api/v1`
   - **Security Critical:** HTTPS required to protect customer data
   - Installation guide: [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md#espocrm-installation-and-setup)
   - SSL setup: [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)

**Security Note:** All integrations default to HTTPS to protect sensitive data in transit. For development/testing only, you can manually change URLs to HTTP after quick setup.

**Note:** If you want to use public/cloud servers instead of local installations, you can click "Configure" on each integration and change the server URLs after quick setup.  

## Cost Savings

By using these free open-source integrations with local installations instead of proprietary cloud alternatives:

- **Video Conferencing**: $0 vs $150-300/user/year (Zoom)
- **Team Messaging**: $0 vs $96-240/user/year (Slack/Teams)
- **CRM**: $0 vs $1,200+/user/year (Salesforce)

**Total Savings: $3,726+ per user per year!**

**Additional Benefits of Local Hosting:**
- ✅ Complete data privacy and control
- ✅ No dependency on external services
- ✅ No recurring subscription fees
- ✅ Customizable to your specific needs
- ✅ Secure HTTPS encryption for all communications

---

**Last Updated**: December 15, 2025  
**Feature Status**: ✅ Production Ready
