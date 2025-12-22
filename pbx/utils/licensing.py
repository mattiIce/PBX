#!/usr/bin/env python3
"""
Flexible Licensing and Subscription System for PBX

Features:
- Multiple license types (trial, basic, professional, enterprise, perpetual)
- Admin toggle to enable/disable licensing enforcement
- Grace periods and trial modes
- Feature gating based on license tier
- Online and offline license validation
- License key generation and validation
- Expiration tracking and notifications
"""

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """License type enumeration"""
    TRIAL = "trial"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    PERPETUAL = "perpetual"
    CUSTOM = "custom"


class LicenseStatus(Enum):
    """License status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALID = "invalid"
    GRACE_PERIOD = "grace_period"
    DISABLED = "disabled"


class LicenseManager:
    """
    Manages licensing and subscription functionality.
    
    Can be enabled/disabled by admin via configuration or environment variable.
    Supports multiple license types and feature gating.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize license manager.
        
        Args:
            config: Configuration dictionary with licensing settings
        """
        self.config = config or {}
        
        # Check if licensing is enabled
        # Can be controlled via config or environment variable
        self.enabled = self._is_licensing_enabled()
        
        # License storage path
        self.license_path = self.config.get(
            'license_file', 
            os.path.join(os.path.dirname(__file__), '..', '..', '.license')
        )
        
        # Grace period in days
        self.grace_period_days = self.config.get('grace_period_days', 7)
        
        # Trial period in days
        self.trial_period_days = self.config.get('trial_period_days', 30)
        
        # Feature definitions per license tier
        self.features = self._initialize_features()
        
        # Current license info
        self.current_license = None
        
        if self.enabled:
            logger.info("Licensing system is ENABLED")
            self._load_license()
        else:
            logger.info("Licensing system is DISABLED - all features available")
    
    def _is_licensing_enabled(self) -> bool:
        """
        Check if licensing is enabled.
        
        Checks multiple sources in order of priority:
        1. License lock file: .license_lock (if exists, licensing is mandatory)
        2. Environment variable: PBX_LICENSING_ENABLED
        3. Config file: licensing.enabled
        4. Default: False (disabled by default for open-source use)
        
        Returns:
            True if licensing should be enforced, False otherwise
        """
        # Check for license lock file (highest priority - enforces licensing)
        # This file is created when a commercial license is first installed
        # and prevents users from disabling licensing via config/env
        license_lock_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '.license_lock'
        )
        if os.path.exists(license_lock_path):
            logger.info("License lock file detected - licensing enforcement is mandatory")
            return True
        
        # Environment variable (second priority)
        env_enabled = os.getenv('PBX_LICENSING_ENABLED', '').lower()
        if env_enabled in ('true', '1', 'yes', 'on'):
            return True
        if env_enabled in ('false', '0', 'no', 'off'):
            return False
        
        # Config file (third priority)
        if 'licensing' in self.config:
            return self.config['licensing'].get('enabled', False)
        
        # Default: disabled (open-source friendly)
        return False
    
    def _initialize_features(self) -> Dict[str, List[str]]:
        """
        Initialize feature sets for each license tier.
        
        Returns:
            Dictionary mapping license types to available features
        """
        return {
            'trial': [
                'basic_calling',
                'voicemail',
                'call_recording',
                'basic_ivr',
                'max_extensions:10',
                'max_concurrent_calls:5',
            ],
            'basic': [
                'basic_calling',
                'voicemail',
                'call_recording',
                'ivr',
                'call_queues',
                'conference',
                'max_extensions:50',
                'max_concurrent_calls:25',
            ],
            'professional': [
                'basic_calling',
                'voicemail',
                'call_recording',
                'ivr',
                'call_queues',
                'conference',
                'call_parking',
                'hot_desking',
                'webrtc',
                'crm_integration',
                'ad_integration',
                'mfa',
                'max_extensions:200',
                'max_concurrent_calls:100',
            ],
            'enterprise': [
                'basic_calling',
                'voicemail',
                'call_recording',
                'ivr',
                'call_queues',
                'conference',
                'call_parking',
                'hot_desking',
                'webrtc',
                'crm_integration',
                'ad_integration',
                'mfa',
                'ai_features',
                'advanced_analytics',
                'high_availability',
                'multi_site',
                'sbc',
                'max_extensions:unlimited',
                'max_concurrent_calls:unlimited',
            ],
            'perpetual': [
                'basic_calling',
                'voicemail',
                'call_recording',
                'ivr',
                'call_queues',
                'conference',
                'call_parking',
                'hot_desking',
                'webrtc',
                'crm_integration',
                'ad_integration',
                'mfa',
                'max_extensions:unlimited',
                'max_concurrent_calls:unlimited',
            ],
            'custom': [],  # Defined per-license
        }
    
    def _load_license(self) -> None:
        """Load license from file if it exists."""
        if not os.path.exists(self.license_path):
            logger.warning(f"No license file found at {self.license_path}")
            self.current_license = None
            return
        
        try:
            with open(self.license_path, 'r') as f:
                license_data = json.load(f)
            
            # Validate and decrypt license
            self.current_license = self._validate_license(license_data)
            
            if self.current_license:
                logger.info(f"Loaded license: {self.current_license['type']} "
                          f"(expires: {self.current_license.get('expiration', 'never')})")
            else:
                logger.error("License validation failed")
        
        except Exception as e:
            logger.error(f"Error loading license: {e}")
            self.current_license = None
    
    def _validate_license(self, license_data: Dict) -> Optional[Dict]:
        """
        Validate license data.
        
        Args:
            license_data: License data to validate
        
        Returns:
            Validated license dict or None if invalid
        """
        required_fields = ['key', 'type', 'issued_to', 'issued_date']
        
        # Check required fields
        for field in required_fields:
            if field not in license_data:
                logger.error(f"Missing required field in license: {field}")
                return None
        
        # Verify license key signature
        if not self._verify_signature(license_data):
            logger.error("License signature verification failed")
            return None
        
        return license_data
    
    def _verify_signature(self, license_data: Dict) -> bool:
        """
        Verify license signature.
        
        Args:
            license_data: License data with signature
        
        Returns:
            True if signature is valid, False otherwise
        """
        # Extract signature
        signature = license_data.get('signature')
        if not signature:
            return False
        
        # Create payload (all fields except signature)
        payload = {k: v for k, v in license_data.items() if k != 'signature'}
        payload_str = json.dumps(payload, sort_keys=True)
        
        # Generate expected signature
        # In production, use a private/public key pair and change the secret key!
        secret_key = self.config.get('license_secret_key')
        if not secret_key or secret_key == 'default_secret_key':
            logger.warning(
                "Using default license secret key! "
                "Set 'licensing.license_secret_key' in config.yml for production."
            )
            secret_key = 'default_secret_key'
        
        expected_signature = hashlib.sha256(
            f"{payload_str}{secret_key}".encode()
        ).hexdigest()
        
        return signature == expected_signature
    
    def generate_license_key(
        self,
        license_type: LicenseType,
        issued_to: str,
        max_extensions: Optional[int] = None,
        max_concurrent_calls: Optional[int] = None,
        expiration_days: Optional[int] = None,
        custom_features: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate a new license key.
        
        Args:
            license_type: Type of license
            issued_to: Organization/person name
            max_extensions: Maximum extensions (None for unlimited)
            max_concurrent_calls: Maximum concurrent calls (None for unlimited)
            expiration_days: Days until expiration (None for perpetual)
            custom_features: Custom feature list (for custom license type)
        
        Returns:
            License data dictionary
        """
        issued_date = datetime.now().isoformat()
        
        # Calculate expiration
        expiration = None
        if expiration_days:
            expiration = (datetime.now() + timedelta(days=expiration_days)).isoformat()
        
        # Generate unique license key
        license_key = self._generate_key_string(issued_to, issued_date)
        
        # Build license data
        license_data = {
            'key': license_key,
            'type': license_type.value,
            'issued_to': issued_to,
            'issued_date': issued_date,
            'expiration': expiration,
            'max_extensions': max_extensions,
            'max_concurrent_calls': max_concurrent_calls,
        }
        
        # Add custom features for custom license type
        if license_type == LicenseType.CUSTOM and custom_features:
            license_data['custom_features'] = custom_features
        
        # Generate signature
        payload_str = json.dumps(license_data, sort_keys=True)
        secret_key = self.config.get('license_secret_key', 'default_secret_key')
        signature = hashlib.sha256(
            f"{payload_str}{secret_key}".encode()
        ).hexdigest()
        
        license_data['signature'] = signature
        
        return license_data
    
    def _generate_key_string(self, issued_to: str, issued_date: str) -> str:
        """
        Generate a unique license key string.
        
        Args:
            issued_to: Organization/person name
            issued_date: Issue date
        
        Returns:
            License key string in format XXXX-XXXX-XXXX-XXXX
        """
        # Create unique data
        data = f"{issued_to}{issued_date}{secrets.token_hex(16)}"
        
        # Hash it
        key_hash = hashlib.sha256(data.encode()).hexdigest()
        
        # Format as XXXX-XXXX-XXXX-XXXX
        parts = [key_hash[i:i+4].upper() for i in range(0, 16, 4)]
        return '-'.join(parts)
    
    def save_license(self, license_data: Dict, enforce_licensing: bool = False) -> bool:
        """
        Save license to file.
        
        Args:
            license_data: License data to save
            enforce_licensing: If True, create a license lock file to prevent 
                             licensing from being disabled (for commercial deployments)
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.license_path, 'w') as f:
                json.dump(license_data, f, indent=2)
            
            logger.info(f"License saved to {self.license_path}")
            
            # Create license lock file if enforcement is requested
            if enforce_licensing:
                self._create_license_lock(license_data)
            
            # Reload license
            self._load_license()
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving license: {e}")
            return False
    
    def _create_license_lock(self, license_data: Dict) -> None:
        """
        Create a license lock file to enforce licensing.
        
        This file prevents users from disabling licensing via config or environment.
        Used for commercial deployments where licensing must be enforced.
        
        Args:
            license_data: License data to include in lock file
        """
        lock_path = os.path.join(
            os.path.dirname(self.license_path), '.license_lock'
        )
        
        try:
            lock_data = {
                'created': datetime.now().isoformat(),
                'license_key': license_data.get('key', '')[:19] + '...',  # Partial key
                'issued_to': license_data.get('issued_to', ''),
                'type': license_data.get('type', ''),
                'enforcement': 'mandatory'
            }
            
            with open(lock_path, 'w') as f:
                json.dump(lock_data, f, indent=2)
            
            # Restrict permissions (owner read/write only)
            os.chmod(lock_path, 0o600)
            
            logger.info(f"License lock file created at {lock_path} - licensing enforcement is now mandatory")
        
        except Exception as e:
            logger.error(f"Error creating license lock file: {e}")
    
    def remove_license_lock(self) -> bool:
        """
        Remove license lock file (admin operation).
        
        This allows licensing to be disabled again. Should only be used when
        transitioning from commercial to open-source deployment.
        
        Returns:
            True if removed successfully, False otherwise
        """
        lock_path = os.path.join(
            os.path.dirname(self.license_path), '.license_lock'
        )
        
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
                logger.info("License lock file removed - licensing can now be disabled")
                return True
            else:
                logger.warning("License lock file does not exist")
                return False
        
        except Exception as e:
            logger.error(f"Error removing license lock file: {e}")
            return False
    
    def get_license_status(self) -> Tuple[LicenseStatus, Optional[str]]:
        """
        Get current license status.
        
        Returns:
            Tuple of (status, message)
        """
        # If licensing is disabled, return disabled status
        if not self.enabled:
            return LicenseStatus.DISABLED, "Licensing is disabled by administrator"
        
        # If no license, check for trial
        if not self.current_license:
            return self._check_trial_eligibility()
        
        # Check expiration
        expiration = self.current_license.get('expiration')
        if expiration:
            expiration_date = datetime.fromisoformat(expiration)
            now = datetime.now()
            
            if now > expiration_date:
                # Check grace period
                grace_end = expiration_date + timedelta(days=self.grace_period_days)
                if now <= grace_end:
                    days_left = (grace_end - now).days
                    return (
                        LicenseStatus.GRACE_PERIOD,
                        f"License expired. Grace period ends in {days_left} days"
                    )
                else:
                    return LicenseStatus.EXPIRED, "License has expired"
        
        # License is active
        if expiration:
            expiration_date = datetime.fromisoformat(expiration)
            days_until_expiration = (expiration_date - datetime.now()).days
            return (
                LicenseStatus.ACTIVE,
                f"License active. Expires in {days_until_expiration} days"
            )
        else:
            return LicenseStatus.ACTIVE, "License active (perpetual)"
    
    def _check_trial_eligibility(self) -> Tuple[LicenseStatus, Optional[str]]:
        """
        Check if system is eligible for trial mode.
        
        Returns:
            Tuple of (status, message)
        """
        trial_marker = os.path.join(
            os.path.dirname(self.license_path),
            '.trial_start'
        )
        
        if not os.path.exists(trial_marker):
            # Start trial
            try:
                with open(trial_marker, 'w') as f:
                    f.write(datetime.now().isoformat())
                
                return (
                    LicenseStatus.ACTIVE,
                    f"Trial mode activated ({self.trial_period_days} days)"
                )
            except Exception as e:
                logger.error(f"Error creating trial marker: {e}")
                return LicenseStatus.INVALID, "Unable to activate trial mode"
        
        # Check trial expiration
        try:
            with open(trial_marker, 'r') as f:
                trial_start = datetime.fromisoformat(f.read().strip())
            
            trial_end = trial_start + timedelta(days=self.trial_period_days)
            now = datetime.now()
            
            if now <= trial_end:
                days_left = (trial_end - now).days
                return (
                    LicenseStatus.ACTIVE,
                    f"Trial mode active ({days_left} days remaining)"
                )
            else:
                return LicenseStatus.EXPIRED, "Trial period has expired"
        
        except Exception as e:
            logger.error(f"Error checking trial status: {e}")
            return LicenseStatus.INVALID, "Unable to verify trial status"
    
    def has_feature(self, feature_name: str) -> bool:
        """
        Check if current license allows a specific feature.
        
        Args:
            feature_name: Name of the feature to check
        
        Returns:
            True if feature is allowed, False otherwise
        """
        # If licensing is disabled, all features are allowed
        if not self.enabled:
            return True
        
        # If no license, use trial features
        if not self.current_license:
            return feature_name in self.features.get('trial', [])
        
        # Check license status
        status, _ = self.get_license_status()
        if status in (LicenseStatus.EXPIRED, LicenseStatus.INVALID):
            return False
        
        # Get license type
        license_type = self.current_license.get('type', 'trial')
        
        # For custom license, check custom features
        if license_type == 'custom':
            custom_features = self.current_license.get('custom_features', [])
            return feature_name in custom_features
        
        # Check standard features
        allowed_features = self.features.get(license_type, [])
        return feature_name in allowed_features
    
    def get_limit(self, limit_name: str) -> Optional[int]:
        """
        Get a numeric limit for current license.
        
        Args:
            limit_name: Name of the limit (e.g., 'max_extensions')
        
        Returns:
            Limit value or None for unlimited
        """
        # If licensing is disabled, no limits
        if not self.enabled:
            return None
        
        # If no license, use trial
        if not self.current_license:
            license_type = 'trial'
        else:
            license_type = self.current_license.get('type', 'trial')
        
        # Check for explicit limit in license
        limit_value = self.current_license.get(limit_name) if self.current_license else None
        if limit_value is not None:
            return None if limit_value == 'unlimited' else limit_value
        
        # Check features for limits
        allowed_features = self.features.get(license_type, [])
        for feature in allowed_features:
            if feature.startswith(f'{limit_name}:'):
                value = feature.split(':', 1)[1]
                return None if value == 'unlimited' else int(value)
        
        # No limit found
        return None
    
    def check_limit(self, limit_name: str, current_value: int) -> bool:
        """
        Check if current value is within license limits.
        
        Args:
            limit_name: Name of the limit to check
            current_value: Current value to check against limit
        
        Returns:
            True if within limits, False if exceeded
        """
        limit = self.get_limit(limit_name)
        
        # None means unlimited
        if limit is None:
            return True
        
        return current_value <= limit
    
    def get_license_info(self) -> Dict:
        """
        Get comprehensive license information.
        
        Returns:
            Dictionary with license details
        """
        status, message = self.get_license_status()
        
        info = {
            'enabled': self.enabled,
            'status': status.value,
            'message': message,
        }
        
        if not self.enabled:
            info['type'] = 'disabled'
            info['features'] = 'all'
            return info
        
        if self.current_license:
            info['type'] = self.current_license.get('type')
            info['issued_to'] = self.current_license.get('issued_to')
            info['issued_date'] = self.current_license.get('issued_date')
            info['expiration'] = self.current_license.get('expiration', 'never')
            info['key'] = self.current_license.get('key', '')[:19] + '...'  # Partial key
        else:
            info['type'] = 'trial'
        
        # Add limits
        info['limits'] = {
            'max_extensions': self.get_limit('max_extensions'),
            'max_concurrent_calls': self.get_limit('max_concurrent_calls'),
        }
        
        return info
    
    def revoke_license(self) -> bool:
        """
        Revoke current license.
        
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            if os.path.exists(self.license_path):
                os.remove(self.license_path)
                logger.info("License revoked")
            
            self.current_license = None
            return True
        
        except Exception as e:
            logger.error(f"Error revoking license: {e}")
            return False


# Convenience functions for use throughout the application

_license_manager = None


def initialize_license_manager(config: Optional[Dict] = None) -> LicenseManager:
    """
    Initialize the global license manager.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Initialized LicenseManager instance
    """
    global _license_manager
    _license_manager = LicenseManager(config)
    return _license_manager


def get_license_manager() -> LicenseManager:
    """
    Get the global license manager instance.
    
    Returns:
        LicenseManager instance
    """
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def has_feature(feature_name: str) -> bool:
    """
    Check if a feature is available under current license.
    
    Args:
        feature_name: Name of the feature
    
    Returns:
        True if feature is available, False otherwise
    """
    return get_license_manager().has_feature(feature_name)


def check_limit(limit_name: str, current_value: int) -> bool:
    """
    Check if current value is within license limits.
    
    Args:
        limit_name: Name of the limit
        current_value: Current value to check
    
    Returns:
        True if within limits, False otherwise
    """
    return get_license_manager().check_limit(limit_name, current_value)


def get_license_info() -> Dict:
    """
    Get current license information.
    
    Returns:
        Dictionary with license details
    """
    return get_license_manager().get_license_info()
