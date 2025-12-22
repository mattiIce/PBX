#!/usr/bin/env python3
"""
Request SSL certificate from in-house CA
Generates a CSR and submits it to the CA for signing
"""
import argparse
import os
import sys
from pathlib import Path

try:
    import requests
    import yaml
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError as e:
    print(f"Error: Required library not available: {e}")
    print("Install with: pip install requests cryptography pyyaml")
    sys.exit(1)


def request_certificate_from_ca(ca_server, ca_endpoint, hostname, cert_dir="certs", ca_cert=None):
    """
    Request certificate from in-house CA

    Args:
        ca_server: URL of the CA server (e.g., https://ca.example.com)
        ca_endpoint: API endpoint for certificate signing (e.g., /api/sign-cert)
        hostname: Hostname for the certificate
        cert_dir: Directory to store certificate files
        ca_cert: Path to CA certificate for verification (optional)

    Returns:
        True if successful
    """
    cert_path = Path(cert_dir)
    cert_path.mkdir(exist_ok=True)

    cert_file = cert_path / "server.crt"
    key_file = cert_path / "server.key"

    print(f"Requesting certificate for hostname: {hostname}")
    print(f"CA Server: {ca_server}")
    print()

    # Check if we already have a private key
    if key_file.exists():
        print(f"Using existing private key: {key_file}")
        with open(key_file, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    else:
        print("1. Generating RSA private key (2048 bits)...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Save private key
        with open(key_file, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # Set restrictive permissions
        os.chmod(key_file, 0o600)
        print(f"   Private key saved to: {key_file}")

    # Generate CSR
    print("2. Generating Certificate Signing Request (CSR)...")
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PBX System"),
                    x509.NameAttribute(NameOID.COMMON_NAME, hostname),
                ]
            )
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(hostname),
                    x509.DNSName("localhost"),
                ]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    # Save CSR for reference
    csr_file = cert_path / "server.csr"
    with open(csr_file, "w") as f:
        f.write(csr_pem)
    print(f"   CSR saved to: {csr_file}")

    # Submit CSR to CA
    print(f"3. Submitting CSR to CA: {ca_server}{ca_endpoint}")

    try:
        verify = ca_cert if ca_cert and os.path.exists(ca_cert) else True

        response = requests.post(
            f"{ca_server}{ca_endpoint}",
            json={
                "csr": csr_pem,
                "hostname": hostname,  # hostname serves as common_name in the CSR
            },
            timeout=30,
            verify=verify,
        )

        if response.status_code != 200:
            print(f"   ✗ CA server returned error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

        # Parse response
        cert_data = response.json()
        signed_cert = cert_data.get("certificate")

        if not signed_cert:
            print("   ✗ CA did not return a signed certificate")
            return False

        # Save certificate
        with open(cert_file, "w") as f:
            f.write(signed_cert)
        print(f"   ✓ Certificate saved to: {cert_file}")

        # Save CA certificate if returned
        ca_cert_data = cert_data.get("ca_certificate")
        if ca_cert_data:
            ca_cert_file = cert_path / "ca.crt"
            with open(ca_cert_file, "w") as f:
                f.write(ca_cert_data)
            print(f"   ✓ CA certificate saved to: {ca_cert_file}")

        print()
        print("✓ Certificate successfully obtained from in-house CA!")
        print()
        print("Certificate files:")
        print(f"  Certificate:  {cert_file}")
        print(f"  Private Key:  {key_file}")
        print(f"  CSR:          {csr_file}")
        if ca_cert_data:
            print(f"  CA Cert:      {ca_cert_file}")
        print()
        print("Update config.yml with:")
        print("  api:")
        print("    ssl:")
        print("      enabled: true")
        print(f"      cert_file: {cert_file}")
        print(f"      key_file: {key_file}")
        print()

        return True

    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error communicating with CA: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def load_ca_config_from_yml(config_file="config.yml"):
    """Load CA configuration from config.yml"""
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        ssl_config = config.get("api", {}).get("ssl", {})
        ca_config = ssl_config.get("ca", {})

        return {
            "server_url": ca_config.get("server_url"),
            "endpoint": ca_config.get("request_endpoint", "/api/sign-cert"),
            "ca_cert": ca_config.get("ca_cert"),
            "cert_dir": os.path.dirname(ssl_config.get("cert_file", "certs/server.crt")) or "certs",
        }
    except Exception as e:
        print(f"Warning: Could not load CA config from {config_file}: {e}")
        return {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Request SSL certificate from in-house CA")
    parser.add_argument("--ca-server", help="URL of the CA server (e.g., https://ca.example.com)")
    parser.add_argument(
        "--ca-endpoint",
        default="/api/sign-cert",
        help="CA API endpoint for certificate signing (default: /api/sign-cert)",
    )
    parser.add_argument(
        "--hostname",
        help="Hostname for the certificate (default: from config.yml server.external_ip or localhost)",
    )
    parser.add_argument(
        "--cert-dir", default="certs", help="Directory to store certificate files (default: certs)"
    )
    parser.add_argument("--ca-cert", help="Path to CA certificate for verification (optional)")
    parser.add_argument(
        "--config", default="config.yml", help="Path to config.yml (default: config.yml)"
    )

    args = parser.parse_args()

    # Try to load config from config.yml
    yml_config = load_ca_config_from_yml(args.config)

    # Use command line args if provided, otherwise fall back to config.yml
    ca_server = args.ca_server or yml_config.get("server_url")
    ca_endpoint = args.ca_endpoint or yml_config.get("endpoint", "/api/sign-cert")
    ca_cert = args.ca_cert or yml_config.get("ca_cert")
    cert_dir = args.cert_dir or yml_config.get("cert_dir", "certs")

    # Determine hostname
    hostname = args.hostname
    if not hostname:
        # Try to load from config.yml
        try:
            with open(args.config, "r") as f:
                config = yaml.safe_load(f)
            hostname = config.get("server", {}).get("external_ip", "localhost")
        except:
            hostname = "localhost"

    if not ca_server:
        print("Error: CA server URL is required")
        print()
        print("Options:")
        print("  1. Provide via command line: --ca-server https://ca.example.com")
        print("  2. Configure in config.yml:")
        print("     api:")
        print("       ssl:")
        print("         ca:")
        print("           enabled: true")
        print("           server_url: https://ca.example.com")
        sys.exit(1)

    try:
        success = request_certificate_from_ca(
            ca_server=ca_server,
            ca_endpoint=ca_endpoint,
            hostname=hostname,
            cert_dir=cert_dir,
            ca_cert=ca_cert,
        )

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
