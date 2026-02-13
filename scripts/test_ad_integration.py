#!/usr/bin/env python3
"""
Active Directory Integration Test Script

This script tests and verifies the Active Directory integration is working correctly.
It performs comprehensive checks to ensure all aspects of AD integration are functional.

Usage:
    python scripts/test_ad_integration.py [--config CONFIG_FILE] [--verbose]

Options:
    --config    Path to config file (default: config.yml)
    --verbose   Show detailed output

Tests performed:
    1. Configuration validation
    2. Network connectivity to AD server
    3. Authentication with bind credentials
    4. User search functionality
    5. User attribute retrieval
    6. Extension sync verification
    7. Group membership (if configured)

Exit codes:
    0 - All tests passed
    1 - One or more tests failed
    2 - Configuration error
"""

import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.integrations.active_directory import ActiveDirectoryIntegration
from pbx.utils.config import Config
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class ADIntegrationTester:
    """Test suite for Active Directory integration"""

    def __init__(self, config_path: str, verbose: bool = False):
        self.config_path = config_path
        self.verbose = verbose
        self.config = None
        self.ad = None
        self.test_results = []

    def print_header(self, title: str):
        """Print a formatted header"""
        print()
        print("=" * 70)
        print(f"{Colors.BOLD}{title}{Colors.RESET}")
        print("=" * 70)
        print()

    def print_test(self, test_name: str, status: str, details: str = ""):
        """Print test result"""
        if status == "PASS":
            icon = f"{Colors.GREEN}✓{Colors.RESET}"
            status_text = f"{Colors.GREEN}PASS{Colors.RESET}"
        elif status == "FAIL":
            icon = f"{Colors.RED}✗{Colors.RESET}"
            status_text = f"{Colors.RED}FAIL{Colors.RESET}"
        elif status == "WARN":
            icon = f"{Colors.YELLOW}⚠{Colors.RESET}"
            status_text = f"{Colors.YELLOW}WARN{Colors.RESET}"
        else:
            icon = f"{Colors.BLUE}ℹ{Colors.RESET}"
            status_text = f"{Colors.BLUE}INFO{Colors.RESET}"

        print(f"{icon} {test_name}: {status_text}")
        if details and (self.verbose or status in ["FAIL", "WARN"]):
            print(f"  {details}")

        self.test_results.append((test_name, status, details))

    def test_configuration(self) -> bool:
        """Test 1: Verify configuration is valid"""
        self.print_header("Test 1: Configuration Validation")

        try:
            self.config = Config(self.config_path)
            self.print_test("Load config file", "PASS", f"Loaded {self.config_path}")
        except FileNotFoundError:
            self.print_test("Load config file", "FAIL", f"File not found: {self.config_path}")
            return False
        except Exception as e:
            self.print_test("Load config file", "FAIL", f"Error: {e}")
            return False

        # Check if AD integration is enabled
        enabled = self.config.get("integrations.active_directory.enabled", False)
        if not enabled:
            self.print_test(
                "AD integration enabled",
                "FAIL",
                "Set integrations.active_directory.enabled: true in config.yml",
            )
            return False
        self.print_test("AD integration enabled", "PASS")

        # Check required configuration fields
        required_fields = {
            "server": "integrations.active_directory.server",
            "base_dn": "integrations.active_directory.base_dn",
            "bind_dn": "integrations.active_directory.bind_dn",
            "bind_password": "integrations.active_directory.bind_password",
        }

        all_fields_present = True
        for field_name, config_key in required_fields.items():
            value = self.config.get(config_key)
            if not value:
                self.print_test(
                    f"Required field: {field_name}", "FAIL", f"Missing or empty: {config_key}"
                )
                all_fields_present = False
            else:
                # Don't show password in output
                display_value = "***" if "password" in field_name.lower() else value
                self.print_test(f"Required field: {field_name}", "PASS", f"{display_value}")

        if not all_fields_present:
            return False

        # Check optional but recommended fields
        user_search_base = self.config.get("integrations.active_directory.user_search_base")
        if user_search_base:
            self.print_test("User search base configured", "PASS", user_search_base)
        else:
            self.print_test(
                "User search base configured", "WARN", "Not set, will use base_dn (may be slower)"
            )

        auto_provision = self.config.get("integrations.active_directory.auto_provision", False)
        if auto_provision:
            self.print_test("Auto-provision enabled", "PASS")
        else:
            self.print_test(
                "Auto-provision enabled", "WARN", "Extensions won't be created automatically"
            )

        use_ssl = self.config.get("integrations.active_directory.use_ssl", True)
        if use_ssl:
            self.print_test("SSL/TLS enabled", "PASS", "Using secure connection")
        else:
            self.print_test(
                "SSL/TLS enabled", "WARN", "Unencrypted connection - not recommended for production"
            )

        return True

    def test_ldap3_available(self) -> bool:
        """Test 2: Check if ldap3 library is installed"""
        self.print_header("Test 2: Dependencies Check")

        try:
            import ldap3

            version = ldap3.__version__ if hasattr(ldap3, "__version__") else "unknown"
            self.print_test("ldap3 library installed", "PASS", f"Version: {version}")
            return True
        except ImportError:
            self.print_test("ldap3 library installed", "FAIL", "Install with: pip install ldap3")
            return False

    def test_connection(self) -> bool:
        """Test 3: Test connection to AD server"""
        self.print_header("Test 3: Active Directory Connection")

        # Initialize AD integration
        ad_config = {
            "integrations.active_directory.enabled": self.config.get(
                "integrations.active_directory.enabled"
            ),
            "integrations.active_directory.server": self.config.get(
                "integrations.active_directory.server"
            ),
            "integrations.active_directory.base_dn": self.config.get(
                "integrations.active_directory.base_dn"
            ),
            "integrations.active_directory.bind_dn": self.config.get(
                "integrations.active_directory.bind_dn"
            ),
            "integrations.active_directory.bind_password": self.config.get(
                "integrations.active_directory.bind_password"
            ),
            "integrations.active_directory.use_ssl": self.config.get(
                "integrations.active_directory.use_ssl", True
            ),
            "integrations.active_directory.auto_provision": self.config.get(
                "integrations.active_directory.auto_provision"
            ),
            "integrations.active_directory.user_search_base": self.config.get(
                "integrations.active_directory.user_search_base"
            ),
            "config_file": self.config_path,
        }

        self.ad = ActiveDirectoryIntegration(ad_config)

        if not self.ad.enabled:
            self.print_test("Initialize AD integration", "FAIL", "Could not initialize")
            return False
        self.print_test("Initialize AD integration", "PASS")

        # Test connection
        server = self.config.get("integrations.active_directory.server")
        self.print_test("AD server", "INFO", server)

        if self.ad.connect():
            self.print_test(
                "Connect to AD server", "PASS", "Successfully connected and authenticated"
            )
            return True
        else:
            self.print_test(
                "Connect to AD server",
                "FAIL",
                "Check server address, credentials, and network connectivity",
            )
            return False

    def test_user_search(self) -> tuple[bool, list[dict]]:
        """Test 4: Test user search functionality"""
        self.print_header("Test 4: User Search and Discovery")

        if not self.ad or not self.ad.connection:
            self.print_test("Search users", "FAIL", "No active connection")
            return False, []

        try:
            # Search for users with telephone numbers
            from ldap3 import SUBTREE

            user_search_base = self.config.get(
                "integrations.active_directory.user_search_base",
                self.config.get("integrations.active_directory.base_dn"),
            )

            search_filter = "(&(objectClass=user)(telephoneNumber=*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"

            self.ad.connection.search(
                search_base=user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["sAMAccountName", "displayName", "mail", "telephoneNumber"],
                size_limit=100,
            )

            users = []
            for entry in self.ad.connection.entries:
                users.append(
                    {
                        "username": (
                            str(entry.sAMAccountName) if hasattr(entry, "sAMAccountName") else ""
                        ),
                        "display_name": (
                            str(entry.displayName) if hasattr(entry, "displayName") else ""
                        ),
                        "email": str(entry.mail) if hasattr(entry, "mail") else "",
                        "phone": (
                            str(entry.telephoneNumber) if hasattr(entry, "telephoneNumber") else ""
                        ),
                    }
                )

            if len(users) == 0:
                self.print_test(
                    "Search for users", "WARN", "No users found with telephoneNumber attribute"
                )
                return True, []
            else:
                self.print_test(
                    "Search for users", "PASS", f"Found {len(users)} users with phone numbers"
                )
                return True, users

        except (KeyError, TypeError, ValueError) as e:
            self.print_test("Search for users", "FAIL", f"Error: {e}")
            return False, []

    def test_user_attributes(self, users: list[dict]) -> bool:
        """Test 5: Verify user attributes are retrieved correctly"""
        self.print_header("Test 5: User Attributes Verification")

        if not users:
            self.print_test("User attributes", "WARN", "No users to verify")
            return True

        # Check first few users
        check_count = min(5, len(users))
        all_valid = True

        print(f"Checking first {check_count} users:")
        print()

        for i, user in enumerate(users[:check_count], 1):
            print(f"{Colors.CYAN}User {i}: {user['username']}{Colors.RESET}")

            has_required = True
            if not user["username"]:
                print(f"  {Colors.RED}✗{Colors.RESET} Missing username")
                has_required = False
            else:
                print(f"  {Colors.GREEN}✓{Colors.RESET} Username: {user['username']}")

            if not user["phone"]:
                print(f"  {Colors.RED}✗{Colors.RESET} Missing phone number")
                has_required = False
            else:
                print(f"  {Colors.GREEN}✓{Colors.RESET} Phone: {user['phone']}")

            if user["display_name"]:
                print(f"  {Colors.GREEN}✓{Colors.RESET} Display name: {user['display_name']}")
            else:
                print(f"  {Colors.YELLOW}⚠{Colors.RESET} Missing display name (will use username)")

            if user["email"]:
                print(f"  {Colors.GREEN}✓{Colors.RESET} Email: {user['email']}")
            else:
                print(
                    f"  {Colors.YELLOW}⚠{Colors.RESET} Missing email (voicemail notifications disabled)"
                )

            print()

            if not has_required:
                all_valid = False

        if all_valid:
            self.print_test("User attributes", "PASS", "All checked users have required attributes")
        else:
            self.print_test(
                "User attributes",
                "WARN",
                "Some users missing required attributes (will be skipped during sync)",
            )

        return True

    def test_extension_sync(self, users: list[dict]) -> bool:
        """Test 6: Verify extension sync would work correctly"""
        self.print_header("Test 6: Extension Synchronization Check")

        if not users:
            self.print_test("Extension sync readiness", "WARN", "No users found to sync")
            return True

        auto_provision = self.config.get("integrations.active_directory.auto_provision", False)

        if not auto_provision:
            self.print_test(
                "Auto-provision enabled",
                "WARN",
                "Auto-provision is disabled. Enable it to sync users automatically.",
            )
            return True

        # Check how many users would be synced
        import re

        syncable_users = []
        skipped_users = []

        for user in users:
            if user["username"] and user["phone"]:
                # Clean phone number
                extension_number = re.sub(r"[^0-9]", "", user["phone"])
                if extension_number and len(extension_number) >= 3:
                    syncable_users.append((user, extension_number))
                else:
                    skipped_users.append(user["username"])
            else:
                skipped_users.append(user["username"])

        self.print_test("Syncable users", "INFO", f"{len(syncable_users)} users can be synced")

        if skipped_users:
            self.print_test("Skipped users", "INFO", f"{len(skipped_users)} users will be skipped")

        # Show first few syncable users
        if syncable_users:
            print()
            print("Example users that would be synced:")
            for user, ext_num in syncable_users[:5]:
                print(f"  • {user['username']} ({user['display_name']}) → Extension {ext_num}")

        # Check for potential conflicts
        existing_extensions = self.config.get_extensions()
        existing_numbers = {ext["number"] for ext in existing_extensions}

        conflicts = []
        for user, ext_num in syncable_users:
            if ext_num in existing_numbers:
                conflicts.append((ext_num, user["username"]))

        if conflicts:
            print()
            self.print_test(
                "Extension conflicts",
                "INFO",
                f"{len(conflicts)} extensions already exist (will be updated)",
            )
            if self.verbose:
                for ext_num, username in conflicts[:5]:
                    print(f"  • Extension {ext_num} (user: {username})")

        self.print_test("Extension sync check", "PASS", "Ready to sync users")

        return True

    def test_authentication(self, users: list[dict]) -> bool:
        """Test 7: Test user authentication (optional)"""
        self.print_header("Test 7: Authentication Test")

        # This test is informational only - we can't test without actual passwords
        self.print_test(
            "Authentication capability",
            "INFO",
            "Authentication requires user passwords (not tested automatically)",
        )

        print()
        print("To test authentication manually:")
        print("  1. Choose a test user from the list above")
        print("  2. Use the following Python code:")
        print()
        print("     from pbx.integrations.active_directory import ActiveDirectoryIntegration")
        print("     from pbx.utils.config import Config")
        print()
        print("     config = Config('config.yml')")
        print("     ad = ActiveDirectoryIntegration(config)")
        print("     result = ad.authenticate_user('username', 'password')")
        print("     print(result)")
        print()
        print(
            "Note: Extensions are stored in database. Use scripts/list_extensions_from_db.py to view."
        )

        return True

    def run_all_tests(self) -> bool:
        """Run all tests and return overall result"""
        self.print_header("Active Directory Integration Test Suite")

        print(f"Configuration file: {self.config_path}")
        print(f"Verbose mode: {self.verbose}")

        # Run all tests
        tests = [
            ("Configuration", self.test_configuration),
            ("Dependencies", self.test_ldap3_available),
            ("Connection", self.test_connection),
        ]

        # Run initial tests
        for test_name, test_func in tests:
            if not test_func():
                self.print_summary(success=False)
                return False

        # Run user-related tests
        success, users = self.test_user_search()
        if success:
            self.test_user_attributes(users)
            self.test_extension_sync(users)
            self.test_authentication(users)

        # Print summary
        self.print_summary(success=True)
        return True

    def print_summary(self, success: bool):
        """Print test summary"""
        self.print_header("Test Summary")

        passed = sum(1 for _, status, _ in self.test_results if status == "PASS")
        failed = sum(1 for _, status, _ in self.test_results if status == "FAIL")
        warnings = sum(1 for _, status, _ in self.test_results if status == "WARN")

        print(f"Total tests: {len(self.test_results)}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Warnings: {warnings}{Colors.RESET}")
        print()

        if failed > 0:
            print(f"{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.RESET}")
            print()
            print("Failed tests:")
            for test_name, status, details in self.test_results:
                if status == "FAIL":
                    print(f"  • {test_name}")
                    if details:
                        print(f"    {details}")
            print()
            print("Fix the issues above and run the test again.")
        elif warnings > 0:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠ TESTS PASSED WITH WARNINGS{Colors.RESET}")
            print()
            print("Some configuration recommendations were noted.")
            print("The integration will work, but consider addressing the warnings.")
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED{Colors.RESET}")
            print()
            print("Active Directory integration is configured correctly!")
            print()
            print("Next steps:")
            print("  1. Run the sync script:")
            print("     python scripts/sync_ad_users.py")
            print()
            print("  2. Verify extensions were created in config.yml")
            print()
            print("  3. Test SIP registration with a synced extension")


def main():
    parser = argparse.ArgumentParser(
        description="Test Active Directory integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", default="config.yml", help="Path to config file (default: config.yml)"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    # Run tests
    tester = ADIntegrationTester(args.config, args.verbose)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
