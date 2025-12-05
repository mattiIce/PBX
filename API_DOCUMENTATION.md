# REST API Documentation

The PBX system provides a comprehensive REST API for management and integration.

## Base URL

```
http://localhost:8080/api
```

## Authentication

Currently, the API is unauthenticated. For production, implement authentication using:
- API keys in headers
- OAuth 2.0
- JWT tokens
- Basic authentication with reverse proxy

## Endpoints

### System Status

#### GET /api/status

Get overall system status.

**Response:**
```json
{
  "running": true,
  "registered_extensions": 3,
  "active_calls": 2,
  "total_calls": 145,
  "active_recordings": 1,
  "active_conferences": 0,
  "parked_calls": 0,
  "queued_calls": 0
}
```

### Extensions

#### GET /api/extensions

List all extensions.

**Response:**
```json
[
  {
    "number": "1001",
    "name": "Office Extension 1",
    "email": "ext1001@company.com",
    "registered": true,
    "allow_external": true
  },
  {
    "number": "1002",
    "name": "Office Extension 2",
    "email": "ext1002@company.com",
    "registered": false,
    "allow_external": true
  }
]
```

#### POST /api/extensions

Add a new extension.

**Request:**
```json
{
  "number": "1005",
  "name": "New User",
  "email": "newuser@company.com",
  "password": "securepassword123",
  "allow_external": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Extension added successfully"
}
```

#### PUT /api/extensions/{number}

Update an existing extension.

**Request:**
```json
{
  "name": "Updated Name",
  "email": "updated@company.com",
  "password": "newpassword123",
  "allow_external": false
}
```

**Note:** Password is optional. If not provided, the existing password will be kept.

**Response:**
```json
{
  "success": true,
  "message": "Extension updated successfully"
}
```

#### DELETE /api/extensions/{number}

Delete an extension.

**Response:**
```json
{
  "success": true,
  "message": "Extension deleted successfully"
}
```

### Calls

#### GET /api/calls

List active calls.

**Response:**
```json
[
  "Call call-123: 1001 -> 1002 (connected)",
  "Call call-456: 1003 -> 1004 (ringing)"
]
```

#### POST /api/call

Initiate a new call.

**Request:**
```json
{
  "from": "1001",
  "to": "1002"
}
```

**Response:**
```json
{
  "success": true,
  "call_id": "api-call-1001-1002"
}
```

#### POST /api/call/transfer

Transfer an active call.

**Request:**
```json
{
  "call_id": "call-123",
  "destination": "1003"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /api/call/hold

Put call on hold.

**Request:**
```json
{
  "call_id": "call-123"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /api/call/resume

Resume call from hold.

**Request:**
```json
{
  "call_id": "call-123"
}
```

**Response:**
```json
{
  "success": true
}
```

#### POST /api/call/park

Park a call.

**Request:**
```json
{
  "call_id": "call-123",
  "from_extension": "1001"
}
```

**Response:**
```json
{
  "success": true,
  "park_number": 70
}
```

### Presence

#### GET /api/presence

Get presence information for all users.

**Response:**
```json
[
  {
    "extension": "1001",
    "name": "Office Extension 1",
    "status": "available",
    "custom_message": "",
    "in_call": false,
    "last_activity": "2024-01-15T10:30:00",
    "idle_time": 120
  }
]
```

#### POST /api/presence/set

Set presence status.

**Request:**
```json
{
  "extension": "1001",
  "status": "away",
  "message": "Out for lunch"
}
```

**Status values:** `available`, `busy`, `away`, `do_not_disturb`, `in_meeting`, `offline`

**Response:**
```json
{
  "success": true
}
```

### Call Queues

#### GET /api/queues

Get status of all call queues.

**Response:**
```json
[
  {
    "queue_number": "8001",
    "name": "Sales Queue",
    "calls_waiting": 3,
    "total_agents": 5,
    "available_agents": 2,
    "average_wait_time": 45.5
  }
]
```

### Call Detail Records

#### GET /api/cdr

Get call detail records.

**Query Parameters:**
- `date`: Date in YYYY-MM-DD format (optional, defaults to today)
- `limit`: Maximum records to return (optional, default 100)

**Response:**
```json
[
  {
    "call_id": "call-123",
    "from_extension": "1001",
    "to_extension": "1002",
    "start_time": "2024-01-15T10:00:00",
    "answer_time": "2024-01-15T10:00:05",
    "end_time": "2024-01-15T10:15:30",
    "disposition": "answered",
    "duration": 930,
    "billsec": 925,
    "recording_file": "recordings/1001_to_1002_20240115_100000.wav"
  }
]
```

### Statistics

#### GET /api/statistics

Get call statistics.

**Query Parameters:**
- `date`: Date in YYYY-MM-DD format (optional, defaults to today)

**Response:**
```json
{
  "date": "2024-01-15",
  "total_calls": 145,
  "answered_calls": 132,
  "failed_calls": 13,
  "answer_rate": 91.03,
  "total_duration": 12450.5,
  "total_billsec": 12100.0,
  "average_duration": 85.9
}
```

### Parked Calls

#### GET /api/parked

Get list of parked calls.

**Response:**
```json
[
  {
    "call_id": "call-123",
    "park_number": 70,
    "from_extension": "1001",
    "original_destination": "1002",
    "parker": "1001",
    "park_time": "2024-01-15T10:30:00",
    "duration": 45
  }
]
```

## WebSocket Support (Future)

For real-time updates, WebSocket support will be added:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle real-time updates
};
```

## Error Responses

All endpoints return standard HTTP status codes:

- **200 OK**: Successful request
- **400 Bad Request**: Invalid parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

Error response format:
```json
{
  "error": "Description of the error"
}
```

## CORS

Cross-Origin Resource Sharing (CORS) is enabled by default for all origins. Configure in `config.yml`:

```yaml
api:
  enable_cors: true
```

## Rate Limiting (Future)

To prevent abuse, rate limiting will be implemented:
- 100 requests per minute per IP
- 1000 requests per hour per IP

## Examples

### Python
```python
import requests

# Get status
response = requests.get('http://localhost:8080/api/status')
print(response.json())

# Make a call
response = requests.post('http://localhost:8080/api/call', 
                        json={'from': '1001', 'to': '1002'})
print(response.json())
```

### JavaScript
```javascript
// Get status
fetch('http://localhost:8080/api/status')
  .then(response => response.json())
  .then(data => console.log(data));

// Make a call
fetch('http://localhost:8080/api/call', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({from: '1001', to: '1002'})
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### cURL
```bash
# Get status
curl http://localhost:8080/api/status

# Make a call
curl -X POST http://localhost:8080/api/call \
  -H "Content-Type: application/json" \
  -d '{"from":"1001","to":"1002"}'

# Set presence
curl -X POST http://localhost:8080/api/presence/set \
  -H "Content-Type: application/json" \
  -d '{"extension":"1001","status":"away","message":"In a meeting"}'
```

### Configuration

#### GET /api/config

Get current system configuration (SMTP and email settings).

**Response:**
```json
{
  "smtp": {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "pbx@company.com"
  },
  "email": {
    "from_address": "voicemail@company.com"
  },
  "email_notifications": true
}
```

#### PUT /api/config

Update system configuration.

**Request:**
```json
{
  "smtp": {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "pbx@company.com",
    "password": "app-password"
  },
  "email": {
    "from_address": "voicemail@company.com"
  },
  "email_notifications": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated successfully. Restart required."
}
```

**Note:** Configuration changes are saved to `config.yml` and require a system restart to take effect.

## Phone Registration & MAC/IP Tracking

### Overview

The PBX system tracks phones in two ways:
1. **Provisioning System** - Stores MAC addresses assigned to extensions during device registration
2. **SIP Registration** - Tracks IP addresses when phones actually register via SIP

The challenge: **Phones provide their IP when registering but often don't provide their MAC address**. The correlation endpoints solve this problem by linking these two data sources.

### GET /api/registered-phones

List all phones that have registered via SIP (tracks IP addresses).

**Response:**
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

### GET /api/registered-phones/with-mac

**NEW:** Enhanced endpoint that correlates registered phones with provisioning data to provide MAC addresses.

This endpoint:
- Lists all phones from SIP registration (IP addresses)
- Cross-references with provisioning system (MAC addresses)
- Adds MAC, vendor, and model information when available

**Response:**
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
    "contact_uri": "<sip:1001@192.168.1.100:5060>",
    "mac_source": "sip_registration",
    "vendor": "yealink",
    "model": "t46s",
    "config_url": "http://192.168.1.14:8080/provision/001565123456.cfg"
  },
  {
    "id": 2,
    "mac_address": "001565abcdef",
    "extension_number": "1002",
    "user_agent": "PolycomVVX-VVX_450-UA/5.9.0.9373",
    "ip_address": "192.168.1.101",
    "first_registered": "2025-12-05T10:05:00",
    "last_registered": "2025-12-05T12:05:00",
    "contact_uri": "<sip:1002@192.168.1.101:5060>",
    "mac_source": "provisioning",
    "vendor": "polycom",
    "model": "vvx450",
    "config_url": "http://192.168.1.14:8080/provision/001565abcdef.cfg"
  }
]
```

**Key Features:**
- If phone provided MAC in SIP: `mac_source: "sip_registration"`
- If MAC came from provisioning: `mac_source: "provisioning"`
- Includes vendor, model, and config URL from provisioning system

### GET /api/registered-phones/extension/{number}

List all registered phones for a specific extension.

**Example:**
```bash
curl http://localhost:8080/api/registered-phones/extension/1001
```

**Response:**
```json
[
  {
    "id": 1,
    "mac_address": "001565123456",
    "extension_number": "1001",
    "ip_address": "192.168.1.100",
    "user_agent": "Yealink SIP-T46S 66.85.0.5",
    "first_registered": "2025-12-05T10:00:00",
    "last_registered": "2025-12-05T12:00:00"
  }
]
```

### GET /api/phone-lookup/{mac_or_ip}

**NEW:** Unified lookup endpoint that accepts either a MAC address or IP address and returns correlated information.

**Lookup by MAC Address:**
```bash
curl http://localhost:8080/api/phone-lookup/00:15:65:12:34:56
```

**Response:**
```json
{
  "identifier": "00:15:65:12:34:56",
  "type": "mac",
  "provisioned_device": {
    "mac_address": "001565123456",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s",
    "config_url": "http://192.168.1.14:8080/provision/001565123456.cfg"
  },
  "registered_phone": {
    "id": 1,
    "mac_address": "001565123456",
    "extension_number": "1001",
    "ip_address": "192.168.1.100",
    "user_agent": "Yealink SIP-T46S 66.85.0.5"
  },
  "correlation": {
    "matched": true,
    "extension": "1001",
    "mac_address": "001565123456",
    "ip_address": "192.168.1.100",
    "vendor": "yealink",
    "model": "t46s"
  }
}
```

**Lookup by IP Address:**
```bash
curl http://localhost:8080/api/phone-lookup/192.168.1.100
```

**Response:**
```json
{
  "identifier": "192.168.1.100",
  "type": "ip",
  "registered_phone": {
    "id": 1,
    "extension_number": "1001",
    "ip_address": "192.168.1.100",
    "mac_address": null,
    "user_agent": "Polycom VVX 450"
  },
  "provisioned_device": {
    "mac_address": "001565abcdef",
    "extension_number": "1001",
    "vendor": "polycom",
    "model": "vvx450"
  },
  "correlation": {
    "matched": true,
    "extension": "1001",
    "mac_address": "001565abcdef",
    "ip_address": "192.168.1.100",
    "vendor": "polycom",
    "model": "vvx450"
  }
}
```

**Use Cases:**

1. **Given IP, find MAC:**
   - Phone registers with IP 192.168.1.100
   - Look up by IP to find extension 1001
   - Cross-reference with provisioning to get MAC address

2. **Given MAC, find IP:**
   - Device provisioned with MAC 00:15:65:12:34:56
   - Look up by MAC to find it's registered to extension 1001
   - Get current IP address from registration data

3. **Identify which phone is which:**
   - See phone on network with IP 192.168.1.101
   - Use lookup to determine it's the Polycom VVX 450 for extension 1002
   - Get MAC address for inventory/asset management

## Integration Examples

### CRM Integration
Use the API to click-to-dial from your CRM:
```python
def click_to_dial(agent_extension, customer_number):
    response = requests.post('http://pbx.company.com:8080/api/call',
                            json={'from': agent_extension, 'to': customer_number})
    return response.json()
```

### Call Center Dashboard
Real-time queue monitoring:
```javascript
setInterval(() => {
  fetch('http://pbx.company.com:8080/api/queues')
    .then(r => r.json())
    .then(queues => updateDashboard(queues));
}, 5000);
```

### Presence Widget
Show team availability:
```javascript
fetch('http://pbx.company.com:8080/api/presence')
  .then(r => r.json())
  .then(users => {
    users.forEach(user => {
      document.getElementById(`user-${user.extension}`)
        .className = user.status;
    });
  });
```
