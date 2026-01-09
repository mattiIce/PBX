# TLS 1.3 Support in Warden VoIP PBX

## Overview

The Warden VoIP PBX system now supports **TLS 1.3**, the latest version of the Transport Layer Security protocol. This provides enhanced security, improved performance, and modern cryptographic algorithms for encrypted communications.

## What is TLS 1.3?

TLS 1.3 is the newest version of the TLS protocol, published in August 2018 (RFC 8446). It offers several improvements over TLS 1.2:

- **Enhanced Security**: Removed support for weak cipher suites and algorithms
- **Faster Handshake**: Reduced round trips for connection establishment
- **Forward Secrecy**: All cipher suites provide forward secrecy by default
- **Simplified Protocol**: Removed legacy features and complexity
- **Better Privacy**: Encrypted more of the handshake process

## Components Supporting TLS 1.3

### 1. REST API Server (`pbx/api/rest_api.py`)

The HTTPS API server now supports TLS 1.3 for secure communication:

```python
# Minimum TLS version: 1.2 (for backward compatibility)
# Maximum TLS version: 1.3 (latest supported)
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
# No maximum version set - allows TLS 1.3 negotiation
```

**Benefits**:
- Secure admin interface access
- Protected API endpoints
- Encrypted configuration data

### 2. SIP/TLS Manager (`pbx/utils/tls_support.py`)

The TLS Manager for encrypted SIP signaling (SIPS) supports TLS 1.3:

```python
# Both FIPS and non-FIPS modes support TLS 1.3
tls_manager = TLSManager(cert_file="cert.pem", key_file="key.pem", fips_mode=True)
```

**Benefits**:
- Encrypted SIP signaling
- Secure call setup and teardown
- Protected authentication credentials

## Configuration

### Enabling TLS/HTTPS

TLS 1.3 is automatically enabled when you configure SSL/TLS. No special configuration is needed.

**In `config.yml`**:

```yaml
api:
  ssl:
    enabled: true
    cert_file: certs/server.crt
    key_file: certs/server.key

security:
  enable_tls: true
  tls_cert_file: certs/server.crt
  tls_key_file: certs/server.key
```

### FIPS Mode

When FIPS mode is enabled, TLS 1.3 is still supported with FIPS-approved algorithms:

```yaml
security:
  fips_mode: true
  enforce_fips: true
```

## Cipher Suites

### TLS 1.2 Cipher Suites (Explicit Configuration)

When using TLS 1.2, the following cipher suites are configured:

**FIPS Mode**:
- `ECDHE-RSA-AES256-GCM-SHA384`
- `ECDHE-RSA-AES128-GCM-SHA256`
- `AES256-GCM-SHA384`
- `AES128-GCM-SHA256`

**Non-FIPS Mode**:
- `HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4`

### TLS 1.3 Cipher Suites (Automatic)

TLS 1.3 cipher suites are configured automatically by the protocol. The supported cipher suites include:

- `TLS_AES_256_GCM_SHA384`
- `TLS_AES_128_GCM_SHA256`
- `TLS_CHACHA20_POLY1305_SHA256`

These are all AEAD (Authenticated Encryption with Associated Data) cipher suites that provide both confidentiality and authenticity.

## Security Features

### Disabled Protocols

All insecure protocols are explicitly disabled:

- ✗ SSLv2
- ✗ SSLv3
- ✗ TLS 1.0
- ✗ TLS 1.1
- ✓ TLS 1.2 (minimum)
- ✓ TLS 1.3 (latest)

### Perfect Forward Secrecy

All TLS 1.3 cipher suites provide perfect forward secrecy (PFS), meaning:

- Session keys cannot be derived from long-term keys
- Past communications remain secure even if private keys are compromised
- Each session uses unique ephemeral keys

## Testing

### Running TLS 1.3 Tests

Comprehensive tests are provided to verify TLS 1.3 support:

```bash
python3 tests/test_tls13_support.py
```

**Test Coverage**:
1. ✓ TLS 1.3 Availability - Verifies Python ssl module supports TLS 1.3
2. ✓ TLSManager Support - Tests TLS manager creates TLS 1.3-capable contexts
3. ✓ API Server Support - Tests REST API server supports TLS 1.3
4. ✓ Security Options - Verifies insecure protocols are disabled

### Verifying TLS Version in Production

You can verify the TLS version negotiated by clients using OpenSSL:

```bash
# Test HTTPS API server
openssl s_client -connect localhost:9000 -tls1_3

# Test SIPS (SIP over TLS)
openssl s_client -connect localhost:5061 -tls1_3
```

Look for `Protocol : TLSv1.3` in the output.

## Client Compatibility

### TLS 1.3 Support by Client Type

| Client Type | TLS 1.3 Support | Notes |
|------------|----------------|-------|
| Modern Web Browsers | ✓ Yes | Chrome 70+, Firefox 63+, Safari 12.1+ |
| Python requests | ✓ Yes | Python 3.7+ with OpenSSL 1.1.1+ |
| SIP Phones (Hardware) | Varies | Check manufacturer documentation |
| SIP Softphones | Varies | Most modern clients support TLS 1.3 |
| WebRTC Clients | ✓ Yes | Browser-based clients |

### Backward Compatibility

Don't worry about older clients - the system maintains backward compatibility:

- **TLS 1.2 clients**: Still fully supported
- **TLS 1.3 clients**: Automatically negotiate TLS 1.3
- **Version negotiation**: Handled automatically by the TLS protocol

## Performance Benefits

TLS 1.3 provides performance improvements:

### Faster Connection Establishment

- **TLS 1.2**: 2-RTT (Round Trip Time) handshake
- **TLS 1.3**: 1-RTT handshake (50% faster)
- **TLS 1.3 0-RTT**: Optional 0-RTT for resumed connections (instant)

### Lower CPU Usage

- More efficient cryptographic algorithms
- Simplified handshake process
- Better hardware acceleration support

## Troubleshooting

### Problem: Client Cannot Connect with TLS 1.3

**Solution**: This is likely due to outdated client software.

1. **Check client TLS support**:
   ```bash
   openssl s_client -connect server:port -tls1_3
   ```

2. **Update client software** to a version that supports TLS 1.3

3. **Fallback to TLS 1.2**: The system automatically falls back to TLS 1.2 for older clients

### Problem: Certificate Errors

**Solution**: Ensure your certificate is valid and properly configured.

1. **Generate a new certificate**:
   ```bash
   python scripts/generate_ssl_cert.py
   ```

2. **Verify certificate**:
   ```bash
   openssl x509 -in certs/server.crt -text -noout
   ```

3. **Check certificate chain**:
   ```bash
   openssl verify -CAfile certs/ca.crt certs/server.crt
   ```

### Problem: TLS 1.3 Not Negotiated

**Solution**: Check OpenSSL version and Python version.

1. **Check Python version** (requires 3.7+):
   ```bash
   python3 --version
   ```

2. **Check OpenSSL version** (requires 1.1.1+):
   ```bash
   openssl version
   ```

3. **Verify TLS 1.3 availability**:
   ```python
   import ssl
   print(hasattr(ssl.TLSVersion, 'TLSv1_3'))  # Should print: True
   ```

## Best Practices

### 1. Use Valid Certificates

- Use certificates from a trusted Certificate Authority (CA)
- For internal use, set up an in-house CA
- Regularly renew certificates before expiration
- Use Let's Encrypt for public-facing servers

### 2. Monitor TLS Connections

- Log TLS handshake details
- Monitor for failed TLS connections
- Track TLS version distribution
- Alert on use of deprecated versions

### 3. Keep Software Updated

- Update Python to the latest stable version
- Update OpenSSL to the latest stable version
- Update client software regularly
- Monitor security advisories

### 4. Test Regularly

- Run TLS tests after upgrades
- Verify certificate validity
- Test client compatibility
- Perform security scans

## References

- [RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3](https://datatracker.ietf.org/doc/html/rfc8446)
- [Python ssl Module Documentation](https://docs.python.org/3/library/ssl.html)
- [OpenSSL TLS 1.3 Support](https://www.openssl.org/docs/man1.1.1/man3/SSL_CTX_set_min_proto_version.html)
- [NIST TLS Guidelines](https://csrc.nist.gov/publications/detail/sp/800-52/rev-2/final)

## Support

For issues or questions about TLS 1.3 support:

1. Check the test suite: `python3 tests/test_tls13_support.py`
2. Review the logs in `logs/pbx.log`
3. Consult the troubleshooting section above
4. Open an issue on the GitHub repository

---

**Last Updated**: 2026-01-09  
**Version**: 1.0.0
