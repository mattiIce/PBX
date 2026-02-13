"""
WebRTC Browser Calling Support
Provides WebRTC signaling and integration with PBX SIP infrastructure
"""

import os
import threading
import time
import uuid
from datetime import datetime, timezone
from collections.abc import Callable

from pbx.utils.logger import get_logger


class WebRTCSession:
    """Represents a WebRTC session"""

    def __init__(self, session_id: str, extension: str, peer_connection_id: str | None = None):
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
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.state = "new"  # new, connecting, connected, disconnected
        self.local_sdp = None
        self.remote_sdp = None
        self.ice_candidates = []
        self.call_id = None
        self.metadata = {}

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)

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

    def __init__(self, config=None, pbx_core=None):
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

        if self.enabled:
            self.logger.info("WebRTC signaling server enabled")
            if self.verbose_logging:
                self.logger.info("WebRTC verbose logging ENABLED")
                self.logger.info(f"  STUN servers: {self.stun_servers}")
                self.logger.info(f"  TURN servers: {len(self.turn_servers)} configured")
                self.logger.info(f"  Session timeout: {self.session_timeout}s")
                self.logger.info(
                    f"  ICE transport policy: {self.ice_transport_policy}"
                )
            self._start_cleanup_thread()
        else:
            self.logger.info("WebRTC signaling server disabled")

    def _get_config(self, key: str, default=None):
        """Get configuration value"""
        if hasattr(self.config, "get"):
            return self.config.get(key, default)
        return default

    def _start_cleanup_thread(self):
        """Start session cleanup thread"""
        self.running = True
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker, name="WebRTCCleanup", daemon=True
        )
        self.cleanup_thread.start()
        self.logger.info("Started WebRTC session cleanup thread")

    def stop(self):
        """Stop the WebRTC signaling server"""
        self.logger.info("Stopping WebRTC signaling server...")
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        self.logger.info("WebRTC signaling server stopped")

    def _cleanup_worker(self):
        """Worker thread for cleaning up stale sessions"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            self._cleanup_stale_sessions()

    def _cleanup_stale_sessions(self):
        """Remove stale sessions that have timed out"""
        with self.lock:
            now = datetime.now(timezone.utc)
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

    def _log_session_creation(self, session_id: str, extension: str, session):
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

    def _create_virtual_webrtc_extension(self, extension: str):
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
                    success, stored_mac = self.pbx_core.registered_phones_db.register_phone(
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
                    f"[VERBOSE] Available extensions: {list(self.pbx_core.extension_registry.extensions.keys())[:10]}"
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

    def handle_offer(self, session_id: str, sdp: str) -> bool:
        """
        Handle SDP offer from client

        Args:
            session_id: Session identifier
            sdp: SDP offer

        Returns:
            True if offer was accepted
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.warning(f"Received offer for unknown session: {session_id}")
            if self.verbose_logging:
                self.logger.warning("[VERBOSE] Unknown session details:")
                self.logger.warning(f"  Session ID: {session_id}")
                self.logger.warning(
                    f"  Active sessions: {list(self.sessions.keys())}"
                )
            return False

        session.local_sdp = sdp
        session.state = "connecting"
        session.update_activity()

        self.logger.info(f"Received SDP offer for session: {session_id}")
        self.logger.debug(f"SDP offer: {sdp[:100]}...")

        if self.verbose_logging:
            self.logger.info("[VERBOSE] SDP offer received:")
            self.logger.info(f"  Session ID: {session_id}")
            self.logger.info(f"  Extension: {session.extension}")
            self.logger.info("  State transition: -> connecting")
            self.logger.info(f"  SDP length: {len(sdp)} bytes")
            self.logger.info(f"  Full SDP offer:\n{sdp}")

        if self.on_offer_received:
            try:
                self.on_offer_received(session, sdp)
            except Exception as e:
                self.logger.error(f"Error in offer received callback: {e}")

        return True

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
            self.logger.info(
                f"  Candidate: {candidate.get('candidate', 'N/A')}"
            )
            self.logger.info(f"  SDP MID: {candidate.get('sdpMid', 'N/A')}")
            self.logger.info(f"  SDP M-Line Index: {candidate.get('sdpMLineIndex', 'N/A')}")
            self.logger.info(f"  Total candidates for session: {len(session.ice_candidates)}")

        return True

    def get_ice_servers_config(self) -> dict:
        """
        Get ICE servers configuration for client

        Returns:
            Dictionary with ICE servers configuration, codec preferences,
            audio settings, and DTMF configuration (matches Zultys ZIP33G)
        """
        ice_servers = []

        # Add STUN servers
        for stun_url in self.stun_servers:
            ice_servers.append({"urls": stun_url})

        # Add TURN servers
        for turn_config in self.turn_servers:
            ice_servers.append(
                {
                    "urls": turn_config.get("url"),
                    "username": turn_config.get("username"),
                    "credential": turn_config.get("credential"),
                }
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

    def set_session_metadata(self, session_id: str, key: str, value) -> bool:
        """set metadata for a session"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.metadata[key] = value
        session.update_activity()
        return True

    def get_session_metadata(self, session_id: str, key: str, default=None):
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

    def __init__(self, pbx_core=None):
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
        self, sip_sdp: str, ice_ufrag: str = None, ice_pwd: str = None, fingerprint: str = None
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
        self, session_id: str, target_extension: str, webrtc_signaling=None
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
                        self.logger.error(
                            f"  Active sessions: {list(webrtc_signaling.sessions.keys())}"
                        )
                    else:
                        self.logger.error("  No signaling server provided")
                return None

            # Get source extension from session
            from_extension = session.extension

            if self.verbose_logging:
                self.logger.info("[VERBOSE] Session found:")
                self.logger.info(f"  From Extension: {from_extension}")
                self.logger.info(f"  Session State: {session.state}")
                self.logger.info(
                    f"  Has Local SDP: {session.local_sdp is not None}"
                )

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
                        list(self.pbx_core.extension_registry.extensions.keys())
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
                    self.logger.debug(
                        f"WebRTC RTP endpoint: {call.caller_rtp}"
                    )

                    if self.verbose_logging:
                        self.logger.info("[VERBOSE] RTP endpoint info extracted:")
                        self.logger.info(
                            f"  Address: {audio_info.get('address')}"
                        )
                        self.logger.info(f"  Port: {audio_info.get('port')}")
                        self.logger.info(
                            f"  Formats: {audio_info.get('formats', [])}"
                        )
                else:
                    if self.verbose_logging:
                        self.logger.warning("[VERBOSE] No audio info found in SDP")
            else:
                if self.verbose_logging:
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

            # 6. Handle special extensions (auto attendant, voicemail, etc.)
            # Check if target is auto attendant
            if (
                self.pbx_core.auto_attendant
                and target_extension == self.pbx_core.auto_attendant.get_extension()
            ):
                if self.verbose_logging:
                    self.logger.info("[VERBOSE] Target is auto attendant, starting session")

                # Mark as auto attendant call
                call.auto_attendant_active = True

                # Start auto attendant session
                aa_session = self.pbx_core.auto_attendant.start_session(call_id, from_extension)
                call.aa_session = aa_session

                if self.verbose_logging:
                    self.logger.info("[VERBOSE] Auto attendant session started")
                    self.logger.info(
                        f"[VERBOSE] Initial action: {aa_session.get('action')}"
                    )

                # set up RTP player to play the welcome message
                if aa_session.get("action") == "play" and aa_session.get("file"):
                    audio_file = aa_session.get("file")

                    # Get caller's RTP endpoint from call
                    if call.caller_rtp and isinstance(call.caller_rtp, dict):
                        # Validate RTP info has required fields
                        caller_address = call.caller_rtp.get("address")
                        caller_port = call.caller_rtp.get("port")

                        if caller_address and caller_port:
                            from pbx.rtp.handler import RTPPlayer

                            # Create RTP player to send audio to WebRTC client
                            player = RTPPlayer(
                                local_port=call.rtp_ports[0] if call.rtp_ports else None,
                                remote_host=caller_address,
                                remote_port=caller_port,
                                call_id=call_id,
                            )

                            # Store player reference in call for cleanup
                            call.rtp_player = player

                            # Start the RTP player
                            if player.start():
                                # Play the audio file
                                if audio_file and os.path.exists(audio_file):
                                    player.play_file(audio_file)
                                    self.logger.info(
                                        f"Auto attendant playing welcome message for call {call_id}"
                                    )
                                else:
                                    self.logger.warning(f"Audio file not found: {audio_file}")
                            else:
                                self.logger.error(
                                    f"Failed to start RTP player for auto attendant call {call_id}"
                                )
                        else:
                            self.logger.warning(
                                f"Incomplete caller RTP info (missing address or port) for call {call_id}"
                            )
                    else:
                        self.logger.warning(
                            f"No caller RTP info available for auto attendant call {call_id}"
                        )

            # Check if target is voicemail access (*xxxx pattern)
            # Use regex to match dialplan pattern for consistency
            import re

            voicemail_pattern = r"^\*[0-9]{3,4}$"
            if re.match(voicemail_pattern, target_extension):
                if self.verbose_logging:
                    self.logger.info(f"[VERBOSE] Target is voicemail access: {target_extension}")

                # Mark as voicemail access call
                call.voicemail_access = True
                target_mailbox = target_extension[1:]  # Remove * prefix
                call.voicemail_extension = target_mailbox

                self.logger.info(
                    f"Voicemail access pattern detected for mailbox {target_mailbox} from call {call_id}"
                )

                # ============================================================
                # RTP SETUP FOR WEBRTC VOICEMAIL ACCESS - BIDIRECTIONAL AUDIO
                # ============================================================
                # This mirrors the pattern used for auto attendant and regular
                # SIP phone voicemail access. Sets up full-duplex audio channel.
                # ============================================================

                # Verify target mailbox exists
                if self.pbx_core.voicemail_system:
                    mailbox = self.pbx_core.voicemail_system.get_mailbox(target_mailbox)

                    if self.verbose_logging:
                        self.logger.info("[VERBOSE] Setting up voicemail IVR for WebRTC")
                        self.logger.info(f"  Mailbox: {target_mailbox}")
                        self.logger.info(f"  Call ID: {call_id}")

                    # Create VoicemailIVR for this call
                    from pbx.features.voicemail import VoicemailIVR

                    voicemail_ivr = VoicemailIVR(self.pbx_core.voicemail_system, target_mailbox)
                    call.voicemail_ivr = voicemail_ivr

                    # Mark call as connected (similar to regular SIP voicemail
                    # access)
                    call.connect()
                    if self.verbose_logging:
                        self.logger.info(
                            f"[VERBOSE] Call marked as connected, state: {call.state}"
                        )

                    # Start CDR record for analytics
                    if hasattr(self.pbx_core, "cdr_system") and self.pbx_core.cdr_system:
                        self.pbx_core.cdr_system.start_record(
                            call_id, from_extension, target_extension
                        )
                        if self.verbose_logging:
                            self.logger.info("[VERBOSE] CDR record started")

                    # Get caller's RTP endpoint from call
                    if call.caller_rtp and isinstance(call.caller_rtp, dict):
                        caller_address = call.caller_rtp.get("address")
                        caller_port = call.caller_rtp.get("port")

                        if caller_address and caller_port and call.rtp_ports:
                            if self.verbose_logging:
                                self.logger.info(
                                    "[VERBOSE] Starting voicemail IVR session with RTP"
                                )
                                self.logger.info(f"  Caller RTP: {caller_address}:{caller_port}")
                                self.logger.info(
                                    f"  Local RTP port: {call.rtp_ports[0]}"
                                )

                            # Start voicemail IVR session in a separate thread
                            # This handles audio prompts and DTMF input, just
                            # like regular phones
                            import threading

                            ivr_thread = threading.Thread(
                                target=self.pbx_core._voicemail_ivr_session,
                                args=(call_id, call, mailbox, voicemail_ivr),
                                daemon=True,
                            )
                            ivr_thread.start()

                            self.logger.info(
                                f"WebRTC voicemail IVR session started for call {call_id}"
                            )
                            if self.verbose_logging:
                                self.logger.info(
                                    "[VERBOSE] Voicemail IVR thread started successfully"
                                )
                        else:
                            self.logger.warning(
                                f"Incomplete RTP info for WebRTC voicemail call {call_id}"
                            )
                            if self.verbose_logging:
                                self.logger.warning("[VERBOSE] Missing RTP data:")
                                self.logger.warning(f"  caller_address: {caller_address}")
                                self.logger.warning(f"  caller_port: {caller_port}")
                                self.logger.warning(f"  rtp_ports: {call.rtp_ports}")
                    else:
                        self.logger.warning(
                            f"No caller RTP info available for WebRTC voicemail call {call_id}"
                        )
                        if self.verbose_logging:
                            self.logger.warning(
                                f"[VERBOSE] caller_rtp: {call.caller_rtp}"
                            )
                else:
                    self.logger.error(f"Voicemail system not available for WebRTC call {call_id}")
                    if self.verbose_logging:
                        self.logger.error("[VERBOSE] pbx_core.voicemail_system is None")

            # For regular extension calls, the call is set up
            # When the target extension answers, the CallManager will bridge
            # the media

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
                self.logger.error(
                    f"[VERBOSE] Exception type: {type(e).__name__}"
                )
                self.logger.error(f"[VERBOSE] Exception message: {str(e)}")
            import traceback

            self.logger.debug(traceback.format_exc())
            if self.verbose_logging:
                self.logger.error(
                    f"[VERBOSE] Full traceback:\n{traceback.format_exc()}"
                )
            return None

    def receive_call(
        self, session_id: str, call_id: str, caller_sdp: str = None, webrtc_signaling=None
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

    def answer_call(self, session_id: str, webrtc_signaling=None) -> bool:
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
                    self.logger.debug(
                        f"WebRTC answered RTP endpoint: {call.callee_rtp}"
                    )

            # Connect the call
            call.connect()
            session.state = "connected"
            session.update_activity()

            self.logger.info(
                f"WebRTC session {session_id} answered call {session.call_id}"
            )
            return True

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error answering call from WebRTC: {e}")
            import traceback

            self.logger.debug(traceback.format_exc())
            return False
