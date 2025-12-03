"""
RTP Media Handler
Handles real-time audio/video streaming
"""
import socket
import threading
import struct
from pbx.utils.logger import get_logger


class RTPHandler:
    """Handle RTP media streams"""
    
    def __init__(self, local_port, remote_host=None, remote_port=None):
        """
        Initialize RTP handler
        
        Args:
            local_port: Local port to bind to
            remote_host: Remote host to send to
            remote_port: Remote port to send to
        """
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.logger = get_logger()
        self.socket = None
        self.running = False
        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = 0x12345678  # Synchronization source identifier
        
    def start(self):
        """Start RTP handler"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.local_port))
            self.running = True
            
            self.logger.info(f"RTP handler started on port {self.local_port}")
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self._receive_loop)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to start RTP handler: {e}")
            return False
    
    def stop(self):
        """Stop RTP handler"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info(f"RTP handler stopped on port {self.local_port}")
    
    def _receive_loop(self):
        """Receive RTP packets"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                self._handle_rtp_packet(data, addr)
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error receiving RTP packet: {e}")
    
    def _handle_rtp_packet(self, data, addr):
        """
        Handle incoming RTP packet
        
        Args:
            data: Packet data
            addr: Source address
        """
        if len(data) < 12:
            return
        
        # Parse RTP header (simplified)
        # RTP header: version(2), padding(1), extension(1), CSRC count(4),
        #             marker(1), payload type(7), sequence number(16),
        #             timestamp(32), SSRC(32)
        
        header = struct.unpack('!BBHII', data[:12])
        version = (header[0] >> 6) & 0x03
        payload_type = header[1] & 0x7F
        seq_num = header[2]
        timestamp = header[3]
        ssrc = header[4]
        
        payload = data[12:]
        
        self.logger.debug(f"Received RTP packet: seq={seq_num}, pt={payload_type}, size={len(payload)}")
        
        # In a real implementation, you would:
        # 1. Buffer and reorder packets based on sequence number
        # 2. Decode audio based on payload type (codec)
        # 3. Mix/route audio to other participants
        # 4. Handle packet loss and jitter
    
    def send_packet(self, payload, payload_type=0, marker=False):
        """
        Send RTP packet
        
        Args:
            payload: Audio/video payload data
            payload_type: RTP payload type (codec identifier)
            marker: Marker bit
            
        Returns:
            True if sent successfully
        """
        if not self.remote_host or not self.remote_port:
            return False
        
        try:
            # Build RTP header
            version = 2
            padding = 0
            extension = 0
            csrc_count = 0
            
            byte0 = (version << 6) | (padding << 5) | (extension << 4) | csrc_count
            byte1 = (int(marker) << 7) | (payload_type & 0x7F)
            
            header = struct.pack('!BBHII',
                                byte0,
                                byte1,
                                self.sequence_number,
                                self.timestamp,
                                self.ssrc)
            
            packet = header + payload
            
            self.socket.sendto(packet, (self.remote_host, self.remote_port))
            
            # Update sequence and timestamp
            self.sequence_number = (self.sequence_number + 1) & 0xFFFF
            self.timestamp += len(payload)  # Simplified, should be based on sample rate
            
            return True
        except Exception as e:
            self.logger.error(f"Error sending RTP packet: {e}")
            return False


class RTPRelay:
    """
    RTP relay for connecting two endpoints
    Used for call forwarding, conferencing, etc.
    """
    
    def __init__(self, port_range_start=10000, port_range_end=20000):
        """
        Initialize RTP relay
        
        Args:
            port_range_start: Start of port range for RTP
            port_range_end: End of port range for RTP
        """
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.active_relays = {}
        self.logger = get_logger()
        self.port_pool = list(range(port_range_start, port_range_end, 2))  # Even ports for RTP
    
    def allocate_relay(self, call_id):
        """
        Allocate RTP relay for a call
        
        Args:
            call_id: Unique call identifier
            
        Returns:
            Tuple of (rtp_port, rtcp_port) or None if allocation failed
        """
        if not self.port_pool:
            self.logger.error("No available ports for RTP relay")
            return None
        
        rtp_port = self.port_pool.pop(0)
        rtcp_port = rtp_port + 1
        
        handler = RTPHandler(rtp_port)
        if handler.start():
            self.active_relays[call_id] = {
                'rtp_port': rtp_port,
                'rtcp_port': rtcp_port,
                'handler': handler
            }
            self.logger.info(f"Allocated RTP relay for call {call_id}: ports {rtp_port}/{rtcp_port}")
            return (rtp_port, rtcp_port)
        else:
            self.port_pool.insert(0, rtp_port)
            return None
    
    def release_relay(self, call_id):
        """
        Release RTP relay for a call
        
        Args:
            call_id: Call identifier
        """
        if call_id in self.active_relays:
            relay = self.active_relays[call_id]
            relay['handler'].stop()
            self.port_pool.append(relay['rtp_port'])
            self.port_pool.sort()
            del self.active_relays[call_id]
            self.logger.info(f"Released RTP relay for call {call_id}")
