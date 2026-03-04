#!/usr/bin/env python3
"""
Test WebRTC virtual extension routing (voicemail, auto attendant, paging)

Verifies that WebRTC clients can call virtual extensions and get routed
to the correct service handler sessions.
"""

import sys
from unittest.mock import MagicMock, patch

# Ensure pbx.features.voicemail can be imported even when heavy deps
# (cryptography / cffi) are unavailable in the test environment.
if "pbx.features.voicemail" not in sys.modules:
    _vm_mod = MagicMock()
    sys.modules.setdefault("pbx.features.voicemail", _vm_mod)

from pbx.core.call import Call, CallState
from pbx.features.webrtc import WebRTCGateway


class TestWebRTCVoicemailAccess:
    """Test cases for WebRTC voicemail access"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.config_file = "config.yml"

    def _make_gateway_with_mocks(
        self,
        *,
        has_aa: bool = False,
        has_paging: bool = False,
    ) -> tuple[WebRTCGateway, MagicMock, MagicMock, MagicMock]:
        """Create a WebRTC gateway with standard mocks.

        Returns (gateway, mock_pbx_core, mock_call, mock_signaling).
        """
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        # Mock call
        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = {"address": "127.0.0.1", "port": 10000, "formats": [0, 8]}
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        # Mock RTP relay with port pool
        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)
        mock_pbx_core.rtp_relay.port_pool = [30000, 30002, 30004]

        # Mock voicemail system
        mock_voicemail_system = MagicMock()
        mock_mailbox = MagicMock()
        mock_voicemail_system.get_mailbox.return_value = mock_mailbox
        mock_pbx_core.voicemail_system = mock_voicemail_system

        # Mock CDR system
        mock_pbx_core.cdr_system = MagicMock()

        # Auto attendant
        if has_aa:
            mock_pbx_core.auto_attendant = MagicMock()
            mock_pbx_core.auto_attendant.get_extension.return_value = "0"
        else:
            mock_pbx_core.auto_attendant = None

        # Paging system
        if has_paging:
            mock_pbx_core.paging_system = MagicMock()
            mock_pbx_core.paging_system.is_paging_extension.return_value = True
            mock_pbx_core.paging_system.initiate_page.return_value = "page-123"
            mock_pbx_core.paging_system.get_page_info.return_value = {
                "zone_names": "Zone A",
                "zones": [{"zone_id": "z1", "dac_device": "dac-1"}],
            }
            mock_pbx_core.paging_system.get_dac_devices.return_value = [
                {"device_id": "dac-1", "device_type": "SIP", "ip_address": "192.168.1.50"},
            ]
        else:
            mock_pbx_core.paging_system = None

        # Create gateway
        gateway = WebRTCGateway(mock_pbx_core)

        # Mock session
        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = (
            "v=0\r\no=- 123 456 IN IP4 127.0.0.1\r\ns=-\r\n"
            "t=0 0\r\nm=audio 10000 RTP/AVP 0 8\r\nc=IN IP4 127.0.0.1\r\n"
        )

        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        return gateway, mock_pbx_core, mock_call, mock_signaling

    def test_webrtc_voicemail_pattern_detection(self) -> None:
        """Test that WebRTC gateway detects voicemail access pattern"""
        gateway, mock_pbx_core, mock_call, mock_signaling = self._make_gateway_with_mocks()

        # Mock the thread start and service media bridge
        with (
            patch("threading.Thread") as mock_thread,
            patch.object(mock_signaling, "start_service_media_bridge", return_value=40000),
        ):
            # Initiate call to voicemail
            call_id = gateway.initiate_call(
                session_id="test-session",
                target_extension="*1001",
                webrtc_signaling=mock_signaling,
            )

            # Verify call was created
            assert call_id is not None, "Call ID should be returned"

            # Verify voicemail attributes were set
            assert mock_call.voicemail_access, "Call should be marked as voicemail access"
            assert mock_call.voicemail_extension == "1001", (
                "Voicemail extension should be extracted"
            )

            # Verify call was marked as connected
            mock_call.connect.assert_called_once()

            # Verify CDR was started
            mock_pbx_core.cdr_system.start_record.assert_called_once()

            # Verify IVR session thread was started
            mock_thread.assert_called_once()
            thread_call = mock_thread.call_args
            assert thread_call[1]["daemon"], "Thread should be daemon"

            # Verify thread target is the voicemail IVR session
            assert thread_call[1]["target"] == mock_pbx_core._voicemail_ivr_session

            # Verify thread args include call_id, call, mailbox, and ivr
            args = thread_call[1]["args"]
            assert len(args) == 4, "Should have 4 arguments"
            assert args[0] == call_id, "First arg should be call_id"
            assert args[1] == mock_call, "Second arg should be call"
            assert args[2] == mock_pbx_core.voicemail_system.get_mailbox.return_value, (
                "Third arg should be mailbox"
            )
            # Fourth arg is the VoicemailIVR instance

    def test_webrtc_voicemail_invalid_pattern(self) -> None:
        """Test that invalid patterns are not treated as voicemail"""
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core._check_dialplan.return_value = False

        gateway = WebRTCGateway(mock_pbx_core)

        mock_session = MagicMock()
        mock_session.extension = "1001"

        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        # Try to initiate call to invalid extension
        call_id = gateway.initiate_call(
            session_id="test-session",
            target_extension="*99",  # Too short, should not match
            webrtc_signaling=mock_signaling,
        )

        # Should fail because dialplan check returns False
        assert call_id is None, "Call should fail for invalid extension"

    def test_webrtc_voicemail_missing_rtp_info(self) -> None:
        """Test that voicemail gracefully handles missing RTP info"""
        gateway, _mock_pbx_core, mock_call, mock_signaling = self._make_gateway_with_mocks()

        # Override: no SDP, so no caller_rtp
        mock_signaling.get_session.return_value.local_sdp = None
        mock_call.caller_rtp = None

        with patch.object(mock_signaling, "start_service_media_bridge", return_value=40000):
            call_id = gateway.initiate_call(
                session_id="test-session",
                target_extension="*1001",
                webrtc_signaling=mock_signaling,
            )

            # Call should be created even without RTP info
            assert call_id is not None, "Call should be created"

            # Voicemail attributes should still be set
            assert mock_call.voicemail_access, "Call should be marked as voicemail access"

    def test_webrtc_voicemail_relay_released(self) -> None:
        """Test that the RTP relay is released for voicemail calls"""
        gateway, mock_pbx_core, _mock_call, mock_signaling = self._make_gateway_with_mocks()

        with (
            patch("threading.Thread"),
            patch.object(mock_signaling, "start_service_media_bridge", return_value=40000),
        ):
            call_id = gateway.initiate_call(
                session_id="test-session",
                target_extension="*1001",
                webrtc_signaling=mock_signaling,
            )

            assert call_id is not None
            mock_pbx_core.rtp_relay.release_relay.assert_called_once_with(call_id)

    def test_webrtc_voicemail_service_port_allocated(self) -> None:
        """Test that a service port is popped from port pool"""
        gateway, mock_pbx_core, _mock_call, mock_signaling = self._make_gateway_with_mocks()

        initial_pool_size = len(mock_pbx_core.rtp_relay.port_pool)

        with (
            patch("threading.Thread"),
            patch.object(mock_signaling, "start_service_media_bridge", return_value=40000),
        ):
            gateway.initiate_call(
                session_id="test-session",
                target_extension="*1001",
                webrtc_signaling=mock_signaling,
            )

            # Port pool should have one less port
            assert len(mock_pbx_core.rtp_relay.port_pool) == initial_pool_size - 1


class TestWebRTCAutoAttendant:
    """Test cases for WebRTC auto attendant routing"""

    def test_webrtc_auto_attendant_routing(self) -> None:
        """Test that WebRTC calls to extension 0 route to auto attendant"""
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = {"address": "127.0.0.1", "port": 10000, "formats": [0, 8]}
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)
        mock_pbx_core.rtp_relay.port_pool = [30000, 30002]

        mock_pbx_core.cdr_system = MagicMock()

        # Set up auto attendant
        mock_pbx_core.auto_attendant = MagicMock()
        mock_pbx_core.auto_attendant.get_extension.return_value = "0"
        mock_aa_session = {"session": "welcome", "file": None}
        mock_pbx_core.auto_attendant.start_session.return_value = mock_aa_session

        mock_pbx_core.paging_system = None

        gateway = WebRTCGateway(mock_pbx_core)

        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = (
            "v=0\r\no=- 123 456 IN IP4 127.0.0.1\r\ns=-\r\n"
            "t=0 0\r\nm=audio 10000 RTP/AVP 0 8\r\nc=IN IP4 127.0.0.1\r\n"
        )
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        with (
            patch("threading.Thread") as mock_thread,
            patch.object(mock_signaling, "start_service_media_bridge", return_value=40000),
        ):
            call_id = gateway.initiate_call(
                session_id="test-session",
                target_extension="0",
                webrtc_signaling=mock_signaling,
            )

            assert call_id is not None

            # Verify AA attributes set
            assert mock_call.auto_attendant_active, "Call should be marked as AA"

            # Verify call connected
            mock_call.connect.assert_called_once()

            # Verify CDR started
            mock_pbx_core.cdr_system.start_record.assert_called_once()

            # Verify AA session started
            mock_pbx_core.auto_attendant.start_session.assert_called_once()
            assert mock_call.aa_session == mock_aa_session

            # Verify thread targets AA session handler
            mock_thread.assert_called_once()
            thread_call = mock_thread.call_args
            assert thread_call[1]["target"] == mock_pbx_core._auto_attendant_session
            assert thread_call[1]["daemon"]
            args = thread_call[1]["args"]
            assert args[0] == call_id
            assert args[1] == mock_call
            assert args[2] == mock_aa_session


class TestWebRTCPaging:
    """Test cases for WebRTC paging routing"""

    def test_webrtc_paging_routing(self) -> None:
        """Test that WebRTC calls to paging extension route to paging handler"""
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = {"address": "127.0.0.1", "port": 10000, "formats": [0, 8]}
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)
        mock_pbx_core.rtp_relay.port_pool = [30000, 30002]

        mock_pbx_core.cdr_system = MagicMock()
        mock_pbx_core.auto_attendant = None

        # Set up paging
        mock_pbx_core.paging_system = MagicMock()
        mock_pbx_core.paging_system.is_paging_extension.return_value = True
        mock_pbx_core.paging_system.initiate_page.return_value = "page-123"
        mock_pbx_core.paging_system.get_page_info.return_value = {
            "zone_names": "Zone A",
            "zones": [{"zone_id": "z1", "dac_device": "dac-1"}],
        }
        mock_pbx_core.paging_system.get_dac_devices.return_value = [
            {"device_id": "dac-1", "device_type": "SIP", "ip_address": "192.168.1.50"},
        ]

        gateway = WebRTCGateway(mock_pbx_core)

        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = (
            "v=0\r\no=- 123 456 IN IP4 127.0.0.1\r\ns=-\r\n"
            "t=0 0\r\nm=audio 10000 RTP/AVP 0 8\r\nc=IN IP4 127.0.0.1\r\n"
        )
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        with (
            patch("threading.Thread") as mock_thread,
            patch.object(mock_signaling, "start_service_media_bridge", return_value=40000),
        ):
            call_id = gateway.initiate_call(
                session_id="test-session",
                target_extension="700",
                webrtc_signaling=mock_signaling,
            )

            assert call_id is not None

            # Verify paging attributes set
            assert mock_call.paging_active, "Call should be marked as paging"
            assert mock_call.page_id == "page-123"
            assert mock_call.paging_zones == "Zone A"

            # Verify call connected
            mock_call.connect.assert_called_once()

            # Verify CDR started
            mock_pbx_core.cdr_system.start_record.assert_called_once()

            # Verify paging session thread started
            mock_thread.assert_called_once()
            thread_call = mock_thread.call_args
            assert thread_call[1]["target"] == mock_pbx_core._paging_session
            assert thread_call[1]["daemon"]

    def test_webrtc_paging_initiate_fails(self) -> None:
        """Test graceful handling when paging initiation fails"""
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = {"address": "127.0.0.1", "port": 10000, "formats": [0, 8]}
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)
        mock_pbx_core.rtp_relay.port_pool = [30000, 30002]

        mock_pbx_core.cdr_system = MagicMock()
        mock_pbx_core.auto_attendant = None

        # Paging system returns None (initiation fails)
        mock_pbx_core.paging_system = MagicMock()
        mock_pbx_core.paging_system.is_paging_extension.return_value = True
        mock_pbx_core.paging_system.initiate_page.return_value = None

        gateway = WebRTCGateway(mock_pbx_core)

        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = None
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        with patch.object(mock_signaling, "start_service_media_bridge", return_value=40000):
            call_id = gateway.initiate_call(
                session_id="test-session",
                target_extension="700",
                webrtc_signaling=mock_signaling,
            )

            # Call should still be created (page initiation failure is logged)
            assert call_id is not None


class TestWebRTCUnsupportedDialplan:
    """Test that unsupported dialplan patterns get a warning but don't crash"""

    def test_unsupported_dialplan_pattern(self) -> None:
        """Test fallback for unrecognized dialplan patterns"""
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = None
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)
        mock_pbx_core.rtp_relay.port_pool = [30000, 30002]

        mock_pbx_core.cdr_system = MagicMock()
        mock_pbx_core.auto_attendant = None
        mock_pbx_core.paging_system = None

        gateway = WebRTCGateway(mock_pbx_core)

        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = None
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        with patch.object(mock_signaling, "start_service_media_bridge", return_value=40000):
            call_id = gateway.initiate_call(
                session_id="test-session",
                target_extension="8000",  # Queue extension - not yet handled
                webrtc_signaling=mock_signaling,
            )

            # Call is created, connect() called for status polling
            assert call_id is not None
            mock_call.connect.assert_called_once()


class TestWebRTCServiceMediaBridgeFailure:
    """Test handling when service media bridge fails to start"""

    def test_bridge_failure_returns_none(self) -> None:
        """Test that call fails gracefully when bridge cannot start"""
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = None
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)
        mock_pbx_core.rtp_relay.port_pool = [30000, 30002]

        gateway = WebRTCGateway(mock_pbx_core)

        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = None
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        # Bridge fails — signaling returns None
        mock_signaling.start_service_media_bridge.return_value = None
        call_id = gateway.initiate_call(
            session_id="test-session",
            target_extension="*1001",
            webrtc_signaling=mock_signaling,
        )

        # Should return None when bridge fails
        assert call_id is None

        # Port should be returned to pool
        assert 30000 in mock_pbx_core.rtp_relay.port_pool
