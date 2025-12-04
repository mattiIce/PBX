# InHouse PBX System

A comprehensive, feature-rich Private Branch Exchange (PBX) and VOIP system built from scratch in Python. This system provides enterprise-grade telephony features for internal communication and external connectivity.

## 🌟 Features

### Core PBX Features
- **SIP Protocol Support** - Full Session Initiation Protocol implementation
- **RTP Media Handling** - Real-time Protocol for audio streaming
- **Extension Management** - User registration and authentication
- **Call Routing** - Intelligent call routing based on dialplan rules
- **Call Management** - Hold, resume, transfer, and forward calls

### Advanced Call Features
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
- **Phone Provisioning** - Auto-configuration for ZIP IP phones (33G, 37G)
- **CDR (Call Detail Records)** - Comprehensive call logging and statistics
- **REST API** - HTTP API for integration and management
- **Web Admin Panel** - Modern browser-based admin interface for managing extensions, users, and configuration
- **Multi-codec Support** - G.711, G.729 and more
- **DTMF Detection** - Goertzel algorithm for interactive voice menus

### Operator Console Features
- **VIP Caller Database** - Priority handling for important callers
- **Call Screening** - Intercept and screen calls before transfer
- **Announced Transfers** - Announce caller before completing transfer
- **Park and Page** - Park calls and page via multiple methods
- **BLF Monitoring** - Real-time extension busy lamp field status
- **Company Directory** - Quick lookup with search functionality

### Enterprise Integrations
- **Zoom Integration** - Create instant or scheduled Zoom meetings from PBX
- **Active Directory** - LDAP authentication and user directory sync
- **Microsoft Outlook** - Calendar sync, availability, and contact integration
- **Microsoft Teams** - Presence sync and meeting escalation

### Security & Compliance
- **FIPS 140-2 Compliant Encryption** - Government-grade security
- **TLS/SIPS** - Encrypted SIP signaling
- **SRTP** - Encrypted media streams
- **FIPS-Approved Algorithms** - AES-256, SHA-256, PBKDF2
- **Password Security** - PBKDF2-HMAC-SHA256 hashing with 100,000 iterations

## 📋 Requirements

- Python 3.7+
- PyYAML (for configuration)
- cryptography>=41.0.0 (for FIPS-compliant encryption)
- Network access for SIP/RTP ports

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX
```

2. Install dependencies:
```bash
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

See [VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md) for detailed database setup.

4. Configure the system:
```bash
# Edit config.yml with your settings
nano config.yml
```

5. Start the PBX:
```bash
python main.py
```

The PBX will start on:
- SIP Server: UDP port 5060
- RTP Media: UDP ports 10000-20000
- REST API: HTTP port 8080
- Admin Panel: http://localhost:8080/admin/

## 🖥️ Admin Panel

Access the web-based admin panel at `http://localhost:8080/admin/` to manage your PBX system through a modern, intuitive interface.

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

- **1xxx** - Internal extensions (e.g., 1001, 1002)
- **2xxx** - Conference rooms (e.g., 2001)
- **7x** - Call parking slots (e.g., 70-79)
- **8xxx** - Call queues (e.g., 8001 for Sales)
- **\*xxx** - Voicemail access (e.g., \*1001)

### Example Calls

- Dial `1002` - Call extension 1002
- Dial `2001` - Join conference room 2001
- Dial `8001` - Enter sales queue
- Dial `*1001` - Access voicemail for extension 1001

## 🛠️ Architecture

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
├── moh/               # Music on hold files
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

## 🔐 Security

- **FIPS 140-2 Compliance** - Government-grade cryptographic standards
- **Authentication** - FIPS-compliant password hashing (PBKDF2-HMAC-SHA256)
- **Encryption** - AES-256-GCM for data encryption
- **TLS/SIPS** - Encrypted SIP signaling with FIPS-approved ciphers
- **SRTP** - Encrypted RTP media streams
- **Rate Limiting** - Protection against brute force attacks
- **IP Banning** - Automatic blocking after failed attempts

For detailed security information, see [SECURITY.md](SECURITY.md) and [FIPS_COMPLIANCE.md](FIPS_COMPLIANCE.md).

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
  - Audio files stored efficiently on file system
  - See [VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md) for setup guide

### Future Enhancements
- [ ] WebRTC support for browser-based calls
- [ ] SMS/Messaging integration
- [ ] Mobile app support (iOS/Android)
- [ ] Clustering/High availability
- [ ] Advanced analytics dashboard
- [ ] Video conferencing support
- [ ] Full SIP Direct Routing to Teams
- [ ] CRM integrations (Salesforce, HubSpot)

---

**Built with ❤️ for creating robust in-house communication systems**
