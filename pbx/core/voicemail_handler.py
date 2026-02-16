"""
Voicemail handler for PBX Core

Extracts voicemail IVR logic from PBXCore into a dedicated class,
including voicemail access, message playback, IVR session management,
DTMF monitoring during recording, and voicemail recording completion.
"""

import contextlib
import struct
import threading
import time
import traceback
from pathlib import Path
from typing import Any


class VoicemailHandler:
    """Handles voicemail access, IVR sessions, message playback, and recording"""

    def __init__(self, pbx_core: Any) -> None:
        """
        Initialize VoicemailHandler with reference to PBXCore.

        Args:
            pbx_core: The PBXCore instance
        """
        self.pbx_core: Any = pbx_core

    def handle_voicemail_access(
        self,
        from_ext: str,
        to_ext: str,
        call_id: str,
        message: Any,
        from_addr: tuple[str, int],
    ) -> bool:
        """
        Handle voicemail access calls (*xxxx pattern)

        Args:
            from_ext: Calling extension
            to_ext: Destination (e.g., *1001)
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Caller address

        Returns:
            True if call was handled
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        pbx = self.pbx_core

        # Extract the target extension from *xxxx pattern
        target_ext: str = to_ext[1:]  # Remove the * prefix

        pbx.logger.info("=" * 70)
        pbx.logger.info("VOICEMAIL ACCESS INITIATED")
        pbx.logger.info(f"  Call ID: {call_id}")
        pbx.logger.info(f"  From Extension: {from_ext}")
        pbx.logger.info(f"  Target Extension: {target_ext}")
        pbx.logger.info(f"  Caller Address: {from_addr}")
        pbx.logger.info("=" * 70)

        # Verify the target extension exists (check both database and config)
        pbx.logger.info(f"[VM Access] Step 1: Verifying target extension {target_ext} exists")
        extension_exists: bool = False

        # Check extension registry first (includes both database and config
        # extensions)
        if pbx.extension_registry.get(target_ext):
            extension_exists = True
            pbx.logger.info(f"[VM Access] ✓ Extension {target_ext} found in registry")
        # Fallback to config check for backwards compatibility
        elif pbx.config.get_extension(target_ext):
            extension_exists = True
            pbx.logger.info(f"[VM Access] ✓ Extension {target_ext} found in config file")

        if not extension_exists:
            pbx.logger.warning(
                f"[VM Access] ✗ Extension {target_ext} not found - rejecting voicemail access"
            )
            return False

        # Get the voicemail box
        pbx.logger.info(f"[VM Access] Step 2: Loading voicemail box for extension {target_ext}")
        mailbox = pbx.voicemail_system.get_mailbox(target_ext)
        pbx.logger.info("[VM Access] ✓ Voicemail box loaded")

        # Parse SDP from caller's INVITE
        pbx.logger.info("[VM Access] Step 3: Parsing SDP from caller INVITE")
        caller_sdp: dict[str, Any] | None = None
        caller_codecs: list[str] | None = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()
            if caller_sdp:
                pbx.logger.info(
                    f"[VM Access] ✓ Caller SDP parsed: address={caller_sdp.get('address')}, port={caller_sdp.get('port')}, formats={caller_sdp.get('formats')}"
                )
                # Extract caller's codec list for negotiation
                caller_codecs = caller_sdp.get("formats", None)
            else:
                pbx.logger.warning("[VM Access] ⚠ No audio info found in caller SDP")
        else:
            pbx.logger.warning("[VM Access] ⚠ No SDP body in INVITE message")

        # Create call for voicemail access
        pbx.logger.info("[VM Access] Step 4: Creating call object in call manager")
        call = pbx.call_manager.create_call(call_id, from_ext, f"*{target_ext}")
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.voicemail_access = True
        call.voicemail_extension = target_ext
        pbx.logger.info(f"[VM Access] ✓ Call object created with state: {call.state}")

        # Start CDR record for analytics
        pbx.logger.info("[VM Access] Step 5: Starting CDR record for analytics")
        pbx.cdr_system.start_record(call_id, from_ext, f"*{target_ext}")

        # Allocate RTP ports for bidirectional audio communication
        # These ports will be used by RTPPlayer (sending prompts) and RTPRecorder (receiving DTMF)
        # in the IVR session thread. The RTP relay handler manages the socket
        # binding and packet forwarding.
        pbx.logger.info("[VM Access] Step 6: Allocating RTP relay ports")
        rtp_ports = pbx.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
            pbx.logger.info(f"[VM Access] ✓ RTP ports allocated: {rtp_ports[0]}/{rtp_ports[1]}")
        else:
            pbx.logger.error(
                "[VM Access] ✗ Failed to allocate RTP ports - aborting voicemail access"
            )
            return False

        # Answer the call
        pbx.logger.info("[VM Access] Step 7: Building SIP 200 OK response")
        server_ip: str = pbx._get_server_ip()
        pbx.logger.info(f"[VM Access] Server IP: {server_ip}")

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
                f"[VM Access] Detected caller phone model: {caller_phone_model}, "
                f"offering codecs: {codecs_for_caller}"
            )

        # Build SDP for answering, using phone-model-specific codecs
        # Get DTMF payload type from config
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
        pbx.logger.info(f"[VM Access] ✓ SDP built for response (RTP port: {call.rtp_ports[0]})")

        # Send 200 OK to answer the call
        pbx.logger.info("[VM Access] Step 8: Building and sending 200 OK response")
        ok_response = SIPMessageBuilder.build_response(
            200, "OK", call.original_invite, body=voicemail_sdp
        )
        ok_response.set_header("Content-type", "application/sdp")

        # Build Contact header
        sip_port: int = pbx.config.get("server.sip_port", 5060)
        contact_uri: str = f"<sip:{target_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header("Contact", contact_uri)
        pbx.logger.info(f"[VM Access] Contact header: {contact_uri}")

        # Send to caller
        pbx.sip_server._send_message(ok_response.build(), call.caller_addr)
        pbx.logger.info(f"[VM Access] ✓ 200 OK sent to {call.caller_addr}")

        # Mark call as connected
        call.connect()
        pbx.logger.info(f"[VM Access] ✓ Call state changed to: {call.state}")

        # Create VoicemailIVR for this call
        pbx.logger.info("[VM Access] Step 9: Initializing Voicemail IVR")
        from pbx.features.voicemail import VoicemailIVR

        voicemail_ivr = VoicemailIVR(pbx.voicemail_system, target_ext)
        call.voicemail_ivr = voicemail_ivr
        pbx.logger.info(f"[VM Access] ✓ Voicemail IVR created for extension {target_ext}")

        # Get message count
        pbx.logger.info("[VM Access] Step 10: Checking voicemail message count")
        messages = mailbox.get_messages(unread_only=False)
        unread = mailbox.get_messages(unread_only=True)
        pbx.logger.info(
            f"[VM Access] ✓ Mailbox status: {len(unread)} unread, {len(messages)} total messages"
        )

        # Start IVR-based voicemail management
        # This runs in a separate thread so it doesn't block
        pbx.logger.info("[VM Access] Step 11: Starting IVR session thread")
        playback_thread = threading.Thread(
            target=self._voicemail_ivr_session, args=(call_id, call, mailbox, voicemail_ivr)
        )
        playback_thread.daemon = True
        playback_thread.start()
        pbx.logger.info("[VM Access] ✓ IVR session thread started (daemon)")

        pbx.logger.info("=" * 70)
        pbx.logger.info("VOICEMAIL ACCESS SETUP COMPLETE")
        pbx.logger.info(f"  Call ID: {call_id}")
        pbx.logger.info(f"  Extension: {target_ext}")
        pbx.logger.info(f"  State: {call.state}")
        pbx.logger.info("  Ready for user interaction")
        pbx.logger.info("=" * 70)

        return True

    def _playback_voicemails(
        self,
        call_id: str,
        call: Any,
        mailbox: Any,
        messages: list[dict[str, Any]],
    ) -> None:
        """
        Play voicemail messages to caller

        Args:
            call_id: Call identifier
            call: Call object
            mailbox: VoicemailBox object
            messages: list of message dictionaries
        """
        from pbx.rtp.handler import RTPPlayer

        pbx = self.pbx_core

        try:
            # Wait a moment for RTP to stabilize
            time.sleep(0.5)

            # Create RTP player to send audio to caller
            if not call.caller_rtp:
                pbx.logger.warning(f"No caller RTP info for voicemail playback {call_id}")
                # End call after short delay
                time.sleep(2)
                pbx.end_call(call_id)
                return

            # Use the same port as allocated for the call for proper RTP
            # communication
            player = RTPPlayer(
                local_port=call.rtp_ports[0],
                remote_host=call.caller_rtp["address"],
                remote_port=call.caller_rtp["port"],
                call_id=call_id,
            )

            if not player.start():
                pbx.logger.error(f"Failed to start RTP player for voicemail playback {call_id}")
                time.sleep(2)
                pbx.end_call(call_id)
                return

            try:
                # Play each voicemail message
                if not messages:
                    # No messages - play short beep and hang up
                    pbx.logger.info(f"No voicemail messages for {call.voicemail_extension}")
                    player.play_beep(frequency=400, duration_ms=500)
                    time.sleep(2)
                else:
                    # Play messages
                    pbx.logger.info(
                        f"Playing {len(messages)} voicemail messages for {call.voicemail_extension}"
                    )

                    for idx, message in enumerate(messages):
                        # Play a beep between messages
                        if idx > 0:
                            time.sleep(0.5)
                            player.play_beep(frequency=800, duration_ms=300)
                            time.sleep(0.5)

                        # Play the voicemail message
                        file_path: str = message["file_path"]
                        pbx.logger.info(f"Playing voicemail {idx + 1}/{len(messages)}: {file_path}")

                        if player.play_file(file_path):
                            # Mark message as listened
                            mailbox.mark_listened(message["id"])
                            pbx.logger.info(f"Marked voicemail {message['id']} as listened")
                        else:
                            pbx.logger.warning(f"Failed to play voicemail: {file_path}")

                        # Pause between messages
                        time.sleep(1)

                    pbx.logger.info(
                        f"Finished playing all voicemails for {call.voicemail_extension}"
                    )
                    time.sleep(1)

            finally:
                player.stop()

            # End the call after playback
            pbx.end_call(call_id)

        except (KeyError, TypeError, ValueError) as e:
            pbx.logger.error(f"Error in voicemail playback: {e}")
            traceback.print_exc()
            # Ensure call is ended even if there's an error
            try:
                pbx.end_call(call_id)
            except Exception as e:
                pbx.logger.error(f"Error ending call during cleanup: {e}")

    def _voicemail_ivr_session(
        self, call_id: str, call: Any, mailbox: Any, voicemail_ivr: Any
    ) -> None:
        """
        Interactive voicemail management session with IVR menu

        Args:
            call_id: Call identifier
            call: Call object
            mailbox: VoicemailBox object
            voicemail_ivr: VoicemailIVR object
        """
        import tempfile

        from pbx.core.call import CallState
        from pbx.rtp.handler import RTPPlayer, RTPRecorder
        from pbx.utils.audio import get_prompt_audio
        from pbx.utils.dtmf import DTMFDetector

        pbx = self.pbx_core

        pbx.logger.info("")
        pbx.logger.info(f"{'=' * 70}")
        pbx.logger.info("VOICEMAIL IVR SESSION STARTING")
        pbx.logger.info(f"  Call ID: {call_id}")
        pbx.logger.info(f"  Extension: {call.voicemail_extension}")
        pbx.logger.info(f"  Call State: {call.state}")
        pbx.logger.info(f"{'=' * 70}")

        try:
            # Wait a moment for RTP to stabilize
            pbx.logger.info("[VM IVR] Waiting 0.5s for RTP to stabilize...")
            time.sleep(0.5)

            # Check if call was terminated during RTP stabilization
            if call.state == CallState.ENDED:
                pbx.logger.info("")
                pbx.logger.info("[VM IVR] ✗ call ended before IVR could start")
                pbx.logger.info(f"[VM IVR] Extension: {call.voicemail_extension}")
                pbx.logger.info(f"[VM IVR] State: {call.state}")
                pbx.logger.info("[VM IVR] Exiting IVR session")
                pbx.logger.info("")
                return

            pbx.logger.info("[VM IVR] Checking caller RTP information...")
            if not call.caller_rtp:
                pbx.logger.warning("[VM IVR] ✗ No caller RTP info available - cannot proceed")
                time.sleep(2)
                pbx.end_call(call_id)
                return
            pbx.logger.info(
                f"[VM IVR] ✓ Caller RTP: {call.caller_rtp['address']}:{call.caller_rtp['port']}"
            )

            # ============================================================
            # RTP SETUP FOR VOICEMAIL IVR - BIDIRECTIONAL AUDIO
            # ============================================================
            # This section sets up RTP for interactive voicemail access:
            # 1. RTPPlayer: Sends audio prompts to the caller (server -> client)
            # 2. RTPRecorder: Receives audio from caller for DTMF detection (client -> server)
            # Both use the same local port (call.rtp_ports[0]) allocated by RTP relay.
            # This creates a full-duplex audio channel for the IVR system.
            # ============================================================

            # Create RTP player for sending audio prompts to the caller
            # This sends voicemail prompts, menus, and messages to the user
            pbx.logger.info("[VM IVR] Creating RTP player for audio prompts...")
            pbx.logger.info(f"[VM IVR]   Local port: {call.rtp_ports[0]}")
            pbx.logger.info(
                f"[VM IVR]   Remote: {call.caller_rtp['address']}:{call.caller_rtp['port']}"
            )
            player = RTPPlayer(
                local_port=call.rtp_ports[0],
                remote_host=call.caller_rtp["address"],
                remote_port=call.caller_rtp["port"],
                call_id=call_id,
            )

            if not player.start():
                pbx.logger.error("[VM IVR] ✗ Failed to start RTP player")
                time.sleep(2)
                pbx.end_call(call_id)
                return
            pbx.logger.info("[VM IVR] ✓ RTP player started successfully")

            # Create DTMF detector for processing user input (menu selections,
            # PIN, etc.)
            pbx.logger.info("[VM IVR] Creating DTMF detector (sample_rate=8000Hz)...")
            dtmf_detector = DTMFDetector(sample_rate=8000)
            pbx.logger.info("[VM IVR] ✓ DTMF detector created")

            # Create RTP recorder to receive audio from caller for DTMF detection
            # This listens on the same port, captures incoming RTP packets, and
            # extracts audio
            pbx.logger.info(
                f"[VM IVR] Creating RTP recorder for DTMF detection (port {call.rtp_ports[0]})..."
            )
            recorder = RTPRecorder(call.rtp_ports[0], call_id)
            if not recorder.start():
                pbx.logger.error("[VM IVR] ✗ Failed to start RTP recorder")
                player.stop()
                time.sleep(2)
                pbx.end_call(call_id)
                return
            pbx.logger.info("[VM IVR] ✓ RTP recorder started successfully")
            pbx.logger.info(
                "[VM IVR] ✓ RTP setup complete - bidirectional audio channel established"
            )

            try:
                # Start the IVR flow - transition from WELCOME to PIN_ENTRY state
                # Use '*' which won't be collected as part of PIN (only 0-9 are
                # collected)
                pbx.logger.info("[VM IVR] Initializing IVR state machine...")
                initial_action: dict[str, Any] = voicemail_ivr.handle_dtmf("*")

                # Play the PIN entry prompt that the IVR returned
                if not isinstance(initial_action, dict):
                    pbx.logger.error(
                        f"[VM IVR] ✗ IVR handle_dtmf returned unexpected type: {type(initial_action)}"
                    )
                    initial_action = {"action": "play_prompt", "prompt": "enter_pin"}

                pbx.logger.info(
                    f"[VM IVR] ✓ IVR initialized - Action: {initial_action.get('action')}, Prompt: {initial_action.get('prompt')}"
                )

                prompt_type: str = initial_action.get("prompt", "enter_pin")
                # Try to load from voicemail_prompts/ directory, fallback to
                # tone generation
                pbx.logger.info(f"[VM IVR] Loading audio prompt: {prompt_type}")
                pin_prompt: bytes = get_prompt_audio(prompt_type)
                pbx.logger.info(f"[VM IVR] ✓ Prompt audio loaded ({len(pin_prompt)} bytes)")

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(pin_prompt)
                    prompt_file: str = temp_file.name

                try:
                    pbx.logger.info(
                        f"[VM IVR] Playing PIN entry prompt (call state: {call.state})..."
                    )
                    player.play_file(prompt_file)
                    pbx.logger.info(
                        f"[VM IVR] ✓ Finished playing PIN entry prompt (call state: {call.state})"
                    )
                finally:
                    with contextlib.suppress(OSError):
                        Path(prompt_file).unlink()

                time.sleep(0.5)
                pbx.logger.info("[VM IVR] Post-prompt pause complete, checking call state...")

                # Check if call was terminated early (e.g., immediate BYE after answering)
                # Log the actual call state for debugging
                pbx.logger.info(
                    f"[VM IVR] Call state check: call_id={call_id}, state={call.state}, state.value={call.state.value if hasattr(call.state, 'value') else 'N/A'}"
                )

                if call.state == CallState.ENDED:
                    pbx.logger.info("")
                    pbx.logger.info("[VM IVR] ✗ call ended before IVR could start")
                    pbx.logger.info(f"[VM IVR] Extension: {call.voicemail_extension}")
                    pbx.logger.info(f"[VM IVR] State: {call.state}")
                    pbx.logger.info("[VM IVR] Exiting IVR session")
                    pbx.logger.info("")
                    return

                pbx.logger.info("")
                pbx.logger.info("[VM IVR] ✓ IVR fully started and ready for user input")
                pbx.logger.info(f"[VM IVR] Extension: {call.voicemail_extension}")
                pbx.logger.info(f"[VM IVR] State: {call.state}")
                pbx.logger.info("[VM IVR] Waiting for PIN entry...")
                pbx.logger.info("")

                # Main IVR loop - listen for DTMF input
                ivr_active: bool = True
                last_audio_check: float = time.time()

                # DTMF debouncing: track last detected digit and time to
                # prevent duplicates
                last_detected_digit: str | None = None
                last_detection_time: float = 0.0
                DTMF_DEBOUNCE_SECONDS: float = 0.5  # Ignore same digit within 500ms

                # Constants for DTMF detection
                # ~0.5s of audio at 160 bytes per 20ms RTP packet
                DTMF_DETECTION_PACKETS: int = 40  # 40 packets * 20ms = 0.8s of audio
                # Minimum audio data needed for reliable DTMF detection
                MIN_AUDIO_BYTES_FOR_DTMF: int = 1600

                while ivr_active:
                    # Check if call is still active
                    if call.state == CallState.ENDED:
                        pbx.logger.info(f"[VM IVR] Call {call_id} ended - exiting IVR loop")
                        break

                    # Detect DTMF from either SIP INFO (out-of-band) or in-band
                    # audio
                    digit: str | None = None

                    # Priority 1: Check for DTMF from SIP INFO messages (most
                    # reliable)
                    if hasattr(call, "dtmf_info_queue") and call.dtmf_info_queue:
                        digit = call.dtmf_info_queue.pop(0)
                        pbx.logger.info(f"[VM IVR] >>> DTMF RECEIVED (SIP INFO): '{digit}' <<<")
                    else:
                        # Priority 2: Fall back to in-band DTMF detection from
                        # audio
                        time.sleep(0.1)

                        # Check for recorded audio (DTMF tones from user)
                        if hasattr(recorder, "recorded_data") and recorder.recorded_data:
                            # Get recent audio data
                            if len(recorder.recorded_data) > 0:
                                # Collect last portion of audio for DTMF
                                # detection
                                recent_audio = b"".join(
                                    recorder.recorded_data[-DTMF_DETECTION_PACKETS:]
                                )

                                if (
                                    len(recent_audio) > MIN_AUDIO_BYTES_FOR_DTMF
                                ):  # Need sufficient audio for DTMF
                                    try:
                                        # Detect DTMF in audio with error
                                        # handling
                                        digit = dtmf_detector.detect(recent_audio)
                                    except Exception as e:
                                        pbx.logger.error(f"Error detecting DTMF: {e}")
                                        digit = None

                                    if digit:
                                        # Debounce: ignore duplicate detections
                                        # of same digit within debounce period
                                        current_time: float = time.time()
                                        if (
                                            digit == last_detected_digit
                                            and (current_time - last_detection_time)
                                            < DTMF_DEBOUNCE_SECONDS
                                        ):
                                            # Same digit detected too soon,
                                            # likely echo or lingering tone
                                            pbx.logger.debug(
                                                f"[VM IVR] DTMF '{digit}' debounced (duplicate within {DTMF_DEBOUNCE_SECONDS}s)"
                                            )
                                            continue

                                        # Update debounce tracking
                                        last_detected_digit = digit
                                        last_detection_time = current_time
                                        pbx.logger.info(
                                            f"[VM IVR] >>> DTMF RECEIVED (In-band audio): '{digit}' <<<"
                                        )

                    # Process detected DTMF digit (from either SIP INFO or
                    # in-band)
                    if digit:
                        # Handle DTMF input through IVR
                        pbx.logger.info(
                            f"[VM IVR] Processing DTMF '{digit}' through IVR state machine..."
                        )
                        pbx.logger.info(f"[VM IVR] Current IVR state: {voicemail_ivr.state}")
                        action: dict[str, Any] = voicemail_ivr.handle_dtmf(digit)
                        pbx.logger.info(f"[VM IVR] IVR returned action: {action.get('action')}")
                        pbx.logger.info(f"[VM IVR] New IVR state: {voicemail_ivr.state}")

                        # Process IVR action
                        if action["action"] == "play_message":
                            # Check if call is still active before playing
                            if call.state == CallState.ENDED:
                                pbx.logger.info(
                                    f"[VM IVR] Call {call_id} ended, skipping message playback"
                                )
                                break
                            # Play the voicemail message
                            file_path: str | None = action.get("file_path")
                            message_id: str | None = action.get("message_id")
                            caller_id: str | None = action.get("caller_id")
                            pbx.logger.info(
                                f"[VM IVR] Playing voicemail message: {message_id} from {caller_id}"
                            )
                            if file_path and Path(file_path).exists():
                                player.play_file(file_path)
                                mailbox.mark_listened(message_id)
                                pbx.logger.info(
                                    f"[VM IVR] ✓ Voicemail {message_id} played and marked as listened"
                                )
                            else:
                                pbx.logger.warning(
                                    f"[VM IVR] ✗ Voicemail file not found: {file_path}"
                                )
                            time.sleep(0.5)

                        elif action["action"] == "play_prompt":
                            # Check if call is still active before playing
                            if call.state == CallState.ENDED:
                                pbx.logger.info(
                                    f"[VM IVR] Call {call_id} ended, skipping prompt playback"
                                )
                                break
                            # Play a prompt
                            prompt_type = action.get("prompt", "main_menu")
                            pbx.logger.info(f"[VM IVR] Playing prompt: {prompt_type}")
                            # Try to load from voicemail_prompts/ directory,
                            # fallback to tone generation
                            prompt_audio: bytes = get_prompt_audio(prompt_type)

                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(prompt_audio)
                                prompt_file = temp_file.name

                            try:
                                player.play_file(prompt_file)
                                pbx.logger.info(f"[VM IVR] ✓ Prompt '{prompt_type}' played")
                            finally:
                                try:
                                    Path(prompt_file).unlink()
                                except OSError:
                                    pass  # File already deleted or doesn't exist

                            time.sleep(0.3)

                        elif action["action"] == "hangup":
                            # Check if call is still active before playing
                            # goodbye
                            if call.state == CallState.ENDED:
                                pbx.logger.info(
                                    f"[VM IVR] Call {call_id} already ended, skipping goodbye prompt"
                                )
                                ivr_active = False
                                break
                            pbx.logger.info(
                                "[VM IVR] User requested hangup - playing goodbye and ending call"
                            )
                            # Play goodbye and end call
                            # Try to load from voicemail_prompts/ directory,
                            # fallback to tone generation
                            goodbye_prompt: bytes = get_prompt_audio("goodbye")
                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(goodbye_prompt)
                                prompt_file = temp_file.name

                            try:
                                player.play_file(prompt_file)
                            finally:
                                try:
                                    Path(prompt_file).unlink()
                                except OSError:
                                    pass  # File already deleted or doesn't exist

                            time.sleep(1)
                            ivr_active = False

                        elif action["action"] == "start_recording":
                            # Start recording greeting
                            if call.state == CallState.ENDED:
                                pbx.logger.info(f"Call {call_id} ended, cannot start recording")
                                break

                            pbx.logger.info(
                                f"Starting greeting recording for extension {call.voicemail_extension}"
                            )

                            # Play beep tone
                            beep_prompt: bytes = get_prompt_audio("beep")
                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(beep_prompt)
                                beep_file: str = temp_file.name

                            try:
                                player.play_file(beep_file)
                            finally:
                                with contextlib.suppress(OSError):
                                    Path(beep_file).unlink()

                            time.sleep(0.2)

                            # Start recording
                            recorder.recorded_data = []  # Clear previous recording
                            recording_start_time: float = time.time()
                            max_recording_time: int = 120  # 2 minutes max

                            # Wait for # to stop recording or timeout
                            recording: bool = True
                            while recording and ivr_active:
                                if call.state == CallState.ENDED:
                                    pbx.logger.info(f"Call {call_id} ended during recording")
                                    recording = False
                                    break

                                # Check for timeout
                                if time.time() - recording_start_time > max_recording_time:
                                    pbx.logger.info(
                                        f"Recording timed out after {max_recording_time}s"
                                    )
                                    recording = False
                                    break

                                time.sleep(0.1)

                                # Check for DTMF # to stop recording (SIP INFO
                                # or in-band)
                                stop_digit: str | None = None

                                # Priority 1: Check SIP INFO queue
                                if hasattr(call, "dtmf_info_queue") and call.dtmf_info_queue:
                                    stop_digit = call.dtmf_info_queue.pop(0)
                                    pbx.logger.info(
                                        f"Received DTMF from SIP INFO during recording: {stop_digit}"
                                    )
                                # Priority 2: Check in-band audio
                                elif hasattr(recorder, "recorded_data") and recorder.recorded_data:
                                    recent_audio = b"".join(
                                        recorder.recorded_data[-DTMF_DETECTION_PACKETS:]
                                    )
                                    if len(recent_audio) > MIN_AUDIO_BYTES_FOR_DTMF:
                                        try:
                                            stop_digit = dtmf_detector.detect(recent_audio)
                                            if stop_digit:
                                                pbx.logger.info(
                                                    f"Received DTMF from in-band audio during recording: {stop_digit}"
                                                )
                                        except Exception as e:
                                            pbx.logger.error(
                                                f"Error detecting DTMF during recording: {e}"
                                            )
                                            stop_digit = None

                                if stop_digit == "#":
                                    pbx.logger.info("Recording stopped by user (#)")
                                    recording = False
                                    # Process through IVR to transition state
                                    action = voicemail_ivr.handle_dtmf("#")
                                    # Save recorded audio - convert to WAV format
                                    if (
                                        hasattr(recorder, "recorded_data")
                                        and recorder.recorded_data
                                    ):
                                        greeting_audio_raw: bytes = b"".join(recorder.recorded_data)
                                        # Convert raw audio to WAV format before saving
                                        greeting_audio_wav: bytes = pbx._build_wav_file(
                                            greeting_audio_raw
                                        )
                                        voicemail_ivr.save_recorded_greeting(greeting_audio_wav)
                                        pbx.logger.info(
                                            f"Saved recorded greeting as WAV ({len(greeting_audio_wav)} bytes, {len(greeting_audio_raw)} bytes raw audio)"
                                        )
                                    # Handle the returned action
                                    if action.get("action") == "play_prompt":
                                        # Play greeting review menu prompt
                                        prompt_type = action.get("prompt", "greeting_review_menu")
                                        prompt_audio = get_prompt_audio(prompt_type)
                                        with tempfile.NamedTemporaryFile(
                                            suffix=".wav", delete=False
                                        ) as temp_file:
                                            temp_file.write(prompt_audio)
                                            prompt_file = temp_file.name
                                        try:
                                            player.play_file(prompt_file)
                                        finally:
                                            with contextlib.suppress(OSError):
                                                Path(prompt_file).unlink()
                                    elif action.get("action") == "stop_recording":
                                        # Also valid, just log it
                                        pbx.logger.info(
                                            "IVR returned stop_recording action, continuing"
                                        )
                                    else:
                                        # Unexpected action type
                                        pbx.logger.warning(
                                            f"Unexpected action from IVR after #: {action.get('action')}"
                                        )
                                    # Clear recorder after saving
                                    recorder.recorded_data = []
                                    break

                        elif action["action"] == "play_greeting":
                            # Play back the recorded greeting for review
                            if call.state == CallState.ENDED:
                                pbx.logger.info(f"Call {call_id} ended, cannot play greeting")
                                break

                            greeting_data: bytes | None = voicemail_ivr.get_recorded_greeting()
                            if greeting_data:
                                pbx.logger.info(
                                    f"Playing recorded greeting for review ({len(greeting_data)} bytes)"
                                )

                                # Greeting is already in WAV format (converted when recorded)
                                with tempfile.NamedTemporaryFile(
                                    suffix=".wav", delete=False
                                ) as temp_file:
                                    temp_file.write(greeting_data)
                                    greeting_file: str = temp_file.name

                                try:
                                    player.play_file(greeting_file)
                                finally:
                                    with contextlib.suppress(OSError):
                                        Path(greeting_file).unlink()

                                time.sleep(0.5)

                                # Play review menu again
                                review_prompt: bytes = get_prompt_audio("greeting_review_menu")
                                with tempfile.NamedTemporaryFile(
                                    suffix=".wav", delete=False
                                ) as temp_file:
                                    temp_file.write(review_prompt)
                                    prompt_file = temp_file.name

                                try:
                                    player.play_file(prompt_file)
                                finally:
                                    with contextlib.suppress(OSError):
                                        Path(prompt_file).unlink()
                            else:
                                pbx.logger.warning(
                                    "No recorded greeting data available for playback"
                                )

                        elif action["action"] == "collect_digit":
                            # Digit is being collected (e.g., PIN entry)
                            # No additional action needed - digit is already stored in IVR state
                            # Just continue the loop to wait for more digits
                            pbx.logger.debug("[VM IVR] Collecting digit, waiting for more input...")

                        else:
                            # Unknown action type
                            pbx.logger.warning(
                                f"[VM IVR] Unknown action type: {action.get('action')} - continuing"
                            )

                        # Clear audio buffer after processing DTMF
                        # Note: Directly modifying internal state - consider
                        # adding clear() method to RTPRecorder
                        if hasattr(recorder, "recorded_data"):
                            recorder.recorded_data = []

                    # Timeout after 60 seconds of no activity
                    if time.time() - last_audio_check > 60:
                        pbx.logger.info(f"Voicemail IVR timeout for {call.voicemail_extension}")
                        ivr_active = False

                pbx.logger.info("")
                pbx.logger.info(f"{'=' * 70}")
                pbx.logger.info("VOICEMAIL IVR SESSION COMPLETED")
                pbx.logger.info(f"  Call ID: {call_id}")
                pbx.logger.info(f"  Extension: {call.voicemail_extension}")
                pbx.logger.info(f"  Final State: {call.state}")
                pbx.logger.info(f"{'=' * 70}")

            finally:
                pbx.logger.info("[VM IVR] Cleaning up RTP player and recorder...")
                player.stop()
                recorder.stop()
                pbx.logger.info("[VM IVR] ✓ RTP resources released")

            # End the call
            pbx.logger.info(f"[VM IVR] Ending call {call_id}...")
            pbx.end_call(call_id)
            pbx.logger.info("[VM IVR] ✓ Call ended")

        except (KeyError, OSError, TypeError, ValueError) as e:
            pbx.logger.error("")
            pbx.logger.error(f"{'=' * 70}")
            pbx.logger.error("ERROR IN VOICEMAIL IVR SESSION")
            pbx.logger.error(f"  Call ID: {call_id}")
            pbx.logger.error(f"  Error: {e}")
            pbx.logger.error(f"{'=' * 70}")
            traceback.print_exc()
            try:
                pbx.end_call(call_id)
            except Exception as e:
                pbx.logger.error(f"[VM IVR] Error ending call during cleanup: {e}")

    def monitor_voicemail_dtmf(self, call_id: str, call: Any, recorder: Any) -> None:
        """
        Monitor for DTMF # key press during voicemail recording
        When # is detected, complete the voicemail recording early

        Args:
            call_id: Call identifier
            call: Call object
            recorder: RTPRecorder instance
        """
        from pbx.utils.dtmf import DTMFDetector

        pbx = self.pbx_core

        try:
            # Create DTMF detector
            dtmf_detector = DTMFDetector(sample_rate=8000)

            # Constants for DTMF detection
            DTMF_DETECTION_PACKETS: int = 40  # 40 packets * 20ms = 0.8s of audio
            # Minimum audio data needed for reliable DTMF detection
            MIN_AUDIO_BYTES_FOR_DTMF: int = 1600

            pbx.logger.info(f"Started DTMF monitoring for voicemail recording on call {call_id}")

            # Monitor for # key press
            while recorder.running and call.state.value != "ended":
                time.sleep(0.1)

                # Check for recorded audio (DTMF tones from caller)
                if hasattr(recorder, "recorded_data") and recorder.recorded_data:
                    # Get recent audio data
                    if len(recorder.recorded_data) > 0:
                        # Collect last portion of audio for DTMF detection
                        recent_audio = b"".join(recorder.recorded_data[-DTMF_DETECTION_PACKETS:])

                        if len(recent_audio) > MIN_AUDIO_BYTES_FOR_DTMF:
                            # Convert bytes to audio samples for DTMF detection
                            # G.711 u-law is 8-bit samples, one byte per sample
                            # Use struct.unpack for efficient batch conversion
                            samples: list[float] = []
                            # Process in chunks for efficiency
                            chunk_size: int = min(
                                len(recent_audio), 8192
                            )  # Process up to 8KB at once
                            for i in range(0, len(recent_audio), chunk_size):
                                chunk = recent_audio[i : i + chunk_size]
                                # Unpack bytes and convert to float samples
                                unpacked = struct.unpack(f"{len(chunk)}B", chunk)
                                # Convert unsigned byte to signed float (-1.0
                                # to 1.0)
                                samples.extend([(b - 128) / 128.0 for b in unpacked])

                            # Detect DTMF
                            digit: str | None = dtmf_detector.detect_tone(samples)

                            if digit == "#":
                                pbx.logger.info(
                                    f"Detected # key press during voicemail recording on call {call_id}"
                                )
                                # Complete the voicemail recording
                                self.complete_voicemail_recording(call_id)
                                return

            pbx.logger.debug(f"DTMF monitoring ended for voicemail recording on call {call_id}")

        except (KeyError, TypeError, ValueError, struct.error) as e:
            pbx.logger.error(f"Error in voicemail DTMF monitoring: {e}")
            pbx.logger.error(traceback.format_exc())

    def complete_voicemail_recording(self, call_id: str) -> None:
        """
        Complete voicemail recording and save the message

        Args:
            call_id: Call identifier
        """
        pbx = self.pbx_core

        call = pbx.call_manager.get_call(call_id)
        if not call:
            pbx.logger.warning(f"Cannot complete voicemail for non-existent call {call_id}")
            return

        # Get the recorder if it exists
        recorder: Any | None = getattr(call, "voicemail_recorder", None)
        if recorder:
            # Stop recording
            recorder.stop()

            # Get recorded audio
            audio_data: bytes = recorder.get_recorded_audio()
            duration: float = recorder.get_duration()

            if audio_data and len(audio_data) > 0:
                # Build proper WAV file header for the recorded audio
                wav_data: bytes = pbx._build_wav_file(audio_data)

                # Save to voicemail system
                pbx.voicemail_system.save_message(
                    extension_number=call.to_extension,
                    caller_id=call.from_extension,
                    audio_data=wav_data,
                    duration=duration,
                )
                pbx.logger.info(
                    f"Saved voicemail for extension {call.to_extension} from {call.from_extension}, duration: {duration}s"
                )
            else:
                pbx.logger.warning(f"No audio recorded for voicemail on call {call_id}")
                # Still create a minimal voicemail to indicate the attempt
                placeholder_audio: bytes = pbx._build_wav_file(b"")
                pbx.voicemail_system.save_message(
                    extension_number=call.to_extension,
                    caller_id=call.from_extension,
                    audio_data=placeholder_audio,
                    duration=0,
                )

        # End the call
        pbx.end_call(call_id)
