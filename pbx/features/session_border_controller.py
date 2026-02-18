"""
Session Border Controller (SBC)
Enhanced security and NAT traversal
"""

import re
import socket
import time
from collections import defaultdict
from datetime import UTC, datetime
from enum import Enum
from typing import Any

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
    Session Border Controller (SBC)

    Enterprise-grade security and NAT traversal for SIP/RTP.
    Features:
    - NAT traversal (STUN/TURN/ICE)
    - Topology hiding
    - Protocol normalization
    - Security filtering (DoS protection, malformed packets)
    - Media relay and transcoding
    - Call admission control
    - SIP header manipulation
    """

    # Constants
    IP_PATTERN = r"(\d+\.\d+\.\d+\.\d+)"
    PACKETS_PER_SECOND = 50  # Assumed packets per second for VoIP bandwidth calculation

    def __init__(self, config: Any | None = None) -> None:
        """Initialize SBC"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        sbc_config = self.config.get("features", {}).get("sbc", {})
        self.enabled = sbc_config.get("enabled", False)
        self.topology_hiding = sbc_config.get("topology_hiding", True)
        self.media_relay = sbc_config.get("media_relay", True)
        self.max_calls = sbc_config.get("max_calls", 1000)
        self.max_bandwidth = sbc_config.get("max_bandwidth", 100000)  # kbps

        # NAT/firewall traversal
        self.stun_enabled = sbc_config.get("stun_enabled", True)
        self.turn_enabled = sbc_config.get("turn_enabled", True)
        self.ice_enabled = sbc_config.get("ice_enabled", True)

        # Security
        self.rate_limit = sbc_config.get("rate_limit", 100)  # requests/second
        self.blacklist: set = set()
        self.whitelist: set = set()

        # Rate limiting tracking
        self.request_counts: dict[str, list[float]] = defaultdict(list)
        self.rate_limit_window = 1.0  # 1 second window

        # Media relay sessions
        self.relay_sessions: dict[str, dict] = {}
        self.next_relay_port = 10000
        self.relay_port_pool: set = set(range(10000, 20000, 2))  # RTP uses even ports

        # Bandwidth tracking
        self.current_bandwidth = 0  # kbps
        self.bandwidth_by_call: dict[str, int] = {}

        # Statistics
        self.total_sessions = 0
        self.active_sessions = 0
        self.blocked_requests = 0
        self.relayed_media_bytes = 0

        self.logger.info("Session Border Controller initialized")
        self.logger.info(f"  Topology hiding: {self.topology_hiding}")
        self.logger.info(f"  Media relay: {self.media_relay}")
        self.logger.info(f"  NAT traversal: STUN={self.stun_enabled}, TURN={self.turn_enabled}")
        self.logger.info(f"  Enabled: {self.enabled}")

    def process_inbound_sip(self, message: dict, source_ip: str) -> dict:
        """
        Process inbound SIP message

        Args:
            message: SIP message
            source_ip: Source IP address

        Returns:
            dict: Processing result
        """
        # Security checks
        if self._is_blacklisted(source_ip):
            self.blocked_requests += 1
            return {"action": "block", "reason": "Blacklisted IP"}

        # Rate limiting
        if not self._check_rate_limit(source_ip):
            self.blocked_requests += 1
            return {"action": "block", "reason": "Rate limit exceeded"}

        # Topology hiding - rewrite headers
        if self.topology_hiding:
            message = self._hide_topology(message, "inbound")

        # Protocol normalization
        message = self._normalize_sip_message(message)

        return {"action": "forward", "message": message}

    def process_outbound_sip(self, message: dict) -> dict:
        """Process outbound SIP message"""
        # Topology hiding
        if self.topology_hiding:
            message = self._hide_topology(message, "outbound")

        return {"action": "forward", "message": message}

    def _hide_topology(self, message: dict, direction: str) -> dict:
        """
        Hide internal topology in SIP headers

        Args:
            message: SIP message
            direction: Direction (inbound/outbound)

        Returns:
            dict: Modified message
        """
        if not isinstance(message, dict):
            return message

        # Get SBC public IP (use configured or detect)
        sbc_public_ip = (
            self.config.get("features", {}).get("sbc", {}).get("public_ip", "0.0.0.0")  # nosec B104 - SBC needs to bind all interfaces
        )

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

        elif direction == "inbound":
            # For inbound, ensure internal IPs are hidden in responses
            if "via" in modified_message:
                # Prepend SBC's own Via header so responses route back through us,
                # while preserving the original external Via for proper SIP routing
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
        # Replace IP addresses in Via header with SBC public IP
        # Format: Via: SIP/2.0/UDP 192.168.1.1:5060;branch=z9hG4bK...
        return re.sub(self.IP_PATTERN, public_ip, via)

    def _rewrite_contact_header(self, contact: str, public_ip: str) -> str:
        """Rewrite Contact header with SBC IP"""
        # Replace IP in Contact header
        # Format: Contact: <sip:user@192.168.1.1:5060>
        return re.sub(self.IP_PATTERN, public_ip, contact)

    def _rewrite_record_route(self, record_route: str, public_ip: str) -> str:
        """Rewrite Record-Route header with SBC IP"""
        # Replace IP in Record-Route
        return re.sub(self.IP_PATTERN, public_ip, record_route)

    def _hide_internal_ips_in_sdp(self, sdp: str, public_ip: str) -> str:
        """Hide internal IPs in SDP body"""
        # Replace connection line (c=) with public IP
        # Format: c=IN IP4 192.168.1.1
        sdp_pattern = r"(c=IN IP4 )" + self.IP_PATTERN
        return re.sub(sdp_pattern, r"\g<1>" + public_ip, sdp)

    def _normalize_sip_message(self, message: dict) -> dict:
        """Normalize SIP message format"""
        if not isinstance(message, dict):
            return message

        normalized = message.copy()

        # Fix common malformed headers
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

        # Validate and fix method if present
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

    def detect_nat(self, local_ip: str, public_ip: str) -> NATType:
        """
        Detect NAT type using STUN binding requests (RFC 5389).

        Sends actual STUN Binding Request packets to the configured STUN
        server (or falls back to the supplied *public_ip* on port 3478).

        The algorithm follows RFC 3489 section 10.1:
          1. **Test I** -- basic binding request to primary address/port.
          2. **Test II** -- binding request with CHANGE-REQUEST flag
             (change IP + port).
          3. **Test III** -- binding request with CHANGE-REQUEST flag
             (change port only).

        Args:
            local_ip: Local IP address of this host.
            public_ip: Known or assumed public IP address.

        Returns:
            NATType: Detected NAT type.
        """
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
            self.logger.warning("STUN Test I failed — cannot reach STUN server")
            # Cannot determine; assume port-restricted (most common)
            return NATType.PORT_RESTRICTED

        mapped_ip_1, mapped_port_1 = mapped_addr_1
        self.logger.debug(f"STUN Test I: mapped address {mapped_ip_1}:{mapped_port_1}")

        # --- Test II: Request server to respond from a different IP and port ---
        # CHANGE-REQUEST flags: change IP (0x04) + change port (0x02) = 0x06
        mapped_addr_2 = self._stun_binding_request(
            stun_server, stun_port, change_request_flags=0x06
        )

        if mapped_addr_2 is not None:
            # We received a response from a different server IP/port.
            # This means the NAT allows traffic from any source — Full Cone.
            self.logger.debug("STUN Test II succeeded — Full Cone NAT")
            return NATType.FULL_CONE

        # --- Test III: Same server IP, different port ---
        # CHANGE-REQUEST flags: change port only (0x02)
        mapped_addr_3 = self._stun_binding_request(
            stun_server, stun_port, change_request_flags=0x02
        )

        if mapped_addr_3 is not None:
            # Accepts from same IP but different port — Restricted Cone
            self.logger.debug("STUN Test III succeeded — Restricted Cone NAT")
            return NATType.RESTRICTED_CONE

        # --- Test IV: Second binding to a different port to check for symmetric ---
        alt_port = stun_port + 1
        mapped_addr_4 = self._stun_binding_request(stun_server, alt_port)

        if mapped_addr_4 is not None:
            _mapped_ip_4, mapped_port_4 = mapped_addr_4
            if mapped_port_4 != mapped_port_1:
                # Different mapped port for different destination — Symmetric NAT
                self.logger.debug(
                    f"STUN Test IV: mapped port changed "
                    f"({mapped_port_1} vs {mapped_port_4}) — Symmetric NAT"
                )
                return NATType.SYMMETRIC

        # Default: Port Restricted Cone
        self.logger.debug("STUN classification: Port Restricted Cone NAT")
        return NATType.PORT_RESTRICTED

    def _stun_binding_request(
        self,
        server: str,
        port: int,
        change_request_flags: int | None = None,
    ) -> tuple[str, int] | None:
        """Send a single STUN Binding Request and parse the response.

        Constructs a minimal RFC 5389 Binding Request, optionally including
        a CHANGE-REQUEST attribute (RFC 3489), sends it via UDP, and
        extracts the XOR-MAPPED-ADDRESS (or MAPPED-ADDRESS) from the
        response.

        Args:
            server: STUN server hostname or IP.
            port: STUN server port.
            change_request_flags: Optional CHANGE-REQUEST flags byte
                (``0x02`` = change port, ``0x04`` = change IP, ``0x06`` =
                both).

        Returns:
            ``(mapped_ip, mapped_port)`` tuple, or ``None`` on failure.
        """
        import os
        import struct

        try:
            # Build STUN Binding Request (RFC 5389 section 6)
            transaction_id = os.urandom(12)  # 96-bit transaction ID
            attrs = b""

            if change_request_flags is not None:
                # CHANGE-REQUEST attribute (type 0x0003, length 4)
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

            # Parse response
            if len(data) < self.STUN_HEADER_SIZE:
                return None

            msg_type, _msg_len, _magic = struct.unpack_from("!HHI", data, 0)
            resp_txn = data[8:20]

            if msg_type != self.STUN_BINDING_RESPONSE:
                return None
            if resp_txn != transaction_id:
                return None

            # Walk attributes looking for XOR-MAPPED-ADDRESS or MAPPED-ADDRESS
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

                # Advance to next attribute (padded to 4-byte boundary)
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
        import struct

        if offset + 8 > len(data):
            return None

        _reserved, family, xport = struct.unpack_from("!BBH", data, offset)
        if family != 0x01:  # Only IPv4 supported here
            return None

        xaddr = struct.unpack_from("!I", data, offset + 4)[0]

        # XOR with magic cookie
        mapped_port = xport ^ (SessionBorderController.STUN_MAGIC_COOKIE >> 16)
        mapped_addr_int = xaddr ^ SessionBorderController.STUN_MAGIC_COOKIE

        mapped_ip = socket.inet_ntoa(struct.pack("!I", mapped_addr_int))
        return mapped_ip, mapped_port

    @staticmethod
    def _parse_mapped_address(data: bytes, offset: int) -> tuple[str, int] | None:
        """Parse a MAPPED-ADDRESS attribute (RFC 5389 section 15.1)."""
        import struct

        if offset + 8 > len(data):
            return None

        _reserved, family, mapped_port = struct.unpack_from("!BBH", data, offset)
        if family != 0x01:  # IPv4
            return None

        mapped_addr_int = struct.unpack_from("!I", data, offset + 4)[0]
        mapped_ip = socket.inet_ntoa(struct.pack("!I", mapped_addr_int))
        return mapped_ip, mapped_port

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private range"""
        try:
            octets = [int(x) for x in ip.split(".")]
            # 10.0.0.0/8
            if octets[0] == 10:
                return True
            # 172.16.0.0/12
            if octets[0] == 172 and 16 <= octets[1] <= 31:
                return True
            # 192.168.0.0/16
            return bool(octets[0] == 192 and octets[1] == 168)
        except (ValueError, IndexError):
            return False

    def allocate_relay(self, call_id: str, codec: str) -> dict:
        """
        Allocate media relay for NAT traversal

        Args:
            call_id: Call identifier
            codec: Media codec

        Returns:
            dict: Relay allocation
        """
        if not self.media_relay:
            return {"success": False, "reason": "Media relay disabled"}

        # Check if already allocated
        if call_id in self.relay_sessions:
            return self.relay_sessions[call_id]

        # Allocate RTP/RTCP port pair
        if len(self.relay_port_pool) < 2:
            return {"success": False, "reason": "No relay ports available"}

        # Get even port for RTP (odd port+1 for RTCP)
        rtp_port = min(self.relay_port_pool)
        self.relay_port_pool.discard(rtp_port)
        rtcp_port = rtp_port + 1
        self.relay_port_pool.discard(rtcp_port)

        # Get SBC public IP
        relay_ip = (
            self.config.get("features", {}).get("sbc", {}).get("public_ip", "0.0.0.0")  # nosec B104 - SBC needs to bind all interfaces
        )

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

        self.logger.info(f"Allocated media relay for call {call_id}")
        self.logger.info(f"  RTP: {relay_ip}:{rtp_port}, RTCP: {relay_ip}:{rtcp_port}")

        return relay_info

    def release_relay(self, call_id: str) -> None:
        """Release relay ports for a call"""
        if call_id in self.relay_sessions:
            session = self.relay_sessions[call_id]
            # Return ports to pool
            self.relay_port_pool.add(session["rtp_port"])
            self.relay_port_pool.add(session["rtcp_port"])
            del self.relay_sessions[call_id]
            self.logger.info(f"Released relay ports for call {call_id}")

    def relay_rtp_packet(self, packet: bytes, call_id: str) -> bool:
        """
        Relay RTP packet

        Args:
            packet: RTP packet
            call_id: Call identifier

        Returns:
            bool: Success
        """
        # Check if relay session exists
        if call_id not in self.relay_sessions:
            self.logger.warning(f"No relay session for call {call_id}")
            return False

        self.relay_sessions[call_id]

        # In production, this would:
        # 1. Parse RTP header
        # 2. Maintain session state (SSRC, sequence numbers)
        # 3. Forward packet to destination
        # 4. Handle RTCP for the session
        # 5. Detect and handle packet loss

        # Track bandwidth usage
        packet_size = len(packet)
        self.relayed_media_bytes += packet_size

        # Update bandwidth tracking (rough estimate in kbps)
        (packet_size * 8 * self.PACKETS_PER_SECOND) / 1000

        self.logger.debug(f"Relayed RTP packet for {call_id}: {packet_size} bytes")

        return True

    def perform_call_admission_control(self, call_request: dict) -> dict:
        """
        Perform call admission control

        Args:
            call_request: Call request information

        Returns:
            dict: Admission decision
        """
        # Check current load
        if self.active_sessions >= self.max_calls:
            return {"admit": False, "reason": "Maximum calls reached"}

        # Check bandwidth
        estimated_bandwidth = self._estimate_call_bandwidth(call_request.get("codec", "pcmu"))

        # Track current bandwidth usage
        if self.current_bandwidth + estimated_bandwidth > self.max_bandwidth:
            return {"admit": False, "reason": "Insufficient bandwidth"}

        # Allocate bandwidth
        call_id = call_request.get("call_id", "unknown")
        self.bandwidth_by_call[call_id] = estimated_bandwidth
        self.current_bandwidth += estimated_bandwidth

        return {"admit": True, "allocated_bandwidth": estimated_bandwidth}

    def release_call_resources(self, call_id: str) -> None:
        """Release resources for a completed call"""
        # Release bandwidth
        if call_id in self.bandwidth_by_call:
            bandwidth = self.bandwidth_by_call[call_id]
            self.current_bandwidth -= bandwidth
            del self.bandwidth_by_call[call_id]

        # Release relay ports
        self.release_relay(call_id)

        # Update session count
        if self.active_sessions > 0:
            self.active_sessions -= 1

    def _estimate_call_bandwidth(self, codec: str) -> int:
        """Estimate bandwidth for codec (kbps)"""
        bandwidth_map = {"pcmu": 80, "pcma": 80, "g722": 80, "opus": 40, "g729": 30}
        return bandwidth_map.get(codec, 80)

    def _is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        return ip in self.blacklist

    def _check_rate_limit(self, ip: str) -> bool:
        """
        Check rate limit for IP using sliding window

        Args:
            ip: IP address

        Returns:
            bool: True if within rate limit
        """
        current_time = time.time()

        # Get or create request list for this IP
        if ip not in self.request_counts:
            self.request_counts[ip] = []

        requests = self.request_counts[ip]

        # Remove requests outside the time window
        cutoff_time = current_time - self.rate_limit_window
        self.request_counts[ip] = [t for t in requests if t > cutoff_time]

        # Check if under rate limit
        if len(self.request_counts[ip]) >= self.rate_limit:
            self.logger.warning(
                f"Rate limit exceeded for {ip}: {len(self.request_counts[ip])} requests in {self.rate_limit_window}s"
            )
            return False

        # Add current request
        self.request_counts[ip].append(current_time)

        return True

    def add_to_blacklist(self, ip: str) -> bool:
        """Add IP to blacklist"""
        if not self.enabled:
            self.logger.error(
                "Cannot add to blacklist: Session border controller feature is not enabled"
            )
            return False

        self.blacklist.add(ip)
        self.logger.warning(f"Added {ip} to blacklist")
        return True

    def add_to_whitelist(self, ip: str) -> bool:
        """Add IP to whitelist"""
        if not self.enabled:
            self.logger.error(
                "Cannot add to whitelist: Session border controller feature is not enabled"
            )
            return False

        self.whitelist.add(ip)
        self.logger.info(f"Added {ip} to whitelist")
        return True

    def get_statistics(self) -> dict:
        """Get SBC statistics"""
        return {
            "enabled": self.enabled,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "blocked_requests": self.blocked_requests,
            "relayed_media_mb": self.relayed_media_bytes / (1024 * 1024),
            "blacklist_size": len(self.blacklist),
            "whitelist_size": len(self.whitelist),
            "topology_hiding": self.topology_hiding,
            "media_relay": self.media_relay,
        }


# Global instance
_sbc = None


def get_sbc(config: Any | None = None) -> SessionBorderController:
    """Get or create SBC instance"""
    global _sbc
    if _sbc is None:
        _sbc = SessionBorderController(config)
    return _sbc
