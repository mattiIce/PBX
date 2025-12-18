# E911 Protection Guide

> **⚠️ DEPRECATED**: This guide has been consolidated into [REGULATIONS_COMPLIANCE_GUIDE.md](REGULATIONS_COMPLIANCE_GUIDE.md#e911-protection). Please refer to the "E911 Protection" section in the consolidated guide.

## Overview

The PBX system includes a comprehensive E911 (Enhanced 911) protection system that prevents emergency calls from being placed during testing and development scenarios. This is a critical safety feature that ensures 911 calls are never accidentally placed during testing, which could:

- Tie up emergency services resources
- Result in fines or legal issues
- Create confusion for emergency responders
- Violate telecommunications regulations

## How It Works

### Automatic Test Mode Detection

The E911 protection system automatically detects when the PBX is running in test mode by checking for:

1. **Environment Variables:**
   - `PYTEST_CURRENT_TEST` - Set by pytest
   - `TEST_MODE` - Generic test mode indicator
   - `TESTING` - Alternative test mode indicator
   - `PBX_TEST_MODE` - PBX-specific test mode flag

2. **Configuration File Names:**
   - Files containing "test" in the name (e.g., `test_config.yml`)

### E911 Number Detection

The system recognizes various E911 patterns:

- `911` - Standard emergency number
- `1911`, `12911`, etc. - Enhanced 911 with location prefixes
- `*911` - Special prefix variations

### Protection Levels

#### Test Mode (Automatic)
When test mode is detected:
- **All E911 calls are BLOCKED**
- Error messages are logged
- Calls fail gracefully without reaching SIP trunks
- No emergency service is contacted

#### Production Mode
In production mode:
- E911 calls are **allowed** to proceed
- Warning messages are logged for audit purposes
- Emergency services can be contacted normally

## Usage

### For Testing

The protection is automatic. Simply run your tests normally:

```bash
# Run tests with pytest (automatically detected)
pytest tests/test_e911_protection.py

# Run tests directly (set environment variable)
TEST_MODE=1 python tests/test_basic.py

# Run with test configuration
python main.py --config test_config.yml
```

### For Development

Set the `TEST_MODE` environment variable to prevent accidental 911 calls:

```bash
# In your shell
export TEST_MODE=1

# Run the PBX
python main.py
```

### For Production

Simply run the PBX normally without any test mode indicators:

```bash
# Production mode - E911 allowed
python main.py
```

## Implementation Details

### E911Protection Class

Location: `pbx/utils/e911_protection.py`

Key methods:
- `is_e911_number(number)` - Check if a number is an E911 pattern
- `block_if_e911(number, context)` - Block E911 calls in test mode
- `is_test_mode()` - Check if currently in test mode

### Integration Points

The E911 protection is integrated at critical points:

1. **SIP Trunk System** (`pbx/features/sip_trunk.py`)
   - `route_outbound()` - Blocks E911 before routing
   - `make_outbound_call()` - Blocks E911 before calling

2. **PBX Core** (`pbx/core/pbx.py`)
   - Passes configuration to SIP trunk system
   - Ensures protection is active for all outbound calls

## Testing

Comprehensive tests are available in `tests/test_e911_protection.py`:

- Pattern detection tests
- Test mode detection tests
- Blocking behavior tests
- SIP trunk integration tests

Run the tests:

```bash
python tests/test_e911_protection.py
```

Expected output:
```
============================================================
E911 Protection Tests
============================================================

Testing E911 pattern detection...
✓ E911 pattern detection works correctly

Testing test mode detection...
✓ Test mode detection works correctly

Testing E911 blocking in test mode...
✓ E911 blocking in test mode works correctly

Testing E911 warning in production mode...
✓ E911 warning in production mode works correctly

Testing SIP trunk E911 blocking...
✓ SIP trunk E911 blocking works correctly

============================================================
Results: 5 passed, 0 failed
============================================================
```

## Logging

The system logs important events:

### Test Mode Activation
```
WARNING - E911 Protection: TEST MODE DETECTED - All emergency calls will be blocked
```

### Blocked E911 Call (Test Mode)
```
ERROR - E911 Protection: BLOCKED emergency call to 911 (context: make_outbound_call)
ERROR - E911 call from 1001 to 911 blocked by protection system
```

### E911 Call Detection (Production Mode)
```
WARNING - E911 Protection: Emergency call detected to 911 (context: make_outbound_call)
```

## Best Practices

1. **Always run tests in test mode** - Set `TEST_MODE=1` or use pytest
2. **Never disable the protection** - It's there for safety
3. **Monitor logs** - Review logs for any E911 activity
4. **Test with care** - Even in production, coordinate with emergency services before testing 911
5. **Use test patterns** - Use non-emergency numbers (like 555-xxxx) for testing

## Regulatory Compliance

This system helps ensure compliance with:

- **FCC Regulations** - Preventing false 911 calls
- **State/Local Laws** - Avoiding penalties for false emergency calls
- **Carrier Requirements** - Meeting SIP trunk provider terms of service

## Troubleshooting

### E911 Blocked When It Shouldn't Be

Check if any test mode indicators are set:
```bash
env | grep -E 'TEST|PYTEST'
```

Clear test mode:
```bash
unset TEST_MODE
unset TESTING
unset PBX_TEST_MODE
```

### E911 Not Blocked During Testing

Ensure test mode is set:
```bash
export TEST_MODE=1
```

Or use pytest:
```bash
pytest tests/your_test.py
```

## Support

For issues or questions about E911 protection:

1. Review the logs for detailed information
2. Check test mode detection with `is_test_mode()`
3. Verify E911 patterns with `is_e911_number()`
4. Consult `tests/test_e911_protection.py` for examples

## Summary

The E911 protection system is a critical safety feature that:
- ✅ Automatically detects test mode
- ✅ Blocks all E911 calls during testing
- ✅ Logs all E911-related activity
- ✅ Allows production E911 calls
- ✅ Provides comprehensive test coverage
- ✅ Helps ensure regulatory compliance

**Remember:** Always use test mode when testing, and never place actual 911 calls unless coordinating with emergency services for legitimate testing purposes.
