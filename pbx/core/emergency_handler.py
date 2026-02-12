"""
Emergency call handler for PBX Core

Extracts emergency call handling logic from PBXCore into a dedicated class,
implementing Kari's Law compliance for direct 911 dialing and routing.
"""


class EmergencyHandler:
    """Handles emergency calls (911) according to Kari's Law"""

    def __init__(self, pbx_core):
        """
        Initialize EmergencyHandler with reference to PBXCore.

        Args:
            pbx_core: The PBXCore instance
        """
        self.pbx_core = pbx_core

    def handle_emergency_call(self, from_ext, to_ext, call_id, message, from_addr):
        """
        Handle emergency call (911) according to Kari's Law

        Federal law requires direct 911 dialing without prefix and immediate routing.

        Args:
            from_ext: Calling extension
            to_ext: Dialed number (911, 9911, etc.)
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Caller address

        Returns:
            True if emergency call was handled
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        pbx = self.pbx_core

        pbx.logger.critical("=" * 70)
        pbx.logger.critical("🚨 EMERGENCY CALL INITIATED")
        pbx.logger.critical("=" * 70)

        # Handle via Kari's Law compliance module
        success, routing_info = pbx.karis_law.handle_emergency_call(
            caller_extension=from_ext, dialed_number=to_ext, call_id=call_id, from_addr=from_addr
        )

        if not success:
            pbx.logger.error(
                f"Emergency call handling failed: {routing_info.get('error', 'Unknown error')}"
            )
            return False

        if not routing_info.get("success"):
            pbx.logger.error(
                f"Emergency call routing failed: {routing_info.get('error', 'No trunk available')}"
            )
            # Still return True because the call was processed (notification sent)
            # but log the routing failure critically
            pbx.logger.critical("⚠️  EMERGENCY CALL COULD NOT BE ROUTED TO 911")
            return True

        # Parse SDP from caller's INVITE
        caller_sdp = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

            if caller_sdp:
                pbx.logger.critical(f"Caller RTP: {caller_sdp['address']}:{caller_sdp['port']}")

        # Create call record for tracking
        normalized_number = routing_info.get("destination", "911")
        call = pbx.call_manager.create_call(call_id, from_ext, normalized_number)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.is_emergency = True
        call.emergency_routing = routing_info

        # Start CDR record
        pbx.cdr_system.start_record(call_id, from_ext, normalized_number)

        # Allocate RTP relay for the call
        rtp_ports = pbx.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports

            # Set caller's endpoint if we have RTP info
            if caller_sdp:
                caller_endpoint = (caller_sdp["address"], caller_sdp["port"])
                relay_info = pbx.rtp_relay.active_relays.get(call_id)
                if relay_info:
                    handler = relay_info["handler"]
                    handler.set_endpoint1(caller_endpoint)
                    pbx.logger.info("Emergency call RTP relay configured")

        # In production, this would:
        # 1. Route the call through the emergency trunk to 911
        # 2. Provide location information (Ray Baum's Act)
        # 3. Maintain the call until disconnected
        # 4. Log all details for regulatory compliance

        # For now, send 200 OK to acknowledge the call was processed
        # The trunk system will handle actual routing
        server_ip = pbx._get_server_ip()

        # Build SDP for response
        if caller_sdp:
            caller_codecs = caller_sdp.get("formats", ["0", "8"])
        else:
            caller_codecs = ["0", "8"]

        rtp_port = rtp_ports[0] if rtp_ports else 10000
        response_sdp = SDPBuilder.build_audio_sdp(
            local_ip=server_ip,
            local_port=rtp_port,
            session_id=call_id,
            codecs=caller_codecs,
        )

        # Send 200 OK
        ok_response = SIPMessageBuilder.build_response(
            status_code=200,
            status_text="OK",
            request_msg=message,
            body=response_sdp,
        )

        pbx.sip_server._send_message(ok_response.build(), from_addr)

        pbx.logger.critical("Emergency call acknowledged and routed")
        pbx.logger.critical(f"Trunk: {routing_info.get('trunk_name', 'Unknown')}")
        pbx.logger.critical("=" * 70)

        return True
