#!/usr/bin/env python3
"""
Environment variable setup and validation for production deployments.

This script helps configure environment variables required for production,
validates their format, and checks for security issues.
"""

import os
import re
import sys
import secrets
from pathlib import Path


class EnvSetup:
    """Environment variable setup and validation"""
    
    def __init__(self, env_file=".env"):
        """
        Initialize environment setup.
        
        Args:
            env_file: Path to environment file
        """
        self.env_file = env_file
        self.env_example = ".env.example"
        self.variables = {}
        
    def run_interactive_setup(self):
        """Run interactive setup to configure environment variables."""
        print("=" * 70)
        print("PBX Environment Variable Setup")
        print("=" * 70)
        print()
        
        # Check if .env already exists
        if os.path.exists(self.env_file):
            response = input(f"{self.env_file} already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return False
        
        # Database configuration
        print("\n--- Database Configuration ---")
        db_type = self._prompt_choice(
            "Database type",
            ["postgresql", "sqlite"],
            default="postgresql"
        )
        
        if db_type == "postgresql":
            self.variables['DB_HOST'] = self._prompt(
                "Database host",
                default="localhost",
                validator=self._validate_hostname
            )
            self.variables['DB_PORT'] = self._prompt(
                "Database port",
                default="5432",
                validator=self._validate_port
            )
            self.variables['DB_NAME'] = self._prompt(
                "Database name",
                default="pbx_system"
            )
            self.variables['DB_USER'] = self._prompt(
                "Database user",
                default="pbx_user"
            )
            
            # Generate secure password if not provided
            db_password = input("Database password (leave empty to generate): ").strip()
            if not db_password:
                db_password = self._generate_password(32)
                print("A secure database password has been generated and will be saved to the environment file.")
            
            self.variables['DB_PASSWORD'] = db_password
        
        # SMTP configuration (optional)
        print("\n--- SMTP Configuration (Optional - for voicemail-to-email) ---")
        configure_smtp = input("Configure SMTP? (y/N): ").strip().lower() == 'y'
        
        if configure_smtp:
            self.variables['SMTP_HOST'] = self._prompt("SMTP host")
            self.variables['SMTP_PORT'] = self._prompt(
                "SMTP port",
                default="587",
                validator=self._validate_port
            )
            self.variables['SMTP_USERNAME'] = self._prompt("SMTP username")
            
            smtp_password = input("SMTP password: ").strip()
            if not smtp_password:
                print("Warning: SMTP password is empty")
            self.variables['SMTP_PASSWORD'] = smtp_password
            
            self.variables['SMTP_FROM_ADDRESS'] = self._prompt(
                "From email address",
                validator=self._validate_email
            )
        
        # API secrets
        print("\n--- API Configuration ---")
        generate_api_key = input("Generate API key? (Y/n): ").strip().lower() != 'n'
        
        if generate_api_key:
            api_key = self._generate_password(64)
            self.variables['API_SECRET_KEY'] = api_key
            print(f"Generated API key: {api_key}")
        
        # Write to file
        self._write_env_file()
        
        print()
        print("=" * 70)
        print(f"✓ Environment file created: {self.env_file}")
        print("=" * 70)
        print()
        print("IMPORTANT:")
        print(f"  • Keep {self.env_file} secure (already in .gitignore)")
        print("  • Set file permissions: chmod 600 .env")
        print("  • Backup this file securely")
        print()
        
        return True
    
    def validate_existing_env(self) -> bool:
        """
        Validate existing environment file.
        
        Returns:
            True if valid, False otherwise
        """
        if not os.path.exists(self.env_file):
            print(f"Error: {self.env_file} not found")
            return False
        
        print(f"Validating {self.env_file}...")
        print()
        
        errors = []
        warnings = []
        
        # Load existing file
        self._load_env_file()
        
        # Check required variables for PostgreSQL
        if 'DB_HOST' in self.variables:  # Assume PostgreSQL if DB_HOST is set
            required = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
            for var in required:
                if var not in self.variables or not self.variables[var]:
                    errors.append(f"Missing required variable: {var}")
        
        # Validate formats
        if 'DB_PORT' in self.variables:
            if not self._validate_port(self.variables['DB_PORT']):
                errors.append("Invalid DB_PORT (must be 1-65535)")
        
        if 'SMTP_PORT' in self.variables:
            if not self._validate_port(self.variables['SMTP_PORT']):
                errors.append("Invalid SMTP_PORT (must be 1-65535)")
        
        if 'SMTP_FROM_ADDRESS' in self.variables:
            if not self._validate_email(self.variables['SMTP_FROM_ADDRESS']):
                warnings.append("SMTP_FROM_ADDRESS may not be a valid email")
        
        # Check for weak passwords
        if 'DB_PASSWORD' in self.variables:
            password = self.variables['DB_PASSWORD']
            if len(password) < 16:
                warnings.append("DB_PASSWORD is short (< 16 characters)")
            if password.lower() in ['password', 'admin', '123456']:
                errors.append("DB_PASSWORD is too weak")
        
        # Print results
        if errors:
            print("ERRORS:")
            for error in errors:
                print(f"  ✗ {error}")
            print()
        
        if warnings:
            print("WARNINGS:")
            for warning in warnings:
                print(f"  ⚠ {warning}")
            print()
        
        if not errors and not warnings:
            print("✓ Environment validation passed")
        elif not errors:
            print("✓ Environment validation passed with warnings")
        else:
            print("✗ Environment validation failed")
        
        return len(errors) == 0
    
    def _prompt(self, name: str, default: str = "", validator=None) -> str:
        """
        Prompt for a value with optional default and validation.
        
        Args:
            name: Variable name
            default: Default value
            validator: Optional validation function
            
        Returns:
            User input or default
        """
        while True:
            prompt = f"{name}"
            if default:
                prompt += f" [{default}]"
            prompt += ": "
            
            value = input(prompt).strip() or default
            
            if validator:
                if not validator(value):
                    print(f"Invalid value for {name}")
                    continue
            
            return value
    
    def _prompt_choice(self, name: str, choices: list, default: str = "") -> str:
        """
        Prompt for a choice from a list.
        
        Args:
            name: Variable name
            choices: List of valid choices
            default: Default choice
            
        Returns:
            Selected choice
        """
        while True:
            print(f"{name} ({'/'.join(choices)})")
            value = self._prompt("Choice", default=default)
            if value in choices:
                return value
            print(f"Invalid choice. Must be one of: {', '.join(choices)}")
    
    def _validate_hostname(self, value: str) -> bool:
        """Validate hostname or IP address."""
        if not value:
            return False
        
        # Check if it's a valid IP
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, value):
            parts = value.split('.')
            return all(0 <= int(p) <= 255 for p in parts)
        
        # Check if it's a valid hostname
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(hostname_pattern, value))
    
    def _validate_port(self, value: str) -> bool:
        """Validate port number."""
        try:
            port = int(value)
            return 1 <= port <= 65535
        except ValueError:
            return False
    
    def _validate_email(self, value: str) -> bool:
        """Validate email address."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, value))
    
    def _generate_password(self, length: int = 32) -> str:
        """
        Generate a secure random password.
        
        Args:
            length: Password length
            
        Returns:
            Generated password
        """
        # Use secrets module for cryptographically secure randomness
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    def _load_env_file(self):
        """Load existing environment file."""
        self.variables = {}
        
        if not os.path.exists(self.env_file):
            return
        
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    self.variables[key.strip()] = value
    
    def _write_env_file(self):
        """Write environment variables to file."""
        # Set secure permissions first (Unix-like systems)
        try:
            # Create file with restricted permissions
            Path(self.env_file).touch(mode=0o600)
        except Exception:
            pass  # Windows doesn't support chmod
        
        with open(self.env_file, 'w') as f:
            f.write("# PBX Environment Configuration\n")
            f.write(f"# Generated on: {os.popen('date').read().strip()}\n")
            f.write("#\n")
            f.write("# SECURITY: Keep this file secure!\n")
            f.write("# - Never commit to version control\n")
            f.write("# - Set permissions: chmod 600 .env\n")
            f.write("# - Backup securely\n")
            f.write("\n")
            
            for key, value in self.variables.items():
                # Quote values with spaces
                if ' ' in value:
                    value = f'"{value}"'
                f.write(f"{key}={value}\n")


def main():
    """Main entry point"""
    setup = EnvSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "validate":
            # Validate existing .env file
            if not setup.validate_existing_env():
                sys.exit(1)
        elif command == "interactive":
            # Run interactive setup
            if not setup.run_interactive_setup():
                sys.exit(1)
        else:
            print(f"Unknown command: {command}")
            print("Usage:")
            print("  python scripts/setup_production_env.py interactive   # Interactive setup")
            print("  python scripts/setup_production_env.py validate      # Validate existing .env")
            sys.exit(1)
    else:
        # Default: interactive setup
        if not setup.run_interactive_setup():
            sys.exit(1)


if __name__ == "__main__":
    main()
