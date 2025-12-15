# Open Source Integration Guide

## Overview

This guide documents all free and open-source integrations available for the PBX system. All components listed are either free, open-source, or self-hosted solutions that don't require proprietary licenses or paid APIs.

**Philosophy**: This PBX system prioritizes free and open-source components. Where proprietary alternatives exist, we provide open-source alternatives first.

## 🆓 Core Open-Source Components

### Speech Recognition & Transcription

#### **Vosk** (Primary - FREE, Offline)
- **Status**: ✅ Fully Integrated
- **License**: Apache 2.0
- **Cost**: Free
- **Features**: Offline speech recognition, 20+ languages
- **Usage**: Voicemail transcription, speech analytics
- **Setup**:
  ```bash
  pip install vosk
  
  # Download model (one-time)
  wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
  unzip vosk-model-small-en-us-0.15.zip -d models/
  ```
- **Configuration**:
  ```yaml
  features:
    voicemail_transcription:
      enabled: true
      provider: vosk  # Free, offline
      vosk_model_path: models/vosk-model-small-en-us-0.15
  ```

#### **Whisper.cpp** (Alternative - FREE, Offline)
- **License**: MIT
- **Cost**: Free
- **Features**: OpenAI Whisper models optimized for CPU
- **Setup**:
  ```bash
  git clone https://github.com/ggerganov/whisper.cpp
  cd whisper.cpp
  make
  # Download base model
  bash ./models/download-ggml-model.sh base.en
  ```

### Directory Services & Authentication

#### **OpenLDAP** (Free Alternative to Active Directory)
- **Status**: ⚠️ Compatible (Use existing AD integration code)
- **License**: OpenLDAP Public License
- **Cost**: Free
- **Features**: LDAP directory, authentication, SSO
- **Setup**:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install slapd ldap-utils
  
  # Configure base DN
  sudo dpkg-reconfigure slapd
  ```
- **Configuration** (Use existing AD integration):
  ```yaml
  integrations:
    active_directory:
      enabled: true
      ldap_server: "ldap://localhost:389"
      base_dn: "dc=company,dc=com"
      bind_dn: "cn=admin,dc=company,dc=com"
      bind_password: "your-password"
  ```

#### **FreeIPA** (Alternative - Enterprise Identity Management)
- **License**: GPL
- **Cost**: Free
- **Features**: LDAP, Kerberos, DNS, CA
- **Website**: https://www.freeipa.org/

#### **Keycloak** (Alternative - Modern SSO/OAuth)
- **License**: Apache 2.0
- **Cost**: Free
- **Features**: OAuth2, SAML, OpenID Connect
- **Website**: https://www.keycloak.org/

### Video Conferencing

#### **Jitsi Meet** (Free Alternative to Zoom/Teams)
- **Status**: 🔧 Integration Needed
- **License**: Apache 2.0
- **Cost**: Free
- **Features**: Video calls, screen sharing, recording
- **Self-Hosted**: Yes
- **Setup**:
  ```bash
  # Quick install on Ubuntu
  wget -qO - https://download.jitsi.org/jitsi-key.gpg.key | sudo apt-key add -
  sudo sh -c "echo 'deb https://download.jitsi.org stable/' > /etc/apt/sources.list.d/jitsi-stable.list"
  sudo apt-get update
  sudo apt-get install jitsi-meet
  ```
- **Integration**: Create meetings via REST API

#### **BigBlueButton** (Alternative - Education Focus)
- **License**: LGPL
- **Cost**: Free
- **Features**: Breakout rooms, whiteboard, recording
- **Website**: https://bigbluebutton.org/

### Team Messaging & Collaboration

#### **Matrix (Element)** (Free Alternative to Slack/Teams Chat)
- **Status**: 🔧 Integration Needed
- **License**: Apache 2.0
- **Cost**: Free
- **Features**: Federated messaging, E2E encryption, file sharing
- **Self-Hosted**: Yes (Synapse server)
- **Setup**:
  ```bash
  # Install Synapse (Matrix homeserver)
  pip install matrix-synapse
  python -m synapse.app.homeserver \
    --server-name my.domain.name \
    --config-path homeserver.yaml \
    --generate-config \
    --report-stats=yes
  ```
- **Client**: Element (web, desktop, mobile)

#### **Rocket.Chat** (Alternative)
- **License**: MIT
- **Cost**: Free (Community Edition)
- **Features**: Team chat, video calls, file sharing
- **Website**: https://rocket.chat/

#### **Mattermost** (Alternative)
- **License**: MIT
- **Cost**: Free (Team Edition)
- **Features**: Slack-like interface, integrations
- **Website**: https://mattermost.com/

### CRM (Customer Relationship Management)

#### **EspoCRM** (Free Alternative to Salesforce/HubSpot)
- **Status**: 🔧 Integration Needed
- **License**: GPL v3
- **Cost**: Free
- **Features**: Contacts, deals, cases, workflow automation
- **Self-Hosted**: Yes
- **API**: REST API available
- **Setup**:
  ```bash
  # Download and extract
  wget https://www.espocrm.com/downloads/EspoCRM-7.x.x.zip
  unzip EspoCRM-7.x.x.zip -d /var/www/espocrm
  
  # Configure web server and database
  ```

#### **SuiteCRM** (Alternative - Salesforce Fork)
- **License**: AGPLv3
- **Cost**: Free
- **Features**: Full CRM suite, SugarCRM fork
- **API**: REST API, CalDAV, CardDAV
- **Website**: https://suitecrm.com/

#### **Odoo** (Alternative - Full ERP)
- **License**: LGPL (Community)
- **Cost**: Free (Community Edition)
- **Features**: CRM, Sales, Inventory, Accounting
- **Website**: https://www.odoo.com/

### Helpdesk & Ticketing

#### **osTicket** (Free Alternative to Zendesk)
- **Status**: 🔧 Integration Needed
- **License**: GPL v2
- **Cost**: Free
- **Features**: Ticket management, SLA, email integration
- **Self-Hosted**: Yes
- **API**: REST API available
- **Setup**:
  ```bash
  git clone https://github.com/osTicket/osTicket
  cd osTicket
  php manage.php deploy --setup /var/www/osticket
  ```

#### **OTRS** (Alternative - Enterprise Features)
- **License**: GPL v3
- **Cost**: Free (Community Edition)
- **Features**: ITIL compliant, CMDB, change management
- **Website**: https://otrs.com/

#### **FreeScout** (Alternative - Simple)
- **License**: AGPL v3
- **Cost**: Free
- **Features**: Email-based ticketing, knowledge base
- **Website**: https://freescout.net/

### Business Intelligence & Analytics

#### **Metabase** (Free Alternative to Power BI/Tableau)
- **Status**: 🔧 Integration Needed
- **License**: AGPL v3
- **Cost**: Free
- **Features**: SQL queries, dashboards, visualizations
- **Self-Hosted**: Yes
- **Setup**:
  ```bash
  # Docker deployment
  docker run -d -p 3000:3000 \
    -v ~/metabase-data:/metabase-data \
    -e "MB_DB_FILE=/metabase-data/metabase.db" \
    metabase/metabase
  ```
- **Integration**: Connect to PBX PostgreSQL database

#### **Apache Superset** (Alternative - Advanced)
- **License**: Apache 2.0
- **Cost**: Free
- **Features**: Advanced visualizations, SQL Lab, dashboards
- **Website**: https://superset.apache.org/

#### **Grafana** (Alternative - Time Series Focus)
- **License**: AGPL v3
- **Cost**: Free
- **Features**: Real-time dashboards, alerting, PostgreSQL support
- **Website**: https://grafana.com/

### Email Services

#### **Postfix + Dovecot** (Self-Hosted Email)
- **Status**: ✅ Compatible (SMTP)
- **License**: IBM Public License / MIT & LGPL
- **Cost**: Free
- **Features**: Full email server, IMAP/SMTP
- **Setup**:
  ```bash
  sudo apt-get install postfix dovecot-core dovecot-imapd
  ```

#### **Mail-in-a-Box** (Alternative - Turnkey Solution)
- **License**: CC0 (Public Domain)
- **Cost**: Free
- **Features**: Complete email server in one package
- **Website**: https://mailinabox.email/

### File Storage & Sharing

#### **Nextcloud** (Free Alternative to OneDrive/Dropbox)
- **Status**: 🔧 Integration Needed
- **License**: AGPL v3
- **Cost**: Free
- **Features**: File sync, sharing, calendars, contacts
- **Self-Hosted**: Yes
- **API**: WebDAV, CalDAV, CardDAV, REST
- **Setup**:
  ```bash
  # Snap installation
  sudo snap install nextcloud
  ```

#### **Seafile** (Alternative - Performance Focus)
- **License**: GPL v2/v3
- **Cost**: Free (Community Edition)
- **Features**: Fast file sync, encryption, versioning
- **Website**: https://www.seafile.com/

### Calendar & Contacts

#### **Radicale** (Lightweight CalDAV/CardDAV)
- **License**: GPL v3
- **Cost**: Free
- **Features**: Calendar, contacts sync
- **Setup**:
  ```bash
  pip3 install radicale
  python3 -m radicale --config "" --storage-filesystem-folder=~/.radicale/collections
  ```

#### **Baikal** (Alternative)
- **License**: GPL v3
- **Cost**: Free
- **Features**: CalDAV/CardDAV server
- **Website**: https://sabre.io/baikal/

### Monitoring & Alerting

#### **Prometheus + Alertmanager** (Free Monitoring)
- **License**: Apache 2.0
- **Cost**: Free
- **Features**: Metrics collection, alerting, time series DB
- **Setup**:
  ```bash
  # Download Prometheus
  wget https://github.com/prometheus/prometheus/releases/download/v*/prometheus-*-linux-amd64.tar.gz
  tar xvfz prometheus-*.tar.gz
  cd prometheus-*
  ./prometheus --config.file=prometheus.yml
  ```

#### **Nagios** (Alternative - Traditional)
- **License**: GPL v2
- **Cost**: Free (Core)
- **Features**: Infrastructure monitoring, alerting
- **Website**: https://www.nagios.org/

### VoIP & Telephony

#### **FreeSWITCH** (SIP Server Alternative)
- **License**: MPL 1.1
- **Cost**: Free
- **Features**: Full telephony platform, SIP, WebRTC
- **Website**: https://freeswitch.com/

#### **Asterisk** (Alternative)
- **License**: GPL v2
- **Cost**: Free
- **Features**: PBX, IVR, voicemail, conferencing
- **Website**: https://www.asterisk.org/

#### **Kamailio** (SIP Proxy/Load Balancer)
- **License**: GPL v2
- **Cost**: Free
- **Features**: SIP routing, load balancing, presence
- **Website**: https://www.kamailio.org/

### SIP Trunk Providers (Free Tiers)

#### **Twilio** (Freemium)
- **Free Tier**: Trial credits ($15)
- **Pay-as-you-go**: After trial
- **Features**: SIP trunking, SMS, voice

#### **Bandwidth.com** (Freemium)
- **Free Tier**: Developer sandbox
- **Pay-as-you-go**: Production use
- **Features**: SIP, messaging, 911

#### **VoIP.ms** (Low-Cost)
- **Free Tier**: No (but very low cost)
- **Pricing**: Pay-per-minute ($0.01/min)
- **Features**: DID numbers, SIP trunking, 911

## 🔧 Integration Implementation Guide

### Adding a New Open-Source Integration

1. **Create Integration Module**
   ```python
   # pbx/integrations/espocrm.py
   class EspoCRMIntegration:
       def __init__(self, config):
           self.api_url = config.get('integrations.espocrm.api_url')
           self.api_key = config.get('integrations.espocrm.api_key')
       
       def create_contact(self, name, phone):
           # Implementation
           pass
   ```

2. **Add Configuration Schema**
   ```yaml
   integrations:
     espocrm:
       enabled: true
       api_url: "https://your-espocrm.com/api/v1"
       api_key: "your-api-key"
       auto_create_contacts: true
   ```

3. **Create REST API Endpoints**
   ```python
   # In pbx/api/rest_api.py
   @app.route('/api/integrations/espocrm/contacts', methods=['GET'])
   def get_espocrm_contacts():
       # Implementation
       pass
   ```

4. **Add Admin Panel UI**
   ```html
   <!-- In admin/index.html -->
   <div id="espocrm-integration">
       <h3>EspoCRM Integration</h3>
       <!-- Configuration form -->
   </div>
   ```

### Integration Architecture

```
┌─────────────────────────────────────────────────┐
│              PBX System                         │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │     Integration Manager                   │ │
│  │  (pbx/integrations/__init__.py)          │ │
│  └─────────┬─────────────────────────────────┘ │
│            │                                     │
│  ┌─────────▼─────────┐  ┌──────────────────┐  │
│  │  OpenLDAP        │  │  Jitsi Meet      │  │
│  │  (Directory)     │  │  (Video Calls)   │  │
│  └──────────────────┘  └──────────────────┘  │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Matrix/Element  │  │  EspoCRM         │  │
│  │  (Team Chat)     │  │  (CRM)           │  │
│  └──────────────────┘  └──────────────────┘  │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │  osTicket        │  │  Metabase        │  │
│  │  (Helpdesk)      │  │  (Analytics)     │  │
│  └──────────────────┘  └──────────────────┘  │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Nextcloud       │  │  Vosk/Whisper    │  │
│  │  (File Storage)  │  │  (Speech-to-Text)│  │
│  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────┘
```

## 📋 Migration from Proprietary Services

### From Zoom to Jitsi Meet

**Before** (Proprietary - Requires License):
```yaml
integrations:
  zoom:
    enabled: true
    account_id: "xxx"
    client_id: "xxx"
    client_secret: "xxx"
    phone_enabled: true
```

**After** (Open Source - Free):
```yaml
integrations:
  jitsi:
    enabled: true
    server_url: "https://meet.jit.si"  # Or self-hosted
    # OR self-hosted:
    # server_url: "https://jitsi.yourcompany.com"
    auto_create_rooms: true
```

### From Salesforce to EspoCRM

**Before** (Proprietary - Paid):
```yaml
integrations:
  salesforce:
    enabled: true
    instance_url: "https://yourcompany.salesforce.com"
    client_id: "xxx"
    client_secret: "xxx"
```

**After** (Open Source - Free):
```yaml
integrations:
  espocrm:
    enabled: true
    api_url: "https://crm.yourcompany.com/api/v1"
    api_key: "your-api-key"
    auto_create_contacts: true
    screen_pop: true
```

### From Power BI to Metabase

**Before** (Proprietary - Paid):
```yaml
integrations:
  powerbi:
    enabled: true
    tenant_id: "xxx"
    client_id: "xxx"
    workspace_id: "xxx"
```

**After** (Open Source - Free):
```yaml
integrations:
  metabase:
    enabled: true
    server_url: "https://analytics.yourcompany.com"
    database_id: 1  # PBX PostgreSQL database
    auto_create_dashboards: true
```

## 🚀 Quick Start with All Open-Source Stack

### Minimal Open-Source Deployment

```bash
# 1. PBX System
cd /path/to/pbx
pip install -r requirements.txt

# 2. Vosk for speech recognition (FREE)
pip install vosk
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip -d models/

# 3. OpenLDAP for directory (FREE)
sudo apt-get install slapd ldap-utils

# 4. Jitsi Meet for video (FREE)
# See https://jitsi.github.io/handbook/docs/devops-guide/devops-guide-quickstart

# 5. Metabase for analytics (FREE)
docker run -d -p 3000:3000 metabase/metabase

# 6. Matrix for team chat (FREE)
pip install matrix-synapse
python -m synapse.app.homeserver --generate-config

# 7. Configure PBX
cp config.yml.example config.yml
nano config.yml  # Enable open-source integrations
```

### Configuration Example (All Open-Source)

```yaml
# config.yml - 100% Open Source Configuration

server:
  sip_port: 5060
  rtp_port_range: [10000, 20000]

database:
  type: postgresql  # Free
  host: localhost
  port: 5432
  name: pbx_system
  user: pbx_user

integrations:
  # Directory Services (OpenLDAP)
  active_directory:
    enabled: true
    ldap_server: "ldap://localhost:389"
    base_dn: "dc=company,dc=com"
  
  # Video Conferencing (Jitsi)
  jitsi:
    enabled: true
    server_url: "https://meet.jit.si"
  
  # Team Messaging (Matrix)
  matrix:
    enabled: true
    homeserver_url: "https://matrix.yourcompany.com"
  
  # CRM (EspoCRM)
  espocrm:
    enabled: true
    api_url: "https://crm.yourcompany.com/api/v1"
  
  # Analytics (Metabase)
  metabase:
    enabled: true
    server_url: "http://localhost:3000"

features:
  # Speech Recognition (Vosk)
  voicemail_transcription:
    enabled: true
    provider: vosk
    vosk_model_path: models/vosk-model-small-en-us-0.15
  
  # Email (Postfix)
  email:
    smtp_host: localhost
    smtp_port: 25
```

## 📊 Cost Comparison

| Feature | Proprietary Option | Cost/Year | Open Source Alternative | Cost |
|---------|-------------------|-----------|------------------------|------|
| PBX Core | 3CX, RingCentral | $1,500+ | This PBX System | $0 |
| Video Conferencing | Zoom | $150-300/user | Jitsi Meet | $0 |
| Team Messaging | Slack, Teams | $96-240/user | Matrix/Rocket.Chat | $0 |
| CRM | Salesforce | $1,200+/user | EspoCRM/SuiteCRM | $0 |
| Helpdesk | Zendesk | $600+/agent | osTicket/OTRS | $0 |
| Analytics | Power BI | $120/user | Metabase/Grafana | $0 |
| File Storage | OneDrive | $60-240/user | Nextcloud | $0 |
| Speech-to-Text | Google Cloud | $0.006/15s | Vosk/Whisper | $0 |
| **Total** | | **$3,726+/user/year** | | **$0** |

**Note**: Hardware/hosting costs not included. Self-hosted solutions require server infrastructure.

## 🔒 Security Considerations

All open-source integrations should follow these security practices:

1. **Use HTTPS/TLS** for all external API connections
2. **Encrypt credentials** in configuration files
3. **Implement rate limiting** for API endpoints
4. **Use API keys** instead of username/password where possible
5. **Regular updates** of open-source components
6. **Audit logs** for all integration activities
7. **Network isolation** for sensitive integrations
8. **Firewall rules** to restrict access

## 📚 Additional Resources

### Documentation
- Jitsi Meet: https://jitsi.github.io/handbook/
- Matrix/Synapse: https://matrix.org/docs/guides/
- EspoCRM: https://docs.espocrm.com/
- Metabase: https://www.metabase.com/docs/
- Vosk: https://alphacephei.com/vosk/

### Communities
- Jitsi Community: https://community.jitsi.org/
- Matrix Community: https://matrix.to/#/#matrix:matrix.org
- EspoCRM Forum: https://forum.espocrm.com/
- Open Source PBX: https://www.voip-info.org/

## 🎯 Summary

This PBX system can be deployed with **100% free and open-source components**:

✅ **Core PBX**: Python-based, open-source  
✅ **Speech Recognition**: Vosk (offline, free)  
✅ **Directory**: OpenLDAP (free)  
✅ **Video Calls**: Jitsi Meet (free)  
✅ **Team Chat**: Matrix (free)  
✅ **CRM**: EspoCRM (free)  
✅ **Helpdesk**: osTicket (free)  
✅ **Analytics**: Metabase (free)  
✅ **File Storage**: Nextcloud (free)  
✅ **Database**: PostgreSQL (free)  

**Total Cost**: $0 in licensing fees (hosting infrastructure not included)

---

**Last Updated**: December 15, 2025  
**Maintained By**: PBX Development Team
