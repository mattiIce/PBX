"""Comprehensive tests for audio utilities module."""

from __future__ import annotations

import math
import struct
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.mark.unit
class TestConstants:
    """Tests for module-level constants."""

    def test_max_16bit_signed(self) -> None:
        from pbx.utils.audio import MAX_16BIT_SIGNED

        assert MAX_16BIT_SIGNED == 32767

    def test_default_amplitude(self) -> None:
        from pbx.utils.audio import DEFAULT_AMPLITUDE

        assert DEFAULT_AMPLITUDE == 0.5

    def test_wav_format_codes(self) -> None:
        from pbx.utils.audio import (
            WAV_FORMAT_ALAW,
            WAV_FORMAT_G722,
            WAV_FORMAT_PCM,
            WAV_FORMAT_ULAW,
        )

        assert WAV_FORMAT_PCM == 1
        assert WAV_FORMAT_ULAW == 7
        assert WAV_FORMAT_ALAW == 6
        assert WAV_FORMAT_G722 == 0x0067


@pytest.mark.unit
class TestPcm16ToUlaw:
    """Tests for pcm16_to_ulaw function."""

    def test_empty_input(self) -> None:
        from pbx.utils.audio import pcm16_to_ulaw

        result = pcm16_to_ulaw(b"")
        assert result == b""

    def test_single_byte_input(self) -> None:
        """Odd byte count means last byte is dropped."""
        from pbx.utils.audio import pcm16_to_ulaw

        result = pcm16_to_ulaw(b"\x00")
        assert result == b""

    def test_silence(self) -> None:
        """Zero samples should encode without error."""
        from pbx.utils.audio import pcm16_to_ulaw

        # 4 samples of silence (16-bit, 8 bytes)
        pcm_data = struct.pack("<hhhh", 0, 0, 0, 0)
        result = pcm16_to_ulaw(pcm_data)
        assert len(result) == 4

    def test_positive_sample(self) -> None:
        """Positive samples are encoded correctly."""
        from pbx.utils.audio import pcm16_to_ulaw

        pcm_data = struct.pack("<h", 16000)
        result = pcm16_to_ulaw(pcm_data)
        assert len(result) == 1
        assert isinstance(result[0], int)

    def test_negative_sample(self) -> None:
        """Negative samples include sign bit."""
        from pbx.utils.audio import pcm16_to_ulaw

        pcm_data = struct.pack("<h", -16000)
        result = pcm16_to_ulaw(pcm_data)
        assert len(result) == 1

    def test_max_positive(self) -> None:
        """Max positive value is clipped."""
        from pbx.utils.audio import pcm16_to_ulaw

        pcm_data = struct.pack("<h", 32767)
        result = pcm16_to_ulaw(pcm_data)
        assert len(result) == 1

    def test_max_negative(self) -> None:
        """Max negative value is handled."""
        from pbx.utils.audio import pcm16_to_ulaw

        pcm_data = struct.pack("<h", -32768)
        result = pcm16_to_ulaw(pcm_data)
        assert len(result) == 1

    def test_multiple_samples(self) -> None:
        """Multiple samples produce expected output length."""
        from pbx.utils.audio import pcm16_to_ulaw

        samples = [1000, -1000, 5000, -5000, 0, 32767, -32768, 100]
        pcm_data = struct.pack(f"<{len(samples)}h", *samples)
        result = pcm16_to_ulaw(pcm_data)
        assert len(result) == len(samples)

    def test_roundtrip_produces_bytes(self) -> None:
        """Generated beep tone converts to ulaw without error."""
        from pbx.utils.audio import generate_beep_tone, pcm16_to_ulaw

        pcm_data = generate_beep_tone(frequency=1000, duration_ms=100, sample_rate=8000)
        result = pcm16_to_ulaw(pcm_data)
        assert len(result) > 0


@pytest.mark.unit
class TestPcm16ToG722:
    """Tests for pcm16_to_g722 function."""

    def test_empty_input(self) -> None:
        from pbx.utils.audio import pcm16_to_g722

        result = pcm16_to_g722(b"")
        assert result == b""

    def test_single_byte_input(self) -> None:
        from pbx.utils.audio import pcm16_to_g722

        result = pcm16_to_g722(b"\x00")
        assert result == b""

    def test_odd_length_truncated(self) -> None:
        """Odd-length input is truncated to even."""
        from pbx.utils.audio import pcm16_to_g722

        # 3 bytes -> truncate to 2 bytes (1 sample)
        pcm_data = b"\x00\x00\x01"
        with patch("pbx.features.g722_codec.G722Codec") as mock_codec_cls:
            mock_codec = MagicMock()
            mock_codec.encode.return_value = b"\x42"
            mock_codec_cls.return_value = mock_codec
            _result = pcm16_to_g722(pcm_data, sample_rate=16000)

    @patch("pbx.features.g722_codec.G722Codec")
    def test_16khz_no_upsampling(self, mock_codec_cls) -> None:
        """16kHz input is not upsampled."""
        mock_codec = MagicMock()
        mock_codec.encode.return_value = b"\x42\x43"
        mock_codec_cls.return_value = mock_codec

        from pbx.utils.audio import pcm16_to_g722

        pcm_data = struct.pack("<hh", 1000, 2000)
        _result = pcm16_to_g722(pcm_data, sample_rate=16000)
        # encode is called with original data (no upsampling)
        mock_codec.encode.assert_called_once_with(pcm_data)

    @patch("pbx.features.g722_codec.G722Codec")
    def test_8khz_upsampled(self, mock_codec_cls) -> None:
        """8kHz input is upsampled to 16kHz."""
        mock_codec = MagicMock()
        mock_codec.encode.return_value = b"\x42\x43\x44\x45"
        mock_codec_cls.return_value = mock_codec

        from pbx.utils.audio import pcm16_to_g722

        # 4 samples at 8kHz -> 8 samples at 16kHz
        pcm_data = struct.pack("<hhhh", 100, 200, 300, 400)
        _result = pcm16_to_g722(pcm_data, sample_rate=8000)
        # Verify encoder was called with upsampled data (longer)
        called_data = mock_codec.encode.call_args[0][0]
        assert len(called_data) > len(pcm_data)

    @patch("pbx.features.g722_codec.G722Codec")
    def test_encoder_returns_none(self, mock_codec_cls) -> None:
        """If encoder returns None, function returns empty bytes."""
        mock_codec = MagicMock()
        mock_codec.encode.return_value = None
        mock_codec_cls.return_value = mock_codec

        from pbx.utils.audio import pcm16_to_g722

        pcm_data = struct.pack("<hh", 100, 200)
        result = pcm16_to_g722(pcm_data, sample_rate=16000)
        assert result == b""

    @patch("pbx.features.g722_codec.G722Codec")
    def test_8khz_single_sample_returns_empty(self, mock_codec_cls) -> None:
        """8kHz with zero samples after check returns empty."""
        from pbx.utils.audio import pcm16_to_g722

        # Create input with 0 samples after dividing by 2
        result = pcm16_to_g722(b"", sample_rate=8000)
        assert result == b""


@pytest.mark.unit
class TestConvertPcmWavToG722Wav:
    """Tests for convert_pcm_wav_to_g722_wav function."""

    def _build_pcm_wav(self, pcm_data: bytes, sample_rate: int = 8000) -> bytes:
        """Helper to build a minimal PCM WAV file."""
        from pbx.utils.audio import WAV_FORMAT_PCM, build_wav_header

        header = build_wav_header(
            len(pcm_data),
            sample_rate=sample_rate,
            channels=1,
            bits_per_sample=16,
            audio_format=WAV_FORMAT_PCM,
        )
        return header + pcm_data

    @patch("pbx.features.g722_codec.G722Codec")
    def test_convert_valid_wav(self, mock_codec_cls, tmp_path) -> None:
        """Convert a valid PCM WAV file."""
        mock_codec = MagicMock()
        mock_codec.encode.return_value = b"\x42" * 100
        mock_codec_cls.return_value = mock_codec

        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        # Create a valid PCM WAV
        pcm_data = struct.pack("<" + "h" * 100, *([1000] * 100))
        wav_data = self._build_pcm_wav(pcm_data)

        input_path = tmp_path / "input.wav"
        output_path = tmp_path / "output.wav"
        input_path.write_bytes(wav_data)

        result = convert_pcm_wav_to_g722_wav(str(input_path), str(output_path))
        assert result is True
        assert output_path.exists()

    @patch("pbx.features.g722_codec.G722Codec")
    def test_convert_overwrite_input(self, mock_codec_cls, tmp_path) -> None:
        """When output path is None, overwrite input."""
        mock_codec = MagicMock()
        mock_codec.encode.return_value = b"\x42" * 100
        mock_codec_cls.return_value = mock_codec

        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        pcm_data = struct.pack("<" + "h" * 100, *([1000] * 100))
        wav_data = self._build_pcm_wav(pcm_data)

        input_path = tmp_path / "input.wav"
        input_path.write_bytes(wav_data)

        result = convert_pcm_wav_to_g722_wav(str(input_path))
        assert result is True

    def test_convert_invalid_riff(self, tmp_path) -> None:
        """Non-RIFF file returns False."""
        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        input_path = tmp_path / "notawav.wav"
        input_path.write_bytes(b"NOT_RIFF" + b"\x00" * 100)

        result = convert_pcm_wav_to_g722_wav(str(input_path))
        assert result is False

    def test_convert_invalid_wave(self, tmp_path) -> None:
        """RIFF file without WAVE marker returns False."""
        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        data = b"RIFF" + struct.pack("<I", 100) + b"XXXX" + b"\x00" * 100
        input_path = tmp_path / "bad.wav"
        input_path.write_bytes(data)

        result = convert_pcm_wav_to_g722_wav(str(input_path))
        assert result is False

    def test_convert_non_pcm_format(self, tmp_path) -> None:
        """Non-PCM WAV returns False."""
        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        # Build WAV with ulaw format (7) instead of PCM (1)
        fmt_data = struct.pack("<HHIIHH", 7, 1, 8000, 8000, 1, 8)  # ulaw
        data = b"RIFF"
        chunk_content = b"WAVE"
        chunk_content += b"fmt " + struct.pack("<I", len(fmt_data)) + fmt_data
        audio = b"\x00" * 100
        chunk_content += b"data" + struct.pack("<I", len(audio)) + audio
        data += struct.pack("<I", len(chunk_content)) + chunk_content

        input_path = tmp_path / "ulaw.wav"
        input_path.write_bytes(data)

        result = convert_pcm_wav_to_g722_wav(str(input_path))
        assert result is False

    def test_convert_missing_file(self, tmp_path) -> None:
        """Missing file returns False."""
        import warnings

        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = convert_pcm_wav_to_g722_wav(str(tmp_path / "missing.wav"))
        assert result is False

    @patch("pbx.features.g722_codec.G722Codec")
    def test_convert_empty_g722_data(self, mock_codec_cls, tmp_path) -> None:
        """If G.722 encoder produces empty data, return False."""
        mock_codec = MagicMock()
        mock_codec.encode.return_value = b""
        mock_codec_cls.return_value = mock_codec

        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        pcm_data = struct.pack("<h", 0)  # minimal data
        wav_data = self._build_pcm_wav(pcm_data)

        input_path = tmp_path / "input.wav"
        input_path.write_bytes(wav_data)

        result = convert_pcm_wav_to_g722_wav(str(input_path))
        assert result is False

    def test_convert_no_audio_data(self, tmp_path) -> None:
        """WAV with no data chunk returns False."""
        from pbx.utils.audio import convert_pcm_wav_to_g722_wav

        fmt_data = struct.pack("<HHIIHH", 1, 1, 8000, 16000, 2, 16)
        data = b"RIFF"
        chunk_content = b"WAVE"
        chunk_content += b"fmt " + struct.pack("<I", len(fmt_data)) + fmt_data
        # No data chunk
        data += struct.pack("<I", len(chunk_content)) + chunk_content

        input_path = tmp_path / "nodata.wav"
        input_path.write_bytes(data)

        result = convert_pcm_wav_to_g722_wav(str(input_path))
        assert result is False


@pytest.mark.unit
class TestGenerateBeepTone:
    """Tests for generate_beep_tone function."""

    def test_default_parameters(self) -> None:
        from pbx.utils.audio import generate_beep_tone

        data = generate_beep_tone()
        # 500ms at 8000Hz = 4000 samples * 2 bytes = 8000 bytes
        expected_bytes = int(8000 * 500 / 1000) * 2
        assert len(data) == expected_bytes

    def test_custom_parameters(self) -> None:
        from pbx.utils.audio import generate_beep_tone

        data = generate_beep_tone(frequency=440, duration_ms=100, sample_rate=16000)
        expected_samples = int(16000 * 100 / 1000)
        assert len(data) == expected_samples * 2

    def test_zero_duration(self) -> None:
        from pbx.utils.audio import generate_beep_tone

        data = generate_beep_tone(duration_ms=0)
        assert len(data) == 0

    def test_output_is_valid_pcm(self) -> None:
        """Output can be parsed as 16-bit signed LE samples."""
        from pbx.utils.audio import generate_beep_tone

        data = generate_beep_tone(duration_ms=10, sample_rate=8000)
        num_samples = len(data) // 2
        for i in range(num_samples):
            sample = struct.unpack("<h", data[i * 2 : (i + 1) * 2])[0]
            assert -32768 <= sample <= 32767


@pytest.mark.unit
class TestBuildWavHeader:
    """Tests for build_wav_header function."""

    def test_pcm_header(self) -> None:
        from pbx.utils.audio import WAV_FORMAT_PCM, build_wav_header

        header = build_wav_header(1000, sample_rate=8000, channels=1, bits_per_sample=16)
        assert header[:4] == b"RIFF"
        assert header[8:12] == b"WAVE"
        assert header[12:16] == b"fmt "
        assert header[36:40] == b"data"
        # File size = 36 + data_size
        file_size = struct.unpack("<I", header[4:8])[0]
        assert file_size == 36 + 1000
        # Audio format
        audio_format = struct.unpack("<H", header[20:22])[0]
        assert audio_format == WAV_FORMAT_PCM

    def test_g722_header(self) -> None:
        from pbx.utils.audio import WAV_FORMAT_G722, build_wav_header

        header = build_wav_header(
            500,
            sample_rate=8000,
            channels=1,
            bits_per_sample=8,
            audio_format=WAV_FORMAT_G722,
        )
        audio_format = struct.unpack("<H", header[20:22])[0]
        assert audio_format == WAV_FORMAT_G722
        # G.722 byte rate = 8000
        byte_rate = struct.unpack("<I", header[28:32])[0]
        assert byte_rate == 8000

    def test_stereo_header(self) -> None:
        from pbx.utils.audio import build_wav_header

        header = build_wav_header(2000, sample_rate=44100, channels=2, bits_per_sample=16)
        channels = struct.unpack("<H", header[22:24])[0]
        assert channels == 2
        byte_rate = struct.unpack("<I", header[28:32])[0]
        assert byte_rate == 44100 * 2 * 2  # sr * channels * bytes_per_sample

    def test_header_length(self) -> None:
        from pbx.utils.audio import build_wav_header

        header = build_wav_header(100)
        assert len(header) == 44  # Standard WAV header


@pytest.mark.unit
class TestGenerateVoicemailBeep:
    """Tests for generate_voicemail_beep function."""

    def test_returns_valid_wav(self) -> None:
        from pbx.utils.audio import generate_voicemail_beep

        data = generate_voicemail_beep()
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"

    def test_correct_audio_length(self) -> None:
        from pbx.utils.audio import generate_voicemail_beep

        data = generate_voicemail_beep()
        # Header is 44 bytes
        pcm_length = len(data) - 44
        # 500ms at 8000Hz * 2 bytes = 8000 bytes
        expected = int(8000 * 500 / 1000) * 2
        assert pcm_length == expected


@pytest.mark.unit
class TestGenerateRingTone:
    """Tests for generate_ring_tone function."""

    def test_single_ring(self) -> None:
        from pbx.utils.audio import generate_ring_tone

        data = generate_ring_tone(rings=1)
        assert data[:4] == b"RIFF"
        assert len(data) > 44  # Has actual audio

    def test_multiple_rings(self) -> None:
        from pbx.utils.audio import generate_ring_tone

        data1 = generate_ring_tone(rings=1)
        data2 = generate_ring_tone(rings=2)
        assert len(data2) > len(data1)

    def test_zero_rings(self) -> None:
        from pbx.utils.audio import generate_ring_tone

        data = generate_ring_tone(rings=0)
        # Still has header but no audio data
        assert data[:4] == b"RIFF"


@pytest.mark.unit
class TestGenerateBusyTone:
    """Tests for generate_busy_tone function."""

    def test_returns_valid_wav(self) -> None:
        from pbx.utils.audio import generate_busy_tone

        data = generate_busy_tone()
        assert data[:4] == b"RIFF"

    def test_has_audio_data(self) -> None:
        from pbx.utils.audio import generate_busy_tone

        data = generate_busy_tone()
        assert len(data) > 44


@pytest.mark.unit
class TestGenerateVoicePrompt:
    """Tests for generate_voice_prompt function."""

    def test_known_prompt_type(self) -> None:
        from pbx.utils.audio import generate_voice_prompt

        data = generate_voice_prompt("leave_message")
        assert data[:4] == b"RIFF"
        assert len(data) > 44

    def test_enter_pin_prompt(self) -> None:
        from pbx.utils.audio import generate_voice_prompt

        data = generate_voice_prompt("enter_pin")
        assert data[:4] == b"RIFF"

    def test_main_menu_prompt(self) -> None:
        from pbx.utils.audio import generate_voice_prompt

        data = generate_voice_prompt("main_menu")
        assert data[:4] == b"RIFF"

    def test_unknown_prompt_type_uses_default(self) -> None:
        from pbx.utils.audio import generate_voice_prompt

        data = generate_voice_prompt("nonexistent_prompt")
        assert data[:4] == b"RIFF"
        assert len(data) > 44

    def test_silence_in_sequence(self) -> None:
        """Prompts with silence (frequency 0) generate correctly."""
        from pbx.utils.audio import generate_voice_prompt

        data = generate_voice_prompt("enter_pin")  # Has silence gaps
        assert data[:4] == b"RIFF"

    def test_all_known_prompt_types(self) -> None:
        """All known prompt types generate valid WAV data."""
        from pbx.utils.audio import generate_voice_prompt

        known_types = [
            "leave_message",
            "enter_pin",
            "main_menu",
            "message_menu",
            "no_messages",
            "goodbye",
            "invalid_option",
            "you_have_messages",
            "auto_attendant_welcome",
            "auto_attendant_menu",
            "timeout",
            "transferring",
            "invalid_pin",
            "recording_greeting",
            "greeting_saved",
            "message_deleted",
            "end_of_messages",
            "beep",
        ]
        for prompt_type in known_types:
            data = generate_voice_prompt(prompt_type)
            assert data[:4] == b"RIFF", f"Failed for prompt type: {prompt_type}"

    def test_custom_sample_rate(self) -> None:
        from pbx.utils.audio import generate_voice_prompt

        data = generate_voice_prompt("goodbye", sample_rate=16000)
        assert data[:4] == b"RIFF"
        # Check sample rate in header
        sr = struct.unpack("<I", data[24:28])[0]
        assert sr == 16000


@pytest.mark.unit
class TestLoadPromptFile:
    """Tests for load_prompt_file function."""

    def test_file_not_found(self, tmp_path) -> None:
        from pbx.utils.audio import load_prompt_file

        result = load_prompt_file("enter_pin", str(tmp_path / "nonexistent"))
        assert result is None

    def test_file_exists(self, tmp_path) -> None:
        from pbx.utils.audio import load_prompt_file

        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        wav_file = prompt_dir / "enter_pin.wav"
        wav_file.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

        result = load_prompt_file("enter_pin", str(prompt_dir))
        assert result == b"RIFF\x00\x00\x00\x00WAVE"

    def test_file_read_error(self, tmp_path) -> None:
        """OSError reading file returns None."""
        import warnings

        from pbx.utils.audio import load_prompt_file

        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        wav_file = prompt_dir / "enter_pin.wav"
        wav_file.write_bytes(b"data")

        with (
            patch.object(Path, "open", side_effect=OSError("Permission denied")),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore", UserWarning)
            result = load_prompt_file("enter_pin", str(prompt_dir))
            assert result is None


@pytest.mark.unit
class TestGetPromptAudio:
    """Tests for get_prompt_audio function."""

    def test_file_found(self, tmp_path) -> None:
        from pbx.utils.audio import get_prompt_audio

        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        wav_file = prompt_dir / "goodbye.wav"
        wav_content = b"RIFF\x00\x00\x00\x00WAVEtest"
        wav_file.write_bytes(wav_content)

        result = get_prompt_audio("goodbye", str(prompt_dir))
        assert result == wav_content

    def test_fallback_to_generated(self, tmp_path) -> None:
        """When file is not found, generates tone prompt."""
        from pbx.utils.audio import get_prompt_audio

        result = get_prompt_audio("goodbye", str(tmp_path / "nonexistent"))
        assert result[:4] == b"RIFF"
        assert len(result) > 44

    def test_custom_sample_rate_for_generated(self, tmp_path) -> None:
        from pbx.utils.audio import get_prompt_audio

        result = get_prompt_audio("goodbye", str(tmp_path / "nonexistent"), sample_rate=16000)
        sr = struct.unpack("<I", result[24:28])[0]
        assert sr == 16000
