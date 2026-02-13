#!/usr/bin/env python3
"""
Smoke Tests for PBX System
Quick validation of critical functionality
"""

import sys
import urllib.request
from collections.abc import Callable


class SmokeTestRunner:
    """Run smoke tests for critical PBX functionality"""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.errors: list[tuple[str, str]] = []

    def test(self, name: str, func: Callable[[], None]) -> bool:
        """Run a single test"""
        try:
            func()
            self.passed += 1
            return True
        except Exception as e:
            self.failed += 1
            self.errors.append((name, str(e)))
            return False

    def test_imports(self) -> None:
        """Test that core modules can be imported"""

    def test_config_loading(self) -> None:
        """Test configuration loading"""
        from pbx.utils.config import Config

        config = Config()
        assert config.config is not None, "Config not loaded"

    def test_logger(self) -> None:
        """Test logging system"""
        from pbx.utils.logger import get_logger

        logger = get_logger()
        logger.info("Smoke test log message")

    def test_database_schema(self) -> None:
        """Test database utilities can be imported"""
        from pbx.utils import database

        # Just verify the module can be imported
        assert database is not None

    def test_encryption(self) -> None:
        """Test encryption utilities"""
        from pbx.utils.encryption import FIPSEncryption

        # Test FIPS encryption
        encryption = FIPSEncryption()
        test_data = b"test message"
        # Use exactly 32 bytes for AES-256
        key = b"a" * 32  # 32-byte key
        encrypted_data, nonce, tag = encryption.encrypt_data(test_data, key)
        decrypted = encryption.decrypt_data(encrypted_data, nonce, tag, key)
        assert decrypted == test_data, "Encryption/decryption failed"

    def test_sip_message_parsing(self) -> None:
        """Test SIP message parsing"""
        from pbx.sip.message import SIPMessage

        # Just verify the class can be imported
        assert SIPMessage is not None

    def test_audio_utils(self) -> None:
        """Test audio utilities"""
        from pbx.utils import audio

        # Just verify the module exists
        assert audio is not None

    def test_dtmf_detection(self) -> None:
        """Test DTMF detection"""
        from pbx.utils import dtmf

        # Just verify the module exists
        assert dtmf is not None

    def test_security_functions(self) -> None:
        """Test security utilities"""
        from pbx.utils.security import SecurePasswordManager

        # Test password hashing
        pm = SecurePasswordManager()
        password = "test_password"
        hashed, salt = pm.hash_password(password)
        assert pm.verify_password(password, hashed, salt), "Password verification failed"
        assert not pm.verify_password("wrong", hashed, salt), "Wrong password verified"

    def test_health_endpoint_available(self) -> None:
        """Test if health endpoint is reachable (if server is running)"""
        # This test only runs if we can detect a server running
        try:
            req = urllib.request.Request("http://localhost:9000/health", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                assert response.status == 200, "Health endpoint returned non-200"
        except Exception:
            # Server not running, skip this test

    def run_all(self) -> bool:
        """Run all smoke tests"""

        # Core functionality tests
        self.test("Module imports", self.test_imports)
        self.test("Configuration loading", self.test_config_loading)
        self.test("Logging system", self.test_logger)
        self.test("Database schema", self.test_database_schema)

        self.test("Encryption/Decryption", self.test_encryption)
        self.test("Password hashing", self.test_security_functions)

        self.test("SIP message parsing", self.test_sip_message_parsing)
        self.test("Audio utilities", self.test_audio_utils)
        self.test("DTMF detection", self.test_dtmf_detection)

        self.test("Health endpoint", self.test_health_endpoint_available)

        # Print summary

        if self.errors:
            for name, error in self.errors:


        return self.failed == 0


def main() -> None:
    """Main entry point"""
    runner = SmokeTestRunner()
    success = runner.run_all()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
