# Phone Book and Paging System API Reference

## Phone Book API Endpoints

### Get All Entries
```http
GET /api/phone-book
```

**Response:**
```json
[
  {
    "extension": "1001",
    "name": "John Doe",
    "department": "Sales",
    "email": "john@example.com",
    "mobile": "555-1234",
    "office_location": "Building A",
    "ad_synced": true,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00"
  }
]
```

### Add/Update Entry
```http
POST /api/phone-book
Content-Type: application/json

{
  "extension": "1001",
  "name": "John Doe",
  "department": "Sales",
  "email": "john@example.com",
  "mobile": "555-1234",
  "office_location": "Building A"
}
```

### Search Entries
```http
GET /api/phone-book/search?q=John
```

### Delete Entry
```http
DELETE /api/phone-book/{extension}
```

### Sync from Active Directory
```http
POST /api/phone-book/sync
```

**Response:**
```json
{
  "success": true,
  "message": "Phone book synced from Active Directory",
  "synced_count": 25
}
```

### Export Formats

#### Yealink XML
```http
GET /api/phone-book/export/xml
```

Returns:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<YealinkIPPhoneDirectory>
  <Title>Company Directory</Title>
  <DirectoryEntry>
    <Name>John Doe</Name>
    <Telephone>1001</Telephone>
  </DirectoryEntry>
</YealinkIPPhoneDirectory>
```

#### Cisco XML
```http
GET /api/phone-book/export/cisco-xml
```

Returns:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneDirectory>
  <Title>Company Directory</Title>
  <Prompt>Select a contact</Prompt>
  <DirectoryEntry>
    <Name>John Doe</Name>
    <Telephone>1001</Telephone>
  </DirectoryEntry>
</CiscoIPPhoneDirectory>
```

#### JSON
```http
GET /api/phone-book/export/json
```

---

## Paging System API Endpoints

### Get All Zones
```http
GET /api/paging/zones
```

**Response:**
```json
[
  {
    "extension": "701",
    "name": "Zone 1 - Office",
    "description": "Main office area",
    "dac_device": "paging-gateway-1",
    "created_at": "2024-01-01T10:00:00"
  }
]
```

### Add Zone
```http
POST /api/paging/zones
Content-Type: application/json

{
  "extension": "701",
  "name": "Zone 1 - Office",
  "description": "Main office area",
  "dac_device": "paging-gateway-1"
}
```

### Delete Zone
```http
DELETE /api/paging/zones/{extension}
```

### Get DAC Devices
```http
GET /api/paging/devices
```

**Response:**
```json
[
  {
    "device_id": "paging-gateway-1",
    "device_type": "cisco_vg224",
    "sip_uri": "sip:paging@192.168.1.100:5060",
    "ip_address": "192.168.1.100",
    "port": 5060,
    "configured_at": "2024-01-01T10:00:00"
  }
]
```

### Configure DAC Device
```http
POST /api/paging/devices
Content-Type: application/json

{
  "device_id": "paging-gateway-1",
  "device_type": "cisco_vg224",
  "sip_uri": "sip:paging@192.168.1.100:5060",
  "ip_address": "192.168.1.100",
  "port": 5060
}
```

### Get Active Pages
```http
GET /api/paging/active
```

**Response:**
```json
[
  {
    "page_id": "page-20241201120000-1001-abc123",
    "from_extension": "1001",
    "to_extension": "701",
    "zones": [
      {
        "extension": "701",
        "name": "Zone 1 - Office"
      }
    ],
    "zone_names": "Zone 1 - Office",
    "started_at": "2024-01-01T12:00:00",
    "status": "active"
  }
]
```

---

## Example Usage Scenarios

### Scenario 1: Setup Phone Book with AD Sync

1. **Enable phone book in config.yml:**
```yaml
features:
  phone_book:
    enabled: true
    auto_sync_from_ad: true
```

2. **Trigger sync from Active Directory:**
```bash
curl -X POST http://localhost:8080/api/phone-book/sync
```

3. **Verify entries:**
```bash
curl http://localhost:8080/api/phone-book
```

4. **Configure Yealink phones to fetch directory:**
   - Phone web interface → Directory → Remote Phone Book
   - URL: `http://<pbx-ip>:8080/api/phone-book/export/xml`

### Scenario 2: Manual Phone Book Entry

```bash
# Add entry
curl -X POST http://localhost:8080/api/phone-book \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "1001",
    "name": "Jane Smith",
    "department": "IT",
    "email": "jane@example.com"
  }'

# Search for entry
curl "http://localhost:8080/api/phone-book/search?q=Jane"

# Update entry (same API call)
curl -X POST http://localhost:8080/api/phone-book \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "1001",
    "name": "Jane Smith-Jones",
    "department": "IT",
    "email": "jane.jones@example.com"
  }'

# Delete entry
curl -X DELETE http://localhost:8080/api/phone-book/1001
```

### Scenario 3: Setup Paging System

1. **Enable paging in config.yml:**
```yaml
features:
  paging:
    enabled: true
    prefix: "7"
    all_call_extension: "700"
```

2. **Configure DAC device:**
```bash
curl -X POST http://localhost:8080/api/paging/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "paging-gateway-1",
    "device_type": "cisco_vg224",
    "sip_uri": "sip:paging@192.168.1.100:5060",
    "ip_address": "192.168.1.100",
    "port": 5060
  }'
```

3. **Add paging zones:**
```bash
# Zone 1 - Office
curl -X POST http://localhost:8080/api/paging/zones \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "701",
    "name": "Zone 1 - Office",
    "description": "Main office area"
  }'

# Zone 2 - Warehouse
curl -X POST http://localhost:8080/api/paging/zones \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "702",
    "name": "Zone 2 - Warehouse",
    "description": "Warehouse and loading dock"
  }'
```

4. **Make a page (from phone):**
   - Dial `700` for all-call paging
   - Dial `701` for office zone only
   - Dial `702` for warehouse zone only

5. **Monitor active pages:**
```bash
curl http://localhost:8080/api/paging/active
```

---

## Integration Examples

### Python Integration

```python
import requests

# Add phone book entry
response = requests.post(
    'http://localhost:8080/api/phone-book',
    json={
        'extension': '1001',
        'name': 'John Doe',
        'email': 'john@example.com'
    }
)
print(response.json())

# Get all entries
entries = requests.get('http://localhost:8080/api/phone-book').json()
for entry in entries:
    print(f"{entry['name']}: {entry['extension']}")

# Search
results = requests.get(
    'http://localhost:8080/api/phone-book/search',
    params={'q': 'John'}
).json()
```

### JavaScript Integration

```javascript
// Add phone book entry
fetch('http://localhost:8080/api/phone-book', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    extension: '1001',
    name: 'John Doe',
    email: 'john@example.com'
  })
})
.then(response => response.json())
.then(data => console.log(data));

// Get all entries
fetch('http://localhost:8080/api/phone-book')
  .then(response => response.json())
  .then(entries => {
    entries.forEach(entry => {
      console.log(`${entry.name}: ${entry.extension}`);
    });
  });
```

### cURL Scripts

```bash
#!/bin/bash
# bulk_add_phonebook.sh

# Array of entries
entries=(
  "1001:John Doe:Sales:john@example.com"
  "1002:Jane Smith:IT:jane@example.com"
  "1003:Bob Johnson:HR:bob@example.com"
)

for entry in "${entries[@]}"; do
  IFS=':' read -r ext name dept email <<< "$entry"
  
  curl -X POST http://localhost:8080/api/phone-book \
    -H "Content-Type: application/json" \
    -d "{
      \"extension\": \"$ext\",
      \"name\": \"$name\",
      \"department\": \"$dept\",
      \"email\": \"$email\"
    }"
  
  echo "Added: $name"
done
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message description"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (missing required parameters)
- `404` - Not Found
- `500` - Internal Server Error (feature not enabled or server error)

---

## Security Notes

- All endpoints are currently unauthenticated
- Consider adding authentication for production deployments
- Use HTTPS when exposing APIs over the internet
- Directory information should be treated as confidential
- Restrict access to paging API to prevent abuse
