#!/usr/bin/env python3
"""
Export All Built-in Provisioning Templates

This script exports all built-in phone provisioning templates to the
provisioning_templates directory for customization.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.utils.config import Config


def main():
    """Export all built-in templates to files"""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Export all built-in phone provisioning templates to files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/export_all_templates.py
  python scripts/export_all_templates.py --config config.yml
  python scripts/export_all_templates.py --config /path/to/custom_config.yml
        """,
    )
    parser.add_argument(
        "--config", default="config.yml", help="Path to configuration file (default: config.yml)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Export All Provisioning Templates")
    print("=" * 70)
    print()

    # Load config
    config_path = args.config
    if not Path(config_path).exists():
        print(f"❌ Config file not found: {config_path}")
        print("   Please specify a valid config file path")
        return 1

    print(f"📋 Loading configuration from {config_path}...")
    config = Config(config_path)

    # Initialize provisioning system
    print("🔧 Initializing phone provisioning system...")
    provisioning = PhoneProvisioning(config)

    # Get all templates
    templates = provisioning.list_all_templates()
    print(f"✓ Found {len(templates)} templates")
    print()

    # Export each template
    print("📤 Exporting templates...")
    print()

    exported_count = 0
    skipped_count = 0
    failed_count = 0

    for template_info in templates:
        vendor = template_info["vendor"]
        model = template_info["model"]
        template_name = f"{vendor}_{model}"

        # Check if already exported (custom)
        if template_info["is_custom"]:
            print(f"⏭️  {template_name:25} - already exists (custom), skipping")
            skipped_count += 1
            continue

        # Export the template
        success, message, filepath = provisioning.export_template_to_file(vendor, model)

        if success:
            print(f"✓  {template_name:25} - exported to {filepath}")
            exported_count += 1
        else:
            print(f"❌ {template_name:25} - failed: {message}")
            failed_count += 1

    # Summary
    print()
    print("=" * 70)
    print("Export Summary")
    print("=" * 70)
    print(f"✓ Exported:  {exported_count} templates")
    print(f"⏭️  Skipped:   {skipped_count} templates (already exist)")
    if failed_count > 0:
        print(f"❌ Failed:    {failed_count} templates")
    print()

    # Show next steps
    if exported_count > 0:
        # Get API URL from config
        api_host = config.get("server.external_ip", "localhost")
        api_port = config.get("api.port", 8080)
        api_url = f"https://{api_host}:{api_port}"

        print("Next steps:")
        print("1. Review the exported templates in the provisioning_templates directory")
        print("2. Customize any templates as needed")
        print("3. Restart the PBX server or reload templates:")
        print(f"   curl -X POST {api_url}/api/provisioning/reload-templates")
        print()

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except (KeyError, TypeError, ValueError) as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
