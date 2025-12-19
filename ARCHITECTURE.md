# PBX System Architecture

## Overview

The Aluminum Blanking Phone System is a comprehensive, enterprise-grade PBX system built in Python. This document provides a high-level overview of the system architecture.

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         PBX System                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   SIP Server │  │  RTP Handler │  │  REST API    │          │
│  │   (Port 5060)│  │(10000-20000) │  │  (Port 8080) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                    ┌───────▼────────┐                           │
│                    │   PBX Core     │                           │
│                    │ (Coordinator)  │                           │
│                    └───────┬────────┘                           │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         │                  │                  │                 │
│  ┌──────▼─────┐   ┌────────▼──────┐   ┌──────▼─────┐          │
│  │ Extensions │   │ Call Manager  │   │  Features  │          │
│  │  Registry  │   │               │   │ (Voicemail,│          │
│  └────────────┘   └───────────────┘   │ Queues,    │          │
│                                        │ Recording, │          │
│                                        │ etc.)      │          │
│                                        └────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
         ┌──────▼──────┐ ┌─▼────────┐ ┌▼──────────┐
         │  PostgreSQL │ │  Redis   │ │File System│
         │  (Metadata) │ │ (Cache)  │ │  (Audio)  │
         └─────────────┘ └──────────┘ └───────────┘
```

## Core Modules

### 1. SIP Server (`pbx/sip/`)
- **Purpose**: Handles SIP protocol communication
- **Components**:
  - `server.py`: UDP server for SIP messages
  - `message.py`: SIP message parsing and generation
  - `sdp.py`: Session Description Protocol handling
- **Ports**: UDP 5060

### 2. RTP Handler (`pbx/rtp/`)
- **Purpose**: Manages real-time media streaming
- **Components**:
  - `handler.py`: RTP packet handling
  - `jitter_buffer.py`: Jitter compensation
  - `rfc2833.py`: DTMF tone handling
  - `rtcp_monitor.py`: Quality monitoring
- **Ports**: UDP 10000-20000

### 3. PBX Core (`pbx/core/`)
- **Purpose**: Central coordinator for all PBX operations
- **Components**:
  - `pbx.py`: Main PBX coordinator
  - `call.py`: Call state management
- **Responsibilities**: 
  - Call routing
  - Feature coordination
  - State management

### 4. Features (`pbx/features/`)
- **Purpose**: Implements advanced telephony features
- **Key Features**:
  - Voicemail system
  - Call queues (ACD)
  - Conference calling
  - Call recording
  - Auto attendant (IVR)
  - Music on hold
  - Call parking
  - Phone provisioning
  - Presence system

### 5. REST API (`pbx/api/`)
- **Purpose**: Web-based management interface
- **Components**:
  - `rest_api.py`: HTTP/HTTPS API server
  - `opensource_integration_api.py`: Integration endpoints
- **Endpoints**:
  - `/api/status` - System status
  - `/api/extensions` - Extension management
  - `/api/calls` - Active calls
  - `/admin/` - Web admin panel
  - `/health` - Health check

### 6. Integrations (`pbx/integrations/`)
- **Purpose**: External service integrations
- **Supported**:
  - Active Directory (LDAP)
  - Microsoft Teams
  - Microsoft Outlook
  - Zoom
  - EspoCRM
  - Matrix/Element
  - Jitsi Meet

### 7. Utilities (`pbx/utils/`)
- **Purpose**: Common utilities and helpers
- **Components**:
  - `config.py`: Configuration management
  - `database.py`: Database operations
  - `logger.py`: Logging system
  - `security.py`: Security functions
  - `encryption.py`: FIPS-compliant encryption
  - `tts.py`: Text-to-speech

## Data Flow

### Incoming Call Flow
```
1. IP Phone → SIP INVITE → SIP Server
2. SIP Server → PBX Core (validates extension)
3. PBX Core → Call Manager (creates call object)
4. Call Manager → Dialplan (determines routing)
5. Dialplan → Target Extension/Feature
6. RTP Handler ↔ Media Exchange ↔ RTP Handler
```

### Voicemail Flow
```
1. No Answer (timeout) → Voicemail Feature
2. Voicemail → Play Greeting (TTS or custom)
3. Voicemail → Record Message (RTP → File)
4. Voicemail → Save to Database + Filesystem
5. Voicemail → Send Email Notification (if configured)
```

## Storage Architecture

### Database (PostgreSQL/SQLite)
- Extension metadata
- Voicemail metadata
- Call Detail Records (CDR)
- Phone registration tracking
- Queue statistics
- User preferences

### Filesystem
- Audio recordings
- Voicemail audio files
- Call recordings
- Music on hold files
- Voice prompts

### Cache (Redis)
- Session tokens
- Presence information
- Real-time call state
- Rate limiting counters

## Security Layers

### 1. Network Security
- SIP authentication (digest auth)
- TLS/SIPS for encrypted signaling
- SRTP for encrypted media
- Rate limiting on API endpoints

### 2. Application Security
- PBKDF2 password hashing
- FIPS-approved cryptography
- Session token management
- Input validation and sanitization

### 3. API Security
- JWT-based authentication
- CORS headers
- Security headers (CSP, X-Frame-Options, etc.)
- HTTPS/SSL support

## Scalability Considerations

### Current Architecture
- Single-server deployment
- Vertical scaling supported
- PostgreSQL for concurrent access

### Future Enhancements
- Clustering support (planned)
- Geographic redundancy (framework exists)
- Load balancing (SBC integration available)

## Deployment Options

### 1. Bare Metal / VM
- Direct Python installation
- SystemD service
- Nginx reverse proxy (optional)

### 2. Docker
- docker-compose with PostgreSQL + Redis
- Container health checks
- Volume mounts for persistent data

### 3. Kubernetes (Planned)
- Helm charts
- Horizontal pod autoscaling
- Persistent volume claims

## Monitoring and Observability

### Metrics
- Prometheus client (built-in)
- Call statistics
- System resource usage
- QoS metrics

### Logging
- Structured logging
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation supported

### Health Checks
- `/health` endpoint for orchestration
- `/api/status` for detailed status
- Database connection checks

## Performance Characteristics

### Capacity
- **Concurrent Calls**: 100+ (depends on hardware)
- **Extensions**: 1000+ supported
- **RTP Streams**: Limited by network bandwidth
- **API Requests**: 1000+ req/sec (with proper hardware)

### Resource Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 2GB+ recommended
- **Storage**: Depends on recording/voicemail volume
- **Network**: 100 Kbps per concurrent call (G.711)

## Technology Stack

### Core Technologies
- **Language**: Python 3.8+
- **Web Framework**: Built-in HTTP server / Flask
- **Database**: PostgreSQL 15+ / SQLite
- **Cache**: Redis 7+

### Key Libraries
- `aiortc`: WebRTC support
- `twisted`: Async networking
- `cryptography`: FIPS-compliant encryption
- `sqlalchemy`: ORM
- `pydub`: Audio processing

## References

- [README.md](README.md) - Getting started guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - REST API reference
- [SECURITY.md](SECURITY.md) - Security documentation
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions
