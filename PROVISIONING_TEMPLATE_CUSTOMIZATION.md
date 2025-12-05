# Provisioning Template Customization Guide

This guide explains how to view, customize, and manage phone provisioning templates in the PBX system.

## Overview

The PBX system automatically generates phone configuration files based on templates. Each template contains placeholders that are automatically replaced with device-specific information when a phone requests its configuration.

## Where Are Provisioning Files Located?

### Built-in Templates
Built-in templates are embedded in the code at:
```
pbx/features/phone_provisioning.py
```

These templates are loaded automatically and provide default configurations for:
- **Zultys**: ZIP 33G, ZIP 37G
- **Yealink**: T46S
- **Polycom**: VVX 450
- **Cisco**: SPA504G
- **Grandstream**: GXP2170

### Custom Templates
Custom templates (which override built-in templates) are stored in:
```
provisioning_templates/
```

This directory is created automatically and is where you can place customized templates.

## How Auto-Provisioning Works

When you register a device via the admin console:

1. **Admin registers device:**
   ```bash
   curl -X POST http://your-pbx-ip:8080/api/provisioning/devices \
     -H "Content-Type: application/json" \
     -d '{
       "mac_address": "00:15:65:12:34:56",
       "extension_number": "1001",
       "vendor": "yealink",
       "model": "t46s"
     }'
   ```

2. **System looks up extension information:**
   - Extension number: `1001`
   - Extension name: `John Smith` (from config or Active Directory)
   - Extension password: `password1001` (from config)
   - SIP server: `192.168.1.14` (from server.external_ip in config)
   - SIP port: `5060` (from server.sip_port in config)

3. **System loads appropriate template:**
   - First checks `provisioning_templates/yealink_t46s.template`
   - If not found, uses built-in template

4. **System replaces placeholders:**
   ```
   {{EXTENSION_NUMBER}} → 1001
   {{EXTENSION_NAME}} → John Smith
   {{EXTENSION_PASSWORD}} → password1001
   {{SIP_SERVER}} → 192.168.1.14
   {{SIP_PORT}} → 5060
   {{SERVER_NAME}} → Aluminum Blanking Phone System
   ```

5. **Phone downloads configuration:**
   - Phone requests: `http://192.168.1.14:8080/provision/001565123456.cfg`
   - Receives fully populated configuration file ready to use

6. **Phone automatically configures itself:**
   - Extension registered with correct credentials
   - Display name shows "John Smith"
   - All settings applied from template

## Available Placeholders

All templates support these placeholders:

| Placeholder | Description | Example Value |
|-------------|-------------|---------------|
| `{{EXTENSION_NUMBER}}` | Extension number | `1001` |
| `{{EXTENSION_NAME}}` | User's display name | `John Smith` |
| `{{EXTENSION_PASSWORD}}` | SIP authentication password | `password1001` |
| `{{SIP_SERVER}}` | PBX server IP address | `192.168.1.14` |
| `{{SIP_PORT}}` | SIP server port | `5060` |
| `{{SERVER_NAME}}` | PBX server name | `Aluminum Blanking Phone System` |

**Important:** 
- Extension name automatically syncs from Active Directory (if enabled)
- Placeholders are replaced EVERY TIME a phone requests configuration
- Always use `{{PLACEHOLDER}}` format (double curly braces)

## Viewing Templates

### Via Admin Web Interface

1. Access admin panel: `http://your-pbx-ip:8080/admin/`
2. Click on **"Phone Provisioning"** tab
3. Scroll to **"Provisioning Templates"** section
4. Click **"Refresh Templates"** to load the list
5. Click **"👁️ View"** next to any template

The view will show:
- Complete template content
- Available placeholders
- Template type (Built-in or Custom)
- Template size

### Via API

```bash
# List all templates
curl http://your-pbx-ip:8080/api/provisioning/templates

# View specific template
curl http://your-pbx-ip:8080/api/provisioning/templates/yealink/t46s
```

### Via Command Line

```bash
# View custom template if it exists
cat provisioning_templates/yealink_t46s.template

# View built-in templates (in source code)
grep -A 50 "yealink_t46s_template = " pbx/features/phone_provisioning.py
```

## Customizing Templates

### Method 1: Via Admin Web Interface (Recommended)

1. **Export a built-in template:**
   - Go to admin panel → Phone Provisioning → Provisioning Templates
   - Find the template you want to customize
   - Click **"💾 Export"**
   - Template is saved to `provisioning_templates/` directory

2. **Edit the template:**
   - Click **"✏️ Edit"** next to the custom template
   - Modify the template content in the editor
   - Keep placeholders intact: `{{EXTENSION_NAME}}`, etc.
   - Click **"💾 Save Changes"**

3. **Reload templates:**
   - Click **"♻️ Reload from Disk"**
   - System will reload all templates including your changes

### Method 2: Via API

```bash
# Export template to file
curl -X POST http://your-pbx-ip:8080/api/provisioning/templates/yealink/t46s/export

# Update template content
curl -X PUT http://your-pbx-ip:8080/api/provisioning/templates/yealink/t46s \
  -H "Content-Type: application/json" \
  -d '{"content": "your modified template content here"}'

# Reload all templates from disk
curl -X POST http://your-pbx-ip:8080/api/provisioning/reload-templates
```

### Method 3: Direct File Editing

1. **Export or create template file:**
   ```bash
   # Create custom template directory if it doesn't exist
   mkdir -p provisioning_templates
   
   # Copy from built-in or create new
   nano provisioning_templates/yealink_t46s.template
   ```

2. **Edit the template:**
   - Use any text editor
   - Keep placeholders intact
   - Add your customizations

3. **Reload templates:**
   ```bash
   # Via API
   curl -X POST http://your-pbx-ip:8080/api/provisioning/reload-templates
   
   # Or restart PBX server
   python main.py
   ```

## Example: Customizing Yealink T46S Template

### Step 1: Export Built-in Template

Via admin UI or API:
```bash
curl -X POST http://localhost:8080/api/provisioning/templates/yealink/t46s/export
```

This creates: `provisioning_templates/yealink_t46s.template`

### Step 2: View Original Template

```ini
#!version:1.0.0.1

# Yealink T46S Configuration File

# Account 1
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600

# Codecs
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = PCMU
account.1.codec.2.enable = 1
account.1.codec.2.payload_type = PCMA
account.1.codec.3.enable = 1
account.1.codec.3.payload_type = G729

# Network
network.internet_port.type = 0
network.internet_port.dhcp = 1

# Time
local_time.time_zone = -8
local_time.ntp_server1 = pool.ntp.org
```

### Step 3: Add Customizations

Edit `provisioning_templates/yealink_t46s.template`:

```ini
#!version:1.0.0.1

# Yealink T46S Configuration File - Custom for Aluminum Blanking

# Account 1
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600

# Codecs - Prioritize G.711 PCMU
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = PCMU
account.1.codec.2.enable = 1
account.1.codec.2.payload_type = PCMA
account.1.codec.3.enable = 0
account.1.codec.3.payload_type = G729

# Network
network.internet_port.type = 0
network.internet_port.dhcp = 1
network.vlan.internet_port_enable = 0

# Time - US Pacific
local_time.time_zone = -8
local_time.ntp_server1 = pool.ntp.org
local_time.summer_time = 2

# Custom: Company branding
phone.background_image.url = http://192.168.1.14/images/company_logo.jpg
phone.screensaver.type = 1

# Custom: Call settings
call_waiting.enable = 1
call_forward.always.enable = 0
dnd.enable = 0

# Custom: Audio settings
audio.ringtone.speaker_volume = 8
audio.handset.receive_gain = 6
audio.handsfree.receive_gain = 6

# Custom: Button mapping - Speed dials
programablekey.1.type = 10
programablekey.1.line = 1
programablekey.1.value = 1002
programablekey.1.label = Reception

programablekey.2.type = 10
programablekey.2.line = 1
programablekey.2.value = 1003
programablekey.2.label = Manager
```

### Step 4: Reload and Test

```bash
# Reload templates
curl -X POST http://localhost:8080/api/provisioning/reload-templates

# Test configuration generation
curl http://localhost:8080/provision/001565123456.cfg

# Verify placeholders are replaced:
# - {{EXTENSION_NAME}} should show actual name
# - {{EXTENSION_NUMBER}} should show actual extension
# - etc.
```

## Adding Templates for New Phone Models

To add support for a new phone model:

### 1. Create Template File

Create `provisioning_templates/{vendor}_{model}.template`:

```bash
nano provisioning_templates/yealink_t57w.template
```

### 2. Add Template Content

Use vendor-specific configuration syntax with placeholders:

```ini
#!version:1.0.0.1

# Yealink T57W Configuration File

# Account 1
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}

# T57W specific features
wifi.enable = 1
bluetooth.enable = 1
# ... more settings ...
```

### 3. Reload Templates

```bash
curl -X POST http://localhost:8080/api/provisioning/reload-templates
```

### 4. Register Device

```bash
curl -X POST http://localhost:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:15:65:AB:CD:EF",
    "extension_number": "1005",
    "vendor": "yealink",
    "model": "t57w"
  }'
```

## Template Priority

When a phone requests configuration:

1. System first checks `provisioning_templates/{vendor}_{model}.template`
2. If custom template exists, uses that
3. Otherwise, falls back to built-in template
4. If no template found, returns error

This means:
- ✓ Custom templates override built-in templates
- ✓ You can customize some models and leave others as default
- ✓ Built-in templates are always available as fallback

## Testing Templates

After customizing a template, test it:

### 1. Test Configuration Generation

```bash
# Generate config for a registered device
curl http://your-pbx-ip:8080/provision/001565123456.cfg
```

### 2. Verify Placeholders Replaced

Check that the output contains actual values, not placeholders:

```bash
curl http://your-pbx-ip:8080/provision/001565123456.cfg | grep -E "(EXTENSION_|SIP_|SERVER_)"
```

Should return nothing if all placeholders are replaced.

### 3. Verify Device-Specific Information

```bash
curl http://your-pbx-ip:8080/provision/001565123456.cfg | grep -E "(1001|John Smith|192.168.1.14)"
```

Should show actual extension number, name, and server IP.

### 4. Test on Actual Phone

1. Reboot the phone
2. Phone will request: `http://your-pbx-ip:8080/provision/$mac.cfg`
3. Check phone display shows correct name
4. Verify all your custom settings are applied

## Troubleshooting

### Template Not Loading

**Problem:** Changes to template not appearing

**Solution:**
```bash
# Reload templates
curl -X POST http://localhost:8080/api/provisioning/reload-templates

# Or restart PBX
python main.py
```

### Placeholders Not Replaced

**Problem:** Config file shows `{{EXTENSION_NUMBER}}` instead of actual number

**Possible causes:**
1. Device not registered in provisioning system
2. Extension not found in config
3. Typo in placeholder name

**Solution:**
```bash
# Verify device registered
curl http://your-pbx-ip:8080/api/provisioning/devices

# Verify extension exists
curl http://your-pbx-ip:8080/api/extensions

# Check placeholder syntax (must be {{PLACEHOLDER}} not {PLACEHOLDER})
```

### Phone Not Applying Config

**Problem:** Phone doesn't show customizations

**Possible causes:**
1. Phone using cached config
2. Phone requesting wrong MAC format
3. Template has syntax errors

**Solution:**
```bash
# Check provisioning logs
tail -f logs/pbx.log | grep -i provision

# Verify phone is requesting config
# Check for MAC address in logs

# Test config manually
curl http://your-pbx-ip:8080/provision/YOUR_PHONE_MAC.cfg
```

## Best Practices

1. **Always Keep Placeholders:**
   - Don't hardcode values that should be dynamic
   - Use `{{EXTENSION_NAME}}` not `"John Smith"`

2. **Test Before Deployment:**
   - Test custom templates with test phones first
   - Verify all features work as expected

3. **Document Customizations:**
   - Add comments in template explaining custom settings
   - Keep notes on why changes were made

4. **Backup Templates:**
   - Keep backup copies of working templates
   - Use version control for template directory

5. **Use Version Comments:**
   ```ini
   # Custom Template v1.2
   # Last modified: 2025-12-05
   # Changes: Added speed dial buttons
   ```

## Related Documentation

- [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md) - Complete provisioning guide
- [provisioning_templates/README.md](provisioning_templates/README.md) - Templates directory documentation
- [TROUBLESHOOTING_PROVISIONING.md](TROUBLESHOOTING_PROVISIONING.md) - Troubleshooting guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API reference

## Support

For additional help:
1. Check logs: `tail -f logs/pbx.log | grep -i provision`
2. Use diagnostics: `curl http://your-pbx-ip:8080/api/provisioning/diagnostics`
3. Consult vendor documentation for phone-specific configuration syntax
