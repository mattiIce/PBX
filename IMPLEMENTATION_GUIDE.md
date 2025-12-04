# PBX Feature Implementation Guide

This document provides a comprehensive list of requirements to fully implement all stub/TODO features in the PBX system.

## Table of Contents
1. [Enterprise Integrations](#enterprise-integrations)
2. [Operator Console Features](#operator-console-features)
3. [Core PBX Features](#core-pbx-features)
4. [Infrastructure Requirements](#infrastructure-requirements)
5. [Development Tools](#development-tools)

---

## Enterprise Integrations

### 1. Zoom Integration (`pbx/integrations/zoom.py`)

**What You Need:**

#### A. Zoom Account & API Credentials
- **Zoom Account**: Business or Enterprise account
- **Zoom App Marketplace**: https://marketplace.zoom.us/
- **Create Server-to-Server OAuth App**:
  1. Go to https://marketplace.zoom.us/develop/create
  2. Select "Server-to-Server OAuth"
  3. Fill in app information
  4. Get credentials:
     - Account ID
     - Client ID
     - Client Secret

#### B. Required Scopes/Permissions
- `meeting:write:admin` - Create meetings
- `meeting:read:admin` - Read meeting details
- `phone:read:admin` - Read Zoom Phone data (if using Zoom Phone)
- `phone:write:admin` - Manage Zoom Phone (if using Zoom Phone)

#### C. Python Dependencies
```bash
pip install requests  # For API calls
pip install PyJWT  # For OAuth token generation
```

#### D. Configuration in `config.yml`
```yaml
integrations:
  zoom:
    enabled: true
    account_id: "YOUR_ACCOUNT_ID"
    client_id: "YOUR_CLIENT_ID"
    client_secret: "YOUR_CLIENT_SECRET"
    phone_enabled: true  # If using Zoom Phone
    api_base_url: "https://api.zoom.us/v2"
```

#### E. Implementation Steps
1. **OAuth Authentication**:
   - Implement token exchange: `POST https://zoom.us/oauth/token`
   - Handle token refresh (tokens expire)
   - Store access token securely

2. **Meeting Creation**:
   - API endpoint: `POST /users/me/meetings`
   - Request body: topic, start_time, duration, type
   - Parse response for join URL and meeting ID

3. **Zoom Phone Integration** (if enabled):
   - Configure SIP trunk between PBX and Zoom Phone
   - Set up number routing rules
   - Implement presence synchronization

#### F. Testing Requirements
- Zoom test account
- Test phone numbers for Zoom Phone
- Test meeting participants

**Estimated Implementation Time**: 2-3 days

---

### 2. Microsoft Outlook Integration (`pbx/integrations/outlook.py`)

**What You Need:**

#### A. Microsoft Azure Account & App Registration
- **Azure Portal**: https://portal.azure.com/
- **Register Application**:
  1. Go to "Azure Active Directory" → "App registrations"
  2. Click "New registration"
  3. Set name and supported account types
  4. Add redirect URI (e.g., `http://localhost:8080/callback`)
  5. Create client secret in "Certificates & secrets"

#### B. Required API Permissions (Microsoft Graph)
- `Calendars.Read` - Read user calendars
- `Calendars.ReadWrite` - Modify calendars
- `Contacts.Read` - Read contacts
- `User.Read` - Read user profile
- `Presence.Read` - Read presence status
- `MailboxSettings.Read` - Read automatic replies

#### C. Credentials Needed
- **Tenant ID**: From Azure AD overview
- **Client ID**: From app registration
- **Client Secret**: From certificates & secrets
- **Redirect URI**: Where OAuth callbacks go

#### D. Python Dependencies
```bash
pip install msal  # Microsoft Authentication Library
pip install requests
pip install python-dateutil  # For date parsing
```

#### E. Configuration in `config.yml`
```yaml
integrations:
  outlook:
    enabled: true
    tenant_id: "YOUR_TENANT_ID"
    client_id: "YOUR_CLIENT_ID"
    client_secret: "YOUR_CLIENT_SECRET"
    redirect_uri: "http://localhost:8080/callback"
    scopes:
      - "https://graph.microsoft.com/Calendars.Read"
      - "https://graph.microsoft.com/Calendars.ReadWrite"
      - "https://graph.microsoft.com/Contacts.Read"
      - "https://graph.microsoft.com/User.Read"
      - "https://graph.microsoft.com/Presence.Read"
```

#### F. Implementation Steps
1. **OAuth 2.0 Flow**:
   - Implement authorization code flow
   - Get authorization URL for user consent
   - Handle callback and exchange code for token
   - Refresh tokens before expiry

2. **Calendar Integration**:
   - API: `GET /me/calendar/calendarView`
   - Parse events and availability
   - Create events: `POST /me/events`
   - Update presence based on calendar status

3. **Contacts Integration**:
   - API: `GET /me/contacts`
   - Search: `GET /me/contacts?$filter=...`
   - Sync with PBX extension directory

4. **Automatic Replies**:
   - API: `GET /me/mailboxSettings/automaticRepliesSetting`
   - Update presence when out of office

#### G. Testing Requirements
- Microsoft 365 Business account
- Test users with calendar data
- Test contacts directory

**Estimated Implementation Time**: 3-4 days

---

### 3. Active Directory Integration (`pbx/integrations/active_directory.py`)

**What You Need:**

#### A. Active Directory Server
- **Domain Controller** with Active Directory Domain Services (AD DS)
- **LDAP Access** enabled
- **SSL/TLS Certificate** for secure LDAP (LDAPS) - recommended

#### B. Service Account
- **AD Service Account** with read permissions
  - Username: `svc-pbx@domain.local`
  - Password: Strong password
  - Permissions: Read all user attributes

#### C. Network Access
- **LDAP Port**: 389 (non-SSL) or 636 (SSL/LDAPS)
- **Firewall Rules**: Allow PBX server to connect to DC
- **DNS Resolution**: Ensure PBX can resolve domain controller

#### D. Python Dependencies
```bash
pip install ldap3  # LDAP client library
pip install pyasn1  # For LDAP schema parsing
```

#### E. Configuration in `config.yml`
```yaml
integrations:
  active_directory:
    enabled: true
    server: "ldaps://dc.domain.local:636"  # Or ldap://dc.domain.local:389
    base_dn: "DC=domain,DC=local"
    bind_dn: "CN=svc-pbx,OU=Service Accounts,DC=domain,DC=local"
    bind_password: "YOUR_SERVICE_ACCOUNT_PASSWORD"
    use_ssl: true
    user_search_base: "OU=Users,DC=domain,DC=local"
    group_search_base: "OU=Groups,DC=domain,DC=local"
    attributes:
      - "sAMAccountName"
      - "displayName"
      - "mail"
      - "telephoneNumber"
      - "memberOf"
      - "thumbnailPhoto"
```

#### F. Implementation Steps
1. **LDAP Connection**:
   - Use ldap3 library
   - Connect with SSL/TLS
   - Bind with service account credentials
   - Handle connection pooling

2. **User Authentication**:
   - Bind with user credentials to verify password
   - Return success/failure
   - Lock account after failed attempts

3. **User Synchronization**:
   - Query AD for users: `(objectClass=user)(!(objectClass=computer))`
   - Parse attributes (name, email, phone)
   - Create/update PBX extensions
   - Schedule periodic sync (e.g., hourly)

4. **Group Membership**:
   - Query `memberOf` attribute
   - Map AD groups to PBX permissions
   - Implement role-based access control

5. **User Search**:
   - Implement LDAP filter syntax
   - Search by name, email, phone
   - Return formatted results

6. **Photo Retrieval**:
   - Fetch `thumbnailPhoto` binary attribute
   - Convert to image format
   - Cache photos locally

#### G. Testing Requirements
- Test Active Directory environment
- Test users in different OUs
- Test group memberships
- Test photo attributes

#### H. Security Considerations
- **Always use LDAPS** (LDAP over SSL)
- Store service account password encrypted
- Implement connection timeouts
- Log authentication attempts
- Rate limit login attempts

**Estimated Implementation Time**: 4-5 days

---

### 4. Microsoft Teams Integration (`pbx/integrations/teams.py`)

**What You Need:**

#### A. Microsoft 365 Tenant & Azure Setup
- **Microsoft 365 Business/Enterprise** subscription
- **Azure AD App Registration** (same process as Outlook)
- **Teams Admin Center** access

#### B. Required API Permissions
- `Presence.ReadWrite` - Update user presence
- `OnlineMeetings.ReadWrite` - Create Teams meetings
- `Calls.Initiate.All` - Initiate calls
- `CallRecords.Read.All` - Read call records (optional)

#### C. SIP Direct Routing (for calling integration)
- **Session Border Controller (SBC)** or certified gateway
- **Public SIP domain** (e.g., sip.yourdomain.com)
- **TLS certificate** for SIP signaling
- **Configure in Teams Admin Center**:
  - Voice → Direct Routing
  - Add SBC FQDN
  - Create voice routing policies

#### D. Credentials & Configuration
```yaml
integrations:
  teams:
    enabled: true
    tenant_id: "YOUR_TENANT_ID"
    client_id: "YOUR_CLIENT_ID"
    client_secret: "YOUR_CLIENT_SECRET"
    sip_domain: "sip.yourdomain.com"
    sbc_fqdn: "sbc.yourdomain.com"
```

#### E. Python Dependencies
```bash
pip install msal
pip install requests
```

#### F. Implementation Steps
1. **OAuth Authentication**: Same as Outlook

2. **Presence Synchronization**:
   - API: `PATCH /users/{userId}/presence/setPresence`
   - Map PBX call states to Teams presence:
     - Available, Busy, DoNotDisturb, Away
   - Handle bidirectional sync

3. **Online Meetings**:
   - API: `POST /users/{userId}/onlineMeetings`
   - Create instant meetings from PBX
   - Get join URL and meeting ID

4. **SIP Direct Routing**:
   - Configure SIP trunk to Teams
   - Route calls via SIP INVITE to Teams SBC
   - Handle Teams-to-PBX calls
   - Implement SRTP for media encryption

#### G. Infrastructure Requirements
- **Session Border Controller** (e.g., AudioCodes, Ribbon, Oracle)
- **Public IP address** for SBC
- **DNS records**: SIP SRV records
- **Firewall rules**: 
  - SIP signaling (port 5061 TLS)
  - Media ports (UDP 49152-53247)

#### H. Testing Requirements
- Microsoft 365 test tenant
- SBC or gateway for testing
- Test Teams users
- Test phone numbers

**Estimated Implementation Time**: 5-7 days (plus SBC configuration)

---

## Operator Console Features

### 1. Call Interception (`pbx/features/operator_console.py`)

**What You Need:**

#### A. Implementation Requirements
- **Call State Management**: Track incoming calls before they ring
- **Privilege System**: Determine who can intercept calls
- **Notification System**: Alert operator of incoming calls

#### B. Python Dependencies
```bash
# No additional dependencies needed - uses existing PBX components
```

#### C. Implementation Steps
1. **Call Interception Logic**:
   - Hook into call routing before ringing destination
   - Pause call in "interceptable" state
   - Send notification to operator console
   - Wait for operator action (intercept or release)

2. **Operator Interface**:
   - REST API endpoints for call list
   - WebSocket for real-time notifications
   - Web UI for operator dashboard

3. **SIP Handling**:
   - Send new INVITE to operator when intercepting
   - Send CANCEL to original destination
   - Connect RTP streams

#### D. Configuration
```yaml
features:
  operator_console:
    enabled: true
    operator_extensions:
      - "1000"  # Extensions that can intercept
    intercept_timeout: 10  # Seconds before auto-release
```

**Estimated Implementation Time**: 2 days

---

### 2. Announced Transfer (`pbx/features/operator_console.py`)

**What You Need:**

#### A. Implementation Requirements
- **Hold functionality** (already implemented)
- **Three-way calling** capability
- **Audio mixing** for announcements

#### B. Implementation Steps
1. Place first party on hold (music on hold)
2. Call second party
3. Play announcement to second party
4. Options:
   - Complete transfer (disconnect first party)
   - Cancel transfer (reconnect to first party)
   - Conference all three parties

**Estimated Implementation Time**: 1-2 days

---

### 3. Paging System (`pbx/features/operator_console.py`)

**What You Need:**

#### A. Hardware/Infrastructure
- **Overhead Paging Speakers** with SIP/multicast support
- **Paging Gateway** (e.g., CyberData, Algo, Valcom)
  - Model examples:
    - CyberData SIP Paging Gateway
    - Algo 8301 SIP Paging Adapter
    - Valcom VIP-D8-IC

#### B. Software Requirements
- **Multicast Paging**:
  - Multicast address (e.g., 224.0.1.1:5004)
  - All speakers listen on same multicast group
  
- **OR SIP-based Paging**:
  - SIP URI for paging (e.g., sip:page-all@pbx.local)
  - Auto-answer configuration on paging devices

#### C. Network Requirements
- **Multicast routing** enabled on network switches
- **IGMP snooping** configured
- **QoS** for voice traffic

#### D. Implementation Steps
1. **Multicast Paging**:
   - Generate RTP stream to multicast address
   - Encode audio (G.711)
   - Send to all paging devices simultaneously

2. **SIP Paging**:
   - Send INVITE to paging group SIP URI
   - Devices auto-answer
   - Stream audio announcement

3. **Zones**:
   - Define paging zones (All, Warehouse, Office, etc.)
   - Map zones to multicast addresses or SIP URIs

#### E. Configuration
```yaml
features:
  paging:
    enabled: true
    method: "multicast"  # or "sip"
    zones:
      all:
        multicast_address: "224.0.1.1"
        multicast_port: 5004
      warehouse:
        multicast_address: "224.0.1.2"
        multicast_port: 5004
      office:
        multicast_address: "224.0.1.3"
        multicast_port: 5004
```

**Estimated Implementation Time**: 2-3 days (plus hardware setup)

---

### 4. VIP Caller Database (`pbx/features/operator_console.py`)

**What You Need:**

#### A. Database Backend
- **PostgreSQL** (recommended) or **MySQL**
- **SQLAlchemy** for ORM

#### B. Python Dependencies
```bash
pip install sqlalchemy
pip install psycopg2-binary  # For PostgreSQL
# OR
pip install pymysql  # For MySQL
```

#### C. Database Schema
```sql
CREATE TABLE vip_callers (
    id SERIAL PRIMARY KEY,
    caller_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255),
    priority_level INTEGER DEFAULT 1,  -- 1=VIP, 2=VVIP, 3=Executive
    notes TEXT,
    special_routing VARCHAR(50),  -- Extension or queue to route to
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_caller_id ON vip_callers(caller_id);
CREATE INDEX idx_priority ON vip_callers(priority_level);
```

#### D. Implementation Steps
1. **Database Connection**:
   - Configure SQLAlchemy connection pool
   - Create ORM models

2. **VIP Detection**:
   - Check caller ID against database on incoming call
   - Retrieve priority level and routing rules
   - Apply special treatment (skip queue, priority routing)

3. **Management API**:
   - Add/update/delete VIP entries
   - REST endpoints for CRUD operations
   - Web UI for management

4. **CRM Integration** (optional):
   - Query external CRM for VIP status
   - Sync VIP database with CRM
   - API webhooks for updates

#### E. Configuration
```yaml
database:
  vip_callers:
    host: "localhost"
    port: 5432
    database: "pbx_vip"
    username: "pbx_user"
    password: "YOUR_DB_PASSWORD"
    
features:
  vip_routing:
    enabled: true
    priority_levels:
      1:  # VIP
        skip_queue: true
        music_on_hold: "premium"
      2:  # VVIP
        direct_to_executive: true
        no_voicemail: true
      3:  # Executive
        immediate_escalation: true
```

**Estimated Implementation Time**: 2-3 days

---

## Core PBX Features

### 1. Voicemail IVR with DTMF (`pbx/core/pbx.py`)

**What You Need:**

#### A. Python Dependencies
```bash
pip install scipy  # For DTMF detection
pip install numpy  # For signal processing
```

#### B. Audio Prompts
Create or record WAV files (G.711 μ-law, 8kHz, mono):
- `welcome.wav` - "Welcome to your voicemail..."
- `enter_pin.wav` - "Please enter your PIN followed by pound"
- `invalid_pin.wav` - "Invalid PIN, please try again"
- `main_menu.wav` - "You have X new messages. Press 1 to listen..."
- `message_playback.wav` - "Message from..."
- `message_menu.wav` - "Press 1 to replay, 2 to delete..."
- `goodbye.wav` - "Goodbye"
- `beep.wav` - Recording beep

Tools for creating prompts:
- **Text-to-Speech**: AWS Polly, Google Cloud TTS, Azure TTS
- **Recording**: Audacity (free) or professional voice talent
- **Format conversion**: `ffmpeg -i YOUR_AUDIO_FILE.wav -ar 8000 -ac 1 -acodec pcm_mulaw output.wav`

#### C. Implementation Steps
1. **DTMF Detection**:
   - Implement Goertzel algorithm for tone detection
   - Detect dual-tone frequencies (697-1633 Hz)
   - Parse digits 0-9, *, #

2. **IVR State Machine**:
   - States: Welcome → PIN Entry → Main Menu → Message Playback → etc.
   - Handle transitions based on DTMF input
   - Timeout handling (return to previous menu)

3. **PIN Verification**:
   - Collect 4-digit PIN
   - Verify against stored PIN
   - 3 attempts before disconnect

4. **Message Navigation**:
   - Play message count
   - Play messages (first unread, then read)
   - Options: replay, delete, save, skip

#### D. DTMF Detection Code Example
```python
def detect_dtmf_goertzel(samples, sample_rate=8000):
    """Detect DTMF tones using Goertzel algorithm"""
    dtmf_freqs = {
        '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
        '4': (770, 1209), '5': (770, 1336), '6': (770, 1477),
        '7': (852, 1209), '8': (852, 1336), '9': (852, 1477),
        '*': (941, 1209), '0': (941, 1336), '#': (941, 1477)
    }
    # Implementation of Goertzel algorithm
    # Return detected digit or None
```

#### E. Configuration
```yaml
voicemail:
  ivr:
    enabled: true
    prompts_path: "voicemail/prompts"
    pin_attempts: 3
    menu_timeout: 5  # Seconds
    inter_digit_timeout: 3  # Seconds
```

**Estimated Implementation Time**: 3-4 days

---

## Infrastructure Requirements

### 1. Session Border Controller (SBC)
**For external SIP trunking and Teams integration**

#### Options:
- **Software SBCs**:
  - Kamailio (open source)
  - FreeSWITCH (open source)
  - Asterisk (open source)
  
- **Hardware SBCs**:
  - AudioCodes Mediant series ($2,000 - $50,000)
  - Ribbon SBC 1000/2000 ($5,000 - $100,000)
  - Oracle Acme Packet ($50,000+)

#### What SBC Provides:
- NAT traversal
- Security (topology hiding, DoS protection)
- Protocol normalization
- Media anchoring
- Encryption (TLS, SRTP)
- Call admission control

---

### 2. Database Server
**For VIP callers, CDR, user management**

#### Recommended: PostgreSQL
```bash
# Installation
sudo apt install postgresql postgresql-contrib

# Configuration
sudo -u postgres psql
CREATE DATABASE pbx_system;
CREATE USER pbx_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;
```

#### Alternative: MySQL
```bash
sudo apt install mysql-server
sudo mysql_secure_installation
```

---

### 3. SMTP Server
**For voicemail-to-email (already configured)**

#### Options:
- **Gmail** (for testing)
- **SendGrid** (API-based)
- **Amazon SES**
- **Office 365 SMTP**
- **Local Postfix server**

Already implemented - just needs valid credentials in config.yml

---

### 4. Network Infrastructure

#### Required:
- **Static IP addresses** for PBX servers
- **DNS records**:
  - A records for servers
  - SRV records for SIP (`_sip._udp.domain.com`)
- **Firewall rules**:
  - SIP: UDP 5060 (or TCP 5061 for TLS)
  - RTP: UDP 10000-20000 (or configured range)
- **QoS/DSCP** markings for voice traffic (EF/46)
- **VLAN** for voice traffic (optional but recommended)

---

## Development Tools

### 1. SIP Testing Tools
```bash
# SIPp - SIP protocol tester
sudo apt install sipp

# Test registration
sipp -sn uac -s 1001 -r 1 -rp 1000 pbx_ip:5060

# Wireshark - Packet capture
sudo apt install wireshark
```

### 2. Audio Tools
```bash
# FFmpeg - Audio conversion
sudo apt install ffmpeg

# Convert to G.711 μ-law (replace YOUR_AUDIO_FILE.wav with your actual audio file)
ffmpeg -i YOUR_AUDIO_FILE.wav -ar 8000 -ac 1 -acodec pcm_mulaw output.wav

# SoX - Audio processing
sudo apt install sox
```

### 3. Load Testing
```bash
# SIPp scenarios
sipp -sf scenario.xml -r 10 -l 100 pbx_ip
```

---

## Cost Estimates

### Software/Services (Annual)
| Item | Cost Range |
|------|------------|
| Zoom Business Account | $150 - $250 per user |
| Microsoft 365 Business | $150 - $240 per user |
| Azure AD (included with M365) | $0 |
| PostgreSQL Database | $0 (open source) |
| SSL Certificates | $0 - $200 (Let's Encrypt free) |

### Hardware (One-time)
| Item | Cost Range |
|------|------------|
| Paging Gateway | $300 - $1,500 |
| Overhead Speakers | $100 - $400 each |
| Session Border Controller | $2,000 - $50,000 |
| Server Hardware | $1,000 - $10,000 |

### Development Time
| Feature Category | Estimated Days |
|-----------------|----------------|
| Zoom Integration | 2-3 days |
| Outlook Integration | 3-4 days |
| Active Directory | 4-5 days |
| Teams Integration | 5-7 days |
| Operator Console | 5-6 days |
| Voicemail IVR | 3-4 days |
| **Total** | **22-33 days** |

---

## Quick Start Priorities

If you want to implement features incrementally, here's the recommended order:

### Phase 1: Core Features (1-2 weeks)
1. ✅ Call Transfer (DONE)
2. ✅ WAV File Playback (DONE)
3. Voicemail IVR with DTMF
4. Database backend for VIP callers

### Phase 2: Enterprise Integration (2-3 weeks)
1. Active Directory (most companies have this)
2. Outlook Calendar Integration
3. Zoom or Teams (pick one based on company usage)

### Phase 3: Advanced Features (1-2 weeks)
1. Operator Console features
2. Paging system (if hardware available)
3. Full Teams/Zoom integration

---

## Support & Resources

### Documentation Links
- **Zoom API**: https://marketplace.zoom.us/docs/api-reference/
- **Microsoft Graph**: https://docs.microsoft.com/en-us/graph/
- **ldap3 (Python)**: https://ldap3.readthedocs.io/
- **SIP RFC 3261**: https://www.rfc-editor.org/rfc/rfc3261

### Community
- **VoIP Info Wiki**: https://www.voip-info.org/
- **Asterisk Community**: https://community.asterisk.org/
- **Stack Overflow**: Tag `sip`, `voip`, `pbx`

### Testing Services
- **SIP Test Accounts**: Most VoIP providers offer free test accounts
- **Azure Free Trial**: $200 credit for 30 days
- **Microsoft 365 Developer**: Free E5 subscription for 90 days

---

## Conclusion

All stub features can be fully implemented with the resources listed above. The main requirements are:

1. **External API Accounts**: Zoom, Microsoft 365, Azure
2. **Infrastructure**: Database server, network configuration
3. **Hardware** (optional): Paging equipment, SBC
4. **Development Time**: 3-5 weeks for full implementation
5. **Budget**: $500-$5,000 depending on hardware choices

For questions or assistance, refer to the documentation links or community resources listed above.
