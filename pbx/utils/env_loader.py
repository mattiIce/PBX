"""
Environment Variable Loader
Securely loads sensitive configuration from environment variables
"""
import os
import re
from typing import Any, Optional

from pbx.utils.logger import get_logger


class EnvironmentLoader:
    """Load configuration values from environment variables"""

    # Pattern to match ${VAR_NAME} or $VAR_NAME in config values
    ENV_VAR_PATTERN = re.compile(r'\$\{([A-Z0-9_]+)\}|\$([A-Z0-9_]+)')

    # Default values for common environment variables
    # These are used when the environment variable is not set
    DEFAULT_VALUES = {
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'pbx_system',
        'DB_USER': 'pbx_user',
        # DB_PASSWORD has no default - must be explicitly set for PostgreSQL
        'SMTP_HOST': '',  # Empty default - set in .env if using email notifications
        'SMTP_PORT': '587',
        'SMTP_USERNAME': '',  # Empty default - set in .env if using email notifications
        # SMTP_PASSWORD has no default - must be explicitly set if using email
        # Empty default - set in .env if using voicemail transcription
        'TRANSCRIPTION_API_KEY': '',
    }

    def __init__(self):
        """Initialize environment loader"""
        self.logger = get_logger()
        self.loaded_vars = {}

    def resolve_value(self, value: Any, default: Any = None) -> Any:
        """
        Resolve a configuration value, replacing environment variable references

        Args:
            value: Configuration value (may contain ${VAR} or $VAR)
            default: Default value if environment variable not found

        Returns:
            Resolved value with environment variables substituted
        """
        if not isinstance(value, str):
            return value

        # Check if value contains environment variable reference
        matches = self.ENV_VAR_PATTERN.findall(value)
        if not matches:
            return value

        # Replace all environment variable references
        result = value
        for match in matches:
            # match is tuple: (${VAR}, $VAR) - one will be empty
            var_name = match[0] or match[1]
            env_value = os.environ.get(var_name)

            if env_value is None:
                # Try to use provided default first
                if default is not None:
                    env_value = str(default)
                    self.logger.warning(
                        f"Environment variable {var_name} not found, using provided default")
                # Fall back to class-level defaults
                elif var_name in self.DEFAULT_VALUES:
                    env_value = self.DEFAULT_VALUES[var_name]
                    self.logger.info(
                        f"Environment variable {var_name} not set, using default value")
                else:
                    self.logger.error(
                        f"Environment variable {var_name} not found and no default available")
                    # Return original value if env var not found
                    continue

            # Replace the variable reference
            if match[0]:  # ${VAR} format
                result = result.replace(f'${{{var_name}}}', env_value)
            else:  # $VAR format
                result = result.replace(f'${var_name}', env_value)

            # Track loaded vars (without exposing values)
            self.loaded_vars[var_name] = '***'

        # Try to convert to appropriate type (int, float, bool)
        # Only if the entire string is a substitution (e.g., "${DB_PORT}" not
        # "prefix_${DB_PORT}")
        if result and self._is_complete_substitution(value, matches):
            return self._try_type_conversion(result)

        return result

    def _is_complete_substitution(self, value: str, matches: list) -> bool:
        """
        Check if the value is a complete environment variable substitution
        (e.g., "${DB_PORT}") rather than a partial substitution (e.g., "prefix_${DB_PORT}")

        Args:
            value: Original value string
            matches: List of regex matches

        Returns:
            True if value is a complete substitution
        """
        # Build list of possible complete substitution patterns
        complete_patterns = []
        for match in matches:
            if match[0]:  # ${VAR} format
                complete_patterns.append(f'${{{match[0]}}}')
            if match[1]:  # $VAR format
                complete_patterns.append(f'${match[1]}')

        return value.strip() in complete_patterns

    def _try_type_conversion(self, value: str):
        """
        Try to convert string value to appropriate type (int, float, bool)

        Args:
            value: String value to convert

        Returns:
            Converted value or original string if conversion fails
        """
        # Try integer conversion
        try:
            return int(value)
        except ValueError:
            pass

        # Try float conversion
        try:
            return float(value)
        except ValueError:
            pass

        # Try boolean conversion
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False

        return value

    def resolve_config(self, config: dict) -> dict:
        """
        Recursively resolve all environment variables in a configuration dict

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with environment variables resolved
        """
        resolved = {}

        for key, value in config.items():
            if isinstance(value, dict):
                # Recursively resolve nested dictionaries
                resolved[key] = self.resolve_config(value)
            elif isinstance(value, list):
                # Resolve each item in list
                resolved[key] = [
                    self.resolve_config(item) if isinstance(item, dict)
                    else self.resolve_value(item)
                    for item in value
                ]
            else:
                # Resolve simple values
                resolved[key] = self.resolve_value(value)

        return resolved

    def get_loaded_vars(self) -> list:
        """
        Get list of environment variables that were loaded

        Returns:
            List of environment variable names (values are masked)
        """
        return list(self.loaded_vars.keys())

    def validate_required_vars(self, required_vars: list) -> tuple:
        """
        Validate that required environment variables are set

        Args:
            required_vars: List of required environment variable names

        Returns:
            Tuple of (all_present, missing_vars)
        """
        missing = []

        for var_name in required_vars:
            if var_name not in os.environ:
                missing.append(var_name)

        return len(missing) == 0, missing

    @staticmethod
    def load_env_file(env_file: str = '.env'):
        """
        Load environment variables from a .env file

        Args:
            env_file: Path to .env file

        Returns:
            Number of variables loaded
        """
        logger = get_logger()

        if not os.path.exists(env_file):
            logger.debug(f"Environment file {env_file} not found")
            return 0

        loaded_count = 0

        try:
            with open(env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip empty lines and comments
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse KEY=VALUE format
                    if '=' not in line:
                        logger.warning(
                            f"Invalid line {line_num} in {env_file}: {line}")
                        continue

                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes from value if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
                        loaded_count += 1

            if loaded_count > 0:
                logger.info(
                    f"Loaded {loaded_count} environment variables from {env_file}")

            return loaded_count

        except Exception as e:
            logger.error(f"Error loading environment file {env_file}: {e}")
            return 0


def get_env_loader() -> EnvironmentLoader:
    """Get environment loader instance"""
    return EnvironmentLoader()


def load_env_file(env_file: str = '.env') -> int:
    """Load environment variables from file"""
    return EnvironmentLoader.load_env_file(env_file)
