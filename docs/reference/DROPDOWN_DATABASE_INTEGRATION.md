# Dropdown Database Integration Documentation

## Overview
This document explains how the "Add New Phone Device" form dropdowns retrieve data from the PostgreSQL database.

The API layer is implemented as Flask blueprints. The relevant route modules are
`pbx/api/routes/provisioning.py` and `pbx/api/routes/extensions.py`. Authentication is
enforced with the `@require_auth` / `@require_admin` decorators (or a direct
`verify_authentication()` call) from `pbx/api/utils.py`, and JSON responses are produced via
the `send_json()` helper (or Flask's `jsonify()`).

## Database Tables

### 1. Extensions Table
Stores user extensions/phone numbers.

**Schema** (see `extensions` table in `pbx/utils/database.py`, `Database.initialize_schema()`).
The `id` column uses a `{SERIAL}`/`{BOOLEAN_*}` placeholder that is rendered to the correct
dialect (PostgreSQL or SQLite) by `_build_table_sql()`:
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

**Schema** (see `provisioned_devices` table in `pbx/utils/database.py`,
`Database.initialize_schema()`):
```sql
CREATE TABLE IF NOT EXISTS provisioned_devices (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(20) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    extension_number_2 VARCHAR(20),
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    device_type VARCHAR(20) DEFAULT 'phone',
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
Extensions are loaded from the database into the in-memory registry. The
`ExtensionFeature._load_extensions()` method reads every row via `ExtensionDB.get_all()`
(`SELECT * FROM extensions`) and builds the runtime extension objects.

#### API Endpoint (pbx/api/routes/extensions.py)
The `get_extensions()` view backs `GET /api/extensions`. It calls `verify_authentication()`
and returns `401` when no valid token is present. Admins receive every extension; non-admin
users receive only their own extension:
```python
@extensions_bp.route("/api/extensions", methods=["GET"])
def get_extensions() -> tuple[Response, int]:
    """Get extensions."""
    # SECURITY: Require authentication (but not necessarily admin)
    is_authenticated, payload = verify_authentication()
    if not is_authenticated or payload is None:
        return jsonify({"error": "Authentication required"}), 401

    pbx_core = get_pbx_core()
    extensions = pbx_core.extension_registry.get_all()
    is_admin = payload.get("is_admin", False)
    current_extension = payload.get("extension")
    if not is_admin:
        extensions = [e for e in extensions if e.number == current_extension]

    data = [
        {"number": e.number, "name": e.name, "email": e.config.get("email"), ...}
        for e in extensions
    ]
    return send_json(data), 200
```

**API Endpoint**: `GET /api/extensions`
**Authentication**: Required
**Source query**: `SELECT * FROM extensions` (loaded into `extension_registry`)

#### Frontend (admin/js/pages/provisioning.ts)
`loadExtensionsForProvisioning()` fetches `/api/extensions` with `getAuthHeaders()` and fills
the extension `<select>`:
```typescript
async function loadExtensionsForProvisioning(): Promise<void> {
    const API_BASE = getApiBaseUrl();
    const response = await fetch(`${API_BASE}/api/extensions`, {
        headers: getAuthHeaders()  // includes Bearer token
    });
    const extensions: ExtensionEntry[] = await response.json();

    const select = document.getElementById('device-extension') as HTMLSelectElement | null;
    if (!select) return;
    select.innerHTML = '<option value="">Select Extension</option>';
    for (const ext of extensions) {
        const option = document.createElement('option');
        option.value = ext.number;
        option.textContent = `${ext.number} - ${ext.name}`;
        select.appendChild(option);
    }
}
```

**HTML Element**: `<select id="device-extension">`
**Data Source**: PostgreSQL `extensions` table

---

### Vendor Dropdown

#### Backend Loading (pbx/features/phone_provisioning.py)
`PhoneProvisioning.get_supported_vendors()` derives the vendor list from the built-in phone
templates (the keys of `self.templates`); it does not read the database:
```python
def get_supported_vendors(self) -> list:
    """Get list of supported vendors"""
    vendors = set()
    for vendor, _model in self.templates:
        vendors.add(vendor)
    return sorted(vendors)
```

**Note**: Vendors come from built-in phone templates (loaded by `_load_builtin_templates()`),
NOT from the database. This is intentional — templates define supported phone models.

#### API Endpoint (pbx/api/routes/provisioning.py)
`handle_get_provisioning_vendors()` backs `GET /api/provisioning/vendors`. It is protected by
the `@require_auth` decorator and returns both the vendor list and the per-vendor model map:
```python
@provisioning_bp.route("/api/provisioning/vendors", methods=["GET"])
@require_auth
def handle_get_provisioning_vendors() -> Response:
    """Get supported vendors and models."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "phone_provisioning"):
        vendors = pbx_core.phone_provisioning.get_supported_vendors()
        models = pbx_core.phone_provisioning.get_supported_models()
        return send_json({"vendors": vendors, "models": models})
    return send_json({"error": "Phone provisioning not enabled"}, 500)
```

**API Endpoint**: `GET /api/provisioning/vendors`
**Authentication**: Required (`@require_auth`)
**Data Source**: Built-in templates (static configuration)

#### Frontend (admin/js/pages/provisioning.ts)
`loadSupportedVendors()` fetches `/api/provisioning/vendors`, caches the vendor list and model
map in module state, then calls `populateProvisioningFormDropdowns()` to fill the vendor
`<select>`:
```typescript
export async function loadSupportedVendors(): Promise<void> {
    const API_BASE = getApiBaseUrl();
    const response = await fetch(`${API_BASE}/api/provisioning/vendors`, {
        headers: getAuthHeaders()  // authentication required
    });
    const data: VendorsResponse = await response.json();
    supportedVendors = data.vendors || [];
    supportedModels = data.models || {};
    populateProvisioningFormDropdowns();
    populateSupportedVendorsList();
}

function populateProvisioningFormDropdowns(): void {
    const vendorSelect = document.getElementById('device-vendor') as HTMLSelectElement | null;
    if (!vendorSelect) return;
    vendorSelect.innerHTML = '<option value="">Select Vendor</option>';
    for (const v of supportedVendors) {
        const option = document.createElement('option');
        option.value = v;
        option.textContent = v;
        vendorSelect.appendChild(option);
    }
}
```

**HTML Element**: `<select id="device-vendor">`
**Data Source**: Built-in templates

**Supported Vendors** (defined by the built-in templates in `_load_builtin_templates()`):
- yealink
- polycom
- grandstream
- cisco
- zultys

**Note**: This list is defined by the built-in phone templates and may be extended over time.

**Total Models**: 17 built-in phone templates

---

### Model Dropdown

#### Frontend (admin/js/pages/provisioning.ts)
`updateModelOptions()` runs when the vendor dropdown changes. It looks up the models for the
selected vendor from the cached `supportedModels` map and fills the model `<select>`:
```typescript
export function updateModelOptions(): void {
    const vendorSelect = document.getElementById('device-vendor') as HTMLSelectElement | null;
    const modelSelect = document.getElementById('device-model') as HTMLSelectElement | null;
    if (!vendorSelect || !modelSelect) return;

    const vendor = vendorSelect.value;
    modelSelect.innerHTML = '';
    if (!vendor) {
        modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
        return;
    }
    const models = supportedModels[vendor] || supportedModels[vendor.toLowerCase()] || [];
    modelSelect.innerHTML = '<option value="">Select Model</option>';
    for (const m of models) {
        const option = document.createElement('option');
        option.value = m;
        option.textContent = m;
        modelSelect.appendChild(option);
    }
}
```

**HTML Element**: `<select id="device-model">`
**Data Source**: Built-in templates (filtered by selected vendor)
**Trigger**: `onchange` event from the vendor dropdown

---

### Provisioned Devices List

#### Backend Loading (pbx/features/phone_provisioning.py)
On startup, `_load_devices_from_database()` reads `provisioned_devices`
(via the devices DB `list_all()`, i.e. `SELECT * FROM provisioned_devices`) and rebuilds the
in-memory `ProvisioningDevice` objects.

#### API Endpoint (pbx/api/routes/provisioning.py)
`handle_get_provisioning_devices()` backs `GET /api/provisioning/devices`. It is protected by
the `@require_admin` decorator:
```python
@provisioning_bp.route("/api/provisioning/devices", methods=["GET"])
@require_admin
def handle_get_provisioning_devices() -> Response:
    """Get all provisioned devices."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "phone_provisioning"):
        devices = pbx_core.phone_provisioning.get_all_devices()
        return send_json([d.to_dict() for d in devices])
    return send_json({"error": "Phone provisioning not enabled"}, 500)
```

**API Endpoint**: `GET /api/provisioning/devices`
**Authentication**: Required (`@require_admin` — admin only)
**Source query**: `SELECT * FROM provisioned_devices`

---

## Authentication Flow

### Login Process
1. User enters extension number and voicemail PIN in the login form
2. Frontend sends `POST /api/auth/login` with credentials
3. Backend validates credentials against the PostgreSQL `extensions` table
4. Backend returns a session token
5. Frontend stores the token in localStorage as `pbx_token`

### Authenticated API Calls
The frontend attaches the token via `getAuthHeaders()` (imported from `../api/client.ts`):
```typescript
import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';

const response = await fetch(`${API_BASE}/api/extensions`, {
    headers: getAuthHeaders()  // includes: Authorization: Bearer <token>
});
```

On the backend, `verify_authentication()` in `pbx/api/utils.py` extracts the Bearer token and
validates it with the session token manager. The `@require_auth` decorator rejects
unauthenticated requests with `401`; `@require_admin` additionally rejects non-admin tokens
with `403`.

---

## Endpoint Authentication Summary

All provisioning endpoints require authentication. Some require admin privileges:

| Endpoint | Decorator | Access |
|----------|-----------|--------|
| `GET /api/extensions` | `verify_authentication()` | Authenticated (non-admins see only their own extension) |
| `GET /api/provisioning/vendors` | `@require_auth` | Authenticated |
| `GET /api/provisioning/templates` | `@require_auth` | Authenticated |
| `GET /api/provisioning/devices` | `@require_admin` | Admin only |
| `POST /api/provisioning/devices` | `@require_admin` | Admin only |
| `GET /api/provisioning/diagnostics` | `@require_admin` | Admin only |
| `GET /api/provisioning/requests` | `@require_admin` | Admin only |

Because every dropdown-feeding endpoint requires authentication, the dropdowns either all
populate (when the user is authenticated) or all fail consistently (when not), which makes
troubleshooting straightforward.

---

## Device Registration Flow (PostgreSQL Write)

When a user adds a new phone device:

1. **Frontend**: User fills the form and submits it (`add-device-form`)
2. **Frontend**: Sends `POST /api/provisioning/devices` with the device data
3. **Backend API** (`pbx/api/routes/provisioning.py`) — `handle_register_device()` (admin only):
   ```python
   @provisioning_bp.route("/api/provisioning/devices", methods=["POST"])
   @require_admin
   def handle_register_device() -> Response:
       body = get_request_body()
       device = pbx_core.phone_provisioning.register_device(
           body["mac_address"], body["extension_number"],
           body["vendor"], body["model"],
           extension_number_2=body.get("extension_number_2"),
       )
       # Auto-reboots the phone if the extension is currently registered
       return send_json({"success": True, "device": device.to_dict()})
   ```
4. **Backend Provisioning** (`pbx/features/phone_provisioning.py`) — `register_device()` adds the
   device to the in-memory map and persists it via the devices DB.
5. **Database Layer** (`pbx/utils/database.py`) — `add_device()` runs an `INSERT INTO
   provisioned_devices (...)` (or an `UPDATE` if the device already exists).

**Result**: The device is stored in PostgreSQL and reloaded on the next startup.

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

Environment variables should be set in a `.env` file (not committed to git).

---

## Summary

### Data from PostgreSQL Database
1. **Extensions** — loaded from the `extensions` table
2. **Provisioned Devices** — loaded from the `provisioned_devices` table

### Data from Configuration (By Design)
3. **Phone Vendors** — from built-in templates (static)
4. **Phone Models** — from built-in templates (static)

### Security
- All dropdown-feeding API endpoints require authentication (some require admin)
- Bearer session tokens are used for session management
- Passwords are hashed with PBKDF2-HMAC-SHA256 (FIPS 140-2 compliant)
