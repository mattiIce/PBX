"""
REST API Server for PBX Management
Provides HTTP API for managing PBX features
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket
import threading
import os
import mimetypes
from urllib.parse import urlparse
from pbx.utils.logger import get_logger
from pbx.utils.config import Config

# Admin directory path
ADMIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'admin')


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
        self.wfile.write(json.dumps(data).encode())

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
        path = parsed.path

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
            elif path == '/api/registered-phones':
                self._handle_get_registered_phones()
            elif path.startswith('/api/registered-phones/extension/'):
                # Extract extension: /api/registered-phones/extension/{number}
                extension = path.split('/')[-1]
                self._handle_get_registered_phones_by_extension(extension)
            elif path.startswith('/api/voicemail/'):
                self._handle_get_voicemail(path)
            elif path.startswith('/provision/') and path.endswith('.cfg'):
                self._handle_provisioning_request(path)
            elif path == '/' or path == '/admin' or path == '/admin/':
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
                <li>GET /api/registered-phones/extension/{number} - List registered phones for extension</li>
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
                    'registered': e.registered, 'allow_external': e.config.get('allow_external', True)}
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

    def _handle_get_registered_phones(self):
        """Get all registered phones from database"""
        if self.pbx_core and hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                phones = self.pbx_core.registered_phones_db.list_all()
                self._send_json(phones)
            except Exception as e:
                self._send_json({'error': str(e)}, 500)
        else:
            # Return empty array when database is not available (graceful degradation)
            self._send_json([])

    def _handle_get_registered_phones_by_extension(self, extension):
        """Get registered phones for a specific extension"""
        if self.pbx_core and hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                phones = self.pbx_core.registered_phones_db.get_by_extension(extension)
                self._send_json(phones)
            except Exception as e:
                self._send_json({'error': str(e)}, 500)
        else:
            # Return empty array when database is not available (graceful degradation)
            self._send_json([])

    def _handle_register_device(self):
        """Register a device for provisioning"""
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
            self._send_json({
                'success': True,
                'device': device.to_dict()
            })
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
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            # Extract MAC address from path: /provision/{mac}.cfg
            filename = path.split('/')[-1]
            mac = filename.replace('.cfg', '')

            # Generate configuration
            config_content, content_type = self.pbx_core.phone_provisioning.generate_config(
                mac, self.pbx_core.extension_registry
            )

            if config_content:
                self._set_headers(content_type=content_type)
                self.wfile.write(config_content.encode())
            else:
                self._send_json({'error': 'Device or template not found'}, 404)
        except Exception as e:
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

            # Add extension to configuration
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

            # Update extension in configuration
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

            # Delete extension from configuration
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
