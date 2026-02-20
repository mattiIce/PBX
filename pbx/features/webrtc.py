"""
WebRTC Browser Calling Support
Provides WebRTC signaling and integration with PBX SIP infrastructure.

Uses aiortc for server-side WebRTC (DTLS-SRTP, ICE) so that browsers
can exchange real media with the PBX's plain-RTP infrastructure.
"""

import asyncio
import fractions
import socket
import struct
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pbx.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

# aiortc – server-side WebRTC implementation
try:
    from aiortc import MediaStreamTrack, RTCPeerConnection as AiortcPC, RTCSessionDescription
    from av import AudioFrame

    AIORTC_AVAILABLE = True
except ImportError:  # graceful degradation
    AIORTC_AVAILABLE = False


logger = get_logger()


# ---------------------------------------------------------------------------
# Audio bridge track – sends audio FROM the PBX TO the browser
# ---------------------------------------------------------------------------

if AIORTC_AVAILABLE:

    class AudioBridgeTrack(MediaStreamTrack):
        """MediaStreamTrack that feeds audio from the PBX RTP stream to the browser."""

        kind = "audio"

        def __init__(self, sample_rate: int = 8000, samples_per_frame: int = 160) -> None:
            super().__init__()
            self._sample_rate = sample_rate
            self._samples_per_frame = samples_per_frame
            self._queue: asyncio.Queue[AudioFrame] = asyncio.Queue(maxsize=200)
            self._timestamp = 0

        async def recv(self) -> "AudioFrame":
            """Return the next frame (or silence if nothing queued)."""
            try:
                frame = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                frame = self._silence_frame()
            # Pace at ~20 ms per frame to avoid busy-looping
            await asyncio.sleep(self._samples_per_frame / self._sample_rate)
            return frame

        def push_frame(self, frame: "AudioFrame") -> None:
            try:
                self._queue.put_nowait(frame)
            except asyncio.QueueFull:
                pass  # drop oldest – real-time audio cannot block

        def _silence_frame(self) -> "AudioFrame":
            frame = AudioFrame(format="s16", layout="mono", samples=self._samples_per_frame)
            for plane in frame.planes:
                plane.update(bytes(self._samples_per_frame * 2))
            frame.pts = self._timestamp
            frame.sample_rate = self._sample_rate
            frame.time_base = fractions.Fraction(1, self._sample_rate)
            self._timestamp += self._samples_per_frame
            return frame


# ---------------------------------------------------------------------------
# RTP ↔ aiortc audio bridge (runs in background threads / coroutines)
# ---------------------------------------------------------------------------

# u-law lookup tables (replaces removed audioop in Python 3.13)
_ULAW_ENCODE_TABLE: list[int] | None = None
_ULAW_DECODE_TABLE: list[int] | None = None


def _init_ulaw_tables() -> None:
    """Lazily build u-law encode / decode lookup tables."""
    global _ULAW_ENCODE_TABLE, _ULAW_DECODE_TABLE  # noqa: PLW0603

    if _ULAW_DECODE_TABLE is not None:
        return

    # Decode: 256 entries mapping u-law byte → signed 16-bit sample
    _ULAW_DECODE_TABLE = []
    for i in range(256):
        val = ~i
        sign = val & 0x80
        exponent = (val >> 4) & 0x07
        mantissa = val & 0x0F
        sample = ((mantissa << 3) + 0x84) << exponent
        sample -= 0x84
        _ULAW_DECODE_TABLE.append(-sample if sign else sample)

    # Encode: 65536 entries mapping unsigned index → u-law byte
    BIAS = 0x84
    CLIP = 32635
    _ULAW_ENCODE_TABLE = []
    for idx in range(65536):
        sample = idx - 32768  # convert to signed
        sign_bit = 0
        if sample < 0:
            sign_bit = 0x80
            sample = -sample
        if sample > CLIP:
            sample = CLIP
        sample += BIAS
        exponent = 7
        for mask in (0x4000, 0x2000, 0x1000, 0x0800, 0x0400, 0x0200, 0x0100):
            if sample & mask:
                break
            exponent -= 1
        mantissa = (sample >> (exponent + 3)) & 0x0F
        _ULAW_ENCODE_TABLE.append(~(sign_bit | (exponent << 4) | mantissa) & 0xFF)


def _pcm_to_ulaw(pcm_bytes: bytes) -> bytes:
    """Convert signed-16-bit-LE PCM to u-law bytes."""
    _init_ulaw_tables()
    assert _ULAW_ENCODE_TABLE is not None
    out = bytearray(len(pcm_bytes) // 2)
    for i in range(0, len(pcm_bytes), 2):
        sample = int.from_bytes(pcm_bytes[i : i + 2], "little", signed=True)
        out[i // 2] = _ULAW_ENCODE_TABLE[sample + 32768]
    return bytes(out)


def _ulaw_to_pcm(ulaw_bytes: bytes) -> bytes:
    """Convert u-law bytes to signed-16-bit-LE PCM."""
    _init_ulaw_tables()
    assert _ULAW_DECODE_TABLE is not None
    out = bytearray(len(ulaw_bytes) * 2)
    for i, b in enumerate(ulaw_bytes):
        sample = _ULAW_DECODE_TABLE[b]
        out[i * 2 : i * 2 + 2] = sample.to_bytes(2, "little", signed=True)
    return bytes(out)


class WebRTCSession:
    """Represents a WebRTC session"""

    def __init__(
        self, session_id: str, extension: str, peer_connection_id: str | None = None
    ) -> None:
        """
        Initialize WebRTC session

        Args:
            session_id: Unique session identifier
            extension: Extension number associated with this session
            peer_connection_id: Optional peer connection identifier
        """
        self.session_id = session_id
        self.extension = extension
        self.peer_connection_id = peer_connection_id or str(uuid.uuid4())
        self.created_at = datetime.now(UTC)
        self.last_activity = datetime.now(UTC)
        self.state = "new"  # new, connecting, connected, disconnected
        self.local_sdp = None
        self.remote_sdp = None
        self.ice_candidates = []
        self.call_id = None
        self.metadata = {}

        # aiortc server-side peer connection
        self.pc: Any | None = None  # AiortcPC
        self.answer_sdp: str | None = None
        self.bridge_track: Any | None = None  # AudioBridgeTrack → browser
        self.browser_track: Any | None = None  # Track received from browser
        self.bridge_socket: socket.socket | None = None  # UDP for RTP relay I/O
        self.bridge_port: int | None = None
        self._bridge_running = False

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now(UTC)

    def to_dict(self) -> dict:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "extension": self.extension,
            "peer_connection_id": self.peer_connection_id,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "call_id": self.call_id,
        }


class WebRTCSignalingServer:
    """
    WebRTC Signaling Server

    Handles WebRTC signaling between browser clients and PBX
    - Session management
    - SDP offer/answer exchange
    - ICE candidate exchange
    - Integration with SIP infrastructure
    """

    def __init__(self, config: Any | None = None, pbx_core: Any | None = None) -> None:
        """
        Initialize WebRTC signaling server

        Args:
            config: Configuration object
            pbx_core: PBXCore instance (optional, for extension registration)
        """
        self.logger = get_logger()
        self.config = config or {}
        self.pbx_core = pbx_core

        # WebRTC configuration
        self.enabled = self._get_config("features.webrtc.enabled", False)
        self.verbose_logging = self._get_config("features.webrtc.verbose_logging", False)
        self.stun_servers = self._get_config(
            "features.webrtc.stun_servers",
            ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"],
        )
        self.turn_servers = self._get_config("features.webrtc.turn_servers", [])
        self.ice_transport_policy = self._get_config("features.webrtc.ice_transport_policy", "all")
        self.session_timeout = self._get_config(
            "features.webrtc.session_timeout", 3600
        )  # 1 hour (matches ZIP33G)

        # Codec configuration (matches Zultys ZIP33G)
        self.codecs = self._get_config(
            "features.webrtc.codecs",
            [
                {"payload_type": 0, "name": "PCMU", "priority": 1, "enabled": True},
                {"payload_type": 8, "name": "PCMA", "priority": 2, "enabled": True},
                {"payload_type": 101, "name": "telephone-event", "priority": 3, "enabled": True},
            ],
        )

        # DTMF configuration (matches Zultys ZIP33G)
        self.dtmf_mode = self._get_config("features.webrtc.dtmf.mode", "RFC2833")
        self.dtmf_payload_type = self._get_config("features.webrtc.dtmf.payload_type", 101)
        self.dtmf_duration = self._get_config("features.webrtc.dtmf.duration", 160)
        self.dtmf_sip_info_fallback = self._get_config(
            "features.webrtc.dtmf.sip_info_fallback", True
        )

        # RTP configuration (matches Zultys ZIP33G)
        self.rtp_port_min = self._get_config("features.webrtc.rtp.port_min", 10000)
        self.rtp_port_max = self._get_config("features.webrtc.rtp.port_max", 20000)
        self.rtp_packet_time = self._get_config("features.webrtc.rtp.packet_time", 20)

        # NAT configuration (matches Zultys ZIP33G)
        self.nat_udp_update_time = self._get_config("features.webrtc.nat.udp_update_time", 30)
        self.nat_rport = self._get_config("features.webrtc.nat.rport", True)

        # Audio configuration (matches Zultys ZIP33G)
        self.audio_echo_cancellation = self._get_config(
            "features.webrtc.audio.echo_cancellation", True
        )
        self.audio_noise_reduction = self._get_config("features.webrtc.audio.noise_reduction", True)
        self.audio_auto_gain_control = self._get_config(
            "features.webrtc.audio.auto_gain_control", True
        )
        self.audio_vad = self._get_config("features.webrtc.audio.voice_activity_detection", True)
        self.audio_comfort_noise = self._get_config("features.webrtc.audio.comfort_noise", True)

        # Sessions
        self.sessions: dict[str, WebRTCSession] = {}
        # extension -> set of session_ids
        self.extension_sessions: dict[str, set[str]] = {}
        self.lock = threading.Lock()

        # Callbacks
        self.on_session_created: Callable | None = None
        self.on_session_closed: Callable | None = None
        self.on_offer_received: Callable | None = None
        self.on_answer_received: Callable | None = None

        # Cleanup thread
        self.running = False
        self.cleanup_thread = None

        # Dedicated asyncio event loop for aiortc peer connections
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None

        if self.enabled:
            self.logger.info("WebRTC signaling server enabled")
            if AIORTC_AVAILABLE:
                self._loop = asyncio.new_event_loop()
                self._loop_thread = threading.Thread(
                    target=self._run_event_loop, daemon=True, name="WebRTCAsyncLoop"
                )
                self._loop_thread.start()
                self.logger.info("aiortc async event loop started")
            else:
                self.logger.warning("aiortc not installed – WebRTC media bridge unavailable")
            if self.verbose_logging:
                self.logger.info("WebRTC verbose logging ENABLED")
                self.logger.info(f"  STUN servers: {self.stun_servers}")
                self.logger.info(f"  TURN servers: {len(self.turn_servers)} configured")
                self.logger.info(f"  Session timeout: {self.session_timeout}s")
                self.logger.info(f"  ICE transport policy: {self.ice_transport_policy}")
            self._start_cleanup_thread()
        else:
            self.logger.info("WebRTC signaling server disabled")

    def _get_config(self, key: str, default: Any | None = None) -> Any:
        """Get configuration value"""
        if hasattr(self.config, "get"):
            return self.config.get(key, default)
        return default

    def _start_cleanup_thread(self) -> None:
        """Start session cleanup thread"""
        self.running = True
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker, name="WebRTCCleanup", daemon=True
        )
        self.cleanup_thread.start()
        self.logger.info("Started WebRTC session cleanup thread")

    def stop(self) -> None:
        """Stop the WebRTC signaling server"""
        self.logger.info("Stopping WebRTC signaling server...")
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.logger.info("WebRTC signaling server stopped")

    # ------------------------------------------------------------------
    # Async event loop helpers
    # ------------------------------------------------------------------

    def _run_event_loop(self) -> None:
        """Target for the background thread that runs the aiortc event loop."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro: Any, timeout: float = 15.0) -> Any:
        """Run *coro* on the aiortc event loop from synchronous code."""
        if not self._loop:
            raise RuntimeError("aiortc event loop not started")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ------------------------------------------------------------------
    # aiortc offer → answer
    # ------------------------------------------------------------------

    async def _handle_offer_async(self, session: WebRTCSession, sdp: str) -> str | None:
        """Create an aiortc PeerConnection, process the browser's offer,
        and return the SDP answer string."""
        pc = AiortcPC()
        session.pc = pc

        # Create the bridge track (PBX → browser audio) and add it so
        # the answer includes an audio media section.
        bridge_track = AudioBridgeTrack()
        session.bridge_track = bridge_track
        pc.addTrack(bridge_track)

        # Capture the browser's audio track when it arrives
        @pc.on("track")
        def _on_track(track: Any) -> None:
            self.logger.info(f"Received browser audio track for session {session.session_id}")
            session.browser_track = track

        @pc.on("connectionstatechange")
        async def _on_state() -> None:
            self.logger.info(
                f"WebRTC connection state for {session.session_id}: {pc.connectionState}"
            )
            if pc.connectionState == "connected":
                session.state = "connected"
            elif pc.connectionState in ("failed", "closed"):
                session.state = "disconnected"

        # Process the browser's offer
        offer = RTCSessionDescription(sdp=sdp, type="offer")
        await pc.setRemoteDescription(offer)

        # Generate and apply the answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        session.answer_sdp = pc.localDescription.sdp
        session.state = "connecting"
        self.logger.info(f"Generated SDP answer for session {session.session_id}")
        return session.answer_sdp

    def _cleanup_worker(self) -> None:
        """Worker thread for cleaning up stale sessions"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            self._cleanup_stale_sessions()

    def _cleanup_stale_sessions(self) -> None:
        """Remove stale sessions that have timed out"""
        with self.lock:
            now = datetime.now(UTC)
            stale_sessions = []

            for session_id, session in self.sessions.items():
                age = (now - session.last_activity).total_seconds()
                if age > self.session_timeout:
                    stale_sessions.append(session_id)

            for session_id in stale_sessions:
                session = self.sessions.get(session_id)
                if session:
                    self.logger.info(
                        f"Cleaning up stale WebRTC session: {session_id} (extension: {session.extension})"
                    )
                    self._remove_session(session_id)

    def _log_session_creation(self, session_id: str, extension: str, session: dict) -> None:
        """Log verbose session creation details"""
        if not self.verbose_logging:
            return

        self.logger.info("[VERBOSE] Session created details:")
        self.logger.info(f"  Session ID: {session_id}")
        self.logger.info(f"  Extension: {extension}")
        self.logger.info(f"  Peer Connection ID: {session.peer_connection_id}")
        self.logger.info(f"  Total active sessions: {len(self.sessions)}")
        self.logger.info(
            f"  Sessions for extension {extension}: {len(self.extension_sessions.get(extension, set()))}"
        )

    def _create_virtual_webrtc_extension(self, extension: str) -> None:
        """Create virtual WebRTC extension if needed"""
        if not self.pbx_core:
            return None

        try:
            # Check if extension exists in registry
            ext_obj = self.pbx_core.extension_registry.get_extension(extension)

            if not ext_obj and extension.startswith("webrtc-"):
                # Auto-create virtual WebRTC extension if it doesn't exist
                self.logger.info(f"Auto-creating virtual WebRTC extension: {extension}")

                from pbx.features.extensions import Extension

                virtual_ext_config = {
                    "number": extension,
                    "name": f"WebRTC Client ({extension})",
                    "allow_external": True,
                    "virtual": True,  # Mark as virtual extension
                    "webrtc_only": True,  # Mark as WebRTC-only extension
                }

                ext_obj = Extension(extension, virtual_ext_config["name"], virtual_ext_config)
                self.pbx_core.extension_registry.extensions[extension] = ext_obj
                self.logger.info(f"Created virtual extension {extension} in registry")

                if self.verbose_logging:
                    self.logger.info("[VERBOSE] Virtual extension created:")
                    self.logger.info(f"  Extension: {extension}")
                    self.logger.info("  type: Virtual WebRTC")

            return ext_obj
        except (KeyError, TypeError, ValueError) as e:
            self.logger.warning(f"Could not register WebRTC extension: {e}")
            return None

    def create_session(self, extension: str) -> WebRTCSession:
        """
        Create a new WebRTC session

        Args:
            extension: Extension number

        Returns:
            WebRTCSession object
        """
        if not self.enabled:
            raise RuntimeError("WebRTC is not enabled")

        session_id = str(uuid.uuid4())
        session = WebRTCSession(session_id, extension)

        with self.lock:
            self.sessions[session_id] = session

            # Track sessions by extension
            if extension not in self.extension_sessions:
                self.extension_sessions[extension] = set()
            self.extension_sessions[extension].add(session_id)

        self.logger.info(f"Created WebRTC session: {session_id} (extension: {extension})")
        self._log_session_creation(session_id, extension, session)

        # Register the extension in the extension registry if PBX core is available
        ext_obj = self._create_virtual_webrtc_extension(extension)

        if ext_obj:
            # Register as active with a virtual WebRTC address
            # Use session_id as the unique identifier for the WebRTC connection
            webrtc_addr = ("webrtc", session_id)
            self.pbx_core.extension_registry.register(extension, webrtc_addr)
            self.logger.info(f"Registered WebRTC extension {extension} in extension registry")

            if self.verbose_logging:
                self.logger.info("[VERBOSE] Extension registered:")
                self.logger.info(f"  Extension: {extension}")
                self.logger.info(f"  WebRTC Address: {webrtc_addr}")

            # Track in registered_phones_db if available
            if (
                hasattr(self.pbx_core, "registered_phones_db")
                and self.pbx_core.registered_phones_db
            ):
                try:
                    # Register WebRTC client as a phone in the database
                    # Use hash of session_id for MAC to avoid collisions while keeping reasonable length
                    import hashlib

                    mac_suffix = hashlib.sha256(session_id.encode()).hexdigest()[:12]
                    success, _stored_mac = self.pbx_core.registered_phones_db.register_phone(
                        extension_number=extension,
                        ip_address="webrtc",  # Special marker for WebRTC connections
                        # Use hash of session ID for uniqueness
                        mac_address=f"webrtc-{mac_suffix}",
                        user_agent=f"WebRTC Browser Client (Session: {session_id})",
                        contact_uri=f"<webrtc:{extension}@{session_id}>",
                    )

                    if success:
                        self.logger.info(
                            f"Registered WebRTC session in phones database: ext={extension}"
                        )
                        if self.verbose_logging:
                            self.logger.info("[VERBOSE] Phone DB registration successful")
                    else:
                        self.logger.warning("Failed to register WebRTC session in phones database")
                except Exception as e:
                    self.logger.error(f"Error registering WebRTC session in phones database: {e}")
        else:
            self.logger.warning(f"Extension {extension} not found in registry for WebRTC session")
            if self.verbose_logging and self.pbx_core:
                self.logger.warning(
                    f"[VERBOSE] Available extensions: {list(self.pbx_core.extension_registry.extensions)[:10]}"
                )

        if self.on_session_created:
            try:
                self.on_session_created(session)
            except Exception as e:
                self.logger.error(f"Error in session created callback: {e}")

        return session

    def get_session(self, session_id: str) -> WebRTCSession | None:
        """Get session by ID"""
        with self.lock:
            return self.sessions.get(session_id)

    def get_extension_sessions(self, extension: str) -> list:
        """Get all sessions for an extension"""
        with self.lock:
            session_ids = self.extension_sessions.get(extension, set())
            return [self.sessions[sid] for sid in session_ids if sid in self.sessions]

    def close_session(self, session_id: str) -> bool:
        """
        Close a WebRTC session

        Args:
            session_id: Session identifier

        Returns:
            True if session was closed, False if not found
        """
        with self.lock:
            return self._remove_session(session_id)

    def _remove_session(self, session_id: str) -> bool:
        """Remove session (internal, assumes lock is held)"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        # Get extension before removing session
        extension = session.extension

        # Remove from sessions
        del self.sessions[session_id]

        # Remove from extension tracking
        if extension in self.extension_sessions:
            self.extension_sessions[extension].discard(session_id)
            # Check if this was the last session for this extension
            last_session = not self.extension_sessions[extension]
            if last_session:
                del self.extension_sessions[extension]

                # Unregister the extension from the registry if it was the last
                # session
                if self.pbx_core:
                    try:
                        self.pbx_core.extension_registry.unregister(extension)
                        self.logger.info(
                            f"Unregistered WebRTC extension {extension} from extension registry"
                        )

                        if self.verbose_logging:
                            self.logger.info("[VERBOSE] Extension unregistered:")
                            self.logger.info(f"  Extension: {extension}")
                            self.logger.info("  Reason: Last WebRTC session closed")
                    except Exception as e:
                        self.logger.error(f"Error unregistering WebRTC extension: {e}")

        self.logger.info(f"Closed WebRTC session: {session_id} (extension: {extension})")

        if self.on_session_closed:
            try:
                self.on_session_closed(session)
            except Exception as e:
                self.logger.error(f"Error in session closed callback: {e}")

        return True

    def handle_offer(self, session_id: str, sdp: str) -> str | None:
        """
        Handle SDP offer from client.

        When aiortc is available the method creates a server-side
        RTCPeerConnection and returns the SDP **answer** string so the
        browser can complete the WebRTC handshake.  Falls back to the
        legacy store-only behaviour (returns ``"__legacy__"``) when
        aiortc is missing.

        Args:
            session_id: Session identifier
            sdp: SDP offer from the browser

        Returns:
            SDP answer string, ``"__legacy__"`` (aiortc unavailable),
            or ``None`` on error.
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.warning(f"Received offer for unknown session: {session_id}")
            if self.verbose_logging:
                self.logger.warning("[VERBOSE] Unknown session details:")
                self.logger.warning(f"  Session ID: {session_id}")
                self.logger.warning(f"  Active sessions: {list(self.sessions)}")
            return None

        session.local_sdp = sdp
        session.update_activity()

        self.logger.info(f"Received SDP offer for session: {session_id}")
        self.logger.debug(f"SDP offer: {sdp[:100]}...")

        if self.verbose_logging:
            self.logger.info("[VERBOSE] SDP offer received:")
            self.logger.info(f"  Session ID: {session_id}")
            self.logger.info(f"  Extension: {session.extension}")
            self.logger.info(f"  SDP length: {len(sdp)} bytes")

        if self.on_offer_received:
            try:
                self.on_offer_received(session, sdp)
            except Exception as e:
                self.logger.error(f"Error in offer received callback: {e}")

        # --- aiortc path: generate a real SDP answer ---
        if AIORTC_AVAILABLE and self._loop:
            try:
                answer_sdp = self._run_async(self._handle_offer_async(session, sdp))
                if answer_sdp:
                    self.logger.info(f"SDP answer generated for session {session_id}")
                    return answer_sdp
                self.logger.error(f"Failed to generate SDP answer for session {session_id}")
                return None
            except Exception as e:
                self.logger.error(f"aiortc error generating SDP answer: {e}")
                return None

        # --- fallback: store offer only (no real media will flow) ---
        session.state = "connecting"
        return "__legacy__"

    def handle_answer(self, session_id: str, sdp: str) -> bool:
        """
        Handle SDP answer from client

        Args:
            session_id: Session identifier
            sdp: SDP answer

        Returns:
            True if answer was accepted
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.warning(f"Received answer for unknown session: {session_id}")
            return False

        session.remote_sdp = sdp
        session.state = "connected"
        session.update_activity()

        self.logger.info(f"Received SDP answer for session: {session_id}")
        self.logger.debug(f"SDP answer: {sdp[:100]}...")

        if self.on_answer_received:
            try:
                self.on_answer_received(session, sdp)
            except Exception as e:
                self.logger.error(f"Error in answer received callback: {e}")

        return True

    def add_ice_candidate(self, session_id: str, candidate: dict) -> bool:
        """
        Add ICE candidate for session

        Args:
            session_id: Session identifier
            candidate: ICE candidate dictionary

        Returns:
            True if candidate was added
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.warning(f"Received ICE candidate for unknown session: {session_id}")
            return False

        session.ice_candidates.append(candidate)
        session.update_activity()

        self.logger.debug(f"Added ICE candidate for session: {session_id}")

        if self.verbose_logging:
            self.logger.info("[VERBOSE] ICE candidate added:")
            self.logger.info(f"  Session ID: {session_id}")
            self.logger.info(f"  Candidate: {candidate.get('candidate', 'N/A')}")
            self.logger.info(f"  SDP MID: {candidate.get('sdpMid', 'N/A')}")
            self.logger.info(f"  SDP M-Line Index: {candidate.get('sdpMLineIndex', 'N/A')}")
            self.logger.info(f"  Total candidates for session: {len(session.ice_candidates)}")

        return True

    # ------------------------------------------------------------------
    # RTP ↔ aiortc media bridge
    # ------------------------------------------------------------------

    def start_media_bridge(
        self,
        session: WebRTCSession,
        relay_port: int,
        phone_endpoint: tuple[str, int],
    ) -> bool:
        """Start bidirectional audio bridge between aiortc and the RTP relay.

        *relay_port* is the PBX RTP relay's local port.  The bridge
        opens its own UDP socket, sends/receives plain RTP to/from the
        relay, and converts between aiortc AudioFrames and u-law RTP
        packets.

        Args:
            session: The WebRTC session.
            relay_port: Local port of the PBX RTP relay for this call.
            phone_endpoint: (ip, port) of the SIP phone (used to
                configure the relay's endpoint B).

        Returns:
            True if the bridge was started.
        """
        if not AIORTC_AVAILABLE or not session.pc:
            self.logger.error("Cannot start media bridge: aiortc not available or no PC")
            return False

        try:
            # Open a UDP socket that will talk to the RTP relay
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))  # OS picks a free port
            bridge_port = sock.getsockname()[1]
            sock.settimeout(0.05)  # non-blocking-ish for the reader thread

            session.bridge_socket = sock
            session.bridge_port = bridge_port
            session._bridge_running = True

            self.logger.info(
                f"Media bridge for session {session.session_id}: "
                f"127.0.0.1:{bridge_port} <-> relay:{relay_port}"
            )

            # Tell the RTP relay that endpoint A is our bridge socket
            if self.pbx_core and session.call_id:
                relay_info = self.pbx_core.rtp_relay.active_relays.get(session.call_id)
                if relay_info:
                    handler = relay_info["handler"]
                    handler.set_endpoints(("127.0.0.1", bridge_port), phone_endpoint)

            relay_addr = ("127.0.0.1", relay_port)

            # --- Thread: RTP relay → aiortc (phone audio → browser) ---
            def _relay_to_browser() -> None:
                seq = 0
                while session._bridge_running:
                    try:
                        data, _addr = sock.recvfrom(2048)
                    except (TimeoutError, OSError):
                        continue
                    if len(data) < 12:
                        continue
                    # Strip RTP header (12 bytes minimum) and decode u-law payload
                    payload = data[12:]
                    pcm = _ulaw_to_pcm(payload)
                    samples = len(pcm) // 2
                    frame = AudioFrame(format="s16", layout="mono", samples=samples)
                    for plane in frame.planes:
                        plane.update(pcm)
                    frame.pts = seq * samples
                    frame.sample_rate = 8000
                    frame.time_base = fractions.Fraction(1, 8000)
                    if session.bridge_track:
                        session.bridge_track.push_frame(frame)
                    seq += 1

            threading.Thread(
                target=_relay_to_browser,
                daemon=True,
                name=f"WebRTC-R2B-{session.session_id[:8]}",
            ).start()

            # --- Async coroutine: aiortc → RTP relay (browser audio → phone) ---
            async def _browser_to_relay() -> None:
                rtp_seq = 0
                rtp_ts = 0
                ssrc = int.from_bytes(uuid.uuid4().bytes[:4], "big")
                while session._bridge_running:
                    if not session.browser_track:
                        await asyncio.sleep(0.02)
                        continue
                    try:
                        frame = await asyncio.wait_for(
                            session.browser_track.recv(), timeout=0.1
                        )
                    except (asyncio.TimeoutError, Exception):
                        continue
                    # Resample to 8 kHz mono if needed
                    pcm = bytes(frame.planes[0])
                    sr = frame.sample_rate
                    if sr != 8000:
                        # Simple decimation (works well for 48→8 kHz)
                        import array

                        src = array.array("h", pcm)
                        ratio = sr // 8000
                        if ratio > 0:
                            dst = array.array("h", (src[i] for i in range(0, len(src), ratio)))
                            pcm = dst.tobytes()
                    ulaw = _pcm_to_ulaw(pcm)
                    samples = len(ulaw)
                    # Build RTP packet: V=2, PT=0 (PCMU), with seq/ts/ssrc
                    header = struct.pack(
                        "!BBHII",
                        0x80,  # V=2, no padding/extension/CSRC
                        0,  # PT=0 (PCMU)
                        rtp_seq & 0xFFFF,
                        rtp_ts & 0xFFFFFFFF,
                        ssrc,
                    )
                    try:
                        sock.sendto(header + ulaw, relay_addr)
                    except OSError:
                        pass
                    rtp_seq += 1
                    rtp_ts += samples

            if self._loop:
                asyncio.run_coroutine_threadsafe(_browser_to_relay(), self._loop)

            return True
        except Exception as e:
            self.logger.error(f"Error starting media bridge: {e}")
            return False

    def stop_media_bridge(self, session: WebRTCSession) -> None:
        """Stop the media bridge for a session."""
        session._bridge_running = False
        if session.bridge_socket:
            try:
                session.bridge_socket.close()
            except OSError:
                pass
            session.bridge_socket = None
        if session.pc:
            if self._loop:
                try:
                    asyncio.run_coroutine_threadsafe(session.pc.close(), self._loop)
                except Exception:
                    pass
            session.pc = None

    def get_ice_servers_config(self) -> dict:
        """
        Get ICE servers configuration for client

        Returns:
            Dictionary with ICE servers configuration, codec preferences,
            audio settings, and DTMF configuration (matches Zultys ZIP33G)
        """
        ice_servers = [{"urls": stun_url} for stun_url in self.stun_servers]

        # Add TURN servers
        ice_servers.extend(
            {
                "urls": turn_config.get("url"),
                "username": turn_config.get("username"),
                "credential": turn_config.get("credential"),
            }
            for turn_config in self.turn_servers
        )

        return {
            "iceServers": ice_servers,
            "iceTransportPolicy": self.ice_transport_policy,
            # Include codec preferences (matches Zultys ZIP33G)
            "codecs": self.codecs,
            # Include audio settings (matches Zultys ZIP33G)
            "audio": {
                "echoCancellation": self.audio_echo_cancellation,
                "noiseSuppression": self.audio_noise_reduction,
                "autoGainControl": self.audio_auto_gain_control,
            },
            # Include DTMF settings (matches Zultys ZIP33G)
            "dtmf": {
                "mode": self.dtmf_mode,
                "payloadType": self.dtmf_payload_type,
                "duration": self.dtmf_duration,
                "sipInfoFallback": self.dtmf_sip_info_fallback,
            },
        }

    def get_sessions_info(self) -> list:
        """Get information about all active sessions"""
        with self.lock:
            return [session.to_dict() for session in self.sessions.values()]

    def set_session_call_id(self, session_id: str, call_id: str) -> bool:
        """Associate a call ID with a session"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.call_id = call_id
        session.update_activity()
        self.logger.info(f"Associated call {call_id} with WebRTC session {session_id}")
        return True

    def set_session_metadata(self, session_id: str, key: str, value: Any) -> bool:
        """set metadata for a session"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.metadata[key] = value
        session.update_activity()
        return True

    def get_session_metadata(self, session_id: str, key: str, default: Any | None = None) -> Any:
        """Get metadata from a session"""
        session = self.get_session(session_id)
        if not session:
            return default

        return session.metadata.get(key, default)


class WebRTCGateway:
    """
    WebRTC to SIP Gateway

    Translates between WebRTC and SIP protocols
    - Converts WebRTC SDP to SIP SDP
    - Handles media negotiation
    - Manages RTP/SRTP bridging
    """

    def __init__(self, pbx_core: Any | None = None) -> None:
        """
        Initialize WebRTC gateway

        Args:
            pbx_core: PBX core instance
        """
        self.logger = get_logger()
        self.pbx_core = pbx_core
        self.verbose_logging = False
        # Check if pbx_core has webrtc_signaling with verbose_logging enabled
        if pbx_core and hasattr(pbx_core, "webrtc_signaling"):
            self.verbose_logging = getattr(pbx_core.webrtc_signaling, "verbose_logging", False)
        self.logger.info("WebRTC to SIP gateway initialized")
        if self.verbose_logging:
            self.logger.info("[VERBOSE] WebRTC gateway verbose logging ENABLED")

    def webrtc_to_sip_sdp(self, webrtc_sdp: str) -> str:
        """
        Convert WebRTC SDP to SIP-compatible SDP

        Args:
            webrtc_sdp: WebRTC SDP

        Returns:
            SIP-compatible SDP
        """
        from pbx.sip.sdp import SDPSession

        self.logger.debug("Converting WebRTC SDP to SIP SDP")

        try:
            # Parse WebRTC SDP
            sdp = SDPSession()
            sdp.parse(webrtc_sdp)

            # Transform for SIP compatibility
            for media in sdp.media:
                # Convert DTLS-SRTP to RTP/AVP (standard SIP)
                original_protocol = media.get("protocol", "")
                if "DTLS" in original_protocol:
                    media["protocol"] = "RTP/AVP"
                    self.logger.debug(f"Converted protocol from {original_protocol} to RTP/AVP")

                # Filter out WebRTC-specific attributes that SIP doesn't
                # understand
                webrtc_attrs = [
                    "ice-ufrag",
                    "ice-pwd",
                    "ice-options",
                    "fingerprint",
                    "setup",
                    "mid",
                    "extmap",
                    "msid",
                    "ssrc",
                    "rtcp-mux",
                ]

                original_attrs = media.get("attributes", [])
                filtered_attrs = []

                for attr in original_attrs:
                    # Keep attribute if it's not WebRTC-specific
                    attr_name = attr.split(":")[0] if ":" in attr else attr
                    if attr_name not in webrtc_attrs:
                        filtered_attrs.append(attr)
                    else:
                        self.logger.debug(f"Filtered WebRTC attribute: {attr_name}")

                media["attributes"] = filtered_attrs

                # Ensure we have basic RTP attributes
                has_sendrecv = any(
                    "sendrecv" in attr or "sendonly" in attr or "recvonly" in attr
                    for attr in filtered_attrs
                )
                if not has_sendrecv:
                    filtered_attrs.append("sendrecv")

            # Build and return transformed SDP
            result = sdp.build()
            self.logger.debug("WebRTC to SIP SDP conversion complete")
            return result

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error converting WebRTC to SIP SDP: {e}")
            # Fallback: return original SDP
            return webrtc_sdp

    def sip_to_webrtc_sdp(
        self,
        sip_sdp: str,
        ice_ufrag: str | None = None,
        ice_pwd: str | None = None,
        fingerprint: str | None = None,
    ) -> str:
        """
        Convert SIP SDP to WebRTC-compatible SDP

        Args:
            sip_sdp: SIP SDP
            ice_ufrag: ICE username fragment (generated if not provided)
            ice_pwd: ICE password (generated if not provided)
            fingerprint: DTLS fingerprint (generated if not provided)

        Returns:
            WebRTC-compatible SDP
        """
        import hashlib
        import secrets

        from pbx.sip.sdp import SDPSession

        self.logger.debug("Converting SIP SDP to WebRTC SDP")

        try:
            # Parse SIP SDP
            sdp = SDPSession()
            sdp.parse(sip_sdp)

            # Generate WebRTC-required values if not provided
            if not ice_ufrag:
                ice_ufrag = secrets.token_hex(4)
            if not ice_pwd:
                ice_pwd = secrets.token_hex(12)
            if not fingerprint:
                # Generate a basic fingerprint (in production, this would be
                # from actual cert)
                fingerprint = "fingerprint:sha-256 " + ":".join(
                    [
                        hashlib.sha256(secrets.token_bytes(32)).hexdigest()[i : i + 2].upper()
                        for i in range(0, 64, 2)
                    ]
                )

            # Transform for WebRTC compatibility
            for media_idx, media in enumerate(sdp.media):
                # Convert RTP/AVP to RTP/SAVPF (secure audio/video profile with
                # feedback)
                if media.get("protocol") == "RTP/AVP":
                    media["protocol"] = "RTP/SAVPF"
                    self.logger.debug("Converted protocol to RTP/SAVPF for WebRTC")

                # Get existing attributes
                attrs = media.get("attributes", [])

                # Add WebRTC-required attributes
                webrtc_attrs = [
                    f"ice-ufrag:{ice_ufrag}",
                    f"ice-pwd:{ice_pwd}",
                    "ice-options:trickle",
                    fingerprint,
                    "setup:actpass",  # Active/passive for DTLS
                    f"mid:{media_idx}",  # Media ID
                    "rtcp-mux",  # Multiplex RTP and RTCP on same port
                ]

                # Add WebRTC attributes at the beginning
                media["attributes"] = webrtc_attrs + attrs

                self.logger.debug(f"Added WebRTC attributes to media {media_idx}")

            # Build and return transformed SDP
            result = sdp.build()
            self.logger.debug("SIP to WebRTC SDP conversion complete")
            return result

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error converting SIP to WebRTC SDP: {e}")
            # Fallback: return original SDP
            return sip_sdp

    def initiate_call(
        self, session_id: str, target_extension: str, webrtc_signaling: Any | None = None
    ) -> str | None:
        """
        Initiate a call from WebRTC client to extension

        Args:
            session_id: WebRTC session ID
            target_extension: Target extension number
            webrtc_signaling: WebRTCSignalingServer instance (optional)

        Returns:
            Call ID if successful, None otherwise
        """
        if not self.pbx_core:
            self.logger.error("PBX core not available for call initiation")
            return None

        self.logger.info(f"Initiating call from WebRTC session {session_id} to {target_extension}")

        if self.verbose_logging:
            self.logger.info("[VERBOSE] Call initiation details:")
            self.logger.info(f"  Session ID: {session_id}")
            self.logger.info(f"  Target Extension: {target_extension}")

        try:
            # 1. Get WebRTC session
            session = None
            if webrtc_signaling:
                session = webrtc_signaling.get_session(session_id)

            if not session:
                self.logger.error(f"WebRTC session {session_id} not found")
                if self.verbose_logging:
                    self.logger.error("[VERBOSE] Session lookup failed:")
                    if webrtc_signaling:
                        self.logger.error(f"  Active sessions: {list(webrtc_signaling.sessions)}")
                    else:
                        self.logger.error("  No signaling server provided")
                return None

            # Get source extension from session
            from_extension = session.extension

            if self.verbose_logging:
                self.logger.info("[VERBOSE] Session found:")
                self.logger.info(f"  From Extension: {from_extension}")
                self.logger.info(f"  Session State: {session.state}")
                self.logger.info(f"  Has Local SDP: {session.local_sdp is not None}")

            # Verify target extension exists or is a valid dialplan pattern
            # Check if it's a regular extension in the registry
            target_ext_obj = self.pbx_core.extension_registry.get_extension(target_extension)

            # If not in registry, check if it matches a valid dialplan pattern
            # (voicemail, auto attendant, conference, etc.)
            is_valid_dialplan = False
            if not target_ext_obj:
                is_valid_dialplan = self.pbx_core._check_dialplan(target_extension)

            if not target_ext_obj and not is_valid_dialplan:
                self.logger.error(
                    f"Target extension {target_extension} not found and doesn't match any dialplan pattern"
                )
                if self.verbose_logging:
                    self.logger.error("[VERBOSE] Extension validation failed:")
                    all_exts = (
                        list(self.pbx_core.extension_registry.extensions)
                        if hasattr(self.pbx_core.extension_registry, "extensions")
                        else []
                    )
                    self.logger.error(
                        f"  Available extensions: {all_exts[:10]}{'...' if len(all_exts) > 10 else ''}"
                    )
                    self.logger.error(f"  Dialplan check result: {is_valid_dialplan}")
                return None

            if self.verbose_logging:
                self.logger.info("[VERBOSE] Target extension validated:")
                self.logger.info(f"  Extension: {target_extension}")
                if target_ext_obj:
                    self.logger.info(f"  Extension Object: {target_ext_obj}")
                    self.logger.info("  Found in registry: Yes")
                else:
                    self.logger.info("  Extension Object: None")
                    self.logger.info("  Found in registry: No")
                    self.logger.info("  Matches dialplan pattern: Yes")

            # 2. Create SIP call through CallManager
            call_id = str(uuid.uuid4())

            if self.verbose_logging:
                self.logger.info("[VERBOSE] Creating call through CallManager:")
                self.logger.info(f"  Call ID: {call_id}")
                self.logger.info(f"  From: {from_extension}")
                self.logger.info(f"  To: {target_extension}")

            call = self.pbx_core.call_manager.create_call(
                call_id=call_id, from_extension=from_extension, to_extension=target_extension
            )

            if self.verbose_logging:
                self.logger.info(f"[VERBOSE] Call object created: {call}")

            # Start the call
            call.start()

            if self.verbose_logging:
                self.logger.info("[VERBOSE] Call started successfully")

            # 3. Bridge WebRTC and SIP media
            # Get WebRTC SDP from session
            if session.local_sdp:
                if self.verbose_logging:
                    self.logger.info("[VERBOSE] Processing WebRTC SDP for media bridge:")
                    self.logger.info(f"  SDP length: {len(session.local_sdp)} bytes")

                # Convert WebRTC SDP to SIP-compatible SDP
                sip_sdp = self.webrtc_to_sip_sdp(session.local_sdp)

                if self.verbose_logging:
                    self.logger.info("[VERBOSE] Converted WebRTC SDP to SIP SDP")
                    self.logger.info(f"  SIP SDP length: {len(sip_sdp)} bytes")

                # Parse SDP to get RTP info
                from pbx.sip.sdp import SDPSession

                sdp = SDPSession()
                sdp.parse(sip_sdp)
                audio_info = sdp.get_audio_info()

                if audio_info:
                    # Store RTP endpoint info in call
                    call.caller_rtp = {
                        "address": audio_info.get("address"),
                        "port": audio_info.get("port"),
                        "formats": audio_info.get("formats", []),
                    }
                    self.logger.debug(f"WebRTC RTP endpoint: {call.caller_rtp}")

                    if self.verbose_logging:
                        self.logger.info("[VERBOSE] RTP endpoint info extracted:")
                        self.logger.info(f"  Address: {audio_info.get('address')}")
                        self.logger.info(f"  Port: {audio_info.get('port')}")
                        self.logger.info(f"  Formats: {audio_info.get('formats', [])}")
                elif self.verbose_logging:
                    self.logger.warning("[VERBOSE] No audio info found in SDP")
            elif self.verbose_logging:
                self.logger.warning("[VERBOSE] No local SDP available in session")

            # 4. Associate call ID with WebRTC session
            if webrtc_signaling:
                webrtc_signaling.set_session_call_id(session_id, call_id)
                if self.verbose_logging:
                    self.logger.info(
                        f"[VERBOSE] Associated call ID {call_id} with session {session_id}"
                    )

            # 5. set up RTP relay for media path
            rtp_ports = self.pbx_core.rtp_relay.allocate_relay(call_id)
            if rtp_ports:
                call.rtp_ports = rtp_ports
                if self.verbose_logging:
                    self.logger.info(f"[VERBOSE] RTP ports allocated: {rtp_ports}")
            else:
                self.logger.error(f"Failed to allocate RTP ports for WebRTC call {call_id}")
                return None

            # 6. Send SIP INVITE to the target phone (regular extension calls)
            #    Special extensions (AA, voicemail) are handled by the PBX
            #    call router when the INVITE is processed.
            dest_ext_obj = self.pbx_core.extension_registry.get(target_extension)
            if dest_ext_obj and dest_ext_obj.address:
                # Regular SIP phone – send INVITE with PBX RTP endpoint
                from pbx.sip.message import SIPMessageBuilder
                from pbx.sip.sdp import SDPBuilder

                server_ip = self.pbx_core._get_server_ip()
                sip_port = self.pbx_core.config.get("server.sip_port", 5060)
                dtmf_pt = self.pbx_core._get_dtmf_payload_type()
                ilbc_mode = self.pbx_core._get_ilbc_mode()

                callee_sdp = SDPBuilder.build_audio_sdp(
                    server_ip,
                    rtp_ports[0],
                    session_id=call_id,
                    codecs=None,  # default codecs
                    dtmf_payload_type=dtmf_pt,
                    ilbc_mode=ilbc_mode,
                )

                from_uri = f"sip:{from_extension}@{server_ip}:{sip_port}"
                to_uri = f"sip:{target_extension}@{server_ip}:{sip_port}"

                invite = SIPMessageBuilder.build_request(
                    method="INVITE",
                    uri=f"sip:{target_extension}@{server_ip}",
                    from_addr=f"<{from_uri}>",
                    to_addr=f"<{to_uri}>",
                    call_id=call_id,
                    cseq=1,
                    body=callee_sdp,
                )
                invite.set_header(
                    "Via",
                    f"SIP/2.0/UDP {server_ip}:{sip_port};branch=z9hG4bK{uuid.uuid4().hex[:16]}",
                )
                invite.set_header(
                    "Contact", f"<sip:{from_extension}@{server_ip}:{sip_port}>"
                )
                invite.set_header("Content-type", "application/sdp")

                # Store invite so handle_callee_answer can send 200 OK
                call.original_invite = invite
                call.caller_addr = None  # WebRTC caller — no SIP address

                # Mark that this is a WebRTC-originated call so
                # handle_callee_answer knows to use the media bridge
                # instead of sending a SIP 200 OK to the caller.
                call.webrtc_session_id = session.session_id

                self.pbx_core.sip_server._send_message(
                    invite.build(), dest_ext_obj.address
                )
                call.callee_addr = dest_ext_obj.address
                self.logger.info(
                    f"Sent SIP INVITE to {target_extension} at {dest_ext_obj.address}"
                )

                # Start no-answer timer
                no_answer_timeout = self.pbx_core.config.get("voicemail.no_answer_timeout", 30)
                call.no_answer_timer = threading.Timer(
                    no_answer_timeout,
                    self.pbx_core._call_router._handle_no_answer,
                    args=(call_id,),
                )
                call.no_answer_timer.start()
            else:
                self.logger.warning(
                    f"Target {target_extension} has no SIP address; "
                    "call created but no INVITE sent"
                )

            self.logger.info(
                f"Call {call_id} initiated from WebRTC session {session_id} to {target_extension}"
            )

            if self.verbose_logging:
                self.logger.info("[VERBOSE] ===== Call initiation SUCCESSFUL =====")

            return call_id

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error initiating call from WebRTC: {e}")
            if self.verbose_logging:
                self.logger.error("[VERBOSE] ===== Call initiation FAILED =====")
                self.logger.error(f"[VERBOSE] Exception type: {type(e).__name__}")
                self.logger.error(f"[VERBOSE] Exception message: {e!s}")
            import traceback

            self.logger.debug(traceback.format_exc())
            if self.verbose_logging:
                self.logger.error(f"[VERBOSE] Full traceback:\n{traceback.format_exc()}")
            return None

    def receive_call(
        self,
        session_id: str,
        call_id: str,
        caller_sdp: str | None = None,
        webrtc_signaling: Any | None = None,
    ) -> bool:
        """
        Route incoming call to WebRTC client

        Args:
            session_id: WebRTC session ID
            call_id: Incoming call ID
            caller_sdp: SDP from caller (optional)
            webrtc_signaling: WebRTCSignalingServer instance (optional)

        Returns:
            True if call was routed successfully
        """
        if not self.pbx_core:
            self.logger.error("PBX core not available for call routing")
            return False

        self.logger.info(f"Routing incoming call {call_id} to WebRTC session {session_id}")

        try:
            # 1. Get WebRTC session
            session = None
            if webrtc_signaling:
                session = webrtc_signaling.get_session(session_id)

            if not session:
                self.logger.error(f"WebRTC session {session_id} not found")
                return False

            # Get the call from CallManager
            call = self.pbx_core.call_manager.get_call(call_id)
            if not call:
                self.logger.error(f"Call {call_id} not found")
                return False

            # 2. Prepare WebRTC-compatible SDP for client notification
            if caller_sdp:
                # Convert SIP SDP to WebRTC-compatible SDP
                webrtc_sdp = self.sip_to_webrtc_sdp(caller_sdp)

                # Store the remote SDP in session
                session.remote_sdp = webrtc_sdp
                session.state = "ringing"
                session.update_activity()

                self.logger.debug(f"Converted SIP SDP to WebRTC SDP for session {session_id}")

            # 3. Associate call with session for media bridging when answered
            if webrtc_signaling:
                webrtc_signaling.set_session_call_id(session_id, call_id)
                # Store additional metadata for call routing
                webrtc_signaling.set_session_metadata(session_id, "incoming_call", True)
                webrtc_signaling.set_session_metadata(
                    session_id, "caller_extension", call.from_extension
                )

            # Update call state
            call.ring()

            self.logger.info(f"Incoming call {call_id} routed to WebRTC session {session_id}")
            self.logger.info(
                "Client should be notified via signaling channel to accept/reject call"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error routing incoming call to WebRTC: {e}")
            import traceback

            self.logger.debug(traceback.format_exc())
            return False

    def answer_call(self, session_id: str, webrtc_signaling: Any | None = None) -> bool:
        """
        Handle WebRTC client answering an incoming call

        Args:
            session_id: WebRTC session ID
            webrtc_signaling: WebRTCSignalingServer instance (optional)

        Returns:
            True if call was answered successfully
        """
        if not self.pbx_core:
            self.logger.error("PBX core not available")
            return False

        try:
            # Get WebRTC session
            session = None
            if webrtc_signaling:
                session = webrtc_signaling.get_session(session_id)

            if not session or not session.call_id:
                self.logger.error(f"No call associated with session {session_id}")
                return False

            # Get the call
            call = self.pbx_core.call_manager.get_call(session.call_id)
            if not call:
                self.logger.error(f"Call {session.call_id} not found")
                return False

            # Bridge WebRTC and SIP media
            if session.local_sdp:
                # Parse WebRTC SDP to get RTP endpoint
                from pbx.sip.sdp import SDPSession

                sdp = SDPSession()
                sdp.parse(session.local_sdp)
                audio_info = sdp.get_audio_info()

                if audio_info:
                    # Store WebRTC RTP endpoint in call
                    call.callee_rtp = {
                        "address": audio_info.get("address"),
                        "port": audio_info.get("port"),
                        "formats": audio_info.get("formats", []),
                    }
                    self.logger.debug(f"WebRTC answered RTP endpoint: {call.callee_rtp}")

            # Connect the call
            call.connect()
            session.state = "connected"
            session.update_activity()

            self.logger.info(f"WebRTC session {session_id} answered call {session.call_id}")
            return True

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error answering call from WebRTC: {e}")
            import traceback

            self.logger.debug(traceback.format_exc())
            return False
