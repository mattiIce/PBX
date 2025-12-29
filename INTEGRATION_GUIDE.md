# Integration Guide

**Last Updated**: December 15, 2025  
**Purpose**: Complete guide for setting up, using, and troubleshooting Jitsi, Matrix, and EspoCRM integrations

## Table of Contents
- [Quick Problem Resolution](#-quick-problem-resolution)
- [Using Integration Features](#using-integration-features)
- [Port Configuration](#port-configuration)
- [Jitsi Self-Hosted Integration](#-jitsi-self-hosted-integration-complete-guide)
- [Matrix Team Messaging Setup](#-matrix-team-messaging-setup)
- [EspoCRM Setup](#-espocrm-installation-and-setup)
- [Testing Integrations](#-testing-your-integrations)
- [Getting Help](#-getting-help)

---

---

## Using Integration Features

After running `setup_integrations.py`, you can interact with configured integrations directly from the PBX admin interface.

### Accessing Integration Features

**Navigate to**: Admin Panel → Integrations → Open Source (Free)

This tab shows:
- ✅ Status of each integration (enabled/disabled)
- 🚀 Quick Setup buttons to enable integrations with default settings
- ⚡ Quick Action buttons to jump directly to each integration's interaction page

### Jitsi Meet Video Conferencing

**Navigate to**: Admin Panel → Integrations → Jitsi (Video)

**What You Can Do:**
- **Create Instant Meetings**: Generate a meeting URL immediately
  - Optionally specify a custom room name
  - Get a shareable meeting link
  - Copy URL to clipboard or open directly

- **Schedule Meetings**: Plan meetings for the future
  - Set meeting subject
  - Specify duration (15-480 minutes)
  - Get meeting URL to share with participants

**Example Use Case:**
1. Click "🚀 Create Instant Meeting"
2. Optional: Enter room name like "sales-team"
3. Click "Create Instant Meeting" button
4. Copy the meeting URL and share with participants
5. Click "🚀 Join Now" to open the meeting

### Matrix Team Messaging

**Navigate to**: Admin Panel → Integrations → Matrix (Chat)

**What You Can Do:**
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

**Example Use Case:**
1. Select "Notification Room" from dropdown
2. Enter message: "Testing PBX integration! 👋"
3. Click "📤 Send Message"
4. Check your Matrix client (Element, etc.) to see the message

### EspoCRM Contact Management

**Navigate to**: Admin Panel → Integrations → EspoCRM (CRM)

**What You Can Do:**
- **Search Contacts**: Find existing contacts
  - Search by phone number, email, or name
  - View full contact details
  - See CRM ID for reference

- **Create Contacts**: Add new contacts to CRM
  - Enter first name, last name
  - Add phone and/or email
  - Optional: Company and title
  - Immediately synced to EspoCRM

---

## Port Configuration

### Default Port Allocation

All integrations use **dedicated ports** to avoid conflicts:

| Integration | Default Configuration | Port Used | Purpose |
|-------------|----------------------|-----------|---------|
| **Jitsi Meet** | `https://localhost:8443` | 8443 | Video conferencing |
| **Matrix** | `https://localhost:8008` | 8008 | Team messaging |
| **EspoCRM** | `https://localhost:8001/api/v1` | 8001 | CRM API |
| **PBX API** | `http://0.0.0.0:8080` | 8080 | PBX REST API |
| **PBX SIP** | `udp://0.0.0.0:5060` | 5060 | SIP signaling |
| **PBX RTP** | `udp://0.0.0.0:10000-20000` | 10000-20000 | Media streams |

### Port Configuration Strategy

**Jitsi Meet:**
- **Default**: `https://localhost:8443` (dedicated HTTPS port)
- **Network**: `https://jitsi.yourcompany.com:8443`
- **Development**: `http://localhost:8888` (HTTP for testing)

**Matrix:**
- **Default**: `https://localhost:8008` (Matrix Synapse standard port)
- **Alternative**: `https://localhost:8448` (Synapse federation port)
- **Network**: `https://matrix.yourcompany.com:8008`

**EspoCRM:**
- **Default**: `https://localhost:8001/api/v1` (dedicated port)
- **Alternative**: `http://localhost:8001/api/v1` (HTTP for development)
- **Network**: `https://crm.yourcompany.com/api/v1` (dedicated server)

### Updating Port Configuration

**Option 1: Using Admin Portal**
1. Navigate to: Admin Panel → Integrations
2. Select the integration tab
3. Update the server URL field
4. Click "Test Connection" to verify
5. Click "Save Configuration"

**Option 2: Edit config.yml**

```yaml
integrations:
  # Jitsi Meet - Video Conferencing
  jitsi:
    enabled: true
    server_url: https://localhost:8443  # Update as needed
    auto_create_rooms: true
    
  # Matrix - Team Messaging
  matrix:
    enabled: true
    homeserver_url: https://localhost:8008  # Update as needed
    bot_access_token: "your_token_here"
    
  # EspoCRM - Contact Management
  espocrm:
    enabled: true
    api_url: https://localhost:8001/api/v1  # Update as needed
    api_key: "your_api_key_here"
```

After editing config.yml, restart the PBX:
```bash
sudo systemctl restart pbx
```

---

### Common Issues:

1. **Jitsi**: "I set up self-hosted Jitsi but don't know how to complete the integration"
   - [Solution: Jump to Jitsi Self-Hosted Integration](#jitsi-self-hosted-integration-complete-guide)

2. **Matrix**: "pip3 install worked but python3 command doesn't work"
   - [Solution: Jump to Matrix Synapse Startup](#matrix-synapse-proper-startup)

3. **EspoCRM**: "Getting 404 Not Found errors"
   - [Solution: Jump to EspoCRM Setup](#espocrm-installation-and-setup)

---

## 📹 Jitsi Self-Hosted Integration (Complete Guide)

### Problem
You ran the Jitsi installation commands and it installed successfully, but you don't know how to connect it to the PBX system.

### Solution: Step-by-Step

#### Step 1: Verify Jitsi is Running

```bash
# Check if Jitsi services are running
sudo systemctl status jitsi-videobridge2
sudo systemctl status jicofo
sudo systemctl status prosody
```

All three services should show "active (running)". If not:

```bash
# Start the services
sudo systemctl start jitsi-videobridge2
sudo systemctl start jicofo
sudo systemctl start prosody
```

#### Step 2: Test Your Jitsi Server

Open a web browser and navigate to your Jitsi server URL:
```
https://your-server-domain.com
# OR
https://your-server-ip-address
```

You should see the Jitsi Meet interface. Try creating a test meeting to ensure it works.

#### Step 3: Configure PBX to Use Your Jitsi Server

**Option A: Using the Admin Web Portal (Recommended)**

1. Navigate to the PBX admin portal:
   ```
   https://your-pbx-server:8080/admin/
   ```

2. Log in with your admin credentials

3. Click **"Integrations"** in the left sidebar

4. Click the **"Jitsi (Video)"** tab

5. Fill in the form:
   - ✅ Check "Enable Jitsi Integration"
   - **Server URL**: Enter your Jitsi server URL (e.g., `https://jitsi.yourcompany.com`)
   - ✅ Check "Auto Create Rooms" (optional but recommended)
   - Leave App ID and App Secret empty unless you configured JWT authentication

6. Click **"Test Connection"** to verify the configuration

7. Click **"Save Configuration"**

**Option B: Editing config.yml Directly**

1. Edit the PBX configuration file:
   ```bash
   nano /home/runner/work/PBX/PBX/config.yml
   ```

2. Find the `integrations.jitsi` section (around line 431):
   ```yaml
   integrations:
     jitsi:
       enabled: true  # Change from false to true
       server_url: https://jitsi.yourcompany.com  # Your Jitsi server URL
       auto_create_rooms: true
       app_id: ''  # Leave empty unless using JWT
       app_secret: ''  # Leave empty unless using JWT
   ```

3. Replace `https://jitsi.yourcompany.com` with:
   - Your domain if you set one up: `https://meet.example.com`
   - OR your server IP: `https://192.168.1.100`

4. Save the file (Ctrl+O, Enter, Ctrl+X in nano)

5. Restart the PBX system:
   ```bash
   sudo systemctl restart pbx
   # OR if not using systemd:
   cd /home/runner/work/PBX/PBX
   python3 main.py
   ```

#### Step 4: Verify Integration

1. Log into the PBX admin portal
2. Navigate to Integrations → Jitsi
3. You should see a success message if the connection works

#### Step 5: Create a Test Meeting

Use the PBX API to create a test meeting:

```bash
curl -X POST http://your-pbx-server:8080/api/integrations/jitsi/instant \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "1001",
    "contact_name": "Test Meeting"
  }'
```

You should receive a response with a meeting URL.

### Advanced: JWT Authentication (Optional)

If you want to secure your Jitsi rooms with JWT authentication:

1. Install JWT token library on Jitsi server:
   ```bash
   sudo apt-get install lua-basexx
   ```

2. Configure Jitsi for JWT (edit `/etc/prosody/conf.avail/your-domain.cfg.lua`):
   ```lua
   VirtualHost "your-domain.com"
       authentication = "token"
       app_id = "pbx_system"
       app_secret = "generate-a-random-secret-here"
   ```

3. Restart Prosody:
   ```bash
   sudo systemctl restart prosody
   ```

4. Update PBX config.yml with the app_id and app_secret

### Troubleshooting Jitsi

**Problem**: Can't connect to Jitsi server
- **Check firewall**: Ensure ports 443 (HTTPS) and 10000 (video) are open
  ```bash
  sudo ufw allow 443/tcp
  sudo ufw allow 10000/udp
  ```

**Problem**: SSL/TLS certificate errors
- **Solution**: Jitsi installer should have generated certificates. If not:
  ```bash
  sudo /usr/share/jitsi-meet/scripts/install-letsencrypt-cert.sh
  ```

**Problem**: "Integration not enabled" error in API
- **Solution**: Make sure `enabled: true` in config.yml and restart PBX

---

## 💬 Matrix Synapse Proper Startup

### Problem
You ran `pip3 install matrix-synapse` successfully, but the `python3 -m synapse.app.homeserver` command doesn't work or gives errors.

### Solution: Correct Installation and Startup

#### Step 1: Verify Installation

```bash
# Check if synapse is installed
python3 -c "import synapse; print('Synapse installed successfully')"
```

If you get an import error, reinstall:
```bash
pip3 install --upgrade matrix-synapse
```

#### Step 2: Create Configuration (One-Time Setup)

The documentation shows a command that generates config but tries to run the server at the same time. This is confusing. Here's the correct way:

**First, just generate the configuration:**

```bash
# Create a directory for Matrix data
mkdir -p ~/matrix-synapse
cd ~/matrix-synapse

# Generate configuration file
python3 -m synapse.app.homeserver \
  --server-name your-domain.com \
  --config-path homeserver.yaml \
  --generate-config \
  --report-stats=no
```

**Important**: 
- Replace `your-domain.com` with your actual domain (or use `localhost` for testing)
- This creates `homeserver.yaml` and STOPS (doesn't start the server)
- Use `--report-stats=no` to opt out of anonymous stats

#### Step 3: Edit Configuration (Optional but Recommended)

```bash
nano homeserver.yaml
```

Key settings to check:
1. **Enable registration** (to create bot account):
   ```yaml
   enable_registration: true
   enable_registration_without_verification: true  # For testing only!
   ```

2. **Database** (default is SQLite, which is fine for testing):
   ```yaml
   database:
     name: sqlite3
     args:
       database: /home/youruser/matrix-synapse/homeserver.db
   ```

3. **Listeners** (should be configured by default):
   ```yaml
   listeners:
     - port: 8008
       type: http
       bind_addresses: ['0.0.0.0']
   ```

#### Step 4: Start the Server (Correct Command)

**Option A: Foreground (for testing)**
```bash
cd ~/matrix-synapse
python3 -m synapse.app.homeserver --config-path homeserver.yaml
```

**Option B: Background (for production)**
```bash
cd ~/matrix-synapse
nohup python3 -m synapse.app.homeserver --config-path homeserver.yaml > synapse.log 2>&1 &
```

**Option C: Using systemd (recommended for production)**

Create a service file:
```bash
sudo nano /etc/systemd/system/matrix-synapse.service
```

Content:
```ini
[Unit]
Description=Matrix Synapse Homeserver
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/matrix-synapse
ExecStart=/usr/bin/python3 -m synapse.app.homeserver --config-path /home/youruser/matrix-synapse/homeserver.yaml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable matrix-synapse
sudo systemctl start matrix-synapse
sudo systemctl status matrix-synapse
```

#### Step 5: Verify Server is Running

```bash
# Check if the server is listening
curl http://localhost:8008/_matrix/client/versions

# Should return something like:
# {"versions":["r0.0.1","r0.1.0", ...]}
```

#### Step 6: Create Bot Account

**Option A: Using Element (Web Client)**
1. Go to https://app.element.io (or your server URL if you set up a web client)
2. Click "Create Account"
3. Select "Advanced" → "Homeserver" → Enter `http://your-server-ip:8008`
4. Create account with username like `pbxbot`
5. Save the credentials

**Option B: Using Command Line (Requires registration_shared_secret)**

1. Add to `homeserver.yaml`:
   ```yaml
   registration_shared_secret: "generate-a-random-secret-here"
   ```

2. Restart synapse

3. Register bot:
   ```bash
   register_new_matrix_user -c homeserver.yaml http://localhost:8008
   # Follow prompts to create @pbxbot:your-domain
   ```

#### Step 7: Create Notification Rooms

1. Open Element (https://app.element.io)
2. Log in with bot account
3. Click "+" to create new room
4. Name it "PBX Notifications"
5. Click room settings → Advanced → Copy the "Internal Room ID" (looks like `!abc123:matrix.org`)

#### Step 8: Configure PBX Integration

**Edit config.yml:**
```yaml
integrations:
  matrix:
    enabled: true
    homeserver_url: http://your-server-ip:8008  # or https://matrix.org for public server
    bot_username: '@pbxbot:your-domain.com'  # Full Matrix ID
    bot_password: ${MATRIX_BOT_PASSWORD}  # Set in .env file
    notification_room: '!abc123:your-domain.com'  # Room ID from step 7
    missed_call_notifications: true
```

**Edit .env file:**
```bash
nano .env
```

Add:
```bash
MATRIX_BOT_PASSWORD=your-bot-password-here
```

#### Step 9: Restart PBX and Test

```bash
# Restart PBX
sudo systemctl restart pbx

# Test the integration via API
curl -X POST http://your-pbx-server:8080/api/integrations/matrix/messages \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": "!abc123:your-domain.com",
    "message": "Test message from PBX"
  }'
```

Check the Element room - you should see the message!

### Troubleshooting Matrix

**Problem**: `ModuleNotFoundError: No module named 'synapse'`
- **Solution**: Install in the correct Python environment:
  ```bash
  # If using venv:
  source venv/bin/activate
  pip3 install matrix-synapse
  
  # Or install globally:
  sudo pip3 install matrix-synapse
  ```

**Problem**: "Port 8008 already in use"
- **Solution**: Change port in homeserver.yaml or kill the existing process:
  ```bash
  sudo lsof -i :8008  # Find what's using the port
  kill <PID>  # Kill the process
  ```

**Problem**: "Can't register new users"
- **Solution**: Enable registration in homeserver.yaml (see Step 3)

**Problem**: Database errors
- **Solution**: Make sure the database path is writable:
  ```bash
  mkdir -p ~/matrix-synapse
  chmod 755 ~/matrix-synapse
  ```

---

## 👥 EspoCRM Installation and Setup

### Problem
You're trying to access EspoCRM but getting "404 Not Found" errors. This means EspoCRM is not installed or not configured correctly.

### Solution: Complete Installation

#### Prerequisites

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y apache2 mysql-server php php-mysql php-curl \
  php-gd php-mbstring php-xml php-zip php-intl unzip wget
```

#### Step 1: Download EspoCRM

```bash
# Create directory
sudo mkdir -p /var/www/espocrm
cd /tmp

# Download latest version (replace X.X.X with actual version)
wget https://www.espocrm.com/downloads/EspoCRM-8.1.3.zip

# Extract
sudo unzip EspoCRM-8.1.3.zip -d /var/www/espocrm

# Set permissions
sudo chown -R www-data:www-data /var/www/espocrm
sudo chmod -R 755 /var/www/espocrm
```

#### Step 2: Configure MySQL Database

```bash
# Login to MySQL
sudo mysql -u root -p

# Create database and user
CREATE DATABASE espocrm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'espocrm_user'@'localhost' IDENTIFIED BY 'strong_password_here';
GRANT ALL PRIVILEGES ON espocrm.* TO 'espocrm_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Step 3: Configure Apache

Create a virtual host configuration:

```bash
sudo nano /etc/apache2/sites-available/espocrm.conf
```

Content:
```apache
<VirtualHost *:80>
    ServerName crm.yourcompany.com
    DocumentRoot /var/www/espocrm

    <Directory /var/www/espocrm>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/espocrm_error.log
    CustomLog ${APACHE_LOG_DIR}/espocrm_access.log combined
</VirtualHost>
```

Enable the site and required modules:
```bash
sudo a2enmod rewrite
sudo a2ensite espocrm
sudo systemctl restart apache2
```

#### Step 4: Update /etc/hosts (if not using DNS)

If you're testing locally without a domain:
```bash
sudo nano /etc/hosts
```

Add:
```
127.0.0.1    crm.yourcompany.com
```

#### Step 5: Run Web Installation Wizard

1. Open browser and navigate to:
   ```
   http://crm.yourcompany.com
   # OR
   http://your-server-ip
   ```

2. You should see the EspoCRM installation wizard

3. Click "Install EspoCRM"

4. Accept the license agreement

5. Check system requirements (all should be green)

6. Database Configuration:
   - **Database Name**: `espocrm`
   - **User Name**: `espocrm_user`
   - **Password**: `strong_password_here` (from Step 2)
   - **Host**: `localhost`

7. Admin User Configuration:
   - **Username**: `admin`
   - **Password**: Choose a strong password
   - **Email**: your-email@example.com

8. Click "Install"

9. Wait for installation to complete

10. You should now see the EspoCRM login page

#### Step 6: Create API User and Get API Key

1. Log in to EspoCRM with admin credentials

2. Go to **Administration** (top right menu)

3. Scroll down and click **API Users** (under "Users" section)

4. Click **Create API User**

5. Fill in:
   - **Username**: `pbx_api_user`
   - **API Key**: Click "Generate" or enter a strong random string
   - **Status**: Active
   - **Is Admin**: No (unless you need full access)

6. Click **Save**

7. Copy the API Key - you'll need this for the PBX configuration

#### Step 7: Configure PBX Integration

**Option A: Using Admin Web Portal**

1. Go to PBX admin: `http://your-pbx-server:8080/admin/`

2. Click **Integrations** → **EspoCRM (CRM)**

3. Fill in:
   - ✅ Enable EspoCRM Integration
   - **API URL**: `http://crm.yourcompany.com/api/v1`
   - **API Key**: Paste the API key from Step 6
   - ✅ Auto Create Contacts
   - ✅ Auto Log Calls
   - ✅ Screen Pop

4. Click **Test Connection**

5. Click **Save Configuration**

**Option B: Edit config.yml**

```bash
nano /home/runner/work/PBX/PBX/config.yml
```

Find the EspoCRM section:
```yaml
integrations:
  espocrm:
    enabled: true  # Change from false to true
    api_url: 'http://crm.yourcompany.com/api/v1'
    api_key: ${ESPOCRM_API_KEY}
    auto_create_contacts: true
    auto_log_calls: true
    screen_pop: true
```

Create/edit .env file:
```bash
nano /home/runner/work/PBX/PBX/.env
```

Add:
```bash
ESPOCRM_API_KEY=your-api-key-from-step-6
```

#### Step 8: Restart PBX and Test

```bash
# Restart PBX
sudo systemctl restart pbx

# Test the integration
curl -X GET 'http://your-pbx-server:8080/api/integrations/espocrm/contacts/search?phone=5551234567'
```

You should get a JSON response (even if no contact is found, it should return `{"success": false, "message": "Contact not found"}` instead of an error).

### Troubleshooting EspoCRM

**Problem**: Still getting 404 errors after installation
- **Check Apache is running**: `sudo systemctl status apache2`
- **Check virtual host is enabled**: `sudo a2ensite espocrm`
- **Check file permissions**: `sudo chown -R www-data:www-data /var/www/espocrm`
- **Check Apache error log**: `sudo tail -f /var/log/apache2/espocrm_error.log`

**Problem**: Installation wizard shows database connection error
- **Verify MySQL is running**: `sudo systemctl status mysql`
- **Test database credentials**:
  ```bash
  mysql -u espocrm_user -p espocrm
  # Enter password when prompted
  ```

**Problem**: "api/v1" gives 404 but main site works
- **Solution**: This is normal before installation. Complete the installation wizard first, then the API will be available.

**Problem**: API authentication fails
- **Check API key is correct**: Log into EspoCRM → Administration → API Users → verify the key
- **Check API user is active**: Make sure Status is "Active"
- **Test manually**:
  ```bash
  curl -H "X-Api-Key: your-api-key" http://crm.yourcompany.com/api/v1/Contact
  ```

**Problem**: Permission denied errors
- **Solution**:
  ```bash
  sudo chown -R www-data:www-data /var/www/espocrm
  sudo chmod -R 755 /var/www/espocrm
  sudo chmod -R 775 /var/www/espocrm/data
  sudo chmod -R 775 /var/www/espocrm/custom
  ```

---

## 🔧 Quick Reference Commands

### Start All Services

```bash
# Jitsi (if self-hosted)
sudo systemctl start jitsi-videobridge2 jicofo prosody

# Matrix
cd ~/matrix-synapse
python3 -m synapse.app.homeserver --config-path homeserver.yaml &

# EspoCRM (Apache should auto-start)
sudo systemctl start apache2 mysql

# PBX
sudo systemctl start pbx
```

### Check Service Status

```bash
# Jitsi
sudo systemctl status jitsi-videobridge2

# Matrix
curl http://localhost:8008/_matrix/client/versions

# EspoCRM
curl http://localhost/api/v1  # Should return 401 or JSON, not 404

# PBX
curl http://localhost:8080/health  # Or appropriate health endpoint
```

### View Logs

```bash
# Jitsi
sudo journalctl -u jitsi-videobridge2 -f
sudo journalctl -u jicofo -f

# Matrix
tail -f ~/matrix-synapse/synapse.log

# EspoCRM
sudo tail -f /var/log/apache2/espocrm_error.log

# PBX
sudo journalctl -u pbx -f
```

---

## 🎯 Testing Your Integrations

### Test Jitsi

```bash
# Create instant meeting
curl -X POST http://localhost:8080/api/integrations/jitsi/instant \
  -H "Content-Type: application/json" \
  -d '{"extension": "1001", "contact_name": "Test"}'
```

### Test Matrix

```bash
# Send test message
curl -X POST http://localhost:8080/api/integrations/matrix/messages \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": "!your-room-id:matrix.org",
    "message": "Test from PBX"
  }'
```

### Test EspoCRM

```bash
# Search for contact
curl -X GET 'http://localhost:8080/api/integrations/espocrm/contacts/search?phone=1234567890'

# Create contact
curl -X POST http://localhost:8080/api/integrations/espocrm/contacts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "phone": "5551234567",
    "email": "john@example.com"
  }'
```

---

## 📞 Getting Help

If you're still having issues after following this guide:

1. **Check the main documentation**:
   - [OPEN_SOURCE_INTEGRATIONS.md](OPEN_SOURCE_INTEGRATIONS.md) - Detailed integration guide
   - [OPENSOURCE_INTEGRATIONS_SUMMARY.md](OPENSOURCE_INTEGRATIONS_SUMMARY.md) - Quick summary

2. **Enable debug logging** in config.yml:
   ```yaml
   logging:
     level: DEBUG
   ```

3. **Check PBX logs** for specific error messages

4. **Community support**:
   - Jitsi: https://community.jitsi.org/
   - Matrix: https://matrix.to/#/#matrix:matrix.org
   - EspoCRM: https://forum.espocrm.com/

---

**Document Version**: 1.0  
**Last Updated**: December 15, 2025  
**Maintained By**: PBX Development Team
