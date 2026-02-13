"""
Auto-attendant handler for PBX Core

Extracts auto-attendant logic from PBXCore into a dedicated class,
including session management, DTMF input handling, and menu navigation.
"""

import time


class AutoAttendantHandler:
    """Handles auto-attendant call sessions with menu and DTMF input"""

    def __init__(self, pbx_core):
        """
        Initialize AutoAttendantHandler with reference to PBXCore.

        Args:
            pbx_core: The PBXCore instance
        """
        self.pbx_core = pbx_core

    def handle_auto_attendant(self, from_ext, to_ext, call_id, message, from_addr):
        """
        Handle auto attendant calls (extension 0)

        Args:
            from_ext: Calling extension
            to_ext: Destination (auto attendant extension, typically '0')
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Caller address

        Returns:
            True if call was handled
        """
        import threading

        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        pbx = self.pbx_core

        pbx.logger.info(f"Auto attendant call: {from_ext} -> {to_ext}")

        # Parse SDP from caller's INVITE
        caller_sdp = None
        caller_codecs = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()
            if caller_sdp:
                # Extract caller's codec list for negotiation
                caller_codecs = caller_sdp.get("formats", None)
                if caller_codecs:
                    pbx.logger.info(f"Auto attendant: Caller codecs: {caller_codecs}")

        # Create call for auto attendant
        call = pbx.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.auto_attendant_active = True

        # Start CDR record for analytics
        pbx.cdr_system.start_record(call_id, from_ext, to_ext)

        # Allocate RTP port for audio communication
        # For auto attendant, we don't need a relay (which forwards between two endpoints).
        # Instead, we directly play audio to the caller and listen for DTMF.
        # Find an available port from the RTP port pool.
        try:
            rtp_port = pbx.rtp_relay.port_pool.pop(0)
        except IndexError:
            pbx.logger.error(f"No available RTP ports for auto attendant {call_id}")
            return False

        rtcp_port = rtp_port + 1
        call.rtp_ports = (rtp_port, rtcp_port)
        pbx.logger.info(
            f"Allocated RTP port {rtp_port} for auto attendant {call_id} (no relay needed)"
        )

        # Store port allocation for cleanup
        call.aa_rtp_port = rtp_port

        # Send 180 Ringing first to provide ring-back tone to caller
        server_ip = pbx._get_server_ip()
        ringing_response = SIPMessageBuilder.build_response(180, "Ringing", call.original_invite)

        # Build Contact header for ringing response
        sip_port = pbx.config.get("server.sip_port", 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ringing_response.set_header("Contact", contact_uri)

        # Send ringing response to caller
        pbx.sip_server._send_message(ringing_response.build(), call.caller_addr)
        pbx.logger.info(f"Sent 180 Ringing for auto attendant call {call_id}")

        # Brief delay to allow ring-back tone to be established
        time.sleep(0.5)

        # Answer the call

        # Determine which codecs to offer based on caller's phone model
        # Get caller's User-Agent to detect phone model
        caller_user_agent = pbx._get_phone_user_agent(from_ext)
        caller_phone_model = pbx._detect_phone_model(caller_user_agent)

        # Select appropriate codecs for the caller's phone
        codecs_for_caller = pbx._get_codecs_for_phone_model(
            caller_phone_model, default_codecs=caller_codecs
        )

        if caller_phone_model:
            pbx.logger.info(
                f"Auto attendant: Detected caller phone model: {caller_phone_model}, "
                f"offering codecs: {codecs_for_caller}"
            )

        # Build SDP for answering, using phone-model-specific codecs
        # Get DTMF payload type from config
        dtmf_payload_type = pbx._get_dtmf_payload_type()
        ilbc_mode = pbx._get_ilbc_mode()
        aa_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id,
            codecs=codecs_for_caller,
            dtmf_payload_type=dtmf_payload_type,
            ilbc_mode=ilbc_mode,
        )

        # Send 200 OK to answer the call
        ok_response = SIPMessageBuilder.build_response(200, "OK", call.original_invite, body=aa_sdp)
        ok_response.set_header("Content-type", "application/sdp")

        # Build Contact header
        sip_port = pbx.config.get("server.sip_port", 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header("Contact", contact_uri)

        # Send to caller
        pbx.sip_server._send_message(ok_response.build(), call.caller_addr)
        pbx.logger.info(f"Answered auto attendant call {call_id}")

        # Mark call as connected
        call.connect()

        # Start auto attendant session
        session = pbx.auto_attendant.start_session(call_id, from_ext)
        call.aa_session = session

        # Start auto attendant interaction thread
        aa_thread = threading.Thread(
            target=self._auto_attendant_session, args=(call_id, call, session)
        )
        aa_thread.daemon = True
        aa_thread.start()

        return True

    def _auto_attendant_session(self, call_id, call, session):
        """
        Handle auto attendant session with menu and DTMF input

        Args:
            call_id: Call identifier
            call: Call object
            session: Auto attendant session
        """
        import os
        import tempfile

        from pbx.rtp.handler import RTPDTMFListener, RTPPlayer
        from pbx.utils.audio import get_prompt_audio

        pbx = self.pbx_core

        try:
            # Wait for RTP to stabilize
            time.sleep(0.5)

            if not call.caller_rtp:
                pbx.logger.warning(f"No caller RTP info for auto attendant {call_id}")
                return

            # ============================================================
            # RTP SETUP FOR AUTO ATTENDANT - BIDIRECTIONAL AUDIO
            # ============================================================
            # This section sets up RTP for interactive auto attendant:
            # 1. RTPPlayer: Sends audio prompts/menus to the caller (server -> client)
            # 2. RTPDTMFListener: Receives audio and detects DTMF tones (client -> server)
            # Both use the same local port (call.rtp_ports[0]) allocated by RTP relay.
            # This creates a full-duplex audio channel for the auto attendant system.
            # ============================================================

            # Create RTP player for sending audio prompts to the caller
            player = RTPPlayer(
                local_port=call.rtp_ports[0],
                remote_host=call.caller_rtp["address"],
                remote_port=call.caller_rtp["port"],
                call_id=call_id,
            )

            if not player.start():
                pbx.logger.error(f"Failed to start RTP player for auto attendant {call_id}")
                return

            # Create DTMF listener for receiving and detecting user input
            dtmf_listener = RTPDTMFListener(call.rtp_ports[0])
            if not dtmf_listener.start():
                pbx.logger.error(f"Failed to start DTMF listener for auto attendant {call_id}")
                player.stop()
                return
            pbx.logger.info(
                "Auto attendant RTP setup complete - bidirectional audio channel established"
            )

            # Play welcome greeting
            action = session.get("session")
            audio_file = session.get("file")

            pbx.logger.info(f"[Auto Attendant] Starting audio playback for call {call_id}")
            audio_played = False

            if audio_file and os.path.exists(audio_file):
                pbx.logger.info(f"[Auto Attendant] Playing welcome file: {audio_file}")
                audio_played = player.play_file(audio_file)
                if audio_played:
                    pbx.logger.info("[Auto Attendant] ✓ Welcome audio played successfully")
                else:
                    pbx.logger.error("[Auto Attendant] ✗ Failed to play welcome audio")
            else:
                # Try to load from auto_attendant/welcome.wav, fallback to tone
                # generation
                pbx.logger.info("[Auto Attendant] Generating welcome prompt audio")
                prompt_data = get_prompt_audio("welcome", prompt_dir="auto_attendant")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(prompt_data)
                    temp_file_path = temp_file.name
                try:
                    audio_played = player.play_file(temp_file_path)
                    if audio_played:
                        pbx.logger.info(
                            "[Auto Attendant] ✓ Generated welcome audio played successfully"
                        )
                    else:
                        pbx.logger.error(
                            "[Auto Attendant] ✗ Failed to play generated welcome audio"
                        )
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except BaseException:
                        pass

            time.sleep(0.5)

            # Play main menu
            pbx.logger.info(f"[Auto Attendant] Playing main menu for call {call_id}")
            menu_audio = pbx.auto_attendant._get_audio_file("main_menu")
            if menu_audio and os.path.exists(menu_audio):
                pbx.logger.info(f"[Auto Attendant] Playing menu file: {menu_audio}")
                audio_played = player.play_file(menu_audio)
                if audio_played:
                    pbx.logger.info("[Auto Attendant] ✓ Menu audio played successfully")
                else:
                    pbx.logger.error("[Auto Attendant] ✗ Failed to play menu audio")
            else:
                # Try to load from auto_attendant/main_menu.wav, fallback to
                # tone generation
                pbx.logger.info("[Auto Attendant] Generating menu prompt audio")
                prompt_data = get_prompt_audio("main_menu", prompt_dir="auto_attendant")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(prompt_data)
                    temp_file_path = temp_file.name
                try:
                    audio_played = player.play_file(temp_file_path)
                    if audio_played:
                        pbx.logger.info(
                            "[Auto Attendant] ✓ Generated menu audio played successfully"
                        )
                    else:
                        pbx.logger.error("[Auto Attendant] ✗ Failed to play generated menu audio")
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except BaseException:
                        pass

            # Main loop - wait for DTMF input
            session_active = True
            timeout = pbx.auto_attendant.timeout
            start_time = time.time()

            while session_active and (time.time() - start_time) < timeout:
                # Check for DTMF input from SIP INFO or in-band
                digit = None

                # Priority 1: Check SIP INFO queue
                if hasattr(call, "dtmf_info_queue") and call.dtmf_info_queue:
                    digit = call.dtmf_info_queue.pop(0)
                    pbx.logger.info(f"Auto attendant received DTMF from SIP INFO: {digit}")
                else:
                    # Priority 2: Check in-band DTMF
                    digit = dtmf_listener.get_digit(timeout=1.0)
                    if digit:
                        pbx.logger.info(
                            f"Auto attendant received DTMF from in-band audio: {digit}"
                        )

                if digit:
                    pbx.logger.info(f"Auto attendant received DTMF: {digit}")

                    # Handle the input
                    result = pbx.auto_attendant.handle_dtmf(session["session"], digit)
                    action = result.get("action")

                    if action == "transfer":
                        destination = result.get("destination")
                        pbx.logger.info(f"Auto attendant transferring to {destination}")

                        # Play transfer message
                        transfer_audio = pbx.auto_attendant._get_audio_file("transferring")
                        if transfer_audio and os.path.exists(transfer_audio):
                            player.play_file(transfer_audio)
                        else:
                            # Try to load from auto_attendant/transferring.wav,
                            # fallback to tone generation
                            prompt_data = get_prompt_audio(
                                "transferring", prompt_dir="auto_attendant"
                            )
                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(prompt_data)
                                temp_file_path = temp_file.name
                            try:
                                player.play_file(temp_file_path)
                            finally:
                                try:
                                    os.unlink(temp_file_path)
                                except BaseException:
                                    pass

                        time.sleep(0.5)

                        # Transfer the call using existing transfer_call method
                        if call_id:
                            success = pbx.transfer_call(call_id, destination)
                            if not success:
                                pbx.logger.warning(
                                    f"Failed to transfer call {call_id} to {destination}"
                                )
                        else:
                            pbx.logger.warning("Cannot transfer call: no call_id available")
                        session_active = False

                    elif action == "play":
                        # Play the requested audio
                        audio_file = result.get("file")
                        if audio_file and os.path.exists(audio_file):
                            player.play_file(audio_file)

                        # Reset timeout
                        start_time = time.time()

                    # Update session
                    if "session" in result:
                        session["session"] = result["session"]

            # Timeout - handle it
            if time.time() - start_time >= timeout:
                result = pbx.auto_attendant.handle_timeout(session["session"])
                action = result.get("action")

                if action == "transfer":
                    destination = result.get("destination")
                    pbx.logger.info(f"Auto attendant timeout, transferring to {destination}")
                    if call_id:
                        success = pbx.transfer_call(call_id, destination)
                        if not success:
                            pbx.logger.warning(
                                f"Failed to transfer call {call_id} to {destination} on timeout"
                            )

            # Clean up
            player.stop()
            dtmf_listener.stop()

            # Return port to pool
            if hasattr(call, "aa_rtp_port"):
                pbx.rtp_relay.port_pool.append(call.aa_rtp_port)
                pbx.rtp_relay.port_pool.sort()
                pbx.logger.info(
                    f"Returned RTP port {call.aa_rtp_port} to pool"
                )

        except Exception as e:
            pbx.logger.error(f"Error in auto attendant session: {e}")
            import traceback

            pbx.logger.error(traceback.format_exc())

            # Ensure port is returned even on error
            if hasattr(call, "aa_rtp_port"):
                try:
                    pbx.rtp_relay.port_pool.append(call.aa_rtp_port)
                    pbx.rtp_relay.port_pool.sort()
                except Exception:
                    pass
        finally:
            # End the call
            time.sleep(1)
            pbx.end_call(call_id)
