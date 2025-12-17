"""
SDP (Session Description Protocol) Parser and Builder
Used for media negotiation in SIP calls
"""


class SDPSession:
    """Represents an SDP session description"""

    def __init__(self):
        """Initialize SDP session"""
        self.version = 0
        self.origin = {}  # username, session_id, version, network_type, address_type, address
        self.session_name = "-"
        self.connection = {}  # network_type, address_type, address
        self.media = []  # List of media descriptions

    def parse(self, sdp_body):
        """
        Parse SDP body

        Args:
            sdp_body: SDP body as string
        """
        lines = sdp_body.strip().split('\n')
        current_media = None

        for line in lines:
            line = line.strip()
            if not line or '=' not in line:
                continue

            type_char = line[0]
            value = line[2:].strip()

            if type_char == 'v':
                # Version
                self.version = int(value)

            elif type_char == 'o':
                # Origin
                parts = value.split()
                if len(parts) >= 6:
                    self.origin = {
                        'username': parts[0],
                        'session_id': parts[1],
                        'version': parts[2],
                        'network_type': parts[3],
                        'address_type': parts[4],
                        'address': parts[5]
                    }

            elif type_char == 's':
                # Session name
                self.session_name = value

            elif type_char == 'c':
                # Connection information
                parts = value.split()
                if len(parts) >= 3:
                    connection = {
                        'network_type': parts[0],
                        'address_type': parts[1],
                        'address': parts[2]
                    }
                    if current_media:
                        current_media['connection'] = connection
                    else:
                        self.connection = connection

            elif type_char == 'm':
                # Media description
                parts = value.split()
                if len(parts) >= 4:
                    current_media = {
                        'type': parts[0],  # audio, video, etc.
                        'port': int(parts[1]),
                        'protocol': parts[2],
                        'formats': parts[3:],  # Payload types
                        'attributes': []
                    }
                    self.media.append(current_media)

            elif type_char == 'a' and current_media:
                # Attribute (associated with current media)
                current_media['attributes'].append(value)

    def get_audio_info(self):
        """
        Get audio media information

        Returns:
            Dictionary with audio info or None
        """
        for media in self.media:
            if media['type'] == 'audio':
                # Get connection info (prefer media-level, fallback to
                # session-level)
                connection = media.get('connection', self.connection)

                return {
                    'address': connection.get('address'),
                    'port': media['port'],
                    'formats': media['formats']
                }
        return None

    def build(self):
        """
        Build SDP string

        Returns:
            SDP body as string
        """
        lines = []

        # Version
        lines.append(f"v={self.version}")

        # Origin
        if self.origin:
            o = self.origin
            lines.append(
                f"o={
                    o['username']} {
                    o['session_id']} {
                    o['version']} " f"{
                    o['network_type']} {
                        o['address_type']} {
                            o['address']}")

        # Session name
        lines.append(f"s={self.session_name}")

        # Connection (session-level)
        if self.connection:
            c = self.connection
            lines.append(
                f"c={
                    c['network_type']} {
                    c['address_type']} {
                    c['address']}")

        # Time (required by SDP spec)
        lines.append("t=0 0")

        # Media descriptions
        for media in self.media:
            # Media line
            formats = ' '.join(media['formats'])
            lines.append(
                f"m={
                    media['type']} {
                    media['port']} {
                    media['protocol']} {formats}")

            # Media-level connection
            if 'connection' in media:
                c = media['connection']
                lines.append(
                    f"c={
                        c['network_type']} {
                        c['address_type']} {
                        c['address']}")

            # Attributes
            for attr in media.get('attributes', []):
                lines.append(f"a={attr}")

        return '\r\n'.join(lines) + '\r\n'


class SDPBuilder:
    """Helper to build SDP messages"""

    @staticmethod
    def build_audio_sdp(local_ip, local_port, session_id="0", codecs=None, dtmf_payload_type=101):
        """
        Build SDP for audio call

        Args:
            local_ip: Local IP address for RTP
            local_port: Local RTP port
            session_id: Session ID (can be timestamp)
            codecs: List of codec payload types to offer (default: ['0', '8', '9', '18', '2', '101'])
                   When negotiating with a caller, pass their offered codecs to maintain compatibility
                   Standard payload types: 0=PCMU, 8=PCMA, 9=G722, 18=G729, 2=G726-32
            dtmf_payload_type: Payload type for RFC2833 telephone-event (default: 101)
                   Can be configured to use alternative payload types (96-127) if needed

        Returns:
            SDP body as string
        """
        if codecs is None:
            # Default codec order: PCMU, PCMA, G722, G729, G726-32, telephone-event
            # Use configured dtmf_payload_type for telephone-event codec
            codecs = ['0', '8', '9', '18', '2', str(dtmf_payload_type)]

        sdp = SDPSession()
        sdp.version = 0
        sdp.origin = {
            'username': 'pbx',
            'session_id': session_id,
            'version': '0',
            'network_type': 'IN',
            'address_type': 'IP4',
            'address': local_ip
        }
        sdp.session_name = "PBX Call"
        sdp.connection = {
            'network_type': 'IN',
            'address_type': 'IP4',
            'address': local_ip
        }

        # Build attributes dynamically based on codecs
        attributes = []

        # Add rtpmap for each codec
        if '0' in codecs:
            attributes.append('rtpmap:0 PCMU/8000')
        if '8' in codecs:
            attributes.append('rtpmap:8 PCMA/8000')
        if '9' in codecs:
            # G.722 uses 8000 in SDP even though actual rate is 16000 (RFC 3551
            # quirk)
            attributes.append('rtpmap:9 G722/8000')
        if '18' in codecs:
            # G.729 (8 kbit/s low-bitrate codec)
            attributes.append('rtpmap:18 G729/8000')
            # Optionally disable Annex B (VAD/CNG) if needed
            # attributes.append('fmtp:18 annexb=no')
        if '2' in codecs:
            # G.726-32 (also known as G721) - 32 kbit/s ADPCM
            attributes.append('rtpmap:2 G726-32/8000')
        
        # Support for G.726 variants with dynamic payload types
        # G.726-40 (typically uses dynamic PT 114)
        if '114' in codecs:
            attributes.append('rtpmap:114 G726-40/8000')
        # G.726-24 (typically uses dynamic PT 113)
        if '113' in codecs:
            attributes.append('rtpmap:113 G726-24/8000')
        # G.726-16 (typically uses dynamic PT 112)
        if '112' in codecs:
            attributes.append('rtpmap:112 G726-16/8000')
        
        # iLBC - Internet Low Bitrate Codec (dynamic PT)
        # Note: Check config for actual payload type, default to 97 if iLBC enabled
        # If both iLBC and Speex narrowband are enabled, ensure distinct payload types
        if '97' in codecs:
            attributes.append('rtpmap:97 iLBC/8000')
            # Default to 30ms mode (13.33 kbps)
            # TODO: Read mode from config
            attributes.append('fmtp:97 mode=30')
        
        # Speex - Open source speech codec (dynamic PT)
        # Use distinct payload types for each bandwidth mode
        # PT 98 for narrowband, PT 99 for wideband, PT 100 for ultra-wideband
        if '98' in codecs:
            # Speex narrowband (8kHz)
            attributes.append('rtpmap:98 SPEEX/8000')
        if '99' in codecs:
            # Speex wideband (16kHz)
            attributes.append('rtpmap:99 SPEEX/16000')
            attributes.append('fmtp:99 vbr=on;mode="1,any"')
        if '100' in codecs:
            # Speex ultra-wideband (32kHz)
            attributes.append('rtpmap:100 SPEEX/32000')
            attributes.append('fmtp:100 vbr=on;mode="2,any"')
        
        # Support configurable DTMF payload type (not just hardcoded 101)
        dtmf_pt_str = str(dtmf_payload_type)
        if dtmf_pt_str in codecs:
            attributes.append(f'rtpmap:{dtmf_pt_str} telephone-event/8000')
            attributes.append(f'fmtp:{dtmf_pt_str} 0-16')

        attributes.append('sendrecv')

        # Add audio media
        media = {
            'type': 'audio',
            'port': local_port,
            'protocol': 'RTP/AVP',
            'formats': codecs,
            'attributes': attributes
        }
        sdp.media.append(media)

        return sdp.build()
