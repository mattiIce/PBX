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
- Server: https://meet.jit.si (free public server)
- Auto-create rooms: enabled
- **Ready to use immediately!**

**Matrix:**
- ✅ Enabled: true
- Homeserver: https://matrix.org (free public server)
- **Requires:** Bot username and password to be configured

**EspoCRM:**
- ✅ Enabled: true
- **Requires:** Your CRM URL and API key to be configured

## Additional Configuration (If Needed)

### For Jitsi
✅ **No additional setup needed!** Works immediately with the free public server.

For self-hosted Jitsi, click "Configure" and set your custom server URL.

### For Matrix

1. **Create a bot account:**
   - Go to https://app.element.io
   - Create a new account (e.g., @pbxbot:matrix.org)
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

1. **Install EspoCRM** (if not already installed)
   - See [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md#espocrm-installation-and-setup) for installation steps

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
✅ **Safe Defaults** - Uses free public servers  
✅ **Instant Activation** - Works immediately (Jitsi)  
✅ **Easy to Customize** - Click "Configure" for advanced options  
✅ **Visual Feedback** - Status badges show what's enabled  
✅ **Reversible** - Uncheck to disable instantly  

## Cost Savings

By using these free open-source integrations instead of proprietary alternatives:

- **Video Conferencing**: $0 vs $150-300/user/year (Zoom)
- **Team Messaging**: $0 vs $96-240/user/year (Slack/Teams)
- **CRM**: $0 vs $1,200+/user/year (Salesforce)

**Total Savings: $3,726+ per user per year!**

---

**Last Updated**: December 15, 2025  
**Feature Status**: ✅ Production Ready
