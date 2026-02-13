# PBX Scripts Directory

This directory contains utility scripts for managing and configuring the PBX system.

## DTMF Configuration

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

**Example session:**
```
$ python scripts/dtmf_payload_selector.py

═══════════════════════════════════════════════════════════
   DTMF RFC2833 Payload Type Selector
═══════════════════════════════════════════════════════════

Step 1: Current Status

Is DTMF currently working with payload type 101?
  1. Yes, it's working fine
  2. No, DTMF is not working
  3. I'm not sure / new setup

Enter choice (1-3): 2

Step 2: Equipment Information

What type of equipment are you using?
  1. Cisco phones or equipment
  2. Polycom phones
  3. Yealink, Zultys, or Grandstream phones
  4. SIP trunk from major carrier (Verizon, AT&T, etc.)
  5. Other / Not sure

Enter choice (1-5): 3

✓ Recommendation: Try alternatives in this order

Recommended testing order:
  1. Payload type 100 (most common alternative)
  2. Payload type 102 (carrier alternative)
  3. Payload type 96 (generic fallback)
  4. Payload type 101 (standard)

═══════════════════════════════════════════════════════════
Configuration Instructions

1. Edit config.yml:
   vim config.yml

2. Find the DTMF configuration section and change:
   features:
     dtmf:
       payload_type: 100  # Changed from 101

3. Restart the PBX:
   sudo systemctl restart pbx

4. Reprovision phones:
   - Reboot phones, OR
   - On phone: Menu → Settings → Auto Provision → Provision Now

5. Test DTMF:
   - Call voicemail: *<extension>
   - Enter PIN and verify it's recognized
   - Test auto-attendant navigation

✓ See COMPLETE_GUIDE.md for detailed guide
═══════════════════════════════════════════════════════════
```

**Related Documentation:**
- [COMPLETE_GUIDE.md - Section 3: Core Features](../COMPLETE_GUIDE.md#3-core-features--configuration) - DTMF configuration
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Troubleshooting guide

---

## Other Scripts

### Voice Generation

See [README_VOICE_GENERATION.md](README_VOICE_GENERATION.md) for voice and TTS prompt generation scripts.

### Database Management

- `init_database.py` - Initialize the PBX database
- `migrate_extensions_to_db.py` - Migrate extensions from config to database
- `migrate_passwords_to_database.py` - Migrate passwords to database
- `list_extensions_from_db.py` - List all extensions in database

### Security & SSL

- `generate_ssl_cert.py` - Generate self-signed SSL certificates
- `request_ca_cert.py` - Request certificate from internal CA
- `enable_fips_ubuntu.sh` - Enable FIPS mode on Ubuntu
- `check_fips_health.py` - Check FIPS compliance status
- `security_compliance_check.py` - Comprehensive FIPS 140-2 and SOC 2 Type 2 compliance check
- `test_soc2_controls.py` - Automated SOC 2 Type 2 control testing
- `verify_fips.py` - Detailed FIPS 140-2 compliance verification

See [README_SECURITY_COMPLIANCE.md](README_SECURITY_COMPLIANCE.md) for security and compliance documentation.

### Phone Provisioning

- `export_all_templates.py` - Export all phone provisioning templates
- `cleanup_config_extensions.py` - Clean up extension configurations

### Voicemail

- `import_merlin_voicemail.py` - Import voicemail from Merlin system
- `check_voicemail_storage.py` - Check voicemail storage usage

### Quality of Service

- `diagnose_qos.py` - Diagnose QoS issues and network quality

---

## General Usage Notes

Most scripts can be run directly:

```bash
python scripts/<script_name>.py
```

Some scripts may require root privileges or specific configuration.

For script-specific help, run:

```bash
python scripts/<script_name>.py --help
```

Or check the script's source code for documentation.
