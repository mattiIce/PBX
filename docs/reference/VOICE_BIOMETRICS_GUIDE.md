# Voice Biometrics Guide

## Overview

The Voice Biometrics framework provides speaker authentication and fraud detection capabilities using voice analysis. This enables secure, passwordless authentication and real-time fraud prevention.

## Features

- **Speaker Enrollment** - Create voice profiles for users
- **Voice Authentication** - Verify caller identity using voice
- **Fraud Detection** - Detect voice spoofing and impersonation
- **Passive Enrollment** - Build profiles from multiple calls
- **Active Verification** - Challenge-response authentication
- **Liveness Detection** - Prevent replay attacks

## Use Cases

- **Passwordless Authentication** - Login using voice only
- **Account Security** - Additional authentication factor
- **Fraud Prevention** - Detect unauthorized callers
- **VIP Caller Verification** - Verify high-value customers
- **Compliance** - Meet authentication requirements

## Configuration

### config.yml
```yaml
features:
  voice_biometrics:
    enabled: true
    provider: nuance  # nuance, pindrop, aws, azure
    enrollment:
      min_duration: 30        # Minimum seconds of audio for enrollment
      quality_threshold: 0.8  # Minimum audio quality
      passive_enabled: true   # Allow passive enrollment
    verification:
      threshold: 0.85         # Match threshold (0.0-1.0)
      liveness_check: true    # Enable liveness detection
    fraud_detection:
      enabled: true
      score_threshold: 0.7    # Fraud score threshold
```

## External Service Integration

### Nuance Voice Biometrics

```python
from pbx.features.voice_biometrics import get_voice_biometrics

bio = get_voice_biometrics()

# Configure Nuance provider
bio.configure_provider('nuance', {
    'api_url': 'https://voicebiometrics.nuance.com',
    'api_key': 'your-nuance-api-key',
    'enrollment_mode': 'dynamic'  # or 'static'
})
```

### AWS Connect Voice ID

```python
# Configure AWS Voice ID
bio.configure_provider('aws', {
    'region': 'us-east-1',
    'access_key_id': 'your-access-key',
    'secret_access_key': 'your-secret-key',
    'domain_id': 'your-domain-id'
})
```

### Pindrop

```python
# Configure Pindrop
bio.configure_provider('pindrop', {
    'api_url': 'https://api.pindrop.com',
    'api_key': 'your-pindrop-key',
    'fraud_detection': True
})
```

## Usage

### Python API

```python
from pbx.features.voice_biometrics import get_voice_biometrics

bio = get_voice_biometrics()

# Enroll a user
result = bio.enroll_user(
    extension='1001',
    audio_samples=[
        '/path/to/sample1.wav',
        '/path/to/sample2.wav',
        '/path/to/sample3.wav'
    ]
)

# Verify caller
verification = bio.verify_caller(
    extension='1001',
    audio_sample='/path/to/call_audio.wav'
)

if verification['match'] and verification['score'] > 0.85:
    print("Caller verified!")
else:
    print("Verification failed")

# Check for fraud
fraud_check = bio.detect_fraud(
    audio_sample='/path/to/suspicious_call.wav'
)

if fraud_check['is_fraud']:
    print(f"Fraud detected! Score: {fraud_check['fraud_score']}")
```

### REST API Endpoints

#### Enroll User
```bash
POST /api/framework/voice-biometrics/enroll
{
  "extension": "1001",
  "audio_samples": ["base64-encoded-audio-1", "base64-encoded-audio-2"]
}
```

#### Verify Caller
```bash
POST /api/framework/voice-biometrics/verify
{
  "extension": "1001",
  "audio_sample": "base64-encoded-audio",
  "liveness_check": true
}

Response:
{
  "match": true,
  "score": 0.92,
  "confidence": "high",
  "liveness_passed": true
}
```

#### Detect Fraud
```bash
POST /api/framework/voice-biometrics/fraud-check
{
  "audio_sample": "base64-encoded-audio"
}

Response:
{
  "is_fraud": false,
  "fraud_score": 0.15,
  "indicators": [],
  "risk_level": "low"
}
```

#### Get Voiceprint Status
```bash
GET /api/framework/voice-biometrics/voiceprint/{extension}

Response:
{
  "extension": "1001",
  "enrolled": true,
  "sample_count": 5,
  "quality_score": 0.89,
  "created_at": "2025-01-15T10:30:00Z",
  "last_updated": "2025-01-20T14:15:00Z"
}
```

## Enrollment Process

### Active Enrollment

Active enrollment requires the user to speak specific phrases:

```python
# Configure enrollment phrases
bio.configure_enrollment_phrases([
    "My voice is my password",
    "Authentication is successful",
    "Welcome to the system"
])

# Start enrollment
session = bio.start_enrollment('1001')

# Add audio samples
for phrase_audio in collected_samples:
    bio.add_enrollment_sample(
        session_id=session['id'],
        audio=phrase_audio
    )

# Complete enrollment
result = bio.complete_enrollment(session['id'])
```

### Passive Enrollment

Passive enrollment builds a voiceprint from regular calls:

```python
# Enable passive enrollment
bio.enable_passive_enrollment(
    extension='1001',
    min_calls=5,      # Minimum calls needed
    min_duration=30   # Minimum seconds per call
)

# System automatically collects audio during calls
# No action needed from user
```

## Verification Methods

### Text-Dependent Verification

User must speak a specific phrase:

```python
verification = bio.verify_text_dependent(
    extension='1001',
    audio=audio_sample,
    expected_text="My voice is my password"
)
```

### Text-Independent Verification

User can speak freely:

```python
verification = bio.verify_text_independent(
    extension='1001',
    audio=audio_sample
)
```

### Continuous Verification

Verify throughout the call:

```python
# Start continuous verification
session = bio.start_continuous_verification(
    call_id='call-123',
    extension='1001'
)

# Stream audio chunks
for audio_chunk in call_audio_stream:
    result = bio.verify_audio_chunk(
        session_id=session['id'],
        audio_chunk=audio_chunk
    )
    
    if not result['match']:
        # Potential fraud or impersonation
        bio.flag_suspicious_activity(call_id='call-123')
```

## Fraud Detection

### Replay Attack Detection

```python
fraud = bio.detect_fraud(
    audio_sample=audio,
    checks=['replay', 'synthesis', 'impersonation']
)

if fraud['replay_detected']:
    print("Replay attack detected!")
```

### Voice Synthesis Detection

```python
# Detect synthetic/deepfake voice
synthesis_check = bio.check_voice_synthesis(audio_sample)

if synthesis_check['is_synthetic']:
    print(f"Synthetic voice detected: {synthesis_check['confidence']}")
```

### Impersonation Detection

```python
# Compare against known fraud profiles
impersonation = bio.check_impersonation(
    audio_sample=audio,
    extension='1001'
)
```

## Admin Panel

Access Voice Biometrics in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **Voice Biometrics**
2. View enrolled users and voiceprint quality
3. Manage enrollment settings
4. Review verification history
5. Monitor fraud detection alerts
6. Test voice verification

## Integration with Call Flow

### IVR Authentication

```python
# In auto attendant or IVR
def handle_voice_authentication(call):
    # Prompt for voice authentication
    play_prompt("Please say your name for verification")
    
    # Record audio
    audio = record_audio(duration=5)
    
    # Verify
    result = bio.verify_caller(
        extension=call.extension,
        audio_sample=audio
    )
    
    if result['match']:
        # Grant access
        route_to_secure_menu(call)
    else:
        # Authentication failed
        route_to_fallback(call)
```

### Automatic Fraud Check

```python
# Check all calls automatically
def on_call_start(call):
    if bio.is_enabled():
        # Start fraud detection
        fraud_session = bio.start_fraud_monitoring(
            call_id=call.call_id
        )
        
        # Monitor throughout call
        call.add_callback('audio_chunk', lambda chunk:
            bio.process_fraud_check(fraud_session, chunk)
        )
```

## Best Practices

### Enrollment
- **Multiple Samples:** Collect 3-5 audio samples for robust profiles
- **Quality Check:** Ensure clean audio with minimal background noise
- **Regular Updates:** Update voiceprints periodically (every 6-12 months)
- **Consent:** Get explicit user consent for biometric collection

### Verification
- **Threshold Tuning:** Adjust match threshold based on security needs
- **Fallback Authentication:** Provide alternative auth if voice fails
- **User Experience:** Make verification quick and seamless
- **Error Handling:** Gracefully handle poor audio quality

### Security
- **Encrypt Voiceprints:** Store voiceprints encrypted at rest
- **Access Control:** Restrict access to biometric data
- **Audit Logging:** Log all verification attempts
- **Compliance:** Follow biometric privacy regulations (BIPA, GDPR)

### Performance
- **Audio Quality:** Use high-quality audio (16kHz+ sampling)
- **Processing Time:** Optimize for < 2 second verification
- **Caching:** Cache voiceprints in memory
- **Batch Processing:** Process multiple verifications in parallel

## Database Schema

### voiceprints
```sql
CREATE TABLE voiceprints (
    id SERIAL PRIMARY KEY,
    extension VARCHAR(10) NOT NULL UNIQUE,
    voiceprint_data BYTEA NOT NULL,  -- Encrypted
    enrollment_method VARCHAR(20),    -- active, passive
    sample_count INTEGER DEFAULT 0,
    quality_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### verification_history
```sql
CREATE TABLE verification_history (
    id SERIAL PRIMARY KEY,
    extension VARCHAR(10) NOT NULL,
    call_id VARCHAR(100),
    match BOOLEAN NOT NULL,
    score FLOAT NOT NULL,
    method VARCHAR(50),
    liveness_passed BOOLEAN,
    verified_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_extension (extension),
    INDEX idx_call_id (call_id)
);
```

### fraud_detections
```sql
CREATE TABLE fraud_detections (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(100) NOT NULL,
    fraud_score FLOAT NOT NULL,
    indicators TEXT[],
    risk_level VARCHAR(20),
    action_taken VARCHAR(50),
    detected_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_call_id (call_id),
    INDEX idx_detected_at (detected_at)
);
```

## Troubleshooting

### Low Verification Scores
**Solution:**
- Check audio quality (sample rate, noise)
- Re-enroll with better audio samples
- Adjust verification threshold
- Use text-dependent verification

### Enrollment Fails
**Solution:**
- Ensure minimum audio duration met
- Check for background noise
- Verify audio format is correct
- Try multiple enrollment attempts

### False Fraud Alerts
**Solution:**
- Tune fraud score threshold higher
- Review fraud indicators
- Update fraud detection models
- Whitelist known variations

## Compliance Considerations

### BIPA (Illinois Biometric Information Privacy Act)
- Obtain written consent before collecting
- Provide retention and destruction policies
- Secure storage requirements

### GDPR (European Union)
- Biometric data is special category data
- Explicit consent required
- Right to erasure applies
- Data minimization principles

### CCPA (California Consumer Privacy Act)
- Disclose biometric data collection
- Provide opt-out mechanisms
- Secure storage requirements

## Next Steps

1. **Choose Provider:** Select voice biometrics service
2. **Configure Integration:** Set up API credentials
3. **Plan Enrollment:** Decide on active vs passive
4. **Set Thresholds:** Configure match and fraud thresholds
5. **Test Thoroughly:** Validate with diverse voice samples
6. **Deploy Gradually:** Start with pilot group
7. **Monitor Performance:** Track success rates and adjust

## See Also

- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md)
- [COMPLETE_GUIDE.md](../../COMPLETE_GUIDE.md) - Comprehensive documentation
