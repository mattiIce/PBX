# Voicemail Transcription Guide

**Last Updated**: December 7, 2025  
**Feature Status**: ✅ Production-Ready

---

## Overview

The voicemail transcription feature automatically converts voicemail messages to text using speech-to-text APIs. Transcriptions are stored in the database and can be included in email notifications, making it easier to quickly review voicemail messages without listening to the audio.

### Key Features

- **Automatic Transcription**: Voicemails are automatically transcribed when saved
- **Multiple Providers**: Support for OpenAI Whisper and Google Cloud Speech-to-Text
- **Database Storage**: Transcriptions stored with confidence scores and metadata
- **Email Integration**: Transcriptions can be included in voicemail-to-email notifications
- **Language Support**: Configurable language for transcription
- **High Accuracy**: Modern speech-to-text engines provide excellent accuracy

---

## Supported Providers

### OpenAI Whisper API

- **Model**: `whisper-1`
- **Accuracy**: Excellent for various accents and background noise
- **Cost**: Pay-per-use (check OpenAI pricing)
- **Setup**: Requires OpenAI API key
- **Library**: `openai` Python package

### Google Cloud Speech-to-Text

- **Model**: Optimized for phone call audio
- **Accuracy**: Very high with confidence scores
- **Cost**: Pay-per-use (check Google Cloud pricing)
- **Setup**: Requires Google Cloud credentials
- **Library**: `google-cloud-speech` Python package

---

## Installation

### 1. Install Dependencies

Choose one of the following based on your preferred provider:

#### For OpenAI Whisper:
```bash
pip install openai
```

#### For Google Cloud Speech-to-Text:
```bash
pip install google-cloud-speech
```

### 2. Configure Credentials

#### OpenAI Setup:
1. Sign up at [OpenAI](https://openai.com/)
2. Generate an API key from your account dashboard
3. Add the API key to your environment:
```bash
export TRANSCRIPTION_API_KEY="your-openai-api-key"
```

#### Google Cloud Setup:
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Speech-to-Text API
3. Create a service account and download the JSON key file
4. Set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 3. Enable in Configuration

Edit `config.yml`:

```yaml
features:
  voicemail_transcription:
    enabled: true
    provider: openai  # or 'google'
    api_key: ${TRANSCRIPTION_API_KEY}  # Only needed for OpenAI
```

---

## Configuration Reference

### Basic Configuration

```yaml
features:
  voicemail_transcription:
    enabled: true              # Enable/disable transcription
    provider: openai           # Provider: 'openai' or 'google'
    api_key: ${TRANSCRIPTION_API_KEY}  # API key (OpenAI only)
```

### Configuration Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `enabled` | boolean | No | `false` | Enable voicemail transcription |
| `provider` | string | Yes* | `openai` | Transcription provider (`openai` or `google`) |
| `api_key` | string | Yes** | None | API key for transcription service (OpenAI only) |

\* Required if enabled is true  
\** Required for OpenAI provider

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `TRANSCRIPTION_API_KEY` | OpenAI API key | `sk-...` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Google Cloud service account key | `/path/to/key.json` |

---

## Database Schema

Transcription data is stored in the `voicemail_messages` table:

```sql
CREATE TABLE voicemail_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    caller_id VARCHAR(50),
    file_path VARCHAR(255),
    duration INTEGER,
    listened BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Transcription fields
    transcription_text TEXT,
    transcription_confidence FLOAT,
    transcription_language VARCHAR(10),
    transcription_provider VARCHAR(20),
    transcribed_at TIMESTAMP
);
```

### Schema Migration

The database schema will automatically migrate to add transcription columns when the PBX starts. No manual intervention is required.

---

## Usage

### Automatic Transcription

When a voicemail is saved, it will automatically be transcribed if the service is enabled:

```python
# In your PBX code
voicemail_box = VoicemailBox(
    extension_number='1001',
    config=config,
    database=database,
    transcription_service=transcription_service  # Pass the service
)

# Save voicemail - automatic transcription happens here
message_id = voicemail_box.save_message(
    caller_id='5551234567',
    audio_data=audio_bytes,
    duration=30
)
```

### Retrieve Transcriptions

Transcriptions are included in message data:

```python
messages = voicemail_box.get_messages()

for message in messages:
    print(f"Caller: {message['caller_id']}")
    print(f"Duration: {message['duration']}s")
    
    if 'transcription' in message:
        print(f"Transcription: {message['transcription']}")
        print(f"Confidence: {message['transcription_confidence']:.2%}")
        print(f"Language: {message['transcription_language']}")
        print(f"Provider: {message['transcription_provider']}")
```

### API Access

Transcriptions are available via the REST API:

```bash
# Get voicemail messages with transcriptions
curl http://pbx:8080/api/voicemail/1001/messages
```

Response:
```json
{
  "messages": [
    {
      "id": "5551234567_20251207_143022",
      "caller_id": "5551234567",
      "timestamp": "2025-12-07T14:30:22",
      "duration": 30,
      "listened": false,
      "transcription": "Hi, this is John calling about the order. Please call me back at 555-123-4567.",
      "transcription_confidence": 0.95,
      "transcription_language": "en-US",
      "transcription_provider": "openai",
      "transcribed_at": "2025-12-07T14:30:25"
    }
  ]
}
```

---

## Email Notifications

Transcriptions can be included in voicemail-to-email notifications. Update your email notifier to support the `transcription` parameter.

Example email template:

```
Subject: New Voicemail from {caller_id}

You have received a new voicemail:

Caller: {caller_id}
Duration: {duration} seconds
Time: {timestamp}

Transcription:
{transcription}
(Confidence: {confidence}%)

The voicemail audio is attached.
```

---

## Performance Considerations

### Transcription Time

- **OpenAI Whisper**: ~2-5 seconds per 30-second voicemail
- **Google Speech**: ~1-3 seconds per 30-second voicemail
- Transcription happens asynchronously after voicemail is saved
- Does not block voicemail saving or caller

### Cost Considerations

#### OpenAI Whisper Pricing (as of Dec 2025)
- $0.006 per minute of audio
- Example: 100 voicemails/day × 30 seconds avg = $0.30/day or ~$9/month

#### Google Cloud Speech-to-Text Pricing (as of Dec 2025)
- Standard model: $0.006 per 15 seconds
- Phone call model: $0.009 per 15 seconds
- Example: 100 voicemails/day × 30 seconds avg = $0.36/day or ~$11/month

### Best Practices

1. **Monitor API Usage**: Set up billing alerts in your provider dashboard
2. **Error Handling**: Transcription failures don't affect voicemail saving
3. **Rate Limiting**: Both providers have rate limits; monitor usage
4. **Storage**: Transcriptions are stored as text (minimal database impact)

---

## Troubleshooting

### Transcription Not Working

**Symptom**: Voicemails saved but no transcription

**Possible Causes**:
1. Service not enabled in config
2. API key not configured
3. API library not installed
4. Network issues

**Solutions**:
```bash
# Check config
grep -A 5 "voicemail_transcription:" config.yml

# Check environment variables
echo $TRANSCRIPTION_API_KEY

# Check library installation
python -c "import openai" 2>/dev/null && echo "OpenAI installed" || echo "OpenAI not installed"
python -c "from google.cloud import speech" 2>/dev/null && echo "Google installed" || echo "Google not installed"

# Check logs
tail -f logs/pbx.log | grep -i transcription
```

### Low Confidence Scores

**Symptom**: Transcriptions have low confidence scores (< 0.7)

**Possible Causes**:
1. Poor audio quality
2. Background noise
3. Strong accents
4. Wrong language setting

**Solutions**:
- Use Google's phone call model (optimized for phone audio)
- Specify correct language in configuration
- Improve audio quality (better phones, network)
- Consider OpenAI Whisper for better accent handling

### API Errors

**Symptom**: Transcription fails with API errors

**Common Errors**:

#### OpenAI:
- `API rate limit exceeded`: Upgrade OpenAI plan or reduce usage
- `Invalid API key`: Check API key configuration
- `Insufficient credits`: Add credits to OpenAI account

#### Google:
- `Quota exceeded`: Increase quota in Google Cloud Console
- `Authentication failed`: Check GOOGLE_APPLICATION_CREDENTIALS
- `API not enabled`: Enable Speech-to-Text API in console

---

## Advanced Configuration

### Custom Language

Configure transcription language:

```yaml
features:
  voicemail_transcription:
    enabled: true
    provider: openai
    api_key: ${TRANSCRIPTION_API_KEY}
    language: es-ES  # Spanish (Spain)
```

Supported languages vary by provider. Common options:
- `en-US`: English (United States)
- `en-GB`: English (United Kingdom)
- `es-ES`: Spanish (Spain)
- `es-MX`: Spanish (Mexico)
- `fr-FR`: French (France)
- `de-DE`: German (Germany)

### Provider-Specific Options

#### OpenAI Whisper

```python
# In voicemail_transcription.py, customize:
response = openai.Audio.transcribe(
    model="whisper-1",
    file=audio_file,
    language=lang_code,
    # Optional parameters:
    # temperature=0,  # Lower = more consistent
    # prompt="..."    # Context for better accuracy
)
```

#### Google Cloud Speech

```python
# In voicemail_transcription.py, customize:
config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=8000,
    language_code=language,
    enable_automatic_punctuation=True,
    model='phone_call',
    # Optional parameters:
    # use_enhanced=True,  # Better accuracy (higher cost)
    # enable_word_time_offsets=True,  # Word-level timing
    # profanity_filter=True,  # Filter profanity
)
```

---

## Testing

### Manual Testing

1. Leave a test voicemail
2. Check database for transcription:
```sql
SELECT message_id, transcription_text, transcription_confidence
FROM voicemail_messages
WHERE extension_number = '1001'
ORDER BY created_at DESC
LIMIT 1;
```

3. Verify transcription quality

### Automated Testing

Run the test suite:

```bash
python -m unittest tests.test_voicemail_transcription -v
```

Tests cover:
- Service initialization
- OpenAI transcription
- Google transcription
- Error handling
- Database integration

---

## Security Considerations

### API Key Security

- **Never commit API keys to version control**
- Use environment variables for secrets
- Rotate API keys regularly
- Restrict API key permissions to minimum required

### Data Privacy

- Transcriptions may contain sensitive information
- Ensure compliance with privacy regulations (GDPR, HIPAA, etc.)
- Configure data retention policies
- Consider encryption at rest for transcriptions

### Audio Data Transmission

- Both OpenAI and Google process audio on their servers
- Audio is transmitted over HTTPS
- Audio is not stored by providers (per their policies)
- For highly sensitive environments, consider on-premise solutions

---

## Monitoring

### Key Metrics to Track

1. **Transcription Success Rate**: Percentage of successfully transcribed voicemails
2. **Average Confidence Score**: Overall transcription quality
3. **API Response Time**: Latency for transcription requests
4. **API Error Rate**: Failed transcription attempts
5. **Cost Per Transcription**: Track API usage costs

### Logging

Transcription events are logged:

```
2025-12-07 14:30:22 - PBX - INFO - Transcribing voicemail 5551234567_20251207_143022...
2025-12-07 14:30:22 - PBX - INFO -   Provider: openai
2025-12-07 14:30:22 - PBX - INFO -   Language: en-US
2025-12-07 14:30:25 - PBX - INFO - ✓ Voicemail transcribed successfully
2025-12-07 14:30:25 - PBX - INFO -   Confidence: 95.00%
```

---

## Migration from Non-Transcription System

If you're enabling transcription on an existing system:

1. **Existing Voicemails**: Not automatically transcribed
2. **New Voicemails**: Automatically transcribed
3. **Database**: Schema migrates automatically on startup
4. **Backward Compatible**: System works with or without transcriptions

To transcribe existing voicemails:

```python
from pbx.features.voicemail_transcription import VoicemailTranscriptionService

# Initialize service
config = Config('config.yml')
service = VoicemailTranscriptionService(config)

# Transcribe existing voicemail
result = service.transcribe('/path/to/voicemail.wav')

if result['success']:
    # Update database
    database.execute("""
        UPDATE voicemail_messages
        SET transcription_text = %s,
            transcription_confidence = %s,
            transcription_language = %s,
            transcription_provider = %s,
            transcribed_at = %s
        WHERE message_id = %s
    """, (
        result['text'],
        result['confidence'],
        result['language'],
        result['provider'],
        result['timestamp'],
        message_id
    ))
```

---

## Support and Resources

### Official Documentation

- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text/docs)

### Troubleshooting Resources

- Check PBX logs: `logs/pbx.log`
- Database queries: See [DATABASE_MIGRATION_GUIDE.md](DATABASE_MIGRATION_GUIDE.md)
- Email setup: See [VOICEMAIL_EMAIL_GUIDE.md](VOICEMAIL_EMAIL_GUIDE.md)

### Contact

For issues or questions:
- Review logs for error messages
- Check configuration settings
- Verify API credentials
- Test with sample voicemail files

---

## FAQ

**Q: Can I use both OpenAI and Google for different extensions?**  
A: Not currently. The provider is system-wide. You can change the provider in configuration and restart the PBX.

**Q: What happens if transcription fails?**  
A: The voicemail is still saved normally. The transcription field remains NULL in the database, and email notifications still work.

**Q: Can I transcribe voicemails in multiple languages?**  
A: Yes, but the language setting is system-wide. OpenAI Whisper auto-detects language. Google requires explicit language configuration.

**Q: How accurate are the transcriptions?**  
A: Both providers offer 90-95% accuracy for clear audio. Accuracy depends on audio quality, accent, background noise, and language.

**Q: Can I use local/on-premise speech-to-text?**  
A: Not currently, but you can extend the `VoicemailTranscriptionService` class to add custom providers.

**Q: Does transcription affect call quality or performance?**  
A: No. Transcription happens asynchronously after the call ends and doesn't affect real-time call processing.

---

**Document Version**: 1.0  
**Last Updated**: December 7, 2025  
**Status**: ✅ Production-Ready
