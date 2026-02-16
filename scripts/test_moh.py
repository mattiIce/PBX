#!/usr/bin/env python3
"""
Test script to verify Music on Hold (MOH) files are properly loaded and functional.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pbx.features.music_on_hold import MusicOnHold


def test_moh_system() -> bool:
    """Test the MOH system."""
    print("=" * 70)
    print("Music on Hold (MOH) System Test")
    print("=" * 70)
    print()

    # Initialize MOH system
    print("1. Initializing MOH system...")
    moh = MusicOnHold(moh_directory="moh")
    print("   ✓ MOH system initialized")
    print()

    # Check classes loaded
    print("2. Checking loaded MOH classes...")
    classes = moh.get_classes()
    print(f"   Found {len(classes)} MOH class(es): {classes}")

    if not classes:
        print("   ✗ ERROR: No MOH classes found!")
        return False

    if "default" not in classes:
        print("   ✗ ERROR: 'default' class not found!")
        return False

    print("   ✓ Default MOH class loaded successfully")
    print()

    # Check files in default class
    print("3. Checking files in 'default' class...")
    files = moh.get_class_files("default")
    print(f"   Found {len(files)} file(s):")

    if not files:
        print("   ✗ ERROR: No MOH files found in default class!")
        return False

    for filepath in files:
        filename = Path(filepath).name
        size_kb = Path(filepath).stat().st_size / 1024
        print(f"     • {filename} ({size_kb:.1f} KB)")

        # Check if file exists
        if not Path(filepath).exists():
            print("       ✗ ERROR: File does not exist!")
            return False

        # Check if it's a WAV file
        with open(filepath, "rb") as f:
            header = f.read(12)
            if not (header[0:4] == b"RIFF" and header[8:12] == b"WAVE"):
                print("       ✗ ERROR: Not a valid WAV file!")
                return False

    print(f"   ✓ All {len(files)} MOH files are valid WAV files")
    print()

    # Test starting MOH
    print("4. Testing MOH playback simulation...")
    test_call_id = "test-call-123"

    audio_file = moh.start_moh(test_call_id)
    if not audio_file:
        print("   ✗ ERROR: Failed to start MOH!")
        return False

    print(f"   ✓ MOH started for call {test_call_id}")
    print(f"   Playing: {Path(audio_file).name}")
    print()

    # Test getting next file
    print("5. Testing file rotation...")
    next_file = moh.get_next_file(test_call_id)
    if not next_file:
        print("   ✗ ERROR: Failed to get next MOH file!")
        return False

    print(f"   ✓ Next file: {Path(next_file).name}")
    print()

    # Test stopping MOH
    print("6. Testing MOH stop...")
    moh.stop_moh(test_call_id)
    print(f"   ✓ MOH stopped for call {test_call_id}")
    print()

    # Summary
    print("=" * 70)
    print("✓ All MOH tests passed successfully!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  • MOH classes loaded: {len(classes)}")
    print(f"  • Files in default class: {len(files)}")
    print(f"  • Total audio files: {len(files)}")
    print()
    print("The Music on Hold system is ready for use!")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_moh_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
