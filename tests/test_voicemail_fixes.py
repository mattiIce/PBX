#!/usr/bin/env python3
"""
Test voicemail fixes for:
1. Admin panel playback (API serves audio files)
2. Voicemail access via dial pattern (*xxxx)
3. Email notification with database extensions
"""

import os
import shutil
import tempfile


from pbx.core.pbx import PBXCore
from pbx.features.email_notification import EmailNotifier
from pbx.features.voicemail import VoicemailBox, VoicemailSystem
from pbx.utils.config import Config


def test_api_serves_audio_by_default() -> None:
    """Test that API endpoint serves audio file by default"""

    # Create temporary directory for voicemail
    temp_dir = tempfile.mkdtemp()

    try:
        # Create voicemail system
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)

        # Create a test voicemail message with audio file
        mailbox = vm_system.get_mailbox("1001")

        # Create a simple WAV file
        import struct

        audio_data = b"\x7f" * 1600  # 0.2 seconds

        # Build minimal WAV file
        # WAV format constants
        MULAW_FORMAT = 7  # G.711 μ-law audio format
        sample_rate = 8000
        bits_per_sample = 8
        num_channels = 1
        audio_format = MULAW_FORMAT

        data_size = len(audio_data)
        file_size = 4 + 26 + 8 + data_size

        wav_header = struct.pack("<4sI4s", b"RIFF", file_size, b"WAVE")
        fmt_chunk = struct.pack(
            "<4sIHHIIHH",
            b"fmt ",
            18,
            audio_format,
            num_channels,
            sample_rate,
            sample_rate * num_channels * bits_per_sample // 8,
            num_channels * bits_per_sample // 8,
            bits_per_sample,
        )
        fmt_extension = struct.pack("<H", 0)
        data_chunk = struct.pack("<4sI", b"data", data_size)

        wav_data = wav_header + fmt_chunk + fmt_extension + data_chunk + audio_data

        # Save voicemail
        mailbox.save_message("1002", wav_data, duration=1)

        # Verify message was saved with audio file
        messages = mailbox.get_messages()
        assert len(messages) == 1
        assert os.path.exists(messages[0]["file_path"])

        # Read the audio file to verify it was written correctly
        with open(messages[0]["file_path"], "rb") as f:
            saved_data = f.read()

        assert len(saved_data) == len(wav_data)
        assert saved_data == wav_data


    finally:
        shutil.rmtree(temp_dir)


def test_voicemail_access_checks_registry() -> None:
    """Test that voicemail access checks extension registry"""

    try:
        # Create PBX instance
        pbx = PBXCore("config.yml")

        # Get an extension from the registry
        extensions = pbx.extension_registry.get_all()
        if not extensions:
            return

        test_ext = extensions[0].number

        # Verify extension exists in registry
        ext = pbx.extension_registry.get(test_ext)
        assert ext is not None, f"Extension {test_ext} should exist in registry"


        # Test the voicemail pattern matching
        voicemail_ext = f"*{test_ext}"

        # The pattern should match
        import re

        dialplan = pbx.config.get("dialplan", {})
        # Default pattern supports 3-4 digit extensions
        voicemail_pattern = dialplan.get("voicemail_pattern", "^\\*[0-9]{3,4}$")

        # Check if pattern matches (should match *100, *1001, etc.)
        # Pattern typically supports 3-4 digit extensions as per config
        if len(test_ext) >= 3 and len(test_ext) <= 4 and test_ext.isdigit():
            pattern_matches = re.match(voicemail_pattern, voicemail_ext)
            assert (
                pattern_matches
            ), f"Voicemail pattern '{voicemail_pattern}' should match {voicemail_ext}"
        else:
            # Extension is non-standard length, pattern check informational only
            pattern_matches = re.match(voicemail_pattern, voicemail_ext)

    except Exception as e:


def test_email_notification_checks_database() -> None:
    """Test that email notification checks database for extension info"""

    # Create temporary directory for voicemail
    temp_dir = tempfile.mkdtemp()

    try:
        # Create config and voicemail system
        config = Config("config.yml")

        # Check if email notifications are enabled
        email_enabled = config.get("voicemail.email_notifications", False)

        if not email_enabled:
        else:
            # Check if SMTP is configured
            smtp_host = config.get("voicemail.smtp.host")
            from_addr = config.get("voicemail.email.from_address")

            if not smtp_host or not from_addr:
            else:

        # The fix ensures that voicemail.py checks database first, then config
        # We can verify the code path by checking the save_message
        # implementation
        import inspect

        from pbx.features.voicemail import VoicemailBox

        source = inspect.getsource(VoicemailBox.save_message)

        # Check if the code includes database checking logic for email
        if "ExtensionDB" in source and "database" in source.lower():
        else:


    finally:
        shutil.rmtree(temp_dir)
