# PBX System Documentation Index

This document helps you navigate the comprehensive documentation for the PBX system.

## Getting Started

Start here if you're new to the PBX system:

1. **[README.md](README.md)** - Project overview, features, and basic usage
2. **[QUICK_START.md](QUICK_START.md)** - First-time setup checklist for quick deployment
3. **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation instructions

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
- **[PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)** - Auto-configuration for IP phones
- **[PHONE_REGISTRATION_TRACKING.md](PHONE_REGISTRATION_TRACKING.md)** - Automatic tracking of registered phones by MAC/IP address

## Integration Guides

Connect the PBX with external services:

- **[ENTERPRISE_INTEGRATIONS.md](ENTERPRISE_INTEGRATIONS.md)** - Zoom, Active Directory, Outlook, Teams integrations
- **[AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md)** - Active Directory user synchronization
- **[TESTING_AD_INTEGRATION.md](TESTING_AD_INTEGRATION.md)** - Testing Active Directory integration

## Security Documentation

Secure your PBX deployment:

- **[SECURITY.md](SECURITY.md)** - Security summary and CodeQL analysis results
- **[SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md)** - Comprehensive security guide for production
- **[FIPS_COMPLIANCE.md](FIPS_COMPLIANCE.md)** - FIPS 140-2 compliance guide for regulated industries

## Development Documentation

For developers working on or extending the PBX:

- **[SUMMARY.md](SUMMARY.md)** - Project architecture and technical overview
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Requirements for implementing features
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing procedures and guidelines
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - REST API reference for custom integrations

## Troubleshooting

Common issues and solutions:

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
2. API_DOCUMENTATION.md
3. STUB_AND_TODO_ANALYSIS.md (for remaining work)
4. IMPLEMENTATION_GUIDE.md
5. TESTING_GUIDE.md

### Security Officer

Must read:
1. SECURITY.md
2. SECURITY_BEST_PRACTICES.md
3. FIPS_COMPLIANCE.md

### Project Manager

Must read:
1. README.md
2. FEATURES.md
3. SUMMARY.md
4. DEPLOYMENT_CHECKLIST.md

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
