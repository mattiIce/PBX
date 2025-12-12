# Quiet Startup Mode

## Overview

The PBX system can generate verbose output during startup as it initializes dozens of features and integrations. The **quiet startup** mode reduces this verbosity by moving initialization messages from INFO to DEBUG level.

## Configuration

Add to your `config.yml`:

```yaml
logging:
  level: INFO
  file: logs/pbx.log
  console: true
  quiet_startup: false  # Set to true for quieter startup
```

## Behavior

### Normal Mode (`quiet_startup: false`)

Full startup output with all initialization messages:

```
✓ All core dependencies satisfied
⚠ 4 optional dependencies missing (use --verbose to see details)

Performing security checks...
✓ FIPS 140-2 compliance verified

2025-12-12 20:00:00 - PBX - INFO - Database backend initialized successfully (sqlite)
2025-12-12 20:00:00 - PBX - INFO - Extensions, voicemail metadata, and phone registrations will be stored in database
2025-12-12 20:00:00 - PBX - INFO - Statistics and analytics engine initialized
2025-12-12 20:00:00 - PBX - INFO - QoS monitoring system initialized and integrated with RTP relay
2025-12-12 20:00:00 - PBX - INFO - Active Directory integration initialized
2025-12-12 20:00:00 - PBX - INFO - Phone book feature initialized
2025-12-12 20:00:00 - PBX - INFO - Emergency notification system initialized
2025-12-12 20:00:00 - PBX - INFO - Paging system initialized
2025-12-12 20:00:00 - PBX - INFO - E911 location service initialized
2025-12-12 20:00:00 - PBX - INFO - Kari's Law compliance initialized (direct 911 dialing enabled)
2025-12-12 20:00:00 - PBX - INFO - WebRTC browser calling initialized
2025-12-12 20:00:00 - PBX - INFO - CRM integration and screen pop initialized
2025-12-12 20:00:00 - PBX - INFO - Hot-desking system initialized
2025-12-12 20:00:00 - PBX - INFO - Multi-Factor Authentication (MFA) initialized
2025-12-12 20:00:00 - PBX - INFO - Enhanced threat detection initialized
2025-12-12 20:00:00 - PBX - INFO - DND Scheduler initialized
2025-12-12 20:00:00 - PBX - INFO - Skills-Based Routing initialized
2025-12-12 20:00:00 - PBX - INFO - PBX Core initialized with all features
2025-12-12 20:00:00 - PBX - INFO - SIP Server started on 0.0.0.0:5060
2025-12-12 20:00:00 - PBX - INFO - RTP Relay listening on ports 10000-20000
```

### Quiet Mode (`quiet_startup: true`)

Reduced startup output - initialization messages moved to DEBUG:

```
✓ All core dependencies satisfied
⚠ 4 optional dependencies missing (use --verbose to see details)

Performing security checks...
✓ FIPS 140-2 compliance verified

2025-12-12 20:00:00 - PBX - INFO - SIP Server started on 0.0.0.0:5060
2025-12-12 20:00:00 - PBX - INFO - RTP Relay listening on ports 10000-20000
2025-12-12 20:00:00 - PBX - INFO - REST API server listening on https://0.0.0.0:8080

PBX system is running...
```

The initialization messages are still logged to the log file at DEBUG level, so they're available for troubleshooting if needed.

## Viewing Initialization Details in Quiet Mode

If you need to see initialization details while using quiet mode, you can:

1. **Check the log file**: Startup messages are logged to the file even in quiet mode
2. **Enable DEBUG logging temporarily**:
   ```yaml
   logging:
     level: DEBUG  # Shows all initialization details
     quiet_startup: true  # Ignored when level is DEBUG
   ```

3. **Disable quiet mode for detailed startup**:
   ```yaml
   logging:
     level: INFO
     quiet_startup: false
   ```

## Benefits

- **Faster review** of startup output - no scrolling through dozens of initialization messages
- **Easier troubleshooting** - important messages (errors, warnings, server start) stand out
- **Cleaner logs** during normal operation
- **Full details still available** in log file for debugging

## Recommended Settings

### Development

```yaml
logging:
  level: DEBUG
  quiet_startup: false  # See all details during development
```

### Production

```yaml
logging:
  level: INFO
  quiet_startup: true  # Cleaner console output for operators
```

## Related

- See [ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md) for dependency checking setup
- See `main.py` for startup sequence and dependency validation
