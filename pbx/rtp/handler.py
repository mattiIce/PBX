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
        
        handler = RTPRelayHandler(rtp_port, call_id)
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
    
    def set_endpoints(self, call_id, endpoint_a, endpoint_b):
        """
        Set both endpoints for RTP relay
        
        Args:
            call_id: Call identifier
            endpoint_a: Tuple of (host, port) for first endpoint
            endpoint_b: Tuple of (host, port) for second endpoint
        """
        if call_id in self.active_relays:
            handler = self.active_relays[call_id]['handler']
            handler.set_endpoints(endpoint_a, endpoint_b)
            self.logger.info(f"RTP relay {call_id}: {endpoint_a} <-> {endpoint_b}")
    
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


class RTPRelayHandler:
    """
    RTP relay handler that forwards packets between two endpoints
    """
    
    def __init__(self, local_port, call_id):
        """
        Initialize RTP relay handler
        
        Args:
            local_port: Local port to bind to
            call_id: Call identifier for logging
        """
        self.local_port = local_port
        self.call_id = call_id
        self.logger = get_logger()
        self.socket = None
        self.running = False
        self.endpoint_a = None  # (host, port)
        self.endpoint_b = None  # (host, port)
        self.lock = threading.Lock()
    
    def set_endpoints(self, endpoint_a, endpoint_b):
        """
        Set the two endpoints to relay between
        
        Args:
            endpoint_a: Tuple of (host, port)
            endpoint_b: Tuple of (host, port)
        """
        with self.lock:
            self.endpoint_a = endpoint_a
            self.endpoint_b = endpoint_b
    
    def start(self):
        """Start RTP relay handler"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.local_port))
            self.running = True
            
            self.logger.info(f"RTP relay handler started on port {self.local_port} for call {self.call_id}")
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self._relay_loop)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to start RTP relay handler: {e}")
            return False
    
    def stop(self):
        """Stop RTP relay handler"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info(f"RTP relay handler stopped on port {self.local_port}")
    
    def _relay_loop(self):
        """Relay RTP packets between endpoints"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                
                # Determine which endpoint sent this packet and forward to the other
                with self.lock:
                    if self.endpoint_a and self.endpoint_b:
                        # Check if packet is from endpoint A, send to B
                        if addr[0] == self.endpoint_a[0] and addr[1] == self.endpoint_a[1]:
                            self.socket.sendto(data, self.endpoint_b)
                            self.logger.debug(f"Relayed {len(data)} bytes: A->B")
                        # Check if packet is from endpoint B, send to A
                        elif addr[0] == self.endpoint_b[0] and addr[1] == self.endpoint_b[1]:
                            self.socket.sendto(data, self.endpoint_a)
                            self.logger.debug(f"Relayed {len(data)} bytes: B->A")
                        else:
                            # First packet from unknown endpoint, might need to learn the address
                            self.logger.debug(f"RTP packet from unknown source: {addr}")
                    
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in RTP relay loop: {e}")


class RTPRecorder:
    """
    RTP recorder for voicemail recording
    Records incoming RTP audio stream
    """
    
    def __init__(self, local_port, call_id):
        """
        Initialize RTP recorder
        
        Args:
            local_port: Local port to bind to
            call_id: Call identifier for logging
        """
        self.local_port = local_port
        self.call_id = call_id
        self.logger = get_logger()
        self.socket = None
        self.running = False
        self.recorded_data = []
        self.lock = threading.Lock()
        self.remote_endpoint = None  # Will be learned from first packet
        
    def start(self):
        """Start RTP recorder"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.local_port))
            self.socket.settimeout(0.5)  # 500ms timeout for recv
            self.running = True
            
            self.logger.info(f"RTP recorder started on port {self.local_port} for call {self.call_id}")
            
            # Start recording thread
            record_thread = threading.Thread(target=self._record_loop)
            record_thread.daemon = True
            record_thread.start()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to start RTP recorder: {e}")
            return False
    
    def stop(self):
        """Stop RTP recorder"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except (OSError, socket.error) as e:
                self.logger.debug(f"Error closing socket: {e}")
        self.logger.info(f"RTP recorder stopped on port {self.local_port}")
    
    def _record_loop(self):
        """Record RTP packets"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                
                # Learn remote endpoint from first packet
                if not self.remote_endpoint:
                    self.remote_endpoint = addr
                    self.logger.info(f"Learned remote RTP endpoint: {addr}")
                
                # Extract audio payload from RTP packet
                if len(data) >= 12:
                    # Parse RTP header to get payload
                    header = struct.unpack('!BBHII', data[:12])
                    payload_type = header[1] & 0x7F
                    payload = data[12:]
                    
                    # Store the audio payload
                    with self.lock:
                        self.recorded_data.append(payload)
                    
                    self.logger.debug(f"Recorded {len(payload)} bytes from call {self.call_id}")
                    
            except socket.timeout:
                # Timeout is normal, just continue
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in RTP record loop: {e}")
    
    def get_recorded_audio(self):
        """
        Get all recorded audio data
        
        Returns:
            bytes: Combined audio data
        """
        with self.lock:
            # Combine all recorded payloads
            return b''.join(self.recorded_data)
    
    def get_duration(self):
        """
        Estimate recording duration based on packets received
        Assumes 20ms per packet (typical for G.711)
        
        Note: This is an approximation. For accurate duration calculation,
        we would need to track RTP timestamps and account for packet timing
        variations, lost packets, or different packetization intervals.
        
        Returns:
            int: Duration in seconds (estimated)
        """
        with self.lock:
            num_packets = len(self.recorded_data)
            # Each packet typically represents 20ms of audio
            duration_ms = num_packets * 20
            return duration_ms // 1000


class RTPPlayer:
    """
    RTP Player - Sends audio to remote endpoint
    Used for playing tones, announcements, music on hold, etc.
    """
    
    def __init__(self, local_port, remote_host, remote_port, call_id=None):
        """
        Initialize RTP player
        
        Args:
            local_port: Local UDP port to send from
            remote_host: Remote host IP address
            remote_port: Remote UDP port
            call_id: Optional call identifier for logging
        """
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.call_id = call_id or "unknown"
        self.logger = get_logger()
        self.socket = None
        self.running = False
        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = 0x87654321  # Synchronization source identifier
        self.lock = threading.Lock()
        
    def start(self):
        """Start RTP player"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces (0.0.0.0) to allow RTP from any network adapter
            # This is intentional for VoIP systems which need to handle multi-homed servers
            self.socket.bind(('0.0.0.0', self.local_port))
            self.running = True
            
            self.logger.info(f"RTP player started on port {self.local_port} for call {self.call_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start RTP player: {e}")
            return False
    
    def stop(self):
        """Stop RTP player"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.logger.info(f"RTP player stopped for call {self.call_id}")
    
    def send_audio(self, audio_data, payload_type=0, samples_per_packet=160, bytes_per_sample=2):
        """
        Send audio data via RTP packets
        
        Args:
            audio_data: Raw PCM audio data
            payload_type: RTP payload type (0 = PCMU, 8 = PCMA)
            samples_per_packet: Number of samples per RTP packet (default 160 = 20ms at 8kHz)
            bytes_per_sample: Bytes per sample (1 for G.711, 2 for 16-bit PCM)
        
        Returns:
            bool: True if successful
        """
        if not self.running or not self.socket:
            self.logger.warning(f"Cannot send audio - RTP player not running")
            return False
        
        try:
            # Split audio into packets
            bytes_per_packet = samples_per_packet * bytes_per_sample
            num_packets = (len(audio_data) + bytes_per_packet - 1) // bytes_per_packet
            
            for i in range(num_packets):
                start = i * bytes_per_packet
                end = min(start + bytes_per_packet, len(audio_data))
                payload = audio_data[start:end]
                
                # Build RTP packet
                rtp_packet = self._build_rtp_packet(payload, payload_type)
                
                # Send packet
                self.socket.sendto(rtp_packet, (self.remote_host, self.remote_port))
                
                # Increment sequence and timestamp
                with self.lock:
                    self.sequence_number = (self.sequence_number + 1) & 0xFFFF
                    self.timestamp = (self.timestamp + samples_per_packet) & 0xFFFFFFFF
                
                # Small delay to pace packets (20ms for 160 samples at 8kHz)
                import time
                time.sleep(0.020)
            
            self.logger.info(f"Sent {num_packets} RTP packets for call {self.call_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending audio: {e}")
            return False
    
    def _build_rtp_packet(self, payload, payload_type=0):
        """
        Build an RTP packet
        
        Args:
            payload: Audio payload bytes
            payload_type: RTP payload type
        
        Returns:
            bytes: Complete RTP packet
        """
        # RTP header (12 bytes)
        # Byte 0: V(2), P(1), X(1), CC(4)
        # V=2, P=0, X=0, CC=0
        byte0 = 0x80  # Version 2, no padding, no extension, no CSRC
        
        # Byte 1: M(1), PT(7)
        # M=0 (not first packet), PT=payload_type
        byte1 = payload_type & 0x7F
        
        with self.lock:
            header = struct.pack('>BBHII',
                byte0,
                byte1,
                self.sequence_number,
                self.timestamp,
                self.ssrc
            )
        
        return header + payload
    
    def play_beep(self, frequency=1000, duration_ms=500):
        """
        Play a beep tone
        
        Args:
            frequency: Frequency in Hz
            duration_ms: Duration in milliseconds
        
        Returns:
            bool: True if successful
        """
        # Note: Import here to avoid circular dependency with audio module
        try:
            from pbx.utils.audio import generate_beep_tone
            pcm_data = generate_beep_tone(frequency, duration_ms, sample_rate=8000)
            # Beep tone is 16-bit PCM, 2 bytes per sample
            return self.send_audio(pcm_data, payload_type=0, bytes_per_sample=2)
        except ImportError:
            self.logger.error("Audio utilities not available")
            return False
    
    def play_file(self, file_path):
        """
        Play an audio file
        
        Args:
            file_path: Path to WAV file
        
        Returns:
            bool: True if successful
        """
        import os
        
        if not os.path.exists(file_path):
            self.logger.error(f"Audio file not found: {file_path}")
            return False
        
        try:
            # Read WAV file
            with open(file_path, 'rb') as f:
                wav_data = f.read()
            
            # Parse WAV header to find audio data
            # WAV format: RIFF header (12 bytes) + chunks
            if not wav_data.startswith(b'RIFF') or b'WAVE' not in wav_data[:20]:
                self.logger.error(f"Invalid WAV file: {file_path}")
                return False
            
            # Find the data chunk
            data_pos = wav_data.find(b'data')
            if data_pos == -1:
                self.logger.error(f"No data chunk in WAV file: {file_path}")
                return False
            
            # Read data chunk size (4 bytes after 'data')
            data_size = struct.unpack('<I', wav_data[data_pos + 4:data_pos + 8])[0]
            
            # Extract audio data (skip 'data' + size = 8 bytes)
            audio_data = wav_data[data_pos + 8:data_pos + 8 + data_size]
            
            # For G.711 μ-law (8-bit samples), we can send directly
            # Each sample is 1 byte, so 160 bytes = 160 samples = 20ms at 8kHz
            samples_per_packet = 160
            
            # Send audio in chunks (G.711 is 1 byte per sample)
            return self.send_audio(audio_data, payload_type=0, samples_per_packet=samples_per_packet, bytes_per_sample=1)
            
        except Exception as e:
            self.logger.error(f"Error playing file {file_path}: {e}")
            return False
