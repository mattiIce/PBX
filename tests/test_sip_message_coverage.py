"""Comprehensive tests for pbx/sip/message.py - SIP message parser."""

from unittest.mock import MagicMock, patch

import pytest

from pbx.sip.message import SIPMessage, SIPMessageBuilder


@pytest.mark.unit
class TestSIPMessageInit:
    """Tests for SIPMessage.__init__."""

    def test_default_initialization(self) -> None:
        msg = SIPMessage()
        assert msg.method is None
        assert msg.uri is None
        assert msg.version == "SIP/2.0"
        assert msg.status_code is None
        assert msg.status_text is None
        assert msg.headers == {}
        assert msg.body == ""

    def test_init_with_raw_request(self) -> None:
        raw = "INVITE sip:1002@pbx.local SIP/2.0\r\nContent-Length: 0\r\n\r\n"
        msg = SIPMessage(raw)
        assert msg.method == "INVITE"
        assert msg.uri == "sip:1002@pbx.local"

    def test_init_with_raw_response(self) -> None:
        raw = "SIP/2.0 200 OK\r\nContent-Length: 0\r\n\r\n"
        msg = SIPMessage(raw)
        assert msg.status_code == 200
        assert msg.status_text == "OK"


@pytest.mark.unit
class TestSIPMessageParseRequest:
    """Tests for SIPMessage.parse - request parsing."""

    def test_parse_invite(self) -> None:
        raw = (
            "INVITE sip:1002@pbx.local SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.100:5060\r\n"
            "From: <sip:1001@pbx.local>;tag=abc123\r\n"
            "To: <sip:1002@pbx.local>\r\n"
            "Call-ID: call123@192.168.1.100\r\n"
            "CSeq: 1 INVITE\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.method == "INVITE"
        assert msg.uri == "sip:1002@pbx.local"
        assert msg.version == "SIP/2.0"

    def test_parse_register(self) -> None:
        raw = (
            "REGISTER sip:pbx.local SIP/2.0\r\n"
            "From: <sip:1001@pbx.local>\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.method == "REGISTER"
        assert msg.uri == "sip:pbx.local"

    def test_parse_bye(self) -> None:
        raw = "BYE sip:1002@pbx.local SIP/2.0\r\nContent-Length: 0\r\n\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.method == "BYE"

    def test_parse_request_default_version(self) -> None:
        raw = "INVITE sip:1002@pbx.local\r\n\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.method == "INVITE"
        assert msg.uri == "sip:1002@pbx.local"
        assert msg.version == "SIP/2.0"

    def test_parse_request_headers(self) -> None:
        raw = (
            "INVITE sip:1002@pbx.local SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.100:5060\r\n"
            "From: <sip:1001@pbx.local>;tag=abc123\r\n"
            "To: <sip:1002@pbx.local>\r\n"
            "Call-ID: call123\r\n"
            "CSeq: 1 INVITE\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.headers["Via"] == "SIP/2.0/UDP 192.168.1.100:5060"
        assert msg.headers["Call-ID"] == "call123"
        assert msg.headers["CSeq"] == "1 INVITE"
        assert msg.headers["Content-Length"] == "0"

    def test_parse_request_with_body(self) -> None:
        sdp_body = "v=0\r\no=user 123 0 IN IP4 192.168.1.1"
        raw = (
            "INVITE sip:1002@pbx.local SIP/2.0\r\n"
            "Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp_body)}\r\n"
            "\r\n"
            f"{sdp_body}"
        )
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.body == sdp_body


@pytest.mark.unit
class TestSIPMessageParseResponse:
    """Tests for SIPMessage.parse - response parsing."""

    def test_parse_200_ok(self) -> None:
        raw = "SIP/2.0 200 OK\r\nVia: SIP/2.0/UDP 192.168.1.100:5060\r\nContent-Length: 0\r\n\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.status_code == 200
        assert msg.status_text == "OK"
        assert msg.version == "SIP/2.0"

    def test_parse_100_trying(self) -> None:
        raw = "SIP/2.0 100 Trying\r\n\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.status_code == 100
        assert msg.status_text == "Trying"

    def test_parse_180_ringing(self) -> None:
        raw = "SIP/2.0 180 Ringing\r\n\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.status_code == 180
        assert msg.status_text == "Ringing"

    def test_parse_404_not_found(self) -> None:
        raw = "SIP/2.0 404 Not Found\r\n\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.status_code == 404
        assert msg.status_text == "Not Found"

    def test_parse_response_no_status_text(self) -> None:
        raw = "SIP/2.0 200\r\n\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.status_code == 200
        assert msg.status_text == ""

    def test_parse_response_with_body(self) -> None:
        body_text = "v=0\r\nc=IN IP4 10.0.0.1"
        raw = f"SIP/2.0 200 OK\r\nContent-Type: application/sdp\r\n\r\n{body_text}"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.body == body_text


@pytest.mark.unit
class TestSIPMessageParseEdgeCases:
    """Tests for SIPMessage.parse - edge cases."""

    def test_parse_empty_lines(self) -> None:
        msg = SIPMessage()
        msg.parse("")
        # With just one empty string from split, the first line is empty
        # The method should handle this gracefully
        assert msg.method is None
        assert msg.status_code is None

    def test_parse_malformed_request_single_word(self) -> None:
        msg = SIPMessage()
        msg.parse("INVITE\r\n\r\n")
        # Only one part, fewer than 2 -> malformed
        assert msg.method is None

    def test_parse_malformed_response_single_word(self) -> None:
        msg = SIPMessage()
        msg.parse("SIP/2.0\r\n\r\n")
        # Starts with SIP/ but only 1 part -> malformed
        assert msg.status_code is None

    def test_parse_invalid_status_code(self) -> None:
        msg = SIPMessage()
        msg.parse("SIP/2.0 abc OK\r\n\r\n")
        # Non-numeric status code
        assert msg.status_code is None

    def test_parse_header_with_colon_in_value(self) -> None:
        raw = (
            "INVITE sip:1002@pbx.local SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK\r\n"
            "\r\n"
        )
        msg = SIPMessage()
        msg.parse(raw)
        # Colon in the value part should be preserved
        assert msg.headers["Via"] == "SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK"

    def test_parse_no_body_separator(self) -> None:
        raw = "INVITE sip:1002@pbx.local SIP/2.0\r\nVia: SIP/2.0/UDP 192.168.1.100:5060\r\n"
        msg = SIPMessage()
        msg.parse(raw)
        assert msg.method == "INVITE"
        assert msg.body == ""


@pytest.mark.unit
class TestSIPMessageGetHeader:
    """Tests for SIPMessage.get_header."""

    def test_get_existing_header(self) -> None:
        msg = SIPMessage()
        msg.headers["Via"] = "SIP/2.0/UDP 192.168.1.100:5060"
        assert msg.get_header("Via") == "SIP/2.0/UDP 192.168.1.100:5060"

    def test_get_nonexistent_header(self) -> None:
        msg = SIPMessage()
        assert msg.get_header("X-Custom") is None

    def test_get_header_case_sensitive(self) -> None:
        msg = SIPMessage()
        msg.headers["Call-ID"] = "abc123"
        assert msg.get_header("Call-ID") == "abc123"
        assert msg.get_header("call-id") is None


@pytest.mark.unit
class TestSIPMessageSetHeader:
    """Tests for SIPMessage.set_header."""

    def test_set_new_header(self) -> None:
        msg = SIPMessage()
        msg.set_header("X-Custom", "value1")
        assert msg.headers["X-Custom"] == "value1"

    def test_overwrite_existing_header(self) -> None:
        msg = SIPMessage()
        msg.set_header("Via", "original")
        msg.set_header("Via", "updated")
        assert msg.headers["Via"] == "updated"


@pytest.mark.unit
class TestSIPMessageIsRequest:
    """Tests for SIPMessage.is_request."""

    def test_is_request_true(self) -> None:
        msg = SIPMessage()
        msg.method = "INVITE"
        assert msg.is_request() is True

    def test_is_request_false_for_response(self) -> None:
        msg = SIPMessage()
        msg.status_code = 200
        assert msg.is_request() is False

    def test_is_request_false_when_empty(self) -> None:
        msg = SIPMessage()
        assert msg.is_request() is False


@pytest.mark.unit
class TestSIPMessageIsResponse:
    """Tests for SIPMessage.is_response."""

    def test_is_response_true(self) -> None:
        msg = SIPMessage()
        msg.status_code = 200
        assert msg.is_response() is True

    def test_is_response_false_for_request(self) -> None:
        msg = SIPMessage()
        msg.method = "INVITE"
        assert msg.is_response() is False

    def test_is_response_false_when_empty(self) -> None:
        msg = SIPMessage()
        assert msg.is_response() is False


@pytest.mark.unit
class TestSIPMessageBuild:
    """Tests for SIPMessage.build."""

    def test_build_request(self) -> None:
        msg = SIPMessage()
        msg.method = "INVITE"
        msg.uri = "sip:1002@pbx.local"
        msg.version = "SIP/2.0"
        msg.set_header("From", "<sip:1001@pbx.local>")
        msg.set_header("Content-Length", "0")
        result = msg.build()
        assert result.startswith("INVITE sip:1002@pbx.local SIP/2.0\r\n")
        assert "From: <sip:1001@pbx.local>\r\n" in result
        assert "Content-Length: 0\r\n" in result

    def test_build_response(self) -> None:
        msg = SIPMessage()
        msg.status_code = 200
        msg.status_text = "OK"
        msg.version = "SIP/2.0"
        msg.set_header("Content-Length", "0")
        result = msg.build()
        assert result.startswith("SIP/2.0 200 OK\r\n")

    def test_build_with_body(self) -> None:
        msg = SIPMessage()
        msg.method = "INVITE"
        msg.uri = "sip:1002@pbx.local"
        msg.body = "v=0\r\nc=IN IP4 10.0.0.1"
        result = msg.build()
        assert "v=0\r\nc=IN IP4 10.0.0.1" in result

    def test_build_without_body(self) -> None:
        msg = SIPMessage()
        msg.method = "INVITE"
        msg.uri = "sip:1002@pbx.local"
        result = msg.build()
        # RFC 3261: SIP messages must end with CRLFCRLF
        assert result.endswith("\r\n\r\n")

    def test_build_preserves_header_order(self) -> None:
        msg = SIPMessage()
        msg.method = "INVITE"
        msg.uri = "sip:1002@pbx.local"
        msg.set_header("From", "alice")
        msg.set_header("To", "bob")
        msg.set_header("Call-ID", "xyz")
        result = msg.build()
        from_idx = result.index("From:")
        to_idx = result.index("To:")
        callid_idx = result.index("Call-ID:")
        assert from_idx < to_idx < callid_idx


@pytest.mark.unit
class TestSIPMessageStr:
    """Tests for SIPMessage.__str__."""

    def test_str_returns_build_output(self) -> None:
        msg = SIPMessage()
        msg.method = "INVITE"
        msg.uri = "sip:1002@pbx.local"
        assert str(msg) == msg.build()


@pytest.mark.unit
class TestSIPMessageRoundTrip:
    """Test parse->build round trip."""

    def test_request_round_trip(self) -> None:
        raw = (
            "INVITE sip:1002@pbx.local SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.100:5060\r\n"
            "From: <sip:1001@pbx.local>\r\n"
            "To: <sip:1002@pbx.local>\r\n"
            "Call-ID: call123\r\n"
            "CSeq: 1 INVITE\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        msg = SIPMessage(raw)
        built = msg.build()
        msg2 = SIPMessage(built)
        assert msg2.method == "INVITE"
        assert msg2.uri == "sip:1002@pbx.local"
        assert msg2.headers["Call-ID"] == "call123"

    def test_response_round_trip(self) -> None:
        raw = (
            "SIP/2.0 200 OK\r\n"
            "Via: SIP/2.0/UDP 192.168.1.100:5060\r\n"
            "Call-ID: call123\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        msg = SIPMessage(raw)
        built = msg.build()
        msg2 = SIPMessage(built)
        assert msg2.status_code == 200
        assert msg2.status_text == "OK"


@pytest.mark.unit
class TestSIPMessageBuilderBuildResponse:
    """Tests for SIPMessageBuilder.build_response."""

    def test_build_200_ok(self) -> None:
        request = SIPMessage()
        request.method = "INVITE"
        request.uri = "sip:1002@pbx.local"
        request.set_header("Via", "SIP/2.0/UDP 192.168.1.100:5060")
        request.set_header("From", "<sip:1001@pbx.local>")
        request.set_header("To", "<sip:1002@pbx.local>")
        request.set_header("Call-ID", "call123")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.status_code == 200
        assert response.status_text == "OK"

    def test_response_copies_via(self) -> None:
        request = SIPMessage()
        request.method = "INVITE"
        request.set_header("Via", "SIP/2.0/UDP 192.168.1.100:5060")
        request.set_header("From", "<sip:1001@pbx.local>")
        request.set_header("To", "<sip:1002@pbx.local>")
        request.set_header("Call-ID", "call123")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.get_header("Via") == "SIP/2.0/UDP 192.168.1.100:5060"

    def test_response_copies_from(self) -> None:
        request = SIPMessage()
        request.set_header("From", "<sip:1001@pbx.local>")
        request.set_header("To", "<sip:1002@pbx.local>")
        request.set_header("Call-ID", "call123")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.get_header("From") == "<sip:1001@pbx.local>"

    def test_response_copies_to(self) -> None:
        request = SIPMessage()
        request.set_header("From", "<sip:1001@pbx.local>")
        request.set_header("To", "<sip:1002@pbx.local>")
        request.set_header("Call-ID", "call123")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.get_header("To") == "<sip:1002@pbx.local>"

    def test_response_copies_call_id(self) -> None:
        request = SIPMessage()
        request.set_header("From", "<sip:1001@pbx.local>")
        request.set_header("To", "<sip:1002@pbx.local>")
        request.set_header("Call-ID", "call123")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.get_header("Call-ID") == "call123"

    def test_response_copies_cseq(self) -> None:
        request = SIPMessage()
        request.set_header("From", "<sip:1001@pbx.local>")
        request.set_header("To", "<sip:1002@pbx.local>")
        request.set_header("Call-ID", "call123")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.get_header("CSeq") == "1 INVITE"

    def test_response_without_body_has_zero_content_length(self) -> None:
        request = SIPMessage()
        request.set_header("From", "a")
        request.set_header("To", "b")
        request.set_header("Call-ID", "c")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.get_header("Content-Length") == "0"
        assert response.body == ""

    def test_response_with_body(self) -> None:
        request = SIPMessage()
        request.set_header("From", "a")
        request.set_header("To", "b")
        request.set_header("Call-ID", "c")
        request.set_header("CSeq", "1 INVITE")

        body = "v=0\r\nc=IN IP4 10.0.0.1"
        response = SIPMessageBuilder.build_response(200, "OK", request, body=body)
        assert response.body == body
        assert response.get_header("Content-Length") == str(len(body))

    def test_response_skips_missing_headers(self) -> None:
        request = SIPMessage()
        # No headers set at all
        response = SIPMessageBuilder.build_response(200, "OK", request)
        assert response.get_header("Via") is None
        assert response.get_header("From") is None
        assert response.status_code == 200

    def test_build_4xx_response(self) -> None:
        request = SIPMessage()
        request.set_header("Via", "SIP/2.0/UDP 192.168.1.100:5060")
        request.set_header("From", "<sip:1001@pbx.local>")
        request.set_header("To", "<sip:1002@pbx.local>")
        request.set_header("Call-ID", "call123")
        request.set_header("CSeq", "1 INVITE")

        response = SIPMessageBuilder.build_response(404, "Not Found", request)
        assert response.status_code == 404
        assert response.status_text == "Not Found"


@pytest.mark.unit
class TestSIPMessageBuilderBuildRequest:
    """Tests for SIPMessageBuilder.build_request."""

    def test_build_invite(self) -> None:
        request = SIPMessageBuilder.build_request(
            method="INVITE",
            uri="sip:1002@pbx.local",
            from_addr="<sip:1001@pbx.local>",
            to_addr="<sip:1002@pbx.local>",
            call_id="call123",
            cseq=1,
        )
        assert request.method == "INVITE"
        assert request.uri == "sip:1002@pbx.local"
        assert request.get_header("From") == "<sip:1001@pbx.local>"
        assert request.get_header("To") == "<sip:1002@pbx.local>"
        assert request.get_header("Call-ID") == "call123"
        assert request.get_header("CSeq") == "1 INVITE"
        assert request.get_header("Content-Length") == "0"

    def test_build_register(self) -> None:
        request = SIPMessageBuilder.build_request(
            method="REGISTER",
            uri="sip:pbx.local",
            from_addr="<sip:1001@pbx.local>",
            to_addr="<sip:1001@pbx.local>",
            call_id="reg123",
            cseq=1,
        )
        assert request.method == "REGISTER"
        assert request.get_header("CSeq") == "1 REGISTER"

    def test_build_request_with_body(self) -> None:
        body = "v=0\r\nc=IN IP4 10.0.0.1"
        request = SIPMessageBuilder.build_request(
            method="INVITE",
            uri="sip:1002@pbx.local",
            from_addr="<sip:1001@pbx.local>",
            to_addr="<sip:1002@pbx.local>",
            call_id="call123",
            cseq=1,
            body=body,
        )
        assert request.body == body
        assert request.get_header("Content-Length") == str(len(body))

    def test_build_request_with_string_cseq(self) -> None:
        request = SIPMessageBuilder.build_request(
            method="BYE",
            uri="sip:1002@pbx.local",
            from_addr="<sip:1001@pbx.local>",
            to_addr="<sip:1002@pbx.local>",
            call_id="call123",
            cseq="42",
        )
        assert request.get_header("CSeq") == "42 BYE"

    def test_build_request_is_request_type(self) -> None:
        request = SIPMessageBuilder.build_request(
            method="INVITE",
            uri="sip:1002@pbx.local",
            from_addr="<sip:1001@pbx.local>",
            to_addr="<sip:1002@pbx.local>",
            call_id="call123",
            cseq=1,
        )
        assert request.is_request() is True
        assert request.is_response() is False


@pytest.mark.unit
class TestSIPMessageBuilderAddCallerIdHeaders:
    """Tests for SIPMessageBuilder.add_caller_id_headers."""

    def test_adds_p_asserted_identity(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_caller_id_headers(msg, "1001", "John Doe", "192.168.1.1")
        pai = msg.get_header("P-Asserted-Identity")
        assert pai is not None
        assert '"John Doe"' in pai
        assert "sip:1001@192.168.1.1" in pai

    def test_adds_remote_party_id(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_caller_id_headers(msg, "1001", "John Doe", "192.168.1.1")
        rpid = msg.get_header("Remote-Party-ID")
        assert rpid is not None
        assert '"John Doe"' in rpid
        assert "sip:1001@192.168.1.1" in rpid
        assert "party=calling" in rpid
        assert "privacy=off" in rpid
        assert "screen=no" in rpid

    def test_caller_id_format(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_caller_id_headers(msg, "2000", "Jane Smith", "10.0.0.5")
        pai = msg.get_header("P-Asserted-Identity")
        assert pai == '"Jane Smith" <sip:2000@10.0.0.5>'

    def test_caller_id_rpid_format(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_caller_id_headers(msg, "2000", "Jane Smith", "10.0.0.5")
        rpid = msg.get_header("Remote-Party-ID")
        expected = '"Jane Smith" <sip:2000@10.0.0.5>;party=calling;privacy=off;screen=no'
        assert rpid == expected


@pytest.mark.unit
class TestSIPMessageBuilderAddMacAddressHeader:
    """Tests for SIPMessageBuilder.add_mac_address_header."""

    def test_adds_mac_address_colon_format(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "AA:BB:CC:DD:EE:FF")
        assert msg.get_header("X-MAC-Address") == "aa:bb:cc:dd:ee:ff"

    def test_adds_mac_address_no_separator(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "AABBCCDDEEFF")
        assert msg.get_header("X-MAC-Address") == "aa:bb:cc:dd:ee:ff"

    def test_adds_mac_address_dash_format(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "AA-BB-CC-DD-EE-FF")
        assert msg.get_header("X-MAC-Address") == "aa:bb:cc:dd:ee:ff"

    def test_mac_address_none_does_nothing(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, None)
        assert msg.get_header("X-MAC-Address") is None

    def test_mac_address_empty_string_does_nothing(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "")
        assert msg.get_header("X-MAC-Address") is None

    def test_mac_address_invalid_too_short(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "AABBCC")
        assert msg.get_header("X-MAC-Address") is None

    def test_mac_address_invalid_too_long(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "AABBCCDDEEFF00")
        assert msg.get_header("X-MAC-Address") is None

    def test_mac_address_invalid_chars(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "GGHHIIJJKKLL")
        assert msg.get_header("X-MAC-Address") is None

    def test_mac_address_lowercase_input(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "aa:bb:cc:dd:ee:ff")
        assert msg.get_header("X-MAC-Address") == "aa:bb:cc:dd:ee:ff"

    def test_mac_address_mixed_case_input(self) -> None:
        msg = SIPMessage()
        SIPMessageBuilder.add_mac_address_header(msg, "aAbBcCdDeEfF")
        assert msg.get_header("X-MAC-Address") == "aa:bb:cc:dd:ee:ff"
