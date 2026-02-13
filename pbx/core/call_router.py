"""
Call routing handler for PBX Core

Extracts call routing logic from PBXCore into a dedicated class,
including dialplan checking, call forwarding, no-answer handling,
and voicemail fallback routing.
"""

import re
import struct
import threading
import time
import traceback

from pbx.features.webhooks import WebhookEvent
from pathlib import Path


class CallRouter:
    """Handles call routing, dialplan checking, and no-answer fallback"""

    def __init__(self, pbx_core):
        """
        Initialize CallRouter with reference to PBXCore.

        Args:
            pbx_core: The PBXCore instance
        """
        self.pbx_core = pbx_core

    def route_call(self, from_header, to_header, call_id, message, from_addr):
        """
        Route call from one extension to another

        Args:
            from_header: From SIP header
            to_header: To SIP header
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Address tuple of caller

        Returns:
            True if call was routed successfully
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        pbx = self.pbx_core

        # Parse extension numbers - handle both regular extensions and special
        # patterns
        from_match = re.search(r"sip:(\d+)@", from_header)
        # Allow * prefix for voicemail access (e.g., *1001), but validate
        # format
        to_match = re.search(r"sip:(\*?\d+)@", to_header)

        if not from_match or not to_match:
            pbx.logger.warning("Could not parse extensions from headers")
            return False

        from_ext = from_match.group(1)
        to_ext = to_match.group(1)

        # Check if this is an emergency call (911) - Kari's Law compliance
        # Must be handled first for immediate routing
        if pbx.karis_law and pbx.karis_law.is_emergency_number(to_ext):
            return pbx._emergency_handler.handle_emergency_call(from_ext, to_ext, call_id, message, from_addr)

        # Check if this is an auto attendant call (extension 0)
        if pbx.auto_attendant and to_ext == pbx.auto_attendant.get_extension():
            return pbx._auto_attendant_handler.handle_auto_attendant(from_ext, to_ext, call_id, message, from_addr)

        # Check if this is a voicemail access call (*xxxx pattern)
        # Validate format: must be * followed by exactly 3 or 4 digits
        if (
            to_ext.startswith("*")
            and len(to_ext) >= 4
            and len(to_ext) <= 5
            and to_ext[1:].isdigit()
        ):
            return pbx._voicemail_handler.handle_voicemail_access(from_ext, to_ext, call_id, message, from_addr)

        # Check if this is a paging call (7xx pattern or all-call)
        if pbx.paging_system and pbx.paging_system.is_paging_extension(to_ext):
            return pbx._paging_handler.handle_paging(from_ext, to_ext, call_id, message, from_addr)

        # Check if destination extension is registered
        if not pbx.extension_registry.is_registered(to_ext):
            pbx.logger.warning(f"Extension {to_ext} is not registered")
            return False

        # Check dialplan
        if not self._check_dialplan(to_ext):
            pbx.logger.warning(f"Extension {to_ext} not allowed by dialplan")
            return False

        # Parse SDP from caller's INVITE
        caller_sdp = None
        caller_codecs = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

            if caller_sdp:
                pbx.logger.info(
                    f"Caller RTP: {caller_sdp['address']}:{caller_sdp['port']}"
                )
                # Extract caller's codec list to maintain codec compatibility
                caller_codecs = caller_sdp.get("formats", None)
                if caller_codecs:
                    pbx.logger.info(f"Caller codecs: {caller_codecs}")

        # Create call
        call = pbx.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message  # Store original INVITE for later response

        # Start CDR record for analytics
        pbx.cdr_system.start_record(call_id, from_ext, to_ext)

        # Trigger webhook event
        pbx.webhook_system.trigger_event(
            WebhookEvent.CALL_STARTED,
            {
                "call_id": call_id,
                "from_extension": from_ext,
                "to_extension": to_ext,
                "timestamp": call.start_time.isoformat() if call.start_time else None,
            },
        )

        # Allocate RTP relay
        rtp_ports = pbx.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports

            # Store caller's RTP info and set endpoint immediately to avoid
            # dropping early packets
            if caller_sdp:
                call.caller_rtp = caller_sdp
                call.caller_addr = from_addr

                # set caller's endpoint immediately to enable early RTP packet learning
                # This prevents dropping packets that arrive before the 200 OK
                # response
                caller_endpoint = (caller_sdp["address"], caller_sdp["port"])
                relay_info = pbx.rtp_relay.active_relays.get(call_id)
                if relay_info:
                    handler = relay_info["handler"]
                    # set only endpoint A for now; endpoint B will be set after
                    # 200 OK
                    handler.set_endpoints(caller_endpoint, None)
                    pbx.logger.info(
                        f"RTP relay allocated on port {rtp_ports[0]}, caller endpoint set to {caller_endpoint}"
                    )

        # Get destination extension's address
        dest_ext_obj = pbx.extension_registry.get(to_ext)
        if not dest_ext_obj or not dest_ext_obj.address:
            pbx.logger.error(f"Cannot get address for extension {to_ext}")
            return False

        # Check if destination is a WebRTC extension
        is_webrtc_destination = (
            dest_ext_obj.address
            and isinstance(dest_ext_obj.address, tuple)
            and len(dest_ext_obj.address) == 2
            and dest_ext_obj.address[0] == "webrtc"
        )

        if is_webrtc_destination:
            # Route call to WebRTC client
            # Extract session ID from address tuple
            session_id = dest_ext_obj.address[1]
            pbx.logger.info(f"Routing call to WebRTC extension {to_ext} (session: {session_id})")

            if pbx.webrtc_gateway:
                # Get caller's SDP if available
                caller_sdp_str = message.body if message.body else None

                # Route the call through WebRTC gateway
                success = pbx.webrtc_gateway.receive_call(
                    session_id=session_id,
                    call_id=call_id,
                    caller_sdp=caller_sdp_str,
                    webrtc_signaling=(
                        pbx.webrtc_signaling if hasattr(pbx, "webrtc_signaling") else None
                    ),
                )

                if success:
                    pbx.logger.info(f"Call {call_id} routed to WebRTC session {session_id}")
                    # Note: The WebRTC client will be notified via the signaling channel
                    # and should send an answer when the user accepts the call
                    return True
                else:
                    pbx.logger.error(f"Failed to route call to WebRTC session {session_id}")
                    return False
            else:
                pbx.logger.error("WebRTC gateway not available for routing call")
                return False

        # Build SDP for forwarding INVITE to callee
        # Use the server's external IP address for SDP
        server_ip = pbx._get_server_ip()

        if rtp_ports:
            # Determine which codecs to offer based on callee's phone model
            # Get callee's User-Agent to detect phone model
            callee_user_agent = pbx._get_phone_user_agent(to_ext)
            callee_phone_model = pbx._detect_phone_model(callee_user_agent)

            # Select appropriate codecs for the callee's phone
            # - ZIP37G: PCMU/PCMA only
            # - ZIP33G: G726/G729/G722 only
            # - Other phones: use caller's codecs (existing behavior)
            codecs_for_callee = pbx._get_codecs_for_phone_model(
                callee_phone_model, default_codecs=caller_codecs
            )

            if callee_phone_model:
                pbx.logger.info(
                    f"Detected callee phone model: {callee_phone_model}, "
                    f"offering codecs: {codecs_for_callee}"
                )

            # Create new INVITE with PBX's RTP endpoint in SDP
            # Get DTMF payload type from config
            dtmf_payload_type = pbx._get_dtmf_payload_type()
            ilbc_mode = pbx._get_ilbc_mode()
            callee_sdp_body = SDPBuilder.build_audio_sdp(
                server_ip,
                rtp_ports[0],
                session_id=call_id,
                codecs=codecs_for_callee,
                dtmf_payload_type=dtmf_payload_type,
                ilbc_mode=ilbc_mode,
            )

            # Forward INVITE to callee
            invite_to_callee = SIPMessageBuilder.build_request(
                method="INVITE",
                uri=f"sip:{to_ext}@{server_ip}",
                from_addr=from_header,
                to_addr=to_header,
                call_id=call_id,
                cseq=int(message.get_header("CSeq").split()[0]),
                body=callee_sdp_body,
            )

            # Add required headers
            invite_to_callee.set_header("Via", message.get_header("Via"))
            invite_to_callee.set_header(
                "Contact",
                f"<sip:{from_ext}@{server_ip}:{pbx.config.get('server.sip_port', 5060)}>",
            )
            invite_to_callee.set_header("Content-type", "application/sdp")

            # Add caller ID headers (P-Asserted-Identity and Remote-Party-ID) if configured
            if pbx.config.get("sip.caller_id.send_p_asserted_identity", True) or pbx.config.get(
                "sip.caller_id.send_remote_party_id", True
            ):
                # Get caller's display name from extension
                caller_ext_obj = pbx.extension_registry.get(from_ext)
                display_name = from_ext  # Default to extension number
                if caller_ext_obj:
                    # Try to get name from extension object
                    display_name = getattr(caller_ext_obj, "name", from_ext)
                    if not display_name or display_name == "":
                        display_name = from_ext

                # Add caller ID headers for line identification
                SIPMessageBuilder.add_caller_id_headers(
                    invite_to_callee, from_ext, display_name, server_ip
                )
                pbx.logger.debug(f"Added caller ID headers: {display_name} <{from_ext}>")

            # Add MAC address header if configured
            if pbx.config.get("sip.device.send_mac_address", True):
                # Try to get MAC address from registered phones database
                mac_address = None
                if pbx.registered_phones_db:
                    try:
                        phones = pbx.registered_phones_db.get_by_extension(from_ext)
                        if phones and len(phones) > 0 and phones[0].get("mac_address"):
                            mac_address = phones[0]["mac_address"]
                    except (KeyError, TypeError, ValueError) as e:
                        pbx.logger.debug(f"Could not retrieve MAC for extension {from_ext}: {e}")

                # Also check if MAC was sent in the original INVITE
                if not mac_address and pbx.config.get("sip.device.accept_mac_in_invite", True):
                    x_mac = message.get_header("X-MAC-Address")
                    if x_mac:
                        mac_address = x_mac
                        pbx.logger.debug(f"Using MAC from incoming INVITE: {mac_address}")

                # Add MAC header if we found one
                if mac_address:
                    SIPMessageBuilder.add_mac_address_header(invite_to_callee, mac_address)
                    pbx.logger.debug(f"Added X-MAC-Address header: {mac_address}")

            # Send to destination
            pbx.sip_server._send_message(invite_to_callee.build(), dest_ext_obj.address)

            # Store callee address for later use (e.g., to send CANCEL if
            # routing to voicemail)
            call.callee_addr = dest_ext_obj.address
            call.callee_invite = invite_to_callee  # Store the INVITE for CANCEL reference

            pbx.logger.info(
                f"Forwarded INVITE to {to_ext} at {dest_ext_obj.address}"
            )
            pbx.logger.info(
                f"Routing call {call_id}: {from_ext} -> {to_ext} via RTP relay {rtp_ports[0]}"
            )

            # Start no-answer timer to route to voicemail if not answered
            no_answer_timeout = pbx.config.get("voicemail.no_answer_timeout", 30)
            call.no_answer_timer = threading.Timer(
                no_answer_timeout, self._handle_no_answer, args=(call_id,)
            )
            call.no_answer_timer.start()
            pbx.logger.info(f"Started no-answer timer ({no_answer_timeout}s) for call {call_id}")

        return True

    def _check_dialplan(self, extension):
        """
        Check if extension matches dialplan rules

        Args:
            extension: Extension number

        Returns:
            True if allowed by dialplan
        """
        dialplan = self.pbx_core.config.get("dialplan", {})

        # Check emergency pattern (Kari's Law - direct 911 dialing)
        # Always allow 911 and legacy formats (9911, 9-911)
        emergency_pattern = dialplan.get("emergency_pattern", "^9?-?911$")
        if re.match(emergency_pattern, extension):
            return True

        # Check internal pattern
        internal_pattern = dialplan.get("internal_pattern", "^1[0-9]{3}$")
        if re.match(internal_pattern, extension):
            return True

        # Check conference pattern
        conference_pattern = dialplan.get("conference_pattern", "^2[0-9]{3}$")
        if re.match(conference_pattern, extension):
            return True

        # Check voicemail pattern
        voicemail_pattern = dialplan.get("voicemail_pattern", "^\\*[0-9]{3,4}$")
        if re.match(voicemail_pattern, extension):
            return True

        # Check auto attendant pattern
        auto_attendant_pattern = dialplan.get("auto_attendant_pattern", "^0$")
        if re.match(auto_attendant_pattern, extension):
            return True

        # Check parking pattern
        parking_pattern = dialplan.get("parking_pattern", "^7[0-9]$")
        if re.match(parking_pattern, extension):
            return True

        # Check queue pattern
        queue_pattern = dialplan.get("queue_pattern", "^8[0-9]{3}$")
        if re.match(queue_pattern, extension):
            return True

        return False

    def _send_cancel_to_callee(self, call, call_id):
        """Send CANCEL to callee to stop their phone from ringing"""
        from pbx.sip.message import SIPMessageBuilder

        if not (
            hasattr(call, "callee_addr")
            and call.callee_addr
            and hasattr(call, "callee_invite")
            and call.callee_invite
        ):
            return

        cancel_request = SIPMessageBuilder.build_request(
            method="CANCEL",
            uri=call.callee_invite.uri,
            from_addr=call.callee_invite.get_header("From"),
            to_addr=call.callee_invite.get_header("To"),
            call_id=call_id,
            cseq=int(call.callee_invite.get_header("CSeq").split()[0]),
        )
        cancel_request.set_header("Via", call.callee_invite.get_header("Via"))
        self.pbx_core.sip_server._send_message(cancel_request.build(), call.callee_addr)
        self.pbx_core.logger.info(f"Sent CANCEL to callee {call.to_extension} to stop ringing")

    def _answer_call_for_voicemail(self, call, call_id):
        """Answer call for voicemail recording"""
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder

        pbx = self.pbx_core

        if not (call.original_invite and call.caller_addr and call.caller_rtp and call.rtp_ports):
            return False

        server_ip = pbx._get_server_ip()
        caller_user_agent = pbx._get_phone_user_agent(call.from_extension)
        caller_phone_model = pbx._detect_phone_model(caller_user_agent)
        caller_codecs = call.caller_rtp.get("formats", None) if call.caller_rtp else None
        codecs_for_caller = pbx._get_codecs_for_phone_model(
            caller_phone_model, default_codecs=caller_codecs
        )

        if caller_phone_model:
            pbx.logger.info(
                f"Voicemail: Detected caller phone model: {caller_phone_model}, "
                f"offering codecs: {codecs_for_caller}"
            )

        # Build SDP for the voicemail recording endpoint
        dtmf_payload_type = pbx._get_dtmf_payload_type()
        ilbc_mode = pbx._get_ilbc_mode()
        voicemail_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id,
            codecs=codecs_for_caller,
            dtmf_payload_type=dtmf_payload_type,
            ilbc_mode=ilbc_mode,
        )

        # Send 200 OK to answer the call for voicemail recording
        ok_response = SIPMessageBuilder.build_response(
            200, "OK", call.original_invite, body=voicemail_sdp
        )
        ok_response.set_header("Content-type", "application/sdp")

        # Build Contact header
        sip_port = pbx.config.get("server.sip_port", 5060)
        contact_uri = f"<sip:{call.to_extension}@{server_ip}:{sip_port}>"
        ok_response.set_header("Contact", contact_uri)

        # Send to caller
        pbx.sip_server._send_message(ok_response.build(), call.caller_addr)
        pbx.logger.info(f"Answered call {call_id} for voicemail recording")
        call.connect()
        return True

    def _handle_no_answer(self, call_id):
        """
        Handle no-answer timeout - route call to voicemail

        Args:
            call_id: Call identifier
        """
        from pbx.core.call import CallState
        from pbx.rtp.handler import RTPPlayer, RTPRecorder
        from pbx.utils.audio import get_prompt_audio

        pbx = self.pbx_core

        call = pbx.call_manager.get_call(call_id)
        if not call:
            pbx.logger.warning(f"No-answer timeout for non-existent call {call_id}")
            return

        # Check if call was already answered or routed
        if call.state == CallState.CONNECTED:
            pbx.logger.debug(f"Call {call_id} already answered, ignoring no-answer timeout")
            return

        if call.routed_to_voicemail:
            pbx.logger.debug(f"Call {call_id} already routed to voicemail")
            return

        call.routed_to_voicemail = True
        pbx.logger.info(f"No answer for call {call_id}, routing to voicemail")

        # Send CANCEL to the callee to stop their phone from ringing
        self._send_cancel_to_callee(call, call_id)

        # Answer the call to allow voicemail recording
        if not self._answer_call_for_voicemail(call, call_id):
            return

        # Play voicemail greeting and beep tone to caller
        if call.caller_rtp:
            try:
                import os
                import tempfile

                # Create RTP player to send audio to caller
                # Use the same port as the RTPRecorder since both bind to 0.0.0.0
                # and can handle bidirectional RTP communication
                player = RTPPlayer(
                    # Same port as RTPRecorder
                    local_port=call.rtp_ports[0],
                    remote_host=call.caller_rtp["address"],
                    remote_port=call.caller_rtp["port"],
                    call_id=call_id,
                )
                if player.start():
                    # Check for custom greeting first
                    mailbox = pbx.voicemail_system.get_mailbox(call.to_extension)
                    custom_greeting_path = mailbox.get_greeting_path()
                    greeting_file = None
                    temp_file_created = False

                    if custom_greeting_path:
                        # Use custom greeting
                        greeting_file = custom_greeting_path
                        pbx.logger.info(
                            f"Using custom greeting for extension {call.to_extension}: {custom_greeting_path}"
                        )
                        # Verify file exists and is readable
                        if Path(custom_greeting_path).exists():
                            file_size = Path(custom_greeting_path).stat().st_size
                            pbx.logger.info(f"Custom greeting file exists ({file_size} bytes)")
                        else:
                            pbx.logger.warning(
                                f"Custom greeting file not found at {custom_greeting_path}, using default"
                            )
                            custom_greeting_path = None  # Fall back to default

                    if not custom_greeting_path:
                        # Use default prompt: "Please leave a message after the tone"
                        # Try to load from voicemail_prompts/leave_message.wav, fallback to tone generation
                        greeting_prompt = get_prompt_audio("leave_message")
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                            temp_file.write(greeting_prompt)
                            greeting_file = temp_file.name
                            temp_file_created = True
                        pbx.logger.info(
                            f"Using default greeting for extension {call.to_extension}"
                        )

                    try:
                        player.play_file(greeting_file)
                        time.sleep(0.3)  # Brief pause before beep
                    finally:
                        # Clean up temp file only if we created one
                        if temp_file_created:
                            try:
                                os.unlink(greeting_file)
                            except (OSError, FileNotFoundError) as e:
                                pbx.logger.debug(f"Could not delete temp greeting file: {e}")

                    # Play beep tone (1000 Hz, 500ms)
                    player.play_beep(frequency=1000, duration_ms=500)
                    player.stop()
                    pbx.logger.info(f"Played voicemail greeting and beep for call {call_id}")
                else:
                    pbx.logger.warning(
                        f"Failed to start RTP player for greeting on call {call_id}"
                    )
            except OSError as e:
                pbx.logger.error(f"Error playing voicemail greeting: {e}")

            # Start RTP recorder on the allocated port
            recorder = RTPRecorder(call.rtp_ports[0], call_id)
            if recorder.start():
                # Store recorder in call object for later retrieval
                call.voicemail_recorder = recorder

                # set recording timeout (max voicemail duration)
                max_duration = pbx.config.get("voicemail.max_message_duration", 180)

                # Schedule voicemail completion after max duration
                voicemail_timer = threading.Timer(
                    max_duration, pbx._voicemail_handler.complete_voicemail_recording, args=(call_id,)
                )
                voicemail_timer.start()
                call.voicemail_timer = voicemail_timer

                # Start DTMF monitoring thread to detect # key press
                dtmf_monitor_thread = threading.Thread(
                    target=pbx._voicemail_handler.monitor_voicemail_dtmf, args=(call_id, call, recorder)
                )
                dtmf_monitor_thread.daemon = True
                dtmf_monitor_thread.start()

                pbx.logger.info(
                    f"Started voicemail recording for call {call_id}, max duration: {max_duration}s"
                )
            else:
                pbx.logger.error(f"Failed to start voicemail recorder for call {call_id}")
                pbx.end_call(call_id)
        else:
            pbx.logger.error(
                f"Cannot route call {call_id} to voicemail - missing required information"
            )
            # Fallback to ending the call
            pbx.end_call(call_id)
