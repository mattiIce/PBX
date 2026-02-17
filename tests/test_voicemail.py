"""Unit tests for pbx.features.voicemail — VoicemailBox and VoicemailSystem."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("pbx.features.voicemail.get_vm_ivr_logger", return_value=MagicMock())
@patch("pbx.features.voicemail.get_logger", return_value=MagicMock())
class TestVoicemailBox:
    """Tests for VoicemailBox."""

    def test_voicemail_box_init(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """VoicemailBox creates storage dir and initialises attributes."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)

        assert box.extension_number == "1001"
        assert box.messages == []
        assert box.pin is None
        assert (tmp_path / "1001").is_dir()

    def test_save_message(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """save_message creates a .wav file and appends a message dict."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)
        audio = b"\x00" * 100
        msg_id = box.save_message("5551234", audio, duration=5.0)

        assert msg_id.startswith("5551234_")
        assert len(box.messages) == 1

        msg = box.messages[0]
        assert msg["id"] == msg_id
        assert msg["caller_id"] == "5551234"
        assert msg["listened"] is False
        assert msg["duration"] == 5.0
        assert Path(msg["file_path"]).exists()
        assert Path(msg["file_path"]).read_bytes() == audio

    def test_get_messages_filters(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """get_messages filters by unread_only."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)
        box.messages = [
            {"id": "m1", "listened": False},
            {"id": "m2", "listened": False},
            {"id": "m3", "listened": True},
        ]

        assert len(box.get_messages()) == 3
        assert len(box.get_messages(unread_only=True)) == 2

    def test_mark_listened(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """mark_listened sets listened=True on the matching message."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)
        msg_id = box.save_message("5551234", b"\x00" * 50)
        box.mark_listened(msg_id)

        assert box.messages[0]["listened"] is True

    def test_delete_message(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """delete_message removes file from disk and entry from list."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)
        msg_id = box.save_message("5551234", b"\x00" * 50)
        file_path = box.messages[0]["file_path"]

        assert Path(file_path).exists()
        assert box.delete_message(msg_id) is True
        assert not Path(file_path).exists()
        assert len(box.messages) == 0

        # Deleting nonexistent returns False
        assert box.delete_message("nonexistent") is False

    def test_set_pin_validation(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """set_pin accepts valid 4-digit PINs and rejects invalid ones."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)

        assert box.set_pin("1234") is True
        assert box.pin == "1234"

        assert box.set_pin("") is False
        assert box.set_pin("12") is False
        assert box.set_pin("abcd") is False
        assert box.set_pin(None) is False

    def test_verify_pin(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """verify_pin checks against the stored plaintext PIN."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)
        box.pin = "5678"

        assert box.verify_pin("5678") is True
        assert box.verify_pin("0000") is False

    def test_greeting_save_delete(self, _mock_logger, _mock_ivr_logger, tmp_path):
        """save_greeting writes a file; delete_greeting removes it."""
        from pbx.features.voicemail import VoicemailBox

        box = VoicemailBox("1001", storage_path=str(tmp_path), database=None, config=None)

        riff_data = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100
        assert box.save_greeting(riff_data) is True
        assert box.has_custom_greeting() is True

        assert box.delete_greeting() is True
        assert box.has_custom_greeting() is False
