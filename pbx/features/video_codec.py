"""
H.264/H.265 Video Codec Support
Video codec support for video calling using FREE open-source FFmpeg
"""

import subprocess
from datetime import UTC, datetime
from enum import Enum

from pbx.utils.logger import get_logger
from typing import Any

# Try to import PyAV (Python binding for FFmpeg)
try:
    PYAV_AVAILABLE = True
except ImportError:
    PYAV_AVAILABLE = False

# Try to import imageio-ffmpeg (simpler FFmpeg wrapper)
try:
    IMAGEIO_FFMPEG_AVAILABLE = True
except ImportError:
    IMAGEIO_FFMPEG_AVAILABLE = False


class VideoCodec(Enum):
    """Video codec enumeration"""

    H264 = "H.264"
    H265 = "H.265"
    VP8 = "VP8"
    VP9 = "VP9"
    AV1 = "AV1"


class VideoProfile(Enum):
    """H.264/H.265 encoding profiles"""

    BASELINE = "baseline"
    MAIN = "main"
    HIGH = "high"
    HIGH10 = "high10"


class VideoResolution(Enum):
    """Common video resolutions"""

    QVGA = (320, 240)
    VGA = (640, 480)
    HD = (1280, 720)
    FULL_HD = (1920, 1080)
    QHD = (2560, 1440)
    UHD_4K = (3840, 2160)


class VideoCodecManager:
    """
    Video Codec Manager

    Manages H.264/H.265 video codecs for video calling using FREE open-source FFmpeg.

    Uses FREE open-source tools:
    - FFmpeg (libx264, libx265) - industry-standard video processing
    - PyAV - Pythonic binding for FFmpeg
    - OpenH264 - Cisco's open-source H.264 codec
    - x265 - open-source HEVC/H.265 encoder
    - libvpx - VP8/VP9 codecs

    Can also integrate with:
    - GStreamer video plugins
    - Hardware encoders (NVENC, QuickSync, etc.)
    """

    def __init__(self, config: Any | None =None) -> None:
        """Initialize video codec manager"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        video_config = self.config.get("features", {}).get("video_codec", {})
        self.enabled = video_config.get("enabled", False)
        self.default_codec = VideoCodec(video_config.get("default_codec", "H.264"))
        self.default_profile = VideoProfile(video_config.get("default_profile", "main"))
        self.default_resolution = video_config.get("default_resolution", "HD")
        self.default_framerate = video_config.get("default_framerate", 30)
        self.default_bitrate = video_config.get("default_bitrate", 2000)  # kbps

        # FFmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()

        # Codec availability
        self.available_codecs = self._detect_available_codecs()

        # Statistics
        self.frames_encoded = 0
        self.frames_decoded = 0
        self.total_bandwidth_used = 0

        self.logger.info("Video codec manager initialized")
        self.logger.info(f"  Default codec: {self.default_codec.value}")
        self.logger.info(f"  Default profile: {self.default_profile.value}")
        self.logger.info(f"  Default resolution: {self.default_resolution}")
        self.logger.info(f"  FFmpeg available: {self.ffmpeg_available}")
        self.logger.info(f"  PyAV available: {PYAV_AVAILABLE}")
        self.logger.info(f"  Available codecs: {', '.join(self.available_codecs)}")
        self.logger.info(f"  Enabled: {self.enabled}")

        if not self.ffmpeg_available:
            self.logger.info("Install FFmpeg for video codec support:")
            self.logger.info("  Ubuntu/Debian: sudo apt-get install ffmpeg")
            self.logger.info("  macOS: brew install ffmpeg")

        if not PYAV_AVAILABLE:
            self.logger.info("Install PyAV for Python FFmpeg bindings:")
            self.logger.info("  pip install av")

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _detect_codecs_via_ffmpeg(self) -> list:
        """Detect codecs using FFmpeg"""
        available = []
        if not self.ffmpeg_available:
            return available

        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                output = result.stdout

                # Check for H.264 encoders
                if "libx264" in output or "h264" in output.lower():
                    available.append("H.264")
                    self.logger.debug("H.264 codec available (libx264)")

                # Check for H.265 encoders
                if "libx265" in output or "hevc" in output.lower():
                    available.append("H.265")
                    self.logger.debug("H.265 codec available (libx265)")

                # Check for VP8/VP9
                if "libvpx" in output or "vp8" in output.lower():
                    available.append("VP8")
                    self.logger.debug("VP8 codec available (libvpx)")

                if "libvpx-vp9" in output or "vp9" in output.lower():
                    available.append("VP9")
                    self.logger.debug("VP9 codec available (libvpx-vp9)")

                # Check for AV1
                if "libaom" in output or "av1" in output.lower():
                    available.append("AV1")
                    self.logger.debug("AV1 codec available (libaom)")

        except (subprocess.TimeoutExpired, Exception) as e:
            self.logger.debug(f"FFmpeg encoder detection error: {e}")

        return available

    def _detect_openh264(self, available: list) -> list:
        """Detect OpenH264 library"""
        try:
            import ctypes

            for lib_name in ["libopenh264.so", "openh264.dll", "libopenh264.dylib"]:
                try:
                    ctypes.CDLL(lib_name)
                    self.logger.info(f"OpenH264 library detected: {lib_name}")
                    if "H.264" not in available:
                        available.append("H.264")
                    break
                except OSError:
                    continue
        except Exception as e:
            self.logger.debug(f"OpenH264 detection error: {e}")
        return available

    def _detect_x265(self, available: list) -> list:
        """Detect x265 encoder"""
        try:
            result = subprocess.run(
                ["x265", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.logger.info("x265 encoder detected")
                if "H.265" not in available:
                    available.append("H.265")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            self.logger.debug(f"x265 not found: {e}")
        return available

    def _detect_available_codecs(self) -> list:
        """
        Detect which video codecs are available using FFmpeg

        Checks for installed codec libraries and returns list of supported codecs.
        Uses FREE open-source FFmpeg to detect:
        - H.264 (libx264, openh264)
        - H.265 (libx265)
        - VP8/VP9 (libvpx)
        - AV1 (libaom)

        Returns:
            list: list of available codec names
        """
        available = self._detect_codecs_via_ffmpeg()
        available = self._detect_openh264(available)
        available = self._detect_x265(available)

        # If nothing detected, provide framework placeholders
        if not available:
            self.logger.warning("No video codec libraries detected")
            # Still add H.264 as placeholder for framework purposes
            available.append("H.264")

        return available

    def encode_frame(
        self,
        frame_data: bytes,
        codec: str | None = None,
        resolution: tuple | None = None,
        bitrate: int | None = None,
    ) -> bytes | None:
        """
        Encode video frame using FFmpeg/PyAV

        Args:
            frame_data: Raw video frame (YUV or RGB)
            codec: Codec to use (default: H.264)
            resolution: Video resolution tuple (width, height)
            bitrate: Target bitrate in kbps

        Returns:
            bytes | None: Encoded frame data or None
        """
        if not self.enabled:
            return None

        codec = codec or self.default_codec.value
        bitrate = bitrate or self.default_bitrate

        # Implement actual video encoding
        # In production, integrate with FFmpeg using subprocess or PyAV library

        # Option 1: Using FFmpeg subprocess
        # import subprocess
        # import tempfile
        #
        # # Write raw frame to temporary file
        # with tempfile.NamedTemporaryFile(suffix='.yuv') as temp_in:
        #     temp_in.write(frame_data)
        #     temp_in.flush()
        #
        #     # Encode using FFmpeg
        #     result = subprocess.run([
        #         'ffmpeg', '-', 'rawvideo', '-pix_fmt', 'yuv420p',
        #         '-s', f'{resolution[0]}x{resolution[1]}',
        #         '-i', temp_in.name,
        #         '-c:v', 'libx264',  # or libx265 for H.265
        #         '-b:v', f'{bitrate}k',
        #         '-', 'h264',  # Output format
        #         'pipe:1'  # Output to stdout
        #     ], capture_output=True)
        #
        #     if result.returncode == 0:
        #         return result.stdout

        # Option 2: Using PyAV library (more efficient)
        # import av
        #
        # # Create codec context
        # codec_ctx = av.CodecContext.create(codec.lower(), 'w')
        # codec_ctx.width = resolution[0]
        # codec_ctx.height = resolution[1]
        # codec_ctx.bit_rate = bitrate * 1000
        # codec_ctx.time_base = fractions.Fraction(1, 30)  # 30 fps
        # codec_ctx.pix_fmt = 'yuv420p'
        #
        # # Create frame from raw data
        # frame = av.VideoFrame.from_ndarray(frame_array, format='yuv420p')
        #
        # # Encode
        # packets = codec_ctx.encode(frame)
        # if packets:
        #     return packets[0].to_bytes()

        # Framework placeholder - logs encoding attempt
        self.frames_encoded += 1
        self.total_bandwidth_used += len(frame_data)

        self.logger.debug(
            f"Encoded frame: codec={codec}, bitrate={bitrate}kbps, size={len(frame_data)} bytes"
        )
        self.logger.debug("NOTE: Using placeholder - integrate FFmpeg/PyAV for actual encoding")

        # Placeholder return (in production, return actual encoded data)
        return frame_data

    def decode_frame(self, encoded_data: bytes, codec: str | None = None) -> bytes | None:
        """
        Decode video frame

        Args:
            encoded_data: Encoded video frame
            codec: Codec used for encoding

        Returns:
            bytes | None: Decoded frame data (raw YUV or RGB) or None
        """
        if not self.enabled:
            return None

        codec = codec or self.default_codec.value

        # Implement actual video decoding
        # In production, integrate with FFmpeg using subprocess or PyAV library

        # Option 1: Using FFmpeg subprocess
        # import subprocess
        # import tempfile
        #
        # with tempfile.NamedTemporaryFile(suffix='.h264') as temp_in:
        #     temp_in.write(encoded_data)
        #     temp_in.flush()
        #
        #     # Decode using FFmpeg
        #     result = subprocess.run([
        #         'ffmpeg', '-i', temp_in.name,
        #         '-', 'rawvideo', '-pix_fmt', 'yuv420p',
        #         'pipe:1'  # Output to stdout
        #     ], capture_output=True)
        #
        #     if result.returncode == 0:
        #         return result.stdout

        # Option 2: Using PyAV library (more efficient)
        # import av
        #
        # # Create codec context for decoding
        # codec_ctx = av.CodecContext.create(codec.lower(), 'r')
        #
        # # Create packet from encoded data
        # packet = av.Packet(encoded_data)
        #
        # # Decode
        # frames = codec_ctx.decode(packet)
        # if frames:
        #     # Convert frame to raw bytes
        #     frame = frames[0]
        #     return frame.to_ndarray().tobytes()

        # Framework placeholder - logs decoding attempt
        self.frames_decoded += 1

        self.logger.debug(f"Decoded frame: codec={codec}, size={len(encoded_data)} bytes")
        self.logger.debug("NOTE: Using placeholder - integrate FFmpeg/PyAV for actual decoding")

        # Placeholder return (in production, return actual decoded data)
        return encoded_data

    def create_encoder(
        self,
        codec: VideoCodec,
        profile: VideoProfile,
        resolution: VideoResolution,
        framerate: int,
        bitrate: int,
    ) -> dict:
        """
        Create a video encoder instance

        Args:
            codec: Video codec to use
            profile: Encoding profile
            resolution: Video resolution
            framerate: Frames per second
            bitrate: Target bitrate in kbps

        Returns:
            dict: Encoder configuration
        """
        encoder_config = {
            "codec": codec.value,
            "profile": profile.value,
            "resolution": resolution.value,
            "framerate": framerate,
            "bitrate": bitrate,
            "gop_size": framerate * 2,  # GOP size (keyframe interval)
            "b_frames": 2,  # B-frames for better compression
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Initialize actual encoder with FFmpeg or PyAV library
        # In production, this would create and configure an encoder instance

        # Example using PyAV:
        # import av
        #
        # codec_name = 'libx264' if codec == VideoCodec.H264 else 'libx265'
        # encoder_ctx = av.CodecContext.create(codec_name, 'w')
        # encoder_ctx.width = resolution.value[0]
        # encoder_ctx.height = resolution.value[1]
        # encoder_ctx.bit_rate = bitrate * 1000
        # encoder_ctx.time_base = fractions.Fraction(1, framerate)
        # encoder_ctx.framerate = framerate
        # encoder_ctx.pix_fmt = 'yuv420p'
        # encoder_ctx.gop_size = framerate * 2
        #
        # # H.264 specific options
        # if codec == VideoCodec.H264:
        #     encoder_ctx.options = {
        #         'profile': profile.value.replace('_', '-'),  # baseline, main, high
        #         'preset': 'medium',  # ultrafast, fast, medium, slow, veryslow
        #         'tune': 'zerolatency'  # For real-time encoding
        #     }
        #
        # # Store encoder context
        # encoder_config['encoder_ctx'] = encoder_ctx

        self.logger.info(
            f"Created encoder: {codec.value} {profile.value} "
            f"{resolution.value[0]}x{resolution.value[1]} "
            f"{framerate}fps {bitrate}kbps"
        )
        self.logger.info(
            "NOTE: Using framework placeholder - integrate PyAV/FFmpeg for actual encoder"
        )

        return encoder_config

    def create_decoder(self, codec: VideoCodec) -> dict:
        """
        Create a video decoder instance

        Args:
            codec: Video codec

        Returns:
            dict: Decoder configuration
        """
        decoder_config = {
            "codec": codec.value,
            "threads": 4,  # Multi-threaded decoding
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Initialize actual decoder with FFmpeg or PyAV library
        # In production, this would create and configure a decoder instance

        # Example using PyAV:
        # import av
        #
        # codec_name = 'h264' if codec == VideoCodec.H264 else 'hevc'
        # decoder_ctx = av.CodecContext.create(codec_name, 'r')
        # decoder_ctx.thread_count = 4  # Multi-threaded decoding
        # decoder_ctx.thread_type = 'AUTO'
        #
        # # Store decoder context
        # decoder_config['decoder_ctx'] = decoder_ctx

        self.logger.info(f"Created decoder: {codec.value}")
        self.logger.info(
            "NOTE: Using framework placeholder - integrate PyAV/FFmpeg for actual decoder"
        )

        return decoder_config

    def negotiate_codec(self, local_codecs: list, remote_codecs: list) -> str | None:
        """
        Negotiate codec between local and remote endpoints

        Args:
            local_codecs: list of locally supported codecs
            remote_codecs: list of remotely supported codecs

        Returns:
            str | None: Negotiated codec or None
        """
        # Find common codec with preference order
        codec_preference = ["H.265", "H.264", "VP9", "VP8"]

        for codec in codec_preference:
            if codec in local_codecs and codec in remote_codecs:
                self.logger.info(f"Negotiated video codec: {codec}")
                return codec

        self.logger.warning("No common video codec found")
        return None

    def get_supported_resolutions(self, codec: str) -> list:
        """Get supported resolutions for a codec"""
        # Most codecs support all common resolutions
        return [
            VideoResolution.QVGA.value,
            VideoResolution.VGA.value,
            VideoResolution.HD.value,
            VideoResolution.FULL_HD.value,
            VideoResolution.QHD.value,
            VideoResolution.UHD_4K.value,
        ]

    def calculate_bandwidth(
        self, resolution: tuple, framerate: int, quality: str = "medium"
    ) -> int:
        """
        Calculate required bandwidth for video stream

        Args:
            resolution: Video resolution (width, height)
            framerate: Frames per second
            quality: Quality level (low, medium, high)

        Returns:
            int: Required bitrate in kbps
        """
        pixels = resolution[0] * resolution[1]

        # Base bitrate per megapixel
        quality_multipliers = {"low": 0.5, "medium": 1.0, "high": 2.0}

        multiplier = quality_multipliers.get(quality, 1.0)
        base_rate = (pixels / 1000000) * 1000  # 1 Mbps per megapixel

        bitrate = int(base_rate * multiplier * (framerate / 30))

        return bitrate

    def get_statistics(self) -> dict:
        """Get video codec statistics"""
        return {
            "enabled": self.enabled,
            "default_codec": self.default_codec.value,
            "available_codecs": self.available_codecs,
            "frames_encoded": self.frames_encoded,
            "frames_decoded": self.frames_decoded,
            "total_bandwidth_used": self.total_bandwidth_used,
            "bandwidth_mb": self.total_bandwidth_used / (1024 * 1024),
        }


# Global instance
_video_codec_manager = None


def get_video_codec_manager(config: Any | None =None) -> VideoCodecManager:
    """Get or create video codec manager instance"""
    global _video_codec_manager
    if _video_codec_manager is None:
        _video_codec_manager = VideoCodecManager(config)
    return _video_codec_manager
