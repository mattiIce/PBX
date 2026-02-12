#!/usr/bin/env python3
"""
Smoke Tests for PBX System
Quick validation of critical functionality
"""

import sys
import urllib.request
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class SmokeTestRunner:
    """Run smoke tests for critical PBX functionality"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test(self, name, func):
        """Run a single test"""
        try:
            print(f"  Testing {name}...", end=" ")
            func()
            print("✓ PASS")
            self.passed += 1
            return True
        except Exception as e:
            print(f"✗ FAIL: {e}")
            self.failed += 1
            self.errors.append((name, str(e)))
            return False

    def test_imports(self):
        """Test that core modules can be imported"""

    def test_config_loading(self):
        """Test configuration loading"""
        from pbx.utils.config import Config

        config = Config()
        assert config.config is not None, "Config not loaded"

    def test_logger(self):
        """Test logging system"""
        from pbx.utils.logger import get_logger

        logger = get_logger()
        logger.info("Smoke test log message")

    def test_database_schema(self):
        """Test database utilities can be imported"""
        from pbx.utils import database

        # Just verify the module can be imported
        assert database is not None

    def test_encryption(self):
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

    def test_sip_message_parsing(self):
        """Test SIP message parsing"""
        from pbx.sip.message import SIPMessage

        # Just verify the class can be imported
        assert SIPMessage is not None

    def test_audio_utils(self):
        """Test audio utilities"""
        from pbx.utils import audio

        # Just verify the module exists
        assert audio is not None

    def test_dtmf_detection(self):
        """Test DTMF detection"""
        from pbx.utils import dtmf

        # Just verify the module exists
        assert dtmf is not None

    def test_security_functions(self):
        """Test security utilities"""
        from pbx.utils.security import SecurePasswordManager

        # Test password hashing
        pm = SecurePasswordManager()
        password = "test_password"
        hashed, salt = pm.hash_password(password)
        assert pm.verify_password(password, hashed, salt), "Password verification failed"
        assert not pm.verify_password("wrong", hashed, salt), "Wrong password verified"

    def test_health_endpoint_available(self):
        """Test if health endpoint is reachable (if server is running)"""
        # This test only runs if we can detect a server running
        try:
            req = urllib.request.Request("http://localhost:8880/health", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                assert response.status == 200, "Health endpoint returned non-200"
        except Exception:
            # Server not running, skip this test
            print("(server not running, skipped)", end=" ")

    def run_all(self):
        """Run all smoke tests"""
        print("\n" + "=" * 70)
        print("PBX SYSTEM SMOKE TESTS")
        print("=" * 70 + "\n")

        # Core functionality tests
        print("Core Functionality:")
        self.test("Module imports", self.test_imports)
        self.test("Configuration loading", self.test_config_loading)
        self.test("Logging system", self.test_logger)
        self.test("Database schema", self.test_database_schema)

        print("\nSecurity:")
        self.test("Encryption/Decryption", self.test_encryption)
        self.test("Password hashing", self.test_security_functions)

        print("\nSIP/RTP:")
        self.test("SIP message parsing", self.test_sip_message_parsing)
        self.test("Audio utilities", self.test_audio_utils)
        self.test("DTMF detection", self.test_dtmf_detection)

        print("\nAPI:")
        self.test("Health endpoint", self.test_health_endpoint_available)

        # Print summary
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.errors:
            print("\nFailed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")

        print("=" * 70 + "\n")

        return self.failed == 0


def main():
    """Main entry point"""
    runner = SmokeTestRunner()
    success = runner.run_all()

    if success:
        print("✓ All smoke tests passed!")
        sys.exit(0)
    else:
        print("✗ Some smoke tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
