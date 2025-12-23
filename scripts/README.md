# PBX Scripts Directory

This directory contains utility scripts for managing and configuring the PBX system.

## ⚠️ IMPORTANT: Shell Scripts vs Python Scripts

This directory contains **two types** of scripts:

### Shell Scripts (.sh files) - Run with `bash`
Shell scripts **MUST** be run with `bash` or `sh`, **NOT** with `python3`:

```bash
# ✅ CORRECT - Run with bash
bash scripts/update_server_from_repo.sh
bash scripts/diagnose_server.sh
bash scripts/emergency_recovery.sh

# ❌ WRONG - Do NOT run with python3
python3 scripts/update_server_from_repo.sh  # This will cause syntax errors!
```

**Common Error:**
```
File "/root/PBX/scripts/update_server_from_repo.sh", line 8
    echo "=========================================="
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: invalid syntax
```

If you see this error, you're trying to run a shell script with Python. Use `bash` instead.

### Python Scripts (.py files) - Run with `python3`
Python scripts should be run with `python3`:

```bash
# ✅ CORRECT - Run with python3
python3 scripts/dtmf_payload_selector.py
python3 scripts/init_database.py
```

---

## Server Management Scripts (Shell Scripts)

### update_server_from_repo.sh
Interactive script to update the server from the git repository with safety checks and confirmations.

**Usage:**
```bash
cd /root/PBX
bash scripts/update_server_from_repo.sh
```

See [SERVER_UPDATE_GUIDE.md](../SERVER_UPDATE_GUIDE.md) for details.

### force_update_server.sh
Non-interactive script for automated updates without prompts.

**Usage:**
```bash
cd /root/PBX
bash scripts/force_update_server.sh
```

### diagnose_server.sh
Diagnostic script to check server status, git state, and common issues.

**Usage:**
```bash
cd /root/PBX
bash scripts/diagnose_server.sh
```

### emergency_recovery.sh
Emergency recovery script for restoring server to a working state.

**Usage:**
```bash
cd /root/PBX
bash scripts/emergency_recovery.sh
```

### setup_reverse_proxy.sh
Setup script for configuring Nginx reverse proxy with SSL.

**Usage:**
```bash
sudo bash scripts/setup_reverse_proxy.sh
```

See [ABPS_IMPLEMENTATION_GUIDE.md](../ABPS_IMPLEMENTATION_GUIDE.md) for details.

### enable_fips_ubuntu.sh
Enable FIPS 140-2 compliance mode on Ubuntu systems.

**Usage:**
```bash
sudo bash scripts/enable_fips_ubuntu.sh
```

See [UBUNTU_FIPS_GUIDE.md](../UBUNTU_FIPS_GUIDE.md) for details.

### deploy_production_pilot.sh
Automated production deployment script for Ubuntu 24.04 LTS.

**Usage:**
```bash
# Dry run (test without making changes)
sudo bash scripts/deploy_production_pilot.sh --dry-run

# Actual deployment (requires root)
sudo bash scripts/deploy_production_pilot.sh
```

See [README_CRITICAL_BLOCKERS.md](README_CRITICAL_BLOCKERS.md) for details.

---

## Python Scripts

### DTMF Configuration

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

✓ See DTMF_PAYLOAD_TYPE_CONFIGURATION.md for detailed guide
═══════════════════════════════════════════════════════════
```

**Related Documentation:**
- [DTMF_PAYLOAD_TYPE_CONFIGURATION.md](../DTMF_PAYLOAD_TYPE_CONFIGURATION.md) - Complete configuration guide
- [ZIP33G_DTMF_PAYLOAD_TYPE_RESOLUTION.md](../ZIP33G_DTMF_PAYLOAD_TYPE_RESOLUTION.md) - Resolution summary

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
- `enable_fips_ubuntu.sh` - **(Shell script)** Enable FIPS mode on Ubuntu - run with `bash`
- `check_fips_health.py` - Check FIPS compliance status

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

**Python scripts (.py files):**

```bash
python scripts/<script_name>.py
```

**Shell scripts (.sh files):**

```bash
bash scripts/<script_name>.sh
```

Some scripts may require root privileges or specific configuration.

For script-specific help, run:

```bash
python scripts/<script_name>.py --help
```

Or check the script's source code for documentation.
