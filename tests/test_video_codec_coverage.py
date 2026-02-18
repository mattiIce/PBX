"""
Comprehensive tests for H.264/H.265 Video Codec Support (video_codec.py).

Covers all public classes, enums, methods, and code paths including
initialization, encoding, decoding, codec negotiation, bandwidth calculation,
encoder/decoder creation, statistics, and the global singleton accessor.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pbx.features.video_codec import VideoCodecManager


@pytest.mark.unit
class TestVideoCodecEnum:
    """Test VideoCodec enumeration"""

    def test_h264_value(self) -> None:
        from pbx.features.video_codec import VideoCodec

        assert VideoCodec.H264.value == "H.264"

    def test_h265_value(self) -> None:
        from pbx.features.video_codec import VideoCodec

        assert VideoCodec.H265.value == "H.265"

    def test_vp8_value(self) -> None:
        from pbx.features.video_codec import VideoCodec

        assert VideoCodec.VP8.value == "VP8"

    def test_vp9_value(self) -> None:
        from pbx.features.video_codec import VideoCodec

        assert VideoCodec.VP9.value == "VP9"

    def test_av1_value(self) -> None:
        from pbx.features.video_codec import VideoCodec

        assert VideoCodec.AV1.value == "AV1"

    def test_all_members_present(self) -> None:
        from pbx.features.video_codec import VideoCodec

        members = [m.name for m in VideoCodec]
        assert set(members) == {"H264", "H265", "VP8", "VP9", "AV1"}

    def test_create_from_value(self) -> None:
        from pbx.features.video_codec import VideoCodec

        assert VideoCodec("H.264") == VideoCodec.H264
        assert VideoCodec("H.265") == VideoCodec.H265
        assert VideoCodec("VP8") == VideoCodec.VP8

    def test_create_from_invalid_value_raises(self) -> None:
        from pbx.features.video_codec import VideoCodec

        with pytest.raises(ValueError):
            VideoCodec("INVALID")


@pytest.mark.unit
class TestVideoProfileEnum:
    """Test VideoProfile enumeration"""

    def test_baseline_value(self) -> None:
        from pbx.features.video_codec import VideoProfile

        assert VideoProfile.BASELINE.value == "baseline"

    def test_main_value(self) -> None:
        from pbx.features.video_codec import VideoProfile

        assert VideoProfile.MAIN.value == "main"

    def test_high_value(self) -> None:
        from pbx.features.video_codec import VideoProfile

        assert VideoProfile.HIGH.value == "high"

    def test_high10_value(self) -> None:
        from pbx.features.video_codec import VideoProfile

        assert VideoProfile.HIGH10.value == "high10"

    def test_all_members_present(self) -> None:
        from pbx.features.video_codec import VideoProfile

        members = [m.name for m in VideoProfile]
        assert set(members) == {"BASELINE", "MAIN", "HIGH", "HIGH10"}

    def test_create_from_value(self) -> None:
        from pbx.features.video_codec import VideoProfile

        assert VideoProfile("baseline") == VideoProfile.BASELINE
        assert VideoProfile("main") == VideoProfile.MAIN
        assert VideoProfile("high") == VideoProfile.HIGH
        assert VideoProfile("high10") == VideoProfile.HIGH10


@pytest.mark.unit
class TestVideoResolutionEnum:
    """Test VideoResolution enumeration"""

    def test_qvga_value(self) -> None:
        from pbx.features.video_codec import VideoResolution

        assert VideoResolution.QVGA.value == (320, 240)

    def test_vga_value(self) -> None:
        from pbx.features.video_codec import VideoResolution

        assert VideoResolution.VGA.value == (640, 480)

    def test_hd_value(self) -> None:
        from pbx.features.video_codec import VideoResolution

        assert VideoResolution.HD.value == (1280, 720)

    def test_full_hd_value(self) -> None:
        from pbx.features.video_codec import VideoResolution

        assert VideoResolution.FULL_HD.value == (1920, 1080)

    def test_qhd_value(self) -> None:
        from pbx.features.video_codec import VideoResolution

        assert VideoResolution.QHD.value == (2560, 1440)

    def test_uhd_4k_value(self) -> None:
        from pbx.features.video_codec import VideoResolution

        assert VideoResolution.UHD_4K.value == (3840, 2160)

    def test_all_members_present(self) -> None:
        from pbx.features.video_codec import VideoResolution

        members = [m.name for m in VideoResolution]
        assert set(members) == {"QVGA", "VGA", "HD", "FULL_HD", "QHD", "UHD_4K"}

    def test_resolution_tuples_have_two_elements(self) -> None:
        from pbx.features.video_codec import VideoResolution

        for res in VideoResolution:
            assert len(res.value) == 2
            assert isinstance(res.value[0], int)
            assert isinstance(res.value[1], int)


@pytest.mark.unit
class TestVideoCodecManagerInit:
    """Test VideoCodecManager initialization with various configurations"""

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_no_config(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with no config (None)"""
        from pbx.features.video_codec import VideoCodec, VideoCodecManager, VideoProfile

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        manager = VideoCodecManager(None)

        assert manager.config == {}
        assert manager.enabled is False
        assert manager.default_codec == VideoCodec.H264
        assert manager.default_profile == VideoProfile.MAIN
        assert manager.default_resolution == "HD"
        assert manager.default_framerate == 30
        assert manager.default_bitrate == 2000
        assert manager.frames_encoded == 0
        assert manager.frames_decoded == 0
        assert manager.total_bandwidth_used == 0

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_empty_config(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with empty dict config"""
        from pbx.features.video_codec import VideoCodecManager

        mock_check_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        manager = VideoCodecManager({})

        assert manager.config == {}
        assert manager.enabled is False

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_enabled(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with feature enabled"""
        from pbx.features.video_codec import VideoCodecManager

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264", "H.265"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"enabled": True}}}
        manager = VideoCodecManager(config)

        assert manager.enabled is True

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_disabled(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with feature explicitly disabled"""
        from pbx.features.video_codec import VideoCodecManager

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"enabled": False}}}
        manager = VideoCodecManager(config)

        assert manager.enabled is False

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_custom_codec_h265(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with H.265 as default codec"""
        from pbx.features.video_codec import VideoCodec, VideoCodecManager

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264", "H.265"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"default_codec": "H.265"}}}
        manager = VideoCodecManager(config)

        assert manager.default_codec == VideoCodec.H265

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_custom_profile_high(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with high profile"""
        from pbx.features.video_codec import VideoCodecManager, VideoProfile

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"default_profile": "high"}}}
        manager = VideoCodecManager(config)

        assert manager.default_profile == VideoProfile.HIGH

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_custom_resolution(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with custom default resolution"""
        from pbx.features.video_codec import VideoCodecManager

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"default_resolution": "FULL_HD"}}}
        manager = VideoCodecManager(config)

        assert manager.default_resolution == "FULL_HD"

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_custom_framerate(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with custom framerate"""
        from pbx.features.video_codec import VideoCodecManager

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"default_framerate": 60}}}
        manager = VideoCodecManager(config)

        assert manager.default_framerate == 60

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_custom_bitrate(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with custom bitrate"""
        from pbx.features.video_codec import VideoCodecManager

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"default_bitrate": 5000}}}
        manager = VideoCodecManager(config)

        assert manager.default_bitrate == 5000

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_full_custom_config(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test initialization with all custom config values"""
        from pbx.features.video_codec import VideoCodec, VideoCodecManager, VideoProfile

        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264", "H.265", "VP8", "VP9", "AV1"]
        mock_logger.return_value = MagicMock()

        config = {
            "features": {
                "video_codec": {
                    "enabled": True,
                    "default_codec": "VP9",
                    "default_profile": "baseline",
                    "default_resolution": "QHD",
                    "default_framerate": 24,
                    "default_bitrate": 8000,
                }
            }
        }
        manager = VideoCodecManager(config)

        assert manager.enabled is True
        assert manager.default_codec == VideoCodec.VP9
        assert manager.default_profile == VideoProfile.BASELINE
        assert manager.default_resolution == "QHD"
        assert manager.default_framerate == 24
        assert manager.default_bitrate == 8000

    @patch("pbx.features.video_codec.PYAV_AVAILABLE", False)
    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_logs_ffmpeg_not_available(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test that init logs instructions when FFmpeg is not available"""
        from pbx.features.video_codec import VideoCodecManager

        logger_instance = MagicMock()
        mock_logger.return_value = logger_instance
        mock_check_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        VideoCodecManager(None)

        # Should log installation instructions for both FFmpeg and PyAV
        info_calls = [str(c) for c in logger_instance.info.call_args_list]
        info_text = " ".join(info_calls)
        assert "FFmpeg" in info_text or "ffmpeg" in info_text
        assert "PyAV" in info_text or "pip install av" in info_text

    @patch("pbx.features.video_codec.PYAV_AVAILABLE", True)
    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_init_ffmpeg_available_pyav_available(
        self, mock_check_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test init when both FFmpeg and PyAV are available (no install instructions)"""
        from pbx.features.video_codec import VideoCodecManager

        logger_instance = MagicMock()
        mock_logger.return_value = logger_instance
        mock_check_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264", "H.265"]

        VideoCodecManager(None)

        # Should not log FFmpeg or PyAV install instructions
        info_calls = [str(c) for c in logger_instance.info.call_args_list]
        info_text = " ".join(info_calls)
        assert "Install FFmpeg" not in info_text
        assert "Install PyAV" not in info_text


@pytest.mark.unit
class TestCheckFfmpeg:
    """Test the _check_ffmpeg method"""

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.subprocess.run")
    def test_ffmpeg_available(
        self, mock_run: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test when FFmpeg is available"""
        from pbx.features.video_codec import VideoCodecManager

        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=0)

        manager = VideoCodecManager(None)

        assert manager.ffmpeg_available is True

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.subprocess.run")
    def test_ffmpeg_not_found(
        self, mock_run: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test when FFmpeg binary is not found"""
        from pbx.features.video_codec import VideoCodecManager

        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()
        mock_run.side_effect = FileNotFoundError

        manager = VideoCodecManager(None)

        assert manager.ffmpeg_available is False

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.subprocess.run")
    def test_ffmpeg_timeout(
        self, mock_run: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test when FFmpeg check times out"""
        import subprocess

        from pbx.features.video_codec import VideoCodecManager

        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=5)

        manager = VideoCodecManager(None)

        assert manager.ffmpeg_available is False

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.subprocess.run")
    def test_ffmpeg_nonzero_return(
        self, mock_run: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test when FFmpeg returns non-zero exit code"""
        from pbx.features.video_codec import VideoCodecManager

        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=1)

        manager = VideoCodecManager(None)

        assert manager.ffmpeg_available is False


@pytest.mark.unit
class TestDetectCodecsViaFfmpeg:
    """Test the _detect_codecs_via_ffmpeg method"""

    def _create_manager(
        self, mock_logger: MagicMock, ffmpeg_available: bool = True
    ) -> VideoCodecManager:
        """Helper to create a manager for testing internal methods"""
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=ffmpeg_available),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        # Reset ffmpeg_available to desired state for the test
        manager.ffmpeg_available = ffmpeg_available
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_no_ffmpeg_returns_empty(self, mock_logger: MagicMock) -> None:
        """Test returns empty list when FFmpeg not available"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=False)

        result = manager._detect_codecs_via_ffmpeg()

        assert result == []

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_h264_libx264(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects H.264 via libx264"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... libx264 ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "H.264" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_h264_via_h264_keyword(
        self, mock_logger: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test detects H.264 via h264 keyword in lowercase output"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... H264 encoder ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "H.264" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_h265_libx265(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects H.265 via libx265"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... libx265 ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "H.265" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_h265_via_hevc_keyword(
        self, mock_logger: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test detects H.265 via hevc keyword in lowercase output"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... HEVC encoder ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "H.265" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_vp8(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects VP8 via libvpx"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... libvpx ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "VP8" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_vp9(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects VP9 via libvpx-vp9"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... libvpx-vp9 ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "VP9" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_vp9_via_keyword(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects VP9 via vp9 keyword in lowercase output"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... VP9 encoder ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "VP9" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_av1(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects AV1 via libaom"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... libaom-av1 ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "AV1" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_av1_via_keyword(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects AV1 via av1 keyword in lowercase output"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... AV1 encoder ")

        result = manager._detect_codecs_via_ffmpeg()

        assert "AV1" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detects_all_codecs(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test detects all codecs when all present in output"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        ffmpeg_output = (
            " V..... libx264    H.264 encoder\n"
            " V..... libx265    H.265/HEVC encoder\n"
            " V..... libvpx     VP8 encoder\n"
            " V..... libvpx-vp9 VP9 encoder\n"
            " V..... libaom-av1 AV1 encoder\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=ffmpeg_output)

        result = manager._detect_codecs_via_ffmpeg()

        assert "H.264" in result
        assert "H.265" in result
        assert "VP8" in result
        assert "VP9" in result
        assert "AV1" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_ffmpeg_encoders_nonzero_return(
        self, mock_logger: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test when ffmpeg -encoders returns non-zero"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = manager._detect_codecs_via_ffmpeg()

        assert result == []

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_ffmpeg_encoders_timeout(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test when ffmpeg -encoders times out"""
        import subprocess

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=5)

        result = manager._detect_codecs_via_ffmpeg()

        assert result == []

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_ffmpeg_encoders_general_exception(
        self, mock_logger: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test when ffmpeg -encoders raises an unexpected exception"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.side_effect = RuntimeError("unexpected")

        result = manager._detect_codecs_via_ffmpeg()

        assert result == []

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_no_codecs_in_output(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test when FFmpeg output contains no known codecs"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, ffmpeg_available=True)

        mock_run.return_value = MagicMock(returncode=0, stdout=" V..... libxyz unknown_codec ")

        result = manager._detect_codecs_via_ffmpeg()

        assert result == []


@pytest.mark.unit
class TestDetectOpenH264:
    """Test the _detect_openh264 method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=False),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_openh264_detected_adds_h264(self, mock_logger: MagicMock) -> None:
        """Test that detecting OpenH264 adds H.264 to available list"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        with patch("ctypes.CDLL") as mock_cdll:
            mock_cdll.return_value = MagicMock()
            result = manager._detect_openh264([])

        assert "H.264" in result

    @patch("pbx.features.video_codec.get_logger")
    def test_openh264_not_detected(self, mock_logger: MagicMock) -> None:
        """Test when no OpenH264 library is found"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        with patch("ctypes.CDLL", side_effect=OSError):
            result = manager._detect_openh264([])

        assert "H.264" not in result

    @patch("pbx.features.video_codec.get_logger")
    def test_openh264_already_in_list(self, mock_logger: MagicMock) -> None:
        """Test that H.264 is not duplicated if already present"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        with patch("ctypes.CDLL") as mock_cdll:
            mock_cdll.return_value = MagicMock()
            result = manager._detect_openh264(["H.264"])

        assert result.count("H.264") == 1

    @patch("pbx.features.video_codec.get_logger")
    def test_openh264_detection_general_exception(self, mock_logger: MagicMock) -> None:
        """Test when openh264 detection raises a general exception"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        with patch("ctypes.CDLL", side_effect=RuntimeError("import fail")):
            result = manager._detect_openh264([])

        # Should handle gracefully; H.264 should not be added
        assert result == []


@pytest.mark.unit
class TestDetectX265:
    """Test the _detect_x265 method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=False),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_x265_detected(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test when x265 is found"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        mock_run.return_value = MagicMock(returncode=0)

        result = manager._detect_x265([])

        assert "H.265" in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_x265_not_found(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test when x265 binary is not found"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        mock_run.side_effect = FileNotFoundError

        result = manager._detect_x265([])

        assert "H.265" not in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_x265_timeout(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test when x265 check times out"""
        import subprocess

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="x265", timeout=5)

        result = manager._detect_x265([])

        assert "H.265" not in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_x265_nonzero_return(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test when x265 returns non-zero exit code"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        mock_run.return_value = MagicMock(returncode=1)

        result = manager._detect_x265([])

        assert "H.265" not in result

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_x265_already_in_list(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test that H.265 is not duplicated if already in list"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        mock_run.return_value = MagicMock(returncode=0)

        result = manager._detect_x265(["H.265"])

        assert result.count("H.265") == 1

    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_x265_general_exception(self, mock_logger: MagicMock, mock_run: MagicMock) -> None:
        """Test when x265 detection raises an unexpected exception"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        mock_run.side_effect = RuntimeError("unexpected")

        result = manager._detect_x265([])

        assert "H.265" not in result


@pytest.mark.unit
class TestDetectAvailableCodecs:
    """Test the _detect_available_codecs method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=False),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_combines_all_detection_methods(self, mock_logger: MagicMock) -> None:
        """Test that all detection methods are called and combined"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        with (
            patch.object(manager, "_detect_codecs_via_ffmpeg", return_value=["H.264"]),
            patch.object(manager, "_detect_openh264", return_value=["H.264"]) as mock_openh264,
            patch.object(manager, "_detect_x265", return_value=["H.264", "H.265"]) as mock_x265,
        ):
            result = manager._detect_available_codecs()

        mock_openh264.assert_called_once_with(["H.264"])
        mock_x265.assert_called_once()
        assert "H.264" in result
        assert "H.265" in result

    @patch("pbx.features.video_codec.get_logger")
    def test_fallback_empty_when_no_codecs(self, mock_logger: MagicMock) -> None:
        """Test that an empty list is returned when no codecs are found"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        with (
            patch.object(manager, "_detect_codecs_via_ffmpeg", return_value=[]),
            patch.object(manager, "_detect_openh264", return_value=[]),
            patch.object(manager, "_detect_x265", return_value=[]),
            patch("pbx.features.video_codec.PYAV_AVAILABLE", False),
        ):
            result = manager._detect_available_codecs()

        assert result == []

    @patch("pbx.features.video_codec.get_logger")
    def test_no_fallback_when_codecs_found(self, mock_logger: MagicMock) -> None:
        """Test no fallback placeholder when at least one codec detected"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        with (
            patch.object(manager, "_detect_codecs_via_ffmpeg", return_value=["VP8"]),
            patch.object(manager, "_detect_openh264", return_value=["VP8"]),
            patch.object(manager, "_detect_x265", return_value=["VP8"]),
        ):
            result = manager._detect_available_codecs()

        # VP8 should be present, H.264 placeholder should NOT be added
        assert "VP8" in result
        # The fallback only triggers when the list is empty
        assert len(result) > 0


@pytest.mark.unit
class TestEncodeFrame:
    """Test the encode_frame method"""

    def _create_manager(self, mock_logger: MagicMock, enabled: bool = True) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        config = {"features": {"video_codec": {"enabled": enabled}}}
        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(config)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_when_disabled_returns_none(self, mock_logger: MagicMock) -> None:
        """Test that encoding returns None when manager is disabled"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=False)

        result = manager.encode_frame(b"\x00" * 100)

        assert result is None

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_returns_frame_data(self, mock_logger: MagicMock) -> None:
        """Test encoding returns frame data (placeholder behavior)"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        frame = b"\x00\x01\x02" * 100
        result = manager.encode_frame(frame)

        assert result == frame

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_increments_counter(self, mock_logger: MagicMock) -> None:
        """Test that encoding increments the frames_encoded counter"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        assert manager.frames_encoded == 0

        manager.encode_frame(b"\x00" * 50)
        assert manager.frames_encoded == 1

        manager.encode_frame(b"\x00" * 50)
        assert manager.frames_encoded == 2

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_tracks_bandwidth(self, mock_logger: MagicMock) -> None:
        """Test that encoding tracks total bandwidth used"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        assert manager.total_bandwidth_used == 0

        frame1 = b"\x00" * 100
        frame2 = b"\x00" * 200
        manager.encode_frame(frame1)
        manager.encode_frame(frame2)

        assert manager.total_bandwidth_used == 300

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_with_custom_codec(self, mock_logger: MagicMock) -> None:
        """Test encoding with a specific codec name"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        frame = b"\x00" * 50
        result = manager.encode_frame(frame, codec="H.265")

        assert result == frame
        assert manager.frames_encoded == 1

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_with_custom_resolution(self, mock_logger: MagicMock) -> None:
        """Test encoding with a specific resolution"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        frame = b"\x00" * 50
        result = manager.encode_frame(frame, resolution=(1920, 1080))

        assert result == frame

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_with_custom_bitrate(self, mock_logger: MagicMock) -> None:
        """Test encoding with a specific bitrate"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        frame = b"\x00" * 50
        result = manager.encode_frame(frame, bitrate=5000)

        assert result == frame

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_with_all_params(self, mock_logger: MagicMock) -> None:
        """Test encoding with all parameters specified"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        frame = b"\xab\xcd" * 100
        result = manager.encode_frame(frame, codec="VP8", resolution=(640, 480), bitrate=1000)

        assert result == frame
        assert manager.frames_encoded == 1
        assert manager.total_bandwidth_used == 200

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_uses_default_codec_when_none(self, mock_logger: MagicMock) -> None:
        """Test that encode uses default_codec when codec param is None"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        _logger_instance = manager.logger
        frame = b"\x00" * 10
        manager.encode_frame(frame, codec=None)

        # Verify it was called; the log message should contain the default codec
        assert manager.frames_encoded == 1

    @patch("pbx.features.video_codec.get_logger")
    def test_encode_uses_default_bitrate_when_none(self, mock_logger: MagicMock) -> None:
        """Test that encode uses default_bitrate when bitrate param is None"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        frame = b"\x00" * 10
        manager.encode_frame(frame, bitrate=None)

        assert manager.frames_encoded == 1


@pytest.mark.unit
class TestDecodeFrame:
    """Test the decode_frame method"""

    def _create_manager(self, mock_logger: MagicMock, enabled: bool = True) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        config = {"features": {"video_codec": {"enabled": enabled}}}
        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(config)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_decode_when_disabled_returns_none(self, mock_logger: MagicMock) -> None:
        """Test that decoding returns None when manager is disabled"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=False)

        result = manager.decode_frame(b"\x00" * 100)

        assert result is None

    @patch("pbx.features.video_codec.get_logger")
    def test_decode_returns_data(self, mock_logger: MagicMock) -> None:
        """Test decoding returns encoded data (placeholder behavior)"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        data = b"\xde\xad\xbe\xef" * 50
        result = manager.decode_frame(data)

        assert result == data

    @patch("pbx.features.video_codec.get_logger")
    def test_decode_increments_counter(self, mock_logger: MagicMock) -> None:
        """Test that decoding increments the frames_decoded counter"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        assert manager.frames_decoded == 0

        manager.decode_frame(b"\x00" * 50)
        assert manager.frames_decoded == 1

        manager.decode_frame(b"\x00" * 50)
        assert manager.frames_decoded == 2

    @patch("pbx.features.video_codec.get_logger")
    def test_decode_with_custom_codec(self, mock_logger: MagicMock) -> None:
        """Test decoding with a specific codec"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        data = b"\x00" * 50
        result = manager.decode_frame(data, codec="H.265")

        assert result == data
        assert manager.frames_decoded == 1

    @patch("pbx.features.video_codec.get_logger")
    def test_decode_uses_default_codec_when_none(self, mock_logger: MagicMock) -> None:
        """Test that decode uses default_codec when codec is None"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        data = b"\x00" * 10
        result = manager.decode_frame(data, codec=None)

        assert result == data
        assert manager.frames_decoded == 1


@pytest.mark.unit
class TestCreateEncoder:
    """Test the create_encoder method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder_h264_basic(self, mock_logger: MagicMock) -> None:
        """Test creating a basic H.264 encoder"""
        from pbx.features.video_codec import VideoCodec, VideoProfile, VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.create_encoder(
            codec=VideoCodec.H264,
            profile=VideoProfile.MAIN,
            resolution=VideoResolution.HD,
            framerate=30,
            bitrate=2000,
        )

        assert result["codec"] == "H.264"
        assert result["profile"] == "main"
        assert result["resolution"] == (1280, 720)
        assert result["framerate"] == 30
        assert result["bitrate"] == 2000
        assert result["gop_size"] == 60  # framerate * 2
        assert result["b_frames"] == 2
        assert "created_at" in result

    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder_h265_high_profile(self, mock_logger: MagicMock) -> None:
        """Test creating an H.265 encoder with high profile"""
        from pbx.features.video_codec import VideoCodec, VideoProfile, VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.create_encoder(
            codec=VideoCodec.H265,
            profile=VideoProfile.HIGH,
            resolution=VideoResolution.FULL_HD,
            framerate=60,
            bitrate=5000,
        )

        assert result["codec"] == "H.265"
        assert result["profile"] == "high"
        assert result["resolution"] == (1920, 1080)
        assert result["framerate"] == 60
        assert result["bitrate"] == 5000
        assert result["gop_size"] == 120

    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder_vp9_4k(self, mock_logger: MagicMock) -> None:
        """Test creating a VP9 encoder at 4K resolution"""
        from pbx.features.video_codec import VideoCodec, VideoProfile, VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.create_encoder(
            codec=VideoCodec.VP9,
            profile=VideoProfile.BASELINE,
            resolution=VideoResolution.UHD_4K,
            framerate=24,
            bitrate=15000,
        )

        assert result["codec"] == "VP9"
        assert result["resolution"] == (3840, 2160)
        assert result["framerate"] == 24
        assert result["gop_size"] == 48

    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder_created_at_is_utc(self, mock_logger: MagicMock) -> None:
        """Test that encoder config has a UTC timestamp"""
        from pbx.features.video_codec import VideoCodec, VideoProfile, VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.create_encoder(
            codec=VideoCodec.H264,
            profile=VideoProfile.MAIN,
            resolution=VideoResolution.VGA,
            framerate=15,
            bitrate=500,
        )

        # Verify the timestamp is valid ISO format with timezone info
        ts = result["created_at"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None

    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder_all_codecs(self, mock_logger: MagicMock) -> None:
        """Test creating encoders for every codec type"""
        from pbx.features.video_codec import VideoCodec, VideoProfile, VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        for codec in VideoCodec:
            result = manager.create_encoder(
                codec=codec,
                profile=VideoProfile.MAIN,
                resolution=VideoResolution.HD,
                framerate=30,
                bitrate=2000,
            )
            assert result["codec"] == codec.value

    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder_all_profiles(self, mock_logger: MagicMock) -> None:
        """Test creating encoders for every profile"""
        from pbx.features.video_codec import VideoCodec, VideoProfile, VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        for profile in VideoProfile:
            result = manager.create_encoder(
                codec=VideoCodec.H264,
                profile=profile,
                resolution=VideoResolution.HD,
                framerate=30,
                bitrate=2000,
            )
            assert result["profile"] == profile.value

    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder_all_resolutions(self, mock_logger: MagicMock) -> None:
        """Test creating encoders for every resolution"""
        from pbx.features.video_codec import VideoCodec, VideoProfile, VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        for resolution in VideoResolution:
            result = manager.create_encoder(
                codec=VideoCodec.H264,
                profile=VideoProfile.MAIN,
                resolution=resolution,
                framerate=30,
                bitrate=2000,
            )
            assert result["resolution"] == resolution.value


@pytest.mark.unit
class TestCreateDecoder:
    """Test the create_decoder method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_create_decoder_h264(self, mock_logger: MagicMock) -> None:
        """Test creating an H.264 decoder"""
        from pbx.features.video_codec import VideoCodec

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.create_decoder(VideoCodec.H264)

        assert result["codec"] == "H.264"
        assert result["threads"] == 4
        assert "created_at" in result

    @patch("pbx.features.video_codec.get_logger")
    def test_create_decoder_h265(self, mock_logger: MagicMock) -> None:
        """Test creating an H.265 decoder"""
        from pbx.features.video_codec import VideoCodec

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.create_decoder(VideoCodec.H265)

        assert result["codec"] == "H.265"

    @patch("pbx.features.video_codec.get_logger")
    def test_create_decoder_all_codecs(self, mock_logger: MagicMock) -> None:
        """Test creating decoders for all codec types"""
        from pbx.features.video_codec import VideoCodec

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        for codec in VideoCodec:
            result = manager.create_decoder(codec)
            assert result["codec"] == codec.value
            assert result["threads"] == 4

    @patch("pbx.features.video_codec.get_logger")
    def test_create_decoder_created_at_is_utc(self, mock_logger: MagicMock) -> None:
        """Test that decoder config has a UTC timestamp"""
        from pbx.features.video_codec import VideoCodec

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.create_decoder(VideoCodec.VP8)

        ts = result["created_at"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None


@pytest.mark.unit
class TestNegotiateCodec:
    """Test the negotiate_codec method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_h265_preferred(self, mock_logger: MagicMock) -> None:
        """Test that H.265 is preferred when both sides support it"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec(
            ["H.264", "H.265", "VP8"],
            ["H.265", "VP8"],
        )

        assert result == "H.265"

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_h264_fallback(self, mock_logger: MagicMock) -> None:
        """Test fallback to H.264 when H.265 is not common"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec(
            ["H.264", "VP8"],
            ["H.264", "VP9"],
        )

        assert result == "H.264"

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_vp9(self, mock_logger: MagicMock) -> None:
        """Test negotiation selects VP9 when it is the best common codec"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec(
            ["VP8", "VP9"],
            ["VP9", "AV1"],
        )

        assert result == "VP9"

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_vp8(self, mock_logger: MagicMock) -> None:
        """Test negotiation selects VP8 when it is the only common codec"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec(
            ["VP8"],
            ["VP8"],
        )

        assert result == "VP8"

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_no_common(self, mock_logger: MagicMock) -> None:
        """Test negotiation returns None when no common codec exists"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec(
            ["H.264"],
            ["VP9"],
        )

        assert result is None

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_empty_local(self, mock_logger: MagicMock) -> None:
        """Test negotiation returns None with empty local codec list"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec([], ["H.264"])

        assert result is None

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_empty_remote(self, mock_logger: MagicMock) -> None:
        """Test negotiation returns None with empty remote codec list"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec(["H.264"], [])

        assert result is None

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_both_empty(self, mock_logger: MagicMock) -> None:
        """Test negotiation returns None with both lists empty"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec([], [])

        assert result is None

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_preference_order(self, mock_logger: MagicMock) -> None:
        """Test that the preference order is H.265 > H.264 > VP9 > VP8"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        all_codecs = ["VP8", "VP9", "H.264", "H.265"]

        result = manager.negotiate_codec(all_codecs, all_codecs)

        assert result == "H.265"

    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_av1_not_in_preference(self, mock_logger: MagicMock) -> None:
        """Test that AV1 is not in the preference list and returns None"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.negotiate_codec(["AV1"], ["AV1"])

        # AV1 is not in codec_preference list
        assert result is None


@pytest.mark.unit
class TestGetSupportedResolutions:
    """Test the get_supported_resolutions method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_returns_all_resolutions(self, mock_logger: MagicMock) -> None:
        """Test that all common resolutions are returned"""
        from pbx.features.video_codec import VideoResolution

        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.get_supported_resolutions("H.264")

        assert len(result) == 6
        assert VideoResolution.QVGA.value in result
        assert VideoResolution.VGA.value in result
        assert VideoResolution.HD.value in result
        assert VideoResolution.FULL_HD.value in result
        assert VideoResolution.QHD.value in result
        assert VideoResolution.UHD_4K.value in result

    @patch("pbx.features.video_codec.get_logger")
    def test_returns_same_for_any_codec(self, mock_logger: MagicMock) -> None:
        """Test that the same resolutions are returned for all codecs"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        h264_res = manager.get_supported_resolutions("H.264")
        h265_res = manager.get_supported_resolutions("H.265")
        vp8_res = manager.get_supported_resolutions("VP8")
        vp9_res = manager.get_supported_resolutions("VP9")
        av1_res = manager.get_supported_resolutions("AV1")

        assert h264_res == h265_res == vp8_res == vp9_res == av1_res


@pytest.mark.unit
class TestCalculateBandwidth:
    """Test the calculate_bandwidth method"""

    def _create_manager(self, mock_logger: MagicMock) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(VideoCodecManager, "_detect_available_codecs", return_value=["H.264"]),
        ):
            manager = VideoCodecManager(None)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_hd_medium_30fps(self, mock_logger: MagicMock) -> None:
        """Test bandwidth calculation for HD at medium quality 30fps"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        # HD = 1280x720 = 921600 pixels
        # base_rate = 921600 / 1000000 * 1000 = 921.6
        # bitrate = 921.6 * 1.0 * (30/30) = 921.6 -> int = 921
        result = manager.calculate_bandwidth((1280, 720), 30, "medium")

        expected = int((1280 * 720 / 1000000) * 1000 * 1.0 * (30 / 30))
        assert result == expected

    @patch("pbx.features.video_codec.get_logger")
    def test_hd_low_30fps(self, mock_logger: MagicMock) -> None:
        """Test bandwidth calculation for HD at low quality"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.calculate_bandwidth((1280, 720), 30, "low")

        expected = int((1280 * 720 / 1000000) * 1000 * 0.5 * (30 / 30))
        assert result == expected

    @patch("pbx.features.video_codec.get_logger")
    def test_hd_high_30fps(self, mock_logger: MagicMock) -> None:
        """Test bandwidth calculation for HD at high quality"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.calculate_bandwidth((1280, 720), 30, "high")

        expected = int((1280 * 720 / 1000000) * 1000 * 2.0 * (30 / 30))
        assert result == expected

    @patch("pbx.features.video_codec.get_logger")
    def test_4k_medium_60fps(self, mock_logger: MagicMock) -> None:
        """Test bandwidth calculation for 4K at 60fps"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.calculate_bandwidth((3840, 2160), 60, "medium")

        expected = int((3840 * 2160 / 1000000) * 1000 * 1.0 * (60 / 30))
        assert result == expected

    @patch("pbx.features.video_codec.get_logger")
    def test_qvga_low_15fps(self, mock_logger: MagicMock) -> None:
        """Test bandwidth calculation for QVGA at low quality 15fps"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.calculate_bandwidth((320, 240), 15, "low")

        expected = int((320 * 240 / 1000000) * 1000 * 0.5 * (15 / 30))
        assert result == expected

    @patch("pbx.features.video_codec.get_logger")
    def test_unknown_quality_uses_default_multiplier(self, mock_logger: MagicMock) -> None:
        """Test that unknown quality level defaults to multiplier 1.0"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result_unknown = manager.calculate_bandwidth((1280, 720), 30, "unknown")
        result_medium = manager.calculate_bandwidth((1280, 720), 30, "medium")

        # Both should use multiplier 1.0
        assert result_unknown == result_medium

    @patch("pbx.features.video_codec.get_logger")
    def test_default_quality_is_medium(self, mock_logger: MagicMock) -> None:
        """Test that default quality parameter is medium"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result_default = manager.calculate_bandwidth((1280, 720), 30)
        result_medium = manager.calculate_bandwidth((1280, 720), 30, "medium")

        assert result_default == result_medium

    @patch("pbx.features.video_codec.get_logger")
    def test_returns_integer(self, mock_logger: MagicMock) -> None:
        """Test that the return value is always an integer"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        result = manager.calculate_bandwidth((1920, 1080), 30, "high")

        assert isinstance(result, int)

    @patch("pbx.features.video_codec.get_logger")
    def test_higher_resolution_more_bandwidth(self, mock_logger: MagicMock) -> None:
        """Test that higher resolution requires more bandwidth"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        bw_vga = manager.calculate_bandwidth((640, 480), 30, "medium")
        bw_hd = manager.calculate_bandwidth((1280, 720), 30, "medium")
        bw_fhd = manager.calculate_bandwidth((1920, 1080), 30, "medium")

        assert bw_vga < bw_hd < bw_fhd

    @patch("pbx.features.video_codec.get_logger")
    def test_higher_framerate_more_bandwidth(self, mock_logger: MagicMock) -> None:
        """Test that higher framerate requires more bandwidth"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        bw_15 = manager.calculate_bandwidth((1280, 720), 15, "medium")
        bw_30 = manager.calculate_bandwidth((1280, 720), 30, "medium")
        bw_60 = manager.calculate_bandwidth((1280, 720), 60, "medium")

        assert bw_15 < bw_30 < bw_60


@pytest.mark.unit
class TestGetStatistics:
    """Test the get_statistics method"""

    def _create_manager(self, mock_logger: MagicMock, enabled: bool = False) -> VideoCodecManager:
        from pbx.features.video_codec import VideoCodecManager

        config = {"features": {"video_codec": {"enabled": enabled}}}
        with (
            patch.object(VideoCodecManager, "_check_ffmpeg", return_value=True),
            patch.object(
                VideoCodecManager, "_detect_available_codecs", return_value=["H.264", "VP8"]
            ),
        ):
            manager = VideoCodecManager(config)
        return manager

    @patch("pbx.features.video_codec.get_logger")
    def test_initial_statistics(self, mock_logger: MagicMock) -> None:
        """Test statistics at initialization"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=False)

        stats = manager.get_statistics()

        assert stats["enabled"] is False
        assert stats["default_codec"] == "H.264"
        assert stats["available_codecs"] == ["H.264", "VP8"]
        assert stats["frames_encoded"] == 0
        assert stats["frames_decoded"] == 0
        assert stats["total_bandwidth_used"] == 0
        assert stats["bandwidth_mb"] == 0.0

    @patch("pbx.features.video_codec.get_logger")
    def test_statistics_after_encoding(self, mock_logger: MagicMock) -> None:
        """Test statistics after encoding frames"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        manager.encode_frame(b"\x00" * 1024)
        manager.encode_frame(b"\x00" * 2048)

        stats = manager.get_statistics()

        assert stats["enabled"] is True
        assert stats["frames_encoded"] == 2
        assert stats["total_bandwidth_used"] == 3072
        assert stats["bandwidth_mb"] == 3072 / (1024 * 1024)

    @patch("pbx.features.video_codec.get_logger")
    def test_statistics_after_decoding(self, mock_logger: MagicMock) -> None:
        """Test statistics after decoding frames"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        manager.decode_frame(b"\x00" * 100)
        manager.decode_frame(b"\x00" * 200)
        manager.decode_frame(b"\x00" * 300)

        stats = manager.get_statistics()

        assert stats["frames_decoded"] == 3

    @patch("pbx.features.video_codec.get_logger")
    def test_statistics_structure(self, mock_logger: MagicMock) -> None:
        """Test that statistics dictionary has expected keys"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger)

        stats = manager.get_statistics()

        expected_keys = {
            "enabled",
            "default_codec",
            "available_codecs",
            "frames_encoded",
            "frames_decoded",
            "total_bandwidth_used",
            "bandwidth_mb",
        }
        assert set(stats.keys()) == expected_keys

    @patch("pbx.features.video_codec.get_logger")
    def test_bandwidth_mb_calculation(self, mock_logger: MagicMock) -> None:
        """Test that bandwidth_mb is correctly calculated from total_bandwidth_used"""
        mock_logger.return_value = MagicMock()
        manager = self._create_manager(mock_logger, enabled=True)

        # Encode exactly 1 MB of data
        mb_data = b"\x00" * (1024 * 1024)
        manager.encode_frame(mb_data)

        stats = manager.get_statistics()

        assert stats["bandwidth_mb"] == pytest.approx(1.0)


@pytest.mark.unit
class TestGetVideoCodecManager:
    """Test the global get_video_codec_manager singleton function"""

    def teardown_method(self) -> None:
        """Reset the global singleton after each test"""
        import pbx.features.video_codec as vc_mod

        vc_mod._video_codec_manager = None

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_creates_instance_on_first_call(
        self, mock_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test that first call creates a new instance"""
        from pbx.features.video_codec import VideoCodecManager, get_video_codec_manager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        result = get_video_codec_manager()

        assert isinstance(result, VideoCodecManager)

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_returns_same_instance_on_subsequent_calls(
        self, mock_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test that subsequent calls return the same instance"""
        from pbx.features.video_codec import get_video_codec_manager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        instance1 = get_video_codec_manager()
        instance2 = get_video_codec_manager()

        assert instance1 is instance2

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_passes_config_to_constructor(
        self, mock_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test that config is passed through to the constructor"""
        from pbx.features.video_codec import get_video_codec_manager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        config = {"features": {"video_codec": {"enabled": True, "default_framerate": 24}}}
        result = get_video_codec_manager(config)

        assert result.enabled is True
        assert result.default_framerate == 24

    @patch("pbx.features.video_codec.get_logger")
    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    def test_ignores_config_on_subsequent_calls(
        self, mock_ffmpeg: MagicMock, mock_detect: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test that config on subsequent call does not replace existing instance"""
        from pbx.features.video_codec import get_video_codec_manager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]
        mock_logger.return_value = MagicMock()

        config1 = {"features": {"video_codec": {"default_framerate": 24}}}
        config2 = {"features": {"video_codec": {"default_framerate": 60}}}

        instance1 = get_video_codec_manager(config1)
        instance2 = get_video_codec_manager(config2)

        assert instance1 is instance2
        assert instance2.default_framerate == 24  # First config wins


@pytest.mark.unit
class TestModuleLevelFlags:
    """Test module-level PYAV_AVAILABLE and IMAGEIO_FFMPEG_AVAILABLE flags"""

    def test_pyav_available_is_boolean(self) -> None:
        """Test that PYAV_AVAILABLE is a boolean"""
        from pbx.features.video_codec import PYAV_AVAILABLE

        assert isinstance(PYAV_AVAILABLE, bool)

    def test_imageio_ffmpeg_available_is_boolean(self) -> None:
        """Test that IMAGEIO_FFMPEG_AVAILABLE is a boolean"""
        from pbx.features.video_codec import IMAGEIO_FFMPEG_AVAILABLE

        assert isinstance(IMAGEIO_FFMPEG_AVAILABLE, bool)
