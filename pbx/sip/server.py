"""
SIP Server implementation
"""

from __future__ import annotations

import socket
import threading
from typing import TYPE_CHECKING

from pbx.sip.message import SIPMessage, SIPMessageBuilder
from pbx.utils.logger import get_logger

if TYPE_CHECKING:
    from pbx.core.pbx import PBXCore

# Type alias for network address tuples
type AddrTuple = tuple[str, int]

# Valid DTMF digits for SIP INFO validation
VALID_DTMF_DIGITS: list[str] = [
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

# RFC 2833 Event Code to DTMF digit mapping (for SIP INFO messages that send event codes)
# Some phones send "Signal=11" instead of "Signal=#"
RFC2833_EVENT_TO_DTMF: dict[str, str] = {
    "0": "0",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "10": "*",
    "11": "#",
    "12": "A",
    "13": "B",
    "14": "C",
    "15": "D",
}


class SIPServer:
    """SIP server for handling registration and calls."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5060,
        pbx_core: PBXCore | None = None,  # nosec B104 - SIP server needs to bind all interfaces
    ) -> None:
        """
        Initialize SIP server.

        Args:
            host: Host to bind to.
            port: Port to bind to.
            pbx_core: Reference to PBX core.
        """
        self.host: str = host
        self.port: int = port
        self.pbx_core: PBXCore | None = pbx_core
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.running: bool = False

    def start(self) -> bool:
        """
        Start SIP server.

        Returns:
            True if the server started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # set socket timeout to allow periodic checking of running flag
            self.socket.settimeout(1.0)
            self.socket.bind((self.host, self.port))
            self.running = True

            self.logger.info(f"SIP server started on {self.host}:{self.port}")

            # Start listening thread
            listen_thread = threading.Thread(target=self._listen)
            listen_thread.daemon = True
            listen_thread.start()

            return True
        except OSError as e:
            self.logger.error(f"Failed to start SIP server: {e}")
            return False

    def stop(self) -> None:
        """Stop SIP server."""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info("SIP server stopped")

    def _listen(self) -> None:
        """Listen for incoming SIP messages."""
        self.logger.info("SIP server listening for messages...")

        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)

                # Handle message in separate thread
                handler_thread = threading.Thread(
                    target=self._handle_message, args=(data.decode("utf-8"), addr)
                )
                handler_thread.daemon = True
                handler_thread.start()

            except TimeoutError:
                # Timeout allows us to check running flag periodically
                continue
            except OSError as e:
                if self.running:
                    self.logger.error(f"Error receiving message: {e}")

        self.logger.info("SIP server listening thread stopped")

    def _handle_message(self, raw_message: str, addr: AddrTuple) -> None:
        """
        Handle incoming SIP message.

        Args:
            raw_message: Raw SIP message string.
            addr: Source address tuple (host, port).
        """
        try:
            message = SIPMessage(raw_message)

            self.logger.debug(f"Received {message.method or message.status_code} from {addr}")

            if message.is_request():
                self._handle_request(message, addr)
            else:
                self._handle_response(message, addr)

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def _handle_request(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle SIP request.

        Args:
            message: SIPMessage object.
            addr: Source address.
        """
        method = message.method

        if method == "REGISTER":
            self._handle_register(message, addr)
        elif method == "INVITE":
            self._handle_invite(message, addr)
        elif method == "ACK":
            self._handle_ack(message, addr)
        elif method == "BYE":
            self._handle_bye(message, addr)
        elif method == "CANCEL":
            self._handle_cancel(message, addr)
        elif method == "OPTIONS":
            self._handle_options(message, addr)
        elif method == "SUBSCRIBE":
            self._handle_subscribe(message, addr)
        elif method == "NOTIFY":
            self._handle_notify(message, addr)
        elif method == "REFER":
            self._handle_refer(message, addr)
        elif method == "INFO":
            self._handle_info(message, addr)
        elif method == "MESSAGE":
            self._handle_sip_message_method(message, addr)
        elif method == "PRACK":
            self._handle_prack(message, addr)
        elif method == "UPDATE":
            self._handle_update(message, addr)
        elif method == "PUBLISH":
            self._handle_publish(message, addr)
        else:
            self.logger.warning(f"Unhandled SIP method: {method}")
            self._send_response(405, "Method Not Allowed", message, addr)

    def _handle_register(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle REGISTER request.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"REGISTER request from {addr}")

        # Extract extension from URI or From header
        from_header = message.get_header("From")

        # Extract additional registration info
        user_agent = message.get_header("User-Agent")
        contact = message.get_header("Contact")

        if self.pbx_core:
            # Simple registration - in production, verify credentials
            success = self.pbx_core.register_extension(from_header, addr, user_agent, contact)

            if success:
                self._send_response(200, "OK", message, addr)
            else:
                self._send_response(401, "Unauthorized", message, addr)
        else:
            self._send_response(200, "OK", message, addr)

    def _handle_invite(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle INVITE request.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"INVITE request from {addr}")

        if self.pbx_core:
            # Extract call information
            from_header = message.get_header("From")
            to_header = message.get_header("To")
            call_id = message.get_header("Call-ID")

            # Route call through PBX core
            success = self.pbx_core.route_call(from_header, to_header, call_id, message, addr)

            if success:
                self._send_response(100, "Trying", message, addr)
                # Actual call setup would continue asynchronously
            else:
                self._send_response(404, "Not Found", message, addr)
        else:
            self._send_response(200, "OK", message, addr)

    def _handle_ack(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle ACK request.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"ACK request from {addr}")

        # Forward ACK to complete the three-way handshake
        if self.pbx_core:
            call_id = message.get_header("Call-ID")
            if call_id:
                call = self.pbx_core.call_manager.get_call(call_id)
                if call and call.callee_addr:
                    # Forward ACK to callee
                    self._send_message(message.build(), call.callee_addr)
                    self.logger.debug(f"Forwarded ACK to callee for call {call_id}")

        # ACK is not responded to

    def _handle_bye(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle BYE request.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        call_id = message.get_header("Call-ID")
        self.logger.info("")
        self.logger.info(">>> BYE REQUEST RECEIVED <<<")
        self.logger.info(f"  Call ID: {call_id}")
        self.logger.info(f"  From: {addr}")

        if self.pbx_core:
            call = self.pbx_core.call_manager.get_call(call_id)

            # Forward BYE to the other party in the call if present
            if call:
                self.logger.info(
                    f"  Call type: {'Voicemail Access' if hasattr(call, 'voicemail_access') and call.voicemail_access else 'Regular Call'}"
                )
                self.logger.info(f"  Call State: {call.state}")
                if hasattr(call, "voicemail_extension"):
                    self.logger.info(f"  Voicemail Extension: {call.voicemail_extension}")
                # Determine which party sent BYE and forward to the other
                other_party_addr: AddrTuple | None = None

                if call.caller_addr and call.caller_addr == addr:
                    # Caller sent BYE, forward to callee
                    other_party_addr = call.callee_addr
                    self.logger.debug(
                        f"BYE from caller, forwarding to callee at {other_party_addr}"
                    )
                elif call.callee_addr and call.callee_addr == addr:
                    # Callee sent BYE, forward to caller
                    other_party_addr = call.caller_addr
                    self.logger.debug(
                        f"BYE from callee, forwarding to caller at {other_party_addr}"
                    )

                # Forward BYE to the other party if they exist
                if other_party_addr:
                    try:
                        self._send_message(message.build(), other_party_addr)
                        self.logger.info(f"Forwarded BYE to other party at {other_party_addr}")
                    except Exception as e:
                        self.logger.error(f"Failed to forward BYE to other party: {e}")

            # End the call internally
            self.logger.info(f"  Processing BYE - ending call {call_id}")
            self.pbx_core.end_call(call_id)
            self.logger.info(f"  Call {call_id} ended")
        else:
            self.logger.info(f"  Call {call_id} not found in call manager")

        self._send_response(200, "OK", message, addr)
        self.logger.info(f"  Sent 200 OK response to {addr}")
        self.logger.info("")

    def _handle_cancel(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle CANCEL request.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"CANCEL request from {addr}")
        self._send_response(200, "OK", message, addr)

    def _handle_options(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle OPTIONS request.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"OPTIONS request from {addr}")
        response = SIPMessageBuilder.build_response(200, "OK", message)
        response.set_header(
            "Allow",
            "INVITE, ACK, BYE, CANCEL, OPTIONS, REGISTER, SUBSCRIBE, NOTIFY, INFO, REFER, MESSAGE, PRACK, UPDATE, PUBLISH",
        )
        self._send_message(response.build(), addr)

    def _handle_subscribe(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle SUBSCRIBE request for presence/event notifications.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"SUBSCRIBE request from {addr}")

        # Get the event type being subscribed to
        event = message.get_header("Event")
        expires = message.get_header("Expires") or "3600"

        if event:
            self.logger.info(f"SUBSCRIBE for event: {event}, expires: {expires}")

        # Accept the subscription (basic implementation)
        # In full implementation, would track subscriptions and send NOTIFY
        # updates
        response = SIPMessageBuilder.build_response(200, "OK", message)
        response.set_header("Expires", expires)
        self._send_message(response.build(), addr)

        # Optionally send initial NOTIFY (would need full NOTIFY
        # implementation)

    def _handle_notify(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle NOTIFY request.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"NOTIFY request from {addr}")
        # Acknowledge the notification
        self._send_response(200, "OK", message, addr)

    def _handle_refer(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle REFER request for call transfer.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"REFER request from {addr}")

        # Get the Refer-To header
        refer_to = message.get_header("Refer-To")
        if not refer_to:
            self._send_response(400, "Bad Request - Missing Refer-To", message, addr)
            return

        self.logger.info(f"REFER to: {refer_to}")

        # Accept the REFER request
        self._send_response(202, "Accepted", message, addr)

        # In a full implementation, would initiate new call to refer-to destination
        # and send NOTIFY messages about transfer progress

    def _handle_info(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle INFO request (typically used for DTMF signaling).

        SIP INFO can carry DTMF digits in the message body with Content-type:
        - application/dtmf-relay (RFC 2833 style)
        - application/dtmf (simple format)

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"INFO request from {addr}")

        # Get call context
        call_id = message.get_header("Call-ID")
        content_type = message.get_header("Content-type")

        # Extract DTMF digit from message body
        dtmf_digit: str | None = None
        if message.body and content_type:
            content_type_lower = content_type.lower()

            # Only process DTMF-related content types (handle charset and other
            # parameters)
            if content_type_lower.startswith(("application/dtmf-relay", "application/dtm")):
                # Parse DTMF from body
                # Format can be:
                # Signal=1
                # Signal=1\nDuration=160
                body_lines = message.body.strip().split("\n")
                for line in body_lines:
                    if line.startswith("Signal="):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            digit = parts[1].strip()

                            # Check if it's already a valid DTMF digit
                            # character
                            if digit in VALID_DTMF_DIGITS:
                                dtmf_digit = digit
                                break
                            # Check if it's an RFC 2833 event code (some phones
                            # send "11" for "#")
                            if digit in RFC2833_EVENT_TO_DTMF:
                                dtmf_digit = RFC2833_EVENT_TO_DTMF[digit]
                                self.logger.debug(
                                    f"Converted RFC 2833 event code {digit} to DTMF digit {dtmf_digit}"
                                )
                                break
                            self.logger.warning(f"Invalid DTMF digit in SIP INFO: {digit}")
                        break

                if dtmf_digit:
                    self.logger.info(f"Received DTMF via SIP INFO: {dtmf_digit} for call {call_id}")

                    # Deliver DTMF to PBX core for processing
                    if self.pbx_core and call_id:
                        self.pbx_core.handle_dtmf_info(call_id, dtmf_digit)

        # Always respond with 200 OK to INFO requests
        self._send_response(200, "OK", message, addr)

    def _handle_sip_message_method(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle MESSAGE request for instant messaging (RFC 3428).

        MESSAGE is used to send instant messages between SIP endpoints.
        The message body typically contains text/plain content.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"MESSAGE request from {addr}")

        # Get message details
        from_header = message.get_header("From")
        to_header = message.get_header("To")
        content_type = message.get_header("Content-type")

        if message.body:
            self.logger.info(f"MESSAGE from {from_header} to {to_header}: {message.body[:100]}")

            # Forward message to PBX core if available for delivery
            if self.pbx_core:
                # In full implementation, would route message to recipient
                # For now, log and accept
                self.logger.debug(f"MESSAGE content-type: {content_type}")
                self.logger.debug(f"MESSAGE body: {message.body}")
        else:
            self.logger.warning("MESSAGE request received with empty body")

        # Accept the message
        self._send_response(200, "OK", message, addr)

    def _handle_prack(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle PRACK request for Provisional Response Acknowledgment (RFC 3262).

        PRACK is used to acknowledge provisional responses (1xx) reliably.
        This enables reliable transmission of provisional responses like 180 Ringing.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"PRACK request from {addr}")

        # Get RAck header which identifies the provisional response being
        # acknowledged
        rack_header = message.get_header("RAck")
        call_id = message.get_header("Call-ID")

        if rack_header:
            self.logger.info(f"PRACK acknowledging response: {rack_header} for call {call_id}")

        # In full implementation, would:
        # 1. Verify RAck matches a sent reliable provisional response
        # 2. Stop retransmitting that provisional response
        # 3. Continue with call establishment

        # Accept the PRACK
        self._send_response(200, "OK", message, addr)

    def _handle_update(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle UPDATE request for session modification (RFC 3311).

        UPDATE allows modification of session parameters (like SDP) without
        changing the dialog state. Unlike re-INVITE, it cannot be used to
        change the remote target or route set.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"UPDATE request from {addr}")

        call_id = message.get_header("Call-ID")
        content_type = message.get_header("Content-type")

        # Check if this is a session update with SDP
        if message.body and content_type and "sdp" in content_type.lower():
            self.logger.info(f"UPDATE with SDP for call {call_id}")

            # In full implementation, would:
            # 1. Parse SDP to understand requested changes
            # 2. Validate changes are acceptable
            # 3. Update media session parameters
            # 4. Respond with 200 OK and answer SDP

            # For now, accept the update
            self._send_response(200, "OK", message, addr)
        else:
            # UPDATE without SDP body
            self.logger.debug(f"UPDATE without SDP for call {call_id}")
            self._send_response(200, "OK", message, addr)

    def _handle_publish(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle PUBLISH request for event state publication (RFC 3903).

        PUBLISH is used to publish event state to an event state compositor (ESC).
        Common uses include publishing presence information, dialog state, etc.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"PUBLISH request from {addr}")

        # Get event and expires headers
        event = message.get_header("Event")
        expires = message.get_header("Expires") or "3600"
        sip_if_match = message.get_header("SIP-If-Match")
        content_type = message.get_header("Content-type")

        if event:
            self.logger.info(f"PUBLISH for event: {event}, expires: {expires}")

        # In full implementation, would:
        # 1. Store published event state
        # 2. Generate entity tag (ETag) for this publication
        # 3. Notify subscribers of state changes
        # 4. Handle conditional requests using SIP-If-Match

        if sip_if_match:
            # This is a refresh or modification of existing publication
            self.logger.debug(f"PUBLISH refresh/modify with SIP-If-Match: {sip_if_match}")

        if message.body and content_type:
            self.logger.debug(f"PUBLISH body content-type: {content_type}")

        # Accept the publication
        response = SIPMessageBuilder.build_response(200, "OK", message)
        response.set_header("Expires", expires)
        # In full implementation, would set SIP-ETag header
        response.set_header("SIP-ETag", "entity-tag-placeholder")
        self._send_message(response.build(), addr)

    def _handle_response(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle SIP response.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"Received response {message.status_code} from {addr}")

        # Handle responses from callee
        if self.pbx_core and message.status_code:
            call_id = message.get_header("Call-ID")

            if message.status_code == 180:
                # Ringing - forward to caller
                self.logger.info(f"Callee ringing for call {call_id}")
                if call_id:
                    call = self.pbx_core.call_manager.get_call(call_id)
                    if call:
                        call.ring()  # Mark call as ringing
                        if call.caller_addr:
                            self._send_message(message.build(), call.caller_addr)

            elif message.status_code == 200:
                # OK - callee answered
                self.logger.info(f"Callee answered call {call_id}")
                if call_id:
                    self.pbx_core.handle_callee_answer(call_id, message, addr)

    def _send_response(
        self, status_code: int, status_text: str, request: SIPMessage, addr: AddrTuple
    ) -> None:
        """
        Send SIP response.

        Args:
            status_code: Status code.
            status_text: Status text.
            request: Original request message.
            addr: Destination address.
        """
        response = SIPMessageBuilder.build_response(status_code, status_text, request)
        self._send_message(response.build(), addr)

    def _send_message(self, message: str, addr: AddrTuple) -> None:
        """
        Send SIP message over the network.

        Args:
            message: Message string.
            addr: Destination address tuple (host, port).
        """
        try:
            self.socket.sendto(message.encode("utf-8"), addr)
            self.logger.debug(f"Sent message to {addr}")
        except OSError as e:
            self.logger.error(f"Error sending message: {e}")
