# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Documentation Cleanup Phase 3** (February 2026)
  - Moved planning/status docs to docs/: EXECUTIVE_SUMMARY, FEATURES, IMPLEMENTATION_STATUS, PRODUCT_IMPROVEMENT_RECOMMENDATIONS, STRATEGIC_ROADMAP, TODO, DOCUMENTATION_INDEX
  - Root directory now contains only essential files: README, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, COMPLETE_GUIDE, TROUBLESHOOTING
  - Fixed 13+ broken cross-references to deleted/consolidated files
  - Fixed all remaining pip/requirements.txt references to uv/pyproject.toml
  - Updated relative paths in DOCUMENTATION_INDEX.md, docs/reference/README.md, and all docs/ files
  - Removed outdated AGENTS.md (Copilot instructions with venv/pip references)
- **Documentation Modernization Update** (February 2026)
  - Updated COMPLETE_GUIDE.md to v1.2.0 reflecting codebase modernization
  - Section 1.2: Installation now uses uv package manager and Makefile targets
  - Section 8: Package management updated from pip/venv to uv/pyproject.toml
  - Section 9: Completely rewritten Developer Guide covering Flask Blueprints, SQLAlchemy ORM, Alembic migrations, Pydantic schemas, TypeScript frontend modules, and OpenAPI docs
  - Updated README.md and CONTRIBUTING.md install instructions
  - Fixed all pip/requirements.txt references across documentation
  - Updated docs/HA_DEPLOYMENT_GUIDE.md, docs/LICENSE_ADMIN_INTERFACE.md, docs/PRODUCTION_READINESS_CHECKLIST.md
- **Documentation Consolidation Phase 2** (February 2026)
  - Reduced documentation from 87 to 53 markdown files (39% reduction)
  - Merged provisioning connection error fix content into TROUBLESHOOTING.md
  - Merged Apache 404 fix content into TROUBLESHOOTING.md
  - Moved operational guides (runbook, incident response, checklist) to docs/
  - Moved license admin interface docs to docs/
  - Moved dropdown database integration docs to docs/reference/
  - Deduplicated ATA documentation (3 files consolidated to 1)
  - Updated DOCUMENTATION_INDEX.md with complete file inventory

### Removed
- Historical fix documents (7 files): ADMIN_UI_AUTO_REFRESH_FIX.md, ADMIN_UI_AUTO_REFRESH_TESTING.md, API_GRACEFUL_DEGRADATION_FIX.md, LOAD_JITSI_CONFIG_FIX.md, PROVISIONING_CONNECTION_ERROR_FIX.md, RATE_LIMIT_FIX.md, docs/APACHE_404_FIX.md
- Historical summary documents (9 files): API_GRACEFUL_DEGRADATION_SUMMARY.md, IMPLEMENTATION_SUMMARY.md, IMPLEMENTATION_SUMMARY_ATA.md, PROVISIONING_FIX_SUMMARY.md, REFRESH_ALL_FIX_SUMMARY.md, SETUP_WIZARD_SUMMARY.md, PRODUCTION_READINESS_SUMMARY.md, FINAL_SUMMARY.md, SOLUTION_SUMMARY.md
- Redundant production documents (7 files): PRODUCTION_CERTIFICATION.md, PRODUCTION_DOCUMENTATION_INDEX.md, PRODUCTION_MASTER_INDEX.md, PRODUCTION_READY_100_PERCENT.md, PRODUCTION_READY_FINAL.md, PRODUCTION_READINESS_README.md, PRODUCTION_READINESS_FINAL.md
- Duplicate production runbook (consolidated with docs/OPERATIONS_RUNBOOK.md)
- Redundant root documents (8 files): LICENSING_GUIDE.md, DEPLOYMENT_GUIDE_STEPBYSTEP.md, SETUP_GUIDE.md, TROUBLESHOOTING_WINDOWS_README.md, PROJECT_QUALITY_IMPROVEMENTS.md, RATE_LIMITING_REMOVAL.md, BRANCH_MANAGEMENT.md, OPERATIONS_MANUAL.md
- Duplicate ATA documentation (2 files): docs/ATA_SUPPORT.md, docs/ATA_QUICK_REFERENCE.md

**Note:** All useful content from removed files has been preserved in COMPLETE_GUIDE.md, TROUBLESHOOTING.md, or relocated to docs/. No information was lost.

### Added
- **Cisco Enterprise ATA Support** ✨ NEW (December 30, 2025)
  - Cisco ATA 191 (ATA191-3PW-K9) provisioning template with PoE support
  - Cisco ATA 192 provisioning template with multiplatform firmware support
  - Enterprise-grade analog telephone adapter support
  - 4 additional unit tests for new ATA models (21 total tests, all passing)
  - Updated documentation to include new models
- **Full ATA (Analog Telephone Adapter) Support** ✨ (December 29, 2025)
  - Grandstream HT801 (1-port) provisioning template
  - Grandstream HT802 (2-port) provisioning template
  - Cisco SPA112 (2-port) provisioning template
  - Cisco SPA122 (2-port with router) provisioning template
  - T.38 fax over IP support enabled by default
  - Echo cancellation optimized for analog lines
  - G.711 codec priority for best analog/fax quality
  - DTMF support (SIP INFO method) for IVR/voicemail
  - Comprehensive ATA Support Guide documentation
  - 17 unit tests for ATA provisioning (all passing)
  - See [docs/ATA_SUPPORT_GUIDE.md](docs/ATA_SUPPORT_GUIDE.md) for complete setup instructions
- Comprehensive consolidated documentation guides:
  - PRODUCTION_DEPLOYMENT_GUIDE.md - Complete production deployment reference
  - ADMIN_PANEL_GUIDE.md - Complete admin panel usage guide
  - INTEGRATION_GUIDE.md - Integration setup, usage, and troubleshooting
  - TESTING_GUIDE.md - Automated testing, AD integration, and general testing procedures
  - VOICEMAIL_GUIDE.md - Complete voicemail system guide (database, email, transcription, greetings)
  - Enhanced INSTALLATION.md with Quick Start Checklist
  - Enhanced TROUBLESHOOTING.md with admin panel, QoS, and browser cache sections
  - Enhanced VOICE_PROMPTS_GUIDE.md with all TTS options and repository design
  - Enhanced LICENSE_ADMIN_INTERFACE.md with quick reference
  - Enhanced PRODUCT_IMPROVEMENT_RECOMMENDATIONS.md with quick wins section
  - Enhanced REVERSE_PROXY_SETUP.md with quick start automation
  - Enhanced PHONE_PROVISIONING.md with persistence, templates, and cleanup

### Changed
- Documentation consolidation: Reduced from 118 to 81 markdown files (31.4% reduction)
- Updated DOCUMENTATION_INDEX.md to reflect consolidated structure
- Improved documentation clarity by removing redundant content
- Generalized specific information (IP addresses, server names, organization details)
- Organized related content into comprehensive guides with table of contents
- All voicemail documentation consolidated into single comprehensive guide
- All testing documentation consolidated into single guide
- All admin panel documentation consolidated into single guide
- All phone provisioning documentation consolidated into single guide

### Removed
- Historical summary and report documents (11 files):
  - DOCUMENTATION_CONSOLIDATION_SUMMARY.md
  - DOCUMENTATION_FINALIZATION_SUMMARY.md
  - AUTO_ATTENDANT_MENU_FIXES_SUMMARY.md
  - CRITICAL_BLOCKERS_COMPLETION_REPORT.md
  - CODEC_REVIEW_PHASE5.md
  - SECURITY_COMPLIANCE_IMPLEMENTATION.md
- Deprecated individual guides (6 files):
  - DEBUG_VM_PIN.md → VOICEMAIL_GUIDE.md
  - ENABLE_DEBUG_VM_PIN.md → VOICEMAIL_GUIDE.md
  - VM_IVR_LOGGING.md → VOICEMAIL_GUIDE.md
  - VOICEMAIL_TRANSCRIPTION_VOSK.md → VOICEMAIL_TRANSCRIPTION_GUIDE.md
  - SECURITY.md → SECURITY_GUIDE.md
- Deployment documentation (3 files consolidated → PRODUCTION_DEPLOYMENT_GUIDE.md):
  - DEPLOYMENT_CHECKLIST.md
  - POST_DEPLOYMENT.md
  - PRODUCTION_DEPLOYMENT_CHECKLIST.md
- Installation/setup guides (1 file merged → INSTALLATION.md):
  - QUICK_START.md
- Troubleshooting documentation (4 files merged → TROUBLESHOOTING.md):
  - LOGIN_CONNECTION_TROUBLESHOOTING.md
  - BROWSER_CACHE_FIX.md
  - TROUBLESHOOTING_AUTO_ATTENDANT_MENUS.md
  - QOS_TROUBLESHOOTING_ONE_WAY_AUDIO.md
- Integration documentation (2 files merged → INTEGRATION_GUIDE.md):
  - INTEGRATION_INTERACTION_GUIDE.md
  - INTEGRATION_PORT_ALLOCATION.md
- Admin panel documentation (4 files consolidated → ADMIN_PANEL_GUIDE.md):
  - ADMIN_PANEL_AUTO_ATTENDANT.md
  - ADMIN_PANEL_VOICEMAIL_MANAGEMENT.md
  - ADMIN_VS_USER_SCREEN_GUIDE.md
  - ADMIN_EXTENSION_ACCESS_CONTROL.md
- Voice prompt documentation (2 files merged → VOICE_PROMPTS_GUIDE.md):
  - HOW_TO_ADD_VOICE_FILES.md
  - SETUP_GTTS_VOICES.md
- Voicemail documentation (4 files consolidated → VOICEMAIL_GUIDE.md):
  - VOICEMAIL_CUSTOM_GREETING_GUIDE.md
  - VOICEMAIL_EMAIL_GUIDE.md
  - VOICEMAIL_TRANSCRIPTION_GUIDE.md
  - VOICEMAIL_DATABASE_SETUP.md
- Testing documentation (2 files merged → TESTING_GUIDE.md):
  - TESTING_SETUP.md
  - TESTING_AD_INTEGRATION.md
- Quick reference documentation (2 files merged):
  - LICENSE_ADMIN_QUICKREF.md → LICENSE_ADMIN_INTERFACE.md
  - QUICK_IMPROVEMENT_GUIDE.md → PRODUCT_IMPROVEMENT_RECOMMENDATIONS.md
- Reverse proxy documentation (2 files merged → REVERSE_PROXY_SETUP.md):
  - QUICK_START_ABPS_SETUP.md
  - ABPS_IMPLEMENTATION_GUIDE.md
- Phone provisioning documentation (3 files consolidated → PHONE_PROVISIONING.md):
  - PHONE_CLEANUP_GUIDE.md
  - PROVISIONING_PERSISTENCE.md
  - PROVISIONING_TEMPLATE_CUSTOMIZATION.md

**Note:** All useful content from removed files has been preserved in consolidated guides. No information was lost.

### Documentation Statistics (All Consolidation Phases)
- **Phase 1 files removed**: 37 (31.4% reduction from 118 to 81)
- **Phase 2 files removed**: 34 (39% reduction from 87 to 53)
- **Total files removed**: 71+ across both phases
- **Final documentation count**: 53 markdown files (37 curated docs + 16 in-place READMEs)
- **Content preserved**: 100% - all useful content merged into comprehensive guides
- **Key consolidation targets**: COMPLETE_GUIDE.md, TROUBLESHOOTING.md, docs/ directory

### Fixed
- docker-compose compatibility: Downgraded requests library from 2.32.3 to 2.31.0 to fix `URLSchemeUnknown: Not supported URL scheme http+docker` error when building with docker-compose v1.29.2

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
