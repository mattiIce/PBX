#!/usr/bin/env python3
"""
Automatic Integration Installation Script

This script automatically installs and configures required services:
- Jitsi Meet (video conferencing)
- Matrix Synapse (team messaging)
- EspoCRM (customer relationship management)

It handles dependencies, SSL certificates, and basic configuration.
"""

import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path


class IntegrationInstaller:
    """Automated installer for PBX integrations"""
    
    def __init__(self, verbose=False, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.base_path = Path(__file__).parent.parent
        self.is_root = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
        
    def log(self, message, level="INFO"):
        """Log a message"""
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️ ",
            "STEP": "🔧"
        }.get(level, "")
        print(f"{prefix} {message}")
    
    def run_command(self, cmd, check=True, capture=False):
        """Run a shell command"""
        if self.verbose or self.dry_run:
            self.log(f"Running: {cmd}", "STEP")
        
        if self.dry_run:
            return True
        
        try:
            if capture:
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    check=check,
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
            else:
                subprocess.run(cmd, shell=True, check=check)
                return True
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {cmd}", "ERROR")
            if self.verbose:
                self.log(f"Error: {e}", "ERROR")
            return False
    
    def check_command_exists(self, command):
        """Check if a command exists"""
        result = self.run_command(f"command -v {command}", check=False, capture=True)
        return bool(result)
    
    def detect_os(self):
        """Detect the operating system"""
        system = platform.system().lower()
        if system == "linux":
            # Try to detect specific distro
            if Path("/etc/debian_version").exists():
                return "debian"
            elif Path("/etc/redhat-release").exists():
                return "redhat"
        return system
    
    def check_prerequisites(self):
        """Check if system meets prerequisites"""
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
            if proceed != 'y':
                return False
        
        self.log("Prerequisites check passed", "SUCCESS")
        return True
    
    def install_ssl_certificates(self):
        """Install SSL certificates for localhost"""
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
        
        # Generate self-signed certificate
        self.log("Generating self-signed SSL certificate...", "STEP")
        cmd = f"""openssl req -x509 -newkey rsa:4096 -nodes \
            -keyout {key_file} \
            -out {cert_file} \
            -days 365 \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
        """
        
        if self.run_command(cmd):
            self.log("SSL certificates generated successfully", "SUCCESS")
            return True
        else:
            self.log("Failed to generate SSL certificates", "ERROR")
            return False
    
    def install_jitsi(self):
        """Install Jitsi Meet"""
        self.log("Installing Jitsi Meet...", "STEP")
        
        # Check if already installed
        if self.check_command_exists("jitsi-meet"):
            self.log("Jitsi Meet is already installed", "INFO")
            return True
        
        os_type = self.detect_os()
        
        if os_type in ["debian", "ubuntu"]:
            # Add Jitsi repository
            self.log("Adding Jitsi repository...", "STEP")
            commands = [
                "curl -sL https://download.jitsi.org/jitsi-key.gpg.key | gpg --dearmor | tee /usr/share/keyrings/jitsi-keyring.gpg > /dev/null",
                'echo "deb [signed-by=/usr/share/keyrings/jitsi-keyring.gpg] https://download.jitsi.org stable/" | tee /etc/apt/sources.list.d/jitsi-stable.list',
                "apt-get update",
            ]
            
            for cmd in commands:
                if not self.run_command(cmd):
                    self.log("Failed to add Jitsi repository", "ERROR")
                    return False
            
            # Install Jitsi
            self.log("Installing Jitsi Meet package...", "STEP")
            # Use debconf to pre-seed configuration
            preseed_cmds = [
                'echo "jitsi-meet jitsi-meet/jvb-hostname string localhost" | debconf-set-selections',
                'echo "jitsi-meet-web-config jitsi-meet/cert-choice select Generate a new self-signed certificate" | debconf-set-selections',
            ]
            
            for cmd in preseed_cmds:
                self.run_command(cmd)
            
            if self.run_command("DEBIAN_FRONTEND=noninteractive apt-get install -y jitsi-meet"):
                self.log("Jitsi Meet installed successfully", "SUCCESS")
                return True
            else:
                self.log("Failed to install Jitsi Meet", "ERROR")
                return False
        else:
            self.log("Automatic Jitsi installation only supported on Debian/Ubuntu", "ERROR")
            self.log("Please install manually: https://jitsi.github.io/handbook/docs/devops-guide/devops-guide-quickstart", "INFO")
            return False
    
    def install_matrix_synapse(self):
        """Install Matrix Synapse"""
        self.log("Installing Matrix Synapse...", "STEP")
        
        # Check if already installed
        if self.check_command_exists("synapse_homeserver"):
            self.log("Matrix Synapse is already installed", "INFO")
            return True
        
        os_type = self.detect_os()
        
        if os_type in ["debian", "ubuntu"]:
            # Add Matrix repository
            self.log("Adding Matrix repository...", "STEP")
            commands = [
                "apt-get install -y wget apt-transport-https",
                "wget -O /usr/share/keyrings/matrix-org-archive-keyring.gpg https://packages.matrix.org/debian/matrix-org-archive-keyring.gpg",
                'echo "deb [signed-by=/usr/share/keyrings/matrix-org-archive-keyring.gpg] https://packages.matrix.org/debian/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/matrix-org.list',
                "apt-get update",
            ]
            
            for cmd in commands:
                if not self.run_command(cmd):
                    self.log("Failed to add Matrix repository", "ERROR")
                    return False
            
            # Install Matrix Synapse
            self.log("Installing Matrix Synapse package...", "STEP")
            if self.run_command("apt-get install -y matrix-synapse-py3"):
                self.log("Matrix Synapse installed successfully", "SUCCESS")
                
                # Configure Synapse
                self.log("Configuring Matrix Synapse...", "STEP")
                config_path = "/etc/matrix-synapse/homeserver.yaml"
                
                # Enable registration (for creating bot account)
                if Path(config_path).exists():
                    self.run_command(f"sed -i 's/enable_registration: false/enable_registration: true/' {config_path}")
                    self.run_command("systemctl restart matrix-synapse")
                
                return True
            else:
                self.log("Failed to install Matrix Synapse", "ERROR")
                return False
        else:
            self.log("Automatic Matrix installation only supported on Debian/Ubuntu", "ERROR")
            self.log("Please install manually: https://matrix-org.github.io/synapse/latest/setup/installation.html", "INFO")
            return False
    
    def install_espocrm(self):
        """Install EspoCRM"""
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
            commands = [
                "apt-get install -y apache2 mysql-server php libapache2-mod-php",
                "apt-get install -y php-mysql php-json php-gd php-zip php-mbstring php-xml php-curl php-ldap",
            ]
            
            for cmd in commands:
                if not self.run_command(cmd):
                    self.log("Failed to install prerequisites", "ERROR")
                    return False
            
            # Download and extract EspoCRM
            self.log("Downloading EspoCRM...", "STEP")
            espocrm_version = "7.5.5"  # Latest stable version
            commands = [
                f"wget -O /tmp/espocrm.zip https://www.espocrm.com/downloads/EspoCRM-{espocrm_version}.zip",
                "mkdir -p /var/www/html/espocrm",
                "unzip /tmp/espocrm.zip -d /var/www/html/espocrm",
                "chown -R www-data:www-data /var/www/html/espocrm",
                "chmod -R 755 /var/www/html/espocrm",
            ]
            
            for cmd in commands:
                if not self.run_command(cmd):
                    self.log("Failed to download/extract EspoCRM", "ERROR")
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
            
            commands = [
                "a2ensite espocrm",
                "a2enmod rewrite",
                "systemctl restart apache2",
            ]
            
            for cmd in commands:
                self.run_command(cmd)
            
            # Setup MySQL database
            self.log("Setting up MySQL database...", "STEP")
            mysql_commands = """
CREATE DATABASE IF NOT EXISTS espocrm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'espocrm_user'@'localhost' IDENTIFIED BY 'espocrm_password';
GRANT ALL PRIVILEGES ON espocrm.* TO 'espocrm_user'@'localhost';
FLUSH PRIVILEGES;
"""
            
            self.run_command(f"mysql -u root -e \"{mysql_commands}\"", check=False)
            
            self.log("EspoCRM installed successfully", "SUCCESS")
            self.log("Complete setup at: http://localhost/espocrm", "INFO")
            self.log("Database: espocrm, User: espocrm_user, Password: espocrm_password", "INFO")
            
            return True
        else:
            self.log("Automatic EspoCRM installation only supported on Debian/Ubuntu", "ERROR")
            self.log("Please install manually: https://docs.espocrm.com/administration/installation/", "INFO")
            return False
    
    def install_all(self):
        """Install all integrations"""
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
        results['jitsi'] = self.install_jitsi()
        
        # Install Matrix Synapse
        results['matrix'] = self.install_matrix_synapse()
        
        # Install EspoCRM
        results['espocrm'] = self.install_espocrm()
        
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
            self.log("3. Create Matrix bot account: sudo -u matrix-synapse register_new_matrix_user", "INFO")
            self.log("4. Complete EspoCRM setup at http://localhost/espocrm", "INFO")
            return True
        else:
            self.log("Some installations failed. Check logs above.", "WARNING")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Automatically install PBX integration services',
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
        """
    )
    
    parser.add_argument(
        '--service', '-s',
        choices=['jitsi', 'matrix', 'espocrm', 'all'],
        default='all',
        help='Service to install (default: all)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    installer = IntegrationInstaller(
        verbose=args.verbose,
        dry_run=args.dry_run
    )
    
    if args.service == 'all':
        success = installer.install_all()
    elif args.service == 'jitsi':
        success = installer.install_jitsi()
    elif args.service == 'matrix':
        success = installer.install_matrix_synapse()
    elif args.service == 'espocrm':
        success = installer.install_espocrm()
    else:
        print("Invalid service selection")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
