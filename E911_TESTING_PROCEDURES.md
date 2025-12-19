# E911 Testing and Validation Procedures

**Purpose**: Testing procedures for E911 compliance (Kari's Law, Ray Baum's Act)  
**Critical Blocker**: 1.3 from STRATEGIC_ROADMAP.md  
**Regulatory Requirement**: Federal law compliance  
**Generated**: December 19, 2025

---

## Overview

This document provides comprehensive testing procedures for validating E911 emergency calling functionality in the PBX system. Proper E911 testing is **required by federal law** and must be performed regularly to ensure compliance.

### Regulatory Requirements

1. **Kari's Law** (47 U.S.C. § 623)
   - Direct 911 dialing without prefix (no "9" needed)
   - Notification to security/reception on 911 calls
   - Applies to: Multi-line telephone systems (MLTS)

2. **Ray Baum's Act** (47 U.S.C. § 615a-1)
   - Dispatchable location information
   - Building, floor, room/suite number
   - Applies to: Fixed and non-fixed devices

### Implementation Status

✅ **Kari's Law**: IMPLEMENTED (Dec 12, 2025)  
✅ **Ray Baum's Act**: IMPLEMENTED (Dec 15, 2025)  
✅ **Multi-Site E911**: IMPLEMENTED (Dec 15, 2025)  
✅ **Nomadic E911**: IMPLEMENTED (Dec 15, 2025)

⚠️ **Testing Required**: Production validation needed

---

## Testing Schedule

### Initial Testing
- [ ] Complete before pilot deployment
- [ ] Test all sites and trunk configurations
- [ ] Document all test results

### Ongoing Testing
- [ ] Quarterly testing (recommended)
- [ ] After any trunk configuration changes
- [ ] After any location database changes
- [ ] After major system upgrades

---

## Pre-Test Checklist

### 1. Coordination

- [ ] Schedule test with PSAP (911 center) if possible
- [ ] Use non-emergency test line (933 in some jurisdictions)
- [ ] Notify IT staff and security team
- [ ] Prepare test plan and documentation

### 2. Environment Preparation

- [ ] Identify test extensions at each location
- [ ] Verify location database is up to date
- [ ] Verify trunk routing configuration
- [ ] Prepare monitoring tools

### 3. Safety Precautions

- [ ] **NEVER** dial 911 for testing without coordination
- [ ] Use 933 test line or coordinate with PSAP
- [ ] Have alternative emergency contact method ready
- [ ] Keep test duration brief

---

## Test Procedures

### Test 1: Direct 911 Dialing (Kari's Law)

**Objective**: Verify that 911 can be dialed directly without prefix

**Steps**:
1. From test extension, dial `911` (no prefix needed)
2. Verify call connects to PSAP or test line
3. Verify no "9" or other prefix is required
4. Document call connection time

**Expected Results**:
- ✓ Call connects directly to 911
- ✓ No prefix required
- ✓ Call setup time < 5 seconds

**Pass/Fail Criteria**:
```
PASS: 911 call connects without prefix
FAIL: Requires prefix or call doesn't connect
```

---

### Test 2: Dispatchable Location (Ray Baum's Act)

**Objective**: Verify correct location information is transmitted

**Steps**:
1. Make test 911 call from known location
2. Ask dispatcher what location they see
3. Verify accuracy of:
   - Building/facility name
   - Floor number
   - Room/suite number
   - Street address
   - City, state, ZIP

**Expected Results**:
```
Building: [Facility Name]
Floor: [Floor Number]
Room: [Room/Suite]
Address: [Full Street Address]
City/State/ZIP: [City, State ZIP]
```

**Pass/Fail Criteria**:
```
PASS: All location fields accurate and complete
WARN: Location partially accurate (needs update)
FAIL: Location missing or incorrect
```

---

### Test 3: Emergency Notification (Kari's Law)

**Objective**: Verify notification sent to security/reception

**Steps**:
1. Configure notification endpoint (security/reception)
2. Make test 911 call
3. Verify notification received within 30 seconds
4. Check notification contains:
   - Caller extension
   - Caller name
   - Location information
   - Call timestamp

**Expected Results**:
- ✓ Notification sent immediately (< 30 seconds)
- ✓ Notification includes all required information
- ✓ Multiple notification methods work (email, SMS, screen pop)

**Pass/Fail Criteria**:
```
PASS: Notification received with complete info
WARN: Notification delayed or partial info
FAIL: No notification received
```

---

### Test 4: PSAP Callback Routing

**Objective**: Verify callback from PSAP reaches correct location

**Steps**:
1. Make test 911 call
2. Request dispatcher call back
3. Verify callback routes to:
   - Security desk (primary)
   - Reception (secondary)
   - Original caller (tertiary)

**Expected Results**:
- ✓ Callback rings security desk
- ✓ If no answer, rings reception
- ✓ If no answer, rings original caller

**Pass/Fail Criteria**:
```
PASS: Callback reaches appropriate endpoint
WARN: Callback works but routing order incorrect
FAIL: Callback fails or routes incorrectly
```

---

### Test 5: Multi-Site Routing

**Objective**: Verify correct PSAP for each site

**For each site**:
1. Make test call from extension at that site
2. Verify call routes to correct local PSAP
3. Verify location information is site-specific

**Expected Results**:

| Site | Extension | Expected PSAP | Trunk Used |
|------|-----------|---------------|------------|
| HQ | 1001 | City A PSAP | Trunk A |
| Branch 1 | 2001 | City B PSAP | Trunk B |
| Branch 2 | 3001 | City C PSAP | Trunk C |

**Pass/Fail Criteria**:
```
PASS: All sites route to correct local PSAP
WARN: Some sites route correctly, others need adjustment
FAIL: Sites route to incorrect PSAP
```

---

### Test 6: Nomadic E911 (Remote Workers)

**Objective**: Verify location updates for remote workers

**Steps**:
1. Configure test softphone/mobile device
2. Register from different locations
3. Update location information
4. Make test call
5. Verify location matches current location

**Expected Results**:
- ✓ Location update succeeds
- ✓ 911 call uses updated location
- ✓ Call routes to correct local PSAP

**Pass/Fail Criteria**:
```
PASS: Nomadic location tracking works
WARN: Location updates but with delays
FAIL: Location not updated or incorrect
```

---

## Test Documentation Template

### Test Record Form

```
E911 TEST RECORD
================
Date: ______________
Time: ______________
Tester: ______________
Site: ______________

Test Extension: ______________
Extension Name: ______________
Location: ______________

Test Results:
[ ] Direct 911 dialing works (no prefix)
[ ] Location information correct
[ ] Notification sent to security
[ ] PSAP callback routing works
[ ] Multi-site routing correct (if applicable)
[ ] Nomadic E911 works (if applicable)

Issues Found:
_________________________________
_________________________________
_________________________________

Actions Required:
_________________________________
_________________________________
_________________________________

Tested By: ______________
Signature: ______________
```

---

## Compliance Verification Checklist

### Kari's Law Compliance

- [ ] Direct 911 dialing enabled (no prefix required)
- [ ] Emergency notifications configured
- [ ] Notifications sent to security/front desk
- [ ] Notification contains caller ID and location
- [ ] System tested quarterly

### Ray Baum's Act Compliance

- [ ] Dispatchable location database maintained
- [ ] Location includes building, floor, room
- [ ] Location accuracy verified
- [ ] Location transmitted with 911 calls
- [ ] Remote worker locations tracked (if applicable)

### Ongoing Compliance

- [ ] Testing schedule established (quarterly minimum)
- [ ] Test results documented
- [ ] Issues identified and resolved
- [ ] Compliance audit trail maintained
- [ ] Staff trained on emergency procedures

---

## Troubleshooting Common Issues

### Issue: 911 Call Doesn't Connect

**Possible Causes**:
- Trunk not configured
- SIP provider doesn't support E911
- Incorrect dial plan

**Solutions**:
1. Verify trunk configuration in config.yml
2. Contact SIP provider to enable E911
3. Check dial plan for 911 routing rule
4. Test with `*911` pattern in logs

### Issue: Wrong Location Transmitted

**Possible Causes**:
- Location database not updated
- Extension not mapped to location
- Multi-site routing incorrect

**Solutions**:
1. Update location database
2. Map extension to correct location
3. Verify site-to-trunk mapping
4. Test location lookup function

### Issue: No Notification Sent

**Possible Causes**:
- Notification endpoint not configured
- Email/SMS credentials invalid
- Network connectivity issue

**Solutions**:
1. Configure notification settings in config.yml
2. Verify email/SMS credentials
3. Test notification system separately
4. Check network connectivity

### Issue: PSAP Callback Fails

**Possible Causes**:
- Callback number not in DID pool
- Routing rule missing
- Trunk doesn't support inbound calls

**Solutions**:
1. Add callback number to DID pool
2. Create routing rule for callback
3. Verify trunk supports bidirectional calls
4. Test inbound call to callback number

---

## E911 Testing Script

Automated test helper:

```bash
#!/bin/bash
# E911 Testing Helper Script

echo "E911 Testing Helper"
echo "==================="
echo ""
echo "⚠️  WARNING: Use 933 test line or coordinate with PSAP"
echo "    NEVER dial 911 without proper coordination"
echo ""

# Test configuration
read -p "Test extension: " EXTENSION
read -p "Expected location: " LOCATION
read -p "Test method (933/PSAP): " METHOD

echo ""
echo "Test Plan:"
echo "----------"
echo "Extension: $EXTENSION"
echo "Location: $LOCATION"
echo "Method: $METHOD"
echo ""

read -p "Proceed with test? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Test cancelled"
    exit 0
fi

echo ""
echo "Test Checklist:"
echo "---------------"
echo "1. [ ] Direct dial works (no prefix)"
echo "2. [ ] Location transmitted correctly"
echo "3. [ ] Notification sent to security"
echo "4. [ ] Callback routing works"
echo ""

read -p "Record test results in log? (yes/no): " RECORD

if [ "$RECORD" = "yes" ]; then
    LOG_FILE="e911_test_$(date +%Y%m%d_%H%M%S).log"
    echo "Test Date: $(date)" > $LOG_FILE
    echo "Extension: $EXTENSION" >> $LOG_FILE
    echo "Location: $LOCATION" >> $LOG_FILE
    echo "Method: $METHOD" >> $LOG_FILE
    echo "Test log saved to: $LOG_FILE"
fi

echo ""
echo "Test complete. Review results above."
```

---

## Non-Emergency Test Line (933)

Many jurisdictions provide a non-emergency test line for 911 systems:

### Using 933 Test Line

1. **Check Availability**: Not all areas have 933
2. **Dial**: Call 933 instead of 911
3. **Recording**: Usually plays a recording
4. **Verification**: May provide location verification

### Test Line Alternatives

- **PSAP Coordination**: Schedule with local PSAP
- **SIP Provider**: Some provide test endpoints
- **Internal Test**: Test dial plan without PSAP connection

---

## Compliance Documentation

### Required Records

1. **Test Results**: Date, time, results, issues
2. **Location Database**: Current, accurate, timestamped
3. **Configuration**: Trunk settings, routing rules
4. **Training**: Staff training on E911 procedures
5. **Audit Trail**: All changes to E911 configuration

### Retention Period

- Test results: 2 years minimum
- Configuration changes: 2 years minimum
- Training records: Duration of employment + 1 year

---

## Next Steps

### This Week
- [ ] Schedule E911 test with PSAP or use 933
- [ ] Test at least 3 extensions at different locations
- [ ] Document all test results
- [ ] Verify location database accuracy

### This Month
- [ ] Complete testing for all sites
- [ ] Train security/reception on notification procedures
- [ ] Establish quarterly testing schedule
- [ ] Create compliance audit trail

### Ongoing
- [ ] Quarterly testing
- [ ] Update location database as changes occur
- [ ] Re-test after any system changes
- [ ] Maintain compliance documentation

---

## References

### Legal Requirements

- **Kari's Law**: 47 U.S.C. § 623
- **Ray Baum's Act**: 47 U.S.C. § 615a-1
- **FCC Guidelines**: [https://www.fcc.gov/911-and-e911-services](https://www.fcc.gov/911-and-e911-services)

### PBX Documentation

- `E911_PROTECTION_GUIDE.md` - E911 system overview
- `KARIS_LAW_GUIDE.md` - Kari's Law implementation
- `MULTI_SITE_E911_GUIDE.md` - Multi-site configuration
- `config.yml` - E911 configuration settings

### Contact Information

- **Local PSAP**: [Contact info]
- **SIP Provider**: [Support contact]
- **IT Support**: [Internal contact]
- **Security Team**: [Internal contact]

---

**Document Version**: 1.0  
**Last Updated**: December 19, 2025  
**Next Review**: March 19, 2026
