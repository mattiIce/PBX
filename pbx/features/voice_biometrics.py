"""
Voice Biometrics
Speaker authentication and fraud detection using voice analysis
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pbx.utils.logger import get_logger
import hashlib
import random


class BiometricStatus(Enum):
    """Biometric enrollment status"""
    NOT_ENROLLED = "not_enrolled"
    ENROLLING = "enrolling"
    ENROLLED = "enrolled"
    SUSPENDED = "suspended"


class VoiceProfile:
    """Represents a voice biometric profile"""
    
    def __init__(self, user_id: str, extension: str):
        """
        Initialize voice profile
        
        Args:
            user_id: Unique user identifier
            extension: User's extension number
        """
        self.user_id = user_id
        self.extension = extension
        self.status = BiometricStatus.NOT_ENROLLED
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.enrollment_samples = 0
        self.required_samples = 3
        self.voiceprint = None  # Placeholder for actual voiceprint data
        self.successful_verifications = 0
        self.failed_verifications = 0


class VoiceBiometrics:
    """
    Voice Biometrics System
    
    Speaker authentication and fraud detection using voice analysis.
    This framework is ready for integration with voice biometric services like:
    - Nuance VocalPassword
    - Pindrop
    - ValidSoft
    - AWS Connect Voice ID
    - Microsoft Azure Speaker Recognition
    """
    
    def __init__(self, config=None, db_backend=None):
        """Initialize voice biometrics system"""
        self.logger = get_logger()
        self.config = config or {}
        self.db_backend = db_backend
        self.db = None
        
        # Configuration
        biometric_config = self.config.get('features', {}).get('voice_biometrics', {})
        self.enabled = biometric_config.get('enabled', False)
        self.provider = biometric_config.get('provider', 'nuance')
        self.verification_threshold = biometric_config.get('threshold', 0.85)
        self.enrollment_required_samples = biometric_config.get('enrollment_samples', 3)
        self.fraud_detection_enabled = biometric_config.get('fraud_detection', True)
        
        # Voice profiles
        self.profiles: Dict[str, VoiceProfile] = {}
        
        # Statistics
        self.total_enrollments = 0
        self.total_verifications = 0
        self.successful_verifications = 0
        self.failed_verifications = 0
        self.fraud_attempts_detected = 0
        
        # Initialize database if available
        if self.db_backend and self.db_backend.enabled:
            try:
                from pbx.features.voice_biometrics_db import VoiceBiometricsDatabase
                self.db = VoiceBiometricsDatabase(self.db_backend)
                self.db.create_tables()
                self.logger.info("Voice biometrics database layer initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize database layer: {e}")
        
        self.logger.info("Voice biometrics system initialized")
        self.logger.info(f"  Provider: {self.provider}")
        self.logger.info(f"  Verification threshold: {self.verification_threshold}")
        self.logger.info(f"  Fraud detection: {self.fraud_detection_enabled}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def create_profile(self, user_id: str, extension: str) -> VoiceProfile:
        """
        Create a voice biometric profile
        
        Args:
            user_id: Unique user identifier
            extension: User's extension number
            
        Returns:
            VoiceProfile: Created profile
        """
        if user_id in self.profiles:
            self.logger.warning(f"Profile already exists for user {user_id}")
            return self.profiles[user_id]
        
        profile = VoiceProfile(user_id, extension)
        profile.required_samples = self.enrollment_required_samples
        self.profiles[user_id] = profile
        
        # Save to database
        if self.db:
            self.db.save_profile(user_id, extension, profile.status.value)
        
        self.logger.info(f"Created voice profile for user {user_id}")
        return profile
    
    def start_enrollment(self, user_id: str) -> Dict:
        """
        Start voice enrollment process
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict: Enrollment session information
        """
        if user_id not in self.profiles:
            self.logger.error(f"No profile found for user {user_id}")
            return {'success': False, 'error': 'Profile not found'}
        
        profile = self.profiles[user_id]
        profile.status = BiometricStatus.ENROLLING
        profile.enrollment_samples = 0
        
        self.logger.info(f"Started enrollment for user {user_id}")
        
        return {
            'success': True,
            'user_id': user_id,
            'required_samples': profile.required_samples,
            'session_id': self._generate_session_id(user_id)
        }
    
    def add_enrollment_sample(self, user_id: str, audio_data: bytes) -> Dict:
        """
        Add a voice sample for enrollment
        
        Args:
            user_id: User identifier
            audio_data: Audio sample (WAV format, 16kHz, 16-bit PCM recommended)
            
        Returns:
            Dict: Enrollment progress
        """
        if user_id not in self.profiles:
            return {'success': False, 'error': 'Profile not found'}
        
        profile = self.profiles[user_id]
        
        # TODO: Process audio and extract voice features
        # This is where you would integrate with a voice biometric service
        
        profile.enrollment_samples += 1
        profile.last_updated = datetime.now()
        
        enrollment_complete = profile.enrollment_samples >= profile.required_samples
        
        if enrollment_complete:
            profile.status = BiometricStatus.ENROLLED
            # TODO: Create final voiceprint
            profile.voiceprint = self._create_voiceprint(user_id, audio_data)
            self.total_enrollments += 1
            self.logger.info(f"Enrollment completed for user {user_id}")
        
        # Update database
        if self.db:
            self.db.update_enrollment_progress(user_id, profile.enrollment_samples)
            if enrollment_complete:
                self.db.save_profile(user_id, profile.extension, profile.status.value)
        
        return {
            'success': True,
            'samples_collected': profile.enrollment_samples,
            'samples_required': profile.required_samples,
            'enrollment_complete': enrollment_complete
        }
    
    def verify_speaker(self, user_id: str, audio_data: bytes) -> Dict:
        """
        Verify speaker identity using voice biometrics
        
        Args:
            user_id: Claimed user identifier
            audio_data: Audio sample to verify
            
        Returns:
            Dict: Verification result with confidence score
        """
        if user_id not in self.profiles:
            return {
                'verified': False,
                'confidence': 0.0,
                'error': 'No profile found'
            }
        
        profile = self.profiles[user_id]
        
        if profile.status != BiometricStatus.ENROLLED:
            return {
                'verified': False,
                'confidence': 0.0,
                'error': 'Profile not enrolled'
            }
        
        # TODO: Compare audio against stored voiceprint
        # This is where you would integrate with a voice biometric service
        confidence = self._calculate_match_score(profile, audio_data)
        
        verified = confidence >= self.verification_threshold
        self.total_verifications += 1
        
        if verified:
            profile.successful_verifications += 1
            self.successful_verifications += 1
            self.logger.info(f"Voice verification successful for user {user_id} "
                           f"(confidence: {confidence:.2f})")
        else:
            profile.failed_verifications += 1
            self.failed_verifications += 1
            self.logger.warning(f"Voice verification failed for user {user_id} "
                              f"(confidence: {confidence:.2f})")
        
        # Save to database
        if self.db:
            call_id = f"call-{datetime.now().timestamp()}"
            self.db.save_verification(user_id, call_id, verified, confidence)
        
        return {
            'verified': verified,
            'confidence': confidence,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
    
    def detect_fraud(self, audio_data: bytes, caller_info: Dict) -> Dict:
        """
        Detect potential fraud using voice analysis
        
        Args:
            audio_data: Audio sample to analyze
            caller_info: Information about the caller
            
        Returns:
            Dict: Fraud detection result
        """
        if not self.fraud_detection_enabled:
            return {'fraud_detected': False, 'reason': 'Fraud detection disabled'}
        
        # TODO: Implement fraud detection algorithms
        # - Replay attack detection
        # - Synthetic voice detection
        # - Voice manipulation detection
        # - Known fraudster voiceprint matching
        
        fraud_indicators = []
        risk_score = 0.0
        
        # Placeholder logic
        # In production, integrate with fraud detection service
        
        fraud_detected = risk_score > 0.7
        
        if fraud_detected:
            self.fraud_attempts_detected += 1
            self.logger.warning(f"Fraud detected! Risk score: {risk_score:.2f}")
            self.logger.warning(f"  Indicators: {', '.join(fraud_indicators)}")
        
        # Save to database
        if self.db:
            call_id = caller_info.get('call_id', f"call-{datetime.now().timestamp()}")
            caller_id = caller_info.get('caller_id', 'unknown')
            self.db.save_fraud_detection(call_id, caller_id, fraud_detected, risk_score, fraud_indicators)
        
        return {
            'fraud_detected': fraud_detected,
            'risk_score': risk_score,
            'indicators': fraud_indicators,
            'caller_info': caller_info,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_session_id(self, user_id: str) -> str:
        """Generate enrollment session ID"""
        data = f"{user_id}-{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _create_voiceprint(self, user_id: str, audio_data: bytes) -> str:
        """
        Create voiceprint from enrollment samples
        
        Args:
            user_id: User identifier
            audio_data: Audio sample
            
        Returns:
            str: Voiceprint identifier
        """
        # TODO: Process audio and create actual voiceprint
        # This would involve feature extraction (MFCC, i-vectors, x-vectors, etc.)
        return hashlib.sha256(f"{user_id}-{datetime.now()}".encode()).hexdigest()
    
    def _calculate_match_score(self, profile: VoiceProfile, audio_data: bytes) -> float:
        """
        Calculate match score between audio and profile
        
        Args:
            profile: Voice profile
            audio_data: Audio to match
            
        Returns:
            float: Match score (0.0 to 1.0)
        """
        # TODO: Implement actual voice matching algorithm
        # Placeholder returns random score for testing
        return random.uniform(0.75, 0.95)
    
    def get_profile(self, user_id: str) -> Optional[VoiceProfile]:
        """Get voice profile for a user"""
        return self.profiles.get(user_id)
    
    def delete_profile(self, user_id: str) -> bool:
        """Delete a voice profile"""
        if user_id in self.profiles:
            del self.profiles[user_id]
            self.logger.info(f"Deleted voice profile for user {user_id}")
            return True
        return False
    
    def suspend_profile(self, user_id: str):
        """Suspend a voice profile (e.g., after multiple failed verifications)"""
        if user_id in self.profiles:
            self.profiles[user_id].status = BiometricStatus.SUSPENDED
            self.logger.warning(f"Suspended voice profile for user {user_id}")
    
    def get_statistics(self) -> Dict:
        """Get voice biometrics statistics"""
        stats = {
            'total_profiles': len(self.profiles),
            'enrolled_profiles': len([p for p in self.profiles.values() 
                                     if p.status == BiometricStatus.ENROLLED]),
            'total_enrollments': self.total_enrollments,
            'total_verifications': self.total_verifications,
            'successful_verifications': self.successful_verifications,
            'failed_verifications': self.failed_verifications,
            'verification_success_rate': self.successful_verifications / max(1, self.total_verifications),
            'fraud_attempts_detected': self.fraud_attempts_detected,
            'provider': self.provider,
            'enabled': self.enabled
        }
        
        # Add database statistics if available
        if self.db:
            db_stats = self.db.get_statistics()
            if db_stats:
                stats['database_stats'] = db_stats
        
        return stats


# Global instance
_voice_biometrics = None


def get_voice_biometrics(config=None, db_backend=None) -> VoiceBiometrics:
    """Get or create voice biometrics instance"""
    global _voice_biometrics
    if _voice_biometrics is None:
        _voice_biometrics = VoiceBiometrics(config, db_backend)
    return _voice_biometrics
