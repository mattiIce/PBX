# VM IVR Dedicated Logging

## Overview

The Voicemail IVR system now has its own dedicated log file separate from the main PBX logs. This makes it easier to troubleshoot voicemail-specific issues without having to search through the entire PBX log.

## Log File Location

**File:** `logs/vm_ivr.log`

All voicemail IVR activity is logged to this dedicated file, including:
- PIN entry and verification
- IVR state transitions
- DTMF digit processing
- Menu navigation
- Message playback
- Voicemail actions (delete, save, etc.)
- Debug PIN logging (when DEBUG_VM_PIN=true)

## Benefits

1. **Easier Troubleshooting**: All VM IVR logs in one place
2. **Reduced Noise**: Main PBX log is cleaner
3. **Better Analysis**: Can analyze voicemail patterns separately
4. **Improved DEBUG_VM_PIN**: Sensitive PIN data stays in dedicated log

## Log Format

Each log entry includes:
- Timestamp
- Logger name (PBX.VM_IVR)
- Log level (INFO, WARNING, ERROR, DEBUG)
- Message

Example:
```
2025-12-17 15:54:45 - PBX.VM_IVR - INFO - Voicemail IVR initialized for extension 1001
2025-12-17 15:54:45 - PBX.VM_IVR - INFO - [VM IVR PIN] # pressed, entered_pin length: 4
2025-12-17 15:54:45 - PBX.VM_IVR - INFO - [VM IVR PIN] PIN verification result: VALID
```

## With DEBUG_VM_PIN Enabled

When DEBUG_VM_PIN=true, sensitive PIN information is logged to vm_ivr.log:

```
2025-12-17 15:54:45 - PBX.VM_IVR - WARNING - [VM IVR] ⚠️  PIN DEBUG LOGGING ENABLED for extension 1001 - TESTING ONLY!
2025-12-17 15:54:45 - PBX.VM_IVR - INFO - [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '1' collected, current PIN buffer: '1'
2025-12-17 15:54:45 - PBX.VM_IVR - INFO - [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Digit '2' collected, current PIN buffer: '12'
2025-12-17 15:54:45 - PBX.VM_IVR - INFO - [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Entered PIN: '1234'
2025-12-17 15:54:45 - PBX.VM_IVR - INFO - [VM IVR PIN DEBUG] ⚠️  TESTING ONLY - Expected PIN: '1234'
```

**⚠️ Security Note:** The vm_ivr.log file should be secured when DEBUG_VM_PIN is enabled, as it contains sensitive PIN data.

## Console Output

VM IVR logs are still output to the console in addition to the log file. This allows you to see real-time activity while also maintaining a separate log file for analysis.

To disable console output for VM IVR (if needed), modify the logger setup in `pbx/utils/logger.py`.

## Viewing Logs

### View recent VM IVR activity:
```bash
tail -f logs/vm_ivr.log
```

### View last 50 lines:
```bash
tail -50 logs/vm_ivr.log
```

### Search for specific extension:
```bash
grep "extension 1001" logs/vm_ivr.log
```

### Search for PIN failures:
```bash
grep "INVALID" logs/vm_ivr.log
```

### View only DEBUG PIN logs:
```bash
grep "PIN DEBUG" logs/vm_ivr.log
```

## Log Rotation

The vm_ivr.log file will grow over time. Consider implementing log rotation using:

1. **Linux logrotate** (recommended for production):
   ```
   # /etc/logrotate.d/pbx-vm-ivr
   /path/to/PBX/logs/vm_ivr.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
       create 0644 pbx pbx
   }
   ```

2. **Python logging RotatingFileHandler** (can be implemented in logger.py if needed)

## Comparison: Main PBX Log vs VM IVR Log

| Feature | pbx.log | vm_ivr.log |
|---------|---------|------------|
| SIP messages | ✓ | ✗ |
| Call setup/teardown | ✓ | ✗ |
| Extension registration | ✓ | ✗ |
| Auto attendant | ✓ | ✗ |
| **Voicemail IVR** | ✗ | ✓ |
| **PIN entry/verification** | ✗ | ✓ |
| **DTMF in VM context** | ✗ | ✓ |
| **Message playback** | ✗ | ✓ |

## Troubleshooting with VM IVR Log

### Example: Investigating PIN failures

1. Enable DEBUG_VM_PIN:
   ```bash
   export DEBUG_VM_PIN=true
   ```

2. Restart PBX and reproduce the issue

3. Check the VM IVR log:
   ```bash
   tail -100 logs/vm_ivr.log | grep -A 5 "PIN DEBUG"
   ```

4. Look for the PIN buffer accumulation and compare entered vs expected PIN

### Example: Finding DTMF issues

```bash
# See all DTMF processing
grep "DTMF" logs/vm_ivr.log

# See PIN-related DTMF only
grep "VM IVR PIN" logs/vm_ivr.log
```

## Related Documentation

- [DEBUG_VM_PIN.md](DEBUG_VM_PIN.md) - Debug PIN logging feature
- [ENABLE_DEBUG_VM_PIN.md](ENABLE_DEBUG_VM_PIN.md) - Quick start guide for PIN debugging
