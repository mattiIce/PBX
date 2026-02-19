#!/usr/bin/env python3
"""
Warden VoIP PBX - Interactive Setup Wizard for Ubuntu

This script provides an easy-to-use setup experience for installing
the Warden VoIP PBX system on Ubuntu 24.04 LTS.

Usage:
    sudo python3 scripts/setup_ubuntu.py

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
    - Python 3.13+
    - Root/sudo access
"""

import os
import re
import shlex
import socket
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path


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

    def __init__(self) -> None:
        """Initialize the setup wizard"""
        self.project_root = Path(__file__).resolve().parent.parent
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.config_file = self.project_root / "config.yml"
        self.errors = []
        self.warnings = []
        self.db_config = {}

    def print_header(self, text: str) -> None:
        """Print a formatted header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")

    def print_success(self, text: str) -> None:
        """Print a success message"""
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

    def print_error(self, text: str) -> None:
        """Print an error message"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
        self.errors.append(text)

    def print_warning(self, text: str) -> None:
        """Print a warning message"""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
        self.warnings.append(text)

    def print_info(self, text: str) -> None:
        """Print an info message"""
        print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

    def run_command(
        self,
        cmd: str,
        description: str,
        check: bool = True,
        shell: bool = True,
        timeout: int = 300,
    ) -> tuple[int, str, str]:
        """
        Run a shell command and return the result

        Args:
            cmd: Command to run
            description: Description of what the command does
            check: Whether to check for errors
            shell: Whether to use shell execution
            timeout: Command timeout in seconds (default: 300)

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
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except subprocess.TimeoutExpired:
            self.print_error(f"Command timed out: {description}")
            return 124, "", "Command timed out"

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
            with Path("/etc/os-release").open(encoding="utf-8") as f:
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
        if version.major == 3 and version.minor >= 13:
            self.print_success(f"Python {version.major}.{version.minor} detected")
            return True
        self.print_error(f"Python 3.13+ required. Current version: {version.major}.{version.minor}")
        return False

    def install_system_dependencies(self) -> bool:
        """Install required system packages"""
        self.print_header("Installing System Dependencies")

        # Update package lists
        ret, _, _ = self.run_command("apt-get update", "Updating package lists", check=False)
        if ret != 0:
            self.print_error("Failed to update package lists")
            return False

        # Add PostgreSQL 17 official repository (Ubuntu 24.04 default repos only provide PG 16)
        self.print_info("Adding PostgreSQL 17 repository...")
        self.run_command(
            "apt-get install -y curl ca-certificates", "Installing prerequisites", check=False
        )
        self.run_command(
            "install -d /usr/share/postgresql-common/pgdg",
            "Creating PostgreSQL PGDG directory",
            check=False,
        )
        self.run_command(
            "curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail "
            "https://www.postgresql.org/media/keys/ACCC4CF8.asc",
            "Downloading PostgreSQL signing key",
            check=False,
        )
        self.run_command(
            "sh -c 'echo \"deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc]"
            " https://apt.postgresql.org/pub/repos/apt"
            " $(lsb_release -cs)-pgdg main\" > /etc/apt/sources.list.d/pgdg.list'",
            "Adding PostgreSQL repository",
            check=False,
        )
        self.run_command("apt-get update", "Updating package lists", check=False)

        # List of required packages
        packages = [
            "espeak",  # Text-to-speech engine
            "ffmpeg",  # Audio/video processing
            "libopus-dev",  # Opus codec library
            "portaudio19-dev",  # Audio I/O library
            "libspeex-dev",  # Speex codec library
            "postgresql-17",  # Database server (PostgreSQL 17 from PGDG repo)
            "postgresql-contrib",  # PostgreSQL extensions
            "libpq-dev",  # PostgreSQL client library headers (for psycopg2)
            "nginx",  # Reverse proxy
            "python3-venv",  # Python virtual environment
            "python3-pip",  # Python package installer
            "python3-dev",  # Python headers (for building C extensions)
            "build-essential",  # Compiler toolchain (gcc, make, etc.)
            "git",  # Version control
        ]

        # Install packages (longer timeout for slow networks)
        packages_str = " ".join(packages)
        ret, _, stderr = self.run_command(
            f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages_str}",
            "Installing system packages",
            check=False,
            timeout=600,  # 10 minute timeout for package installation
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

        ret, _, stderr = self.run_command(
            f"python3 -m venv {self.venv_path}",
            "Creating virtual environment",
            check=False,
        )
        if ret != 0:
            self.print_warning(f"Standard venv creation failed ({stderr[:120].strip()})")
            self.print_info("Retrying with --without-pip and manual pip bootstrap...")
            ret2, _, stderr2 = self.run_command(
                f"python3 -m venv --without-pip {self.venv_path}",
                "Creating virtual environment (without pip)",
                check=False,
            )
            if ret2 != 0:
                self.print_error(f"Failed to create virtual environment: {stderr2[:200]}")
                return False
            # Bootstrap pip via get-pip.py
            python_path = self.venv_path / "bin" / "python3"
            ret3, _, stderr3 = self.run_command(
                f"curl -sSL https://bootstrap.pypa.io/get-pip.py | {python_path}",
                "Bootstrapping pip via get-pip.py",
                check=False,
                timeout=120,
            )
            if ret3 != 0:
                self.print_error(f"Failed to bootstrap pip: {stderr3[:200]}")
                return False

        self.print_success("Virtual environment created")

        # Install uv and upgrade pip
        pip_path = self.venv_path / "bin" / "pip"
        ret, _, _ = self.run_command(
            f"{pip_path} install --upgrade pip uv", "Installing uv package manager", check=False
        )
        if ret != 0:
            self.print_warning("Failed to install uv (falling back to pip)")

        # Install project dependencies (longer timeout for slow networks)
        uv_path = self.venv_path / "bin" / "uv"
        if uv_path.exists():
            self.print_info(
                "Installing Python dependencies with uv (this may take several minutes)..."
            )
            ret, _, stderr = self.run_command(
                f"{uv_path} pip install -e {self.project_root}",
                "Installing Python packages",
                check=False,
                timeout=900,  # 15 minute timeout for Python package installation
            )
        else:
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                self.print_error(f"Requirements file not found: {requirements_file}")
                return False
            self.print_info(
                "Installing Python dependencies with pip (this may take several minutes)..."
            )
            ret, _, stderr = self.run_command(
                f"{pip_path} install -r {requirements_file}",
                "Installing Python packages (pip fallback)",
                check=False,
                timeout=900,  # 15 minute timeout for Python package installation
            )
        if ret != 0:
            self.print_error(f"Failed to install Python dependencies: {stderr}")
            return False
        self.print_success("Python dependencies installed")

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

        # Validate inputs to prevent SQL injection
        # PostgreSQL identifiers: start with letter, contain letters, numbers, underscores
        # Hyphens allowed in middle but not at end
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9_]$|^[a-zA-Z]$", db_user):
            self.print_error(
                "Database user must start with a letter, contain only letters, numbers, underscores, hyphens, and not end with a hyphen"
            )
            return False
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9_]$|^[a-zA-Z]$", db_name):
            self.print_error(
                "Database name must start with a letter, contain only letters, numbers, underscores, hyphens, and not end with a hyphen"
            )
            return False

        # Create database user
        # Escape single quotes in password for SQL
        escaped_password = db_password.replace("'", "''")
        sql_cmd = f"CREATE USER {db_user} WITH PASSWORD '{escaped_password}';"
        # Use shlex.quote to safely pass SQL to the shell
        create_user_cmd = f"sudo -u postgres psql -c {shlex.quote(sql_cmd)}"
        return_code, _, stderr = self.run_command(
            create_user_cmd, f"Creating database user '{db_user}'", check=False
        )

        if return_code != 0 and "already exists" not in stderr:
            self.print_error(f"Failed to create database user: {stderr}")
            return False
        if "already exists" in stderr:
            self.print_warning(f"User '{db_user}' already exists")

        # Create database (safe - inputs validated above)
        sql_cmd = f"CREATE DATABASE {db_name} OWNER {db_user};"
        create_db_cmd = f"sudo -u postgres psql -c {shlex.quote(sql_cmd)}"
        return_code, _, stderr = self.run_command(
            create_db_cmd, f"Creating database '{db_name}'", check=False
        )

        if return_code != 0 and "already exists" not in stderr:
            self.print_error(f"Failed to create database: {stderr}")
            return False
        if "already exists" in stderr:
            self.print_warning(f"Database '{db_name}' already exists")

        # Grant privileges (safe - inputs validated above)
        sql_cmd = f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
        grant_cmd = f"sudo -u postgres psql -c {shlex.quote(sql_cmd)}"
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
DB_HOST={self.db_config["DB_HOST"]}
DB_PORT={self.db_config["DB_PORT"]}
DB_NAME={self.db_config["DB_NAME"]}
DB_USER={self.db_config["DB_USER"]}
DB_PASSWORD={self.db_config["DB_PASSWORD"]}

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
            with self.env_file.open("w", encoding="utf-8") as f:
                f.write(env_content)
            # Set restrictive permissions on .env file
            self.env_file.chmod(0o600)
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
        default_hostname = socket.gethostname()
        hostname = (
            input(f"  Hostname or IP address [{default_hostname}]: ").strip() or default_hostname
        )

        # Validate hostname to prevent command injection
        # Allow alphanumeric, dots, hyphens, and colons (for IPv6) per RFC 952/1123
        if not re.match(r"^[a-zA-Z0-9.:-]+$", hostname):
            self.print_error(
                "Invalid hostname format. Use only letters, numbers, dots, hyphens, and colons."
            )
            return False

        ssl_script = self.project_root / "scripts" / "generate_ssl_cert.py"
        if not ssl_script.exists():
            self.print_warning("SSL certificate generation script not found, skipping...")
            return True

        python_path = self.venv_path / "bin" / "python"
        # Use shlex.quote for defense in depth (hostname is already validated)
        safe_hostname = shlex.quote(hostname)
        ret, _, stderr = self.run_command(
            f"{python_path} {ssl_script} --hostname {safe_hostname}",
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

    def setup_nginx(self) -> bool:
        """Set up Nginx reverse proxy"""
        self.print_header("Configuring Nginx Reverse Proxy")

        # Check if Nginx is installed
        ret, _, _ = self.run_command("which nginx", "Checking Nginx installation", check=False)
        if ret != 0:
            self.print_error("Nginx is not installed")
            return False

        # Prompt for hostname/domain
        default_hostname = socket.gethostname()
        hostname = (
            input(f"  Domain or hostname for Nginx [{default_hostname}]: ").strip()
            or default_hostname
        )

        # Validate hostname
        if not re.match(r"^[a-zA-Z0-9._-]+$", hostname):
            self.print_error(
                "Invalid hostname format. Use only letters, numbers, dots, hyphens, and underscores."
            )
            return False

        # Write Nginx site configuration
        nginx_conf = f"""server {{
    listen 80;
    server_name {hostname};

    location / {{
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }}

    location /ws {{
        proxy_pass http://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""

        try:
            Path("/etc/nginx/sites-available/pbx").write_text(nginx_conf)
        except OSError as e:
            self.print_error(f"Failed to write Nginx config: {e}")
            return False

        # Enable the site
        self.run_command(
            "ln -sf /etc/nginx/sites-available/pbx /etc/nginx/sites-enabled/",
            "Enabling Nginx site",
            check=False,
        )
        self.run_command(
            "rm -f /etc/nginx/sites-enabled/default",
            "Removing default Nginx site",
            check=False,
        )

        # Test Nginx configuration
        ret, _, stderr = self.run_command("nginx -t", "Testing Nginx configuration", check=False)
        if ret != 0:
            self.print_error(f"Nginx configuration test failed: {stderr}")
            return False

        # Reload/start Nginx
        self.run_command(
            "systemctl reload nginx || systemctl start nginx",
            "Starting Nginx",
            check=False,
        )
        self.run_command("systemctl enable nginx", "Enabling Nginx on boot", check=False)

        self.print_success(f"Nginx configured — proxying to PBX at http://{hostname}")
        return True

    def configure_config_yml(self) -> bool:
        """Configure config.yml with user settings"""
        self.print_header("Configuring config.yml")

        if not self.config_file.exists():
            self.print_warning("config.yml not found — a default will be created on first run")
            return True

        self.print_info("Current config.yml found. Let's review key settings.\n")

        response = input("Edit config.yml settings interactively? (Y/n): ").strip().lower()
        if response == "n":
            self.print_info("Keeping existing config.yml")
            return True

        try:
            config_text = self.config_file.read_text(encoding="utf-8")
        except OSError as e:
            self.print_error(f"Failed to read config.yml: {e}")
            return False

        # Prompt for key settings
        print("\nServer Configuration:")
        external_ip = input("  External IP address [192.168.1.14]: ").strip() or ""
        server_name = input("  Server name [Warden Voip]: ").strip() or ""
        api_port = input("  API port [9000]: ").strip() or ""

        # Apply changes
        if external_ip:
            config_text = re.sub(
                r"(external_ip:\s*).*",
                f"\\g<1>{external_ip}",
                config_text,
            )

        if server_name:
            config_text = re.sub(
                r"(server_name:\s*).*",
                f"\\g<1>{server_name}",
                config_text,
            )

        if api_port:
            config_text = re.sub(
                r"(port:\s*)9000",
                f"\\g<1>{api_port}",
                config_text,
                count=1,
            )

        try:
            self.config_file.write_text(config_text, encoding="utf-8")
            self.print_success("config.yml updated")
        except OSError as e:
            self.print_error(f"Failed to write config.yml: {e}")
            return False

        return True

    def configure_env_file(self) -> bool:
        """Allow user to edit .env settings"""
        self.print_header("Reviewing .env Configuration")

        if not self.env_file.exists():
            self.print_warning(".env file not found — skipping")
            return True

        self.print_info("The .env file contains database and integration credentials.\n")

        response = input("Edit .env settings interactively? (y/N): ").strip().lower()
        if response != "y":
            self.print_info("Keeping existing .env settings")
            return True

        try:
            env_text = self.env_file.read_text(encoding="utf-8")
        except OSError as e:
            self.print_error(f"Failed to read .env file: {e}")
            return False

        # SMTP configuration
        print("\nSMTP Configuration (for voicemail-to-email):")
        smtp_host = input("  SMTP host (leave blank to skip): ").strip()
        if smtp_host:
            smtp_port = input("  SMTP port [587]: ").strip() or "587"
            smtp_user = input("  SMTP username: ").strip()
            smtp_password = input("  SMTP password: ").strip()

            # Replace commented SMTP lines with actual values
            env_text = re.sub(r"#\s*SMTP_HOST=.*", f"SMTP_HOST={smtp_host}", env_text)
            env_text = re.sub(r"#\s*SMTP_PORT=.*", f"SMTP_PORT={smtp_port}", env_text)
            if smtp_user:
                env_text = re.sub(r"#\s*SMTP_USERNAME=.*", f"SMTP_USERNAME={smtp_user}", env_text)
            if smtp_password:
                env_text = re.sub(
                    r"#\s*SMTP_PASSWORD=.*", f"SMTP_PASSWORD={smtp_password}", env_text
                )

        # Redis configuration
        print("\nRedis Configuration:")
        redis_password = input("  Redis password (leave blank for none): ").strip()
        if redis_password:
            env_text = re.sub(
                r"#\s*REDIS_PASSWORD=.*", f"REDIS_PASSWORD={redis_password}", env_text
            )

        try:
            self.env_file.write_text(env_text, encoding="utf-8")
            self.env_file.chmod(0o600)
            self.print_success(".env file updated")
        except OSError as e:
            self.print_error(f"Failed to write .env file: {e}")
            return False

        return True

    def setup_systemd_service(self) -> bool:
        """Generate and install the systemd service file"""
        self.print_header("Installing Systemd Service")

        python_path = self.venv_path / "bin" / "python"
        if not python_path.exists():
            # Fall back to system python3 if venv doesn't exist
            python_path = Path("/usr/bin/python3")

        service_content = textwrap.dedent(f"""\
            [Unit]
            Description=Warden VoIP PBX System
            After=network.target postgresql.service

            [Service]
            Type=simple
            User=root
            Group=root
            WorkingDirectory={self.project_root}
            ExecStart={python_path} {self.project_root}/main.py
            Restart=on-failure
            RestartSec=5
            StandardOutput=journal
            StandardError=journal

            [Install]
            WantedBy=multi-user.target
        """)

        # Write to project root for reference
        service_file = self.project_root / "pbx.service"
        try:
            service_file.write_text(service_content, encoding="utf-8")
        except OSError as e:
            self.print_error(f"Failed to write pbx.service to project root: {e}")
            return False

        # Install to systemd
        systemd_path = Path("/etc/systemd/system/pbx.service")
        try:
            systemd_path.write_text(service_content, encoding="utf-8")
        except OSError as e:
            self.print_error(f"Failed to install pbx.service to {systemd_path}: {e}")
            return False

        self.print_success(f"Service file installed to {systemd_path}")

        # Reload systemd so it recognizes the new service
        ret, _, stderr = self.run_command(
            "systemctl daemon-reload", "Reloading systemd", check=False
        )
        if ret != 0:
            self.print_warning(f"Failed to reload systemd: {stderr}")

        # Enable the service to start on boot
        ret, _, stderr = self.run_command(
            "systemctl enable pbx.service", "Enabling PBX service on boot", check=False
        )
        if ret != 0:
            self.print_warning(f"Failed to enable service: {stderr}")
        else:
            self.print_success("PBX service enabled (will start on boot)")

        return True

    def start_pbx(self) -> bool:
        """Start the PBX server via systemd"""
        self.print_header("Starting Warden VoIP PBX")

        response = input("Start the PBX server now? (Y/n): ").strip().lower()
        if response == "n":
            self.print_info("PBX not started. You can start it later with:")
            self.print_info("  sudo systemctl start pbx")
            return True

        # Create logs directory if it doesn't exist
        (self.project_root / "logs").mkdir(exist_ok=True)

        # Use systemctl if the service file is installed
        systemd_service = Path("/etc/systemd/system/pbx.service")
        if systemd_service.exists():
            self.print_info("Starting PBX via systemd...")
            ret, _, stderr = self.run_command(
                "systemctl start pbx", "Starting PBX service", check=False
            )
            if ret != 0:
                self.print_warning(f"Failed to start PBX service: {stderr}")
                self.print_info("You can start it manually with:")
                self.print_info("  sudo systemctl start pbx")
                return True

            self.print_success("PBX service started")
            self.print_info("View logs: journalctl -u pbx -f")
            return True

        # Fall back to direct execution if service file is missing
        python_path = self.venv_path / "bin" / "python"
        main_script = self.project_root / "main.py"

        if not main_script.exists():
            self.print_error(f"main.py not found at {main_script}")
            return False

        self.print_info("Starting PBX server directly (systemd service not found)...")
        self.print_info(f"  Command: {python_path} {main_script}")

        ret, _, stderr = self.run_command(
            f"nohup {python_path} {main_script} > {self.project_root}/logs/pbx.log 2>&1 &",
            "Starting PBX server",
            check=False,
        )

        if ret != 0:
            self.print_warning(f"Failed to start PBX server: {stderr}")
            self.print_info("You can start it manually with:")
            self.print_info("  sudo systemctl start pbx")
            return True

        self.print_success("PBX server started")
        self.print_info(f"Logs: {self.project_root}/logs/pbx.log")
        return True

    def verify_setup(self) -> bool:
        """Verify the setup"""
        self.print_header("Verifying Setup")

        checks_passed = 0
        total_checks = 7

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

        # Check 5: Nginx is running
        ret, _, _ = self.run_command("systemctl is-active nginx", "Checking Nginx", check=False)
        if ret == 0:
            self.print_success("Nginx is running")
            checks_passed += 1
        else:
            self.print_error("Nginx is not running")

        # Check 6: Python packages installed
        pip_path = self.venv_path / "bin" / "pip"
        ret, stdout, _ = self.run_command(
            f"{pip_path} list", "Checking Python packages", check=False
        )
        if ret == 0 and "PyYAML" in stdout:
            self.print_success("Python packages installed")
            checks_passed += 1
        else:
            self.print_error("Python packages not properly installed")

        # Check 7: Required system packages
        required_packages = ["espeak", "ffmpeg", "postgresql", "nginx"]
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

        # Critical checks: PostgreSQL and Python packages must pass for system to be functional
        # PostgreSQL check
        ret_pg, _, _ = self.run_command(
            "systemctl is-active postgresql", "Verifying PostgreSQL (critical)", check=False
        )
        if ret_pg != 0:
            self.print_error("Critical check failed: PostgreSQL is not running")
            return False

        # Python packages check
        pip_path = self.venv_path / "bin" / "pip"
        ret_py, stdout, _ = self.run_command(
            f"{pip_path} list", "Verifying Python packages (critical)", check=False
        )
        if ret_py != 0 or "PyYAML" not in stdout:
            self.print_error("Critical check failed: Python packages not properly installed")
            return False

        # Allow non-critical checks to fail (6 out of 7 total)
        return checks_passed >= 6

    def print_next_steps(self) -> None:
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
        print("   Open your browser to: https://localhost:9000")
        print("   (You'll need to accept the self-signed certificate)\n")

        print(f"{Colors.OKCYAN}4. Manage the PBX service:{Colors.ENDC}")
        print("   sudo systemctl start pbx     # Start the service")
        print("   sudo systemctl stop pbx      # Stop the service")
        print("   sudo systemctl restart pbx   # Restart the service")
        print("   sudo systemctl status pbx    # Check service status\n")

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

    def run(self) -> int:
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
        print("  • Install system dependencies (espeak, ffmpeg, Nginx, PostgreSQL, etc.)")
        print("  • Create Python virtual environment")
        print("  • Install Python packages")
        print("  • Configure PostgreSQL database")
        print("  • Create .env configuration file")
        print("  • Initialize database schema")
        print("  • Generate SSL certificate")
        print("  • Generate voice prompts")
        print("  • Configure Nginx reverse proxy")
        print("  • Configure config.yml")
        print("  • Configure .env settings")
        print("  • Install systemd service (pbx.service)")
        print("  • Start the PBX server")
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
            ("Nginx Reverse Proxy", self.setup_nginx),
            ("Configure config.yml", self.configure_config_yml),
            ("Configure .env", self.configure_env_file),
            ("Systemd Service", self.setup_systemd_service),
            ("Setup Verification", self.verify_setup),
            ("Start PBX", self.start_pbx),
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


def main() -> None:
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
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
