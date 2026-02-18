# PBX Scripts Directory

This directory contains 62 utility scripts for managing, configuring, testing, and deploying the PBX system, organized by function.

---

## Setup & Installation

- `setup_ubuntu.py` - Automated Ubuntu setup wizard (installs dependencies, configures PostgreSQL, generates SSL certs, creates voice prompts, initializes database)
- `setup_env.py` - Interactive environment setup (creates `.env` file with credentials)
- `setup_production_env.py` - Production environment configuration
- `setup_integrations.py` - Third-party integration setup (AD, CRM, Teams, etc.)
- `install_integrations.py` - Install integration dependencies
- `setup_phone_provisioning.py` - Phone provisioning setup
- `setup_reverse_proxy.sh` - Nginx reverse proxy setup with SSL
- `setup_apache_reverse_proxy.sh` - Apache reverse proxy setup with SSL

## Deployment & Updates

- `deploy_production_pilot.sh` - Automated production deployment (PostgreSQL, Python venv, Nginx, UFW, backups, Prometheus, systemd)
- `zero_downtime_deploy.sh` - Zero-downtime deployment with rolling updates
- `force_update_server.sh` - Force update server from repository
- `update_server_from_repo.sh` - Update server from git repository
- `release.sh` - Release management
- `backup.sh` - System backup
- `verify_backup.py` - Verify backup integrity
- `emergency_recovery.sh` - Emergency recovery procedures

## Database Management

- `init_database.py` - Initialize the PBX database schema and tables
- `migrate_extensions_to_db.py` - Migrate extensions from config.yml to database
- `migrate_passwords_to_database.py` - Migrate passwords to database
- `list_extensions_from_db.py` - List all extensions stored in database
- `seed_extensions.py` - Seed database with sample extensions
- `verify_database.py` - Verify database integrity and connectivity
- `update_phone_extension.py` - Update phone extension configuration

## Security & Compliance

- `generate_ssl_cert.py` - Generate self-signed SSL certificates
- `request_ca_cert.py` - Request certificate from internal CA
- `letsencrypt_manager.py` - Let's Encrypt certificate management
- `enable_fips_ubuntu.sh` - Enable FIPS mode on Ubuntu (requires Ubuntu Pro)
- `check_fips_health.py` - Quick FIPS compliance health check
- `verify_fips.py` - Detailed FIPS 140-2 compliance verification
- `security_compliance_check.py` - Comprehensive FIPS 140-2 and SOC 2 Type 2 compliance check
- `test_soc2_controls.py` - Automated SOC 2 Type 2 control testing (16 controls)
- `compliance_report.py` - Generate compliance reports
- `run_compliance_check.sh` - Run compliance checks (shell wrapper)

See [README_SECURITY_COMPLIANCE.md](README_SECURITY_COMPLIANCE.md) for detailed security and compliance documentation.

## Voice Generation

- `generate_espeak_voices.py` - Generate professional voice prompts using gTTS (recommended)
- `generate_tts_prompts.py` - Generate TTS voice prompts using gTTS (compatibility alias)
- `generate_moh_music.py` - Generate music on hold tracks

See [README_VOICE_GENERATION.md](README_VOICE_GENERATION.md) for full voice generation documentation.

## Testing & Validation

- `smoke_tests.py` - Quick smoke tests for basic functionality
- `production_validation.py` - Production deployment validation
- `production_health_check.py` - Production health check
- `validate_production_readiness.py` - Validate production readiness against checklist
- `test_ad_integration.py` - Test Active Directory integration
- `test_audio_comprehensive.py` - Comprehensive audio testing
- `test_disaster_recovery.py` - Test disaster recovery procedures
- `test_menu_endpoints.py` - Test menu API endpoints
- `test_moh.py` - Test music on hold functionality
- `test_webrtc_audio.py` - Test WebRTC audio functionality

## Monitoring & Diagnostics

- `health_monitor.py` - System health monitoring
- `diagnose_server.sh` - Server diagnostics
- `diagnose_qos.py` - Diagnose QoS issues and network quality
- `verify_qos_fix.py` - Verify QoS fixes
- `load_test_sip.py` - SIP load testing
- `benchmark_performance.py` - Performance benchmarking
- `capacity_calculator.py` - Capacity planning calculator

## Phone Provisioning & DTMF

- `export_all_templates.py` - Export all phone provisioning templates
- `cleanup_config_extensions.py` - Clean up extension configurations
- `troubleshoot_provisioning.py` - Troubleshoot provisioning issues
- `dtmf_payload_selector.py` - Interactive DTMF payload type selector

### dtmf_payload_selector.py

**Interactive tool to help choose the right RFC2833 DTMF payload type.**

When DTMF isn't working properly, this tool helps you identify which payload type to use based on your equipment and symptoms.

**Usage:**

```bash
# Interactive mode (recommended)
python scripts/dtmf_payload_selector.py

# Show all available payload types
python scripts/dtmf_payload_selector.py --list

# Show help
python scripts/dtmf_payload_selector.py --help
```

**Features:**
- Asks questions about your setup (phone model, carrier, symptoms)
- Recommends the best payload type to try
- Shows step-by-step configuration instructions
- Lists all available payload types with descriptions
- Explains when to use each option

**Related Documentation:**
- [COMPLETE_GUIDE.md - Section 3: Core Features](../COMPLETE_GUIDE.md#3-core-features--configuration) - DTMF configuration
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Troubleshooting guide

## Voicemail & Data Migration

- `import_merlin_voicemail.py` - Import voicemail from AT&T Merlin Legend systems
- `check_voicemail_storage.py` - Check voicemail storage usage

## Integration & Sync

- `sync_ad_users.py` - Sync Active Directory users to PBX extensions

## License Management

- `license_manager.py` - License generation, installation, status, and management (CLI tool)

## Utilities

- `convert_troubleshooting_to_html.py` - Convert troubleshooting docs to HTML format

---

## General Usage Notes

Most scripts can be run directly:

```bash
python scripts/<script_name>.py
```

Some scripts require root privileges (especially setup and deployment scripts):

```bash
sudo python scripts/setup_ubuntu.py
sudo bash scripts/deploy_production_pilot.sh
```

For script-specific help, run:

```bash
python scripts/<script_name>.py --help
```

## Related Documentation

- [README_VOICE_GENERATION.md](README_VOICE_GENERATION.md) - Voice and TTS prompt generation
- [README_SECURITY_COMPLIANCE.md](README_SECURITY_COMPLIANCE.md) - Security and compliance checking
- [COMPLETE_GUIDE.md](../COMPLETE_GUIDE.md) - Comprehensive PBX documentation
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Troubleshooting guide
