# DTMF Detection Fix - Technical Notes

## Issue Summary
DTMF (Dual-Tone Multi-Frequency) detection was experiencing false positives during Auto Attendant operation, where the system incorrectly detected key presses from silence or background noise.

## Root Cause
The DTMF detector's Goertzel algorithm was using an extremely low threshold value of 0.01, which caused it to trigger on noise, silence, and other non-DTMF signals.

## Solution Implemented

### Changes to `pbx/utils/dtmf.py`

1. **Increased Detection Threshold**
   - Changed default threshold from `0.01` to `0.3` (30x increase)
   - This ensures only signals with sufficient magnitude are considered

2. **Added Pre-normalization Energy Check**
   - Rejects signals with amplitude < 0.01 before normalization
   - Prevents silence and very weak signals from triggering false positives

3. **Enhanced Noise Rejection**
   - Implemented relative magnitude checking
   - Detected frequencies must be at least 2x stronger than other frequencies
   - This ensures DTMF tones are dominant over background noise

### Code Changes Summary
```python
# Before: Very low threshold allowed false positives
def detect_tone(self, samples: List[float], threshold: float = 0.01) -> Optional[str]:
    # ... normalization ...
    if low_mag > threshold and high_mag > threshold:
        return digit

# After: Higher threshold + energy check + noise rejection
def detect_tone(self, samples: List[float], threshold: float = 0.3) -> Optional[str]:
    # Check signal energy first
    max_val = max(abs(s) for s in samples)
    if max_val < 0.01:
        return None
    
    # ... normalization ...
    
    # Verify detected frequencies are dominant (2x stronger than others)
    if low_mag > threshold and high_mag > threshold:
        if low_mag > avg_other_low * 2.0 and high_mag > avg_other_high * 2.0:
            return digit
```

## Testing

### New Test Suite
Created comprehensive test suite (`tests/test_dtmf_detection.py`) with 14 test cases covering:

- ✅ Valid DTMF tone detection (digits 0-9, *, #)
- ✅ DTMF sequence detection
- ✅ Silence rejection
- ✅ White noise rejection
- ✅ Single-frequency rejection (DTMF requires two frequencies)
- ✅ Weak signal rejection
- ✅ Noise dominance rejection
- ✅ Threshold parameter validation

### Regression Testing
- All existing Auto Attendant tests continue to pass (12 tests)
- No changes required to calling code
- Backward compatible (threshold is a parameter, defaults to 0.3)

## Impact

### Before Fix
- False DTMF detections during silence
- False DTMF detections from background noise
- Auto Attendant would respond to non-existent key presses
- Poor user experience during IVR interactions

### After Fix
- Reliable DTMF detection only for actual key presses
- Proper rejection of silence and noise
- Auto Attendant correctly waits for valid user input
- Improved IVR reliability and user experience

## Technical Background

### DTMF Detection Principles
DTMF tones consist of two simultaneous frequencies:
- Low frequency (697, 770, 852, or 941 Hz)
- High frequency (1209, 1336, 1477, or 1633 Hz)

For valid detection, both frequencies must:
1. Have sufficient magnitude (> threshold)
2. Be significantly stronger than other frequencies (noise rejection)
3. Have sufficient signal energy (not just normalized noise)

### Goertzel Algorithm
The Goertzel algorithm is a efficient method for detecting specific frequencies in a signal. It's more efficient than FFT for detecting a small number of frequencies, making it ideal for DTMF detection.

Key parameters:
- Sample rate: 8000 Hz (telephony standard)
- Samples per frame: 205 (approximately 25.6ms)
- Threshold: 0.3 (relative magnitude after normalization)

## References
- ITU-T Recommendation Q.24: Multifrequency push-button signal reception
- ITU-T Recommendation Q.23: Technical features of push-button telephone sets

## Files Changed
- `pbx/utils/dtmf.py` - Core detection logic improvements
- `tests/test_dtmf_detection.py` - New comprehensive test suite (14 tests)

## Security Note
No security vulnerabilities identified. Changes are purely algorithmic improvements to reduce false positives in signal detection.
