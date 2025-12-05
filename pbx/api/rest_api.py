"""
REST API Server for PBX Management
Provides HTTP API for managing PBX features
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime, date
import socket
import threading
import os
import mimetypes
import traceback
from urllib.parse import urlparse, parse_qs
from pbx.utils.logger import get_logger
from pbx.utils.config import Config

# Admin directory path
ADMIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'admin')


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class PBXAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for PBX API"""

    pbx_core = None  # Set by PBXAPIServer

    def _set_headers(self, status=200, content_type='application/json'):
        """Set response headers"""
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _send_json(self, data, status=200):
        """Send JSON response"""
        self._set_headers(status)
        self.wfile.write(json.dumps(data, cls=DateTimeEncoder).encode())

    def _get_body(self):
        """Get request body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        return {}

    def do_OPTIONS(self):
        """Handle OPTIONS for CORS"""
        self._set_headers(204)

    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == '/api/provisioning/devices':
                self._handle_register_device()
            elif path == '/api/extensions':
                self._handle_add_extension()
            elif path == '/api/phones/reboot':
                self._handle_reboot_phones()
            elif path.startswith('/api/phones/') and path.endswith('/reboot'):
                # Extract extension number: /api/phones/{extension}/reboot
                parts = path.split('/')
                if len(parts) >= 4:
                    extension = parts[3]
                    self._handle_reboot_phone(extension)
                else:
                    self._send_json({'error': 'Invalid path'}, 400)
            elif path == '/api/integrations/ad/sync':
                self._handle_ad_sync()
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def do_PUT(self):
        """Handle PUT requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith('/api/extensions/'):
                # Extract extension number from path
                number = path.split('/')[-1]
                self._handle_update_extension(number)
            elif path == '/api/config':
                self._handle_update_config()
            elif path.startswith('/api/voicemail/'):
                self._handle_update_voicemail(path)
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith('/api/provisioning/devices/'):
                # Extract MAC address from path
                mac = path.split('/')[-1]
                self._handle_unregister_device(mac)
            elif path.startswith('/api/extensions/'):
                # Extract extension number from path
                number = path.split('/')[-1]
                self._handle_delete_extension(number)
            elif path.startswith('/api/voicemail/'):
                self._handle_delete_voicemail(path)
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        try:
            if path == '/api/status':
                self._handle_status()
            elif path == '/api/extensions':
                self._handle_get_extensions()
            elif path == '/api/calls':
                self._handle_get_calls()
            elif path == '/api/config':
                self._handle_get_config()
            elif path == '/api/provisioning/devices':
                self._handle_get_provisioning_devices()
            elif path == '/api/provisioning/vendors':
                self._handle_get_provisioning_vendors()
            elif path == '/api/provisioning/diagnostics':
                self._handle_get_provisioning_diagnostics()
            elif path == '/api/provisioning/requests':
                self._handle_get_provisioning_requests()
            elif path == '/api/registered-phones':
                self._handle_get_registered_phones()
            elif path == '/api/registered-phones/with-mac':
                self._handle_get_registered_phones_with_mac()
            elif path.startswith('/api/registered-phones/extension/'):
                # Extract extension: /api/registered-phones/extension/{number}
                extension = path.split('/')[-1]
                self._handle_get_registered_phones_by_extension(extension)
            elif path.startswith('/api/phone-lookup/'):
                # Extract identifier: /api/phone-lookup/{mac_or_ip}
                identifier = path.split('/')[-1]
                self._handle_phone_lookup(identifier)
            elif path == '/api/integrations/ad/status':
                self._handle_ad_status()
            elif path.startswith('/api/voicemail/'):
                self._handle_get_voicemail(path)
            elif path.startswith('/provision/') and path.endswith('.cfg'):
                self._handle_provisioning_request(path)
            elif path == '' or path == '/admin':
                self._handle_admin_redirect()
            elif path.startswith('/admin/'):
                self._handle_static_file(path)
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_root(self):
        """Handle root path"""
        self._set_headers(content_type='text/html')
        html = """
        <html>
        <head><title>InHouse PBX API</title></head>
        <body>
            <h1>InHouse PBX System API</h1>
            <h2>Available Endpoints:</h2>
            <ul>
                <li>GET /api/status - System status</li>
                <li>GET /api/extensions - List extensions</li>
                <li>GET /api/calls - List active calls</li>
                <li>GET /api/provisioning/devices - List provisioned devices</li>
                <li>GET /api/provisioning/vendors - List supported vendors</li>
                <li>POST /api/provisioning/devices - Register a device</li>
                <li>DELETE /api/provisioning/devices/{mac} - Unregister a device</li>
                <li>GET /provision/{mac}.cfg - Get device configuration</li>
                <li>GET /api/registered-phones - List all registered phones (MAC/IP tracking)</li>
                <li>GET /api/registered-phones/with-mac - List registered phones with MAC addresses from provisioning</li>
                <li>GET /api/registered-phones/extension/{number} - List registered phones for extension</li>
                <li>GET /api/phone-lookup/{mac_or_ip} - Unified lookup by MAC or IP address with correlation</li>
            </ul>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _handle_status(self):
        """Get PBX status"""
        if self.pbx_core:
            status = self.pbx_core.get_status()
            self._send_json(status)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _handle_get_extensions(self):
        """Get extensions"""
        if self.pbx_core:
            extensions = self.pbx_core.extension_registry.get_all()
            data = [{'number': e.number, 'name': e.name, 'email': e.config.get('email'),
                    'registered': e.registered, 'allow_external': e.config.get('allow_external', True),
                    'ad_synced': e.config.get('ad_synced', False), 'voicemail_pin': e.config.get('voicemail_pin')}
                   for e in extensions]
            self._send_json(data)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _handle_get_calls(self):
        """Get active calls"""
        if self.pbx_core:
            calls = self.pbx_core.call_manager.get_active_calls()
            data = [str(call) for call in calls]
            self._send_json(data)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _handle_get_provisioning_devices(self):
        """Get all provisioned devices"""
        if self.pbx_core and hasattr(self.pbx_core, 'phone_provisioning'):
            devices = self.pbx_core.phone_provisioning.get_all_devices()
            data = [d.to_dict() for d in devices]
            self._send_json(data)
        else:
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)

    def _handle_get_provisioning_vendors(self):
        """Get supported vendors and models"""
        if self.pbx_core and hasattr(self.pbx_core, 'phone_provisioning'):
            vendors = self.pbx_core.phone_provisioning.get_supported_vendors()
            models = self.pbx_core.phone_provisioning.get_supported_models()
            data = {
                'vendors': vendors,
                'models': models
            }
            self._send_json(data)
        else:
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
    
    def _handle_get_provisioning_diagnostics(self):
        """Get provisioning system diagnostics"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        provisioning = self.pbx_core.phone_provisioning
        
        # Gather diagnostic information
        diagnostics = {
            'enabled': True,
            'configuration': {
                'url_format': self.pbx_core.config.get('provisioning.url_format', 'Not configured'),
                'external_ip': self.pbx_core.config.get('server.external_ip', 'Not configured'),
                'api_port': self.pbx_core.config.get('api.port', 'Not configured'),
                'sip_host': self.pbx_core.config.get('server.sip_host', 'Not configured'),
                'sip_port': self.pbx_core.config.get('server.sip_port', 'Not configured'),
                'custom_templates_dir': self.pbx_core.config.get('provisioning.custom_templates_dir', 'Not configured')
            },
            'statistics': {
                'total_devices': len(provisioning.devices),
                'total_templates': len(provisioning.templates),
                'total_requests': len(provisioning.provision_requests),
                'successful_requests': sum(1 for r in provisioning.provision_requests if r.get('success')),
                'failed_requests': sum(1 for r in provisioning.provision_requests if not r.get('success'))
            },
            'devices': [d.to_dict() for d in provisioning.get_all_devices()],
            'vendors': provisioning.get_supported_vendors(),
            'models': provisioning.get_supported_models(),
            'recent_requests': provisioning.get_request_history(limit=20)
        }
        
        # Add warnings for common issues
        warnings = []
        if diagnostics['configuration']['external_ip'] == 'Not configured':
            warnings.append('server.external_ip is not configured - phones may not be able to reach the PBX')
        if diagnostics['statistics']['total_devices'] == 0:
            warnings.append('No devices registered - use POST /api/provisioning/devices to register devices')
        if diagnostics['statistics']['failed_requests'] > 0:
            warnings.append(f"{diagnostics['statistics']['failed_requests']} provisioning requests failed - check recent_requests for details")
        
        diagnostics['warnings'] = warnings
        
        self._send_json(diagnostics)
    
    def _handle_get_provisioning_requests(self):
        """Get provisioning request history"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        # Get limit from query parameter if provided
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        limit = int(query_params.get('limit', [50])[0])
        
        requests = self.pbx_core.phone_provisioning.get_request_history(limit=limit)
        self._send_json({
            'total': len(self.pbx_core.phone_provisioning.provision_requests),
            'limit': limit,
            'requests': requests
        })

    def _handle_get_registered_phones(self):
        """Get all registered phones from database"""
        logger = get_logger()
        if self.pbx_core and hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                phones = self.pbx_core.registered_phones_db.list_all()
                self._send_json(phones)
            except Exception as e:
                logger.error(f"Error loading registered phones from database: {e}")
                logger.error(f"  Database type: {self.pbx_core.registered_phones_db.db.db_type if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Database enabled: {self.pbx_core.registered_phones_db.db.enabled if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Traceback: {traceback.format_exc()}")
                self._send_json({'error': str(e), 'details': 'Check server logs for full error details'}, 500)
        else:
            # Return empty array when database is not available (graceful degradation)
            logger.warning("Registered phones database not available - returning empty list")
            if self.pbx_core:
                logger.warning(f"  pbx_core exists: True")
                logger.warning(f"  has registered_phones_db attr: {hasattr(self.pbx_core, 'registered_phones_db')}")
                if hasattr(self.pbx_core, 'registered_phones_db'):
                    logger.warning(f"  registered_phones_db is None: {self.pbx_core.registered_phones_db is None}")
            self._send_json([])

    def _handle_get_registered_phones_with_mac(self):
        """Get registered phones with MAC addresses from provisioning system"""
        logger = get_logger()
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return
        
        # Get registered phones (IP + Extension from SIP registrations)
        registered_phones = []
        if hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                registered_phones = self.pbx_core.registered_phones_db.list_all()
            except Exception as e:
                logger.error(f"Error loading registered phones: {e}")
        
        # Get provisioned devices (MAC + Extension from provisioning config)
        provisioned_devices = {}
        if hasattr(self.pbx_core, 'phone_provisioning'):
            try:
                devices = self.pbx_core.phone_provisioning.get_all_devices()
                # Create a lookup by extension
                for device in devices:
                    provisioned_devices[device.extension_number] = device
            except Exception as e:
                logger.error(f"Error loading provisioned devices: {e}")
        
        # Correlate the two data sources
        enhanced_phones = []
        for phone in registered_phones:
            enhanced = dict(phone)
            extension = phone.get('extension_number')
            
            # Add MAC from provisioning if available and not already present
            if extension and extension in provisioned_devices and not phone.get('mac_address'):
                device = provisioned_devices[extension]
                enhanced['mac_address'] = device.mac_address
                enhanced['vendor'] = device.vendor
                enhanced['model'] = device.model
                enhanced['config_url'] = device.config_url
                enhanced['mac_source'] = 'provisioning'
            elif phone.get('mac_address'):
                enhanced['mac_source'] = 'sip_registration'
            
            enhanced_phones.append(enhanced)
        
        self._send_json(enhanced_phones)

    def _handle_phone_lookup(self, identifier):
        """Unified phone lookup by MAC or IP address"""
        logger = get_logger()
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return
        
        result = {
            'identifier': identifier,
            'type': None,
            'registered_phone': None,
            'provisioned_device': None,
            'correlation': None
        }
        
        # Normalize the identifier to detect if it's a MAC or IP
        from pbx.features.phone_provisioning import normalize_mac_address
        import re
        
        # Check if it looks like a MAC address using regex
        # Matches formats: XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, XXXXXXXXXXXX
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$')
        is_mac = bool(mac_pattern.match(identifier))
        
        # Check if it looks like an IP address using regex
        # Matches valid IPv4 addresses
        ip_pattern = re.compile(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
        is_ip = bool(ip_pattern.match(identifier))
        
        # Try MAC address lookup
        if is_mac:
            result['type'] = 'mac'
            normalized_mac = normalize_mac_address(identifier)
            
            # Check provisioning system
            if hasattr(self.pbx_core, 'phone_provisioning'):
                device = self.pbx_core.phone_provisioning.get_device(identifier)
                if device:
                    result['provisioned_device'] = device.to_dict()
            
            # Check registered phones
            if hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
                try:
                    phone = self.pbx_core.registered_phones_db.get_by_mac(normalized_mac)
                    if phone:
                        result['registered_phone'] = phone
                except Exception as e:
                    logger.error(f"Error looking up MAC in registered_phones: {e}")
        
        # Try IP address lookup
        elif is_ip:
            result['type'] = 'ip'
            
            # Check registered phones first
            if hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
                try:
                    phone = self.pbx_core.registered_phones_db.get_by_ip(identifier)
                    if phone:
                        result['registered_phone'] = phone
                        
                        # Now try to find MAC from provisioning using the extension
                        extension = phone.get('extension_number')
                        if extension and hasattr(self.pbx_core, 'phone_provisioning'):
                            device = None
                            # Search through provisioned devices for this extension
                            for dev in self.pbx_core.phone_provisioning.get_all_devices():
                                if dev.extension_number == extension:
                                    device = dev
                                    break
                            if device:
                                result['provisioned_device'] = device.to_dict()
                except Exception as e:
                    logger.error(f"Error looking up IP in registered_phones: {e}")
        else:
            result['type'] = 'unknown'
            self._send_json({'error': f'Could not determine if {identifier} is a MAC address or IP address'}, 400)
            return
        
        # Add correlation summary
        if result['registered_phone'] and result['provisioned_device']:
            result['correlation'] = {
                'matched': True,
                'extension': result['registered_phone'].get('extension_number'),
                'mac_address': result['provisioned_device'].get('mac_address'),
                'ip_address': result['registered_phone'].get('ip_address'),
                'vendor': result['provisioned_device'].get('vendor'),
                'model': result['provisioned_device'].get('model')
            }
        elif result['registered_phone']:
            result['correlation'] = {
                'matched': False,
                'message': 'Phone is registered but not provisioned in the system',
                'extension': result['registered_phone'].get('extension_number'),
                'ip_address': result['registered_phone'].get('ip_address')
            }
        elif result['provisioned_device']:
            result['correlation'] = {
                'matched': False,
                'message': 'Device is provisioned but not currently registered',
                'extension': result['provisioned_device'].get('extension_number'),
                'mac_address': result['provisioned_device'].get('mac_address')
            }
        else:
            result['correlation'] = {
                'matched': False,
                'message': 'No information found for this identifier'
            }
        
        self._send_json(result)

    def _handle_get_registered_phones_by_extension(self, extension):
        """Get registered phones for a specific extension"""
        logger = get_logger()
        if self.pbx_core and hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                phones = self.pbx_core.registered_phones_db.get_by_extension(extension)
                self._send_json(phones)
            except Exception as e:
                logger.error(f"Error loading registered phones for extension {extension} from database: {e}")
                logger.error(f"  Extension: {extension}")
                logger.error(f"  Database type: {self.pbx_core.registered_phones_db.db.db_type if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Database enabled: {self.pbx_core.registered_phones_db.db.enabled if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Traceback: {traceback.format_exc()}")
                self._send_json({'error': str(e), 'details': 'Check server logs for full error details'}, 500)
        else:
            # Return empty array when database is not available (graceful degradation)
            logger.warning(f"Registered phones database not available for extension {extension} - returning empty list")
            if self.pbx_core:
                logger.warning(f"  pbx_core exists: True")
                logger.warning(f"  has registered_phones_db attr: {hasattr(self.pbx_core, 'registered_phones_db')}")
                if hasattr(self.pbx_core, 'registered_phones_db'):
                    logger.warning(f"  registered_phones_db is None: {self.pbx_core.registered_phones_db is None}")
            self._send_json([])

    def _handle_register_device(self):
        """Register a device for provisioning"""
        logger = get_logger()
        
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            body = self._get_body()
            mac = body.get('mac_address')
            extension = body.get('extension_number')
            vendor = body.get('vendor')
            model = body.get('model')

            if not all([mac, extension, vendor, model]):
                self._send_json({'error': 'Missing required fields'}, 400)
                return

            device = self.pbx_core.phone_provisioning.register_device(
                mac, extension, vendor, model
            )
            
            # Automatically trigger phone reboot after registration
            # This ensures the phone fetches its fresh configuration immediately
            reboot_triggered = False
            try:
                ext = self.pbx_core.extension_registry.get(extension)
                if ext and ext.registered:
                    logger.info(f"Auto-provisioning: Automatically rebooting phone for extension {extension} after device registration")
                    reboot_triggered = self.pbx_core.phone_provisioning.reboot_phone(
                        extension, self.pbx_core.sip_server
                    )
                    if reboot_triggered:
                        logger.info(f"Auto-provisioning: Successfully triggered reboot for extension {extension}")
                    else:
                        logger.info(f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot")
                else:
                    logger.info(f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot")
            except Exception as reboot_error:
                logger.warning(f"Auto-provisioning: Could not auto-reboot phone for extension {extension}: {reboot_error}")
                # Don't fail the registration if reboot fails
            
            response = {
                'success': True,
                'device': device.to_dict()
            }
            if reboot_triggered:
                response['reboot_triggered'] = True
                response['message'] = 'Device registered and phone reboot triggered automatically'
            else:
                response['reboot_triggered'] = False
                response['message'] = 'Device registered. Phone will fetch config on next boot.'
            
            self._send_json(response)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_unregister_device(self, mac):
        """Unregister a device"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            success = self.pbx_core.phone_provisioning.unregister_device(mac)
            if success:
                self._send_json({'success': True, 'message': 'Device unregistered'})
            else:
                self._send_json({'error': 'Device not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_provisioning_request(self, path):
        """Handle phone provisioning config request"""
        logger = get_logger()
        
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            logger.error("Phone provisioning not enabled but provisioning request received")
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            # Extract MAC address from path: /provision/{mac}.cfg
            filename = path.split('/')[-1]
            mac = filename.replace('.cfg', '')
            
            # Gather request information for logging
            request_info = {
                'ip': self.client_address[0] if self.client_address else 'Unknown',
                'user_agent': self.headers.get('User-Agent', 'Unknown'),
                'path': path
            }
            
            logger.info(f"Provisioning config request: path={path}, MAC={mac}, IP={request_info['ip']}")

            # Generate configuration
            config_content, content_type = self.pbx_core.phone_provisioning.generate_config(
                mac, self.pbx_core.extension_registry, request_info
            )

            if config_content:
                self._set_headers(content_type=content_type)
                self.wfile.write(config_content.encode())
                logger.info(f"✓ Provisioning config delivered: {len(config_content)} bytes to {request_info['ip']}")
            else:
                logger.warning(f"✗ Provisioning failed for MAC {mac} from IP {request_info['ip']}")
                logger.warning(f"  Reason: Device not registered or template not found")
                logger.warning(f"  See detailed error messages above for troubleshooting guidance")
                logger.warning(f"  To register this device:")
                logger.warning(f"    curl -X POST http://YOUR_PBX_IP:8080/api/provisioning/devices \\")
                logger.warning(f"      -H 'Content-Type: application/json' \\")
                logger.warning(f"      -d '{{\"mac_address\":\"{mac}\",\"extension_number\":\"XXXX\",\"vendor\":\"VENDOR\",\"model\":\"MODEL\"}}'")
                self._send_json({'error': 'Device or template not found'}, 404)
        except Exception as e:
            logger.error(f"Error handling provisioning request: {e}")
            logger.error(f"  Path: {path}")
            logger.error(f"  Traceback: {traceback.format_exc()}")
            self._send_json({'error': str(e)}, 500)

    def _handle_admin_redirect(self):
        """Redirect to admin panel"""
        self.send_response(302)
        self.send_header('Location', '/admin/index.html')
        self.end_headers()

    def _handle_static_file(self, path):
        """Serve static files from admin directory"""
        try:
            # Remove /admin prefix to get relative path
            file_path = path.replace('/admin/', '', 1)
            full_path = os.path.join(ADMIN_DIR, file_path)

            # Prevent directory traversal attacks - ensure path stays within admin directory
            real_admin_dir = os.path.realpath(ADMIN_DIR)
            real_full_path = os.path.realpath(full_path)

            if not real_full_path.startswith(real_admin_dir):
                self._send_json({'error': 'Access denied'}, 403)
                return

            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                self._send_json({'error': 'File not found'}, 404)
                return

            # Determine content type
            content_type, _ = mimetypes.guess_type(full_path)
            if not content_type:
                content_type = 'application/octet-stream'

            # Read and serve file
            with open(full_path, 'rb') as f:
                content = f.read()

            self._set_headers(content_type=content_type)
            self.wfile.write(content)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_get_config(self):
        """Get current configuration"""
        if self.pbx_core:
            config_data = {
                'smtp': {
                    'host': self.pbx_core.config.get('voicemail.smtp.host', ''),
                    'port': self.pbx_core.config.get('voicemail.smtp.port', 587),
                    'username': self.pbx_core.config.get('voicemail.smtp.username', '')
                },
                'email': {
                    'from_address': self.pbx_core.config.get('voicemail.email.from_address', '')
                },
                'email_notifications': self.pbx_core.config.get('voicemail.email_notifications', False)
            }
            self._send_json(config_data)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _handle_add_extension(self):
        """Add a new extension"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body()
            number = body.get('number')
            name = body.get('name')
            email = body.get('email')
            password = body.get('password')
            allow_external = body.get('allow_external', True)
            voicemail_pin = body.get('voicemail_pin')

            if not all([number, name, password]):
                self._send_json({'error': 'Missing required fields'}, 400)
                return

            # Validate extension number format (4 digits)
            if not str(number).isdigit() or len(str(number)) != 4:
                self._send_json({'error': 'Extension number must be 4 digits'}, 400)
                return

            # Validate password strength (minimum 8 characters)
            if len(password) < 8:
                self._send_json({'error': 'Password must be at least 8 characters'}, 400)
                return

            # Validate email format if provided
            if email and not Config.validate_email(email):
                self._send_json({'error': 'Invalid email format'}, 400)
                return

            # Check if extension already exists
            if self.pbx_core.extension_registry.get(number):
                self._send_json({'error': 'Extension already exists'}, 400)
                return

            # Try to add to database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Add to database
                # TODO: Implement proper password hashing (bcrypt/PBKDF2) for production
                password_hash = password
                success = self.pbx_core.extension_db.add(
                    number=number,
                    name=name,
                    password_hash=password_hash,
                    email=email if email else None,
                    allow_external=allow_external,
                    voicemail_pin=voicemail_pin if voicemail_pin else None,
                    ad_synced=False,
                    ad_username=None
                )
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.add_extension(number, name, email, password, allow_external)

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({'success': True, 'message': 'Extension added successfully'})
            else:
                self._send_json({'error': 'Failed to add extension'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_update_extension(self, number):
        """Update an existing extension"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body()
            name = body.get('name')
            email = body.get('email')
            password = body.get('password')  # Optional
            allow_external = body.get('allow_external')
            voicemail_pin = body.get('voicemail_pin')

            # Check if extension exists
            extension = self.pbx_core.extension_registry.get(number)
            if not extension:
                self._send_json({'error': 'Extension not found'}, 404)
                return

            # Validate password strength if provided (minimum 8 characters)
            if password and len(password) < 8:
                self._send_json({'error': 'Password must be at least 8 characters'}, 400)
                return

            # Validate email format if provided
            if email and not Config.validate_email(email):
                self._send_json({'error': 'Invalid email format'}, 400)
                return

            # Try to update in database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Update in database
                # TODO: Implement proper password hashing (bcrypt/PBKDF2) for production
                password_hash = password if password else None
                success = self.pbx_core.extension_db.update(
                    number=number,
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    allow_external=allow_external,
                    voicemail_pin=voicemail_pin
                )
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.update_extension(number, name, email, password, allow_external)

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({'success': True, 'message': 'Extension updated successfully'})
            else:
                self._send_json({'error': 'Failed to update extension'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_delete_extension(self, number):
        """Delete an extension"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            # Check if extension exists
            extension = self.pbx_core.extension_registry.get(number)
            if not extension:
                self._send_json({'error': 'Extension not found'}, 404)
                return

            # Try to delete from database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Delete from database
                success = self.pbx_core.extension_db.delete(number)
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.delete_extension(number)

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({'success': True, 'message': 'Extension deleted successfully'})
            else:
                self._send_json({'error': 'Failed to delete extension'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_update_config(self):
        """Update system configuration"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body()

            # Update configuration
            success = self.pbx_core.config.update_email_config(body)

            if success:
                self._send_json({'success': True, 'message': 'Configuration updated successfully. Restart required.'})
            else:
                self._send_json({'error': 'Failed to update configuration'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_get_voicemail(self, path):
        """Get voicemail messages for an extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail not enabled'}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension} or /api/voicemail/{extension}/{message_id}
            parts = path.split('/')
            if len(parts) < 4:
                self._send_json({'error': 'Invalid path'}, 400)
                return

            extension = parts[3]

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            if len(parts) == 4:
                # List all messages
                messages = mailbox.get_messages()
                data = []
                for msg in messages:
                    data.append({
                        'id': msg['id'],
                        'caller_id': msg['caller_id'],
                        'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                        'listened': msg['listened'],
                        'duration': msg['duration']
                    })
                self._send_json({'messages': data})
            elif len(parts) == 5:
                # Get specific message or download audio
                message_id = parts[4]

                # Find message
                message = None
                for msg in mailbox.get_messages():
                    if msg['id'] == message_id:
                        message = msg
                        break

                if not message:
                    self._send_json({'error': 'Message not found'}, 404)
                    return

                # Check if request is for audio download
                if 'download' in path or path.endswith('/audio'):
                    # Serve audio file
                    if os.path.exists(message['file_path']):
                        self._set_headers(content_type='audio/wav')
                        with open(message['file_path'], 'rb') as f:
                            self.wfile.write(f.read())
                    else:
                        self._send_json({'error': 'Audio file not found'}, 404)
                else:
                    # Return message details
                    self._send_json({
                        'id': message['id'],
                        'caller_id': message['caller_id'],
                        'timestamp': message['timestamp'].isoformat() if message['timestamp'] else None,
                        'listened': message['listened'],
                        'duration': message['duration'],
                        'file_path': message['file_path']
                    })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_update_voicemail(self, path):
        """Update voicemail settings (mark as read, update PIN)"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail not enabled'}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension}/pin or /api/voicemail/{extension}/{message_id}/mark-read
            parts = path.split('/')
            if len(parts) < 4:
                self._send_json({'error': 'Invalid path'}, 400)
                return

            extension = parts[3]
            body = self._get_body()

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            if len(parts) == 5 and parts[4] == 'pin':
                # Update PIN
                pin = body.get('pin')
                if not pin:
                    self._send_json({'error': 'PIN required'}, 400)
                    return

                if mailbox.set_pin(pin):
                    # Also update in config
                    self.pbx_core.config.update_voicemail_pin(extension, pin)
                    self._send_json({'success': True, 'message': 'PIN updated successfully'})
                else:
                    self._send_json({'error': 'Invalid PIN format. Must be 4 digits.'}, 400)
            elif len(parts) == 6 and parts[5] == 'mark-read':
                # Mark message as read
                message_id = parts[4]
                mailbox.mark_listened(message_id)
                self._send_json({'success': True, 'message': 'Message marked as read'})
            else:
                self._send_json({'error': 'Invalid operation'}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_delete_voicemail(self, path):
        """Delete voicemail message"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail not enabled'}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension}/{message_id}
            parts = path.split('/')
            if len(parts) != 5:
                self._send_json({'error': 'Invalid path'}, 400)
                return

            extension = parts[3]
            message_id = parts[4]

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            # Delete message
            if mailbox.delete_message(message_id):
                self._send_json({'success': True, 'message': 'Message deleted successfully'})
            else:
                self._send_json({'error': 'Message not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_reboot_phone(self, extension):
        """Reboot a specific phone"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            # Send SIP NOTIFY to reboot the phone
            success = self.pbx_core.phone_provisioning.reboot_phone(
                extension,
                self.pbx_core.sip_server
            )

            if success:
                self._send_json({
                    'success': True,
                    'message': f'Reboot signal sent to extension {extension}'
                })
            else:
                self._send_json({
                    'error': f'Failed to send reboot signal to extension {extension}. Extension may not be registered.'
                }, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_ad_status(self):
        """Get Active Directory integration status"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            status = self.pbx_core.get_ad_integration_status()
            self._send_json(status)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_ad_sync(self):
        """Manually trigger Active Directory user synchronization"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            result = self.pbx_core.sync_ad_users()
            if result['success']:
                self._send_json({
                    'success': True,
                    'message': f'Successfully synchronized {result["synced_count"]} users from Active Directory',
                    'synced_count': result['synced_count']
                })
            else:
                self._send_json({
                    'success': False,
                    'error': result['error']
                }, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_reboot_phones(self):
        """Reboot all registered phones"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            # Send SIP NOTIFY to all registered phones
            results = self.pbx_core.phone_provisioning.reboot_all_phones(
                self.pbx_core.sip_server
            )

            self._send_json({
                'success': True,
                'message': f'Rebooted {results["success_count"]} phones',
                'rebooted': results['rebooted'],
                'failed': results['failed'],
                'success_count': results['success_count'],
                'failed_count': results['failed_count']
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def log_message(self, format, *args):
        """Override to use PBX logger"""
        pass  # Suppress default logging


class PBXAPIServer:
    """REST API server for PBX"""

    def __init__(self, pbx_core, host='0.0.0.0', port=8080):
        """
        Initialize API server

        Args:
            pbx_core: PBXCore instance
            host: Host to bind to
            port: Port to bind to
        """
        self.pbx_core = pbx_core
        self.host = host
        self.port = port
        self.server = None
        self.logger = get_logger()
        self.running = False

        # Set PBX core for handler
        PBXAPIHandler.pbx_core = pbx_core

    def start(self):
        """Start API server"""
        try:
            self.server = HTTPServer((self.host, self.port), PBXAPIHandler)
            # Set timeout on socket to allow periodic checking of running flag
            self.server.socket.settimeout(1.0)
            self.running = True

            self.logger.info(f"API server started on http://{self.host}:{self.port}")

            # Start in separate thread
            server_thread = threading.Thread(target=self._run)
            server_thread.daemon = True
            server_thread.start()

            return True
        except Exception as e:
            self.logger.error(f"Failed to start API server: {e}")
            return False

    def _run(self):
        """Run server"""
        while self.running:
            try:
                self.server.handle_request()
            except socket.timeout:
                # Timeout allows us to check running flag periodically
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error handling request: {e}")
        self.logger.info("API server thread stopped")

    def stop(self):
        """Stop API server"""
        self.running = False
        if self.server:
            try:
                self.server.server_close()
            except (OSError, socket.error) as e:
                self.logger.error(f"Error closing API server: {e}")
        self.logger.info("API server stopped")
