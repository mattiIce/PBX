"""
RTP Media Handler
Handles real-time audio/video streaming
"""
import socket
import threading
import struct
from pbx.utils.logger import get_logger
from pbx.utils.audio import WAV_FORMAT_PCM, WAV_FORMAT_ULAW, WAV_FORMAT_ALAW, WAV_FORMAT_G722


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

    def __init__(self, port_range_start=10000, port_range_end=20000, qos_monitor=None):
        """
        Initialize RTP relay

        Args:
            port_range_start: Start of port range for RTP
            port_range_end: End of port range for RTP
            qos_monitor: Optional QoS monitor for tracking call quality
        """
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.active_relays = {}
        self.logger = get_logger()
        self.port_pool = list(range(port_range_start, port_range_end, 2))  # Even ports for RTP
        self.qos_monitor = qos_monitor

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

        handler = RTPRelayHandler(rtp_port, call_id, qos_monitor=self.qos_monitor)
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

    def __init__(self, local_port, call_id, qos_monitor=None):
        """
        Initialize RTP relay handler

        Args:
            local_port: Local port to bind to
            call_id: Call identifier for logging
            qos_monitor: Optional QoS monitor for tracking call quality
        """
        self.local_port = local_port
        self.call_id = call_id
        self.logger = get_logger()
        self.socket = None
        self.running = False
        self.endpoint_a = None  # (host, port)
        self.endpoint_b = None  # (host, port)
        self.lock = threading.Lock()
        self.qos_monitor = qos_monitor
        self.qos_metrics = None
        self._qos_packet_count = 0  # For sampling QoS updates
        
        # Start QoS monitoring if monitor is available
        if self.qos_monitor:
            self.qos_metrics = self.qos_monitor.start_monitoring(call_id)

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
        
        # Stop QoS monitoring if active
        if self.qos_monitor and self.qos_metrics:
            self.qos_monitor.stop_monitoring(self.call_id)
        
        self.logger.info(f"RTP relay handler stopped on port {self.local_port}")

    def _relay_loop(self):
        """Relay RTP packets between endpoints"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)

                # Update QoS metrics if monitoring is enabled (sample every 10th packet for performance)
                if self.qos_metrics and len(data) >= 12:
                    self._qos_packet_count += 1
                    if self._qos_packet_count % 10 == 0:
                        try:
                            # Parse RTP header
                            header = struct.unpack('!BBHII', data[:12])
                            seq_num = header[2]
                            timestamp = header[3]
                            payload_size = len(data) - 12
                            
                            # Update received packet metrics
                            self.qos_metrics.update_packet_received(seq_num, timestamp, payload_size)
                        except Exception as qos_error:
                            self.logger.debug(f"Error updating QoS metrics: {qos_error}")

                # Determine which endpoint sent this packet and forward to the other
                with self.lock:
                    if self.endpoint_a and self.endpoint_b:
                        # Check if packet is from endpoint A, send to B
                        if addr[0] == self.endpoint_a[0] and addr[1] == self.endpoint_a[1]:
                            self.socket.sendto(data, self.endpoint_b)
                            if self.qos_metrics:
                                self.qos_metrics.update_packet_sent()
                            self.logger.debug(f"Relayed {len(data)} bytes: A->B")
                        # Check if packet is from endpoint B, send to A
                        elif addr[0] == self.endpoint_b[0] and addr[1] == self.endpoint_b[1]:
                            self.socket.sendto(data, self.endpoint_a)
                            if self.qos_metrics:
                                self.qos_metrics.update_packet_sent()
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
    Automatically filters out RFC 2833 telephone-event packets (payload type 101)
    """

    def __init__(self, local_port, call_id, rfc2833_handler=None):
        """
        Initialize RTP recorder

        Args:
            local_port: Local port to bind to
            call_id: Call identifier for logging
            rfc2833_handler: Optional RFC 2833 receiver for DTMF event handling
        """
        self.local_port = local_port
        self.call_id = call_id
        self.logger = get_logger()
        self.socket = None
        self.running = False
        self.recorded_data = []
        self.lock = threading.Lock()
        self.remote_endpoint = None  # Will be learned from first packet
        self.rfc2833_handler = rfc2833_handler  # Optional RFC 2833 receiver

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

                    # Filter out RFC 2833 telephone-event packets (payload type 101)
                    # These are DTMF signaling packets, not audio
                    if payload_type == 101:
                        self.logger.debug(f"Received RFC 2833 telephone-event packet (filtered from recording)")
                        # If we have an RFC 2833 handler, delegate event processing
                        if self.rfc2833_handler:
                            self.rfc2833_handler.handle_rtp_packet(data, addr)
                        continue

                    # Store only audio payloads (not telephone-events)
                    with self.lock:
                        self.recorded_data.append(payload)

                    self.logger.debug(f"Recorded {len(payload)} bytes (PT {payload_type}) from call {self.call_id}")

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
            except OSError:
                pass  # Socket already closed
            self.socket = None
        self.logger.info(f"RTP player stopped for call {self.call_id}")

    def send_audio(self, audio_data, payload_type=0, samples_per_packet=160, bytes_per_sample=None):
        """
        Send audio data via RTP packets

        Args:
            audio_data: Raw audio data (format depends on payload_type)
                        - For PCMU/PCMA (PT 0/8): 8-bit samples (1 byte per sample)
                        - For G.722 (PT 9): 8-bit encoded samples (1 byte per sample)
                        - For PCM (PT 10/11): 16-bit samples (2 bytes per sample)
            payload_type: RTP payload type (0 = PCMU, 8 = PCMA, 9 = G.722, 10 = L16 stereo, 11 = L16 mono)
            samples_per_packet: Number of samples per RTP packet (default 160 = 20ms at 8kHz)
            bytes_per_sample: Bytes per sample (None=auto-detect, 1 for G.711/G.722, 2 for 16-bit PCM)

        Returns:
            bool: True if successful
        """
        if not self.running or not self.socket:
            self.logger.warning(f"Cannot send audio - RTP player not running")
            return False

        try:
            # Determine bytes per sample if not explicitly provided
            if bytes_per_sample is None:
                # G.711 formats (PCMU, PCMA) are 8-bit = 1 byte per sample
                # G.722 is also 8-bit encoded = 1 byte per sample
                # PCM formats are typically 16-bit = 2 bytes per sample
                if payload_type in [0, 8, 9]:  # PCMU, PCMA, or G.722
                    bytes_per_sample = 1
                else:  # PCM or other formats
                    bytes_per_sample = 2

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
            return self.send_audio(pcm_data, payload_type=0)
        except ImportError:
            self.logger.error("Audio utilities not available")
            return False

    def play_file(self, file_path):
        """
        Play an audio file from a WAV file

        Supports WAV files with:
        - G.711 μ-law (8-bit, 8kHz) - legacy format
        - G.711 A-law (8-bit, 8kHz) - legacy format
        - PCM (16-bit, 8kHz/16kHz) - converted to G.722 for HD audio

        Args:
            file_path: Path to WAV file

        Returns:
            bool: True if successful
        """
        import os
        import struct

        if not os.path.exists(file_path):
            self.logger.error(f"Audio file not found: {file_path}")
            return False

        try:
            with open(file_path, 'rb') as f:
                # Read WAV header
                riff = f.read(4)
                if riff != b'RIFF' or len(riff) < 4:
                    self.logger.error(f"Invalid WAV file (bad RIFF header): {file_path}")
                    return False

                size_bytes = f.read(4)
                if len(size_bytes) < 4:
                    self.logger.error(f"Truncated WAV file (no file size): {file_path}")
                    return False
                file_size = struct.unpack('<I', size_bytes)[0]

                wave = f.read(4)
                if wave != b'WAVE' or len(wave) < 4:
                    self.logger.error(f"Invalid WAV file (bad WAVE marker): {file_path}")
                    return False

                # Find fmt chunk
                while True:
                    chunk_id = f.read(4)
                    if not chunk_id or len(chunk_id) < 4:
                        self.logger.error(f"No format chunk found in WAV file: {file_path}")
                        return False

                    size_bytes = f.read(4)
                    if not size_bytes or len(size_bytes) < 4:
                        self.logger.error(f"Truncated chunk size in WAV file: {file_path}")
                        return False
                    chunk_size = struct.unpack('<I', size_bytes)[0]

                    if chunk_id == b'fmt ':
                        # Validate fmt chunk size (minimum 16 bytes for basic format)
                        if chunk_size < 16:
                            self.logger.error(f"Invalid fmt chunk size in WAV file: {file_path}")
                            return False

                        # Parse format
                        fmt_data = f.read(16)
                        if len(fmt_data) < 16:
                            self.logger.error(f"Truncated fmt chunk in WAV file: {file_path}")
                            return False

                        audio_format = struct.unpack('<H', fmt_data[0:2])[0]
                        num_channels = struct.unpack('<H', fmt_data[2:4])[0]
                        sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                        byte_rate = struct.unpack('<I', fmt_data[8:12])[0]
                        block_align = struct.unpack('<H', fmt_data[12:14])[0]
                        bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]

                        # Skip any extra format bytes
                        if chunk_size > 16:
                            extra_bytes = f.read(chunk_size - 16)

                        # Determine payload type based on format
                        convert_to_pcmu = False
                        if audio_format == WAV_FORMAT_ULAW:
                            payload_type = 0  # PCMU (μ-law)
                        elif audio_format == WAV_FORMAT_ALAW:
                            payload_type = 8  # PCMA (A-law)
                        elif audio_format == WAV_FORMAT_G722:
                            # G.722 format - already encoded, no conversion needed
                            payload_type = 9  # G.722
                            self.logger.info(f"G.722 format detected - already encoded for VoIP.")
                        elif audio_format == WAV_FORMAT_PCM:
                            # PCM format - convert to PCMU (G.711 μ-law) for maximum compatibility
                            # Note: Previously converted to G.722, but G.722 has implementation issues
                            payload_type = 0  # PCMU
                            convert_to_pcmu = True
                            self.logger.info(f"PCM format detected - will convert to PCMU (G.711 μ-law) "
                                           f"for maximum compatibility.")
                        else:
                            self.logger.error(f"Unsupported audio format: {audio_format}")
                            return False

                        self.logger.info(f"WAV file: format={audio_format}, channels={num_channels}, "
                                       f"rate={sample_rate}Hz, bits={bits_per_sample}")
                        break

                    elif chunk_id == b'data':
                        # Found data before fmt - invalid
                        self.logger.error(f"Invalid WAV structure")
                        return False
                    else:
                        # Skip unknown chunk
                        f.read(chunk_size)

                # Find data chunk
                while True:
                    chunk_id = f.read(4)
                    if not chunk_id or len(chunk_id) < 4:
                        self.logger.error(f"No data chunk found in WAV file: {file_path}")
                        return False

                    size_bytes = f.read(4)
                    if not size_bytes or len(size_bytes) < 4:
                        self.logger.error(f"Truncated data chunk size in WAV file: {file_path}")
                        return False
                    chunk_size = struct.unpack('<I', size_bytes)[0]

                    if chunk_id == b'data':
                        # Validate data size is reasonable
                        if chunk_size == 0:
                            self.logger.error(f"Empty data chunk in WAV file: {file_path}")
                            return False
                        if chunk_size > 100 * 1024 * 1024:  # 100MB limit
                            self.logger.error(f"Data chunk too large ({chunk_size} bytes) in WAV file: {file_path}")
                            return False

                        # Read audio data
                        audio_data = f.read(chunk_size)
                        if len(audio_data) < chunk_size:
                            self.logger.warning(f"Truncated audio data in WAV file: {file_path} "
                                              f"(expected {chunk_size}, got {len(audio_data)})")
                            # Continue with partial data rather than failing completely

                        # For mono files, use data as-is
                        # For stereo, we'd need to downmix (take left channel)
                        if num_channels == 2:
                            self.logger.warning(f"Stereo audio detected, extracting left channel only")
                            # Extract left channel (assuming interleaved samples)
                            if audio_format == WAV_FORMAT_PCM:  # PCM 16-bit
                                # Extract every other 16-bit sample (left channel)
                                # More efficient using slice with step
                                audio_data = audio_data[::4] + audio_data[1::4]
                            else:  # 8-bit formats (G.711, G.722)
                                audio_data = audio_data[::2]

                        # Convert PCM to PCMU if needed
                        if convert_to_pcmu:
                            try:
                                from pbx.utils.audio import pcm16_to_ulaw
                                original_size = len(audio_data)
                                
                                # First, downsample from 16kHz to 8kHz if needed
                                if sample_rate == 16000:
                                    # Simple decimation: take every other sample
                                    downsampled = bytearray()
                                    for i in range(0, len(audio_data), 4):  # Skip every other 16-bit sample
                                        if i + 1 < len(audio_data):
                                            downsampled.extend(audio_data[i:i+2])
                                    audio_data = bytes(downsampled)
                                    sample_rate = 8000
                                    self.logger.info(f"Downsampled from 16kHz to 8kHz: {original_size} bytes -> {len(audio_data)} bytes")
                                
                                # Convert to μ-law
                                audio_data = pcm16_to_ulaw(audio_data)
                                self.logger.info(f"Converted PCM to PCMU: {len(audio_data)} bytes (μ-law)")
                            except Exception as e:
                                self.logger.error(f"Failed to convert PCM to PCMU: {e}")
                                return False
                        elif payload_type == 9:
                            # G.722 format - already encoded, ensure correct sample rate for packets
                            # G.722 uses 8kHz clock rate but actual 16kHz sampling
                            sample_rate = 16000

                        # Calculate samples per packet based on sample rate
                        # 20ms packet = sample_rate * 0.02
                        samples_per_packet = int(sample_rate * 0.02)

                        # Send the audio
                        self.logger.info(f"Playing audio file: {file_path} ({len(audio_data)} bytes)")
                        return self.send_audio(audio_data, payload_type, samples_per_packet)

                    else:
                        # Skip this chunk (with size validation)
                        if chunk_size > 100 * 1024 * 1024:  # 100MB limit
                            self.logger.error(f"Chunk size too large ({chunk_size} bytes) in WAV file: {file_path}")
                            return False
                        f.read(chunk_size)

        except Exception as e:
            self.logger.error(f"Error playing audio file {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return False


class RTPDTMFListener:
    """
    RTP DTMF Listener - Receives RTP audio and detects DTMF tones
    Used for interactive voice response (IVR) and auto attendant systems
    """

    def __init__(self, local_port, call_id=None):
        """
        Initialize RTP DTMF listener

        Args:
            local_port: Local UDP port to receive RTP packets
            call_id: Optional call identifier for logging
        """
        self.local_port = local_port
        self.call_id = call_id or "unknown"
        self.logger = get_logger()
        self.socket = None
        self.running = False
        self.detected_digits = []
        self.lock = threading.Lock()
        self.audio_buffer = []
        self.sample_rate = 8000  # Standard for telephony
        
        # DTMF detection frame sizes (based on DTMFDetector default of 205 samples per frame)
        # We need ~2x frame size for reliable detection with overlap
        self.dtmf_frame_size = 205  # Samples per DTMF detection frame
        self.dtmf_buffer_size = 410  # Buffer size for detection (2x frame size)
        self.dtmf_slide_size = 205   # Sliding window size
        
        # Initialize DTMF detector
        from pbx.utils.dtmf import DTMFDetector
        self.dtmf_detector = DTMFDetector(sample_rate=self.sample_rate)

    def start(self):
        """Start RTP DTMF listener"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces (0.0.0.0) to allow RTP from any network adapter
            # This is intentional for VoIP systems which need to handle multi-homed servers
            self.socket.bind(('0.0.0.0', self.local_port))
            self.socket.settimeout(0.1)  # 100ms timeout for recv
            self.running = True

            self.logger.info(f"RTP DTMF listener started on port {self.local_port} for call {self.call_id}")

            # Start listening thread
            listen_thread = threading.Thread(target=self._listen_loop)
            listen_thread.daemon = True
            listen_thread.start()

            return True
        except Exception as e:
            self.logger.error(f"Failed to start RTP DTMF listener: {e}")
            return False

    def stop(self):
        """Stop RTP DTMF listener"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except (OSError, socket.error) as e:
                self.logger.debug(f"Error closing socket: {e}")
            self.socket = None
        self.logger.info(f"RTP DTMF listener stopped for call {self.call_id}")

    def _listen_loop(self):
        """Listen for RTP packets and detect DTMF tones"""
        import time
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)

                # Extract audio payload from RTP packet
                if len(data) >= 12:
                    # Parse RTP header
                    header = struct.unpack('!BBHII', data[:12])
                    payload_type = header[1] & 0x7F
                    payload = data[12:]

                    # Convert audio payload to samples for DTMF detection
                    # Assuming G.711 μ-law (payload type 0) or A-law (payload type 8)
                    if payload_type in [0, 8]:
                        # Convert G.711 to linear PCM samples
                        samples = self._decode_g711(payload, payload_type)
                        
                        with self.lock:
                            self.audio_buffer.extend(samples)
                            
                            # Process buffer when we have enough samples
                            if len(self.audio_buffer) >= self.dtmf_buffer_size:
                                # Try to detect DTMF tone
                                digit = self.dtmf_detector.detect_tone(self.audio_buffer[:self.dtmf_buffer_size])
                                
                                if digit:
                                    # Check if this is a new digit (not a repeat)
                                    if not self.detected_digits or self.detected_digits[-1] != digit:
                                        self.detected_digits.append(digit)
                                        self.logger.info(f"DTMF digit detected: {digit}")
                                
                                # Keep a sliding window of audio
                                self.audio_buffer = self.audio_buffer[self.dtmf_slide_size:]

            except socket.timeout:
                # Timeout is normal, just continue
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in RTP DTMF listen loop: {e}")

    def _decode_g711(self, payload, payload_type):
        """
        Decode G.711 audio to linear PCM samples

        Args:
            payload: G.711 encoded audio bytes
            payload_type: 0 for μ-law, 8 for A-law

        Returns:
            list: Linear PCM samples normalized to [-1.0, 1.0]
        """
        samples = []
        
        for byte in payload:
            if payload_type == 0:  # μ-law
                # Simplified μ-law decode
                sample = self._ulaw_to_linear(byte)
            else:  # A-law (payload_type == 8)
                # Simplified A-law decode
                sample = self._alaw_to_linear(byte)
            
            # Normalize to [-1.0, 1.0]
            samples.append(sample / 32768.0)
        
        return samples

    def _ulaw_to_linear(self, ulaw_byte):
        """
        Convert μ-law byte to linear PCM sample

        Args:
            ulaw_byte: μ-law encoded byte

        Returns:
            int: Linear PCM sample (-32768 to 32767)
        """
        # μ-law decompression algorithm (ITU-T G.711)
        ulaw_byte = ~ulaw_byte & 0xFF
        sign = (ulaw_byte & 0x80) >> 7
        exponent = (ulaw_byte & 0x70) >> 4
        mantissa = ulaw_byte & 0x0F
        
        # Calculate linear value
        # 0x84 (132) is the bias value added to mantissa in μ-law encoding
        linear = ((mantissa << 3) + 0x84) << exponent
        
        if sign:
            return -linear
        else:
            return linear

    def _alaw_to_linear(self, alaw_byte):
        """
        Convert A-law byte to linear PCM sample

        Args:
            alaw_byte: A-law encoded byte

        Returns:
            int: Linear PCM sample (-32768 to 32767)
        """
        # A-law decompression algorithm (ITU-T G.711)
        alaw_byte ^= 0x55  # XOR with 0x55 per A-law spec
        sign = (alaw_byte & 0x80) >> 7
        exponent = (alaw_byte & 0x70) >> 4
        mantissa = alaw_byte & 0x0F
        
        if exponent == 0:
            linear = (mantissa << 4) + 8
        else:
            # 0x108 (264) is the bias for non-zero exponents in A-law encoding
            linear = ((mantissa << 4) + 0x108) << (exponent - 1)
        
        if sign:
            return -linear
        else:
            return linear

    def get_digit(self, timeout=1.0):
        """
        Get the next detected DTMF digit

        Args:
            timeout: Maximum time to wait for a digit (seconds)

        Returns:
            str: Detected digit ('0'-'9', '*', '#', 'A'-'D') or None
        """
        import time
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            with self.lock:
                if self.detected_digits:
                    return self.detected_digits.pop(0)
            
            # Small delay to avoid busy waiting
            time.sleep(0.05)
        
        return None

    def clear_digits(self):
        """Clear all detected digits from the buffer"""
        with self.lock:
            self.detected_digits.clear()
