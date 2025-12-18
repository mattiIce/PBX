# PBX System Documentation Index

This document helps you navigate the comprehensive documentation for the PBX system.

## Executive Overview

For executives, managers, and decision-makers:

- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - Comprehensive executive summary with business value, ROI analysis, and strategic recommendations

## Getting Started

Start here if you're new to the PBX system:

1. **[README.md](README.md)** - Project overview, features, and basic usage
2. **[QUICK_START.md](QUICK_START.md)** - First-time setup checklist for quick deployment
3. **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation instructions
4. **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** - ⭐ **Complete feature status and implementation overview**

## Deployment Guides

Choose the guide that fits your deployment scenario:

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Step-by-step deployment guide for specific server setup
- **[UBUNTU_SETUP_GUIDE.md](UBUNTU_SETUP_GUIDE.md)** - Complete Ubuntu 24.04 LTS setup with all databases and services
- **[POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md)** - PostgreSQL database configuration for advanced features

## Feature Documentation

Learn about specific features:

- **[FEATURES.md](FEATURES.md)** - Complete list of all PBX features with descriptions
- **[CALL_FLOW.md](CALL_FLOW.md)** - How phone-to-phone calls work through the system
- **[PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)** - Auto-configuration for IP phones
- **[PHONE_REGISTRATION_TRACKING.md](PHONE_REGISTRATION_TRACKING.md)** - Automatic tracking of registered phones by MAC/IP address

## Migration & Import

Migrate from legacy phone systems:

- **[MERLIN_IMPORT_GUIDE.md](MERLIN_IMPORT_GUIDE.md)** - Import voicemail data from AT&T Merlin Legend systems

## Integration Guides

Connect the PBX with external services:

- **[OPEN_SOURCE_INTEGRATIONS.md](OPEN_SOURCE_INTEGRATIONS.md)** - ⭐ **Free integrations (Jitsi, Matrix, EspoCRM)**
- **[QUICK_SETUP_GUIDE.md](QUICK_SETUP_GUIDE.md)** - One-click integration setup
- **[INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md)** - Integration setup and fixes
- **[ENTERPRISE_INTEGRATIONS.md](ENTERPRISE_INTEGRATIONS.md)** - Zoom, Active Directory, Outlook, Teams integrations
- **[AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md)** - Active Directory user synchronization
- **[TESTING_AD_INTEGRATION.md](TESTING_AD_INTEGRATION.md)** - Testing Active Directory integration

## Security Documentation

Secure your PBX deployment:

- **[SECURITY_GUIDE.md](SECURITY_GUIDE.md)** - ⭐ **Complete security guide** (FIPS compliance, MFA, best practices, Ubuntu FIPS deployment)
  - Replaces: SECURITY.md, SECURITY_BEST_PRACTICES.md, SECURITY_IMPLEMENTATION.md, MFA_GUIDE.md, FIPS_COMPLIANCE_STATUS.md, UBUNTU_FIPS_GUIDE.md

## Regulations and Compliance

Ensure regulatory compliance:

- **[REGULATIONS_COMPLIANCE_GUIDE.md](REGULATIONS_COMPLIANCE_GUIDE.md)** - ⭐ **Complete compliance guide** (E911, Kari's Law, Multi-Site E911, STIR/SHAKEN, SOC 2)
  - Replaces: E911_PROTECTION_GUIDE.md, KARIS_LAW_GUIDE.md, MULTI_SITE_E911_GUIDE.md, STIR_SHAKEN_GUIDE.md, SOC2_TYPE2_IMPLEMENTATION.md

## Technical Implementation Guides

### Audio Codecs

- **[CODEC_IMPLEMENTATION_GUIDE.md](CODEC_IMPLEMENTATION_GUIDE.md)** - ⭐ **Complete codec guide** (G.711, G.722, Opus, G.729, G.726, iLBC, Speex, phone-specific configuration)
  - Replaces: G722_CODEC_GUIDE.md, G729_G726_CODEC_GUIDE.md, OPUS_CODEC_GUIDE.md, SPEEX_CODEC_GUIDE.md, ILBC_CODEC_GUIDE.md, PHONE_MODEL_CODEC_SELECTION.md, ZULTYS_ZIP33G_CODEC_CONFIGURATION.md
- **[CODEC_COMPARISON_GUIDE.md](CODEC_COMPARISON_GUIDE.md)** - Codec comparison matrix and decision guide

### DTMF Configuration

- **[DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md)** - ⭐ **Complete DTMF guide** (RFC 2833, SIP INFO, payload types, troubleshooting)
  - Replaces: DTMF_PAYLOAD_TYPE_CONFIGURATION.md, SIP_INFO_DTMF_GUIDE.md, RFC2833_IMPLEMENTATION_GUIDE.md, ZIP33G_DTMF_PAYLOAD_TYPE_RESOLUTION.md, ZULTYS_DTMF_TROUBLESHOOTING.md

### WebRTC

- **[WEBRTC_GUIDE.md](WEBRTC_GUIDE.md)** - ⭐ **Complete WebRTC guide** (browser calling, configuration, debugging, troubleshooting)
  - Replaces: WEBRTC_IMPLEMENTATION_GUIDE.md, WEBRTC_PHONE_USAGE.md, WEBRTC_VERBOSE_LOGGING.md, WEBRTC_ZIP33G_ALIGNMENT.md

### Voicemail

- **[VOICEMAIL_CUSTOM_GREETING_GUIDE.md](VOICEMAIL_CUSTOM_GREETING_GUIDE.md)** - Custom greetings, debugging, and VM IVR logging
  - Includes: DEBUG_VM_PIN.md, ENABLE_DEBUG_VM_PIN.md, VM_IVR_LOGGING.md
- **[VOICEMAIL_TRANSCRIPTION_GUIDE.md](VOICEMAIL_TRANSCRIPTION_GUIDE.md)** - Speech-to-text (OpenAI, Google Cloud, Vosk offline)
  - Includes: VOICEMAIL_TRANSCRIPTION_VOSK.md
- **[VOICEMAIL_EMAIL_GUIDE.md](VOICEMAIL_EMAIL_GUIDE.md)** - Voicemail-to-email configuration and usage
- **[VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md)** - Database configuration

## Development Documentation

For developers working on or extending the PBX:

- **[SUMMARY.md](SUMMARY.md)** - Project architecture and technical overview
- **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** - ⭐ **Complete feature implementation status**
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Requirements for implementing features
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing procedures and guidelines
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - REST API reference for custom integrations

## Troubleshooting

Common issues and solutions:

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - ⭐ **Comprehensive troubleshooting guide** (audio, integration, networking, config)
- **[FIXING_YAML_MERGE_CONFLICTS.md](FIXING_YAML_MERGE_CONFLICTS.md)** - How to resolve Git merge conflicts in config.yml
- **[TROUBLESHOOTING_PROVISIONING.md](TROUBLESHOOTING_PROVISIONING.md)** - Phone provisioning troubleshooting

## Quick Reference

### Essential Files

- **config.yml** - Main configuration file
- **.env.example** - Environment variables template for credentials
- **requirements.txt** - Python dependencies
- **main.py** - PBX system entry point

### Directory Structure

```
PBX/
├── admin/              # Web admin panel
├── examples/           # Example client code
├── pbx/                # Main PBX code
│   ├── api/           # REST API
│   ├── core/          # Core PBX logic
│   ├── features/      # Advanced features
│   ├── integrations/  # External integrations
│   ├── rtp/           # RTP media handling
│   ├── sip/           # SIP protocol
│   └── utils/         # Utilities
├── scripts/           # Utility scripts
├── tests/             # Test suite
└── logs/              # Log files (created at runtime)
```

## Documentation by Role

### System Administrator

Must read:
1. [INSTALLATION.md](INSTALLATION.md)
2. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) or [UBUNTU_SETUP_GUIDE.md](UBUNTU_SETUP_GUIDE.md)
3. [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Complete security reference
4. [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) (if using database features)
5. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) (for common issues)

### Network Administrator

Must read:
1. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. [CALL_FLOW.md](CALL_FLOW.md)
3. [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)
4. [SECURITY_GUIDE.md](SECURITY_GUIDE.md) (Network Security section)
5. [CODEC_IMPLEMENTATION_GUIDE.md](CODEC_IMPLEMENTATION_GUIDE.md)
6. [DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md)

### End User

Must read:
1. [README.md](README.md) (User sections)
2. [VOICEMAIL_EMAIL_GUIDE.md](VOICEMAIL_EMAIL_GUIDE.md)
3. [VOICEMAIL_CUSTOM_GREETING_GUIDE.md](VOICEMAIL_CUSTOM_GREETING_GUIDE.md)
4. [WEBRTC_GUIDE.md](WEBRTC_GUIDE.md) (for browser calling)
5. [QUICK_START.md](QUICK_START.md) (Basic usage)

### Developer

Must read:
1. [SUMMARY.md](SUMMARY.md)
2. [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) (feature status)
3. [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
4. [TODO.md](TODO.md) (for remaining work)
5. [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
6. [TESTING_GUIDE.md](TESTING_GUIDE.md)
7. [CODEC_IMPLEMENTATION_GUIDE.md](CODEC_IMPLEMENTATION_GUIDE.md)
8. [DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md)
9. [WEBRTC_GUIDE.md](WEBRTC_GUIDE.md)

### Security Officer

Must read:
1. [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Complete security and compliance reference
2. [REGULATIONS_COMPLIANCE_GUIDE.md](REGULATIONS_COMPLIANCE_GUIDE.md) - E911, Kari's Law, STIR/SHAKEN, SOC 2

### Compliance Officer

Must read:
1. [REGULATIONS_COMPLIANCE_GUIDE.md](REGULATIONS_COMPLIANCE_GUIDE.md) - Complete compliance guide
2. [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Security compliance
3. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

### Project Manager

Must read:
1. [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
2. [README.md](README.md)
3. [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) (feature status)
4. [FEATURES.md](FEATURES.md)
5. [SUMMARY.md](SUMMARY.md)
6. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

### Executive / Business Leader

Must read:
1. [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) (complete business case)
2. [README.md](README.md) (technical capabilities overview)
3. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) (implementation readiness)

## Support and Contributing

- **Issues**: Report issues on GitHub
- **Questions**: Check documentation first, then open a GitHub issue
- **Security**: Report security issues privately (see SECURITY_BEST_PRACTICES.md)

## Version History

This documentation is for PBX System v1.0.0

## Additional Resources

- GitHub Repository: https://github.com/mattiIce/PBX
- Python Documentation: https://docs.python.org/3/
- SIP Protocol (RFC 3261): https://tools.ietf.org/html/rfc3261
- RTP Protocol (RFC 3550): https://tools.ietf.org/html/rfc3550
