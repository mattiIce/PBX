#!/usr/bin/env python3
"""
Warden VoIP PBX - Interactive Setup Wizard for Ubuntu

This script provides an easy-to-use setup experience for installing
the Warden VoIP PBX system on Ubuntu 24.04 LTS.

Usage:
    sudo python3 setup_ubuntu.py

Features:
    - System dependency installation
    - Python environment setup
    - PostgreSQL database configuration
    - Environment variable configuration
    - Database initialization
    - Voice prompts generation
    - SSL certificate generation
    - Setup verification

Requirements:
    - Ubuntu 24.04 LTS (recommended)
    - Python 3.12+
    - Root/sudo access
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class SetupWizard:
    """Interactive setup wizard for Warden VoIP PBX"""

    def __init__(self):
        """Initialize the setup wizard"""
        self.project_root = Path(__file__).parent.absolute()
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.config_file = self.project_root / "config.yml"
        self.errors = []
        self.warnings = []
        self.db_config = {}

    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")

    def print_success(self, text: str):
        """Print a success message"""
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

    def print_error(self, text: str):
        """Print an error message"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
        self.errors.append(text)

    def print_warning(self, text: str):
        """Print a warning message"""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
        self.warnings.append(text)

    def print_info(self, text: str):
        """Print an info message"""
        print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

    def run_command(
        self, cmd: str, description: str, check: bool = True, shell: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run a shell command and return the result

        Args:
            cmd: Command to run
            description: Description of what the command does
            check: Whether to check for errors
            shell: Whether to use shell execution

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        self.print_info(f"{description}...")
        try:
            result = subprocess.run(
                cmd,
                shell=shell,
                check=check,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except subprocess.TimeoutExpired:
            self.print_error(f"Command timed out: {description}")
            return -1, "", "Command timed out"

    def check_root(self) -> bool:
        """Check if running as root"""
        if os.geteuid() != 0:
            self.print_error("This script must be run as root (use sudo)")
            return False
        return True

    def check_ubuntu_version(self) -> bool:
        """Check Ubuntu version"""
        self.print_info("Checking Ubuntu version...")
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                content = f.read()
                if "Ubuntu" in content:
                    if "24.04" in content:
                        self.print_success("Ubuntu 24.04 LTS detected")
                        return True
                    self.print_warning(
                        "Ubuntu 24.04 LTS is recommended. Other versions may work but are not tested."
                    )
                    return True
                self.print_error("This script is designed for Ubuntu")
                return False
        except FileNotFoundError:
            self.print_error("Cannot detect OS version")
            return False

    def check_python_version(self) -> bool:
        """Check Python version"""
        self.print_info("Checking Python version...")
        version = sys.version_info
        if version.major == 3 and version.minor >= 12:
            self.print_success(f"Python {version.major}.{version.minor} detected")
            return True
        else:
            self.print_error(
                f"Python 3.12+ required. Current version: {version.major}.{version.minor}"
            )
            return False

    def install_system_dependencies(self) -> bool:
        """Install required system packages"""
        self.print_header("Installing System Dependencies")

        # Update package lists
        ret, _, _ = self.run_command("apt-get update", "Updating package lists", check=False)
        if ret != 0:
            self.print_error("Failed to update package lists")
            return False

        # List of required packages
        packages = [
            "espeak",  # Text-to-speech engine
            "ffmpeg",  # Audio/video processing
            "libopus-dev",  # Opus codec library
            "portaudio19-dev",  # Audio I/O library
            "libspeex-dev",  # Speex codec library
            "postgresql",  # Database server
            "postgresql-contrib",  # PostgreSQL extensions
            "python3-venv",  # Python virtual environment
            "python3-pip",  # Python package installer
            "git",  # Version control
        ]

        # Install packages
        packages_str = " ".join(packages)
        ret, _, stderr = self.run_command(
            f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages_str}",
            "Installing system packages",
            check=False,
        )

        if ret != 0:
            self.print_error(f"Failed to install some packages: {stderr}")
            return False

        self.print_success("All system dependencies installed")
        return True

    def setup_python_venv(self) -> bool:
        """Set up Python virtual environment"""
        self.print_header("Setting Up Python Environment")

        # Create virtual environment
        if self.venv_path.exists():
            self.print_info("Virtual environment already exists")
            response = input("Recreate it? (y/N): ").strip().lower()
            if response == "y":
                self.print_info("Removing existing virtual environment...")
                subprocess.run(["rm", "-rf", str(self.venv_path)], check=True)
            else:
                self.print_info("Using existing virtual environment")
                return True

        ret, _, _ = self.run_command(
            f"python3 -m venv {self.venv_path}",
            "Creating virtual environment",
            check=False,
        )
        if ret != 0:
            self.print_error("Failed to create virtual environment")
            return False

        self.print_success("Virtual environment created")

        # Upgrade pip
        pip_path = self.venv_path / "bin" / "pip"
        ret, _, _ = self.run_command(
            f"{pip_path} install --upgrade pip", "Upgrading pip", check=False
        )
        if ret != 0:
            self.print_warning("Failed to upgrade pip (continuing anyway)")

        # Install requirements
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            self.print_info("Installing Python dependencies (this may take several minutes)...")
            ret, _, stderr = self.run_command(
                f"{pip_path} install -r {requirements_file}",
                "Installing Python packages",
                check=False,
            )
            if ret != 0:
                self.print_error(f"Failed to install Python dependencies: {stderr}")
                return False
            self.print_success("Python dependencies installed")
        else:
            self.print_error(f"Requirements file not found: {requirements_file}")
            return False

        return True

    def setup_postgresql(self) -> bool:
        """Set up PostgreSQL database"""
        self.print_header("Configuring PostgreSQL Database")

        # Check if PostgreSQL is running
        ret, _, _ = self.run_command(
            "systemctl is-active postgresql", "Checking PostgreSQL status", check=False
        )

        if ret != 0:
            self.print_info("Starting PostgreSQL service...")
            ret, _, _ = self.run_command(
                "systemctl start postgresql", "Starting PostgreSQL", check=False
            )
            if ret != 0:
                self.print_error("Failed to start PostgreSQL")
                return False

        # Enable PostgreSQL to start on boot
        self.run_command("systemctl enable postgresql", "Enabling PostgreSQL on boot", check=False)

        self.print_success("PostgreSQL is running")

        # Prompt for database configuration
        print("\nDatabase Configuration:")
        db_name = input("  Database name [pbx_system]: ").strip() or "pbx_system"
        db_user = input("  Database user [pbx_user]: ").strip() or "pbx_user"
        db_password = input("  Database password: ").strip()

        if not db_password:
            self.print_error("Database password is required")
            return False

        # Create database user
        create_user_cmd = (
            f"sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_password}';\""
        )
        ret, _, stderr = self.run_command(
            create_user_cmd, f"Creating database user '{db_user}'", check=False
        )

        if ret != 0 and "already exists" not in stderr:
            self.print_error(f"Failed to create database user: {stderr}")
            return False
        elif "already exists" in stderr:
            self.print_warning(f"User '{db_user}' already exists")

        # Create database
        create_db_cmd = f'sudo -u postgres psql -c "CREATE DATABASE {db_name} OWNER {db_user};"'
        ret, _, stderr = self.run_command(
            create_db_cmd, f"Creating database '{db_name}'", check=False
        )

        if ret != 0 and "already exists" not in stderr:
            self.print_error(f"Failed to create database: {stderr}")
            return False
        elif "already exists" in stderr:
            self.print_warning(f"Database '{db_name}' already exists")

        # Grant privileges
        grant_cmd = (
            f'sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"'
        )
        self.run_command(grant_cmd, "Granting privileges", check=False)

        self.print_success("Database configured successfully")

        # Store database configuration for later use
        self.db_config = {
            "DB_NAME": db_name,
            "DB_USER": db_user,
            "DB_PASSWORD": db_password,
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
        }

        return True

    def setup_environment_file(self) -> bool:
        """Set up .env file"""
        self.print_header("Configuring Environment Variables")

        # Check if .env already exists
        if self.env_file.exists():
            self.print_info(".env file already exists")
            response = input("Overwrite it? (y/N): ").strip().lower()
            if response != "y":
                self.print_info("Keeping existing .env file")
                return True

        # Create .env file with database configuration
        env_content = f"""# Warden VoIP PBX Environment Variables
# Generated by setup_ubuntu.py

# Database Configuration
DB_HOST={self.db_config['DB_HOST']}
DB_PORT={self.db_config['DB_PORT']}
DB_NAME={self.db_config['DB_NAME']}
DB_USER={self.db_config['DB_USER']}
DB_PASSWORD={self.db_config['DB_PASSWORD']}

# Redis Configuration (optional)
# REDIS_PASSWORD=

# SMTP Configuration (optional - for voicemail-to-email)
# SMTP_HOST=
# SMTP_PORT=587
# SMTP_USERNAME=
# SMTP_PASSWORD=

# Optional Integrations
# ZOOM_CLIENT_ID=
# ZOOM_CLIENT_SECRET=
# OUTLOOK_CLIENT_ID=
# OUTLOOK_CLIENT_SECRET=
"""

        try:
            with open(self.env_file, "w", encoding="utf-8") as f:
                f.write(env_content)
            # Set restrictive permissions on .env file
            os.chmod(self.env_file, 0o600)
            self.print_success(f".env file created at {self.env_file}")
            return True
        except OSError as e:
            self.print_error(f"Failed to create .env file: {e}")
            return False

    def initialize_database(self) -> bool:
        """Initialize the database schema"""
        self.print_header("Initializing Database Schema")

        init_script = self.project_root / "scripts" / "init_database.py"
        if not init_script.exists():
            self.print_warning("Database initialization script not found, skipping...")
            return True

        python_path = self.venv_path / "bin" / "python"
        ret, _, stderr = self.run_command(
            f"{python_path} {init_script}",
            "Initializing database tables",
            check=False,
        )

        if ret != 0:
            self.print_error(f"Failed to initialize database: {stderr}")
            return False

        self.print_success("Database initialized successfully")
        return True

    def generate_ssl_certificate(self) -> bool:
        """Generate self-signed SSL certificate"""
        self.print_header("Generating SSL Certificate")

        # Prompt for hostname
        import socket

        default_hostname = socket.gethostname()
        hostname = (
            input(f"  Hostname or IP address [{default_hostname}]: ").strip() or default_hostname
        )

        ssl_script = self.project_root / "scripts" / "generate_ssl_cert.py"
        if not ssl_script.exists():
            self.print_warning("SSL certificate generation script not found, skipping...")
            return True

        python_path = self.venv_path / "bin" / "python"
        ret, _, stderr = self.run_command(
            f"{python_path} {ssl_script} --hostname {hostname}",
            "Generating SSL certificate",
            check=False,
        )

        if ret != 0:
            self.print_warning(f"Failed to generate SSL certificate: {stderr}")
            self.print_info("You can generate it later using: python scripts/generate_ssl_cert.py")
            return True

        self.print_success("SSL certificate generated")
        return True

    def generate_voice_prompts(self) -> bool:
        """Generate voice prompts"""
        self.print_header("Generating Voice Prompts")

        self.print_info("Voice prompts are required for voicemail and auto-attendant features.")
        response = input("Generate voice prompts now? (Y/n): ").strip().lower()

        if response == "n":
            self.print_warning(
                "Skipping voice prompt generation. You can generate them later using:"
            )
            self.print_info("  python scripts/generate_tts_prompts.py")
            return True

        # Check for voice generation script
        voice_script = self.project_root / "scripts" / "generate_tts_prompts.py"
        if not voice_script.exists():
            self.print_warning("Voice prompt generation script not found")
            return True

        python_path = self.venv_path / "bin" / "python"
        self.print_info("Generating voice prompts (this may take a few minutes)...")
        ret, _, stderr = self.run_command(
            f"{python_path} {voice_script}",
            "Generating voice prompts",
            check=False,
        )

        if ret != 0:
            self.print_warning(f"Failed to generate voice prompts: {stderr}")
            self.print_info(
                "You can generate them later using: python scripts/generate_tts_prompts.py"
            )
            return True

        self.print_success("Voice prompts generated")
        return True

    def verify_setup(self) -> bool:
        """Verify the setup"""
        self.print_header("Verifying Setup")

        checks_passed = 0
        total_checks = 6

        # Check 1: Virtual environment exists
        if self.venv_path.exists():
            self.print_success("Virtual environment exists")
            checks_passed += 1
        else:
            self.print_error("Virtual environment not found")

        # Check 2: .env file exists
        if self.env_file.exists():
            self.print_success(".env file exists")
            checks_passed += 1
        else:
            self.print_error(".env file not found")

        # Check 3: config.yml exists
        if self.config_file.exists():
            self.print_success("config.yml exists")
            checks_passed += 1
        else:
            self.print_warning("config.yml not found (will use defaults)")
            checks_passed += 1

        # Check 4: PostgreSQL is running
        ret, _, _ = self.run_command(
            "systemctl is-active postgresql", "Checking PostgreSQL", check=False
        )
        if ret == 0:
            self.print_success("PostgreSQL is running")
            checks_passed += 1
        else:
            self.print_error("PostgreSQL is not running")

        # Check 5: Python packages installed
        pip_path = self.venv_path / "bin" / "pip"
        ret, stdout, _ = self.run_command(
            f"{pip_path} list", "Checking Python packages", check=False
        )
        if ret == 0 and "PyYAML" in stdout:
            self.print_success("Python packages installed")
            checks_passed += 1
        else:
            self.print_error("Python packages not properly installed")

        # Check 6: Required system packages
        required_packages = ["espeak", "ffmpeg", "postgresql"]
        all_installed = True
        for package in required_packages:
            ret, _, _ = self.run_command(
                f"dpkg -l | grep -q {package}", f"Checking {package}", check=False
            )
            if ret != 0:
                all_installed = False
                break

        if all_installed:
            self.print_success("System packages installed")
            checks_passed += 1
        else:
            self.print_error("Some system packages are missing")

        print(
            f"\n{Colors.BOLD}Setup verification: {checks_passed}/{total_checks} checks passed{Colors.ENDC}"
        )

        return checks_passed >= 5  # Allow one check to fail

    def print_next_steps(self):
        """Print next steps after setup"""
        self.print_header("Setup Complete!")

        print(
            f"{Colors.OKGREEN}The Warden VoIP PBX system has been set up successfully!{Colors.ENDC}\n"
        )

        print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}\n")

        print(f"{Colors.OKCYAN}1. Configure the system:{Colors.ENDC}")
        print("   Edit config.yml to customize your PBX settings")
        print("   (extensions, dialplan, features, etc.)\n")

        print(f"{Colors.OKCYAN}2. Start the PBX server:{Colors.ENDC}")
        print("   source venv/bin/activate")
        print("   python main.py\n")

        print(f"{Colors.OKCYAN}3. Access the Admin Interface:{Colors.ENDC}")
        print("   Open your browser to: https://localhost:8080")
        print("   (You'll need to accept the self-signed certificate)\n")

        print(f"{Colors.OKCYAN}4. Optional - Install as a system service:{Colors.ENDC}")
        print("   sudo cp pbx.service /etc/systemd/system/")
        print("   sudo systemctl enable pbx")
        print("   sudo systemctl start pbx\n")

        print(f"{Colors.OKCYAN}5. Review the documentation:{Colors.ENDC}")
        print("   README.md - Quick overview")
        print("   COMPLETE_GUIDE.md - Comprehensive documentation")
        print("   TROUBLESHOOTING.md - Common issues and solutions\n")

        if self.warnings:
            print(f"{Colors.WARNING}Warnings during setup:{Colors.ENDC}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
            print()

        if self.errors:
            print(f"{Colors.FAIL}Errors during setup:{Colors.ENDC}")
            for error in self.errors:
                print(f"  ✗ {error}")
            print()

    def run(self):
        """Run the setup wizard"""
        # Print welcome message
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("╔" + "═" * 78 + "╗")
        print("║" + "Warden VoIP PBX - Interactive Setup Wizard".center(78) + "║")
        print("║" + "Ubuntu 24.04 LTS".center(78) + "║")
        print("╚" + "═" * 78 + "╝")
        print(f"{Colors.ENDC}\n")

        print("This wizard will guide you through the installation and configuration of")
        print("the Warden VoIP PBX system.\n")

        # Pre-flight checks
        if not self.check_root():
            return 1

        if not self.check_ubuntu_version():
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response != "y":
                return 1

        if not self.check_python_version():
            return 1

        # Confirm before proceeding
        print(f"\n{Colors.BOLD}This wizard will:{Colors.ENDC}")
        print("  • Install system dependencies (espeak, ffmpeg, PostgreSQL, etc.)")
        print("  • Create Python virtual environment")
        print("  • Install Python packages")
        print("  • Configure PostgreSQL database")
        print("  • Create .env configuration file")
        print("  • Initialize database schema")
        print("  • Generate SSL certificate")
        print("  • Generate voice prompts")
        print()

        response = input(f"{Colors.BOLD}Continue with setup? (Y/n): {Colors.ENDC}").strip().lower()
        if response == "n":
            print("Setup cancelled.")
            return 0

        # Run setup steps
        steps = [
            ("System Dependencies", self.install_system_dependencies),
            ("Python Environment", self.setup_python_venv),
            ("PostgreSQL Database", self.setup_postgresql),
            ("Environment Variables", self.setup_environment_file),
            ("Database Schema", self.initialize_database),
            ("SSL Certificate", self.generate_ssl_certificate),
            ("Voice Prompts", self.generate_voice_prompts),
            ("Setup Verification", self.verify_setup),
        ]

        for step_name, step_func in steps:
            if not step_func():
                self.print_error(f"Setup failed at step: {step_name}")
                print(
                    f"\n{Colors.FAIL}Setup did not complete successfully. "
                    f"Please review the errors above.{Colors.ENDC}"
                )
                return 1

        # Print next steps
        self.print_next_steps()

        return 0


def main():
    """Main entry point"""
    wizard = SetupWizard()
    try:
        exit_code = wizard.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Setup cancelled by user.{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
