"""
SIP Server implementation
"""
import socket
import threading
from pbx.sip.message import SIPMessage, SIPMessageBuilder
from pbx.utils.logger import get_logger


class SIPServer:
    """SIP server for handling registration and calls"""
    
    def __init__(self, host='0.0.0.0', port=5060, pbx_core=None):
        """
        Initialize SIP server
        
        Args:
            host: Host to bind to
            port: Port to bind to
            pbx_core: Reference to PBX core
        """
        self.host = host
        self.port = port
        self.pbx_core = pbx_core
        self.logger = get_logger()
        self.socket = None
        self.running = False
        
    def start(self):
        """Start SIP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.running = True
            
            self.logger.info(f"SIP server started on {self.host}:{self.port}")
            
            # Start listening thread
            listen_thread = threading.Thread(target=self._listen)
            listen_thread.daemon = True
            listen_thread.start()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to start SIP server: {e}")
            return False
    
    def stop(self):
        """Stop SIP server"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info("SIP server stopped")
    
    def _listen(self):
        """Listen for incoming SIP messages"""
        self.logger.info("SIP server listening for messages...")
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                
                # Handle message in separate thread
                handler_thread = threading.Thread(
                    target=self._handle_message,
                    args=(data.decode('utf-8'), addr)
                )
                handler_thread.daemon = True
                handler_thread.start()
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error receiving message: {e}")
    
    def _handle_message(self, raw_message, addr):
        """
        Handle incoming SIP message
        
        Args:
            raw_message: Raw SIP message string
            addr: Source address tuple (host, port)
        """
        try:
            message = SIPMessage(raw_message)
            
            self.logger.debug(f"Received {message.method or message.status_code} from {addr}")
            
            if message.is_request():
                self._handle_request(message, addr)
            else:
                self._handle_response(message, addr)
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def _handle_request(self, message, addr):
        """
        Handle SIP request
        
        Args:
            message: SIPMessage object
            addr: Source address
        """
        method = message.method
        
        if method == 'REGISTER':
            self._handle_register(message, addr)
        elif method == 'INVITE':
            self._handle_invite(message, addr)
        elif method == 'ACK':
            self._handle_ack(message, addr)
        elif method == 'BYE':
            self._handle_bye(message, addr)
        elif method == 'CANCEL':
            self._handle_cancel(message, addr)
        elif method == 'OPTIONS':
            self._handle_options(message, addr)
        else:
            self.logger.warning(f"Unhandled SIP method: {method}")
            self._send_response(405, "Method Not Allowed", message, addr)
    
    def _handle_register(self, message, addr):
        """Handle REGISTER request"""
        self.logger.info(f"REGISTER request from {addr}")
        
        # Extract extension from URI or From header
        from_header = message.get_header('From')
        
        if self.pbx_core:
            # Simple registration - in production, verify credentials
            success = self.pbx_core.register_extension(from_header, addr)
            
            if success:
                self._send_response(200, "OK", message, addr)
            else:
                self._send_response(401, "Unauthorized", message, addr)
        else:
            self._send_response(200, "OK", message, addr)
    
    def _handle_invite(self, message, addr):
        """Handle INVITE request"""
        self.logger.info(f"INVITE request from {addr}")
        
        if self.pbx_core:
            # Extract call information
            from_header = message.get_header('From')
            to_header = message.get_header('To')
            call_id = message.get_header('Call-ID')
            
            # Route call through PBX core
            success = self.pbx_core.route_call(from_header, to_header, call_id, message)
            
            if success:
                self._send_response(100, "Trying", message, addr)
                # Actual call setup would continue asynchronously
            else:
                self._send_response(404, "Not Found", message, addr)
        else:
            self._send_response(200, "OK", message, addr)
    
    def _handle_ack(self, message, addr):
        """Handle ACK request"""
        self.logger.debug(f"ACK request from {addr}")
        # ACK is not responded to
    
    def _handle_bye(self, message, addr):
        """Handle BYE request"""
        self.logger.info(f"BYE request from {addr}")
        
        if self.pbx_core:
            call_id = message.get_header('Call-ID')
            self.pbx_core.end_call(call_id)
        
        self._send_response(200, "OK", message, addr)
    
    def _handle_cancel(self, message, addr):
        """Handle CANCEL request"""
        self.logger.info(f"CANCEL request from {addr}")
        self._send_response(200, "OK", message, addr)
    
    def _handle_options(self, message, addr):
        """Handle OPTIONS request"""
        self.logger.debug(f"OPTIONS request from {addr}")
        response = SIPMessageBuilder.build_response(200, "OK", message)
        response.set_header('Allow', 'INVITE, ACK, BYE, CANCEL, OPTIONS, REGISTER')
        self._send_message(response.build(), addr)
    
    def _handle_response(self, message, addr):
        """Handle SIP response"""
        self.logger.debug(f"Received response {message.status_code} from {addr}")
    
    def _send_response(self, status_code, status_text, request, addr):
        """
        Send SIP response
        
        Args:
            status_code: Status code
            status_text: Status text
            request: Original request message
            addr: Destination address
        """
        response = SIPMessageBuilder.build_response(status_code, status_text, request)
        self._send_message(response.build(), addr)
    
    def _send_message(self, message, addr):
        """
        Send SIP message
        
        Args:
            message: Message string
            addr: Destination address
        """
        try:
            self.socket.sendto(message.encode('utf-8'), addr)
            self.logger.debug(f"Sent message to {addr}")
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
