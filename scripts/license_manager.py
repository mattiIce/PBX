#!/usr/bin/env python3
"""
License Management CLI Tool

Command-line utility for generating, installing, and managing licenses.

Usage:
    python scripts/license_manager.py --help
    python scripts/license_manager.py generate --type professional --org "Example Corp"
    python scripts/license_manager.py install license.json
    python scripts/license_manager.py status
    python scripts/license_manager.py enable
    python scripts/license_manager.py disable
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.licensing import LicenseManager, LicenseType, LicenseStatus


def setup_config():
    """Load configuration for license manager."""
    # Try to load from config.yml
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('licensing', {})
    except Exception as e:
        print(f"Warning: Could not load config.yml: {e}")
    
    return {}


def cmd_generate(args):
    """Generate a new license."""
    config = setup_config()
    lm = LicenseManager(config)
    
    # Parse license type
    try:
        license_type = LicenseType(args.type)
    except ValueError:
        print(f"Error: Invalid license type '{args.type}'")
        print(f"Valid types: {', '.join([t.value for t in LicenseType])}")
        return 1
    
    # Parse custom features if provided
    custom_features = None
    if args.features:
        custom_features = args.features.split(',')
    
    # Generate license
    print(f"Generating {license_type.value} license for '{args.org}'...")
    
    license_data = lm.generate_license_key(
        license_type=license_type,
        issued_to=args.org,
        max_extensions=args.max_extensions,
        max_concurrent_calls=args.max_calls,
        expiration_days=args.days,
        custom_features=custom_features
    )
    
    # Save to file
    output_file = args.output or f"license_{args.org.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(output_file, 'w') as f:
        json.dump(license_data, f, indent=2)
    
    print(f"\n✓ License generated successfully!")
    print(f"\nLicense Key: {license_data['key']}")
    print(f"Type: {license_data['type']}")
    print(f"Issued To: {license_data['issued_to']}")
    print(f"Issued Date: {license_data['issued_date']}")
    print(f"Expiration: {license_data.get('expiration', 'Never (Perpetual)')}")
    print(f"\nLicense saved to: {output_file}")
    print(f"\nTo install: python {__file__} install {output_file}")
    
    return 0


def cmd_install(args):
    """Install a license file."""
    config = setup_config()
    lm = LicenseManager(config)
    
    # Load license file
    if not os.path.exists(args.license_file):
        print(f"Error: License file not found: {args.license_file}")
        return 1
    
    try:
        with open(args.license_file, 'r') as f:
            license_data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to load license file: {e}")
        return 1
    
    # Install license
    print(f"Installing license from {args.license_file}...")
    
    if lm.save_license(license_data):
        print("\n✓ License installed successfully!")
        
        # Show status
        status, message = lm.get_license_status()
        print(f"\nStatus: {status.value}")
        print(f"Message: {message}")
        
        return 0
    else:
        print("\n✗ Failed to install license")
        return 1


def cmd_status(args):
    """Show license status."""
    config = setup_config()
    lm = LicenseManager(config)
    
    info = lm.get_license_info()
    
    print("=" * 60)
    print("LICENSE STATUS")
    print("=" * 60)
    
    print(f"\nLicensing Enabled: {info['enabled']}")
    print(f"Status: {info['status']}")
    print(f"Message: {info['message']}")
    
    if info.get('type'):
        print(f"\nLicense Type: {info['type']}")
    
    if info.get('issued_to'):
        print(f"Issued To: {info['issued_to']}")
        print(f"Issued Date: {info['issued_date']}")
        print(f"Expiration: {info.get('expiration', 'Never')}")
        print(f"License Key: {info.get('key', 'N/A')}")
    
    if info.get('limits'):
        print(f"\nLimits:")
        for limit_name, limit_value in info['limits'].items():
            display_value = 'Unlimited' if limit_value is None else limit_value
            print(f"  {limit_name}: {display_value}")
    
    print()
    return 0


def cmd_revoke(args):
    """Revoke current license."""
    config = setup_config()
    lm = LicenseManager(config)
    
    if not args.yes:
        response = input("Are you sure you want to revoke the current license? (yes/no): ")
        if response.lower() not in ('yes', 'y'):
            print("Aborted.")
            return 0
    
    print("Revoking license...")
    
    if lm.revoke_license():
        print("✓ License revoked successfully")
        return 0
    else:
        print("✗ Failed to revoke license")
        return 1


def cmd_enable(args):
    """Enable licensing enforcement."""
    # Update environment file
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    
    print("Enabling licensing enforcement...")
    
    # Read existing .env
    env_lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add PBX_LICENSING_ENABLED
    found = False
    for i, line in enumerate(env_lines):
        if line.startswith('PBX_LICENSING_ENABLED='):
            env_lines[i] = 'PBX_LICENSING_ENABLED=true\n'
            found = True
            break
    
    if not found:
        env_lines.append('\n# Licensing\nPBX_LICENSING_ENABLED=true\n')
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(env_lines)
    
    print("✓ Licensing enabled in .env file")
    print("\nNote: Restart the PBX system for changes to take effect:")
    print("  sudo systemctl restart pbx")
    
    return 0


def cmd_disable(args):
    """Disable licensing enforcement."""
    # Update environment file
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    
    print("Disabling licensing enforcement...")
    
    # Read existing .env
    env_lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add PBX_LICENSING_ENABLED
    found = False
    for i, line in enumerate(env_lines):
        if line.startswith('PBX_LICENSING_ENABLED='):
            env_lines[i] = 'PBX_LICENSING_ENABLED=false\n'
            found = True
            break
    
    if not found:
        env_lines.append('\n# Licensing\nPBX_LICENSING_ENABLED=false\n')
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(env_lines)
    
    print("✓ Licensing disabled in .env file (all features unlocked)")
    print("\nNote: Restart the PBX system for changes to take effect:")
    print("  sudo systemctl restart pbx")
    
    return 0


def cmd_features(args):
    """List available features for current license."""
    config = setup_config()
    lm = LicenseManager(config)
    
    if not lm.enabled:
        print("Licensing is DISABLED - all features are available")
        return 0
    
    # Get license type
    if lm.current_license:
        license_type = lm.current_license.get('type', 'trial')
    else:
        license_type = 'trial'
    
    # Get features
    features = lm.features.get(license_type, [])
    
    if license_type == 'custom' and lm.current_license:
        features = lm.current_license.get('custom_features', [])
    
    print(f"\nAvailable Features ({license_type} license):")
    print("=" * 60)
    
    # Separate features and limits
    feature_list = []
    limits = {}
    
    for feature in features:
        if ':' in feature and any(feature.startswith(f'{limit}:') for limit in ['max_extensions', 'max_concurrent_calls']):
            limit_name, limit_value = feature.split(':', 1)
            limits[limit_name] = None if limit_value == 'unlimited' else int(limit_value)
        else:
            feature_list.append(feature)
    
    # Print features
    for feature in sorted(feature_list):
        print(f"  ✓ {feature}")
    
    # Print limits
    if limits:
        print(f"\nLimits:")
        for limit_name, limit_value in limits.items():
            display_value = 'Unlimited' if limit_value is None else f"{limit_value:,}"
            print(f"  • {limit_name.replace('_', ' ').title()}: {display_value}")
    
    print()
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='License Management CLI Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a professional license
  python scripts/license_manager.py generate --type professional --org "Acme Corp" --days 365

  # Generate an enterprise license (unlimited, 1 year)
  python scripts/license_manager.py generate --type enterprise --org "BigCo Inc" --days 365

  # Generate a perpetual license (never expires)
  python scripts/license_manager.py generate --type perpetual --org "Example LLC"

  # Install a license
  python scripts/license_manager.py install license_acme_corp_20251222.json

  # Check license status
  python scripts/license_manager.py status

  # List available features
  python scripts/license_manager.py features

  # Enable licensing
  python scripts/license_manager.py enable

  # Disable licensing (free/open-source mode)
  python scripts/license_manager.py disable

  # Revoke current license
  python scripts/license_manager.py revoke
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a new license')
    gen_parser.add_argument('--type', required=True, help='License type (trial, basic, professional, enterprise, perpetual, custom)')
    gen_parser.add_argument('--org', required=True, help='Organization/person name')
    gen_parser.add_argument('--days', type=int, help='Days until expiration (omit for perpetual)')
    gen_parser.add_argument('--max-extensions', type=int, help='Maximum extensions')
    gen_parser.add_argument('--max-calls', type=int, help='Maximum concurrent calls')
    gen_parser.add_argument('--features', help='Custom features (comma-separated, for custom type)')
    gen_parser.add_argument('--output', '-o', help='Output file path')
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install a license file')
    install_parser.add_argument('license_file', help='Path to license JSON file')
    
    # Status command
    subparsers.add_parser('status', help='Show license status')
    
    # Features command
    subparsers.add_parser('features', help='List available features')
    
    # Revoke command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke current license')
    revoke_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    
    # Enable command
    subparsers.add_parser('enable', help='Enable licensing enforcement')
    
    # Disable command
    subparsers.add_parser('disable', help='Disable licensing enforcement')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        if args.command == 'generate':
            return cmd_generate(args)
        elif args.command == 'install':
            return cmd_install(args)
        elif args.command == 'status':
            return cmd_status(args)
        elif args.command == 'features':
            return cmd_features(args)
        elif args.command == 'revoke':
            return cmd_revoke(args)
        elif args.command == 'enable':
            return cmd_enable(args)
        elif args.command == 'disable':
            return cmd_disable(args)
        else:
            parser.print_help()
            return 1
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
