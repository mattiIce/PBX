"""
Core PBX implementation
Central coordinator for all PBX functionality
"""
import re
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
        self.voicemail_system = VoicemailSystem()
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
        
        # Initialize API server
        api_host = self.config.get('api.host', '0.0.0.0')
        api_port = self.config.get('api.port', 8080)
        self.api_server = PBXAPIServer(self, api_host, api_port)
        
        self.running = False
        
        self.logger.info("PBX Core initialized with all features")
    
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
    
    def route_call(self, from_header, to_header, call_id, message):
        """
        Route call from one extension to another
        
        Args:
            from_header: From SIP header
            to_header: To SIP header
            call_id: Call ID
            message: SIP INVITE message
            
        Returns:
            True if call was routed successfully
        """
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
        
        # Create call
        call = self.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        
        # Allocate RTP relay
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
        
        self.logger.info(f"Routing call {call_id}: {from_ext} -> {to_ext}")
        
        # In a complete implementation:
        # 1. Forward INVITE to destination
        # 2. Handle ringing response
        # 3. Connect RTP streams when both parties answer
        
        return True
    
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
