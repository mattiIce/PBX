# Zultys Phone Configuration Format Analysis

## Summary of Findings

After analyzing exported configuration files from actual Zultys phones, we've discovered important differences between the ZIP 33G and ZIP 37G models.

## Configuration File Formats

### ZIP 33G Format
- **File Type**: Flat text configuration file (`.cfg`)
- **Format**: `key = value` pairs
- **Version Header**: `#!version:1.0.0.1`
- **Export Files**:
  - `000bea85f554-all.cfg` - Human-readable config export
  - `33G.bin` - Binary/compressed backup format (proprietary, not for provisioning)

**Key Characteristics:**
```
#!version:1.0.0.1
account.1.enable = 1
account.1.label = Lisa Dingman
account.1.display_name = Lisa Dingman
account.1.user_name = 1501
account.1.auth_name = Lisa Dingman
account.1.sip_server.1.address = 192.168.1.14
account.1.sip_server.1.expires = 600
voice_mail.number.1 = *1501
```

### ZIP 37G Format  
- **File Type**: TAR archive (`.bin`)
- **Format**: Multiple INI files with `[Section]` structure
- **Export File**: `config.bin` - TAR archive containing factory/ directory
- **Contents**:
  - `factory/system.ini` - System/network/auto-provision settings
  - `factory/user.ini` - User preferences/voicemail/features
  - `factory/voip/sipAccount1.cfg` - SIP account configuration (INI format)
  - Additional XML and config files

**Key Characteristics:**
```ini
[ AutoProvision ]
bEnablePowerOn = 1
bEnableRepeat = 1
nRepeatMinutes = 1440

[ account ]
Enable = 1
Label = Lisa Dingman
DisplayName = Lisa Dingman
UserName = 1501
AuthName = Lisa Dingman
SIPServerHost = 192.168.1.14
```

## Critical Findings

### 1. Different Provisioning Methods

**ZIP 33G:**
- Uses flat `.cfg` file downloaded from HTTP URL
- Phone parses `key = value` format
- Single file contains all settings
- URL format: `http://192.168.1.14:8080/provision/000bea85f554.cfg`

**ZIP 37G:**
- Requires `config.bin` (TAR archive with multiple INI files)
- More complex structure with sectioned configuration
- Multiple files for different settings categories
- URL format: `http://192.168.1.14:8080/provision/000bea85bc14.cfg` (but downloads .bin)

### 2. Auto-Provision Parameters NOT in Config Files

**Important Discovery:**
The auto-provision settings we initially added (`auto_provision.power_on.enable`, `auto_provision.repeat.enable`, etc.) are **NOT configured via the downloaded config file**.

These settings are:
- Configured in the phone's UI/web interface
- Stored in phone's persistent memory
- Control WHEN the phone checks for config updates
- Control HOW the phone discovers the config URL

The downloaded config file contains:
- SIP account credentials
- Server addresses
- Feature settings
- But NOT the auto-provision schedule/behavior

### 3. Key Parameter Differences

| Setting | ZIP 33G Format | ZIP 37G Format |
|---------|----------------|----------------|
| Enable Account | `account.1.enable = 1` | `[ account ]`<br>`Enable = 1` |
| SIP Server | `account.1.sip_server.1.address = IP` | `SIPServerHost = IP` |
| Auth Name | `account.1.auth_name = NAME` | `AuthName = NAME` |
| Voicemail | `voice_mail.number.1 = *1501` | `[ Message ]`<br>`VoiceNumber0 = *1501` |
| Codecs | `account.1.codec.6.enable = 0` | `[ audio0 ]`<br>`enable = 1`<br>`PayloadType = PCMU` |

## What We Fixed

### Before (Incorrect)
Our templates used:
- Old/wrong parameter names: `account.1.sip_server_host` (should be `account.1.sip_server.1.address`)
- Added auto-provision parameters that don't belong in config files
- Used same format for both ZIP 33G and ZIP 37G

### After (Correct)
Our templates now:
- **ZIP 33G**: Uses flat `.cfg` format matching actual exported config
  - Correct parameter names: `account.1.sip_server.1.address`
  - Legacy compatibility: `account.1.sip_server_host.legacy`
  - Modern firmware format (47.80.132.4+)
  - Auth name uses display name, not number: `account.1.auth_name = {{EXTENSION_NAME}}`
  
- **ZIP 37G**: Uses INI format with sections
  - INI-style sections: `[ account ]`, `[ AutoProvision ]`
  - Different parameter names to match TAR archive structure
  - Note: Full ZIP 37G support requires TAR generation (future enhancement)

## Template Updates Made

### 1. ZIP 33G Template (`provisioning_templates/zultys_zip33g.template`)
```
✓ Added version header: #!version:1.0.0.1
✓ Updated SIP server format: account.1.sip_server.1.address
✓ Added legacy parameter: account.1.sip_server_host.legacy
✓ Fixed auth_name: Uses {{EXTENSION_NAME}} not {{EXTENSION_NUMBER}}
✓ Added missing parameters: phone_setting.*, linekey.*
✓ Added codec slot 6 disable
✓ Added LLDP settings
✓ Removed incorrect auto_provision.power_on.enable (phone UI setting)
```

### 2. ZIP 37G Template (`provisioning_templates/zultys_zip37g.template`)
```
✓ Changed to INI format with [sections]
✓ Added proper section headers
✓ Updated parameter names to match INI structure
✓ Added note about config.bin TAR requirement
✓ Provided simplified flat format for basic compatibility
```

## Why Configuration Wasn't Applying

The original issue: **"Phone downloads config but doesn't apply it"**

### Root Cause (Multiple Issues)
1. **Wrong Parameter Format**: Templates used `account.1.sip_server_host` instead of `account.1.sip_server.1.address`
   - Phone couldn't parse the config correctly
   - Old firmware parameter names

2. **Missing Parameters**: Export shows parameters we didn't have:
   - `account.1.sip_server_host.legacy` for compatibility
   - `phone_setting.*` for redial/call return
   - `account.1.codec.6.enable = 0` to disable unused slot

3. **Auto-Provision Misunderstanding**: We added parameters to force auto-apply, but:
   - These are phone UI settings, not config file settings
   - Phone applies config based on its UI configuration
   - The auto-provision schedule is set on the phone, not in the downloaded config

### Solution
1. **Use correct parameter names** matching firmware 47.80.132.4+
2. **Include all required parameters** from actual exported config
3. **User must configure auto-provision in phone UI** (one-time setup):
   - Enable "Power On" provisioning
   - Enable "Repeatedly" provisioning (optional)
   - Set Server URL: `http://192.168.1.14:8080/provision/$mac.cfg`

## Testing the Fix

### ZIP 33G Verification
```bash
# Download config from PBX
curl http://192.168.1.14:8080/provision/000bea85f554.cfg

# Should see:
# - #!version:1.0.0.1 header
# - account.1.sip_server.1.address = 192.168.1.14
# - account.1.auth_name = Lisa Dingman (not 1501)
# - voice_mail.number.1 = *1501
```

### Expected Behavior
1. Phone checks for config (schedule set in phone UI)
2. Downloads config file from PBX
3. Parses config with modern parameter format
4. Applies settings successfully
5. Registers with SIP server

## Files Reference

| File | Phone Model | Format | Purpose |
|------|-------------|--------|---------|
| `000bea85f554-all.cfg` | ZIP 33G | Flat .cfg | Human-readable export, template source |
| `33G.bin` | ZIP 33G | Binary | Compressed backup (not for provisioning) |
| `config.bin` | ZIP 37G | TAR archive | Full config backup with INI files |

## Recommendations

### For ZIP 33G Users
✅ Current templates should work correctly
- Use the `.cfg` format
- Parameters match exported config
- Phone should apply settings

### For ZIP 37G Users
⚠️ Limited support currently
- Template provides INI format
- May have limited compatibility with flat file delivery
- **Recommendation**: Consider generating proper `config.bin` TAR archive
- Future enhancement: Add TAR generation for full ZIP 37G support

## Next Steps

1. **Test with real ZIP 33G phone** (MAC: 000bea85f554, Extension: 1501)
   - Verify config downloads correctly
   - Confirm phone applies settings
   - Check SIP registration

2. **Monitor logs** for provisioning requests:
   ```
   tail -f logs/pbx.log | grep -i provision
   ```

3. **If issues persist**, check:
   - Phone firmware version (should be 47.80.132.4+)
   - Phone auto-provision UI settings
   - Network connectivity to PBX
   - MAC address format in URL

4. **Future enhancement**: Implement config.bin TAR generation for full ZIP 37G support

## Technical Details

### Password Field
Note: Exported configs don't include passwords (security feature)
- Phones don't export passwords
- Our templates correctly include: `password = {{EXTENSION_PASSWORD}}`
- This is populated by PBX during config generation

### MAC Address Variables
Phones substitute their MAC address when requesting config:
- Zultys phones use: `$mac` variable
- Phone replaces with actual MAC: `000bea85f554`
- Server URL should be: `http://IP:PORT/provision/$mac.cfg`

### Content Type
- ZIP 33G: `text/plain` or `application/octet-stream`
- ZIP 37G: `application/octet-stream` (for .bin files)

## Conclusion

The templates have been updated to match the actual configuration format used by Zultys phones based on real exported configs. The key issue was using outdated parameter names that modern firmware versions don't recognize. With the corrected format, phones should now successfully apply downloaded configurations.
