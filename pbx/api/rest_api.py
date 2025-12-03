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
