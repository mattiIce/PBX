# ZIP33G DTMF Payload Type Issue - Resolution Summary

## Issue Description

**Question**: Could the DTMF issue be related to using DTMF payload type 101 by default on the 33G's?

**Answer**: Yes, potentially. The hardcoded payload type 101 could cause DTMF issues in certain scenarios.

## Root Cause Analysis

### The Problem

1. **PBX Behavior**: The PBX was hardcoded to advertise RFC2833 with payload type 101 in SDP offers
2. **ZIP33G Configuration**: Phones were configured to use SIP INFO for DTMF (not RFC2833)
3. **Potential Conflict**: This mismatch between advertised capability (RFC2833/101) and actual usage (SIP INFO) could cause:
   - DTMF detection failures
   - Spurious DTMF digits
   - One-way DTMF issues
   - Incompatibility with some SIP providers

### Why Payload Type 101?

Payload type 101 is the RFC 2833 standard for telephone-event (DTMF). However:

- Some phone firmware versions have bugs with payload type 101
- Some SIP providers require alternative payload types (e.g., 100, 102)
- Some network equipment may filter or modify payload type 101
- Having it hardcoded prevented addressing these issues without code changes

## Solution Implemented

### Changes Made

#### 1. Configuration File (config.yml)
Added global DTMF payload type configuration:

```yaml
features:
  dtmf:
    payload_type: 101  # Configurable (96-127)
```

#### 2. Provisioning System (phone_provisioning.py)
- Added `{{DTMF_PAYLOAD_TYPE}}` placeholder support
- Automatically replaces placeholder with configured value
- Defaults to 101 if not configured

#### 3. Phone Templates
Updated all templates to use placeholder:

```ini
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}
```

**Templates Updated:**
- `zultys_zip33g.template`
- `zultys_zip37g.template`
- `yealink_t28g.template`
- `yealink_t46s.template`

#### 4. SDP Negotiation (sdp.py)
- Added `dtmf_payload_type` parameter to `build_audio_sdp()`
- Dynamically builds SDP with configured payload type
- Maintains backward compatibility (defaults to 101)

#### 5. RFC2833 Implementation (rfc2833.py)
- Added `payload_type` parameter to `RFC2833Receiver` class
- Added `payload_type` parameter to `RFC2833Sender` class
- Both classes can now handle any valid payload type (96-127)

## Benefits

### 1. Flexibility
- Can change DTMF payload type without code modifications
- Single configuration point for all phones
- Per-phone override still possible via template editing

### 2. Compatibility
- Supports SIP providers with non-standard requirements
- Works around phone firmware bugs
- Handles network equipment that filters payload 101

### 3. Troubleshooting
- Easy to test alternative payload types
- No code deployment required for configuration changes
- Quick rollback if issues occur

### 4. Backward Compatibility
- Defaults to standard payload type 101
- No breaking changes to existing installations
- Existing configurations work without modification

## How to Use

### Check if You Need This

You may need to change the payload type if experiencing:

- DTMF digits not detected in voicemail/auto-attendant
- Phantom DTMF keypresses
- One-way DTMF (can send but not receive, or vice versa)
- SIP provider requiring specific payload type

### Configuration Steps

#### 1. Edit config.yml
```yaml
features:
  dtmf:
    payload_type: 100  # Change from 101 to alternative
```

#### 2. Restart PBX
```bash
sudo systemctl restart pbx
```

#### 3. Reprovision Phones
- Option A: Reboot phones to force reprovision
- Option B: Wait for automatic reprovision (24 hours)
- Option C: Use phone menu: Settings → Auto Provision → Provision Now

#### 4. Test DTMF
```
Test 1: Call voicemail (*<extension>)
Test 2: Enter PIN when prompted
Test 3: Navigate menu options
Test 4: Verify immediate response
```

### Verification

Check phone configuration was updated:
```bash
# Access phone web interface
http://<phone-ip>/config.txt

# Look for:
account.1.dtmf.dtmf_payload = 100  # (or your configured value)
```

Check PBX logs for DTMF events:
```bash
tail -f logs/pbx.log | grep -i dtmf

# Should see:
# RFC 2833 DTMF event completed: 5 (duration: 160)
```

## Testing Results

### Unit Tests
Created comprehensive test suite: `tests/test_dtmf_payload_type_config.py`

**Test Coverage:**
- ✅ SDP builder with default payload type 101
- ✅ SDP builder with custom payload types (100, 102)
- ✅ RFC2833 receiver with configurable payload type
- ✅ RFC2833 sender with configurable payload type
- ✅ Phone template placeholder replacement
- ✅ Default value handling (101 when not configured)
- ✅ Valid payload type range (96-127)

**Results:** All 14 tests pass ✅

### Code Review
- ✅ All feedback addressed
- ✅ Comments improved for clarity
- ✅ Logic simplified where appropriate

### Security Scan
- ✅ CodeQL analysis: 0 alerts
- ✅ No new vulnerabilities introduced
- ✅ Configuration-only changes, no new attack vectors

## Documentation

### Created Files

1. **DTMF_PAYLOAD_TYPE_CONFIGURATION.md**
   - Comprehensive configuration guide
   - Troubleshooting procedures
   - Best practices
   - Technical details
   - Examples and use cases

2. **tests/test_dtmf_payload_type_config.py**
   - Complete test suite
   - Validates all functionality
   - Ensures backward compatibility

3. **This document (ZIP33G_DTMF_PAYLOAD_TYPE_RESOLUTION.md)**
   - Executive summary
   - Quick reference
   - Deployment guide

## Recommendations

### For ZIP33G Phones

**Current Configuration (Working):**
- DTMF Method: SIP INFO (type 2)
- DTMF Payload: 101 (for RFC2833 fallback)
- Status: ✅ Working with SIP INFO

**If Experiencing Issues:**
1. First, try changing to RFC2833 (type 1) with payload 101
2. If still issues, try payload type 100 or 102
3. If no improvement, revert to SIP INFO (current working config)

### For Other Phone Models

**Yealink Phones:**
- Default: SIP INFO with payload 101
- Generally reliable, no changes needed unless issues

**Future Phone Models:**
- Test with standard payload type 101 first
- Document any model-specific requirements
- Update compatibility matrix in documentation

## Deployment Checklist

- [ ] Review current DTMF configuration
- [ ] Identify if payload type change needed
- [ ] Update config.yml if required
- [ ] Test configuration change in development/staging
- [ ] Schedule maintenance window for production
- [ ] Restart PBX service
- [ ] Reprovision phones
- [ ] Verify DTMF functionality (voicemail, auto-attendant)
- [ ] Monitor PBX logs for DTMF events
- [ ] Document any phone-specific requirements discovered
- [ ] Update compatibility matrix if needed

## Rollback Plan

If issues occur after changing payload type:

1. **Immediate Rollback**
   ```bash
   # Revert config.yml
   git checkout HEAD -- config.yml
   
   # Or manually change back to:
   features:
     dtmf:
       payload_type: 101
   
   # Restart PBX
   sudo systemctl restart pbx
   ```

2. **Reprovision Phones**
   - Reboot phones to fetch original configuration
   - Or wait for automatic reprovision

3. **Verify**
   - Test DTMF on affected phones
   - Check logs for normal operation

## Related Issues

### Known Phone Issues

**Zultys ZIP33G:**
- False BYE issue during voicemail access (separate issue, already fixed)
- SIP INFO works reliably for DTMF
- RFC2833 support present but not currently primary method

**Zultys ZIP37G:**
- Shares firmware base with ZIP33G
- Same configuration applies
- Similar DTMF characteristics

### SIP Provider Compatibility

Document any provider-specific requirements here:

| Provider | Required Payload Type | Notes |
|----------|----------------------|-------|
| Standard | 101 | RFC 2833 standard |
| (Add provider) | (Type) | (Notes) |

## Support Resources

### Documentation
- [DTMF Payload Type Configuration Guide](DTMF_PAYLOAD_TYPE_CONFIGURATION.md)
- [Zultys DTMF Troubleshooting](ZULTYS_DTMF_TROUBLESHOOTING.md)
- [RFC2833 Implementation Guide](RFC2833_IMPLEMENTATION_GUIDE.md)
- [Complete DTMF Implementation Summary](COMPLETE_DTMF_IMPLEMENTATION_SUMMARY.md)

### Testing Tools
- Unit tests: `tests/test_dtmf_payload_type_config.py`
- Manual testing procedures in configuration guide
- Packet capture analysis examples

### Configuration Files
- Main config: `config.yml`
- Phone templates: `provisioning_templates/*.template`
- Source code: `pbx/sip/sdp.py`, `pbx/rtp/rfc2833.py`

## Conclusion

The DTMF payload type 101 issue has been resolved by making it configurable. This provides:

✅ **Flexibility** to handle different phone models and SIP providers  
✅ **Backward compatibility** with existing installations  
✅ **Easy troubleshooting** without code changes  
✅ **Complete documentation** for deployment and support  
✅ **Comprehensive testing** to ensure reliability  
✅ **Security validated** with no new vulnerabilities  

The default configuration (payload type 101 with SIP INFO primary) works well for ZIP33G phones. The new configurability allows addressing edge cases without requiring code modifications.

---

**Status**: ✅ Complete  
**Version**: 1.0  
**Date**: December 12, 2024  
**Impact**: All IP phones  
**Breaking Changes**: None  
**Tests**: 14 tests, all passing  
**Security**: No vulnerabilities detected
