# Warden VoIP PBX - Complete Documentation

**Version:** 1.0.0  
**Last Updated:** 2025-12-29  
**Project:** https://github.com/mattiIce/PBX

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Production Deployment](#2-production-deployment)
3. [Core Features & Configuration](#3-core-features--configuration)
4. [Advanced Features](#4-advanced-features)
5. [Integration Guides](#5-integration-guides)
6. [Security & Compliance](#6-security--compliance)
7. [Operations & Troubleshooting](#7-operations--troubleshooting)
8. [Developer Guide](#8-developer-guide)
9. [Appendices](#9-appendices)

---

## 1. Quick Start

### 1.1 Installation Overview

Warden VoIP PBX is a comprehensive VoIP system built in Python. Choose your installation method:

**Option A: Quick Development Setup** (5-10 minutes)
- For testing and development
- Uses SQLite database
- Self-signed SSL certificate

**Option B: Production Deployment** (30-45 minutes)
- Automated Ubuntu 24.04 LTS setup
- PostgreSQL database
- Full security hardening
- See Section 2 for complete guide

### 1.2 Quick Development Setup

#### Prerequisites
- Python 3.12+
- Ubuntu/Debian Linux (recommended)
- 2GB+ RAM, 10GB+ disk space

#### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/mattiIce/PBX.git
cd PBX

# 2. Install system dependencies
sudo apt-get update
sudo apt-get install -y espeak ffmpeg libopus-dev portaudio19-dev libspeex-dev postgresql

# 3. Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your settings

# 5. Configure system
cp config.yml your_config.yml
# Edit your_config.yml

# 6. Generate SSL certificate
python scripts/generate_ssl_cert.py --hostname YOUR_IP_OR_HOSTNAME

# 7. Generate voice prompts (REQUIRED)
python scripts/generate_voice_prompts.py

# 8. Start PBX
python main.py
```

**Access Points:**
- SIP Server: UDP port 5060
- RTP Media: UDP ports 10000-20000
- Admin Panel: https://localhost:8080/admin/
- REST API: https://localhost:8080/api/

### 1.3 Environment Configuration

Create `.env` file with credentials (never commit this file):

```bash
# Database (for production - PostgreSQL recommended)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pbx_system
DB_USER=pbx_user
DB_PASSWORD=your_secure_password_here

# Email (for voicemail notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password

# Optional: Integrations
ZOOM_CLIENT_ID=your_zoom_client_id
ZOOM_CLIENT_SECRET=your_zoom_secret
OPENAI_API_KEY=your_openai_key  # For voicemail transcription
```

Use the interactive setup script:
```bash
python scripts/setup_env.py
```

---

## 2. Production Deployment

### 2.1 Automated Ubuntu 24.04 LTS Deployment

For production deployments, use the automated deployment script:

```bash
# Clone repository
git clone https://github.com/mattiIce/PBX.git
cd PBX

# Run deployment (requires sudo)
sudo bash scripts/deploy_production_pilot.sh

# Or dry-run first
sudo bash scripts/deploy_production_pilot.sh --dry-run
```

**What Gets Configured:**
- ✓ PostgreSQL database with secure credentials
- ✓ Python virtual environment
- ✓ Nginx reverse proxy (optional but recommended)
- ✓ UFW firewall with required ports
- ✓ Daily backup system (2 AM)
- ✓ Prometheus + Node Exporter monitoring
- ✓ Systemd service for auto-start

### 2.2 Post-Deployment Steps

After the deployment script completes:

#### Step 1: Secure Database Password
```bash
# The script generates a random password stored in:
cat /opt/pbx/.db_password

# Update .env file if needed
sudo nano /opt/pbx/.env
```

#### Step 2: SSL Certificate Setup

**Option A: Let's Encrypt (Recommended for Production)**
```bash
sudo scripts/setup_reverse_proxy.sh
# Follow prompts to configure domain and SSL
```

**Option B: In-House Certificate Authority**
```bash
# If you have an enterprise CA
python scripts/request_certificate.py --ca-server ca.yourcompany.com
```

**Option C: Self-Signed (Development Only)**
```bash
python scripts/generate_ssl_cert.py --hostname pbx.yourcompany.com
```

#### Step 3: Generate Voice Prompts (CRITICAL)
```bash
# Voice prompts are REQUIRED for auto-attendant and voicemail
python scripts/generate_voice_prompts.py

# Verify prompts were created
ls -lh voicemail_prompts/
ls -lh auto_attendant/prompts/
```

#### Step 4: Configure PBX
```bash
sudo nano /opt/pbx/config.yml
```

Key settings to configure:
- Extensions and users
- SIP trunk settings (if using external provider)
- Auto-attendant menu options
- Call queue settings
- Email notification settings

#### Step 5: Start and Enable Service
```bash
sudo systemctl start pbx
sudo systemctl enable pbx
sudo systemctl status pbx
```

#### Step 6: Verify Installation
```bash
# Check PBX is running
curl -k https://localhost:8080/api/status

# Check database connection
python scripts/verify_database.py

# View logs
sudo journalctl -u pbx -f
```

### 2.3 Firewall Configuration

Required ports:
```bash
# SIP signaling
sudo ufw allow 5060/udp

# RTP media
sudo ufw allow 10000:20000/udp

# HTTPS admin/API
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp

# Enable firewall
sudo ufw enable
```

### 2.4 Reverse Proxy Setup (Recommended)

Use Nginx reverse proxy for:
- Friendly URLs (https://pbx.yourcompany.com instead of IP:8080)
- Let's Encrypt SSL with auto-renewal
- Rate limiting and security
- WebSocket support for WebRTC

```bash
# Automated setup
sudo scripts/setup_reverse_proxy.sh

# Manual nginx configuration
sudo nano /etc/nginx/sites-available/pbx
```

Sample nginx config:
```nginx
server {
    listen 443 ssl http2;
    server_name pbx.yourcompany.com;
    
    ssl_certificate /etc/letsencrypt/live/pbx.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pbx.yourcompany.com/privkey.pem;
    
    location / {
        proxy_pass https://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 3. Core Features & Configuration

### 3.1 Feature Overview

**Core PBX Capabilities:**
- ✓ Full SIP protocol support (RFC 3261)
- ✓ RTP media handling with multiple codecs
- ✓ Extension management and authentication
- ✓ Intelligent call routing and dial plans
- ✓ Call hold, resume, transfer, forward
- ✓ Conference calling (multi-party)
- ✓ Call parking and retrieval
- ✓ Music on hold (5 tracks included)
- ✓ Voicemail with email notifications
- ✓ Auto-attendant (IVR) system
- ✓ Call Detail Records (CDR)
- ✓ REST API for integration

### 3.2 Audio Codec Support

**Supported Codecs:**

| Codec | Quality | Bandwidth | Best For |
|-------|---------|-----------|----------|
| G.711 (PCMU/PCMA) | Excellent | 64 kbps | Standard VoIP, highest compatibility |
| G.722 | HD Audio | 48-64 kbps | High-quality audio, wideband |
| Opus | Excellent | 6-510 kbps | Modern VoIP, adaptive bitrate |
| G.729 | Good | 8 kbps | Low bandwidth, licensed codec |
| G.726 | Good | 16-40 kbps | Medium quality, ADPCM |
| iLBC | Fair | 13.3-15.2 kbps | Packet loss resilience |
| Speex | Good | 2.15-44 kbps | Variable rate, narrowband/wideband |

**Configuration:**

```yaml
# config.yml
codecs:
  enabled:
    - "PCMU"    # G.711 μ-law (North America)
    - "PCMA"    # G.711 A-law (Europe)
    - "G722"    # HD audio
    - "opus"    # Modern codec
  
  priority:  # Negotiation order
    - "opus"
    - "G722"
    - "PCMU"
    - "PCMA"
```

**Codec Selection Tips:**
- **G.711 (PCMU)**: Best compatibility, use for standard VoIP
- **G.722**: HD audio for conference rooms and executives
- **Opus**: Modern codec with best quality/bandwidth ratio
- **G.729**: Low bandwidth but requires licensing

### 3.3 DTMF Configuration

**Supported DTMF Methods:**
1. **RFC 2833** (RTP Events) - Recommended
2. **SIP INFO** - Legacy support
3. **In-band** - Goertzel algorithm detection

```yaml
# config.yml
dtmf:
  method: "rfc2833"  # or "sip_info", "inband", "auto"
  payload_type: 101  # RFC 2833 payload type
  inband_detection: true  # Enable Goertzel algorithm
  volume: -6  # DTMF volume in dB
```

**Troubleshooting DTMF:**
- If IVR menus don't respond, try `method: "auto"`
- Check phone's DTMF settings (RFC 2833 vs SIP INFO)
- Verify payload type matches between PBX and phone
- Test with in-band detection: `dtmf.inband_detection: true`

### 3.4 Call Flow

**Phone-to-Phone Call Sequence:**

1. **Registration**
   ```
   Phone A → REGISTER → PBX
   PBX → 200 OK → Phone A
   ```

2. **Call Initiation**
   ```
   Phone A → INVITE (to 1002) → PBX
   PBX → 100 Trying → Phone A
   PBX → INVITE → Phone B
   ```

3. **Ringing**
   ```
   Phone B → 180 Ringing → PBX
   PBX → 180 Ringing → Phone A
   ```

4. **Call Answered**
   ```
   Phone B → 200 OK → PBX
   PBX → 200 OK → Phone A
   Phone A → ACK → PBX
   PBX → ACK → Phone B
   ```

5. **RTP Media Stream**
   ```
   Phone A ←→ RTP ←→ PBX ←→ RTP ←→ Phone B
   ```

6. **Call Termination**
   ```
   Phone A → BYE → PBX
   PBX → BYE → Phone B
   Phone B → 200 OK → PBX
   PBX → 200 OK → Phone A
   ```

### 3.5 Extension Configuration

```yaml
# config.yml
extensions:
  - number: "1001"
    name: "John Doe"
    email: "john@company.com"
    password: "securepass"
    allow_external: true  # Allow outbound calls
    voicemail: true
    caller_id: "John Doe <1001>"
    
  - number: "1002"
    name: "Jane Smith"
    email: "jane@company.com"
    password: "securepass"
    allow_external: true
    voicemail: true
```

**Add Extension via API:**
```bash
curl -X POST https://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1005",
    "name": "New User",
    "email": "user@company.com",
    "password": "securepass123",
    "allow_external": true
  }'
```

### 3.6 Dialplan Configuration

```yaml
# config.yml
dialplan:
  patterns:
    # Internal extensions
    - pattern: "^1[0-9]{3}$"
      action: "extension"
      
    # Auto attendant
    - pattern: "^0$"
      action: "auto_attendant"
      
    # Conference rooms
    - pattern: "^2[0-9]{3}$"
      action: "conference"
      
    # Call parking
    - pattern: "^7[0-9]$"
      action: "park"
      
    # Call queues
    - pattern: "^8[0-9]{3}$"
      action: "queue"
      
    # Voicemail access
    - pattern: "^\*([0-9]{4})$"
      action: "voicemail"
      
    # External calls (10-digit)
    - pattern: "^[2-9][0-9]{9}$"
      action: "trunk"
      trunk: "primary_trunk"
```

### 3.7 WebRTC Support

**Current Status:** Framework implemented, needs browser integration testing

**Configuration:**
```yaml
# config.yml
webrtc:
  enabled: true
  stun_servers:
    - "stun:stun.l.google.com:19302"
  turn_servers:
    - url: "turn:turn.yourcompany.com:3478"
      username: "webrtc"
      credential: "password"
  
  ice_candidate_timeout: 5  # seconds
  dtls_certificate: "certs/webrtc.pem"
```

**Known Issues:**
- Browser-to-phone calling needs testing
- Audio codec negotiation in progress
- Use physical IP phones or SIP softphones for production

---

## 4. Advanced Features

### 4.1 Voicemail System

**Capabilities:**
- ✓ Custom greeting recording via phone
- ✓ Automatic email notifications with audio attachment
- ✓ Voicemail-to-email with transcription (optional)
- ✓ Daily reminders for unread messages
- ✓ Auto-route to voicemail on no-answer (configurable timeout)
- ✓ PIN-based access from any phone
- ✓ Message management (listen, delete, skip)
- ✓ Database storage (PostgreSQL/SQLite)

**Configuration:**
```yaml
# config.yml
voicemail:
  enabled: true
  email_notifications: true
  no_answer_timeout: 30  # seconds before routing to VM
  max_recording_time: 180  # 3 minutes
  
  # Email settings
  smtp:
    host: "smtp.gmail.com"
    port: 587
    use_tls: true
    username: "voicemail@company.com"
    password: "${SMTP_PASSWORD}"  # from .env
  
  email:
    from_address: "voicemail@company.com"
    from_name: "PBX Voicemail"
    include_attachment: true
  
  # Daily reminders
  reminders:
    enabled: true
    time: "09:00"  # 9 AM daily
    unread_only: true
  
  # Transcription (optional)
  transcription:
    enabled: false
    provider: "vosk"  # "openai", "google", or "vosk" (offline)
```

**Recording Custom Greetings:**
1. Dial `*1001` (your extension)
2. Enter PIN
3. Press `2` for options
4. Press `1` to record greeting
5. Follow prompts

**Accessing Voicemail:**
- From your phone: Dial `*1001`
- From any phone: Dial `*1001`, then enter PIN

**Database Setup:**
```bash
# PostgreSQL (recommended for production)
sudo -u postgres createdb pbx_voicemail
python scripts/init_voicemail_db.py

# Tables created:
# - voicemail_messages: metadata (caller, timestamp, duration, listened)
# - voicemail_greetings: custom greeting files
# Audio files stored in: voicemail/{extension}/
```

### 4.2 Auto-Attendant (IVR)

**Features:**
- ✓ Multi-level menu system
- ✓ Custom voice prompts (TTS or recorded)
- ✓ DTMF navigation
- ✓ Business hours routing
- ✓ Holiday schedules
- ✓ Queue overflow routing

**Configuration:**
```yaml
# auto_attendant/config.yml
auto_attendant:
  enabled: true
  extension: "0"  # Dial 0 to reach AA
  
  greeting: "auto_attendant/prompts/welcome.wav"
  
  menu_options:
    "1":
      action: "queue"
      target: "8001"  # Sales queue
      prompt: "Transferring to Sales"
    
    "2":
      action: "queue"
      target: "8002"  # Support queue
      prompt: "Transferring to Support"
    
    "3":
      action: "extension"
      target: "1000"  # Operator
      prompt: "Transferring to Operator"
    
    "4":
      action: "submenu"
      menu: "directory"
    
    "9":
      action: "repeat"
    
    "0":
      action: "extension"
      target: "1000"  # Operator fallback
  
  business_hours:
    enabled: true
    timezone: "America/New_York"
    schedule:
      monday: { start: "09:00", end: "17:00" }
      tuesday: { start: "09:00", end: "17:00" }
      wednesday: { start: "09:00", end: "17:00" }
      thursday: { start: "09:00", end: "17:00" }
      friday: { start: "09:00", end: "17:00" }
    
    after_hours_action: "voicemail"
    after_hours_target: "1000"  # General voicemail
  
  timeout: 10  # seconds before repeating menu
  max_retries: 3
  invalid_retry: 2
```

**Generating Voice Prompts:**
```bash
# Generate all default prompts
python scripts/generate_voice_prompts.py

# Generate custom prompt
python scripts/generate_voice_prompts.py --text "Thank you for calling ABC Company" --output auto_attendant/prompts/custom_welcome.wav
```

### 4.3 Phone Provisioning

**Supported Brands:**
- Zultys (ZIP 33G, 37G, 535M, 555M)
- Yealink (T41S, T42S, T46S, T48S, T53, T54W, T57W)
- Polycom (VVX 150, 250, 350, 450, 501, 601)
- Cisco (7940, 7960, 7941, 7942, 7945, 7961, 7962, 7965)
- Grandstream (GXP series, GRP series)

**Auto-Provisioning Setup:**
```yaml
# config.yml
provisioning:
  enabled: true
  http_port: 8888  # Provision server port
  base_url: "http://pbx.company.com:8888"
  
  # Server settings auto-populated
  sip_server: "pbx.company.com"
  sip_port: 5060
  
  # Template directory
  template_path: "provisioning_templates/"
  
  # DHCP Option 66 or phone manual config
  tftp_server: "pbx.company.com"
```

**Phone Configuration:**
1. Connect phone to network
2. Configure DHCP Option 66: `http://pbx.company.com:8888`
3. Or manually set provision server in phone
4. Phone downloads config and reboots
5. Extension auto-registers

**Template Customization:**
```bash
# View available templates
ls provisioning_templates/

# Edit template (variables auto-populated)
nano provisioning_templates/yealink/t46s.cfg

# Available variables:
# {EXTENSION} - Extension number
# {PASSWORD} - SIP password
# {DISPLAY_NAME} - User name
# {SIP_SERVER} - PBX IP/hostname
# {SIP_PORT} - SIP port (5060)
```

### 4.4 Phone Book System

**Features:**
- ✓ Centralized company directory
- ✓ Active Directory sync
- ✓ Push to IP phones (multiple formats)
- ✓ Search capability
- ✓ Database storage
- ✓ LDAPS support for phones

**Configuration:**
```yaml
# config.yml
phonebook:
  enabled: true
  
  # Active Directory sync
  ad_sync:
    enabled: true
    server: "ldap://ad.company.com"
    base_dn: "DC=company,DC=com"
    username: "${AD_USERNAME}"
    password: "${AD_PASSWORD}"
    sync_interval: 3600  # 1 hour
    
    # Fields to sync
    fields:
      name: "displayName"
      number: "telephoneNumber"
      mobile: "mobile"
      email: "mail"
      department: "department"
  
  # Export formats
  formats:
    - yealink_xml
    - cisco_xml
    - json
  
  # Push to phones
  push_enabled: true
  push_url: "http://pbx.company.com:8080/api/phonebook"
```

**Manual Entry:**
```bash
# Add entry via API
curl -X POST https://localhost:8080/api/phonebook \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "number": "1001",
    "mobile": "555-123-4567",
    "email": "john@company.com",
    "department": "Sales"
  }'
```

**LDAPS Configuration for Phones:**
```yaml
# For phones with LDAPS support (Zultys ZIP 33G/37G)
phonebook:
  ldaps:
    enabled: true
    port: 3890  # LDAPS port
    base_dn: "ou=phonebook,dc=pbx"
    bind_dn: "cn=phonebook,dc=pbx"
    bind_password: "${LDAPS_PASSWORD}"
```

Configure on phone:
- LDAP Server: `pbx.company.com:3890`
- Base DN: `ou=phonebook,dc=pbx`
- Username: `cn=phonebook,dc=pbx`
- Password: (as configured)

### 4.5 Call Queues (ACD)

**Queue Strategies:**
- Ring All - All available agents ring simultaneously
- Round Robin - Distribute calls evenly
- Least Recent - Route to agent who answered longest ago
- Fewest Calls - Route to agent with least calls answered
- Random - Random agent selection
- Priority - Based on agent priority levels

**Configuration:**
```yaml
# config.yml
queues:
  - number: "8001"
    name: "Sales Queue"
    strategy: "least_recent"
    agents:
      - extension: "1001"
        priority: 1
      - extension: "1002"
        priority: 1
    
    max_wait_time: 300  # 5 minutes
    overflow_action: "voicemail"
    overflow_target: "1000"
    
    announce_position: true
    announce_hold_time: true
    
    music_on_hold: "default"
    periodic_announce: 30  # seconds
```

**Agent Login/Logout:**
```bash
# Via API
curl -X POST https://localhost:8080/api/queues/8001/agents/1001/login
curl -X POST https://localhost:8080/api/queues/8001/agents/1001/logout

# Via phone (feature code)
# Dial *72 to login to queue
# Dial *73 to logout from queue
```

### 4.6 Paging System

**Features:**
- ✓ Zone-based paging
- ✓ All-call paging
- ✓ SIP/RTP integration
- ✓ Digital-to-analog converter support
- ✓ Hardware-ready deployment

**Configuration:**
```yaml
# config.yml
paging:
  enabled: true
  
  zones:
    - id: "page1"
      name: "First Floor"
      extension: "9001"
      devices:
        - ip: "192.168.1.100"  # DAC device
          codec: "PCMU"
    
    - id: "page2"
      name: "Second Floor"
      extension: "9002"
      devices:
        - ip: "192.168.1.101"
    
    - id: "pageall"
      name: "All Call"
      extension: "9999"
      devices:
        - ip: "192.168.1.100"
        - ip: "192.168.1.101"
```

**Usage:**
- Dial `9001` for First Floor page
- Dial `9002` for Second Floor page
- Dial `9999` for all-call page

### 4.7 Webhook System

**Event Types:**
- Call events: answered, ended, transferred, parked
- Voicemail: new message, message retrieved
- Extension: registered, unregistered
- Queue: agent login/logout, call queued
- Conference: participant joined/left

**Configuration:**
```yaml
# config.yml
webhooks:
  enabled: true
  
  subscriptions:
    - url: "https://crm.company.com/api/pbx/events"
      events:
        - "call.answered"
        - "call.ended"
        - "voicemail.new"
      
      # Security
      secret: "${WEBHOOK_SECRET}"  # HMAC signature
      
      # Custom headers
      headers:
        Authorization: "Bearer ${CRM_API_TOKEN}"
      
      # Retry configuration
      retry:
        max_attempts: 3
        backoff_factor: 2  # Exponential backoff
```

**Webhook Payload Example:**
```json
{
  "event": "call.answered",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "call_id": "abc123",
    "from": "1001",
    "to": "1002",
    "caller_name": "John Doe"
  },
  "signature": "sha256=abc123..."
}
```

**Signature Verification (Python):**
```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    computed = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={computed}", signature)
```


---

## 5. Integration Guides

### 5.1 Integration Overview

**Free & Open Source Options:**
- Jitsi Meet (video conferencing) - Zoom alternative
- Matrix/Element (team messaging) - Slack/Teams alternative
- EspoCRM (customer relationship) - Salesforce alternative
- Vosk (speech recognition) - offline transcription
- OpenLDAP (directory services) - Active Directory compatible

**Enterprise Integrations (Optional):**
- Zoom - OAuth meetings
- Active Directory - LDAP auth and sync
- Microsoft Outlook - calendar and contacts
- Microsoft Teams - presence and meetings

### 5.2 Active Directory Integration

**Configuration:**
```yaml
# config.yml
integrations:
  active_directory:
    enabled: true
    server: "ldap://ad.company.com"
    port: 389
    use_ssl: true
    
    # Authentication
    bind_dn: "CN=pbx-service,OU=Service Accounts,DC=company,DC=com"
    bind_password: "${AD_PASSWORD}"
    
    # Search settings
    base_dn: "DC=company,DC=com"
    user_filter: "(&(objectClass=user)(objectCategory=person))"
    
    # Attribute mapping
    attributes:
      username: "sAMAccountName"
      display_name: "displayName"
      email: "mail"
      phone: "telephoneNumber"
      mobile: "mobile"
      department: "department"
    
    # Sync settings
    sync_enabled: true
    sync_interval: 3600  # 1 hour
```

**Search API:**
```bash
# Search AD users
curl "https://localhost:8080/api/ad/search?q=john"

# Get user details
curl "https://localhost:8080/api/ad/user/jdoe"
```

### 5.3 CRM Integration (EspoCRM)

**Setup:**
```bash
# Install EspoCRM (free, open-source)
# See https://www.espocrm.com/

# Configure webhook in PBX
```

```yaml
# config.yml
webhooks:
  subscriptions:
    - url: "https://crm.company.com/api/v1/pbx/call"
      events: ["call.answered", "call.ended"]
      headers:
        X-Api-Key: "${ESPO_API_KEY}"
```

**Features:**
- Screen pop on incoming calls
- Call logging (duration, outcome)
- Contact lookup by phone number
- Click-to-dial from CRM

### 5.4 Email Integration

**Voicemail-to-Email:**
```yaml
voicemail:
  email_notifications: true
  smtp:
    host: "smtp.gmail.com"
    port: 587
    use_tls: true
    username: "pbx@company.com"
    password: "${SMTP_PASSWORD}"
```

**Gmail App Password:**
1. Enable 2FA on Google account
2. Generate app password: https://myaccount.google.com/apppasswords
3. Use app password in .env file

**Office 365:**
```yaml
smtp:
  host: "smtp.office365.com"
  port: 587
  use_tls: true
  username: "pbx@company.com"
  password: "${O365_PASSWORD}"
```

### 5.5 Zoom Integration

**OAuth Setup:**
1. Create Zoom OAuth app: https://marketplace.zoom.us/
2. Configure redirect URI: `https://pbx.company.com:8080/api/zoom/callback`
3. Get Client ID and Secret

```bash
# .env
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
```

**Configuration:**
```yaml
integrations:
  zoom:
    enabled: true
    client_id: "${ZOOM_CLIENT_ID}"
    client_secret: "${ZOOM_CLIENT_SECRET}"
    redirect_uri: "https://pbx.company.com:8080/api/zoom/callback"
```

**Create Meeting:**
```bash
curl -X POST https://localhost:8080/api/zoom/meeting \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Sales Meeting",
    "start_time": "2025-01-20T14:00:00Z",
    "duration": 60
  }'
```

---

## 6. Security & Compliance

### 6.1 Security Features

**Implemented Security:**
- ✓ FIPS 140-2 compliant encryption (AES-256-GCM)
- ✓ TLS/SIPS support (encrypted signaling)
- ✓ SRTP support (encrypted media)
- ✓ PBKDF2-HMAC-SHA256 password hashing (600k iterations)
- ✓ Rate limiting (brute force protection)
- ✓ IP banning (automatic blocking)
- ✓ HTTPS API with TLS 1.2+
- ✓ Certificate management (Let's Encrypt, in-house CA)

**Password Security:**
```yaml
# config.yml
security:
  password_hashing:
    algorithm: "pbkdf2_hmac_sha256"
    iterations: 600000  # OWASP 2024 recommendation
    salt_length: 32
  
  rate_limiting:
    enabled: true
    max_attempts: 5
    window: 300  # 5 minutes
    ban_duration: 3600  # 1 hour
  
  tls:
    min_version: "TLSv1.2"
    ciphers:
      - "TLS_AES_256_GCM_SHA384"
      - "TLS_AES_128_GCM_SHA256"
      - "ECDHE-RSA-AES256-GCM-SHA384"
```

### 6.2 SSL/TLS Configuration

**Let's Encrypt (Recommended):**
```bash
sudo scripts/setup_reverse_proxy.sh
# Select Let's Encrypt option
```

**Manual certbot:**
```bash
sudo certbot certonly --standalone -d pbx.company.com
```

**In-House CA:**
```bash
python scripts/request_certificate.py \
  --ca-server ca.company.com \
  --common-name pbx.company.com
```

**Self-Signed (Development):**
```bash
python scripts/generate_ssl_cert.py \
  --hostname pbx.company.com \
  --output certs/
```

### 6.3 Compliance - E911

**E911 Protection:**
The PBX includes automatic protection against accidental 911 calls during testing:

```yaml
# config.yml
e911_protection:
  enabled: true  # Blocks 911 in test/dev environments
  production_mode: false  # Set true for production
  
  # Allowed in production only
  emergency_numbers:
    - "911"
    - "933"  # Test number
  
  # Location information
  location:
    address: "123 Main St"
    city: "New York"
    state: "NY"
    zip: "10001"
    building: "Main Building"
    floor: "3rd Floor"
```

**Kari's Law Compliance:**
- Direct 911 dialing (no prefix required)
- Automatic notification to security/reception
- Location information transmission

**Multi-Site E911:**
```yaml
extensions:
  - number: "1001"
    location_id: "building_a_floor_3"
    
locations:
  - id: "building_a_floor_3"
    address: "123 Main St, Floor 3"
    city: "New York"
    state: "NY"
    zip: "10001"
    elin: "+12125551234"  # Emergency Location ID Number
```

### 6.4 FIPS 140-2 Deployment

**Ubuntu FIPS Kernel:**
```bash
# Enable FIPS mode (Ubuntu Pro required)
sudo ua attach YOUR_TOKEN
sudo ua enable fips
sudo reboot

# Verify FIPS mode
cat /proc/sys/crypto/fips_enabled  # Should output: 1
```

**PBX FIPS Configuration:**
```yaml
# config.yml
security:
  fips_mode: true
  
  encryption:
    algorithm: "AES-256-GCM"  # FIPS-approved
    key_derivation: "PBKDF2-HMAC-SHA256"
  
  tls:
    fips_ciphers_only: true
```

---

## 7. Operations & Troubleshooting

### 7.1 Admin Panel

**Access:** https://pbx.company.com/admin/ (or https://localhost:8080/admin/)

**Features:**
- Dashboard - system status and statistics
- Extension Management - add, edit, delete extensions
- User Management - passwords, permissions
- Active Calls - monitor ongoing calls
- Call History - CDR viewer
- Email Configuration - SMTP settings
- System Settings - PBX configuration

**Login Issues:**
If you see "Connection error. Please try again.":

1. **Check PBX is running:**
   ```bash
   sudo systemctl status pbx
   # If not running:
   sudo systemctl start pbx
   ```

2. **Verify API is accessible:**
   ```bash
   curl -k https://localhost:8080/api/status
   ```

3. **Check browser console (F12)** for detailed error messages

4. **Clear browser cache:** `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)

5. **Check firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 8080/tcp
   ```

### 7.2 Common Issues

**Issue: No Audio on Calls**
```bash
# Check RTP ports are open
sudo ufw allow 10000:20000/udp

# Verify codec compatibility
# Check config.yml codecs match phone codecs

# Regenerate voice prompts at correct sample rate
python scripts/generate_voice_prompts.py
```

**Issue: Extensions Won't Register**
```bash
# Check SIP port
sudo ufw allow 5060/udp

# Verify credentials in config.yml
# Check phone SIP server settings

# View SIP logs
tail -f logs/pbx.log | grep SIP
```

**Issue: Voicemail Not Working**
```bash
# Check database
python scripts/verify_database.py

# Initialize voicemail DB
python scripts/init_voicemail_db.py

# Verify voice prompts exist
ls -lh voicemail_prompts/
```

**Issue: Email Notifications Not Sending**
```bash
# Test SMTP settings
python scripts/test_email.py

# Check .env credentials
cat .env | grep SMTP

# View email logs
tail -f logs/pbx.log | grep EMAIL
```

### 7.3 Database Management

**PostgreSQL Backup:**
```bash
# Manual backup
sudo -u postgres pg_dump pbx_system > /backup/pbx_$(date +%Y%m%d).sql

# Automated daily backup (installed by deployment script)
# Runs at 2 AM daily, keeps 30 days
# Location: /var/backups/pbx/
```

**Restore from Backup:**
```bash
sudo systemctl stop pbx
sudo -u postgres dropdb pbx_system
sudo -u postgres createdb pbx_system
sudo -u postgres psql pbx_system < /backup/pbx_20250115.sql
sudo systemctl start pbx
```

**Database Migration:**
```bash
# Export from SQLite
python scripts/export_db.py --from sqlite --output export.json

# Import to PostgreSQL
python scripts/import_db.py --to postgresql --input export.json
```

### 7.4 Log Management

**Log Locations:**
```bash
# System logs
/opt/pbx/logs/pbx.log

# Systemd journal
sudo journalctl -u pbx

# Nginx logs (if using reverse proxy)
/var/log/nginx/access.log
/var/log/nginx/error.log
```

**Log Levels:**
```yaml
# config.yml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/pbx.log"
  max_size: 10485760  # 10 MB
  backup_count: 5
```

**Real-time Monitoring:**
```bash
# Follow main log
tail -f logs/pbx.log

# Filter for errors
tail -f logs/pbx.log | grep ERROR

# SIP traffic only
tail -f logs/pbx.log | grep SIP

# Call events
tail -f logs/pbx.log | grep "CALL"
```

### 7.5 Performance Monitoring

**System Status API:**
```bash
curl -k https://localhost:8080/api/status
```

Response:
```json
{
  "status": "running",
  "uptime": 86400,
  "active_calls": 5,
  "registered_extensions": 25,
  "memory_usage": "256 MB",
  "cpu_usage": "5%"
}
```

**Call Statistics:**
```bash
curl -k https://localhost:8080/api/statistics
```

**Prometheus Metrics:**
If monitoring is enabled:
```bash
curl http://localhost:9090/metrics
```

Metrics include:
- `pbx_active_calls` - Current active calls
- `pbx_total_calls` - Total calls since startup
- `pbx_registered_extensions` - Registered extensions
- `pbx_voicemail_messages` - Unread voicemails
- `pbx_queue_calls_waiting` - Calls in queues

### 7.6 Backup & Recovery

**Full System Backup:**
```bash
# Backup script (run as root)
sudo /opt/pbx/scripts/backup_full.sh

# Creates:
# - Database dump
# - Config files
# - Voicemail recordings
# - Call recordings
# - Custom prompts
```

**Emergency Recovery:**
```bash
# Stop PBX
sudo systemctl stop pbx

# Restore from backup
sudo /opt/pbx/scripts/restore_backup.sh /backup/pbx_20250115.tar.gz

# Verify database
python scripts/verify_database.py

# Start PBX
sudo systemctl start pbx
```

---

## 8. Developer Guide

### 8.1 Architecture Overview

**Component Structure:**
```
PBX System
├── pbx/core/          - Core call handling logic
├── pbx/sip/           - SIP protocol implementation
├── pbx/rtp/           - RTP media handling
├── pbx/features/      - Advanced features (VM, queues, etc.)
├── pbx/integrations/  - External service integrations
├── pbx/api/           - REST API server
└── pbx/utils/         - Utilities and helpers
```

**Call Flow:**
1. SIP Server receives INVITE
2. PBX Core validates and routes call
3. RTP Handler establishes media session
4. Features layer adds capabilities (transfer, hold, etc.)
5. CDR logs call details

### 8.2 REST API Reference

**Authentication:**
Currently API is open. For production, implement authentication:
```python
# Add to api/rest_api.py
@app.before_request
def check_auth():
    api_key = request.headers.get('X-API-Key')
    if not validate_api_key(api_key):
        return jsonify({"error": "Unauthorized"}), 401
```

**Endpoints:**

**System Status:**
```bash
GET /api/status
```

**Extensions:**
```bash
# List all
GET /api/extensions

# Get specific
GET /api/extensions/1001

# Create
POST /api/extensions
{
  "number": "1005",
  "name": "New User",
  "email": "user@company.com",
  "password": "secure123"
}

# Update
PUT /api/extensions/1005
{
  "name": "Updated Name",
  "email": "newemail@company.com"
}

# Delete
DELETE /api/extensions/1005
```

**Active Calls:**
```bash
# List active calls
GET /api/calls

# Get call details
GET /api/calls/{call_id}

# Transfer call
POST /api/calls/{call_id}/transfer
{
  "to": "1002"
}

# Hangup call
DELETE /api/calls/{call_id}
```

**Call Detail Records:**
```bash
# Get CDR
GET /api/cdr?start_date=2025-01-01&end_date=2025-01-31

# Get statistics
GET /api/statistics
```

**Configuration:**
```bash
# Get config
GET /api/config

# Update config
PUT /api/config
{
  "voicemail": {
    "no_answer_timeout": 25
  }
}
```

### 8.3 Development Setup

**Prerequisites:**
```bash
# Python 3.12+
python3 --version

# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

**Code Quality:**
```bash
# Format code
make format

# Run linters
make lint

# Type checking
make mypy

# All quality checks
make quality
```

**Testing:**
```bash
# Run all tests
make test

# Run specific test
pytest tests/test_basic.py

# Coverage report
make test-cov
```

### 8.4 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Commit message format
- Pull request process
- Testing requirements

**Quick Checklist:**
- [ ] Code follows PEP 8 style
- [ ] Type hints added
- [ ] Docstrings written
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Linters pass (black, flake8, pylint)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated

---

## 9. Appendices

### Appendix A: Configuration Reference

Complete `config.yml` structure:
```yaml
# Server Settings
server:
  host: "0.0.0.0"
  sip_port: 5060
  rtp_port_range: [10000, 20000]
  
# Security
security:
  fips_mode: false
  password_hashing:
    algorithm: "pbkdf2_hmac_sha256"
    iterations: 600000
  
# Extensions
extensions:
  - number: "1001"
    name: "User Name"
    email: "user@company.com"
    password: "secure"
    allow_external: true
    
# Features
voicemail:
  enabled: true
  email_notifications: true
  
auto_attendant:
  enabled: true
  extension: "0"
  
queues:
  - number: "8001"
    name: "Sales"
    strategy: "least_recent"
    
# Integrations
integrations:
  active_directory:
    enabled: false
  zoom:
    enabled: false
```

### Appendix B: Port Reference

| Port | Protocol | Purpose |
|------|----------|---------|
| 5060 | UDP | SIP signaling |
| 5061 | TCP/TLS | Secure SIP (SIPS) |
| 10000-20000 | UDP | RTP media streams |
| 8080 | TCP | HTTPS API/Admin |
| 8888 | TCP | Phone provisioning |
| 443 | TCP | Nginx reverse proxy |
| 9090 | TCP | Prometheus metrics |

### Appendix C: Dialplan Patterns

| Pattern | Range | Purpose |
|---------|-------|---------|
| 0 | Single | Auto attendant |
| 1xxx | 1000-1999 | Extensions |
| 2xxx | 2000-2999 | Conferences |
| 7x | 70-79 | Call parking |
| 8xxx | 8000-8999 | Call queues |
| 9xxx | 9000-9999 | Paging zones |
| \*xxxx | Any | Voicemail access |

### Appendix D: Feature Codes

| Code | Function |
|------|----------|
| \*1001 | Access voicemail for ext 1001 |
| \*72 | Login to queue |
| \*73 | Logout from queue |
| \*74 | Park call |
| \*75 | Retrieve parked call |
| 0 | Operator/Auto-attendant |

### Appendix E: Troubleshooting Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| No audio | Check firewall: `sudo ufw allow 10000:20000/udp` |
| Won't register | Verify SIP port: `sudo ufw allow 5060/udp` |
| Login fails | Clear cache: `Ctrl+Shift+R`, check service: `systemctl status pbx` |
| Email not sending | Test: `python scripts/test_email.py` |
| Database error | Verify: `python scripts/verify_database.py` |
| Voice prompts missing | Generate: `python scripts/generate_voice_prompts.py` |

### Appendix F: Additional Resources

**Documentation:**
- README.md - Project overview
- CHANGELOG.md - Version history
- TODO.md - Planned features
- EXECUTIVE_SUMMARY.md - Business overview

**External Resources:**
- SIP Protocol: RFC 3261
- RTP Protocol: RFC 3550
- SRTP: RFC 3711
- Python: https://docs.python.org/3/

**Support:**
- GitHub Issues: https://github.com/mattiIce/PBX/issues
- Email: support@yourcompany.com

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-12-29  
**Copyright:** Warden VoIP PBX Project

