# Warden VoIP PBX - Complete Documentation

**Version:** 1.2.0
**Last Updated:** 2026-02-13
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
8. [Update & Maintenance Guide](#8-update--maintenance-guide)
9. [Developer Guide](#9-developer-guide) (Architecture, API, Database, Frontend)
10. [Appendices](#10-appendices)

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
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js (for frontend TypeScript compilation)
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

# 3. Install Python dependencies (using uv)
make install          # Development mode with dev dependencies
# Or for production only:
# make install-prod

# 4. Install frontend dependencies
npm install

# 5. Set up environment
cp .env.example .env
# Edit .env with your settings

# 6. Configure system
cp config.yml your_config.yml
# Edit your_config.yml

# 7. Generate SSL certificate
python scripts/generate_ssl_cert.py --hostname YOUR_IP_OR_HOSTNAME

# 8. Generate voice prompts (REQUIRED)
python scripts/generate_voice_prompts.py

# 9. Start PBX (with auto-reload for development)
make dev              # Backend + frontend with hot reload
# Or backend only:
# make dev-backend
# Or production mode (no auto-reload):
# make run
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

## 8. Update & Maintenance Guide

### 8.1 Overview

This section covers how to safely update your PBX system, including:
- Python package and dependency updates
- System package updates
- Code updates from the repository
- Database migrations
- Safe update procedures
- Rollback strategies
- Post-update testing

**Update Types:**
- **Security Updates**: Critical patches for vulnerabilities (immediate)
- **Feature Updates**: New features and enhancements (scheduled)
- **Dependency Updates**: Updated Python packages or system libraries (periodic)
- **Hotfixes**: Emergency fixes for production issues (as needed)

### 8.2 Pre-Update Checklist

**Before any update, always:**

1. **Create a full backup:**
   ```bash
   # Automated backup script
   sudo /opt/pbx/scripts/backup_full.sh
   
   # Manual backup
   BACKUP_DIR="/var/backups/pbx/manual-$(date +%Y%m%d-%H%M%S)"
   sudo mkdir -p "$BACKUP_DIR"
   
   # Backup database
   sudo -u postgres pg_dump pbx_system > "$BACKUP_DIR/database.sql"
   
   # Backup configuration
   sudo cp /opt/pbx/config.yml "$BACKUP_DIR/"
   sudo cp /opt/pbx/.env "$BACKUP_DIR/"
   
   # Backup voicemail and recordings
   sudo tar -czf "$BACKUP_DIR/voicemail.tar.gz" /opt/pbx/voicemail/
   sudo tar -czf "$BACKUP_DIR/recordings.tar.gz" /opt/pbx/recordings/
   ```

2. **Schedule during maintenance window:**
   - Notify users of planned downtime
   - Choose low-traffic period (typically 2-4 AM)
   - Plan for 15-30 minutes of downtime

3. **Document current version:**
   ```bash
   # Record current versions
   cd /opt/pbx
   git log -1 --oneline > /tmp/pre-update-version.txt
   uv pip freeze > /tmp/pre-update-packages.txt
   ```

4. **Verify system health:**
   ```bash
   # Check service status
   sudo systemctl status pbx
   
   # Check disk space (need at least 1GB free)
   df -h /opt/pbx
   
   # Check database connectivity
   python scripts/verify_database.py
   
   # Check active calls (should be 0 during maintenance)
   curl -k https://localhost:8080/api/calls
   ```

### 8.3 Updating Python Packages

#### When to Update Python Packages

Update Python packages when:
- Security vulnerabilities are announced
- New features require updated dependencies
- You see deprecation warnings in logs
- Following a major release update

#### Dependency Management

Dependencies are defined in `pyproject.toml` and managed via **uv**:

```bash
# Install/update all dependencies
cd /opt/pbx
make install-prod        # Production
make install             # Development (includes dev tools)

# Update a specific package
uv pip install --upgrade cryptography

# Generate a locked requirements file for reproducible builds
make lock                # Creates requirements.lock from pyproject.toml
make sync                # Install from requirements.lock
```

#### Safe Package Update Procedure

```bash
# 1. Navigate to PBX directory
cd /opt/pbx

# 2. Stop PBX service
sudo systemctl stop pbx

# 3. Update dependencies
make install-prod

# 4. Verify installation
python -c "import pbx; print('Import successful')"

# 5. Run tests
make test

# 6. Restart service
sudo systemctl start pbx

# 7. Monitor logs for errors
sudo journalctl -u pbx -f
```

#### Update Specific Package (Production)

```bash
# Stop service
sudo systemctl stop pbx

# Update specific package
uv pip install --upgrade cryptography==46.0.5

# Verify
python -c "from cryptography.fernet import Fernet; print('OK')"

# Restart and verify
sudo systemctl start pbx
curl -k https://localhost:8080/api/status
```

### 8.4 Updating System Packages

#### System Dependencies

The PBX requires these system packages:
- `espeak` - Text-to-speech engine
- `ffmpeg` - Audio/video processing
- `libopus-dev` - Opus codec library
- `portaudio19-dev` - Audio I/O library
- `libspeex-dev` - Speex codec library
- `postgresql` - Database server

#### Safe System Update Procedure

```bash
# Update package lists
sudo apt-get update

# Check what will be updated
sudo apt-get --dry-run upgrade

# Update specific packages
sudo apt-get install --only-upgrade espeak ffmpeg

# Or update all system packages
sudo apt-get upgrade -y

# If PostgreSQL is updated, restart it
sudo systemctl restart postgresql

# Verify PBX still works
sudo systemctl restart pbx
sudo systemctl status pbx
```

#### After System Package Updates

```bash
# Regenerate voice prompts (if espeak was updated)
cd /opt/pbx
python scripts/generate_voice_prompts.py

# Test audio functionality
python scripts/test_audio_comprehensive.py

# Verify codecs still work
curl -k https://localhost:8080/api/codecs
```

### 8.5 Updating PBX Code from Repository

#### Method 1: Automated Update Script (Recommended)

```bash
# Interactive update with prompts
cd /opt/pbx
sudo bash scripts/update_server_from_repo.sh

# The script will:
# 1. Check for local modifications
# 2. Create backup of changed files
# 3. Fetch latest changes
# 4. Show what will be updated
# 5. Apply updates (your choice: merge or hard reset)
# 6. Verify Python syntax
# 7. Offer to restart service
```

**Script Options:**
- **Merge**: Preserves local changes, merges with remote (safer)
- **Hard Reset**: Discards all local changes, matches repository exactly (cleanest)

#### Method 2: Force Update (No Prompts)

```bash
# For automated updates or when you want to overwrite everything
cd /opt/pbx
sudo bash scripts/force_update_server.sh

# This will:
# 1. Create backup
# 2. Hard reset to repository
# 3. Verify syntax
# 4. Restart service automatically
```

#### Method 3: Manual Update (Full Control)

```bash
# Navigate to PBX directory
cd /opt/pbx

# Check current status
git status

# Fetch latest changes
git fetch origin

# Review changes before applying
git log HEAD..origin/main --oneline

# See detailed changes
git diff HEAD..origin/main

# Backup local modifications (if any)
git stash save "Backup before update $(date)"

# Pull latest changes
git pull origin main

# Update dependencies (if pyproject.toml changed)
make install-prod

# Run database migrations (if any)
alembic upgrade head

# Restart service
sudo systemctl restart pbx

# Monitor logs
sudo journalctl -u pbx -f
```

#### Updating Specific Files Only

```bash
# Update only specific files from repository
cd /opt/pbx

# Check what changed in a specific file
git diff origin/main -- path/to/file.py

# Update just that file
git checkout origin/main -- path/to/file.py

# Or update entire directory
git checkout origin/main -- pbx/core/

# Restart service
sudo systemctl restart pbx
```

### 8.6 Database Migrations

The PBX uses **Alembic** for database schema migrations with **SQLAlchemy** ORM models.

#### Checking for Database Changes

```bash
# Check if update includes new migrations
cd /opt/pbx
git log HEAD..origin/main -- alembic/versions/

# View current migration status
alembic current

# View pending migrations
alembic history --indicate-current
```

#### Running Database Migrations

```bash
# Backup database first (CRITICAL!)
sudo -u postgres pg_dump pbx_system > /var/backups/pbx/pre-migration-$(date +%Y%m%d).sql

# Stop PBX service
sudo systemctl stop pbx

# Apply all pending migrations
alembic upgrade head

# Verify migration
python scripts/verify_database.py

# Start service
sudo systemctl start pbx

# Test functionality
curl -k https://localhost:8080/api/status
```

#### Creating New Migrations (Developers)

```bash
# After modifying SQLAlchemy models in pbx/models/
alembic revision --autogenerate -m "Add new_field to extensions"

# Review the generated migration in alembic/versions/
# Then apply it:
alembic upgrade head

# Rollback one migration:
alembic downgrade -1
```

### 8.7 Handling Update Failures

#### Service Won't Start After Update

```bash
# Check service status
sudo systemctl status pbx

# View recent logs
sudo journalctl -u pbx -n 100 --no-pager

# Check for Python errors
cd /opt/pbx
python main.py

# Common issues:
# 1. Syntax errors - Check logs for file and line number
# 2. Import errors - Missing dependencies: make install-prod
# 3. Configuration errors - Verify config.yml syntax: python -c "import yaml; yaml.safe_load(open('config.yml'))"
# 4. Database errors - Check connection: python scripts/verify_database.py
# 5. Migration errors - Run: alembic upgrade head
```

#### Dependency Conflicts

```bash
# Reinstall all dependencies from scratch
cd /opt/pbx

# Clean install
make clean
make install-prod

# Or use locked dependencies for reproducible builds
make sync
```

#### Configuration Issues

```bash
# Validate config.yml syntax
python -c "import yaml; yaml.safe_load(open('config.yml'))"

# Compare with example config
diff config.yml config.yml.example

# Reset to default (backup first!)
cp config.yml config.yml.backup
cp config.yml.example config.yml
# Then manually restore your settings
```

### 8.8 Rollback Procedures

#### Quick Rollback - Service Issues

```bash
# Stop failing service
sudo systemctl stop pbx

# Rollback to previous code version
cd /opt/pbx
git log --oneline -10  # Find previous commit
git reset --hard COMMIT_HASH  # Replace with actual commit hash

# Restore dependencies
make install-prod

# Rollback database migrations if needed
alembic downgrade -1

# Restart service
sudo systemctl start pbx
sudo systemctl status pbx
```

#### Full Rollback - Complete Restore

```bash
# Stop service
sudo systemctl stop pbx

# Restore database
BACKUP_FILE="/var/backups/pbx/pbx_20250115.sql"
sudo -u postgres dropdb pbx_system
sudo -u postgres createdb pbx_system
sudo -u postgres psql pbx_system < "$BACKUP_FILE"

# Restore code
cd /opt/pbx
git reset --hard PREVIOUS_COMMIT_HASH

# Restore configuration
sudo cp /var/backups/pbx/manual-20250115/config.yml .
sudo cp /var/backups/pbx/manual-20250115/.env .

# Restore dependencies
make install-prod

# Restore voicemail (if needed)
sudo tar -xzf /var/backups/pbx/manual-20250115/voicemail.tar.gz -C /

# Start service
sudo systemctl start pbx

# Verify
curl -k https://localhost:8080/api/status
```

#### Rollback to Specific Version

```bash
# View version history
cd /opt/pbx
git log --oneline --graph --all

# Rollback to specific tag/release
git checkout v1.0.0

# Reinstall dependencies for that version
make install-prod

# Restart
sudo systemctl restart pbx
```

### 8.9 Post-Update Testing

#### Essential Tests After Any Update

```bash
# 1. Service Health
sudo systemctl status pbx
curl -k https://localhost:8080/api/status

# 2. Database Connectivity
python scripts/verify_database.py

# 3. Extension Registration
# Register a test phone and verify it shows in:
curl -k https://localhost:8080/api/extensions

# 4. Test Call
# Make a test call between two extensions
# Verify audio works in both directions

# 5. Voicemail
# Call extension, let it go to voicemail
# Leave message and verify it's recorded
# Check email notification received

# 6. Admin Panel
# Access https://your-server:8080/admin/
# Verify login works
# Check dashboard loads
# Clear browser cache first: Ctrl+Shift+R

# 7. Check Logs for Errors
sudo journalctl -u pbx -n 100 | grep -i error
```

#### Comprehensive Test Suite

```bash
# Run automated tests
cd /opt/pbx

# Full test suite (Python + JavaScript)
make test

# Python tests only
make test-python

# JavaScript tests only
make test-js

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Coverage report
make test-cov
# View report: open htmlcov/index.html
```

### 8.10 Update Best Practices

#### Update Schedule Recommendations

**Development Environment:**
- Update weekly or as needed
- Test new features immediately
- Keep dependencies up to date

**Staging Environment:**
- Update 1 week before production
- Run full test suite
- Verify all integrations work

**Production Environment:**
- Update monthly for features
- Update immediately for security patches
- Always test in staging first
- Schedule during maintenance windows

#### Security Update Priority

**Critical (Apply within 24 hours):**
- Remote code execution vulnerabilities
- Authentication bypass issues
- Database security patches

**High (Apply within 1 week):**
- Privilege escalation vulnerabilities
- SQL injection fixes
- XSS vulnerabilities

**Medium (Apply within 1 month):**
- DoS vulnerabilities
- Information disclosure
- Non-critical dependency updates

**Low (Apply during next maintenance window):**
- Minor bug fixes
- Performance improvements
- Feature enhancements

#### Update Documentation

```bash
# After each update, document:
# 1. What was updated
echo "$(date): Updated to version X.Y.Z" >> /opt/pbx/UPDATE_LOG.txt

# 2. Why (security, features, bug fixes)
echo "Reason: Security patch for CVE-XXXX-YYYY" >> /opt/pbx/UPDATE_LOG.txt

# 3. Any issues encountered
echo "Issues: None" >> /opt/pbx/UPDATE_LOG.txt

# 4. Post-update test results
echo "Tests: All passed" >> /opt/pbx/UPDATE_LOG.txt
echo "---" >> /opt/pbx/UPDATE_LOG.txt
```

### 8.11 Monitoring After Updates

#### First 24 Hours

```bash
# Monitor logs continuously
sudo journalctl -u pbx -f

# Watch for errors
sudo journalctl -u pbx -f | grep -i "error\|warning\|critical"

# Monitor resource usage
htop

# Check active calls
watch -n 5 'curl -sk https://localhost:8080/api/calls | jq'

# Database connections
watch -n 10 "sudo -u postgres psql -c 'SELECT count(*) FROM pg_stat_activity WHERE datname=''pbx_system'';'"
```

#### First Week

```bash
# Daily health check
cat > /opt/pbx/daily_health_check.sh << 'EOF'
#!/bin/bash
echo "=== Daily Health Check $(date) ===" >> /var/log/pbx_health.log

# Service status
systemctl is-active pbx >> /var/log/pbx_health.log 2>&1

# Error count in last 24h
journalctl -u pbx --since "24 hours ago" | grep -i error | wc -l >> /var/log/pbx_health.log

# Active calls
curl -sk https://localhost:8080/api/statistics >> /var/log/pbx_health.log 2>&1

echo "---" >> /var/log/pbx_health.log
EOF

chmod +x /opt/pbx/daily_health_check.sh

# Add to root's cron (append without overwriting existing entries)
(sudo crontab -l 2>/dev/null; echo "0 6 * * * /opt/pbx/daily_health_check.sh") | sudo crontab -
```

#### Performance Monitoring

```bash
# Compare before/after update
# CPU usage
top -b -n 1 | grep python

# Memory usage
ps aux | grep python | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Call quality metrics
curl -k https://localhost:8080/api/statistics

# Response time
time curl -k https://localhost:8080/api/status
```

### 8.12 Common Update Scenarios

#### Scenario 1: Security Patch for Python Package

```bash
# Example: Cryptography library has a CVE

# 1. Check current version
uv pip show cryptography

# 2. Stop service
sudo systemctl stop pbx

# 3. Update package
uv pip install --upgrade cryptography==46.0.5

# 4. Test import
python -c "from cryptography.fernet import Fernet; print('✓ OK')"

# 5. Restart and verify
sudo systemctl start pbx
curl -k https://localhost:8080/api/status

# 6. Monitor logs
sudo journalctl -u pbx -f
```

#### Scenario 2: New Feature Release

```bash
# 1. Review release notes
cd /opt/pbx
git fetch origin
git log HEAD..origin/main

# 2. Create backup
sudo /opt/pbx/scripts/backup_full.sh

# 3. Apply update during maintenance window
sudo systemctl stop pbx
git pull origin main

# 4. Update dependencies (if pyproject.toml changed)
make install-prod

# 5. Run migrations (if any)
alembic upgrade head

# 6. Update configuration (review CHANGELOG)
# Add new config options if required
nano config.yml

# 7. Restart and test
sudo systemctl start pbx
python scripts/smoke_tests.py

# 8. Monitor
sudo journalctl -u pbx -f
```

#### Scenario 3: Emergency Hotfix

```bash
# 1. Minimal downtime approach
cd /opt/pbx

# 2. Fetch hotfix
git fetch origin
git checkout hotfix/critical-fix

# 3. Quick test
python -m py_compile path/to/fixed/file.py

# 4. Apply
sudo systemctl restart pbx

# 5. Verify fix
# Test the specific issue that was fixed

# 6. Monitor
sudo journalctl -u pbx -f
```

---

## 9. Developer Guide

### 9.1 Architecture Overview

The PBX uses a modular architecture with Flask Blueprints, SQLAlchemy ORM, and TypeScript frontend modules.

**Backend Structure:**
```
PBX System
├── pbx/
│   ├── core/              - Core call handling logic
│   ├── sip/               - SIP protocol implementation
│   ├── rtp/               - RTP media handling
│   ├── features/          - Advanced features (VM, queues, etc.)
│   ├── integrations/      - External service integrations
│   ├── api/
│   │   ├── app.py         - Flask application factory
│   │   ├── routes/        - 21 Flask Blueprint modules
│   │   ├── schemas/       - Pydantic request/response validation
│   │   ├── openapi.py     - Auto-generated OpenAPI spec
│   │   └── errors.py      - Error handlers
│   ├── models/            - SQLAlchemy ORM models
│   │   ├── base.py        - Base model (id, created_at, updated_at)
│   │   ├── extension.py   - Extension model
│   │   ├── call_record.py - CDR model
│   │   ├── voicemail.py   - Voicemail model
│   │   └── registered_phone.py
│   └── utils/             - Utilities and helpers
├── admin/js/
│   ├── pages/             - 13 TypeScript page modules
│   ├── ui/                - UI components (tabs, notifications)
│   ├── client.ts          - API client
│   └── store.ts           - State management
├── alembic/               - Database migration scripts
├── Makefile               - Development workflow targets
└── pyproject.toml         - Dependencies and tool config
```

**Flask Blueprints (API Routes):**
The API is organized into 21 Blueprints registered in `pbx/api/app.py`:
`health`, `auth`, `extensions`, `calls`, `provisioning`, `phones`, `config`, `voicemail`, `webrtc`, `integrations`, `phone_book`, `paging`, `webhooks`, `emergency`, `security`, `qos`, `features`, `framework`, `static`, `license`, `compat`, `docs`

**Call Flow:**
1. SIP Server receives INVITE
2. PBX Core validates and routes call
3. RTP Handler establishes media session
4. Features layer adds capabilities (transfer, hold, etc.)
5. CDR logs call details via SQLAlchemy model

### 9.2 REST API Reference

**Interactive API Documentation:**
Full OpenAPI 3.0 documentation is auto-generated and available at:
- **Swagger UI:** `https://your-server:8080/api/docs/swagger`
- **OpenAPI JSON:** `https://your-server:8080/api/docs/openapi.json`

**Request Validation:**
API requests are validated using Pydantic schemas defined in `pbx/api/schemas/`:
- `auth.py` - Authentication request/response models
- `extensions.py` - Extension CRUD validation
- `provisioning.py` - Phone provisioning models
- `common.py` - Shared response models

**Key Endpoints:**

```bash
# System Status
GET /api/status
GET /api/health

# Extensions
GET    /api/extensions
GET    /api/extensions/1001
POST   /api/extensions
PUT    /api/extensions/1005
DELETE /api/extensions/1005

# Active Calls
GET    /api/calls
GET    /api/calls/{call_id}
POST   /api/calls/{call_id}/transfer
DELETE /api/calls/{call_id}

# Call Detail Records
GET /api/cdr?start_date=2025-01-01&end_date=2025-01-31
GET /api/statistics

# Configuration
GET /api/config
PUT /api/config

# Phone Provisioning
GET  /api/provisioning/devices
POST /api/provisioning/devices

# Voicemail
GET /api/voicemail/{extension}
```

**Adding a New API Endpoint:**

1. Create a route in `pbx/api/routes/your_feature.py`:
```python
from flask import Blueprint, jsonify
your_bp = Blueprint("your_feature", __name__)

@your_bp.route("/api/your-feature", methods=["GET"])
def get_feature():
    return jsonify({"status": "ok"})
```

2. Register the Blueprint in `pbx/api/app.py`:
```python
from pbx.api.routes.your_feature import your_bp
blueprints = [..., your_bp]
```

3. Add Pydantic schema validation in `pbx/api/schemas/` if needed.

### 9.3 Development Setup

**Prerequisites:**
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Node.js 18+ and npm

**Quick Start:**
```bash
# Install all dependencies (Python + dev tools)
make install

# Install frontend dependencies
npm install

# Install pre-commit hooks
make pre-commit-install
```

**Development Workflow:**
```bash
# Start backend + frontend with hot reload
make dev

# Backend only (Flask debug mode with auto-reload)
make dev-backend

# Frontend only (TypeScript dev server)
make dev-frontend

# Run production server (no auto-reload)
make run
```

**Code Quality:**
```bash
# Auto-format code (black + isort)
make format

# Check formatting without changes
make format-check

# Run all linters (pylint, flake8, mypy)
make lint

# Type checking only
make mypy
```

**Testing:**
```bash
# Run all tests (Python + JavaScript)
make test

# Python tests only
make test-python

# JavaScript tests only
make test-js

# Unit tests only (pytest -m unit)
make test-unit

# Integration tests only (pytest -m integration)
make test-integration

# Coverage report (HTML)
make test-cov
# View: open htmlcov/index.html
```

**Docker:**
```bash
make docker-build    # Build image
make docker-up       # Start services
make docker-down     # Stop services
make docker-logs     # View logs
make docker-shell    # Shell into container
```

### 9.4 Database Architecture

**SQLAlchemy Models** are defined in `pbx/models/`:
- `Base` - Common fields: `id`, `created_at`, `updated_at`
- `Extension` - User extensions
- `CallRecord` - Call detail records
- `Voicemail` - Voicemail messages
- `RegisteredPhone` - Phone registration tracking

**Migrations** are managed by Alembic:
```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history --indicate-current
```

### 9.5 Frontend Architecture

The admin panel uses **TypeScript ES modules** organized in `admin/js/`:

**Page Modules** (`admin/js/pages/`):
Each feature has a dedicated TypeScript module: `dashboard.ts`, `extensions.ts`, `calls.ts`, `voicemail.ts`, `phones.ts`, `provisioning.ts`, `config.ts`, `analytics.ts`, `emergency.ts`, `paging.ts`, `phone_book.ts`, `license.ts`, `security.ts`

**Shared Modules:**
- `admin/js/client.ts` - Centralized API client
- `admin/js/store.ts` - State management
- `admin/js/ui/tabs.ts` - Tab navigation
- `admin/js/ui/notifications.ts` - Toast notifications
- `admin/js/html.ts` - Safe HTML utilities

**Building:**
```bash
npm run dev      # Watch mode with hot reload
npm run build    # Production build
npm test         # Run Jest tests
```

### 9.6 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Commit message format
- Pull request process
- Testing requirements

**Quick Checklist:**
- [ ] Code follows PEP 8 style (enforced by `make format`)
- [ ] Type hints added to all functions
- [ ] Tests added/updated (`make test`)
- [ ] All linters pass (`make lint`)
- [ ] Type checking passes (`make mypy`)
- [ ] Database migrations created if models changed (`alembic revision --autogenerate`)

**Deprecation Notice:**
The old `pbx/api/rest_api.py` module is deprecated. Use Flask Blueprints in `pbx/api/routes/` instead. Do not add new endpoints to `rest_api.py`.

---

## 10. Appendices

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

**Document Version:** 1.2.0
**Last Updated:** 2026-02-13
**Copyright:** Warden VoIP PBX Project

