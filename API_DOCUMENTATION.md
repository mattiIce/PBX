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
