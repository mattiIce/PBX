#!/usr/bin/env python3
"""
Interactive Phone Provisioning Setup Script

This script provides an interactive way to set up phone auto-provisioning
by asking the user for settings rather than requiring manual REST API calls
or config file editing.
"""

import os
import sys
from pathlib import Path

import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  Warning: 'requests' module not available. Some features may be limited.")
    print("   Install with: pip install requests")


class PhoneProvisioningSetup:
    """Interactive setup for phone provisioning"""

    def __init__(
        self, config_path: str = "config.yml", api_url: str = "https://localhost:9000"
    ) -> None:
        self.config_path = config_path
        self.api_url = api_url
        self.config = None
        self.pbx_running = False
        self.devices_to_register = []

    def clear_screen(self) -> None:
        """Clear the terminal screen"""
        os.system("clear" if os.name != "nt" else "cls")

    def print_header(self, text: str) -> None:
        """Print a formatted header"""
        print("\n" + "=" * 70)
        print(f"  {text}")
        print("=" * 70 + "\n")

    def print_section(self, text: str) -> None:
        """Print a formatted section header"""
        print(f"\n{'─' * 70}")
        print(f"  {text}")
        print("─" * 70)

    def get_input(
        self, prompt: str, default: str | None = None, validation_func: object = None
    ) -> str:
        """Get user input with optional default and validation"""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()

            if not user_input and not default:
                print("❌ This field is required. Please enter a value.")
                continue

            if validation_func:
                is_valid, error_msg = validation_func(user_input)
                if not is_valid:
                    print(f"❌ {error_msg}")
                    continue

            return user_input

    def get_yes_no(self, prompt: str, default: str = "y") -> bool:
        """Get yes/no input from user"""
        default_text = "Y/n" if default.lower() == "y" else "y/N"
        response = input(f"{prompt} [{default_text}]: ").strip().lower()
        if not response:
            response = default.lower()
        return response in ["y", "yes"]

    def validate_mac_address(self, mac: str) -> tuple[bool, str | None]:
        """Validate MAC address format"""
        # Remove common separators
        cleaned = mac.replace(":", "").replace("-", "").replace(".", "")
        if len(cleaned) == 12:
            try:
                int(cleaned, 16)
                return True, None
            except ValueError:
                pass
        return False, "Invalid MAC address format. Use format like: 00:15:65:12:34:56"

    def validate_extension(self, ext: str) -> tuple[bool, str | None]:
        """Validate extension number"""
        if ext.isdigit() and len(ext) >= 3:
            return True, None
        return False, "Extension must be a number with at least 3 digits"

    def load_config(self) -> bool:
        """Load the PBX configuration file"""
        try:
            with Path(self.config_path).open() as f:
                self.config = yaml.safe_load(f)
            return True
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {self.config_path}")
            return False
        except (KeyError, OSError, TypeError, ValueError) as e:
            print(f"❌ Error loading configuration: {e}")
            return False

    def save_config(self) -> bool:
        """Save the PBX configuration file"""
        try:
            with Path(self.config_path).open("w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            return True
        except OSError as e:
            print(f"❌ Error saving configuration: {e}")
            return False

    def check_pbx_running(self) -> bool:
        """Check if PBX is currently running"""
        if not REQUESTS_AVAILABLE:
            return False

        try:
            response = requests.get(f"{self.api_url}/api/status", timeout=2)
            self.pbx_running = response.status_code == 200
            return self.pbx_running
        except (KeyError, TypeError, ValueError, requests.RequestException):
            self.pbx_running = False
            return False

    def get_supported_vendors(self) -> dict:
        """Get list of supported phone vendors and models"""
        if not REQUESTS_AVAILABLE or not self.pbx_running:
            # Return defaults if PBX is not running
            return {
                "vendors": ["zultys", "yealink", "polycom", "cisco", "grandstream"],
                "models": {
                    "zultys": ["zip33g", "zip37g"],
                    "yealink": ["t46s"],
                    "polycom": ["vvx450"],
                    "cisco": ["spa504g"],
                    "grandstream": ["gxp2170"],
                },
            }

        try:
            response = requests.get(f"{self.api_url}/api/provisioning/vendors", timeout=2)
            if response.status_code == 200:
                return response.json()
        except (KeyError, TypeError, ValueError, requests.RequestException):
            pass

        return {"vendors": [], "models": {}}

    def get_extensions(self) -> list[str]:
        """Get list of configured extensions"""
        if not self.config:
            return []

        extensions = self.config.get("extensions", [])
        return [ext["number"] for ext in extensions]

    def register_device_api(self, mac: str, extension: str, vendor: str, model: str) -> bool:
        """Register a device via API (if PBX is running)"""
        if not REQUESTS_AVAILABLE or not self.pbx_running:
            return False

        try:
            response = requests.post(
                f"{self.api_url}/api/provisioning/devices",
                json={
                    "mac_address": mac,
                    "extension_number": extension,
                    "vendor": vendor,
                    "model": model,
                },
                timeout=5,
            )
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"❌ Error registering device: {e}")
            return False

    def add_device_to_config(self, mac: str, extension: str, vendor: str, model: str) -> bool:
        """Add device to config.yml provisioning section"""
        if not self.config:
            return False

        # Ensure provisioning section exists
        if "provisioning" not in self.config:
            self.config["provisioning"] = {}

        if "devices" not in self.config["provisioning"]:
            self.config["provisioning"]["devices"] = []

        # Normalize MAC address
        mac_normalized = mac.replace(":", "").replace("-", "").replace(".", "").lower()

        # Add device if not already present
        devices = self.config["provisioning"]["devices"]
        for device in devices:
            if (
                device.get("mac", "").replace(":", "").replace("-", "").replace(".", "").lower()
                == mac_normalized
            ):
                print(f"⚠️  Device with MAC {mac} already in config, updating...")
                device["extension"] = extension
                device["vendor"] = vendor
                device["model"] = model
                return True

        # Add new device
        devices.append({"mac": mac, "extension": extension, "vendor": vendor, "model": model})

        return True

    def setup_provisioning_settings(self) -> bool:
        """Configure basic provisioning settings"""
        self.print_section("Step 1: Provisioning Settings")

        if not self.config:
            print("❌ Configuration not loaded")
            return False

        # Get current settings
        provisioning = self.config.get("provisioning", {})
        current_enabled = provisioning.get("enabled", False)

        print(f"Current provisioning status: {'Enabled' if current_enabled else 'Disabled'}")
        print()

        # Ask if user wants to enable provisioning
        enable = self.get_yes_no("Enable phone auto-provisioning?", "y")

        if not enable:
            print("ℹ️  Phone provisioning will remain disabled")
            return True

        # Get server IP
        server_section = self.config.get("server", {})
        current_ip = server_section.get("external_ip", "192.168.1.14")

        print(
            "\nℹ️  The PBX server IP address that phones will use to download their configuration."
        )
        print("   This should be the IP address of this PBX server on your network.")
        server_ip = self.get_input("Enter PBX server IP address", current_ip)

        # Get API port
        api_section = self.config.get("api", {})
        current_port = api_section.get("port", 9000)

        port = self.get_input("Enter API port", str(current_port))

        # Build provisioning URL
        url_format = f"https://{server_ip}:{port}/provision/{{mac}}.cfg"

        print("\nℹ️  Phones will download configuration from:")
        print(f"   {url_format}")
        print()

        # Ask about custom templates
        has_custom = self.get_yes_no("Do you have custom phone templates?", "n")
        custom_dir = ""
        if has_custom:
            custom_dir = self.get_input(
                "Enter path to custom templates directory", "custom_templates"
            )

        # Update config
        self.config["provisioning"] = {
            "enabled": True,
            "url_format": url_format,
            "custom_templates_dir": custom_dir,
            "devices": provisioning.get("devices", []),
        }

        # Update server IP if changed
        if "server" not in self.config:
            self.config["server"] = {}
        self.config["server"]["external_ip"] = server_ip

        print("\n✅ Provisioning settings configured")
        return True

    def add_phone_device(self) -> dict | None:
        """Add a phone device interactively"""
        self.print_section("Add Phone Device")

        # Get supported vendors and models
        vendor_data = self.get_supported_vendors()
        vendors = vendor_data.get("vendors", [])
        models_dict = vendor_data.get("models", {})

        if not vendors:
            print(
                "❌ No phone vendors available. Make sure PBX is running or templates are configured."
            )
            return None

        # Show available vendors
        print("Available phone vendors:")
        for i, vendor in enumerate(vendors, 1):
            print(f"  {i}. {vendor.upper()}")
        print()

        # Select vendor
        if len(vendors) == 1:
            vendor = vendors[0]
            print(f"Using vendor: {vendor.upper()}")
        else:
            vendor_choice = self.get_input(f"Select vendor (1-{len(vendors)})", "1")
            try:
                vendor_idx = int(vendor_choice) - 1
                if 0 <= vendor_idx < len(vendors):
                    vendor = vendors[vendor_idx]
                else:
                    print("❌ Invalid vendor selection")
                    return None
            except ValueError:
                # Allow typing vendor name
                vendor = vendor_choice.lower()
                if vendor not in vendors:
                    print("❌ Invalid vendor")
                    return None

        # Show available models for selected vendor
        models = models_dict.get(vendor, [])
        if not models:
            print(f"❌ No models available for vendor: {vendor}")
            return None

        print(f"\nAvailable models for {vendor.upper()}:")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model.upper()}")
        print()

        # Select model
        if len(models) == 1:
            model = models[0]
            print(f"Using model: {model.upper()}")
        else:
            model_choice = self.get_input(f"Select model (1-{len(models)})", "1")
            try:
                model_idx = int(model_choice) - 1
                if 0 <= model_idx < len(models):
                    model = models[model_idx]
                else:
                    print("❌ Invalid model selection")
                    return None
            except ValueError:
                # Allow typing model name
                model = model_choice.lower()
                if model not in models:
                    print("❌ Invalid model")
                    return None

        # Get MAC address
        print("\nℹ️  Enter the MAC address of the phone.")
        print("   You can find this on a label on the phone or in the phone's network settings.")
        print("   Format: 00:15:65:12:34:56 or 001565123456")
        mac = self.get_input("MAC Address", validation_func=self.validate_mac_address)

        # Get extension
        available_extensions = self.get_extensions()
        if available_extensions:
            print(f"\nℹ️  Available extensions: {', '.join(available_extensions)}")

        extension = self.get_input("Extension Number", validation_func=self.validate_extension)

        # Verify extension exists
        if available_extensions and extension not in available_extensions:
            print(f"⚠️  Warning: Extension {extension} is not configured in the system.")
            if not self.get_yes_no("Continue anyway?", "n"):
                return None

        return {"mac": mac, "extension": extension, "vendor": vendor, "model": model}

    def display_device_summary(self) -> None:
        """Display summary of devices to be registered"""
        if not self.devices_to_register:
            return

        self.print_section("Devices to Register")
        print(f"Total devices: {len(self.devices_to_register)}\n")

        for i, device in enumerate(self.devices_to_register, 1):
            print(f"{i}. MAC: {device['mac']}")
            print(f"   Extension: {device['extension']}")
            print(f"   Phone: {device['vendor'].upper()} {device['model'].upper()}")
            print()

    def batch_add_devices(self) -> bool:
        """Add multiple phone devices"""
        self.print_section("Step 2: Add Phone Devices")

        print("You can add phone devices one at a time.")
        print("Each device needs:")
        print("  - MAC address (found on phone label or network settings)")
        print("  - Extension number to assign")
        print("  - Phone vendor and model")
        print()

        while True:
            device = self.add_phone_device()
            if device:
                self.devices_to_register.append(device)
                print(f"\n✅ Device added: {device['mac']} → Extension {device['extension']}")
            else:
                print("\n❌ Device not added")

            print()
            if not self.get_yes_no("Add another device?", "y"):
                break

        if self.devices_to_register:
            self.display_device_summary()

        return len(self.devices_to_register) > 0

    def register_devices(self) -> bool:
        """Register all devices"""
        if not self.devices_to_register:
            print("ℹ️  No devices to register")
            return True

        self.print_section("Step 3: Register Devices")

        # Check if PBX is running
        if self.check_pbx_running():
            print("✅ PBX is running - devices will be registered via API")
            method = "api"
        else:
            print("ℹ️  PBX is not running - devices will be saved to config.yml")
            print("   (You'll need to restart the PBX for them to take effect)")
            method = "config"

        print()

        success_count = 0
        fail_count = 0

        for i, device in enumerate(self.devices_to_register, 1):
            print(f"[{i}/{len(self.devices_to_register)}] Registering {device['mac']}...", end=" ")

            if method == "api":
                if self.register_device_api(
                    device["mac"], device["extension"], device["vendor"], device["model"]
                ):
                    print("✅")
                    success_count += 1
                else:
                    print("❌")
                    fail_count += 1
                    # Fallback to config
                    if self.add_device_to_config(
                        device["mac"], device["extension"], device["vendor"], device["model"]
                    ):
                        print("   → Added to config.yml as fallback")
            elif self.add_device_to_config(
                device["mac"], device["extension"], device["vendor"], device["model"]
            ):
                print("✅")
                success_count += 1
            else:
                print("❌")
                fail_count += 1

        print(f"\n📊 Results: {success_count} succeeded, {fail_count} failed")

        # Save config if we added devices there
        if method == "config" or fail_count > 0:
            if self.save_config():
                print("✅ Configuration saved to config.yml")
            else:
                print("❌ Failed to save configuration")
                return False

        return success_count > 0

    def show_next_steps(self) -> None:
        """Show next steps after setup"""
        self.print_section("Next Steps")

        if not self.pbx_running:
            print("1. Start the PBX system:")
            print("   python main.py")
            print()

        print("2. Configure your DHCP server to provide the provisioning URL:")

        if self.config:
            provisioning = self.config.get("provisioning", {})
            url_format = provisioning.get("url_format", "")
            if url_format:
                print(f"   Option 66: {url_format}")

        print()
        print("3. Reboot your phones, and they will automatically download their configuration")
        print()
        print("4. Alternatively, manually configure each phone with the provisioning URL")
        print()
        print("5. Monitor registered phones in the admin panel:")
        if self.config:
            api_section = self.config.get("api", {})
            port = api_section.get("port", 9000)
            server_section = self.config.get("server", {})
            ip = server_section.get("external_ip", "localhost")
            print(f"   https://{ip}:{port}/admin/")

        print()
        print("📚 For more information, see PHONE_PROVISIONING.md")

    def run(self) -> bool:
        """Run the interactive setup"""
        self.clear_screen()
        self.print_header("Phone Auto-Provisioning Setup Wizard")

        print("This wizard will help you set up automatic phone provisioning.")
        print("You'll be asked for settings to configure phones without manual API calls.")
        print()

        # Check PBX status
        print("Checking PBX status...", end=" ")
        if self.check_pbx_running():
            print("✅ PBX is running")
        else:
            print("⚠️  PBX is not running (devices will be saved to config.yml)")
        print()

        # Load configuration
        print("Loading configuration...", end=" ")
        if not self.load_config():
            print("❌ Failed")
            return False
        print("✅ Loaded")

        input("\nPress Enter to continue...")

        # Step 1: Configure provisioning settings
        self.clear_screen()
        self.print_header("Phone Auto-Provisioning Setup Wizard")
        if not self.setup_provisioning_settings():
            return False

        input("\nPress Enter to continue...")

        # Step 2: Add phone devices
        self.clear_screen()
        self.print_header("Phone Auto-Provisioning Setup Wizard")
        if not self.batch_add_devices():
            print("\nℹ️  No devices added. You can add them later via the API or config.yml")

        input("\nPress Enter to continue...")

        # Step 3: Register devices
        self.clear_screen()
        self.print_header("Phone Auto-Provisioning Setup Wizard")
        if self.devices_to_register:
            self.register_devices()

        input("\nPress Enter to continue...")

        # Show next steps
        self.clear_screen()
        self.print_header("Setup Complete!")
        self.show_next_steps()

        return True


def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive phone provisioning setup wizard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings
  python scripts/setup_phone_provisioning.py

  # Specify custom config file
  python scripts/setup_phone_provisioning.py --config /path/to/config.yml

  # Use different API URL
  python scripts/setup_phone_provisioning.py --api-url https://192.168.1.100:9000
        """,
    )

    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to PBX configuration file (default: config.yml)",
    )

    parser.add_argument(
        "--api-url",
        default="https://localhost:9000",
        help="PBX API URL (default: https://localhost:9000)",
    )

    args = parser.parse_args()

    # Create and run setup
    setup = PhoneProvisioningSetup(config_path=args.config, api_url=args.api_url)

    try:
        success = setup.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except (KeyError, TypeError, ValueError) as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
