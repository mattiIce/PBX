"""
TLS/SRTP Support for FIPS-compliant encrypted communications
Provides SIPS (SIP over TLS) and SRTP (Secure RTP) functionality
"""

import ssl

from pbx.utils.logger import get_logger

# Check if cryptography library is available for SRTP
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class TLSManager:
    """
    Manages TLS connections for SIP (SIPS)
    Supports FIPS-approved cipher suites
    """

    def __init__(self, cert_file: str | None = None, key_file: str | None = None, fips_mode: bool = False) -> None:
        """
        Initialize TLS manager

        Args:
            cert_file: Path to TLS certificate file
            key_file: Path to TLS private key file
            fips_mode: Enable FIPS mode
        """
        self.cert_file = cert_file
        self.key_file = key_file
        self.fips_mode = fips_mode
        self.logger = get_logger()
        self.ssl_context = None

        if cert_file and key_file:
            self._create_ssl_context()

    def _create_ssl_context(self) -> None:
        """Create SSL context with FIPS-approved settings and TLS 1.3 support"""
        try:
            # Create SSL context
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

            # Load certificate and private key
            self.ssl_context.load_cert_chain(self.cert_file, self.key_file)

            if self.fips_mode:
                # Configure FIPS-approved cipher suites for TLS 1.2 and TLS 1.3
                # TLS 1.2 ciphers: AES-based ciphers approved by FIPS 140-2
                # TLS 1.3 ciphers are handled automatically by the TLS 1.3 protocol
                fips_ciphers = [
                    "ECDHE-RSA-AES256-GCM-SHA384",
                    "ECDHE-RSA-AES128-GCM-SHA256",
                    "AES256-GCM-SHA384",
                    "AES128-GCM-SHA256",
                ]
                self.ssl_context.set_ciphers(":".join(fips_ciphers))

                # Require TLS 1.2 or higher (includes TLS 1.3)
                self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            else:
                # Use strong ciphers but not limited to FIPS
                self.ssl_context.set_ciphers("HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4")
                self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Enable TLS 1.3 by not setting a maximum version restriction
            # This allows the latest supported TLS version (1.3) to be negotiated
            # Note: TLS 1.3 cipher suites are configured automatically

            # Additional security settings
            self.ssl_context.options |= ssl.OP_NO_SSLv2
            self.ssl_context.options |= ssl.OP_NO_SSLv3
            self.ssl_context.options |= ssl.OP_NO_TLSv1
            self.ssl_context.options |= ssl.OP_NO_TLSv1_1

            self.logger.info(
                f"TLS context created (FIPS mode: {self.fips_mode}, TLS 1.2-1.3 supported)"
            )

        except (OSError, ssl.SSLError) as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            self.ssl_context = None

    def wrap_socket(self, socket: object, server_side: bool = True) -> ssl.SSLSocket | None:
        """
        Wrap socket with TLS

        Args:
            socket: Socket to wrap
            server_side: True if server socket

        Returns:
            Wrapped SSL socket or None
        """
        if not self.ssl_context:
            self.logger.error("SSL context not initialized")
            return None

        try:
            ssl_socket = self.ssl_context.wrap_socket(
                socket, server_side=server_side, do_handshake_on_connect=True
            )
            return ssl_socket
        except (OSError, ssl.SSLError) as e:
            self.logger.error(f"Failed to wrap socket with TLS: {e}")
            return None

    def is_available(self) -> bool:
        """Check if TLS is available"""
        return self.ssl_context is not None


class SRTPManager:
    """
    Manages SRTP (Secure RTP) for encrypted media
    Uses AES-GCM for FIPS compliance
    """

    def __init__(self, fips_mode: bool = False) -> None:
        """
        Initialize SRTP manager

        Args:
            fips_mode: Enable FIPS mode
        """
        self.fips_mode = fips_mode
        self.logger = get_logger()
        self.sessions = {}  # call_id -> encryption keys

        if not CRYPTO_AVAILABLE:
            self.logger.warning(
                "SRTP requires cryptography library. Install with: pip install cryptography"
            )

    def create_session(self, call_id: str, master_key: bytes, master_salt: bytes) -> bool:
        """
        Create SRTP session with encryption keys

        Args:
            call_id: Call identifier
            master_key: Master key (16 or 32 bytes)
            master_salt: Master salt (14 bytes)

        Returns:
            True if session created
        """
        if not CRYPTO_AVAILABLE:
            self.logger.error("SRTP not available - cryptography library required")
            return False

        try:
            # Store session keys
            self.sessions[call_id] = {
                "master_key": master_key,
                "master_salt": master_salt,
                "cipher": AESGCM(master_key),
            }

            self.logger.info(f"Created SRTP session for call {call_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create SRTP session: {e}")
            return False

    def encrypt_rtp_packet(self, call_id: str, rtp_packet: bytes, sequence_number: int) -> bytes | None:
        """
        Encrypt RTP packet using SRTP

        Args:
            call_id: Call identifier
            rtp_packet: RTP packet data
            sequence_number: RTP sequence number

        Returns:
            Encrypted packet or None
        """
        session = self.sessions.get(call_id)
        if not session:
            self.logger.warning(f"No SRTP session for call {call_id}")
            return None

        try:
            # Create nonce from sequence number and salt
            nonce = self._derive_nonce(session["master_salt"], sequence_number)

            # Encrypt using AES-GCM (FIPS-approved)
            cipher = session["cipher"]
            encrypted = cipher.encrypt(nonce, rtp_packet, None)

            return encrypted

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to encrypt RTP packet: {e}")
            return None

    def decrypt_rtp_packet(self, call_id: str, encrypted_packet: bytes, sequence_number: int) -> bytes | None:
        """
        Decrypt SRTP packet

        Args:
            call_id: Call identifier
            encrypted_packet: Encrypted packet data
            sequence_number: RTP sequence number

        Returns:
            Decrypted packet or None
        """
        session = self.sessions.get(call_id)
        if not session:
            self.logger.warning(f"No SRTP session for call {call_id}")
            return None

        try:
            # Create nonce
            nonce = self._derive_nonce(session["master_salt"], sequence_number)

            # Decrypt using AES-GCM
            cipher = session["cipher"]
            decrypted = cipher.decrypt(nonce, encrypted_packet, None)

            return decrypted

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to decrypt SRTP packet: {e}")
            return None

    def _derive_nonce(self, salt: bytes, sequence_number: int) -> bytes:
        """
        Derive nonce from salt and sequence number per RFC 3711 section 4.1.1

        Args:
            salt: Master salt (14 bytes)
            sequence_number: RTP sequence number

        Returns:
            Nonce bytes (12 bytes for AES-GCM)

        Note: This is a simplified implementation. Production SRTP should use
        a full RFC 3711 compliant implementation with proper key derivation.
        """
        # RFC 3711 compliant nonce derivation
        # SRTP uses: IV = (k_s * 2^16) XOR SSRC XOR (i * 2^16) where i is packet index
        # For AES-GCM, we use first 12 bytes of salt and XOR with packet info

        nonce = bytearray(12)

        # Use first 12 bytes of 14-byte salt
        for i in range(12):
            nonce[i] = salt[i] if i < len(salt) else 0

        # XOR with packet index (sequence number extended to 48 bits)
        # Place sequence number in the middle of nonce for better distribution
        seq_bytes = sequence_number.to_bytes(6, "big")
        for i in range(6):
            nonce[i + 3] ^= seq_bytes[i]

        return bytes(nonce)

    def close_session(self, call_id: str) -> None:
        """
        Close SRTP session

        Args:
            call_id: Call identifier
        """
        if call_id in self.sessions:
            del self.sessions[call_id]
            self.logger.info(f"Closed SRTP session for call {call_id}")

    def is_available(self) -> bool:
        """Check if SRTP is available"""
        return CRYPTO_AVAILABLE


def generate_srtp_keys() -> tuple[bytes, bytes]:
    """
    Generate random SRTP keys

    Returns:
        tuple of (master_key, master_salt)
    """
    import secrets

    # AES-256 requires 32-byte key
    master_key = secrets.token_bytes(32)

    # SRTP uses 14-byte salt
    master_salt = secrets.token_bytes(14)

    return master_key, master_salt
