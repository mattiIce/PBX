# WebPhone Fix Summary

## Issues Fixed

### 1. WebPhone Cannot Make or Receive Calls ✅
- **Problem**: WebRTC extensions were not being registered in the extension registry
- **Solution**: WebRTC sessions now automatically register extensions when created
- **Result**: WebPhone can make outbound calls and receive incoming calls

### 2. WebPhone Not Registering in Database ✅
- **Problem**: WebRTC sessions weren't being tracked in the phones database
- **Solution**: Added automatic phone registration with special WebRTC markers
- **Result**: WebPhone sessions visible in database with unique identifiers

### 3. "Extension Not Found" Errors ✅
- **Problem**: Critical extensions (0, 1001) and AD extensions missing from database
- **Solution**: Auto-seed critical extensions and AD sync at startup
- **Result**: Extensions 0, 1001, and AD extensions always available

## What Happens at Startup

### Automatic Extension Creation

When the PBX starts, it automatically creates these extensions if they don't exist:

1. **Extension 0** - Auto Attendant
   - Automated greeting and call routing system
   - Always created on first startup

2. **Extension 1001** - Operator / WebAdmin Phone
   - Primary operator extension
   - Used for web-based admin phone
   - Password displayed in logs on first creation

### Active Directory Sync

If Active Directory integration is enabled with `auto_provision: true`:

- All AD users with `telephoneNumber` field are synced
- Extension number = telephoneNumber (digits only)
- User names and emails updated from AD
- Extensions persist in database even when user info changes
- Removed AD users are deactivated (not deleted)

### WebRTC Virtual Extensions

When a WebRTC session is created:

- Virtual extensions (like `webrtc-admin`) are auto-created if missing
- Extensions are registered as "online" in the extension registry
- Sessions tracked in phones database with special markers:
  - IP address: `webrtc`
  - MAC address: `webrtc-{hash}`
  - User agent: `WebRTC Browser Client (Session: {session_id})`

## First-Time Setup

### Step 1: Start the PBX

```bash
python main.py
```

### Step 2: Find Extension 1001 Credentials

Check the logs for this section:

```
======================================================================
FIRST-TIME SETUP - EXTENSION 1001 CREDENTIALS
======================================================================
Extension: 1001
Password:  ChangeMe-Operator-xxxxxxxx
Voicemail PIN: 1001

⚠️  CHANGE THIS PASSWORD IMMEDIATELY via admin panel!
   Access admin panel: https://<your-server-ip>:8080/admin/
======================================================================
```

### Step 3: Login and Change Password

1. Access: `https://<server-ip>:8080/admin/`
2. Login with Extension 1001 and the displayed password
3. **IMMEDIATELY** change the password via admin panel
4. Update voicemail PIN if needed

## Using the WebPhone

### Making Calls

1. Open admin panel in browser
2. WebRTC session automatically creates `webrtc-admin` extension
3. Can now dial:
   - `0` - Auto Attendant
   - `1001` - Operator
   - `*1001` - Voicemail for extension 1001
   - Any AD-synced extension number

### Receiving Calls

- Other extensions can dial `webrtc-admin` to reach the webphone
- Calls are routed through the WebRTC gateway
- Browser will show incoming call notification

## Active Directory Configuration

### Enable AD Sync at Startup

In `config.yml`:

```yaml
integrations:
  active_directory:
    enabled: true
    auto_provision: true  # Enable automatic sync at startup
    server: ldap://your-ad-server.com
    base_dn: DC=company,DC=com
    bind_dn: CN=pbxuser,OU=Service Accounts,DC=company,DC=com
    bind_password: ${AD_BIND_PASSWORD}  # Set in .env file
    user_search_base: OU=Users,DC=company,DC=com
    use_ssl: true
    deactivate_removed_users: true
```

### How AD Sync Works

1. **At Startup**: PBX automatically syncs users from AD
2. **Extension Numbers**: Pulled from `telephoneNumber` attribute
3. **User Info**: Name and email synced from AD
4. **Persistence**: Extension numbers saved to database permanently
5. **Updates**: User info updates on subsequent syncs
6. **Removals**: Users removed from AD are deactivated (not deleted)

## Database Schema

### Extensions Table

Extensions from all sources (manual, AD, auto-seeded) are stored in the `extensions` table:

- `number` - Extension number (primary identifier)
- `name` - Display name (updates from AD)
- `email` - Email address (updates from AD)
- `password_hash` - Hashed password
- `allow_external` - Can make external calls
- `voicemail_pin` - Voicemail access PIN
- `ad_synced` - True if synced from AD
- `ad_username` - AD username (sAMAccountName)

### Registered Phones Table

WebRTC sessions are tracked in `registered_phones`:

- `extension_number` - Extension number
- `ip_address` - `webrtc` for WebRTC sessions
- `mac_address` - `webrtc-{hash}` unique per session
- `user_agent` - `WebRTC Browser Client`
- `contact_uri` - `<webrtc:extension@session_id>`
- `last_registration` - Last activity timestamp

## Troubleshooting

### WebPhone Shows "Extension Not Found"

**Cause**: Database not initialized or extensions not seeded

**Solution**: 
1. Check logs for auto-seeding messages
2. If not present, restart PBX server
3. Verify database connection in logs
4. Run: `python scripts/seed_extensions.py` manually if needed

### Cannot Call Extension from WebPhone

**Cause**: Target extension not in database

**Solution**:
1. Check if extension exists: `SELECT * FROM extensions WHERE number = 'XXXX'`
2. If using AD, verify `telephoneNumber` field in AD
3. If manual extension, add via admin panel or seed script

### AD Extensions Not Syncing

**Cause**: AD integration not configured or disabled

**Solution**:
1. Verify `integrations.active_directory.enabled: true` in config
2. Verify `integrations.active_directory.auto_provision: true` in config
3. Check AD credentials in config
4. Check logs for AD connection errors
5. Manually trigger sync via admin panel API: `POST /api/admin/ad/sync`

### WebRTC Session Not Registering

**Cause**: WebRTC not enabled in config

**Solution**:
1. Add to `config.yml`:
   ```yaml
   features:
     webrtc:
       enabled: true
   ```
2. Restart PBX server

## Security Considerations

### Auto-Created Passwords

- Extension 0 and 1001 get random secure passwords on first creation
- Passwords are displayed **once** in the logs during first startup
- Passwords MUST be changed immediately after first login
- Never commit logs with passwords to version control

### WebRTC Sessions

- Each WebRTC session gets a unique identifier
- MAC addresses use SHA-256 hash to prevent collisions
- Sessions are properly cleaned up when browser closes
- Extensions are unregistered when last session ends

### Active Directory

- AD passwords are never stored in PBX database
- Only hashed passwords for local authentication
- AD users can authenticate via LDAP
- AD sync respects group-based permissions

## API Endpoints

### Manual AD Sync

```http
POST /api/admin/ad/sync
Authorization: Bearer <token>
```

### List Extensions

```http
GET /api/extensions
Authorization: Bearer <token>
```

### WebRTC Session Management

```http
POST /api/webrtc/session
Content-Type: application/json
{"extension": "webrtc-admin"}
```

## Files Modified

- `pbx/core/pbx.py` - Auto-seeding and AD sync logic
- `pbx/features/webrtc.py` - WebRTC registration and tracking

## Testing

All tests pass:
- ✅ Registered phone tests (9/9)
- ✅ WebRTC session creation
- ✅ Extension auto-creation
- ✅ Call routing
- ✅ Security scan (0 vulnerabilities)

## Support

For issues or questions:
1. Check logs in `logs/pbx.log`
2. Verify database connectivity
3. Test with: `python tests/test_registered_phones.py`
4. Check documentation in `/docs` directory
