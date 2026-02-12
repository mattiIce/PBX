#!/usr/bin/env python3
"""
Simple SIP client example for testing PBX
This demonstrates how to register an extension and make calls
"""
import socket
import time

from pbx.sip.message import SIPMessageBuilder


class SimpleSIPClient:
    """Simple SIP client for testing"""

    def __init__(self, extension, password, server_host="127.0.0.1", server_port=5060):
        """
        Initialize SIP client

        Args:
            extension: Extension number
            password: Extension password
            server_host: PBX server host
            server_port: PBX server port
        """
        self.extension = extension
        self.password = password
        self.server_host = server_host
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", 0))  # Bind to any available port
        self.local_port = self.socket.getsockname()[1]
        self.call_id = 0
        self.cseq = 0

    def register(self):
        """Register extension with PBX"""
        print(f"Registering extension {self.extension}...")

        self.cseq += 1
        from_addr = f'"Extension {self.extension}" <sip:{self.extension}@{self.server_host}>'
        to_addr = from_addr

        # Build REGISTER request
        request = SIPMessageBuilder.build_request(
            method="REGISTER",
            uri=f"sip:{self.server_host}",
            from_addr=from_addr,
            to_addr=to_addr,
            call_id=f"register-{self.extension}-{int(time.time())}",
            cseq=self.cseq,
        )

        request.set_header("Contact", f"<sip:{self.extension}@127.0.0.1:{self.local_port}>")
        request.set_header("Expires", "3600")

        # Send request
        self.socket.sendto(request.build().encode("utf-8"), (self.server_host, self.server_port))

        # Wait for response
        try:
            self.socket.settimeout(5)
            data, addr = self.socket.recvfrom(4096)
            response = data.decode("utf-8")

            if "200 OK" in response:
                print(f"✓ Extension {self.extension} registered successfully")
                return True
            else:
                first_line = response.split('\r\n')[0]
                print(f"✗ Registration failed: {first_line}")
                return False
        except socket.timeout:
            print("✗ Registration timeout")
            return False

    def call(self, destination):
        """
        Make call to destination

        Args:
            destination: Destination extension number
        """
        print(f"Calling extension {destination}...")

        self.call_id += 1
        self.cseq += 1

        from_addr = f'"Extension {self.extension}" <sip:{self.extension}@{self.server_host}>'
        to_addr = f"<sip:{destination}@{self.server_host}>"

        # Build INVITE request
        request = SIPMessageBuilder.build_request(
            method="INVITE",
            uri=f"sip:{destination}@{self.server_host}",
            from_addr=from_addr,
            to_addr=to_addr,
            call_id=f"call-{self.extension}-{self.call_id}",
            cseq=self.cseq,
        )

        request.set_header("Contact", f"<sip:{self.extension}@127.0.0.1:{self.local_port}>")

        # Send request
        self.socket.sendto(request.build().encode("utf-8"), (self.server_host, self.server_port))

        print(f"✓ Call initiated to {destination}")

    def close(self):
        """Close client socket"""
        self.socket.close()


def main():
    """Example usage"""
    print("Simple SIP Client Test")
    print("=" * 40)

    # Create client for extension 1001
    client = SimpleSIPClient("1001", "password1001")

    # Register
    if client.register():
        # Wait a moment
        time.sleep(1)

        # Make a test call to extension 1002
        client.call("1002")

        # Wait before closing
        time.sleep(2)

    client.close()
    print("\nClient closed")


if __name__ == "__main__":
    main()
