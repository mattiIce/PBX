# Active Directory Search API Guide

## Overview

The Active Directory Search API endpoint allows you to search for users in your Active Directory by name, email, or phone number (telephoneNumber attribute). This is useful for directory lookups, auto-complete features, and phone book integration.

## Endpoint

```
GET /api/integrations/ad/search?q={query}&max_results={max}
```

## Parameters

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| `q` | Yes | string | - | Search query (searches name, email, and telephoneNumber) |
| `max_results` | No | integer | 50 | Maximum number of results to return (1-100) |

## Response Format

### Success Response

```json
{
  "success": true,
  "count": 2,
  "results": [
    {
      "username": "cmattinson",
      "display_name": "Codi Mattinson",
      "email": "cmattinson@albl.com",
      "phone": "555-1234"
    },
    {
      "username": "bsautter",
      "display_name": "Bill Sautter",
      "email": "bsautter@albl.com",
      "phone": "555-5678"
    }
  ]
}
```

### Error Responses

**Missing query parameter:**
```json
{
  "error": "Query parameter 'q' is required"
}
```
**Status Code:** 400

**Invalid max_results:**
```json
{
  "error": "max_results must be between 1 and 100"
}
```
**Status Code:** 400

**AD integration not enabled:**
```json
{
  "error": "Active Directory integration not enabled"
}
```
**Status Code:** 500

## Examples

### Search by Name

```bash
curl "http://localhost:8080/api/integrations/ad/search?q=John"
```

### Search by Email

```bash
curl "http://localhost:8080/api/integrations/ad/search?q=john@company.com"
```

### Search by Phone Number

```bash
curl "http://localhost:8080/api/integrations/ad/search?q=555-1234"
```

This searches the `telephoneNumber` attribute in Active Directory.

### Limit Results

```bash
curl "http://localhost:8080/api/integrations/ad/search?q=Smith&max_results=10"
```

## Search Behavior

The API searches the following Active Directory attributes:
- `cn` (Common Name)
- `displayName` (Display Name)
- `mail` (Email Address)
- **`telephoneNumber` (Phone Number)**

The search uses wildcards, so partial matches are returned. For example:
- Query `"John"` will match `"John Smith"`, `"Johnson"`, etc.
- Query `"555"` will match any phone number containing `"555"`

## Requirements

1. **Active Directory Integration Must Be Enabled**
   
   In `config.yml`:
   ```yaml
   integrations:
     active_directory:
       enabled: true
       server: ldaps://your-ad-server.com:636
       base_dn: DC=company,DC=com
       bind_dn: CN=Administrator,CN=Users,DC=company,DC=com
       bind_password: ${AD_BIND_PASSWORD}
       use_ssl: true
   ```

2. **AD Bind Account Must Have Read Permissions**
   
   The account specified in `bind_dn` must have permission to read user attributes including `telephoneNumber`.

3. **ldap3 Python Library**
   
   ```bash
   pip install ldap3
   ```

## Use Cases

### Directory Search Feature

Build an auto-complete directory search for your admin interface:

```javascript
async function searchDirectory(query) {
  const response = await fetch(
    `http://pbx-server:8080/api/integrations/ad/search?q=${encodeURIComponent(query)}&max_results=10`
  );
  const data = await response.json();
  return data.results;
}
```

### Phone Number Lookup

Look up user information by phone number:

```javascript
async function lookupByPhone(phoneNumber) {
  const response = await fetch(
    `http://pbx-server:8080/api/integrations/ad/search?q=${encodeURIComponent(phoneNumber)}&max_results=1`
  );
  const data = await response.json();
  return data.results[0];
}
```

### Caller ID Enhancement

Integrate with your PBX to show caller information:

```python
import requests

def get_caller_info(phone_number):
    """Get caller information from AD by phone number"""
    response = requests.get(
        f"http://localhost:8080/api/integrations/ad/search",
        params={'q': phone_number, 'max_results': 1}
    )
    data = response.json()
    if data['success'] and data['count'] > 0:
        return data['results'][0]
    return None

# Usage
caller = get_caller_info("555-1234")
if caller:
    print(f"Call from: {caller['display_name']} ({caller['phone']})")
```

## Troubleshooting

### No Results Returned

1. **Check AD Connection**
   ```bash
   curl "http://localhost:8080/api/integrations/ad/status"
   ```
   Verify that `connection: true` is returned.

2. **Verify Users Have telephoneNumber Attribute**
   
   In Active Directory, ensure users have the `telephoneNumber` attribute populated:
   ```powershell
   Get-ADUser -Filter {SamAccountName -eq "username"} -Properties telephoneNumber
   ```

3. **Check Search Base**
   
   Ensure `user_search_base` in your config includes the OU where users are located:
   ```yaml
   integrations:
     active_directory:
       user_search_base: CN=Users,DC=company,DC=com
   ```

### Search is Slow

- Reduce `max_results` to limit the number of results returned
- Use more specific search queries
- Ensure your AD server has proper indexing on the search attributes

### Permission Errors

The bind account needs read access to:
- `sAMAccountName`
- `displayName`
- `mail`
- `telephoneNumber`

In Active Directory Users and Computers, verify the account has "Read" permissions on these attributes.

## Security Considerations

1. **Use LDAPS (SSL/TLS)**: Always use `ldaps://` protocol with port 636
2. **Read-Only Account**: Use a dedicated read-only account for AD binding
3. **API Authentication**: Consider adding authentication to the API endpoint if exposed to untrusted networks
4. **Rate Limiting**: Implement rate limiting to prevent abuse of the search endpoint

## Related Documentation

- [AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md) - Active Directory user synchronization
- [LDAPS_PHONEBOOK_GUIDE.md](LDAPS_PHONEBOOK_GUIDE.md) - LDAP phone book for IP phones
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Complete API reference

## Support

For issues or questions:
- Check PBX logs: `tail -f logs/pbx.log`
- Review Active Directory integration status via API
- GitHub Issues: https://github.com/mattiIce/PBX/issues
