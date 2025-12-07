"""
Core PBX implementation
Central coordinator for all PBX functionality
"""
import re
import struct
import threading
import traceback
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
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


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

        # Initialize database backend
        self.database = DatabaseBackend(self.config)
        self.registered_phones_db = None
        self.extension_db = None
        if self.database.connect():
            self.database.create_tables()
            from pbx.utils.database import ExtensionDB
            self.registered_phones_db = RegisteredPhonesDB(self.database)
            self.extension_db = ExtensionDB(self.database)
            self.logger.info(f"Database backend initialized successfully ({self.database.db_type})")
            self.logger.info("Extensions, voicemail metadata, and phone registrations will be stored in database")
        else:
            self.logger.warning("Database backend not available - running without database")
            self.logger.warning("Extensions will be loaded from config.yml only")
            self.logger.warning("Voicemails will be stored ONLY as files (no database metadata)")
            self.logger.warning("Phone registrations will not be persisted")

        # Initialize core components
        # Pass database to extension registry so it can load extensions from DB
        self.extension_registry = ExtensionRegistry(self.config, database=self.database if self.database.enabled else None)
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
        self.voicemail_system = VoicemailSystem(
            storage_path=voicemail_path,
            config=self.config,
            database=self.database if hasattr(self, 'database') and self.database.enabled else None
        )
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
        
        # Initialize auto attendant if enabled
        if self.config.get('features.auto_attendant', False):
            from pbx.features.auto_attendant import AutoAttendant
            self.auto_attendant = AutoAttendant(self.config, self)
            self.logger.info(f"Auto Attendant initialized on extension {self.auto_attendant.get_extension()}")
        else:
            self.auto_attendant = None

        # Initialize phone provisioning if enabled
        if self.config.get('provisioning.enabled', False):
            self.phone_provisioning = PhoneProvisioning(self.config)
            self._load_provisioning_devices()
        else:
            self.phone_provisioning = None

        # Initialize Active Directory integration
        if self.config.get('integrations.active_directory.enabled', False):
            from pbx.integrations.active_directory import ActiveDirectoryIntegration
            ad_config = {
                'integrations.active_directory.enabled': self.config.get('integrations.active_directory.enabled'),
                'integrations.active_directory.server': self.config.get('integrations.active_directory.server'),
                'integrations.active_directory.base_dn': self.config.get('integrations.active_directory.base_dn'),
                'integrations.active_directory.bind_dn': self.config.get('integrations.active_directory.bind_dn'),
                'integrations.active_directory.bind_password': self.config.get('integrations.active_directory.bind_password'),
                'integrations.active_directory.use_ssl': self.config.get('integrations.active_directory.use_ssl', True),
                'integrations.active_directory.auto_provision': self.config.get('integrations.active_directory.auto_provision', False),
                'integrations.active_directory.user_search_base': self.config.get('integrations.active_directory.user_search_base'),
                'integrations.active_directory.deactivate_removed_users': self.config.get('integrations.active_directory.deactivate_removed_users', True),
                'config_file': config_file
            }
            self.ad_integration = ActiveDirectoryIntegration(ad_config)
            if self.ad_integration.enabled:
                self.logger.info("Active Directory integration initialized")
            else:
                self.logger.warning("Active Directory integration enabled in config but failed to initialize")
                self.ad_integration = None
        else:
            self.ad_integration = None

        # Initialize phone book if enabled
        if self.config.get('features.phone_book.enabled', False):
            from pbx.features.phone_book import PhoneBook
            self.phone_book = PhoneBook(self.config, database=self.database if self.database.enabled else None)
            self.logger.info("Phone book feature initialized")
        else:
            self.phone_book = None

        # Initialize paging system if enabled
        if self.config.get('features.paging.enabled', False):
            from pbx.features.paging import PagingSystem
            self.paging_system = PagingSystem(self.config, database=self.database if self.database.enabled else None)
            self.logger.info("Paging system initialized")
        else:
            self.paging_system = None

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

    def register_extension(self, from_header, addr, user_agent=None, contact=None):
        """
        Register extension and store phone information

        Args:
            from_header: SIP From header
            addr: Network address (host, port)
            user_agent: User-Agent header from SIP REGISTER
            contact: Contact header from SIP REGISTER

        Returns:
            True if registration successful
        """
        # Parse extension number from header
        # Format: "Display Name" <sip:1001@host>
        match = re.search(r'sip:(\d+)@', from_header)
        if match:
            extension_number = match.group(1)

            # Verify extension exists - check database first, then config
            extension_exists = False
            
            # Check extensions database table first (if available)
            if self.extension_db:
                try:
                    db_extension = self.extension_db.get(extension_number)
                    if db_extension:
                        extension_exists = True
                        self.logger.debug(f"Extension {extension_number} found in database")
                        
                        # Ensure extension is loaded in registry (if not already)
                        if not self.extension_registry.get(extension_number):
                            # Create Extension object from database data using helper method
                            extension_obj = ExtensionRegistry.create_extension_from_db(db_extension)
                            self.extension_registry.extensions[extension_number] = extension_obj
                            self.logger.debug(f"Loaded extension {extension_number} into registry from database")
                except Exception as e:
                    self.logger.debug(f"Error checking extension in database: {e}")
            
            # Fall back to config if not found in database or database not available
            if not extension_exists:
                extension = self.config.get_extension(extension_number)
                if extension:
                    extension_exists = True
                    self.logger.debug(f"Extension {extension_number} found in config")
            
            if extension_exists:
                self.extension_registry.register(extension_number, addr)
                self.logger.info(f"Extension {extension_number} registered from {addr}")
                
                # Store phone registration in database
                if self.registered_phones_db:
                    ip_address = addr[0]  # Extract IP from (host, port) tuple
                    
                    # Try to extract MAC address from Contact URI or User-Agent
                    # Common patterns:
                    # - Contact: <sip:1001@192.168.1.100:5060;mac=00:11:22:33:44:55>
                    # - Contact: <sip:1001@192.168.1.100:5060>;+sip.instance="<urn:uuid:00112233-4455-6677-8899-aabbccddeeff>"
                    # - User-Agent: Yealink SIP-T46S 66.85.0.5 00:15:65:12:34:56
                    mac_address = self._extract_mac_address(contact, user_agent)
                    
                    try:
                        self.registered_phones_db.register_phone(
                            extension_number=extension_number,
                            ip_address=ip_address,
                            mac_address=mac_address,
                            user_agent=user_agent,
                            contact_uri=contact
                        )
                        if mac_address:
                            self.logger.info(f"Stored phone registration: ext={extension_number}, ip={ip_address}, mac={mac_address}")
                        else:
                            self.logger.info(f"Stored phone registration: ext={extension_number}, ip={ip_address} (no MAC)")
                    except Exception as e:
                        self.logger.error(f"Failed to store phone registration in database: {e}")
                        self.logger.error(f"  Extension: {extension_number}")
                        self.logger.error(f"  IP Address: {ip_address}")
                        self.logger.error(f"  MAC Address: {mac_address}")
                        self.logger.error(f"  User Agent: {user_agent}")
                        self.logger.error(f"  Contact URI: {contact}")
                        self.logger.error(f"  Traceback: {traceback.format_exc()}")
                
                return True
            else:
                self.logger.warning(f"Unknown extension {extension_number} attempted registration")
                return False

        self.logger.warning(f"Could not parse extension from {from_header}")
        return False

    def _extract_mac_address(self, contact, user_agent):
        """
        Extract MAC address from SIP headers
        
        Args:
            contact: Contact header
            user_agent: User-Agent header
            
        Returns:
            MAC address string or None
        """
        mac_address = None
        
        # Try to extract from Contact header
        if contact:
            # Pattern 1: mac=XX:XX:XX:XX:XX:XX or mac=XX-XX-XX-XX-XX-XX
            mac_match = re.search(r'mac=([0-9a-fA-F:]{17}|[0-9a-fA-F-]{17})', contact)
            if mac_match:
                mac_address = mac_match.group(1).lower()
            
            # Pattern 2: Instance ID that may contain MAC
            # <urn:uuid:00112233-4455-6677-8899-aabbccddeeff>
            instance_match = re.search(r'sip\.instance="<urn:uuid:([0-9a-f-]+)>"', contact, re.IGNORECASE)
            if not mac_address and instance_match:
                # Some devices use UUID derived from MAC
                uuid_str = instance_match.group(1).replace('-', '')
                # Last 12 chars might be MAC
                if len(uuid_str) >= 12:
                    potential_mac = uuid_str[-12:]
                    # Format as MAC: XX:XX:XX:XX:XX:XX
                    mac_address = ':'.join([potential_mac[i:i+2] for i in range(0, 12, 2)])
        
        # Try to extract from User-Agent
        if not mac_address and user_agent:
            # Pattern: User-Agent might end with MAC like "... 00:15:65:12:34:56"
            mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', user_agent)
            if mac_match:
                mac_address = mac_match.group(0).lower()
        
        # Normalize MAC address format (remove separators, lowercase)
        if mac_address:
            mac_address = mac_address.replace(':', '').replace('-', '').lower()
        
        return mac_address

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

        # Parse extension numbers - handle both regular extensions and special patterns
        from_match = re.search(r'sip:(\d+)@', from_header)
        # Allow * prefix for voicemail access (e.g., *1001), but validate format
        to_match = re.search(r'sip:(\*?\d+)@', to_header)

        if not from_match or not to_match:
            self.logger.warning(f"Could not parse extensions from headers")
            return False

        from_ext = from_match.group(1)
        to_ext = to_match.group(1)

        # Check if this is an auto attendant call (extension 0)
        if self.auto_attendant and to_ext == self.auto_attendant.get_extension():
            return self._handle_auto_attendant(from_ext, to_ext, call_id, message, from_addr)
        
        # Check if this is a voicemail access call (*xxxx pattern)
        # Validate format: must be * followed by exactly 3 or 4 digits
        if to_ext.startswith('*') and len(to_ext) >= 4 and len(to_ext) <= 5 and to_ext[1:].isdigit():
            return self._handle_voicemail_access(from_ext, to_ext, call_id, message, from_addr)
        
        # Check if this is a paging call (7xx pattern or all-call)
        if self.paging_system and self.paging_system.is_paging_extension(to_ext):
            return self._handle_paging(from_ext, to_ext, call_id, message, from_addr)

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

            # Store callee address for later use (e.g., to send CANCEL if routing to voicemail)
            call.callee_addr = dest_ext_obj.address
            call.callee_invite = invite_to_callee  # Store the INVITE for CANCEL reference

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
        if call and call.no_answer_timer:
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

            # If this is a voicemail recording, complete it first
            if call.routed_to_voicemail and hasattr(call, 'voicemail_recorder'):
                # Cancel the timer if it exists
                if hasattr(call, 'voicemail_timer') and call.voicemail_timer:
                    call.voicemail_timer.cancel()

                # Get the recorder
                recorder = call.voicemail_recorder
                if recorder and recorder.running:
                    # Stop recording
                    recorder.stop()

                    # Get recorded audio
                    audio_data = recorder.get_recorded_audio()
                    duration = recorder.get_duration()

                    if audio_data and len(audio_data) > 0:
                        # Build proper WAV file header for the recorded audio
                        wav_data = self._build_wav_file(audio_data)

                        # Save to voicemail system
                        self.voicemail_system.save_message(
                            extension_number=call.to_extension,
                            caller_id=call.from_extension,
                            audio_data=wav_data,
                            duration=duration
                        )
                        self.logger.info(f"Saved voicemail (on hangup) for extension {call.to_extension} from {call.from_extension}, duration: {duration}s")
                    else:
                        self.logger.warning(f"No audio recorded for voicemail on call {call_id}")

            self.call_manager.end_call(call_id)
            self.rtp_relay.release_relay(call_id)

    def transfer_call(self, call_id, new_destination):
        """
        Transfer call to new destination using SIP REFER

        Args:
            call_id: Call identifier
            new_destination: New destination extension

        Returns:
            True if transfer initiated
        """
        from pbx.sip.message import SIPMessageBuilder

        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.error(f"Call {call_id} not found for transfer")
            return False

        # Verify new destination exists
        if not self.extension_registry.is_registered(new_destination):
            self.logger.error(f"Transfer destination {new_destination} not registered")
            return False

        self.logger.info(f"Transferring call {call_id} from {call.from_extension} to {new_destination}")

        # Determine which party to send REFER to (typically the caller)
        refer_to_addr = call.caller_addr if call.caller_addr else call.callee_addr
        if not refer_to_addr:
            self.logger.error(f"No address found for REFER in call {call_id}")
            return False

        # Build REFER message
        server_ip = self._get_server_ip()
        sip_port = self.config.get('server.sip_port', 5060)

        refer_msg = SIPMessageBuilder.build_request(
            method='REFER',
            uri=f"sip:{call.from_extension}@{server_ip}",
            from_addr=f"<sip:{call.to_extension}@{server_ip}>",
            to_addr=f"<sip:{call.from_extension}@{server_ip}>",
            call_id=call_id,
            cseq=1
        )

        # Add Refer-To header with new destination
        refer_msg.set_header('Refer-To', f"<sip:{new_destination}@{server_ip}>")

        # Add Referred-By header
        refer_msg.set_header('Referred-By', f"<sip:{call.to_extension}@{server_ip}>")

        # Add Contact header
        refer_msg.set_header('Contact', f"<sip:{call.to_extension}@{server_ip}:{sip_port}>")

        # Send REFER message
        self.sip_server._send_message(refer_msg.build(), refer_to_addr)
        self.logger.info(f"Sent REFER to {refer_to_addr} for call {call_id} to transfer to {new_destination}")

        # Mark call as transferred
        call.transferred = True
        call.transfer_destination = new_destination

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
        from pbx.sip.sdp import SDPBuilder
        from pbx.rtp.handler import RTPRecorder, RTPPlayer

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

        # Send CANCEL to the callee to stop their phone from ringing
        if hasattr(call, 'callee_addr') and call.callee_addr and hasattr(call, 'callee_invite') and call.callee_invite:
            cancel_request = SIPMessageBuilder.build_request(
                method='CANCEL',
                uri=call.callee_invite.uri,
                from_addr=call.callee_invite.get_header('From'),
                to_addr=call.callee_invite.get_header('To'),
                call_id=call_id,
                cseq=int(call.callee_invite.get_header('CSeq').split()[0])
            )
            cancel_request.set_header('Via', call.callee_invite.get_header('Via'))

            self.sip_server._send_message(cancel_request.build(), call.callee_addr)
            self.logger.info(f"Sent CANCEL to callee {call.to_extension} to stop ringing")

        # Answer the call to allow voicemail recording
        if call.original_invite and call.caller_addr and call.caller_rtp and call.rtp_ports:
            server_ip = self._get_server_ip()

            # Build SDP for the voicemail recording endpoint
            voicemail_sdp = SDPBuilder.build_audio_sdp(
                server_ip,
                call.rtp_ports[0],
                session_id=call_id
            )

            # Send 200 OK to answer the call for voicemail recording
            ok_response = SIPMessageBuilder.build_response(
                200,
                "OK",
                call.original_invite,
                body=voicemail_sdp
            )
            ok_response.set_header('Content-Type', 'application/sdp')

            # Build Contact header
            sip_port = self.config.get('server.sip_port', 5060)
            contact_uri = f"<sip:{call.to_extension}@{server_ip}:{sip_port}>"
            ok_response.set_header('Contact', contact_uri)

            # Send to caller
            self.sip_server._send_message(ok_response.build(), call.caller_addr)
            self.logger.info(f"Answered call {call_id} for voicemail recording")

            # Mark call as connected
            call.connect()

            # Play voicemail greeting and beep tone to caller
            if call.caller_rtp:
                try:
                    from pbx.utils.audio import get_prompt_audio
                    import tempfile
                    import os
                    
                    # Create RTP player to send audio to caller
                    # Note: Using adjacent port (rtp_port + 1) for sending audio back to caller
                    # In production, consider implementing proper port allocation to avoid conflicts
                    player = RTPPlayer(
                        local_port=call.rtp_ports[0] + 1,  # Adjacent port for sending
                        remote_host=call.caller_rtp['address'],
                        remote_port=call.caller_rtp['port'],
                        call_id=call_id
                    )
                    if player.start():
                        # Check for custom greeting first
                        mailbox = self.voicemail_system.get_mailbox(call.to_extension)
                        custom_greeting_path = mailbox.get_greeting_path()
                        greeting_file = None
                        temp_file_created = False
                        
                        if custom_greeting_path:
                            # Use custom greeting
                            greeting_file = custom_greeting_path
                            self.logger.info(f"Using custom greeting for extension {call.to_extension}")
                        else:
                            # Use default prompt: "Please leave a message after the tone"
                            # Try to load from voicemail_prompts/leave_message.wav, fallback to tone generation
                            greeting_prompt = get_prompt_audio('leave_message')
                            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                                temp_file.write(greeting_prompt)
                                greeting_file = temp_file.name
                                temp_file_created = True
                            self.logger.info(f"Using default greeting for extension {call.to_extension}")
                        
                        try:
                            player.play_file(greeting_file)
                            import time
                            time.sleep(0.3)  # Brief pause before beep
                        finally:
                            # Clean up temp file only if we created one
                            if temp_file_created:
                                try:
                                    os.unlink(greeting_file)
                                except (OSError, FileNotFoundError) as e:
                                    self.logger.debug(f"Could not delete temp greeting file: {e}")
                        
                        # Play beep tone (1000 Hz, 500ms)
                        player.play_beep(frequency=1000, duration_ms=500)
                        player.stop()
                        self.logger.info(f"Played voicemail greeting and beep for call {call_id}")
                    else:
                        self.logger.warning(f"Failed to start RTP player for greeting on call {call_id}")
                except Exception as e:
                    self.logger.error(f"Error playing voicemail greeting: {e}")

            # Start RTP recorder on the allocated port
            recorder = RTPRecorder(call.rtp_ports[0], call_id)
            if recorder.start():
                # Store recorder in call object for later retrieval
                call.voicemail_recorder = recorder

                # Set recording timeout (max voicemail duration)
                max_duration = self.config.get('voicemail.max_message_duration', 180)

                # Schedule voicemail completion after max duration
                voicemail_timer = threading.Timer(
                    max_duration,
                    self._complete_voicemail_recording,
                    args=(call_id,)
                )
                voicemail_timer.start()
                call.voicemail_timer = voicemail_timer

                self.logger.info(f"Started voicemail recording for call {call_id}, max duration: {max_duration}s")
            else:
                self.logger.error(f"Failed to start voicemail recorder for call {call_id}")
                self.end_call(call_id)
        else:
            self.logger.error(f"Cannot route call {call_id} to voicemail - missing required information")
            # Fallback to ending the call
            self.end_call(call_id)

    def _complete_voicemail_recording(self, call_id):
        """
        Complete voicemail recording and save the message

        Args:
            call_id: Call identifier
        """
        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.warning(f"Cannot complete voicemail for non-existent call {call_id}")
            return

        # Get the recorder if it exists
        recorder = getattr(call, 'voicemail_recorder', None)
        if recorder:
            # Stop recording
            recorder.stop()

            # Get recorded audio
            audio_data = recorder.get_recorded_audio()
            duration = recorder.get_duration()

            if audio_data and len(audio_data) > 0:
                # Build proper WAV file header for the recorded audio
                wav_data = self._build_wav_file(audio_data)

                # Save to voicemail system
                self.voicemail_system.save_message(
                    extension_number=call.to_extension,
                    caller_id=call.from_extension,
                    audio_data=wav_data,
                    duration=duration
                )
                self.logger.info(f"Saved voicemail for extension {call.to_extension} from {call.from_extension}, duration: {duration}s")
            else:
                self.logger.warning(f"No audio recorded for voicemail on call {call_id}")
                # Still create a minimal voicemail to indicate the attempt
                placeholder_audio = self._build_wav_file(b'')
                self.voicemail_system.save_message(
                    extension_number=call.to_extension,
                    caller_id=call.from_extension,
                    audio_data=placeholder_audio,
                    duration=0
                )

        # End the call
        self.end_call(call_id)

    def _handle_auto_attendant(self, from_ext, to_ext, call_id, message, from_addr):
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
        from pbx.sip.sdp import SDPSession, SDPBuilder
        from pbx.sip.message import SIPMessageBuilder
        from pbx.rtp.handler import RTPPlayer
        
        self.logger.info(f"Auto attendant call: {from_ext} -> {to_ext}")
        
        # Parse SDP from caller's INVITE
        caller_sdp = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()
        
        # Create call for auto attendant
        call = self.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.auto_attendant_active = True
        
        # Allocate RTP ports
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
        else:
            self.logger.error(f"Failed to allocate RTP ports for auto attendant {call_id}")
            return False
        
        # Answer the call
        server_ip = self._get_server_ip()
        
        # Build SDP for answering
        aa_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id
        )
        
        # Send 200 OK to answer the call
        ok_response = SIPMessageBuilder.build_response(
            200,
            "OK",
            call.original_invite,
            body=aa_sdp
        )
        ok_response.set_header('Content-Type', 'application/sdp')
        
        # Build Contact header
        sip_port = self.config.get('server.sip_port', 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header('Contact', contact_uri)
        
        # Send to caller
        self.sip_server._send_message(ok_response.build(), call.caller_addr)
        self.logger.info(f"Answered auto attendant call {call_id}")
        
        # Mark call as connected
        call.connect()
        
        # Start auto attendant session
        session = self.auto_attendant.start_session(call_id, from_ext)
        call.aa_session = session
        
        # Start auto attendant interaction thread
        aa_thread = threading.Thread(
            target=self._auto_attendant_session,
            args=(call_id, call, session)
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
        from pbx.rtp.handler import RTPPlayer, RTPDTMFListener
        from pbx.utils.audio import get_prompt_audio
        import time
        import tempfile
        import os
        
        try:
            # Wait for RTP to stabilize
            time.sleep(0.5)
            
            if not call.caller_rtp:
                self.logger.warning(f"No caller RTP info for auto attendant {call_id}")
                return
            
            # Create RTP player for audio prompts
            player = RTPPlayer(
                local_port=call.rtp_ports[0] + 1,
                remote_host=call.caller_rtp['address'],
                remote_port=call.caller_rtp['port'],
                call_id=call_id
            )
            
            if not player.start():
                self.logger.error(f"Failed to start RTP player for auto attendant {call_id}")
                return
            
            # Create DTMF listener
            dtmf_listener = RTPDTMFListener(call.rtp_ports[0])
            if not dtmf_listener.start():
                self.logger.error(f"Failed to start DTMF listener for auto attendant {call_id}")
                player.stop()
                return
            
            # Play welcome greeting
            action = session.get('session')
            audio_file = session.get('file')
            
            if audio_file and os.path.exists(audio_file):
                player.play_file(audio_file)
            else:
                # Try to load from auto_attendant/welcome.wav, fallback to tone generation
                prompt_data = get_prompt_audio('welcome', prompt_dir='auto_attendant')
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(prompt_data)
                    temp_file_path = temp_file.name
                try:
                    player.play_file(temp_file_path)
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
            
            time.sleep(0.5)
            
            # Play main menu
            menu_audio = self.auto_attendant._get_audio_file('main_menu')
            if menu_audio and os.path.exists(menu_audio):
                player.play_file(menu_audio)
            else:
                # Try to load from auto_attendant/main_menu.wav, fallback to tone generation
                prompt_data = get_prompt_audio('main_menu', prompt_dir='auto_attendant')
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(prompt_data)
                    temp_file_path = temp_file.name
                try:
                    player.play_file(temp_file_path)
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
            
            # Main loop - wait for DTMF input
            session_active = True
            timeout = self.auto_attendant.timeout
            start_time = time.time()
            
            while session_active and (time.time() - start_time) < timeout:
                # Check for DTMF input
                digit = dtmf_listener.get_digit(timeout=1.0)
                
                if digit:
                    self.logger.info(f"Auto attendant received DTMF: {digit}")
                    
                    # Handle the input
                    result = self.auto_attendant.handle_dtmf(session['session'], digit)
                    action = result.get('action')
                    
                    if action == 'transfer':
                        destination = result.get('destination')
                        self.logger.info(f"Auto attendant transferring to {destination}")
                        
                        # Play transfer message
                        transfer_audio = self.auto_attendant._get_audio_file('transferring')
                        if transfer_audio and os.path.exists(transfer_audio):
                            player.play_file(transfer_audio)
                        else:
                            # Try to load from auto_attendant/transferring.wav, fallback to tone generation
                            prompt_data = get_prompt_audio('transferring', prompt_dir='auto_attendant')
                            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                                temp_file.write(prompt_data)
                                temp_file_path = temp_file.name
                            try:
                                player.play_file(temp_file_path)
                            finally:
                                try:
                                    os.unlink(temp_file_path)
                                except:
                                    pass
                        
                        time.sleep(0.5)
                        
                        # Transfer the call using existing transfer_call method
                        if call_id:
                            success = self.transfer_call(call_id, destination)
                            if not success:
                                self.logger.warning(f"Failed to transfer call {call_id} to {destination}")
                        else:
                            self.logger.warning("Cannot transfer call: no call_id available")
                        session_active = False
                        
                    elif action == 'play':
                        # Play the requested audio
                        audio_file = result.get('file')
                        if audio_file and os.path.exists(audio_file):
                            player.play_file(audio_file)
                        
                        # Reset timeout
                        start_time = time.time()
                    
                    # Update session
                    if 'session' in result:
                        session['session'] = result['session']
            
            # Timeout - handle it
            if time.time() - start_time >= timeout:
                result = self.auto_attendant.handle_timeout(session['session'])
                action = result.get('action')
                
                if action == 'transfer':
                    destination = result.get('destination')
                    self.logger.info(f"Auto attendant timeout, transferring to {destination}")
                    if call_id:
                        success = self.transfer_call(call_id, destination)
                        if not success:
                            self.logger.warning(f"Failed to transfer call {call_id} to {destination} on timeout")
            
            # Clean up
            player.stop()
            dtmf_listener.stop()
            
        except Exception as e:
            self.logger.error(f"Error in auto attendant session: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            # End the call
            time.sleep(1)
            self.end_call(call_id)

    def _handle_voicemail_access(self, from_ext, to_ext, call_id, message, from_addr):
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
        from pbx.sip.sdp import SDPSession, SDPBuilder
        from pbx.sip.message import SIPMessageBuilder

        # Extract the target extension from *xxxx pattern
        target_ext = to_ext[1:]  # Remove the * prefix

        self.logger.info(f"Voicemail access: {from_ext} -> {target_ext}")

        # Verify the target extension exists
        if not self.config.get_extension(target_ext):
            self.logger.warning(f"Voicemail access to non-existent extension {target_ext}")
            return False

        # Get the voicemail box
        mailbox = self.voicemail_system.get_mailbox(target_ext)

        # Parse SDP from caller's INVITE
        caller_sdp = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

        # Create call for voicemail access
        call = self.call_manager.create_call(call_id, from_ext, f"*{target_ext}")
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.voicemail_access = True
        call.voicemail_extension = target_ext

        # Allocate RTP ports
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
        else:
            self.logger.error(f"Failed to allocate RTP ports for voicemail access {call_id}")
            return False

        # Answer the call
        server_ip = self._get_server_ip()

        # Build SDP for answering
        voicemail_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id
        )

        # Send 200 OK to answer the call
        ok_response = SIPMessageBuilder.build_response(
            200,
            "OK",
            call.original_invite,
            body=voicemail_sdp
        )
        ok_response.set_header('Content-Type', 'application/sdp')

        # Build Contact header
        sip_port = self.config.get('server.sip_port', 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header('Contact', contact_uri)

        # Send to caller
        self.sip_server._send_message(ok_response.build(), call.caller_addr)
        self.logger.info(f"Answered voicemail access call {call_id}")

        # Mark call as connected
        call.connect()

        # Create VoicemailIVR for this call
        from pbx.features.voicemail import VoicemailIVR
        voicemail_ivr = VoicemailIVR(self.voicemail_system, target_ext)
        call.voicemail_ivr = voicemail_ivr

        # Get message count
        messages = mailbox.get_messages(unread_only=False)
        unread = mailbox.get_messages(unread_only=True)

        self.logger.info(f"Voicemail access for {target_ext}: {len(unread)} unread, {len(messages)} total")

        # Start IVR-based voicemail management
        # This runs in a separate thread so it doesn't block
        playback_thread = threading.Thread(
            target=self._voicemail_ivr_session,
            args=(call_id, call, mailbox, voicemail_ivr)
        )
        playback_thread.daemon = True
        playback_thread.start()

        return True

    def _handle_paging(self, from_ext, to_ext, call_id, message, from_addr):
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
        from pbx.sip.sdp import SDPSession, SDPBuilder
        from pbx.sip.message import SIPMessageBuilder
        
        self.logger.info(f"Paging call: {from_ext} -> {to_ext}")
        
        # Initiate the page through the paging system
        page_id = self.paging_system.initiate_page(from_ext, to_ext)
        if not page_id:
            self.logger.error(f"Failed to initiate page from {from_ext} to {to_ext}")
            return False
        
        # Get zone information
        page_info = self.paging_system.get_page_info(page_id)
        if not page_info:
            self.logger.error(f"Failed to get page info for {page_id}")
            return False
        
        # Parse SDP from caller's INVITE
        caller_sdp = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()
            
            if caller_sdp:
                self.logger.info(f"Paging caller RTP: {caller_sdp['address']}:{caller_sdp['port']}")
        
        # Create call for paging
        call = self.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.paging_active = True
        call.page_id = page_id
        call.paging_zones = page_info.get('zone_names', 'Unknown')
        
        # Allocate RTP ports
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
        else:
            self.logger.error(f"Failed to allocate RTP ports for paging {call_id}")
            self.paging_system.end_page(page_id)
            return False
        
        # Get configured paging gateway device
        zones = page_info.get('zones', [])
        if not zones:
            self.logger.error(f"No zones configured for paging extension {to_ext}")
            self.paging_system.end_page(page_id)
            return False
        
        # For now, use the first zone's DAC device
        zone = zones[0]
        dac_device_id = zone.get('dac_device')
        
        if not dac_device_id:
            self.logger.warning(f"No DAC device configured for zone {zone.get('name')}")
            # Continue anyway - this allows testing without hardware
        
        # Find the DAC device configuration
        dac_device = None
        for device in self.paging_system.get_dac_devices():
            if device.get('device_id') == dac_device_id:
                dac_device = device
                break
        
        # Answer the call immediately (auto-answer for paging)
        server_ip = self._get_server_ip()
        
        # Build SDP for answering
        paging_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id
        )
        
        # Send 200 OK to answer the call
        ok_response = SIPMessageBuilder.build_response(
            200,
            "OK",
            call.original_invite,
            body=paging_sdp
        )
        ok_response.set_header('Content-Type', 'application/sdp')
        
        # Build Contact header
        sip_port = self.config.get('server.sip_port', 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header('Contact', contact_uri)
        
        # Send to caller
        self.sip_server._send_message(ok_response.build(), call.caller_addr)
        self.logger.info(f"Answered paging call {call_id} - Paging {page_info.get('zone_names')}")
        
        # Mark call as connected
        call.connect()
        
        # If we have a DAC device configured, route audio to it
        if dac_device:
            # Start paging session thread to handle audio routing
            paging_thread = threading.Thread(
                target=self._paging_session,
                args=(call_id, call, dac_device, page_info)
            )
            paging_thread.daemon = True
            paging_thread.start()
        else:
            # No hardware - just maintain the call for testing
            self.logger.warning(f"Paging call {call_id} connected but no DAC device available")
            self.logger.info(f"Audio from {from_ext} would be routed to {page_info.get('zone_names')}")
        
        return True
    
    def _paging_session(self, call_id, call, dac_device, page_info):
        """
        Handle paging session with audio routing to DAC device
        
        Args:
            call_id: Call identifier
            call: Call object
            dac_device: DAC device configuration
            page_info: Paging information dictionary
        """
        import time
        
        try:
            self.logger.info(f"Paging session started for {call_id}")
            self.logger.info(f"DAC device: {dac_device.get('device_id')} ({dac_device.get('device_type')})")
            self.logger.info(f"Paging zones: {page_info.get('zone_names')}")
            
            # Get DAC device SIP information
            dac_sip_uri = dac_device.get('sip_uri')
            dac_ip = dac_device.get('ip_address')
            dac_port = dac_device.get('port', 5060)
            
            if not dac_sip_uri or not dac_ip:
                self.logger.error(f"DAC device {dac_device.get('device_id')} missing SIP configuration")
                return
            
            # In a full implementation, we would:
            # 1. Establish SIP connection to the DAC gateway device
            # 2. Set up RTP relay to forward audio from caller to DAC
            # 3. Handle zone selection (if multi-zone gateway)
            # 4. Monitor the call and end when caller hangs up
            
            # For now, log the routing information
            self.logger.info(f"Would route RTP audio to {dac_ip}:{dac_port}")
            
            if call.caller_rtp:
                self.logger.info(f"Caller RTP: {call.caller_rtp['address']}:{call.caller_rtp['port']}")
                self.logger.info(f"Audio relay: Caller -> PBX:{call.rtp_ports[0]} -> DAC:{dac_ip}")
            
            # TODO: Implement actual SIP INVITE to DAC device
            # TODO: Implement RTP relay from caller to DAC
            # This requires:
            # - SIP message to DAC device with auto-answer indication
            # - RTP forwarding from caller's stream to DAC device
            # - Handling of zone selection via DTMF or dedicated ports
            
            # Monitor the call until it ends
            while call.state.value != 'ended':
                time.sleep(1)
            
            self.logger.info(f"Paging session ended for {call_id}")
            
            # End the page
            self.paging_system.end_page(call.page_id)
            
        except Exception as e:
            self.logger.error(f"Error in paging session {call_id}: {e}")
            import traceback
            traceback.print_exc()

    def _playback_voicemails(self, call_id, call, mailbox, messages):
        """
        Play voicemail messages to caller

        Args:
            call_id: Call identifier
            call: Call object
            mailbox: VoicemailBox object
            messages: List of message dictionaries
        """
        import time
        from pbx.rtp.handler import RTPPlayer

        try:
            # Wait a moment for RTP to stabilize
            time.sleep(0.5)

            # Create RTP player to send audio to caller
            if not call.caller_rtp:
                self.logger.warning(f"No caller RTP info for voicemail playback {call_id}")
                # End call after short delay
                time.sleep(2)
                self.end_call(call_id)
                return

            player = RTPPlayer(
                local_port=call.rtp_ports[0] + 1,
                remote_host=call.caller_rtp['address'],
                remote_port=call.caller_rtp['port'],
                call_id=call_id
            )

            if not player.start():
                self.logger.error(f"Failed to start RTP player for voicemail playback {call_id}")
                time.sleep(2)
                self.end_call(call_id)
                return

            try:
                # Play each voicemail message
                if not messages:
                    # No messages - play short beep and hang up
                    self.logger.info(f"No voicemail messages for {call.voicemail_extension}")
                    player.play_beep(frequency=400, duration_ms=500)
                    time.sleep(2)
                else:
                    # Play messages
                    self.logger.info(f"Playing {len(messages)} voicemail messages for {call.voicemail_extension}")

                    for idx, message in enumerate(messages):
                        # Play a beep between messages
                        if idx > 0:
                            time.sleep(0.5)
                            player.play_beep(frequency=800, duration_ms=300)
                            time.sleep(0.5)

                        # Play the voicemail message
                        file_path = message['file_path']
                        self.logger.info(f"Playing voicemail {idx + 1}/{len(messages)}: {file_path}")

                        if player.play_file(file_path):
                            # Mark message as listened
                            mailbox.mark_listened(message['id'])
                            self.logger.info(f"Marked voicemail {message['id']} as listened")
                        else:
                            self.logger.warning(f"Failed to play voicemail: {file_path}")

                        # Pause between messages
                        time.sleep(1)

                    self.logger.info(f"Finished playing all voicemails for {call.voicemail_extension}")
                    time.sleep(1)

            finally:
                player.stop()

            # End the call after playback
            self.end_call(call_id)

        except Exception as e:
            self.logger.error(f"Error in voicemail playback: {e}")
            import traceback
            traceback.print_exc()
            # Ensure call is ended even if there's an error
            try:
                self.end_call(call_id)
            except Exception as e:
                self.logger.error(f"Error ending call during cleanup: {e}")

    def _voicemail_ivr_session(self, call_id, call, mailbox, voicemail_ivr):
        """
        Interactive voicemail management session with IVR menu
        
        Args:
            call_id: Call identifier
            call: Call object
            mailbox: VoicemailBox object
            voicemail_ivr: VoicemailIVR object
        """
        import time
        from pbx.rtp.handler import RTPPlayer, RTPRecorder
        from pbx.utils.audio import get_prompt_audio
        from pbx.utils.dtmf import DTMFDetector
        import tempfile
        import os
        
        try:
            # Wait a moment for RTP to stabilize
            time.sleep(0.5)
            
            if not call.caller_rtp:
                self.logger.warning(f"No caller RTP info for voicemail IVR {call_id}")
                time.sleep(2)
                self.end_call(call_id)
                return
            
            # Create RTP player for sending audio prompts
            player = RTPPlayer(
                local_port=call.rtp_ports[0] + 1,
                remote_host=call.caller_rtp['address'],
                remote_port=call.caller_rtp['port'],
                call_id=call_id
            )
            
            if not player.start():
                self.logger.error(f"Failed to start RTP player for voicemail IVR {call_id}")
                time.sleep(2)
                self.end_call(call_id)
                return
            
            # Create DTMF detector for receiving menu selections
            dtmf_detector = DTMFDetector(sample_rate=8000)
            
            # Create RTP receiver for DTMF detection
            recorder = RTPRecorder(call.rtp_ports[0], call_id)
            if not recorder.start():
                self.logger.error(f"Failed to start RTP receiver for DTMF {call_id}")
                player.stop()
                time.sleep(2)
                self.end_call(call_id)
                return
            
            try:
                # Start the IVR flow - transition from WELCOME to PIN_ENTRY state
                # Use '*' which won't be collected as part of PIN (only 0-9 are collected)
                initial_action = voicemail_ivr.handle_dtmf('*')
                
                # Play the PIN entry prompt that the IVR returned
                if not isinstance(initial_action, dict):
                    self.logger.error(f"IVR handle_dtmf expected to return dict but got: {type(initial_action)}")
                    initial_action = {'action': 'play_prompt', 'prompt': 'enter_pin'}
                
                prompt_type = initial_action.get('prompt', 'enter_pin')
                # Try to load from voicemail_prompts/ directory, fallback to tone generation
                pin_prompt = get_prompt_audio(prompt_type)
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(pin_prompt)
                    prompt_file = temp_file.name
                
                try:
                    player.play_file(prompt_file)
                finally:
                    try:
                        os.unlink(prompt_file)
                    except Exception:
                        pass
                
                time.sleep(0.5)
                
                self.logger.info(f"Voicemail IVR started for {call.voicemail_extension}, waiting for PIN")
                
                # Main IVR loop - listen for DTMF input
                ivr_active = True
                last_audio_check = time.time()
                audio_buffer = []
                
                # Constants for DTMF detection
                # ~0.5s of audio at 160 bytes per 20ms RTP packet
                DTMF_DETECTION_PACKETS = 40  # 40 packets * 20ms = 0.8s of audio
                MIN_AUDIO_BYTES_FOR_DTMF = 1600  # Minimum audio data needed for reliable DTMF detection
                
                while ivr_active:
                    # Check if call is still active
                    if call.state.value == 'ended':
                        break
                    
                    # Collect audio for DTMF detection
                    time.sleep(0.1)
                    
                    # Check for recorded audio (DTMF tones from user)
                    if hasattr(recorder, 'recorded_data') and recorder.recorded_data:
                        # Get recent audio data
                        if len(recorder.recorded_data) > 0:
                            # Collect last portion of audio for DTMF detection
                            recent_audio = b''.join(recorder.recorded_data[-DTMF_DETECTION_PACKETS:])
                            
                            if len(recent_audio) > MIN_AUDIO_BYTES_FOR_DTMF:  # Need sufficient audio for DTMF
                                # Detect DTMF in audio
                                digit = dtmf_detector.detect(recent_audio)
                                
                                if digit:
                                    self.logger.info(f"Detected DTMF digit: {digit} in voicemail IVR")
                                    
                                    # Handle DTMF input through IVR
                                    action = voicemail_ivr.handle_dtmf(digit)
                                    
                                    # Process IVR action
                                    if action['action'] == 'play_message':
                                        # Play the voicemail message
                                        file_path = action.get('file_path')
                                        if file_path and os.path.exists(file_path):
                                            player.play_file(file_path)
                                            mailbox.mark_listened(action['message_id'])
                                            self.logger.info(f"Played voicemail {action['message_id']}")
                                        time.sleep(0.5)
                                    
                                    elif action['action'] == 'play_prompt':
                                        # Play a prompt
                                        prompt_type = action.get('prompt', 'main_menu')
                                        # Try to load from voicemail_prompts/ directory, fallback to tone generation
                                        prompt_audio = get_prompt_audio(prompt_type)
                                        
                                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                                            temp_file.write(prompt_audio)
                                            prompt_file = temp_file.name
                                        
                                        try:
                                            player.play_file(prompt_file)
                                        finally:
                                            try:
                                                os.unlink(prompt_file)
                                            except OSError:
                                                pass  # File already deleted or doesn't exist
                                        
                                        time.sleep(0.3)
                                    
                                    elif action['action'] == 'hangup':
                                        # Play goodbye and end call
                                        # Try to load from voicemail_prompts/ directory, fallback to tone generation
                                        goodbye_prompt = get_prompt_audio('goodbye')
                                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                                            temp_file.write(goodbye_prompt)
                                            prompt_file = temp_file.name
                                        
                                        try:
                                            player.play_file(prompt_file)
                                        finally:
                                            try:
                                                os.unlink(prompt_file)
                                            except OSError:
                                                pass  # File already deleted or doesn't exist
                                        
                                        time.sleep(1)
                                        ivr_active = False
                                    
                                    # Clear audio buffer after processing DTMF
                                    # Note: Directly modifying internal state - consider adding clear() method to RTPRecorder
                                    if hasattr(recorder, 'recorded_data'):
                                        recorder.recorded_data = []
                    
                    # Timeout after 60 seconds of no activity
                    if time.time() - last_audio_check > 60:
                        self.logger.info(f"Voicemail IVR timeout for {call.voicemail_extension}")
                        ivr_active = False
                
                self.logger.info(f"Voicemail IVR session ended for {call.voicemail_extension}")
            
            finally:
                player.stop()
                recorder.stop()
            
            # End the call
            self.end_call(call_id)
        
        except Exception as e:
            self.logger.error(f"Error in voicemail IVR session: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.end_call(call_id)
            except Exception as e:
                self.logger.error(f"Error ending call during cleanup: {e}")

    def _build_wav_file(self, audio_data):
        """
        Build a proper WAV file from raw audio data
        Assumes G.711 μ-law (PCMU) codec at 8kHz

        Args:
            audio_data: Raw audio payload data

        Returns:
            bytes: Complete WAV file
        """
        # WAV file format for G.711 μ-law
        sample_rate = 8000
        bits_per_sample = 8
        num_channels = 1
        audio_format = 7  # μ-law

        # Calculate sizes
        # RIFF header: 12 bytes (RIFF + size + WAVE)
        # fmt chunk: 26 bytes (chunk header + fmt data + extension)
        # data chunk header: 8 bytes (data + size)
        # Total header size: 46 bytes
        data_size = len(audio_data)
        # File size for RIFF header is total size minus 8 bytes (RIFF + size field itself)
        file_size = 4 + 26 + 8 + data_size  # WAVE + fmt chunk + data chunk header + data

        # Build WAV header (12 bytes)
        wav_header = struct.pack('<4sI4s',
            b'RIFF',
            file_size,
            b'WAVE'
        )

        # Format chunk (24 bytes + 2 bytes extension = 26 bytes)
        fmt_chunk = struct.pack('<4sIHHIIHH',
            b'fmt ',
            18,  # Chunk size (18 for non-PCM formats like μ-law)
            audio_format,
            num_channels,
            sample_rate,
            sample_rate * num_channels * bits_per_sample // 8,  # Byte rate
            num_channels * bits_per_sample // 8,  # Block align
            bits_per_sample
        )

        # Add extension size (2 bytes, value 0 for G.711)
        fmt_extension = struct.pack('<H', 0)

        # Data chunk header (8 bytes)
        data_chunk = struct.pack('<4sI',
            b'data',
            data_size
        )

        # Combine all parts
        return wav_header + fmt_chunk + fmt_extension + data_chunk + audio_data

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

    def get_ad_integration_status(self):
        """
        Get Active Directory integration status

        Returns:
            Dictionary with AD integration status
        """
        if not self.ad_integration:
            return {
                'enabled': False,
                'connected': False,
                'auto_provision': False,
                'server': None,
                'last_sync': None,
                'synced_users': 0,
                'error': None
            }

        # Try to connect to check status
        connected = False
        error = None
        try:
            connected = self.ad_integration.connect()
        except Exception as e:
            error = str(e)

        # Get count of AD-synced extensions
        synced_count = 0
        if self.extension_db:
            try:
                synced_extensions = self.extension_db.get_ad_synced()
                synced_count = len(synced_extensions)
            except Exception as e:
                self.logger.error(f"Error getting AD-synced extension count: {e}")

        return {
            'enabled': self.ad_integration.enabled,
            'connected': connected,
            'auto_provision': self.ad_integration.auto_provision,
            'server': self.ad_integration.ldap_server,
            'synced_users': synced_count,
            'error': error
        }

    def sync_ad_users(self):
        """
        Manually trigger Active Directory user synchronization

        Returns:
            dict: Sync results with count and status
        """
        if not self.ad_integration:
            return {
                'success': False,
                'error': 'Active Directory integration is not enabled',
                'synced_count': 0
            }

        if not self.ad_integration.enabled:
            return {
                'success': False,
                'error': 'Active Directory integration is disabled',
                'synced_count': 0
            }

        try:
            self.logger.info("Manual AD user sync triggered")
            sync_result = self.ad_integration.sync_users(
                extension_registry=self.extension_registry,
                extension_db=self.extension_db,
                phone_provisioning=self.phone_provisioning if hasattr(self, 'phone_provisioning') else None
            )
            
            # Handle both old (int) and new (dict) return types for backward compatibility
            if isinstance(sync_result, int):
                synced_count = sync_result
                extensions_to_reboot = []
            else:
                synced_count = sync_result.get('synced_count', 0)
                extensions_to_reboot = sync_result.get('extensions_to_reboot', [])
            
            # Reload extensions after sync
            self.extension_registry.reload()
            
            # Automatically trigger phone reboots for updated extensions
            rebooted_count = 0
            if extensions_to_reboot and hasattr(self, 'phone_provisioning') and self.phone_provisioning:
                self.logger.info(f"Auto-provisioning: Automatically rebooting {len(extensions_to_reboot)} phones after AD sync")
                for extension_number in extensions_to_reboot:
                    try:
                        if self.phone_provisioning.reboot_phone(extension_number, self.sip_server):
                            rebooted_count += 1
                    except Exception as reboot_error:
                        self.logger.warning(f"Could not reboot phone for extension {extension_number}: {reboot_error}")
                
                if rebooted_count > 0:
                    self.logger.info(f"Auto-provisioning: Successfully triggered reboot for {rebooted_count} phones")
            
            return {
                'success': True,
                'synced_count': synced_count,
                'rebooted_count': rebooted_count,
                'error': None
            }
        except Exception as e:
            self.logger.error(f"Error during AD sync: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'synced_count': 0,
                'rebooted_count': 0
            }
