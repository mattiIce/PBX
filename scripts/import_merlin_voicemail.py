#!/usr/bin/env python3
"""
Import Voicemail Data from AT&T Merlin Legend System

This script imports voicemail messages, PINs, and greetings from an AT&T Merlin Legend
phone system into the PBX. It supports multiple import formats to accommodate different
export methods.

Supported Import Formats:
1. CSV metadata + WAV audio files
2. JSON metadata + WAV audio files
3. Directory structure with WAV files (filename-based metadata)

Usage:
    # Import from CSV + WAV files
    python scripts/import_merlin_voicemail.py --csv voicemail_data.csv --audio-dir /path/to/wav/files

    # Import from JSON + WAV files
    python scripts/import_merlin_voicemail.py --json voicemail_data.json --audio-dir /path/to/wav/files

    # Import from directory structure
    python scripts/import_merlin_voicemail.py --audio-dir /path/to/wav/files --parse-filenames

    # Dry run to preview import
    python scripts/import_merlin_voicemail.py --csv voicemail_data.csv --audio-dir /path/to/wav/files --dry-run

    # Import voicemail PINs only
    python scripts/import_merlin_voicemail.py --pins pins.csv
"""

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.features.voicemail import VoicemailSystem
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend
from pbx.utils.logger import get_logger


def parse_csv_metadata(csv_path):
    """
    Parse voicemail metadata from CSV file

    Expected CSV format:
        extension,caller_id,timestamp,audio_file,duration,listened,voicemail_pin

    Example:
        1001,5551234567,2024-01-15 14:30:00,msg001.wav,45,false,1234
        1002,5559876543,2024-01-15 15:00:00,msg002.wav,30,true,5678

    Args:
        csv_path: Path to CSV file

    Returns:
        list: List of voicemail metadata dictionaries
    """
    messages = []
    pins = {}

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract voicemail PIN if present
            if row.get("voicemail_pin"):
                pins[row["extension"]] = row["voicemail_pin"]

            # Parse timestamp
            timestamp_str = row.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace(" ", "T"))
            except (ValueError, AttributeError):
                try:
                    # Try alternative formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y%m%d_%H%M%S"]:
                        try:
                            timestamp = datetime.strptime(timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        timestamp = datetime.now(UTC)
                except (ValueError, TypeError):
                    timestamp = datetime.now(UTC)

            # Parse listened status
            listened = row.get("listened", "false").lower() in ("true", "1", "yes", "y")

            # Parse duration
            try:
                duration = int(row.get("duration", 0))
            except (ValueError, TypeError):
                duration = None

            message = {
                "extension": row["extension"],
                "caller_id": row["caller_id"],
                "timestamp": timestamp,
                "audio_file": row["audio_file"],
                "duration": duration,
                "listened": listened,
            }
            messages.append(message)

    return messages, pins


def parse_json_metadata(json_path):
    """
    Parse voicemail metadata from JSON file

    Expected JSON format:
    {
        "voicemails": [
            {
                "extension": "1001",
                "caller_id": "5551234567",
                "timestamp": "2024-01-15T14:30:00",
                "audio_file": "msg001.wav",
                "duration": 45,
                "listened": false
            }
        ],
        "pins": {
            "1001": "1234",
            "1002": "5678"
        }
    }

    Args:
        json_path: Path to JSON file

    Returns:
        tuple: (list of messages, dict of pins)
    """
    with open(json_path) as f:
        data = json.load(f)

    messages = []
    for msg in data.get("voicemails", []):
        # Parse timestamp
        timestamp_str = msg.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError, TypeError):
            timestamp = datetime.now(UTC)

        message = {
            "extension": msg["extension"],
            "caller_id": msg["caller_id"],
            "timestamp": timestamp,
            "audio_file": msg["audio_file"],
            "duration": msg.get("duration"),
            "listened": msg.get("listened", False),
        }
        messages.append(message)

    pins = data.get("pins", {})

    return messages, pins


def parse_filename_metadata(audio_dir):
    """
    Parse voicemail metadata from WAV filenames in directory structure

    Expected directory structure:
        /audio-dir/
            1001/
                5551234567_20240115_143000.wav
                5559876543_20240115_150000.wav
            1002/
                5551112222_20240115_160000.wav

    Filename format: {caller_id}_{YYYYMMDD}_{HHMMSS}.wav

    Args:
        audio_dir: Path to audio directory

    Returns:
        list: List of voicemail metadata dictionaries
    """
    messages = []
    audio_path = Path(audio_dir)

    # Find all extension directories
    for ext_dir in audio_path.iterdir():
        if not ext_dir.is_dir():
            continue

        extension = ext_dir.name

        # Find all WAV files in extension directory
        for wav_file in ext_dir.glob("*.wav"):
            # Parse filename: {caller_id}_{date}_{time}.wav
            filename = wav_file.stem
            parts = filename.split("_")

            if len(parts) >= 3:
                caller_id = parts[0]
                date_str = parts[1]
                time_str = parts[2]

                try:
                    timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                except (ValueError, TypeError):
                    timestamp = datetime.fromtimestamp(wav_file.stat().st_mtime, tz=UTC)

                message = {
                    "extension": extension,
                    "caller_id": caller_id,
                    "timestamp": timestamp,
                    "audio_file": str(wav_file),
                    "duration": None,
                    "listened": False,
                }
                messages.append(message)

    return messages, {}


def parse_pins_csv(csv_path):
    """
    Parse voicemail PINs from CSV file

    Expected format:
        extension,pin
        1001,1234
        1002,5678

    Args:
        csv_path: Path to CSV file

    Returns:
        dict: Extension to PIN mapping
    """
    pins = {}

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            extension = row["extension"]
            pin = row["pin"]
            if pin and len(pin) == 4 and pin.isdigit():
                pins[extension] = pin

    return pins


def import_voicemail_messages(messages, audio_dir, config, database, dry_run=False):
    """
    Import voicemail messages into the PBX system

    Args:
        messages: List of message metadata dictionaries
        audio_dir: Directory containing audio files
        config: Config object
        database: DatabaseBackend object
        dry_run: If True, don't actually import

    Returns:
        tuple: (imported_count, skipped_count, error_count)
    """
    logger = get_logger()
    voicemail_system = VoicemailSystem(config=config, database=database)

    imported = 0
    skipped = 0
    errors = 0

    for msg in messages:
        extension = msg["extension"]
        caller_id = msg["caller_id"]
        timestamp = msg["timestamp"]
        audio_file = msg["audio_file"]
        duration = msg["duration"]
        listened = msg["listened"]

        print(f"\n→ Message for extension {extension}")
        print(f"  From: {caller_id}")
        print(f"  Date: {timestamp}")
        print(f"  Audio: {audio_file}")
        print(f"  Duration: {duration}s" if duration else "  Duration: unknown")
        print(f"  Status: {'listened' if listened else 'new'}")

        if dry_run:
            print("  [DRY RUN] Would import this message")
            imported += 1
            continue

        # Find audio file
        audio_path = None
        if Path(audio_file).is_absolute():
            audio_path = audio_file
        elif audio_dir:
            # Try various locations
            candidates = [
                Path(audio_dir) / audio_file,
                Path(audio_dir) / extension / audio_file,
                Path(audio_dir) / extension / Path(audio_file).name,
            ]
            for candidate in candidates:
                if Path(candidate).exists():
                    audio_path = candidate
                    break

        if not audio_path or not Path(audio_path).exists():
            print(f"  ✗ Audio file not found: {audio_file}")
            errors += 1
            continue

        # Read audio data
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"  ✗ Error reading audio file: {e}")
            errors += 1
            continue

        # Get or create mailbox
        mailbox = voicemail_system.get_mailbox(extension)

        # Generate message ID from timestamp and caller
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        message_id = f"{caller_id}_{timestamp_str}"

        # Check if message already exists
        existing_messages = mailbox.get_messages()
        if any(m["id"] == message_id for m in existing_messages):
            print("  ⚠ Message already exists, skipping")
            skipped += 1
            continue

        # Save message
        try:
            saved_id = mailbox.save_message(caller_id, audio_data, duration)

            # Update listened status if needed
            if listened:
                mailbox.mark_listened(saved_id)

            print(f"  ✓ Imported successfully (ID: {saved_id})")
            imported += 1
        except (OSError, ValueError, RuntimeError) as e:
            print(f"  ✗ Import failed: {e}")
            logger.error(f"Error importing voicemail: {e}", exc_info=True)
            errors += 1

    return imported, skipped, errors


def import_voicemail_pins(pins, config, database, dry_run=False):
    """
    Import voicemail PINs

    Args:
        pins: Dictionary mapping extension to PIN
        config: Config object
        database: DatabaseBackend object
        dry_run: If True, don't actually import

    Returns:
        tuple: (imported_count, skipped_count, error_count)
    """
    logger = get_logger()
    voicemail_system = VoicemailSystem(config=config, database=database)

    imported = 0
    skipped = 0
    errors = 0

    for extension, pin in pins.items():
        print(f"\n→ PIN for extension {extension}")
        print(f"  PIN: {pin}")

        if dry_run:
            print("  [DRY RUN] Would set this PIN")
            imported += 1
            continue

        # Get or create mailbox
        mailbox = voicemail_system.get_mailbox(extension)

        # Set PIN
        try:
            if mailbox.set_pin(pin):
                print("  ✓ PIN set successfully")
                imported += 1
            else:
                print("  ✗ Invalid PIN format (must be 4 digits)")
                errors += 1
        except (ValueError, TypeError, RuntimeError) as e:
            print(f"  ✗ Failed to set PIN: {e}")
            logger.error(f"Error setting PIN: {e}", exc_info=True)
            errors += 1

    return imported, skipped, errors


def import_greetings(greetings_dir, config, database, dry_run=False):
    """
    Import custom voicemail greetings

    Expected structure:
        /greetings-dir/
            1001_greeting.wav
            1002_greeting.wav

    Args:
        greetings_dir: Directory containing greeting files
        config: Config object
        database: DatabaseBackend object
        dry_run: If True, don't actually import

    Returns:
        tuple: (imported_count, error_count)
    """
    logger = get_logger()
    voicemail_system = VoicemailSystem(config=config, database=database)

    imported = 0
    errors = 0

    greetings_path = Path(greetings_dir)

    for greeting_file in greetings_path.glob("*_greeting.wav"):
        # Extract extension from filename
        extension = greeting_file.stem.replace("_greeting", "")

        print(f"\n→ Greeting for extension {extension}")
        print(f"  File: {greeting_file.name}")

        if dry_run:
            print("  [DRY RUN] Would import this greeting")
            imported += 1
            continue

        # Read audio data
        try:
            with open(greeting_file, "rb") as f:
                audio_data = f.read()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"  ✗ Error reading greeting file: {e}")
            errors += 1
            continue

        # Get or create mailbox
        mailbox = voicemail_system.get_mailbox(extension)

        # Save greeting
        try:
            if mailbox.save_greeting(audio_data):
                print("  ✓ Greeting imported successfully")
                imported += 1
            else:
                print("  ✗ Failed to save greeting")
                errors += 1
        except (OSError, ValueError, RuntimeError) as e:
            print(f"  ✗ Import failed: {e}")
            logger.error(f"Error importing greeting: {e}", exc_info=True)
            errors += 1

    return imported, errors


def main():
    parser = argparse.ArgumentParser(
        description="Import voicemail data from AT&T Merlin Legend system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input format options
    parser.add_argument("--csv", help="CSV file with voicemail metadata")
    parser.add_argument("--json", help="JSON file with voicemail metadata")
    parser.add_argument("--audio-dir", help="Directory containing audio files")
    parser.add_argument(
        "--parse-filenames",
        action="store_true",
        help="Parse metadata from filenames (use with --audio-dir)",
    )

    # PIN import
    parser.add_argument("--pins", help="CSV file with voicemail PINs")

    # Greeting import
    parser.add_argument("--greetings-dir", help="Directory containing greeting files")

    # Options
    parser.add_argument(
        "--config", default="config.yml", help="Path to config file (default: config.yml)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview import without making changes"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("AT&T Merlin Legend Voicemail Import")
    print("=" * 70)
    print()

    if args.dry_run:
        print("⚠ DRY RUN MODE: No changes will be made")
        print()

    # Load configuration
    try:
        config = Config(args.config)
    except FileNotFoundError:
        print(f"✗ Configuration file '{args.config}' not found")
        sys.exit(1)

    # Initialize database
    print("Connecting to database...")
    db_config = {
        "database.type": config.get("database.type", "sqlite"),
        "database.host": config.get("database.host", "localhost"),
        "database.port": config.get("database.port", 5432),
        "database.name": config.get("database.name", "pbx_system"),
        "database.user": config.get("database.user", "pbx_user"),
        "database.password": config.get("database.password", ""),
        "database.path": config.get("database.path", "pbx.db"),
    }

    database = DatabaseBackend(db_config)

    if not database.connect():
        print("⚠ Database connection failed - will import to file system only")
        print()
    else:
        print("✓ Connected to database")
        # Ensure tables exist
        database.create_tables()
        print()

    # Parse metadata
    messages = []
    pins = {}

    if args.csv:
        print(f"Reading CSV metadata from: {args.csv}")
        csv_messages, csv_pins = parse_csv_metadata(args.csv)
        messages.extend(csv_messages)
        pins.update(csv_pins)
        print(f"  Found {len(csv_messages)} voicemail messages")
        print(f"  Found {len(csv_pins)} voicemail PINs")
        print()

    if args.json:
        print(f"Reading JSON metadata from: {args.json}")
        json_messages, json_pins = parse_json_metadata(args.json)
        messages.extend(json_messages)
        pins.update(json_pins)
        print(f"  Found {len(json_messages)} voicemail messages")
        print(f"  Found {len(json_pins)} voicemail PINs")
        print()

    if args.parse_filenames and args.audio_dir:
        print(f"Parsing filenames from: {args.audio_dir}")
        filename_messages, _ = parse_filename_metadata(args.audio_dir)
        messages.extend(filename_messages)
        print(f"  Found {len(filename_messages)} voicemail messages")
        print()

    if args.pins:
        print(f"Reading PINs from: {args.pins}")
        pins_from_file = parse_pins_csv(args.pins)
        pins.update(pins_from_file)
        print(f"  Found {len(pins_from_file)} voicemail PINs")
        print()

    # Import data
    total_imported = 0
    total_skipped = 0
    total_errors = 0

    if messages:
        print("=" * 70)
        print(f"Importing {len(messages)} voicemail messages...")
        print("=" * 70)

        imported, skipped, errors = import_voicemail_messages(
            messages, args.audio_dir, config, database, args.dry_run
        )
        total_imported += imported
        total_skipped += skipped
        total_errors += errors

        print()
        print(f"Messages: {imported} imported, {skipped} skipped, {errors} errors")

    if pins:
        print()
        print("=" * 70)
        print(f"Importing {len(pins)} voicemail PINs...")
        print("=" * 70)

        imported, skipped, errors = import_voicemail_pins(pins, config, database, args.dry_run)
        total_imported += imported
        total_skipped += skipped
        total_errors += errors

        print()
        print(f"PINs: {imported} imported, {skipped} skipped, {errors} errors")

    if args.greetings_dir:
        print()
        print("=" * 70)
        print("Importing custom greetings...")
        print("=" * 70)

        imported, errors = import_greetings(args.greetings_dir, config, database, args.dry_run)
        total_imported += imported
        total_errors += errors

        print()
        print(f"Greetings: {imported} imported, {errors} errors")

    # Summary
    print()
    print("=" * 70)
    print("Import Summary")
    print("=" * 70)
    print(f"Total imported: {total_imported}")
    print(f"Total skipped:  {total_skipped}")
    print(f"Total errors:   {total_errors}")
    print()

    if args.dry_run:
        print("This was a dry run. Run without --dry-run to perform import.")
    elif total_errors > 0:
        print("⚠ Import completed with errors")
        sys.exit(1)
    elif total_imported > 0:
        print("✓ Import completed successfully!")
    else:
        print("No data imported")

    if database.enabled:
        database.disconnect()


if __name__ == "__main__":
    main()
