"""
Core PBX implementation
Central coordinator for all PBX functionality
"""
import re
import threading
from pbx.utils.config import Config
from pbx.utils.logger import get_logger, PBXLogger
from pbx.sip.server import SIPServer
from pbx.rtp.handler import RTPRelay
from pbx.core.call import CallManager
from pbx.features.extensions import ExtensionRegistry
from pbx.features.voicemail import VoicemailSystem
from pbx.features.conference import ConferenceSystem
from pbx.features.call_recording import CallRecordingSystem
from pbx.features.call_queue import QueueSystem
from pbx.features.presence import PresenceSystem
from pbx.features.call_parking import CallParkingSystem
from pbx.features.cdr import CDRSystem
from pbx.features.music_on_hold import MusicOnHold
from pbx.features.sip_trunk import SIPTrunkSystem
from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.api.rest_api import PBXAPIServer


class PBXCore:
    """Main PBX system coordinator"""
    
    def __init__(self, config_file="config.yml"):
        """
        Initialize PBX core
        
        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_file)
        
        # Setup logging
        log_config = self.config.get('logging', {})
        PBXLogger().setup(
            log_level=log_config.get('level', 'INFO'),
            log_file=log_config.get('file', 'logs/pbx.log'),
            console=log_config.get('console', True)
        )
        self.logger = get_logger()
        
        # Initialize core components
        self.extension_registry = ExtensionRegistry(self.config)
        self.call_manager = CallManager()
        self.rtp_relay = RTPRelay(
            self.config.get('server.rtp_port_range_start', 10000),
            self.config.get('server.rtp_port_range_end', 20000)
        )
        
        # Initialize SIP server
        self.sip_server = SIPServer(
            host=self.config.get('server.sip_host', '0.0.0.0'),
            port=self.config.get('server.sip_port', 5060),
            pbx_core=self
        )
        
        # Initialize advanced features
        voicemail_path = self.config.get('voicemail.storage_path', 'voicemail')
        self.voicemail_system = VoicemailSystem(storage_path=voicemail_path, config=self.config)
        self.conference_system = ConferenceSystem()
        self.recording_system = CallRecordingSystem(
            auto_record=self.config.get('features.call_recording', False)
        )
        self.queue_system = QueueSystem()
        self.presence_system = PresenceSystem()
        self.parking_system = CallParkingSystem()
        self.cdr_system = CDRSystem()
        self.moh_system = MusicOnHold()
        self.trunk_system = SIPTrunkSystem()
        
        # Initialize phone provisioning if enabled
        if self.config.get('provisioning.enabled', False):
            self.phone_provisioning = PhoneProvisioning(self.config)
            self._load_provisioning_devices()
        else:
            self.phone_provisioning = None
        
        # Initialize API server
        api_host = self.config.get('api.host', '0.0.0.0')
        api_port = self.config.get('api.port', 8080)
        self.api_server = PBXAPIServer(self, api_host, api_port)
        
        self.running = False
        
        self.logger.info("PBX Core initialized with all features")
    
    def _load_provisioning_devices(self):
        """Load provisioning devices from configuration"""
        if not self.phone_provisioning:
            return
        
        devices_config = self.config.get('provisioning.devices', [])
        for device_config in devices_config:
            mac = device_config.get('mac')
            extension = device_config.get('extension')
            vendor = device_config.get('vendor')
            model = device_config.get('model')
            
            if all([mac, extension, vendor, model]):
                try:
                    self.phone_provisioning.register_device(mac, extension, vendor, model)
                    self.logger.info(f"Loaded provisioning device {mac} for extension {extension}")
                except Exception as e:
                    self.logger.error(f"Failed to load provisioning device {mac}: {e}")
    
    def start(self):
        """Start PBX system"""
        self.logger.info("Starting PBX system...")
        
        # Start SIP server
        if not self.sip_server.start():
            self.logger.error("Failed to start SIP server")
            return False
        
        # Start API server
        if not self.api_server.start():
            self.logger.warning("Failed to start API server (non-critical)")
        
        # Register SIP trunks
        self.trunk_system.register_all()
        
        self.running = True
        self.logger.info("PBX system started successfully")
        return True
    
    def stop(self):
        """Stop PBX system"""
        self.logger.info("Stopping PBX system...")
        self.running = False
        
        # Stop API server
        self.api_server.stop()
        
        # Stop SIP server
        self.sip_server.stop()
        
        # End all active calls
        for call in self.call_manager.get_active_calls():
            self.call_manager.end_call(call.call_id)
            self.rtp_relay.release_relay(call.call_id)
            
            # Stop any recordings
            if self.recording_system.is_recording(call.call_id):
                self.recording_system.stop_recording(call.call_id)
        
        self.logger.info("PBX system stopped")
    
    def register_extension(self, from_header, addr):
        """
        Register extension
        
        Args:
            from_header: SIP From header
            addr: Network address (host, port)
            
        Returns:
            True if registration successful
        """
        # Parse extension number from header
        # Format: "Display Name" <sip:1001@host>
        match = re.search(r'sip:(\d+)@', from_header)
        if match:
            extension_number = match.group(1)
            
            # Verify extension exists in configuration
            extension = self.config.get_extension(extension_number)
            if extension:
                self.extension_registry.register(extension_number, addr)
                self.logger.info(f"Extension {extension_number} registered from {addr}")
                return True
            else:
                self.logger.warning(f"Unknown extension {extension_number} attempted registration")
                return False
        
        self.logger.warning(f"Could not parse extension from {from_header}")
        return False
    
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
        from pbx.sip.sdp import SDPSession, SDPBuilder
        from pbx.sip.message import SIPMessageBuilder
        
        # Parse extension numbers
        from_match = re.search(r'sip:(\d+)@', from_header)
        to_match = re.search(r'sip:(\d+)@', to_header)
        
        if not from_match or not to_match:
            self.logger.warning(f"Could not parse extensions from headers")
            return False
        
        from_ext = from_match.group(1)
        to_ext = to_match.group(1)
        
        # Check if destination extension is registered
        if not self.extension_registry.is_registered(to_ext):
            self.logger.warning(f"Extension {to_ext} is not registered")
            return False
        
        # Check dialplan
        if not self._check_dialplan(to_ext):
            self.logger.warning(f"Extension {to_ext} not allowed by dialplan")
            return False
        
        # Parse SDP from caller's INVITE
        caller_sdp = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()
            
            if caller_sdp:
                self.logger.info(f"Caller RTP: {caller_sdp['address']}:{caller_sdp['port']}")
        
        # Create call
        call = self.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message  # Store original INVITE for later response
        
        # Allocate RTP relay
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
            
            # Store caller's RTP info for later relay setup
            if caller_sdp:
                call.caller_rtp = caller_sdp
                call.caller_addr = from_addr
                
                # Get the RTP handler and set remote endpoint for caller side
                relay_info = self.rtp_relay.active_relays.get(call_id)
                if relay_info:
                    handler = relay_info['handler']
                    # For now, just log - full relay needs bidirectional forwarding
                    self.logger.info(f"RTP relay allocated on port {rtp_ports[0]}")
        
        # Get destination extension's address
        dest_ext_obj = self.extension_registry.get(to_ext)
        if not dest_ext_obj or not dest_ext_obj.address:
            self.logger.error(f"Cannot get address for extension {to_ext}")
            return False
        
        # Build SDP for forwarding INVITE to callee
        # Use the server's external IP address for SDP
        server_ip = self._get_server_ip()
        
        if rtp_ports:
            # Create new INVITE with PBX's RTP endpoint in SDP
            callee_sdp_body = SDPBuilder.build_audio_sdp(
                server_ip,
                rtp_ports[0],
                session_id=call_id
            )
            
            # Forward INVITE to callee
            invite_to_callee = SIPMessageBuilder.build_request(
                method='INVITE',
                uri=f"sip:{to_ext}@{server_ip}",
                from_addr=from_header,
                to_addr=to_header,
                call_id=call_id,
                cseq=int(message.get_header('CSeq').split()[0]),
                body=callee_sdp_body
            )
            
            # Add required headers
            invite_to_callee.set_header('Via', message.get_header('Via'))
            invite_to_callee.set_header('Contact', f"<sip:{from_ext}@{server_ip}:{self.config.get('server.sip_port', 5060)}>")
            invite_to_callee.set_header('Content-Type', 'application/sdp')
            
            # Send to destination
            self.sip_server._send_message(invite_to_callee.build(), dest_ext_obj.address)
            
            self.logger.info(f"Forwarded INVITE to {to_ext} at {dest_ext_obj.address}")
            self.logger.info(f"Routing call {call_id}: {from_ext} -> {to_ext} via RTP relay {rtp_ports[0]}")
            
            # Start no-answer timer to route to voicemail if not answered
            no_answer_timeout = self.config.get('voicemail.no_answer_timeout', 30)
            call.no_answer_timer = threading.Timer(
                no_answer_timeout,
                self._handle_no_answer,
                args=(call_id,)
            )
            call.no_answer_timer.start()
            self.logger.info(f"Started no-answer timer ({no_answer_timeout}s) for call {call_id}")
        
        return True
    
    def _get_server_ip(self):
        """
        Get server's IP address for SDP
        
        Returns:
            Server IP address as string
        """
        # First, try to get configured external IP
        external_ip = self.config.get('server.external_ip')
        if external_ip:
            return external_ip
        
        # Fallback: try to detect local IP
        import socket
        try:
            # Create a socket to determine the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"  # Last resort fallback
    
    def handle_callee_answer(self, call_id, response_message, callee_addr):
        """
        Handle when callee answers the call
        
        Args:
            call_id: Call identifier
            response_message: 200 OK response from callee
            callee_addr: Callee's address
        """
        from pbx.sip.sdp import SDPSession, SDPBuilder
        from pbx.sip.message import SIPMessageBuilder
        
        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.error(f"Call {call_id} not found")
            return
        
        # Parse callee's SDP from 200 OK
        callee_sdp = None
        if response_message.body:
            callee_sdp_obj = SDPSession()
            callee_sdp_obj.parse(response_message.body)
            callee_sdp = callee_sdp_obj.get_audio_info()
            
            if callee_sdp:
                self.logger.info(f"Callee RTP: {callee_sdp['address']}:{callee_sdp['port']}")
                call.callee_rtp = callee_sdp
                call.callee_addr = callee_addr
        
        # Now we have both endpoints, set up the RTP relay
        if call.caller_rtp and call.callee_rtp and call.rtp_ports:
            caller_endpoint = (call.caller_rtp['address'], call.caller_rtp['port'])
            callee_endpoint = (call.callee_rtp['address'], call.callee_rtp['port'])
            
            self.rtp_relay.set_endpoints(call_id, caller_endpoint, callee_endpoint)
            self.logger.info(f"RTP relay connected for call {call_id}")
        
        # Cancel no-answer timer if it's running
        if call.no_answer_timer:
            call.no_answer_timer.cancel()
            self.logger.info(f"Cancelled no-answer timer for call {call_id}")
        
        # Mark call as connected
        call.connect()
        
        # Send 200 OK back to caller with PBX's RTP endpoint
        server_ip = self._get_server_ip()
        
        if call.rtp_ports and call.caller_addr:
            # Build SDP for caller (with PBX RTP endpoint)
            caller_response_sdp = SDPBuilder.build_audio_sdp(
                server_ip,
                call.rtp_ports[0],
                session_id=call_id
            )
            
            # Build 200 OK for caller using original INVITE
            if call.original_invite:
                ok_response = SIPMessageBuilder.build_response(
                    200,
                    "OK",
                    call.original_invite,
                    body=caller_response_sdp
                )
                ok_response.set_header('Content-Type', 'application/sdp')
                
                # Build Contact header
                sip_port = self.config.get('server.sip_port', 5060)
                contact_uri = f"<sip:{call.to_extension}@{server_ip}:{sip_port}>"
                ok_response.set_header('Contact', contact_uri)
                
                # Send to caller
                self.sip_server._send_message(ok_response.build(), call.caller_addr)
                self.logger.info(f"Sent 200 OK to caller for call {call_id}")
    
    def end_call(self, call_id):
        """
        End call
        
        Args:
            call_id: Call identifier
        """
        call = self.call_manager.get_call(call_id)
        if call:
            self.logger.info(f"Ending call {call_id}")
            self.call_manager.end_call(call_id)
            self.rtp_relay.release_relay(call_id)
    
    def transfer_call(self, call_id, new_destination):
        """
        Transfer call to new destination
        
        Args:
            call_id: Call identifier
            new_destination: New destination extension
            
        Returns:
            True if transfer initiated
        """
        call = self.call_manager.get_call(call_id)
        if not call:
            return False
        
        self.logger.info(f"Transferring call {call_id} to {new_destination}")
        
        # In a complete implementation:
        # 1. Send REFER message to transfer call
        # 2. Handle transfer response
        # 3. Update call routing
        
        return True
    
    def hold_call(self, call_id):
        """
        Put call on hold
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if call put on hold
        """
        call = self.call_manager.get_call(call_id)
        if call:
            call.hold()
            self.logger.info(f"Call {call_id} put on hold")
            return True
        return False
    
    def resume_call(self, call_id):
        """
        Resume call from hold
        
        Args:
            call_id: Call identifier
            
        Returns:
            True if call resumed
        """
        call = self.call_manager.get_call(call_id)
        if call:
            call.resume()
            self.logger.info(f"Call {call_id} resumed")
            return True
        return False
    
    def _check_dialplan(self, extension):
        """
        Check if extension matches dialplan rules
        
        Args:
            extension: Extension number
            
        Returns:
            True if allowed by dialplan
        """
        dialplan = self.config.get('dialplan', {})
        
        # Check internal pattern
        internal_pattern = dialplan.get('internal_pattern', '^1[0-9]{3}$')
        if re.match(internal_pattern, extension):
            return True
        
        # Check conference pattern
        conference_pattern = dialplan.get('conference_pattern', '^2[0-9]{3}$')
        if re.match(conference_pattern, extension):
            return True
        
        # Check voicemail pattern
        voicemail_pattern = dialplan.get('voicemail_pattern', '^\\*[0-9]{3}$')
        if re.match(voicemail_pattern, extension):
            return True
        
        return False
    
    def _handle_no_answer(self, call_id):
        """
        Handle no-answer timeout - route call to voicemail
        
        Args:
            call_id: Call identifier
        """
        from pbx.sip.message import SIPMessageBuilder
        
        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.warning(f"No-answer timeout for non-existent call {call_id}")
            return
        
        # Check if call was already answered
        from pbx.core.call import CallState
        if call.state == CallState.CONNECTED:
            self.logger.debug(f"Call {call_id} already answered, ignoring no-answer timeout")
            return
        
        if call.routed_to_voicemail:
            self.logger.debug(f"Call {call_id} already routed to voicemail")
            return
        
        call.routed_to_voicemail = True
        self.logger.info(f"No answer for call {call_id}, routing to voicemail")
        
        # Send 486 Busy Here to caller (or could use 480 Temporarily Unavailable)
        if call.original_invite and call.caller_addr:
            busy_response = SIPMessageBuilder.build_response(
                486,
                "Busy Here - Routing to Voicemail",
                call.original_invite
            )
            self.sip_server._send_message(busy_response.build(), call.caller_addr)
            self.logger.info(f"Sent 486 Busy to caller for call {call_id}")
        
        # In a full implementation, this would:
        # 1. Play voicemail greeting to caller
        # 2. Record the message
        # 3. Save to voicemail system
        # For now, just log and create a placeholder voicemail
        
        # Create a placeholder voicemail message
        placeholder_audio = b'RIFF' + b'\x00' * 40  # Minimal WAV header
        self.voicemail_system.save_message(
            extension_number=call.to_extension,
            caller_id=call.from_extension,
            audio_data=placeholder_audio,
            duration=0
        )
        
        # End the call
        self.end_call(call_id)
    
    def get_status(self):
        """
        Get PBX status
        
        Returns:
            Dictionary with status information
        """
        return {
            'running': self.running,
            'registered_extensions': self.extension_registry.get_registered_count(),
            'active_calls': len(self.call_manager.get_active_calls()),
            'total_calls': len(self.call_manager.call_history),
            'active_recordings': len(self.recording_system.active_recordings),
            'active_conferences': len(self.conference_system.get_active_rooms()),
            'parked_calls': len(self.parking_system.get_parked_calls()),
            'queued_calls': sum(len(q.queue) for q in self.queue_system.queues.values())
        }
