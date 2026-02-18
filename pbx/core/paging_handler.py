"""
Paging handler for PBX Core

Extracts paging system logic from PBXCore into a dedicated class,
including page initiation, zone management, and audio routing to DAC devices.
"""

import time
from typing import Any


class PagingHandler:
    """Handles paging system calls and audio routing"""

    def __init__(self, pbx_core: Any) -> None:
        """
        Initialize PagingHandler with reference to PBXCore.

        Args:
            pbx_core: The PBXCore instance
        """
        self.pbx_core: Any = pbx_core

    def handle_paging(
        self,
        from_ext: str,
        to_ext: str,
        call_id: str,
        message: Any,
        from_addr: tuple[str, int],
    ) -> bool:
        """
        Handle paging system calls (7xx pattern or all-call)

        Args:
            from_ext: Calling extension
            to_ext: Paging extension (e.g., 700, 701, 702)
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

        pbx.logger.info(f"Paging call: {from_ext} -> {to_ext}")

        # Initiate the page through the paging system
        page_id: str | None = pbx.paging_system.initiate_page(from_ext, to_ext)
        if not page_id:
            pbx.logger.error(f"Failed to initiate page from {from_ext} to {to_ext}")
            return False

        # Get zone information
        page_info: dict[str, Any] | None = pbx.paging_system.get_page_info(page_id)
        if not page_info:
            pbx.logger.error(f"Failed to get page info for {page_id}")
            return False

        # Parse SDP from caller's INVITE
        caller_sdp: dict[str, Any] | None = None
        caller_codecs: list[str] | None = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

            if caller_sdp:
                pbx.logger.info(f"Paging caller RTP: {caller_sdp['address']}:{caller_sdp['port']}")
                # Extract caller's codec list for negotiation
                caller_codecs = caller_sdp.get("formats", None)

        # Create call for paging
        call = pbx.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.paging_active = True
        call.page_id = page_id
        call.paging_zones = page_info.get("zone_names", "Unknown")

        # Start CDR record for analytics
        pbx.cdr_system.start_record(call_id, from_ext, to_ext)

        # Allocate RTP ports
        rtp_ports = pbx.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
        else:
            pbx.logger.error(f"Failed to allocate RTP ports for paging {call_id}")
            pbx.paging_system.end_page(page_id)
            return False

        # Get configured paging gateway device
        zones: list[dict[str, Any]] = page_info.get("zones", [])
        if not zones:
            pbx.logger.error(f"No zones configured for paging extension {to_ext}")
            pbx.paging_system.end_page(page_id)
            return False

        # For now, use the first zone's DAC device
        zone: dict[str, Any] = zones[0]
        dac_device_id: str | None = zone.get("dac_device")

        if not dac_device_id:
            pbx.logger.warning(f"No DAC device configured for zone {zone.get('name')}")
            # Continue anyway - this allows testing without hardware

        # Find the DAC device configuration
        dac_device: dict[str, Any] | None = None
        for device in pbx.paging_system.get_dac_devices():
            if device.get("device_id") == dac_device_id:
                dac_device = device
                break

        # Answer the call immediately (auto-answer for paging)
        server_ip: str = pbx._get_server_ip()

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
                f"Paging: Detected caller phone model: {caller_phone_model}, "
                f"offering codecs: {codecs_for_caller}"
            )

        # Build SDP for answering, using phone-model-specific codecs
        # Get DTMF payload type from config
        dtmf_payload_type = pbx._get_dtmf_payload_type()
        ilbc_mode = pbx._get_ilbc_mode()
        paging_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id,
            codecs=codecs_for_caller,
            dtmf_payload_type=dtmf_payload_type,
            ilbc_mode=ilbc_mode,
        )

        # Send 200 OK to answer the call
        ok_response = SIPMessageBuilder.build_response(
            200, "OK", call.original_invite, body=paging_sdp
        )
        ok_response.set_header("Content-type", "application/sdp")

        # Build Contact header
        sip_port: int = pbx.config.get("server.sip_port", 5060)
        contact_uri: str = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header("Contact", contact_uri)

        # Send to caller
        pbx.sip_server._send_message(ok_response.build(), call.caller_addr)
        pbx.logger.info(f"Answered paging call {call_id} - Paging {page_info.get('zone_names')}")

        # Mark call as connected
        call.connect()

        # If we have a DAC device configured, route audio to it
        if dac_device:
            # Start paging session thread to handle audio routing
            paging_thread = threading.Thread(
                target=self._paging_session, args=(call_id, call, dac_device, page_info)
            )
            paging_thread.daemon = True
            paging_thread.start()
        else:
            # No hardware - just maintain the call for testing
            pbx.logger.warning(f"Paging call {call_id} connected but no DAC device available")
            pbx.logger.info(
                f"Audio from {from_ext} would be routed to {page_info.get('zone_names')}"
            )

        return True

    def _paging_session(
        self,
        call_id: str,
        call: Any,
        dac_device: dict[str, Any],
        page_info: dict[str, Any],
    ) -> None:
        """
        Handle paging session with audio routing to DAC device

        Args:
            call_id: Call identifier
            call: Call object
            dac_device: DAC device configuration
            page_info: Paging information dictionary
        """
        pbx = self.pbx_core

        try:
            pbx.logger.info(f"Paging session started for {call_id}")
            pbx.logger.info(
                f"DAC device: {dac_device.get('device_id')} ({dac_device.get('device_type')})"
            )
            pbx.logger.info(f"Paging zones: {page_info.get('zone_names')}")

            # Get DAC device SIP information
            dac_sip_uri: str | None = dac_device.get("sip_uri")
            dac_ip: str | None = dac_device.get("ip_address")
            dac_port: int = dac_device.get("port", 5060)

            if not dac_sip_uri or not dac_ip:
                pbx.logger.error(
                    f"DAC device {dac_device.get('device_id')} missing SIP configuration"
                )
                return

            # Establish SIP connection to the DAC gateway device
            import uuid

            from pbx.sip.message import SIPMessageBuilder
            from pbx.sip.sdp import SDPBuilder

            server_ip: str = pbx._get_server_ip()
            sip_port: int = pbx.config.get("server.sip_port", 5060)
            dac_call_id = str(uuid.uuid4())

            # Build SDP for DAC connection (sendonly - paging is one-way audio)
            dac_rtp_port: int = call.rtp_ports[1] if call.rtp_ports else 10001
            dac_sdp = SDPBuilder.build_audio_sdp(server_ip, dac_rtp_port, session_id=dac_call_id)

            # Build INVITE to DAC device
            invite_msg = SIPMessageBuilder.build_request(
                method="INVITE",
                uri=dac_sip_uri,
                from_addr=f"<sip:paging@{server_ip}>",
                to_addr=f"<sip:paging@{dac_ip}:{dac_port}>",
                call_id=dac_call_id,
                cseq=1,
                body=dac_sdp,
            )
            invite_msg.set_header("Content-type", "application/sdp")
            invite_msg.set_header("Contact", f"<sip:paging@{server_ip}:{sip_port}>")

            # Add zone selection header if multi-zone DAC
            zones: list[dict[str, Any]] = page_info.get("zones", [])
            if zones:
                zone_id: str | None = zones[0].get("zone_id")
                if zone_id:
                    invite_msg.set_header("X-Paging-Zone", zone_id)

            # Send INVITE to DAC device
            dac_addr: tuple[str, int] = (dac_ip, dac_port)
            try:
                pbx.sip_server._send_message(invite_msg.build(), dac_addr)
                pbx.logger.info(f"Sent INVITE to DAC device at {dac_ip}:{dac_port}")
            except Exception as invite_err:
                pbx.logger.error(f"Failed to send INVITE to DAC: {invite_err}")
                return

            # Set up RTP relay to forward audio from caller to DAC
            if call.caller_rtp:
                caller_endpoint: tuple[str, int] = (
                    call.caller_rtp["address"],
                    call.caller_rtp["port"],
                )
                dac_endpoint: tuple[str, int] = (dac_ip, dac_port + 1)

                # Configure RTP relay for forwarding
                pbx.rtp_relay.set_endpoints(call.call_id, caller_endpoint, dac_endpoint)
                pbx.logger.info(f"RTP relay configured: {caller_endpoint} -> {dac_endpoint}")
                pbx.logger.info(
                    f"Audio relay active: Caller -> PBX:{call.rtp_ports[0]} -> DAC:{dac_ip}"
                )

            # Monitor the call until it ends
            while call.state.value != "ended":
                time.sleep(1)

            # Send BYE to DAC device to end the paging session
            try:
                bye_msg = SIPMessageBuilder.build_request(
                    method="BYE",
                    uri=dac_sip_uri,
                    from_addr=f"<sip:paging@{server_ip}>",
                    to_addr=f"<sip:paging@{dac_ip}:{dac_port}>",
                    call_id=dac_call_id,
                    cseq=2,
                )
                pbx.sip_server._send_message(bye_msg.build(), dac_addr)
                pbx.logger.info("Sent BYE to DAC device")
            except Exception as bye_err:
                pbx.logger.error(f"Failed to send BYE to DAC: {bye_err}")

            pbx.logger.info(f"Paging session ended for {call_id}")

            # End the page
            pbx.paging_system.end_page(call.page_id)

        except (KeyError, TypeError, ValueError) as e:
            pbx.logger.error(f"Error in paging session {call_id}: {e}")
            pbx.logger.debug("Paging session error details", exc_info=True)
