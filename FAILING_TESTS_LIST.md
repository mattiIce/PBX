# Failing Tests Report

**Generated:** 2025-12-11 12:07:25  
**Test Suite:** PBX System  
**Total Tests:** 72  
**Passed:** 56 (77.8%)  
**Failed:** 16 (22.2%)

---

## Summary of Failing Tests

This document provides a comprehensive list of the 16 failing tests identified in the PBX system test suite.

## Detailed Failing Tests List

### 1. test_dtmf_detection.py
**Status:** ❌ FAILED  
**Issue:** White noise false positive detection  
**Details:**
- Test: `test_no_detection_on_white_noise`
- Error: White noise is incorrectly detected as DTMF tone 'B'
- Expected: White noise should not trigger DTMF detection
- Root Cause: DTMF detector sensitivity too high

### 2. test_enterprise_integrations.py
**Status:** ❌ FAILED  
**Issue:** Missing dependency - 'msal' library  
**Details:**
- Failed Tests:
  - `test_teams_direct_routing` - Should successfully route with configured trunk
  - `test_outlook_meeting_reminder` - Should successfully schedule reminder with PBX core
- Error: "Teams integration requires 'msal' library. Install with: pip install msal"
- 3 tests passed, 2 tests failed

### 3. test_g722_codec.py
**Status:** ❌ FAILED  
**Issue:** Module import error  
**Details:**
- Error: `ModuleNotFoundError: No module named 'pbx'`
- Cannot import: `from pbx.features.g722_codec import G722Codec, G722CodecManager`
- Root Cause: Python path or module structure issue

### 4. test_json_serialization.py
**Status:** ⚠️ PASSED (with warnings)  
**Issue:** Missing environment variables  
**Details:**
- All 3 tests passed
- Warnings: Missing DB_PASSWORD, SMTP_PASSWORD, AD_BIND_PASSWORD
- Note: Listed as failed in log but test execution succeeded

### 5. test_opus_codec.py
**Status:** ❌ FAILED  
**Issue:** Module import error  
**Details:**
- Error: `ModuleNotFoundError: No module named 'pbx'`
- Cannot import: `from pbx.features.opus_codec import OpusCodec, OpusCodecManager`
- Root Cause: Python path or module structure issue

### 6. test_pbx_boot_clear.py
**Status:** ⚠️ PASSED (with configuration issues)  
**Issue:** SSL certificate not found  
**Details:**
- Test passed: PBX preserves registered phones on boot
- Warning: SSL certificate file not found at certs/server.crt
- Server continues on HTTP instead of HTTPS

### 7. test_phone_book_paging.py
**Status:** ⚠️ PASSED (with warnings)  
**Issue:** Configuration warnings  
**Details:**
- All tests passed
- Info: Paging system is a stub implementation
- Warning: Full paging requires hardware integration

### 8. test_phone_cleanup_startup.py
**Status:** ❌ FAILED  
**Issue:** Module import error  
**Details:**
- Error: `ModuleNotFoundError: No module named 'pbx'`
- Cannot import: `from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB`
- Root Cause: Python path or module structure issue

### 9. test_phone_registration_integration.py
**Status:** ⚠️ PASSED (with errors)  
**Issue:** PostgreSQL library missing  
**Details:**
- All 3 tests passed
- Error: "PostgreSQL requested but psycopg2 not installed"
- Fallback: System uses SQLite instead
- Missing environment variables: DB_PASSWORD, SMTP_PASSWORD, AD_BIND_PASSWORD

### 10. test_provisioning.py
**Status:** ⚠️ PASSED (with warnings)  
**Issue:** Unregistered device warnings  
**Details:**
- All tests passed
- Warnings: Device needs to be registered via API
- Similar MAC addresses found (possible typo)

### 11. test_provisioning_persistence.py
**Status:** ⚠️ PASSED (with warnings)  
**Issue:** Environment variable warnings  
**Details:**
- All 3 tests passed
- Missing: DB_PASSWORD, SMTP_PASSWORD, AD_BIND_PASSWORD
- Tests use temporary database successfully

### 12. test_qos_monitoring.py
**Status:** ❌ FAILED  
**Issue:** Module import error  
**Details:**
- Error: `ModuleNotFoundError: No module named 'pbx'`
- Cannot import: `from pbx.features.qos_monitoring import QoSMetrics, QoSMonitor`
- Root Cause: Python path or module structure issue

### 13. test_registered_phones.py
**Status:** ⚠️ PASSED (with extensive logging)  
**Issue:** Verbose configuration warnings  
**Details:**
- All 9 tests passed
- Extensive logging from database initialization
- Multiple warnings about missing environment variables

### 14. test_statistics.py
**Status:** ❌ FAILED  
**Issue:** Module import error  
**Details:**
- Error: `ModuleNotFoundError: No module named 'pbx'`
- Cannot import: `from pbx.features.cdr import CDRSystem, CDRRecord, CallDisposition`
- Root Cause: Python path or module structure issue

### 15. test_voicemail_ivr_early_termination.py
**Status:** ❌ FAILED  
**Issue:** IVR early termination detection not working  
**Details:**
- Failed Tests:
  - `test_ivr_detects_call_ended_before_start` - Should log that call ended before IVR started
  - `test_ivr_session_ended_message_only_after_loop` - Should detect call ended before IVR started
- Both tests ran but assertions failed
- Root Cause: IVR not properly detecting when call ends before main loop starts

### 16. test_voicemail_transcription.py
**Status:** ❌ FAILED  
**Issue:** Module import error  
**Details:**
- Error: `ModuleNotFoundError: No module named 'pbx'`
- Cannot import: `from pbx.features.voicemail_transcription import VoicemailTranscriptionService`
- Root Cause: Python path or module structure issue

---

## Failure Categories

### Critical Import Errors (6 tests)
Tests failing due to `ModuleNotFoundError: No module named 'pbx'`:
- test_g722_codec.py
- test_opus_codec.py
- test_phone_cleanup_startup.py
- test_qos_monitoring.py
- test_statistics.py
- test_voicemail_transcription.py

**Root Cause:** Python module path issue or missing `__init__.py` files

### Missing Dependencies (1 test)
- test_enterprise_integrations.py - Requires 'msal' library for Teams/Outlook integration

### Logic Errors (2 tests)
- test_dtmf_detection.py - False positive in DTMF detection
- test_voicemail_ivr_early_termination.py - IVR termination detection logic

### Configuration Issues (7 tests)
Tests that pass but have warnings/errors:
- test_json_serialization.py
- test_pbx_boot_clear.py
- test_phone_book_paging.py
- test_phone_registration_integration.py
- test_provisioning.py
- test_provisioning_persistence.py
- test_registered_phones.py

---

## Recommendations

1. **Fix Python Module Path**: Add proper `__init__.py` files or fix PYTHONPATH to resolve the 6 import errors
2. **Install Missing Dependencies**: Run `pip install msal` for enterprise integrations
3. **Fix DTMF Detection**: Adjust sensitivity threshold to prevent false positives
4. **Fix IVR Early Termination**: Update logic to properly detect call termination before IVR loop
5. **Address Configuration Warnings**: Set up environment variables (DB_PASSWORD, SMTP_PASSWORD, AD_BIND_PASSWORD) or use proper defaults
6. **Generate SSL Certificate**: Run `python scripts/generate_ssl_cert.py` for development/testing

---

## Test Failure Log Location

Full test failure details are available in:
- **File:** `test_failures.log`
- **Location:** `/home/runner/work/PBX/PBX/test_failures.log`

---

## How to Run Tests

### Run All Tests
```bash
python run_tests.py
```

### Run Specific Test
```bash
python tests/test_dtmf_detection.py
```

### Run Tests with Verbose Output
```bash
python run_tests.py 2>&1 | tee test_output.log
```
