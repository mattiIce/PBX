"""
REST API Server for PBX Management
Provides HTTP API for managing PBX features
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from urllib.parse import urlparse, parse_qs
from pbx.utils.logger import get_logger


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
            elif path == '/api/provisioning/devices':
                self._handle_get_provisioning_devices()
            elif path == '/api/provisioning/vendors':
                self._handle_get_provisioning_vendors()
            elif path.startswith('/provision/') and path.endswith('.cfg'):
                self._handle_provisioning_request(path)
            elif path == '/':
                self._handle_root()
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
            data = [{'number': e.number, 'name': e.name, 'registered': e.registered} 
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
            self.server.handle_request()
    
    def stop(self):
        """Stop API server"""
        self.running = False
        if self.server:
            self.server.shutdown()
        self.logger.info("API server stopped")
