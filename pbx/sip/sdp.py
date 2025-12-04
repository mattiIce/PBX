"""
SDP (Session Description Protocol) Parser and Builder
Used for media negotiation in SIP calls
"""
import re


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
                # Get connection info (prefer media-level, fallback to session-level)
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
            lines.append(f"o={o['username']} {o['session_id']} {o['version']} "
                        f"{o['network_type']} {o['address_type']} {o['address']}")

        # Session name
        lines.append(f"s={self.session_name}")

        # Connection (session-level)
        if self.connection:
            c = self.connection
            lines.append(f"c={c['network_type']} {c['address_type']} {c['address']}")

        # Time (required by SDP spec)
        lines.append("t=0 0")

        # Media descriptions
        for media in self.media:
            # Media line
            formats = ' '.join(media['formats'])
            lines.append(f"m={media['type']} {media['port']} {media['protocol']} {formats}")

            # Media-level connection
            if 'connection' in media:
                c = media['connection']
                lines.append(f"c={c['network_type']} {c['address_type']} {c['address']}")

            # Attributes
            for attr in media.get('attributes', []):
                lines.append(f"a={attr}")

        return '\r\n'.join(lines) + '\r\n'


class SDPBuilder:
    """Helper to build SDP messages"""

    @staticmethod
    def build_audio_sdp(local_ip, local_port, session_id="0", codecs=None):
        """
        Build SDP for audio call

        Args:
            local_ip: Local IP address for RTP
            local_port: Local RTP port
            session_id: Session ID (can be timestamp)
            codecs: List of codec payload types (default: ['0', '8', '101'])

        Returns:
            SDP body as string
        """
        if codecs is None:
            codecs = ['0', '8', '101']  # PCMU, PCMA, telephone-event

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

        # Add audio media
        media = {
            'type': 'audio',
            'port': local_port,
            'protocol': 'RTP/AVP',
            'formats': codecs,
            'attributes': [
                'rtpmap:0 PCMU/8000',
                'rtpmap:8 PCMA/8000',
                'rtpmap:101 telephone-event/8000',
                'fmtp:101 0-16',
                'sendrecv'
            ]
        }
        sdp.media.append(media)

        return sdp.build()
