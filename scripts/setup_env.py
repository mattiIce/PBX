#!/usr/bin/env python3
"""
Environment Variable Setup Script

This interactive script helps you create and update the .env file
with all the required environment variables for the PBX system.

Usage:
    python scripts/setup_env.py

The .env file location:
    - File path: .env (in the root directory of the PBX project)
    - This file is automatically loaded when the PBX system starts
    - It's ignored by Git, so your credentials stay private
"""

import sys
from pathlib import Path

# Environment variable definitions with descriptions and defaults
ENV_VARS = {
    "Database Configuration": {
        "DB_HOST": {
            "description": "Database host address",
            "default": "localhost",
            "required": False,
            "example": "localhost or 192.168.1.50",
        },
        "DB_PORT": {
            "description": "Database port",
            "default": "5432",
            "required": False,
            "example": "5432 for PostgreSQL",
        },
        "DB_NAME": {
            "description": "Database name",
            "default": "pbx_system",
            "required": False,
            "example": "pbx_system",
        },
        "DB_USER": {
            "description": "Database username",
            "default": "pbx_user",
            "required": False,
            "example": "pbx_user",
        },
        "DB_PASSWORD": {
            "description": "Database password",
            "default": "",
            "required": False,
            "example": "YourSecurePassword123!",
            "sensitive": True,
        },
    },
    "Active Directory Configuration": {
        "AD_BIND_PASSWORD": {
            "description": "Active Directory bind password",
            "default": "",
            "required": True,
            "example": "YourADPassword",
            "sensitive": True,
            "help": "Password for the AD service account (bind_dn) configured in config.yml",
        },
    },
    "Email (SMTP) Configuration": {
        "SMTP_HOST": {
            "description": "SMTP server hostname",
            "default": "",
            "required": False,
            "example": "192.168.1.75 or smtp.gmail.com",
        },
        "SMTP_PORT": {
            "description": "SMTP server port",
            "default": "587",
            "required": False,
            "example": "587 (TLS) or 465 (SSL)",
        },
        "SMTP_USERNAME": {
            "description": "SMTP username",
            "default": "",
            "required": False,
            "example": "your-email@company.com",
        },
        "SMTP_PASSWORD": {
            "description": "SMTP password",
            "default": "",
            "required": False,
            "example": "your-email-password",
            "sensitive": True,
        },
    },
    "Zoom Integration (Optional)": {
        "ZOOM_CLIENT_ID": {
            "description": "Zoom API client ID",
            "default": "",
            "required": False,
            "example": "your-zoom-client-id",
        },
        "ZOOM_CLIENT_SECRET": {
            "description": "Zoom API client secret",
            "default": "",
            "required": False,
            "example": "your-zoom-client-secret",
            "sensitive": True,
        },
    },
    "Microsoft Outlook/Teams Integration (Optional)": {
        "OUTLOOK_CLIENT_ID": {
            "description": "Outlook API client ID",
            "default": "",
            "required": False,
            "example": "your-outlook-client-id",
        },
        "OUTLOOK_CLIENT_SECRET": {
            "description": "Outlook API client secret",
            "default": "",
            "required": False,
            "example": "your-outlook-client-secret",
            "sensitive": True,
        },
        "TEAMS_CLIENT_ID": {
            "description": "Teams API client ID",
            "default": "",
            "required": False,
            "example": "your-teams-client-id",
        },
        "TEAMS_CLIENT_SECRET": {
            "description": "Teams API client secret",
            "default": "",
            "required": False,
            "example": "your-teams-client-secret",
            "sensitive": True,
        },
    },
    "Voicemail Transcription (Optional)": {
        "TRANSCRIPTION_API_KEY": {
            "description": "API key for voicemail transcription service (OpenAI or Google)",
            "default": "",
            "required": False,
            "example": "sk-proj-...",
            "sensitive": True,
            "help": "Only needed if voicemail_transcription.enabled is true in config.yml. Get OpenAI key from https://platform.openai.com/api-keys",
        },
    },
}


def get_project_root() -> Path:
    """Get the project root directory"""
    # Script is in scripts/, so parent is project root
    return Path(__file__).parent.parent


def read_existing_env() -> tuple[dict[str, str], Path]:
    """Read existing .env file if it exists"""
    env_file = get_project_root() / ".env"
    env_vars = {}

    if env_file.exists():
        print(f"✓ Found existing .env file at: {env_file}")
        with env_file.open() as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith("#") and "=" in stripped_line:
                    key, value = stripped_line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]
                    env_vars[key.strip()] = value
    else:
        print(f"ℹ No existing .env file found. Will create new one at: {env_file}")

    return env_vars, env_file


def prompt_for_value(
    var_name: str, var_info: dict, current_value: str | None = None, retry_count: int = 0
) -> str:
    """Prompt user for an environment variable value"""
    # Prevent infinite recursion
    if retry_count >= 3:
        print("  ⚠ Maximum retries reached. Using empty value.")
        return ""

    desc = var_info["description"]
    default = current_value or var_info.get("default", "")
    example = var_info.get("example", "")
    required = var_info.get("required", False)
    help_text = var_info.get("help", "")

    # Show description
    print(f"\n{var_name}")
    print(f"  Description: {desc}")
    if help_text:
        print(f"  Note: {help_text}")
    if example:
        print(f"  Example: {example}")

    # Show current value (masked if sensitive)
    if current_value:
        if var_info.get("sensitive", False) and current_value:
            masked = "*" * min(len(current_value), 8)
            print(f"  Current: {masked}")
        else:
            print(f"  Current: {current_value}")

    # Prompt for new value
    prompt = "  New value"
    if default and not required:
        prompt += " (press Enter to keep current/default)"
    elif required and not current_value:
        prompt += " [REQUIRED]"
    prompt += ": "

    new_value = input(prompt).strip()

    # Use default if no value provided
    if not new_value:
        if current_value:
            return current_value
        if default:
            return default
        if required:
            print("  ⚠ This value is required!")
            return prompt_for_value(var_name, var_info, current_value, retry_count + 1)

    return new_value


def write_env_file(env_vars: dict[str, str], env_file: Path) -> None:
    """Write environment variables to .env file"""
    with env_file.open("w") as f:
        f.write("# Warden Voip System Environment Variables\n")
        f.write("# This file is automatically generated by scripts/setup_env.py\n")
        f.write("# DO NOT commit this file to version control!\n")
        f.write("\n")

        for category, vars_dict in ENV_VARS.items():
            f.write(f"# {category}\n")
            for var_name in vars_dict:
                value = env_vars.get(var_name, "")
                # Quote values that contain spaces or special characters
                # When wrapping in double quotes, only double quotes need escaping
                # Single quotes are safe inside double quotes
                if " " in value or '"' in value or "'" in value:
                    # Escape existing double quotes to prevent syntax errors
                    value = value.replace('"', '\\"')
                    value = f'"{value}"'
                f.write(f"{var_name}={value}\n")
            f.write("\n")


def main() -> None:
    print("=" * 70)
    print("Warden Voip System - Environment Variable Setup")
    print("=" * 70)
    print()
    print("This script will help you set up the .env file with your credentials.")
    print("The .env file location: .env (in the project root directory)")
    print()

    # Read existing values
    existing_env, env_file = read_existing_env()
    print()

    # Ask what to do
    if existing_env:
        print("Options:")
        print("  1. Update all variables (interactive)")
        print("  2. Update specific variables only")
        print("  3. Quick setup (only required variables)")
        print("  4. Cancel")
        choice = input("\nChoose an option (1-4): ").strip()

        if choice == "4":
            print("Cancelled.")
            return
        if choice == "3":
            update_mode = "required"
        elif choice == "2":
            update_mode = "specific"
        else:
            update_mode = "all"
    else:
        print("Options:")
        print("  1. Full setup (all variables)")
        print("  2. Quick setup (only required variables)")
        print("  3. Cancel")
        choice = input("\nChoose an option (1-3): ").strip()

        if choice == "3":
            print("Cancelled.")
            return
        if choice == "2":
            update_mode = "required"
        else:
            update_mode = "all"

    print()

    # Collect values
    new_env = existing_env.copy()

    if update_mode == "specific":
        print("Available variables:")
        all_vars = []
        var_info_map = {}  # Create flat mapping for efficient lookup
        idx = 1
        for vars_dict in ENV_VARS.values():
            for var_name, var_info in vars_dict.items():
                all_vars.append(var_name)
                var_info_map[var_name] = var_info
                current = new_env.get(var_name, "")
                status = "(set)" if current else "(not set)"
                print(f"  {idx}. {var_name} {status}")
                idx += 1

        print()
        selection = input(
            "Enter variable numbers to update (comma-separated, e.g., 1,3,5): "
        ).strip()

        # Parse selections and track invalid inputs
        selected_indices = []
        invalid_inputs = []
        for item in selection.split(","):
            stripped_item = item.strip()
            if not stripped_item:
                continue
            try:
                num = int(stripped_item)
                if num >= 1:  # Only accept positive numbers starting from 1
                    selected_indices.append(num - 1)
                else:
                    invalid_inputs.append(stripped_item)
            except ValueError:
                invalid_inputs.append(stripped_item)

        # Warn about invalid inputs
        if invalid_inputs:
            print(f"⚠ Ignoring invalid selections: {', '.join(invalid_inputs)}")

        if not selected_indices:
            print("⚠ No valid selections made. Exiting.")
            return

        # Track out-of-range selections
        out_of_range = [str(i + 1) for i in selected_indices if i < 0 or i >= len(all_vars)]
        if out_of_range:
            print(f"⚠ Ignoring out-of-range selections: {', '.join(out_of_range)}")

        # Process valid selections
        for i in selected_indices:
            if 0 <= i < len(all_vars):
                var_name = all_vars[i]
                var_info = var_info_map[var_name]
                current_value = new_env.get(var_name, "")
                new_env[var_name] = prompt_for_value(var_name, var_info, current_value)
    else:
        for category, vars_dict in ENV_VARS.items():
            print(f"\n{'=' * 70}")
            print(f"{category}")
            print("=" * 70)

            for var_name, var_info in vars_dict.items():
                # Skip if only doing required and this is not required
                if update_mode == "required" and not var_info.get("required", False):
                    # Keep existing value or use default
                    if var_name not in new_env:
                        new_env[var_name] = var_info.get("default", "")
                    continue

                current_value = new_env.get(var_name, "")
                new_env[var_name] = prompt_for_value(var_name, var_info, current_value)

    # Write the file
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\nThe following variables will be saved to: {env_file}")
    print()

    for category, vars_dict in ENV_VARS.items():
        print(f"{category}:")
        for var_name, var_info in vars_dict.items():
            value = new_env.get(var_name, "")
            if var_info.get("sensitive", False) and value:
                display_value = "*" * 8
            else:
                display_value = value or "(not set)"
            print(f"  {var_name}: {display_value}")
        print()

    confirm = input("Save these settings? (yes/no): ").strip().lower()
    if confirm in ["yes", "y"]:
        write_env_file(new_env, env_file)
        print(f"\n✓ Environment variables saved to: {env_file}")
        print("\nNext steps:")
        print("  1. The .env file is now ready to use")
        print("  2. Start the PBX system: python main.py")
        print("  3. Or sync AD users: python scripts/sync_ad_users.py")
        print("\nNote: The .env file is automatically loaded by the system.")
    else:
        print("\nCancelled. No changes made.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except (KeyError, TypeError, ValueError) as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
