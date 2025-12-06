# Phone Book Feature Guide

## Overview

The Phone Book feature provides a centralized directory that can be automatically synchronized from Active Directory and pushed to IP phones. This allows users to have an up-to-date company directory directly on their desk phones.

## Features

- **Centralized Directory**: Store employee names and extension numbers in one place
- **Active Directory Sync**: Automatically populate phone book from AD
- **Multi-format Export**: Support for Yealink XML, Cisco XML, and JSON formats
- **Database Storage**: Persistent storage in PostgreSQL or SQLite
- **REST API**: Full API for management and integration
- **Search Capability**: Quick lookup of contacts

## Configuration

Add the following to your `config.yml`:

```yaml
features:
  phone_book:
    enabled: true
    auto_sync_from_ad: true  # Automatically sync from Active Directory
```

## Database Schema

The phone book uses the following database table:

```sql
CREATE TABLE phone_book (
    id SERIAL PRIMARY KEY,
    extension VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    email VARCHAR(255),
    mobile VARCHAR(50),
    office_location VARCHAR(100),
    ad_synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Active Directory Integration

When Active Directory integration is enabled and `auto_sync_from_ad` is set to `true`, the phone book will automatically sync entries from AD during user synchronization.

The sync process:
1. Reads user information from Active Directory
2. Updates phone book with name, extension, and email
3. Marks entries as `ad_synced` for tracking
4. Updates existing entries or creates new ones

To manually trigger a sync:

```bash
curl -X POST http://localhost:8080/api/phone-book/sync
```

## REST API Endpoints

### Get All Entries

```bash
curl http://localhost:8080/api/phone-book
```

Response:
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

```bash
curl -X POST http://localhost:8080/api/phone-book \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "1001",
    "name": "John Doe",
    "department": "Sales",
    "email": "john@example.com",
    "mobile": "555-1234",
    "office_location": "Building A"
  }'
```

### Search Entries

```bash
curl "http://localhost:8080/api/phone-book/search?q=John"
```

### Delete Entry

```bash
curl -X DELETE http://localhost:8080/api/phone-book/1001
```

### Export Formats

#### Yealink XML Format
```bash
curl http://localhost:8080/api/phone-book/export/xml
```

Returns XML in Yealink format that can be served to Yealink phones.

#### Cisco XML Format
```bash
curl http://localhost:8080/api/phone-book/export/cisco-xml
```

Returns XML in Cisco format for Cisco IP phones.

#### JSON Format
```bash
curl http://localhost:8080/api/phone-book/export/json
```

Returns JSON format for custom integrations.

## Phone Integration

### Yealink Phones

Configure your Yealink phones to fetch the directory from the PBX:

1. In the phone's web interface, go to Directory → Remote Phone Book
2. Set the URL to: `http://<pbx-ip>:8080/api/phone-book/export/xml`
3. Save and reboot the phone

### Cisco Phones

For Cisco phones, configure the directory URL in the phone configuration:

```xml
<directoryURL>http://<pbx-ip>:8080/api/phone-book/export/cisco-xml</directoryURL>
```

### Other Phones

For phones that support JSON or custom formats, use the JSON export endpoint and transform as needed.

## Manual Management

You can manually add entries to the phone book even without Active Directory:

```python
from pbx.features.phone_book import PhoneBook

# Create phone book instance
phone_book = PhoneBook(config, database)

# Add entry
phone_book.add_entry(
    extension="1001",
    name="John Doe",
    department="Sales",
    email="john@example.com",
    mobile="555-1234",
    office_location="Building A"
)

# Search entries
results = phone_book.search("Sales")

# Export to XML
xml_content = phone_book.export_xml()
```

## Best Practices

1. **Use Active Directory Sync**: If you have AD, enable `auto_sync_from_ad` to keep the directory up-to-date automatically
2. **Regular Updates**: Set up a cron job to trigger phone book sync regularly if needed
3. **Phone Configuration**: Configure phones to refresh the directory periodically (e.g., daily)
4. **Backup**: The phone book is stored in the database, ensure you have database backups
5. **Testing**: Test the export formats with your specific phone models before deployment

## Troubleshooting

### Phone book not syncing from AD

- Check that Active Directory integration is enabled
- Verify `auto_sync_from_ad` is set to `true`
- Check PBX logs for AD sync errors
- Ensure AD users have extension numbers assigned

### Phones not showing directory

- Verify the phone can reach the PBX API (check firewall)
- Test the export URL in a browser
- Check phone configuration for correct directory URL
- Ensure the phone supports the export format (XML vs JSON)

### Entries not appearing

- Check database connection
- Verify entries were added successfully via API
- Check PBX logs for errors
- Query the database directly: `SELECT * FROM phone_book;`

## Security Considerations

- The phone book API endpoints are currently unauthenticated
- Consider adding authentication if the PBX is exposed to untrusted networks
- Directory information should be treated as confidential
- Use HTTPS if serving directory over the internet
