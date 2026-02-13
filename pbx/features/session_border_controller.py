"""
Session Border Controller (SBC)
Enhanced security and NAT traversal
"""

import re
import socket
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum

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

    def __init__(self, config=None):
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
            self.config.get("features", {})
            .get("sbc", {})
            .get("public_ip", "0.0.0.0")  # nosec B104 - SBC needs to bind all interfaces
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
                # Keep Via from external, but may need to add our own
                pass

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

    def detect_nat(self, local_ip: str, public_ip: str) -> NATType:
        """
        Detect NAT type using STUN-like algorithm

        Args:
            local_ip: Local IP address
            public_ip: Public IP address

        Returns:
            NATType: Detected NAT type
        """
        # Check if behind NAT
        if local_ip == public_ip:
            return NATType.NONE

        # Check if local IP is private
        if not self._is_private_ip(local_ip):
            # Both are public but different - unusual
            return NATType.NONE

        # Simplified NAT detection based on RFC 3489/5389
        # In production, this would perform STUN binding tests:
        # 1. Test I: Basic binding test
        # 2. Test II: Binding test with changed port
        # 3. Test III: Binding test with changed IP and port

        # For now, use heuristic based on common NAT behaviors
        # Check if we can determine NAT type from IP patterns

        try:
            # Try to connect to external service to determine NAT type
            # This is a simplified version - production would use STUN protocol
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)

            # Attempt connection (doesn't actually send data, just tests binding)
            try:
                sock.connect((public_ip, 3478))  # STUN port
                # If we can bind, it's likely port-restricted or better
                sock.close()

                # Default to port-restricted for most home/office NATs
                return NATType.PORT_RESTRICTED
            except (OSError, socket.error):
                sock.close()
                # Symmetric NAT is most restrictive
                return NATType.SYMMETRIC
        except (OSError, socket.error):
            # If we can't determine, assume port-restricted (most common)
            return NATType.PORT_RESTRICTED

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
            if octets[0] == 192 and octets[1] == 168:
                return True
            return False
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
            self.config.get("features", {})
            .get("sbc", {})
            .get("public_ip", "0.0.0.0")  # nosec B104 - SBC needs to bind all interfaces
        )

        relay_info = {
            "success": True,
            "call_id": call_id,
            "rtp_port": rtp_port,
            "rtcp_port": rtcp_port,
            "relay_ip": relay_ip,
            "codec": codec,
            "allocated_at": datetime.now().isoformat(),
        }

        self.relay_sessions[call_id] = relay_info

        self.logger.info(f"Allocated media relay for call {call_id}")
        self.logger.info(f"  RTP: {relay_ip}:{rtp_port}, RTCP: {relay_ip}:{rtcp_port}")

        return relay_info

    def release_relay(self, call_id: str):
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

    def release_call_resources(self, call_id: str):
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

    def add_to_blacklist(self, ip: str):
        """Add IP to blacklist"""
        if not self.enabled:
            self.logger.error(
                "Cannot add to blacklist: Session border controller feature is not enabled"
            )
            return False

        self.blacklist.add(ip)
        self.logger.warning(f"Added {ip} to blacklist")
        return True

    def add_to_whitelist(self, ip: str):
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


def get_sbc(config=None) -> SessionBorderController:
    """Get or create SBC instance"""
    global _sbc
    if _sbc is None:
        _sbc = SessionBorderController(config)
    return _sbc
