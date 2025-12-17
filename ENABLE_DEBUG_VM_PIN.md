# Quick Guide: Enable DEBUG_VM_PIN

## For Immediate Troubleshooting

If you're experiencing DTMF PIN recognition issues in voicemail IVR, follow these steps to enable debug logging:

### Method 1: Using .env file (Recommended for persistent debugging)

1. Create or edit the `.env` file in the PBX root directory:
   ```bash
   cd /path/to/PBX
   nano .env
   ```

2. Add this line:
   ```
   DEBUG_VM_PIN=true
   ```

3. Save and exit (Ctrl+X, then Y, then Enter)

4. Restart the PBX system:
   ```bash
   # If running as a service
   sudo systemctl restart pbx
   
   # Or if running manually
   python main.py
   ```

### Method 2: One-time testing (Inline environment variable)

Run the PBX with DEBUG_VM_PIN enabled for this session only:

```bash
DEBUG_VM_PIN=true python main.py
```

### Method 3: Export for current shell session

```bash
export DEBUG_VM_PIN=true
python main.py
```

## What to Look For

Once enabled, call into voicemail and enter your PIN. You should see output like:

```
[VM IVR] ⚠️  PIN DEBUG LOGGING ENABLED for extension 1001 - TESTING ONLY!
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '1' collected, current PIN buffer: '1'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '2' collected, current PIN buffer: '12'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '3' collected, current PIN buffer: '123'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '4' collected, current PIN buffer: '1234'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Entered PIN: '1234'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Expected PIN: '1234'
[VM IVR PIN] PIN verification result: VALID
```

## Diagnosing Your Issue

### ✅ Good: PIN buffer accumulates correctly
If you see the buffer growing with each digit (1, 12, 123, 1234), DTMF collection is working.

**Check:**
- Does "Entered PIN" match what you typed?
- Does "Expected PIN" match the configured PIN for the mailbox?
- If both match but result is INVALID, check for encoding issues in PIN storage

### ❌ Problem: PIN buffer stays at single digit
If the buffer shows only '1' for each digit press (not accumulating):

```
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '1' collected, current PIN buffer: '1'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '2' collected, current PIN buffer: '2'  <- Should be '12'!
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '3' collected, current PIN buffer: '3'  <- Should be '123'!
```

**This indicates a bug:** The IVR instance may be getting recreated or entered_pin is being reset.

### ❌ Problem: Digits missing from buffer
If some digits don't appear in the sequence:

```
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '1' collected, current PIN buffer: '1'
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '3' collected, current PIN buffer: '13'  <- '2' is missing!
[VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '4' collected, current PIN buffer: '134'
```

**Possible causes:**
- DTMF transmission lost packets
- Phone DTMF duration too short
- Try in-band DTMF instead of SIP INFO

## After Debugging

**IMPORTANT:** Disable DEBUG_VM_PIN when done:

```bash
# If using .env file, edit it and set:
DEBUG_VM_PIN=false

# Or remove the line entirely, then restart:
sudo systemctl restart pbx
```

## Need More Help?

See the full documentation: [DEBUG_VM_PIN.md](DEBUG_VM_PIN.md)
