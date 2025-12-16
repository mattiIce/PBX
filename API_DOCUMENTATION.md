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

## Paging System

### GET /api/paging/zones

Get all configured paging zones.

**Response:**
```json
{
  "zones": [
    {
      "extension": "701",
      "name": "Warehouse",
      "description": "Warehouse paging zone",
      "device_id": "dac-1"
    },
    {
      "extension": "702",
      "name": "Office",
      "description": "Office area paging",
      "device_id": "dac-1"
    }
  ],
  "all_call_extension": "700"
}
```

### POST /api/paging/zones

Add a new paging zone.

**Request:**
```json
{
  "extension": "703",
  "name": "Production Floor",
  "description": "Production floor paging",
  "device_id": "dac-2"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Zone added successfully",
  "zone": {
    "extension": "703",
    "name": "Production Floor",
    "description": "Production floor paging",
    "device_id": "dac-2"
  }
}
```

### DELETE /api/paging/zones/{extension}

Delete a paging zone.

**Response:**
```json
{
  "success": true,
  "message": "Zone deleted"
}
```

### GET /api/paging/devices

Get all configured DAC devices.

**Response:**
```json
{
  "devices": [
    {
      "device_id": "dac-1",
      "name": "Main PA System",
      "type": "sip_gateway",
      "sip_address": "paging@192.168.1.10:5060",
      "status": "Online"
    }
  ]
}
```

### POST /api/paging/devices

Add a new DAC device.

**Request:**
```json
{
  "device_id": "dac-2",
  "name": "Production PA System",
  "type": "sip_gateway",
  "sip_address": "paging@192.168.1.20:5060"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Device added successfully"
}
```

### GET /api/paging/active

Get all active paging sessions.

**Response:**
```json
{
  "active_pages": [
    {
      "page_id": "page-20251215143022-1001-abc123",
      "from_extension": "1001",
      "to_extension": "701",
      "zone_names": "Warehouse",
      "started_at": "2025-12-15T14:30:22Z",
      "status": "active"
    }
  ]
}
```

## Framework Features API

The following endpoints provide access to advanced framework features. These features have complete backend implementations and REST APIs, but may require external service integration for full production use.

### Conversational AI

AI-powered call handling and auto-responses.

#### GET /api/framework/conversational-ai/config

Get AI configuration.

#### GET /api/framework/conversational-ai/statistics

Get AI statistics.

#### GET /api/framework/conversational-ai/conversations

Get active conversations.

#### POST /api/framework/conversational-ai/conversation

Start a new conversation.

**Request:**
```json
{
  "call_id": "call-123",
  "caller_id": "+15551234567"
}
```

#### POST /api/framework/conversational-ai/process

Process user input in conversation.

**Request:**
```json
{
  "call_id": "call-123",
  "input": "I need help with my order"
}
```

#### POST /api/framework/conversational-ai/config

Configure AI provider.

**Request:**
```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "options": {
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

### Predictive Dialing

AI-optimized outbound campaign management.

#### GET /api/framework/predictive-dialing/campaigns

List all campaigns.

#### GET /api/framework/predictive-dialing/statistics

Get dialing statistics.

#### GET /api/framework/predictive-dialing/campaign/{id}

Get specific campaign details.

#### POST /api/framework/predictive-dialing/campaign

Create a new campaign.

**Request:**
```json
{
  "campaign_id": "campaign-001",
  "name": "Q1 Outreach",
  "dialing_mode": "progressive",
  "max_attempts": 3,
  "retry_interval": 3600
}
```

#### POST /api/framework/predictive-dialing/contacts

Add contacts to campaign.

**Request:**
```json
{
  "campaign_id": "campaign-001",
  "contacts": [
    {
      "contact_id": "c1",
      "phone_number": "+15551234567",
      "data": {"name": "John Doe"}
    }
  ]
}
```

#### POST /api/framework/predictive-dialing/campaign/{id}/start

Start a campaign.

#### POST /api/framework/predictive-dialing/campaign/{id}/pause

Pause a campaign.

### Voice Biometrics

Speaker authentication and fraud detection.

#### GET /api/framework/voice-biometrics/profiles

List all voice profiles.

#### GET /api/framework/voice-biometrics/statistics

Get biometrics statistics.

#### GET /api/framework/voice-biometrics/profile/{user_id}

Get specific voice profile.

#### POST /api/framework/voice-biometrics/profile

Create a voice profile.

**Request:**
```json
{
  "user_id": "user123",
  "extension": "1001"
}
```

#### POST /api/framework/voice-biometrics/enroll

Start enrollment process.

**Request:**
```json
{
  "user_id": "user123"
}
```

#### POST /api/framework/voice-biometrics/verify

Verify speaker identity.

**Request:**
```json
{
  "user_id": "user123",
  "audio_data": "base64_encoded_audio..."
}
```

#### DELETE /api/framework/voice-biometrics/profile/{user_id}

Delete a voice profile.

### Call Quality Prediction

ML-based quality prediction and monitoring.

#### GET /api/framework/call-quality-prediction/predictions

Get all predictions.

#### GET /api/framework/call-quality-prediction/statistics

Get prediction statistics.

#### GET /api/framework/call-quality-prediction/prediction/{call_id}

Get prediction for specific call.

#### POST /api/framework/call-quality-prediction/metrics

Collect quality metrics for a call.

**Request:**
```json
{
  "call_id": "call-123",
  "packet_loss": 0.5,
  "jitter": 20,
  "latency": 50,
  "bandwidth": 100
}
```

#### POST /api/framework/call-quality-prediction/train

Train the prediction model.

**Request:**
```json
{
  "data": [
    {
      "packet_loss": 0.5,
      "jitter": 20,
      "latency": 50,
      "mos": 4.2
    }
  ]
}
```

### Video Codec

Video codec support for H.264/H.265.

#### GET /api/framework/video-codec/codecs

Get supported video codecs.

#### GET /api/framework/video-codec/statistics

Get video codec statistics.

#### POST /api/framework/video-codec/bandwidth

Calculate required bandwidth for video.

**Request:**
```json
{
  "resolution": [1920, 1080],
  "framerate": 30,
  "codec": "h264",
  "quality": "high"
}
```

### Mobile Number Portability

Mobile DID mapping and routing.

#### GET /api/framework/mobile-portability/mappings

List all number mappings.

#### GET /api/framework/mobile-portability/statistics

Get portability statistics.

#### GET /api/framework/mobile-portability/mapping/{number}

Get specific mapping.

#### POST /api/framework/mobile-portability/mapping

Create number mapping.

**Request:**
```json
{
  "business_number": "+15551234567",
  "extension": "1001",
  "mobile_device": "mobile:user123@pbx.example.com",
  "forward_to_mobile": true
}
```

#### POST /api/framework/mobile-portability/mapping/{number}/toggle

Toggle mapping active status.

**Request:**
```json
{
  "active": true
}
```

#### DELETE /api/framework/mobile-portability/mapping/{number}

Delete a number mapping.

### Call Recording Analytics

AI analysis of call recordings.

#### GET /api/framework/recording-analytics/analyses

Get all recording analyses.

#### GET /api/framework/recording-analytics/statistics

Get analytics statistics.

#### GET /api/framework/recording-analytics/analysis/{id}

Get specific analysis.

#### POST /api/framework/recording-analytics/analyze

Analyze a recording.

**Request:**
```json
{
  "recording_id": "rec-123",
  "audio_path": "/recordings/call-123.wav",
  "metadata": {
    "extension": "1001",
    "duration": 180
  }
}
```

#### POST /api/framework/recording-analytics/search

Search recordings by criteria.

**Request:**
```json
{
  "criteria": {
    "sentiment": "positive",
    "keywords": ["sales", "support"]
  }
}
```

### Predictive Voicemail Drop

Automated voicemail message delivery.

#### GET /api/framework/voicemail-drop/messages

List all drop messages.

#### GET /api/framework/voicemail-drop/statistics

Get drop statistics.

#### POST /api/framework/voicemail-drop/message

Add a drop message.

**Request:**
```json
{
  "message_id": "msg-001",
  "name": "Holiday Greeting",
  "audio_path": "/messages/holiday.wav",
  "description": "2024 Holiday greeting message"
}
```

#### POST /api/framework/voicemail-drop/drop

Drop a message to voicemail.

**Request:**
```json
{
  "call_id": "call-123",
  "message_id": "msg-001"
}
```

### DNS SRV Failover

Automatic DNS-based server failover.

#### GET /api/framework/dns-srv/records

Get cached SRV records.

#### GET /api/framework/dns-srv/statistics

Get DNS SRV statistics.

#### POST /api/framework/dns-srv/lookup

Lookup SRV records.

**Request:**
```json
{
  "service": "sip",
  "protocol": "tcp",
  "domain": "example.com"
}
```

### Session Border Controller

Security and NAT traversal for SIP/RTP.

#### GET /api/framework/sbc/statistics

Get SBC statistics.

#### GET /api/framework/sbc/relays

Get active RTP relays.

#### POST /api/framework/sbc/relay

Allocate RTP relay for a call.

**Request:**
```json
{
  "call_id": "call-123",
  "codec": "PCMU"
}
```

### Data Residency Controls

Geographic data storage compliance.

#### GET /api/framework/data-residency/regions

Get configured storage regions.

#### GET /api/framework/data-residency/statistics

Get residency statistics.

#### POST /api/framework/data-residency/location

Get storage location for data category.

**Request:**
```json
{
  "category": "call_recordings",
  "user_region": "us-east-1"
}
```

## See Also

- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md) - Detailed framework feature documentation
- [README.md](README.md) - Getting started guide
- [TODO.md](TODO.md) - Implementation status and roadmap
