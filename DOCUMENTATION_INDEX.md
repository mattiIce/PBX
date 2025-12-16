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
- **[VOICEMAIL_EMAIL_GUIDE.md](VOICEMAIL_EMAIL_GUIDE.md)** - Voicemail-to-email configuration and usage
- **[VOICEMAIL_CUSTOM_GREETING_GUIDE.md](VOICEMAIL_CUSTOM_GREETING_GUIDE.md)** - Recording and managing custom voicemail greetings via IVR
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

- **[SECURITY.md](SECURITY.md)** - Security summary and CodeQL analysis results
- **[SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md)** - Comprehensive security guide for production
- **[FIPS_COMPLIANCE_STATUS.md](FIPS_COMPLIANCE_STATUS.md)** - ⭐ **Complete FIPS compliance reference** (consolidated guide)
- **[UBUNTU_FIPS_GUIDE.md](UBUNTU_FIPS_GUIDE.md)** - Ubuntu FIPS deployment guide

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
1. INSTALLATION.md
2. DEPLOYMENT_GUIDE.md or UBUNTU_SETUP_GUIDE.md
3. SECURITY_BEST_PRACTICES.md
4. POSTGRESQL_SETUP.md (if using database features)
5. TROUBLESHOOTING.md (for common issues)

### Network Administrator

Must read:
1. DEPLOYMENT_GUIDE.md
2. CALL_FLOW.md
3. PHONE_PROVISIONING.md
4. SECURITY_BEST_PRACTICES.md (Network Security section)

### End User

Must read:
1. README.md (User sections)
2. VOICEMAIL_EMAIL_GUIDE.md
3. QUICK_START.md (Basic usage)

### Developer

Must read:
1. SUMMARY.md
2. IMPLEMENTATION_STATUS.md (feature status)
3. API_DOCUMENTATION.md
4. TODO.md (for remaining work)
5. IMPLEMENTATION_GUIDE.md
6. TESTING_GUIDE.md

### Security Officer

Must read:
1. FIPS_COMPLIANCE_STATUS.md (complete compliance reference)
2. SECURITY.md
3. SECURITY_BEST_PRACTICES.md
4. UBUNTU_FIPS_GUIDE.md (deployment guide)

### Project Manager

Must read:
1. EXECUTIVE_SUMMARY.md
2. README.md
3. IMPLEMENTATION_STATUS.md (feature status)
4. FEATURES.md
5. SUMMARY.md
6. DEPLOYMENT_CHECKLIST.md

### Executive / Business Leader

Must read:
1. EXECUTIVE_SUMMARY.md (complete business case)
2. README.md (technical capabilities overview)
3. DEPLOYMENT_CHECKLIST.md (implementation readiness)

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
