# CRM Integration and Screen Pop - Implementation Guide

## Overview

The CRM Integration feature provides automatic caller identification and screen pop capabilities, enabling customer information to be displayed automatically when a call comes in. This enhances customer service by providing context before answering.

**Status**: ✅ **Implemented and Tested**

## Features

- **Multi-Source Lookup**: Search across Phone Book, Active Directory, and external CRMs
- **Caching**: Performance optimization with configurable cache timeout
- **Screen Pop**: Webhook-based notifications for incoming calls
- **API Access**: RESTful API for caller lookup
- **Flexible Providers**: Easy to add custom lookup sources

## Architecture

### Components

1. **CRMIntegration** - Main integration controller
2. **CRMLookupProvider** - Base class for lookup providers
3. **PhoneBookLookupProvider** - Searches internal phone book
4. **ActiveDirectoryLookupProvider** - Searches AD by phone number
5. **ExternalCRMLookupProvider** - Queries external CRM APIs
6. **CallerInfo** - Represents caller information

### Lookup Flow

```
Incoming Call
    ↓
CRM Integration
    ↓ (Priority Order)
Phone Book Provider → AD Provider → External CRM Provider
    ↓
Cache Result
    ↓
Trigger Screen Pop Webhook
    ↓
External System (CRM, Dashboard, etc.)
```

## Configuration

### Enable CRM Integration in config.yml

```yaml
features:
  crm_integration:
    enabled: true
    cache_enabled: true       # Cache lookup results
    cache_timeout: 3600       # Cache timeout in seconds (1 hour)
    
    # Lookup providers (tried in order)
    providers:
      # Phone Book lookup
      - type: phone_book
        enabled: true
        name: PhoneBook
      
      # Active Directory lookup
      - type: active_directory
        enabled: true
        name: ActiveDirectory
      
      # External CRM API lookup (example)
      - type: external_crm
        enabled: true
        name: SalesforceCRM
        url: https://your-crm.com/api/lookup
        api_key: your-api-key-here
        timeout: 5
```

## API Endpoints

### 1. Lookup Caller Information

Look up caller information by phone number.

**Request:**
```bash
GET /api/crm/lookup?phone=555-1234
```

**Response:**
```json
{
  "found": true,
  "caller_info": {
    "phone_number": "555-1234",
    "name": "John Doe",
    "company": "Acme Corp",
    "email": "john@acme.com",
    "account_id": "ACC-12345",
    "contact_id": "CON-67890",
    "tags": ["vip", "sales"],
    "notes": "Preferred customer, always calls about orders",
    "last_contact": "2025-12-01T10:30:00",
    "contact_count": 15,
    "source": "phone_book",
    "custom_fields": {
      "customer_since": "2020-01-15",
      "tier": "gold"
    }
  }
}
```

### 2. Get Provider Status

Get status of all configured lookup providers.

**Request:**
```bash
GET /api/crm/providers
```

**Response:**
```json
{
  "enabled": true,
  "providers": [
    {
      "name": "PhoneBook",
      "enabled": true,
      "type": "PhoneBookLookupProvider"
    },
    {
      "name": "ActiveDirectory",
      "enabled": true,
      "type": "ActiveDirectoryLookupProvider"
    },
    {
      "name": "SalesforceCRM",
      "enabled": true,
      "type": "ExternalCRMLookupProvider"
    }
  ]
}
```

### 3. Trigger Screen Pop

Manually trigger a screen pop notification.

**Request:**
```bash
POST /api/crm/screen-pop
Content-Type: application/json

{
  "phone_number": "555-1234",
  "call_id": "call-abc123",
  "extension": "1001"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Screen pop triggered"
}
```

## Webhook Integration

When a screen pop is triggered, a webhook event `crm.screen_pop` is sent to all subscribed endpoints.

### Webhook Payload Example

```json
{
  "event_id": "crm.screen_pop-1701964800123",
  "event_type": "crm.screen_pop",
  "timestamp": "2025-12-07T12:00:00.123456",
  "data": {
    "call_id": "call-abc123",
    "phone_number": "555-1234",
    "extension": "1001",
    "timestamp": "2025-12-07T12:00:00",
    "caller_info": {
      "name": "John Doe",
      "company": "Acme Corp",
      "email": "john@acme.com",
      "account_id": "ACC-12345",
      "contact_id": "CON-67890",
      "tags": ["vip", "sales"],
      "source": "phone_book"
    }
  }
}
```

### Configure Webhook Subscription

Add a webhook subscription in config.yml to receive screen pops:

```yaml
features:
  webhooks:
    enabled: true
    subscriptions:
      - url: "https://your-crm.com/webhooks/screen-pop"
        events: ["crm.screen_pop"]
        enabled: true
        secret: "your-webhook-secret"
```

## Creating Custom Lookup Providers

### Example: External API Provider

```python
from pbx.features.crm_integration import CRMLookupProvider, CallerInfo
import requests

class CustomCRMLookupProvider(CRMLookupProvider):
    """Custom CRM lookup provider"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.api_url = config.get('api_url')
        self.api_key = config.get('api_key')
        self.name = 'CustomCRM'
    
    def lookup(self, phone_number: str) -> Optional[CallerInfo]:
        """Look up caller in custom CRM"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'{self.api_url}/contacts/search',
                headers=headers,
                params={'phone': phone_number},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('found'):
                    caller_info = CallerInfo(phone_number)
                    caller_info.name = data['name']
                    caller_info.company = data['company']
                    caller_info.email = data['email']
                    caller_info.account_id = data['account_id']
                    caller_info.source = 'custom_crm'
                    return caller_info
        except Exception as e:
            self.logger.error(f"Custom CRM lookup error: {e}")
        
        return None
```

### Register Custom Provider

```python
# In your PBX initialization code
from custom_provider import CustomCRMLookupProvider

# Add to CRM integration
provider_config = {
    'enabled': True,
    'name': 'CustomCRM',
    'api_url': 'https://api.yourcrm.com',
    'api_key': 'your-api-key'
}
provider = CustomCRMLookupProvider(provider_config)
pbx_core.crm_integration.providers.append(provider)
```

## Use Cases

### 1. Sales Team Screen Pop

**Scenario**: Sales team receives call from customer

**Flow**:
1. Call comes in from 555-1234
2. CRM Integration looks up caller
3. Finds customer in Salesforce
4. Triggers screen pop webhook
5. CRM displays customer account and recent orders
6. Sales rep answers with full context

### 2. Support Ticket Creation

**Scenario**: Support call automatically creates ticket

**Flow**:
1. Call comes in from 555-5678
2. CRM Integration looks up caller
3. Finds customer in help desk system
4. Triggers screen pop webhook
5. Help desk creates ticket and displays customer history
6. Support rep answers with ticket number ready

### 3. VIP Caller Recognition

**Scenario**: Identify VIP callers for priority handling

**Flow**:
1. Call comes in from 555-9999
2. CRM Integration looks up caller
3. Finds VIP tag in phone book
4. Triggers screen pop with VIP indicator
5. Call is prioritized or routed to senior staff
6. VIP receives enhanced service

## Performance Optimization

### Caching Strategy

The CRM Integration includes a built-in cache to improve performance:

- **Cache Duration**: Configurable (default: 1 hour)
- **Cache Key**: Normalized phone number
- **Cache Invalidation**: Automatic expiration or manual clear

### Cache Management

```python
# Clear cache manually
pbx_core.crm_integration.clear_cache()

# Disable cache for fresh lookups
caller_info = pbx_core.crm_integration.lookup_caller(
    phone_number='555-1234',
    use_cache=False
)
```

## Phone Number Normalization

Phone numbers are automatically normalized for consistent lookups:

- **Input**: `+1 (555) 123-4567`
- **Normalized**: `15551234567`

Supported formats:
- `555-1234`
- `(555) 123-4567`
- `+1-555-123-4567`
- `555 123 4567`

## Integration Examples

### Salesforce Integration

```yaml
providers:
  - type: external_crm
    enabled: true
    name: Salesforce
    url: https://your-instance.salesforce.com/services/apexrest/pbx/lookup
    api_key: your-salesforce-api-key
    timeout: 5
```

### HubSpot Integration

```yaml
providers:
  - type: external_crm
    enabled: true
    name: HubSpot
    url: https://api.hubapi.com/contacts/v1/contact/phone
    api_key: your-hubspot-api-key
    timeout: 5
```

## Troubleshooting

### Lookup Returns No Results

**Check**:
- Phone number format matches database records
- All providers are enabled
- Provider credentials are correct
- Network connectivity to external APIs

### Slow Lookups

**Solutions**:
- Enable caching
- Reduce number of providers
- Increase provider timeout
- Optimize provider order (fastest first)

### Screen Pop Not Triggering

**Check**:
- Webhook system is enabled
- Webhook subscription for `crm.screen_pop` exists
- Webhook URL is accessible
- Check webhook logs for errors

## Testing

Run CRM integration tests:
```bash
python tests/test_crm_integration.py
```

All 9 tests should pass:
- CallerInfo creation and conversion
- PhoneBook lookup provider
- Active Directory lookup provider
- CRM integration initialization
- Multi-provider lookup
- Caching system
- Screen pop triggering
- Phone number normalization
- Provider status

---

**Implementation Date**: December 7, 2025  
**Status**: Production Ready ✅  
**Test Coverage**: 9/9 tests passing
