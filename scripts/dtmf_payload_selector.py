#!/usr/bin/env python3
"""
DTMF Payload Type Selector
Interactive tool to help choose the right RFC2833 payload type
"""

import sys

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Payload type information
PAYLOAD_TYPES = {
    "101": {
        "name": "RFC2833 Standard",
        "description": "Industry standard, works with most phones and providers",
        "use_when": "Default choice - start here",
        "compatibility": "Universal (99% of systems)",
        "priority": 1,
    },
    "100": {
        "name": "Cisco/Common Alternative",
        "description": "Used by Cisco systems and many SIP providers",
        "use_when": "When 101 fails, or Cisco equipment in use",
        "compatibility": "Cisco, Grandstream, some Yealink",
        "priority": 2,
    },
    "102": {
        "name": "Carrier Alternative",
        "description": "Required by some major carriers",
        "use_when": "Verizon, AT&T, or when carrier specifies",
        "compatibility": "Major carriers, some SIP trunks",
        "priority": 3,
    },
    "96": {
        "name": "Generic Fallback",
        "description": "First dynamic payload type, universal fallback",
        "use_when": "When 100/101/102 all fail",
        "compatibility": "Universal fallback",
        "priority": 4,
    },
    "121": {
        "name": "Polycom Specific",
        "description": "Sometimes needed for Polycom phones",
        "use_when": "Polycom VVX series with DTMF issues",
        "compatibility": "Polycom phones",
        "priority": 5,
    },
}


def print_header() -> None:
    """Print tool header."""
    print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{BLUE}   DTMF RFC2833 Payload Type Selector{RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════{RESET}\n")


def print_payload_info(pt_num: str, info: dict, is_recommended: bool = False) -> None:
    """Print information about a payload type."""
    marker = f"{GREEN}✓{RESET}" if is_recommended else " "
    print(f"{marker} {BOLD}Payload Type {pt_num}{RESET}: {info['name']}")
    print(f"  Description: {info['description']}")
    print(f"  Use when: {info['use_when']}")
    print(f"  Compatibility: {info['compatibility']}")
    print()


def ask_question(question: str, options: list[str]) -> int:
    """Ask a multiple-choice question."""
    print(f"{YELLOW}{question}{RESET}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")

    while True:
        try:
            choice = input(f"\nEnter choice (1-{len(options)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return choice_num - 1
        except (ValueError, KeyboardInterrupt):
            pass
        print(f"{RED}Invalid choice. Please enter a number between 1 and {len(options)}.{RESET}")


def recommend_payload_type() -> str:
    """Interactive recommendation flow."""
    print_header()

    # Question 1: Is DTMF working?
    print(f"{BOLD}Step 1: Current Status{RESET}\n")
    working = ask_question(
        "Is DTMF currently working with payload type 101?",
        ["Yes, it's working fine", "No, DTMF is not working", "I'm not sure / new setup"],
    )

    if working == 0:  # Working fine
        print(f"\n{GREEN}✓ Recommendation: Keep payload type 101 (standard){RESET}\n")
        print("Your current configuration is working correctly.")
        print("No changes needed unless you experience issues.")
        return "101"

    # Question 2: Type of equipment
    print(f"\n{BOLD}Step 2: Equipment Information{RESET}\n")
    equipment = ask_question(
        "What type of equipment are you using?",
        [
            "Cisco phones or equipment",
            "Polycom phones",
            "Yealink, Zultys, or Grandstream phones",
            "SIP trunk from major carrier (Verizon, AT&T, etc.)",
            "Other / Not sure",
        ],
    )

    if equipment == 0:  # Cisco
        print(f"\n{GREEN}✓ Recommendation: Try payload type 100 first{RESET}\n")
        print_payload_info("100", PAYLOAD_TYPES["100"], is_recommended=True)
        print("Cisco systems commonly use payload type 100.")
        print("If 100 doesn't work, try: 101 → 102 → 96")
        return "100"

    if equipment == 1:  # Polycom
        print(f"\n{GREEN}✓ Recommendation: Try payload type 121 or 100{RESET}\n")
        print_payload_info("121", PAYLOAD_TYPES["121"], is_recommended=True)
        print("Polycom phones sometimes need payload type 121.")
        print("If 121 doesn't work, try: 100 → 101 → 102")
        return "121"

    if equipment == 3:  # Carrier
        print(f"\n{GREEN}✓ Recommendation: Try payload type 102 or 100{RESET}\n")
        print_payload_info("102", PAYLOAD_TYPES["102"], is_recommended=True)
        print("Major carriers often require payload type 102 or 100.")
        print("If 102 doesn't work, try: 100 → 101 → 96")
        print(f"\n{YELLOW}TIP: Check your carrier's documentation for required payload type{RESET}")
        return "102"

    # Yealink/Zultys/Other
    print(f"\n{GREEN}✓ Recommendation: Try alternatives in this order{RESET}\n")
    print("Recommended testing order:")
    print("  1. Payload type 100 (most common alternative)")
    print("  2. Payload type 102 (carrier alternative)")
    print("  3. Payload type 96 (generic fallback)")
    print("  4. Payload type 101 (standard)")
    return "100"


def show_all_options() -> None:
    """Display all available payload types."""
    print_header()
    print(f"{BOLD}Available Payload Types{RESET}\n")

    # Sort by priority
    sorted_pts = sorted(PAYLOAD_TYPES.items(), key=lambda x: x[1]["priority"])

    for pt_num, info in sorted_pts:
        is_recommended = pt_num == "101"
        print_payload_info(pt_num, info, is_recommended)

    print(f"{YELLOW}Valid range: 96-127 (dynamic RTP payload types){RESET}")
    print("Custom values can be used if required by your provider.\n")


def show_configuration_example(payload_type: str) -> None:
    """Show how to configure the selected payload type."""
    print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}Configuration Instructions{RESET}\n")

    print("1. Edit config.yml:")
    print(f"{BOLD}   vim config.yml{RESET}\n")

    print("2. Find the DTMF configuration section and change:")
    print(f"   {YELLOW}features:")
    print("     dtmf:")
    print(f"       payload_type: {payload_type}  # Changed from 101{RESET}\n")

    print("3. Restart the PBX:")
    print(f"{BOLD}   sudo systemctl restart pbx{RESET}\n")

    print("4. Reprovision phones:")
    print("   - Reboot phones, OR")
    print("   - On phone: Menu → Settings → Auto Provision → Provision Now\n")

    print("5. Test DTMF:")
    print("   - Call voicemail: *<extension>")
    print("   - Enter PIN and verify it's recognized")
    print("   - Test auto-attendant navigation\n")

    print(f"{GREEN}✓ See DTMF_PAYLOAD_TYPE_CONFIGURATION.md for detailed guide{RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════{RESET}\n")


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print_header()
        print("Usage: python dtmf_payload_selector.py [--list]")
        print()
        print("Options:")
        print("  --list, -l    Show all available payload types")
        print("  --help, -h    Show this help message")
        print()
        print("Interactive mode: Run without arguments for guided selection")
        return

    if len(sys.argv) > 1 and sys.argv[1] in ["--list", "-l"]:
        show_all_options()
        return

    # Interactive mode
    try:
        recommended = recommend_payload_type()
        show_configuration_example(recommended)

        # Ask if user wants to see all options
        print(
            f"\n{YELLOW}Would you like to see all available payload types? (y/n):{RESET} ", end=""
        )
        if input().strip().lower() in ["y", "yes"]:
            show_all_options()

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Cancelled by user{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
