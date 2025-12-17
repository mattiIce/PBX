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

## Troubleshooting Common Issues

### Issue: DTMF digits received but PIN always invalid

**Symptoms:**
- You see DTMF digits being received in the logs
- Each digit shows "Queued DTMF 'X' from SIP INFO for voicemail IVR"
- IVR processes each digit: "Processing DTMF 'X' through IVR state machine"
- But PIN verification fails with INVALID result

**How to diagnose with DEBUG_VM_PIN:**

1. Enable debug logging:
   ```bash
   export DEBUG_VM_PIN=true
   python main.py
   ```

2. Call voicemail and enter your PIN (e.g., 1234)

3. Look for the PIN buffer logs:
   ```
   [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '1' collected, current PIN buffer: '1'
   [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '2' collected, current PIN buffer: '12'
   [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '3' collected, current PIN buffer: '123'
   [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '4' collected, current PIN buffer: '1234'
   ```

4. **If you see the buffer accumulating correctly** (1, 12, 123, 1234):
   - The DTMF collection is working
   - Check the "Expected PIN" in the verification log
   - Problem is likely with configured PIN, not DTMF detection

5. **If the buffer is NOT accumulating** (stays '1' for each digit):
   - Indicates the IVR instance may be getting recreated
   - Or the entered_pin is being reset between digits
   - This is a bug that needs investigation

6. **If digits are missing** (buffer shows '1', '2', '4' but skips '3'):
   - DTMF transmission issue
   - Try using in-band DTMF instead of SIP INFO
   - Check phone DTMF configuration

7. **If digits are duplicated** (buffer shows '11', '112', '1123'):
   - DTMF debouncing issue
   - May need to adjust debounce timing
   - Check if phone is sending duplicate DTMF events

### Issue: First digit lost when entering PIN

**Symptoms:**
- First digit you press doesn't appear in PIN buffer
- Subsequent digits work fine

**Solution:**
This was fixed in a recent update. The voicemail IVR now captures the first digit when transitioning from WELCOME state to PIN_ENTRY state. Ensure you're running the latest version.

### Issue: PIN appears correct in logs but still fails verification

**Symptoms:**
- Debug shows: Entered PIN: '1234', Expected PIN: '1234'
- But verification still fails

**Possible causes:**
1. Hidden characters in the configured PIN (whitespace, newlines)
2. PIN stored in different encoding
3. Check mailbox PIN configuration in database or config file

