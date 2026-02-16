#!/usr/bin/env python3
"""
Automated SSL/TLS certificate management with Let's Encrypt.

Handles automatic certificate issuance and renewal for production deployments.
"""

import argparse
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CertificateManager:
    """Manage SSL/TLS certificates with Let's Encrypt."""

    def __init__(
        self,
        domain: str,
        email: str,
        cert_dir: str = "/opt/pbx/ssl",
        webroot: str = "/var/www/html",
        config_file: str = "/opt/pbx/config.yml",
    ):
        """
        Initialize certificate manager.

        Args:
            domain: Domain name for certificate
            email: Email for Let's Encrypt notifications
            cert_dir: Directory to store certificates
            webroot: Webroot directory for HTTP-01 challenge
            config_file: PBX configuration file path
        """
        self.domain = domain
        self.email = email
        self.cert_dir = Path(cert_dir)
        self.webroot = Path(webroot)
        self.config_file = Path(config_file)

        # Certificate paths
        self.cert_path = self.cert_dir / "server.crt"
        self.key_path = self.cert_dir / "server.key"
        self.chain_path = self.cert_dir / "chain.pem"
        self.fullchain_path = self.cert_dir / "fullchain.pem"

        # Let's Encrypt paths
        self.le_live_dir = Path(f"/etc/letsencrypt/live/{domain}")
        self.le_cert = self.le_live_dir / "cert.pem"
        self.le_chain = self.le_live_dir / "chain.pem"
        self.le_fullchain = self.le_live_dir / "fullchain.pem"
        self.le_privkey = self.le_live_dir / "privkey.pem"

    def check_certbot_installed(self) -> bool:
        """
        Check if certbot is installed.

        Returns:
            True if certbot is installed
        """
        try:
            result = subprocess.run(
                ["certbot", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                logger.info(f"Certbot is installed: {result.stdout.strip()}")
                return True
            return False
        except FileNotFoundError:
            return False

    def install_certbot(self) -> bool:
        """
        Install certbot using snap.

        Returns:
            True if installation successful
        """
        logger.info("Installing certbot...")
        try:
            # Install snapd if needed
            subprocess.run(
                ["sudo", "apt-get", "update"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", "snapd"],
                check=True,
                capture_output=True,
            )

            # Install certbot via snap
            subprocess.run(
                ["sudo", "snap", "install", "--classic", "certbot"],
                check=True,
                capture_output=True,
            )

            # Create symlink
            subprocess.run(
                ["sudo", "ln", "-sf", "/snap/bin/certbot", "/usr/bin/certbot"],
                check=True,
                capture_output=True,
            )

            logger.info("Certbot installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install certbot: {e}")
            return False

    def get_certificate_expiry(self) -> datetime | None:
        """
        Get certificate expiration date.

        Returns:
            Certificate expiry datetime or None if no certificate
        """
        if not self.cert_path.exists():
            return None

        try:
            result = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in",
                    str(self.cert_path),
                    "-noout",
                    "-enddate",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse output: notAfter=Jan  1 00:00:00 2025 GMT
            date_str = result.stdout.strip().split("=")[1]
            return datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            logger.error(f"Failed to get certificate expiry: {e}")
            return None

    def is_certificate_valid(self, min_days: int = 30) -> bool:
        """
        Check if certificate is valid and not expiring soon.

        Args:
            min_days: Minimum days before expiry to consider valid

        Returns:
            True if certificate is valid
        """
        if not isinstance(min_days, int) or min_days < 0:
            raise ValueError("min_days must be a positive integer")

        expiry = self.get_certificate_expiry()
        if not expiry:
            return False

        days_remaining = (expiry - datetime.now(UTC)).days
        logger.info(f"Certificate expires in {days_remaining} days")

        return days_remaining >= min_days

    def obtain_certificate(self, staging: bool = False) -> bool:
        """
        Obtain new certificate from Let's Encrypt.

        Args:
            staging: Use Let's Encrypt staging server for testing

        Returns:
            True if certificate obtained successfully
        """
        logger.info(f"Obtaining certificate for {self.domain}...")

        # Ensure webroot exists
        self.webroot.mkdir(parents=True, exist_ok=True)

        # Build certbot command
        cmd = [
            "sudo",
            "certbot",
            "certonly",
            "--webroot",
            "-w",
            str(self.webroot),
            "-d",
            self.domain,
            "--email",
            self.email,
            "--agree-tos",
            "--non-interactive",
        ]

        if staging:
            cmd.append("--staging")
            logger.info("Using Let's Encrypt staging server (for testing)")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Certificate obtained successfully")
            logger.debug(result.stdout)

            # Copy certificates to PBX directory
            return self.copy_certificates()

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to obtain certificate: {e}")
            logger.error(e.stderr)
            return False

    def renew_certificate(self) -> bool:
        """
        Renew existing certificate.

        Returns:
            True if renewal successful
        """
        logger.info("Renewing certificate...")

        try:
            subprocess.run(
                ["sudo", "certbot", "renew", "--quiet"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Certificate renewed successfully")

            # Copy renewed certificates
            return self.copy_certificates()

        except subprocess.CalledProcessError as e:
            if "not yet due for renewal" in e.stderr:
                logger.info("Certificate not yet due for renewal")
                return True
            logger.error(f"Failed to renew certificate: {e}")
            logger.error(e.stderr)
            return False

    def copy_certificates(self) -> bool:
        """
        Copy Let's Encrypt certificates to PBX directory.

        Returns:
            True if copy successful
        """
        logger.info(f"Copying certificates to {self.cert_dir}...")

        # Ensure cert directory exists
        self.cert_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy certificate files
            subprocess.run(
                ["sudo", "cp", str(self.le_cert), str(self.cert_path)],
                check=True,
            )
            subprocess.run(
                ["sudo", "cp", str(self.le_chain), str(self.chain_path)],
                check=True,
            )
            subprocess.run(
                ["sudo", "cp", str(self.le_fullchain), str(self.fullchain_path)],
                check=True,
            )
            subprocess.run(
                ["sudo", "cp", str(self.le_privkey), str(self.key_path)],
                check=True,
            )

            # Set proper permissions
            for path in self.cert_dir.iterdir():
                subprocess.run(
                    ["sudo", "chown", "pbx:pbx", str(path)],
                    check=True,
                )
            subprocess.run(
                ["sudo", "chmod", "644", str(self.cert_path)],
                check=True,
            )
            subprocess.run(
                ["sudo", "chmod", "600", str(self.key_path)],
                check=True,
            )

            logger.info("Certificates copied successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to copy certificates: {e}")
            return False

    def reload_pbx_service(self) -> bool:
        """
        Reload PBX service to use new certificates.

        Returns:
            True if reload successful
        """
        logger.info("Reloading PBX service...")

        try:
            subprocess.run(
                ["sudo", "systemctl", "reload", "pbx"],
                check=True,
                capture_output=True,
            )
            logger.info("PBX service reloaded successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reload PBX service: {e}")
            # Try restart if reload fails
            try:
                subprocess.run(
                    ["sudo", "systemctl", "restart", "pbx"],
                    check=True,
                    capture_output=True,
                )
                logger.info("PBX service restarted successfully")
                return True
            except subprocess.CalledProcessError as e2:
                logger.error(f"Failed to restart PBX service: {e2}")
                return False

    def setup_auto_renewal(self) -> bool:
        """
        Set up automatic certificate renewal with cron.

        Returns:
            True if setup successful
        """
        logger.info("Setting up automatic renewal...")

        # Certbot includes a systemd timer for auto-renewal
        # Just need to verify it's enabled
        try:
            # Check if timer is active
            result = subprocess.run(
                ["sudo", "systemctl", "is-active", "certbot.timer"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout.strip() != "active":
                # Enable and start timer
                subprocess.run(
                    ["sudo", "systemctl", "enable", "certbot.timer"],
                    check=True,
                )
                subprocess.run(
                    ["sudo", "systemctl", "start", "certbot.timer"],
                    check=True,
                )

            logger.info("Auto-renewal is configured")

            # Add renewal hook to reload PBX
            hook_dir = Path("/etc/letsencrypt/renewal-hooks/deploy")
            hook_dir.mkdir(parents=True, exist_ok=True)

            script_path = Path(__file__).resolve()
            hook_script = hook_dir / "reload-pbx.sh"
            with open(hook_script, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("# Reload PBX service after certificate renewal\n")
                f.write(f"python3 {script_path} --reload-only\n")

            subprocess.run(["sudo", "chmod", "+x", str(hook_script)], check=True)

            logger.info("Renewal hook installed")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup auto-renewal: {e}")
            return False

    def check_and_renew(self, min_days: int = 30) -> bool:
        """
        Check certificate and renew if needed.

        Args:
            min_days: Renew if expiring within this many days

        Returns:
            True if certificate is valid (renewed if needed)
        """
        if self.is_certificate_valid(min_days):
            logger.info("Certificate is valid, no renewal needed")
            return True

        logger.info("Certificate expiring soon, renewing...")
        success = self.renew_certificate()

        if success:
            self.reload_pbx_service()

        return success


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage SSL/TLS certificates with Let's Encrypt")
    parser.add_argument("--reload-only", action="store_true", help="Only reload PBX service")

    # Parse args first to check reload-only mode
    args, _remaining = parser.parse_known_args()

    # Handle reload-only mode early (doesn't need domain/email)
    if args.reload_only:
        # Minimal parsing for reload-only
        parser.add_argument(
            "--domain", default="localhost", help="Domain name (not used in reload-only)"
        )
        parser.add_argument(
            "--email", default="admin@localhost", help="Email (not used in reload-only)"
        )
        parser.add_argument("--cert-dir", default="/opt/pbx/ssl", help="Certificate directory")
        parser.add_argument("--webroot", default="/var/www/html", help="Webroot directory")
        args = parser.parse_args()

        manager = CertificateManager(
            domain=args.domain,
            email=args.email,
            cert_dir=args.cert_dir,
            webroot=args.webroot,
        )
        manager.copy_certificates()
        manager.reload_pbx_service()
        return 0

    # Normal mode requires domain and email
    parser.add_argument("--domain", required=True, help="Domain name")
    parser.add_argument("--email", required=True, help="Email for Let's Encrypt notifications")
    parser.add_argument("--cert-dir", default="/opt/pbx/ssl", help="Certificate directory")
    parser.add_argument("--webroot", default="/var/www/html", help="Webroot directory")
    parser.add_argument(
        "--install-certbot",
        action="store_true",
        help="Install certbot if not present",
    )
    parser.add_argument("--obtain", action="store_true", help="Obtain new certificate")
    parser.add_argument("--renew", action="store_true", help="Renew existing certificate")
    parser.add_argument("--check", action="store_true", help="Check and renew if needed")
    parser.add_argument("--setup-auto-renewal", action="store_true", help="Setup automatic renewal")
    parser.add_argument(
        "--staging",
        action="store_true",
        help="Use Let's Encrypt staging server (for testing)",
    )
    parser.add_argument(
        "--min-days", type=int, default=30, help="Minimum days before expiry to renew"
    )

    args = parser.parse_args()

    manager = CertificateManager(
        domain=args.domain,
        email=args.email,
        cert_dir=args.cert_dir,
        webroot=args.webroot,
    )

    # Check if certbot is installed
    if not manager.check_certbot_installed():
        if args.install_certbot:
            if not manager.install_certbot():
                logger.error("Failed to install certbot")
                return 1
        else:
            logger.error("Certbot is not installed. Run with --install-certbot to install it.")
            return 1

    # Perform requested action
    if args.obtain:
        success = manager.obtain_certificate(staging=args.staging)
        if success:
            manager.reload_pbx_service()
        return 0 if success else 1

    if args.renew:
        success = manager.renew_certificate()
        if success:
            manager.reload_pbx_service()
        return 0 if success else 1

    if args.check:
        success = manager.check_and_renew(min_days=args.min_days)
        return 0 if success else 1

    if args.setup_auto_renewal:
        success = manager.setup_auto_renewal()
        return 0 if success else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
