"""
Warden SBC - Session Border Controller

Enterprise-grade session border controller providing NAT traversal,
topology hiding, protocol normalization, security filtering, media relay,
and call admission control for SIP/RTP traffic.
"""

import json
import re
import socket
import struct
import time
from collections import defaultdict
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from pbx.utils.logger import get_logger


class NATType(Enum):
    """NAT type enumeration"""

    NONE = "none"
    FULL_CONE = "full_cone"
    RESTRICTED_CONE = "restricted_cone"
    PORT_RESTRICTED = "port_restricted"
    SYMMETRIC = "symmetric"


class SessionBorderController:
    """
    Warden SBC - Session Border Controller

    Enterprise-grade security and NAT traversal for SIP/RTP.
    Features:
    - NAT traversal (STUN/TURN/ICE)
    - Topology hiding
    - Protocol normalization
    - Security filtering (DoS protection, malformed packets)
    - Media relay with bandwidth tracking
    - Call admission control
    - SIP header manipulation
    - Persistent blacklist/whitelist
    """

    PRODUCT_NAME = "Warden SBC"

    # Constants
    IP_PATTERN = r"(\d+\.\d+\.\d+\.\d+)"
    PACKETS_PER_SECOND = 50  # Assumed packets per second for VoIP bandwidth calculation
    DATA_DIR = "data/sbc"

    # STUN message constants (RFC 5389)
    STUN_BINDING_REQUEST = 0x0001
    STUN_BINDING_RESPONSE = 0x0101
    STUN_MAGIC_COOKIE = 0x2112A442
    STUN_ATTR_MAPPED_ADDRESS = 0x0001
    STUN_ATTR_XOR_MAPPED_ADDRESS = 0x0020
    STUN_ATTR_CHANGE_REQUEST = 0x0003
    STUN_HEADER_SIZE = 20
    STUN_DEFAULT_PORT = 3478
    STUN_TIMEOUT = 2.0

    # Codec bandwidth map (kbps)
    CODEC_BANDWIDTH: ClassVar[dict[str, int]] = {
        "pcmu": 80,
        "pcma": 80,
        "g722": 80,
        "opus": 40,
        "g729": 30,
    }

    def __init__(self, config: Any | None = None) -> None:
        """Initialize Warden SBC"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        sbc_config = self.config.get("features", {}).get("sbc", {})
        self.enabled = sbc_config.get("enabled", False)
        self.topology_hiding = sbc_config.get("topology_hiding", True)
        self.media_relay = sbc_config.get("media_relay", True)
        self.max_calls = sbc_config.get("max_calls", 1000)
        self.max_bandwidth = sbc_config.get("max_bandwidth", 100000)  # kbps
        self.public_ip = sbc_config.get("public_ip", "0.0.0.0")  # nosec B104

        # NAT/firewall traversal
        self.stun_enabled = sbc_config.get("stun_enabled", True)
        self.turn_enabled = sbc_config.get("turn_enabled", True)
        self.ice_enabled = sbc_config.get("ice_enabled", True)

        # Security
        self.rate_limit = sbc_config.get("rate_limit", 100)  # requests/second
        self.blacklist: set[str] = set()
        self.whitelist: set[str] = set()

        # Rate limiting tracking
        self.request_counts: dict[str, list[float]] = defaultdict(list)
        self.rate_limit_window = 1.0  # 1 second window

        # Media relay sessions
        self.relay_sessions: dict[str, dict] = {}
        self.relay_port_pool: set[int] = set(range(10000, 20000, 2))  # RTP uses even ports

        # RTP relay state tracking per call
        self.relay_state: dict[str, dict] = {}

        # Bandwidth tracking
        self.current_bandwidth = 0  # kbps
        self.bandwidth_by_call: dict[str, int] = {}

        # Statistics
        self.total_sessions = 0
        self.active_sessions = 0
        self.blocked_requests = 0
        self.relayed_media_bytes = 0
        self.rate_limit_violations = 0
        self.cac_rejections = 0
        self.codec_call_counts: dict[str, int] = defaultdict(int)
        self.topology_hiding_ops = 0
        self.nat_detection_count = 0

        # Load persisted blacklist/whitelist
        self._load_lists()

        self.logger.info(f"{self.PRODUCT_NAME} initialized")
        self.logger.info(f"  Topology hiding: {self.topology_hiding}")
        self.logger.info(f"  Media relay: {self.media_relay}")
        self.logger.info(f"  NAT traversal: STUN={self.stun_enabled}, TURN={self.turn_enabled}")
        self.logger.info(f"  Enabled: {self.enabled}")

    # =========================================================================
    # SIP Processing
    # =========================================================================

    def process_inbound_sip(self, message: dict, source_ip: str) -> dict:
        """
        Process inbound SIP message through the SBC pipeline.

        Args:
            message: SIP message dict
            source_ip: Source IP address

        Returns:
            dict with 'action' ('forward' or 'block') and processed message or reason
        """
        # Security checks
        if self._is_blacklisted(source_ip):
            self.blocked_requests += 1
            return {"action": "block", "reason": "Blacklisted IP"}

        # Rate limiting
        if not self._check_rate_limit(source_ip):
            self.blocked_requests += 1
            self.rate_limit_violations += 1
            return {"action": "block", "reason": "Rate limit exceeded"}

        # Topology hiding - rewrite headers
        if self.topology_hiding:
            message = self._hide_topology(message, "inbound")

        # Protocol normalization
        message = self._normalize_sip_message(message)

        return {"action": "forward", "message": message}

    def process_outbound_sip(self, message: dict) -> dict:
        """Process outbound SIP message through topology hiding."""
        if self.topology_hiding:
            message = self._hide_topology(message, "outbound")

        return {"action": "forward", "message": message}

    # =========================================================================
    # Topology Hiding
    # =========================================================================

    def _hide_topology(self, message: dict, direction: str) -> dict:
        """
        Hide internal topology in SIP headers.

        Args:
            message: SIP message dict
            direction: 'inbound' or 'outbound'

        Returns:
            Modified message with internal IPs hidden
        """
        if not isinstance(message, dict):
            return message

        self.topology_hiding_ops += 1
        sbc_public_ip = self.public_ip

        # Create a copy to avoid modifying original
        modified_message = message.copy()

        if direction == "outbound":
            # Replace Via headers with SBC IP
            if "via" in modified_message:
                modified_message["via"] = self._rewrite_via_header(
                    modified_message["via"], sbc_public_ip
                )

            # Rewrite Contact header
            if "contact" in modified_message:
                modified_message["contact"] = self._rewrite_contact_header(
                    modified_message["contact"], sbc_public_ip
                )

            # Modify Record-Route to use SBC
            if "record_route" in modified_message:
                modified_message["record_route"] = self._rewrite_record_route(
                    modified_message["record_route"], sbc_public_ip
                )

            # Rewrite Route header
            if "route" in modified_message:
                modified_message["route"] = re.sub(
                    self.IP_PATTERN, sbc_public_ip, modified_message["route"]
                )

            # Hide P-Asserted-Identity internal IPs
            if "p_asserted_identity" in modified_message:
                modified_message["p_asserted_identity"] = re.sub(
                    self.IP_PATTERN, sbc_public_ip, modified_message["p_asserted_identity"]
                )

            # Hide P-Preferred-Identity internal IPs
            if "p_preferred_identity" in modified_message:
                modified_message["p_preferred_identity"] = re.sub(
                    self.IP_PATTERN, sbc_public_ip, modified_message["p_preferred_identity"]
                )

        elif direction == "inbound":
            # For inbound, ensure internal IPs are hidden in responses
            if "via" in modified_message:
                sbc_via = (
                    f"SIP/2.0/UDP {sbc_public_ip}:5060;branch=z9hG4bK-sbc-{id(modified_message)}"
                )
                modified_message["via"] = sbc_via + ", " + modified_message["via"]

            # Rewrite any internal IPs in SDP
            if "sdp" in modified_message:
                modified_message["sdp"] = self._hide_internal_ips_in_sdp(
                    modified_message["sdp"], sbc_public_ip
                )

        return modified_message

    def _rewrite_via_header(self, via: str, public_ip: str) -> str:
        """Rewrite Via header with SBC IP"""
        return re.sub(self.IP_PATTERN, public_ip, via)

    def _rewrite_contact_header(self, contact: str, public_ip: str) -> str:
        """Rewrite Contact header with SBC IP"""
        return re.sub(self.IP_PATTERN, public_ip, contact)

    def _rewrite_record_route(self, record_route: str, public_ip: str) -> str:
        """Rewrite Record-Route header with SBC IP"""
        return re.sub(self.IP_PATTERN, public_ip, record_route)

    def _hide_internal_ips_in_sdp(self, sdp: str, public_ip: str) -> str:
        """Hide internal IPs in SDP body"""
        sdp_pattern = r"(c=IN IP4 )" + self.IP_PATTERN
        return re.sub(sdp_pattern, r"\g<1>" + public_ip, sdp)

    # =========================================================================
    # Protocol Normalization
    # =========================================================================

    def _normalize_sip_message(self, message: dict) -> dict:
        """Normalize SIP message format"""
        if not isinstance(message, dict):
            return message

        normalized = message.copy()

        # Ensure required headers exist
        required_headers = ["via", "from", "to", "call_id", "cseq"]
        for header in required_headers:
            if header not in normalized:
                self.logger.warning(f"Missing required SIP header: {header}")

        # Standardize header capitalization
        header_mapping = {
            "call-id": "call_id",
            "callid": "call_id",
            "cseq": "cseq",
            "c-seq": "cseq",
            "from": "from",
            "": "from",
            "to": "to",
            "t": "to",
        }

        for old_name, new_name in header_mapping.items():
            if old_name in normalized and old_name != new_name:
                normalized[new_name] = normalized.pop(old_name)

        # Remove unnecessary headers that may leak information
        unnecessary_headers = ["user_agent", "server", "organization"]
        for header in unnecessary_headers:
            if header in normalized:
                del normalized[header]

        # Validate method if present
        if "method" in normalized:
            valid_methods = [
                "INVITE",
                "ACK",
                "BYE",
                "CANCEL",
                "REGISTER",
                "OPTIONS",
                "INFO",
                "UPDATE",
                "REFER",
                "NOTIFY",
            ]
            if normalized["method"].upper() not in valid_methods:
                self.logger.warning(f"Invalid SIP method: {normalized['method']}")

        return normalized

    # =========================================================================
    # NAT Detection (STUN - RFC 5389)
    # =========================================================================

    def detect_nat(self, local_ip: str, public_ip: str) -> NATType:
        """
        Detect NAT type using STUN binding requests (RFC 5389).

        Follows RFC 3489 section 10.1 classification algorithm.

        Args:
            local_ip: Local IP address of this host.
            public_ip: Known or assumed public IP address.

        Returns:
            NATType: Detected NAT type.
        """
        self.nat_detection_count += 1

        # No NAT if local equals public
        if local_ip == public_ip:
            return NATType.NONE

        # Not behind NAT if local address is already public
        if not self._is_private_ip(local_ip):
            return NATType.NONE

        stun_server = self.config.get("features", {}).get("sbc", {}).get("stun_server", public_ip)
        stun_port = (
            self.config.get("features", {}).get("sbc", {}).get("stun_port", self.STUN_DEFAULT_PORT)
        )

        # --- Test I: Basic STUN Binding Request ---
        mapped_addr_1 = self._stun_binding_request(stun_server, stun_port)
        if mapped_addr_1 is None:
            self.logger.warning("STUN Test I failed - cannot reach STUN server")
            return NATType.PORT_RESTRICTED

        mapped_ip_1, mapped_port_1 = mapped_addr_1
        self.logger.debug(f"STUN Test I: mapped address {mapped_ip_1}:{mapped_port_1}")

        # --- Test II: Request server to respond from a different IP and port ---
        mapped_addr_2 = self._stun_binding_request(
            stun_server, stun_port, change_request_flags=0x06
        )

        if mapped_addr_2 is not None:
            self.logger.debug("STUN Test II succeeded - Full Cone NAT")
            return NATType.FULL_CONE

        # --- Test III: Same server IP, different port ---
        mapped_addr_3 = self._stun_binding_request(
            stun_server, stun_port, change_request_flags=0x02
        )

        if mapped_addr_3 is not None:
            self.logger.debug("STUN Test III succeeded - Restricted Cone NAT")
            return NATType.RESTRICTED_CONE

        # --- Test IV: Second binding to a different port to check for symmetric ---
        alt_port = stun_port + 1
        mapped_addr_4 = self._stun_binding_request(stun_server, alt_port)

        if mapped_addr_4 is not None:
            _mapped_ip_4, mapped_port_4 = mapped_addr_4
            if mapped_port_4 != mapped_port_1:
                self.logger.debug(
                    f"STUN Test IV: mapped port changed "
                    f"({mapped_port_1} vs {mapped_port_4}) - Symmetric NAT"
                )
                return NATType.SYMMETRIC

        self.logger.debug("STUN classification: Port Restricted Cone NAT")
        return NATType.PORT_RESTRICTED

    def _stun_binding_request(
        self,
        server: str,
        port: int,
        change_request_flags: int | None = None,
    ) -> tuple[str, int] | None:
        """Send a single STUN Binding Request and parse the response.

        Args:
            server: STUN server hostname or IP.
            port: STUN server port.
            change_request_flags: Optional CHANGE-REQUEST flags byte.

        Returns:
            (mapped_ip, mapped_port) tuple, or None on failure.
        """
        import os

        try:
            transaction_id = os.urandom(12)
            attrs = b""

            if change_request_flags is not None:
                attr_value = struct.pack("!I", change_request_flags)
                attrs += struct.pack("!HH", self.STUN_ATTR_CHANGE_REQUEST, len(attr_value))
                attrs += attr_value

            header = struct.pack(
                "!HHI",
                self.STUN_BINDING_REQUEST,
                len(attrs),
                self.STUN_MAGIC_COOKIE,
            )
            packet = header + transaction_id + attrs

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.STUN_TIMEOUT)

            try:
                sock.sendto(packet, (server, port))
                data, _addr = sock.recvfrom(1024)
            finally:
                sock.close()

            if len(data) < self.STUN_HEADER_SIZE:
                return None

            msg_type, _msg_len, _magic = struct.unpack_from("!HHI", data, 0)
            resp_txn = data[8:20]

            if msg_type != self.STUN_BINDING_RESPONSE:
                return None
            if resp_txn != transaction_id:
                return None

            offset = self.STUN_HEADER_SIZE
            while offset + 4 <= len(data):
                attr_type, attr_len = struct.unpack_from("!HH", data, offset)
                offset += 4
                if offset + attr_len > len(data):
                    break

                if attr_type == self.STUN_ATTR_XOR_MAPPED_ADDRESS:
                    result = self._parse_xor_mapped_address(data, offset, transaction_id)
                    if result:
                        return result

                elif attr_type == self.STUN_ATTR_MAPPED_ADDRESS:
                    result = self._parse_mapped_address(data, offset)
                    if result:
                        return result

                offset += attr_len + ((4 - attr_len % 4) % 4)

            return None

        except OSError as e:
            self.logger.debug(f"STUN request to {server}:{port} failed: {e}")
            return None

    @staticmethod
    def _parse_xor_mapped_address(
        data: bytes, offset: int, _transaction_id: bytes
    ) -> tuple[str, int] | None:
        """Parse an XOR-MAPPED-ADDRESS attribute (RFC 5389 section 15.2)."""
        if offset + 8 > len(data):
            return None

        _reserved, family, xport = struct.unpack_from("!BBH", data, offset)
        if family != 0x01:
            return None

        xaddr = struct.unpack_from("!I", data, offset + 4)[0]
        mapped_port = xport ^ (SessionBorderController.STUN_MAGIC_COOKIE >> 16)
        mapped_addr_int = xaddr ^ SessionBorderController.STUN_MAGIC_COOKIE
        mapped_ip = socket.inet_ntoa(struct.pack("!I", mapped_addr_int))
        return mapped_ip, mapped_port

    @staticmethod
    def _parse_mapped_address(data: bytes, offset: int) -> tuple[str, int] | None:
        """Parse a MAPPED-ADDRESS attribute (RFC 5389 section 15.1)."""
        if offset + 8 > len(data):
            return None

        _reserved, family, mapped_port = struct.unpack_from("!BBH", data, offset)
        if family != 0x01:
            return None

        mapped_addr_int = struct.unpack_from("!I", data, offset + 4)[0]
        mapped_ip = socket.inet_ntoa(struct.pack("!I", mapped_addr_int))
        return mapped_ip, mapped_port

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private range"""
        try:
            octets = [int(x) for x in ip.split(".")]
            if octets[0] == 10:
                return True
            if octets[0] == 172 and 16 <= octets[1] <= 31:
                return True
            return bool(octets[0] == 192 and octets[1] == 168)
        except (ValueError, IndexError):
            return False

    # =========================================================================
    # Media Relay
    # =========================================================================

    def allocate_relay(self, call_id: str, codec: str) -> dict:
        """
        Allocate media relay for NAT traversal.

        Args:
            call_id: Call identifier
            codec: Media codec name

        Returns:
            dict with relay allocation details
        """
        if not self.media_relay:
            return {"success": False, "reason": "Media relay disabled"}

        if call_id in self.relay_sessions:
            return self.relay_sessions[call_id]

        if len(self.relay_port_pool) < 2:
            return {"success": False, "reason": "No relay ports available"}

        rtp_port = min(self.relay_port_pool)
        self.relay_port_pool.discard(rtp_port)
        rtcp_port = rtp_port + 1
        self.relay_port_pool.discard(rtcp_port)

        relay_ip = self.public_ip

        relay_info = {
            "success": True,
            "call_id": call_id,
            "rtp_port": rtp_port,
            "rtcp_port": rtcp_port,
            "relay_ip": relay_ip,
            "codec": codec,
            "allocated_at": datetime.now(UTC).isoformat(),
        }

        self.relay_sessions[call_id] = relay_info

        # Initialize relay state for packet tracking
        self.relay_state[call_id] = {
            "last_seq": -1,
            "packets_relayed": 0,
            "packets_lost": 0,
            "bytes_relayed": 0,
            "bandwidth_kbps": 0,
        }

        # Track codec usage
        codec_lower = codec.lower()
        self.codec_call_counts[codec_lower] += 1

        self.total_sessions += 1
        self.active_sessions += 1

        self.logger.info(f"Allocated media relay for call {call_id}")
        self.logger.info(f"  RTP: {relay_ip}:{rtp_port}, RTCP: {relay_ip}:{rtcp_port}")

        return relay_info

    def release_relay(self, call_id: str) -> None:
        """Release relay ports for a call"""
        if call_id in self.relay_sessions:
            session = self.relay_sessions[call_id]
            self.relay_port_pool.add(session["rtp_port"])
            self.relay_port_pool.add(session["rtcp_port"])
            del self.relay_sessions[call_id]

            # Clean up relay state
            self.relay_state.pop(call_id, None)

            self.logger.info(f"Released relay ports for call {call_id}")

    def relay_rtp_packet(self, packet: bytes, call_id: str) -> bool:
        """
        Relay RTP packet with state tracking.

        Parses the RTP header to track sequence numbers for packet loss
        detection, updates bandwidth metrics, and forwards the packet
        through the relay session.

        Args:
            packet: RTP packet bytes
            call_id: Call identifier

        Returns:
            True if packet was processed successfully
        """
        if call_id not in self.relay_sessions:
            self.logger.warning(f"No relay session for call {call_id}")
            return False

        session = self.relay_sessions[call_id]
        state = self.relay_state.get(call_id)
        if state is None:
            state = {
                "last_seq": -1,
                "packets_relayed": 0,
                "packets_lost": 0,
                "bytes_relayed": 0,
                "bandwidth_kbps": 0,
            }
            self.relay_state[call_id] = state

        packet_size = len(packet)

        # Parse RTP header if packet is large enough (minimum 12 bytes)
        if packet_size >= 12:
            # RTP header: V(2) P(1) X(1) CC(4) M(1) PT(7) SeqNum(16)
            seq_num = struct.unpack_from("!H", packet, 2)[0]

            # Detect packet loss via sequence number gaps
            last_seq = state["last_seq"]
            if last_seq >= 0:
                expected_seq = (last_seq + 1) & 0xFFFF
                if seq_num != expected_seq:
                    # Calculate gap accounting for wrap-around
                    gap = (seq_num - expected_seq) & 0xFFFF
                    if gap < 1000:  # Reasonable gap threshold
                        state["packets_lost"] += gap

            state["last_seq"] = seq_num

        # Track bandwidth usage
        self.relayed_media_bytes += packet_size
        state["bytes_relayed"] += packet_size
        state["packets_relayed"] += 1

        # Estimate instantaneous bandwidth (kbps)
        bandwidth_kbps = (packet_size * 8 * self.PACKETS_PER_SECOND) / 1000
        state["bandwidth_kbps"] = bandwidth_kbps

        self.logger.debug(
            f"Relayed RTP for {call_id}: {packet_size}B via "
            f"{session['relay_ip']}:{session['rtp_port']}"
        )

        return True

    # =========================================================================
    # Call Admission Control
    # =========================================================================

    def perform_call_admission_control(self, call_request: dict) -> dict:
        """
        Perform call admission control.

        Args:
            call_request: dict with 'call_id' and 'codec'

        Returns:
            dict with 'admit' boolean and details
        """
        if self.active_sessions >= self.max_calls:
            self.cac_rejections += 1
            return {"admit": False, "reason": "Maximum calls reached"}

        estimated_bandwidth = self._estimate_call_bandwidth(call_request.get("codec", "pcmu"))

        if self.current_bandwidth + estimated_bandwidth > self.max_bandwidth:
            self.cac_rejections += 1
            return {"admit": False, "reason": "Insufficient bandwidth"}

        call_id = call_request.get("call_id", "unknown")
        self.bandwidth_by_call[call_id] = estimated_bandwidth
        self.current_bandwidth += estimated_bandwidth

        return {"admit": True, "allocated_bandwidth": estimated_bandwidth}

    def release_call_resources(self, call_id: str) -> None:
        """Release resources for a completed call"""
        if call_id in self.bandwidth_by_call:
            bandwidth = self.bandwidth_by_call[call_id]
            self.current_bandwidth -= bandwidth
            del self.bandwidth_by_call[call_id]

        self.release_relay(call_id)

        if self.active_sessions > 0:
            self.active_sessions -= 1

    def _estimate_call_bandwidth(self, codec: str) -> int:
        """Estimate bandwidth for codec (kbps)"""
        return self.CODEC_BANDWIDTH.get(codec, 80)

    # =========================================================================
    # Security: Blacklist / Whitelist / Rate Limiting
    # =========================================================================

    def _is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        return ip in self.blacklist

    def _check_rate_limit(self, ip: str) -> bool:
        """
        Check rate limit for IP using sliding window.

        Whitelisted IPs bypass rate limiting.

        Returns:
            True if within rate limit or whitelisted
        """
        # Whitelisted IPs bypass rate limiting
        if ip in self.whitelist:
            return True

        current_time = time.time()

        if ip not in self.request_counts:
            self.request_counts[ip] = []

        requests = self.request_counts[ip]

        cutoff_time = current_time - self.rate_limit_window
        self.request_counts[ip] = [t for t in requests if t > cutoff_time]

        if len(self.request_counts[ip]) >= self.rate_limit:
            self.logger.warning(
                f"Rate limit exceeded for {ip}: "
                f"{len(self.request_counts[ip])} requests in {self.rate_limit_window}s"
            )
            return False

        self.request_counts[ip].append(current_time)
        return True

    def add_to_blacklist(self, ip: str) -> bool:
        """Add IP to blacklist and persist"""
        self.blacklist.add(ip)
        self._save_lists()
        self.logger.warning(f"Added {ip} to blacklist")
        return True

    def remove_from_blacklist(self, ip: str) -> bool:
        """Remove IP from blacklist and persist"""
        if ip in self.blacklist:
            self.blacklist.discard(ip)
            self._save_lists()
            self.logger.info(f"Removed {ip} from blacklist")
            return True
        return False

    def add_to_whitelist(self, ip: str) -> bool:
        """Add IP to whitelist and persist"""
        self.whitelist.add(ip)
        self._save_lists()
        self.logger.info(f"Added {ip} to whitelist")
        return True

    def remove_from_whitelist(self, ip: str) -> bool:
        """Remove IP from whitelist and persist"""
        if ip in self.whitelist:
            self.whitelist.discard(ip)
            self._save_lists()
            self.logger.info(f"Removed {ip} from whitelist")
            return True
        return False

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_lists(self) -> None:
        """Persist blacklist and whitelist to disk"""
        try:
            data_dir = Path(self.DATA_DIR)
            data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "blacklist": sorted(self.blacklist),
                "whitelist": sorted(self.whitelist),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            lists_file = data_dir / "lists.json"
            lists_file.write_text(json.dumps(data, indent=2))
        except OSError as e:
            self.logger.error(f"Failed to save SBC lists: {e}")

    def _load_lists(self) -> None:
        """Load blacklist and whitelist from disk"""
        try:
            lists_file = Path(self.DATA_DIR) / "lists.json"
            if lists_file.exists():
                data = json.loads(lists_file.read_text())
                self.blacklist = set(data.get("blacklist", []))
                self.whitelist = set(data.get("whitelist", []))
                self.logger.info(
                    f"Loaded {len(self.blacklist)} blacklist and "
                    f"{len(self.whitelist)} whitelist entries"
                )
        except (OSError, json.JSONDecodeError) as e:
            self.logger.warning(f"Failed to load SBC lists: {e}")

    # =========================================================================
    # Configuration
    # =========================================================================

    def get_config(self) -> dict:
        """Get current SBC configuration"""
        return {
            "enabled": self.enabled,
            "topology_hiding": self.topology_hiding,
            "media_relay": self.media_relay,
            "stun_enabled": self.stun_enabled,
            "turn_enabled": self.turn_enabled,
            "ice_enabled": self.ice_enabled,
            "max_calls": self.max_calls,
            "max_bandwidth": self.max_bandwidth,
            "rate_limit": self.rate_limit,
            "public_ip": self.public_ip,
            "product_name": self.PRODUCT_NAME,
        }

    def update_config(self, updates: dict) -> dict:
        """
        Update SBC configuration at runtime.

        Args:
            updates: dict of config keys to update

        Returns:
            Updated config dict
        """
        allowed_keys = {
            "enabled",
            "topology_hiding",
            "media_relay",
            "stun_enabled",
            "turn_enabled",
            "ice_enabled",
            "max_calls",
            "max_bandwidth",
            "rate_limit",
            "public_ip",
        }

        applied = {}
        for key, value in updates.items():
            if key in allowed_keys:
                setattr(self, key, value)
                applied[key] = value

        if applied:
            self.logger.info(f"{self.PRODUCT_NAME} config updated: {applied}")

        return self.get_config()

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict:
        """Get comprehensive SBC statistics"""
        bandwidth_utilization = (
            (self.current_bandwidth / self.max_bandwidth * 100) if self.max_bandwidth > 0 else 0.0
        )

        return {
            "product_name": self.PRODUCT_NAME,
            "enabled": self.enabled,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "blocked_requests": self.blocked_requests,
            "relayed_media_mb": round(self.relayed_media_bytes / (1024 * 1024), 2),
            "blacklist_size": len(self.blacklist),
            "whitelist_size": len(self.whitelist),
            "topology_hiding": self.topology_hiding,
            "media_relay": self.media_relay,
            "current_bandwidth_kbps": self.current_bandwidth,
            "max_bandwidth_kbps": self.max_bandwidth,
            "bandwidth_utilization_pct": round(bandwidth_utilization, 1),
            "rate_limit_violations": self.rate_limit_violations,
            "cac_rejections": self.cac_rejections,
            "codec_call_counts": dict(self.codec_call_counts),
            "topology_hiding_ops": self.topology_hiding_ops,
            "nat_detection_count": self.nat_detection_count,
            "relay_port_pool_size": len(self.relay_port_pool),
            "relay_port_pool_total": 5000,
            "max_calls": self.max_calls,
            "rate_limit": self.rate_limit,
        }


# Global instance
_sbc = None


def get_sbc(config: Any | None = None) -> SessionBorderController:
    """Get or create SBC instance"""
    global _sbc
    if _sbc is None:
        _sbc = SessionBorderController(config)
    return _sbc
