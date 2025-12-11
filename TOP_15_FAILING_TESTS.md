# Top 15 Failing Tests

**Note:** The test suite actually has 16 failing tests. Below are the 15 most critical ones (excluding test_json_serialization.py which technically passes but has warnings).

---

## 1. test_dtmf_detection.py
**Issue:** White noise false positive - incorrectly detected as DTMF tone 'B'  
**Fix:** Adjust DTMF detector sensitivity threshold

## 2. test_enterprise_integrations.py
**Issue:** Missing 'msal' library for Teams/Outlook integration  
**Fix:** Run `pip install msal`

## 3. test_g722_codec.py
**Issue:** ModuleNotFoundError: No module named 'pbx'  
**Fix:** Fix Python module path or add __init__.py files

## 4. test_opus_codec.py
**Issue:** ModuleNotFoundError: No module named 'pbx'  
**Fix:** Fix Python module path or add __init__.py files

## 5. test_phone_cleanup_startup.py
**Issue:** ModuleNotFoundError: No module named 'pbx'  
**Fix:** Fix Python module path or add __init__.py files

## 6. test_qos_monitoring.py
**Issue:** ModuleNotFoundError: No module named 'pbx'  
**Fix:** Fix Python module path or add __init__.py files

## 7. test_statistics.py
**Issue:** ModuleNotFoundError: No module named 'pbx'  
**Fix:** Fix Python module path or add __init__.py files

## 8. test_voicemail_transcription.py
**Issue:** ModuleNotFoundError: No module named 'pbx'  
**Fix:** Fix Python module path or add __init__.py files

## 9. test_voicemail_ivr_early_termination.py
**Issue:** IVR early termination detection not working (2 sub-tests failed)  
**Fix:** Update IVR logic to properly detect call termination before main loop

## 10. test_pbx_boot_clear.py
**Issue:** SSL certificate not found (test passes but server runs on HTTP)  
**Fix:** Run `python scripts/generate_ssl_cert.py`

## 11. test_phone_registration_integration.py
**Issue:** PostgreSQL library missing (psycopg2)  
**Fix:** Run `pip install psycopg2-binary` or accept SQLite fallback

## 12. test_provisioning.py
**Issue:** Unregistered device warnings  
**Fix:** Register test devices via API or update test configuration

## 13. test_provisioning_persistence.py
**Issue:** Missing environment variables (DB_PASSWORD, SMTP_PASSWORD, AD_BIND_PASSWORD)  
**Fix:** Set environment variables or configure defaults

## 14. test_phone_book_paging.py
**Issue:** Paging system is stub implementation  
**Fix:** Complete hardware integration or document stub status

## 15. test_registered_phones.py
**Issue:** Extensive configuration warnings and missing environment variables  
**Fix:** Configure DB_PASSWORD, SMTP_PASSWORD, AD_BIND_PASSWORD

---

## Priority Fixes

### High Priority (Critical Failures)
1. Fix 6 module import errors by correcting Python path
2. Install 'msal' library for enterprise integrations
3. Fix DTMF detection false positives
4. Fix IVR early termination detection

### Medium Priority (Configuration Issues)
5. Generate SSL certificates
6. Install PostgreSQL library or document SQLite usage
7. Set environment variables

### Low Priority (Warnings)
8. Complete paging hardware integration
9. Reduce configuration logging verbosity

---

**For complete details, see:** `FAILING_TESTS_LIST.md`
