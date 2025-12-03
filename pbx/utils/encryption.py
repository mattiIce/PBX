"""
FIPS-compliant encryption utilities
Provides FIPS 140-2 compliant cryptographic operations for the PBX system
"""
import hashlib
import secrets
import base64
from pbx.utils.logger import get_logger

# Check if cryptography library is available
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class FIPSEncryption:
    """
    FIPS 140-2 compliant encryption utilities
    
    Uses FIPS-approved algorithms:
    - SHA-256 for hashing (FIPS 180-4)
    - PBKDF2 for key derivation (NIST SP 800-132)
    - AES-256 for encryption (FIPS 197)
    """
    
    def __init__(self, fips_mode=False):
        """
        Initialize FIPS encryption
        
        Args:
            fips_mode: Enable FIPS compliance mode
        """
        self.fips_mode = fips_mode
        self.logger = get_logger()
        
        if fips_mode and not CRYPTO_AVAILABLE:
            self.logger.warning(
                "FIPS mode enabled but cryptography library not available. "
                "Install with: pip install cryptography"
            )
        
        if fips_mode:
            self.logger.info("FIPS 140-2 compliant encryption enabled")
    
    def hash_password(self, password, salt=None):
        """
        Hash password using FIPS-approved SHA-256
        
        Args:
            password: Plain text password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if not salt:
            # Generate cryptographically secure random salt
            salt = secrets.token_bytes(32)
        
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        if isinstance(salt, str):
            salt = salt.encode('utf-8')
        
        if self.fips_mode and CRYPTO_AVAILABLE:
            # Use PBKDF2 with SHA-256 (FIPS-approved)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,  # NIST recommendation
                backend=default_backend()
            )
            hashed = kdf.derive(password)
        else:
            # Fallback to hashlib (still secure, but may not be FIPS certified)
            hashed = hashlib.pbkdf2_hmac('sha256', password, salt, 100000)
        
        # Return base64-encoded strings for storage
        return (
            base64.b64encode(hashed).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )
    
    def verify_password(self, password, hashed_password, salt):
        """
        Verify password against hash
        
        Args:
            password: Plain text password to verify
            hashed_password: Base64-encoded hashed password
            salt: Base64-encoded salt
            
        Returns:
            True if password matches
        """
        # Decode from base64
        if isinstance(hashed_password, str):
            hashed_password = base64.b64decode(hashed_password)
        if isinstance(salt, str):
            salt = base64.b64decode(salt)
        
        # Hash the provided password with the same salt
        new_hash, _ = self.hash_password(password, salt)
        new_hash = base64.b64decode(new_hash)
        
        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(new_hash, hashed_password)
    
    def encrypt_data(self, data, key):
        """
        Encrypt data using AES-256-GCM (FIPS 197)
        
        Args:
            data: Data to encrypt (bytes or str)
            key: Encryption key (must be exactly 32 bytes for AES-256)
            
        Returns:
            Tuple of (encrypted_data, nonce, tag) as base64 strings
            
        Raises:
            ValueError: If key length is not 32 bytes
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "Encryption requires cryptography library. "
                "Install with: pip install cryptography"
            )
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        # Validate key length - must be exactly 32 bytes for AES-256
        if len(key) != 32:
            raise ValueError(
                f"Encryption key must be exactly 32 bytes for AES-256, got {len(key)} bytes. "
                "Use derive_key() to generate proper key from password."
            )
        
        # Generate random nonce (96 bits for GCM)
        nonce = secrets.token_bytes(12)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Return encrypted data, nonce, and authentication tag
        return (
            base64.b64encode(ciphertext).decode('utf-8'),
            base64.b64encode(nonce).decode('utf-8'),
            base64.b64encode(encryptor.tag).decode('utf-8')
        )
    
    def decrypt_data(self, encrypted_data, nonce, tag, key):
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            nonce: Base64-encoded nonce
            tag: Base64-encoded authentication tag
            key: Decryption key (must be exactly 32 bytes)
            
        Returns:
            Decrypted data as bytes
            
        Raises:
            ValueError: If key length is not 32 bytes
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "Decryption requires cryptography library. "
                "Install with: pip install cryptography"
            )
        
        # Decode from base64
        ciphertext = base64.b64decode(encrypted_data)
        nonce = base64.b64decode(nonce)
        tag = base64.b64decode(tag)
        
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        # Validate key length
        if len(key) != 32:
            raise ValueError(
                f"Decryption key must be exactly 32 bytes for AES-256, got {len(key)} bytes"
            )
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt data
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext
    
    def generate_secure_token(self, length=32):
        """
        Generate cryptographically secure random token
        
        Args:
            length: Token length in bytes
            
        Returns:
            Base64-encoded token
        """
        token = secrets.token_bytes(length)
        return base64.b64encode(token).decode('utf-8')
    
    def derive_key(self, password, salt=None, key_length=32):
        """
        Derive encryption key from password using PBKDF2 (FIPS-approved KDF)
        
        Args:
            password: Password or passphrase
            salt: Optional salt (generated if not provided)
            key_length: Desired key length in bytes (default 32 for AES-256)
            
        Returns:
            Tuple of (derived_key, salt) as bytes
        """
        if not salt:
            salt = secrets.token_bytes(32)
        
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        if isinstance(salt, str):
            salt = salt.encode('utf-8')
        
        if self.fips_mode and CRYPTO_AVAILABLE:
            # Use PBKDF2 with SHA-256 (FIPS-approved)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=key_length,
                salt=salt,
                iterations=100000,  # NIST recommendation
                backend=default_backend()
            )
            derived = kdf.derive(password)
        else:
            # Fallback to hashlib
            derived = hashlib.pbkdf2_hmac('sha256', password, salt, 100000, dklen=key_length)
        
        return derived, salt
    
    def hash_data(self, data):
        """
        Hash data using SHA-256 (FIPS 180-4)
        
        Args:
            data: Data to hash
            
        Returns:
            Hex-encoded hash
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if self.fips_mode and CRYPTO_AVAILABLE:
            # Use cryptography library for FIPS compliance
            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
            digest.update(data)
            return digest.finalize().hex()
        else:
            # Fallback to hashlib
            return hashlib.sha256(data).hexdigest()


# Global instance
_encryption_instance = None


def get_encryption(fips_mode=False):
    """
    Get or create encryption instance
    
    Args:
        fips_mode: Enable FIPS mode
        
    Returns:
        FIPSEncryption instance
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = FIPSEncryption(fips_mode)
    return _encryption_instance
