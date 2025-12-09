"""
SIP Message Parser and Builder
"""


class SIPMessage:
    """Represents a SIP message"""

    def __init__(self, raw_message=None):
        """
        Initialize SIP message

        Args:
            raw_message: Raw SIP message string
        """
        self.method = None
        self.uri = None
        self.version = "SIP/2.0"
        self.status_code = None
        self.status_text = None
        self.headers = {}
        self.body = ""

        if raw_message:
            self.parse(raw_message)

    def parse(self, raw_message):
        """
        Parse raw SIP message

        Args:
            raw_message: Raw SIP message string
        """
        lines = raw_message.split('\r\n')

        # Validate that we have at least one line
        if not lines or len(lines) == 0:
            return

        # Parse first line (request or response)
        first_line = lines[0]
        if first_line.startswith('SIP/'):
            # Response
            parts = first_line.split(' ', 2)
            if len(parts) >= 2:
                self.version = parts[0]
                try:
                    self.status_code = int(parts[1])
                except ValueError:
                    # Invalid status code, skip parsing
                    return
                self.status_text = parts[2] if len(parts) > 2 else ""
            else:
                # Malformed response line
                return
        else:
            # Request
            parts = first_line.split(' ')
            if len(parts) >= 2:
                self.method = parts[0]
                self.uri = parts[1]
                self.version = parts[2] if len(parts) > 2 else "SIP/2.0"
            else:
                # Malformed request line
                return

        # Parse headers
        body_start = None
        for i, line in enumerate(lines[1:], 1):
            if line == '':
                body_start = i + 1
                break

            if ':' in line:
                key, value = line.split(':', 1)
                self.headers[key.strip()] = value.strip()

        # Parse body
        if body_start and body_start < len(lines):
            self.body = '\r\n'.join(lines[body_start:])

    def get_header(self, name):
        """Get header value"""
        return self.headers.get(name)

    def set_header(self, name, value):
        """Set header value"""
        self.headers[name] = value

    def is_request(self):
        """Check if message is a request"""
        return self.method is not None

    def is_response(self):
        """Check if message is a response"""
        return self.status_code is not None

    def build(self):
        """
        Build SIP message string

        Returns:
            Raw SIP message string
        """
        lines = []

        # First line
        if self.is_request():
            lines.append(f"{self.method} {self.uri} {self.version}")
        else:
            lines.append(f"{self.version} {self.status_code} {self.status_text}")

        # Headers
        for key, value in self.headers.items():
            lines.append(f"{key}: {value}")

        # Empty line before body
        lines.append('')

        # Body
        if self.body:
            lines.append(self.body)

        return '\r\n'.join(lines)

    def __str__(self):
        return self.build()


class SIPMessageBuilder:
    """Helper to build SIP messages"""

    @staticmethod
    def build_response(status_code, status_text, request_msg, body=""):
        """
        Build SIP response

        Args:
            status_code: HTTP-style status code
            status_text: Status text
            request_msg: Original request message
            body: Optional message body

        Returns:
            SIPMessage response
        """
        response = SIPMessage()
        response.status_code = status_code
        response.status_text = status_text

        # Copy relevant headers from request
        for header in ['Via', 'From', 'To', 'Call-ID', 'CSeq']:
            if request_msg.get_header(header):
                response.set_header(header, request_msg.get_header(header))

        if body:
            response.body = body
            response.set_header('Content-Length', str(len(body)))
        else:
            response.set_header('Content-Length', '0')

        return response

    @staticmethod
    def build_request(method, uri, from_addr, to_addr, call_id, cseq, body=""):
        """
        Build SIP request

        Args:
            method: SIP method (INVITE, REGISTER, etc.)
            uri: Request URI
            from_addr: From address
            to_addr: To address
            call_id: Call ID
            cseq: CSeq value
            body: Optional message body

        Returns:
            SIPMessage request
        """
        request = SIPMessage()
        request.method = method
        request.uri = uri

        request.set_header('From', from_addr)
        request.set_header('To', to_addr)
        request.set_header('Call-ID', call_id)
        request.set_header('CSeq', f"{cseq} {method}")

        if body:
            request.body = body
            request.set_header('Content-Length', str(len(body)))
        else:
            request.set_header('Content-Length', '0')

        return request
