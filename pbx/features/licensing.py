"""
Licensing and Subscription Management System
Manages premium features, usage tracking, and license validation
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from pbx.utils.logger import get_logger

logger = get_logger()


class LicenseType:
    """License tier types"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class FeatureFlag:
    """Premium feature flags"""
    # Analytics
    ADVANCED_ANALYTICS = "advanced_analytics"
    CALL_QUALITY_METRICS = "call_quality_metrics"
    PREDICTIVE_ANALYTICS = "predictive_analytics"
    CUSTOM_REPORTS = "custom_reports"
    
    # Call Center
    SUPERVISOR_DASHBOARD = "supervisor_dashboard"
    CALL_MONITORING = "call_monitoring"
    AGENT_PERFORMANCE = "agent_performance"
    WALLBOARD = "wallboard"
    
    # AI & Automation
    VOICEMAIL_TRANSCRIPTION = "voicemail_transcription"
    AI_ROUTING = "ai_routing"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    
    # Integration
    CRM_INTEGRATION = "crm_integration"
    SMS_INTEGRATION = "sms_integration"
    API_WEBHOOKS = "api_webhooks"
    
    # Storage
    TIERED_STORAGE = "tiered_storage"
    UNLIMITED_RECORDING = "unlimited_recording"
    CLOUD_BACKUP = "cloud_backup"
    
    # Security
    ADVANCED_SECURITY = "advanced_security"
    SSO_INTEGRATION = "sso_integration"
    AUDIT_LOGGING = "audit_logging"
    
    # Communication
    VIDEO_CONFERENCING = "video_conferencing"
    SCREEN_SHARING = "screen_sharing"
    
    # IVR
    ADVANCED_IVR = "advanced_ivr"
    SPEECH_RECOGNITION = "speech_recognition"


class LicenseManager:
    """Manages licensing and feature access"""
    
    # Feature matrix: which features are available in each tier
    TIER_FEATURES = {
        LicenseType.FREE: {
            # Basic features only
        },
        LicenseType.BASIC: {
            FeatureFlag.ADVANCED_ANALYTICS,
            FeatureFlag.CUSTOM_REPORTS,
            FeatureFlag.AUDIT_LOGGING,
        },
        LicenseType.PROFESSIONAL: {
            # All BASIC features plus:
            FeatureFlag.ADVANCED_ANALYTICS,
            FeatureFlag.CALL_QUALITY_METRICS,
            FeatureFlag.CUSTOM_REPORTS,
            FeatureFlag.SUPERVISOR_DASHBOARD,
            FeatureFlag.AGENT_PERFORMANCE,
            FeatureFlag.VOICEMAIL_TRANSCRIPTION,
            FeatureFlag.SMS_INTEGRATION,
            FeatureFlag.API_WEBHOOKS,
            FeatureFlag.TIERED_STORAGE,
            FeatureFlag.ADVANCED_SECURITY,
            FeatureFlag.AUDIT_LOGGING,
            FeatureFlag.ADVANCED_IVR,
        },
        LicenseType.ENTERPRISE: {
            # All features
            FeatureFlag.ADVANCED_ANALYTICS,
            FeatureFlag.CALL_QUALITY_METRICS,
            FeatureFlag.PREDICTIVE_ANALYTICS,
            FeatureFlag.CUSTOM_REPORTS,
            FeatureFlag.SUPERVISOR_DASHBOARD,
            FeatureFlag.CALL_MONITORING,
            FeatureFlag.AGENT_PERFORMANCE,
            FeatureFlag.WALLBOARD,
            FeatureFlag.VOICEMAIL_TRANSCRIPTION,
            FeatureFlag.AI_ROUTING,
            FeatureFlag.SENTIMENT_ANALYSIS,
            FeatureFlag.CRM_INTEGRATION,
            FeatureFlag.SMS_INTEGRATION,
            FeatureFlag.API_WEBHOOKS,
            FeatureFlag.TIERED_STORAGE,
            FeatureFlag.UNLIMITED_RECORDING,
            FeatureFlag.CLOUD_BACKUP,
            FeatureFlag.ADVANCED_SECURITY,
            FeatureFlag.SSO_INTEGRATION,
            FeatureFlag.AUDIT_LOGGING,
            FeatureFlag.VIDEO_CONFERENCING,
            FeatureFlag.SCREEN_SHARING,
            FeatureFlag.ADVANCED_IVR,
            FeatureFlag.SPEECH_RECOGNITION,
        }
    }
    
    # Capacity limits by tier
    TIER_LIMITS = {
        LicenseType.FREE: {
            'max_extensions': 5,
            'max_concurrent_calls': 2,
            'max_recording_storage_gb': 1,
            'api_calls_per_day': 100,
        },
        LicenseType.BASIC: {
            'max_extensions': 25,
            'max_concurrent_calls': 10,
            'max_recording_storage_gb': 10,
            'api_calls_per_day': 1000,
        },
        LicenseType.PROFESSIONAL: {
            'max_extensions': 100,
            'max_concurrent_calls': 50,
            'max_recording_storage_gb': 100,
            'api_calls_per_day': 10000,
        },
        LicenseType.ENTERPRISE: {
            'max_extensions': -1,  # Unlimited
            'max_concurrent_calls': -1,  # Unlimited
            'max_recording_storage_gb': -1,  # Unlimited
            'api_calls_per_day': -1,  # Unlimited
        }
    }
    
    def __init__(self, config: dict):
        """Initialize license manager"""
        self.config = config
        self.license_file = Path(config.get('licensing.license_file', 'license.json'))
        self.usage_file = Path(config.get('licensing.usage_file', 'usage.json'))
        self.license_data = self._load_license()
        self.usage_data = self._load_usage()
        
    def _load_license(self) -> Dict:
        """Load license data from file"""
        if self.license_file.exists():
            try:
                with open(self.license_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading license file: {e}")
        
        # Default to FREE tier if no license
        return {
            'tier': LicenseType.FREE,
            'organization': 'Unlicensed',
            'issued_date': datetime.now().isoformat(),
            'expiry_date': (datetime.now() + timedelta(days=30)).isoformat(),
            'license_key': None,
            'max_extensions': 5,
            'custom_features': []
        }
    
    def _load_usage(self) -> Dict:
        """Load usage tracking data"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading usage file: {e}")
        
        return {
            'api_calls_today': 0,
            'last_reset': datetime.now().isoformat(),
            'total_calls_month': 0,
            'recording_storage_used_gb': 0
        }
    
    def _save_license(self):
        """Save license data to file"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(self.license_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving license file: {e}")
    
    def _save_usage(self):
        """Save usage data to file"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving usage file: {e}")
    
    def get_license_tier(self) -> str:
        """Get current license tier"""
        return self.license_data.get('tier', LicenseType.FREE)
    
    def is_license_valid(self) -> bool:
        """Check if license is valid and not expired"""
        try:
            expiry = datetime.fromisoformat(self.license_data.get('expiry_date', ''))
            return datetime.now() < expiry
        except (ValueError, TypeError):
            return False
    
    def has_feature(self, feature: str) -> bool:
        """
        Check if a feature is available in current license
        Args:
            feature: Feature flag from FeatureFlag class
        Returns:
            True if feature is available
        """
        if not self.is_license_valid():
            return False
        
        tier = self.get_license_tier()
        tier_features = self.TIER_FEATURES.get(tier, set())
        custom_features = set(self.license_data.get('custom_features', []))
        
        return feature in tier_features or feature in custom_features
    
    def get_limit(self, limit_name: str) -> int:
        """
        Get capacity limit for current license
        Args:
            limit_name: Name of the limit (e.g., 'max_extensions')
        Returns:
            Limit value (-1 means unlimited)
        """
        tier = self.get_license_tier()
        limits = self.TIER_LIMITS.get(tier, {})
        
        # Check for custom limits in license
        custom_limit = self.license_data.get(limit_name)
        if custom_limit is not None:
            return custom_limit
        
        return limits.get(limit_name, 0)
    
    def check_limit(self, limit_name: str, current_value: int) -> bool:
        """
        Check if current value is within limit
        Args:
            limit_name: Name of the limit
            current_value: Current usage value
        Returns:
            True if within limit
        """
        limit = self.get_limit(limit_name)
        
        # -1 means unlimited
        if limit == -1:
            return True
        
        return current_value < limit
    
    def track_api_call(self):
        """Track an API call for rate limiting"""
        # Reset daily counter if needed
        try:
            last_reset = datetime.fromisoformat(self.usage_data.get('last_reset', ''))
            if last_reset.date() < datetime.now().date():
                self.usage_data['api_calls_today'] = 0
                self.usage_data['last_reset'] = datetime.now().isoformat()
        except (ValueError, TypeError):
            self.usage_data['api_calls_today'] = 0
            self.usage_data['last_reset'] = datetime.now().isoformat()
        
        self.usage_data['api_calls_today'] += 1
        self._save_usage()
    
    def can_make_api_call(self) -> bool:
        """Check if API call is allowed under current limits"""
        current_calls = self.usage_data.get('api_calls_today', 0)
        return self.check_limit('api_calls_per_day', current_calls)
    
    def get_license_info(self) -> Dict:
        """Get complete license information"""
        tier = self.get_license_tier()
        return {
            'tier': tier,
            'organization': self.license_data.get('organization'),
            'valid': self.is_license_valid(),
            'issued_date': self.license_data.get('issued_date'),
            'expiry_date': self.license_data.get('expiry_date'),
            'features': list(self.TIER_FEATURES.get(tier, set())),
            'limits': self.TIER_LIMITS.get(tier, {}),
            'usage': self.usage_data
        }
    
    def update_license(self, license_key: str, license_data: Dict) -> bool:
        """
        Update license with new key and data
        
        NOTE: This is a basic implementation without cryptographic validation.
        Production implementation should include:
        - RSA/ECDSA signature verification
        - License server validation
        - Hardware binding
        - Tamper detection
        
        Args:
            license_key: License key string
            license_data: License data dictionary
        Returns:
            True if successful
        """
        try:
            # TODO: Add cryptographic license validation
            # Example: Verify license_key signature against license_data using public key
            logger.warning("License validation not implemented - using basic file-based licensing")
            
            self.license_data = license_data
            self.license_data['license_key'] = license_key
            self._save_license()
            return True
        except Exception as e:
            logger.error(f"Error updating license: {e}")
            return False
