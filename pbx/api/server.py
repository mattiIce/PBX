"""Flask-based API server for PBX with HTTPS support.

Replaces the legacy BaseHTTPRequestHandler-based server with Flask.
"""

import os
import ssl
import socket
import threading
import time
import traceback

from pbx.api.app import create_app
from pbx.utils.logger import get_logger

logger = get_logger()


class PBXFlaskServer:
    """REST API server for PBX using Flask with HTTPS support."""

    def __init__(
        self,
        pbx_core,
        host: str = "0.0.0.0",  # nosec B104 - PBX API needs to bind all interfaces
        port: int = 9000,
    ) -> None:
        """Initialize Flask API server.

        Args:
            pbx_core: PBXCore instance
            host: Host to bind to
            port: Port to bind to
        """
        self.pbx_core = pbx_core
        self.host = host
        self.port = port
        self.server_thread: threading.Thread | None = None
        self.running = False
        self.ssl_enabled = False
        self.ssl_context: ssl.SSLContext | None = None

        # Create Flask app
        self.app = create_app(pbx_core)

        # Configure SSL/TLS if enabled
        self._configure_ssl()

    def _configure_ssl(self) -> None:
        """Configure SSL context if SSL is enabled in config."""
        ssl_config = self.pbx_core.config.get("api.ssl", {})
        ssl_enabled = ssl_config.get("enabled", False)

        if not ssl_enabled:
            logger.info("SSL/HTTPS is disabled - using HTTP")
            return

        cert_file = ssl_config.get("cert_file")
        key_file = ssl_config.get("key_file")

        ca_config = ssl_config.get("ca", {})
        ca_enabled = ca_config.get("enabled", False)

        if ca_enabled and (not cert_file or not os.path.exists(cert_file)):
            logger.info("Certificate not found, attempting to request from in-house CA")
            self._request_certificate_from_ca(ca_config, cert_file, key_file)

        if not cert_file or not key_file:
            logger.error("SSL is enabled but cert_file or key_file not configured")
            logger.error("Set api.ssl.enabled: false in config.yml to disable SSL")
            return

        if not os.path.exists(cert_file):
            logger.error(f"SSL certificate file not found: {cert_file}")
            return

        if not os.path.exists(key_file):
            logger.error(f"SSL private key file not found: {key_file}")
            return

        try:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(cert_file, key_file)

            ca_cert = ca_config.get("ca_cert")
            if ca_cert and os.path.exists(ca_cert):
                self.ssl_context.load_verify_locations(cafile=ca_cert)

            self.ssl_context.set_ciphers("HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4")
            self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.ssl_context.options |= ssl.OP_NO_SSLv2
            self.ssl_context.options |= ssl.OP_NO_SSLv3
            self.ssl_context.options |= ssl.OP_NO_TLSv1
            self.ssl_context.options |= ssl.OP_NO_TLSv1_1

            self.ssl_enabled = True
            logger.info(f"SSL/HTTPS enabled with certificate: {cert_file}")
        except Exception as e:
            logger.error(f"Failed to configure SSL: {e}")
            traceback.print_exc()

    def _request_certificate_from_ca(self, ca_config, cert_file, key_file):
        """Request certificate from in-house CA."""
        try:
            import requests
            ca_url = ca_config.get("url")
            ca_token = ca_config.get("token")
            hostname = ca_config.get("hostname", socket.gethostname())

            if not ca_url:
                logger.error("CA URL not configured")
                return False

            response = requests.post(
                f"{ca_url}/api/certificate/request",
                json={"hostname": hostname, "type": "server"},
                headers={"Authorization": f"Bearer {ca_token}"} if ca_token else {},
                timeout=30,
                verify=ca_config.get("verify_ssl", True)
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("certificate") and data.get("private_key"):
                    os.makedirs(os.path.dirname(cert_file), exist_ok=True)
                    with open(cert_file, "w") as f:
                        f.write(data["certificate"])
                    with open(key_file, "w") as f:
                        f.write(data["private_key"])
                    os.chmod(key_file, 0o600)
                    logger.info(f"Certificate obtained from CA: {cert_file}")
                    return True

            logger.error(f"CA certificate request failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error requesting certificate from CA: {e}")
            return False

    def start(self) -> bool:
        """Start the Flask API server."""
        try:
            self.running = True
            protocol = "https" if self.ssl_enabled else "http"
            logger.info(f"API server starting on {protocol}://{self.host}:{self.port}")

            self.server_thread = threading.Thread(target=self._run, daemon=True)
            self.server_thread.start()

            return True
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            traceback.print_exc()
            self.running = False
            return False

    def _run(self) -> None:
        """Run Flask server in thread."""
        try:
            ssl_ctx = self.ssl_context if self.ssl_enabled else None
            debug = os.environ.get("FLASK_DEBUG", "0") == "1"
            self.app.run(
                host=self.host,
                port=self.port,
                ssl_context=ssl_ctx,
                threaded=True,
                use_reloader=debug,
                debug=debug,
            )
        except Exception as e:
            if self.running:
                logger.error(f"Flask server error: {e}")

    def stop(self) -> None:
        """Stop API server."""
        self.running = False

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
            if self.server_thread.is_alive():
                logger.warning("API server thread did not stop cleanly")

        self.server_thread = None
        logger.info("API server stopped")
