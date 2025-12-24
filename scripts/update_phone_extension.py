#!/usr/bin/env python3
"""
Update Phone Extension Script

This script updates the extension number for a phone in the registered_phones table.
Use this when reprovisioning a phone to a different extension.

Usage:
    python scripts/update_phone_extension.py <mac_address> <new_extension>

Example:
    python scripts/update_phone_extension.py 001565123456 1002
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


def update_phone_extension(mac_address: str, new_extension: str):
    """
    Update a phone's extension in the registered_phones table

    Args:
        mac_address: MAC address of the phone
        new_extension: New extension number to assign
    """

    print("=" * 60)
    print("Phone Extension Update Tool")
    print("=" * 60)

    # Load configuration
    try:
        config = Config("config.yml")
    except Exception as e:
        print(f"✗ Failed to load config.yml: {e}")
        return False

    # Connect to database
    db = DatabaseBackend(config)
    if not db.connect():
        print("✗ Failed to connect to database")
        print("  Check your database configuration in config.yml")
        return False

    print(f"✓ Connected to database ({db.db_type})")

    # Create registered phones DB instance
    phones_db = RegisteredPhonesDB(db)

    # First, check if the phone exists
    existing_phone = phones_db.get_by_mac(mac_address)

    if not existing_phone:
        print(f"\n⚠ Warning: Phone with MAC {mac_address} not found in registered_phones table")
        print("  This phone may not have registered yet.")
        print(
            "  You can still proceed, but the update will have no effect until the phone registers."
        )

        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != "y":
            print("\nCancelled.")
            db.disconnect()
            return False
    else:
        print("\nFound phone:")
        print(f"  MAC Address:       {existing_phone['mac_address']}")
        print(f"  Current Extension: {existing_phone['extension_number']}")
        print(f"  IP Address:        {existing_phone['ip_address']}")
        print(f"  Last Registered:   {existing_phone.get('last_registered', 'N/A')}")

        if existing_phone["extension_number"] == new_extension:
            print(f"\n⚠ Phone is already assigned to extension {new_extension}")
            db.disconnect()
            return True

    # Confirm the update
    print(f"\nUpdate phone {mac_address} to extension {new_extension}?")
    response = input("Proceed? (y/N): ")

    if response.lower() != "y":
        print("\nCancelled.")
        db.disconnect()
        return False

    # Perform the update
    print("\nUpdating...")
    success = phones_db.update_phone_extension(mac_address, new_extension)

    if success:
        print(f"✓ Successfully updated phone {mac_address} to extension {new_extension}")

        # Verify the update
        updated_phone = phones_db.get_by_mac(mac_address)
        if updated_phone:
            print("\nVerified:")
            print(f"  MAC Address:       {updated_phone['mac_address']}")
            print(f"  New Extension:     {updated_phone['extension_number']}")
            print(f"  IP Address:        {updated_phone['ip_address']}")

        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Update the phone provisioning configuration:")
        print("   - Via Admin Panel: Phone Provisioning tab")
        print("   - Or in config.yml: Update the device's extension")
        print("")
        print("2. Reboot the phone to fetch new configuration:")
        print("   - Power cycle the phone")
        print("   - Or use phone menu to reboot")
        print("")
        print("3. Verify the phone registers with new extension")
        print("=" * 60)
    else:
        print("✗ Failed to update phone extension")

    # Disconnect
    db.disconnect()
    return success


def main():
    """Main entry point"""

    if len(sys.argv) != 3:
        print("Usage: python scripts/update_phone_extension.py <mac_address> <new_extension>")
        print("")
        print("Examples:")
        print("  python scripts/update_phone_extension.py 001565123456 1002")
        print("  python scripts/update_phone_extension.py 00:15:65:12:34:56 1002")
        print("")
        print("Note: MAC address format doesn't matter (colons optional)")
        sys.exit(1)

    mac_address = sys.argv[1]
    new_extension = sys.argv[2]

    # Normalize MAC address (remove colons, dashes, etc.)
    mac_address = mac_address.lower().replace(":", "").replace("-", "").replace(".", "")

    try:
        success = update_phone_extension(mac_address, new_extension)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
