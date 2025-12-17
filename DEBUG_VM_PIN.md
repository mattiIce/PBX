# Voicemail PIN Debug Logging

## Overview

This feature provides detailed console logging to help troubleshoot DTMF PIN recognition issues in the voicemail IVR system.

## Security Notice

⚠️ **WARNING**: This feature logs sensitive PIN data and should **ONLY** be used for testing and troubleshooting purposes. **DO NOT enable this in production environments.**

## How to Enable

Set the `DEBUG_VM_PIN` environment variable to enable PIN debug logging:

```bash
# Enable PIN debug logging
export DEBUG_VM_PIN=true

# Then start the PBX system
python main.py
```

Or run with the environment variable inline:

```bash
DEBUG_VM_PIN=true python main.py
```

## How to Disable

The debug logging is **disabled by default**. To explicitly disable it:

```bash
# Disable PIN debug logging (or simply unset the variable)
export DEBUG_VM_PIN=false

# Or remove the environment variable
unset DEBUG_VM_PIN
```

## What Gets Logged

When `DEBUG_VM_PIN=true` is set, you will see detailed logging:

### 1. Initialization Warning
When the voicemail IVR is initialized, you'll see:
```
[VM IVR] ⚠️  PIN DEBUG LOGGING ENABLED for extension 1001 - TESTING ONLY!
[VM IVR] ⚠️  Set DEBUG_VM_PIN=false to disable sensitive PIN logging
```

### 2. Per-Digit Collection
As each DTMF digit is received:
```
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '1' collected, current PIN buffer: '1'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '2' collected, current PIN buffer: '12'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '3' collected, current PIN buffer: '123'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '4' collected, current PIN buffer: '1234'
```

### 3. PIN Verification
When # is pressed to complete PIN entry:
```
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Entered PIN: '1234'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Expected PIN: '1234'
[VM IVR PIN] PIN verification result: VALID
```

Or if the PIN is incorrect:
```
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Entered PIN: '5678'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Expected PIN: '1234'
[VM IVR PIN] PIN verification result: INVALID
```

## Use Cases

This debug logging is useful for:

1. **DTMF Detection Issues**: Verify which digits are actually being received by the IVR
2. **PIN Configuration Problems**: Confirm the expected PIN matches what you configured
3. **Timing Issues**: See if digits are being lost or duplicated
4. **SIP INFO vs In-band DTMF**: Identify which DTMF method is working

## Example Troubleshooting Session

```bash
# 1. Enable debug logging
export DEBUG_VM_PIN=true

# 2. Start the PBX
python main.py

# 3. Call into voicemail from a phone
# 4. Enter your PIN digits and press #
# 5. Check the console output to see:
#    - Which digits were received
#    - The complete PIN that was assembled
#    - What the system expects
#    - Whether verification passed or failed

# 6. Once debugging is complete, disable the feature
unset DEBUG_VM_PIN

# 7. Restart the PBX without debug logging
python main.py
```

## Regular Logging (Without Debug)

Even without `DEBUG_VM_PIN` enabled, you still get useful (non-sensitive) logging:

```
[VM IVR PIN] # pressed, entered_pin length: 4
[VM IVR PIN] PIN verification result: VALID
```

or

```
[VM IVR PIN] # pressed, entered_pin length: 4
[VM IVR PIN] PIN verification result: INVALID
[VM IVR PIN] ✗ Invalid PIN attempt 1/3
```

This shows you:
- How many digits were entered
- Whether verification passed or failed
- Number of failed attempts

## Security Best Practices

1. **Never enable in production** - Only use for development/testing
2. **Disable after debugging** - Don't leave it enabled
3. **Secure your logs** - If debug logs are written to files, ensure they're properly secured and rotated
4. **Review log access** - Ensure only authorized personnel can access debug logs
5. **Clear sensitive data** - After debugging, clear or rotate logs containing PIN data
