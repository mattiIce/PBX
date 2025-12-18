# PBX System Regulations and Compliance Guide

**Last Updated**: December 18, 2024  
**Version**: 2.0

> **📋 Consolidated Guide**: This document combines all regulatory and compliance documentation including E911, Kari's Law, STIR/SHAKEN, multi-site E911, and SOC 2 Type 2.

## Table of Contents

1. [E911 Protection](#e911-protection)
2. [Kari's Law Compliance](#karis-law-compliance)
3. [Multi-Site E911](#multi-site-e911)
4. [STIR/SHAKEN Authentication](#stirshaken-authentication)
5. [SOC 2 Type 2 Compliance](#soc-2-type-2-compliance)

---

## E911 Protection

### Overview

The PBX system includes a comprehensive E911 (Enhanced 911) protection system that prevents emergency calls from being placed during testing and development scenarios. This is a critical safety feature that ensures 911 calls are never accidentally placed during testing.

**Why This Matters**:
- ❌ Prevents tying up emergency services resources
- ❌ Avoids fines or legal issues
- ❌ Eliminates confusion for emergency responders
- ❌ Ensures telecommunications regulation compliance

**Status**: ✅ **FULLY IMPLEMENTED**

### How It Works

#### Automatic Test Mode Detection

The E911 protection system automatically detects when the PBX is running in test mode by checking for:

**Environment Variables**:
- `PYTEST_CURRENT_TEST` - Set by pytest
- `TEST_MODE` - Generic test mode indicator
- `TESTING` - Alternative test mode indicator
- `PBX_TEST_MODE` - PBX-specific test mode flag

**Configuration File Names**:
- Files containing "test" in the name (e.g., `test_config.yml`)

#### E911 Number Detection

The system recognizes various E911 patterns:
- `911` - Standard emergency number
- `1911`, `12911`, etc. - Enhanced 911 with location prefixes
- `*911` - Special prefix variations

#### Protection Levels

**Test Mode (Automatic)**:
When test mode is detected:
- ✅ All E911 calls are **BLOCKED**
- ✅ Error messages are logged
- ✅ Calls fail gracefully without reaching SIP trunks
- ✅ No emergency service is contacted

**Production Mode**:
In production mode:
- ✅ E911 calls are **allowed** to proceed
- ✅ Warning messages are logged for audit purposes
- ✅ Emergency services can be contacted normally

### Usage

#### For Testing

The protection is automatic. Simply run your tests normally:

```bash
# Run tests with pytest (automatically detected)
pytest tests/test_e911_protection.py

# Run tests directly (set environment variable)
TEST_MODE=1 python tests/test_basic.py

# Run with test configuration
python main.py --config test_config.yml
```

#### For Development

Set the `TEST_MODE` environment variable to prevent accidental 911 calls:

```bash
# In your shell
export TEST_MODE=1

# Run the PBX
python main.py
```

#### For Production

Simply run the PBX normally without any test mode indicators:

```bash
# Production mode - E911 allowed
python main.py
```

### Implementation Details

**E911Protection Class**  
Location: `pbx/utils/e911_protection.py`

**Key Methods**:
- `is_e911_number(number)` - Check if a number is an E911 pattern
- `block_if_e911(number, context)` - Block E911 calls in test mode
- `is_test_mode()` - Check if currently in test mode

**Integration Points**:
- SIP server call routing
- Dialplan processing
- Call manager
- Testing framework

### Testing

```bash
# Run E911 protection tests
pytest tests/test_e911_protection.py

# Test scenarios included:
# - E911 blocking in test mode
# - E911 allowed in production
# - Various emergency number patterns
# - Environment variable detection
# - Configuration file detection
```

### Audit Trail

All E911 call attempts are logged:

```
[E911] WARNING: E911 call blocked in test mode - number: 911, extension: 1001
[E911] INFO: E911 call allowed in production - number: 911, extension: 1001, location: Building A, Floor 2
```

---

## Kari's Law Compliance

### Overview

This PBX system implements **Kari's Law** compliance, which is a federal requirement under 47 CFR § 9.16 for multi-line telephone systems (MLTS).

**Status**: ✅ **FULLY COMPLIANT**

### Legal Requirements

**Kari's Law Requirements**:
1. ✅ **Direct 911 dialing** without requiring a prefix or access code
2. ✅ **Immediate routing** to emergency services without delay
3. ✅ **Automatic notification** to designated contacts when 911 is dialed

**Ray Baum's Act Requirements**:
1. ✅ Provide **dispatchable location information** with 911 calls

### Features

#### ✅ Direct 911 Dialing (Kari's Law Requirement)

Users can dial **911 directly** without needing to dial a prefix like "9-911":

```
User dials: 911
System routes: Directly to emergency services
```

#### ✅ Legacy Prefix Support

The system also accepts legacy dialing patterns for backward compatibility:
- `911` - Direct dialing (preferred)
- `9911` - Legacy prefix
- `9-911` - Legacy prefix with dash

All formats are automatically normalized to `911` before routing.

#### ✅ Automatic Emergency Notification

When 911 is dialed, the system **automatically** notifies designated emergency contacts:

**Notification Recipients**:
- Security team
- Building management
- Safety coordinators
- Other configured contacts

**Notification Methods**:
- Internal calls
- Overhead paging
- Email alerts
- SMS messages (if configured)

#### ✅ Location Information (Ray Baum's Act)

Emergency calls include **dispatchable location** information:
- Building name/number
- Floor
- Room number
- Full address
- City, state, ZIP code

This ensures emergency responders know exactly where to go.

#### ✅ Emergency Call Tracking

All emergency calls are logged with:
- Caller extension
- Caller name
- Location information
- Timestamp
- Call routing details
- Notification status

### Configuration

#### Enable Kari's Law Compliance

Edit `config.yml`:

```yaml
features:
  karis_law:
    enabled: true                    # Enable Kari's Law compliance
    auto_notify: true                # Auto-notify contacts on 911 calls
    require_location: true           # Require location registration
    emergency_trunk_id: "emergency"  # Dedicated emergency trunk (optional)
```

#### Configure E911 Location Service

```yaml
features:
  e911:
    enabled: true
    site_address:
      address: "123 Manufacturing Drive"
      city: "Industrial City"
      state: "MI"
      zip_code: "48001"
    buildings:
      - id: "building_a"
        name: "Building A - Main Assembly"
        floors:
          - id: "floor_1"
            number: 1
            name: "First Floor"
          - id: "floor_2"
            number: 2
            name: "Second Floor"
```

#### Configure Emergency Contacts

```yaml
features:
  karis_law:
    notification_contacts:
      - extension: "5000"
        name: "Security Desk"
        type: "internal_call"
      - email: "security@company.com"
        type: "email"
      - phone: "+15551234567"
        type: "sms"
```

### Implementation

#### Dialplan Rules

The system automatically adds emergency routing rules:

```python
# Emergency routing (Kari's Law)
if dialed_number in ['911', '9911', '9-911']:
    # Normalize to 911
    normalized = '911'
    
    # Get caller location
    location = get_caller_location(extension)
    
    # Route via emergency trunk
    route_emergency_call(normalized, location)
    
    # Notify contacts
    notify_emergency_contacts(extension, location)
    
    # Log emergency call
    log_emergency_call(extension, location, timestamp)
```

#### Location Detection

```python
from pbx.features.nomadic_e911 import NomadicE911

# Get dispatchable location
e911 = NomadicE911()
location = e911.get_location(extension, ip_address)

# Location includes:
# - Building name
# - Floor number
# - Room/office number
# - Full street address
# - City, state, ZIP code
```

### Testing

```bash
# Test emergency routing (safe - uses test mode)
TEST_MODE=1 python tests/test_karis_law.py

# Expected output:
# ✅ Direct 911 dialing works
# ✅ Legacy prefixes normalized
# ✅ Emergency contacts notified
# ✅ Location included in call
# ✅ Call logged with full details
```

### Compliance Verification

To verify Kari's Law compliance:

```bash
# Run compliance verification
python scripts/verify_karis_law_compliance.py

# Checks:
# ✅ Direct 911 dialing enabled
# ✅ No prefix required
# ✅ Automatic notification configured
# ✅ Location service active
# ✅ Emergency contacts defined
# ✅ Logging enabled
```

### Audit Reports

Generate compliance audit reports:

```bash
# Generate monthly audit report
python scripts/generate_emergency_call_report.py --month 2024-12

# Report includes:
# - Total emergency calls
# - Response times
# - Notification success rate
# - Location accuracy
# - Compliance status
```

---

## Multi-Site E911

**Last Updated**: December 15, 2025  
**Status**: ✅ **Production Ready**

### Overview

The Multi-Site E911 feature provides location-based emergency routing for organizations with multiple physical locations. Each site can have its own emergency trunk, PSAP (Public Safety Answering Point) number, and ELIN (Emergency Location Identification Number).

### Key Benefits

- ✅ **Site-Specific Routing**: Automatic routing via correct trunk for each location
- ✅ **Local PSAP Support**: Each site can have unique PSAP number
- ✅ **ELIN Management**: Track Emergency Location Identification Numbers per site
- ✅ **IP-Based Detection**: Automatic site detection based on caller IP address
- ✅ **Compliance**: Ray Baum's Act and Kari's Law compliant
- ✅ **High Availability**: Automatic failover to global emergency trunk

### How It Works

#### Architecture

```
Caller makes 911 call
    ↓
Kari's Law detects emergency number
    ↓
Get caller's IP address and extension
    ↓
Query Nomadic E911 for location
    ↓
Find site configuration by IP range
    ↓
Route via site-specific emergency trunk
    ↓
Include PSAP and ELIN in routing info
    ↓
Trigger emergency notifications
    ↓
Log emergency call with full details
```

#### Emergency Routing Priority

1. **Site-Specific Emergency Trunk** (Highest Priority)
   - Determined by caller's IP address
   - Maps to closest/most appropriate PSAP
   - Includes site-specific ELIN

2. **Global Emergency Trunk** (Fallback)
   - Configured in `config.yml` under `karis_law.emergency_trunk_id`
   - Used if site-specific trunk unavailable

3. **Any Available Trunk** (Last Resort)
   - Standard outbound routing
   - Only used if no emergency trunks available

### Configuration

#### Site Configuration

Each site is configured with:
- **Site Name**: Descriptive name (e.g., "Detroit Factory")
- **IP Range**: Start and end IP addresses
- **Emergency Trunk ID**: SIP trunk ID for emergency calls
- **PSAP Number**: Local emergency services number (usually 911)
- **ELIN**: Emergency Location Identification Number (callback number)
- **Full Address**: Street, city, state, postal code, building, floor

#### Database Schema

```sql
CREATE TABLE multi_site_e911_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name TEXT NOT NULL,
    ip_range_start TEXT NOT NULL,
    ip_range_end TEXT NOT NULL,
    emergency_trunk TEXT,
    psap_number TEXT,
    elin TEXT,
    street_address TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'USA',
    building TEXT,
    floor TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

#### Create Site Configuration

```bash
POST /api/e911/multi-site/config
Content-Type: application/json

{
  "site_name": "Detroit Factory",
  "ip_range_start": "192.168.10.1",
  "ip_range_end": "192.168.10.254",
  "emergency_trunk": "detroit_emergency_trunk",
  "psap_number": "911",
  "elin": "+13135551000",
  "street_address": "1234 Industrial Blvd",
  "city": "Detroit",
  "state": "MI",
  "postal_code": "48201",
  "building": "Building A",
  "floor": "1"
}
```

#### Get Site Configuration

```bash
GET /api/e911/multi-site/config/{site_id}
```

#### List All Sites

```bash
GET /api/e911/multi-site/configs
```

#### Update Site Configuration

```bash
PUT /api/e911/multi-site/config/{site_id}
```

#### Delete Site Configuration

```bash
DELETE /api/e911/multi-site/config/{site_id}
```

### Example Multi-Site Setup

```yaml
# Site 1: Detroit Factory
site_name: "Detroit Factory"
ip_range: "192.168.10.0/24"
emergency_trunk: "detroit_emergency"
psap: "911"
elin: "+13135551000"
address: "1234 Industrial Blvd, Detroit, MI 48201"

# Site 2: Chicago Warehouse
site_name: "Chicago Warehouse"
ip_range: "192.168.20.0/24"
emergency_trunk: "chicago_emergency"
psap: "911"
elin: "+13125552000"
address: "5678 Warehouse Dr, Chicago, IL 60601"

# Site 3: New York Office
site_name: "New York Office"
ip_range: "192.168.30.0/24"
emergency_trunk: "newyork_emergency"
psap: "911"
elin: "+12125553000"
address: "9012 Office Plaza, New York, NY 10001"
```

### Usage

#### Automatic Site Detection

When a user dials 911:

1. System detects IP address: `192.168.10.55`
2. Finds matching site: "Detroit Factory"
3. Routes via trunk: `detroit_emergency`
4. Includes ELIN: `+13135551000`
5. Sends location: "1234 Industrial Blvd, Detroit, MI 48201, Building A, Floor 1"
6. Notifies: Site-specific emergency contacts

#### Manual Site Assignment

```bash
# Assign extension to specific site
POST /api/e911/extension-site
{
  "extension": "1001",
  "site_id": 1
}
```

### Testing

```bash
# Test multi-site routing (safe mode)
TEST_MODE=1 python tests/test_multi_site_e911.py

# Test scenarios:
# ✅ Site detection by IP range
# ✅ Correct trunk selection
# ✅ ELIN inclusion
# ✅ Failover to global trunk
# ✅ Location information accuracy
```

### High Availability

#### Trunk Failover

If site-specific trunk is unavailable:

```python
# Primary: Site-specific trunk
trunk = get_site_emergency_trunk(caller_ip)

if not trunk or not trunk.is_available():
    # Fallback: Global emergency trunk
    trunk = get_global_emergency_trunk()
    
    if not trunk or not trunk.is_available():
        # Last resort: Any available trunk
        trunk = get_any_available_trunk()
```

#### Redundant Trunks

Configure multiple emergency trunks per site:

```yaml
sites:
  - name: "Detroit Factory"
    emergency_trunks:
      - id: "detroit_primary"
        priority: 1
      - id: "detroit_backup"
        priority: 2
```

### Reporting

#### Emergency Call Report

```bash
# Generate site-specific report
python scripts/generate_multi_site_e911_report.py --site-id 1 --month 2024-12

# Report includes:
# - Emergency calls per site
# - Trunk usage statistics
# - ELIN callback numbers used
# - Location accuracy
# - Failover events
```

---

## STIR/SHAKEN Authentication

**Status**: ✅ **FULLY IMPLEMENTED** (December 12, 2025)

### Overview

STIR/SHAKEN is a framework for authenticating caller ID information in Voice over IP (VoIP) telephone networks. It helps prevent caller ID spoofing by digitally signing call information using cryptographic certificates.

**Standards**:
- **STIR** (Secure Telephone Identity Revisited) - RFC 8224
- **SHAKEN** (Signature-based Handling of Asserted information using toKENs) - RFC 8588

### Key Features

✅ **PASSporT Token Creation** - RFC 8225 compliant Personal Assertion Tokens  
✅ **Identity Header Support** - SIP Identity header with cryptographic signatures  
✅ **Three Attestation Levels**:
- **Level A (Full)**: Service provider authenticated caller and verified number authorization
- **Level B (Partial)**: Provider authenticated caller but cannot verify number authorization  
- **Level C (Gateway)**: Provider originated call but cannot authenticate caller

✅ **Certificate Management** - Support for RSA and ECDSA certificates  
✅ **Signature Verification** - Validates incoming caller ID signatures  
✅ **SIP Integration** - Seamless integration with SIP INVITE messages

### Attestation Levels Explained

| Level | Name | Meaning | Use Case |
|-------|------|---------|----------|
| **A** | Full | Provider authenticated caller AND verified number ownership | Your own customers calling out |
| **B** | Partial | Provider authenticated caller but NOT verified number | Calls from authenticated but unverified sources |
| **C** | Gateway | Provider originated call but cannot authenticate | Gateway/trunk calls from other providers |

### Installation

#### Requirements

```bash
# Install cryptography library
pip install cryptography>=41.0.0

# Already included in requirements.txt
```

**System Requirements**:
- Python 3.7+
- OpenSSL (included with most systems)
- STIR/SHAKEN certificate from authorized Certificate Authority (for production)

### Quick Start

#### 1. Generate Test Certificates

For development and testing:

```python
from pbx.features.stir_shaken import STIRSHAKENManager

# Create manager
manager = STIRSHAKENManager()

# Generate test certificate
cert_path, key_path = manager.generate_test_certificate('/etc/pbx/certs')
print(f"Certificate: {cert_path}")
print(f"Private key: {key_path}")
```

#### 2. Configure STIR/SHAKEN Manager

```python
config = {
    'certificate_path': '/etc/pbx/certs/stir_shaken_cert.pem',
    'private_key_path': '/etc/pbx/certs/stir_shaken_key.pem',
    'ca_cert_path': '/etc/pbx/certs/ca-bundle.pem',  # Optional
    'originating_tn': '+18005551234',  # Your service provider number
    'service_provider_code': 'MYSP',
    'certificate_url': 'https://certs.mysp.com/cert.pem',
    'enable_signing': True,
    'enable_verification': True
}

manager = STIRSHAKENManager(config)
```

#### 3. Sign Outgoing Calls

```python
from pbx.features.stir_shaken import (
    AttestationLevel,
    add_stir_shaken_to_invite
)
from pbx.sip.message import SIPMessage

# Create SIP INVITE
sip_msg = SIPMessage()
sip_msg.method = "INVITE"
sip_msg.uri = "sip:+13105555678@carrier.com"

# Add STIR/SHAKEN signature
sip_msg = add_stir_shaken_to_invite(
    sip_msg,
    manager,
    from_number="+18005551234",
    to_number="+13105555678",
    attestation=AttestationLevel.FULL  # Level A
)

# SIP message now includes Identity header with signature
```

#### 4. Verify Incoming Calls

```python
from pbx.features.stir_shaken import verify_stir_shaken

# Verify incoming INVITE
result = verify_stir_shaken(sip_msg, manager)

if result['verified']:
    attestation = result['attestation']  # 'A', 'B', or 'C'
    print(f"Caller ID verified with attestation level: {attestation}")
else:
    print(f"Verification failed: {result['error']}")
```

### Configuration

#### Enable in config.yml

```yaml
features:
  stir_shaken:
    enabled: true
    certificate_path: /etc/pbx/certs/stir_shaken_cert.pem
    private_key_path: /etc/pbx/certs/stir_shaken_key.pem
    ca_cert_path: /etc/pbx/certs/ca-bundle.pem
    
    # Your service provider info
    originating_tn: "+18005551234"
    service_provider_code: "MYSP"
    certificate_url: "https://certs.mysp.com/cert.pem"
    
    # Features
    enable_signing: true          # Sign outgoing calls
    enable_verification: true     # Verify incoming calls
    
    # Default attestation level for outgoing calls
    default_attestation: "A"      # A, B, or C
```

### PASSporT Token Format

A PASSporT token contains:

```json
{
  "header": {
    "alg": "ES256",  # or "RS256"
    "ppt": "shaken",
    "typ": "passport",
    "x5u": "https://certs.mysp.com/cert.pem"
  },
  "payload": {
    "attest": "A",              # Attestation level
    "dest": {
      "tn": ["+13105555678"]    # Destination number
    },
    "iat": 1639584000,          # Issued at timestamp
    "orig": {
      "tn": "+18005551234"      # Originating number
    },
    "origid": "UUID-HERE"       # Unique call identifier
  },
  "signature": "BASE64_SIGNATURE"
}
```

### SIP Integration

#### Identity Header

STIR/SHAKEN adds an `Identity` header to SIP INVITE:

```
INVITE sip:+13105555678@carrier.com SIP/2.0
Identity: eyJhbGc...PASSPORT_TOKEN...;info=<https://certs.mysp.com/cert.pem>;alg=ES256;ppt=shaken
From: <sip:+18005551234@pbx.example.com>
To: <sip:+13105555678@carrier.com>
```

### Certificate Management

#### Production Certificates

For production, obtain certificates from an authorized STIR/SHAKEN Policy Administrator (PA):

1. **STI-PA (ATIS)**: https://www.atis.org/sti-pa/
2. **Register** with your service provider information
3. **Obtain** signing certificate and private key
4. **Install** certificates on PBX server

#### Certificate Rotation

```bash
# Automated certificate renewal
python scripts/renew_stir_shaken_cert.py

# Manual certificate update
cp new_cert.pem /etc/pbx/certs/stir_shaken_cert.pem
cp new_key.pem /etc/pbx/certs/stir_shaken_key.pem
systemctl restart pbx
```

### Testing

```bash
# Test STIR/SHAKEN implementation
python tests/test_stir_shaken.py

# Tests include:
# ✅ PASSporT token creation
# ✅ Signature generation
# ✅ Signature verification
# ✅ Attestation levels
# ✅ Certificate validation
# ✅ SIP Integration
```

### Troubleshooting

#### Signature Verification Fails

**Issue**: Incoming calls fail signature verification

**Solutions**:
1. Verify CA certificate bundle is up to date
2. Check certificate URL is accessible
3. Ensure certificate hasn't expired
4. Validate timestamp synchronization (NTP)

```bash
# Verify certificate
openssl x509 -in /etc/pbx/certs/stir_shaken_cert.pem -text -noout

# Check expiration
openssl x509 -in /etc/pbx/certs/stir_shaken_cert.pem -enddate -noout
```

#### Cannot Sign Outgoing Calls

**Issue**: Outgoing calls not getting signed

**Solutions**:
1. Verify certificate and private key match
2. Check file permissions on private key
3. Ensure `enable_signing: true` in config
4. Verify originating_tn is configured

```bash
# Verify certificate/key match
openssl x509 -modulus -noout -in cert.pem | openssl md5
openssl rsa -modulus -noout -in key.pem | openssl md5
# MD5 hashes should match
```

### Compliance

**FCC Requirements** (USA):
- Voice service providers must implement STIR/SHAKEN
- Required for all IP-based voice traffic
- Effective: June 30, 2021 (large providers), June 30, 2023 (small providers)

**CRTC Requirements** (Canada):
- Similar requirements for Canadian carriers
- Effective: November 30, 2021

---

## SOC 2 Type 2 Compliance

### Overview

This section describes the SOC 2 Type 2 compliance framework implementation in the PBX system.

**Status**: ✅ **FRAMEWORK IMPLEMENTED**

### What is SOC 2 Type 2?

SOC 2 (Service Organization Control 2) Type 2 is an auditing procedure that ensures service providers securely manage data to protect the interests of their organization and the privacy of their clients.

**Type 2 Reports Include**:
- Description of the service organization's system
- Suitability of the design of controls
- Operating effectiveness of controls over a period of time (minimum 6 months)

### Trust Services Criteria

The implementation covers the following Trust Services Criteria:

1. **Security** - Protection against unauthorized access
2. **Availability** - System availability for operation and use
3. **Processing Integrity** - System processing is complete, valid, accurate, timely, and authorized
4. **Confidentiality** - Information designated as confidential is protected

### Implementation Details

#### SOC2ComplianceEngine Class

**Location**: `/pbx/features/compliance_framework.py`

**Key Features**:
- ✅ Automatic control initialization - 16 default controls automatically registered on startup
- ✅ Control registration - Register and update SOC 2 controls
- ✅ Test tracking - Record test results and testing dates
- ✅ Compliance reporting - Generate compliance summaries and statistics
- ✅ Category filtering - Retrieve controls by category

#### Default Controls

**Security (Common Criteria)**:
- **CC1.1** - COSO Principle 1: Integrity and ethical values
- **CC1.2** - COSO Principle 2: Board independence and oversight
- **CC2.1** - COSO Principle 4: Commitment to competence
- **CC3.1** - COSO Principle 6: Suitable objectives
- **CC5.1** - COSO Principle 10: Control activities
- **CC6.1** - Logical and physical access controls
- **CC6.2** - System access authorization and authentication
- **CC6.6** - Encryption of data in transit and at rest
- **CC7.1** - Detection of security incidents
- **CC7.2** - Response to security incidents

**Availability**:
- **A1.1** - System availability and performance monitoring
- **A1.2** - Backup and disaster recovery procedures

**Processing Integrity**:
- **PI1.1** - Data processing quality and integrity controls
- **PI1.2** - System processing accuracy monitoring

**Confidentiality**:
- **C1.1** - Confidential information identification and classification
- **C1.2** - Confidential information disposal procedures

### Database Schema

```sql
CREATE TABLE soc2_controls (
    id INTEGER PRIMARY KEY,
    control_id TEXT NOT NULL,
    control_category TEXT,
    description TEXT,
    implementation_status TEXT,
    last_tested TIMESTAMP,
    test_results TEXT
);
```

### REST API Endpoints

#### Get All Controls

```bash
GET /api/framework/compliance/soc2/controls

# Response:
{
  "controls": [
    {
      "control_id": "CC6.1",
      "control_category": "Security",
      "description": "Logical and physical access controls",
      "implementation_status": "implemented",
      "last_tested": "2024-12-15T10:00:00Z",
      "test_results": "Passed - All access controls verified"
    },
    ...
  ]
}
```

#### Register or Update Control

```bash
POST /api/framework/compliance/soc2/control
Content-Type: application/json

{
  "control_id": "CC6.1",
  "control_category": "Security",
  "description": "Access control implementation",
  "implementation_status": "implemented",
  "test_results": "Passed - 2024-12-15"
}
```

#### Get Controls by Category

```bash
GET /api/framework/compliance/soc2/controls?category=Security
```

#### Generate Compliance Report

```bash
GET /api/framework/compliance/soc2/report

# Response:
{
  "total_controls": 16,
  "implemented": 16,
  "not_implemented": 0,
  "pending": 0,
  "last_audit_date": "2024-12-15",
  "compliance_percentage": 100,
  "categories": {
    "Security": {"total": 10, "implemented": 10},
    "Availability": {"total": 2, "implemented": 2},
    "Processing Integrity": {"total": 2, "implemented": 2},
    "Confidentiality": {"total": 2, "implemented": 2}
  }
}
```

### Usage Example

```python
from pbx.features.compliance_framework import SOC2ComplianceEngine

# Initialize compliance engine
engine = SOC2ComplianceEngine()

# Register a custom control
engine.register_control(
    control_id="CC8.1",
    control_category="Security",
    description="Custom security control",
    implementation_status="implemented"
)

# Update control test results
engine.update_control(
    control_id="CC6.1",
    test_results="Passed - Quarterly audit on 2024-12-15"
)

# Get all controls
controls = engine.get_all_controls()

# Get controls by category
security_controls = engine.get_controls_by_category("Security")

# Generate compliance summary
summary = engine.generate_compliance_summary()
print(f"Compliance: {summary['compliance_percentage']}%")
```

### Compliance Monitoring

#### Automated Testing

```bash
# Run SOC 2 compliance tests
python scripts/test_soc2_compliance.py

# Tests verify:
# ✅ All controls are registered
# ✅ Implementation status is current
# ✅ Test results are documented
# ✅ Periodic testing is performed
```

#### Audit Trail

All control updates are logged:

```
[SOC2] Control CC6.1 registered - Status: implemented
[SOC2] Control CC6.1 tested - Results: Passed
[SOC2] Control CC6.2 updated - Status: implemented
```

### Audit Preparation

#### Generate Audit Package

```bash
# Generate complete audit package
python scripts/generate_soc2_audit_package.py

# Package includes:
# - Control inventory
# - Implementation evidence
# - Test results
# - Change logs
# - Compliance reports
```

#### Evidence Collection

For each control, maintain:
- **Control Description**: What the control does
- **Implementation Evidence**: How it's implemented
- **Test Results**: Proof of effectiveness
- **Change History**: Updates and modifications

### Ongoing Compliance

**Quarterly Tasks**:
- [ ] Review all control statuses
- [ ] Perform control testing
- [ ] Update test results
- [ ] Document any changes

**Annual Tasks**:
- [ ] Full compliance audit
- [ ] Update control descriptions
- [ ] Review and update policies
- [ ] SOC 2 Type 2 examination (if required)

---

## Related Documentation

- **[SECURITY_GUIDE.md](SECURITY_GUIDE.md)** - Security and FIPS compliance
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - REST API reference
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - General troubleshooting

---

**Note**: This consolidated guide replaces the individual regulation and compliance guides:
- E911_PROTECTION_GUIDE.md
- KARIS_LAW_GUIDE.md
- MULTI_SITE_E911_GUIDE.md
- STIR_SHAKEN_GUIDE.md
- SOC2_TYPE2_IMPLEMENTATION.md
