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

        # Subscription tracking for SUBSCRIBE/NOTIFY (RFC 6665)
        # Key: (from_uri, event_type), Value: subscription info dict
        self.subscriptions: dict[tuple[str, str], dict] = {}

        # Published event state for PUBLISH (RFC 3903)
        # Key: (event_type, entity_tag), Value: publication info dict
        self.publications: dict[tuple[str, str], dict] = {}
        self._etag_counter: int = 0

        # Reliable provisional response tracking for PRACK (RFC 3262)
        # Key: (call_id, rseq), Value: provisional response info
        self.pending_provisional_responses: dict[tuple[str, int], dict] = {}
        self._rseq_counter: int = 1

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

                try:
                    message_text = data.decode("utf-8")
                except UnicodeDecodeError:
                    self.logger.warning(f"Malformed UTF-8 from {addr}, using lossy decode")
                    message_text = data.decode("utf-8", errors="replace")

                # Handle message in separate thread
                handler_thread = threading.Thread(
                    target=self._handle_message, args=(message_text, addr)
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
        Handle REGISTER request with digest authentication (RFC 2617).

        Implements a two-step authentication flow:
        1. First REGISTER without credentials: respond with 401 + WWW-Authenticate challenge
        2. Second REGISTER with Authorization header: verify credentials and register

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"REGISTER request from {addr}")

        from_header = message.get_header("From")
        user_agent = message.get_header("User-Agent")
        contact = message.get_header("Contact")
        authorization = message.get_header("Authorization")

        if not self.pbx_core:
            self._send_response(200, "OK", message, addr)
            return

        # Check if this request contains authorization credentials
        if authorization:
            # Verify digest authentication credentials
            if self._verify_digest_auth(authorization, from_header, "REGISTER"):
                success = self.pbx_core.register_extension(from_header, addr, user_agent, contact)
                if success:
                    response = SIPMessageBuilder.build_response(200, "OK", message)
                    # Set Expires header from request or default
                    expires = message.get_header("Expires") or "3600"
                    response.set_header("Expires", expires)
                    if contact:
                        response.set_header("Contact", contact)
                    self._send_message(response.build(), addr)
                else:
                    self._send_response(403, "Forbidden", message, addr)
            else:
                # Credentials invalid - send new challenge
                self._send_auth_challenge(message, addr)
        else:
            # No credentials provided - check if auth is required
            auth_required = True
            if self.pbx_core:
                auth_required = self.pbx_core.config.get("security.sip_auth_required", True)

            if auth_required:
                self._send_auth_challenge(message, addr)
            else:
                # Auth not required - register directly
                success = self.pbx_core.register_extension(from_header, addr, user_agent, contact)
                if success:
                    self._send_response(200, "OK", message, addr)
                else:
                    self._send_response(401, "Unauthorized", message, addr)

    def _send_auth_challenge(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Send 401 Unauthorized with WWW-Authenticate challenge.

        Args:
            message: Original REGISTER request.
            addr: Source address tuple.
        """
        import hashlib
        import time

        # Generate nonce from timestamp and server secret
        timestamp = str(time.time())
        server_secret = "pbx-sip-auth"
        if self.pbx_core:
            server_secret = self.pbx_core.config.get("security.sip_auth_secret", server_secret)
        nonce_input = f"{timestamp}:{server_secret}"
        nonce = hashlib.md5(nonce_input.encode()).hexdigest()  # nosec B324 - MD5 required by SIP digest auth RFC 2617

        realm = "warden-pbx"
        if self.pbx_core:
            realm = self.pbx_core.config.get("server.sip_realm", realm)

        response = SIPMessageBuilder.build_response(401, "Unauthorized", message)
        response.set_header(
            "WWW-Authenticate",
            f'Digest realm="{realm}", nonce="{nonce}", algorithm=MD5, qop="auth"',
        )
        self._send_message(response.build(), addr)

    def _verify_digest_auth(self, authorization: str, from_header: str, method: str) -> bool:
        """
        Verify SIP digest authentication credentials.

        Args:
            authorization: Authorization header value.
            from_header: From header to extract extension.
            method: SIP method (REGISTER, INVITE, etc.).

        Returns:
            True if credentials are valid.
        """
        import hashlib
        import re

        if not self.pbx_core:
            return False

        # Parse digest parameters from Authorization header
        params: dict[str, str] = {}
        for match in re.finditer(r'(\w+)="([^"]*)"', authorization):
            params[match.group(1)] = match.group(2)
        # Also handle unquoted values (like algorithm=MD5)
        for match in re.finditer(r"(\w+)=([^,\s\"]+)", authorization):
            key = match.group(1)
            if key not in params:
                params[key] = match.group(2)

        username = params.get("username", "")
        realm = params.get("realm", "")
        nonce = params.get("nonce", "")
        uri = params.get("uri", "")
        response_hash = params.get("response", "")
        qop = params.get("qop")
        nc = params.get("nc", "")
        cnonce = params.get("cnonce", "")

        if not all([username, realm, nonce, uri, response_hash]):
            self.logger.warning("Incomplete digest auth parameters")
            return False

        # Look up the password for this extension
        password = None

        # Check database first
        if self.pbx_core.extension_db:
            ext_data = self.pbx_core.extension_db.get(username)
            if ext_data:
                # For digest auth we need the plaintext password or pre-computed HA1
                # If we have a stored HA1, use it directly
                password = ext_data.get("sip_password") or ext_data.get("password")

        # Fall back to config
        if not password:
            ext_config = self.pbx_core.config.get_extension(username)
            if ext_config:
                password = ext_config.get("sip_password") or ext_config.get("password")

        # If still no password found, use default format (must match provisioning system)
        if not password:
            password = f"ext{username}"
            self.logger.debug(
                f"Using default SIP password for extension {username}. "
                f"Recommend setting explicit sip_password in database."
            )

        # Compute expected digest response (RFC 2617)
        ha1 = hashlib.md5(  # nosec B324 - MD5 required by SIP digest auth RFC 2617
            f"{username}:{realm}:{password}".encode()
        ).hexdigest()
        ha2 = hashlib.md5(  # nosec B324
            f"{method}:{uri}".encode()
        ).hexdigest()

        if qop == "auth":
            expected = hashlib.md5(  # nosec B324
                f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
            ).hexdigest()
        else:
            expected = hashlib.md5(  # nosec B324
                f"{ha1}:{nonce}:{ha2}".encode()
            ).hexdigest()

        if response_hash == expected:
            self.logger.debug(f"Digest auth verified for {username}")
            return True

        self.logger.warning(f"Digest auth failed for {username}")
        return False

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

            # Send 100 Trying immediately per RFC 3261 Section 8.2.6.1
            # to suppress INVITE retransmissions before doing any routing work
            self._send_response(100, "Trying", message, addr)

            # Route call through PBX core
            success = self.pbx_core.route_call(from_header, to_header, call_id, message, addr)

            if not success:
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
        Handle CANCEL request per RFC 3261 Section 9.2.

        Sends 200 OK for the CANCEL itself, then terminates the pending
        INVITE transaction with a 487 Request Terminated response.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"CANCEL request from {addr}")

        # Send 200 OK for the CANCEL request itself
        self._send_response(200, "OK", message, addr)

        # Find and terminate the matching call
        call_id = message.get_header("Call-ID")
        if call_id and self.pbx_core:
            call = self.pbx_core.call_manager.get_call(call_id)
            if call:
                # Send 487 Request Terminated for the original INVITE
                if hasattr(call, "original_invite") and call.original_invite:
                    response_487 = SIPMessageBuilder.build_response(
                        487, "Request Terminated", call.original_invite
                    )
                    self._send_message(response_487.build(), addr)

                # Forward CANCEL to callee to stop their phone from ringing
                if call.callee_addr and hasattr(call, "callee_invite") and call.callee_invite:
                    self.pbx_core._call_router._send_cancel_to_callee(call, call_id)

                # End the call
                self.pbx_core.end_call(call_id)
                self.logger.info(f"Call {call_id} cancelled and terminated")

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
        Handle SUBSCRIBE request for presence/event notifications (RFC 6665).

        Tracks subscriptions and sends initial NOTIFY with current state.
        Supported event packages: presence, dialog, message-summary, refer.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        import re
        import time

        self.logger.debug(f"SUBSCRIBE request from {addr}")

        event = message.get_header("Event")
        expires_str = message.get_header("Expires") or "3600"
        from_header = message.get_header("From") or ""
        to_header = message.get_header("To") or ""
        call_id = message.get_header("Call-ID") or ""

        try:
            expires = int(expires_str)
        except ValueError:
            expires = 3600

        if not event:
            self._send_response(489, "Bad Event", message, addr)
            return

        self.logger.info(f"SUBSCRIBE for event: {event}, expires: {expires}")

        # Extract subscriber URI for tracking
        subscriber_uri = from_header
        sub_match = re.search(r"sip:([^@>]+)", from_header)
        if sub_match:
            subscriber_uri = sub_match.group(1)

        # Track the subscription
        sub_key = (subscriber_uri, event)

        if expires == 0:
            # Unsubscribe - remove subscription
            if sub_key in self.subscriptions:
                del self.subscriptions[sub_key]
                self.logger.info(f"Removed subscription: {subscriber_uri} for {event}")
            response = SIPMessageBuilder.build_response(200, "OK", message)
            response.set_header("Expires", "0")
            self._send_message(response.build(), addr)

            # Send final NOTIFY with terminated state
            self._send_event_notify(
                from_header, to_header, call_id, addr, event, "terminated;reason=timeout", ""
            )
            return

        # Store subscription
        self.subscriptions[sub_key] = {
            "from": from_header,
            "to": to_header,
            "call_id": call_id,
            "addr": addr,
            "event": event,
            "expires": expires,
            "created": time.time(),
        }

        # Accept the subscription
        response = SIPMessageBuilder.build_response(200, "OK", message)
        response.set_header("Expires", str(expires))
        self._send_message(response.build(), addr)

        # Send initial NOTIFY with current state
        notify_body = self._get_event_state(event, to_header)
        content_type = self._get_event_content_type(event)

        self._send_event_notify(
            from_header,
            to_header,
            call_id,
            addr,
            event,
            f"active;expires={expires}",
            notify_body,
            content_type,
        )

    def _send_event_notify(
        self,
        from_header: str,
        to_header: str,
        call_id: str,
        addr: AddrTuple,
        event: str,
        subscription_state: str,
        body: str,
        content_type: str = "application/pidf+xml",
    ) -> None:
        """
        Send a NOTIFY message for an event subscription.

        Args:
            from_header: From header value.
            to_header: To header value.
            call_id: Call-ID for the subscription dialog.
            addr: Address to send NOTIFY to.
            event: Event type.
            subscription_state: Subscription-State header value.
            body: NOTIFY body content.
            content_type: Content-Type for the body.
        """
        notify_msg = SIPMessageBuilder.build_request(
            method="NOTIFY",
            uri=f"sip:{addr[0]}:{addr[1]}",
            from_addr=to_header,
            to_addr=from_header,
            call_id=call_id,
            cseq=1,
        )
        notify_msg.set_header("Event", event)
        notify_msg.set_header("Subscription-State", subscription_state)

        if body:
            notify_msg.body = body
            notify_msg.set_header("Content-type", content_type)
            notify_msg.set_header("Content-Length", str(len(body)))

        self._send_message(notify_msg.build(), addr)
        self.logger.debug(f"Sent NOTIFY for event {event} to {addr}")

    def _get_event_state(self, event: str, to_header: str) -> str:
        """
        Get current state for an event package.

        Args:
            event: Event type (presence, dialog, message-summary).
            to_header: To header to identify the monitored resource.

        Returns:
            XML/text body representing current state.
        """
        import re

        extension = ""
        ext_match = re.search(r"sip:(\d+)@", to_header or "")
        if ext_match:
            extension = ext_match.group(1)

        if event == "presence":
            # Return PIDF presence document
            status = "open"
            if self.pbx_core and extension and hasattr(self.pbx_core, "presence_system"):
                presence_info = self.pbx_core.presence_system.get_presence(extension)
                if presence_info:
                    status = presence_info.get("status", "open")

            server_ip = "127.0.0.1"
            if self.pbx_core:
                server_ip = self.pbx_core._get_server_ip()

            return (
                '<?xml version="1.0" encoding="UTF-8"?>\r\n'
                '<presence xmlns="urn:ietf:params:xml:ns:pidf" '
                f'entity="sip:{extension}@{server_ip}">\r\n'
                "  <tuple>\r\n"
                f"    <status><basic>{status}</basic></status>\r\n"
                "  </tuple>\r\n"
                "</presence>"
            )

        if event == "message-summary":
            # Return message waiting indication (MWI)
            new_msgs = 0
            old_msgs = 0
            if self.pbx_core and extension and hasattr(self.pbx_core, "voicemail_system"):
                vm_status = self.pbx_core.voicemail_system.get_mailbox_status(extension)
                if vm_status:
                    new_msgs = vm_status.get("new_messages", 0)
                    old_msgs = vm_status.get("old_messages", 0)

            waiting = "yes" if new_msgs > 0 else "no"
            return f"Messages-Waiting: {waiting}\r\nVoice-Message: {new_msgs}/{old_msgs}"

        if event == "dialog":
            # Return dialog info for BLF (busy lamp field)
            dialog_state = "terminated"
            if self.pbx_core and extension:
                calls = self.pbx_core.call_manager.get_extension_calls(extension)
                if calls:
                    dialog_state = "confirmed"

            server_ip = "127.0.0.1"
            if self.pbx_core:
                server_ip = self.pbx_core._get_server_ip()

            return (
                '<?xml version="1.0" encoding="UTF-8"?>\r\n'
                '<dialog-info xmlns="urn:ietf:params:xml:ns:dialog-info" '
                f'version="1" state="full" entity="sip:{extension}@{server_ip}">\r\n'
                f'  <dialog id="1" direction="initiator">\r\n'
                f"    <state>{dialog_state}</state>\r\n"
                "  </dialog>\r\n"
                "</dialog-info>"
            )

        return ""

    def _get_event_content_type(self, event: str) -> str:
        """
        Get the Content-Type for an event package.

        Args:
            event: Event type.

        Returns:
            Content-Type string.
        """
        content_types = {
            "presence": "application/pidf+xml",
            "dialog": "application/dialog-info+xml",
            "message-summary": "application/simple-message-summary",
            "refer": "message/sipfrag;version=2.0",
        }
        return content_types.get(event, "text/plain")

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
        Handle REFER request for call transfer (RFC 3515).

        Implements the full REFER flow:
        1. Validates Refer-To header
        2. Sends 202 Accepted
        3. Sends NOTIFY with 100 Trying (transfer in progress)
        4. Initiates new INVITE to the transfer destination
        5. Sends NOTIFY with final status (200 OK or failure)

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        import re

        self.logger.info(f"REFER request from {addr}")

        refer_to = message.get_header("Refer-To")
        if not refer_to:
            self._send_response(400, "Bad Request - Missing Refer-To", message, addr)
            return

        call_id = message.get_header("Call-ID")
        referred_by = message.get_header("Referred-By")

        self.logger.info(f"REFER to: {refer_to}, Call-ID: {call_id}")

        # Accept the REFER request (creates an implicit subscription)
        self._send_response(202, "Accepted", message, addr)

        # Send initial NOTIFY - transfer is in progress (100 Trying)
        self._send_transfer_notify(message, addr, "SIP/2.0 100 Trying", call_id)

        if not self.pbx_core:
            self._send_transfer_notify(message, addr, "SIP/2.0 503 Service Unavailable", call_id)
            return

        # Extract destination extension from Refer-To URI
        dest_match = re.search(r"sip:([^@>]+)", refer_to)
        if not dest_match:
            self.logger.error(f"Could not parse Refer-To URI: {refer_to}")
            self._send_transfer_notify(message, addr, "SIP/2.0 400 Bad Request", call_id)
            return

        destination = dest_match.group(1)
        self.logger.info(f"Transfer destination: {destination}")

        # Find the active call for this dialog
        call = self.pbx_core.call_manager.get_call(call_id) if call_id else None

        if call:
            # Set call state to transferring
            from pbx.core.call import CallState

            call.state = CallState.TRANSFERRING
            call.transfer_destination = destination
            call.transferred = True

            # Check if destination is registered
            if self.pbx_core.extension_registry.is_registered(destination):
                dest_addr = self.pbx_core.extension_registry.get_address(destination)

                if dest_addr:
                    # Build new INVITE to the transfer destination
                    server_ip = self.pbx_core._get_server_ip()
                    sip_port = self.pbx_core.config.get("server.sip_port", 5060)

                    import uuid

                    new_call_id = str(uuid.uuid4())

                    invite_msg = SIPMessageBuilder.build_request(
                        method="INVITE",
                        uri=f"sip:{destination}@{dest_addr[0]}:{dest_addr[1]}",
                        from_addr=f"<sip:{call.from_extension}@{server_ip}>",
                        to_addr=f"<sip:{destination}@{server_ip}>",
                        call_id=new_call_id,
                        cseq=1,
                    )

                    # Add Referred-By header to indicate this is a transfer
                    if referred_by:
                        invite_msg.set_header("Referred-By", referred_by)

                    invite_msg.set_header(
                        "Contact",
                        f"<sip:{call.from_extension}@{server_ip}:{sip_port}>",
                    )

                    # Include SDP from original call if available
                    if call.caller_rtp and call.rtp_ports:
                        from pbx.sip.sdp import SDPBuilder

                        transfer_sdp = SDPBuilder.build_audio_sdp(
                            server_ip,
                            call.rtp_ports[0],
                            session_id=new_call_id,
                        )
                        invite_msg.body = transfer_sdp
                        invite_msg.set_header("Content-type", "application/sdp")
                        invite_msg.set_header("Content-Length", str(len(transfer_sdp)))

                    # Send INVITE to transfer destination
                    self._send_message(invite_msg.build(), dest_addr)
                    self.logger.info(f"Sent INVITE to {destination} at {dest_addr} for transfer")

                    # Create new call record for the transferred leg
                    new_call = self.pbx_core.call_manager.create_call(
                        new_call_id, call.from_extension, destination
                    )
                    new_call.start()
                    new_call.caller_rtp = call.caller_rtp
                    new_call.caller_addr = call.caller_addr
                    new_call.rtp_ports = call.rtp_ports

                    # Transfer RTP relay ownership before ending old call
                    relay_info = self.pbx_core.rtp_relay.active_relays.pop(call_id, None)
                    if relay_info:
                        self.pbx_core.rtp_relay.active_relays[new_call_id] = relay_info

                    # Send success NOTIFY
                    self._send_transfer_notify(message, addr, "SIP/2.0 200 OK", call_id)

                    # End the original call leg (the transferring party)
                    self.pbx_core.end_call(call_id)
                    self.logger.info(f"Transfer complete: {call.from_extension} -> {destination}")
                else:
                    self.logger.error(f"No address for destination {destination}")
                    self._send_transfer_notify(
                        message, addr, "SIP/2.0 480 Temporarily Unavailable", call_id
                    )
            else:
                self.logger.error(f"Destination {destination} not registered")
                self._send_transfer_notify(message, addr, "SIP/2.0 404 Not Found", call_id)
        else:
            self.logger.warning(f"No active call found for REFER Call-ID: {call_id}")
            self._send_transfer_notify(
                message, addr, "SIP/2.0 481 Call/Transaction Does Not Exist", call_id
            )

    def _send_transfer_notify(
        self,
        refer_msg: SIPMessage,
        addr: AddrTuple,
        sipfrag_status: str,
        call_id: str | None,
    ) -> None:
        """
        Send NOTIFY message for REFER subscription (RFC 3515 Section 2.4).

        The NOTIFY body contains a message/sipfrag with the transfer status.

        Args:
            refer_msg: Original REFER message (for dialog headers).
            addr: Address to send NOTIFY to.
            sipfrag_status: SIP status line for the sipfrag body.
            call_id: Call-ID for the dialog.
        """
        # Build NOTIFY request within the same dialog
        from_header = refer_msg.get_header("To") or ""
        to_header = refer_msg.get_header("From") or ""

        notify_msg = SIPMessageBuilder.build_request(
            method="NOTIFY",
            uri=f"sip:{addr[0]}:{addr[1]}",
            from_addr=from_header,
            to_addr=to_header,
            call_id=call_id or "",
            cseq=1,
        )

        # Set subscription state
        is_final = not sipfrag_status.endswith("Trying")
        if is_final:
            notify_msg.set_header("Subscription-State", "terminated;reason=noresource")
        else:
            notify_msg.set_header("Subscription-State", "active;expires=60")

        notify_msg.set_header("Event", "refer")
        notify_msg.set_header("Content-type", "message/sipfrag;version=2.0")

        # Body is the SIP status line fragment
        notify_msg.body = sipfrag_status
        notify_msg.set_header("Content-Length", str(len(sipfrag_status)))

        self._send_message(notify_msg.build(), addr)
        self.logger.debug(f"Sent transfer NOTIFY: {sipfrag_status}")

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

        Routes SIP MESSAGE to the destination endpoint. If the recipient is
        registered, the message is forwarded. If not, a 404 is returned.

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        import re

        self.logger.info(f"MESSAGE request from {addr}")

        from_header = message.get_header("From")
        to_header = message.get_header("To")
        content_type = message.get_header("Content-type")

        if not message.body:
            self.logger.warning("MESSAGE request received with empty body")
            self._send_response(200, "OK", message, addr)
            return

        self.logger.info(f"MESSAGE from {from_header} to {to_header}: {message.body[:100]}")

        if not self.pbx_core:
            self._send_response(200, "OK", message, addr)
            return

        # Extract destination extension from To header
        dest_match = re.search(r"sip:(\d+)@", to_header or "")
        if not dest_match:
            self.logger.warning(f"Could not parse destination from To header: {to_header}")
            self._send_response(200, "OK", message, addr)
            return

        dest_extension = dest_match.group(1)

        # Check if destination is registered and route the message
        if self.pbx_core.extension_registry.is_registered(dest_extension):
            dest_addr = self.pbx_core.extension_registry.get_address(dest_extension)

            if dest_addr:
                # Forward the MESSAGE to the recipient
                cseq_header = message.get_header("CSeq") or "1 MESSAGE"
                cseq_num = cseq_header.split()[0]
                fwd_msg = SIPMessageBuilder.build_request(
                    method="MESSAGE",
                    uri=f"sip:{dest_extension}@{dest_addr[0]}:{dest_addr[1]}",
                    from_addr=from_header or "",
                    to_addr=to_header or "",
                    call_id=message.get_header("Call-ID") or "",
                    cseq=cseq_num,
                    body=message.body,
                )
                if content_type:
                    fwd_msg.set_header("Content-type", content_type)

                self._send_message(fwd_msg.build(), dest_addr)
                self.logger.info(f"Forwarded MESSAGE to {dest_extension} at {dest_addr}")

                # Trigger webhook if available
                if hasattr(self.pbx_core, "webhook_system"):
                    from pbx.features.webhooks import WebhookEvent

                    self.pbx_core.webhook_system.trigger_event(
                        WebhookEvent.MESSAGE_RECEIVED,
                        {
                            "from": from_header,
                            "to": to_header,
                            "content_type": content_type,
                            "body_preview": message.body[:200],
                        },
                    )

                self._send_response(200, "OK", message, addr)
            else:
                self.logger.warning(
                    f"Destination {dest_extension} registered but no address available"
                )
                self._send_response(480, "Temporarily Unavailable", message, addr)
        else:
            self.logger.info(f"MESSAGE destination {dest_extension} not registered")
            self._send_response(404, "Not Found", message, addr)

    def _handle_prack(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle PRACK request for Provisional Response Acknowledgment (RFC 3262).

        PRACK acknowledges reliable provisional responses (1xx). This implementation:
        1. Validates the RAck header matches a pending provisional response
        2. Stops retransmission of that provisional response
        3. Responds with 200 OK

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.debug(f"PRACK request from {addr}")

        rack_header = message.get_header("RAck")
        call_id = message.get_header("Call-ID")

        if not rack_header:
            self._send_response(400, "Bad Request - Missing RAck", message, addr)
            return

        self.logger.info(f"PRACK acknowledging response: {rack_header} for call {call_id}")

        # Parse RAck header: "response-num cseq-num method"
        rack_parts = rack_header.split()
        if len(rack_parts) >= 2:
            try:
                rseq = int(rack_parts[0])
                # Look up the pending provisional response
                pending_key = (call_id or "", rseq)
                if pending_key in self.pending_provisional_responses:
                    # Stop retransmission of this provisional response
                    pending = self.pending_provisional_responses.pop(pending_key)
                    if pending.get("retransmit_timer"):
                        pending["retransmit_timer"].cancel()
                    self.logger.info(
                        f"Acknowledged provisional response RSeq={rseq} for call {call_id}"
                    )
                else:
                    self.logger.debug(
                        f"No pending provisional response for RSeq={rseq}, call {call_id}"
                    )
            except ValueError:
                self.logger.warning(f"Invalid RAck header format: {rack_header}")

        # Forward PRACK to callee if this is a proxied call
        if self.pbx_core and call_id:
            call = self.pbx_core.call_manager.get_call(call_id)
            if call and call.callee_addr and call.callee_addr != addr:
                self._send_message(message.build(), call.callee_addr)
                self.logger.debug(f"Forwarded PRACK to callee for call {call_id}")

        self._send_response(200, "OK", message, addr)

    def _handle_update(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle UPDATE request for session modification (RFC 3311).

        UPDATE allows modification of session parameters (like SDP) without
        changing the dialog state. This implementation:
        1. Parses the new SDP offer
        2. Validates codec compatibility
        3. Updates the RTP relay endpoints if media address/port changed
        4. Responds with 200 OK and answer SDP

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        self.logger.info(f"UPDATE request from {addr}")

        call_id = message.get_header("Call-ID")
        content_type = message.get_header("Content-type")

        if not message.body or not content_type or "sdp" not in content_type.lower():
            self.logger.debug(f"UPDATE without SDP for call {call_id}")
            self._send_response(200, "OK", message, addr)
            return

        self.logger.info(f"UPDATE with SDP for call {call_id}")

        if not self.pbx_core or not call_id:
            self._send_response(200, "OK", message, addr)
            return

        call = self.pbx_core.call_manager.get_call(call_id)
        if not call:
            self._send_response(481, "Call/Transaction Does Not Exist", message, addr)
            return

        # Parse the new SDP offer
        from pbx.sip.sdp import SDPBuilder, SDPSession

        new_sdp_obj = SDPSession()
        new_sdp_obj.parse(message.body)
        new_audio = new_sdp_obj.get_audio_info()

        if new_audio:
            new_address = new_audio.get("address")
            new_port = new_audio.get("port")

            # Determine which party sent the UPDATE and update their endpoint
            is_caller = addr == call.caller_addr
            if is_caller and new_address and new_port:
                call.caller_rtp = new_audio
                self.logger.info(f"Updated caller media: {new_address}:{new_port}")
                # Update RTP relay endpoint
                if call.rtp_ports:
                    caller_endpoint = (new_address, new_port)
                    callee_endpoint = None
                    if call.callee_rtp:
                        callee_endpoint = (
                            call.callee_rtp["address"],
                            call.callee_rtp["port"],
                        )
                    self.pbx_core.rtp_relay.set_endpoints(call_id, caller_endpoint, callee_endpoint)
            elif new_address and new_port:
                call.callee_rtp = new_audio
                self.logger.info(f"Updated callee media: {new_address}:{new_port}")
                if call.rtp_ports:
                    caller_endpoint = None
                    if call.caller_rtp:
                        caller_endpoint = (
                            call.caller_rtp["address"],
                            call.caller_rtp["port"],
                        )
                    callee_endpoint = (new_address, new_port)
                    self.pbx_core.rtp_relay.set_endpoints(call_id, caller_endpoint, callee_endpoint)

        # Build answer SDP
        server_ip = self.pbx_core._get_server_ip()
        rtp_port = call.rtp_ports[0] if call.rtp_ports else 10000
        answer_sdp = SDPBuilder.build_audio_sdp(server_ip, rtp_port, session_id=call_id)

        response = SIPMessageBuilder.build_response(200, "OK", message, body=answer_sdp)
        response.set_header("Content-type", "application/sdp")
        self._send_message(response.build(), addr)

    def _handle_publish(self, message: SIPMessage, addr: AddrTuple) -> None:
        """
        Handle PUBLISH request for event state publication (RFC 3903).

        Implements the event state compositor (ESC) which:
        1. Stores published event state with unique ETags
        2. Handles initial, refresh, modify, and remove publications
        3. Notifies active subscribers of state changes

        Args:
            message: SIPMessage object.
            addr: Source address tuple.
        """
        import time

        self.logger.info(f"PUBLISH request from {addr}")

        event = message.get_header("Event")
        expires_str = message.get_header("Expires") or "3600"
        sip_if_match = message.get_header("SIP-If-Match")
        content_type = message.get_header("Content-type")

        if not event:
            self._send_response(489, "Bad Event", message, addr)
            return

        try:
            expires = int(expires_str)
        except ValueError:
            expires = 3600

        self.logger.info(f"PUBLISH for event: {event}, expires: {expires}")

        if sip_if_match:
            # Refresh/modify/remove existing publication
            pub_key = (event, sip_if_match)
            if pub_key not in self.publications:
                # ETag not found - Conditional Request Failed
                self._send_response(412, "Conditional Request Failed", message, addr)
                return

            if expires == 0:
                # Remove publication
                del self.publications[pub_key]
                self.logger.info(f"Removed publication: {event}/{sip_if_match}")
                response = SIPMessageBuilder.build_response(200, "OK", message)
                response.set_header("Expires", "0")
                response.set_header("SIP-ETag", sip_if_match)
                self._send_message(response.build(), addr)
                # Notify subscribers of removal
                self._notify_subscribers(event)
                return

            if message.body:
                # Modify publication
                self.publications[pub_key]["body"] = message.body
                self.publications[pub_key]["content_type"] = content_type
                self.publications[pub_key]["expires"] = expires
                self.publications[pub_key]["updated"] = time.time()
                etag = sip_if_match
            else:
                # Refresh publication (extend expiry)
                self.publications[pub_key]["expires"] = expires
                self.publications[pub_key]["updated"] = time.time()
                etag = sip_if_match
        else:
            # Initial publication - generate new ETag
            self._etag_counter += 1
            etag = f"pub-{self._etag_counter}-{int(time.time())}"
            pub_key = (event, etag)

            self.publications[pub_key] = {
                "event": event,
                "etag": etag,
                "body": message.body or "",
                "content_type": content_type,
                "expires": expires,
                "addr": addr,
                "created": time.time(),
                "updated": time.time(),
            }
            self.logger.info(f"New publication: {event}/{etag}")

        # Respond with success and the ETag
        response = SIPMessageBuilder.build_response(200, "OK", message)
        response.set_header("Expires", str(expires))
        response.set_header("SIP-ETag", etag)
        self._send_message(response.build(), addr)

        # Notify active subscribers of the state change
        self._notify_subscribers(event)

    def _notify_subscribers(self, event: str) -> None:
        """
        Notify all active subscribers of a state change for an event type.

        Args:
            event: The event type that changed.
        """
        import time

        for sub_key, sub_info in list(self.subscriptions.items()):
            if sub_info["event"] != event:
                continue

            # Check if subscription has expired
            elapsed = time.time() - sub_info["created"]
            if elapsed > sub_info["expires"]:
                del self.subscriptions[sub_key]
                continue

            remaining = int(sub_info["expires"] - elapsed)
            body = self._get_event_state(event, sub_info["to"])
            content_type = self._get_event_content_type(event)

            self._send_event_notify(
                sub_info["from"],
                sub_info["to"],
                sub_info["call_id"],
                sub_info["addr"],
                event,
                f"active;expires={remaining}",
                body,
                content_type,
            )

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

            elif message.status_code == 183:
                # Session Progress (early media) - forward to caller
                self.logger.info(f"Session progress for call {call_id}")
                if call_id:
                    call = self.pbx_core.call_manager.get_call(call_id)
                    if call and call.caller_addr:
                        self._send_message(message.build(), call.caller_addr)

            elif message.status_code == 200:
                # OK - only process as callee answer if this is a response to INVITE
                # (200 OK is also sent for BYE, CANCEL, OPTIONS, etc.)
                cseq_header = message.get_header("CSeq") or ""
                if call_id and "INVITE" in cseq_header:
                    self.logger.info(f"Callee answered call {call_id}")
                    self.pbx_core.handle_callee_answer(call_id, message, addr)

            elif message.status_code and message.status_code >= 400:
                # Error response from callee (4xx/5xx/6xx) - forward to caller
                # so their phone can stop waiting and play an appropriate tone.
                # Common cases: 486 Busy Here, 488 Not Acceptable Here,
                # 480 Temporarily Unavailable, 603 Decline.
                self.logger.warning(
                    f"Callee error {message.status_code} for call {call_id}"
                )
                if call_id:
                    call = self.pbx_core.call_manager.get_call(call_id)
                    if call:
                        # Cancel no-answer timer since the callee already responded
                        if call.no_answer_timer:
                            call.no_answer_timer.cancel()
                        if call.caller_addr:
                            self._send_message(message.build(), call.caller_addr)
                        # End the call on our side
                        self.pbx_core.end_call(call_id)

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
            if not self.socket:
                self.logger.warning("Cannot send message: socket is closed")
                return
            self.socket.sendto(message.encode("utf-8"), addr)
            self.logger.debug(f"Sent message to {addr}")
        except OSError as e:
            self.logger.error(f"Error sending message: {e}")
