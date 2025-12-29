<div align="center">
  <img src="Warden VoIP Logo.png" alt="Warden VoIP" width="200"/>
  
  # Warden VoIP
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
  [![Tests](https://github.com/mattiIce/PBX/workflows/Tests/badge.svg)](https://github.com/mattiIce/PBX/actions)
  [![Code Quality](https://github.com/mattiIce/PBX/workflows/Code%20Quality/badge.svg)](https://github.com/mattiIce/PBX/actions)
  [![codecov](https://codecov.io/gh/mattiIce/PBX/branch/main/graph/badge.svg)](https://codecov.io/gh/mattiIce/PBX)
  
  **A comprehensive, feature-rich Private Branch Exchange (PBX) and VoIP system built from scratch in Python**
</div>

---

## 📚 Documentation

> **📖 Complete Guide**: See **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** for comprehensive documentation covering installation, deployment, features, integrations, security, troubleshooting, and API reference - all in one place!

> **📊 For Executives**: See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) for business overview, ROI analysis, and strategic recommendations.

> **🗂️ Documentation Index**: See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for a full navigation guide.

## 🌟 Features

### Core PBX Features
- **SIP Protocol Support** - Full Session Initiation Protocol implementation
- **RTP Media Handling** - Real-time Protocol for audio streaming
- **Extension Management** - User registration and authentication
- **Call Routing** - Intelligent call routing based on dialplan rules
- **Call Management** - Hold, resume, transfer, and forward calls

### Advanced Call Features
- **Auto Attendant (IVR)** - Automated call answering with menu options for routing calls
- **Call Recording** - Record calls for compliance and quality assurance
- **Call Queues (ACD)** - Automatic Call Distribution with multiple strategies
- **Conference Calling** - Multi-party conference rooms
- **Call Parking** - Park and retrieve calls from any extension
- **Call Transfer** - Blind and attended transfers
- **Music on Hold** - Customizable hold music
- **Voicemail System** - Full-featured voicemail with custom greeting recording, email notifications, and auto-routing

### Modern VOIP Features
- **Presence System** - Real-time user availability status
- **SIP Trunk Support** - Connect to external SIP providers
- **Phone Provisioning** - Auto-configuration for multiple IP phone brands (Zultys, Yealink, Polycom, Cisco, Grandstream) with customizable templates
- **Phone Registration Tracking** - Automatic tracking of registered phones with MAC addresses and IP addresses
- **SIP Send Line & Send MAC** - Caller ID headers (P-Asserted-Identity, Remote-Party-ID) and device MAC tracking for enhanced call identification (see [docs/reference/SIP_SEND_LINE_MAC_GUIDE.md](docs/reference/SIP_SEND_LINE_MAC_GUIDE.md))
- **Phone Book System** - Centralized directory with AD sync, pushed to IP phones in multiple formats (Yealink, Cisco XML)
- **Paging System** - Full overhead paging support with SIP/RTP integration (hardware-ready)
- **Webhook System** - Event-driven integrations with HMAC signature support for real-time notifications
- **CDR (Call Detail Records)** - Comprehensive call logging and statistics
- **REST API** - HTTPS/HTTP API for integration and management
- **Web Admin Panel** - Modern browser-based admin interface for managing extensions, users, and configuration
- **Multi-codec Support** - G.711 (PCMU/PCMA), G.722 (HD), G.729, G.726, Opus, iLBC, Speex and more
- **DTMF Detection** - Goertzel algorithm for interactive voice menus

### Operator Console Features
- **VIP Caller Database** - Priority handling for important callers
- **Call Screening** - Intercept and screen calls before transfer
- **Announced Transfers** - Announce caller before completing transfer
- **Park and Page** - Park calls and page via multiple methods
- **BLF Monitoring** - Real-time extension busy lamp field status
- **Company Directory** - Quick lookup with search functionality

### 🆓 Free & Open Source Integrations
**Zero licensing costs - 100% free alternatives to expensive proprietary services**
- **Jitsi Meet** - Video conferencing (Zoom alternative) - ✅ Integrated
- **Matrix/Element** - Team messaging (Slack/Teams alternative) - ✅ Integrated  
- **EspoCRM** - CRM with screen pop & call logging (Salesforce alternative) - ✅ Integrated
- **Vosk** - Offline speech recognition for transcription - ✅ Integrated
- **OpenLDAP** - Directory services (Active Directory compatible) - ✅ Compatible

**📖 Documentation:**
- **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** - 📘 **Complete comprehensive documentation (all-in-one)**
- **[docs/reference/](docs/reference/)** - Technical reference documentation

**💰 Cost Savings**: $0/year vs $3,726+/user/year for proprietary stack

### Enterprise Integrations (Optional - Proprietary)
- **Zoom Integration** - Create instant or scheduled Zoom meetings from PBX
- **Active Directory** - LDAP authentication and user directory sync
- **Microsoft Outlook** - Calendar sync, availability, and contact integration
- **Microsoft Teams** - Presence sync and meeting escalation

### Security & Compliance
- **HTTPS/SSL Support** - Secure API communication with TLS 1.2+ (see [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md#62-ssltls-configuration))
- **In-House CA Integration** - Automatic certificate request from enterprise Certificate Authority
- **FIPS 140-2 Compliant Encryption** - Government-grade security
- **TLS/SIPS** - Encrypted SIP signaling
- **SRTP** - Encrypted media streams
- **FIPS-Approved Algorithms** - AES-256, SHA-256, PBKDF2
- **Password Security** - PBKDF2-HMAC-SHA256 hashing with 600,000 iterations (OWASP 2024 recommendation)
- **E911 Protection** - Automatic blocking of emergency calls during testing to prevent accidental 911 calls (see [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md#63-compliance---e911))

## 📋 Requirements

- Python 3.7+
- PyYAML (for configuration)
- cryptography>=41.0.0 (for FIPS-compliant encryption)
- Network access for SIP/RTP ports

## 🚀 Quick Start

> **📌 Production Deployment?** If you're deploying to Ubuntu 24.04 LTS for production use, see the [Production Deployment](#-production-deployment-ubuntu-2404-lts) section below for automated setup.

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX
```

2. Install dependencies:
```bash
# For Debian/Ubuntu systems (with system-managed packages):
./install_requirements.sh

# Or manually:
pip install -r requirements.txt --break-system-packages --ignore-installed typing_extensions

# For other systems or virtual environments:
pip install -r requirements.txt
```

3. Set up database (optional but recommended):
```bash
# For PostgreSQL (recommended for production)
sudo apt-get install postgresql
sudo -u postgres createdb pbx_system
sudo -u postgres psql -c "CREATE USER pbx_user WITH PASSWORD 'YourPassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;"

# Verify database connection
python scripts/verify_database.py

# Or use SQLite for testing (no setup needed)
# Just configure database.type: sqlite in config.yml
```

See [COMPLETE_GUIDE.md - Section 1.3](COMPLETE_GUIDE.md#13-environment-configuration) for detailed database setup.

4. Set up environment variables:
```bash
# Interactive setup (recommended)
python scripts/setup_env.py

# Or copy and edit manually
cp .env.example .env
nano .env
```

See [COMPLETE_GUIDE.md - Section 1.3](COMPLETE_GUIDE.md#13-environment-configuration) for detailed instructions on configuring credentials.

5. Generate SSL certificate (required for HTTPS):
```bash
# Generate self-signed certificate for development/testing
python scripts/generate_ssl_cert.py --hostname YOUR_IP_OR_HOSTNAME

# For production, use a trusted CA like Let's Encrypt
# See COMPLETE_GUIDE.md - Section 6.2 for detailed instructions
```

6. Configure the system:
```bash
# Edit config.yml with your settings
nano config.yml
```

7. Start the PBX:
```bash
python main.py
```

The PBX will start on:
- SIP Server: UDP port 5060
- RTP Media: UDP ports 10000-20000
- REST API: HTTPS port 8080 (HTTP also supported, configure in config.yml)
- Admin Panel: https://localhost:8080/admin/

**Note:** Browsers will show a security warning for self-signed certificates during development. This is normal. For production, use a certificate from a trusted CA like Let's Encrypt.

## 🏭 Production Deployment (Ubuntu 24.04 LTS)

For production deployments on Ubuntu 24.04 LTS, use the automated deployment script:

```bash
# Clone the repository
git clone https://github.com/mattiIce/PBX.git
cd PBX

# Run deployment script (requires sudo)
sudo bash scripts/deploy_production_pilot.sh

# Or run in dry-run mode first to see what will be configured
sudo bash scripts/deploy_production_pilot.sh --dry-run
```

**The script automatically configures:**
- ✓ PostgreSQL database with secure password
- ✓ Python virtual environment
- ✓ Nginx reverse proxy
- ✓ Firewall (UFW) with required ports
- ✓ Daily backup system (2 AM)
- ✓ Monitoring (Prometheus + Node Exporter)
- ✓ Systemd service for automatic startup

**After deployment completes, read:** [POST_DEPLOYMENT.md](POST_DEPLOYMENT.md)

This guide contains:
- Critical first steps (database password, SSL setup)
- Essential documentation to read (in order)
- Voice prompt generation (REQUIRED)
- Testing and verification steps
- Troubleshooting help

### 🌐 Production URL Setup (RECOMMENDED for Production)

For production deployments, you **should** access the admin panel via a friendly URL (e.g., `https://abps.albl.com`) instead of `IP:8080`:

**Quick Setup (Automated - 5-10 minutes):**
```bash
sudo scripts/setup_reverse_proxy.sh
```

**Documentation:**
- **Quick Start:** [QUICK_START_ABPS_SETUP.md](QUICK_START_ABPS_SETUP.md) - Step-by-step guide
- **Manual Setup:** [REVERSE_PROXY_SETUP.md](REVERSE_PROXY_SETUP.md) - Detailed nginx/Apache configuration
- **Implementation:** [ABPS_IMPLEMENTATION_GUIDE.md](ABPS_IMPLEMENTATION_GUIDE.md) - Setup summary

**Benefits:**
- ✅ Access via friendly domain name (no port number needed)
- ✅ HTTPS with free Let's Encrypt SSL certificate (auto-renews)
- ✅ Enhanced security with reverse proxy and rate limiting
- ✅ Professional appearance and industry best practice
- ✅ WebSocket support for WebRTC phones
- ✅ Better monitoring and logging

**Priority:** HIGH - This is the recommended configuration for any production deployment.

## 🖥️ Admin Panel

Access the web-based admin panel at `https://localhost:8080/admin/` to manage your PBX system through a modern, intuitive interface.

**Note:** For self-signed certificates, you may need to accept a browser security warning on first access.

### Features:
- **Dashboard** - Real-time system status and statistics
- **Extension Management** - Add, edit, and delete extensions
- **User Management** - Manage user accounts and passwords
- **Email Configuration** - Configure SMTP settings for voicemail notifications
- **Active Calls** - Monitor ongoing calls
- **Responsive Design** - Works on desktop, tablet, and mobile devices

### Screenshots:

**Dashboard View:**
![Admin Dashboard](https://github.com/user-attachments/assets/fb9d6f67-e87b-4179-9777-cb54f3a45731)

**Extension Management:**
![Extension Management](https://github.com/user-attachments/assets/43bd4d95-92ae-4f1a-a38c-209ecd960c28)

**Add Extension Modal:**
![Add Extension](https://github.com/user-attachments/assets/0794e891-4247-4de7-b552-92c4c5958302)

**Configuration Settings:**
![Configuration](https://github.com/user-attachments/assets/326b2987-a7e3-4aeb-b2b6-6e728478f9e1)

## 📖 Configuration

Edit `config.yml` to customize:

- **Server Settings** - SIP/RTP ports and binding
- **Extensions** - User accounts and email addresses
- **Dialplan** - Call routing rules
- **Features** - Enable/disable features
- **Voicemail** - Email notifications and SMTP settings
- **Call Queues** - Queue configuration
- **SIP Trunks** - External provider settings

### Voicemail-to-Email Setup

The PBX system includes comprehensive voicemail-to-email functionality:

```yaml
voicemail:
  email_notifications: true
  no_answer_timeout: 30  # Route to voicemail after 30 seconds
  
  # SMTP Configuration
  smtp:
    host: "smtp.yourserver.com"
    port: 587
    use_tls: true
    username: "your-username"
    password: "your-password"
  
  # Email Settings
  email:
    from_address: "voicemail@yourcompany.com"
    from_name: "PBX Voicemail System"
    include_attachment: true
    
  # Daily Reminders
  reminders:
    enabled: true
    time: "09:00"  # Send daily reminders at 9 AM
    unread_only: true

# Extensions with email addresses
extensions:
  - number: "1001"
    name: "User Name"
    email: "user@yourcompany.com"  # Receives voicemail notifications
```

**Features:**
- Instant email notifications when voicemail received
- Voicemail audio attached to email
- All message details included (caller, timestamp, duration)
- Daily reminders for unread voicemails
- Automatic routing to voicemail on no-answer
- Configurable timeout before voicemail

## 🔌 API Usage

Access the REST API at `http://localhost:8080/api/`

### Example API Calls

```bash
# Get system status
curl http://localhost:8080/api/status

# List extensions
curl http://localhost:8080/api/extensions

# Add a new extension
curl -X POST http://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{"number":"1005","name":"New User","email":"user@company.com","password":"securepass123","allow_external":true}'

# Update an extension
curl -X PUT http://localhost:8080/api/extensions/1005 \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name","email":"newemail@company.com"}'

# Delete an extension
curl -X DELETE http://localhost:8080/api/extensions/1005

# List active calls
curl http://localhost:8080/api/calls

# Get configuration
curl http://localhost:8080/api/config

# Update email configuration
curl -X PUT http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d '{"smtp":{"host":"smtp.gmail.com","port":587},"email":{"from_address":"pbx@company.com"}}'
```

## 📱 Extension Dialing

### Dialplan Patterns

- **0** - Auto attendant (automated menu system)
- **1xxx** - Internal extensions (e.g., 1001, 1002)
- **2xxx** - Conference rooms (e.g., 2001)
- **7x** - Call parking slots (e.g., 70-79)
- **8xxx** - Call queues (e.g., 8001 for Sales)
- **\*xxx** - Voicemail access (e.g., \*1001)

### Example Calls

- Dial `0` - Access auto attendant menu
- Dial `1002` - Call extension 1002
- Dial `2001` - Join conference room 2001
- Dial `8001` - Enter sales queue
- Dial `*1001` - Access voicemail for extension 1001

## 🛠️ Architecture

For a detailed architecture overview including data flows, component interactions, and deployment options, see [COMPLETE_GUIDE.md - Section 8](COMPLETE_GUIDE.md#8-developer-guide).

### Quick Overview

```
PBX System
├── pbx/
│   ├── core/           # Core PBX logic
│   │   ├── pbx.py      # Main PBX coordinator
│   │   └── call.py     # Call management
│   ├── sip/            # SIP protocol
│   │   ├── server.py   # SIP server
│   │   └── message.py  # SIP message handling
│   ├── rtp/            # Media handling
│   │   └── handler.py  # RTP stream management
│   ├── features/       # Advanced features
│   │   ├── extensions.py      # Extension registry
│   │   ├── voicemail.py       # Voicemail system
│   │   ├── conference.py      # Conference rooms
│   │   ├── call_recording.py  # Call recording
│   │   ├── call_queue.py      # ACD queues
│   │   ├── presence.py        # Presence/status
│   │   ├── call_parking.py    # Call parking
│   │   ├── cdr.py             # Call detail records
│   │   ├── music_on_hold.py   # MOH system
│   │   └── sip_trunk.py       # External trunks
│   ├── api/            # REST API
│   │   └── rest_api.py # HTTP API server
│   └── utils/          # Utilities
│       ├── config.py   # Configuration management
│       └── logger.py   # Logging system
├── examples/           # Example clients
├── logs/              # Log files
├── recordings/        # Call recordings
├── voicemail/         # Voicemail storage
├── moh/               # Music on hold (5 tracks included)
│   └── default/       # Default MOH class
└── config.yml         # Main configuration
```

## 🧪 Testing

Run the example SIP client:

```bash
python examples/simple_client.py
```

This will:
1. Register extension 1001 with the PBX
2. Make a test call to extension 1002

Run test suites to verify functionality:

```bash
# Basic tests
python tests/test_basic.py

# E911 protection tests
python tests/test_e911_protection.py
```

**Important:** The E911 protection system automatically prevents emergency calls during testing. See [COMPLETE_GUIDE.md - Section 6.3](COMPLETE_GUIDE.md#63-compliance---e911) for details.

## 🔐 Security

- **FIPS 140-2 Compliance** - Government-grade cryptographic standards
- **Authentication** - FIPS-compliant password hashing (PBKDF2-HMAC-SHA256)
- **Encryption** - AES-256-GCM for data encryption
- **TLS/SIPS** - Encrypted SIP signaling with FIPS-approved ciphers
- **SRTP** - Encrypted RTP media streams
- **Rate Limiting** - Protection against brute force attacks
- **IP Banning** - Automatic blocking after failed attempts

For detailed security information, see [COMPLETE_GUIDE.md - Section 6](COMPLETE_GUIDE.md#6-security--compliance) for comprehensive security reference and implementation details.

## 📊 Monitoring

### Logs
- System logs: `logs/pbx.log`
- Adjust log level in `config.yml` (DEBUG, INFO, WARNING, ERROR)

### Call Detail Records
- CDR files: `cdr/cdr_YYYY-MM-DD.jsonl`
- Access via API: `/api/cdr`
- Statistics: `/api/statistics`

## 🎯 Use Cases

- **Small Business Phone System** - Complete office telephony
- **Call Center** - Queue management and recording
- **Remote Teams** - Internal communication system
- **Customer Support** - IVR and queue management
- **Development/Testing** - SIP client development

## 🔄 Integration

The REST API allows integration with:
- CRM systems
- Helpdesk software
- Custom applications
- Monitoring systems
- Analytics platforms

## 📝 License

This project is open source and available for use in building your in-house VOIP system.

## 🤝 Contributing

Contributions are welcome! This is a foundation for building a production-grade PBX system.

## 📧 Support

For issues and questions, please open a GitHub issue.

## 🗺️ Roadmap

### Core Features
- [x] **FIPS 140-2 compliant encryption** - ✅ COMPLETED
- [x] **TLS/SRTP encryption** - ✅ COMPLETED
- [x] **Phone Provisioning** - ✅ COMPLETED
- [x] **Voicemail-to-Email** - ✅ COMPLETED
- [x] **DTMF Detection (Goertzel)** - ✅ COMPLETED
- [x] **Voicemail IVR System** - ✅ COMPLETED
- [x] **Auto Attendant (IVR)** - ✅ COMPLETED

### Operator Console
- [x] **VIP Caller Database** - ✅ COMPLETED
- [x] **Call Screening & Interception** - ✅ COMPLETED
- [x] **Announced Transfers** - ✅ COMPLETED
- [x] **Park and Page** - ✅ COMPLETED
- [x] **BLF Status Monitoring** - ✅ COMPLETED

### Enterprise Integrations
- [x] **Zoom Integration** (OAuth, Meetings) - ✅ COMPLETED
- [x] **Active Directory/LDAP** (Auth, Search) - ✅ COMPLETED
- [x] **Outlook Integration** (Calendar, Contacts) - ✅ COMPLETED
- [x] **Microsoft Teams** (Presence, Meetings) - ✅ COMPLETED

### Database Backend
- [x] **PostgreSQL/SQLite Support** - ✅ COMPLETED
  - Stores voicemail metadata (caller_id, duration, timestamp, listened status)
  - Stores CDR (Call Detail Records)
  - Stores VIP caller database
  - Stores registered phone tracking (MAC addresses, IP addresses, extensions)
  - Audio files stored efficiently on file system
  - See [COMPLETE_GUIDE.md - Section 7.3](COMPLETE_GUIDE.md#73-database-management) for setup guide
  - See [COMPLETE_GUIDE.md - Section 4.3](COMPLETE_GUIDE.md#43-phone-provisioning) for phone tracking details

### Legacy System Migration
- [x] **AT&T Merlin Legend Import** - ✅ COMPLETED
  - Import voicemail messages, PINs, and custom greetings
  - Supports CSV, JSON, and directory-based formats
  - Flexible metadata parsing from filenames
  - Batch import with dry-run preview
  - See [COMPLETE_GUIDE.md - Section 5.5](COMPLETE_GUIDE.md#55-zoom-integration) for migration guide

### Phone Provisioning
- [x] **Auto-Configuration for IP Phones** - ✅ COMPLETED
  - Supports Zultys, Yealink, Polycom, Cisco, Grandstream
  - Template-based configuration with automatic device information population
  - Customizable templates via web interface and API
  - Template management (view, export, edit, reload)
  - See [COMPLETE_GUIDE.md - Section 4.3](COMPLETE_GUIDE.md#43-phone-provisioning) for provisioning setup guide

### Phone Book & Directory
- [x] **Phone Book System** - ✅ COMPLETED
  - Centralized company directory
  - Active Directory synchronization
  - Multiple export formats (Yealink XML, Cisco XML, JSON)
  - Database storage with search capability
  - Push to IP phones automatically
  - **NEW: LDAPS configuration for IP phones** (Zultys ZIP 33G/37G)
  - Remote phone book URL as fallback method
  - See [COMPLETE_GUIDE.md - Section 4.4](COMPLETE_GUIDE.md#44-phone-book-system) for setup guide and LDAPS configuration

### Paging System
- [x] **Paging System** - ✅ COMPLETED (Software)
  - Full SIP/RTP integration with PBX core
  - Zone-based paging configuration
  - Digital-to-analog converter device management
  - All-call and zone-specific paging
  - Production-ready software (hardware deployment ready)
  - See [COMPLETE_GUIDE.md - Section 4.6](COMPLETE_GUIDE.md#46-paging-system) for implementation guide

### Webhook System
- [x] **Event-Driven Integrations** - ✅ COMPLETED
  - Real-time HTTP POST notifications for PBX events
  - 15+ event types (calls, voicemail, extensions, queues, conferences)
  - HMAC-SHA256 signature support for security
  - Configurable subscriptions with custom headers
  - Retry logic with exponential backoff
  - Asynchronous delivery with worker threads
  - See [COMPLETE_GUIDE.md - Section 4.7](COMPLETE_GUIDE.md#47-webhook-system) for setup guide

### Known Issues

⚠️ **Login Connection Error**
- **Issue**: "Connection error. Please try again." when trying to log into admin panel
- **Diagnosis**: The login page now shows troubleshooting info automatically
  - Open browser console (F12) for detailed diagnostics
  - Check if API server is running: `sudo systemctl status pbx`
  - Verify port 9000 is accessible: `curl http://localhost:9000/api/status`
- **Common Causes**: 
  - PBX server not running
  - Firewall blocking port 9000
  - Wrong hostname/port configuration
- **Fix**: See [COMPLETE_GUIDE.md - Section 7.1](COMPLETE_GUIDE.md#71-admin-panel) for step-by-step resolution

⚠️ **Admin Panel After Updates**
- **Issue**: After running server update scripts, the admin panel may not display correctly or buttons may not be clickable
- **Cause**: Browser caching old CSS/JavaScript files
- **Fix**: Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac) to force refresh
- **Details**: See [BROWSER_CACHE_FIX.md](BROWSER_CACHE_FIX.md) for comprehensive troubleshooting
- **Status Check**: Visit `/admin/status-check.html` to verify your installation

⚠️ **Audio Features**
- **WebRTC Browser Phone**: Currently disabled and not working. Use physical IP phones or SIP clients for calls.
- ~~**Hardphone Audio**: Audio sample rate mismatch issue~~ - ✅ **FIXED** (December 19, 2025)
  - All voicemail and auto attendant prompts regenerated at correct 8kHz sample rate for PCMU codec
  - Audio playback should now work correctly on IP phones
- **WebRTC Audio**: WebRTC browser calling feature needs further investigation

All other PBX features (call routing, voicemail storage, extensions, admin panel, etc.) are fully functional.

### Framework Features (100% Free & Open Source)

The PBX system includes comprehensive framework implementations for 20+ advanced features. **All features can be implemented using only free and open-source technologies - no paid services required!**

**Implementation Status:**
- **✅ Fully Implemented:** Production-ready with complete admin UI (Click-to-Dial, Paging, Speech Analytics, Nomadic E911)
- **🔧 Enhanced Admin UI:** Full UI with live data, needs external service integration (6 features with free options documented)
- **⚙️ Framework Only:** Backend ready, basic UI, needs service integration (10 features with free options documented)

**AI-Powered Features (FREE options: Vosk, spaCy, Rasa, scikit-learn):**
- 🔧 Conversational AI Assistant - Auto-responses and smart call handling
- 🔧 Predictive Dialing - AI-optimized outbound campaigns
- 🔧 Voice Biometrics - Speaker authentication and fraud detection
- ⚙️ Call Quality Prediction - Proactive network issue detection

**Analytics & Reporting (FREE options: Metabase, Superset, Redash):**
- 🔧 Business Intelligence Integration - Export to BI tools
- 🔧 Call Tagging & Categorization - AI-powered call classification
- ⚙️ Call Recording Analytics - AI analysis of recorded calls

**Mobile & Remote Work (FREE options: React Native, WebRTC):**
- 🔧 Mobile Apps Framework - iOS and Android client support
- ⚙️ Mobile Number Portability - Use business number on mobile

**Advanced Features (FREE options documented):**
- ⚙️ Call Blending - Mix inbound/outbound for efficiency
- ⚙️ Predictive Voicemail Drop - Auto-leave message on voicemail detection
- ⚙️ Geographic Redundancy - Multi-region trunk registration
- ⚙️ DNS SRV Failover - Automatic server failover
- ⚙️ Session Border Controller - Enhanced security (Kamailio, OpenSIPS)
- ⚙️ Data Residency Controls - Geographic data storage options

**Free & Open Source Integration Options:**
- **Speech Recognition:** Vosk (offline, no cloud costs)
- **NLP/AI:** spaCy, NLTK, Rasa, ChatterBot
- **Machine Learning:** scikit-learn, TensorFlow
- **BI Tools:** Metabase, Apache Superset, Redash
- **Mobile:** React Native, Flutter (cross-platform)
- **Predictive Dialer:** Vicidial (open source)
- **SBC:** Kamailio, OpenSIPS, RTPEngine

**Documentation:**
- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md) - Complete framework overview with free options
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) - Implementation status and details
- [BI_INTEGRATION_GUIDE.md](BI_INTEGRATION_GUIDE.md) - Business Intelligence integration
- [CALL_TAGGING_GUIDE.md](CALL_TAGGING_GUIDE.md) - Call tagging and categorization
- [MOBILE_APPS_GUIDE.md](MOBILE_APPS_GUIDE.md) - Mobile app framework

**Note:** Framework features have complete backend implementations, database schemas, and REST APIs. All features can be implemented using free and open-source technologies - detailed integration guides available for each feature.

### Future Enhancements
- [ ] Fix WebRTC browser-based calling (currently non-functional)
- [x] ~~Fix hardphone audio playback issues~~ - ✅ **COMPLETED** (December 19, 2025)
- [x] ~~Resolve audio sample rate mismatch (8kHz vs 16kHz)~~ - ✅ **COMPLETED** (December 19, 2025)
- [ ] Complete free/open-source service integrations for framework features
- [ ] Native iOS and Android mobile apps (React Native/Flutter)
- [ ] SMS/Messaging integration
- [ ] Clustering/High availability
- [ ] Full SIP Direct Routing to Teams
- [ ] Professional voice recordings for auto attendant (TTS or voice actor)

See [TODO.md](TODO.md) for a comprehensive list of planned features organized by priority.

---

**Built with ❤️ for creating robust in-house communication systems**
