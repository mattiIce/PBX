#!/usr/bin/env python3
"""
Generate self-signed SSL certificate for HTTPS support
For development and testing purposes only
"""
import os
import sys
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from datetime import datetime, timedelta
except ImportError:
    print("Error: 'cryptography' library is required")
    print("Install with: pip install cryptography")
    sys.exit(1)


def generate_self_signed_cert(cert_dir="certs", hostname="localhost", days_valid=365):
    """
    Generate a self-signed SSL certificate
    
    Args:
        cert_dir: Directory to store certificate files
        hostname: Hostname for the certificate
        days_valid: Number of days the certificate is valid
    """
    # Create cert directory if it doesn't exist
    cert_path = Path(cert_dir)
    cert_path.mkdir(exist_ok=True)
    
    print(f"Generating self-signed SSL certificate for {hostname}...")
    print(f"Certificate will be valid for {days_valid} days")
    print()
    
    # Generate private key
    print("1. Generating RSA private key (2048 bits)...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Generate certificate
    print("2. Creating self-signed certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PBX System"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=days_valid)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(hostname),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Write private key to file
    key_file = cert_path / "server.key"
    print(f"3. Writing private key to {key_file}...")
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Set restrictive permissions on private key
    os.chmod(key_file, 0o600)
    
    # Write certificate to file
    cert_file = cert_path / "server.crt"
    print(f"4. Writing certificate to {cert_file}...")
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print()
    print("✓ SSL certificate generated successfully!")
    print()
    print("Certificate files created:")
    print(f"  Private Key:  {key_file}")
    print(f"  Certificate:  {cert_file}")
    print()
    print("⚠️  IMPORTANT:")
    print("  This is a SELF-SIGNED certificate for development/testing only.")
    print("  Browsers will show security warnings.")
    print("  For production, use a certificate from a trusted CA (Let's Encrypt, DigiCert, etc.)")
    print()
    print("To use the certificate, ensure config.yml has:")
    print("  api:")
    print("    ssl:")
    print("      enabled: true")
    print(f"      cert_file: {cert_file}")
    print(f"      key_file: {key_file}")
    print()


if __name__ == "__main__":
    import argparse
    import ipaddress
    
    parser = argparse.ArgumentParser(
        description="Generate self-signed SSL certificate for PBX HTTPS API"
    )
    parser.add_argument(
        "--hostname",
        default="localhost",
        help="Hostname for the certificate (default: localhost)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days certificate is valid (default: 365)"
    )
    parser.add_argument(
        "--cert-dir",
        default="certs",
        help="Directory to store certificate files (default: certs)"
    )
    
    args = parser.parse_args()
    
    try:
        generate_self_signed_cert(
            cert_dir=args.cert_dir,
            hostname=args.hostname,
            days_valid=args.days
        )
    except Exception as e:
        print(f"Error generating certificate: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
