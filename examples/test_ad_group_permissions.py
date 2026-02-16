#!/usr/bin/env python3
"""
Example: Testing Active Directory Group-Based Permissions

This example demonstrates how to configure and use AD group-based permissions
to automatically assign PBX privileges based on security group membership.

Run this example:
    python examples/test_ad_group_permissions.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.integrations.active_directory import ActiveDirectoryIntegration


def example_group_permissions_configuration():
    """Example 1: Configure group permissions"""
    print("=" * 70)
    print("Example 1: Group Permissions Configuration")
    print("=" * 70)
    print()

    # Configure AD integration with group permissions
    config = {
        "integrations.active_directory.enabled": False,  # Set to True in production
        "integrations.active_directory.server": "ldaps://dc.example.com:636",
        "integrations.active_directory.base_dn": "DC=example,DC=com",
        "integrations.active_directory.bind_dn": "CN=svc-pbx,OU=Service Accounts,DC=example,DC=com",
        "integrations.active_directory.bind_password": "SecurePassword123!",
        "integrations.active_directory.auto_provision": True,
        # Map AD groups to PBX permissions
        "integrations.active_directory.group_permissions": {
            # Admins get full access
            "CN=PBX_Admins,OU=Security Groups,DC=example,DC=com": [
                "admin",
                "manage_extensions",
                "view_cdr",
                "system_config",
            ],
            # Sales team gets external calling
            "CN=Sales,OU=Departments,DC=example,DC=com": [
                "external_calling",
                "international_calling",
                "call_transfer",
            ],
            # IT Support gets call management features
            "CN=IT_Support,OU=Departments,DC=example,DC=com": [
                "call_recording",
                "call_monitoring",
                "call_queues",
                "call_barge",
            ],
            # Executives get VIP treatment
            "CN=Executives,OU=Security Groups,DC=example,DC=com": [
                "vip_status",
                "priority_routing",
                "personal_assistant",
            ],
        },
    }

    print("✓ Configuration created with group permissions")
    print(f"  - {len(config['integrations.active_directory.group_permissions'])} groups configured")
    print()


def example_permission_mapping():
    """Example 2: Map user groups to permissions"""
    print("=" * 70)
    print("Example 2: Permission Mapping")
    print("=" * 70)
    print()

    # Configure AD integration
    config = {
        "integrations.active_directory.enabled": False,
        "integrations.active_directory.server": "ldap://test.local",
        "integrations.active_directory.base_dn": "DC=test,DC=local",
        "integrations.active_directory.group_permissions": {
            "CN=Admins,OU=Groups,DC=test,DC=local": ["admin", "manage_extensions"],
            "CN=Sales,OU=Groups,DC=test,DC=local": ["external_calling", "international_calling"],
            "CN=Support,OU=Groups,DC=test,DC=local": ["call_recording", "call_queues"],
        },
    }

    ad = ActiveDirectoryIntegration(config)

    # Test Case 1: Admin user
    print("Test Case 1: Admin User")
    user_groups = [
        "CN=Admins,OU=Groups,DC=test,DC=local",
        "CN=Domain Users,OU=Groups,DC=test,DC=local",
    ]
    permissions = ad._map_groups_to_permissions(user_groups)
    print(f"  Groups: {', '.join([g.split(',')[0].replace('CN=', '') for g in user_groups])}")
    print(f"  Permissions: {', '.join(permissions.keys())}")
    print()

    # Test Case 2: Sales rep
    print("Test Case 2: Sales Representative")
    user_groups = ["CN=Sales,OU=Groups,DC=test,DC=local"]
    permissions = ad._map_groups_to_permissions(user_groups)
    print("  Groups: Sales")
    print(f"  Permissions: {', '.join(permissions.keys())}")
    print()

    # Test Case 3: Multi-role user (Sales + Support)
    print("Test Case 3: Multi-Role User (Sales + Support)")
    user_groups = ["CN=Sales,OU=Groups,DC=test,DC=local", "CN=Support,OU=Groups,DC=test,DC=local"]
    permissions = ad._map_groups_to_permissions(user_groups)
    print("  Groups: Sales, Support")
    print(f"  Permissions: {', '.join(permissions.keys())}")
    print("  Note: User gets combined permissions from both groups")
    print()


def example_flexible_matching():
    """Example 3: Flexible group name matching"""
    print("=" * 70)
    print("Example 3: Flexible Group Name Matching")
    print("=" * 70)
    print()

    config = {
        "integrations.active_directory.enabled": False,
        "integrations.active_directory.server": "ldap://test.local",
        "integrations.active_directory.base_dn": "DC=test,DC=local",
        "integrations.active_directory.group_permissions": {
            # Configure using full DN
            "CN=Engineering,OU=Departments,DC=test,DC=local": [
                "external_calling",
                "vpn_access",
                "remote_work",
            ]
        },
    }

    ad = ActiveDirectoryIntegration(config)

    # Test with full DN format
    print("Test 1: User groups in full DN format")
    user_groups = ["CN=Engineering,OU=Departments,DC=test,DC=local"]
    permissions = ad._map_groups_to_permissions(user_groups)
    print(f"  Input: {user_groups[0]}")
    print(f"  Matched: {len(permissions) > 0}")
    print(f"  Permissions: {', '.join(permissions.keys())}")
    print()

    # Test with CN-only format (short form)
    print("Test 2: User groups in CN-only format")
    user_groups = ["Engineering"]  # Just the CN part
    permissions = ad._map_groups_to_permissions(user_groups)
    print(f"  Input: {user_groups[0]}")
    print(f"  Matched: {len(permissions) > 0}")
    print(f"  Permissions: {', '.join(permissions.keys())}")
    print()

    print("✓ Both formats match successfully!")
    print("  This makes configuration easier and more flexible")
    print()


def example_best_practices():
    """Example 4: Best practices for group permissions"""
    print("=" * 70)
    print("Example 4: Best Practices")
    print("=" * 70)
    print()

    print("Best Practice 1: Principle of Least Privilege")
    print("  ✓ Only grant permissions users actually need")
    print("  ✓ Don't give everyone admin access")
    print("  ✓ Review permissions regularly")
    print()

    print("Best Practice 2: Use Descriptive Group Names")
    print("  ✓ Good: 'PBX_Admins', 'Sales_External_Calling'")
    print("  ✗ Bad: 'Group1', 'Users2'")
    print()

    print("Best Practice 3: Organize by Function")
    print("  ✓ Create groups based on job roles")
    print("  ✓ Example: Sales, Support, Engineering, Executives")
    print("  ✓ Easier to manage and understand")
    print()

    print("Best Practice 4: Test Before Deployment")
    print("  ✓ Test with a single user first")
    print("  ✓ Verify permissions are applied correctly")
    print("  ✓ Check logs for permission grants")
    print()

    print("Best Practice 5: Document Your Configuration")
    print("  ✓ Add comments explaining each group's purpose")
    print("  ✓ Document permission meanings")
    print("  ✓ Keep configuration in version control")
    print()


def main():
    """Run all examples"""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "AD Group-Based Permissions Examples" + " " * 17 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    example_group_permissions_configuration()
    example_permission_mapping()
    example_flexible_matching()
    example_best_practices()

    print("=" * 70)
    print("All Examples Complete!")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("  1. Configure group_permissions in config.yml")
    print("  2. Map your AD groups to appropriate permissions")
    print("  3. Run: python scripts/sync_ad_users.py")
    print("  4. Verify permissions in extension configs")
    print()


if __name__ == "__main__":
    main()
