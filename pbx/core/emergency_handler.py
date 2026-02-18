"""
Emergency call handler for PBX Core

Extracts emergency call handling logic from PBXCore into a dedicated class,
implementing Kari's Law compliance for direct 911 dialing and routing.
"""

from typing import Any


class EmergencyHandler:
    """Handles emergency calls (911) according to Kari's Law"""

    def __init__(self, pbx_core: Any) -> None:
        """
        Initialize EmergencyHandler with reference to PBXCore.

        Args:
            pbx_core: The PBXCore instance
        """
        self.pbx_core: Any = pbx_core

    def handle_emergency_call(
        self,
        from_ext: str,
        to_ext: str,
        call_id: str,
        message: Any,
        from_addr: tuple[str, int],
    ) -> bool:
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
        success: bool
        routing_info: dict[str, Any]
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
        caller_sdp: dict[str, Any] | None = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

            if caller_sdp:
                pbx.logger.critical(f"Caller RTP: {caller_sdp['address']}:{caller_sdp['port']}")

        # Create call record for tracking
        normalized_number: str = routing_info.get("destination", "911")
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

            # set caller's endpoint if we have RTP info
            if caller_sdp:
                caller_endpoint: tuple[str, int] = (
                    caller_sdp["address"],
                    caller_sdp["port"],
                )
                relay_info = pbx.rtp_relay.active_relays.get(call_id)
                if relay_info:
                    handler = relay_info["handler"]
                    handler.set_endpoint1(caller_endpoint)
                    pbx.logger.info("Emergency call RTP relay configured")

        # Route through emergency trunk if available
        trunk_name: str = routing_info.get("trunk_name", "")
        trunk_config: dict[str, Any] | None = None
        if trunk_name and hasattr(pbx, "trunk_system"):
            trunk_config = pbx.trunk_system.get_trunk(trunk_name)

        if trunk_config:
            # Route via SIP trunk to PSAP
            trunk_host = trunk_config.get("host", "")
            trunk_port = trunk_config.get("port", 5060)
            if trunk_host:
                pbx.logger.critical(
                    f"Routing emergency call via trunk {trunk_name} to {trunk_host}:{trunk_port}"
                )
                # Build INVITE for trunk with location info (Ray Baum's Act / PIDF-LO)
                trunk_invite = SIPMessageBuilder.build_request(
                    method="INVITE",
                    uri=f"sip:{normalized_number}@{trunk_host}:{trunk_port}",
                    from_addr=f"<sip:{from_ext}@{pbx._get_server_ip()}>",
                    to_addr=f"<sip:{normalized_number}@{trunk_host}>",
                    call_id=call_id,
                    cseq=1,
                )

                # Add Geolocation header with PIDF-LO for Ray Baum's Act
                location_info = routing_info.get("location", {})
                if location_info:
                    trunk_invite.set_header(
                        "Geolocation",
                        f"<cid:{call_id}@{pbx._get_server_ip()}>",
                    )
                    trunk_invite.set_header("Geolocation-Routing", "yes")

                # Add Priority header for emergency
                trunk_invite.set_header("Priority", "emergency")

                # Include original SDP
                if message.body:
                    trunk_invite.body = message.body
                    trunk_invite.set_header("Content-type", "application/sdp")
                    trunk_invite.set_header("Content-Length", str(len(message.body)))

                # Send to trunk
                try:
                    pbx.sip_server._send_message(trunk_invite.build(), (trunk_host, trunk_port))
                    call.callee_addr = (trunk_host, trunk_port)
                    pbx.logger.critical("Emergency INVITE sent to trunk")
                except Exception as trunk_err:
                    pbx.logger.critical(f"Failed to route emergency call via trunk: {trunk_err}")

        # Log all details for regulatory compliance
        compliance_log: dict[str, Any] = {
            "event": "EMERGENCY_CALL",
            "call_id": call_id,
            "caller_extension": from_ext,
            "dialed_number": to_ext,
            "normalized_destination": normalized_number,
            "trunk_name": trunk_name,
            "caller_address": str(from_addr),
            "location_info": routing_info.get("location", {}),
            "timestamp": str(__import__("datetime").datetime.now(__import__("datetime").UTC)),
            "karis_law_compliant": True,
        }
        pbx.logger.critical(f"Emergency call compliance log: {compliance_log}")

        # Store compliance record in CDR
        if hasattr(pbx, "cdr_system"):
            pbx.cdr_system.add_metadata(call_id, "emergency_compliance", compliance_log)

        server_ip: str = pbx._get_server_ip()

        # Build SDP for response
        caller_codecs: list[str]
        if caller_sdp:
            caller_codecs = caller_sdp.get("formats", ["0", "8"])
        else:
            caller_codecs = ["0", "8"]

        rtp_port: int = rtp_ports[0] if rtp_ports else 10000
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
