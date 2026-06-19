# Voice Biometrics Guide

## Overview

The Voice Biometrics framework provides speaker authentication and fraud detection using local voice analysis. It is a self-contained, open-source implementation: audio features are extracted with `pyAudioAnalysis`/`librosa` and speakers are modeled with a scikit-learn Gaussian Mixture Model (GMM), with a pure-Python fallback when those optional libraries are not installed. It does not depend on any commercial voice-biometrics provider.

## Features

- **Speaker Enrollment** - Create voice profiles from multiple audio samples
- **Voice Verification** - Verify a claimed identity from a voice sample
- **Fraud Detection** - Heuristic detection of replay, synthetic-voice, manipulation, and identity-mismatch indicators

## Use Cases

- **Passwordless Authentication** - Verify a caller using voice
- **Account Security** - Additional authentication factor
- **Fraud Prevention** - Flag suspicious or mismatched callers
- **VIP Caller Verification** - Verify high-value customers
- **Compliance** - Meet authentication requirements

## Optional Dependencies

Voice biometrics works without extra packages (basic energy/ZCR/pitch features), but accuracy improves with the optional libraries:

```bash
# FREE open-source speaker recognition features
pip install pyAudioAnalysis
# System packages: sudo apt-get install python3-tk portaudio19-dev

# Advanced audio analysis (MFCCs, spectral features)
pip install librosa soundfile

# GMM-based speaker modeling
pip install scikit-learn numpy
```

## Configuration

### config.yml

```yaml
features:
  voice_biometrics:
    enabled: true
    provider: nuance          # Stored label only; no provider integration
    threshold: 0.85           # Verification match threshold (0.0-1.0)
    enrollment_samples: 3     # Number of samples required to complete enrollment
    fraud_detection: true     # Enable heuristic fraud detection
```

> Note: `provider` is a free-text label that is logged and returned in statistics. There is no provider-specific integration code behind it.

## Usage

### Python API

```python
from pbx.features.voice_biometrics import get_voice_biometrics

bio = get_voice_biometrics()

# 1. Create a profile
profile = bio.create_profile(user_id="alice", extension="1001")

# 2. Start enrollment
session = bio.start_enrollment("alice")

# 3. Add enrollment samples (raw audio bytes; 16kHz 16-bit PCM recommended)
for sample_bytes in collected_samples:
    progress = bio.add_enrollment_sample("alice", sample_bytes)
    if progress["enrollment_complete"]:
        break

# 4. Verify a speaker
result = bio.verify_speaker("alice", audio_data=verification_bytes)
if result["verified"]:
    print(f"Caller verified (confidence: {result['confidence']:.2f})")
else:
    print("Verification failed")

# 5. Fraud detection
fraud = bio.detect_fraud(
    audio_data=audio_bytes,
    caller_info={"user_id": "alice", "call_id": "call-123", "caller_id": "5551234567"},
)
if fraud["fraud_detected"]:
    print(f"Fraud detected! Risk score: {fraud['risk_score']:.2f}")
    print(f"Indicators: {fraud['indicators']}")

# Look up a profile
profile = bio.get_profile("alice")
```

### REST API Endpoints

All endpoints are under the `/api/framework` prefix and require authentication.

#### Create Profile

```bash
POST /api/framework/voice-biometrics/profile
{
  "user_id": "alice",
  "extension": "1001"
}

Response:
{
  "success": true,
  "user_id": "alice",
  "extension": "1001",
  "status": "BiometricStatus.NOT_ENROLLED"
}
```

#### Start Enrollment

```bash
POST /api/framework/voice-biometrics/enroll
{
  "user_id": "alice"
}

Response:
{
  "success": true,
  "user_id": "alice",
  "required_samples": 3,
  "session_id": "a1b2c3d4e5f6g7h8"
}
```

> Audio samples are added server-side via the Python API (`add_enrollment_sample`); the enroll endpoint only starts the session.

#### Verify Speaker

```bash
POST /api/framework/voice-biometrics/verify
{
  "user_id": "alice",
  "audio_data": "base64-encoded-audio"
}

Response:
{
  "verified": true,
  "confidence": 0.92,
  "user_id": "alice",
  "timestamp": "2025-01-15T10:30:00+00:00"
}
```

#### Get Profile

```bash
GET /api/framework/voice-biometrics/profile/{user_id}

Response:
{
  "user_id": "alice",
  "extension": "1001",
  "status": "BiometricStatus.ENROLLED",
  "enrollment_completed": true,
  "created_at": "2025-01-15T10:30:00+00:00",
  "verification_count": 12,
  "fraud_attempts": 1
}
```

#### List Profiles

```bash
GET /api/framework/voice-biometrics/profiles
```

#### Statistics

```bash
GET /api/framework/voice-biometrics/statistics
```

#### Delete Profile

```bash
DELETE /api/framework/voice-biometrics/profile/{user_id}
```

## Enrollment Process

Enrollment collects several audio samples, extracts voice features from each, and (when scikit-learn is available and enough samples are present) trains a per-user GMM. Once `enrollment_samples` samples have been added, the profile status becomes `ENROLLED`.

```python
bio = get_voice_biometrics()
bio.create_profile("alice", "1001")
session = bio.start_enrollment("alice")

for sample_bytes in collected_samples:
    progress = bio.add_enrollment_sample("alice", sample_bytes)
    print(f"{progress['samples_collected']}/{progress['samples_required']}")
    if progress["enrollment_complete"]:
        print("Enrollment complete")
        break
```

## Verification

`verify_speaker(user_id, audio_data)` extracts features from the supplied audio and scores them against the enrolled profile. It uses the GMM log-likelihood when a model is available, otherwise a feature-distance similarity. The caller is considered verified when the confidence is greater than or equal to the configured `threshold`.

```python
result = bio.verify_speaker("alice", audio_data=audio_bytes)
# {"verified": bool, "confidence": float, "user_id": str, "timestamp": str}
```

## Fraud Detection

`detect_fraud(audio_data, caller_info)` returns a risk score (0.0-1.0) and a list of indicator strings. Fraud is flagged when the risk score exceeds 0.7. The heuristics check for:

- **Replay-style artifacts** - low energy variance, high spectral flatness
- **Synthetic patterns** - repetitive audio chunks
- **Voice manipulation** - abnormal pitch or zero-crossing rate
- **Identity mismatch** - voice does not match the claimed profile
- **Known/suspended profiles** - match against suspended profiles or stored fraud voiceprints (when scikit-learn and a database backend are available)

```python
fraud = bio.detect_fraud(
    audio_data=audio_bytes,
    caller_info={"user_id": "alice", "call_id": "call-123", "caller_id": "5551234567"},
)
# {
#   "fraud_detected": False,
#   "risk_score": 0.15,
#   "indicators": [],
#   "caller_info": {...},
#   "timestamp": "..."
# }
```

## Admin Panel

Access Voice Biometrics in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **Voice Biometrics**
2. View enrolled users and profile status
3. Review verification counts and fraud attempts
4. Create and delete profiles

## Best Practices

### Enrollment

- **Multiple Samples:** Collect at least `enrollment_samples` samples (default 3) for a usable profile; more improves GMM accuracy
- **Quality Check:** Ensure clean audio with minimal background noise
- **Consent:** Get explicit user consent for biometric collection

### Verification

- **Threshold Tuning:** Adjust `threshold` based on security needs
- **Fallback Authentication:** Provide alternative auth if voice fails
- **Error Handling:** Gracefully handle poor audio quality

### Security

- **Access Control:** Restrict access to biometric data
- **Audit Logging:** Log all verification attempts
- **Compliance:** Follow biometric privacy regulations (BIPA, GDPR)

### Performance

- **Audio Quality:** Use high-quality audio (16kHz, 16-bit PCM)
- **Optional Libraries:** Install `pyAudioAnalysis`/`librosa`/`scikit-learn` for better accuracy

## Database Schema

Tables are created by `pbx/features/voice_biometrics_db.py` (`create_tables`).

### voice_profiles

```sql
CREATE TABLE IF NOT EXISTS voice_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    extension VARCHAR(20),
    status VARCHAR(20) NOT NULL,
    enrollment_samples INTEGER DEFAULT 0,
    required_samples INTEGER DEFAULT 3,
    voiceprint_data BYTEA,
    successful_verifications INTEGER DEFAULT 0,
    failed_verifications INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### voice_enrollments

```sql
CREATE TABLE IF NOT EXISTS voice_enrollments (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES voice_profiles(id) ON DELETE CASCADE,
    sample_number INTEGER NOT NULL,
    audio_hash VARCHAR(64),
    quality_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### voice_verifications

```sql
CREATE TABLE IF NOT EXISTS voice_verifications (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES voice_profiles(id) ON DELETE CASCADE,
    call_id VARCHAR(255),
    verified BOOLEAN NOT NULL,
    confidence FLOAT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### voice_fraud_detections

```sql
CREATE TABLE IF NOT EXISTS voice_fraud_detections (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(255),
    caller_id VARCHAR(50),
    fraud_detected BOOLEAN NOT NULL,
    risk_score FLOAT,
    indicators JSONB,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Troubleshooting

### Low Verification Scores

**Solution:**

- Check audio quality (sample rate, noise)
- Re-enroll with more/better audio samples
- Adjust the verification `threshold`
- Install `scikit-learn` so GMM-based matching is used

### Enrollment Fails

**Solution:**

- Ensure the profile exists before calling `start_enrollment`
- Add at least `enrollment_samples` samples
- Verify audio is 16-bit PCM and long enough to extract features

### False Fraud Alerts

**Solution:**

- Review the returned `indicators` to see which heuristic fired
- Provide cleaner audio (background noise can trigger artifacts)
- Keep `caller_info` accurate so identity-mismatch checks work

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

## Related Documentation

- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md)
- [PLANNED_FEATURES.md](../PLANNED_FEATURES.md) - Planned (not-yet-implemented) capabilities for this feature
- [COMPLETE_GUIDE.md](../../COMPLETE_GUIDE.md) - Comprehensive documentation
