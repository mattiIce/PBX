# LDAPS Phone Book Configuration Guide

## Overview

This guide explains how to configure LDAPS (LDAP over SSL) phone book access for IP phones, specifically Zultys ZIP 33G and ZIP 37G models. This feature allows phones to directly query your LDAP/Active Directory server for contact lookups.

## Supported Methods

Two phone book access methods are supported, and both can be used simultaneously for redundancy:

1. **LDAPS (Primary Method)**: Phones directly connect to LDAP server
   - ✅ Works offline (no PBX dependency)
   - ✅ Real-time directory access
   - ✅ Secure SSL/TLS connection
   - ⚠️ Requires LDAP credentials on each phone

2. **Remote Phone Book URL (Fallback Method)**: Phones fetch XML from PBX
   - ✅ No LDAP credentials needed on phones
   - ✅ Simple HTTP/HTTPS access
   - ✅ Works with any XML-capable phone
   - ⚠️ Depends on PBX availability

## Supported Phone Models

- ✅ Zultys ZIP 33G
- ✅ Zultys ZIP 37G
- ✅ Yealink T-Series phones (T46S, etc.)
- ✅ Other LDAP-capable IP phones

## Configuration via Admin Panel

### Method 1: Using the Web UI (Recommended)

1. **Access Admin Panel**
   ```
   http://your-pbx-ip:8080/admin/
   ```

2. **Navigate to Phone Provisioning Tab**
   - Click on "Phone Provisioning" in the navigation menu

3. **Configure LDAPS Phone Book**
   - Check "Enable LDAPS Phone Book"
   - Fill in the following fields:
     - **LDAP Server**: `ldaps://your-ad-server.com` or `ldaps://192.168.1.22`
     - **LDAP Port**: `636` (for LDAPS) or `389` (for plain LDAP)
     - **Base DN**: `DC=company,DC=com`
     - **Bind User (DN)**: `CN=phonebook,CN=Users,DC=company,DC=com`
     - **Bind Password**: Enter password (will be stored in .env file)
     - **Use SSL/TLS**: Check this box (recommended)
     - **Display Name**: `Company Directory`

4. **Configure Remote Phone Book (Optional)**
   - Check "Enable Remote Phone Book URL"
   - URL is automatically generated: `http://your-pbx-ip:8080/api/phone-book/export/xml`
   - Set **Refresh Interval**: `60` minutes (or desired value)

5. **Save Settings**
   - Click "Save Phone Book Settings"
   - Copy the generated configuration snippet
   - Update `config.yml` with the provided settings
   - Restart the PBX server

### Method 2: Manual Configuration

Edit `config.yml`:

```yaml
provisioning:
  enabled: true
  # ... existing provisioning settings ...
  
  # LDAP/LDAPS Phone Book Configuration
  ldap_phonebook:
    enable: 1  # Set to 1 to enable
    server: ldaps://192.168.1.22  # LDAP server address
    port: 636  # 636 for LDAPS (SSL), 389 for plain LDAP
    base: DC=albl,DC=com  # Base DN for directory searches
    user: CN=phonebook,CN=Users,DC=albl,DC=com  # Bind DN
    password: ${LDAP_PHONEBOOK_PASSWORD}  # Set in .env file
    version: 3  # LDAP protocol version
    tls_mode: 1  # 1 for LDAPS/TLS, 0 for plain LDAP
    name_filter: (|(cn=%)(sn=%))  # Search filter for names
    number_filter: (|(telephoneNumber=%)(mobile=%))  # Search filter for numbers
    name_attr: cn  # LDAP attribute for contact name
    number_attr: telephoneNumber  # LDAP attribute for phone number
    display_name: Company Directory  # Display name on phone
  
  # Remote Phone Book URL (Fallback)
  remote_phonebook:
    url: http://192.168.1.14:8080/api/phone-book/export/xml
    refresh_interval: 60  # Refresh interval in minutes
```

Add to `.env` file:
```bash
# LDAP Phone Book credentials
LDAP_PHONEBOOK_PASSWORD=YourSecurePassword
```

## LDAP Server Setup

### Option 1: Using Active Directory

If you're already using Active Directory integration, you can use the same server:

1. **Create a dedicated read-only account** (recommended):
   ```
   Username: phonebook
   Password: SecurePassword123!
   DN: CN=phonebook,CN=Users,DC=company,DC=com
   ```

2. **Grant read permissions** on the directory
   - No write permissions needed
   - Read access to user objects
   - Read access to contact attributes

3. **Configure SSL/TLS** (recommended):
   - Use `ldaps://` protocol
   - Port 636 for LDAPS
   - Ensure valid SSL certificates

### Option 2: Using OpenLDAP

If using OpenLDAP:

```
server: ldaps://ldap.company.com
port: 636
base: ou=people,dc=company,dc=com
user: cn=readonly,dc=company,dc=com
```

## Phone Configuration

After configuring the PBX, phones need to be provisioned:

### Automatic Provisioning (Recommended)

1. **Register the phone** in the admin panel:
   - Go to "Phone Provisioning" → "Provisioned Devices"
   - Click "Add Device"
   - Enter MAC address, extension, vendor (zultys), model (zip33g)

2. **Reboot the phone**:
   - Phone will automatically download configuration
   - LDAPS settings will be included

### Manual Configuration

For testing or manual setup, you can access the phone's web interface:

1. Browse to phone's IP address
2. Navigate to Directory → LDAP settings
3. Enter the LDAP parameters manually

## Testing LDAPS Connection

### Test from PBX Server

```bash
# Test LDAPS connection (requires ldapsearch utility)
ldapsearch -H ldaps://192.168.1.22:636 \
  -D "CN=phonebook,CN=Users,DC=albl,DC=com" \
  -w "YourPassword" \
  -b "DC=albl,DC=com" \
  "(cn=*)" cn telephoneNumber

# If successful, you should see directory entries
```

### Test from Phone

1. Access phone directory
2. Try searching for a name
3. Verify results appear from LDAP

## LDAP Search Filters

### Name Filter
```
(|(cn=%)(sn=%))
```
This searches for contacts where common name (cn) OR surname (sn) matches the user's input.

### Number Filter
```
(|(telephoneNumber=%)(mobile=%))
```
This searches for contacts where telephone number OR mobile number matches.

### Custom Filters

You can customize filters for your organization:

```yaml
# Search only users with non-empty email
name_filter: (&(cn=%)(mail=*))

# Search by display name
name_filter: (displayName=%)

# Combined search
name_filter: (|(cn=%)(displayName=%)(mail=%))
```

## Security Considerations

### Best Practices

1. **Use LDAPS (SSL/TLS)**: Always use `ldaps://` and port 636
2. **Read-Only Account**: Create dedicated account with minimal permissions
3. **Strong Password**: Use complex password for LDAP bind account
4. **Store in .env**: Never commit passwords to version control
5. **Firewall Rules**: Restrict LDAP access to phone network only
6. **Regular Audits**: Monitor LDAP access logs

### Password Security

❌ **Don't do this:**
```yaml
password: MyPassword123  # Hardcoded in config.yml
```

✅ **Do this:**
```yaml
password: ${LDAP_PHONEBOOK_PASSWORD}  # Reference from .env
```

In `.env`:
```bash
LDAP_PHONEBOOK_PASSWORD=SecureRandomPassword123!
```

## Troubleshooting

### LDAPS Not Working

**Issue**: Phones can't connect to LDAP server

**Solutions**:
1. Verify LDAP server is accessible from phone network
2. Test connection with `ldapsearch` command
3. Check firewall allows port 636
4. Verify SSL certificates are valid
5. Try plain LDAP (port 389) for testing only

### No Directory Results

**Issue**: Directory search returns no results

**Solutions**:
1. Verify Base DN is correct
2. Check LDAP bind credentials
3. Test search filter with `ldapsearch`
4. Ensure user objects have required attributes (cn, telephoneNumber)
5. Check LDAP user has read permissions

### Phone Shows "Authentication Failed"

**Issue**: Phone can't authenticate to LDAP

**Solutions**:
1. Verify bind DN format: `CN=user,CN=Users,DC=company,DC=com`
2. Check password is correct
3. Ensure account is not locked or expired
4. Verify account has read permissions

### Remote Phone Book Not Updating

**Issue**: Phone book via URL not refreshing

**Solutions**:
1. Verify PBX phone book API is accessible: `http://pbx-ip:8080/api/phone-book/export/xml`
2. Check phone book has entries (add via admin panel)
3. Ensure phone book feature is enabled in config.yml
4. Verify refresh interval is set correctly

## Advanced Configuration

### Multiple LDAP Servers (Failover)

For high availability, configure multiple LDAP servers:

```yaml
ldap_phonebook:
  server: ldaps://ldap1.company.com,ldaps://ldap2.company.com
  # Phone will try servers in order
```

### Custom Attribute Mapping

If your LDAP schema uses different attributes:

```yaml
ldap_phonebook:
  name_attr: displayName  # Instead of cn
  number_attr: ipPhone  # Instead of telephoneNumber
```

### Performance Tuning

For large directories:

```yaml
ldap_phonebook:
  # Limit search results
  name_filter: (&(cn=%*)(objectClass=person))
  # Add size limit if supported
```

## API Reference

### Phone Book Export Endpoints

These endpoints provide directory data for phones:

```bash
# Yealink XML format
GET http://pbx-ip:8080/api/phone-book/export/xml

# Cisco XML format
GET http://pbx-ip:8080/api/phone-book/export/cisco-xml

# JSON format
GET http://pbx-ip:8080/api/phone-book/export/json
```

### Phone Book Management

```bash
# List all entries
GET http://pbx-ip:8080/api/phone-book

# Add entry
POST http://pbx-ip:8080/api/phone-book
Content-Type: application/json
{
  "extension": "1001",
  "name": "John Doe",
  "email": "john@company.com"
}

# Search entries
GET http://pbx-ip:8080/api/phone-book/search?q=John

# Sync from Active Directory
POST http://pbx-ip:8080/api/phone-book/sync
```

## Related Documentation

- [PHONE_BOOK_GUIDE.md](PHONE_BOOK_GUIDE.md) - Phone book feature overview
- [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md) - Phone provisioning guide
- [AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md) - Active Directory integration
- [PROVISIONING_TEMPLATE_CUSTOMIZATION.md](PROVISIONING_TEMPLATE_CUSTOMIZATION.md) - Template customization

## Support

For issues or questions:
- Check PBX logs: `tail -f logs/pbx.log`
- Review test failures: `cat test_failures.log`
- GitHub Issues: https://github.com/mattiIce/PBX/issues
