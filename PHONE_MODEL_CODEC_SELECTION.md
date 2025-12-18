# Phone Model-Specific Codec Selection

> **⚠️ DEPRECATED**: This guide has been consolidated into [CODEC_IMPLEMENTATION_GUIDE.md](CODEC_IMPLEMENTATION_GUIDE.md). Please refer to the consolidated guide for the most up-to-date information on phone-specific codec selection.

## Overview

The PBX server now automatically selects appropriate codecs based on the phone model when establishing calls. This ensures optimal compatibility and audio quality for different Zultys phone models.

## Implementation Date
December 12, 2025

## Affected Phone Models

### Zultys ZIP37G
- **Server-side codec offering**: PCMU/PCMA only
- **Payload types**: 0 (PCMU), 8 (PCMA), 101 (RFC2833 DTMF)
- **Reason**: ZIP37G phones natively support PCMU/PCMA with built-in codec defaults

### Zultys ZIP33G
- **Server-side codec offering**: G726, G729, G722 only
- **Payload types**: 
  - 2 (G726-32)
  - 18 (G729)
  - 9 (G722)
  - 114 (G726-40)
  - 113 (G726-24)
  - 112 (G726-16)
  - 101 (RFC2833 DTMF)
- **Reason**: ZIP33G requires explicit codec configuration and works better with these codecs

### Other Phones
- **Server-side codec offering**: Uses caller's advertised codecs (existing behavior)
- **Behavior**: No change - maintains backward compatibility with all other phone models

## How It Works

### 1. Phone Model Detection

When a phone registers with the PBX, the User-Agent header is stored in the `registered_phones` database table. The PBX analyzes this header to detect the phone model:

```
User-Agent: Zultys ZIP37G 47.85.0.140  → Detected as ZIP37G
User-Agent: Zultys ZIP33G 47.80.0.132  → Detected as ZIP33G
User-Agent: Yealink SIP-T46S 66.85.0.5 → Unknown (uses default behavior)
```

### 2. Codec Selection

When the PBX needs to respond to or initiate a call, it:

1. Retrieves the User-Agent string for the extension from the database
2. Detects the phone model
3. Selects the appropriate codec list:
   - **ZIP37G**: `['0', '8', '101']` (PCMU, PCMA, DTMF)
   - **ZIP33G**: `['2', '18', '9', '114', '113', '112', '101']` (G726 variants, G729, G722, DTMF)
   - **Other**: Uses caller's codecs or defaults

### 3. SDP Construction

The selected codec list is used when building SDP (Session Description Protocol) offers in:

- **Regular calls** (INVITE to callee)
- **Call answers** (200 OK to caller)
- **Voicemail** (no-answer routing)
- **Auto-attendant** (extension 0)
- **Voicemail access** (*xxxx pattern)
- **Paging** (7xx pattern)

## Code Changes

### New Helper Methods in `pbx/core/pbx.py`

```python
def _detect_phone_model(self, user_agent):
    """
    Detect phone model from User-Agent string
    
    Returns: 'ZIP33G', 'ZIP37G', or None
    """

def _get_codecs_for_phone_model(self, phone_model, default_codecs=None):
    """
    Get appropriate codec list for a specific phone model
    
    Returns: List of codec payload types as strings
    """

def _get_phone_user_agent(self, extension_number):
    """
    Get User-Agent string for a registered phone by extension number
    
    Returns: User-Agent string or None if not found
    """
```

### Modified Methods

All SDP building locations now use phone-model-specific codecs:

1. `route_call()` - When forwarding INVITE to callee
2. `handle_callee_answer()` - When sending 200 OK to caller
3. `_handle_no_answer()` - When routing to voicemail
4. `_handle_auto_attendant()` - When answering auto-attendant call
5. `_handle_voicemail_access()` - When answering voicemail access
6. `_handle_paging()` - When answering paging call

## Configuration

### DTMF Payload Type

The DTMF (RFC2833) payload type can be configured in `config.yml`:

```yaml
dtmf:
  payload_type: 101  # Default, can be changed to 96-127 if needed
```

This payload type is automatically included in all codec lists.

## Database Requirements

The feature requires the `registered_phones` table to store User-Agent information:

```sql
CREATE TABLE registered_phones (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(17),
    extension_number VARCHAR(10) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,  -- Used for phone model detection
    contact_uri TEXT,
    first_registered TIMESTAMP,
    last_registered TIMESTAMP
);
```

## Testing

### Unit Tests

New test file: `tests/test_phone_model_codec_selection.py`

- **13 tests** covering:
  - Phone model detection (ZIP33G, ZIP37G, others)
  - Codec selection logic
  - Case-insensitive detection
  - Custom DTMF payload types
  - Fallback behavior

Run tests:
```bash
python -m unittest tests.test_phone_model_codec_selection -v
```

### Manual Testing

1. **Register a ZIP37G phone** (extension 1001)
2. **Make a call** to another extension
3. **Check logs** for:
   ```
   Detected callee phone model: ZIP37G, offering codecs: ['0', '8', '101']
   ```
4. **Verify audio quality** - should use PCMU or PCMA

Repeat for ZIP33G phones - should see:
```
Detected callee phone model: ZIP33G, offering codecs: ['2', '18', '9', '114', '113', '112', '101']
```

## Logging

The PBX logs codec selection decisions at INFO level:

```
INFO: Detected callee phone model: ZIP37G, offering codecs: ['0', '8', '101']
DEBUG: Using ZIP37G codec set: PCMU/PCMA (['0', '8', '101'])
```

```
INFO: Detected caller phone model: ZIP33G, offering codecs in 200 OK: ['2', '18', '9', '114', '113', '112', '101']
DEBUG: Using ZIP33G codec set: G726/G729/G722 (['2', '18', '9', '114', '113', '112', '101'])
```

## Backward Compatibility

This change is **fully backward compatible**:

1. **Phones without stored User-Agent**: Use default codec negotiation
2. **Non-Zultys phones**: Use default codec negotiation
3. **Existing calls**: No changes to call flow or behavior
4. **Database optional**: If database is not available, uses default behavior

## Benefits

### For ZIP37G Phones
- Optimized for PCMU/PCMA codecs that the phone handles natively
- Eliminates codec negotiation issues
- Ensures consistent audio quality

### For ZIP33G Phones
- Uses codecs that work best with ZIP33G firmware
- Avoids PCMU/PCMA issues that require explicit configuration
- Better compatibility with existing phone provisioning

### For Other Phones
- No changes - existing behavior preserved
- Full codec negotiation flexibility maintained

## Troubleshooting

### Issue: Phone model not detected

**Symptoms**: Logs show `Detected callee phone model: None`

**Causes**:
1. Phone hasn't registered yet
2. User-Agent not stored in database
3. Phone sends non-standard User-Agent

**Solution**:
1. Check `registered_phones` table for the extension
2. Verify `user_agent` column has a value
3. Re-register the phone if needed

### Issue: Wrong codecs selected

**Symptoms**: Unexpected codec list in logs

**Cause**: Phone model misdetection

**Solution**:
1. Check User-Agent string in database
2. Verify detection logic handles the format
3. Update `_detect_phone_model()` if needed

### Issue: No audio after codec change

**Symptoms**: Call connects but no audio

**Causes**:
1. Codec negotiation failure
2. RTP ports blocked
3. Phone doesn't support offered codecs

**Solution**:
1. Check SIP messages for codec in SDP
2. Verify phone actually supports the codecs
3. Check RTP relay logs for packet flow

## Related Documentation

- [ZULTYS_ZIP33G_CODEC_CONFIGURATION.md](ZULTYS_ZIP33G_CODEC_CONFIGURATION.md) - ZIP33G provisioning details
- [G729_G726_CODEC_GUIDE.md](G729_G726_CODEC_GUIDE.md) - G729/G726 codec information
- [CODEC_NEGOTIATION_FIX.md](CODEC_NEGOTIATION_FIX.md) - General codec negotiation
- [PHONE_REGISTRATION_TRACKING.md](PHONE_REGISTRATION_TRACKING.md) - Registration database

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | Dec 12, 2025 | Initial implementation of phone model-specific codec selection |

---

**Status**: ✅ Implemented and Tested  
**Compatibility**: Backward compatible with all existing phones  
**Database**: Optional (falls back to default behavior if not available)
