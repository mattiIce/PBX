# License Admin Quick Reference Card

## Admin Credentials (Encrypted)
```
Extension: 9322
Username:  ICE
PIN:       26697647
```
⚠️ This account has exclusive access to license management and uses triple-layer encryption.

## Quick Start

### Web Interface
1. Login to admin panel: `https://your-pbx/admin/`
2. Use Extension 9322 credentials
3. Navigate to: **System** → **License Management**

### Command Line

**Generate a License**:
```bash
python scripts/license_manager.py generate \
  --type professional \
  --org "Customer Name" \
  --days 365 \
  --output license.json
```

**Batch Generate**:
```bash
python scripts/license_manager.py batch-generate examples/batch_licenses.json
```

**Install License**:
```bash
python scripts/license_manager.py install license.json
```

**Check Status**:
```bash
python scripts/license_manager.py status
```

## License Types

| Type | Duration | Extensions | Calls | Key Features |
|------|----------|-----------|-------|--------------|
| Trial | 30 days | 10 | 5 | Basic features |
| Basic | Variable | 50 | 25 | Small business |
| Professional | Variable | 200 | 100 | WebRTC, CRM |
| Enterprise | Variable | ∞ | ∞ | AI, HA, Multi-site |
| Perpetual | Forever | ∞ | ∞ | One-time purchase |
| Custom | Variable | Custom | Custom | Tailored features |

## Common Tasks

### Enable Licensing
```bash
python scripts/license_manager.py enable
```

### Disable Licensing (Open-Source Mode)
```bash
python scripts/license_manager.py disable
```

### Install with Enforcement (Commercial)
```bash
python scripts/license_manager.py install license.json --enforce
```

### Remove License Lock
```bash
python scripts/license_manager.py remove-lock
```

## API Endpoints

### Public (All Users)
- `GET /api/license/status` - View license status
- `GET /api/license/features` - List available features

### Admin Only (Extension 9322)
- `POST /api/license/admin_login` - Authenticate
- `POST /api/license/generate` - Create new license
- `POST /api/license/install` - Install license
- `POST /api/license/revoke` - Remove license
- `POST /api/license/toggle` - Enable/disable licensing

## Batch Config Example

**JSON** (`config.json`):
```json
{
  "licenses": [
    {
      "type": "professional",
      "issued_to": "Customer Name",
      "expiration_days": 365,
      "max_extensions": 100,
      "max_concurrent_calls": 50
    }
  ]
}
```

**Generate**:
```bash
python scripts/license_manager.py batch-generate config.json --output-dir ./licenses
```

## Troubleshooting

**Can't see License Management tab?**
- Verify you're logged in as Extension 9322
- Clear browser cache

**CLI command not found?**
```bash
cd /path/to/PBX
python scripts/license_manager.py --help
```

**Authentication fails?**
- Check Extension: 9322
- Check Username: ICE (case insensitive)
- Check PIN: 26697647
- Review logs: `tail -f logs/pbx.log`

## Documentation

- Full Guide: `LICENSE_ADMIN_INTERFACE.md`
- License Info: `LICENSING_GUIDE.md`
- Implementation: `IMPLEMENTATION_SUMMARY_LICENSE_ADMIN.md`

## Security Notes

✅ Triple-layer encryption (SHA256, PBKDF2, HMAC)  
✅ Constant-time comparison (timing attack prevention)  
✅ Protected system account (cannot be edited/deleted)  
✅ All authentication attempts logged  
✅ Session-based API protection  

## Support

Issues? Check:
1. `LICENSE_ADMIN_INTERFACE.md` - Comprehensive guide
2. `logs/pbx.log` - System logs
3. Verify all dependencies: `pip install -r requirements.txt`
