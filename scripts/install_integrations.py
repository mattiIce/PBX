#!/usr/bin/env python3
"""
Automatic Integration Installation Script

This script automatically installs and configures required services:
- Jitsi Meet (video conferencing)
- Matrix Synapse (team messaging)
- EspoCRM (customer relationship management)

It handles dependencies, SSL certificates, and basic configuration.
"""

import argparse
import os
import platform
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path


class IntegrationInstaller:
    """Automated installer for PBX integrations"""

    def __init__(self, verbose: bool = False, dry_run: bool = False) -> None:
        self.verbose = verbose
        self.dry_run = dry_run
        self.base_path = Path(__file__).parent.parent
        self.is_root = os.geteuid() == 0 if hasattr(os, "geteuid") else False

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message."""
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️ ",
            "STEP": "🔧",
        }.get(level, "")
        print(f"{prefix} {message}")

    def run_command(self, cmd: list[str] | str, check: bool = True, capture: bool = False, show_output: bool = True) -> bool | str:
        """
        Run a command safely using subprocess without shell=True.

        Args:
            cmd: Command as a list (e.g., ['apt-get', 'update']) or string for shell commands
            check: Whether to check return code
            capture: Whether to capture output (returns output instead of displaying it)
            show_output: Whether to show output in real-time (ignored if capture=True)

        Returns:
            True/output if successful, False if failed
        """
        # Determine if this is a list-based command (safe) or shell command (for trusted inputs only)
        if isinstance(cmd, list):
            cmd_str = " ".join(cmd)
            use_shell = False
        else:
            cmd_str = cmd
            use_shell = True

        if self.verbose or self.dry_run:
            self.log(f"Running: {cmd_str}", "STEP")

        if self.dry_run:
            return True

        try:
            if capture:
                result = subprocess.run(
                    cmd, shell=use_shell, check=check, capture_output=True, text=True
                )
                return result.stdout.strip()
            # Let output flow to terminal in real-time
            subprocess.run(cmd, shell=use_shell, check=check)
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {cmd_str}", "ERROR")
            if self.verbose:
                self.log(f"Error: {e}", "ERROR")
            return False

    def run_shell_command(self, cmd: str, check: bool = True, capture: bool = False, show_output: bool = True) -> bool | str:
        """
        Run a shell command that requires pipes/redirections (trusted input only).
        This is kept separate to clearly mark which commands need shell=True.

        Args:
            cmd: Shell command string
            check: Whether to check return code
            capture: Whether to capture output
            show_output: Whether to show output in real-time (ignored if capture=True)
        """
        if self.verbose or self.dry_run:
            self.log(f"Running shell command: {cmd}", "STEP")

        if self.dry_run:
            return True

        try:
            if capture:
                result = subprocess.run(
                    cmd, shell=True, check=check, capture_output=True, text=True
                )
                return result.stdout.strip()
            # Let output flow to terminal in real-time
            subprocess.run(cmd, shell=True, check=check)
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {cmd}", "ERROR")
            if self.verbose:
                self.log(f"Error: {e}", "ERROR")
            return False

    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists using Python's shutil.which for cross-platform compatibility."""
        result = shutil.which(command)
        return result is not None

    def detect_os(self) -> str:
        """Detect the operating system."""
        system = platform.system().lower()
        if system == "linux":
            # Try to detect specific distro
            if Path("/etc/debian_version").exists():
                return "debian"
            if Path("/etc/redhat-release").exists():
                return "redhat"
        return system

    def check_prerequisites(self) -> bool:
        """Check if system meets prerequisites."""
        self.log("Checking prerequisites...", "STEP")

        # Check if running as root
        if not self.is_root and not self.dry_run:
            self.log("This script needs to be run as root (use sudo)", "ERROR")
            return False

        # Check OS
        os_type = self.detect_os()
        if os_type not in ["debian", "ubuntu", "linux"]:
            self.log(f"Unsupported OS: {os_type}. This script supports Debian/Ubuntu.", "WARNING")
            proceed = input("Continue anyway? [y/N]: ").strip().lower()
            if proceed != "y":
                return False

        self.log("Prerequisites check passed", "SUCCESS")
        return True

    def install_ssl_certificates(self) -> bool:
        """Install SSL certificates for localhost."""
        self.log("Setting up SSL certificates...", "STEP")

        cert_dir = self.base_path / "certs"
        cert_file = cert_dir / "server.crt"
        key_file = cert_dir / "server.key"

        # Check if certificates already exist
        if cert_file.exists() and key_file.exists():
            self.log("SSL certificates already exist", "INFO")
            return True

        # Create certs directory
        cert_dir.mkdir(exist_ok=True)

        # Generate self-signed certificate using subprocess for security
        self.log("Generating self-signed SSL certificate...", "STEP")

        try:
            if not self.dry_run:
                subprocess.run(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:4096",
                        "-nodes",
                        "-keyout",
                        str(key_file),
                        "-out",
                        str(cert_file),
                        "-days",
                        "365",
                        "-subj",
                        "/C=US/ST=State/L=City/O=Organization/CN=localhost",
                        "-addext",
                        "subjectAltName=DNS:localhost,IP:127.0.0.1",
                    ],
                    check=True,
                )

            self.log("SSL certificates generated successfully", "SUCCESS")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to generate SSL certificates: {e}", "ERROR")
            return False

    def install_jitsi(self) -> bool:
        """Install Jitsi Meet."""
        self.log("Installing Jitsi Meet...", "STEP")

        # Check if already installed
        if self.check_command_exists("jitsi-meet"):
            self.log("Jitsi Meet is already installed", "INFO")
            return True

        os_type = self.detect_os()

        if os_type in ["debian", "ubuntu"]:
            # Add Jitsi repository
            self.log("Adding Jitsi repository...", "STEP")
            # These commands use pipes/redirections so they need shell=True (trusted, fixed strings)
            shell_commands = [
                "curl -sL https://download.jitsi.org/jitsi-key.gpg.key | gpg --dearmor | tee /usr/share/keyrings/jitsi-keyring.gpg > /dev/null",
                'echo "deb [signed-by=/usr/share/keyrings/jitsi-keyring.gpg] https://download.jitsi.org stable/" | tee /etc/apt/sources.list.d/jitsi-stable.list',
            ]

            for cmd in shell_commands:
                if not self.run_shell_command(cmd):
                    self.log("Failed to add Jitsi repository", "ERROR")
                    return False

            # Safe command without shell injection
            if not self.run_command(["apt-get", "update"]):
                self.log("Failed to update package lists", "ERROR")
                return False

            # Install Jitsi
            self.log("Installing Jitsi Meet package...", "STEP")
            # Use debconf to pre-seed configuration (these use pipes, so need shell)
            preseed_cmds = [
                'echo "jitsi-meet jitsi-meet/jvb-hostname string localhost" | debconf-set-selections',
                'echo "jitsi-meet-web-config jitsi-meet/cert-choice select Generate a new self-signed certificate" | debconf-set-selections',
            ]

            for cmd in preseed_cmds:
                self.run_shell_command(cmd)

            # Safe command execution with environment variable
            env = os.environ.copy()
            env["DEBIAN_FRONTEND"] = "noninteractive"
            try:
                if not self.dry_run:
                    subprocess.run(["apt-get", "install", "-y", "jitsi-meet"], env=env, check=True)
                self.log("Jitsi Meet installed successfully", "SUCCESS")
                return True
            except subprocess.CalledProcessError:
                self.log("Failed to install Jitsi Meet", "ERROR")
                return False
        else:
            self.log("Automatic Jitsi installation only supported on Debian/Ubuntu", "ERROR")
            self.log(
                "Please install manually: https://jitsi.github.io/handbook/docs/devops-guide/devops-guide-quickstart",
                "INFO",
            )
            return False

    def install_matrix_synapse(self) -> bool:
        """Install Matrix Synapse."""
        self.log("Installing Matrix Synapse...", "STEP")

        # Check if already installed
        if self.check_command_exists("synapse_homeserver"):
            self.log("Matrix Synapse is already installed", "INFO")
            return True

        os_type = self.detect_os()

        if os_type in ["debian", "ubuntu"]:
            # Add Matrix repository
            self.log("Adding Matrix repository...", "STEP")

            # Install dependencies first (safe)
            if not self.run_command(["apt-get", "install", "-y", "wget", "apt-transport-https"]):
                self.log("Failed to install dependencies", "ERROR")
                return False

            # Download keyring (safe)
            if not self.run_command(
                [
                    "wget",
                    "-O",
                    "/usr/share/keyrings/matrix-org-archive-keyring.gpg",
                    "https://packages.matrix.org/debian/matrix-org-archive-keyring.gpg",
                ]
            ):
                self.log("Failed to download Matrix keyring", "ERROR")
                return False

            # Add repository (needs shell for command substitution)
            if not self.run_shell_command(
                'echo "deb [signed-by=/usr/share/keyrings/matrix-org-archive-keyring.gpg] https://packages.matrix.org/debian/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/matrix-org.list'
            ):
                self.log("Failed to add Matrix repository", "ERROR")
                return False

            # Update package lists (safe)
            if not self.run_command(["apt-get", "update"]):
                self.log("Failed to update package lists", "ERROR")
                return False

            # Install Matrix Synapse
            self.log("Installing Matrix Synapse package...", "STEP")
            if self.run_command(["apt-get", "install", "-y", "matrix-synapse-py3"]):
                self.log("Matrix Synapse installed successfully", "SUCCESS")

                # Configure Synapse
                self.log("Configuring Matrix Synapse...", "STEP")
                config_path = "/etc/matrix-synapse/homeserver.yaml"

                # Enable registration (for creating bot account) - safe subprocess call
                if Path(config_path).exists():
                    try:
                        if not self.dry_run:
                            subprocess.run(
                                [
                                    "sed",
                                    "-i",
                                    "s/enable_registration: false/enable_registration: true/",
                                    config_path,
                                ],
                                check=True,
                            )
                            subprocess.run(["systemctl", "restart", "matrix-synapse"], check=True)
                    except subprocess.CalledProcessError as e:
                        self.log(f"Failed to configure Matrix: {e}", "WARNING")

                return True
            self.log("Failed to install Matrix Synapse", "ERROR")
            return False
        self.log("Automatic Matrix installation only supported on Debian/Ubuntu", "ERROR")
        self.log(
            "Please install manually: https://matrix-org.github.io/synapse/latest/setup/installation.html",
            "INFO",
        )
        return False

    def install_espocrm(self) -> bool:
        """Install EspoCRM."""
        self.log("Installing EspoCRM...", "STEP")

        # Check if already installed
        espocrm_dir = Path("/var/www/html/espocrm")
        if espocrm_dir.exists():
            self.log("EspoCRM appears to be already installed", "INFO")
            return True

        os_type = self.detect_os()

        if os_type in ["debian", "ubuntu"]:
            # Install prerequisites
            self.log("Installing LAMP stack prerequisites...", "STEP")
            # Use safe subprocess calls
            if not self.run_command(
                ["apt-get", "install", "-y", "apache2", "mysql-server", "php", "libapache2-mod-php"]
            ):
                self.log("Failed to install LAMP stack", "ERROR")
                return False

            if not self.run_command(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "php-mysql",
                    "php-json",
                    "php-gd",
                    "php-zip",
                    "php-mbstring",
                    "php-xml",
                    "php-curl",
                    "php-ldap",
                ]
            ):
                self.log("Failed to install PHP modules", "ERROR")
                return False

            # Download and extract EspoCRM
            self.log("Downloading EspoCRM...", "STEP")
            espocrm_version = "7.5.5"  # Latest stable version
            espocrm_url = f"https://www.espocrm.com/downloads/EspoCRM-{espocrm_version}.zip"
            espocrm_zip = "/tmp/espocrm.zip"

            # Download file (show progress)
            try:
                if not self.dry_run:
                    self.log(f"Downloading from {espocrm_url}...", "STEP")
                    subprocess.run(["wget", "-O", espocrm_zip, espocrm_url], check=True)
            except subprocess.CalledProcessError:
                self.log("Failed to download EspoCRM", "ERROR")
                return False

            # Verify download (basic size check)
            if (
                not self.dry_run and Path(espocrm_zip).stat().st_size < 1000000
            ):  # Less than 1MB is suspicious
                self.log("Downloaded file appears corrupted (too small)", "ERROR")
                return False

            # Extract and set permissions
            commands = [
                (["mkdir", "-p", "/var/www/html/espocrm"], "Creating EspoCRM directory"),
                (["unzip", espocrm_zip, "-d", "/var/www/html/espocrm"], "Extracting EspoCRM files"),
                (
                    ["chown", "-R", "www-data:www-data", "/var/www/html/espocrm"],
                    "Setting file ownership",
                ),
                (["chmod", "-R", "755", "/var/www/html/espocrm"], "Setting file permissions"),
            ]

            for cmd, desc in commands:
                try:
                    self.log(desc, "STEP")
                    if not self.dry_run:
                        subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    self.log(f"Failed: {desc} - {e}", "ERROR")
                    return False

            # Configure Apache
            self.log("Configuring Apache for EspoCRM...", "STEP")
            apache_config = """<VirtualHost *:80>
    ServerName localhost
    DocumentRoot /var/www/html/espocrm

    <Directory /var/www/html/espocrm>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/espocrm_error.log
    CustomLog ${APACHE_LOG_DIR}/espocrm_access.log combined
</VirtualHost>
"""

            config_file = Path("/etc/apache2/sites-available/espocrm.conf")
            if not self.dry_run:
                config_file.write_text(apache_config)

            # Use safe subprocess calls for Apache configuration
            try:
                if not self.dry_run:
                    self.log("Enabling EspoCRM site...", "STEP")
                    subprocess.run(["a2ensite", "espocrm"], check=True)
                    self.log("Enabling Apache rewrite module...", "STEP")
                    subprocess.run(["a2enmod", "rewrite"], check=True)
                    self.log("Restarting Apache...", "STEP")
                    subprocess.run(["systemctl", "restart", "apache2"], check=True)
            except subprocess.CalledProcessError as e:
                self.log(f"Failed to configure Apache: {e}", "ERROR")
                return False

            # Setup MySQL database with random password
            # Generate random password for security
            alphabet = string.ascii_letters + string.digits
            db_password = "".join(secrets.choice(alphabet) for _ in range(16))

            # Store password in a secure location
            password_file = self.base_path / "certs" / "espocrm_db_password.txt"
            if not self.dry_run:
                # Ensure certs directory exists
                password_file.parent.mkdir(exist_ok=True)
                password_file.write_text(db_password)
                os.chmod(password_file, 0o600)  # Read/write for owner only

            # Setup MySQL database
            self.log("Setting up MySQL database...", "STEP")

            if self.dry_run:
                # In dry-run mode, skip actual database setup
                pass
            else:
                # Use NamedTemporaryFile with delete=False (required so files persist for mysql to read)
                # We manually clean up in the finally block
                mysql_config_path = None
                mysql_sql_path = None
                try:
                    # Create config file
                    with tempfile.NamedTemporaryFile(
                        mode="w", prefix="mysql_", suffix=".cnf", delete=False
                    ) as config_file:
                        config_file.write("[client]\n")
                        config_file.write("user=root\n")
                        mysql_config_path = config_file.name
                    os.chmod(mysql_config_path, 0o600)

                    # Escape password for SQL
                    # Note: For production use, strongly consider using MySQL connector library
                    # with parameterized queries instead of string escaping
                    # This escaping handles single quotes for basic SQL injection prevention
                    # but is not comprehensive for all MySQL special characters
                    escaped_password = db_password.replace("\\", "\\\\").replace("'", "''")

                    # Create SQL file (with delete=False since mysql needs to read it)
                    # Security note: Cleanup is critical - handled in finally block
                    with tempfile.NamedTemporaryFile(
                        mode="w", prefix="mysql_", suffix=".sql", delete=False
                    ) as sql_file:
                        sql_file.write(
                            "CREATE DATABASE IF NOT EXISTS espocrm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
                        )
                        # Use escaped password to prevent SQL injection
                        sql_file.write(
                            f"CREATE USER IF NOT EXISTS 'espocrm_user'@'localhost' IDENTIFIED BY '{escaped_password}';\n"
                        )
                        sql_file.write(
                            "GRANT ALL PRIVILEGES ON espocrm.* TO 'espocrm_user'@'localhost';\n"
                        )
                        sql_file.write("FLUSH PRIVILEGES;\n")
                        mysql_sql_path = sql_file.name
                    os.chmod(mysql_sql_path, 0o600)

                    # Execute SQL file - password is in file, not command line or process args
                    self.log("Setting up database and user with secure password...", "STEP")
                    with open(mysql_sql_path) as sql_input:
                        subprocess.run(
                            ["mysql", f"--defaults-file={mysql_config_path}"],
                            stdin=sql_input,
                            check=True,
                        )
                except subprocess.CalledProcessError as e:
                    self.log(f"Failed to setup MySQL database: {e!s}", "ERROR")
                    return False
                finally:
                    # Critical cleanup: Remove temp files containing sensitive data
                    # This must succeed to prevent password leakage
                    cleanup_errors = []
                    for temp_file in [mysql_config_path, mysql_sql_path]:
                        try:
                            if temp_file and Path(temp_file).exists():
                                Path(temp_file).unlink()
                        except OSError as e:
                            cleanup_errors.append(f"{temp_file}: {e}")

                    if cleanup_errors:
                        self.log(
                            "WARNING: Failed to cleanup temporary files with sensitive data:",
                            "WARNING",
                        )
                        for error in cleanup_errors:
                            self.log(f"  {error}", "WARNING")
                        self.log("Please manually delete these files for security", "WARNING")

            self.log("EspoCRM installed successfully", "SUCCESS")
            self.log("Complete setup at: http://localhost/espocrm", "INFO")
            self.log("Database: espocrm, User: espocrm_user", "INFO")
            self.log(f"Password stored in: {password_file}", "INFO")
            self.log(
                "⚠️  SECURITY: Keep this password file secure and delete after setup", "WARNING"
            )

            return True
        self.log("Automatic EspoCRM installation only supported on Debian/Ubuntu", "ERROR")
        self.log(
            "Please install manually: https://docs.espocrm.com/administration/installation/",
            "INFO",
        )
        return False

    def install_all(self) -> bool:
        """Install all integrations."""
        self.log("=" * 60, "INFO")
        self.log("PBX Integration Auto-Installer", "INFO")
        self.log("=" * 60, "INFO")

        if not self.check_prerequisites():
            return False

        # Install SSL certificates first
        if not self.install_ssl_certificates():
            self.log("SSL certificate setup failed, continuing anyway...", "WARNING")

        # Track installation results
        results = {}

        # Install Jitsi
        results["jitsi"] = self.install_jitsi()

        # Install Matrix Synapse
        results["matrix"] = self.install_matrix_synapse()

        # Install EspoCRM
        results["espocrm"] = self.install_espocrm()

        # Summary
        self.log("=" * 60, "INFO")
        self.log("Installation Summary", "INFO")
        self.log("=" * 60, "INFO")

        for service, success in results.items():
            status = "✅ Installed" if success else "❌ Failed"
            self.log(f"{service}: {status}", "INFO")

        if all(results.values()):
            self.log("=" * 60, "INFO")
            self.log("All integrations installed successfully!", "SUCCESS")
            self.log("=" * 60, "INFO")
            self.log("Next steps:", "INFO")
            self.log("1. Run: python3 scripts/setup_integrations.py --status", "INFO")
            self.log("2. Configure integrations via Admin Panel or CLI", "INFO")
            self.log(
                "3. Create Matrix bot account: sudo -u matrix-synapse register_new_matrix_user",
                "INFO",
            )
            self.log("4. Complete EspoCRM setup at http://localhost/espocrm", "INFO")
            return True
        self.log("Some installations failed. Check logs above.", "WARNING")
        return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automatically install PBX integration services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install all services
  sudo python3 scripts/install_integrations.py

  # Install specific service
  sudo python3 scripts/install_integrations.py --service jitsi

  # Dry run (show what would be done)
  python3 scripts/install_integrations.py --dry-run

  # Verbose output
  sudo python3 scripts/install_integrations.py --verbose
        """,
    )

    parser.add_argument(
        "--service",
        "-s",
        choices=["jitsi", "matrix", "espocrm", "all"],
        default="all",
        help="Service to install (default: all)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    installer = IntegrationInstaller(verbose=args.verbose, dry_run=args.dry_run)

    if args.service == "all":
        success = installer.install_all()
    elif args.service == "jitsi":
        success = installer.install_jitsi()
    elif args.service == "matrix":
        success = installer.install_matrix_synapse()
    elif args.service == "espocrm":
        success = installer.install_espocrm()
    else:
        print("Invalid service selection")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
