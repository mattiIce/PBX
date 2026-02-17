"""Comprehensive tests for the TTS (Text-to-Speech) utility module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest


@pytest.mark.unit
class TestTTSAvailability:
    """Tests for TTS availability checks."""

    def test_is_tts_available_when_available(self) -> None:
        """Test is_tts_available returns True when gTTS and pydub are installed."""
        with patch.dict("sys.modules", {"gtts": MagicMock(), "pydub": MagicMock()}):
            # We need to reload the module to re-evaluate the try/except
            import importlib

            import pbx.utils.tts as tts_module

            # Save original and patch
            original_available = tts_module.GTTS_AVAILABLE
            tts_module.GTTS_AVAILABLE = True
            try:
                assert tts_module.is_tts_available() is True
            finally:
                tts_module.GTTS_AVAILABLE = original_available

    def test_is_tts_available_when_not_available(self) -> None:
        """Test is_tts_available returns False when dependencies are missing."""
        import pbx.utils.tts as tts_module

        original_available = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = False
        try:
            assert tts_module.is_tts_available() is False
        finally:
            tts_module.GTTS_AVAILABLE = original_available

    def test_get_tts_requirements(self) -> None:
        """Test get_tts_requirements returns correct pip install string."""
        from pbx.utils.tts import get_tts_requirements

        result = get_tts_requirements()

        assert result == "pip install gTTS pydub"


@pytest.mark.unit
class TestGenerateMp3:
    """Tests for the _generate_mp3 function."""

    @patch("pbx.utils.tts.gTTS", create=True)
    @patch("pbx.utils.tts.tempfile.NamedTemporaryFile")
    def test_generate_mp3_success(
        self, mock_tempfile: MagicMock, mock_gtts_class: MagicMock
    ) -> None:
        """Test successful MP3 generation."""
        from pbx.utils.tts import _generate_mp3

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test.mp3"
        mock_temp.__enter__ = MagicMock(return_value=mock_temp)
        mock_temp.__exit__ = MagicMock(return_value=False)
        mock_tempfile.return_value = mock_temp

        mock_tts_instance = MagicMock()
        mock_gtts_class.return_value = mock_tts_instance

        result = _generate_mp3("Hello world", "en", "com", False)

        assert result == "/tmp/test.mp3"
        mock_gtts_class.assert_called_once_with(text="Hello world", tld="com", lang="en", slow=False)
        mock_tts_instance.save.assert_called_once_with("/tmp/test.mp3")

    @patch("pbx.utils.tts.gTTS", create=True)
    @patch("pbx.utils.tts.tempfile.NamedTemporaryFile")
    def test_generate_mp3_slow_mode(
        self, mock_tempfile: MagicMock, mock_gtts_class: MagicMock
    ) -> None:
        """Test MP3 generation with slow speech rate."""
        from pbx.utils.tts import _generate_mp3

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/slow.mp3"
        mock_temp.__enter__ = MagicMock(return_value=mock_temp)
        mock_temp.__exit__ = MagicMock(return_value=False)
        mock_tempfile.return_value = mock_temp

        mock_tts_instance = MagicMock()
        mock_gtts_class.return_value = mock_tts_instance

        _generate_mp3("Hello", "en", "co.uk", True)

        mock_gtts_class.assert_called_once_with(text="Hello", tld="co.uk", lang="en", slow=True)


@pytest.mark.unit
class TestConvertToTelephonyAudio:
    """Tests for the _convert_to_telephony_audio function."""

    @patch("pbx.utils.tts.AudioSegment", create=True)
    def test_convert_to_telephony_audio(self, mock_audio_segment: MagicMock) -> None:
        """Test conversion to telephony format (mono, 8kHz, 16-bit)."""
        from pbx.utils.tts import _convert_to_telephony_audio

        mock_audio = MagicMock()
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio_segment.from_mp3.return_value = mock_audio

        result = _convert_to_telephony_audio("/tmp/test.mp3", 8000)

        mock_audio_segment.from_mp3.assert_called_once_with("/tmp/test.mp3")
        mock_audio.set_channels.assert_called_once_with(1)
        mock_audio.set_frame_rate.assert_called_once_with(8000)
        mock_audio.set_sample_width.assert_called_once_with(2)
        assert result is mock_audio

    @patch("pbx.utils.tts.AudioSegment", create=True)
    def test_convert_to_telephony_audio_16khz(self, mock_audio_segment: MagicMock) -> None:
        """Test conversion with 16kHz sample rate (wideband)."""
        from pbx.utils.tts import _convert_to_telephony_audio

        mock_audio = MagicMock()
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio_segment.from_mp3.return_value = mock_audio

        _convert_to_telephony_audio("/tmp/test.mp3", 16000)

        mock_audio.set_frame_rate.assert_called_once_with(16000)


@pytest.mark.unit
class TestEncodeG722WithFfmpeg:
    """Tests for the _encode_g722_with_ffmpeg function."""

    @patch("pbx.utils.tts.subprocess.run")
    def test_successful_encoding(self, mock_run: MagicMock) -> None:
        """Test successful G.722 encoding with ffmpeg."""
        from pbx.utils.tts import _encode_g722_with_ffmpeg

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = _encode_g722_with_ffmpeg("/tmp/input.wav", "/tmp/output.g722", 16000)

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffmpeg" in args
        assert "/tmp/input.wav" in args
        assert "/tmp/output.g722" in args
        assert "g722" in args

    @patch("pbx.utils.tts.subprocess.run")
    def test_failed_encoding(self, mock_run: MagicMock) -> None:
        """Test failed G.722 encoding returns False."""
        from pbx.utils.tts import _encode_g722_with_ffmpeg

        mock_run.return_value = MagicMock(returncode=1, stderr="Codec not found")

        result = _encode_g722_with_ffmpeg("/tmp/input.wav", "/tmp/output.g722", 16000)

        assert result is False

    @patch("pbx.utils.tts.subprocess.run")
    def test_timeout_expired(self, mock_run: MagicMock) -> None:
        """Test timeout during encoding returns False."""
        from pbx.utils.tts import _encode_g722_with_ffmpeg

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=30)

        result = _encode_g722_with_ffmpeg("/tmp/input.wav", "/tmp/output.g722", 16000)

        assert result is False

    @patch("pbx.utils.tts.subprocess.run")
    def test_ffmpeg_not_found(self, mock_run: MagicMock) -> None:
        """Test FileNotFoundError when ffmpeg is not installed."""
        from pbx.utils.tts import _encode_g722_with_ffmpeg

        mock_run.side_effect = FileNotFoundError("ffmpeg not found")

        result = _encode_g722_with_ffmpeg("/tmp/input.wav", "/tmp/output.g722", 16000)

        assert result is False

    @patch("pbx.utils.tts.subprocess.run")
    def test_os_error(self, mock_run: MagicMock) -> None:
        """Test OSError during encoding returns False."""
        from pbx.utils.tts import _encode_g722_with_ffmpeg

        mock_run.side_effect = OSError("Permission denied")

        result = _encode_g722_with_ffmpeg("/tmp/input.wav", "/tmp/output.g722", 16000)

        assert result is False

    @patch("pbx.utils.tts.subprocess.run")
    def test_subprocess_error(self, mock_run: MagicMock) -> None:
        """Test SubprocessError during encoding returns False."""
        from pbx.utils.tts import _encode_g722_with_ffmpeg

        mock_run.side_effect = subprocess.SubprocessError("Subprocess failed")

        result = _encode_g722_with_ffmpeg("/tmp/input.wav", "/tmp/output.g722", 16000)

        assert result is False


@pytest.mark.unit
class TestExportAudio:
    """Tests for the _export_audio function."""

    @patch("pbx.utils.tts._encode_g722_with_ffmpeg")
    @patch("pbx.utils.tts.tempfile.NamedTemporaryFile")
    def test_export_with_g722_success(
        self, mock_tempfile: MagicMock, mock_encode: MagicMock
    ) -> None:
        """Test exporting audio with successful G.722 conversion."""
        from pbx.utils.tts import _export_audio

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp.wav"
        mock_temp.__enter__ = MagicMock(return_value=mock_temp)
        mock_temp.__exit__ = MagicMock(return_value=False)
        mock_tempfile.return_value = mock_temp

        mock_encode.return_value = True
        mock_audio = MagicMock()

        result = _export_audio(mock_audio, "/output/file.g722", convert_to_g722=True, sample_rate=16000)

        assert result == "/tmp/temp.wav"
        mock_audio.export.assert_called_once_with("/tmp/temp.wav", format="wav")
        mock_encode.assert_called_once_with("/tmp/temp.wav", "/output/file.g722", 16000)

    @patch("pbx.utils.tts._encode_g722_with_ffmpeg")
    @patch("pbx.utils.tts.tempfile.NamedTemporaryFile")
    def test_export_with_g722_fallback(
        self, mock_tempfile: MagicMock, mock_encode: MagicMock
    ) -> None:
        """Test exporting audio with G.722 failure falls back to PCM WAV."""
        from pbx.utils.tts import _export_audio

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp.wav"
        mock_temp.__enter__ = MagicMock(return_value=mock_temp)
        mock_temp.__exit__ = MagicMock(return_value=False)
        mock_tempfile.return_value = mock_temp

        mock_encode.return_value = False
        mock_audio = MagicMock()

        result = _export_audio(mock_audio, "/output/file.wav", convert_to_g722=True, sample_rate=16000)

        assert result == "/tmp/temp.wav"
        # Should have called export twice: once for temp WAV, once for fallback
        assert mock_audio.export.call_count == 2
        mock_audio.export.assert_any_call("/tmp/temp.wav", format="wav")
        mock_audio.export.assert_any_call("/output/file.wav", format="wav")

    def test_export_without_g722(self) -> None:
        """Test exporting audio as PCM WAV directly (no G.722)."""
        from pbx.utils.tts import _export_audio

        mock_audio = MagicMock()

        result = _export_audio(mock_audio, "/output/file.wav", convert_to_g722=False, sample_rate=8000)

        assert result is None
        mock_audio.export.assert_called_once_with("/output/file.wav", format="wav")


@pytest.mark.unit
class TestTextToWavTelephony:
    """Tests for the text_to_wav_telephony function."""

    @patch("pbx.utils.tts._export_audio")
    @patch("pbx.utils.tts._convert_to_telephony_audio")
    @patch("pbx.utils.tts._generate_mp3")
    @patch("pbx.utils.tts.Path")
    def test_successful_conversion(
        self,
        mock_path_cls: MagicMock,
        mock_gen_mp3: MagicMock,
        mock_convert: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """Test successful text-to-WAV conversion."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_gen_mp3.return_value = "/tmp/test.mp3"
            mock_convert.return_value = MagicMock()
            mock_export.return_value = None

            # Mock Path().exists() to return False for cleanup
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_cls.return_value = mock_path_instance

            result = tts_module.text_to_wav_telephony("Hello", "/output/hello.wav")

            assert result is True
            mock_gen_mp3.assert_called_once_with("Hello", "en", "com", False)
            mock_convert.assert_called_once_with("/tmp/test.mp3", 8000)
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts._export_audio")
    @patch("pbx.utils.tts._convert_to_telephony_audio")
    @patch("pbx.utils.tts._generate_mp3")
    @patch("pbx.utils.tts.Path")
    def test_custom_parameters(
        self,
        mock_path_cls: MagicMock,
        mock_gen_mp3: MagicMock,
        mock_convert: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """Test conversion with custom parameters."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_gen_mp3.return_value = "/tmp/test.mp3"
            mock_convert.return_value = MagicMock()
            mock_export.return_value = "/tmp/temp.wav"

            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_cls.return_value = mock_path_instance

            result = tts_module.text_to_wav_telephony(
                "Hello",
                "/output/hello.wav",
                language="fr",
                tld="co.uk",
                slow=True,
                sample_rate=16000,
                convert_to_g722=True,
            )

            assert result is True
            mock_gen_mp3.assert_called_once_with("Hello", "fr", "co.uk", True)
            mock_convert.assert_called_once_with("/tmp/test.mp3", 16000)
        finally:
            tts_module.GTTS_AVAILABLE = original

    def test_raises_import_error_when_unavailable(self) -> None:
        """Test ImportError raised when gTTS is not available."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = False
        tts_module.GTTS_IMPORT_ERROR = "No module named 'gtts'"
        try:
            with pytest.raises(ImportError, match="TTS dependencies not available"):
                tts_module.text_to_wav_telephony("Hello", "/output/hello.wav")
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts._generate_mp3")
    @patch("pbx.utils.tts.Path")
    def test_cleanup_on_exception(
        self, mock_path_cls: MagicMock, mock_gen_mp3: MagicMock
    ) -> None:
        """Test that temporary files are cleaned up on exception."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_gen_mp3.return_value = "/tmp/test.mp3"

            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_cls.return_value = mock_path_instance

            with patch("pbx.utils.tts._convert_to_telephony_audio", side_effect=RuntimeError("fail")):
                with pytest.raises(RuntimeError, match="fail"):
                    tts_module.text_to_wav_telephony("Hello", "/output/hello.wav")

            # Verify unlink was called for cleanup
            mock_path_instance.unlink.assert_called()
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts._export_audio")
    @patch("pbx.utils.tts._convert_to_telephony_audio")
    @patch("pbx.utils.tts._generate_mp3")
    @patch("pbx.utils.tts.Path")
    def test_cleanup_when_temp_files_do_not_exist(
        self,
        mock_path_cls: MagicMock,
        mock_gen_mp3: MagicMock,
        mock_convert: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """Test cleanup skips unlink when temp files do not exist."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_gen_mp3.return_value = "/tmp/test.mp3"
            mock_convert.return_value = MagicMock()
            mock_export.return_value = None

            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_cls.return_value = mock_path_instance

            tts_module.text_to_wav_telephony("Hello", "/output/hello.wav")

            # unlink should not be called since files don't exist
            mock_path_instance.unlink.assert_not_called()
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts._export_audio")
    @patch("pbx.utils.tts._convert_to_telephony_audio")
    @patch("pbx.utils.tts._generate_mp3")
    @patch("pbx.utils.tts.Path")
    def test_with_path_object_output(
        self,
        mock_path_cls: MagicMock,
        mock_gen_mp3: MagicMock,
        mock_convert: MagicMock,
        mock_export: MagicMock,
    ) -> None:
        """Test that output_file can be a Path object."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_gen_mp3.return_value = "/tmp/test.mp3"
            mock_audio = MagicMock()
            mock_convert.return_value = mock_audio
            mock_export.return_value = None

            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_cls.return_value = mock_path_instance

            # Pass Path object instead of string
            output = Path("/output/hello.wav")
            result = tts_module.text_to_wav_telephony("Hello", output)

            assert result is True
        finally:
            tts_module.GTTS_AVAILABLE = original


@pytest.mark.unit
class TestGeneratePrompts:
    """Tests for the generate_prompts function."""

    @patch("pbx.utils.tts.text_to_wav_telephony")
    @patch("pbx.utils.tts.Path")
    def test_generate_prompts_success(
        self, mock_path_cls: MagicMock, mock_tts: MagicMock
    ) -> None:
        """Test generating multiple prompts successfully."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_tts.return_value = True

            mock_output_dir = MagicMock()
            mock_output_dir.exists.return_value = True

            mock_output_file = MagicMock()
            mock_stat = MagicMock()
            mock_stat.st_size = 16000
            mock_output_file.stat.return_value = mock_stat

            def path_side_effect(arg):
                if arg == "/output":
                    return mock_output_dir
                return mock_output_file

            mock_path_cls.side_effect = path_side_effect

            prompts = {
                "greeting": "Welcome to the PBX",
                "goodbye": "Goodbye, have a nice day",
            }

            success, total = tts_module.generate_prompts(prompts, "/output")

            assert success == 2
            assert total == 2
            assert mock_tts.call_count == 2
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts.text_to_wav_telephony")
    @patch("pbx.utils.tts.Path")
    def test_generate_prompts_with_company_name(
        self, mock_path_cls: MagicMock, mock_tts: MagicMock
    ) -> None:
        """Test company name substitution in prompts."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_tts.return_value = True

            mock_output_dir = MagicMock()
            mock_output_dir.exists.return_value = True

            mock_output_file = MagicMock()
            mock_stat = MagicMock()
            mock_stat.st_size = 16000
            mock_output_file.stat.return_value = mock_stat

            def path_side_effect(arg):
                if arg == "/output":
                    return mock_output_dir
                return mock_output_file

            mock_path_cls.side_effect = path_side_effect

            prompts = {"greeting": "Welcome to {company_name}"}

            tts_module.generate_prompts(prompts, "/output", company_name="Acme Corp")

            # Verify the text was substituted
            call_args = mock_tts.call_args_list[0]
            assert "Acme Corp" in call_args[0][0]  # First positional arg
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts.text_to_wav_telephony")
    @patch("pbx.utils.tts.Path")
    def test_generate_prompts_creates_directory(
        self, mock_path_cls: MagicMock, mock_tts: MagicMock
    ) -> None:
        """Test that output directory is created if it does not exist."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_tts.return_value = True

            mock_output_dir = MagicMock()
            mock_output_dir.exists.return_value = False

            mock_output_file = MagicMock()
            mock_stat = MagicMock()
            mock_stat.st_size = 8000
            mock_output_file.stat.return_value = mock_stat

            def path_side_effect(arg):
                if arg == "/output/new":
                    return mock_output_dir
                return mock_output_file

            mock_path_cls.side_effect = path_side_effect

            prompts = {"test": "Hello"}
            tts_module.generate_prompts(prompts, "/output/new")

            mock_output_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts.text_to_wav_telephony")
    @patch("pbx.utils.tts.Path")
    def test_generate_prompts_handles_failure(
        self, mock_path_cls: MagicMock, mock_tts: MagicMock
    ) -> None:
        """Test that failures for individual prompts are counted."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            # First succeeds, second raises OSError
            mock_tts.side_effect = [True, OSError("Disk full")]

            mock_output_dir = MagicMock()
            mock_output_dir.exists.return_value = True

            mock_output_file = MagicMock()
            mock_stat = MagicMock()
            mock_stat.st_size = 8000
            mock_output_file.stat.return_value = mock_stat

            def path_side_effect(arg):
                if arg == "/output":
                    return mock_output_dir
                return mock_output_file

            mock_path_cls.side_effect = path_side_effect

            prompts = {"good": "Hello", "bad": "World"}

            success, total = tts_module.generate_prompts(prompts, "/output")

            assert success == 1
            assert total == 2
        finally:
            tts_module.GTTS_AVAILABLE = original

    def test_generate_prompts_raises_import_error(self) -> None:
        """Test ImportError raised when gTTS is not available."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = False
        tts_module.GTTS_IMPORT_ERROR = "No module named 'gtts'"
        try:
            with pytest.raises(ImportError, match="TTS dependencies not available"):
                tts_module.generate_prompts({"test": "Hello"}, "/output")
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts.text_to_wav_telephony")
    @patch("pbx.utils.tts.Path")
    def test_generate_prompts_wav_extension(
        self, mock_path_cls: MagicMock, mock_tts: MagicMock
    ) -> None:
        """Test that .wav extension is appended if not present."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_tts.return_value = True

            mock_output_dir = MagicMock()
            mock_output_dir.exists.return_value = True
            mock_output_dir.__truediv__ = MagicMock(return_value=MagicMock())

            mock_output_file = MagicMock()
            mock_stat = MagicMock()
            mock_stat.st_size = 8000
            mock_output_file.stat.return_value = mock_stat

            def path_side_effect(arg):
                if arg == "/output":
                    return mock_output_dir
                return mock_output_file

            mock_path_cls.side_effect = path_side_effect

            prompts = {"greeting.wav": "Already has extension", "farewell": "No extension"}

            tts_module.generate_prompts(prompts, "/output")

            # Both should succeed
            assert mock_tts.call_count == 2
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts.text_to_wav_telephony")
    @patch("pbx.utils.tts.Path")
    def test_generate_prompts_custom_sample_rate(
        self, mock_path_cls: MagicMock, mock_tts: MagicMock
    ) -> None:
        """Test generating prompts with custom sample rate."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_tts.return_value = True

            mock_output_dir = MagicMock()
            mock_output_dir.exists.return_value = True

            mock_output_file = MagicMock()
            mock_stat = MagicMock()
            mock_stat.st_size = 32000
            mock_output_file.stat.return_value = mock_stat

            def path_side_effect(arg):
                if arg == "/output":
                    return mock_output_dir
                return mock_output_file

            mock_path_cls.side_effect = path_side_effect

            prompts = {"test": "Hello"}
            tts_module.generate_prompts(prompts, "/output", sample_rate=16000)

            mock_tts.assert_called_once()
            _, kwargs = mock_tts.call_args
            assert kwargs["sample_rate"] == 16000
        finally:
            tts_module.GTTS_AVAILABLE = original

    @patch("pbx.utils.tts.text_to_wav_telephony")
    @patch("pbx.utils.tts.Path")
    def test_generate_prompts_no_company_name_placeholder(
        self, mock_path_cls: MagicMock, mock_tts: MagicMock
    ) -> None:
        """Test that company_name is not substituted if placeholder is absent."""
        import pbx.utils.tts as tts_module

        original = tts_module.GTTS_AVAILABLE
        tts_module.GTTS_AVAILABLE = True
        try:
            mock_tts.return_value = True

            mock_output_dir = MagicMock()
            mock_output_dir.exists.return_value = True

            mock_output_file = MagicMock()
            mock_stat = MagicMock()
            mock_stat.st_size = 8000
            mock_output_file.stat.return_value = mock_stat

            def path_side_effect(arg):
                if arg == "/output":
                    return mock_output_dir
                return mock_output_file

            mock_path_cls.side_effect = path_side_effect

            prompts = {"test": "No placeholder here"}
            tts_module.generate_prompts(prompts, "/output", company_name="Acme")

            call_args = mock_tts.call_args_list[0]
            assert call_args[0][0] == "No placeholder here"
        finally:
            tts_module.GTTS_AVAILABLE = original
