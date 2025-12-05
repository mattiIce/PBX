# Phone Registration Tracking

The PBX system now includes a database feature to track and remember phones that have registered, storing their MAC addresses (when available) and IP addresses.

## Overview

When a phone registers via SIP REGISTER, the system automatically captures and stores:
- **Extension Number** - The extension the phone is registered to
- **IP Address** - The IP address of the phone (always captured)
- **MAC Address** - The MAC address of the phone (when available from SIP headers)
- **User-Agent** - The SIP User-Agent header (phone model/firmware info)
- **Contact URI** - The SIP Contact URI
- **First Registration** - Timestamp of when the phone was first seen
- **Last Registration** - Timestamp of the most recent registration

## Features

### Automatic Registration Tracking

The system automatically tracks phone registrations without any manual intervention:

1. When a phone sends a SIP REGISTER message
2. The system extracts the extension number, IP address, and attempts to extract MAC address
3. Registration information is stored in the `registered_phones` database table
4. On re-registration, existing records are updated with the latest information

### Data Preservation on Re-registration

Phones typically re-register every 30-60 seconds to maintain their registration. However, not all phones send complete information in every REGISTER message. The system intelligently preserves existing data:

- **MAC Address Preservation**: If a phone initially registers with a MAC address but later re-registers without it, the stored MAC is preserved
- **IP Address Preservation**: Similar preservation applies to IP addresses
- **User-Agent Preservation**: Preserves device model/firmware information
- **Contact URI Preservation**: Maintains SIP contact information

**Why this matters:**
- Some phones only send MAC address in the initial registration, not in subsequent re-registrations
- Preserves valuable device identification data throughout the phone's connection
- Ensures accurate phone inventory even when devices don't send complete info every time
- Prevents loss of MAC addresses that are critical for device identification and troubleshooting

### Automatic Cleanup on Boot

To prevent stale or outdated registrations from persisting:

1. **All phone registrations are cleared when the PBX server boots**
2. This ensures the table only contains currently active registrations
3. Phones automatically re-register when they reconnect (typically every 30-60 seconds)
4. Old/outdated registrations (e.g., phones that have been reassigned) are removed

**Why this matters:**
- Prevents confusion from old registration data (e.g., extension 1001 showing even though it's now 1234)
- Ensures the registered phones list accurately reflects the current state
- Phones will re-register automatically - no manual intervention needed

### MAC Address Extraction

The system attempts to extract MAC addresses from:
- **Contact Header** - Looks for `mac=XX:XX:XX:XX:XX:XX` parameter
- **SIP Instance ID** - Extracts MAC from `+sip.instance` UUID
- **User-Agent** - Searches for MAC address patterns in User-Agent string

### IP-Based Fallback

If MAC address is not available (some phones don't provide it):
- System falls back to tracking by IP address
- Particularly useful when phone IPs are statically configured
- Allows tracking phones even without MAC information

## Database Schema

The `registered_phones` table structure:

```sql
CREATE TABLE registered_phones (
    id INTEGER PRIMARY KEY,
    mac_address VARCHAR(20),              -- MAC address (optional)
    extension_number VARCHAR(20) NOT NULL, -- Extension number
    user_agent VARCHAR(255),              -- User-Agent header
    ip_address VARCHAR(50) NOT NULL,      -- IP address (required)
    first_registered TIMESTAMP,           -- First registration time
    last_registered TIMESTAMP,            -- Last registration time
    contact_uri VARCHAR(255),             -- SIP Contact URI
    UNIQUE(mac_address, extension_number),
    UNIQUE(ip_address, extension_number)
);
```

## API Endpoints

### List All Registered Phones

```bash
GET /api/registered-phones
```

Returns all phones that have registered with the system.

**Example Response:**
```json
[
  {
    "id": 1,
    "mac_address": "001565123456",
    "extension_number": "1001",
    "user_agent": "Yealink SIP-T46S 66.85.0.5",
    "ip_address": "192.168.1.100",
    "first_registered": "2025-12-05T10:00:00",
    "last_registered": "2025-12-05T12:00:00",
    "contact_uri": "<sip:1001@192.168.1.100:5060>"
  },
  {
    "id": 2,
    "mac_address": null,
    "extension_number": "1002",
    "user_agent": "Generic SIP Phone",
    "ip_address": "192.168.1.101",
    "first_registered": "2025-12-05T10:05:00",
    "last_registered": "2025-12-05T12:05:00",
    "contact_uri": "<sip:1002@192.168.1.101:5060>"
  }
]
```

### List Phones for Specific Extension

```bash
GET /api/registered-phones/extension/{number}
```

Returns all phones registered to a specific extension (useful if user has multiple devices).

**Example:**
```bash
curl http://localhost:8080/api/registered-phones/extension/1001
```

## Use Cases

### 1. Phone Inventory Management

Track all phones on your network:
```bash
curl http://localhost:8080/api/registered-phones
```

### 2. Extension Device History

See all devices that have registered to a specific extension:
```bash
curl http://localhost:8080/api/registered-phones/extension/1001
```

### 3. Troubleshooting

When users report phone issues:
- Check which device they're using (MAC/IP)
- Verify registration timestamps
- Check User-Agent to identify phone model/firmware

### 4. Security Auditing

- Monitor which devices are registering to extensions
- Detect unauthorized devices
- Track when phones were last active

### 5. Network Planning

- Identify all active phones on network
- Map phone MAC addresses to IPs
- Plan IP address allocation

## Database Requirements

This feature requires a database backend (PostgreSQL or SQLite):

### PostgreSQL (Recommended for Production)

```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  name: pbx_system
  user: pbx_user
  password: YourSecurePassword
```

### SQLite (For Testing/Small Deployments)

```yaml
database:
  type: sqlite
  path: pbx.db
```

If database is not available, the feature will be disabled and phones will only be tracked in-memory during runtime.

## Implementation Details

### MAC Address Normalization

MAC addresses are normalized to a consistent format:
- Lowercase
- No separators (colons or hyphens removed)
- Example: `00:15:65:12:34:56` becomes `001565123456`

### Update Strategy

When a phone re-registers:
1. System checks if phone already exists (by MAC or IP)
2. If exists: Updates `last_registered`, `user_agent`, `contact_uri`
3. If new: Creates new record with `first_registered` and `last_registered`

### Privacy Considerations

The system stores:
- Technical identifiers (MAC, IP, User-Agent)
- Registration timestamps
- Extension associations

This data is used for:
- System administration
- Troubleshooting
- Network management

Consider your organization's privacy policies when deploying.

## Examples

### Query All Phones

```bash
curl http://localhost:8080/api/registered-phones | jq .
```

### Filter by Extension

```bash
curl http://localhost:8080/api/registered-phones/extension/1001 | jq .
```

### Count Registered Phones

```bash
curl -s http://localhost:8080/api/registered-phones | jq 'length'
```

### Find Phones without MAC

```bash
curl -s http://localhost:8080/api/registered-phones | jq '.[] | select(.mac_address == null)'
```

### List Unique Phone Models

```bash
curl -s http://localhost:8080/api/registered-phones | jq -r '.[].user_agent' | sort -u
```

## Monitoring

### Check Phone Activity

Monitor when phones last registered:

```bash
curl -s http://localhost:8080/api/registered-phones | \
  jq -r '.[] | "\(.extension_number): \(.last_registered)"'
```

### Identify Stale Registrations

Find phones that haven't registered recently (requires date comparison logic).

## Troubleshooting

### No MAC Addresses Captured

If MAC addresses are showing as `null`:
1. Check if your phones include MAC in SIP headers
2. Some phones only include MAC in Contact or User-Agent
3. System will still work with IP-based tracking

### Database Not Available

If you see warnings about database not available:
1. Verify database configuration in `config.yml`
2. Ensure PostgreSQL/SQLite is running
3. Check database credentials
4. Run `python scripts/verify_database.py` for diagnostics

### Duplicate Entries

The system prevents duplicates with unique constraints:
- `(mac_address, extension_number)` must be unique
- `(ip_address, extension_number)` must be unique

If a phone changes IP or extension, a new record is created.

## Future Enhancements

Potential future improvements:
- Web UI for viewing registered phones
- Historical tracking of registration changes
- Alerts for new/unknown devices
- Integration with phone provisioning system
- Geolocation based on IP address
- Device health monitoring

## Related Documentation

- [Database Setup Guide](POSTGRESQL_SETUP.md)
- [Phone Provisioning](PHONE_PROVISIONING.md)
- [API Documentation](API_DOCUMENTATION.md)
