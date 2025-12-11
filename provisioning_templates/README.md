# Provisioning Templates Directory

This directory contains customizable phone provisioning templates that override the built-in templates.

## Directory Structure

Place your custom templates here with the naming convention:
```
{vendor}_{model}.template
```

For example:
- `yealink_t28g.template` - Template for Yealink T28G phones
- `yealink_t46s.template` - Template for Yealink T46S phones
- `polycom_vvx450.template` - Template for Polycom VVX 450 phones
- `zultys_zip33g.template` - Template for Zultys ZIP 33G phones

## Template Placeholders

All templates support the following placeholders that are automatically replaced with device-specific information:

- `{{EXTENSION_NUMBER}}` - The extension number (e.g., "1001")
- `{{EXTENSION_NAME}}` - The user's display name (e.g., "John Smith")
- `{{EXTENSION_PASSWORD}}` - The SIP authentication password for this extension
- `{{SIP_SERVER}}` - The PBX server IP address
- `{{SIP_PORT}}` - The SIP server port (typically 5060)
- `{{SERVER_NAME}}` - The PBX server name

## How to Customize Templates

### Option 1: Export All Templates at Once (Recommended)
Use the command-line script to export all built-in templates:
```bash
python scripts/export_all_templates.py
```
This will export all 7 built-in templates (Zultys ZIP 33G, Zultys ZIP 37G, Yealink T28G, Yealink T46S, Polycom VVX 450, Cisco SPA504G, Grandstream GXP2170) to this directory. You can then edit any template you want to customize.

### Option 2: Export via Admin Panel
1. Access the admin panel at `http://your-pbx-ip:8080/admin/`
2. Go to the "Phone Provisioning" tab
3. Click "View Templates"
4. Select a template and click "Export to File"
5. The template will be saved to this directory
6. Edit the exported file with your customizations

### Option 3: Create from Scratch
1. Create a new `.template` file following the naming convention
2. Add your configuration using vendor-specific syntax
3. Use placeholders ({{EXTENSION_NUMBER}}, etc.) where dynamic values are needed
4. Save the file
5. Restart the PBX or reload templates via API

### Option 4: Use the API
```bash
# View a template
curl http://your-pbx-ip:8080/api/provisioning/templates/yealink/t46s

# Export template to file
curl -X POST http://your-pbx-ip:8080/api/provisioning/templates/yealink/t46s/export

# Update template
curl -X PUT http://your-pbx-ip:8080/api/provisioning/templates/yealink/t46s \
  -H "Content-Type: application/json" \
  -d '{"content": "your template content here"}'
```

## Template Priority

When a phone requests configuration:
1. First, the system checks this directory for a matching custom template
2. If no custom template exists, it uses the built-in template
3. Built-in templates are always available as fallback

## Supported Vendors and Models

Built-in templates are available for:
- **Zultys**: zip33g, zip37g
- **Yealink**: t28g, t46s
- **Polycom**: vvx450
- **Cisco**: spa504g
- **Grandstream**: gxp2170

You can add templates for additional models by creating new `.template` files.

## DTMF Configuration

The PBX system supports multiple DTMF (touch-tone) signaling methods. Templates are pre-configured to use **SIP INFO** for DTMF transport, which is compatible with the PBX's voicemail IVR system.

### DTMF Transport Methods

1. **In-band (In-audio)**: DTMF tones sent as audio in the RTP stream
   - Detected using audio analysis (Goertzel algorithm)
   - Can be affected by audio codecs and quality

2. **RFC 2833 (RTP Events)**: DTMF sent as RTP events 
   - Separate from audio stream
   - Payload type typically 101

3. **SIP INFO**: DTMF sent as SIP INFO messages
   - Out-of-band signaling
   - Most reliable method
   - **Recommended for this PBX system**

### Template DTMF Settings

**Grandstream (GXP2170)**:
```
P79 = 2    # DTMF Type: 0=In-audio, 1=RFC2833, 2=SIP INFO
P184 = 0   # DTMF Info Type: 0=DTMF, 1=DTMF-Relay
P78 = 101  # DTMF Payload Type (for RFC2833)
```

**Yealink (T46S)**:
```
account.1.dtmf.type = 2          # 0=Inband, 1=RFC2833, 2=SIP INFO
account.1.dtmf.info_type = 0     # 0=DTMF, 1=DTMF-Relay
account.1.dtmf.dtmf_payload = 101  # Payload type for RFC2833
```

The PBX automatically handles DTMF from both **SIP INFO** messages and **in-band** detection, ensuring compatibility with various phone configurations.

## Example: Customizing a Yealink T46S Template

1. Export the built-in template:
   ```bash
   curl -X POST http://localhost:8080/api/provisioning/templates/yealink/t46s/export
   ```

2. Edit `yealink_t46s.template`:
   ```ini
   #!version:1.0.0.1
   
   # Account 1
   account.1.enable = 1
   account.1.label = {{EXTENSION_NAME}}
   account.1.display_name = {{EXTENSION_NAME}}
   account.1.auth_name = {{EXTENSION_NUMBER}}
   account.1.user_name = {{EXTENSION_NUMBER}}
   account.1.password = {{EXTENSION_PASSWORD}}
   account.1.sip_server.1.address = {{SIP_SERVER}}
   account.1.sip_server.1.port = {{SIP_PORT}}
   
   # Add your customizations here
   account.1.codec.1.enable = 1
   account.1.codec.1.payload_type = PCMU
   
   # Custom settings
   phone.background_image = http://your-server/logo.jpg
   phone.screensaver.enable = 1
   ```

3. Save and reload:
   ```bash
   curl -X POST http://localhost:8080/api/provisioning/reload-templates
   ```

## Template Testing

After customizing a template, test it by:
1. Requesting the configuration file: `curl http://your-pbx-ip:8080/provision/001122334455.cfg`
2. Verify all placeholders are replaced correctly
3. Check that device-specific information appears where expected

## Automatic Configuration

When you register a device via the admin console or API:
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

The system automatically:
1. Looks up the extension information (name, password)
2. Loads the appropriate template (custom or built-in)
3. Replaces all placeholders with actual values
4. Generates a ready-to-use configuration file
5. Triggers phone reboot if extension is registered

## Troubleshooting

If a phone isn't provisioning correctly:
1. Check that the template file exists and has correct naming
2. Verify placeholders are using correct syntax: `{{PLACEHOLDER}}` not `{PLACEHOLDER}`
3. Check PBX logs: `tail -f logs/pbx.log | grep -i provision`
4. Test template generation: `curl http://your-pbx-ip:8080/provision/{mac}.cfg`
5. Use diagnostics: `curl http://your-pbx-ip:8080/api/provisioning/diagnostics`

## Security Notes

- Templates are plain text and may contain sensitive configuration
- Keep this directory readable only by the PBX process
- Avoid committing templates with hardcoded credentials to version control
- Use placeholders for all sensitive data

## Documentation

For more information, see:
- [PHONE_PROVISIONING.md](../PHONE_PROVISIONING.md) - Complete provisioning guide
- [TROUBLESHOOTING_PROVISIONING.md](../TROUBLESHOOTING_PROVISIONING.md) - Troubleshooting guide
