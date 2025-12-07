# Webhook System Guide

## Overview

The Webhook System provides event-driven integrations by sending HTTP POST notifications to external systems when PBX events occur. This enables real-time integration with CRM systems, monitoring tools, analytics platforms, and custom applications.

**Status**: ✅ **Production Ready**

## Features

- **15+ Event Types** - Call events, voicemail, extensions, queues, paging, conferences
- **Flexible Subscriptions** - Subscribe to specific events or all events (wildcard)
- **Asynchronous Delivery** - Non-blocking webhook delivery with worker threads
- **Retry Logic** - Automatic retry with configurable attempts and delay
- **Multiple Subscriptions** - Support for multiple webhook endpoints
- **Custom Headers** - Add custom HTTP headers to webhook requests
- **Event Filtering** - Subscribe only to events you need
- **Status Tracking** - Monitor delivery success/failure rates
- **REST API Management** - Full API for subscription management

## Supported Event Types

### Call Events
- `call.started` - Call initiated
- `call.answered` - Call answered
- `call.ended` - Call terminated
- `call.hold` - Call put on hold
- `call.resume` - Call resumed from hold
- `call.transfer` - Call transferred
- `call.parked` - Call parked
- `call.retrieved` - Call retrieved from parking

### Voicemail Events
- `voicemail.new` - New voicemail received
- `voicemail.read` - Voicemail message read
- `voicemail.deleted` - Voicemail message deleted

### Extension Events
- `extension.registered` - Extension registered
- `extension.unregistered` - Extension unregistered

### Queue Events
- `queue.call_added` - Call added to queue
- `queue.call_answered` - Call answered from queue
- `queue.call_abandoned` - Call abandoned in queue

### Paging Events
- `paging.started` - Paging session started
- `paging.ended` - Paging session ended

### Conference Events
- `conference.started` - Conference started
- `conference.participant_joined` - Participant joined
- `conference.participant_left` - Participant left
- `conference.ended` - Conference ended

## Configuration

Add webhook configuration to your `config.yml`:

```yaml
features:
  webhooks:
    enabled: true
    max_retries: 3          # Number of retry attempts
    retry_delay: 5          # Seconds between retries
    timeout: 10             # HTTP request timeout in seconds
    worker_threads: 2       # Number of delivery worker threads
    
    # Webhook subscriptions
    subscriptions:
      - url: "https://your-server.com/webhooks/pbx"
        events: ["*"]       # All events (wildcard)
        enabled: true
        secret: "your-webhook-secret"  # Optional
        headers:            # Optional custom headers
          Authorization: "Bearer your-token"
      
      - url: "https://crm.company.com/api/call-events"
        events:
          - "call.started"
          - "call.ended"
        enabled: true
      
      - url: "https://analytics.company.com/webhooks"
        events:
          - "voicemail.new"
          - "queue.call_answered"
        enabled: true
```

## REST API Endpoints

### Get All Webhook Subscriptions

```bash
curl http://localhost:8080/api/webhooks
```

**Response:**
```json
[
  {
    "url": "https://your-server.com/webhooks/pbx",
    "events": ["*"],
    "enabled": true,
    "created_at": "2025-12-07T12:00:00",
    "last_sent": "2025-12-07T12:30:00",
    "success_count": 150,
    "failure_count": 2
  }
]
```

### Add Webhook Subscription

```bash
curl -X POST http://localhost:8080/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhooks",
    "events": ["call.started", "call.ended"],
    "secret": "your-secret-key",
    "headers": {
      "Authorization": "Bearer token123"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Webhook subscription added: https://your-server.com/webhooks",
  "subscription": {
    "url": "https://your-server.com/webhooks",
    "events": ["call.started", "call.ended"],
    "enabled": true
  }
}
```

### Delete Webhook Subscription

```bash
curl -X DELETE "http://localhost:8080/api/webhooks?url=https://your-server.com/webhooks"
```

## Webhook Payload Format

All webhooks are sent as HTTP POST with JSON payload:

```json
{
  "event_id": "call.started-1701964800000",
  "event_type": "call.started",
  "timestamp": "2025-12-07T12:00:00.000000",
  "data": {
    "call_id": "abc123def456",
    "from_extension": "1001",
    "to_extension": "1002",
    "timestamp": "2025-12-07T12:00:00"
  }
}
```

### HTTP Headers

```
Content-Type: application/json
User-Agent: PBX-Webhook/1.0
X-Webhook-Event: call.started
X-Webhook-ID: call.started-1701964800000
[Any custom headers from subscription]
```

### Future: HMAC Signature (Planned)

```
X-Webhook-Signature: sha256=abc123...
```

## Event Examples

### Call Started Event

```json
{
  "event_id": "call.started-1701964800123",
  "event_type": "call.started",
  "timestamp": "2025-12-07T12:00:00.123456",
  "data": {
    "call_id": "call-abc123",
    "from_extension": "1001",
    "to_extension": "1002",
    "timestamp": "2025-12-07T12:00:00"
  }
}
```

### Extension Registered Event

```json
{
  "event_id": "extension.registered-1701964800456",
  "event_type": "extension.registered",
  "timestamp": "2025-12-07T12:00:00.456789",
  "data": {
    "extension": "1001",
    "ip_address": "192.168.1.100",
    "port": 5060,
    "user_agent": "Yealink SIP-T46S 66.85.0.5",
    "timestamp": "2025-12-07T12:00:00"
  }
}
```

### Voicemail New Event

```json
{
  "event_id": "voicemail.new-1701964800789",
  "event_type": "voicemail.new",
  "timestamp": "2025-12-07T12:00:00.789012",
  "data": {
    "extension": "1001",
    "caller_id": "1002",
    "duration": 45,
    "file_path": "/voicemail/1001/msg_001.wav",
    "timestamp": "2025-12-07T12:00:00"
  }
}
```

## Implementation Example (Receiver)

### Python Flask Example

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

@app.route('/webhooks/pbx', methods=['POST'])
def handle_pbx_webhook():
    # Get webhook data
    webhook_data = request.get_json()
    
    # Optional: Verify HMAC signature
    # signature = request.headers.get('X-Webhook-Signature')
    # if not verify_signature(request.data, signature):
    #     return jsonify({'error': 'Invalid signature'}), 401
    
    event_type = webhook_data['event_type']
    event_data = webhook_data['data']
    
    # Handle different event types
    if event_type == 'call.started':
        handle_call_started(event_data)
    elif event_type == 'voicemail.new':
        handle_new_voicemail(event_data)
    # ... handle other events
    
    return jsonify({'success': True}), 200

def handle_call_started(data):
    # Your custom logic here
    print(f"Call started: {data['from_extension']} -> {data['to_extension']}")
    # e.g., Update CRM, send notification, log to analytics

def handle_new_voicemail(data):
    # Your custom logic here
    print(f"New voicemail for {data['extension']} from {data['caller_id']}")
    # e.g., Send email, create ticket, update dashboard

if __name__ == '__main__':
    app.run(port=5000)
```

### Node.js Express Example

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhooks/pbx', (req, res) => {
  const { event_type, data } = req.body;
  
  switch(event_type) {
    case 'call.started':
      handleCallStarted(data);
      break;
    case 'voicemail.new':
      handleNewVoicemail(data);
      break;
    // ... handle other events
  }
  
  res.json({ success: true });
});

function handleCallStarted(data) {
  console.log(`Call started: ${data.from_extension} -> ${data.to_extension}`);
  // Your custom logic
}

function handleNewVoicemail(data) {
  console.log(`New voicemail for ${data.extension}`);
  // Your custom logic
}

app.listen(5000, () => console.log('Webhook receiver listening on port 5000'));
```

## Use Cases

### CRM Integration
- **Screen Pop**: Automatically display customer info when they call
- **Call Logging**: Log all calls to CRM with duration and outcome
- **Lead Scoring**: Track call engagement for lead scoring

### Analytics & Monitoring
- **Real-Time Dashboards**: Update dashboards with live call metrics
- **Call Volume Tracking**: Monitor call patterns and peak times
- **Queue Performance**: Track queue wait times and abandonment rates

### Alerting & Notifications
- **After-Hours Alerts**: Notify on-call staff of after-hours calls
- **VIP Caller Alerts**: Special handling for important callers
- **System Monitoring**: Alert on unusual patterns or issues

### Workflow Automation
- **Ticket Creation**: Auto-create support tickets from calls
- **Email Notifications**: Send custom email notifications
- **Multi-System Sync**: Keep multiple systems in sync

### Business Intelligence
- **Data Warehousing**: Send events to data warehouse
- **Reporting**: Generate custom reports and analytics
- **Compliance**: Log events for regulatory compliance

## Best Practices

### Security
1. **Use HTTPS** - Always use HTTPS for webhook URLs
2. **Verify Signatures** - Implement HMAC signature verification (when available)
3. **IP Whitelisting** - Restrict webhook sources by IP
4. **Authentication** - Use custom headers for authentication

### Reliability
1. **Idempotency** - Handle duplicate events gracefully using `event_id`
2. **Error Handling** - Return 2xx status codes for successful processing
3. **Retry Logic** - Implement exponential backoff for failed processing
4. **Timeouts** - Process webhooks quickly (< 5 seconds)

### Performance
1. **Async Processing** - Process webhooks asynchronously
2. **Queue** - Use message queue for reliable processing
3. **Batching** - Consider batching for high-volume scenarios
4. **Monitoring** - Monitor delivery success rates

### Testing
1. **Mock Endpoint** - Test with a mock webhook receiver
2. **Validation** - Validate payload structure
3. **Load Testing** - Test with high event volumes
4. **Error Scenarios** - Test retry logic and error handling

## Monitoring & Troubleshooting

### Check Subscription Status

```bash
curl http://localhost:8080/api/webhooks
```

Look for:
- `success_count` - Number of successful deliveries
- `failure_count` - Number of failed deliveries
- `last_sent` - Timestamp of last successful delivery
- `enabled` - Whether subscription is active

### Common Issues

**Webhooks not being delivered:**
- Check that webhook system is enabled in config.yml
- Verify URL is accessible from PBX server
- Check firewall rules
- Review PBX logs for errors

**High failure rate:**
- Check receiver endpoint is responding with 2xx status
- Verify timeout settings are appropriate
- Check receiver logs for errors
- Test endpoint manually with curl

**Duplicate events:**
- Use `event_id` for deduplication
- Check if PBX was restarted (may resend pending events)

### Logs

Webhook activity is logged in the main PBX log:

```
2025-12-07 12:00:00 - PBX - INFO - Webhook delivered: call.started -> https://your-server.com/webhook (status: 200)
2025-12-07 12:00:05 - PBX - WARNING - Webhook delivery failed (attempt 1/3): call.started -> https://your-server.com/webhook - Connection timeout
```

## Future Enhancements

- [ ] HMAC signature verification for security
- [ ] Batch delivery mode for high-volume scenarios
- [ ] Event replay functionality
- [ ] Webhook delivery dashboard in admin panel
- [ ] Filtering by extension or other criteria
- [ ] Custom retry policies per subscription
- [ ] Dead letter queue for failed deliveries
- [ ] Webhook templates for common integrations

## Related Documentation

- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Complete API reference
- [ENTERPRISE_INTEGRATIONS.md](ENTERPRISE_INTEGRATIONS.md) - Integration guides
- [TODO.md](TODO.md) - Planned webhook enhancements

## Support

For questions or issues with the webhook system:
1. Check logs for error messages
2. Test endpoint manually with curl
3. Review this guide for configuration examples
4. Open a GitHub issue with details

---

**Last Updated**: December 7, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
