# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.0.0] - 2024-12-19

### Added

#### Core PBX Features
- SIP Protocol Support - Full Session Initiation Protocol implementation
- RTP Media Handling - Real-time Transport Protocol for audio streaming
- Extension Management - User registration and authentication
- Call Routing - Intelligent call routing based on dialplan rules
- Call Management - Hold, resume, transfer, and forward calls

#### Advanced Call Features
- Auto Attendant (IVR) - Automated call answering with menu options
- Call Recording - Record calls for compliance and quality assurance
- Call Queues (ACD) - Automatic Call Distribution with multiple strategies
- Conference Calling - Multi-party conference rooms
- Call Parking - Park and retrieve calls from any extension
- Call Transfer - Blind and attended transfers
- Music on Hold - Customizable hold music
- Voicemail System - Full-featured voicemail with custom greeting recording, email notifications, and auto-routing

#### Modern VOIP Features
- Presence System - Real-time user availability status
- SIP Trunk Support - Connect to external SIP providers
- Phone Provisioning - Auto-configuration for multiple IP phone brands (Zultys, Yealink, Polycom, Cisco, Grandstream)
- Phone Registration Tracking - Automatic tracking of registered phones with MAC addresses and IP addresses
- Phone Book System - Centralized directory with AD sync, pushed to IP phones in multiple formats
- Paging System - Full overhead paging support with SIP/RTP integration
- Webhook System - Event-driven integrations with HMAC signature support
- CDR (Call Detail Records) - Comprehensive call logging and statistics
- REST API - HTTPS/HTTP API for integration and management
- Web Admin Panel - Modern browser-based admin interface
- Multi-codec Support - G.711 (PCMU/PCMA), G.722 (HD), G.729, G.726, Opus, iLBC, Speex
- DTMF Detection - Goertzel algorithm for interactive voice menus

#### Operator Console Features
- VIP Caller Database - Priority handling for important callers
- Call Screening - Intercept and screen calls before transfer
- Announced Transfers - Announce caller before completing transfer
- Park and Page - Park calls and page via multiple methods
- BLF Monitoring - Real-time extension busy lamp field status
- Company Directory - Quick lookup with search functionality

#### Free & Open Source Integrations
- Jitsi Meet integration - Video conferencing
- Matrix/Element integration - Team messaging
- EspoCRM integration - CRM with screen pop and call logging
- Vosk integration - Offline speech recognition for transcription
- OpenLDAP compatibility - Directory services

#### Enterprise Integrations (Optional)
- Zoom Integration - Create instant or scheduled Zoom meetings
- Active Directory - LDAP authentication and user directory sync
- Microsoft Outlook - Calendar sync, availability, and contact integration
- Microsoft Teams - Presence sync and meeting escalation

#### Security & Compliance
- HTTPS/SSL Support - Secure API communication with TLS 1.2+
- In-House CA Integration - Automatic certificate request from enterprise Certificate Authority
- FIPS 140-2 Compliant Encryption - Government-grade security
- TLS/SIPS - Encrypted SIP signaling
- SRTP - Encrypted media streams
- FIPS-Approved Algorithms - AES-256, SHA-256, PBKDF2
- Password Security - PBKDF2-HMAC-SHA256 hashing with 600,000 iterations (OWASP 2024 recommendation)
- E911 Protection - Automatic blocking of emergency calls during testing

[Unreleased]: https://github.com/mattiIce/PBX/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mattiIce/PBX/releases/tag/v1.0.0
