"""
Tests for Session Border Controller (SBC) feature module.
Covers NAT detection, topology hiding, media relay, call admission control,
rate limiting, blacklist/whitelist, and statistics.
"""

import socket
import time
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.session_border_controller import (
    NATType,
    SessionBorderController,
    get_sbc,
)


def _make_sbc_config(
    enabled: bool = True,
    topology_hiding: bool = True,
    media_relay: bool = True,
    max_calls: int = 1000,
    max_bandwidth: int = 100000,
    stun_enabled: bool = True,
    turn_enabled: bool = True,
    ice_enabled: bool = True,
    rate_limit: int = 100,
    public_ip: str = "203.0.113.1",
) -> dict:
    """Helper to build an SBC config dict."""
    return {
        "features": {
            "sbc": {
                "enabled": enabled,
                "topology_hiding": topology_hiding,
                "media_relay": media_relay,
                "max_calls": max_calls,
                "max_bandwidth": max_bandwidth,
                "stun_enabled": stun_enabled,
                "turn_enabled": turn_enabled,
                "ice_enabled": ice_enabled,
                "rate_limit": rate_limit,
                "public_ip": public_ip,
            }
        }
    }


@pytest.mark.unit
class TestNATType:
    """Tests for NATType enum."""

    def test_nat_type_values(self) -> None:
        """Test all NATType enum values exist."""
        assert NATType.NONE.value == "none"
        assert NATType.FULL_CONE.value == "full_cone"
        assert NATType.RESTRICTED_CONE.value == "restricted_cone"
        assert NATType.PORT_RESTRICTED.value == "port_restricted"
        assert NATType.SYMMETRIC.value == "symmetric"

    def test_nat_type_from_value(self) -> None:
        """Test NATType can be constructed from string values."""
        assert NATType("none") is NATType.NONE
        assert NATType("symmetric") is NATType.SYMMETRIC

    def test_nat_type_invalid_value(self) -> None:
        """Test NATType raises on invalid values."""
        with pytest.raises(ValueError):
            NATType("invalid")


@pytest.mark.unit
class TestSessionBorderControllerInit:
    """Tests for SBC initialization."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_init_defaults_no_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with no config uses defaults."""
        sbc = SessionBorderController()

        assert sbc.enabled is False
        assert sbc.topology_hiding is True
        assert sbc.media_relay is True
        assert sbc.max_calls == 1000
        assert sbc.max_bandwidth == 100000
        assert sbc.stun_enabled is True
        assert sbc.turn_enabled is True
        assert sbc.ice_enabled is True
        assert sbc.rate_limit == 100
        assert sbc.blacklist == set()
        assert sbc.whitelist == set()
        assert sbc.relay_sessions == {}
        assert sbc.total_sessions == 0
        assert sbc.active_sessions == 0
        assert sbc.blocked_requests == 0
        assert sbc.relayed_media_bytes == 0
        assert sbc.current_bandwidth == 0
        assert sbc.bandwidth_by_call == {}

    @patch("pbx.features.session_border_controller.get_logger")
    def test_init_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with explicit None config."""
        sbc = SessionBorderController(config=None)
        assert sbc.config == {}
        assert sbc.enabled is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_init_with_full_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with full SBC config."""
        config = _make_sbc_config(
            enabled=True,
            topology_hiding=False,
            media_relay=False,
            max_calls=500,
            max_bandwidth=50000,
            stun_enabled=False,
            turn_enabled=False,
            ice_enabled=False,
            rate_limit=50,
        )
        sbc = SessionBorderController(config)

        assert sbc.enabled is True
        assert sbc.topology_hiding is False
        assert sbc.media_relay is False
        assert sbc.max_calls == 500
        assert sbc.max_bandwidth == 50000
        assert sbc.stun_enabled is False
        assert sbc.turn_enabled is False
        assert sbc.ice_enabled is False
        assert sbc.rate_limit == 50

    @patch("pbx.features.session_border_controller.get_logger")
    def test_init_relay_port_pool(self, mock_get_logger: MagicMock) -> None:
        """Test that relay port pool is initialized correctly with even ports."""
        sbc = SessionBorderController()
        assert 10000 in sbc.relay_port_pool
        assert 10002 in sbc.relay_port_pool
        assert 19998 in sbc.relay_port_pool
        # Odd ports should not be in pool (range step is 2 from even base)
        assert 10001 not in sbc.relay_port_pool
        assert 10003 not in sbc.relay_port_pool

    @patch("pbx.features.session_border_controller.get_logger")
    def test_init_logging(self, mock_get_logger: MagicMock) -> None:
        """Test that initialization logs expected messages."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        SessionBorderController(_make_sbc_config(enabled=True))

        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("Session Border Controller initialized" in c for c in info_calls)
        assert any("Topology hiding" in c for c in info_calls)
        assert any("Media relay" in c for c in info_calls)
        assert any("NAT traversal" in c for c in info_calls)
        assert any("Enabled" in c for c in info_calls)


@pytest.mark.unit
class TestProcessInboundSip:
    """Tests for inbound SIP message processing."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_block_blacklisted_ip(self, mock_get_logger: MagicMock) -> None:
        """Test that blacklisted IPs are blocked."""
        config = _make_sbc_config(enabled=True)
        sbc = SessionBorderController(config)
        sbc.blacklist.add("10.0.0.99")

        result = sbc.process_inbound_sip({"method": "INVITE"}, "10.0.0.99")

        assert result["action"] == "block"
        assert result["reason"] == "Blacklisted IP"
        assert sbc.blocked_requests == 1

    @patch("pbx.features.session_border_controller.get_logger")
    def test_block_rate_limited_ip(self, mock_get_logger: MagicMock) -> None:
        """Test that rate-exceeded IPs are blocked."""
        config = _make_sbc_config(rate_limit=2)
        sbc = SessionBorderController(config)
        msg = {
            "method": "OPTIONS",
            "via": "SIP/2.0/UDP 10.0.0.1:5060",
            "from": "a",
            "to": "b",
            "call_id": "x",
            "cseq": "1",
        }

        # First two should pass
        r1 = sbc.process_inbound_sip(msg, "10.0.0.1")
        r2 = sbc.process_inbound_sip(msg, "10.0.0.1")
        assert r1["action"] == "forward"
        assert r2["action"] == "forward"

        # Third should be rate-limited
        r3 = sbc.process_inbound_sip(msg, "10.0.0.1")
        assert r3["action"] == "block"
        assert r3["reason"] == "Rate limit exceeded"
        assert sbc.blocked_requests == 1

    @patch("pbx.features.session_border_controller.get_logger")
    def test_forward_valid_message(self, mock_get_logger: MagicMock) -> None:
        """Test forwarding of a valid SIP message."""
        config = _make_sbc_config(topology_hiding=False)
        sbc = SessionBorderController(config)
        msg = {"method": "INVITE", "via": "v", "from": "f", "to": "t", "call_id": "c", "cseq": "1"}

        result = sbc.process_inbound_sip(msg, "10.0.0.1")
        assert result["action"] == "forward"
        assert "message" in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_topology_hiding_applied_inbound(self, mock_get_logger: MagicMock) -> None:
        """Test that topology hiding modifies inbound SDP."""
        config = _make_sbc_config(topology_hiding=True, public_ip="203.0.113.1")
        sbc = SessionBorderController(config)
        msg = {
            "method": "INVITE",
            "via": "SIP/2.0/UDP 192.168.1.10:5060",
            "from": "sip:1001@192.168.1.10",
            "to": "sip:1002@pbx.local",
            "call_id": "abc123",
            "cseq": "1 INVITE",
            "sdp": "v=0\r\nc=IN IP4 192.168.1.10\r\nm=audio 5004 RTP/AVP 0",
        }

        result = sbc.process_inbound_sip(msg, "10.0.0.1")
        assert result["action"] == "forward"
        # SDP should have internal IPs replaced
        assert "203.0.113.1" in result["message"]["sdp"]
        assert "192.168.1.10" not in result["message"]["sdp"]

    @patch("pbx.features.session_border_controller.get_logger")
    def test_normalization_removes_unnecessary_headers(self, mock_get_logger: MagicMock) -> None:
        """Test that normalization strips info-leaking headers."""
        config = _make_sbc_config(topology_hiding=False)
        sbc = SessionBorderController(config)
        msg = {
            "method": "INVITE",
            "via": "v",
            "from": "f",
            "to": "t",
            "call_id": "c",
            "cseq": "1",
            "user_agent": "SoftPhone/1.0",
            "server": "PBX/2.0",
            "organization": "Acme Corp",
        }

        result = sbc.process_inbound_sip(msg, "10.0.0.1")
        forwarded = result["message"]
        assert "user_agent" not in forwarded
        assert "server" not in forwarded
        assert "organization" not in forwarded

    @patch("pbx.features.session_border_controller.get_logger")
    def test_blocked_requests_counter_increments(self, mock_get_logger: MagicMock) -> None:
        """Test blocked_requests increments for each blocked message."""
        config = _make_sbc_config(enabled=True)
        sbc = SessionBorderController(config)
        sbc.blacklist.add("1.2.3.4")

        sbc.process_inbound_sip({}, "1.2.3.4")
        sbc.process_inbound_sip({}, "1.2.3.4")
        assert sbc.blocked_requests == 2


@pytest.mark.unit
class TestProcessOutboundSip:
    """Tests for outbound SIP message processing."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_outbound_forward(self, mock_get_logger: MagicMock) -> None:
        """Test basic outbound message forwarding."""
        config = _make_sbc_config(topology_hiding=False)
        sbc = SessionBorderController(config)
        msg = {"method": "INVITE", "via": "v"}

        result = sbc.process_outbound_sip(msg)
        assert result["action"] == "forward"
        assert result["message"] == msg

    @patch("pbx.features.session_border_controller.get_logger")
    def test_outbound_topology_hiding_via(self, mock_get_logger: MagicMock) -> None:
        """Test topology hiding rewrites Via header on outbound."""
        config = _make_sbc_config(topology_hiding=True, public_ip="203.0.113.1")
        sbc = SessionBorderController(config)
        msg = {
            "via": "SIP/2.0/UDP 192.168.1.10:5060;branch=z9hG4bK776",
        }

        result = sbc.process_outbound_sip(msg)
        assert "203.0.113.1" in result["message"]["via"]
        assert "192.168.1.10" not in result["message"]["via"]

    @patch("pbx.features.session_border_controller.get_logger")
    def test_outbound_topology_hiding_contact(self, mock_get_logger: MagicMock) -> None:
        """Test topology hiding rewrites Contact header on outbound."""
        config = _make_sbc_config(topology_hiding=True, public_ip="203.0.113.1")
        sbc = SessionBorderController(config)
        msg = {
            "contact": "<sip:user@192.168.1.10:5060>",
        }

        result = sbc.process_outbound_sip(msg)
        assert "203.0.113.1" in result["message"]["contact"]
        assert "192.168.1.10" not in result["message"]["contact"]

    @patch("pbx.features.session_border_controller.get_logger")
    def test_outbound_topology_hiding_record_route(self, mock_get_logger: MagicMock) -> None:
        """Test topology hiding rewrites Record-Route header on outbound."""
        config = _make_sbc_config(topology_hiding=True, public_ip="203.0.113.1")
        sbc = SessionBorderController(config)
        msg = {
            "record_route": "<sip:192.168.1.10;lr>",
        }

        result = sbc.process_outbound_sip(msg)
        assert "203.0.113.1" in result["message"]["record_route"]
        assert "192.168.1.10" not in result["message"]["record_route"]

    @patch("pbx.features.session_border_controller.get_logger")
    def test_outbound_no_topology_hiding(self, mock_get_logger: MagicMock) -> None:
        """Test outbound with topology hiding disabled preserves message."""
        config = _make_sbc_config(topology_hiding=False)
        sbc = SessionBorderController(config)
        msg = {"via": "SIP/2.0/UDP 192.168.1.10:5060;branch=z9hG4bK776"}

        result = sbc.process_outbound_sip(msg)
        assert "192.168.1.10" in result["message"]["via"]


@pytest.mark.unit
class TestHideTopology:
    """Tests for _hide_topology method."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_non_dict_message_returned_as_is(self, mock_get_logger: MagicMock) -> None:
        """Test that non-dict messages pass through unchanged."""
        sbc = SessionBorderController(_make_sbc_config())
        result = sbc._hide_topology("not a dict", "outbound")
        assert result == "not a dict"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_original_message_not_modified(self, mock_get_logger: MagicMock) -> None:
        """Test that _hide_topology does not modify the original message dict."""
        sbc = SessionBorderController(_make_sbc_config(public_ip="203.0.113.1"))
        original = {"via": "SIP/2.0/UDP 192.168.1.10:5060"}
        original_copy = original.copy()

        sbc._hide_topology(original, "outbound")
        assert original == original_copy

    @patch("pbx.features.session_border_controller.get_logger")
    def test_inbound_sdp_rewrite(self, mock_get_logger: MagicMock) -> None:
        """Test inbound direction rewrites SDP internal IPs."""
        sbc = SessionBorderController(_make_sbc_config(public_ip="203.0.113.1"))
        msg = {"sdp": "v=0\r\nc=IN IP4 10.0.0.5\r\nm=audio 5004 RTP/AVP 0"}

        result = sbc._hide_topology(msg, "inbound")
        assert "203.0.113.1" in result["sdp"]
        assert "10.0.0.5" not in result["sdp"]

    @patch("pbx.features.session_border_controller.get_logger")
    def test_inbound_via_prepends_sbc(self, mock_get_logger: MagicMock) -> None:
        """Test inbound direction prepends SBC Via header."""
        sbc = SessionBorderController(_make_sbc_config(public_ip="203.0.113.1"))
        original_via = "SIP/2.0/UDP 10.0.0.5:5060"
        msg = {"via": original_via}

        result = sbc._hide_topology(msg, "inbound")
        # SBC prepends its own Via so responses route back through it
        assert result["via"].startswith("SIP/2.0/UDP 203.0.113.1:5060;branch=z9hG4bK-sbc-")
        assert result["via"].endswith(", " + original_via)

    @patch("pbx.features.session_border_controller.get_logger")
    def test_outbound_no_headers_present(self, mock_get_logger: MagicMock) -> None:
        """Test outbound with empty message dict."""
        sbc = SessionBorderController(_make_sbc_config(public_ip="203.0.113.1"))
        msg = {"method": "INVITE"}

        result = sbc._hide_topology(msg, "outbound")
        assert result["method"] == "INVITE"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_unknown_direction(self, mock_get_logger: MagicMock) -> None:
        """Test with an unrecognized direction string."""
        sbc = SessionBorderController(_make_sbc_config(public_ip="203.0.113.1"))
        msg = {"via": "SIP/2.0/UDP 10.0.0.5:5060", "sdp": "c=IN IP4 10.0.0.5"}

        result = sbc._hide_topology(msg, "unknown")
        # Neither inbound nor outbound branch executes
        assert result["via"] == msg["via"]
        assert result["sdp"] == msg["sdp"]


@pytest.mark.unit
class TestRewriteHeaders:
    """Tests for individual header rewrite methods."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_rewrite_via_header(self, mock_get_logger: MagicMock) -> None:
        """Test Via header IP replacement."""
        sbc = SessionBorderController()
        via = "SIP/2.0/UDP 192.168.1.10:5060;branch=z9hG4bK776"
        result = sbc._rewrite_via_header(via, "203.0.113.1")
        assert "203.0.113.1" in result
        assert "192.168.1.10" not in result
        # Non-IP parts preserved
        assert "branch=z9hG4bK776" in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_rewrite_contact_header(self, mock_get_logger: MagicMock) -> None:
        """Test Contact header IP replacement."""
        sbc = SessionBorderController()
        contact = "<sip:user@192.168.1.10:5060>"
        result = sbc._rewrite_contact_header(contact, "203.0.113.1")
        assert "203.0.113.1" in result
        assert "192.168.1.10" not in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_rewrite_record_route(self, mock_get_logger: MagicMock) -> None:
        """Test Record-Route header IP replacement."""
        sbc = SessionBorderController()
        rr = "<sip:192.168.1.10;lr>"
        result = sbc._rewrite_record_route(rr, "203.0.113.1")
        assert "203.0.113.1" in result
        assert "192.168.1.10" not in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_hide_internal_ips_in_sdp(self, mock_get_logger: MagicMock) -> None:
        """Test SDP connection line IP replacement."""
        sbc = SessionBorderController()
        sdp = "v=0\r\nc=IN IP4 192.168.1.10\r\nm=audio 5004 RTP/AVP 0"
        result = sbc._hide_internal_ips_in_sdp(sdp, "203.0.113.1")
        assert "c=IN IP4 203.0.113.1" in result
        assert "192.168.1.10" not in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_hide_internal_ips_in_sdp_no_connection_line(self, mock_get_logger: MagicMock) -> None:
        """Test SDP with no connection line is unchanged."""
        sbc = SessionBorderController()
        sdp = "v=0\r\nm=audio 5004 RTP/AVP 0"
        result = sbc._hide_internal_ips_in_sdp(sdp, "203.0.113.1")
        assert result == sdp

    @patch("pbx.features.session_border_controller.get_logger")
    def test_rewrite_via_multiple_ips(self, mock_get_logger: MagicMock) -> None:
        """Test Via with multiple IPs all get replaced."""
        sbc = SessionBorderController()
        via = "SIP/2.0/UDP 10.0.0.1:5060;received=172.16.0.1"
        result = sbc._rewrite_via_header(via, "203.0.113.1")
        assert "10.0.0.1" not in result
        assert "172.16.0.1" not in result


@pytest.mark.unit
class TestNormalizeSipMessage:
    """Tests for _normalize_sip_message method."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_non_dict_message(self, mock_get_logger: MagicMock) -> None:
        """Test non-dict message returns as-is."""
        sbc = SessionBorderController()
        assert sbc._normalize_sip_message("not a dict") == "not a dict"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_header_mapping_call_id(self, mock_get_logger: MagicMock) -> None:
        """Test call-id variants are normalized to call_id."""
        sbc = SessionBorderController()
        msg = {"call-id": "abc@123", "via": "v", "from": "f", "to": "t", "cseq": "1"}
        result = sbc._normalize_sip_message(msg)
        assert "call_id" in result
        assert result["call_id"] == "abc@123"
        assert "call-id" not in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_header_mapping_callid(self, mock_get_logger: MagicMock) -> None:
        """Test callid variant normalized to call_id."""
        sbc = SessionBorderController()
        msg = {"callid": "abc@123", "via": "v", "from": "f", "to": "t", "cseq": "1"}
        result = sbc._normalize_sip_message(msg)
        assert "call_id" in result
        assert "callid" not in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_header_mapping_cseq_variant(self, mock_get_logger: MagicMock) -> None:
        """Test c-seq variant normalized to cseq."""
        sbc = SessionBorderController()
        msg = {"c-seq": "1 INVITE", "via": "v", "from": "f", "to": "t", "call_id": "c"}
        result = sbc._normalize_sip_message(msg)
        assert "cseq" in result
        assert "c-seq" not in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_unnecessary_headers_removed(self, mock_get_logger: MagicMock) -> None:
        """Test user_agent, server, organization headers are stripped."""
        sbc = SessionBorderController()
        msg = {
            "via": "v",
            "from": "f",
            "to": "t",
            "call_id": "c",
            "cseq": "1",
            "user_agent": "Phone/1.0",
            "server": "PBX/2.0",
            "organization": "Acme",
        }
        result = sbc._normalize_sip_message(msg)
        assert "user_agent" not in result
        assert "server" not in result
        assert "organization" not in result

    @patch("pbx.features.session_border_controller.get_logger")
    def test_missing_required_headers_logged(self, mock_get_logger: MagicMock) -> None:
        """Test that missing required headers trigger warning logs."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        sbc = SessionBorderController()
        sbc.logger = mock_logger
        # Deliberately missing all required headers
        sbc._normalize_sip_message({"method": "INVITE"})

        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        # Should warn for each of: via, from, to, call_id, cseq
        assert len([c for c in warning_calls if "Missing required SIP header" in c]) == 5

    @patch("pbx.features.session_border_controller.get_logger")
    def test_invalid_method_logged(self, mock_get_logger: MagicMock) -> None:
        """Test that an invalid SIP method triggers a warning."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        sbc = SessionBorderController()
        sbc.logger = mock_logger
        msg = {
            "method": "FOOBAR",
            "via": "v",
            "from": "f",
            "to": "t",
            "call_id": "c",
            "cseq": "1",
        }
        sbc._normalize_sip_message(msg)

        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any("Invalid SIP method" in c for c in warning_calls)

    @patch("pbx.features.session_border_controller.get_logger")
    def test_valid_methods_not_warned(self, mock_get_logger: MagicMock) -> None:
        """Test all valid SIP methods are accepted without warnings."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        sbc = SessionBorderController()
        sbc.logger = mock_logger
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
        for method in valid_methods:
            mock_logger.warning.reset_mock()
            msg = {
                "method": method,
                "via": "v",
                "from": "f",
                "to": "t",
                "call_id": "c",
                "cseq": "1",
            }
            sbc._normalize_sip_message(msg)
            warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
            assert not any("Invalid SIP method" in c for c in warning_calls), (
                f"Method {method} should be valid"
            )

    @patch("pbx.features.session_border_controller.get_logger")
    def test_method_case_insensitive(self, mock_get_logger: MagicMock) -> None:
        """Test that method validation is case-insensitive."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        sbc = SessionBorderController()
        sbc.logger = mock_logger
        msg = {
            "method": "invite",
            "via": "v",
            "from": "f",
            "to": "t",
            "call_id": "c",
            "cseq": "1",
        }
        sbc._normalize_sip_message(msg)

        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert not any("Invalid SIP method" in c for c in warning_calls)

    @patch("pbx.features.session_border_controller.get_logger")
    def test_original_message_not_mutated(self, mock_get_logger: MagicMock) -> None:
        """Test that normalization does not mutate the original dict."""
        sbc = SessionBorderController()
        original = {
            "via": "v",
            "from": "f",
            "to": "t",
            "call_id": "c",
            "cseq": "1",
            "user_agent": "SoftPhone/1.0",
        }
        original_copy = original.copy()

        sbc._normalize_sip_message(original)
        assert original == original_copy


@pytest.mark.unit
class TestDetectNAT:
    """Tests for NAT detection."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_no_nat_same_ips(self, mock_get_logger: MagicMock) -> None:
        """Test no NAT when local and public IPs match."""
        sbc = SessionBorderController()
        result = sbc.detect_nat("8.8.8.8", "8.8.8.8")
        assert result is NATType.NONE

    @patch("pbx.features.session_border_controller.get_logger")
    def test_no_nat_both_public(self, mock_get_logger: MagicMock) -> None:
        """Test no NAT when local IP is public but different from public IP."""
        sbc = SessionBorderController()
        result = sbc.detect_nat("8.8.4.4", "8.8.8.8")
        assert result is NATType.NONE

    @patch("pbx.features.session_border_controller.get_logger")
    def test_port_restricted_nat(self, mock_get_logger: MagicMock) -> None:
        """Test port-restricted NAT when all STUN tests fail."""
        sbc = SessionBorderController()
        # All STUN binding requests return None -> PORT_RESTRICTED
        with patch.object(sbc, "_stun_binding_request", return_value=None):
            result = sbc.detect_nat("192.168.1.10", "203.0.113.1")
        assert result is NATType.PORT_RESTRICTED

    @patch("pbx.features.session_border_controller.get_logger")
    def test_symmetric_nat(self, mock_get_logger: MagicMock) -> None:
        """Test symmetric NAT when mapped port changes for different destinations."""
        sbc = SessionBorderController()

        # Test I succeeds, Tests II & III fail, Test IV returns different port
        def stun_side_effect(server, port, change_request_flags=None):
            if change_request_flags is not None:
                return None  # Tests II and III fail
            if port == 3478:
                return ("203.0.113.50", 12345)  # Test I
            return ("203.0.113.50", 54321)  # Test IV — different mapped port

        with patch.object(sbc, "_stun_binding_request", side_effect=stun_side_effect):
            result = sbc.detect_nat("192.168.1.10", "203.0.113.1")
        assert result is NATType.SYMMETRIC

    @patch("pbx.features.session_border_controller.get_logger")
    def test_port_restricted_on_stun_failure(self, mock_get_logger: MagicMock) -> None:
        """Test port-restricted NAT when STUN server is unreachable (returns None)."""
        sbc = SessionBorderController()
        # _stun_binding_request catches OSError internally and returns None
        with patch.object(sbc, "_stun_binding_request", return_value=None):
            result = sbc.detect_nat("192.168.1.10", "203.0.113.1")
        assert result is NATType.PORT_RESTRICTED

    @patch("pbx.features.session_border_controller.get_logger")
    def test_detect_nat_172_private(self, mock_get_logger: MagicMock) -> None:
        """Test NAT detection for 172.16.x.x private range."""
        sbc = SessionBorderController()
        with patch.object(sbc, "_stun_binding_request", return_value=None):
            result = sbc.detect_nat("172.16.0.10", "203.0.113.1")
        assert result is NATType.PORT_RESTRICTED

    @patch("pbx.features.session_border_controller.get_logger")
    def test_detect_nat_10_private(self, mock_get_logger: MagicMock) -> None:
        """Test NAT detection for 10.x.x.x private range."""
        sbc = SessionBorderController()
        with patch.object(sbc, "_stun_binding_request", return_value=None):
            result = sbc.detect_nat("10.0.0.5", "203.0.113.1")
        assert result is NATType.PORT_RESTRICTED


@pytest.mark.unit
class TestIsPrivateIP:
    """Tests for _is_private_ip method."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_10_network(self, mock_get_logger: MagicMock) -> None:
        """Test 10.x.x.x is private."""
        sbc = SessionBorderController()
        assert sbc._is_private_ip("10.0.0.1") is True
        assert sbc._is_private_ip("10.255.255.255") is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_172_16_network(self, mock_get_logger: MagicMock) -> None:
        """Test 172.16.x.x-172.31.x.x is private."""
        sbc = SessionBorderController()
        assert sbc._is_private_ip("172.16.0.1") is True
        assert sbc._is_private_ip("172.31.255.255") is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_172_non_private(self, mock_get_logger: MagicMock) -> None:
        """Test 172.x.x.x outside 16-31 range is not private."""
        sbc = SessionBorderController()
        assert sbc._is_private_ip("172.15.0.1") is False
        assert sbc._is_private_ip("172.32.0.1") is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_192_168_network(self, mock_get_logger: MagicMock) -> None:
        """Test 192.168.x.x is private."""
        sbc = SessionBorderController()
        assert sbc._is_private_ip("192.168.0.1") is True
        assert sbc._is_private_ip("192.168.255.255") is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_public_ip(self, mock_get_logger: MagicMock) -> None:
        """Test public IP addresses are not private."""
        sbc = SessionBorderController()
        assert sbc._is_private_ip("8.8.8.8") is False
        assert sbc._is_private_ip("203.0.113.1") is False
        assert sbc._is_private_ip("1.1.1.1") is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_invalid_ip(self, mock_get_logger: MagicMock) -> None:
        """Test invalid IPs return False."""
        sbc = SessionBorderController()
        assert sbc._is_private_ip("not_an_ip") is False
        assert sbc._is_private_ip("") is False
        assert sbc._is_private_ip("999.999.999.999") is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_too_few_octets(self, mock_get_logger: MagicMock) -> None:
        """Test IP with too few octets: 10.x prefix still matches the 10/8 range."""
        sbc = SessionBorderController()
        # "10.0" splits to ["10", "0"] and octets[0]==10 returns True
        assert sbc._is_private_ip("10.0") is True
        # "192.168" splits to ["192", "168"] and matches 192.168/16 check
        assert sbc._is_private_ip("192.168") is True
        # Single octet that doesn't match any private prefix
        assert sbc._is_private_ip("8") is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_non_numeric_octets(self, mock_get_logger: MagicMock) -> None:
        """Test IP with non-numeric octets returns False."""
        sbc = SessionBorderController()
        assert sbc._is_private_ip("10.abc.0.1") is False


@pytest.mark.unit
class TestAllocateRelay:
    """Tests for media relay allocation."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_allocate_relay_success(self, mock_get_logger: MagicMock) -> None:
        """Test successful relay allocation."""
        config = _make_sbc_config(media_relay=True, public_ip="203.0.113.1")
        sbc = SessionBorderController(config)

        result = sbc.allocate_relay("call-001", "pcmu")

        assert result["success"] is True
        assert result["call_id"] == "call-001"
        assert result["rtp_port"] == 10000
        assert result["rtcp_port"] == 10001
        assert result["relay_ip"] == "203.0.113.1"
        assert result["codec"] == "pcmu"
        assert "allocated_at" in result
        assert "call-001" in sbc.relay_sessions

    @patch("pbx.features.session_border_controller.get_logger")
    def test_allocate_relay_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test relay allocation when media relay is disabled."""
        config = _make_sbc_config(media_relay=False)
        sbc = SessionBorderController(config)

        result = sbc.allocate_relay("call-001", "pcmu")
        assert result["success"] is False
        assert result["reason"] == "Media relay disabled"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_allocate_relay_already_exists(self, mock_get_logger: MagicMock) -> None:
        """Test allocation for an already-allocated call returns existing session."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)

        first = sbc.allocate_relay("call-001", "pcmu")
        second = sbc.allocate_relay("call-001", "pcmu")

        assert first is second

    @patch("pbx.features.session_border_controller.get_logger")
    def test_allocate_relay_no_ports_available(self, mock_get_logger: MagicMock) -> None:
        """Test allocation when port pool is exhausted."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)
        sbc.relay_port_pool = set()  # Empty pool

        result = sbc.allocate_relay("call-001", "pcmu")
        assert result["success"] is False
        assert result["reason"] == "No relay ports available"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_allocate_relay_only_one_port_available(self, mock_get_logger: MagicMock) -> None:
        """Test allocation fails when pool has less than 2 ports."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)
        sbc.relay_port_pool = {10000}  # Only 1 port

        result = sbc.allocate_relay("call-001", "pcmu")
        assert result["success"] is False
        assert result["reason"] == "No relay ports available"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_allocate_relay_ports_removed_from_pool(self, mock_get_logger: MagicMock) -> None:
        """Test that allocated ports are removed from the pool."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)
        _pool_before = len(sbc.relay_port_pool)

        sbc.allocate_relay("call-001", "pcmu")

        # RTP port (even) + RTCP port (odd) = 2 ports removed
        # But only even ports are in pool initially, RTCP (odd) uses discard
        # The pool has even ports: 10000, 10002, ...
        # After allocating: 10000 removed, 10001 discarded (wasn't there)
        assert 10000 not in sbc.relay_port_pool

    @patch("pbx.features.session_border_controller.get_logger")
    def test_multiple_allocations_get_different_ports(self, mock_get_logger: MagicMock) -> None:
        """Test that successive allocations use different ports."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)

        r1 = sbc.allocate_relay("call-001", "pcmu")
        r2 = sbc.allocate_relay("call-002", "pcma")

        assert r1["rtp_port"] != r2["rtp_port"]


@pytest.mark.unit
class TestReleaseRelay:
    """Tests for releasing relay sessions."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_release_existing_session(self, mock_get_logger: MagicMock) -> None:
        """Test releasing an existing relay session returns ports to pool."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)

        sbc.allocate_relay("call-001", "pcmu")
        rtp_port = sbc.relay_sessions["call-001"]["rtp_port"]
        rtcp_port = sbc.relay_sessions["call-001"]["rtcp_port"]

        sbc.release_relay("call-001")

        assert "call-001" not in sbc.relay_sessions
        assert rtp_port in sbc.relay_port_pool
        assert rtcp_port in sbc.relay_port_pool

    @patch("pbx.features.session_border_controller.get_logger")
    def test_release_nonexistent_session(self, mock_get_logger: MagicMock) -> None:
        """Test releasing a non-existent session does nothing."""
        sbc = SessionBorderController()
        # Should not raise
        sbc.release_relay("nonexistent-call")
        assert "nonexistent-call" not in sbc.relay_sessions


@pytest.mark.unit
class TestRelayRTPPacket:
    """Tests for RTP packet relay."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_relay_success(self, mock_get_logger: MagicMock) -> None:
        """Test successful RTP packet relay."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)
        sbc.allocate_relay("call-001", "pcmu")

        packet = b"\x80\x00" + b"\x00" * 158  # 160 byte RTP packet
        result = sbc.relay_rtp_packet(packet, "call-001")

        assert result is True
        assert sbc.relayed_media_bytes == 160

    @patch("pbx.features.session_border_controller.get_logger")
    def test_relay_no_session(self, mock_get_logger: MagicMock) -> None:
        """Test relay with no active session returns False."""
        sbc = SessionBorderController()

        result = sbc.relay_rtp_packet(b"\x80\x00", "nonexistent")
        assert result is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_relay_cumulative_bytes(self, mock_get_logger: MagicMock) -> None:
        """Test that relayed bytes accumulate correctly."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)
        sbc.allocate_relay("call-001", "pcmu")

        sbc.relay_rtp_packet(b"\x00" * 100, "call-001")
        sbc.relay_rtp_packet(b"\x00" * 200, "call-001")
        sbc.relay_rtp_packet(b"\x00" * 50, "call-001")

        assert sbc.relayed_media_bytes == 350

    @patch("pbx.features.session_border_controller.get_logger")
    def test_relay_empty_packet(self, mock_get_logger: MagicMock) -> None:
        """Test relay with empty packet succeeds and adds 0 bytes."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)
        sbc.allocate_relay("call-001", "pcmu")

        result = sbc.relay_rtp_packet(b"", "call-001")
        assert result is True
        assert sbc.relayed_media_bytes == 0


@pytest.mark.unit
class TestCallAdmissionControl:
    """Tests for call admission control."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_admit_call(self, mock_get_logger: MagicMock) -> None:
        """Test admitting a call under normal conditions."""
        config = _make_sbc_config(max_calls=100, max_bandwidth=100000)
        sbc = SessionBorderController(config)

        result = sbc.perform_call_admission_control({"call_id": "call-001", "codec": "pcmu"})
        assert result["admit"] is True
        assert result["allocated_bandwidth"] == 80
        assert sbc.current_bandwidth == 80
        assert "call-001" in sbc.bandwidth_by_call

    @patch("pbx.features.session_border_controller.get_logger")
    def test_reject_max_calls_reached(self, mock_get_logger: MagicMock) -> None:
        """Test rejection when max calls is reached."""
        config = _make_sbc_config(max_calls=0)
        sbc = SessionBorderController(config)

        result = sbc.perform_call_admission_control({"call_id": "call-001", "codec": "pcmu"})
        assert result["admit"] is False
        assert result["reason"] == "Maximum calls reached"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_reject_insufficient_bandwidth(self, mock_get_logger: MagicMock) -> None:
        """Test rejection when bandwidth is insufficient."""
        config = _make_sbc_config(max_bandwidth=50)
        sbc = SessionBorderController(config)
        sbc.current_bandwidth = 50  # Already at max

        result = sbc.perform_call_admission_control({"call_id": "call-001", "codec": "pcmu"})
        assert result["admit"] is False
        assert result["reason"] == "Insufficient bandwidth"

    @patch("pbx.features.session_border_controller.get_logger")
    def test_bandwidth_accumulates(self, mock_get_logger: MagicMock) -> None:
        """Test that bandwidth accumulates across calls."""
        config = _make_sbc_config(max_bandwidth=100000)
        sbc = SessionBorderController(config)

        sbc.perform_call_admission_control({"call_id": "call-001", "codec": "pcmu"})
        sbc.perform_call_admission_control({"call_id": "call-002", "codec": "opus"})

        assert sbc.current_bandwidth == 80 + 40  # pcmu + opus

    @patch("pbx.features.session_border_controller.get_logger")
    def test_unknown_codec_uses_default(self, mock_get_logger: MagicMock) -> None:
        """Test that unknown codec defaults to 80 kbps."""
        config = _make_sbc_config(max_bandwidth=100000)
        sbc = SessionBorderController(config)

        result = sbc.perform_call_admission_control(
            {"call_id": "call-001", "codec": "unknown_codec"}
        )
        assert result["allocated_bandwidth"] == 80

    @patch("pbx.features.session_border_controller.get_logger")
    def test_missing_codec_uses_default(self, mock_get_logger: MagicMock) -> None:
        """Test that missing codec key defaults to pcmu bandwidth."""
        config = _make_sbc_config(max_bandwidth=100000)
        sbc = SessionBorderController(config)

        result = sbc.perform_call_admission_control({"call_id": "call-001"})
        assert result["allocated_bandwidth"] == 80

    @patch("pbx.features.session_border_controller.get_logger")
    def test_missing_call_id_uses_unknown(self, mock_get_logger: MagicMock) -> None:
        """Test that missing call_id defaults to 'unknown'."""
        config = _make_sbc_config(max_bandwidth=100000)
        sbc = SessionBorderController(config)

        sbc.perform_call_admission_control({"codec": "pcmu"})
        assert "unknown" in sbc.bandwidth_by_call


@pytest.mark.unit
class TestEstimateCallBandwidth:
    """Tests for _estimate_call_bandwidth method."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_known_codecs(self, mock_get_logger: MagicMock) -> None:
        """Test bandwidth estimation for all known codecs."""
        sbc = SessionBorderController()
        assert sbc._estimate_call_bandwidth("pcmu") == 80
        assert sbc._estimate_call_bandwidth("pcma") == 80
        assert sbc._estimate_call_bandwidth("g722") == 80
        assert sbc._estimate_call_bandwidth("opus") == 40
        assert sbc._estimate_call_bandwidth("g729") == 30

    @patch("pbx.features.session_border_controller.get_logger")
    def test_unknown_codec(self, mock_get_logger: MagicMock) -> None:
        """Test bandwidth estimation for unknown codec defaults to 80."""
        sbc = SessionBorderController()
        assert sbc._estimate_call_bandwidth("speex") == 80
        assert sbc._estimate_call_bandwidth("") == 80


@pytest.mark.unit
class TestReleaseCallResources:
    """Tests for releasing call resources."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_release_bandwidth(self, mock_get_logger: MagicMock) -> None:
        """Test bandwidth is released when call resources are freed."""
        config = _make_sbc_config(media_relay=True, max_bandwidth=100000)
        sbc = SessionBorderController(config)

        sbc.perform_call_admission_control({"call_id": "call-001", "codec": "pcmu"})
        assert sbc.current_bandwidth == 80

        sbc.release_call_resources("call-001")
        assert sbc.current_bandwidth == 0
        assert "call-001" not in sbc.bandwidth_by_call

    @patch("pbx.features.session_border_controller.get_logger")
    def test_release_relay_ports(self, mock_get_logger: MagicMock) -> None:
        """Test relay ports are returned on resource release."""
        config = _make_sbc_config(media_relay=True)
        sbc = SessionBorderController(config)

        sbc.allocate_relay("call-001", "pcmu")
        rtp_port = sbc.relay_sessions["call-001"]["rtp_port"]

        sbc.release_call_resources("call-001")
        assert "call-001" not in sbc.relay_sessions
        assert rtp_port in sbc.relay_port_pool

    @patch("pbx.features.session_border_controller.get_logger")
    def test_release_decrements_active_sessions(self, mock_get_logger: MagicMock) -> None:
        """Test active_sessions is decremented on release."""
        sbc = SessionBorderController()
        sbc.active_sessions = 5

        sbc.release_call_resources("call-001")
        assert sbc.active_sessions == 4

    @patch("pbx.features.session_border_controller.get_logger")
    def test_release_does_not_go_below_zero(self, mock_get_logger: MagicMock) -> None:
        """Test active_sessions does not go below zero."""
        sbc = SessionBorderController()
        sbc.active_sessions = 0

        sbc.release_call_resources("call-001")
        assert sbc.active_sessions == 0

    @patch("pbx.features.session_border_controller.get_logger")
    def test_release_nonexistent_call(self, mock_get_logger: MagicMock) -> None:
        """Test releasing resources for a non-existent call is safe."""
        sbc = SessionBorderController()
        sbc.active_sessions = 3

        sbc.release_call_resources("nonexistent")
        # Should still decrement active sessions
        assert sbc.active_sessions == 2
        # No error should occur


@pytest.mark.unit
class TestRateLimiting:
    """Tests for rate limiting."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_within_rate_limit(self, mock_get_logger: MagicMock) -> None:
        """Test requests within rate limit are allowed."""
        config = _make_sbc_config(rate_limit=5)
        sbc = SessionBorderController(config)

        for _ in range(5):
            assert sbc._check_rate_limit("10.0.0.1") is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_exceeds_rate_limit(self, mock_get_logger: MagicMock) -> None:
        """Test requests exceeding rate limit are blocked."""
        config = _make_sbc_config(rate_limit=3)
        sbc = SessionBorderController(config)

        assert sbc._check_rate_limit("10.0.0.1") is True
        assert sbc._check_rate_limit("10.0.0.1") is True
        assert sbc._check_rate_limit("10.0.0.1") is True
        # 4th request exceeds limit of 3
        assert sbc._check_rate_limit("10.0.0.1") is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_rate_limit_per_ip(self, mock_get_logger: MagicMock) -> None:
        """Test rate limits are tracked per IP."""
        config = _make_sbc_config(rate_limit=2)
        sbc = SessionBorderController(config)

        assert sbc._check_rate_limit("10.0.0.1") is True
        assert sbc._check_rate_limit("10.0.0.1") is True
        assert sbc._check_rate_limit("10.0.0.1") is False  # Blocked

        # Different IP should still be allowed
        assert sbc._check_rate_limit("10.0.0.2") is True

    @patch("pbx.features.session_border_controller.get_logger")
    @patch("time.time")
    def test_rate_limit_window_expiry(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test that old requests expire from the sliding window."""
        config = _make_sbc_config(rate_limit=2)
        sbc = SessionBorderController(config)

        # First two requests at t=0
        mock_time.return_value = 1000.0
        assert sbc._check_rate_limit("10.0.0.1") is True
        assert sbc._check_rate_limit("10.0.0.1") is True
        # Third at t=0 should be blocked
        assert sbc._check_rate_limit("10.0.0.1") is False

        # Move time forward past the 1-second window
        mock_time.return_value = 1001.1
        # Old requests are expired, new request allowed
        assert sbc._check_rate_limit("10.0.0.1") is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_rate_limit_warning_logged(self, mock_get_logger: MagicMock) -> None:
        """Test that rate limit exceeded triggers a warning log."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = _make_sbc_config(rate_limit=1)
        sbc = SessionBorderController(config)
        sbc.logger = mock_logger

        sbc._check_rate_limit("10.0.0.1")  # Allowed
        sbc._check_rate_limit("10.0.0.1")  # Blocked

        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any("Rate limit exceeded" in c for c in warning_calls)


@pytest.mark.unit
class TestBlacklistWhitelist:
    """Tests for blacklist and whitelist management."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_add_to_blacklist_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test adding to blacklist when SBC is enabled."""
        config = _make_sbc_config(enabled=True)
        sbc = SessionBorderController(config)

        result = sbc.add_to_blacklist("1.2.3.4")
        assert result is True
        assert "1.2.3.4" in sbc.blacklist

    @patch("pbx.features.session_border_controller.get_logger")
    def test_add_to_blacklist_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test adding to blacklist when SBC is disabled returns False."""
        config = _make_sbc_config(enabled=False)
        sbc = SessionBorderController(config)

        result = sbc.add_to_blacklist("1.2.3.4")
        assert result is False
        assert "1.2.3.4" not in sbc.blacklist

    @patch("pbx.features.session_border_controller.get_logger")
    def test_add_to_whitelist_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test adding to whitelist when SBC is enabled."""
        config = _make_sbc_config(enabled=True)
        sbc = SessionBorderController(config)

        result = sbc.add_to_whitelist("5.6.7.8")
        assert result is True
        assert "5.6.7.8" in sbc.whitelist

    @patch("pbx.features.session_border_controller.get_logger")
    def test_add_to_whitelist_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test adding to whitelist when SBC is disabled returns False."""
        config = _make_sbc_config(enabled=False)
        sbc = SessionBorderController(config)

        result = sbc.add_to_whitelist("5.6.7.8")
        assert result is False
        assert "5.6.7.8" not in sbc.whitelist

    @patch("pbx.features.session_border_controller.get_logger")
    def test_is_blacklisted_true(self, mock_get_logger: MagicMock) -> None:
        """Test _is_blacklisted returns True for blacklisted IP."""
        sbc = SessionBorderController()
        sbc.blacklist.add("1.2.3.4")
        assert sbc._is_blacklisted("1.2.3.4") is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_is_blacklisted_false(self, mock_get_logger: MagicMock) -> None:
        """Test _is_blacklisted returns False for non-blacklisted IP."""
        sbc = SessionBorderController()
        assert sbc._is_blacklisted("1.2.3.4") is False

    @patch("pbx.features.session_border_controller.get_logger")
    def test_blacklist_duplicate(self, mock_get_logger: MagicMock) -> None:
        """Test adding same IP to blacklist twice is idempotent."""
        config = _make_sbc_config(enabled=True)
        sbc = SessionBorderController(config)

        sbc.add_to_blacklist("1.2.3.4")
        sbc.add_to_blacklist("1.2.3.4")
        assert len(sbc.blacklist) == 1

    @patch("pbx.features.session_border_controller.get_logger")
    def test_blacklist_disabled_logs_error(self, mock_get_logger: MagicMock) -> None:
        """Test that disabled SBC logs error on blacklist attempt."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = _make_sbc_config(enabled=False)
        sbc = SessionBorderController(config)
        sbc.logger = mock_logger

        sbc.add_to_blacklist("1.2.3.4")

        error_calls = [str(c) for c in mock_logger.error.call_args_list]
        assert any("not enabled" in c for c in error_calls)

    @patch("pbx.features.session_border_controller.get_logger")
    def test_whitelist_disabled_logs_error(self, mock_get_logger: MagicMock) -> None:
        """Test that disabled SBC logs error on whitelist attempt."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = _make_sbc_config(enabled=False)
        sbc = SessionBorderController(config)
        sbc.logger = mock_logger

        sbc.add_to_whitelist("1.2.3.4")

        error_calls = [str(c) for c in mock_logger.error.call_args_list]
        assert any("not enabled" in c for c in error_calls)


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics method."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_initial_statistics(self, mock_get_logger: MagicMock) -> None:
        """Test initial statistics values."""
        config = _make_sbc_config(enabled=True, topology_hiding=True, media_relay=True)
        sbc = SessionBorderController(config)

        stats = sbc.get_statistics()
        assert stats["enabled"] is True
        assert stats["total_sessions"] == 0
        assert stats["active_sessions"] == 0
        assert stats["blocked_requests"] == 0
        assert stats["relayed_media_mb"] == 0.0
        assert stats["blacklist_size"] == 0
        assert stats["whitelist_size"] == 0
        assert stats["topology_hiding"] is True
        assert stats["media_relay"] is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_statistics_after_operations(self, mock_get_logger: MagicMock) -> None:
        """Test statistics reflect state changes after operations."""
        config = _make_sbc_config(enabled=True, media_relay=True)
        sbc = SessionBorderController(config)

        # Add some state
        sbc.blacklist.add("1.1.1.1")
        sbc.blacklist.add("2.2.2.2")
        sbc.whitelist.add("3.3.3.3")
        sbc.active_sessions = 5
        sbc.total_sessions = 10
        sbc.blocked_requests = 3
        sbc.relayed_media_bytes = 1024 * 1024 * 10  # 10 MB

        stats = sbc.get_statistics()
        assert stats["blacklist_size"] == 2
        assert stats["whitelist_size"] == 1
        assert stats["active_sessions"] == 5
        assert stats["total_sessions"] == 10
        assert stats["blocked_requests"] == 3
        assert stats["relayed_media_mb"] == pytest.approx(10.0)

    @patch("pbx.features.session_border_controller.get_logger")
    def test_statistics_relayed_media_mb_conversion(self, mock_get_logger: MagicMock) -> None:
        """Test relayed media bytes to MB conversion."""
        sbc = SessionBorderController()
        sbc.relayed_media_bytes = 5242880  # 5 * 1024 * 1024

        stats = sbc.get_statistics()
        assert stats["relayed_media_mb"] == pytest.approx(5.0)


@pytest.mark.unit
class TestGetSBC:
    """Tests for the get_sbc factory function."""

    def setup_method(self) -> None:
        """Reset global _sbc before each test."""
        import pbx.features.session_border_controller as sbc_module

        sbc_module._sbc = None

    def teardown_method(self) -> None:
        """Reset global _sbc after each test."""
        import pbx.features.session_border_controller as sbc_module

        sbc_module._sbc = None

    @patch("pbx.features.session_border_controller.get_logger")
    def test_creates_new_instance(self, mock_get_logger: MagicMock) -> None:
        """Test get_sbc creates a new instance when none exists."""
        config = _make_sbc_config(enabled=True)
        sbc = get_sbc(config)

        assert sbc is not None
        assert isinstance(sbc, SessionBorderController)
        assert sbc.enabled is True

    @patch("pbx.features.session_border_controller.get_logger")
    def test_returns_singleton(self, mock_get_logger: MagicMock) -> None:
        """Test get_sbc returns the same instance on subsequent calls."""
        config = _make_sbc_config(enabled=True)
        sbc1 = get_sbc(config)
        sbc2 = get_sbc(config)

        assert sbc1 is sbc2

    @patch("pbx.features.session_border_controller.get_logger")
    def test_singleton_ignores_new_config(self, mock_get_logger: MagicMock) -> None:
        """Test that once created, get_sbc ignores new config arguments."""
        config1 = _make_sbc_config(enabled=True, max_calls=100)
        config2 = _make_sbc_config(enabled=False, max_calls=200)

        sbc1 = get_sbc(config1)
        sbc2 = get_sbc(config2)

        assert sbc1 is sbc2
        assert sbc2.enabled is True
        assert sbc2.max_calls == 100

    @patch("pbx.features.session_border_controller.get_logger")
    def test_creates_with_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test get_sbc with None config creates instance with defaults."""
        sbc = get_sbc(None)
        assert sbc is not None
        assert sbc.enabled is False


@pytest.mark.unit
class TestIntegrationScenarios:
    """Integration-style tests covering full SBC workflows."""

    @patch("pbx.features.session_border_controller.get_logger")
    def test_full_call_lifecycle(self, mock_get_logger: MagicMock) -> None:
        """Test a complete call lifecycle through the SBC."""
        config = _make_sbc_config(
            enabled=True,
            media_relay=True,
            topology_hiding=True,
            max_calls=10,
            max_bandwidth=100000,
            public_ip="203.0.113.1",
        )
        sbc = SessionBorderController(config)

        # 1. Inbound INVITE
        invite_msg = {
            "method": "INVITE",
            "via": "SIP/2.0/UDP 10.0.0.50:5060",
            "from": "sip:1001@10.0.0.50",
            "to": "sip:1002@pbx.local",
            "call_id": "call-lifecycle-001",
            "cseq": "1 INVITE",
            "sdp": "v=0\r\nc=IN IP4 10.0.0.50\r\nm=audio 5004 RTP/AVP 0",
        }
        result = sbc.process_inbound_sip(invite_msg, "10.0.0.50")
        assert result["action"] == "forward"
        # Internal IP hidden in SDP
        assert "10.0.0.50" not in result["message"]["sdp"]

        # 2. Call admission control
        admission = sbc.perform_call_admission_control(
            {"call_id": "call-lifecycle-001", "codec": "pcmu"}
        )
        assert admission["admit"] is True

        # 3. Allocate media relay
        relay = sbc.allocate_relay("call-lifecycle-001", "pcmu")
        assert relay["success"] is True

        # 4. Relay some RTP packets
        for _ in range(10):
            sbc.relay_rtp_packet(b"\x00" * 160, "call-lifecycle-001")
        assert sbc.relayed_media_bytes == 1600

        # 5. Release resources
        sbc.active_sessions = 1
        sbc.release_call_resources("call-lifecycle-001")
        assert sbc.active_sessions == 0
        assert sbc.current_bandwidth == 0
        assert "call-lifecycle-001" not in sbc.relay_sessions

    @patch("pbx.features.session_border_controller.get_logger")
    def test_blacklist_blocks_entire_flow(self, mock_get_logger: MagicMock) -> None:
        """Test that a blacklisted IP cannot process any messages."""
        config = _make_sbc_config(enabled=True)
        sbc = SessionBorderController(config)
        sbc.add_to_blacklist("10.0.0.99")

        result = sbc.process_inbound_sip(
            {"method": "INVITE", "via": "v", "from": "f", "to": "t", "call_id": "c", "cseq": "1"},
            "10.0.0.99",
        )
        assert result["action"] == "block"
        assert sbc.blocked_requests == 1

    @patch("pbx.features.session_border_controller.get_logger")
    def test_outbound_full_topology_hiding(self, mock_get_logger: MagicMock) -> None:
        """Test outbound message with all topology-hidden headers."""
        config = _make_sbc_config(topology_hiding=True, public_ip="203.0.113.1")
        sbc = SessionBorderController(config)

        msg = {
            "via": "SIP/2.0/UDP 192.168.1.10:5060;branch=z9hG4bK776",
            "contact": "<sip:user@192.168.1.10:5060>",
            "record_route": "<sip:192.168.1.10;lr>",
        }

        result = sbc.process_outbound_sip(msg)
        forwarded = result["message"]

        assert "192.168.1.10" not in forwarded["via"]
        assert "192.168.1.10" not in forwarded["contact"]
        assert "192.168.1.10" not in forwarded["record_route"]
        assert "203.0.113.1" in forwarded["via"]
        assert "203.0.113.1" in forwarded["contact"]
        assert "203.0.113.1" in forwarded["record_route"]
