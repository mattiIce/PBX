"""
H.264/H.265 Video Codec Support
Video codec support for video calling using FREE open-source FFmpeg
"""

import fractions
import subprocess
import tempfile
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pbx.utils.logger import get_logger

# Try to import PyAV (Python binding for FFmpeg)
try:
    import av

    PYAV_AVAILABLE = True
except ImportError:
    av = None  # type: ignore[assignment]
    PYAV_AVAILABLE = False

# Try to import imageio-ffmpeg (simpler FFmpeg wrapper)
try:
    import imageio_ffmpeg  # noqa: F401

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

    def __init__(self, config: Any | None = None) -> None:
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
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5, check=False
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
                ["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5, check=False
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
                ["x265", "--version"], capture_output=True, text=True, timeout=5, check=False
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

        # Also detect codecs via PyAV if available
        if PYAV_AVAILABLE:
            try:
                for codec_name, label in [
                    ("libx264", "H.264"),
                    ("libx265", "H.265"),
                    ("libvpx", "VP8"),
                    ("libvpx-vp9", "VP9"),
                    ("libaom-av1", "AV1"),
                ]:
                    try:
                        av.codec.Codec(codec_name, "w")
                        if label not in available:
                            available.append(label)
                            self.logger.debug(f"{label} codec available via PyAV ({codec_name})")
                    except Exception:
                        continue
            except Exception as e:
                self.logger.debug(f"PyAV codec detection error: {e}")

        if not available:
            self.logger.warning(
                "No video codec libraries detected. "
                "Install FFmpeg or PyAV for video encoding support."
            )

        return available

    def _get_ffmpeg_encoder_name(self, codec: str) -> str:
        """Map codec name to FFmpeg encoder name."""
        codec_map = {
            "H.264": "libx264",
            "H.265": "libx265",
            "VP8": "libvpx",
            "VP9": "libvpx-vp9",
            "AV1": "libaom-av1",
        }
        return codec_map.get(codec, "libx264")

    def _get_ffmpeg_format_name(self, codec: str) -> str:
        """Map codec name to FFmpeg raw output format name."""
        format_map = {
            "H.264": "h264",
            "H.265": "hevc",
            "VP8": "ivf",
            "VP9": "ivf",
            "AV1": "ivf",
        }
        return format_map.get(codec, "h264")

    def _encode_frame_pyav(
        self,
        frame_data: bytes,
        codec: str,
        resolution: tuple,
        bitrate: int,
    ) -> bytes | None:
        """Encode a single video frame using PyAV."""
        encoder_name = self._get_ffmpeg_encoder_name(codec)
        width, height = resolution

        try:
            codec_ctx = av.CodecContext.create(encoder_name, "w")
            codec_ctx.width = width
            codec_ctx.height = height
            codec_ctx.bit_rate = bitrate * 1000
            codec_ctx.time_base = fractions.Fraction(1, self.default_framerate)
            codec_ctx.pix_fmt = "yuv420p"
            codec_ctx.gop_size = self.default_framerate * 2

            if codec == "H.264":
                codec_ctx.options = {
                    "preset": "ultrafast",
                    "tune": "zerolatency",
                    "profile": self.default_profile.value,
                }
            elif codec == "H.265":
                codec_ctx.options = {
                    "preset": "ultrafast",
                    "tune": "zerolatency",
                }

            codec_ctx.open()

            # Build a VideoFrame from raw YUV420p bytes
            expected_yuv_size = width * height * 3 // 2
            if len(frame_data) == expected_yuv_size:
                frame = av.VideoFrame(width, height, "yuv420p")
                # Copy Y, U, V planes
                y_size = width * height
                uv_size = (width // 2) * (height // 2)
                frame.planes[0].update(frame_data[:y_size])
                frame.planes[1].update(frame_data[y_size : y_size + uv_size])
                frame.planes[2].update(frame_data[y_size + uv_size : y_size + 2 * uv_size])
            else:
                # Assume raw RGB24 and let PyAV convert
                expected_rgb_size = width * height * 3
                if len(frame_data) != expected_rgb_size:
                    self.logger.warning(
                        f"Frame data size {len(frame_data)} does not match "
                        f"expected YUV420p ({expected_yuv_size}) or "
                        f"RGB24 ({expected_rgb_size}) for {width}x{height}"
                    )
                    return None
                frame = av.VideoFrame(width, height, "rgb24")
                frame.planes[0].update(frame_data)
                frame = frame.reformat(format="yuv420p")

            frame.pts = self.frames_encoded

            packets = codec_ctx.encode(frame)
            # Flush remaining packets
            packets += codec_ctx.encode(None)

            if packets:
                encoded = b"".join(bytes(p) for p in packets)
                return encoded

        except Exception as e:
            self.logger.debug(f"PyAV encoding failed: {e}")

        return None

    def _encode_frame_ffmpeg(
        self,
        frame_data: bytes,
        codec: str,
        resolution: tuple,
        bitrate: int,
    ) -> bytes | None:
        """Encode a single video frame using FFmpeg subprocess."""
        encoder_name = self._get_ffmpeg_encoder_name(codec)
        out_format = self._get_ffmpeg_format_name(codec)
        width, height = resolution

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "yuv420p",
                "-s",
                f"{width}x{height}",
                "-r",
                str(self.default_framerate),
                "-i",
                "pipe:0",
                "-c:v",
                encoder_name,
                "-b:v",
                f"{bitrate}k",
                "-frames:v",
                "1",
                "-f",
                out_format,
                "pipe:1",
            ]

            if codec == "H.264":
                # Insert H.264 specific options before output
                idx = cmd.index("-f")
                cmd[idx:idx] = ["-preset", "ultrafast", "-tune", "zerolatency"]
            elif codec == "H.265":
                idx = cmd.index("-f")
                cmd[idx:idx] = ["-preset", "ultrafast", "-tune", "zerolatency"]

            result = subprocess.run(
                cmd,
                input=frame_data,
                capture_output=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                return result.stdout

            if result.returncode != 0:
                self.logger.debug(f"FFmpeg encode failed: {result.stderr[:200]!r}")

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.logger.debug(f"FFmpeg subprocess encoding failed: {e}")

        return None

    def encode_frame(
        self,
        frame_data: bytes,
        codec: str | None = None,
        resolution: tuple | None = None,
        bitrate: int | None = None,
    ) -> bytes | None:
        """
        Encode video frame using FFmpeg/PyAV

        Tries PyAV first (most efficient, in-process), then falls back to
        FFmpeg subprocess, and finally returns the raw frame data as a
        passthrough if no encoder is available.

        Args:
            frame_data: Raw video frame (YUV420p or RGB24)
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
        if resolution is None:
            res_enum = VideoResolution[self.default_resolution]
            resolution = res_enum.value

        # Try PyAV first (in-process, most efficient)
        if PYAV_AVAILABLE:
            encoded = self._encode_frame_pyav(frame_data, codec, resolution, bitrate)
            if encoded is not None:
                self.frames_encoded += 1
                self.total_bandwidth_used += len(encoded)
                self.logger.debug(
                    f"Encoded frame via PyAV: codec={codec}, "
                    f"bitrate={bitrate}kbps, "
                    f"input={len(frame_data)} bytes, "
                    f"output={len(encoded)} bytes"
                )
                return encoded

        # Fall back to FFmpeg subprocess
        if self.ffmpeg_available:
            encoded = self._encode_frame_ffmpeg(frame_data, codec, resolution, bitrate)
            if encoded is not None:
                self.frames_encoded += 1
                self.total_bandwidth_used += len(encoded)
                self.logger.debug(
                    f"Encoded frame via FFmpeg subprocess: codec={codec}, "
                    f"bitrate={bitrate}kbps, "
                    f"input={len(frame_data)} bytes, "
                    f"output={len(encoded)} bytes"
                )
                return encoded

        # Passthrough fallback: return raw data when no encoder is available
        self.frames_encoded += 1
        self.total_bandwidth_used += len(frame_data)
        self.logger.debug(
            f"Encoded frame (passthrough): codec={codec}, "
            f"bitrate={bitrate}kbps, size={len(frame_data)} bytes. "
            "No encoder available; install FFmpeg or PyAV for actual encoding."
        )
        return frame_data

    def _get_ffmpeg_decoder_name(self, codec: str) -> str:
        """Map codec name to FFmpeg decoder name."""
        decoder_map = {
            "H.264": "h264",
            "H.265": "hevc",
            "VP8": "vp8",
            "VP9": "vp9",
            "AV1": "av1",
        }
        return decoder_map.get(codec, "h264")

    def _get_ffmpeg_input_format(self, codec: str) -> str:
        """Map codec name to FFmpeg input format for raw bitstream."""
        format_map = {
            "H.264": "h264",
            "H.265": "hevc",
            "VP8": "ivf",
            "VP9": "ivf",
            "AV1": "ivf",
        }
        return format_map.get(codec, "h264")

    def _decode_frame_pyav(self, encoded_data: bytes, codec: str) -> bytes | None:
        """Decode a video frame using PyAV."""
        decoder_name = self._get_ffmpeg_decoder_name(codec)

        try:
            codec_ctx = av.CodecContext.create(decoder_name, "r")
            codec_ctx.open()

            packet = av.Packet(encoded_data)
            frames = codec_ctx.decode(packet)
            # Flush the decoder
            frames = list(frames) + list(codec_ctx.decode(None))

            if frames:
                frame = frames[0].reformat(format="yuv420p")
                # Concatenate Y, U, V planes into raw bytes
                raw = b""
                for plane in frame.planes:
                    raw += bytes(plane)
                return raw

        except Exception as e:
            self.logger.debug(f"PyAV decoding failed: {e}")

        return None

    def _decode_frame_ffmpeg(self, encoded_data: bytes, codec: str) -> bytes | None:
        """Decode a video frame using FFmpeg subprocess."""
        input_format = self._get_ffmpeg_input_format(codec)

        try:
            # Write encoded data to a temp file since piping compressed
            # video via stdin can be unreliable for some container formats
            with tempfile.NamedTemporaryFile(suffix=f".{input_format}", delete=False) as tmp:
                tmp.write(encoded_data)
                tmp_path = Path(tmp.name)

            try:
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f",
                    input_format,
                    "-i",
                    str(tmp_path),
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "yuv420p",
                    "-frames:v",
                    "1",
                    "pipe:1",
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10,
                    check=False,
                )

                if result.returncode == 0 and result.stdout:
                    return result.stdout

                if result.returncode != 0:
                    self.logger.debug(f"FFmpeg decode failed: {result.stderr[:200]!r}")
            finally:
                tmp_path.unlink(missing_ok=True)

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.logger.debug(f"FFmpeg subprocess decoding failed: {e}")

        return None

    def decode_frame(self, encoded_data: bytes, codec: str | None = None) -> bytes | None:
        """
        Decode video frame

        Tries PyAV first (most efficient, in-process), then falls back to
        FFmpeg subprocess, and finally returns the encoded data as a
        passthrough if no decoder is available.

        Args:
            encoded_data: Encoded video frame
            codec: Codec used for encoding

        Returns:
            bytes | None: Decoded frame data (raw YUV420p) or None
        """
        if not self.enabled:
            return None

        codec = codec or self.default_codec.value

        # Try PyAV first
        if PYAV_AVAILABLE:
            decoded = self._decode_frame_pyav(encoded_data, codec)
            if decoded is not None:
                self.frames_decoded += 1
                self.logger.debug(
                    f"Decoded frame via PyAV: codec={codec}, "
                    f"input={len(encoded_data)} bytes, "
                    f"output={len(decoded)} bytes"
                )
                return decoded

        # Fall back to FFmpeg subprocess
        if self.ffmpeg_available:
            decoded = self._decode_frame_ffmpeg(encoded_data, codec)
            if decoded is not None:
                self.frames_decoded += 1
                self.logger.debug(
                    f"Decoded frame via FFmpeg subprocess: codec={codec}, "
                    f"input={len(encoded_data)} bytes, "
                    f"output={len(decoded)} bytes"
                )
                return decoded

        # Passthrough fallback
        self.frames_decoded += 1
        self.logger.debug(
            f"Decoded frame (passthrough): codec={codec}, "
            f"size={len(encoded_data)} bytes. "
            "No decoder available; install FFmpeg or PyAV for actual decoding."
        )
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
            dict: Encoder configuration including a live PyAV encoder context
                  when available
        """
        encoder_config: dict[str, Any] = {
            "codec": codec.value,
            "profile": profile.value,
            "resolution": resolution.value,
            "framerate": framerate,
            "bitrate": bitrate,
            "gop_size": framerate * 2,
            "b_frames": 2,
            "created_at": datetime.now(UTC).isoformat(),
            "backend": "none",
        }

        # Try to create a real PyAV encoder context
        if PYAV_AVAILABLE:
            encoder_name = self._get_ffmpeg_encoder_name(codec.value)
            try:
                encoder_ctx = av.CodecContext.create(encoder_name, "w")
                encoder_ctx.width = resolution.value[0]
                encoder_ctx.height = resolution.value[1]
                encoder_ctx.bit_rate = bitrate * 1000
                encoder_ctx.time_base = fractions.Fraction(1, framerate)
                encoder_ctx.framerate = fractions.Fraction(framerate, 1)
                encoder_ctx.pix_fmt = "yuv420p"
                encoder_ctx.gop_size = framerate * 2
                encoder_ctx.max_b_frames = 2

                options: dict[str, str] = {
                    "preset": "ultrafast",
                    "tune": "zerolatency",
                }
                if codec == VideoCodec.H264:
                    options["profile"] = profile.value
                encoder_ctx.options = options

                encoder_ctx.open()
                encoder_config["encoder_ctx"] = encoder_ctx
                encoder_config["backend"] = "pyav"

                self.logger.info(
                    f"Created PyAV encoder: {codec.value} {profile.value} "
                    f"{resolution.value[0]}x{resolution.value[1]} "
                    f"{framerate}fps {bitrate}kbps"
                )
                return encoder_config

            except Exception as e:
                self.logger.debug(f"PyAV encoder creation failed: {e}")

        # Fall back to FFmpeg subprocess-based encoding (no persistent context)
        if self.ffmpeg_available:
            encoder_config["backend"] = "ffmpeg"
            self.logger.info(
                f"Created FFmpeg subprocess encoder config: {codec.value} {profile.value} "
                f"{resolution.value[0]}x{resolution.value[1]} "
                f"{framerate}fps {bitrate}kbps"
            )
            return encoder_config

        # No encoder backend available -- config only
        self.logger.warning(
            f"Created encoder config without backend: {codec.value} {profile.value} "
            f"{resolution.value[0]}x{resolution.value[1]} "
            f"{framerate}fps {bitrate}kbps. "
            "Install FFmpeg or PyAV for actual encoding."
        )
        return encoder_config

    def create_decoder(self, codec: VideoCodec) -> dict:
        """
        Create a video decoder instance

        Args:
            codec: Video codec

        Returns:
            dict: Decoder configuration including a live PyAV decoder context
                  when available
        """
        decoder_config: dict[str, Any] = {
            "codec": codec.value,
            "threads": 4,
            "created_at": datetime.now(UTC).isoformat(),
            "backend": "none",
        }

        # Try to create a real PyAV decoder context
        if PYAV_AVAILABLE:
            decoder_name = self._get_ffmpeg_decoder_name(codec.value)
            try:
                decoder_ctx = av.CodecContext.create(decoder_name, "r")
                decoder_ctx.thread_count = 4
                decoder_ctx.thread_type = "AUTO"
                decoder_ctx.open()

                decoder_config["decoder_ctx"] = decoder_ctx
                decoder_config["backend"] = "pyav"

                self.logger.info(f"Created PyAV decoder: {codec.value}")
                return decoder_config

            except Exception as e:
                self.logger.debug(f"PyAV decoder creation failed: {e}")

        # Fall back to FFmpeg subprocess-based decoding
        if self.ffmpeg_available:
            decoder_config["backend"] = "ffmpeg"
            self.logger.info(f"Created FFmpeg subprocess decoder config: {codec.value}")
            return decoder_config

        # No decoder backend available -- config only
        self.logger.warning(
            f"Created decoder config without backend: {codec.value}. "
            "Install FFmpeg or PyAV for actual decoding."
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

        if framerate <= 0:
            framerate = 30

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


def get_video_codec_manager(config: Any | None = None) -> VideoCodecManager:
    """Get or create video codec manager instance"""
    global _video_codec_manager
    if _video_codec_manager is None:
        _video_codec_manager = VideoCodecManager(config)
    return _video_codec_manager
