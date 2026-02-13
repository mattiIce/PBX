# Dropdown Database Integration Documentation

## Overview
This document explains how the "Add New Phone Device" form dropdowns retrieve data from the PostgreSQL database.

## Database Tables

### 1. Extensions Table
Stores user extensions/phone numbers.

**Schema** (from `pbx/utils/database.py` lines 520-543):
```sql
CREATE TABLE IF NOT EXISTS extensions (
    id SERIAL PRIMARY KEY,
    number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    password_salt VARCHAR(255),
    allow_external BOOLEAN DEFAULT TRUE,
    voicemail_pin_hash VARCHAR(255),
    voicemail_pin_salt VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    ad_synced BOOLEAN DEFAULT FALSE,
    ad_username VARCHAR(100),
    password_changed_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    account_locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### 2. Provisioned Devices Table
Stores phone provisioning configuration.

**Schema** (from `pbx/utils/database.py` lines 503-518):
```sql
CREATE TABLE IF NOT EXISTS provisioned_devices (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(20) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    static_ip VARCHAR(50),
    config_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_provisioned TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Data Flow: PostgreSQL → Backend → API → Frontend

### Extension Dropdown

#### Backend Loading (pbx/features/extensions.py)
```python
def _load_extensions(self):
    """Load extensions from database only (for security)"""
    # Lines 122-142
    from pbx.utils.database import ExtensionDB
    
    ext_db = ExtensionDB(self.database)
    db_extensions = ext_db.get_all()  # SELECT * FROM extensions
    
    for ext_data in db_extensions:
        extension = self.create_extension_from_db(ext_data)
        self.extensions[number] = extension
```

#### API Endpoint (pbx/api/rest_api.py)
```python
def _handle_get_extensions(self):
    """Get extensions."""
    # Lines 1368-1400
    # SECURITY: Require authentication
    is_authenticated, payload = self._verify_authentication()
    if not is_authenticated:
        self._send_json({"error": "Authentication required"}, 401)
        return
    
    extensions = self.pbx_core.extension_registry.get_all()
    data = [
        {
            "number": e.number,
            "name": e.name,
            "email": e.config.get("email"),
            ...
        }
        for e in extensions
    ]
    self._send_json(data)
```

**API Endpoint**: `GET /api/extensions`  
**Authentication**: Required
**PostgreSQL Query**: `SELECT * FROM extensions`

#### Frontend JavaScript (admin/js/admin.js)
```javascript
async function populateProvisioningFormDropdowns() {
    // Lines 2141-2168
    const response = await fetch(`${API_BASE}/api/extensions`, {
        headers: getAuthHeaders()  // Includes Bearer token
    });
    
    const extensions = await response.json();
    extensionSelect.innerHTML = '<option value="">Select Extension</option>';
    
    extensions.forEach(ext => {
        const option = document.createElement('option');
        option.value = ext.number;
        option.textContent = `${ext.number} - ${ext.name}`;
        extensionSelect.appendChild(option);
    });
}
```

**HTML Element**: `<select id="device-extension">`  
**Data Source**: PostgreSQL `extensions` table

---

### Vendor Dropdown

#### Backend Loading (pbx/features/phone_provisioning.py)
```python
def get_supported_vendors(self):
    """Get list of supported vendors"""
    # Lines 1513-1523
    vendors = set()
    for vendor, model in self.templates.keys():
        vendors.add(vendor)
    return sorted(list(vendors))
```

**Note**: Vendors come from built-in phone templates (hardcoded), NOT from database.  
This is intentional - templates define supported phone models.

#### API Endpoint (pbx/api/rest_api.py)
```python
def _handle_get_provisioning_vendors(self):
    """Get supported vendors and models."""
    # Lines 1588-1602
    # SECURITY: Require authentication (NEW - FIXED IN THIS PR)
    is_authenticated, payload = self._verify_authentication()
    if not is_authenticated:
        self._send_json({"error": "Authentication required"}, 401)
        return
    
    vendors = self.pbx_core.phone_provisioning.get_supported_vendors()
    models = self.pbx_core.phone_provisioning.get_supported_models()
    data = {"vendors": vendors, "models": models}
    self._send_json(data)
```

**API Endpoint**: `GET /api/provisioning/vendors`  
**Authentication**: Required (Fixed)
**Data Source**: Built-in templates (static configuration)

#### Frontend JavaScript (admin/js/admin.js)
```javascript
async function loadSupportedVendors() {
    // Lines 2365-2394
    const response = await fetch(`${API_BASE}/api/provisioning/vendors`, {
        headers: getAuthHeaders()  // Authentication required
    });
    const data = await response.json();
    
    supportedVendors = data.vendors || [];
    supportedModels = data.models || {};
    
    // Populate vendor dropdown
    vendorSelect.innerHTML = '<option value="">Select Vendor</option>';
    supportedVendors.forEach(vendor => {
        const option = document.createElement('option');
        option.value = vendor;
        option.textContent = vendor.toUpperCase();
        vendorSelect.appendChild(option);
    });
}
```

**HTML Element**: `<select id="device-vendor">`  
**Data Source**: Built-in templates

**Supported Vendors** (as of latest code in `pbx/features/phone_provisioning.py` lines 259-1017):
- yealink
- polycom
- grandstream
- cisco
- zultys

**Note**: This list is defined by the built-in phone templates loaded in `_load_builtin_templates()` method and may be extended over time.

**Total Models**: 13 built-in phone templates

---

### Model Dropdown

#### Frontend JavaScript (admin/js/admin.js)
```javascript
function updateModelOptions() {
    // Lines 2436-2454
    const vendor = document.getElementById('device-vendor').value;
    const modelSelect = document.getElementById('device-model');
    
    if (!vendor) {
        modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
        return;
    }
    
    const models = supportedModels[vendor] || [];
    modelSelect.innerHTML = '<option value="">Select Model</option>';
    
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model.toUpperCase();
        modelSelect.appendChild(option);
    });
}
```

**HTML Element**: `<select id="device-model">`  
**Data Source**: Built-in templates (filtered by selected vendor)  
**Trigger**: `onchange` event from vendor dropdown

---

### Provisioned Devices List

#### Backend Loading (pbx/features/phone_provisioning.py)
```python
def _load_devices_from_database(self):
    """Load provisioned devices from database into memory"""
    # Lines 229-257
    db_devices = self.devices_db.list_all()  # SELECT * FROM provisioned_devices
    
    for db_device in db_devices:
        device = ProvisioningDevice(
            mac_address=db_device["mac_address"],
            extension_number=db_device["extension_number"],
            vendor=db_device["vendor"],
            model=db_device["model"],
            config_url=db_device.get("config_url"),
        )
        self.devices[device.mac_address] = device
```

#### API Endpoint (pbx/api/rest_api.py)
```python
def _handle_get_provisioning_devices(self):
    """Get all provisioned devices."""
    # Lines 1573-1586
    # SECURITY: Require authentication (NEW - FIXED IN THIS PR)
    is_authenticated, payload = self._verify_authentication()
    if not is_authenticated:
        self._send_json({"error": "Authentication required"}, 401)
        return
    
    devices = self.pbx_core.phone_provisioning.get_all_devices()
    data = [d.to_dict() for d in devices]
    self._send_json(data)
```

**API Endpoint**: `GET /api/provisioning/devices`  
**Authentication**: Required (Fixed)
**PostgreSQL Query**: `SELECT * FROM provisioned_devices`

---

## Authentication Flow

### Login Process
1. User enters extension number and voicemail PIN in login form
2. Frontend sends `POST /api/auth/login` with credentials
3. Backend validates credentials against PostgreSQL `extensions` table
4. Backend returns JWT token
5. Frontend stores token in localStorage as `pbx_token`

### Authenticated API Calls
```javascript
function getAuthHeaders() {
    const token = localStorage.getItem('pbx_token');
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
}
```

All dropdown population API calls include authentication:
```javascript
const response = await fetch(`${API_BASE}/api/extensions`, {
    headers: getAuthHeaders()  // Includes: Authorization: Bearer <token>
});
```

---

## Security Enhancements (This PR)

### Before
- `/api/provisioning/vendors` - No authentication required
- `/api/provisioning/devices` - No authentication required
- `/api/provisioning/templates` - No authentication required
- `/api/provisioning/diagnostics` - No authentication required
- `/api/provisioning/requests` - No authentication required
- `/api/extensions` - Authentication required

**Problem**: Inconsistent authentication caused extension dropdown to fail while vendor dropdown might work, creating confusion.

### After (Fixed)
- `/api/provisioning/vendors` - Authentication required
- `/api/provisioning/devices` - Authentication required
- `/api/provisioning/templates` - Authentication required
- `/api/provisioning/diagnostics` - Authentication required
- `/api/provisioning/requests` - Authentication required
- `/api/extensions` - Authentication required

**Result**: All endpoints now consistently require authentication. Dropdowns will either all work (when authenticated) or all fail (when not authenticated), making troubleshooting easier.

---

## Device Registration Flow (PostgreSQL Write)

When a user adds a new phone device:

1. **Frontend**: User fills form and clicks "Add Device"
2. **Frontend**: Sends `POST /api/provisioning/devices` with device data
3. **Backend API** (pbx/api/rest_api.py):
   ```python
   def _handle_add_provisioning_device(self):
       # Validates authentication
       # Calls pbx_core.phone_provisioning.register_device()
   ```
4. **Backend Provisioning** (pbx/features/phone_provisioning.py):
   ```python
   def register_device(self, mac_address, extension_number, vendor, model):
       # Lines 1068-1135
       device = ProvisioningDevice(mac_address, extension_number, vendor, model)
       self.devices[device.mac_address] = device
       
       # Save to PostgreSQL database
       if self.devices_db:
           self.devices_db.add_device(
               mac_address=device.mac_address,
               extension_number=extension_number,
               vendor=vendor,
               model=model,
               config_url=config_url,
           )
   ```
5. **Database Layer** (pbx/utils/database.py):
   ```python
   def add_device(self, mac_address, extension_number, vendor, model, ...):
       # Lines 1674-1746
       query = """
       INSERT INTO provisioned_devices
       (mac_address, extension_number, vendor, model, static_ip, config_url,
        created_at, updated_at)
       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
       """
       # Or UPDATE if device already exists
   ```

**Result**: Device is stored in PostgreSQL and loaded on next startup

---

## Database Connection Configuration

From `config.yml`:
```yaml
database:
  type: postgresql  # Using PostgreSQL
  host: ${DB_HOST}  # From environment variable
  port: ${DB_PORT}  # From environment variable (default: 5432)
  name: ${DB_NAME}  # From environment variable (default: pbx_system)
  user: ${DB_USER}  # From environment variable (default: pbx_user)
  password: ${DB_PASSWORD}  # From environment variable (REQUIRED)
```

Environment variables should be set in `.env` file (not committed to git).

---

## Summary

### Data from PostgreSQL Database
1. **Extensions** - Loaded from `extensions` table
2. **Provisioned Devices** - Loaded from `provisioned_devices` table

### Data from Configuration (By Design)
3. **Phone Vendors** - From built-in templates (static)
4. **Phone Models** - From built-in templates (static)

### Security
- All API endpoints require authentication
- JWT tokens used for session management
- Passwords hashed with PBKDF2-HMAC-SHA256 (FIPS 140-2 compliant)

### Issue Resolution
The dropdowns were failing because provisioning endpoints didn't require authentication, causing inconsistent behavior. This PR fixes that by requiring authentication on all provisioning endpoints, ensuring all dropdowns work consistently when the user is properly authenticated.
