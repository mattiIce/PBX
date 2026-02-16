<div align="center">
  <img src="Warden VoIP Logo.png" alt="Warden VoIP" width="200"/>

  # Warden VoIP

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
  [![Linting: Ruff](https://img.shields.io/badge/linting-ruff-261230.svg)](https://github.com/astral-sh/ruff)
  [![Tests](https://github.com/mattiIce/PBX/workflows/Tests/badge.svg)](https://github.com/mattiIce/PBX/actions)
  [![Code Quality](https://github.com/mattiIce/PBX/workflows/Code%20Quality/badge.svg)](https://github.com/mattiIce/PBX/actions)
  [![codecov](https://codecov.io/gh/mattiIce/PBX/branch/main/graph/badge.svg)](https://codecov.io/gh/mattiIce/PBX)

  **A comprehensive, feature-rich Private Branch Exchange (PBX) and VoIP system built from scratch in Python**
</div>

---

## Documentation

- **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** - Comprehensive documentation covering installation, deployment, features, integrations, security, troubleshooting, and API reference
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Troubleshooting guide for administrators with solutions to all known issues
- **[docs/](docs/)** - Operational guides (deployment, HA, incident response, capacity planning, reverse proxy)
- **[docs/reference/](docs/reference/)** - Technical reference (SIP implementation, phone book API, framework features)

## Features

### Core PBX
- **SIP Protocol** - Full SIP implementation with TLS/SIPS support
- **RTP Media** - Real-time audio streaming with multi-codec support (G.711, G.722, G.729, Opus, and more)
- **Extension Management** - User registration, authentication, and directory
- **Call Routing** - Intelligent routing based on dialplan rules
- **Call Management** - Hold, resume, blind/attended transfer, and forward

### Advanced Call Features
- **Auto Attendant (IVR)** - Automated menus with DTMF navigation
- **Call Recording** - Compliance and quality assurance recording
- **Call Queues (ACD)** - Automatic Call Distribution with multiple strategies and skills-based routing
- **Conference Calling** - Multi-party conference rooms
- **Call Parking** - Park and retrieve calls from any extension
- **Music on Hold** - Customizable hold music
- **Voicemail** - Full-featured with email notifications, greeting recording, and transcription (Vosk)
- **CDR** - Comprehensive call detail records and statistics

### Phone & Device Support
- **IP Phone Provisioning** - Auto-configuration for Zultys, Yealink, Polycom, Cisco, Grandstream
- **ATA Support** - Grandstream HT801/HT802, Cisco SPA112/SPA122/ATA191/ATA192 (see [docs/ATA_SUPPORT_GUIDE.md](docs/ATA_SUPPORT_GUIDE.md))
- **Phone Book** - Centralized directory with AD sync, pushed to phones (Yealink XML, Cisco XML)
- **BLF Monitoring** - Real-time busy lamp field status
- **Paging System** - SIP/RTP overhead paging with zone support

### Integrations
- **Jitsi Meet** - Video conferencing (free Zoom alternative)
- **Matrix/Element** - Team messaging (free Slack/Teams alternative)
- **EspoCRM** - CRM with screen pop & call logging (free Salesforce alternative)
- **Vosk** - Offline speech recognition for voicemail transcription
- **Zoom** - Meeting creation from PBX (optional, proprietary)
- **Active Directory** - LDAP authentication and directory sync
- **Microsoft Outlook** - Calendar and contact integration
- **Microsoft Teams** - Presence sync and meeting escalation
- **Webhook System** - Event-driven HTTP notifications with HMAC signatures

### Security & Compliance
- **FIPS 140-2 Compliant** - Government-grade encryption (AES-256, SHA-256, PBKDF2)
- **TLS 1.3 / SIPS / SRTP** - Encrypted signaling and media
- **In-House CA** - Automatic certificate requests from enterprise CA
- **Password Security** - PBKDF2-HMAC-SHA256 with 600,000 iterations
- **Rate Limiting & IP Banning** - Brute force protection
- **E911 Compliance** - Ray Baum's Act dispatchable location support
- **Web Admin Panel** - Modern browser-based management with MFA support

## Requirements

- Python 3.13+
- PyYAML, cryptography>=46.0.5
- Network access for SIP (5060/udp) and RTP (10000-20000/udp) ports

## Quick Start

### Ubuntu Setup Wizard (Easiest)

```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX
sudo python3 scripts/setup_ubuntu.py
```

The wizard installs dependencies, sets up PostgreSQL, generates SSL certificates, creates voice prompts, and initializes the database. See **[COMPLETE_GUIDE.md - Section 1](COMPLETE_GUIDE.md#1-quick-start)** for details.

### Manual Installation

```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX

# Install dependencies (requires uv: https://docs.astral.sh/uv/)
make install          # Development mode
# Or: make install-prod  # Production only

# Install frontend dependencies
npm install

# Set up environment
python scripts/setup_env.py

# Generate SSL certificate
python scripts/generate_ssl_cert.py --hostname YOUR_IP_OR_HOSTNAME

# Configure and start
nano config.yml
python main.py
```

The PBX starts on:
- **SIP**: UDP port 5060
- **RTP Media**: UDP ports 10000-20000
- **REST API / Admin Panel**: HTTPS port 9000

See [COMPLETE_GUIDE.md - Section 1.3](COMPLETE_GUIDE.md#13-environment-configuration) for database and environment setup.

## Production Deployment (Ubuntu 24.04 LTS)

```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX
sudo bash scripts/deploy_production_pilot.sh
# Or dry-run first: sudo bash scripts/deploy_production_pilot.sh --dry-run
```

The script configures PostgreSQL, Python venv, Nginx reverse proxy, UFW firewall, daily backups, monitoring (Prometheus), and systemd service.

**After deployment:** See [COMPLETE_GUIDE.md - Section 2.2](COMPLETE_GUIDE.md#22-post-deployment-steps) for post-deployment steps (database password, SSL, voice prompts).

### Reverse Proxy Setup (Recommended)

```bash
# Nginx (recommended)
sudo scripts/setup_reverse_proxy.sh

# Apache (alternative)
sudo scripts/setup_apache_reverse_proxy.sh
```

See [COMPLETE_GUIDE.md - Section 2.4](COMPLETE_GUIDE.md#24-reverse-proxy-setup-recommended) or [docs/APACHE_REVERSE_PROXY_SETUP.md](docs/APACHE_REVERSE_PROXY_SETUP.md).

## Admin Panel

Access at `https://localhost:9000/admin/` for system management.

**Dashboard View:**
![Admin Dashboard](https://github.com/user-attachments/assets/fb9d6f67-e87b-4179-9777-cb54f3a45731)

**Extension Management:**
![Extension Management](https://github.com/user-attachments/assets/43bd4d95-92ae-4f1a-a38c-209ecd960c28)

**Add Extension:**
![Add Extension](https://github.com/user-attachments/assets/0794e891-4247-4de7-b552-92c4c5958302)

**Configuration:**
![Configuration](https://github.com/user-attachments/assets/326b2987-a7e3-4aeb-b2b6-6e728478f9e1)

## Dialplan

| Pattern | Destination | Example |
|---------|-------------|---------|
| `0` | Auto attendant | Dial `0` |
| `1xxx` | Internal extensions | Dial `1002` |
| `2xxx` | Conference rooms | Dial `2001` |
| `7x` | Call parking slots | Dial `70` |
| `8xxx` | Call queues | Dial `8001` |
| `*xxx` | Voicemail access | Dial `*1001` |

## API

```bash
curl http://localhost:9000/api/status              # System status
curl http://localhost:9000/api/extensions           # List extensions
curl http://localhost:9000/api/calls                # Active calls
curl http://localhost:9000/api/cdr                  # Call records
curl http://localhost:9000/api/config               # Configuration
```

See [COMPLETE_GUIDE.md - Section 9.2](COMPLETE_GUIDE.md#92-rest-api-reference) for full API reference.

## Monitoring

- **System logs**: `logs/pbx.log` (configurable level in `config.yml`)
- **CDR files**: `cdr/cdr_YYYY-MM-DD.jsonl`
- **API endpoints**: `/api/cdr`, `/api/statistics`
- **Grafana dashboards**: See [grafana/dashboards/](grafana/dashboards/)

## Known Issues

- **WebRTC Browser Phone** is currently non-functional. Use physical IP phones or SIP softphone clients.
- **Admin panel after updates**: If the panel doesn't display correctly, press `Ctrl+Shift+R` to force refresh cached files.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive troubleshooting.

## License

MIT License - see [LICENSE](LICENSE).

## Support

For issues and questions, open a [GitHub issue](https://github.com/mattiIce/PBX/issues).

---

**Built for robust in-house communication systems**
