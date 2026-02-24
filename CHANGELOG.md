# Changelog

All notable changes to the Warden VoIP PBX project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-16

### Added

- Full SIP protocol stack (REGISTER, INVITE, ACK, BYE, CANCEL, OPTIONS, SUBSCRIBE, NOTIFY, PUBLISH, REFER, UPDATE, PRACK, INFO, MESSAGE)
- RTP media handling with multi-codec support (G.711, G.722, G.729, Opus)
- 77 pluggable feature modules loaded dynamically via FeatureInitializer
- Modern admin web interface built with TypeScript and Vite
- 23 REST API route modules organized by feature domain
- Flask app factory pattern with blueprint-based routing
- SQLAlchemy 2.0 ORM with PostgreSQL (production) and SQLite (development fallback)
- Alembic database migrations
- Auto Attendant (IVR) with DTMF navigation
- Call queues with Automatic Call Distribution and skills-based routing
- Conference calling with multi-party rooms
- Voicemail with email notifications, greeting recording, and Vosk transcription
- Call recording, parking, and comprehensive CDR
- IP phone auto-provisioning for Zultys, Yealink, Polycom, Cisco, Grandstream
- ATA support for Grandstream HT801/HT802 and Cisco SPA112/SPA122/ATA191/ATA192
- Phone book with Active Directory sync and phone-format exports (Yealink XML, Cisco XML)
- BLF monitoring and paging system with zone support
- Integrations: Jitsi Meet, Matrix/Element, EspoCRM, Vosk, Zoom, Active Directory, Outlook, Teams
- Webhook system with event-driven HTTP notifications and HMAC signatures
- FIPS 140-2 compliant encryption (AES-256, SHA-256, PBKDF2)
- TLS 1.3, SIPS, and SRTP support
- E911 compliance with Ray Baum's Act dispatchable location support
- AI/ML features: call tagging (spaCy), conversational AI (NLTK), voice biometrics (pyAudioAnalysis), call recording analytics (Vosk), video codec (FFmpeg)
- Geographic redundancy and DNS SRV failover
- Mobile app support with push notifications (FCM and APNs)
- Session Border Controller and data residency controls
- Comprehensive test suite (225 test files) with pytest and Jest
- CI/CD pipelines: tests, code quality, security scanning, production deployment, dependency updates, syntax checks
- Docker Compose orchestration (PostgreSQL 17 + Redis 7 + PBX)
- Kubernetes manifests and Terraform IaC
- Grafana monitoring dashboards
- Production deployment scripts with Ubuntu setup wizard
- Pre-commit hooks: ruff, mypy, bandit, yamllint, markdownlint, shellcheck

### Documentation

- Complete guide covering installation, deployment, features, integrations, security, and API reference
- Troubleshooting guide for administrators
- Operational guides: HA deployment, capacity planning, incident response, operations runbook, production readiness checklist
- Technical reference: SIP methods, phone book/paging API, framework features, voice biometrics, geographic redundancy, mobile apps, call tagging, AI integration
- Apache and Nginx reverse proxy setup guides
- ATA support guide

[1.0.0]: https://github.com/mattiIce/PBX/releases/tag/v1.0.0
