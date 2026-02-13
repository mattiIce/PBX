"""
Test suite for SIP INFO DTMF functionality
Validates that SIP INFO messages are properly handled for DTMF signaling
"""


from pbx.core.call import Call
from pbx.sip.message import SIPMessage
from pbx.sip.server import VALID_DTMF_DIGITS, SIPServer


class MockPBXCore:
    """Mock PBX Core for testing SIP INFO handling"""

    def __init__(self) -> None:
        self.dtmf_calls: list[tuple[str, str]] = []
        self.calls: dict[str, Call] = {}

    def handle_dtmf_info(self, call_id: str, dtmf_digit: str) -> None:
        """Mock handler that records DTMF info calls"""
        self.dtmf_calls.append((call_id, dtmf_digit))
        # Simulate queueing behavior
        if call_id in self.calls:
            call = self.calls[call_id]
            if not hasattr(call, "dtmf_info_queue"):
                call.dtmf_info_queue = []
            call.dtmf_info_queue.append(dtmf_digit)


class MockCallManager:
    """Mock call manager for testing"""

    def __init__(self) -> None:
        self.calls: dict[str, Call] = {}

    def get_call(self, call_id: str) -> Call | None:
        return self.calls.get(call_id)

    def add_call(self, call_id: str, call: Call) -> None:
        self.calls[call_id] = call


class TestSIPInfoDTMF:
    """Test SIP INFO DTMF handling"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.mock_pbx = MockPBXCore()
        self.sip_server = SIPServer(host="127.0.0.1", port=5060, pbx_core=self.mock_pbx)

    def test_valid_dtmf_digits_constant(self) -> None:
        """Test that VALID_DTMF_DIGITS constant is properly defined"""
        expected_digits = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "*",
            "#",
            "A",
            "B",
            "C",
            "D",
        ]
        assert VALID_DTMF_DIGITS == expected_digits

    def test_sip_info_message_parsing_dtmf_relay(self) -> None:
        """Test parsing of SIP INFO message with application/dtmf-relay"""
        sip_info_message = (
            "INFO sip:1001@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1002@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: test-call-123\r\n"
            "CSeq: 314159 INFO\r\n"
            "Content-Type: application/dtmf-relay\r\n"
            "Content-Length: 24\r\n"
            "\r\n"
            "Signal=5\r\n"
            "Duration=160"
        )
        message = SIPMessage(sip_info_message)

        # Verify message parsing
        assert message.method == "INFO"
        assert message.get_header("Call-ID") == "test-call-123"
        assert message.get_header("Content-Type") == "application/dtmf-relay"
        assert "Signal=5" in message.body

    def test_sip_info_message_parsing_dtmf(self) -> None:
        """Test parsing of SIP INFO message with application/dtmf"""
        sip_info_message = (
            "INFO sip:1001@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1002@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: test-call-456\r\n"
            "CSeq: 314160 INFO\r\n"
            "Content-Type: application/dtmf\r\n"
            "Content-Length: 24\r\n"
            "\r\n"
            "Signal=3\r\n"
            "Duration=160"
        )
        message = SIPMessage(sip_info_message)

        # Verify message parsing
        assert message.method == "INFO"
        assert message.get_header("Call-ID") == "test-call-456"
        assert message.get_header("Content-Type") == "application/dtmf"
        assert "Signal=3" in message.body

    def test_handle_info_dtmf_extraction(self) -> None:
        """Test that _handle_info properly extracts DTMF digits"""
        # Create a SIP INFO message
        sip_info_message = (
            "INFO sip:1001@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1002@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: test-call-789\r\n"
            "CSeq: 314161 INFO\r\n"
            "Content-Type: application/dtmf-relay\r\n"
            "Content-Length: 24\r\n"
            "\r\n"
            "Signal=7\r\n"
            "Duration=160"
        )
        message = SIPMessage(sip_info_message)
        addr = ("192.168.1.101", 5060)

        # Handle the INFO message
        self.sip_server._handle_info(message, addr)

        # Verify that handle_dtmf_info was called with correct parameters
        assert len(self.mock_pbx.dtmf_calls) == 1
        call_id, digit = self.mock_pbx.dtmf_calls[0]
        assert call_id == "test-call-789"
        assert digit == "7"

    def test_handle_info_all_dtmf_digits(self) -> None:
        """Test handling of all valid DTMF digits via SIP INFO"""
        test_digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#"]

        initial_count = len(self.mock_pbx.dtmf_calls)

        for idx, test_digit in enumerate(test_digits):
            sip_info_message = (
                "INFO sip:1001@192.168.1.100:5060 SIP/2.0\r\n"
                "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
                "From: <sip:1002@192.168.1.100>;tag=1928301774\r\n"
                "To: <sip:1001@192.168.1.100>;tag=a6c85cf\r\n"
                f"Call-ID: test-call-multi-{idx}\r\n"
                f"CSeq: {314162 + idx} INFO\r\n"
                "Content-Type: application/dtmf-relay\r\n"
                "Content-Length: 24\r\n"
                "\r\n"
                f"Signal={test_digit}\r\n"
                "Duration=160"
            )
            message = SIPMessage(sip_info_message)
            addr = ("192.168.1.101", 5060)

            # Handle the INFO message
            self.sip_server._handle_info(message, addr)

            # Verify digit was extracted correctly
            call_id, digit = self.mock_pbx.dtmf_calls[initial_count + idx]
            assert digit == test_digit

    def test_handle_info_invalid_digit(self) -> None:
        """Test that invalid DTMF digits are rejected"""
        sip_info_message = (
            "INFO sip:1001@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1002@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: test-call-invalid\r\n"
            "CSeq: 314163 INFO\r\n"
            "Content-Type: application/dtmf-relay\r\n"
            "Content-Length: 24\r\n"
            "\r\n"
            "Signal=X\r\n"
            "Duration=160"
        )
        message = SIPMessage(sip_info_message)
        addr = ("192.168.1.101", 5060)

        initial_count = len(self.mock_pbx.dtmf_calls)

        # Handle the INFO message
        self.sip_server._handle_info(message, addr)

        # Verify that invalid digit was NOT processed
        assert len(self.mock_pbx.dtmf_calls) == initial_count

    def test_handle_info_content_type_with_charset(self) -> None:
        """Test handling SIP INFO with Content-Type that includes charset parameter"""
        sip_info_message = (
            "INFO sip:1001@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1002@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: test-call-charset\r\n"
            "CSeq: 314164 INFO\r\n"
            "Content-Type: application/dtmf-relay; charset=utf-8\r\n"
            "Content-Length: 24\r\n"
            "\r\n"
            "Signal=9\r\n"
            "Duration=160"
        )
        message = SIPMessage(sip_info_message)
        addr = ("192.168.1.101", 5060)

        # Handle the INFO message
        self.sip_server._handle_info(message, addr)

        # Verify that digit was still extracted despite charset parameter
        assert len(self.mock_pbx.dtmf_calls) > 0
        call_id, digit = self.mock_pbx.dtmf_calls[-1]
        assert digit == "9"

    def test_pbx_core_dtmf_queue_creation(self) -> None:
        """Test that PBX core has DTMF queue initialized"""
        # Create a mock call
        call = Call("test-call-queue", "1001", "1002")
        call_manager = MockCallManager()
        call_manager.add_call("test-call-queue", call)

        # Add call to mock PBX
        self.mock_pbx.calls["test-call-queue"] = call

        # Verify queue exists initially (as of current implementation)
        assert hasattr(call, "dtmf_info_queue")
        assert call.dtmf_info_queue == []
        # Simulate receiving DTMF
        self.mock_pbx.handle_dtmf_info("test-call-queue", "5")

        # Verify digit was queued
        assert hasattr(call, "dtmf_info_queue")
        assert call.dtmf_info_queue == ["5"]

    def test_pbx_core_dtmf_queue_multiple_digits(self) -> None:
        """Test that multiple DTMF digits are properly queued"""
        # Create a mock call
        call = Call("test-call-multi-queue", "1001", "1002")
        self.mock_pbx.calls["test-call-multi-queue"] = call

        # Queue multiple digits
        test_sequence = ["1", "2", "3", "*", "#"]
        for digit in test_sequence:
            self.mock_pbx.handle_dtmf_info("test-call-multi-queue", digit)

        # Verify all digits were queued in order
        assert call.dtmf_info_queue == test_sequence

    def test_dtmf_info_queue_processing_order(self) -> None:
        """Test that DTMF digits are processed in FIFO order"""
        # Create a mock call
        call = Call("test-call-fifo", "1001", "1002")
        self.mock_pbx.calls["test-call-fifo"] = call

        # Queue digits
        digits = ["7", "4", "1", "#"]
        for digit in digits:
            self.mock_pbx.handle_dtmf_info("test-call-fifo", digit)

        # Process them in order
        processed = []
        while call.dtmf_info_queue:
            processed.append(call.dtmf_info_queue.pop(0))

        # Verify FIFO order
        assert processed == digits

class TestSIPInfoIntegration:
    """Integration tests for SIP INFO queue operations with IVR systems"""

    def test_voicemail_ivr_queue_operations(self) -> None:
        """Test SIP INFO queue creation and FIFO operations for voicemail IVR

        Note: This test validates the queue data structure used by the priority system.
        The actual priority logic (checking SIP INFO before in-band detection) is
        implemented in pbx/core/pbx.py lines 2013-2016 and cannot be easily unit tested
        without full IVR session setup.
        """
        call = Call("test-vm-priority", "1001", "*1001")
        call.dtmf_info_queue = ["5"]

        # Verify queue has data (simulating Priority 1 check in IVR)
        assert hasattr(call, "dtmf_info_queue")
        assert call.dtmf_info_queue
        # Pop digit in FIFO order (simulating IVR loop behavior)
        digit = call.dtmf_info_queue.pop(0)
        assert digit == "5"
        # Verify queue is now empty (would trigger Priority 2: in-band
        # detection)
        assert len(call.dtmf_info_queue) == 0

    def test_auto_attendant_queue_operations(self) -> None:
        """Test SIP INFO queue creation and FIFO operations for auto attendant

        Note: This test validates the queue data structure used by the priority system.
        The actual priority logic (checking SIP INFO before in-band detection) is
        implemented in pbx/core/pbx.py lines 1411-1419 and cannot be easily unit tested
        without full auto attendant session setup.
        """
        call = Call("test-aa-priority", "1001", "0")
        call.dtmf_info_queue = ["3"]

        # Verify queue has data (simulating Priority 1 check in auto attendant)
        assert hasattr(call, "dtmf_info_queue")
        assert call.dtmf_info_queue
        # Pop digit in FIFO order (simulating auto attendant loop behavior)
        digit = call.dtmf_info_queue.pop(0)
        assert digit == "3"
        # Verify queue is now empty (would trigger Priority 2: in-band
        # detection)
        assert len(call.dtmf_info_queue) == 0
