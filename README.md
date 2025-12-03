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
- **Voicemail System** - Full-featured voicemail with message management

### Modern VOIP Features
- **Presence System** - Real-time user availability status
- **SIP Trunk Support** - Connect to external SIP providers
- **Phone Provisioning** - Auto-configuration for IP phones (Yealink, Polycom, Cisco, Grandstream)
- **CDR (Call Detail Records)** - Comprehensive call logging and statistics
- **REST API** - HTTP API for integration and management
- **Web Interface** - Browser-based management (API endpoints)
- **Multi-codec Support** - G.711, G.729 and more

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

3. Configure the system:
```bash
# Edit config.yml with your settings
nano config.yml
```

4. Start the PBX:
```bash
python main.py
```

The PBX will start on:
- SIP Server: UDP port 5060
- RTP Media: UDP ports 10000-20000
- REST API: HTTP port 8080

## 📖 Configuration

Edit `config.yml` to customize:

- **Server Settings** - SIP/RTP ports and binding
- **Extensions** - User accounts and permissions
- **Dialplan** - Call routing rules
- **Features** - Enable/disable features
- **Call Queues** - Queue configuration
- **SIP Trunks** - External provider settings

## 🔌 API Usage

Access the REST API at `http://localhost:8080/api/`

### Example API Calls

```bash
# Get system status
curl http://localhost:8080/api/status

# List extensions
curl http://localhost:8080/api/extensions

# List active calls
curl http://localhost:8080/api/calls

# Get call statistics
curl http://localhost:8080/api/statistics
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

- [x] **FIPS 140-2 compliant encryption** - ✅ COMPLETED
- [x] **TLS/SRTP encryption** - ✅ COMPLETED
- [x] **Phone Provisioning** - ✅ COMPLETED
- [ ] WebRTC support for browser-based calls
- [ ] IVR (Interactive Voice Response) system
- [ ] SMS/Messaging integration
- [ ] Mobile app support (iOS/Android)
- [ ] Database backend for scalability
- [ ] Clustering/High availability
- [ ] Advanced analytics dashboard
- [ ] Video conferencing support
- [ ] Integration with Microsoft Teams/Slack

---

**Built with ❤️ for creating robust in-house communication systems**
