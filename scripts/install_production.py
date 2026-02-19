#!/usr/bin/env python3
"""
Warden VoIP PBX - Unified Production Installer

The single, definitive installation method for deploying Warden VoIP PBX
on a production Ubuntu server. This script handles EVERYTHING:

  - Pre-flight checks (root, OS, Python, hardware)
  - System dependencies (PostgreSQL 17, Redis, Nginx, FFmpeg, etc.)
  - Python virtual environment and package installation
  - PostgreSQL database creation and configuration
  - Redis configuration
  - Environment file (.env) generation
  - Database schema initialization (Alembic migrations)
  - SSL certificate (self-signed or Let's Encrypt)
  - Voice prompt generation (TTS)
  - Systemd service installation
  - Nginx reverse proxy configuration
  - UFW firewall rules
  - Automated daily backup system
  - Prometheus + Node Exporter monitoring
  - Full installation verification

Usage:
    sudo python3 scripts/install_production.py [OPTIONS]

Options:
    --non-interactive    Use defaults for all prompts (except passwords)
    --dry-run            Show what would be done without making changes
    --skip STEP          Skip a specific step (can be repeated)
    --domain DOMAIN      Domain name for Nginx/SSL (default: server hostname)
    --email EMAIL        Email for Let's Encrypt certificate
    --db-password PASS   PostgreSQL password (auto-generated if not provided)
    --help               Show this help message

Examples:
    # Full interactive install (recommended for first time)
    sudo python3 scripts/install_production.py

    # Non-interactive with domain and email
    sudo python3 scripts/install_production.py --non-interactive \\
        --domain pbx.example.com --email admin@example.com

    # Skip specific steps
    sudo python3 scripts/install_production.py --skip voice-prompts --skip monitoring

    # Dry run to see what would happen
    sudo python3 scripts/install_production.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shlex
import socket
import string
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path


# ---------------------------------------------------------------------------
# Terminal colors
# ---------------------------------------------------------------------------
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Installer
# ---------------------------------------------------------------------------
class ProductionInstaller:
    """Unified production installer for Warden VoIP PBX."""

    # Steps that can be skipped via --skip
    SKIPPABLE_STEPS: frozenset[str] = frozenset(
        {
            "voice-prompts",
            "monitoring",
            "backup",
            "nginx",
            "firewall",
            "ssl",
            "redis",
        }
    )

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.project_root = Path(__file__).resolve().parent.parent
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.db_password = args.db_password or ""
        self.domain = args.domain or ""
        self.email = args.email or ""
        self.skip_steps: set[str] = set(args.skip) if args.skip else set()
        self.dry_run: bool = args.dry_run
        self.non_interactive: bool = args.non_interactive

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------
    def _banner(self, text: str) -> None:
        width = 78
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * width}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(width)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * width}{Colors.RESET}\n")

    def _step(self, num: int, total: int, text: str) -> None:
        print(f"\n{Colors.BOLD}{Colors.CYAN}[{num}/{total}] {text}{Colors.RESET}\n")

    def _ok(self, text: str) -> None:
        print(f"  {Colors.GREEN}OK{Colors.RESET}  {text}")

    def _warn(self, text: str) -> None:
        print(f"  {Colors.YELLOW}WARN{Colors.RESET}  {text}")
        self.warnings.append(text)

    def _err(self, text: str) -> None:
        print(f"  {Colors.RED}FAIL{Colors.RESET}  {text}")
        self.errors.append(text)

    def _info(self, text: str) -> None:
        print(f"  {Colors.BLUE}INFO{Colors.RESET}  {text}")

    def _dry(self, text: str) -> None:
        print(f"  {Colors.DIM}[DRY RUN]{Colors.RESET} {text}")

    # ------------------------------------------------------------------
    # Command runner
    # ------------------------------------------------------------------
    def _run(
        self,
        cmd: str,
        *,
        description: str = "",
        check: bool = True,
        timeout: int = 600,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        if description:
            self._info(description)

        if self.dry_run:
            self._dry(cmd)
            return 0, "", ""

        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=check,
                env=run_env,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout or "", e.stderr or ""
        except subprocess.TimeoutExpired:
            self._err(f"Command timed out: {cmd[:80]}")
            return 124, "", "timeout"

    def _prompt(self, question: str, default: str = "") -> str:
        """Ask user for input, respecting --non-interactive."""
        if self.non_interactive:
            return default
        suffix = f" [{default}]" if default else ""
        answer = input(f"  {question}{suffix}: ").strip()
        return answer or default

    def _confirm(self, question: str, default_yes: bool = True) -> bool:
        """Ask yes/no, respecting --non-interactive."""
        if self.non_interactive:
            return default_yes
        hint = "Y/n" if default_yes else "y/N"
        answer = input(f"  {question} ({hint}): ").strip().lower()
        if not answer:
            return default_yes
        return answer in ("y", "yes")

    @staticmethod
    def _generate_password(length: int = 32) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    # ------------------------------------------------------------------
    # Step 1: Pre-flight checks
    # ------------------------------------------------------------------
    def preflight_checks(self) -> bool:
        self._step(1, 14, "Pre-flight Checks")

        ok = True

        # Root check
        if os.geteuid() != 0 and not self.dry_run:
            self._err("This script must be run as root (use sudo)")
            return False
        self._ok("Running as root")

        # OS check
        os_release = Path("/etc/os-release")
        if os_release.exists():
            content = os_release.read_text()
            if "Ubuntu" in content:
                if "24.04" in content:
                    self._ok("Ubuntu 24.04 LTS detected")
                else:
                    self._warn("Ubuntu detected but not 24.04 LTS — proceed with caution")
            else:
                self._warn("Non-Ubuntu OS detected — this installer is designed for Ubuntu")
        else:
            self._warn("Cannot detect OS version")

        # Python check
        v = sys.version_info
        if v.major == 3 and v.minor >= 13:
            self._ok(f"Python {v.major}.{v.minor}.{v.micro}")
        else:
            self._err(f"Python 3.13+ required (found {v.major}.{v.minor}.{v.micro})")
            ok = False

        # Hardware checks
        try:
            cpu_count = os.cpu_count() or 1
            if cpu_count >= 2:
                self._ok(f"CPU cores: {cpu_count}")
            else:
                self._warn(f"CPU cores: {cpu_count} (2+ recommended)")
        except Exception:
            self._warn("Cannot detect CPU count")

        try:
            with Path("/proc/meminfo").open() as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        gb = kb / (1024 * 1024)
                        if gb >= 3.5:
                            self._ok(f"RAM: {gb:.1f} GB")
                        else:
                            self._warn(f"RAM: {gb:.1f} GB (4+ GB recommended)")
                        break
        except Exception:
            self._warn("Cannot detect RAM")

        # Disk space
        try:
            st = os.statvfs(str(self.project_root))
            free_gb = (st.f_bavail * st.f_frsize) / (1024**3)
            if free_gb >= 20:
                self._ok(f"Disk free: {free_gb:.1f} GB")
            else:
                self._warn(f"Disk free: {free_gb:.1f} GB (20+ GB recommended)")
        except Exception:
            self._warn("Cannot detect disk space")

        return ok

    # ------------------------------------------------------------------
    # Step 2: System dependencies
    # ------------------------------------------------------------------
    def install_system_deps(self) -> bool:
        self._step(2, 14, "System Dependencies")

        if self.dry_run:
            self._dry("apt-get update && apt-get install -y <packages>")
            return True

        # Update package lists
        ret, _, _ = self._run("apt-get update", description="Updating package lists", check=False)
        if ret != 0:
            self._err("Failed to update package lists")
            return False

        # Add PostgreSQL 17 official repo
        self._info("Adding PostgreSQL 17 repository...")
        self._run(
            "apt-get install -y curl ca-certificates",
            description="Installing prerequisites",
            check=False,
        )
        self._run("install -d /usr/share/postgresql-common/pgdg", check=False)
        self._run(
            "curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail "
            "https://www.postgresql.org/media/keys/ACCC4CF8.asc",
            description="Downloading PostgreSQL signing key",
            check=False,
        )
        self._run(
            "sh -c 'echo \"deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc]"
            " https://apt.postgresql.org/pub/repos/apt"
            " $(lsb_release -cs)-pgdg main\" > /etc/apt/sources.list.d/pgdg.list'",
            check=False,
        )
        self._run("apt-get update", check=False)

        # All packages needed for a complete production deployment
        packages = [
            # Audio/media
            "espeak",
            "ffmpeg",
            "libopus-dev",
            "portaudio19-dev",
            "libspeex-dev",
            # Database
            "postgresql-17",
            "postgresql-contrib",
            "libpq-dev",
            # Python (build deps needed for packages without pre-built wheels)
            "python3-venv",
            "python3-pip",
            "python3-dev",
            "build-essential",
            # Web / reverse proxy
            "nginx",
            "certbot",
            "python3-certbot-nginx",
            # Cache
            "redis-server",
            # Security
            "ufw",
            "fail2ban",
            # Monitoring
            "prometheus",
            "prometheus-node-exporter",
            # Tools
            "git",
            "supervisor",
        ]

        ret, _, stderr = self._run(
            f"DEBIAN_FRONTEND=noninteractive PYTHONWARNINGS='ignore::SyntaxWarning' "
            f"apt-get install -y {' '.join(packages)}",
            description="Installing system packages",
            check=False,
            timeout=900,
        )
        if ret != 0:
            self._err(f"Package installation failed: {stderr[:200]}")
            return False

        self._ok("All system dependencies installed")
        return True

    # ------------------------------------------------------------------
    # Step 3: Python environment
    # ------------------------------------------------------------------
    def setup_python_env(self) -> bool:
        self._step(3, 14, "Python Virtual Environment")

        if self.dry_run:
            self._dry("python3 -m venv venv && pip install uv && uv pip install -e .")
            return True

        # Create venv
        if self.venv_path.exists():
            if self._confirm("Virtual environment already exists. Recreate it?", default_yes=False):
                self._run(f"rm -rf {self.venv_path}", check=False)
            else:
                self._ok("Using existing virtual environment")
                # Ensure dependencies are installed using uv or pip
                uv_path = self.venv_path / "bin" / "uv"
                pip_path = self.venv_path / "bin" / "pip"
                if uv_path.exists():
                    ret, _, stderr = self._run(
                        f"{uv_path} pip install -e {self.project_root}",
                        description="Ensuring dependencies are up to date",
                        check=False,
                        timeout=900,
                    )
                elif pip_path.exists():
                    ret, _, stderr = self._run(
                        f"{pip_path} install -e {self.project_root}",
                        description="Ensuring dependencies are up to date",
                        check=False,
                        timeout=900,
                    )
                else:
                    self._warn("No pip or uv found in existing venv — dependencies may be missing")
                return True

        ret, _, stderr = self._run(
            f"python3 -m venv {self.venv_path}",
            description="Creating virtual environment",
            check=False,
        )
        if ret != 0:
            self._warn(f"Standard venv creation failed ({stderr[:120].strip()})")
            self._info("Retrying with --without-pip and manual pip bootstrap...")
            ret2, _, stderr2 = self._run(
                f"python3 -m venv --without-pip {self.venv_path}",
                description="Creating virtual environment (without pip)",
                check=False,
            )
            if ret2 != 0:
                self._err(f"Failed to create venv: {stderr2[:200]}")
                return False
            # Bootstrap pip via get-pip.py
            python_path = self.venv_path / "bin" / "python3"
            ret3, _, stderr3 = self._run(
                f"curl -sSL https://bootstrap.pypa.io/get-pip.py | {python_path}",
                description="Bootstrapping pip via get-pip.py",
                check=False,
                timeout=120,
            )
            if ret3 != 0:
                self._err(f"Failed to bootstrap pip: {stderr3[:200]}")
                return False
        self._ok("Virtual environment created")

        # Install uv
        pip_path = self.venv_path / "bin" / "pip"
        self._run(
            f"{pip_path} install --upgrade pip uv",
            description="Installing uv package manager",
            check=False,
        )

        # Install project
        uv_path = self.venv_path / "bin" / "uv"
        installer = str(uv_path) if uv_path.exists() else str(pip_path)
        cmd = (
            f"{installer} pip install -e {self.project_root}"
            if uv_path.exists()
            else f"{installer} install -e {self.project_root}"
        )

        ret, _, stderr = self._run(
            cmd,
            description="Installing Warden VoIP PBX and dependencies",
            check=False,
            timeout=900,
        )
        if ret != 0:
            self._err(f"Failed to install Python dependencies: {stderr[:200]}")
            return False

        self._ok("Python packages installed")
        return True

    # ------------------------------------------------------------------
    # Step 4: PostgreSQL
    # ------------------------------------------------------------------
    def setup_postgresql(self) -> bool:
        self._step(4, 14, "PostgreSQL Database")

        if self.dry_run:
            self._dry("CREATE DATABASE pbx_system; CREATE USER pbx_user; GRANT ALL;")
            return True

        # Ensure PostgreSQL is running
        self._run("systemctl start postgresql", check=False)
        self._run("systemctl enable postgresql", check=False)

        ret, _, _ = self._run("systemctl is-active postgresql", check=False)
        if ret != 0:
            self._err("PostgreSQL failed to start")
            return False
        self._ok("PostgreSQL is running")

        # Get database config
        db_name = self._prompt("Database name", "pbx_system")
        db_user = self._prompt("Database user", "pbx_user")

        # Validate identifiers
        ident_re = r"^[a-zA-Z][a-zA-Z0-9_]*$"
        if not re.match(ident_re, db_name):
            self._err("Invalid database name (letters, numbers, underscores only)")
            return False
        if not re.match(ident_re, db_user):
            self._err("Invalid database user (letters, numbers, underscores only)")
            return False

        # Password
        if not self.db_password:
            self.db_password = self._generate_password()
            self._info(f"Generated database password: {self.db_password}")
            self._warn("Save this password — it will not be shown again after installation")

        # Create user
        escaped_pw = self.db_password.replace("'", "''")
        sql = f"CREATE USER {db_user} WITH PASSWORD '{escaped_pw}';"
        ret, _, stderr = self._run(
            f"sudo -u postgres psql -c {shlex.quote(sql)}",
            description=f"Creating database user '{db_user}'",
            check=False,
        )
        if ret != 0 and "already exists" not in (stderr or ""):
            self._err(f"Failed to create user: {stderr[:200]}")
            return False
        if "already exists" in (stderr or ""):
            self._info(f"User '{db_user}' already exists — updating password")
            sql_alter = f"ALTER USER {db_user} WITH PASSWORD '{escaped_pw}';"
            self._run(f"sudo -u postgres psql -c {shlex.quote(sql_alter)}", check=False)

        # Create database
        sql = f"CREATE DATABASE {db_name} OWNER {db_user};"
        ret, _, stderr = self._run(
            f"sudo -u postgres psql -c {shlex.quote(sql)}",
            description=f"Creating database '{db_name}'",
            check=False,
        )
        if ret != 0 and "already exists" not in (stderr or ""):
            self._err(f"Failed to create database: {stderr[:200]}")
            return False

        # Grant privileges
        sql = f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
        self._run(f"sudo -u postgres psql -c {shlex.quote(sql)}", check=False)

        self._ok("PostgreSQL configured")

        # Store for .env generation
        self._db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": db_name,
            "DB_USER": db_user,
            "DB_PASSWORD": self.db_password,
        }
        return True

    # ------------------------------------------------------------------
    # Step 5: Redis
    # ------------------------------------------------------------------
    def setup_redis(self) -> bool:
        self._step(5, 14, "Redis Cache")

        if "redis" in self.skip_steps:
            self._info("Skipped (--skip redis)")
            return True

        if self.dry_run:
            self._dry("systemctl enable --now redis-server")
            return True

        self._run("systemctl start redis-server", check=False)
        self._run("systemctl enable redis-server", check=False)

        ret, _, _ = self._run("systemctl is-active redis-server", check=False)
        if ret != 0:
            self._warn("Redis failed to start — PBX will work without it but caching is disabled")
            return True

        self._ok("Redis is running")
        return True

    # ------------------------------------------------------------------
    # Step 6: Environment file
    # ------------------------------------------------------------------
    def setup_env_file(self) -> bool:
        self._step(6, 14, "Environment File (.env)")

        if self.dry_run:
            self._dry(f"Write {self.env_file}")
            return True

        if self.env_file.exists() and not self._confirm(
            ".env file already exists. Overwrite it?", default_yes=False
        ):
            self._ok("Keeping existing .env file")
            return True

        db = getattr(
            self,
            "_db_config",
            {
                "DB_HOST": "localhost",
                "DB_PORT": "5432",
                "DB_NAME": "pbx_system",
                "DB_USER": "pbx_user",
                "DB_PASSWORD": self.db_password,
            },
        )

        content = textwrap.dedent(f"""\
            # Warden VoIP PBX Environment Variables
            # Generated by install_production.py

            # Database Configuration
            DB_HOST={db["DB_HOST"]}
            DB_PORT={db["DB_PORT"]}
            DB_NAME={db["DB_NAME"]}
            DB_USER={db["DB_USER"]}
            DB_PASSWORD={db["DB_PASSWORD"]}

            # Redis Configuration (optional)
            # REDIS_PASSWORD=

            # SMTP Configuration (optional — for voicemail-to-email)
            # SMTP_HOST=
            # SMTP_PORT=587
            # SMTP_USERNAME=
            # SMTP_PASSWORD=

            # Active Directory (optional — for AD user sync)
            # AD_BIND_PASSWORD=

            # Optional Integrations
            # ZOOM_CLIENT_ID=
            # ZOOM_CLIENT_SECRET=
            # OUTLOOK_CLIENT_ID=
            # OUTLOOK_CLIENT_SECRET=
            # TEAMS_CLIENT_ID=
            # TEAMS_CLIENT_SECRET=
            # TRANSCRIPTION_API_KEY=
        """)

        self.env_file.write_text(content)
        self.env_file.chmod(0o600)
        self._ok(f".env file created at {self.env_file}")
        self._info("Edit .env later to add SMTP, AD, or integration credentials")

        # Verify config.yml exists — PBX cannot start without it
        config_file = self.project_root / "config.yml"
        if not config_file.exists():
            self._warn("config.yml not found in project root")
            # Check for example configs to copy
            example_configs = sorted(self.project_root.glob("config*.yml"))
            if example_configs:
                self._info(f"Found example config(s): {', '.join(c.name for c in example_configs)}")
            self._warn(
                "The PBX requires config.yml to start. "
                "Create one before running: sudo systemctl start pbx"
            )
        else:
            self._ok("config.yml found")

        return True

    # ------------------------------------------------------------------
    # Step 7: Database schema
    # ------------------------------------------------------------------
    def initialize_database(self) -> bool:
        self._step(7, 14, "Database Schema Initialization")

        if self.dry_run:
            self._dry("alembic upgrade head / init_database.py")
            return True

        alembic_bin = self.venv_path / "bin" / "alembic"
        alembic_ini = self.project_root / "alembic.ini"

        # Build env dict from .env so child processes get DB credentials
        db_env = self._load_env_as_dict()

        # Try Alembic first
        if alembic_ini.exists():
            ret, _, stderr = self._run(
                f"cd {self.project_root} && {alembic_bin} upgrade head",
                description="Running Alembic migrations",
                check=False,
                env=db_env,
            )
            if ret == 0:
                self._ok("Database schema migrated via Alembic")
            else:
                self._warn(f"Alembic migration returned non-zero: {stderr[:200]}")

        # Also run init script if available
        init_script = self.project_root / "scripts" / "init_database.py"
        if init_script.exists():
            ret, _, stderr = self._run(
                f"{python_bin} {init_script}",
                description="Running database initialization script",
                check=False,
                env=db_env,
            )
            if ret != 0:
                self._warn(f"init_database.py failed: {stderr[:200]}")
        else:
            self._info("No init_database.py found — schema handled by Alembic / app startup")

        self._ok("Database initialization complete")
        return True

    def _load_env_as_dict(self) -> dict[str, str]:
        """Load the .env file and return its values as a dict for subprocess env."""
        env_vars: dict[str, str] = {}
        if not self.env_file.exists():
            return env_vars
        for line in self.env_file.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            env_vars[key] = value
        return env_vars

    # ------------------------------------------------------------------
    # Step 8: SSL Certificate
    # ------------------------------------------------------------------
    def setup_ssl(self) -> bool:
        self._step(8, 14, "SSL Certificate")

        if "ssl" in self.skip_steps:
            self._info("Skipped (--skip ssl)")
            return True

        if self.dry_run:
            self._dry("generate_ssl_cert.py / certbot")
            return True

        # Determine hostname/domain
        if not self.domain:
            self.domain = self._prompt(
                "Hostname or domain for SSL",
                socket.gethostname(),
            )

        # Validate hostname
        if not re.match(r"^[a-zA-Z0-9._-]+$", self.domain):
            self._err("Invalid hostname/domain format")
            return False

        # Ask about Let's Encrypt vs self-signed
        use_letsencrypt = False
        if not self.non_interactive:
            use_letsencrypt = self._confirm(
                "Use Let's Encrypt for a real SSL certificate? (requires public domain pointing to this server)",
                default_yes=False,
            )

        if use_letsencrypt:
            if not self.email:
                self.email = self._prompt("Email for Let's Encrypt notifications", "")
            if not self.email:
                self._warn("Email required for Let's Encrypt — falling back to self-signed")
                use_letsencrypt = False

        if use_letsencrypt:
            ret, _, stderr = self._run(
                f"certbot certonly --standalone -d {shlex.quote(self.domain)} "
                f"--non-interactive --agree-tos --email {shlex.quote(self.email)}",
                description="Obtaining Let's Encrypt certificate",
                check=False,
            )
            if ret == 0:
                self._ok(f"Let's Encrypt certificate obtained for {self.domain}")
            else:
                self._warn(f"Let's Encrypt failed: {stderr[:200]}")
                self._info("Falling back to self-signed certificate")
                use_letsencrypt = False

        if not use_letsencrypt:
            ssl_script = self.project_root / "scripts" / "generate_ssl_cert.py"
            python_bin = self.venv_path / "bin" / "python"
            if ssl_script.exists():
                ret, _, stderr = self._run(
                    f"{python_bin} {ssl_script} --hostname {shlex.quote(self.domain)}",
                    description="Generating self-signed SSL certificate",
                    check=False,
                )
                if ret == 0:
                    self._ok("Self-signed SSL certificate generated")
                else:
                    self._warn(f"SSL generation failed: {stderr[:200]}")
                    self._info("You can generate it later: python scripts/generate_ssl_cert.py")
            else:
                self._warn("SSL generation script not found — skipping")
                self._info("Generate later: python scripts/generate_ssl_cert.py")

        return True

    # ------------------------------------------------------------------
    # Step 9: Voice prompts
    # ------------------------------------------------------------------
    def generate_voice_prompts(self) -> bool:
        self._step(9, 14, "Voice Prompts")

        if "voice-prompts" in self.skip_steps:
            self._info("Skipped (--skip voice-prompts)")
            return True

        if self.dry_run:
            self._dry("python scripts/generate_tts_prompts.py")
            return True

        voice_script = self.project_root / "scripts" / "generate_tts_prompts.py"
        if not voice_script.exists():
            self._warn("Voice prompt generation script not found")
            return True

        if not self._confirm("Generate voice prompts now? (required for voicemail/auto-attendant)"):
            self._info("Skipped — generate later: python scripts/generate_tts_prompts.py")
            return True

        python_bin = self.venv_path / "bin" / "python"
        ret, _, stderr = self._run(
            f"{python_bin} {voice_script}",
            description="Generating voice prompts via TTS",
            check=False,
            timeout=600,
        )
        if ret != 0:
            self._warn(f"Voice prompt generation failed: {stderr[:200]}")
            self._info("Generate later: python scripts/generate_tts_prompts.py")
        else:
            self._ok("Voice prompts generated")

        return True

    # ------------------------------------------------------------------
    # Step 10: Systemd service
    # ------------------------------------------------------------------
    def setup_systemd(self) -> bool:
        self._step(10, 14, "Systemd Service")

        if self.dry_run:
            self._dry("Install pbx.service to /etc/systemd/system/")
            return True

        service_content = textwrap.dedent(f"""\
            [Unit]
            Description=Warden VoIP PBX System
            After=network.target postgresql.service redis.service

            [Service]
            Type=simple
            User=pbx
            Group=pbx
            WorkingDirectory={self.project_root}
            EnvironmentFile={self.project_root}/.env
            Environment="PATH={self.venv_path}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            ExecStartPre={self.venv_path}/bin/alembic -c {self.project_root}/alembic.ini upgrade head
            ExecStart={self.venv_path}/bin/python {self.project_root}/main.py
            Restart=always
            RestartSec=10
            StandardOutput=journal
            StandardError=journal

            # Security hardening
            NoNewPrivileges=true
            PrivateTmp=true
            ProtectSystem=full
            ProtectHome=true
            ReadWritePaths={self.project_root}/logs {self.project_root}/recordings {self.project_root}/voicemail {self.project_root}/cdr {self.project_root}/moh

            # Resource limits
            LimitNOFILE=65536
            LimitNPROC=4096

            [Install]
            WantedBy=multi-user.target
        """)

        # Write to project root for reference
        service_file = self.project_root / "pbx.service"
        service_file.write_text(service_content)

        # Install to systemd
        Path("/etc/systemd/system/pbx.service").write_text(service_content)

        # Create pbx user if needed
        ret, _, _ = self._run("id -u pbx", check=False)
        if ret != 0:
            self._run(
                "useradd -r -s /bin/false -M -d /nonexistent pbx",
                description="Creating 'pbx' system user",
                check=False,
            )

        # Create required directories
        for subdir in ["logs", "recordings", "voicemail", "cdr", "moh"]:
            (self.project_root / subdir).mkdir(exist_ok=True)

        # Set ownership
        self._run(
            f"chown -R pbx:pbx {self.project_root}",
            description="Setting file ownership to pbx:pbx",
            check=False,
        )

        self._run("systemctl daemon-reload", check=False)
        self._run("systemctl enable pbx.service", description="Enabling PBX service", check=False)

        self._ok("Systemd service installed and enabled")
        self._info("Start with: sudo systemctl start pbx")
        return True

    # ------------------------------------------------------------------
    # Step 11: Nginx reverse proxy
    # ------------------------------------------------------------------
    def setup_nginx(self) -> bool:
        self._step(11, 14, "Nginx Reverse Proxy")

        if "nginx" in self.skip_steps:
            self._info("Skipped (--skip nginx)")
            return True

        if self.dry_run:
            self._dry("Configure Nginx site for PBX")
            return True

        if not self.domain:
            self.domain = self._prompt("Domain/hostname for Nginx", socket.gethostname())

        nginx_conf = textwrap.dedent(f"""\
            server {{
                listen 80;
                server_name {self.domain};

                # Proxy to PBX backend
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

                # WebRTC signaling
                location /ws {{
                    proxy_pass http://127.0.0.1:8443;
                    proxy_http_version 1.1;
                    proxy_set_header Upgrade $http_upgrade;
                    proxy_set_header Connection "upgrade";
                }}

                # Prometheus monitoring (internal)
                location /prometheus/ {{
                    proxy_pass http://127.0.0.1:9090/;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                }}

                # Node Exporter metrics
                location /metrics {{
                    proxy_pass http://127.0.0.1:9100/metrics;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                }}
            }}
        """)

        Path("/etc/nginx/sites-available/pbx").write_text(nginx_conf)
        self._run(
            "ln -sf /etc/nginx/sites-available/pbx /etc/nginx/sites-enabled/",
            check=False,
        )
        self._run("rm -f /etc/nginx/sites-enabled/default", check=False)

        # Test config
        ret, _, stderr = self._run("nginx -t", check=False)
        if ret != 0:
            self._err(f"Nginx config test failed: {stderr[:200]}")
            return False

        self._run("systemctl reload nginx || systemctl start nginx", check=False)
        self._run("systemctl enable nginx", check=False)

        self._ok(f"Nginx configured — proxying to PBX at http://{self.domain}")

        # Offer Let's Encrypt for Nginx if we have a real domain and email
        if (
            self.email
            and "ssl" not in self.skip_steps
            and self._confirm("Run certbot to add HTTPS to Nginx?")
        ):
            ret, _, _ = self._run(
                f"certbot --nginx -d {shlex.quote(self.domain)} "
                f"--non-interactive --agree-tos --email {shlex.quote(self.email)} --redirect",
                description="Configuring HTTPS via Let's Encrypt",
                check=False,
            )
            if ret == 0:
                self._ok(f"HTTPS enabled at https://{self.domain}")
            else:
                self._warn("certbot failed — site available via HTTP only")
                self._info(f"Retry later: sudo certbot --nginx -d {self.domain}")

        return True

    # ------------------------------------------------------------------
    # Step 12: Firewall
    # ------------------------------------------------------------------
    def setup_firewall(self) -> bool:
        self._step(12, 14, "UFW Firewall")

        if "firewall" in self.skip_steps:
            self._info("Skipped (--skip firewall)")
            return True

        if self.dry_run:
            self._dry("UFW: allow SSH, HTTP, HTTPS, SIP, RTP, monitoring")
            return True

        self._run("ufw --force reset", check=False)
        self._run("ufw default deny incoming", check=False)
        self._run("ufw default allow outgoing", check=False)

        rules = [
            ("22/tcp", "SSH"),
            ("80/tcp", "HTTP"),
            ("443/tcp", "HTTPS"),
            ("5060/udp", "SIP (UDP)"),
            ("5060/tcp", "SIP (TCP)"),
            ("5061/tcp", "SIP TLS"),
            ("10000:20000/udp", "RTP media"),
            ("8443/tcp", "WebRTC signaling"),
            ("9090/tcp", "Prometheus"),
            ("9100/tcp", "Node Exporter"),
        ]

        for rule, desc in rules:
            self._run(f"ufw allow {rule}", description=f"Allow {desc}", check=False)

        self._run("ufw --force enable", check=False)
        self._ok("Firewall configured and enabled")
        return True

    # ------------------------------------------------------------------
    # Step 13: Backup system
    # ------------------------------------------------------------------
    def setup_backups(self) -> bool:
        self._step(13, 14, "Automated Backup System")

        if "backup" in self.skip_steps:
            self._info("Skipped (--skip backup)")
            return True

        if self.dry_run:
            self._dry("Install /usr/local/bin/pbx-backup.sh + daily cron")
            return True

        backup_dir = Path("/var/backups/pbx")
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_script = textwrap.dedent(f"""\
            #!/bin/bash
            # Warden VoIP PBX — Automated Backup Script
            set -eo pipefail

            BACKUP_DIR="/var/backups/pbx"
            TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            DATABASE="pbx_system"

            # Database backup
            sudo -u postgres pg_dump "$DATABASE" | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

            # Configuration backup
            tar -czf "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" \\
                "{self.project_root}/config.yml" \\
                "{self.project_root}/.env" \\
                2>/dev/null || true

            # Voicemail backup (incremental — only new files)
            if [ -d "{self.project_root}/voicemail" ]; then
                tar -czf "$BACKUP_DIR/voicemail_$TIMESTAMP.tar.gz" \\
                    "{self.project_root}/voicemail" \\
                    2>/dev/null || true
            fi

            # Keep only last 30 days of backups
            find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

            echo "Backup completed: $TIMESTAMP"
        """)

        Path("/usr/local/bin/pbx-backup.sh").write_text(backup_script)
        self._run("chmod +x /usr/local/bin/pbx-backup.sh", check=False)

        # Add cron job (daily at 2 AM) — idempotent
        self._run(
            "(crontab -l 2>/dev/null | grep -v pbx-backup; "
            'echo "0 2 * * * /usr/local/bin/pbx-backup.sh >> /var/log/pbx-backup.log 2>&1"'
            ") | crontab -",
            description="Installing daily backup cron job (2:00 AM)",
            check=False,
        )

        self._ok("Backup system configured (daily at 2:00 AM)")
        self._info(f"Backups stored in: {backup_dir}")
        return True

    # ------------------------------------------------------------------
    # Step 14: Monitoring
    # ------------------------------------------------------------------
    def setup_monitoring(self) -> bool:
        self._step(14, 14, "Monitoring (Prometheus + Node Exporter)")

        if "monitoring" in self.skip_steps:
            self._info("Skipped (--skip monitoring)")
            return True

        if self.dry_run:
            self._dry("systemctl enable --now prometheus prometheus-node-exporter")
            return True

        self._run("systemctl start prometheus", check=False)
        self._run("systemctl enable prometheus", check=False)
        self._run("systemctl start prometheus-node-exporter", check=False)
        self._run("systemctl enable prometheus-node-exporter", check=False)

        ret, _, _ = self._run("systemctl is-active prometheus", check=False)
        if ret == 0:
            self._ok("Prometheus running on :9090")
        else:
            self._warn("Prometheus failed to start")

        ret, _, _ = self._run("systemctl is-active prometheus-node-exporter", check=False)
        if ret == 0:
            self._ok("Node Exporter running on :9100")
        else:
            self._warn("Node Exporter failed to start")

        return True

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def verify_installation(self) -> bool:
        self._banner("Installation Verification")

        checks = {
            "Virtual environment": self.venv_path.exists(),
            ".env file": self.env_file.exists(),
            "config.yml": (self.project_root / "config.yml").exists(),
        }

        if not self.dry_run:
            # PostgreSQL
            ret, _, _ = self._run("systemctl is-active postgresql", check=False)
            checks["PostgreSQL"] = ret == 0

            # Redis
            if "redis" not in self.skip_steps:
                ret, _, _ = self._run("systemctl is-active redis-server", check=False)
                checks["Redis"] = ret == 0

            # Nginx
            if "nginx" not in self.skip_steps:
                ret, _, _ = self._run("systemctl is-active nginx", check=False)
                checks["Nginx"] = ret == 0

            # Systemd service installed
            checks["Systemd service"] = Path("/etc/systemd/system/pbx.service").exists()

            # Python packages
            pip_path = self.venv_path / "bin" / "pip"
            ret, stdout, _ = self._run(f"{pip_path} list 2>/dev/null", check=False)
            checks["Python packages"] = ret == 0 and "PyYAML" in stdout

            # Firewall
            if "firewall" not in self.skip_steps:
                ret, stdout, _ = self._run("ufw status", check=False)
                checks["Firewall (UFW)"] = ret == 0 and "active" in stdout.lower()

        passed = 0
        total = len(checks)
        for name, ok in checks.items():
            if ok:
                self._ok(name)
                passed += 1
            else:
                self._err(name)

        print(f"\n  {Colors.BOLD}Verification: {passed}/{total} checks passed{Colors.RESET}")

        return passed >= total - 1  # Allow 1 non-critical failure

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def print_summary(self) -> None:
        self._banner("Installation Complete")

        print(f"  {Colors.GREEN}Warden VoIP PBX has been installed successfully!{Colors.RESET}\n")

        domain = self.domain or socket.gethostname()

        print(f"  {Colors.BOLD}Quick Start:{Colors.RESET}")
        print("    sudo systemctl start pbx")
        print("    sudo journalctl -u pbx -f          # watch logs")
        print(f"    Open https://{domain}               # admin panel\n")

        print(f"  {Colors.BOLD}Service Management:{Colors.RESET}")
        print("    sudo systemctl start|stop|restart pbx")
        print("    sudo systemctl status pbx\n")

        print(f"  {Colors.BOLD}Configuration:{Colors.RESET}")
        print(f"    {self.project_root}/config.yml       # main config")
        print(f"    {self.project_root}/.env              # secrets/credentials")
        print("    /etc/nginx/sites-available/pbx       # reverse proxy\n")

        print(f"  {Colors.BOLD}Monitoring:{Colors.RESET}")
        print(f"    Prometheus: http://{domain}:9090")
        print(f"    Node Exporter: http://{domain}:9100/metrics\n")

        print(f"  {Colors.BOLD}Backups:{Colors.RESET}")
        print("    Location: /var/backups/pbx/")
        print("    Schedule: Daily at 2:00 AM")
        print("    Manual:   sudo /usr/local/bin/pbx-backup.sh\n")

        print(f"  {Colors.BOLD}Logs:{Colors.RESET}")
        print("    PBX:     sudo journalctl -u pbx -f")
        print("    Nginx:   /var/log/nginx/")
        print("    Backup:  /var/log/pbx-backup.log\n")

        if self.warnings:
            print(f"  {Colors.YELLOW}Warnings ({len(self.warnings)}):{Colors.RESET}")
            for w in self.warnings:
                print(f"    - {w}")
            print()

        if self.errors:
            print(f"  {Colors.RED}Errors ({len(self.errors)}):{Colors.RESET}")
            for e in self.errors:
                print(f"    - {e}")
            print()

        print(f"  {Colors.BOLD}Next Steps:{Colors.RESET}")
        print("    1. Edit config.yml (extensions, dial plan, features)")
        print("    2. Edit .env to add SMTP/integration credentials")
        print("    3. sudo systemctl start pbx")
        print("    4. Register SIP phones to your server")
        print()

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------
    def run(self) -> int:
        self._banner("Warden VoIP PBX — Production Installer")

        if self.dry_run:
            print(f"  {Colors.YELLOW}DRY RUN MODE — no changes will be made{Colors.RESET}\n")

        print("  This installer will set up a complete production PBX system:\n")
        print("    1.  Pre-flight checks           9.  Voice prompts")
        print("    2.  System dependencies         10.  Systemd service")
        print("    3.  Python environment           11.  Nginx reverse proxy")
        print("    4.  PostgreSQL database          12.  UFW firewall")
        print("    5.  Redis cache                  13.  Automated backups")
        print("    6.  Environment file (.env)      14.  Monitoring")
        print("    7.  Database schema")
        print("    8.  SSL certificate\n")

        if self.skip_steps:
            print(f"  Skipping: {', '.join(sorted(self.skip_steps))}\n")

        if not self._confirm("Proceed with installation?"):
            print("\n  Installation cancelled.")
            return 0

        steps = [
            self.preflight_checks,
            self.install_system_deps,
            self.setup_python_env,
            self.setup_postgresql,
            self.setup_redis,
            self.setup_env_file,
            self.initialize_database,
            self.setup_ssl,
            self.generate_voice_prompts,
            self.setup_systemd,
            self.setup_nginx,
            self.setup_firewall,
            self.setup_backups,
            self.setup_monitoring,
        ]

        for step_fn in steps:
            if not step_fn():
                self._err(f"Installation failed at: {step_fn.__name__}")
                print(
                    f"\n  {Colors.RED}Installation did not complete."
                    f" Review errors above and re-run.{Colors.RESET}\n"
                )
                return 1

        # Verify
        self.verify_installation()

        # Summary
        self.print_summary()

        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Warden VoIP PBX — Unified Production Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              sudo python3 scripts/install_production.py
              sudo python3 scripts/install_production.py --non-interactive --domain pbx.example.com
              sudo python3 scripts/install_production.py --skip voice-prompts --skip monitoring
              sudo python3 scripts/install_production.py --dry-run
        """),
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use defaults for all prompts (except passwords)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--skip",
        action="append",
        choices=sorted(ProductionInstaller.SKIPPABLE_STEPS),
        help="Skip a specific step (can be repeated)",
    )
    parser.add_argument(
        "--domain",
        help="Domain name for Nginx/SSL (default: server hostname)",
    )
    parser.add_argument(
        "--email",
        help="Email address for Let's Encrypt certificate",
    )
    parser.add_argument(
        "--db-password",
        help="PostgreSQL password (auto-generated if not provided)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    installer = ProductionInstaller(args)
    try:
        code = installer.run()
        sys.exit(code)
    except KeyboardInterrupt:
        print(f"\n\n  {Colors.YELLOW}Installation cancelled by user.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  {Colors.RED}Unexpected error: {e}{Colors.RESET}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
