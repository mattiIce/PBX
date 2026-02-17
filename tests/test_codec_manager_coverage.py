"""Comprehensive tests for VideoCodecManager (codec manager)."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestVideoCodecEnums:
    """Tests for video codec enumerations."""

    def test_video_codec_values(self) -> None:
        """Test VideoCodec enum values."""
        from pbx.features.video_codec import VideoCodec

        assert VideoCodec.H264.value == "H.264"
        assert VideoCodec.H265.value == "H.265"
        assert VideoCodec.VP8.value == "VP8"
        assert VideoCodec.VP9.value == "VP9"
        assert VideoCodec.AV1.value == "AV1"

    def test_video_profile_values(self) -> None:
        """Test VideoProfile enum values."""
        from pbx.features.video_codec import VideoProfile

        assert VideoProfile.BASELINE.value == "baseline"
        assert VideoProfile.MAIN.value == "main"
        assert VideoProfile.HIGH.value == "high"
        assert VideoProfile.HIGH10.value == "high10"

    def test_video_resolution_values(self) -> None:
        """Test VideoResolution enum values."""
        from pbx.features.video_codec import VideoResolution

        assert VideoResolution.QVGA.value == (320, 240)
        assert VideoResolution.VGA.value == (640, 480)
        assert VideoResolution.HD.value == (1280, 720)
        assert VideoResolution.FULL_HD.value == (1920, 1080)
        assert VideoResolution.QHD.value == (2560, 1440)
        assert VideoResolution.UHD_4K.value == (3840, 2160)


@pytest.mark.unit
class TestVideoCodecManagerInit:
    """Tests for VideoCodecManager initialization."""

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_init_default_config(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test initialization with default config."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        assert manager.enabled is False
        assert manager.frames_encoded == 0
        assert manager.frames_decoded == 0
        assert manager.total_bandwidth_used == 0

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_init_with_config(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test initialization with custom config."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264", "H.265"]

        config = {
            "features": {
                "video_codec": {
                    "enabled": True,
                    "default_codec": "H.264",
                    "default_profile": "main",
                    "default_resolution": "HD",
                    "default_framerate": 30,
                    "default_bitrate": 2000,
                }
            }
        }

        manager = VideoCodecManager(config)

        assert manager.enabled is True
        assert manager.default_framerate == 30
        assert manager.default_bitrate == 2000
        assert manager.ffmpeg_available is True


@pytest.mark.unit
class TestVideoCodecManagerCheckFFmpeg:
    """Tests for _check_ffmpeg."""

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_ffmpeg_available(
        self,
        mock_get_logger: MagicMock,
        mock_run: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test FFmpeg is available."""
        from pbx.features.video_codec import VideoCodecManager

        mock_run.return_value = MagicMock(returncode=0)
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        assert manager.ffmpeg_available is True

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_ffmpeg_not_found(
        self,
        mock_get_logger: MagicMock,
        mock_run: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test FFmpeg not found."""
        from pbx.features.video_codec import VideoCodecManager

        mock_run.side_effect = FileNotFoundError()
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        assert manager.ffmpeg_available is False

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_ffmpeg_timeout(
        self,
        mock_get_logger: MagicMock,
        mock_run: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test FFmpeg timeout."""
        import subprocess

        from pbx.features.video_codec import VideoCodecManager

        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        assert manager.ffmpeg_available is False


@pytest.mark.unit
class TestVideoCodecManagerDetection:
    """Tests for codec detection methods."""

    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detect_codecs_via_ffmpeg(
        self,
        mock_get_logger: MagicMock,
        mock_run: MagicMock,
        mock_ffmpeg: MagicMock,
    ) -> None:
        """Test codec detection via ffmpeg."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = True

        # First call for _check_ffmpeg, then for _detect_codecs_via_ffmpeg
        encoder_result = MagicMock()
        encoder_result.returncode = 0
        encoder_result.stdout = (
            "libx264 libx265 libvpx libvpx-vp9 libaom vp8 vp9 hevc h264 av1"
        )
        mock_run.return_value = encoder_result

        manager = VideoCodecManager()

        assert "H.264" in manager.available_codecs
        assert "H.265" in manager.available_codecs
        assert "VP8" in manager.available_codecs
        assert "VP9" in manager.available_codecs
        assert "AV1" in manager.available_codecs

    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.subprocess.run")
    @patch("pbx.features.video_codec.get_logger")
    def test_detect_no_codecs_provides_fallback(
        self,
        mock_get_logger: MagicMock,
        mock_run: MagicMock,
        mock_ffmpeg: MagicMock,
    ) -> None:
        """Test fallback when no codecs detected."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_run.side_effect = FileNotFoundError()

        manager = VideoCodecManager()

        # Should still have H.264 as fallback
        assert "H.264" in manager.available_codecs


@pytest.mark.unit
class TestVideoCodecManagerEncoding:
    """Tests for encode_frame and decode_frame."""

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_encode_frame_disabled(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test encode_frame when disabled."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()
        manager.enabled = False

        result = manager.encode_frame(b"\x00" * 100)

        assert result is None

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_encode_frame_success(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test encode_frame when enabled (placeholder)."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()
        manager.enabled = True

        frame_data = b"\x00" * 1000
        result = manager.encode_frame(frame_data)

        assert result == frame_data  # Placeholder returns same data
        assert manager.frames_encoded == 1
        assert manager.total_bandwidth_used == 1000

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_encode_frame_custom_params(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test encode_frame with custom parameters."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()
        manager.enabled = True

        frame_data = b"\x00" * 500
        result = manager.encode_frame(
            frame_data, codec="H.265", resolution=(1920, 1080), bitrate=4000
        )

        assert result is not None

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_decode_frame_disabled(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test decode_frame when disabled."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()
        manager.enabled = False

        result = manager.decode_frame(b"\x00" * 100)

        assert result is None

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_decode_frame_success(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test decode_frame when enabled (placeholder)."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = True
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()
        manager.enabled = True

        encoded_data = b"\x00" * 500
        result = manager.decode_frame(encoded_data, codec="H.264")

        assert result == encoded_data
        assert manager.frames_decoded == 1


@pytest.mark.unit
class TestVideoCodecManagerCreation:
    """Tests for create_encoder and create_decoder."""

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_create_encoder(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test creating an encoder."""
        from pbx.features.video_codec import (
            VideoCodec,
            VideoCodecManager,
            VideoProfile,
            VideoResolution,
        )

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        result = manager.create_encoder(
            VideoCodec.H264, VideoProfile.MAIN, VideoResolution.HD, 30, 2000
        )

        assert result["codec"] == "H.264"
        assert result["profile"] == "main"
        assert result["resolution"] == (1280, 720)
        assert result["framerate"] == 30
        assert result["bitrate"] == 2000
        assert result["gop_size"] == 60
        assert result["b_frames"] == 2

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_create_decoder(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test creating a decoder."""
        from pbx.features.video_codec import VideoCodec, VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        result = manager.create_decoder(VideoCodec.H265)

        assert result["codec"] == "H.265"
        assert result["threads"] == 4


@pytest.mark.unit
class TestVideoCodecManagerNegotiation:
    """Tests for codec negotiation and utilities."""

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_codec_success(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test successful codec negotiation."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        result = manager.negotiate_codec(
            ["H.264", "VP8"], ["H.264", "H.265"]
        )

        assert result == "H.264"

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_codec_prefers_h265(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test codec negotiation prefers H.265."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        result = manager.negotiate_codec(
            ["H.264", "H.265", "VP8"], ["H.265", "H.264"]
        )

        assert result == "H.265"

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_negotiate_codec_no_common(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test codec negotiation with no common codec."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        result = manager.negotiate_codec(["VP8"], ["AV1"])

        assert result is None

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_get_supported_resolutions(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test getting supported resolutions."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        result = manager.get_supported_resolutions("H.264")

        assert len(result) == 6
        assert (1280, 720) in result

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_calculate_bandwidth(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test bandwidth calculation."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        result = manager.calculate_bandwidth((1920, 1080), 30, "medium")

        assert result > 0
        assert isinstance(result, int)

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_calculate_bandwidth_quality_levels(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test bandwidth calculation with different quality levels."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()

        low = manager.calculate_bandwidth((1920, 1080), 30, "low")
        medium = manager.calculate_bandwidth((1920, 1080), 30, "medium")
        high = manager.calculate_bandwidth((1920, 1080), 30, "high")

        assert low < medium < high

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_get_statistics(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test getting statistics."""
        from pbx.features.video_codec import VideoCodecManager

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        manager = VideoCodecManager()
        manager.frames_encoded = 100
        manager.frames_decoded = 50
        manager.total_bandwidth_used = 1024 * 1024

        stats = manager.get_statistics()

        assert stats["frames_encoded"] == 100
        assert stats["frames_decoded"] == 50
        assert stats["bandwidth_mb"] == 1.0


@pytest.mark.unit
class TestGetVideoCodecManager:
    """Tests for the singleton get_video_codec_manager function."""

    @patch("pbx.features.video_codec.VideoCodecManager._detect_available_codecs")
    @patch("pbx.features.video_codec.VideoCodecManager._check_ffmpeg")
    @patch("pbx.features.video_codec.get_logger")
    def test_get_video_codec_manager(
        self,
        mock_get_logger: MagicMock,
        mock_ffmpeg: MagicMock,
        mock_detect: MagicMock,
    ) -> None:
        """Test singleton pattern."""
        import pbx.features.video_codec as vcm

        mock_ffmpeg.return_value = False
        mock_detect.return_value = ["H.264"]

        # Reset singleton
        vcm._video_codec_manager = None

        manager1 = vcm.get_video_codec_manager()
        manager2 = vcm.get_video_codec_manager()

        assert manager1 is manager2

        # Clean up singleton
        vcm._video_codec_manager = None
