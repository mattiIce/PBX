"""
REST API Server for PBX Management
Provides HTTP/HTTPS API for managing PBX features
"""

import base64
import binascii
import errno
import ipaddress
import json
import mimetypes
import os
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import traceback
import zipfile
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

from pbx.features.phone_provisioning import normalize_mac_address
from pbx.utils.config import Config
from pbx.utils.logger import get_logger
from pbx.utils.tts import get_tts_requirements, is_tts_available, text_to_wav_telephony

# Constants
DEFAULT_WEBRTC_EXTENSION = "webrtc-admin"  # Default extension for WebRTC browser phone

# Optional imports for SSL certificate generation
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    SSL_GENERATION_AVAILABLE = True
except ImportError:
    SSL_GENERATION_AVAILABLE = False

# Admin directory path
ADMIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "admin")

# MAC address placeholders that indicate misconfiguration
# These are literal strings that appear in URLs when phones are misconfigured
# Note: $mac and $MA are CORRECT variables that phones should use - they should NOT be in this list
# Only include literal placeholders like {mac} that indicate the phone
# didn't substitute its actual MAC
MAC_ADDRESS_PLACEHOLDERS = ["{mac}", "{MAC}", "{Ma}"]


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class PBXAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for PBX API"""

    pbx_core = None  # Set by PBXAPIServer
    logger = get_logger()  # Initialize logger for handler
    _integration_endpoints = None  # Cache for integration endpoints
    _health_checker = None  # Production health checker instance

    def _get_integration_endpoints(self):
        """Get integration endpoints (cached)"""
        if PBXAPIHandler._integration_endpoints is None:
            from pbx.api.opensource_integration_api import add_opensource_integration_endpoints

            PBXAPIHandler._integration_endpoints = add_opensource_integration_endpoints(self)
        return PBXAPIHandler._integration_endpoints

    def _check_integration_available(self, integration_name):
        """Check if integration is available and enabled"""
        if not self.pbx_core:
            return False, "PBX core not available"

        attr_name = f"{integration_name}_integration"
        if not hasattr(self.pbx_core, attr_name):
            return False, f"{integration_name.capitalize()} integration not available"

        integration = getattr(self.pbx_core, attr_name)
        if not integration or not integration.enabled:
            return False, f"{integration_name.capitalize()} integration not enabled"

        return True, None

    def _set_headers(self, status=200, content_type="application/json"):
        """Set response headers with security enhancements"""
        self.send_response(status)
        self.send_header("Content-type", content_type)

        # CORS headers
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

        # Security headers
        # X-Content-Type-Options: Prevent MIME type sniffing
        self.send_header("X-Content-Type-Options", "nosniff")

        # X-Frame-Options: Prevent clickjacking
        self.send_header("X-Frame-Options", "DENY")

        # X-XSS-Protection: Enable XSS filter (for older browsers)
        self.send_header("X-XSS-Protection", "1; mode=block")

        # Strict-Transport-Security: Enforce HTTPS (when using HTTPS)
        # Note: Only add this when actually using HTTPS
        # self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

        # Content-Security-Policy: Restrict resource loading
        # Allow Chart.js from trusted CDNs for analytics visualization
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:;"
        )
        self.send_header("Content-Security-Policy", csp)

        # Referrer-Policy: Control referrer information
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

        # Permissions-Policy: Control browser features
        # Allow microphone for WebRTC phone functionality, block camera and
        # geolocation
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(self), camera=()")

        self.end_headers()

    def _send_json(self, data, status=200):
        """Send JSON response"""
        try:
            self._set_headers(status)
            self.wfile.write(json.dumps(data, cls=DateTimeEncoder).encode())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            # Client disconnected - log but don't try to send error response
            self.logger.warning(f"Client disconnected before response could be sent: {e}")
        except Exception as e:
            # Other errors during response sending
            self.logger.error(f"Error sending response: {e}")

    def _get_body(self):
        """Get request body"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        return {}

    def _get_provisioning_url_info(self):
        """
        Get provisioning URL information (protocol, server IP, port)

        Returns:
            tuple: (protocol, server_ip, port, base_url)
        """
        if not self.pbx_core:
            return "http", "192.168.1.14", 8080, "http://192.168.1.14:8080"

        # Note: Provisioning typically uses HTTP even when API uses HTTPS
        # because phones often cannot validate self-signed certificates
        ssl_enabled = self.pbx_core.config.get("api.ssl.enabled", False)
        protocol = "https" if ssl_enabled else "http"
        server_ip = self.pbx_core.config.get("server.external_ip", "192.168.1.14")
        port = self.pbx_core.config.get("api.port", 8080)
        base_url = f"{protocol}://{server_ip}:{port}"

        return protocol, server_ip, port, base_url

    def do_OPTIONS(self):
        """Handle OPTIONS for CORS"""
        self._set_headers(204)

    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        # Log all POST requests for debugging
        self.logger.debug(f"POST request received: {path}")

        try:
            if path == "/api/auth/login":
                self._handle_login()
            elif path == "/api/auth/logout":
                self._handle_logout()
            elif path == "/api/provisioning/devices":
                self._handle_register_device()
            elif path.startswith("/api/provisioning/templates/") and path.endswith("/export"):
                # /api/provisioning/templates/{vendor}/{model}/export
                parts = path.split("/")
                if len(parts) >= 7:
                    vendor = parts[4]
                    model = parts[5]
                    # Validate vendor and model to prevent path traversal
                    import re

                    if re.match(r"^[a-z0-9_-]+$", vendor.lower()) and re.match(
                        r"^[a-z0-9_-]+$", model.lower()
                    ):
                        self._handle_export_template(vendor, model)
                    else:
                        self._send_json({"error": "Invalid vendor or model name"}, 400)
                else:
                    self._send_json({"error": "Invalid path"}, 400)
            elif path == "/api/provisioning/reload-templates":
                self._handle_reload_templates()
            elif path.startswith("/api/provisioning/devices/") and "/static-ip" in path:
                # /api/provisioning/devices/{mac}/static-ip
                parts = path.split("/")
                if len(parts) >= 5:
                    mac = parts[4]
                    self._handle_set_static_ip(mac)
                else:
                    self._send_json({"error": "Invalid path"}, 400)
            elif path == "/api/extensions":
                self._handle_add_extension()
            elif path == "/api/phones/reboot":
                self._handle_reboot_phones()
            elif path.startswith("/api/phones/") and path.endswith("/reboot"):
                # Extract extension number: /api/phones/{extension}/reboot
                parts = path.split("/")
                if len(parts) >= 4:
                    extension = parts[3]
                    self._handle_reboot_phone(extension)
                else:
                    self._send_json({"error": "Invalid path"}, 400)
            elif path == "/api/integrations/ad/sync":
                self._handle_ad_sync()
            elif path == "/api/phone-book":
                self._handle_add_phone_book_entry()
            elif path == "/api/phone-book/sync":
                self._handle_sync_phone_book()
            elif path == "/api/paging/zones":
                self._handle_add_paging_zone()
            elif path == "/api/paging/devices":
                self._handle_configure_paging_device()
            elif path == "/api/webhooks":
                self._handle_add_webhook()
            elif path == "/api/webrtc/session":
                self._handle_create_webrtc_session()
            elif path == "/api/webrtc/phone-config":
                self._handle_set_webrtc_phone_config()
            elif path == "/api/webrtc/offer":
                self._handle_webrtc_offer()
            elif path == "/api/webrtc/answer":
                self._handle_webrtc_answer()
            elif path == "/api/webrtc/ice-candidate":
                self._handle_webrtc_ice_candidate()
            elif path == "/api/webrtc/call":
                self._handle_webrtc_call()
            elif path == "/api/webrtc/hangup":
                self._handle_webrtc_hangup()
            elif path == "/api/webrtc/dtmf":
                self._handle_webrtc_dtmf()
            elif path == "/api/emergency/contacts":
                self._handle_add_emergency_contact()
            elif path == "/api/emergency/trigger":
                self._handle_trigger_emergency_notification()
            elif path == "/api/hot-desk/login":
                self._handle_hot_desk_login()
            elif path == "/api/hot-desk/logout":
                self._handle_hot_desk_logout()
            elif path == "/api/mfa/enroll":
                self._handle_mfa_enroll()
            elif path == "/api/mfa/verify-enrollment":
                self._handle_mfa_verify_enrollment()
            elif path == "/api/mfa/verify":
                self._handle_mfa_verify()
            elif path == "/api/mfa/disable":
                self._handle_mfa_disable()
            elif path == "/api/mfa/enroll-yubikey":
                self._handle_mfa_enroll_yubikey()
            elif path == "/api/mfa/enroll-fido2":
                self._handle_mfa_enroll_fido2()
            elif path == "/api/security/block-ip":
                self._handle_block_ip()
            elif path == "/api/security/unblock-ip":
                self._handle_unblock_ip()
            elif path == "/api/dnd/rule":
                self._handle_add_dnd_rule()
            elif path == "/api/dnd/register-calendar":
                self._handle_register_calendar_user()
            elif path == "/api/dnd/override":
                self._handle_dnd_override()
            elif path == "/api/skills/skill":
                self._handle_add_skill()
            elif path == "/api/skills/assign":
                self._handle_assign_skill()
            elif path == "/api/skills/queue-requirements":
                self._handle_set_queue_requirements()
            elif path == "/api/qos/clear-alerts":
                self._handle_clear_qos_alerts()
            elif path == "/api/qos/thresholds":
                self._handle_update_qos_thresholds()
            elif path == "/api/auto-attendant/menu-options":
                self._handle_add_auto_attendant_menu_option()
            elif path.startswith("/api/voicemail-boxes/") and path.endswith("/export"):
                self._handle_export_voicemail_box(path)
            elif path == "/api/ssl/generate-certificate":
                self._handle_generate_ssl_certificate()
            elif path == "/api/sip-trunks":
                self._handle_add_sip_trunk()
            elif path == "/api/sip-trunks/test":
                self._handle_test_sip_trunk()
            elif path == "/api/lcr/rate":
                self._handle_add_lcr_rate()
            elif path == "/api/lcr/time-rate":
                self._handle_add_lcr_time_rate()
            elif path == "/api/lcr/clear-rates":
                self._handle_clear_lcr_rates()
            elif path == "/api/lcr/clear-time-rates":
                self._handle_clear_lcr_time_rates()
            elif path == "/api/fmfm/config":
                self._handle_set_fmfm_config()
            elif path == "/api/fmfm/destination":
                self._handle_add_fmfm_destination()
            elif path == "/api/time-routing/rule":
                self._handle_add_time_routing_rule()
            elif path == "/api/recording-retention/policy":
                self._handle_add_retention_policy()
            elif path == "/api/fraud-detection/blocked-pattern":
                self._handle_add_blocked_pattern()
            elif path == "/api/callback-queue/request":
                self._handle_request_callback()
            elif path == "/api/callback-queue/start":
                self._handle_start_callback()
            elif path == "/api/callback-queue/complete":
                self._handle_complete_callback()
            elif path == "/api/callback-queue/cancel":
                self._handle_cancel_callback()
            elif path == "/api/mobile-push/register":
                self._handle_register_device()
            elif path == "/api/mobile-push/unregister":
                self._handle_unregister_device()
            elif path == "/api/mobile-push/test":
                self._handle_test_push_notification()

            # Framework feature POST APIs
            elif path.startswith("/api/framework/speech-analytics/config/"):
                extension = path.split("/")[-1]
                self._handle_update_speech_analytics_config(extension)
            elif path.startswith("/api/framework/speech-analytics/analyze-sentiment"):
                self._handle_analyze_sentiment()
            elif path.startswith("/api/framework/speech-analytics/generate-summary/"):
                call_id = path.split("/")[-1]
                self._handle_generate_summary(call_id)
            elif path == "/api/framework/video-conference/create-room":
                self._handle_create_video_room()
            elif path.startswith("/api/framework/video-conference/join/"):
                room_id = path.split("/")[-1]
                self._handle_join_video_room(room_id)
            elif path.startswith("/api/framework/click-to-dial/call/"):
                extension = path.split("/")[-1]
                self._handle_click_to_dial_call(extension)
            elif path.startswith("/api/framework/click-to-dial/config/"):
                extension = path.split("/")[-1]
                self._handle_update_click_to_dial_config(extension)
            elif path == "/api/framework/team-messaging/create-channel":
                self._handle_create_team_channel()
            elif path == "/api/framework/team-messaging/send-message":
                self._handle_send_team_message()
            elif path.startswith("/api/framework/nomadic-e911/update-location/"):
                extension = path.split("/")[-1]
                self._handle_update_e911_location(extension)
            elif path.startswith("/api/framework/nomadic-e911/detect-location/"):
                extension = path.split("/")[-1]
                self._handle_detect_e911_location(extension)
            elif path == "/api/framework/nomadic-e911/create-site":
                self._handle_create_e911_site()
            elif path == "/api/framework/integrations/hubspot/config":
                self._handle_update_hubspot_config()
            elif path == "/api/framework/integrations/zendesk/config":
                self._handle_update_zendesk_config()
            elif path == "/api/framework/compliance/gdpr/consent":
                self._handle_record_gdpr_consent()
            elif path == "/api/framework/compliance/gdpr/withdraw":
                self._handle_withdraw_gdpr_consent()
            elif path == "/api/framework/compliance/gdpr/request":
                self._handle_create_gdpr_request()
            elif path == "/api/framework/compliance/soc2/control":
                self._handle_register_soc2_control()
            elif path == "/api/framework/compliance/pci/log":
                self._handle_log_pci_event()

            # BI Integration POST endpoints
            elif path == "/api/framework/bi-integration/export":
                self._handle_export_bi_dataset()
            elif path == "/api/framework/bi-integration/dataset":
                self._handle_create_bi_dataset()
            elif path == "/api/framework/bi-integration/test-connection":
                self._handle_test_bi_connection()

            # Call Tagging POST endpoints
            elif path == "/api/framework/call-tagging/tag":
                self._handle_create_call_tag()
            elif path == "/api/framework/call-tagging/rule":
                self._handle_create_tagging_rule()
            elif path.startswith("/api/framework/call-tagging/classify/"):
                call_id = path.split("/")[-1]
                self._handle_classify_call(call_id)

            # Call Blending POST endpoints
            elif path == "/api/framework/call-blending/agent":
                self._handle_register_blending_agent()
            elif path.startswith("/api/framework/call-blending/agent/"):
                agent_id = path.split("/")[-1]
                if path.endswith("/mode"):
                    self._handle_set_agent_mode(agent_id)
                else:
                    self._send_json({"error": "Not found"}, 404)

            # Geographic Redundancy POST endpoints
            elif path == "/api/framework/geo-redundancy/region":
                self._handle_create_geo_region()
            elif path.startswith("/api/framework/geo-redundancy/region/"):
                region_id = path.split("/")[-1]
                if path.endswith("/failover"):
                    self._handle_trigger_geo_failover(region_id)
                else:
                    self._send_json({"error": "Not found"}, 404)

            # Conversational AI POST endpoints
            elif path == "/api/framework/conversational-ai/conversation":
                self._handle_start_ai_conversation()
            elif path == "/api/framework/conversational-ai/process":
                self._handle_process_ai_input()
            elif path == "/api/framework/conversational-ai/config":
                self._handle_configure_ai_provider()

            # Predictive Dialing POST endpoints
            elif path == "/api/framework/predictive-dialing/campaign":
                self._handle_create_dialing_campaign()
            elif path == "/api/framework/predictive-dialing/contacts":
                self._handle_add_campaign_contacts()
            elif path.startswith("/api/framework/predictive-dialing/campaign/"):
                # Parse campaign ID and action from path: /campaign/{id}/{action}
                path_parts = path.split("/api/framework/predictive-dialing/campaign/")[-1].split(
                    "/"
                )
                if len(path_parts) >= 2:
                    campaign_id = "/".join(path_parts[:-1])  # Support IDs with slashes
                    action = path_parts[-1]
                    if action == "start":
                        self._handle_start_dialing_campaign(campaign_id)
                    elif action == "pause":
                        self._handle_pause_dialing_campaign(campaign_id)
                    else:
                        self._send_json({"error": "Not found"}, 404)
                else:
                    self._send_json({"error": "Invalid path"}, 400)

            # Voice Biometrics POST endpoints
            elif path == "/api/framework/voice-biometrics/profile":
                self._handle_create_voice_profile()
            elif path == "/api/framework/voice-biometrics/enroll":
                self._handle_start_voice_enrollment()
            elif path == "/api/framework/voice-biometrics/verify":
                self._handle_verify_speaker()

            # Call Quality Prediction POST endpoints
            elif path == "/api/framework/call-quality-prediction/metrics":
                self._handle_collect_quality_metrics()
            elif path == "/api/framework/call-quality-prediction/train":
                self._handle_train_quality_model()

            # Video Codec POST endpoints
            elif path == "/api/framework/video-codec/bandwidth":
                self._handle_calculate_video_bandwidth()

            # Mobile Number Portability POST endpoints
            elif path == "/api/framework/mobile-portability/mapping":
                self._handle_create_mobile_mapping()
            elif path.startswith("/api/framework/mobile-portability/mapping/"):
                # Parse business number and action from path: /mapping/{number}/{action}
                path_parts = path.split("/api/framework/mobile-portability/mapping/")[-1].split("/")
                if len(path_parts) >= 2:
                    business_number = "/".join(path_parts[:-1])  # Support numbers with slashes
                    action = path_parts[-1]
                    if action == "toggle":
                        self._handle_toggle_mobile_mapping(business_number)
                    else:
                        self._send_json({"error": "Not found"}, 404)
                else:
                    self._send_json({"error": "Invalid path"}, 400)

            # Call Recording Analytics POST endpoints
            elif path == "/api/framework/recording-analytics/analyze":
                self._handle_analyze_recording()
            elif path == "/api/framework/recording-analytics/search":
                self._handle_search_recordings()

            # Predictive Voicemail Drop POST endpoints
            elif path == "/api/framework/voicemail-drop/message":
                self._handle_add_voicemail_message()
            elif path == "/api/framework/voicemail-drop/drop":
                self._handle_drop_voicemail()

            # DNS SRV Failover POST endpoints
            elif path == "/api/framework/dns-srv/lookup":
                self._handle_lookup_srv()

            # Session Border Controller POST endpoints
            elif path == "/api/framework/sbc/relay":
                self._handle_allocate_sbc_relay()

            # Data Residency Controls POST endpoints
            elif path == "/api/framework/data-residency/location":
                self._handle_get_storage_location()

            # Open-source integration APIs
            elif path == "/api/integrations/jitsi/meetings":
                self._handle_jitsi_create_meeting()
            elif path == "/api/integrations/jitsi/instant":
                self._handle_jitsi_instant_meeting()
            elif path == "/api/integrations/espocrm/contacts":
                self._handle_espocrm_create_contact()
            elif path == "/api/integrations/espocrm/calls":
                self._handle_espocrm_log_call()
            elif path == "/api/integrations/matrix/messages":
                self._handle_matrix_send_message()
            elif path == "/api/integrations/matrix/notifications":
                self._handle_matrix_send_notification()
            elif path == "/api/integrations/matrix/rooms":
                self._handle_matrix_create_room()
            else:
                self._send_json({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            # Client disconnected - log but don't try to send error response
            self.logger.warning(f"Client disconnected during POST request: {e}")
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_PUT(self):
        """Handle PUT requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith("/api/provisioning/templates/"):
                # /api/provisioning/templates/{vendor}/{model}
                parts = path.split("/")
                if len(parts) >= 6:
                    vendor = parts[4]
                    model = parts[5]
                    # Validate vendor and model to prevent path traversal
                    import re

                    if re.match(r"^[a-z0-9_-]+$", vendor.lower()) and re.match(
                        r"^[a-z0-9_-]+$", model.lower()
                    ):
                        self._handle_update_template(vendor, model)
                    else:
                        self._send_json({"error": "Invalid vendor or model name"}, 400)
                else:
                    self._send_json({"error": "Invalid path"}, 400)
            elif path.startswith("/api/extensions/"):
                # Extract extension number from path
                number = path.split("/")[-1]
                self._handle_update_extension(number)
            elif path == "/api/config":
                self._handle_update_config()
            elif path == "/api/config/section":
                self._handle_update_config_section()
            elif path == "/api/config/dtmf":
                self._handle_update_dtmf_config()
            elif path.startswith("/api/voicemail/"):
                self._handle_update_voicemail(path)
            elif path == "/api/auto-attendant/config":
                self._handle_update_auto_attendant_config()
            elif path == "/api/auto-attendant/prompts":
                self._handle_update_auto_attendant_prompts()
            elif path.startswith("/api/auto-attendant/menu-options/"):
                self._handle_update_auto_attendant_menu_option(path)
            elif path.startswith("/api/voicemail-boxes/") and path.endswith("/greeting"):
                self._handle_upload_voicemail_greeting(path)
            else:
                self._send_json({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            # Client disconnected - log but don't try to send error response
            self.logger.warning(f"Client disconnected during PUT request: {e}")
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith("/api/provisioning/devices/"):
                # Extract MAC address from path
                mac = path.split("/")[-1]
                self._handle_unregister_device(mac)
            elif path.startswith("/api/extensions/"):
                # Extract extension number from path
                number = path.split("/")[-1]
                self._handle_delete_extension(number)
            elif path.startswith("/api/voicemail/"):
                self._handle_delete_voicemail(path)
            elif path.startswith("/api/phone-book/"):
                # Extract extension from path
                extension = path.split("/")[-1]
                self._handle_delete_phone_book_entry(extension)
            elif path.startswith("/api/paging/zones/"):
                # Extract extension from path
                extension = path.split("/")[-1]
                self._handle_delete_paging_zone(extension)
            elif path.startswith("/api/dnd/rule/"):
                # Extract rule ID from path
                rule_id = path.split("/")[-1]
                self._handle_delete_dnd_rule(rule_id)
            elif path.startswith("/api/dnd/override/"):
                # Extract extension from path
                extension = path.split("/")[-1]
                self._handle_clear_dnd_override(extension)
            elif path.startswith("/api/skills/assign/"):
                # Extract agent_extension/skill_id from path
                parts = path.split("/")
                if len(parts) >= 5:
                    agent_extension = parts[-2]
                    skill_id = parts[-1]
                    self._handle_remove_skill_from_agent(agent_extension, skill_id)
                else:
                    self._send_json({"error": "Invalid path"}, 400)
            elif path.startswith("/api/auto-attendant/menu-options/"):
                # Extract digit from path
                digit = path.split("/")[-1]
                self._handle_delete_auto_attendant_menu_option(digit)
            elif path.startswith("/api/voicemail-boxes/") and path.endswith("/clear"):
                self._handle_clear_voicemail_box(path)
            elif path.startswith("/api/voicemail-boxes/") and path.endswith("/greeting"):
                self._handle_delete_voicemail_greeting(path)
            elif path.startswith("/api/emergency/contacts/"):
                # Extract contact ID from path
                contact_id = path.split("/")[-1]
                self._handle_delete_emergency_contact(contact_id)
            elif path.startswith("/api/sip-trunks/"):
                # Extract trunk ID from path
                trunk_id = path.split("/")[-1]
                self._handle_delete_sip_trunk(trunk_id)
            elif path.startswith("/api/fmfm/destination/"):
                # Extract extension and number from path
                # Path: /api/fmfm/destination/{extension}/{number}
                parts = path.split("/")
                if len(parts) >= 5:
                    extension = parts[-2]
                    number = parts[-1]
                    self._handle_remove_fmfm_destination(extension, number)
                else:
                    self._send_json({"error": "Invalid path"}, 400)
            elif path.startswith("/api/fmfm/config/"):
                # Extract extension from path
                extension = path.split("/")[-1]
                self._handle_disable_fmfm(extension)
            elif path.startswith("/api/time-routing/rule/"):
                # Extract rule ID from path
                rule_id = path.split("/")[-1]
                self._handle_delete_time_routing_rule(rule_id)
            elif path.startswith("/api/webhooks/"):
                # Extract URL from path (URL-encoded)
                url = unquote(path.split("/", 3)[-1])
                # Validate URL format
                if url.startswith("http://") or url.startswith("https://"):
                    self._handle_delete_webhook(url)
                else:
                    self._send_json({"error": "Invalid webhook URL format"}, 400)
            elif path.startswith("/api/recording-retention/policy/"):
                # Extract policy ID from path - sanitize to prevent path traversal
                policy_id = path.split("/")[-1]
                # Validate: alphanumeric, underscore, hyphen only (no dots, slashes)
                import re

                if policy_id and re.match(r"^[a-zA-Z0-9_-]+$", policy_id):
                    self._handle_delete_retention_policy(policy_id)
                else:
                    self._send_json({"error": "Invalid policy ID"}, 400)
            elif path.startswith("/api/fraud-detection/blocked-pattern/"):
                # Extract pattern ID from path - sanitize
                pattern_id = path.split("/")[-1]
                # Validate: numeric only for array index
                if pattern_id and pattern_id.isdigit():
                    self._handle_delete_blocked_pattern(pattern_id)
                else:
                    self._send_json({"error": "Invalid pattern ID"}, 400)
            elif path.startswith("/api/framework/voice-biometrics/profile/"):
                # Extract user ID from path - sanitize
                user_id = path.split("/")[-1]
                # Validate: alphanumeric, underscore, hyphen, dot only (no path traversal)
                if user_id and re.match(r"^[a-zA-Z0-9_.-]+$", user_id):
                    self._handle_delete_voice_profile(user_id)
                else:
                    self._send_json({"error": "Invalid user ID"}, 400)
            elif path.startswith("/api/framework/mobile-portability/mapping/"):
                # Extract business number from path - sanitize
                business_number = path.split("/")[-1]
                # Validate: phone number format (digits, +, -, parentheses, spaces)
                if business_number and re.match(r"^[\d+\-() ]+$", business_number):
                    self._handle_delete_mobile_mapping(business_number)
                else:
                    self._send_json({"error": "Invalid business number"}, 400)
            else:
                self._send_json({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            # Client disconnected - log but don't try to send error response
            self.logger.warning(f"Client disconnected during DELETE request: {e}")
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            if path == "":
                self._handle_root()
            elif path == "/health" or path == "/healthz":
                self._handle_health()
            elif path == "/ready" or path == "/readiness":
                self._handle_readiness()
            elif path == "/live" or path == "/liveness":
                self._handle_liveness()
            elif path == "/api/status":
                self._handle_status()
            elif path == "/api/health/detailed":
                self._handle_detailed_health()
            elif path == "/metrics":
                self._handle_prometheus_metrics()
            elif path == "/api/extensions":
                self._handle_get_extensions()
            elif path == "/api/calls":
                self._handle_get_calls()
            elif path == "/api/statistics":
                self._handle_get_statistics()
            elif path == "/api/analytics/advanced":
                self._handle_get_advanced_analytics()
            elif path == "/api/analytics/call-center":
                self._handle_get_call_center_metrics()
            elif path == "/api/analytics/export":
                self._handle_export_analytics()
            elif path == "/api/emergency/contacts":
                self._handle_get_emergency_contacts()
            elif path == "/api/emergency/history":
                self._handle_get_emergency_history()
            elif path == "/api/emergency/test":
                self._handle_test_emergency_notification()
            elif path == "/api/qos/metrics":
                self._handle_get_qos_metrics()
            elif path == "/api/qos/alerts":
                self._handle_get_qos_alerts()
            elif path == "/api/qos/history":
                self._handle_get_qos_history()
            elif path == "/api/qos/statistics":
                self._handle_get_qos_statistics()
            elif path.startswith("/api/qos/call/"):
                self._handle_get_qos_call_metrics(path)
            elif path == "/api/config":
                self._handle_get_config()
            elif path == "/api/config/full":
                self._handle_get_full_config()
            elif path == "/api/config/dtmf":
                self._handle_get_dtmf_config()
            elif path == "/api/ssl/status":
                self._handle_get_ssl_status()
            elif path == "/api/provisioning/devices":
                self._handle_get_provisioning_devices()
            elif path == "/api/provisioning/vendors":
                self._handle_get_provisioning_vendors()
            elif path == "/api/provisioning/templates":
                self._handle_get_provisioning_templates()
            elif path.startswith("/api/provisioning/templates/"):
                # /api/provisioning/templates/{vendor}/{model}
                parts = path.split("/")
                if len(parts) >= 6:
                    vendor = parts[4]
                    model = parts[5]
                    # Validate vendor and model to prevent path traversal
                    import re

                    if re.match(r"^[a-z0-9_-]+$", vendor.lower()) and re.match(
                        r"^[a-z0-9_-]+$", model.lower()
                    ):
                        self._handle_get_template_content(vendor, model)
                    else:
                        self._send_json({"error": "Invalid vendor or model name"}, 400)
                else:
                    self._send_json({"error": "Invalid path"}, 400)
            elif path == "/api/provisioning/diagnostics":
                self._handle_get_provisioning_diagnostics()
            elif path == "/api/provisioning/requests":
                self._handle_get_provisioning_requests()
            elif path == "/api/registered-phones":
                self._handle_get_registered_phones()
            elif path == "/api/registered-phones/with-mac":
                self._handle_get_registered_phones_with_mac()
            elif path.startswith("/api/registered-phones/extension/"):
                # Extract extension: /api/registered-phones/extension/{number}
                extension = path.split("/")[-1]
                self._handle_get_registered_phones_by_extension(extension)
            elif path.startswith("/api/phone-lookup/"):
                # Extract identifier: /api/phone-lookup/{mac_or_ip}
                identifier = path.split("/")[-1]
                self._handle_phone_lookup(identifier)
            elif path == "/api/integrations/ad/status":
                self._handle_ad_status()
            elif path.startswith("/api/integrations/ad/search"):
                self._handle_ad_search()
            elif path == "/api/phone-book":
                self._handle_get_phone_book()
            elif path == "/api/phone-book/export/xml":
                self._handle_export_phone_book_xml()
            elif path == "/api/phone-book/export/cisco-xml":
                self._handle_export_phone_book_cisco_xml()
            elif path == "/api/phone-book/export/json":
                self._handle_export_phone_book_json()
            elif path.startswith("/api/phone-book/search"):
                self._handle_search_phone_book()
            elif path == "/api/paging/zones":
                self._handle_get_paging_zones()
            elif path == "/api/paging/devices":
                self._handle_get_paging_devices()
            elif path == "/api/paging/active":
                self._handle_get_active_pages()
            elif path == "/api/webhooks":
                self._handle_get_webhooks()
            elif path == "/api/webrtc/sessions":
                self._handle_get_webrtc_sessions()
            elif path == "/api/webrtc/phone-config":
                self._handle_get_webrtc_phone_config()
            elif path == "/api/webrtc/ice-servers":
                self._handle_get_ice_servers()
            elif path.startswith("/api/webrtc/session/"):
                self._handle_get_webrtc_session(path)
            elif path.startswith("/api/crm/lookup"):
                self._handle_crm_lookup()
            elif path == "/api/crm/providers":
                self._handle_get_crm_providers()
            elif path == "/api/hot-desk/sessions":
                self._handle_get_hot_desk_sessions()
            elif path.startswith("/api/hot-desk/session/"):
                self._handle_get_hot_desk_session(path)
            elif path.startswith("/api/hot-desk/extension/"):
                self._handle_get_hot_desk_extension(path)
            elif path.startswith("/api/mfa/status/"):
                self._handle_get_mfa_status(path)
            elif path.startswith("/api/mfa/methods/"):
                self._handle_get_mfa_methods(path)
            elif path == "/api/security/threat-summary":
                self._handle_get_threat_summary()
            elif path == "/api/security/compliance-status":
                self._handle_get_security_compliance_status()
            elif path == "/api/security/health":
                self._handle_get_security_health()
            elif path.startswith("/api/security/check-ip/"):
                self._handle_check_ip(path)
            elif path.startswith("/api/dnd/status/"):
                self._handle_get_dnd_status(path)
            elif path.startswith("/api/dnd/rules/"):
                self._handle_get_dnd_rules(path)
            elif path == "/api/recording-retention/policies":
                self._handle_get_retention_policies()
            elif path == "/api/recording-retention/statistics":
                self._handle_get_retention_statistics()
            elif path == "/api/fraud-detection/alerts":
                self._handle_get_fraud_alerts()
            elif path == "/api/fraud-detection/statistics":
                self._handle_get_fraud_statistics()
            elif path.startswith("/api/fraud-detection/extension/"):
                # Extract extension from path
                extension = path.split("/")[-1]
                self._handle_get_fraud_extension_stats(extension)
            elif path == "/api/callback-queue/statistics":
                self._handle_get_callback_statistics()
            elif path == "/api/callback-queue/list":
                self._handle_get_callback_list()
            elif path.startswith("/api/callback-queue/queue/"):
                # Extract queue_id from path
                queue_id = path.split("/")[-1]
                self._handle_get_queue_callbacks(queue_id)
            elif path.startswith("/api/callback-queue/info/"):
                # Extract callback_id from path
                callback_id = path.split("/")[-1]
                self._handle_get_callback_info(callback_id)
            elif path == "/api/mobile-push/devices":
                self._handle_get_all_devices()
            elif path.startswith("/api/mobile-push/devices/"):
                # Extract user_id from path
                user_id = path.split("/")[-1]
                self._handle_get_user_devices(user_id)
            elif path == "/api/mobile-push/statistics":
                self._handle_get_push_statistics()
            elif path == "/api/mobile-push/history":
                self._handle_get_push_history()
            elif path == "/api/recording-announcements/statistics":
                self._handle_get_announcement_statistics()
            elif path == "/api/recording-announcements/config":
                self._handle_get_announcement_config()
            elif path == "/api/skills/all":
                self._handle_get_all_skills()
            elif path.startswith("/api/skills/agent/"):
                self._handle_get_agent_skills(path)
            elif path.startswith("/api/skills/queue/"):
                self._handle_get_queue_requirements(path)
            elif path.startswith("/api/voicemail/"):
                self._handle_get_voicemail(path)
            elif path == "/api/auto-attendant/config":
                self._handle_get_auto_attendant_config()
            elif path == "/api/auto-attendant/menu-options":
                self._handle_get_auto_attendant_menu_options()
            elif path == "/api/auto-attendant/prompts":
                self._handle_get_auto_attendant_prompts()
            elif path == "/api/voicemail-boxes":
                self._handle_get_voicemail_boxes()
            elif path.startswith("/api/voicemail-boxes/") and path.endswith("/greeting"):
                self._handle_get_voicemail_greeting(path)
            elif path.startswith("/api/voicemail-boxes/"):
                self._handle_get_voicemail_box_details(path)
            elif path == "/api/sip-trunks":
                self._handle_get_sip_trunks()
            elif path == "/api/sip-trunks/health":
                self._handle_get_trunk_health()
            elif path == "/api/lcr/rates":
                self._handle_get_lcr_rates()
            elif path == "/api/lcr/statistics":
                self._handle_get_lcr_statistics()
            elif path == "/api/fmfm/extensions":
                self._handle_get_fmfm_extensions()
            elif path.startswith("/api/fmfm/config/"):
                # Extract extension from path
                extension = path.split("/")[-1]
                self._handle_get_fmfm_config(extension)
            elif path == "/api/fmfm/statistics":
                self._handle_get_fmfm_statistics()
            elif path == "/api/time-routing/rules":
                self._handle_get_time_routing_rules()
            elif path == "/api/time-routing/statistics":
                self._handle_get_time_routing_statistics()

            # Framework feature APIs
            elif path == "/api/framework/speech-analytics/configs":
                self._handle_get_speech_analytics_configs()
            elif path.startswith("/api/framework/speech-analytics/config/"):
                extension = path.split("/")[-1]
                self._handle_get_speech_analytics_config(extension)
            elif path.startswith("/api/framework/speech-analytics/summary/"):
                call_id = path.split("/")[-1]
                self._handle_get_call_summary(call_id)
            elif path == "/api/framework/video-conference/rooms":
                self._handle_get_video_rooms()
            elif path.startswith("/api/framework/video-conference/room/"):
                room_id = path.split("/")[-1]
                self._handle_get_video_room(room_id)
            elif path == "/api/framework/click-to-dial/configs":
                self._handle_get_click_to_dial_configs()
            elif path.startswith("/api/framework/click-to-dial/config/"):
                extension = path.split("/")[-1]
                self._handle_get_click_to_dial_config(extension)
            elif path.startswith("/api/framework/click-to-dial/history/"):
                extension = path.split("/")[-1]
                self._handle_get_click_to_dial_history(extension)
            elif path == "/api/framework/team-messaging/channels":
                self._handle_get_team_channels()
            elif path.startswith("/api/framework/team-messaging/messages/"):
                channel_id = path.split("/")[-1]
                self._handle_get_team_messages(channel_id)
            elif path == "/api/framework/nomadic-e911/sites":
                self._handle_get_e911_sites()
            elif path.startswith("/api/framework/nomadic-e911/location/"):
                extension = path.split("/")[-1]
                self._handle_get_e911_location(extension)
            elif path.startswith("/api/framework/nomadic-e911/history/"):
                extension = path.split("/")[-1]
                self._handle_get_e911_history(extension)
            elif path == "/api/framework/integrations/hubspot":
                self._handle_get_hubspot_config()
            elif path == "/api/framework/integrations/zendesk":
                self._handle_get_zendesk_config()
            elif path == "/api/framework/integrations/activity":
                self._handle_get_integration_activity()
            elif path == "/api/framework/compliance/gdpr/consents":
                extension = self.headers.get("X-Extension", "")
                self._handle_get_gdpr_consents(extension)
            elif path == "/api/framework/compliance/gdpr/requests":
                self._handle_get_gdpr_requests()
            elif path == "/api/framework/compliance/soc2/controls":
                self._handle_get_soc2_controls()
            elif path == "/api/framework/compliance/pci/audit-log":
                self._handle_get_pci_audit_log()

            # BI Integration API endpoints
            elif path == "/api/framework/bi-integration/datasets":
                self._handle_get_bi_datasets()
            elif path == "/api/framework/bi-integration/statistics":
                self._handle_get_bi_statistics()
            elif path.startswith("/api/framework/bi-integration/export/"):
                dataset_name = path.split("/")[-1]
                self._handle_get_bi_export_status(dataset_name)

            # Call Tagging API endpoints
            elif path == "/api/framework/call-tagging/tags":
                self._handle_get_call_tags()
            elif path == "/api/framework/call-tagging/rules":
                self._handle_get_tagging_rules()
            elif path == "/api/framework/call-tagging/statistics":
                self._handle_get_tagging_statistics()

            # Call Blending API endpoints
            elif path == "/api/framework/call-blending/agents":
                self._handle_get_blending_agents()
            elif path == "/api/framework/call-blending/statistics":
                self._handle_get_blending_statistics()
            elif path.startswith("/api/framework/call-blending/agent/"):
                agent_id = path.split("/")[-1]
                self._handle_get_blending_agent_status(agent_id)

            # Geographic Redundancy API endpoints
            elif path == "/api/framework/geo-redundancy/regions":
                self._handle_get_geo_regions()
            elif path == "/api/framework/geo-redundancy/statistics":
                self._handle_get_geo_statistics()
            elif path.startswith("/api/framework/geo-redundancy/region/"):
                region_id = path.split("/")[-1]
                self._handle_get_geo_region_status(region_id)

            # Conversational AI API endpoints
            elif path == "/api/framework/conversational-ai/config":
                self._handle_get_ai_config()
            elif path == "/api/framework/conversational-ai/statistics":
                self._handle_get_ai_statistics()
            elif path == "/api/framework/conversational-ai/conversations":
                self._handle_get_ai_conversations()
            elif path == "/api/framework/conversational-ai/history":
                self._handle_get_ai_conversation_history()

            # Predictive Dialing API endpoints
            elif path == "/api/framework/predictive-dialing/campaigns":
                self._handle_get_dialing_campaigns()
            elif path == "/api/framework/predictive-dialing/statistics":
                self._handle_get_dialing_statistics()
            elif path.startswith("/api/framework/predictive-dialing/campaign/"):
                campaign_id = path.split("/")[-1]
                self._handle_get_campaign_details(campaign_id)

            # Voice Biometrics API endpoints
            elif path == "/api/framework/voice-biometrics/profiles":
                self._handle_get_voice_profiles()
            elif path == "/api/framework/voice-biometrics/statistics":
                self._handle_get_voice_statistics()
            elif path.startswith("/api/framework/voice-biometrics/profile/"):
                user_id = path.split("/")[-1]
                self._handle_get_voice_profile(user_id)

            # Call Quality Prediction API endpoints
            elif path == "/api/framework/call-quality-prediction/predictions":
                self._handle_get_quality_predictions()
            elif path == "/api/framework/call-quality-prediction/statistics":
                self._handle_get_quality_statistics()
            elif path == "/api/framework/call-quality-prediction/alerts":
                self._handle_get_quality_alerts()
            elif path.startswith("/api/framework/call-quality-prediction/prediction/"):
                call_id = path.split("/")[-1]
                self._handle_get_call_prediction(call_id)

            # Video Codec API endpoints
            elif path == "/api/framework/video-codec/codecs":
                self._handle_get_video_codecs()
            elif path == "/api/framework/video-codec/statistics":
                self._handle_get_video_statistics()

            # Mobile Number Portability API endpoints
            elif path == "/api/framework/mobile-portability/mappings":
                self._handle_get_mobile_mappings()
            elif path == "/api/framework/mobile-portability/statistics":
                self._handle_get_mobile_statistics()
            elif path.startswith("/api/framework/mobile-portability/mapping/"):
                business_number = path.split("/")[-1]
                self._handle_get_mobile_mapping(business_number)

            # Call Recording Analytics API endpoints
            elif path == "/api/framework/recording-analytics/analyses":
                self._handle_get_recording_analyses()
            elif path == "/api/framework/recording-analytics/statistics":
                self._handle_get_recording_statistics()
            elif path.startswith("/api/framework/recording-analytics/analysis/"):
                recording_id = path.split("/")[-1]
                self._handle_get_recording_analysis(recording_id)

            # Predictive Voicemail Drop API endpoints
            elif path == "/api/framework/voicemail-drop/messages":
                self._handle_get_voicemail_messages()
            elif path == "/api/framework/voicemail-drop/statistics":
                self._handle_get_voicemail_drop_statistics()

            # DNS SRV Failover API endpoints
            elif path == "/api/framework/dns-srv/records":
                self._handle_get_srv_records()
            elif path == "/api/framework/dns-srv/statistics":
                self._handle_get_dns_srv_statistics()

            # Session Border Controller API endpoints
            elif path == "/api/framework/sbc/statistics":
                self._handle_get_sbc_statistics()
            elif path == "/api/framework/sbc/relays":
                self._handle_get_sbc_relays()

            # Data Residency Controls API endpoints
            elif path == "/api/framework/data-residency/regions":
                self._handle_get_data_regions()
            elif path == "/api/framework/data-residency/statistics":
                self._handle_get_data_residency_statistics()

            # Open-source integration GET APIs
            elif path.startswith("/api/integrations/espocrm/contacts/search"):
                self._handle_espocrm_search_contact()

            elif path.startswith("/provision/") and path.endswith(".cfg"):
                self._handle_provisioning_request(path)
            elif path == "/admin":
                self._handle_admin_redirect()
            elif path.startswith("/admin/"):
                self._handle_static_file(path)
            else:
                self._send_json({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            # Client disconnected - log but don't try to send error response
            self.logger.warning(f"Client disconnected during GET request: {e}")
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_root(self):
        """Handle root path - redirect to admin panel"""
        self.send_response(302)
        self.send_header("Location", "/admin")
        self.end_headers()

    def _handle_health(self):
        """Lightweight health check endpoint for container orchestration"""
        # Return simple OK response if server is running
        # This is a combined liveness/readiness check for backward compatibility
        try:
            checker = self._get_health_checker()
            is_ready, details = checker.check_readiness()
            
            status_code = 200 if is_ready else 503
            self._set_headers(status_code, "application/json")
            self.wfile.write(json.dumps(details).encode())
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "error": str(e)
            }).encode())
    
    def _handle_liveness(self):
        """Kubernetes-style liveness probe - is the app alive?"""
        try:
            checker = self._get_health_checker()
            is_alive, details = checker.check_liveness()
            
            status_code = 200 if is_alive else 503
            self._set_headers(status_code, "application/json")
            self.wfile.write(json.dumps(details).encode())
        except Exception as e:
            self.logger.error(f"Liveness check error: {e}")
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "error": str(e)
            }).encode())
    
    def _handle_readiness(self):
        """Kubernetes-style readiness probe - is the app ready for traffic?"""
        try:
            checker = self._get_health_checker()
            is_ready, details = checker.check_readiness()
            
            status_code = 200 if is_ready else 503
            self._set_headers(status_code, "application/json")
            self.wfile.write(json.dumps(details).encode())
        except Exception as e:
            self.logger.error(f"Readiness check error: {e}")
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "error": str(e)
            }).encode())
    
    def _handle_detailed_health(self):
        """Comprehensive health status for monitoring dashboards"""
        try:
            checker = self._get_health_checker()
            details = checker.get_detailed_status()
            
            is_healthy = details.get("overall_status") == "healthy"
            status_code = 200 if is_healthy else 503
            
            self._set_headers(status_code, "application/json")
            self.wfile.write(json.dumps(details, indent=2).encode())
        except Exception as e:
            self.logger.error(f"Detailed health check error: {e}")
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "error": str(e)
            }).encode())
    
    def _handle_prometheus_metrics(self):
        """Prometheus metrics endpoint"""
        try:
            checker = self._get_health_checker()
            _, details = checker.check_readiness()
            
            from pbx.utils.production_health import format_health_check_response
            is_healthy = details.get("status") == "ready"
            
            status_code, metrics_text = format_health_check_response(
                is_healthy, details, format_type="prometheus"
            )
            
            self._set_headers(status_code, "text/plain; version=0.0.4")
            self.wfile.write(metrics_text.encode())
        except Exception as e:
            self.logger.error(f"Metrics endpoint error: {e}")
            self._set_headers(500, "text/plain")
            self.wfile.write(f"# ERROR: {str(e)}\n".encode())
    
    def _get_health_checker(self):
        """Get or create production health checker instance"""
        if PBXAPIHandler._health_checker is None:
            from pbx.utils.production_health import ProductionHealthChecker
            
            # Get config from pbx_core if available
            config = None
            if self.pbx_core and hasattr(self.pbx_core, 'config'):
                config = self.pbx_core.config
            
            PBXAPIHandler._health_checker = ProductionHealthChecker(
                pbx_core=self.pbx_core,
                config=config
            )
        
        return PBXAPIHandler._health_checker

    def _handle_status(self):
        """Get PBX status"""
        if self.pbx_core:
            status = self.pbx_core.get_status()
            self._send_json(status)
        else:
            self._send_json({"error": "PBX not initialized"}, 500)

    def _handle_get_extensions(self):
        """Get extensions"""
        # SECURITY: Require authentication (but not necessarily admin)
        is_authenticated, payload = self._verify_authentication()
        if not is_authenticated:
            self._send_json({"error": "Authentication required"}, 401)
            return

        if self.pbx_core:
            extensions = self.pbx_core.extension_registry.get_all()

            # Check if user is admin
            is_admin = payload.get("is_admin", False)
            current_extension = payload.get("extension")

            # Non-admin users should only see their own extension
            if not is_admin:
                extensions = [e for e in extensions if e.number == current_extension]

            data = [
                {
                    "number": e.number,
                    "name": e.name,
                    "email": e.config.get("email"),
                    "registered": e.registered,
                    "allow_external": e.config.get("allow_external", True),
                    "ad_synced": e.config.get("ad_synced", False),
                    "voicemail_pin_hash": e.config.get("voicemail_pin_hash"),
                    "is_admin": e.config.get("is_admin", False),
                }
                for e in extensions
            ]
            self._send_json(data)
        else:
            self._send_json({"error": "PBX not initialized"}, 500)

    def _handle_get_calls(self):
        """Get active calls"""
        if self.pbx_core:
            calls = self.pbx_core.call_manager.get_active_calls()
            data = [str(call) for call in calls]
            self._send_json(data)
        else:
            self._send_json({"error": "PBX not initialized"}, 500)

    def _validate_limit_parameter(
        self, params: dict, default: int, max_value: int
    ) -> Optional[int]:
        """
        Helper method to validate limit query parameters

        Args:
            params: Parsed query parameters
            default: Default value if not provided
            max_value: Maximum allowed value

        Returns:
            Validated limit value or None if invalid (error response will be sent)
        """
        try:
            limit = int(params.get("limit", [default])[0])
            if limit < 1:
                self._send_json({"error": "limit must be at least 1"}, 400)
                return None
            if limit > max_value:
                self._send_json({"error": f"limit cannot exceed {max_value}"}, 400)
                return None
            return limit
        except ValueError:
            self._send_json({"error": "Invalid limit parameter, must be an integer"}, 400)
            return None

    def _handle_get_statistics(self):
        """Get comprehensive statistics for dashboard"""
        if self.pbx_core and hasattr(self.pbx_core, "statistics_engine"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                days = int(params.get("days", [7])[0])

                # Get dashboard statistics
                stats = self.pbx_core.statistics_engine.get_dashboard_statistics(days)

                # Add call quality metrics (with QoS integration)
                stats["call_quality"] = self.pbx_core.statistics_engine.get_call_quality_metrics(
                    self.pbx_core
                )

                # Add real-time metrics
                stats["real_time"] = self.pbx_core.statistics_engine.get_real_time_metrics(
                    self.pbx_core
                )

                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting statistics: {e}")
                self._send_json({"error": f"Error getting statistics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Statistics engine not initialized"}, 500)

    def _handle_get_qos_metrics(self):
        """Get QoS metrics for all active calls"""
        if self.pbx_core and hasattr(self.pbx_core, "qos_monitor"):
            try:
                metrics = self.pbx_core.qos_monitor.get_all_active_metrics()
                self._send_json({"active_calls": len(metrics), "metrics": metrics})
            except Exception as e:
                self.logger.error(f"Error getting QoS metrics: {e}")
                self._send_json({"error": f"Error getting QoS metrics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "QoS monitoring not enabled"}, 500)

    def _handle_get_qos_alerts(self):
        """Get QoS quality alerts"""
        if self.pbx_core and hasattr(self.pbx_core, "qos_monitor"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                # Validate limit parameter
                limit = int(params.get("limit", [50])[0])
                if limit < 1:
                    self._send_json({"error": "limit must be at least 1"}, 400)
                    return
                if limit > 1000:
                    self._send_json({"error": "limit cannot exceed 1000"}, 400)
                    return

                alerts = self.pbx_core.qos_monitor.get_alerts(limit)
                self._send_json({"count": len(alerts), "alerts": alerts})
            except ValueError as e:
                self.logger.error(f"Invalid parameter for QoS alerts: {e}")
                self._send_json({"error": "Invalid limit parameter, must be an integer"}, 400)
            except Exception as e:
                self.logger.error(f"Error getting QoS alerts: {e}")
                self._send_json({"error": f"Error getting QoS alerts: {str(e)}"}, 500)
        else:
            self._send_json({"error": "QoS monitoring not enabled"}, 500)

    def _handle_get_qos_history(self):
        """Get historical QoS metrics"""
        if self.pbx_core and hasattr(self.pbx_core, "qos_monitor"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                # Validate limit parameter
                limit = int(params.get("limit", [100])[0])
                if limit < 1:
                    self._send_json({"error": "limit must be at least 1"}, 400)
                    return
                if limit > 10000:
                    self._send_json({"error": "limit cannot exceed 10000"}, 400)
                    return

                # Validate min_mos parameter
                min_mos = params.get("min_mos", [None])[0]
                if min_mos:
                    min_mos = float(min_mos)
                    if min_mos < 1.0 or min_mos > 5.0:
                        self._send_json({"error": "min_mos must be between 1.0 and 5.0"}, 400)
                        return

                history = self.pbx_core.qos_monitor.get_historical_metrics(limit, min_mos)
                self._send_json({"count": len(history), "metrics": history})
            except ValueError as e:
                self.logger.error(f"Invalid parameter for QoS history: {e}")
                self._send_json(
                    {"error": "Invalid parameters, check limit (integer) and min_mos (float)"}, 400
                )
            except Exception as e:
                self.logger.error(f"Error getting QoS history: {e}")
                self._send_json({"error": f"Error getting QoS history: {str(e)}"}, 500)
        else:
            self._send_json({"error": "QoS monitoring not enabled"}, 500)

    def _handle_get_qos_statistics(self):
        """Get overall QoS statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "qos_monitor"):
            try:
                stats = self.pbx_core.qos_monitor.get_statistics()
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting QoS statistics: {e}")
                self._send_json({"error": f"Error getting QoS statistics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "QoS monitoring not enabled"}, 500)

    def _handle_get_qos_call_metrics(self, path):
        """Get QoS metrics for a specific call"""
        if self.pbx_core and hasattr(self.pbx_core, "qos_monitor"):
            try:
                # Extract call_id from path: /api/qos/call/{call_id}
                call_id = path.split("/")[-1]
                metrics = self.pbx_core.qos_monitor.get_metrics(call_id)
                if metrics:
                    self._send_json(metrics)
                else:
                    self._send_json({"error": f"No QoS metrics found for call {call_id}"}, 404)
            except Exception as e:
                self.logger.error(f"Error getting call QoS metrics: {e}")
                self._send_json({"error": f"Error getting call QoS metrics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "QoS monitoring not enabled"}, 500)

    def _handle_get_provisioning_devices(self):
        """Get all provisioned devices"""
        if self.pbx_core and hasattr(self.pbx_core, "phone_provisioning"):
            devices = self.pbx_core.phone_provisioning.get_all_devices()
            data = [d.to_dict() for d in devices]
            self._send_json(data)
        else:
            self._send_json({"error": "Phone provisioning not enabled"}, 500)

    def _handle_get_provisioning_vendors(self):
        """Get supported vendors and models"""
        if self.pbx_core and hasattr(self.pbx_core, "phone_provisioning"):
            vendors = self.pbx_core.phone_provisioning.get_supported_vendors()
            models = self.pbx_core.phone_provisioning.get_supported_models()
            data = {"vendors": vendors, "models": models}
            self._send_json(data)
        else:
            self._send_json({"error": "Phone provisioning not enabled"}, 500)

    def _handle_get_provisioning_diagnostics(self):
        """Get provisioning system diagnostics"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        provisioning = self.pbx_core.phone_provisioning

        # Gather diagnostic information
        diagnostics = {
            "enabled": True,
            "configuration": {
                "url_format": self.pbx_core.config.get("provisioning.url_format", "Not configured"),
                "external_ip": self.pbx_core.config.get("server.external_ip", "Not configured"),
                "api_port": self.pbx_core.config.get("api.port", "Not configured"),
                "sip_host": self.pbx_core.config.get("server.sip_host", "Not configured"),
                "sip_port": self.pbx_core.config.get("server.sip_port", "Not configured"),
                "custom_templates_dir": self.pbx_core.config.get(
                    "provisioning.custom_templates_dir", "Not configured"
                ),
            },
            "statistics": {
                "total_devices": len(provisioning.devices),
                "total_templates": len(provisioning.templates),
                "total_requests": len(provisioning.provision_requests),
                "successful_requests": sum(
                    1 for r in provisioning.provision_requests if r.get("success")
                ),
                "failed_requests": sum(
                    1 for r in provisioning.provision_requests if not r.get("success")
                ),
            },
            "devices": [d.to_dict() for d in provisioning.get_all_devices()],
            "vendors": provisioning.get_supported_vendors(),
            "models": provisioning.get_supported_models(),
            "recent_requests": provisioning.get_request_history(limit=20),
        }

        # Add warnings for common issues
        warnings = []
        if diagnostics["configuration"]["external_ip"] == "Not configured":
            warnings.append(
                "server.external_ip is not configured - phones may not be able to reach the PBX"
            )
        if diagnostics["statistics"]["total_devices"] == 0:
            warnings.append(
                "No devices registered - use POST /api/provisioning/devices to register devices"
            )
        if diagnostics["statistics"]["failed_requests"] > 0:
            warnings.append(
                f"{diagnostics['statistics']['failed_requests']} provisioning requests failed - check recent_requests for details"
            )

        diagnostics["warnings"] = warnings

        self._send_json(diagnostics)

    def _handle_get_provisioning_requests(self):
        """Get provisioning request history"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        # Get limit from query parameter if provided
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        limit = int(query_params.get("limit", [50])[0])

        requests = self.pbx_core.phone_provisioning.get_request_history(limit=limit)
        self._send_json(
            {
                "total": len(self.pbx_core.phone_provisioning.provision_requests),
                "limit": limit,
                "requests": requests,
            }
        )

    def _handle_get_provisioning_templates(self):
        """Get list of all provisioning templates"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        templates = self.pbx_core.phone_provisioning.list_all_templates()
        self._send_json({"templates": templates, "total": len(templates)})

    def _handle_get_template_content(self, vendor, model):
        """Get content of a specific template"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        content = self.pbx_core.phone_provisioning.get_template_content(vendor, model)
        if content:
            self._send_json(
                {
                    "vendor": vendor,
                    "model": model,
                    "content": content,
                    "placeholders": [
                        "{{EXTENSION_NUMBER}}",
                        "{{EXTENSION_NAME}}",
                        "{{EXTENSION_PASSWORD}}",
                        "{{SIP_SERVER}}",
                        "{{SIP_PORT}}",
                        "{{SERVER_NAME}}",
                    ],
                }
            )
        else:
            self._send_json({"error": f"Template not found for {vendor} {model}"}, 404)

    def _handle_export_template(self, vendor, model):
        """Export template to file"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        success, message, filepath = self.pbx_core.phone_provisioning.export_template_to_file(
            vendor, model
        )
        if success:
            self._send_json(
                {
                    "success": True,
                    "message": message,
                    "filepath": filepath,
                    "vendor": vendor,
                    "model": model,
                }
            )
        else:
            self._send_json({"error": message}, 404)

    def _handle_update_template(self, vendor, model):
        """Update template content"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        try:
            body = self._get_body()
            content = body.get("content")

            if not content:
                self._send_json({"error": "Missing template content"}, 400)
                return

            success, message = self.pbx_core.phone_provisioning.update_template(
                vendor, model, content
            )
            if success:
                self._send_json(
                    {"success": True, "message": message, "vendor": vendor, "model": model}
                )
            else:
                self._send_json({"error": message}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_reload_templates(self):
        """Reload all templates from disk"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        success, message, stats = self.pbx_core.phone_provisioning.reload_templates()
        if success:
            self._send_json({"success": True, "message": message, "statistics": stats})
        else:
            self._send_json({"error": message}, 500)

    def _handle_get_registered_phones(self):
        """Get all registered phones from database"""
        logger = get_logger()
        if (
            self.pbx_core
            and hasattr(self.pbx_core, "registered_phones_db")
            and self.pbx_core.registered_phones_db
        ):
            try:
                phones = self.pbx_core.registered_phones_db.list_all()
                self._send_json(phones)
            except Exception as e:
                logger.error(f"Error loading registered phones from database: {e}")
                logger.error(
                    f"  Database type: {
                        self.pbx_core.registered_phones_db.db.db_type if hasattr(
                            self.pbx_core.registered_phones_db,
                            'db') else 'unknown'}"
                )
                logger.error(
                    f"  Database enabled: {
                        self.pbx_core.registered_phones_db.db.enabled if hasattr(
                            self.pbx_core.registered_phones_db,
                            'db') else 'unknown'}"
                )
                logger.error(f"  Traceback: {traceback.format_exc()}")
                self._send_json(
                    {"error": str(e), "details": "Check server logs for full error details"}, 500
                )
        else:
            # Return empty array when database is not available (graceful
            # degradation)
            logger.warning("Registered phones database not available - returning empty list")
            if self.pbx_core:
                logger.warning(f"  pbx_core exists: True")
                logger.warning(
                    f"  has registered_phones_db attr: {
                        hasattr(
                            self.pbx_core,
                            'registered_phones_db')}"
                )
                if hasattr(self.pbx_core, "registered_phones_db"):
                    logger.warning(
                        f"  registered_phones_db is None: {
                            self.pbx_core.registered_phones_db is None}"
                    )
            self._send_json([])

    def _handle_get_registered_phones_with_mac(self):
        """Get registered phones with MAC addresses from provisioning system"""
        logger = get_logger()
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        # Get registered phones (IP + Extension from SIP registrations)
        registered_phones = []
        if hasattr(self.pbx_core, "registered_phones_db") and self.pbx_core.registered_phones_db:
            try:
                registered_phones = self.pbx_core.registered_phones_db.list_all()
            except Exception as e:
                logger.error(f"Error loading registered phones: {e}")

        # Get provisioned devices (MAC + Extension from provisioning config)
        provisioned_devices = {}
        if hasattr(self.pbx_core, "phone_provisioning"):
            try:
                devices = self.pbx_core.phone_provisioning.get_all_devices()
                # Create a lookup by extension
                for device in devices:
                    provisioned_devices[device.extension_number] = device
            except Exception as e:
                logger.error(f"Error loading provisioned devices: {e}")

        # Correlate the two data sources
        enhanced_phones = []
        for phone in registered_phones:
            enhanced = dict(phone)
            extension = phone.get("extension_number")

            # Add MAC from provisioning if available and not already present
            if extension and extension in provisioned_devices and not phone.get("mac_address"):
                device = provisioned_devices[extension]
                enhanced["mac_address"] = device.mac_address
                enhanced["vendor"] = device.vendor
                enhanced["model"] = device.model
                enhanced["config_url"] = device.config_url
                enhanced["mac_source"] = "provisioning"
            elif phone.get("mac_address"):
                enhanced["mac_source"] = "sip_registration"

            enhanced_phones.append(enhanced)

        self._send_json(enhanced_phones)

    def _handle_phone_lookup(self, identifier):
        """Unified phone lookup by MAC or IP address"""
        logger = get_logger()
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        result = {
            "identifier": identifier,
            "type": None,
            "registered_phone": None,
            "provisioned_device": None,
            "correlation": None,
        }

        # Normalize the identifier to detect if it's a MAC or IP
        import re

        from pbx.features.phone_provisioning import normalize_mac_address

        # Check if it looks like a MAC address using regex
        # Matches formats: XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, XXXXXXXXXXXX
        mac_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$")
        is_mac = bool(mac_pattern.match(identifier))

        # Check if it looks like an IP address using regex
        # Matches valid IPv4 addresses
        ip_pattern = re.compile(
            r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        )
        is_ip = bool(ip_pattern.match(identifier))

        # Try MAC address lookup
        if is_mac:
            result["type"] = "mac"
            normalized_mac = normalize_mac_address(identifier)

            # Check provisioning system
            if hasattr(self.pbx_core, "phone_provisioning"):
                device = self.pbx_core.phone_provisioning.get_device(identifier)
                if device:
                    result["provisioned_device"] = device.to_dict()

            # Check registered phones
            if (
                hasattr(self.pbx_core, "registered_phones_db")
                and self.pbx_core.registered_phones_db
            ):
                try:
                    phone = self.pbx_core.registered_phones_db.get_by_mac(normalized_mac)
                    if phone:
                        result["registered_phone"] = phone
                except Exception as e:
                    logger.error(f"Error looking up MAC in registered_phones: {e}")

        # Try IP address lookup
        elif is_ip:
            result["type"] = "ip"

            # Check registered phones first
            if (
                hasattr(self.pbx_core, "registered_phones_db")
                and self.pbx_core.registered_phones_db
            ):
                try:
                    phone = self.pbx_core.registered_phones_db.get_by_ip(identifier)
                    if phone:
                        result["registered_phone"] = phone

                        # Now try to find MAC from provisioning using the
                        # extension
                        extension = phone.get("extension_number")
                        if extension and hasattr(self.pbx_core, "phone_provisioning"):
                            device = None
                            # Search through provisioned devices for this
                            # extension
                            for dev in self.pbx_core.phone_provisioning.get_all_devices():
                                if dev.extension_number == extension:
                                    device = dev
                                    break
                            if device:
                                result["provisioned_device"] = device.to_dict()
                except Exception as e:
                    logger.error(f"Error looking up IP in registered_phones: {e}")
        else:
            result["type"] = "unknown"
            self._send_json(
                {"error": f"Could not determine if {identifier} is a MAC address or IP address"},
                400,
            )
            return

        # Add correlation summary
        if result["registered_phone"] and result["provisioned_device"]:
            result["correlation"] = {
                "matched": True,
                "extension": result["registered_phone"].get("extension_number"),
                "mac_address": result["provisioned_device"].get("mac_address"),
                "ip_address": result["registered_phone"].get("ip_address"),
                "vendor": result["provisioned_device"].get("vendor"),
                "model": result["provisioned_device"].get("model"),
            }
        elif result["registered_phone"]:
            result["correlation"] = {
                "matched": False,
                "message": "Phone is registered but not provisioned in the system",
                "extension": result["registered_phone"].get("extension_number"),
                "ip_address": result["registered_phone"].get("ip_address"),
            }
        elif result["provisioned_device"]:
            result["correlation"] = {
                "matched": False,
                "message": "Device is provisioned but not currently registered",
                "extension": result["provisioned_device"].get("extension_number"),
                "mac_address": result["provisioned_device"].get("mac_address"),
            }
        else:
            result["correlation"] = {
                "matched": False,
                "message": "No information found for this identifier",
            }

        self._send_json(result)

    def _handle_get_registered_phones_by_extension(self, extension):
        """Get registered phones for a specific extension"""
        logger = get_logger()
        if (
            self.pbx_core
            and hasattr(self.pbx_core, "registered_phones_db")
            and self.pbx_core.registered_phones_db
        ):
            try:
                phones = self.pbx_core.registered_phones_db.get_by_extension(extension)
                self._send_json(phones)
            except Exception as e:
                logger.error(
                    f"Error loading registered phones for extension {extension} from database: {e}"
                )
                logger.error(f"  Extension: {extension}")
                logger.error(
                    f"  Database type: {
                        self.pbx_core.registered_phones_db.db.db_type if hasattr(
                            self.pbx_core.registered_phones_db,
                            'db') else 'unknown'}"
                )
                logger.error(
                    f"  Database enabled: {
                        self.pbx_core.registered_phones_db.db.enabled if hasattr(
                            self.pbx_core.registered_phones_db,
                            'db') else 'unknown'}"
                )
                logger.error(f"  Traceback: {traceback.format_exc()}")
                self._send_json(
                    {"error": str(e), "details": "Check server logs for full error details"}, 500
                )
        else:
            # Return empty array when database is not available (graceful
            # degradation)
            logger.warning(
                f"Registered phones database not available for extension {extension} - returning empty list"
            )
            if self.pbx_core:
                logger.warning(f"  pbx_core exists: True")
                logger.warning(
                    f"  has registered_phones_db attr: {
                        hasattr(
                            self.pbx_core,
                            'registered_phones_db')}"
                )
                if hasattr(self.pbx_core, "registered_phones_db"):
                    logger.warning(
                        f"  registered_phones_db is None: {
                            self.pbx_core.registered_phones_db is None}"
                    )
            self._send_json([])

    def _handle_register_device(self):
        """Register a device for provisioning"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        logger = get_logger()

        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        try:
            body = self._get_body()
            mac = body.get("mac_address")
            extension = body.get("extension_number")
            vendor = body.get("vendor")
            model = body.get("model")

            if not all([mac, extension, vendor, model]):
                self._send_json({"error": "Missing required fields"}, 400)
                return

            device = self.pbx_core.phone_provisioning.register_device(mac, extension, vendor, model)

            # Automatically trigger phone reboot after registration
            # This ensures the phone fetches its fresh configuration
            # immediately
            reboot_triggered = False
            try:
                ext = self.pbx_core.extension_registry.get(extension)
                if ext and ext.registered:
                    logger.info(
                        f"Auto-provisioning: Automatically rebooting phone for extension {extension} after device registration"
                    )
                    reboot_triggered = self.pbx_core.phone_provisioning.reboot_phone(
                        extension, self.pbx_core.sip_server
                    )
                    if reboot_triggered:
                        logger.info(
                            f"Auto-provisioning: Successfully triggered reboot for extension {extension}"
                        )
                    else:
                        logger.info(
                            f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot"
                        )
                else:
                    logger.info(
                        f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot"
                    )
            except Exception as reboot_error:
                logger.warning(
                    f"Auto-provisioning: Could not auto-reboot phone for extension {extension}: {reboot_error}"
                )
                # Don't fail the registration if reboot fails

            response = {"success": True, "device": device.to_dict()}
            if reboot_triggered:
                response["reboot_triggered"] = True
                response["message"] = "Device registered and phone reboot triggered automatically"
            else:
                response["reboot_triggered"] = False
                response["message"] = "Device registered. Phone will fetch config on next boot."

            self._send_json(response)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_unregister_device(self, mac):
        """Unregister a device"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        try:
            success = self.pbx_core.phone_provisioning.unregister_device(mac)
            if success:
                self._send_json({"success": True, "message": "Device unregistered"})
            else:
                self._send_json({"error": "Device not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_set_static_ip(self, mac):
        """Set static IP for a device"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        try:
            body = self._get_body()
            static_ip = body.get("static_ip")

            if not static_ip:
                self._send_json({"error": "Missing static_ip field"}, 400)
                return

            success, message = self.pbx_core.phone_provisioning.set_static_ip(mac, static_ip)
            if success:
                self._send_json({"success": True, "message": message})
            else:
                self._send_json({"error": message}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_provisioning_request(self, path):
        """Handle phone provisioning config request"""
        logger = get_logger()

        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            logger.error("Phone provisioning not enabled but provisioning request received")
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        try:
            # Extract MAC address from path: /provision/{mac}.cfg
            filename = path.split("/")[-1]
            mac = filename.replace(".cfg", "")

            # Gather request information for logging
            request_info = {
                "ip": self.client_address[0] if self.client_address else "Unknown",
                "user_agent": self.headers.get("User-Agent", "Unknown"),
                "path": path,
            }

            logger.info(
                f"Provisioning config request: path={path}, IP={
                    request_info['ip']}"
            )

            # Detect if MAC is a literal placeholder (misconfiguration)
            # Examples: {mac}, {MAC} - these indicate the phone didn't substitute its actual MAC
            # Note: $mac and $MA are not checked here - those are the CORRECT
            # variable formats
            if mac in MAC_ADDRESS_PLACEHOLDERS:
                logger.error(
                    f"CONFIGURATION ERROR: Phone requested provisioning with placeholder '{mac}' instead of actual MAC address"
                )
                logger.error(f"  Request from IP: {request_info['ip']}")
                logger.error(f"  User-Agent: {request_info['user_agent']}")
                logger.error(f"")
                logger.error(f"  ⚠️  ROOT CAUSE: Phone is configured with wrong MAC variable format")
                logger.error(f"")
                logger.error(
                    f"  📋 SOLUTION: Update provisioning URL to use correct MAC variable for your phone:"
                )
                logger.error(f"")

                # Get provisioning URL information
                protocol, server_ip, port, base_url = self._get_provisioning_url_info()

                # Detect vendor from User-Agent and provide specific guidance
                user_agent = request_info["user_agent"].lower()
                if "zultys" in user_agent:
                    logger.error(
                        f"  ✓ Zultys Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                    )
                    logger.error(f"    Configure in: Phone Menu → Setup → Network → Provisioning")
                    logger.error(
                        f"    Or DHCP Option 66: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                    )
                elif "yealink" in user_agent:
                    logger.error(
                        f"  ✓ Yealink Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                    )
                    logger.error(f"    Configure in: Web Interface → Settings → Auto Provision")
                elif "polycom" in user_agent:
                    logger.error(
                        f"  ✓ Polycom Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                    )
                    logger.error(
                        f"    Configure in: Web Interface → Settings → Provisioning Server"
                    )
                elif "cisco" in user_agent:
                    logger.error(
                        f"  ✓ Cisco Phones - Use: {protocol}://{server_ip}:{port}/provision/$MA.cfg"
                    )
                    logger.error(f"    Note: Cisco uses $MA instead of $mac")
                    logger.error(
                        f"    Configure in: Web Interface → Admin Login → Voice → Provisioning"
                    )
                elif "grandstream" in user_agent:
                    logger.error(
                        f"  ✓ Grandstream Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                    )
                    logger.error(
                        f"    Configure in: Web Interface → Maintenance → Upgrade and Provisioning"
                    )
                else:
                    logger.error(f"  Common MAC variable formats by vendor:")
                    logger.error(f"    • Zultys, Yealink, Polycom, Grandstream: $mac")
                    logger.error(f"    • Cisco: $MA")
                logger.error(f"")
                logger.error(
                    f"  📖 See PHONE_PROVISIONING.md for detailed vendor-specific instructions"
                )

                self._send_json(
                    {
                        "error": "Configuration error: MAC address placeholder detected",
                        "details": f'Phone is using placeholder "{mac}" instead of actual MAC. Update provisioning URL to use correct MAC variable format for your phone vendor.',
                    },
                    400,
                )
                return

            logger.info(f"  MAC address from request: {mac}")

            # Generate configuration
            config_content, content_type = self.pbx_core.phone_provisioning.generate_config(
                mac, self.pbx_core.extension_registry, request_info
            )

            if config_content:
                self._set_headers(content_type=content_type)
                self.wfile.write(config_content.encode())
                logger.info(
                    f"✓ Provisioning config delivered: {
                        len(config_content)} bytes to {
                        request_info['ip']}"
                )

                # Store IP to MAC mapping in database for admin panel tracking
                # This allows correlation between provisioned devices and their
                # network addresses
                if (
                    self.pbx_core
                    and hasattr(self.pbx_core, "registered_phones_db")
                    and self.pbx_core.registered_phones_db
                ):
                    try:
                        # Get the device to find its extension number
                        device = self.pbx_core.phone_provisioning.get_device(mac)
                        if device:
                            # Store/update the IP-MAC-Extension mapping
                            normalized_mac = normalize_mac_address(mac)

                            # Store the mapping in the database
                            success, stored_mac = self.pbx_core.registered_phones_db.register_phone(
                                extension_number=device.extension_number,
                                ip_address=request_info["ip"],
                                mac_address=normalized_mac,
                                user_agent=request_info.get("user_agent", "Unknown"),
                                contact_uri=None,  # Not available during provisioning request
                            )
                            if success:
                                # stored_mac should equal normalized_mac since
                                # we're providing it
                                logger.info(
                                    f"  Stored IP-MAC mapping: {
                                        request_info['ip']} → {stored_mac} (ext {
                                        device.extension_number})"
                                )
                    except Exception as e:
                        # Don't fail provisioning if database storage fails
                        logger.warning(f"  Could not store IP-MAC mapping in database: {e}")
            else:
                logger.warning(
                    f"✗ Provisioning failed for MAC {mac} from IP {
                        request_info['ip']}"
                )
                logger.warning(f"  Reason: Device not registered or template not found")
                logger.warning(f"  See detailed error messages above for troubleshooting guidance")

                # Get provisioning URL information
                protocol, server_ip, port, base_url = self._get_provisioning_url_info()

                logger.warning(f"  To register this device:")
                logger.warning(f"    curl -X POST {base_url}/api/provisioning/devices \\")
                logger.warning(f"      -H 'Content-Type: application/json' \\")
                logger.warning(
                    f'      -d \'{{"mac_address":"{mac}","extension_number":"XXXX","vendor":"VENDOR","model":"MODEL"}}\''
                )
                self._send_json({"error": "Device or template not found"}, 404)
        except Exception as e:
            logger.error(f"Error handling provisioning request: {e}")
            logger.error(f"  Path: {path}")
            logger.error(f"  Traceback: {traceback.format_exc()}")
            self._send_json({"error": str(e)}, 500)

    def _handle_admin_redirect(self):
        """Redirect to admin panel"""
        self.send_response(302)
        self.send_header("Location", "/admin/index.html")
        self.end_headers()

    def _handle_static_file(self, path):
        """Serve static files from admin directory"""
        try:
            # Remove /admin prefix to get relative path
            file_path = path.replace("/admin/", "", 1)
            full_path = os.path.join(ADMIN_DIR, file_path)

            # Prevent directory traversal attacks - ensure path stays within
            # admin directory
            real_admin_dir = os.path.realpath(ADMIN_DIR)
            real_full_path = os.path.realpath(full_path)

            if not real_full_path.startswith(real_admin_dir):
                self._send_json({"error": "Access denied"}, 403)
                return

            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                self._send_json({"error": "File not found"}, 404)
                return

            # Determine content type
            content_type, _ = mimetypes.guess_type(full_path)
            if not content_type:
                content_type = "application/octet-stream"

            # Read and serve file
            with open(full_path, "rb") as f:
                content = f.read()

            self._set_headers(content_type=content_type)
            self.wfile.write(content)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _get_auth_token(self):
        """Extract authentication token from request headers"""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        return None

    def _verify_authentication(self):
        """
        Verify authentication token and return payload

        Returns:
            Tuple of (is_authenticated, payload)
            - is_authenticated: True if token is valid
            - payload: Token payload if valid, None otherwise
        """
        token = self._get_auth_token()
        if not token:
            return False, None

        from pbx.utils.session_token import get_session_token_manager

        token_manager = get_session_token_manager()
        return token_manager.verify_token(token)

    def _require_admin(self):
        """
        Check if current user has admin privileges

        Returns:
            Tuple of (is_admin, payload)
            - is_admin: True if user is authenticated and has admin privileges
            - payload: Token payload if authenticated, None otherwise
        """
        is_authenticated, payload = self._verify_authentication()
        if not is_authenticated:
            return False, None

        return payload.get("is_admin", False), payload

    def _handle_login(self):
        """Authenticate extension and return session token"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            body = self._get_body()
            extension_number = body.get("extension")
            password = body.get("password")

            if not extension_number or not password:
                self._send_json({"error": "Extension and password required"}, 400)
                return

            # Get extension from database
            if not self.pbx_core.extension_db:
                self._send_json({"error": "Database not available"}, 500)
                return

            ext = self.pbx_core.extension_db.get(extension_number)
            if not ext:
                self._send_json({"error": "Invalid credentials"}, 401)
                return

            # Verify password using voicemail PIN
            # For Phase 3 authentication, the login password is the user's voicemail PIN
            # This provides a single credential for users to remember (their voicemail PIN)
            voicemail_pin_hash = ext.get("voicemail_pin_hash", "")

            # Check if voicemail PIN is hashed (contains salt) or plain text
            # For backwards compatibility, we support both
            from pbx.utils.encryption import get_encryption

            fips_mode = self.pbx_core.config.get("security.fips_mode", False)
            encryption = get_encryption(fips_mode)

            voicemail_pin_salt = ext.get("voicemail_pin_salt")
            if voicemail_pin_salt:
                # Voicemail PIN is hashed - verify using encryption
                if not encryption.verify_password(password, voicemail_pin_hash, voicemail_pin_salt):
                    self._send_json({"error": "Invalid credentials"}, 401)
                    return
            else:
                # Voicemail PIN is plain text (legacy) or not set
                # If no voicemail PIN is configured, deny access for security
                if not voicemail_pin_hash or voicemail_pin_hash == "":
                    self._send_json({"error": "Invalid credentials"}, 401)
                    return
                import secrets

                # Ensure both values are strings before comparison
                password_str = password if isinstance(password, str) else password.decode("utf-8")
                voicemail_pin_str = (
                    voicemail_pin_hash
                    if isinstance(voicemail_pin_hash, str)
                    else str(voicemail_pin_hash)
                )
                if not secrets.compare_digest(
                    password_str.encode("utf-8"), voicemail_pin_str.encode("utf-8")
                ):
                    self._send_json({"error": "Invalid credentials"}, 401)
                    return

            # Generate session token
            from pbx.utils.session_token import get_session_token_manager

            token_manager = get_session_token_manager()
            token = token_manager.generate_token(
                extension=extension_number,
                is_admin=ext.get("is_admin", False),
                name=ext.get("name"),
                email=ext.get("email"),
            )

            self._send_json(
                {
                    "success": True,
                    "token": token,
                    "extension": extension_number,
                    "is_admin": ext.get("is_admin", False),
                    "name": ext.get("name", "User"),
                    "email": ext.get("email", ""),
                }
            )

        except Exception as e:
            self.logger.error(f"Login error: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            self._send_json({"error": "Authentication failed"}, 500)

    def _handle_logout(self):
        """Handle logout (client-side token removal)"""
        # Logout is primarily handled client-side by removing the token
        # This endpoint is here for completeness and future server-side token invalidation
        self._send_json({"success": True, "message": "Logged out successfully"})

    def _handle_get_config(self):
        """Get current configuration"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        if self.pbx_core:
            config_data = {
                "smtp": {
                    "host": self.pbx_core.config.get("voicemail.smtp.host", ""),
                    "port": self.pbx_core.config.get("voicemail.smtp.port", 587),
                    "username": self.pbx_core.config.get("voicemail.smtp.username", ""),
                },
                "email": {
                    "from_address": self.pbx_core.config.get("voicemail.email.from_address", "")
                },
                "email_notifications": self.pbx_core.config.get(
                    "voicemail.email_notifications", False
                ),
            }
            self._send_json(config_data)
        else:
            self._send_json({"error": "PBX not initialized"}, 500)

    def _handle_add_extension(self):
        """Add a new extension"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            body = self._get_body()
            number = body.get("number")
            name = body.get("name")
            email = body.get("email")
            password = body.get("password")
            allow_external = body.get("allow_external", True)
            voicemail_pin = body.get("voicemail_pin")
            is_admin = body.get("is_admin", False)

            if not all([number, name, password]):
                self._send_json({"error": "Missing required fields"}, 400)
                return

            # SECURITY: Validate voicemail PIN is provided
            if not voicemail_pin:
                self._send_json({"error": "Voicemail PIN is required for security"}, 400)
                return

            # Validate voicemail PIN format (4-6 digits)
            if (
                not str(voicemail_pin).isdigit()
                or len(str(voicemail_pin)) < 4
                or len(str(voicemail_pin)) > 6
            ):
                self._send_json({"error": "Voicemail PIN must be 4-6 digits"}, 400)
                return

            # Validate extension number format (4 digits)
            if not str(number).isdigit() or len(str(number)) != 4:
                self._send_json({"error": "Extension number must be 4 digits"}, 400)
                return

            # Validate password strength (minimum 8 characters)
            if len(password) < 8:
                self._send_json({"error": "Password must be at least 8 characters"}, 400)
                return

            # Validate email format if provided
            if email and not Config.validate_email(email):
                self._send_json({"error": "Invalid email format"}, 400)
                return

            # Check if extension already exists
            if self.pbx_core.extension_registry.get(number):
                self._send_json({"error": "Extension already exists"}, 400)
                return

            # Try to add to database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Add to database
                # NOTE: For production, use FIPS-compliant hashing via pbx.utils.encryption.FIPSEncryption.hash_password()
                # Currently storing plain password; system supports both plain
                # and hashed passwords
                password_hash = password
                success = self.pbx_core.extension_db.add(
                    number=number,
                    name=name,
                    password_hash=password_hash,
                    email=email if email else None,
                    allow_external=allow_external,
                    voicemail_pin=voicemail_pin if voicemail_pin else None,
                    ad_synced=False,
                    ad_username=None,
                    is_admin=is_admin,
                )
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.add_extension(
                    number, name, email, password, allow_external
                )

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({"success": True, "message": "Extension added successfully"})
            else:
                self._send_json({"error": "Failed to add extension"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_extension(self, number):
        """Update an existing extension"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            body = self._get_body()
            name = body.get("name")
            email = body.get("email")
            password = body.get("password")  # Optional
            allow_external = body.get("allow_external")
            voicemail_pin = body.get("voicemail_pin")
            is_admin = body.get("is_admin")

            # Check if extension exists
            extension = self.pbx_core.extension_registry.get(number)
            if not extension:
                self._send_json({"error": "Extension not found"}, 404)
                return

            # Validate password strength if provided (minimum 8 characters)
            if password and len(password) < 8:
                self._send_json({"error": "Password must be at least 8 characters"}, 400)
                return

            # SECURITY: Validate voicemail PIN format if provided (4-6 digits)
            if voicemail_pin is not None:
                if (
                    not str(voicemail_pin).isdigit()
                    or len(str(voicemail_pin)) < 4
                    or len(str(voicemail_pin)) > 6
                ):
                    self._send_json({"error": "Voicemail PIN must be 4-6 digits"}, 400)
                    return

            # Validate email format if provided
            if email and not Config.validate_email(email):
                self._send_json({"error": "Invalid email format"}, 400)
                return

            # Try to update in database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Update in database
                # NOTE: For production, use FIPS-compliant hashing via pbx.utils.encryption.FIPSEncryption.hash_password()
                # Currently storing plain password; system supports both plain
                # and hashed passwords
                password_hash = password if password else None
                success = self.pbx_core.extension_db.update(
                    number=number,
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    allow_external=allow_external,
                    voicemail_pin=voicemail_pin,
                    is_admin=is_admin,
                )
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.update_extension(
                    number, name, email, password, allow_external
                )

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({"success": True, "message": "Extension updated successfully"})
            else:
                self._send_json({"error": "Failed to update extension"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_extension(self, number):
        """Delete an extension"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            # Check if extension exists
            extension = self.pbx_core.extension_registry.get(number)
            if not extension:
                self._send_json({"error": "Extension not found"}, 404)
                return

            # Try to delete from database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Delete from database
                success = self.pbx_core.extension_db.delete(number)
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.delete_extension(number)

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({"success": True, "message": "Extension deleted successfully"})
            else:
                self._send_json({"error": "Failed to delete extension"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_config(self):
        """Update system configuration"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            body = self._get_body()

            # Update configuration
            success = self.pbx_core.config.update_email_config(body)

            if success:
                self._send_json(
                    {
                        "success": True,
                        "message": "Configuration updated successfully. Restart required.",
                    }
                )
            else:
                self._send_json({"error": "Failed to update configuration"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_full_config(self):
        """Get full system configuration for admin panel"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            # Return comprehensive configuration for the admin panel
            config_data = {
                "server": {
                    "sip_port": self.pbx_core.config.get("server.sip_port", 5060),
                    "external_ip": self.pbx_core.config.get("server.external_ip", ""),
                    "server_name": self.pbx_core.config.get("server.server_name", "PBX System"),
                },
                "api": {
                    "port": self.pbx_core.config.get("api.port", 8080),
                    "ssl": {
                        "enabled": self.pbx_core.config.get("api.ssl.enabled", False),
                        "cert_file": self.pbx_core.config.get(
                            "api.ssl.cert_file", "certs/server.crt"
                        ),
                        "key_file": self.pbx_core.config.get(
                            "api.ssl.key_file", "certs/server.key"
                        ),
                    },
                },
                "features": {
                    "call_recording": self.pbx_core.config.get("features.call_recording", True),
                    "call_transfer": self.pbx_core.config.get("features.call_transfer", True),
                    "call_hold": self.pbx_core.config.get("features.call_hold", True),
                    "conference": self.pbx_core.config.get("features.conference", True),
                    "voicemail": self.pbx_core.config.get("features.voicemail", True),
                    "call_parking": self.pbx_core.config.get("features.call_parking", True),
                    "call_queues": self.pbx_core.config.get("features.call_queues", True),
                    "presence": self.pbx_core.config.get("features.presence", True),
                    "music_on_hold": self.pbx_core.config.get("features.music_on_hold", True),
                    "auto_attendant": self.pbx_core.config.get("features.auto_attendant", True),
                    "webrtc": {
                        "enabled": self.pbx_core.config.get("features.webrtc.enabled", True)
                    },
                    "webhooks": {
                        "enabled": self.pbx_core.config.get("features.webhooks.enabled", False)
                    },
                    "crm_integration": {
                        "enabled": self.pbx_core.config.get(
                            "features.crm_integration.enabled", True
                        )
                    },
                    "hot_desking": {
                        "enabled": self.pbx_core.config.get("features.hot_desking.enabled", True),
                        "require_pin": self.pbx_core.config.get(
                            "features.hot_desking.require_pin", True
                        ),
                    },
                    "voicemail_transcription": {
                        "enabled": self.pbx_core.config.get(
                            "features.voicemail_transcription.enabled", True
                        )
                    },
                },
                "voicemail": {
                    "max_message_duration": self.pbx_core.config.get(
                        "voicemail.max_message_duration", 180
                    ),
                    "max_greeting_duration": self.pbx_core.config.get(
                        "voicemail.max_greeting_duration", 30
                    ),
                    "no_answer_timeout": self.pbx_core.config.get(
                        "voicemail.no_answer_timeout", 30
                    ),
                    "allow_custom_greetings": self.pbx_core.config.get(
                        "voicemail.allow_custom_greetings", True
                    ),
                    "email_notifications": self.pbx_core.config.get(
                        "voicemail.email_notifications", True
                    ),
                    "smtp": {
                        "host": self.pbx_core.config.get("voicemail.smtp.host", ""),
                        "port": self.pbx_core.config.get("voicemail.smtp.port", 587),
                        "use_tls": self.pbx_core.config.get("voicemail.smtp.use_tls", True),
                        "username": self.pbx_core.config.get("voicemail.smtp.username", ""),
                    },
                    "email": {
                        "from_address": self.pbx_core.config.get(
                            "voicemail.email.from_address", ""
                        ),
                        "from_name": self.pbx_core.config.get(
                            "voicemail.email.from_name", "PBX Voicemail"
                        ),
                    },
                },
                "recording": {
                    "auto_record": self.pbx_core.config.get("recording.auto_record", False),
                    "format": self.pbx_core.config.get("recording.format", "wav"),
                    "storage_path": self.pbx_core.config.get(
                        "recording.storage_path", "recordings"
                    ),
                },
                "security": {
                    "password": {
                        "min_length": self.pbx_core.config.get("security.password.min_length", 12),
                        "require_uppercase": self.pbx_core.config.get(
                            "security.password.require_uppercase", True
                        ),
                        "require_lowercase": self.pbx_core.config.get(
                            "security.password.require_lowercase", True
                        ),
                        "require_digit": self.pbx_core.config.get(
                            "security.password.require_digit", True
                        ),
                        "require_special": self.pbx_core.config.get(
                            "security.password.require_special", True
                        ),
                    },
                    "rate_limit": {
                        "max_attempts": self.pbx_core.config.get(
                            "security.rate_limit.max_attempts", 5
                        ),
                        "lockout_duration": self.pbx_core.config.get(
                            "security.rate_limit.lockout_duration", 900
                        ),
                    },
                    "fips_mode": self.pbx_core.config.get("security.fips_mode", True),
                },
                "conference": {
                    "max_participants": self.pbx_core.config.get("conference.max_participants", 50),
                    "record_conferences": self.pbx_core.config.get(
                        "conference.record_conferences", False
                    ),
                },
            }

            self._send_json(config_data)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_config_section(self):
        """Update a specific section of system configuration"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            body = self._get_body()
            section = body.get("section")
            data = body.get("data")

            if section is None or data is None:
                self._send_json({"error": "Missing section or data"}, 400)
                return

            # Update the configuration section
            # Use config.get() to safely retrieve section with defaults
            current_section = self.pbx_core.config.config.get(section, {})

            # Deep merge the data into the section
            def deep_merge(target, source):
                """Deep merge source dict into target dict"""
                for key, value in source.items():
                    if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                        deep_merge(target[key], value)
                    else:
                        target[key] = value
                return target

            # Create merged section and update config
            merged_section = deep_merge(
                current_section.copy() if isinstance(current_section, dict) else {}, data
            )
            self.pbx_core.config.config[section] = merged_section

            # Save configuration
            success = self.pbx_core.config.save()

            if success:
                self._send_json(
                    {
                        "success": True,
                        "message": "Configuration updated successfully. Restart may be required for some changes.",
                    }
                )
            else:
                self._send_json({"error": "Failed to save configuration"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_dtmf_config(self):
        """Get DTMF configuration"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            dtmf_config = self.pbx_core.config.get_dtmf_config()
            if dtmf_config is not None:
                self._send_json(dtmf_config)
            else:
                self._send_json({"error": "Failed to get DTMF configuration"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_dtmf_config(self):
        """Update DTMF configuration"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            body = self._get_body()

            # Update DTMF configuration
            success = self.pbx_core.config.update_dtmf_config(body)

            if success:
                self._send_json(
                    {
                        "success": True,
                        "message": "DTMF configuration updated successfully. PBX restart required for changes to take effect.",
                    }
                )
            else:
                self._send_json({"error": "Failed to update DTMF configuration"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_ssl_status(self):
        """Get SSL/HTTPS configuration status"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            ssl_config = self.pbx_core.config.get("api.ssl", {})
            cert_file = ssl_config.get("cert_file", "certs/server.crt")
            key_file = ssl_config.get("key_file", "certs/server.key")

            # Check if certificate files exist
            cert_exists = os.path.exists(cert_file)
            key_exists = os.path.exists(key_file)

            # Get certificate details if it exists
            cert_details = None
            if cert_exists and SSL_GENERATION_AVAILABLE:
                try:
                    with open(cert_file, "rb") as f:
                        cert_data = f.read()
                        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

                        now = datetime.now(timezone.utc)
                        cert_details = {
                            "subject": cert.subject.rfc4514_string(),
                            "issuer": cert.issuer.rfc4514_string(),
                            "valid_from": cert.not_valid_before.isoformat(),
                            "valid_until": cert.not_valid_after.isoformat(),
                            "is_expired": cert.not_valid_after < now,
                            "days_until_expiry": (cert.not_valid_after - now).days,
                            "serial_number": str(cert.serial_number),
                        }
                except Exception as e:
                    self.logger.warning(f"Failed to parse certificate: {e}")

            status_data = {
                "enabled": ssl_config.get("enabled", False),
                "cert_file": cert_file,
                "key_file": key_file,
                "cert_exists": cert_exists,
                "key_exists": key_exists,
                "cert_details": cert_details,
                "ca": {
                    "enabled": ssl_config.get("ca", {}).get("enabled", False),
                    "server_url": ssl_config.get("ca", {}).get("server_url", ""),
                },
            }

            self._send_json(status_data)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_generate_ssl_certificate(self):
        """Generate self-signed SSL certificate"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            body = self._get_body() or {}

            # Get parameters
            hostname = body.get(
                "hostname", self.pbx_core.config.get("server.external_ip", "localhost")
            )
            days_valid = body.get("days_valid", 365)
            cert_dir = body.get("cert_dir", "certs")

            # Validate parameters
            if not hostname:
                hostname = "localhost"

            if not isinstance(days_valid, int) or days_valid < 1 or days_valid > 3650:
                days_valid = 365

            self.logger.info(f"Generating self-signed SSL certificate for {hostname}")

            # Check if SSL generation is available
            if not SSL_GENERATION_AVAILABLE:
                self._send_json(
                    {
                        "error": "Required cryptography library not available",
                        "details": "Install with: pip install cryptography",
                    },
                    500,
                )
                return

            # Create cert directory if it doesn't exist
            cert_path = Path(cert_dir)
            cert_path.mkdir(exist_ok=True)

            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Generate certificate
            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PBX System"),
                    x509.NameAttribute(NameOID.COMMON_NAME, hostname),
                ]
            )

            # Build list of Subject Alternative Names
            san_list = [
                x509.DNSName(hostname),
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]

            # Try to add the hostname as an IP address if it's a valid IP
            try:
                ip = ipaddress.ip_address(hostname)
                san_list.append(x509.IPAddress(ip))
            except ValueError:
                # Not an IP address, it's a hostname
                pass

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.now(timezone.utc))
                .not_valid_after(datetime.now(timezone.utc) + timedelta(days=days_valid))
                .add_extension(
                    x509.SubjectAlternativeName(san_list),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # Write private key to file
            key_file = cert_path / "server.key"
            with open(key_file, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

            # Set restrictive permissions on private key
            os.chmod(key_file, 0o600)

            # Write certificate to file
            cert_file = cert_path / "server.crt"
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            self.logger.info(f"SSL certificate generated successfully: {cert_file}")

            # Update configuration to enable SSL
            ssl_config = self.pbx_core.config.get("api.ssl", {})
            ssl_config["enabled"] = True
            ssl_config["cert_file"] = str(cert_file)
            ssl_config["key_file"] = str(key_file)

            self.pbx_core.config.config.setdefault("api", {})["ssl"] = ssl_config
            self.pbx_core.config.save()

            self._send_json(
                {
                    "success": True,
                    "message": "SSL certificate generated successfully. Server restart required to enable HTTPS.",
                    "cert_file": str(cert_file),
                    "key_file": str(key_file),
                    "hostname": hostname,
                    "valid_days": days_valid,
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to generate SSL certificate: {e}")
            import traceback

            traceback.print_exc()
            self._send_json({"error": str(e)}, 500)

    def _handle_get_voicemail(self, path):
        """Get voicemail messages for an extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail not enabled"}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension} or
            # /api/voicemail/{extension}/{message_id}
            parts = path.split("/")
            if len(parts) < 4:
                self._send_json({"error": "Invalid path"}, 400)
                return

            extension = parts[3]

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            if len(parts) == 4:
                # List all messages
                messages = mailbox.get_messages()
                data = []
                for msg in messages:
                    data.append(
                        {
                            "id": msg["id"],
                            "caller_id": msg["caller_id"],
                            "timestamp": msg["timestamp"].isoformat() if msg["timestamp"] else None,
                            "listened": msg["listened"],
                            "duration": msg["duration"],
                        }
                    )
                self._send_json({"messages": data})
            elif len(parts) == 5:
                # Get specific message or download audio
                message_id = parts[4]

                # Find message
                message = None
                for msg in mailbox.get_messages():
                    if msg["id"] == message_id:
                        message = msg
                        break

                if not message:
                    self._send_json({"error": "Message not found"}, 404)
                    return

                # Check if request is for metadata only (via query parameter)
                # Use self.path to get the full request URL with query string
                query_params = parse_qs(urlparse(self.path).query)
                if query_params.get("metadata", [False])[0] in ["true", "1", True]:
                    # Return message metadata as JSON
                    self._send_json(
                        {
                            "id": message["id"],
                            "caller_id": message["caller_id"],
                            "timestamp": (
                                message["timestamp"].isoformat() if message["timestamp"] else None
                            ),
                            "listened": message["listened"],
                            "duration": message["duration"],
                            "file_path": message["file_path"],
                        }
                    )
                else:
                    # Default: Serve audio file for playback in admin panel
                    if os.path.exists(message["file_path"]):
                        self._set_headers(content_type="audio/wav")
                        with open(message["file_path"], "rb") as f:
                            self.wfile.write(f.read())
                    else:
                        self._send_json({"error": "Audio file not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_voicemail(self, path):
        """Update voicemail settings (mark as read, update PIN)"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail not enabled"}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension}/pin or
            # /api/voicemail/{extension}/{message_id}/mark-read
            parts = path.split("/")
            if len(parts) < 4:
                self._send_json({"error": "Invalid path"}, 400)
                return

            extension = parts[3]
            body = self._get_body()

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            if len(parts) == 5 and parts[4] == "pin":
                # Update PIN
                pin = body.get("pin")
                if not pin:
                    self._send_json({"error": "PIN required"}, 400)
                    return

                if mailbox.set_pin(pin):
                    # Also update in config
                    self.pbx_core.config.update_voicemail_pin(extension, pin)
                    self._send_json({"success": True, "message": "PIN updated successfully"})
                else:
                    self._send_json({"error": "Invalid PIN format. Must be 4 digits."}, 400)
            elif len(parts) == 6 and parts[5] == "mark-read":
                # Mark message as read
                message_id = parts[4]
                mailbox.mark_listened(message_id)
                self._send_json({"success": True, "message": "Message marked as read"})
            else:
                self._send_json({"error": "Invalid operation"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_voicemail(self, path):
        """Delete voicemail message"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail not enabled"}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension}/{message_id}
            parts = path.split("/")
            if len(parts) != 5:
                self._send_json({"error": "Invalid path"}, 400)
                return

            extension = parts[3]
            message_id = parts[4]

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            # Delete message
            if mailbox.delete_message(message_id):
                self._send_json({"success": True, "message": "Message deleted successfully"})
            else:
                self._send_json({"error": "Message not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_reboot_phone(self, extension):
        """Reboot a specific phone"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        try:
            # Send SIP NOTIFY to reboot the phone
            success = self.pbx_core.phone_provisioning.reboot_phone(
                extension, self.pbx_core.sip_server
            )

            if success:
                self._send_json(
                    {"success": True, "message": f"Reboot signal sent to extension {extension}"}
                )
            else:
                self._send_json(
                    {
                        "error": f"Failed to send reboot signal to extension {extension}. Extension may not be registered."
                    },
                    400,
                )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_ad_status(self):
        """Get Active Directory integration status"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            status = self.pbx_core.get_ad_integration_status()
            self._send_json(status)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_ad_sync(self):
        """Manually trigger Active Directory user synchronization"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        try:
            result = self.pbx_core.sync_ad_users()
            if result["success"]:
                self._send_json(
                    {
                        "success": True,
                        "message": f'Successfully synchronized {
                            result["synced_count"]} users from Active Directory',
                        "synced_count": result["synced_count"],
                    }
                )
            else:
                self._send_json({"success": False, "error": result["error"]}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_ad_search(self):
        """Search for users in Active Directory"""
        if not self.pbx_core:
            self._send_json({"error": "PBX not initialized"}, 500)
            return

        if not hasattr(self.pbx_core, "ad_integration") or not self.pbx_core.ad_integration:
            self._send_json({"error": "Active Directory integration not enabled"}, 500)
            return

        try:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            query = query_params.get("q", [""])[0]

            if not query:
                self._send_json({"error": 'Query parameter "q" is required'}, 400)
                return

            # Get max_results parameter (optional) with validation
            try:
                max_results = int(query_params.get("max_results", ["50"])[0])
                if max_results < 1 or max_results > 100:
                    self._send_json({"error": "max_results must be between 1 and 100"}, 400)
                    return
            except ValueError:
                self._send_json({"error": "max_results must be a valid integer"}, 400)
                return

            # Search AD users using the telephoneNumber attribute (and other
            # attributes)
            results = self.pbx_core.ad_integration.search_users(query, max_results)

            self._send_json({"success": True, "count": len(results), "results": results})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_reboot_phones(self):
        """Reboot all registered phones"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_provisioning"):
            self._send_json({"error": "Phone provisioning not enabled"}, 500)
            return

        try:
            # Send SIP NOTIFY to all registered phones
            results = self.pbx_core.phone_provisioning.reboot_all_phones(self.pbx_core.sip_server)

            self._send_json(
                {
                    "success": True,
                    "message": f'Rebooted {results["success_count"]} phones',
                    "rebooted": results["rebooted"],
                    "failed": results["failed"],
                    "success_count": results["success_count"],
                    "failed_count": results["failed_count"],
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def log_message(self, format, *args):
        """Override to use PBX logger"""
        pass  # Suppress default logging

    # Phone Book API handlers
    def _handle_get_phone_book(self):
        """Get all phone book entries"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_book"):
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        try:
            entries = self.pbx_core.phone_book.get_all_entries()
            self._send_json(entries)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_export_phone_book_xml(self):
        """Export phone book as XML (Yealink format)"""
        try:
            # Try to use phone book feature if available
            if (
                self.pbx_core
                and hasattr(self.pbx_core, "phone_book")
                and self.pbx_core.phone_book
                and self.pbx_core.phone_book.enabled
            ):
                xml_content = self.pbx_core.phone_book.export_xml()
            else:
                # Fallback: Generate from extension registry
                xml_content = self._generate_xml_from_extensions()

            self._set_headers(content_type="application/xml")
            self.wfile.write(xml_content.encode())
        except Exception as e:
            self.logger.error(f"Error exporting phone book XML: {e}")
            self._send_json({"error": str(e)}, 500)

    def _generate_xml_from_extensions(self):
        """Generate phone book XML from extension registry (fallback)"""
        if not self.pbx_core or not hasattr(self.pbx_core, "extension_registry"):
            return '<?xml version="1.0" encoding="UTF-8"?><YealinkIPPhoneDirectory><Title>Directory</Title></YealinkIPPhoneDirectory>'

        extensions = self.pbx_core.extension_registry.get_all()

        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append("<YealinkIPPhoneDirectory>")
        xml_lines.append("  <Title>Company Directory</Title>")

        for ext in sorted(extensions, key=lambda x: x.name):
            xml_lines.append("  <DirectoryEntry>")
            name = ext.name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            xml_lines.append(f"    <Name>{name}</Name>")
            xml_lines.append(f"    <Telephone>{ext.number}</Telephone>")
            xml_lines.append("  </DirectoryEntry>")

        xml_lines.append("</YealinkIPPhoneDirectory>")
        return "\n".join(xml_lines)

    def _handle_export_phone_book_cisco_xml(self):
        """Export phone book as Cisco XML format"""
        try:
            # Try to use phone book feature if available
            if (
                self.pbx_core
                and hasattr(self.pbx_core, "phone_book")
                and self.pbx_core.phone_book
                and self.pbx_core.phone_book.enabled
            ):
                xml_content = self.pbx_core.phone_book.export_cisco_xml()
            else:
                # Fallback: Generate from extension registry
                xml_content = self._generate_cisco_xml_from_extensions()

            self._set_headers(content_type="application/xml")
            self.wfile.write(xml_content.encode())
        except Exception as e:
            self.logger.error(f"Error exporting Cisco phone book XML: {e}")
            self._send_json({"error": str(e)}, 500)

    def _generate_cisco_xml_from_extensions(self):
        """Generate Cisco phone book XML from extension registry (fallback)"""
        if not self.pbx_core or not hasattr(self.pbx_core, "extension_registry"):
            return '<?xml version="1.0" encoding="UTF-8"?><CiscoIPPhoneDirectory><Title>Directory</Title></CiscoIPPhoneDirectory>'

        extensions = self.pbx_core.extension_registry.get_all()

        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append("<CiscoIPPhoneDirectory>")
        xml_lines.append("  <Title>Company Directory</Title>")
        xml_lines.append("  <Prompt>Select a contact</Prompt>")

        for ext in sorted(extensions, key=lambda x: x.name):
            xml_lines.append("  <DirectoryEntry>")
            name = ext.name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            xml_lines.append(f"    <Name>{name}</Name>")
            xml_lines.append(f"    <Telephone>{ext.number}</Telephone>")
            xml_lines.append("  </DirectoryEntry>")

        xml_lines.append("</CiscoIPPhoneDirectory>")
        return "\n".join(xml_lines)

    def _handle_export_phone_book_json(self):
        """Export phone book as JSON"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_book"):
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        try:
            json_content = self.pbx_core.phone_book.export_json()
            self._set_headers(content_type="application/json")
            self.wfile.write(json_content.encode())
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_search_phone_book(self):
        """Search phone book entries"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_book"):
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        try:
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            query = query_params.get("q", [""])[0]

            if not query:
                self._send_json({"error": 'Query parameter "q" is required'}, 400)
                return

            results = self.pbx_core.phone_book.search(query)
            self._send_json(results)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_add_phone_book_entry(self):
        """Add or update a phone book entry"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_book"):
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        try:
            data = self._get_body()
            extension = data.get("extension")
            name = data.get("name")

            if not extension or not name:
                self._send_json({"error": "Extension and name are required"}, 400)
                return

            success = self.pbx_core.phone_book.add_entry(
                extension=extension,
                name=name,
                department=data.get("department"),
                email=data.get("email"),
                mobile=data.get("mobile"),
                office_location=data.get("office_location"),
                ad_synced=data.get("ad_synced", False),
            )

            if success:
                self._send_json(
                    {"success": True, "message": f"Phone book entry added/updated: {extension}"}
                )
            else:
                self._send_json({"error": "Failed to add phone book entry"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_phone_book_entry(self, extension: str):
        """Delete a phone book entry"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_book"):
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        try:
            success = self.pbx_core.phone_book.remove_entry(extension)

            if success:
                self._send_json(
                    {"success": True, "message": f"Phone book entry deleted: {extension}"}
                )
            else:
                self._send_json({"error": "Failed to delete phone book entry"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_sync_phone_book(self):
        """Sync phone book from Active Directory"""
        if not self.pbx_core or not hasattr(self.pbx_core, "phone_book"):
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({"error": "Phone book feature not enabled"}, 500)
            return

        if not hasattr(self.pbx_core, "ad_integration") or not self.pbx_core.ad_integration:
            self._send_json({"error": "Active Directory integration not enabled"}, 500)
            return

        try:
            synced_count = self.pbx_core.phone_book.sync_from_ad(
                self.pbx_core.ad_integration, self.pbx_core.extension_registry
            )

            self._send_json(
                {
                    "success": True,
                    "message": f"Phone book synced from Active Directory",
                    "synced_count": synced_count,
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # Paging System API handlers
    def _handle_get_paging_zones(self):
        """Get all paging zones"""
        if not self.pbx_core or not hasattr(self.pbx_core, "paging_system"):
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        try:
            zones = self.pbx_core.paging_system.get_zones()
            self._send_json(zones)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_paging_devices(self):
        """Get all paging DAC devices"""
        if not self.pbx_core or not hasattr(self.pbx_core, "paging_system"):
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        try:
            devices = self.pbx_core.paging_system.get_dac_devices()
            self._send_json(devices)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_active_pages(self):
        """Get all active paging sessions"""
        if not self.pbx_core or not hasattr(self.pbx_core, "paging_system"):
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        try:
            active_pages = self.pbx_core.paging_system.get_active_pages()
            self._send_json(active_pages)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_add_paging_zone(self):
        """Add a paging zone"""
        if not self.pbx_core or not hasattr(self.pbx_core, "paging_system"):
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        try:
            data = self._get_body()
            extension = data.get("extension")
            name = data.get("name")

            if not extension or not name:
                self._send_json({"error": "Extension and name are required"}, 400)
                return

            success = self.pbx_core.paging_system.add_zone(
                extension=extension,
                name=name,
                description=data.get("description"),
                dac_device=data.get("dac_device"),
            )

            if success:
                self._send_json({"success": True, "message": f"Paging zone added: {extension}"})
            else:
                self._send_json({"error": "Failed to add paging zone"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_paging_zone(self, extension: str):
        """Delete a paging zone"""
        if not self.pbx_core or not hasattr(self.pbx_core, "paging_system"):
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        try:
            success = self.pbx_core.paging_system.remove_zone(extension)

            if success:
                self._send_json({"success": True, "message": f"Paging zone deleted: {extension}"})
            else:
                self._send_json({"error": "Failed to delete paging zone"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_configure_paging_device(self):
        """Configure a paging DAC device"""
        if not self.pbx_core or not hasattr(self.pbx_core, "paging_system"):
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({"error": "Paging system not enabled"}, 500)
            return

        try:
            data = self._get_body()
            device_id = data.get("device_id")
            device_type = data.get("device_type")

            if not device_id or not device_type:
                self._send_json({"error": "device_id and device_type are required"}, 400)
                return

            success = self.pbx_core.paging_system.configure_dac_device(
                device_id=device_id,
                device_type=device_type,
                sip_uri=data.get("sip_uri"),
                ip_address=data.get("ip_address"),
                port=data.get("port", 5060),
            )

            if success:
                self._send_json({"success": True, "message": f"DAC device configured: {device_id}"})
            else:
                self._send_json({"error": "Failed to configure DAC device"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_webhooks(self):
        """Get all webhook subscriptions"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webhook_system"):
            self._send_json({"error": "Webhook system not available"}, 500)
            return

        try:
            subscriptions = self.pbx_core.webhook_system.get_subscriptions()
            self._send_json(subscriptions)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_add_webhook(self):
        """Add a webhook subscription"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webhook_system"):
            self._send_json({"error": "Webhook system not available"}, 500)
            return

        try:
            data = self._get_body()
            url = data.get("url")
            events = data.get("events", ["*"])
            secret = data.get("secret")
            headers = data.get("headers")

            if not url:
                self._send_json({"error": "URL is required"}, 400)
                return

            subscription = self.pbx_core.webhook_system.add_subscription(
                url=url, events=events, secret=secret, headers=headers
            )

            self._send_json(
                {
                    "success": True,
                    "message": f"Webhook subscription added: {url}",
                    "subscription": {
                        "url": subscription.url,
                        "events": subscription.events,
                        "enabled": subscription.enabled,
                    },
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_webhook(self, url: str):
        """Delete a webhook subscription"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webhook_system"):
            self._send_json({"error": "Webhook system not available"}, 500)
            return

        try:
            success = self.pbx_core.webhook_system.remove_subscription(url)

            if success:
                self._send_json(
                    {"success": True, "message": f"Webhook subscription deleted: {url}"}
                )
            else:
                self._send_json({"error": "Webhook subscription not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ========== WebRTC Handlers ==========

    def _handle_create_webrtc_session(self):
        """Create a new WebRTC session"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_signaling"):
            self._send_json({"error": "WebRTC not available"}, 500)
            return

        verbose_logging = getattr(self.pbx_core.webrtc_signaling, "verbose_logging", False)

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension = data.get("extension")

            if verbose_logging:
                self.logger.info(f"[VERBOSE] WebRTC session creation request:")
                self.logger.info(f"  Extension: {extension}")
                self.logger.info(f"  Client IP: {self.client_address[0]}")

            if not extension:
                self._send_json({"error": "Extension is required"}, 400)
                return

            # Verify extension exists (allow virtual extensions starting with
            # 'webrtc-' for browser-based calling)
            is_virtual_extension = extension.startswith("webrtc-")
            if not is_virtual_extension and not self.pbx_core.extension_registry.get_extension(
                extension
            ):
                if verbose_logging:
                    self.logger.warning(f"[VERBOSE] Extension not found in registry: {extension}")
                self._send_json({"error": "Extension not found"}, 404)
                return

            session = self.pbx_core.webrtc_signaling.create_session(extension)

            response_data = {
                "success": True,
                "session": session.to_dict(),
                "ice_servers": self.pbx_core.webrtc_signaling.get_ice_servers_config(),
            }

            if verbose_logging:
                self.logger.info(f"[VERBOSE] Session created successfully:")
                self.logger.info(f"  Session ID: {session.session_id}")
                self.logger.info(
                    f"  ICE servers configured: {len(response_data['ice_servers'].get('iceServers', []))}"
                )

            self._send_json(response_data)
        except Exception as e:
            if verbose_logging:
                self.logger.error(f"[VERBOSE] Error creating WebRTC session: {e}")
                import traceback

                self.logger.error(
                    f"[VERBOSE] Traceback:\n{
                        traceback.format_exc()}"
                )
            self._send_json({"error": str(e)}, 500)

    def _handle_webrtc_offer(self):
        """Handle WebRTC SDP offer"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_signaling"):
            self._send_json({"error": "WebRTC not available"}, 500)
            return

        verbose_logging = getattr(self.pbx_core.webrtc_signaling, "verbose_logging", False)

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            session_id = data.get("session_id")
            sdp = data.get("sdp")

            if verbose_logging:
                self.logger.info(f"[VERBOSE] WebRTC offer received:")
                self.logger.info(f"  Session ID: {session_id}")
                self.logger.info(
                    f"  SDP length: {
                        len(sdp) if sdp else 0} bytes"
                )
                self.logger.info(f"  Client IP: {self.client_address[0]}")

            if not session_id or not sdp:
                self._send_json({"error": "session_id and sdp are required"}, 400)
                return

            success = self.pbx_core.webrtc_signaling.handle_offer(session_id, sdp)

            if success:
                if verbose_logging:
                    self.logger.info(f"[VERBOSE] Offer handled successfully")
                self._send_json({"success": True, "message": "Offer received"})
            else:
                if verbose_logging:
                    self.logger.warning(f"[VERBOSE] Session not found for offer")
                self._send_json({"error": "Session not found"}, 404)
        except Exception as e:
            if verbose_logging:
                self.logger.error(f"[VERBOSE] Error handling WebRTC offer: {e}")
                import traceback

                self.logger.error(
                    f"[VERBOSE] Traceback:\n{
                        traceback.format_exc()}"
                )
            self._send_json({"error": str(e)}, 500)

    def _handle_webrtc_answer(self):
        """Handle WebRTC SDP answer"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_signaling"):
            self._send_json({"error": "WebRTC not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            session_id = data.get("session_id")
            sdp = data.get("sdp")

            if not session_id or not sdp:
                self._send_json({"error": "session_id and sdp are required"}, 400)
                return

            success = self.pbx_core.webrtc_signaling.handle_answer(session_id, sdp)

            if success:
                self._send_json({"success": True, "message": "Answer received"})
            else:
                self._send_json({"error": "Session not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_webrtc_ice_candidate(self):
        """Handle WebRTC ICE candidate"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_signaling"):
            self._send_json({"error": "WebRTC not available"}, 500)
            return

        verbose_logging = getattr(self.pbx_core.webrtc_signaling, "verbose_logging", False)

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            session_id = data.get("session_id")
            candidate = data.get("candidate")

            if verbose_logging:
                self.logger.info(f"[VERBOSE] ICE candidate received:")
                self.logger.info(f"  Session ID: {session_id}")
                if candidate:
                    self.logger.info(
                        f"  Candidate: {
                            candidate.get(
                                'candidate',
                                'N/A')}"
                    )

            if not session_id or not candidate:
                self._send_json({"error": "session_id and candidate are required"}, 400)
                return

            success = self.pbx_core.webrtc_signaling.add_ice_candidate(session_id, candidate)

            if success:
                self._send_json({"success": True, "message": "ICE candidate added"})
            else:
                if verbose_logging:
                    self.logger.warning(f"[VERBOSE] Session not found for ICE candidate")
                self._send_json({"error": "Session not found"}, 404)
        except Exception as e:
            if verbose_logging:
                self.logger.error(f"[VERBOSE] Error handling ICE candidate: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_webrtc_call(self):
        """Initiate a call from WebRTC client"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_gateway"):
            self._send_json({"error": "WebRTC gateway not available"}, 500)
            return

        verbose_logging = False
        if hasattr(self.pbx_core, "webrtc_signaling"):
            verbose_logging = getattr(self.pbx_core.webrtc_signaling, "verbose_logging", False)

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            session_id = data.get("session_id")
            target_extension = data.get("target_extension")

            if verbose_logging:
                self.logger.info(f"[VERBOSE] WebRTC call initiation request:")
                self.logger.info(f"  Session ID: {session_id}")
                self.logger.info(f"  Target Extension: {target_extension}")
                self.logger.info(f"  Client IP: {self.client_address[0]}")

            if not session_id or not target_extension:
                self._send_json({"error": "session_id and target_extension are required"}, 400)
                return

            call_id = self.pbx_core.webrtc_gateway.initiate_call(
                session_id,
                target_extension,
                webrtc_signaling=(
                    self.pbx_core.webrtc_signaling
                    if hasattr(self.pbx_core, "webrtc_signaling")
                    else None
                ),
            )

            if call_id:
                if verbose_logging:
                    self.logger.info(f"[VERBOSE] Call initiated successfully:")
                    self.logger.info(f"  Call ID: {call_id}")
                self._send_json(
                    {
                        "success": True,
                        "call_id": call_id,
                        "message": f"Call initiated to {target_extension}",
                    }
                )
            else:
                if verbose_logging:
                    self.logger.error(f"[VERBOSE] Call initiation failed - no call ID returned")
                self._send_json({"error": "Failed to initiate call"}, 500)
        except Exception as e:
            if verbose_logging:
                self.logger.error(f"[VERBOSE] Exception in call handler: {e}")
                import traceback

                self.logger.error(
                    f"[VERBOSE] Traceback:\n{
                        traceback.format_exc()}"
                )
            self._send_json({"error": str(e)}, 500)

    def _handle_webrtc_hangup(self):
        """Handle WebRTC call hangup/termination"""
        if not self.pbx_core:
            self._send_json({"error": "PBX core not available"}, 500)
            return

        verbose_logging = False
        if hasattr(self.pbx_core, "webrtc_signaling"):
            verbose_logging = getattr(self.pbx_core.webrtc_signaling, "verbose_logging", False)

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            session_id = data.get("session_id")
            call_id = data.get("call_id")

            if verbose_logging:
                self.logger.info(f"[VERBOSE] WebRTC hangup request:")
                self.logger.info(f"  Session ID: {session_id}")
                self.logger.info(f"  Call ID: {call_id}")
                self.logger.info(f"  Client IP: {self.client_address[0]}")

            if not session_id:
                self._send_json({"error": "session_id is required"}, 400)
                return

            # Terminate the call if call_id is provided
            if call_id and hasattr(self.pbx_core, "call_manager"):
                call = self.pbx_core.call_manager.get_call(call_id)
                if call:
                    if verbose_logging:
                        self.logger.info(f"[VERBOSE] Terminating call {call_id}")

                    # End the call through call manager
                    self.pbx_core.call_manager.end_call(call_id)

                    if verbose_logging:
                        self.logger.info(f"[VERBOSE] Call {call_id} terminated successfully")
                else:
                    if verbose_logging:
                        self.logger.warning(f"[VERBOSE] Call {call_id} not found in call manager")

            # Clean up WebRTC session
            if hasattr(self.pbx_core, "webrtc_signaling"):
                session = self.pbx_core.webrtc_signaling.get_session(session_id)
                if session:
                    # Close the session
                    self.pbx_core.webrtc_signaling.close_session(session_id)
                    if verbose_logging:
                        self.logger.info(f"[VERBOSE] WebRTC session {session_id} closed")

            self._send_json({"success": True, "message": "Call terminated successfully"})

        except Exception as e:
            if verbose_logging:
                self.logger.error(f"[VERBOSE] Exception in hangup handler: {e}")
                import traceback

                self.logger.error(
                    f"[VERBOSE] Traceback:\n{
                        traceback.format_exc()}"
                )
            self._send_json({"error": str(e)}, 500)

    def _handle_webrtc_dtmf(self):
        """Handle DTMF tone sending from WebRTC client"""
        if not self.pbx_core:
            self._send_json({"error": "PBX core not available"}, 500)
            return

        verbose_logging = False
        if hasattr(self.pbx_core, "webrtc_signaling"):
            verbose_logging = getattr(self.pbx_core.webrtc_signaling, "verbose_logging", False)

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            session_id = data.get("session_id")
            digit = data.get("digit")
            duration = data.get("duration", 160)  # Default 160ms

            if verbose_logging:
                self.logger.info(f"[VERBOSE] WebRTC DTMF request:")
                self.logger.info(f"  Session ID: {session_id}")
                self.logger.info(f"  Digit: {digit}")
                self.logger.info(f"  Duration: {duration}ms")
                self.logger.info(f"  Client IP: {self.client_address[0]}")

            if not session_id or digit is None:
                self._send_json({"error": "session_id and digit are required"}, 400)
                return

            # Validate digit
            if digit not in "0123456789*#":
                self._send_json({"error": "Invalid digit. Must be 0-9, *, or #"}, 400)
                return

            # Get the session
            if not hasattr(self.pbx_core, "webrtc_signaling"):
                self._send_json({"error": "WebRTC signaling not available"}, 500)
                return

            session = self.pbx_core.webrtc_signaling.get_session(session_id)
            if not session:
                self._send_json({"error": "Session not found"}, 404)
                return

            # Get the active call for this session
            if not session.call_id:
                self._send_json({"error": "No active call for this session"}, 400)
                return

            if verbose_logging:
                self.logger.info(f"[VERBOSE] Found call ID: {session.call_id}")

            # Get the call object
            call = None
            if hasattr(self.pbx_core, "call_manager"):
                call = self.pbx_core.call_manager.get_call(session.call_id)

            if not call:
                self._send_json({"error": "Call not found"}, 404)
                return

            if verbose_logging:
                self.logger.info(
                    f"[VERBOSE] Found call object for {
                        session.call_id}"
                )
                self.logger.info(f"  Caller: {call.caller_extension}")
                self.logger.info(f"  Callee: {call.callee_extension}")

            # Send DTMF via the call's RTP handler
            # WebRTC clients typically need to send DTMF to the remote end
            # We'll send to the callee's RTP handler
            if hasattr(call, "rtp_handlers") and call.rtp_handlers:
                # Find the RTP handler that's NOT for the WebRTC extension
                target_handler = None
                for ext, handler in call.rtp_handlers.items():
                    if ext != session.extension:
                        target_handler = handler
                        break

                if target_handler and hasattr(target_handler, "rfc2833_sender"):
                    if verbose_logging:
                        self.logger.info(f"[VERBOSE] Sending DTMF '{digit}' via RFC2833")

                    # Send DTMF via RFC2833 and check return value
                    success = target_handler.rfc2833_sender.send_dtmf(digit, duration_ms=duration)

                    if success:
                        self._send_json(
                            {
                                "success": True,
                                "message": f'DTMF tone "{digit}" sent successfully',
                                "digit": digit,
                                "duration": duration,
                            }
                        )

                        if verbose_logging:
                            self.logger.info(f"[VERBOSE] DTMF '{digit}' sent successfully")
                    else:
                        if verbose_logging:
                            self.logger.error(f"[VERBOSE] Failed to send DTMF '{digit}'")
                        self._send_json({"error": f'Failed to send DTMF tone "{digit}"'}, 500)
                else:
                    if verbose_logging:
                        self.logger.warning(f"[VERBOSE] No RFC2833 sender available for DTMF")
                    self._send_json({"error": "DTMF sending not available for this call"}, 500)
            else:
                if verbose_logging:
                    self.logger.warning(
                        f"[VERBOSE] No RTP handlers found for call {
                            session.call_id}"
                    )
                self._send_json({"error": "No RTP handlers available for this call"}, 500)

        except Exception as e:
            if verbose_logging:
                self.logger.error(f"[VERBOSE] Exception in DTMF handler: {e}")
                import traceback

                self.logger.error(
                    f"[VERBOSE] Traceback:\n{
                        traceback.format_exc()}"
                )
            self._send_json({"error": str(e)}, 500)

    def _handle_get_webrtc_sessions(self):
        """Get all WebRTC sessions"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_signaling"):
            self._send_json({"error": "WebRTC not available"}, 500)
            return

        try:
            sessions = self.pbx_core.webrtc_signaling.get_sessions_info()
            self._send_json(sessions)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_webrtc_session(self, path: str):
        """Get specific WebRTC session"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_signaling"):
            self._send_json({"error": "WebRTC not available"}, 500)
            return

        try:
            session_id = path.split("/")[-1]
            session = self.pbx_core.webrtc_signaling.get_session(session_id)

            if session:
                self._send_json(session.to_dict())
            else:
                self._send_json({"error": "Session not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_ice_servers(self):
        """Get ICE servers configuration"""
        if not self.pbx_core or not hasattr(self.pbx_core, "webrtc_signaling"):
            self._send_json({"error": "WebRTC not available"}, 500)
            return

        try:
            config = self.pbx_core.webrtc_signaling.get_ice_servers_config()
            self._send_json(config)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_webrtc_phone_config(self):
        """Get WebRTC phone extension configuration"""
        try:
            # Get the configured extension for the webrtc admin phone
            extension = self.pbx_core.extension_db.get_config(
                "webrtc_phone_extension", DEFAULT_WEBRTC_EXTENSION
            )
            self._send_json({"success": True, "extension": extension})
        except Exception as e:
            self.logger.error(f"Error getting WebRTC phone config: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_set_webrtc_phone_config(self):
        """Set WebRTC phone extension configuration"""
        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension = data.get("extension")

            if not extension:
                self._send_json({"error": "Extension is required"}, 400)
                return

            # Validate extension exists or is a valid virtual extension
            is_virtual = extension.startswith("webrtc-")
            if not is_virtual:
                ext_info = self.pbx_core.extension_registry.get_extension(extension)
                if not ext_info:
                    self._send_json({"error": "Extension not found"}, 404)
                    return

            # Save the configuration
            success = self.pbx_core.extension_db.set_config(
                "webrtc_phone_extension", extension, "string"
            )

            if success:
                self._send_json({"success": True, "extension": extension})
            else:
                self._send_json({"error": "Failed to save configuration"}, 500)
        except Exception as e:
            self.logger.error(f"Error setting WebRTC phone config: {e}")
            self._send_json({"error": str(e)}, 500)

    # ========== CRM Integration Handlers ==========

    def _handle_crm_lookup(self):
        """Look up caller information"""
        if not self.pbx_core or not hasattr(self.pbx_core, "crm_integration"):
            self._send_json({"error": "CRM integration not available"}, 500)
            return

        try:
            # Get phone number from query string
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            phone_number = query_params.get("phone", [None])[0]

            if not phone_number:
                self._send_json({"error": "phone parameter is required"}, 400)
                return

            # Look up caller info
            caller_info = self.pbx_core.crm_integration.lookup_caller(phone_number)

            if caller_info:
                self._send_json({"found": True, "caller_info": caller_info.to_dict()})
            else:
                self._send_json({"found": False, "message": "Caller not found"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_crm_providers(self):
        """Get CRM provider status"""
        if not self.pbx_core or not hasattr(self.pbx_core, "crm_integration"):
            self._send_json({"error": "CRM integration not available"}, 500)
            return

        try:
            providers = self.pbx_core.crm_integration.get_provider_status()
            self._send_json(
                {"enabled": self.pbx_core.crm_integration.enabled, "providers": providers}
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_trigger_screen_pop(self):
        """Trigger screen pop for a call"""
        if not self.pbx_core or not hasattr(self.pbx_core, "crm_integration"):
            self._send_json({"error": "CRM integration not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            phone_number = data.get("phone_number")
            call_id = data.get("call_id")
            extension = data.get("extension")

            if not all([phone_number, call_id, extension]):
                self._send_json({"error": "phone_number, call_id, and extension are required"}, 400)
                return

            self.pbx_core.crm_integration.trigger_screen_pop(phone_number, call_id, extension)

            self._send_json({"success": True, "message": "Screen pop triggered"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ========== Hot-Desking Handlers ==========

    def _handle_hot_desk_login(self):
        """Handle hot-desk login"""
        if not self.pbx_core or not hasattr(self.pbx_core, "hot_desking"):
            self._send_json({"error": "Hot-desking not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension = data.get("extension")
            device_id = data.get("device_id")
            ip_address = data.get("ip_address", self.client_address[0])
            pin = data.get("pin")

            if not all([extension, device_id]):
                self._send_json({"error": "extension and device_id are required"}, 400)
                return

            success = self.pbx_core.hot_desking.login(extension, device_id, ip_address, pin)

            if success:
                profile = self.pbx_core.hot_desking.get_extension_profile(extension)
                self._send_json(
                    {
                        "success": True,
                        "message": f"Extension {extension} logged in",
                        "profile": profile,
                    }
                )
            else:
                self._send_json({"error": "Login failed"}, 401)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_hot_desk_logout(self):
        """Handle hot-desk logout"""
        if not self.pbx_core or not hasattr(self.pbx_core, "hot_desking"):
            self._send_json({"error": "Hot-desking not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            device_id = data.get("device_id")
            # Optional: logout specific extension
            extension = data.get("extension")

            if device_id:
                success = self.pbx_core.hot_desking.logout(device_id)
                if success:
                    self._send_json(
                        {"success": True, "message": f"Logged out from device {device_id}"}
                    )
                else:
                    self._send_json({"error": "No active session for device"}, 404)
            elif extension:
                count = self.pbx_core.hot_desking.logout_extension(extension)
                self._send_json(
                    {
                        "success": True,
                        "message": f"Extension {extension} logged out from {count} device(s)",
                    }
                )
            else:
                self._send_json({"error": "device_id or extension is required"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_mfa_enroll(self):
        """Handle MFA enrollment"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension_number = data.get("extension")

            if not extension_number:
                self._send_json({"error": "extension is required"}, 400)
                return

            success, provisioning_uri, backup_codes = self.pbx_core.mfa_manager.enroll_user(
                extension_number
            )

            if success:
                self._send_json(
                    {
                        "success": True,
                        "provisioning_uri": provisioning_uri,
                        "backup_codes": backup_codes,
                        "message": "MFA enrollment initiated. Scan QR code and verify with first code.",
                    }
                )
            else:
                self._send_json({"error": "MFA enrollment failed"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_mfa_verify_enrollment(self):
        """Handle MFA enrollment verification"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension_number = data.get("extension")
            code = data.get("code")

            if not extension_number or not code:
                self._send_json({"error": "extension and code are required"}, 400)
                return

            success = self.pbx_core.mfa_manager.verify_enrollment(extension_number, code)

            if success:
                self._send_json({"success": True, "message": "MFA successfully activated"})
            else:
                self._send_json({"error": "Invalid code"}, 401)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_mfa_verify(self):
        """Handle MFA code verification"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension_number = data.get("extension")
            code = data.get("code")

            if not extension_number or not code:
                self._send_json({"error": "extension and code are required"}, 400)
                return

            success = self.pbx_core.mfa_manager.verify_code(extension_number, code)

            if success:
                self._send_json({"success": True, "message": "MFA verification successful"})
            else:
                self._send_json({"error": "Invalid code"}, 401)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_mfa_disable(self):
        """Handle MFA disable"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension_number = data.get("extension")

            if not extension_number:
                self._send_json({"error": "extension is required"}, 400)
                return

            success = self.pbx_core.mfa_manager.disable_for_user(extension_number)

            if success:
                self._send_json({"success": True, "message": "MFA disabled successfully"})
            else:
                self._send_json({"error": "Failed to disable MFA"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_mfa_enroll_yubikey(self):
        """Handle YubiKey enrollment"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension_number = data.get("extension")
            otp = data.get("otp")
            device_name = data.get("device_name", "YubiKey")

            if not extension_number or not otp:
                self._send_json({"error": "extension and otp are required"}, 400)
                return

            success, error = self.pbx_core.mfa_manager.enroll_yubikey(
                extension_number, otp, device_name
            )

            if success:
                self._send_json({"success": True, "message": "YubiKey enrolled successfully"})
            else:
                self._send_json({"error": error or "YubiKey enrollment failed"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_mfa_enroll_fido2(self):
        """Handle FIDO2/WebAuthn credential enrollment"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension_number = data.get("extension")
            credential_data = data.get("credential_data")
            device_name = data.get("device_name", "Security Key")

            if not extension_number or not credential_data:
                self._send_json({"error": "extension and credential_data are required"}, 400)
                return

            success, error = self.pbx_core.mfa_manager.enroll_fido2(
                extension_number, credential_data, device_name
            )

            if success:
                self._send_json(
                    {"success": True, "message": "FIDO2 credential enrolled successfully"}
                )
            else:
                self._send_json({"error": error or "FIDO2 enrollment failed"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_mfa_methods(self, path: str):
        """Get enrolled MFA methods for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            extension = path.split("/")[-1]
            methods = self.pbx_core.mfa_manager.get_enrolled_methods(extension)

            self._send_json({"extension": extension, "methods": methods})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_mfa_status(self, path: str):
        """Get MFA status for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, "mfa_manager"):
            self._send_json({"error": "MFA not available"}, 500)
            return

        try:
            extension = path.split("/")[-1]
            enabled = self.pbx_core.mfa_manager.is_enabled_for_user(extension)

            self._send_json(
                {
                    "extension": extension,
                    "mfa_enabled": enabled,
                    "mfa_required": self.pbx_core.mfa_manager.required,
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_block_ip(self):
        """Handle IP blocking"""
        if not self.pbx_core or not hasattr(self.pbx_core, "threat_detector"):
            self._send_json({"error": "Threat detection not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            ip_address = data.get("ip_address")
            reason = data.get("reason", "Manual block")
            duration = data.get("duration")  # Optional, in seconds

            if not ip_address:
                self._send_json({"error": "ip_address is required"}, 400)
                return

            self.pbx_core.threat_detector.block_ip(ip_address, reason, duration)

            self._send_json({"success": True, "message": f"IP {ip_address} blocked successfully"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_unblock_ip(self):
        """Handle IP unblocking"""
        if not self.pbx_core or not hasattr(self.pbx_core, "threat_detector"):
            self._send_json({"error": "Threat detection not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            ip_address = data.get("ip_address")

            if not ip_address:
                self._send_json({"error": "ip_address is required"}, 400)
                return

            self.pbx_core.threat_detector.unblock_ip(ip_address)

            self._send_json({"success": True, "message": f"IP {ip_address} unblocked successfully"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_threat_summary(self):
        """Get threat detection summary"""
        if not self.pbx_core or not hasattr(self.pbx_core, "threat_detector"):
            self._send_json({"error": "Threat detection not available"}, 500)
            return

        try:
            # Get hours parameter from query string
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            hours = int(params.get("hours", [24])[0])

            summary = self.pbx_core.threat_detector.get_threat_summary(hours)

            self._send_json(summary)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_check_ip(self, path: str):
        """Check if IP is blocked"""
        if not self.pbx_core or not hasattr(self.pbx_core, "threat_detector"):
            self._send_json({"error": "Threat detection not available"}, 500)
            return

        try:
            ip_address = path.split("/")[-1]
            is_blocked, reason = self.pbx_core.threat_detector.is_ip_blocked(ip_address)

            self._send_json({"ip_address": ip_address, "is_blocked": is_blocked, "reason": reason})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_security_compliance_status(self):
        """Get FIPS and security compliance status"""
        if not self.pbx_core or not hasattr(self.pbx_core, "security_monitor"):
            self._send_json({"error": "Security monitor not available"}, 500)
            return

        try:
            status = self.pbx_core.security_monitor.get_compliance_status()
            self._send_json(status)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_security_health(self):
        """Get comprehensive security health check"""
        if not self.pbx_core or not hasattr(self.pbx_core, "security_monitor"):
            self._send_json({"error": "Security monitor not available"}, 500)
            return

        try:
            # Perform security check
            results = self.pbx_core.security_monitor.perform_security_check()
            self._send_json(results)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_add_dnd_rule(self):
        """Handle adding DND rule"""
        if not self.pbx_core or not hasattr(self.pbx_core, "dnd_scheduler"):
            self._send_json({"error": "DND Scheduler not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension = data.get("extension")
            rule_type = data.get("rule_type")  # 'calendar' or 'time_based'
            config = data.get("config", {})

            if not extension or not rule_type:
                self._send_json({"error": "extension and rule_type are required"}, 400)
                return

            rule_id = self.pbx_core.dnd_scheduler.add_rule(extension, rule_type, config)

            self._send_json(
                {"success": True, "rule_id": rule_id, "message": "DND rule added successfully"}
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_dnd_rule(self, rule_id: str):
        """Handle deleting DND rule"""
        if not self.pbx_core or not hasattr(self.pbx_core, "dnd_scheduler"):
            self._send_json({"error": "DND Scheduler not available"}, 500)
            return

        try:
            success = self.pbx_core.dnd_scheduler.remove_rule(rule_id)

            if success:
                self._send_json({"success": True, "message": "DND rule deleted successfully"})
            else:
                self._send_json({"error": "Rule not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_register_calendar_user(self):
        """Handle registering user for calendar-based DND"""
        if not self.pbx_core or not hasattr(self.pbx_core, "dnd_scheduler"):
            self._send_json({"error": "DND Scheduler not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension = data.get("extension")
            email = data.get("email")

            if not extension or not email:
                self._send_json({"error": "extension and email are required"}, 400)
                return

            self.pbx_core.dnd_scheduler.register_calendar_user(extension, email)

            self._send_json(
                {"success": True, "message": f"Calendar monitoring registered for {extension}"}
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_dnd_override(self):
        """Handle manual DND override"""
        if not self.pbx_core or not hasattr(self.pbx_core, "dnd_scheduler"):
            self._send_json({"error": "DND Scheduler not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            extension = data.get("extension")
            status = data.get("status")  # e.g., 'do_not_disturb', 'available'
            duration_minutes = data.get("duration_minutes")  # Optional

            if not extension or not status:
                self._send_json({"error": "extension and status are required"}, 400)
                return

            # Convert status string to PresenceStatus enum
            from pbx.features.presence import PresenceStatus

            try:
                status_enum = PresenceStatus(status)
            except ValueError:
                self._send_json({"error": f"Invalid status: {status}"}, 400)
                return

            self.pbx_core.dnd_scheduler.set_manual_override(
                extension, status_enum, duration_minutes
            )

            self._send_json({"success": True, "message": f"Manual override set for {extension}"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_clear_dnd_override(self, extension: str):
        """Handle clearing DND override"""
        if not self.pbx_core or not hasattr(self.pbx_core, "dnd_scheduler"):
            self._send_json({"error": "DND Scheduler not available"}, 500)
            return

        try:
            self.pbx_core.dnd_scheduler.clear_manual_override(extension)

            self._send_json({"success": True, "message": f"Override cleared for {extension}"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_dnd_status(self, path: str):
        """Get DND status for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, "dnd_scheduler"):
            self._send_json({"error": "DND Scheduler not available"}, 500)
            return

        try:
            extension = path.split("/")[-1]
            status = self.pbx_core.dnd_scheduler.get_status(extension)

            self._send_json(status)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_dnd_rules(self, path: str):
        """Get DND rules for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, "dnd_scheduler"):
            self._send_json({"error": "DND Scheduler not available"}, 500)
            return

        try:
            extension = path.split("/")[-1]
            rules = self.pbx_core.dnd_scheduler.get_rules(extension)

            self._send_json({"extension": extension, "rules": rules})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_add_skill(self):
        """Handle adding a new skill"""
        if not self.pbx_core or not hasattr(self.pbx_core, "skills_router"):
            self._send_json({"error": "Skills routing not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            skill_id = data.get("skill_id")
            name = data.get("name")
            description = data.get("description", "")

            if not skill_id or not name:
                self._send_json({"error": "skill_id and name are required"}, 400)
                return

            success = self.pbx_core.skills_router.add_skill(skill_id, name, description)

            if success:
                self._send_json(
                    {"success": True, "skill_id": skill_id, "message": "Skill added successfully"}
                )
            else:
                self._send_json({"error": "Skill already exists"}, 409)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_assign_skill(self):
        """Handle assigning skill to agent"""
        if not self.pbx_core or not hasattr(self.pbx_core, "skills_router"):
            self._send_json({"error": "Skills routing not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            agent_extension = data.get("agent_extension")
            skill_id = data.get("skill_id")
            proficiency = data.get("proficiency", 5)

            if not agent_extension or not skill_id:
                self._send_json({"error": "agent_extension and skill_id are required"}, 400)
                return

            success = self.pbx_core.skills_router.assign_skill_to_agent(
                agent_extension, skill_id, proficiency
            )

            if success:
                self._send_json(
                    {"success": True, "message": f"Skill assigned to agent {agent_extension}"}
                )
            else:
                self._send_json({"error": "Failed to assign skill"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_remove_skill_from_agent(self, agent_extension: str, skill_id: str):
        """Handle removing skill from agent"""
        if not self.pbx_core or not hasattr(self.pbx_core, "skills_router"):
            self._send_json({"error": "Skills routing not available"}, 500)
            return

        try:
            success = self.pbx_core.skills_router.remove_skill_from_agent(agent_extension, skill_id)

            if success:
                self._send_json(
                    {"success": True, "message": f"Skill removed from agent {agent_extension}"}
                )
            else:
                self._send_json({"error": "Skill not found for agent"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_set_queue_requirements(self):
        """Handle setting queue skill requirements"""
        if not self.pbx_core or not hasattr(self.pbx_core, "skills_router"):
            self._send_json({"error": "Skills routing not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            queue_number = data.get("queue_number")
            requirements = data.get("requirements", [])

            if not queue_number:
                self._send_json({"error": "queue_number is required"}, 400)
                return

            success = self.pbx_core.skills_router.set_queue_requirements(queue_number, requirements)

            if success:
                self._send_json(
                    {"success": True, "message": f"Requirements set for queue {queue_number}"}
                )
            else:
                self._send_json({"error": "Failed to set requirements"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_clear_qos_alerts(self):
        """Handle clearing QoS alerts"""
        if not self.pbx_core or not hasattr(self.pbx_core, "qos_monitor"):
            self._send_json({"error": "QoS monitoring not available"}, 500)
            return

        try:
            count = self.pbx_core.qos_monitor.clear_alerts()
            self._send_json({"success": True, "message": f"Cleared {count} alerts"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_qos_thresholds(self):
        """Handle updating QoS alert thresholds"""
        if not self.pbx_core or not hasattr(self.pbx_core, "qos_monitor"):
            self._send_json({"error": "QoS monitoring not available"}, 500)
            return

        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            thresholds = {}

            # Validate and convert threshold values with range checking
            if "mos_min" in data:
                mos_min = float(data["mos_min"])
                if mos_min < 1.0 or mos_min > 5.0:
                    self._send_json({"error": "mos_min must be between 1.0 and 5.0"}, 400)
                    return
                thresholds["mos_min"] = mos_min

            if "packet_loss_max" in data:
                packet_loss_max = float(data["packet_loss_max"])
                if packet_loss_max < 0.0 or packet_loss_max > 100.0:
                    self._send_json({"error": "packet_loss_max must be between 0.0 and 100.0"}, 400)
                    return
                thresholds["packet_loss_max"] = packet_loss_max

            if "jitter_max" in data:
                jitter_max = float(data["jitter_max"])
                if jitter_max < 0.0 or jitter_max > 1000.0:
                    self._send_json({"error": "jitter_max must be between 0.0 and 1000.0 ms"}, 400)
                    return
                thresholds["jitter_max"] = jitter_max

            if "latency_max" in data:
                latency_max = float(data["latency_max"])
                if latency_max < 0.0 or latency_max > 5000.0:
                    self._send_json({"error": "latency_max must be between 0.0 and 5000.0 ms"}, 400)
                    return
                thresholds["latency_max"] = latency_max

            if not thresholds:
                self._send_json({"error": "No valid threshold parameters provided"}, 400)
                return

            self.pbx_core.qos_monitor.update_alert_thresholds(thresholds)

            self._send_json(
                {
                    "success": True,
                    "message": "QoS thresholds updated",
                    "thresholds": self.pbx_core.qos_monitor.alert_thresholds,
                }
            )
        except ValueError as e:
            self.logger.error(f"Invalid threshold value: {e}")
            self._send_json({"error": "Invalid threshold values, must be valid numbers"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_all_skills(self):
        """Get all skills"""
        if not self.pbx_core or not hasattr(self.pbx_core, "skills_router"):
            self._send_json({"error": "Skills routing not available"}, 500)
            return

        try:
            skills = self.pbx_core.skills_router.get_all_skills()
            self._send_json({"skills": skills})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_agent_skills(self, path: str):
        """Get agent skills"""
        if not self.pbx_core or not hasattr(self.pbx_core, "skills_router"):
            self._send_json({"error": "Skills routing not available"}, 500)
            return

        try:
            agent_extension = path.split("/")[-1]
            skills = self.pbx_core.skills_router.get_agent_skills(agent_extension)

            self._send_json({"agent_extension": agent_extension, "skills": skills})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_queue_requirements(self, path: str):
        """Get queue skill requirements"""
        if not self.pbx_core or not hasattr(self.pbx_core, "skills_router"):
            self._send_json({"error": "Skills routing not available"}, 500)
            return

        try:
            queue_number = path.split("/")[-1]
            requirements = self.pbx_core.skills_router.get_queue_requirements(queue_number)

            self._send_json({"queue_number": queue_number, "requirements": requirements})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_hot_desk_sessions(self):
        """Get all hot-desk sessions"""
        if not self.pbx_core or not hasattr(self.pbx_core, "hot_desking"):
            self._send_json({"error": "Hot-desking not available"}, 500)
            return

        try:
            sessions = self.pbx_core.hot_desking.get_active_sessions()
            self._send_json({"count": len(sessions), "sessions": sessions})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_hot_desk_session(self, path: str):
        """Get specific hot-desk session by device"""
        if not self.pbx_core or not hasattr(self.pbx_core, "hot_desking"):
            self._send_json({"error": "Hot-desking not available"}, 500)
            return

        try:
            device_id = path.split("/")[-1]
            session = self.pbx_core.hot_desking.get_session(device_id)

            if session:
                self._send_json(session.to_dict())
            else:
                self._send_json({"error": "No session found for device"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_hot_desk_extension(self, path: str):
        """Get hot-desk information for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, "hot_desking"):
            self._send_json({"error": "Hot-desking not available"}, 500)
            return

        try:
            extension = path.split("/")[-1]
            devices = self.pbx_core.hot_desking.get_extension_devices(extension)
            sessions = []

            for device_id in devices:
                session = self.pbx_core.hot_desking.get_session(device_id)
                if session:
                    sessions.append(session.to_dict())

            self._send_json(
                {
                    "extension": extension,
                    "logged_in": len(sessions) > 0,
                    "device_count": len(devices),
                    "sessions": sessions,
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ========== Auto Attendant Management Handlers ==========

    def _handle_get_auto_attendant_config(self):
        """Get auto attendant configuration"""
        if not self.pbx_core or not hasattr(self.pbx_core, "auto_attendant"):
            self._send_json({"error": "Auto attendant not available"}, 500)
            return

        try:
            aa = self.pbx_core.auto_attendant
            config = {
                "enabled": aa.enabled,
                "extension": aa.extension,
                "timeout": aa.timeout,
                "max_retries": aa.max_retries,
                "audio_path": aa.audio_path,
            }
            self._send_json(config)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_auto_attendant_config(self):
        """Update auto attendant configuration"""
        if not self.pbx_core or not hasattr(self.pbx_core, "auto_attendant"):
            self._send_json({"error": "Auto attendant not available"}, 500)
            return

        try:
            data = self._get_body()
            aa = self.pbx_core.auto_attendant

            # Update configuration using the new update_config method
            config_updates = {}
            if "enabled" in data:
                config_updates["enabled"] = bool(data["enabled"])
            if "extension" in data:
                config_updates["extension"] = str(data["extension"])
            if "timeout" in data:
                config_updates["timeout"] = int(data["timeout"])
            if "max_retries" in data:
                config_updates["max_retries"] = int(data["max_retries"])

            # Apply updates and persist to database
            if config_updates:
                aa.update_config(**config_updates)
                config_changed = True
            else:
                config_changed = False

            # Check if prompts configuration was updated
            prompts_updated = "prompts" in data

            # Trigger voice regeneration if prompts or menu options changed
            if prompts_updated or config_changed:
                try:
                    self._regenerate_voice_prompts(data.get("prompts", {}))
                except Exception as e:
                    self.logger.warning(f"Failed to regenerate voice prompts: {e}")

            self._send_json(
                {
                    "success": True,
                    "message": "Auto attendant configuration updated and persisted to database",
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_auto_attendant_menu_options(self):
        """Get auto attendant menu options"""
        if not self.pbx_core or not hasattr(self.pbx_core, "auto_attendant"):
            self._send_json({"error": "Auto attendant not available"}, 500)
            return

        try:
            aa = self.pbx_core.auto_attendant
            options = []
            for digit, option in aa.menu_options.items():
                options.append(
                    {
                        "digit": digit,
                        "destination": option["destination"],
                        "description": option["description"],
                    }
                )
            self._send_json({"menu_options": options})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_add_auto_attendant_menu_option(self):
        """Add auto attendant menu option"""
        if not self.pbx_core or not hasattr(self.pbx_core, "auto_attendant"):
            self._send_json({"error": "Auto attendant not available"}, 500)
            return

        try:
            data = self._get_body()
            digit = str(data.get("digit"))
            destination = data.get("destination")
            description = data.get("description", "")

            if not digit or not destination:
                self._send_json({"error": "digit and destination are required"}, 400)
                return

            aa = self.pbx_core.auto_attendant
            # Use the new add_menu_option method which persists to database
            aa.add_menu_option(digit, destination, description)

            # Trigger voice regeneration after menu option addition
            try:
                self._regenerate_voice_prompts({})
            except Exception as e:
                self.logger.warning(f"Failed to regenerate voice prompts: {e}")

            self._send_json(
                {"success": True, "message": f"Menu option {digit} added and persisted to database"}
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_auto_attendant_menu_option(self, path: str):
        """Update auto attendant menu option"""
        if not self.pbx_core or not hasattr(self.pbx_core, "auto_attendant"):
            self._send_json({"error": "Auto attendant not available"}, 500)
            return

        try:
            digit = path.split("/")[-1]
            data = self._get_body()

            aa = self.pbx_core.auto_attendant
            if digit not in aa.menu_options:
                self._send_json({"error": f"Menu option {digit} not found"}, 404)
                return

            # Get current values
            destination = aa.menu_options[digit]["destination"]
            description = aa.menu_options[digit]["description"]

            # Update with new values if provided
            if "destination" in data:
                destination = data["destination"]
            if "description" in data:
                description = data["description"]

            # Use add_menu_option which will update and persist to database
            aa.add_menu_option(digit, destination, description)

            # Trigger voice regeneration after menu option update
            try:
                self._regenerate_voice_prompts({})
            except Exception as e:
                self.logger.warning(f"Failed to regenerate voice prompts: {e}")

            self._send_json(
                {
                    "success": True,
                    "message": f"Menu option {digit} updated and persisted to database",
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_auto_attendant_menu_option(self, digit: str):
        """Delete auto attendant menu option"""
        if not self.pbx_core or not hasattr(self.pbx_core, "auto_attendant"):
            self._send_json({"error": "Auto attendant not available"}, 500)
            return

        try:
            aa = self.pbx_core.auto_attendant
            if digit in aa.menu_options:
                # Use the new remove_menu_option method which deletes from database
                aa.remove_menu_option(digit)

                # Trigger voice regeneration after menu option deletion
                try:
                    self._regenerate_voice_prompts({})
                except Exception as e:
                    self.logger.warning(f"Failed to regenerate voice prompts: {e}")

                self._send_json(
                    {
                        "success": True,
                        "message": f"Menu option {digit} deleted and removed from database",
                    }
                )
            else:
                self._send_json({"error": f"Menu option {digit} not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_auto_attendant_prompts(self):
        """Get auto attendant prompt texts"""
        try:
            # Return current prompt configuration
            config = self.pbx_core.config if self.pbx_core else Config()
            aa_config = config.get("auto_attendant", {})

            prompts = aa_config.get(
                "prompts",
                {
                    "welcome": "Thank you for calling {company_name}.",
                    "main_menu": "For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.",
                    "invalid": "That is not a valid option. Please try again.",
                    "timeout": "We did not receive your selection. Please try again.",
                    "transferring": "Please hold while we transfer your call.",
                },
            )

            company_name = config.get("company_name", "your company")

            self._send_json({"prompts": prompts, "company_name": company_name})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_update_auto_attendant_prompts(self):
        """Update auto attendant prompt texts and regenerate voices"""
        try:
            data = self._get_body()
            prompts = data.get("prompts", {})
            company_name = data.get("company_name")

            # Update configuration
            config = self.pbx_core.config if self.pbx_core else Config()

            # Ensure auto_attendant section exists
            if "auto_attendant" not in config.config:
                config.config["auto_attendant"] = {}

            # Update prompts
            if prompts:
                config.config["auto_attendant"]["prompts"] = prompts

            # Update company name
            if company_name:
                config.config["company_name"] = company_name

            # Save configuration
            success = config.save()
            if not success:
                raise Exception("Failed to save configuration file")

            # Trigger voice regeneration
            self._regenerate_voice_prompts(prompts, company_name)

            self._send_json(
                {"success": True, "message": "Prompts updated and voices regenerated successfully"}
            )
        except Exception as e:
            self.logger.error(f"Error updating prompts: {e}")
            self._send_json({"error": str(e)}, 500)

    def _regenerate_voice_prompts(self, custom_prompts=None, company_name=None):
        """
        Regenerate voice prompts using gTTS

        Args:
            custom_prompts: Optional dict of custom prompt texts
            company_name: Optional company name override
        """
        try:
            # Check if TTS is available
            if not is_tts_available():
                raise ImportError(
                    f"TTS dependencies not available. Install with: {
                        get_tts_requirements()}"
                )

            # Get configuration
            config = self.pbx_core.config if self.pbx_core else Config()
            aa_config = config.get("auto_attendant", {})

            if not company_name:
                company_name = config.get("company_name", "your company")

            # Get prompt texts
            default_prompts = {
                "welcome": f"Thank you for calling {company_name}.",
                "main_menu": "For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.",
                "invalid": "That is not a valid option. Please try again.",
                "timeout": "We did not receive your selection. Please try again.",
                "transferring": "Please hold while we transfer your call.",
            }

            # Merge custom prompts
            prompts = {**default_prompts}
            if custom_prompts:
                prompts.update(custom_prompts)

            # Get output directory
            audio_path = aa_config.get("audio_path", "auto_attendant")
            if not os.path.exists(audio_path):
                os.makedirs(audio_path)

            # Generate each prompt using shared TTS utility
            self.logger.info("Regenerating voice prompts using gTTS...")
            for filename, text in prompts.items():
                output_file = os.path.join(audio_path, f"{filename}.wav")

                try:
                    # Use shared utility function for TTS generation with 8kHz
                    # for PCMU
                    if text_to_wav_telephony(
                        text, output_file, language="en", tld="com", slow=False, sample_rate=8000
                    ):
                        self.logger.info(f"Generated {filename}.wav using gTTS")
                except Exception as e:
                    self.logger.error(f"Failed to generate {filename}.wav: {e}")

            self.logger.info("Voice prompt regeneration complete")
        except Exception as e:
            self.logger.error(f"Error regenerating voice prompts: {e}")
            raise

    # ========== Voicemail Box Management Handlers ==========

    def _handle_get_voicemail_boxes(self):
        """Get list of all voicemail boxes"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail system not available"}, 500)
            return

        try:
            vm_system = self.pbx_core.voicemail_system
            boxes = []

            for extension, mailbox in vm_system.mailboxes.items():
                messages = mailbox.get_messages(unread_only=False)
                unread_count = len(mailbox.get_messages(unread_only=True))

                boxes.append(
                    {
                        "extension": extension,
                        "total_messages": len(messages),
                        "unread_messages": unread_count,
                        "has_custom_greeting": mailbox.has_custom_greeting(),
                        "storage_path": mailbox.storage_path,
                    }
                )

            self._send_json({"voicemail_boxes": boxes})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_voicemail_box_details(self, path: str):
        """Get details of a specific voicemail box"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail system not available"}, 500)
            return

        try:
            # Extract extension from path, handling /export suffix
            parts = path.split("/")
            extension = parts[3] if len(parts) > 3 else None

            if not extension:
                self._send_json({"error": "Invalid path"}, 400)
                return

            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            messages = mailbox.get_messages(unread_only=False)

            details = {
                "extension": extension,
                "total_messages": len(messages),
                "unread_messages": len(mailbox.get_messages(unread_only=True)),
                "has_custom_greeting": mailbox.has_custom_greeting(),
                "storage_path": mailbox.storage_path,
                "messages": [],
            }

            for msg in messages:
                details["messages"].append(
                    {
                        "id": msg["id"],
                        "caller_id": msg["caller_id"],
                        "timestamp": (
                            msg["timestamp"].isoformat()
                            if hasattr(msg["timestamp"], "isoformat")
                            else str(msg["timestamp"])
                        ),
                        "listened": msg["listened"],
                        "duration": msg.get("duration"),
                        "file_path": msg["file_path"],
                    }
                )

            self._send_json(details)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_export_voicemail_box(self, path: str):
        """Export all voicemails from a mailbox as a ZIP file"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail system not available"}, 500)
            return

        try:
            # Extract extension from path:
            # /api/voicemail-boxes/{extension}/export
            parts = path.split("/")
            extension = parts[3] if len(parts) > 3 else None

            if not extension:
                self._send_json({"error": "Invalid path"}, 400)
                return

            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            messages = mailbox.get_messages(unread_only=False)

            if not messages:
                self._send_json({"error": "No messages to export"}, 404)
                return

            # Create temporary directory for ZIP creation
            temp_dir = tempfile.mkdtemp()
            zip_filename = f"voicemail_{extension}_{
                datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)

            try:
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    # Add a manifest file with message details
                    manifest_lines = ["Voicemail Export Manifest\n"]
                    manifest_lines.append(f"Extension: {extension}\n")
                    manifest_lines.append(
                        f"Export Date: {
                            datetime.now().isoformat()}\n"
                    )
                    manifest_lines.append(
                        f"Total Messages: {
                            len(messages)}\n\n"
                    )
                    manifest_lines.append("Message Details:\n")
                    manifest_lines.append("-" * 80 + "\n")

                    for msg in messages:
                        # Add audio file to ZIP
                        if os.path.exists(msg["file_path"]):
                            arcname = os.path.basename(msg["file_path"])
                            zipf.write(msg["file_path"], arcname)

                            # Add to manifest
                            manifest_lines.append(f"\nFile: {arcname}\n")
                            manifest_lines.append(f"Caller ID: {msg['caller_id']}\n")
                            manifest_lines.append(f"Timestamp: {msg['timestamp']}\n")
                            manifest_lines.append(
                                f"Duration: {
                                    msg.get(
                                        'duration',
                                        'Unknown')}s\n"
                            )
                            manifest_lines.append(
                                f"Status: {
                                    'Read' if msg['listened'] else 'Unread'}\n"
                            )

                    # Add manifest to ZIP
                    zipf.writestr("MANIFEST.txt", "".join(manifest_lines))

                # Read ZIP file content
                with open(zip_path, "rb") as f:
                    zip_content = f.read()

                # Send ZIP file as response
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{zip_filename}"')
                self.send_header("Content-Length", str(len(zip_content)))
                self.end_headers()
                self.wfile.write(zip_content)

            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            self.logger.error(f"Error exporting voicemail box: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_clear_voicemail_box(self, path: str):
        """Clear all messages from a voicemail box"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail system not available"}, 500)
            return

        try:
            # Extract extension from path:
            # /api/voicemail-boxes/{extension}/clear
            parts = path.split("/")
            extension = parts[3] if len(parts) > 3 else None

            if not extension:
                self._send_json({"error": "Invalid path"}, 400)
                return

            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            messages = mailbox.get_messages(unread_only=False)

            deleted_count = 0
            for msg in messages[:]:  # Create a copy to iterate over
                if mailbox.delete_message(msg["id"]):
                    deleted_count += 1

            self._send_json(
                {
                    "success": True,
                    "message": f"Cleared {deleted_count} voicemail message(s) from extension {extension}",
                    "deleted_count": deleted_count,
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_voicemail_greeting(self, path: str):
        """Get custom voicemail greeting"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail system not available"}, 500)
            return

        try:
            # Extract extension from path
            parts = path.split("/")
            extension = parts[3] if len(parts) > 3 else None

            if not extension:
                self._send_json({"error": "Invalid path"}, 400)
                return

            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            greeting_path = mailbox.get_greeting_path()

            if not greeting_path or not os.path.exists(greeting_path):
                self._send_json({"error": "No custom greeting found"}, 404)
                return

            # Serve greeting file
            with open(greeting_path, "rb") as f:
                greeting_data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header(
                "Content-Disposition", f'attachment; filename="greeting_{extension}.wav"'
            )
            self.send_header("Content-Length", str(len(greeting_data)))
            self.end_headers()
            self.wfile.write(greeting_data)

        except Exception as e:
            self.logger.error(f"Error getting voicemail greeting: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_upload_voicemail_greeting(self, path: str):
        """Upload/update custom voicemail greeting"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail system not available"}, 500)
            return

        try:
            # Extract extension from path
            parts = path.split("/")
            extension = parts[3] if len(parts) > 3 else None

            if not extension:
                self._send_json({"error": "Invalid path"}, 400)
                return

            # Get audio data from request body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json({"error": "No audio data provided"}, 400)
                return

            audio_data = self.rfile.read(content_length)

            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)

            if mailbox.save_greeting(audio_data):
                self._send_json(
                    {
                        "success": True,
                        "message": f"Custom greeting uploaded for extension {extension}",
                    }
                )
            else:
                self._send_json({"error": "Failed to save greeting"}, 500)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_voicemail_greeting(self, path: str):
        """Delete custom voicemail greeting"""
        if not self.pbx_core or not hasattr(self.pbx_core, "voicemail_system"):
            self._send_json({"error": "Voicemail system not available"}, 500)
            return

        try:
            # Extract extension from path
            parts = path.split("/")
            extension = parts[3] if len(parts) > 3 else None

            if not extension:
                self._send_json({"error": "Invalid path"}, 400)
                return

            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)

            if mailbox.delete_greeting():
                self._send_json(
                    {
                        "success": True,
                        "message": f"Custom greeting deleted for extension {extension}",
                    }
                )
            else:
                self._send_json({"error": "No custom greeting found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_get_advanced_analytics(self):
        """Get advanced analytics with date range and filters"""
        if self.pbx_core and hasattr(self.pbx_core, "statistics_engine"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                start_date = params.get("start_date", [None])[0]
                end_date = params.get("end_date", [None])[0]

                if not start_date or not end_date:
                    self._send_json({"error": "start_date and end_date parameters required"}, 400)
                    return

                # Parse filters
                filters = {}
                if "extension" in params:
                    filters["extension"] = params["extension"][0]
                if "disposition" in params:
                    filters["disposition"] = params["disposition"][0]
                if "min_duration" in params:
                    filters["min_duration"] = int(params["min_duration"][0])

                analytics = self.pbx_core.statistics_engine.get_advanced_analytics(
                    start_date, end_date, filters if filters else None
                )

                self._send_json(analytics)

            except ValueError as e:
                self._send_json({"error": f"Invalid date format: {str(e)}"}, 400)
            except Exception as e:
                self.logger.error(f"Error getting advanced analytics: {e}")
                self._send_json({"error": f"Error getting advanced analytics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Statistics engine not initialized"}, 500)

    def _handle_get_call_center_metrics(self):
        """Get call center performance metrics"""
        if self.pbx_core and hasattr(self.pbx_core, "statistics_engine"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                days = int(params.get("days", [7])[0])
                queue_name = params.get("queue", [None])[0]

                metrics = self.pbx_core.statistics_engine.get_call_center_metrics(days, queue_name)

                self._send_json(metrics)

            except Exception as e:
                self.logger.error(f"Error getting call center metrics: {e}")
                self._send_json({"error": f"Error getting call center metrics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Statistics engine not initialized"}, 500)

    def _handle_export_analytics(self):
        """Export analytics data to CSV"""
        if self.pbx_core and hasattr(self.pbx_core, "statistics_engine"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                start_date = params.get("start_date", [None])[0]
                end_date = params.get("end_date", [None])[0]

                if not start_date or not end_date:
                    self._send_json({"error": "start_date and end_date parameters required"}, 400)
                    return

                # Get analytics data
                analytics = self.pbx_core.statistics_engine.get_advanced_analytics(
                    start_date, end_date, None
                )

                # Export to CSV
                import os
                import tempfile

                temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
                temp_file.close()

                if self.pbx_core.statistics_engine.export_to_csv(
                    analytics["records"], temp_file.name
                ):
                    # Send file
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv")
                    self.send_header(
                        "Content-Disposition",
                        f'attachment; filename="cdr_export_{start_date}_to_{end_date}.csv"',
                    )
                    self.end_headers()

                    with open(temp_file.name, "rb") as f:
                        self.wfile.write(f.read())

                    # Clean up temp file
                    os.unlink(temp_file.name)
                else:
                    self._send_json({"error": "Failed to export data"}, 500)

            except Exception as e:
                self.logger.error(f"Error exporting analytics: {e}")
                self._send_json({"error": f"Error exporting analytics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Statistics engine not initialized"}, 500)

    def _handle_get_emergency_contacts(self):
        """Get emergency contacts"""
        if self.pbx_core and hasattr(self.pbx_core, "emergency_notification"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                priority_filter = (
                    int(params.get("priority", [None])[0])
                    if params.get("priority", [None])[0]
                    else None
                )

                contacts = self.pbx_core.emergency_notification.get_emergency_contacts(
                    priority_filter
                )

                self._send_json({"contacts": contacts, "total": len(contacts)})

            except Exception as e:
                self.logger.error(f"Error getting emergency contacts: {e}")
                self._send_json({"error": f"Error getting emergency contacts: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Emergency notification system not initialized"}, 500)

    def _handle_add_emergency_contact(self):
        """Add emergency contact"""
        # SECURITY: Require admin authentication
        is_admin, payload = self._require_admin()
        if not is_admin:
            self._send_json({"error": "Admin privileges required"}, 403)
            return

        if self.pbx_core and hasattr(self.pbx_core, "emergency_notification"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                contact = self.pbx_core.emergency_notification.add_emergency_contact(
                    name=data.get("name"),
                    extension=data.get("extension"),
                    phone=data.get("phone"),
                    email=data.get("email"),
                    priority=data.get("priority", 1),
                    notification_methods=data.get("notification_methods", ["call"]),
                )

                self._send_json(
                    {
                        "success": True,
                        "contact": contact.to_dict(),
                        "message": "Emergency contact added successfully",
                    }
                )

            except Exception as e:
                self.logger.error(f"Error adding emergency contact: {e}")
                self._send_json({"error": f"Error adding emergency contact: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Emergency notification system not initialized"}, 500)

    def _handle_delete_emergency_contact(self, contact_id: str):
        """Delete emergency contact"""
        if self.pbx_core and hasattr(self.pbx_core, "emergency_notification"):
            try:
                success = self.pbx_core.emergency_notification.remove_emergency_contact(contact_id)

                if success:
                    self._send_json(
                        {"success": True, "message": "Emergency contact removed successfully"}
                    )
                else:
                    self._send_json({"error": "Contact not found"}, 404)

            except Exception as e:
                self.logger.error(f"Error deleting emergency contact: {e}")
                self._send_json({"error": f"Error deleting emergency contact: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Emergency notification system not initialized"}, 500)

    def _handle_trigger_emergency_notification(self):
        """Manually trigger emergency notification"""
        if self.pbx_core and hasattr(self.pbx_core, "emergency_notification"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                success = self.pbx_core.emergency_notification.trigger_emergency_notification(
                    trigger_type=data.get("trigger_type", "manual"), details=data.get("details", {})
                )

                self._send_json({"success": success, "message": "Emergency notification triggered"})

            except Exception as e:
                self.logger.error(f"Error triggering emergency notification: {e}")
                self._send_json(
                    {"error": f"Error triggering emergency notification: {str(e)}"}, 500
                )
        else:
            self._send_json({"error": "Emergency notification system not initialized"}, 500)

    def _handle_get_emergency_history(self):
        """Get emergency notification history"""
        if self.pbx_core and hasattr(self.pbx_core, "emergency_notification"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                limit = int(params.get("limit", [50])[0])

                history = self.pbx_core.emergency_notification.get_notification_history(limit)

                self._send_json({"history": history, "total": len(history)})

            except Exception as e:
                self.logger.error(f"Error getting emergency history: {e}")
                self._send_json({"error": f"Error getting emergency history: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Emergency notification system not initialized"}, 500)

    def _handle_test_emergency_notification(self):
        """Test emergency notification system"""
        if self.pbx_core and hasattr(self.pbx_core, "emergency_notification"):
            try:
                result = self.pbx_core.emergency_notification.test_emergency_notification()
                self._send_json(result)

            except Exception as e:
                self.logger.error(f"Error testing emergency notification: {e}")
                self._send_json({"error": f"Error testing emergency notification: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Emergency notification system not initialized"}, 500)

    # SIP Trunk Management Handlers
    def _handle_get_sip_trunks(self):
        """Get all SIP trunks"""
        if self.pbx_core and hasattr(self.pbx_core, "trunk_system"):
            try:
                trunks = self.pbx_core.trunk_system.get_trunk_status()
                self._send_json({"trunks": trunks, "count": len(trunks)})
            except Exception as e:
                self.logger.error(f"Error getting SIP trunks: {e}")
                self._send_json({"error": f"Error getting SIP trunks: {str(e)}"}, 500)
        else:
            self._send_json({"error": "SIP trunk system not initialized"}, 500)

    def _handle_get_trunk_health(self):
        """Get health status of all trunks"""
        if self.pbx_core and hasattr(self.pbx_core, "trunk_system"):
            try:
                health_data = []
                for trunk in self.pbx_core.trunk_system.trunks.values():
                    health_metrics = trunk.get_health_metrics()
                    health_metrics["trunk_id"] = trunk.trunk_id
                    health_metrics["name"] = trunk.name
                    health_data.append(health_metrics)

                self._send_json(
                    {
                        "health": health_data,
                        "monitoring_active": self.pbx_core.trunk_system.monitoring_active,
                        "failover_enabled": self.pbx_core.trunk_system.failover_enabled,
                    }
                )
            except Exception as e:
                self.logger.error(f"Error getting trunk health: {e}")
                self._send_json({"error": f"Error getting trunk health: {str(e)}"}, 500)
        else:
            self._send_json({"error": "SIP trunk system not initialized"}, 500)

    def _handle_add_sip_trunk(self):
        """Add a new SIP trunk"""
        if self.pbx_core and hasattr(self.pbx_core, "trunk_system"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                from pbx.features.sip_trunk import SIPTrunk

                trunk = SIPTrunk(
                    trunk_id=data["trunk_id"],
                    name=data["name"],
                    host=data["host"],
                    username=data["username"],
                    password=data["password"],
                    port=data.get("port", 5060),
                    codec_preferences=data.get("codec_preferences", ["G.711", "G.729"]),
                    priority=data.get("priority", 100),
                    max_channels=data.get("max_channels", 10),
                    health_check_interval=data.get("health_check_interval", 60),
                )

                self.pbx_core.trunk_system.add_trunk(trunk)
                trunk.register()

                self._send_json(
                    {
                        "success": True,
                        "message": f"Trunk {trunk.name} added successfully",
                        "trunk": trunk.to_dict(),
                    }
                )

            except Exception as e:
                self.logger.error(f"Error adding SIP trunk: {e}")
                self._send_json({"error": f"Error adding SIP trunk: {str(e)}"}, 500)
        else:
            self._send_json({"error": "SIP trunk system not initialized"}, 500)

    def _handle_delete_sip_trunk(self, trunk_id: str):
        """Delete a SIP trunk"""
        if self.pbx_core and hasattr(self.pbx_core, "trunk_system"):
            try:
                trunk = self.pbx_core.trunk_system.get_trunk(trunk_id)
                if trunk:
                    self.pbx_core.trunk_system.remove_trunk(trunk_id)
                    self._send_json(
                        {"success": True, "message": f"Trunk {trunk_id} removed successfully"}
                    )
                else:
                    self._send_json({"error": "Trunk not found"}, 404)

            except Exception as e:
                self.logger.error(f"Error deleting SIP trunk: {e}")
                self._send_json({"error": f"Error deleting SIP trunk: {str(e)}"}, 500)
        else:
            self._send_json({"error": "SIP trunk system not initialized"}, 500)

    def _handle_test_sip_trunk(self):
        """Test a SIP trunk connection"""
        if self.pbx_core and hasattr(self.pbx_core, "trunk_system"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                trunk_id = data.get("trunk_id")
                trunk = self.pbx_core.trunk_system.get_trunk(trunk_id)

                if trunk:
                    # Perform health check
                    health_status = trunk.check_health()

                    self._send_json(
                        {
                            "success": True,
                            "trunk_id": trunk_id,
                            "health_status": health_status.value,
                            "metrics": trunk.get_health_metrics(),
                        }
                    )
                else:
                    self._send_json({"error": "Trunk not found"}, 404)

            except Exception as e:
                self.logger.error(f"Error testing SIP trunk: {e}")
                self._send_json({"error": f"Error testing SIP trunk: {str(e)}"}, 500)
        else:
            self._send_json({"error": "SIP trunk system not initialized"}, 500)

    # Least-Cost Routing Handlers
    def _handle_add_lcr_rate(self):
        """Add a new LCR rate"""
        if self.pbx_core and hasattr(self.pbx_core, "lcr"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                self.pbx_core.lcr.add_rate(
                    trunk_id=data["trunk_id"],
                    pattern=data["pattern"],
                    rate_per_minute=float(data["rate_per_minute"]),
                    description=data.get("description", ""),
                    connection_fee=float(data.get("connection_fee", 0.0)),
                    minimum_seconds=int(data.get("minimum_seconds", 0)),
                    billing_increment=int(data.get("billing_increment", 1)),
                )

                self._send_json({"success": True, "message": "LCR rate added successfully"})

            except Exception as e:
                self.logger.error(f"Error adding LCR rate: {e}")
                self._send_json({"error": f"Error adding LCR rate: {str(e)}"}, 500)
        else:
            self._send_json({"error": "LCR system not initialized"}, 500)

    def _handle_add_lcr_time_rate(self):
        """Add a time-based rate modifier"""
        if self.pbx_core and hasattr(self.pbx_core, "lcr"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                self.pbx_core.lcr.add_time_based_rate(
                    name=data["name"],
                    start_hour=int(data["start_hour"]),
                    start_minute=int(data["start_minute"]),
                    end_hour=int(data["end_hour"]),
                    end_minute=int(data["end_minute"]),
                    days=data["days"],  # List of day indices
                    multiplier=float(data["multiplier"]),
                )

                self._send_json({"success": True, "message": "Time-based rate added successfully"})

            except Exception as e:
                self.logger.error(f"Error adding time-based rate: {e}")
                self._send_json({"error": f"Error adding time-based rate: {str(e)}"}, 500)
        else:
            self._send_json({"error": "LCR system not initialized"}, 500)

    def _handle_get_lcr_rates(self):
        """Get all LCR rates"""
        if self.pbx_core and hasattr(self.pbx_core, "lcr"):
            try:
                rates = []
                for rate_entry in self.pbx_core.lcr.rate_entries:
                    rates.append(
                        {
                            "trunk_id": rate_entry.trunk_id,
                            "pattern": rate_entry.pattern.pattern,
                            "description": rate_entry.pattern.description,
                            "rate_per_minute": rate_entry.rate_per_minute,
                            "connection_fee": rate_entry.connection_fee,
                            "minimum_seconds": rate_entry.minimum_seconds,
                            "billing_increment": rate_entry.billing_increment,
                        }
                    )

                time_rates = []
                for time_rate in self.pbx_core.lcr.time_based_rates:
                    time_rates.append(
                        {
                            "name": time_rate.name,
                            "start_time": time_rate.start_time.strftime("%H:%M"),
                            "end_time": time_rate.end_time.strftime("%H:%M"),
                            "days_of_week": time_rate.days_of_week,
                            "rate_multiplier": time_rate.rate_multiplier,
                        }
                    )

                self._send_json({"rates": rates, "time_rates": time_rates, "count": len(rates)})

            except Exception as e:
                self.logger.error(f"Error getting LCR rates: {e}")
                self._send_json({"error": f"Error getting LCR rates: {str(e)}"}, 500)
        else:
            self._send_json({"error": "LCR system not initialized"}, 500)

    def _handle_get_lcr_statistics(self):
        """Get LCR statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "lcr"):
            try:
                stats = self.pbx_core.lcr.get_statistics()
                self._send_json(stats)

            except Exception as e:
                self.logger.error(f"Error getting LCR statistics: {e}")
                self._send_json({"error": f"Error getting LCR statistics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "LCR system not initialized"}, 500)

    def _handle_clear_lcr_rates(self):
        """Clear all LCR rates"""
        if self.pbx_core and hasattr(self.pbx_core, "lcr"):
            try:
                self.pbx_core.lcr.clear_rates()
                self._send_json({"success": True, "message": "All LCR rates cleared successfully"})

            except Exception as e:
                self.logger.error(f"Error clearing LCR rates: {e}")
                self._send_json({"error": f"Error clearing LCR rates: {str(e)}"}, 500)
        else:
            self._send_json({"error": "LCR system not initialized"}, 500)

    def _handle_clear_lcr_time_rates(self):
        """Clear all time-based rates"""
        if self.pbx_core and hasattr(self.pbx_core, "lcr"):
            try:
                self.pbx_core.lcr.clear_time_rates()
                self._send_json(
                    {"success": True, "message": "All time-based rates cleared successfully"}
                )

            except Exception as e:
                self.logger.error(f"Error clearing time-based rates: {e}")
                self._send_json({"error": f"Error clearing time-based rates: {str(e)}"}, 500)
        else:
            self._send_json({"error": "LCR system not initialized"}, 500)

    # Find Me/Follow Me Handlers
    def _handle_get_fmfm_extensions(self):
        """Get all extensions with FMFM configured"""
        if self.pbx_core and hasattr(self.pbx_core, "find_me_follow_me"):
            try:
                extensions = self.pbx_core.find_me_follow_me.list_extensions_with_fmfm()
                configs = []
                for ext in extensions:
                    config = self.pbx_core.find_me_follow_me.get_config(ext)
                    if config:
                        configs.append(config)

                self._send_json({"extensions": configs, "count": len(configs)})
            except Exception as e:
                self.logger.error(f"Error getting FMFM extensions: {e}")
                self._send_json({"error": f"Error getting FMFM extensions: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Find Me/Follow Me not initialized"}, 500)

    def _handle_get_fmfm_config(self, extension: str):
        """Get FMFM configuration for an extension"""
        if self.pbx_core and hasattr(self.pbx_core, "find_me_follow_me"):
            try:
                config = self.pbx_core.find_me_follow_me.get_config(extension)
                if config:
                    self._send_json(config)
                else:
                    self._send_json(
                        {
                            "extension": extension,
                            "enabled": False,
                            "message": "No FMFM configuration found",
                        }
                    )
            except Exception as e:
                self.logger.error(f"Error getting FMFM config for {extension}: {e}")
                self._send_json({"error": f"Error getting FMFM config: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Find Me/Follow Me not initialized"}, 500)

    def _handle_get_fmfm_statistics(self):
        """Get FMFM statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "find_me_follow_me"):
            try:
                stats = self.pbx_core.find_me_follow_me.get_statistics()
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting FMFM statistics: {e}")
                self._send_json({"error": f"Error getting FMFM statistics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Find Me/Follow Me not initialized"}, 500)

    def _handle_set_fmfm_config(self):
        """Set FMFM configuration for an extension"""
        self.logger.info("Received FMFM config save request")

        if self.pbx_core and hasattr(self.pbx_core, "find_me_follow_me"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                self.logger.info(f"FMFM config data: {data}")

                extension = data.get("extension")
                if not extension:
                    self.logger.warning("FMFM config request missing extension")
                    self._send_json({"error": "Extension required"}, 400)
                    return

                success = self.pbx_core.find_me_follow_me.set_config(extension, data)

                if success:
                    self.logger.info(f"Successfully configured FMFM for extension {extension}")
                    self._send_json(
                        {
                            "success": True,
                            "message": f"FMFM configured for extension {extension}",
                            "config": self.pbx_core.find_me_follow_me.get_config(extension),
                        }
                    )
                else:
                    self.logger.error(f"Failed to set FMFM configuration for extension {extension}")
                    self._send_json({"error": "Failed to set FMFM configuration"}, 500)

            except Exception as e:
                self.logger.error(f"Error setting FMFM config: {e}")
                self._send_json({"error": f"Error setting FMFM config: {str(e)}"}, 500)
        else:
            self.logger.error("Find Me/Follow Me not initialized")
            self._send_json({"error": "Find Me/Follow Me not initialized"}, 500)

    def _handle_add_fmfm_destination(self):
        """Add a destination to FMFM config"""
        if self.pbx_core and hasattr(self.pbx_core, "find_me_follow_me"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                extension = data.get("extension")
                number = data.get("number")
                ring_time = data.get("ring_time", 20)

                if not extension or not number:
                    self._send_json({"error": "Extension and number required"}, 400)
                    return

                success = self.pbx_core.find_me_follow_me.add_destination(
                    extension, number, ring_time
                )

                if success:
                    self._send_json(
                        {
                            "success": True,
                            "message": f"Destination {number} added to {extension}",
                            "config": self.pbx_core.find_me_follow_me.get_config(extension),
                        }
                    )
                else:
                    self._send_json({"error": "Failed to add destination"}, 500)

            except Exception as e:
                self.logger.error(f"Error adding FMFM destination: {e}")
                self._send_json({"error": f"Error adding FMFM destination: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Find Me/Follow Me not initialized"}, 500)

    def _handle_remove_fmfm_destination(self, extension: str, number: str):
        """Remove a destination from FMFM config"""
        if self.pbx_core and hasattr(self.pbx_core, "find_me_follow_me"):
            try:
                success = self.pbx_core.find_me_follow_me.remove_destination(extension, number)

                if success:
                    self._send_json(
                        {
                            "success": True,
                            "message": f"Destination {number} removed from {extension}",
                        }
                    )
                else:
                    self._send_json({"error": "Failed to remove destination"}, 404)

            except Exception as e:
                self.logger.error(f"Error removing FMFM destination: {e}")
                self._send_json({"error": f"Error removing FMFM destination: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Find Me/Follow Me not initialized"}, 500)

    def _handle_disable_fmfm(self, extension: str):
        """Delete FMFM configuration for an extension"""
        if self.pbx_core and hasattr(self.pbx_core, "find_me_follow_me"):
            try:
                success = self.pbx_core.find_me_follow_me.delete_config(extension)

                if success:
                    self._send_json(
                        {
                            "success": True,
                            "message": f"FMFM configuration deleted for extension {extension}",
                        }
                    )
                else:
                    self._send_json({"error": "FMFM configuration not found"}, 404)

            except Exception as e:
                self.logger.error(f"Error deleting FMFM config: {e}")
                self._send_json({"error": f"Error deleting FMFM config: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Find Me/Follow Me not initialized"}, 500)

    # Time-Based Routing Handlers
    def _handle_get_time_routing_rules(self):
        """Get all time-based routing rules"""
        if self.pbx_core and hasattr(self.pbx_core, "time_based_routing"):
            try:
                # Parse query parameters for filtering
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                destination = params.get("destination", [None])[0]

                rules = self.pbx_core.time_based_routing.list_rules(destination=destination)
                self._send_json({"rules": rules, "count": len(rules)})
            except Exception as e:
                self.logger.error(f"Error getting time routing rules: {e}")
                self._send_json({"error": f"Error getting time routing rules: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Time-based routing not initialized"}, 500)

    def _handle_get_time_routing_statistics(self):
        """Get time-based routing statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "time_based_routing"):
            try:
                stats = self.pbx_core.time_based_routing.get_statistics()
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting time routing statistics: {e}")
                self._send_json({"error": f"Error getting time routing statistics: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Time-based routing not initialized"}, 500)

    def _handle_add_time_routing_rule(self):
        """Add a time-based routing rule"""
        if self.pbx_core and hasattr(self.pbx_core, "time_based_routing"):
            try:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                # Validate required fields
                required_fields = ["name", "destination", "route_to", "time_conditions"]
                if not all(field in data for field in required_fields):
                    self._send_json({"error": "Missing required fields"}, 400)
                    return

                rule_id = self.pbx_core.time_based_routing.add_rule(data)

                if rule_id:
                    self._send_json(
                        {
                            "success": True,
                            "rule_id": rule_id,
                            "message": f'Time routing rule "{data["name"]}" added successfully',
                        }
                    )
                else:
                    self._send_json({"error": "Failed to add time routing rule"}, 500)

            except Exception as e:
                self.logger.error(f"Error adding time routing rule: {e}")
                self._send_json({"error": f"Error adding time routing rule: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Time-based routing not initialized"}, 500)

    def _handle_delete_time_routing_rule(self, rule_id: str):
        """Delete a time-based routing rule"""
        if self.pbx_core and hasattr(self.pbx_core, "time_based_routing"):
            try:
                success = self.pbx_core.time_based_routing.delete_rule(rule_id)

                if success:
                    self._send_json(
                        {"success": True, "message": f"Time routing rule {rule_id} deleted"}
                    )
                else:
                    self._send_json({"error": "Rule not found"}, 404)

            except Exception as e:
                self.logger.error(f"Error deleting time routing rule: {e}")
                self._send_json({"error": f"Error deleting time routing rule: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Time-based routing not initialized"}, 500)

    # Recording Retention Handlers
    def _handle_get_retention_policies(self):
        """Get all recording retention policies"""
        if self.pbx_core and hasattr(self.pbx_core, "recording_retention"):
            try:
                policies = []
                for (
                    policy_id,
                    policy,
                ) in self.pbx_core.recording_retention.retention_policies.items():
                    # Sanitize output - don't expose sensitive paths
                    safe_policy = {
                        "policy_id": policy_id,
                        "name": policy.get("name", policy_id),
                        "retention_days": policy.get("retention_days", 0),
                        "tags": policy.get("tags", []),
                        "created_at": None,
                    }

                    # Safely handle created_at datetime
                    created_at = policy.get("created_at")
                    if created_at and hasattr(created_at, "isoformat"):
                        safe_policy["created_at"] = created_at.isoformat()

                    policies.append(safe_policy)

                self._send_json({"policies": policies, "count": len(policies)})
            except Exception as e:
                self.logger.error(f"Error getting retention policies: {e}")
                self._send_json({"error": "Error getting retention policies"}, 500)
        else:
            self._send_json({"error": "Recording retention not initialized"}, 500)

    def _handle_get_retention_statistics(self):
        """Get recording retention statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "recording_retention"):
            try:
                stats = self.pbx_core.recording_retention.get_statistics()

                # Transform to match frontend expectations
                result = {
                    "total_policies": stats.get("policies", 0),
                    "total_recordings": stats.get("total_recordings", 0),
                    "deleted_count": stats.get("lifetime_deleted", 0),
                    "last_cleanup": stats.get("last_cleanup"),
                }

                self._send_json(result)
            except Exception as e:
                self.logger.error(f"Error getting retention statistics: {e}")
                self._send_json({"error": "Error getting retention statistics"}, 500)
        else:
            self._send_json({"error": "Recording retention not initialized"}, 500)

    def _handle_add_retention_policy(self):
        """Add a recording retention policy"""
        if self.pbx_core and hasattr(self.pbx_core, "recording_retention"):
            try:
                content_length = int(self.headers["Content-Length"])
                # Limit request size to prevent DoS
                if content_length > 10240:  # 10KB limit
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                # Validate required fields
                required_fields = ["name", "retention_days"]
                if not all(field in data for field in required_fields):
                    self._send_json({"error": "Missing required fields: name, retention_days"}, 400)
                    return

                # Validate retention_days is a positive integer
                try:
                    retention_days = int(data["retention_days"])
                    if retention_days < 1 or retention_days > 3650:  # Max 10 years
                        self._send_json({"error": "retention_days must be between 1 and 3650"}, 400)
                        return
                except (ValueError, TypeError):
                    self._send_json({"error": "retention_days must be a valid integer"}, 400)
                    return

                # Sanitize name to prevent injection
                import re

                if not re.match(r"^[a-zA-Z0-9_\-\s]+$", data["name"]):
                    self._send_json({"error": "Policy name contains invalid characters"}, 400)
                    return

                policy_id = self.pbx_core.recording_retention.add_policy(data)

                if policy_id:
                    self._send_json(
                        {
                            "success": True,
                            "policy_id": policy_id,
                            "message": f'Retention policy "{data["name"]}" added successfully',
                        }
                    )
                else:
                    self._send_json({"error": "Failed to add retention policy"}, 500)

            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error adding retention policy: {e}")
                self._send_json({"error": "Error adding retention policy"}, 500)
        else:
            self._send_json({"error": "Recording retention not initialized"}, 500)

    def _handle_delete_retention_policy(self, policy_id: str):
        """Delete a retention policy"""
        if self.pbx_core and hasattr(self.pbx_core, "recording_retention"):
            try:
                if policy_id in self.pbx_core.recording_retention.retention_policies:
                    del self.pbx_core.recording_retention.retention_policies[policy_id]
                    self._send_json(
                        {"success": True, "message": f"Retention policy {policy_id} deleted"}
                    )
                else:
                    self._send_json({"error": "Policy not found"}, 404)

            except Exception as e:
                self.logger.error(f"Error deleting retention policy: {e}")
                self._send_json({"error": "Error deleting retention policy"}, 500)
        else:
            self._send_json({"error": "Recording retention not initialized"}, 500)

    # Fraud Detection Handlers
    def _handle_get_fraud_alerts(self):
        """Get fraud detection alerts"""
        if self.pbx_core and hasattr(self.pbx_core, "fraud_detection"):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                extension = params.get("extension", [None])[0]
                # Note: backend get_alerts uses 'hours' parameter, not 'limit'
                hours = int(params.get("hours", [24])[0])

                # Validate hours
                hours = min(hours, 720)  # Max 30 days

                alerts = self.pbx_core.fraud_detection.get_alerts(extension=extension, hours=hours)

                self._send_json({"alerts": alerts, "count": len(alerts)})
            except Exception as e:
                self.logger.error(f"Error getting fraud alerts: {e}")
                self._send_json({"error": "Error getting fraud alerts"}, 500)
        else:
            self._send_json({"error": "Fraud detection not initialized"}, 500)

    def _handle_get_fraud_statistics(self):
        """Get fraud detection statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "fraud_detection"):
            try:
                stats = self.pbx_core.fraud_detection.get_statistics()

                # Transform to match frontend expectations
                result = {
                    "total_alerts": stats.get("total_alerts", 0),
                    "high_risk_alerts": sum(
                        1
                        for a in self.pbx_core.fraud_detection.alerts
                        if a.get("fraud_score", 0) > 0.7
                    ),
                    "blocked_patterns_count": stats.get("blocked_patterns", 0),
                    "extensions_flagged": stats.get("total_extensions_tracked", 0),
                    "alerts_24h": stats.get("alerts_24h", 0),
                    "blocked_patterns": self.pbx_core.fraud_detection.blocked_patterns,
                }

                self._send_json(result)
            except Exception as e:
                self.logger.error(f"Error getting fraud statistics: {e}")
                self._send_json({"error": "Error getting fraud statistics"}, 500)
        else:
            self._send_json({"error": "Fraud detection not initialized"}, 500)

    def _handle_get_fraud_extension_stats(self, extension: str):
        """Get fraud statistics for a specific extension"""
        if self.pbx_core and hasattr(self.pbx_core, "fraud_detection"):
            try:
                # Validate extension format
                import re

                if not re.match(r"^\d{3,5}$", extension):
                    self._send_json({"error": "Invalid extension format"}, 400)
                    return

                stats = self.pbx_core.fraud_detection.get_extension_statistics(extension)
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting extension fraud stats: {e}")
                self._send_json({"error": "Error getting extension statistics"}, 500)
        else:
            self._send_json({"error": "Fraud detection not initialized"}, 500)

    def _handle_add_blocked_pattern(self):
        """Add a blocked number pattern"""
        if self.pbx_core and hasattr(self.pbx_core, "fraud_detection"):
            try:
                content_length = int(self.headers["Content-Length"])
                # Limit request size
                if content_length > 2048:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                # Validate required fields
                if "pattern" not in data or "reason" not in data:
                    self._send_json({"error": "Missing required fields: pattern, reason"}, 400)
                    return

                # Validate pattern is a valid regex (prevent ReDoS)
                import re

                try:
                    re.compile(data["pattern"])
                except re.error:
                    self._send_json({"error": "Invalid regex pattern"}, 400)
                    return

                # Sanitize reason
                reason = str(data["reason"])[:200]  # Limit length

                success = self.pbx_core.fraud_detection.add_blocked_pattern(data["pattern"], reason)

                if success:
                    self._send_json(
                        {"success": True, "message": "Blocked pattern added successfully"}
                    )
                else:
                    self._send_json({"error": "Failed to add blocked pattern"}, 500)

            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error adding blocked pattern: {e}")
                self._send_json({"error": "Error adding blocked pattern"}, 500)
        else:
            self._send_json({"error": "Fraud detection not initialized"}, 500)

    def _handle_delete_blocked_pattern(self, pattern_id: str):
        """Delete a blocked pattern"""
        if self.pbx_core and hasattr(self.pbx_core, "fraud_detection"):
            try:
                # Find and remove pattern by ID/index
                try:
                    index = int(pattern_id)
                    if 0 <= index < len(self.pbx_core.fraud_detection.blocked_patterns):
                        del self.pbx_core.fraud_detection.blocked_patterns[index]
                        self._send_json({"success": True, "message": "Blocked pattern deleted"})
                    else:
                        self._send_json({"error": "Pattern not found"}, 404)
                except (ValueError, IndexError):
                    self._send_json({"error": "Invalid pattern ID"}, 400)

            except Exception as e:
                self.logger.error(f"Error deleting blocked pattern: {e}")
                self._send_json({"error": "Error deleting blocked pattern"}, 500)
        else:
            self._send_json({"error": "Fraud detection not initialized"}, 500)

    # Callback Queue Handlers
    def _handle_request_callback(self):
        """Request a callback from queue"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                content_length = int(self.headers["Content-Length"])
                if content_length > 4096:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                # Validate required fields
                if "queue_id" not in data or "caller_number" not in data:
                    self._send_json(
                        {"error": "Missing required fields: queue_id, caller_number"}, 400
                    )
                    return

                # Sanitize inputs
                queue_id = str(data["queue_id"])[:50]
                caller_number = str(data["caller_number"])[:50]
                caller_name = (
                    str(data.get("caller_name", ""))[:100] if data.get("caller_name") else None
                )

                # Parse preferred_time if provided
                preferred_time = None
                if "preferred_time" in data:
                    try:
                        from datetime import datetime

                        preferred_time = datetime.fromisoformat(data["preferred_time"])
                    except (ValueError, TypeError):
                        self._send_json(
                            {"error": "Invalid preferred_time format. Use ISO 8601 format."}, 400
                        )
                        return

                result = self.pbx_core.callback_queue.request_callback(
                    queue_id, caller_number, caller_name, preferred_time
                )

                if "error" in result:
                    self._send_json(result, 400)
                else:
                    self._send_json({"success": True, **result})
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error requesting callback: {e}")
                self._send_json({"error": "Error requesting callback"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    def _handle_start_callback(self):
        """Start processing a callback"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                content_length = int(self.headers["Content-Length"])
                if content_length > 2048:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                if "callback_id" not in data or "agent_id" not in data:
                    self._send_json(
                        {"error": "Missing required fields: callback_id, agent_id"}, 400
                    )
                    return

                callback_id = str(data["callback_id"])[:100]
                agent_id = str(data["agent_id"])[:50]

                result = self.pbx_core.callback_queue.start_callback(callback_id, agent_id)

                if "error" in result:
                    self._send_json(result, 404)
                else:
                    self._send_json({"success": True, **result})
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error starting callback: {e}")
                self._send_json({"error": "Error starting callback"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    def _handle_complete_callback(self):
        """Complete a callback"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                content_length = int(self.headers["Content-Length"])
                if content_length > 4096:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                if "callback_id" not in data or "success" not in data:
                    self._send_json({"error": "Missing required fields: callback_id, success"}, 400)
                    return

                callback_id = str(data["callback_id"])[:100]
                success = bool(data["success"])
                notes = str(data.get("notes", ""))[:500] if data.get("notes") else None

                result = self.pbx_core.callback_queue.complete_callback(callback_id, success, notes)

                if result:
                    self._send_json({"success": True, "message": "Callback completed"})
                else:
                    self._send_json({"error": "Callback not found"}, 404)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error completing callback: {e}")
                self._send_json({"error": "Error completing callback"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    def _handle_cancel_callback(self):
        """Cancel a pending callback"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                content_length = int(self.headers["Content-Length"])
                if content_length > 2048:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                if "callback_id" not in data:
                    self._send_json({"error": "Missing required field: callback_id"}, 400)
                    return

                callback_id = str(data["callback_id"])[:100]

                result = self.pbx_core.callback_queue.cancel_callback(callback_id)

                if result:
                    self._send_json({"success": True, "message": "Callback cancelled"})
                else:
                    self._send_json({"error": "Callback not found"}, 404)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error cancelling callback: {e}")
                self._send_json({"error": "Error cancelling callback"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    def _handle_get_callback_statistics(self):
        """Get callback queue statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                stats = self.pbx_core.callback_queue.get_statistics()
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting callback statistics: {e}")
                self._send_json({"error": "Error getting callback statistics"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    def _handle_get_callback_list(self):
        """Get list of all callbacks"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                callbacks = []
                for callback_id in self.pbx_core.callback_queue.callbacks:
                    info = self.pbx_core.callback_queue.get_callback_info(callback_id)
                    if info:
                        callbacks.append(info)

                # Sort by requested_at descending (most recent first)
                callbacks.sort(key=lambda x: x.get("requested_at", ""), reverse=True)

                self._send_json({"callbacks": callbacks})
            except Exception as e:
                self.logger.error(f"Error getting callback list: {e}")
                self._send_json({"error": "Error getting callback list"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    def _handle_get_queue_callbacks(self, queue_id: str):
        """Get callbacks for a specific queue"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                # Sanitize queue_id
                import re

                if not re.match(r"^[\w-]{1,50}$", queue_id):
                    self._send_json({"error": "Invalid queue_id format"}, 400)
                    return

                callbacks = self.pbx_core.callback_queue.list_queue_callbacks(queue_id)
                stats = self.pbx_core.callback_queue.get_queue_statistics(queue_id)

                self._send_json({"queue_id": queue_id, "callbacks": callbacks, "statistics": stats})
            except Exception as e:
                self.logger.error(f"Error getting queue callbacks: {e}")
                self._send_json({"error": "Error getting queue callbacks"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    def _handle_get_callback_info(self, callback_id: str):
        """Get information about a specific callback"""
        if self.pbx_core and hasattr(self.pbx_core, "callback_queue"):
            try:
                # Sanitize callback_id
                import re

                if not re.match(r"^cb_[\w]{1,100}$", callback_id):
                    self._send_json({"error": "Invalid callback_id format"}, 400)
                    return

                info = self.pbx_core.callback_queue.get_callback_info(callback_id)

                if info:
                    self._send_json(info)
                else:
                    self._send_json({"error": "Callback not found"}, 404)
            except Exception as e:
                self.logger.error(f"Error getting callback info: {e}")
                self._send_json({"error": "Error getting callback info"}, 500)
        else:
            self._send_json({"error": "Callback queue not initialized"}, 500)

    # Mobile Push Notification Handlers
    def _handle_register_device(self):
        """Register a mobile device for push notifications"""
        if self.pbx_core and hasattr(self.pbx_core, "mobile_push"):
            try:
                content_length = int(self.headers["Content-Length"])
                if content_length > 4096:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                if "user_id" not in data or "device_token" not in data:
                    self._send_json(
                        {"error": "Missing required fields: user_id, device_token"}, 400
                    )
                    return

                user_id = str(data["user_id"])[:50]
                device_token = str(data["device_token"])[:255]
                platform = str(data.get("platform", "unknown"))[:20]

                success = self.pbx_core.mobile_push.register_device(user_id, device_token, platform)

                if success:
                    self._send_json({"success": True, "message": "Device registered successfully"})
                else:
                    self._send_json({"error": "Failed to register device"}, 500)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error registering device: {e}")
                self._send_json({"error": "Error registering device"}, 500)
        else:
            self._send_json({"error": "Mobile push notifications not initialized"}, 500)

    def _handle_unregister_device(self):
        """Unregister a mobile device"""
        if self.pbx_core and hasattr(self.pbx_core, "mobile_push"):
            try:
                content_length = int(self.headers["Content-Length"])
                if content_length > 4096:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                if "user_id" not in data or "device_token" not in data:
                    self._send_json(
                        {"error": "Missing required fields: user_id, device_token"}, 400
                    )
                    return

                user_id = str(data["user_id"])[:50]
                device_token = str(data["device_token"])[:255]

                success = self.pbx_core.mobile_push.unregister_device(user_id, device_token)

                if success:
                    self._send_json(
                        {"success": True, "message": "Device unregistered successfully"}
                    )
                else:
                    self._send_json({"error": "Device not found"}, 404)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error unregistering device: {e}")
                self._send_json({"error": "Error unregistering device"}, 500)
        else:
            self._send_json({"error": "Mobile push notifications not initialized"}, 500)

    def _handle_test_push_notification(self):
        """Send a test push notification"""
        if self.pbx_core and hasattr(self.pbx_core, "mobile_push"):
            try:
                content_length = int(self.headers["Content-Length"])
                if content_length > 4096:
                    self._send_json({"error": "Request too large"}, 413)
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))

                if "user_id" not in data:
                    self._send_json({"error": "Missing required field: user_id"}, 400)
                    return

                user_id = str(data["user_id"])[:50]

                result = self.pbx_core.mobile_push.send_test_notification(user_id)

                if "error" in result:
                    self._send_json(result, 400)
                else:
                    self._send_json({"success": True, **result})
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.logger.error(f"Error sending test notification: {e}")
                self._send_json({"error": "Error sending test notification"}, 500)
        else:
            self._send_json({"error": "Mobile push notifications not initialized"}, 500)

    def _handle_get_all_devices(self):
        """Get all registered mobile devices"""
        if self.pbx_core and hasattr(self.pbx_core, "mobile_push"):
            try:
                all_devices = []
                for user_id, devices in self.pbx_core.mobile_push.device_tokens.items():
                    for device in devices:
                        all_devices.append(
                            {
                                "user_id": user_id,
                                "platform": device["platform"],
                                "registered_at": device["registered_at"].isoformat(),
                                "last_seen": device["last_seen"].isoformat(),
                            }
                        )

                # Sort by last_seen descending
                all_devices.sort(key=lambda x: x["last_seen"], reverse=True)

                self._send_json({"devices": all_devices, "total": len(all_devices)})
            except Exception as e:
                self.logger.error(f"Error getting all devices: {e}")
                self._send_json({"error": "Error getting devices"}, 500)
        else:
            self._send_json({"error": "Mobile push notifications not initialized"}, 500)

    def _handle_get_user_devices(self, user_id: str):
        """Get devices for a specific user"""
        if self.pbx_core and hasattr(self.pbx_core, "mobile_push"):
            try:
                # Sanitize user_id
                import re

                if not re.match(r"^[\w]{1,50}$", user_id):
                    self._send_json({"error": "Invalid user_id format"}, 400)
                    return

                devices = self.pbx_core.mobile_push.get_user_devices(user_id)
                self._send_json({"user_id": user_id, "devices": devices, "count": len(devices)})
            except Exception as e:
                self.logger.error(f"Error getting user devices: {e}")
                self._send_json({"error": "Error getting user devices"}, 500)
        else:
            self._send_json({"error": "Mobile push notifications not initialized"}, 500)

    def _handle_get_push_statistics(self):
        """Get push notification statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "mobile_push"):
            try:
                # Count devices
                total_devices = sum(
                    len(devices) for devices in self.pbx_core.mobile_push.device_tokens.values()
                )
                total_users = len(self.pbx_core.mobile_push.device_tokens)

                # Count by platform
                platform_counts = {}
                for devices in self.pbx_core.mobile_push.device_tokens.values():
                    for device in devices:
                        platform = device["platform"]
                        platform_counts[platform] = platform_counts.get(platform, 0) + 1

                # Recent notifications
                recent_notifications = len(self.pbx_core.mobile_push.notification_history)

                self._send_json(
                    {
                        "total_devices": total_devices,
                        "total_users": total_users,
                        "platforms": platform_counts,
                        "recent_notifications": recent_notifications,
                    }
                )
            except Exception as e:
                self.logger.error(f"Error getting push statistics: {e}")
                self._send_json({"error": "Error getting push statistics"}, 500)
        else:
            self._send_json({"error": "Mobile push notifications not initialized"}, 500)

    def _handle_get_push_history(self):
        """Get push notification history"""
        if self.pbx_core and hasattr(self.pbx_core, "mobile_push"):
            try:
                # Get recent notification history
                history = []
                for notif in self.pbx_core.mobile_push.notification_history[-100:]:  # Last 100
                    history.append(
                        {
                            "user_id": notif["user_id"],
                            "title": notif["title"],
                            "body": notif["body"],
                            "sent_at": notif["sent_at"].isoformat(),
                            "success_count": notif.get("success_count", 0),
                            "failure_count": notif.get("failure_count", 0),
                        }
                    )

                # Sort by sent_at descending
                history.sort(key=lambda x: x["sent_at"], reverse=True)

                self._send_json({"history": history})
            except Exception as e:
                self.logger.error(f"Error getting push history: {e}")
                self._send_json({"error": "Error getting push history"}, 500)
        else:
            self._send_json({"error": "Mobile push notifications not initialized"}, 500)

    # Recording Announcements Handlers
    def _handle_get_announcement_statistics(self):
        """Get recording announcements statistics"""
        if self.pbx_core and hasattr(self.pbx_core, "recording_announcements"):
            try:
                stats = {
                    "enabled": self.pbx_core.recording_announcements.enabled,
                    "announcements_played": self.pbx_core.recording_announcements.announcements_played,
                    "consent_accepted": self.pbx_core.recording_announcements.consent_accepted,
                    "consent_declined": self.pbx_core.recording_announcements.consent_declined,
                    "announcement_type": self.pbx_core.recording_announcements.announcement_type,
                    "require_consent": self.pbx_core.recording_announcements.require_consent,
                }
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting announcement statistics: {e}")
                self._send_json({"error": "Error getting announcement statistics"}, 500)
        else:
            self._send_json({"error": "Recording announcements not initialized"}, 500)

    def _handle_get_announcement_config(self):
        """Get recording announcements configuration"""
        if self.pbx_core and hasattr(self.pbx_core, "recording_announcements"):
            try:
                config = self.pbx_core.recording_announcements.get_announcement_config()
                self._send_json(config)
            except Exception as e:
                self.logger.error(f"Error getting announcement config: {e}")
                self._send_json({"error": "Error getting announcement config"}, 500)
        else:
            self._send_json({"error": "Recording announcements not initialized"}, 500)

    # Framework Feature Handlers - Speech Analytics
    def _handle_get_speech_analytics_configs(self):
        """Get all speech analytics configurations"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.speech_analytics import SpeechAnalyticsEngine

                engine = SpeechAnalyticsEngine(self.pbx_core.database, self.pbx_core.config)
                configs = engine.get_all_configs()
                self._send_json({"configs": configs})
            except Exception as e:
                self.logger.error(f"Error getting speech analytics configs: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_speech_analytics_config(self, extension: str):
        """Get speech analytics config for extension"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.speech_analytics import SpeechAnalyticsEngine

                engine = SpeechAnalyticsEngine(self.pbx_core.database, self.pbx_core.config)
                config = engine.get_config(extension)
                if config:
                    self._send_json(config)
                else:
                    self._send_json({"error": "Config not found"}, 404)
            except Exception as e:
                self.logger.error(f"Error getting speech analytics config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_update_speech_analytics_config(self, extension: str):
        """Update speech analytics configuration"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.speech_analytics import SpeechAnalyticsEngine

                engine = SpeechAnalyticsEngine(self.pbx_core.database, self.pbx_core.config)
                if engine.update_config(extension, body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to update config"}, 500)
            except Exception as e:
                self.logger.error(f"Error updating speech analytics config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_analyze_sentiment(self):
        """Analyze sentiment of provided text"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                text = body.get("text", "")
                if not text:
                    self._send_json({"error": "Text required"}, 400)
                    return

                from pbx.features.speech_analytics import SpeechAnalyticsEngine

                engine = SpeechAnalyticsEngine(self.pbx_core.database, self.pbx_core.config)
                result = engine.analyze_sentiment(text)
                self._send_json(result)
            except Exception as e:
                self.logger.error(f"Error analyzing sentiment: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_generate_summary(self, call_id: str):
        """Generate call summary from transcript"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                transcript = body.get("transcript", "")
                if not transcript:
                    self._send_json({"error": "Transcript required"}, 400)
                    return

                from pbx.features.speech_analytics import SpeechAnalyticsEngine

                engine = SpeechAnalyticsEngine(self.pbx_core.database, self.pbx_core.config)
                summary = engine.generate_summary(call_id, transcript)
                self._send_json({"call_id": call_id, "summary": summary})
            except Exception as e:
                self.logger.error(f"Error generating summary: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_call_summary(self, call_id: str):
        """Get stored call summary"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.speech_analytics import SpeechAnalyticsEngine

                engine = SpeechAnalyticsEngine(self.pbx_core.database, self.pbx_core.config)
                summary = engine.get_call_summary(call_id)
                if summary:
                    self._send_json(summary)
                else:
                    self._send_json({"error": "Summary not found"}, 404)
            except Exception as e:
                self.logger.error(f"Error getting call summary: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    # Framework Feature Handlers - Video Conferencing
    def _handle_get_video_rooms(self):
        """Get all video conference rooms"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.video_conferencing import VideoConferencingEngine

                engine = VideoConferencingEngine(self.pbx_core.database, self.pbx_core.config)
                rooms = engine.get_all_rooms()
                self._send_json({"rooms": rooms})
            except Exception as e:
                self.logger.error(f"Error getting video rooms: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_video_room(self, room_id: str):
        """Get video conference room details"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.video_conferencing import VideoConferencingEngine

                engine = VideoConferencingEngine(self.pbx_core.database, self.pbx_core.config)
                room = engine.get_room(int(room_id))
                if room:
                    participants = engine.get_room_participants(int(room_id))
                    room["participants"] = participants
                    self._send_json(room)
                else:
                    self._send_json({"error": "Room not found"}, 404)
            except Exception as e:
                self.logger.error(f"Error getting video room: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_create_video_room(self):
        """Create video conference room"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.video_conferencing import VideoConferencingEngine

                engine = VideoConferencingEngine(self.pbx_core.database, self.pbx_core.config)
                room_id = engine.create_room(body)
                if room_id:
                    self._send_json({"room_id": room_id, "success": True})
                else:
                    self._send_json({"error": "Failed to create room"}, 500)
            except Exception as e:
                self.logger.error(f"Error creating video room: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_join_video_room(self, room_id: str):
        """Join video conference room"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.video_conferencing import VideoConferencingEngine

                engine = VideoConferencingEngine(self.pbx_core.database, self.pbx_core.config)
                if engine.join_room(int(room_id), body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to join room"}, 500)
            except Exception as e:
                self.logger.error(f"Error joining video room: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    # Framework Feature Handlers - Click-to-Dial
    def _handle_get_click_to_dial_configs(self):
        """Get all click-to-dial configurations"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.click_to_dial import ClickToDialEngine

                engine = ClickToDialEngine(
                    self.pbx_core.database, self.pbx_core.config, self.pbx_core
                )
                configs = engine.get_all_configs()
                self._send_json({"configs": configs})
            except Exception as e:
                self.logger.error(f"Error getting click-to-dial configs: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_click_to_dial_config(self, extension: str):
        """Get click-to-dial config for extension"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.click_to_dial import ClickToDialEngine

                engine = ClickToDialEngine(
                    self.pbx_core.database, self.pbx_core.config, self.pbx_core
                )
                config = engine.get_config(extension)
                if config:
                    self._send_json(config)
                else:
                    # Return default config
                    self._send_json(
                        {
                            "extension": extension,
                            "enabled": True,
                            "auto_answer": False,
                            "browser_notification": True,
                        }
                    )
            except Exception as e:
                self.logger.error(f"Error getting click-to-dial config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_update_click_to_dial_config(self, extension: str):
        """Update click-to-dial configuration"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.click_to_dial import ClickToDialEngine

                engine = ClickToDialEngine(
                    self.pbx_core.database, self.pbx_core.config, self.pbx_core
                )
                if engine.update_config(extension, body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to update config"}, 500)
            except Exception as e:
                self.logger.error(f"Error updating click-to-dial config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_click_to_dial_call(self, extension: str):
        """Initiate click-to-dial call"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                destination = body.get("destination")
                source = body.get("source", "web")

                from pbx.features.click_to_dial import ClickToDialEngine

                engine = ClickToDialEngine(
                    self.pbx_core.database, self.pbx_core.config, self.pbx_core
                )
                call_id = engine.initiate_call(extension, destination, source)

                if call_id:
                    self._send_json({"call_id": call_id, "success": True})
                else:
                    self._send_json({"error": "Failed to initiate call"}, 500)
            except Exception as e:
                self.logger.error(f"Error initiating click-to-dial call: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_click_to_dial_history(self, extension: str):
        """Get click-to-dial call history"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.click_to_dial import ClickToDialEngine

                engine = ClickToDialEngine(
                    self.pbx_core.database, self.pbx_core.config, self.pbx_core
                )
                history = engine.get_call_history(extension)
                self._send_json({"history": history})
            except Exception as e:
                self.logger.error(f"Error getting click-to-dial history: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    # Framework Feature Handlers - Team Messaging
    def _handle_get_team_channels(self):
        """Get all team messaging channels"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.team_collaboration import TeamMessagingEngine

                engine = TeamMessagingEngine(self.pbx_core.database, self.pbx_core.config)
                channels = engine.get_all_channels()
                self._send_json({"channels": channels})
            except Exception as e:
                self.logger.error(f"Error getting team channels: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_create_team_channel(self):
        """Create team messaging channel"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.team_collaboration import TeamMessagingEngine

                engine = TeamMessagingEngine(self.pbx_core.database, self.pbx_core.config)
                channel_id = engine.create_channel(body)
                if channel_id:
                    self._send_json({"channel_id": channel_id, "success": True})
                else:
                    self._send_json({"error": "Failed to create channel"}, 500)
            except Exception as e:
                self.logger.error(f"Error creating team channel: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_send_team_message(self):
        """Send team message"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.team_collaboration import TeamMessagingEngine

                engine = TeamMessagingEngine(self.pbx_core.database, self.pbx_core.config)
                message_id = engine.send_message(body)
                if message_id:
                    self._send_json({"message_id": message_id, "success": True})
                else:
                    self._send_json({"error": "Failed to send message"}, 500)
            except Exception as e:
                self.logger.error(f"Error sending team message: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_team_messages(self, channel_id: str):
        """Get team messages for channel"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.team_collaboration import TeamMessagingEngine

                engine = TeamMessagingEngine(self.pbx_core.database, self.pbx_core.config)
                messages = engine.get_channel_messages(int(channel_id))
                self._send_json({"messages": messages})
            except Exception as e:
                self.logger.error(f"Error getting team messages: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    # Framework Feature Handlers - Nomadic E911
    def _handle_get_e911_sites(self):
        """Get all E911 site configurations"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.nomadic_e911 import NomadicE911Engine

                engine = NomadicE911Engine(self.pbx_core.database, self.pbx_core.config)
                sites = engine.get_all_sites()
                self._send_json({"sites": sites})
            except Exception as e:
                self.logger.error(f"Error getting E911 sites: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_e911_location(self, extension: str):
        """Get E911 location for extension"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.nomadic_e911 import NomadicE911Engine

                engine = NomadicE911Engine(self.pbx_core.database, self.pbx_core.config)
                location = engine.get_location(extension)
                if location:
                    self._send_json(location)
                else:
                    self._send_json({"error": "Location not found"}, 404)
            except Exception as e:
                self.logger.error(f"Error getting E911 location: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_update_e911_location(self, extension: str):
        """Update E911 location for extension"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.nomadic_e911 import NomadicE911Engine

                engine = NomadicE911Engine(self.pbx_core.database, self.pbx_core.config)
                if engine.update_location(extension, body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to update location"}, 500)
            except Exception as e:
                self.logger.error(f"Error updating E911 location: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_create_e911_site(self):
        """Create E911 site configuration"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.nomadic_e911 import NomadicE911Engine

                engine = NomadicE911Engine(self.pbx_core.database, self.pbx_core.config)
                if engine.create_site_config(body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to create site"}, 500)
            except Exception as e:
                self.logger.error(f"Error creating E911 site: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_detect_e911_location(self, extension: str):
        """Auto-detect E911 location for extension by IP"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                ip_address = body.get("ip_address")
                if not ip_address:
                    self._send_json({"error": "IP address required"}, 400)
                    return

                from pbx.features.nomadic_e911 import NomadicE911Engine

                engine = NomadicE911Engine(self.pbx_core.database, self.pbx_core.config)
                location = engine.detect_location_by_ip(extension, ip_address)
                if location:
                    self._send_json(location)
                else:
                    self._send_json({"error": "Location could not be detected"}, 404)
            except Exception as e:
                self.logger.error(f"Error detecting E911 location: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_e911_history(self, extension: str):
        """Get E911 location history for extension"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.nomadic_e911 import NomadicE911Engine

                engine = NomadicE911Engine(self.pbx_core.database, self.pbx_core.config)
                history = engine.get_location_history(extension)
                self._send_json({"history": history})
            except Exception as e:
                self.logger.error(f"Error getting E911 history: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    # Framework Feature Handlers - CRM Integrations
    def _handle_get_hubspot_config(self):
        """Get HubSpot integration configuration"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.crm_integrations import HubSpotIntegration

                integration = HubSpotIntegration(self.pbx_core.database, self.pbx_core.config)
                config = integration.get_config()
                if config:
                    self._send_json(config)
                else:
                    self._send_json({"enabled": False})
            except Exception as e:
                self.logger.error(f"Error getting HubSpot config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_update_hubspot_config(self):
        """Update HubSpot integration configuration"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.crm_integrations import HubSpotIntegration

                integration = HubSpotIntegration(self.pbx_core.database, self.pbx_core.config)
                if integration.update_config(body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to update config"}, 500)
            except Exception as e:
                self.logger.error(f"Error updating HubSpot config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_zendesk_config(self):
        """Get Zendesk integration configuration"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.crm_integrations import ZendeskIntegration

                integration = ZendeskIntegration(self.pbx_core.database, self.pbx_core.config)
                config = integration.get_config()
                if config:
                    self._send_json(config)
                else:
                    self._send_json({"enabled": False})
            except Exception as e:
                self.logger.error(f"Error getting Zendesk config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_update_zendesk_config(self):
        """Update Zendesk integration configuration"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.crm_integrations import ZendeskIntegration

                integration = ZendeskIntegration(self.pbx_core.database, self.pbx_core.config)
                if integration.update_config(body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to update config"}, 500)
            except Exception as e:
                self.logger.error(f"Error updating Zendesk config: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_get_integration_activity(self):
        """Get integration activity log"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                # Query integration activity log directly from database
                result = self.pbx_core.database.execute(
                    """SELECT * FROM integration_activity_log 
                       ORDER BY created_at DESC LIMIT 100"""
                )

                activities = []
                for row in result or []:
                    activities.append(
                        {
                            "integration_type": row[1],
                            "action": row[2],
                            "status": row[3],
                            "details": row[4],
                            "created_at": row[5],
                        }
                    )

                self._send_json({"activities": activities})
            except Exception as e:
                self.logger.error(f"Error getting integration activity: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    # Framework Feature Handlers - Compliance (SOC 2 Type 2 only)
    # GDPR and PCI DSS handlers commented out - not required for US-only operations

    # GDPR Handlers - COMMENTED OUT
    """
    def _handle_get_gdpr_consents(self, extension: str):
        \"\"\"Get GDPR consent records\"\"\"
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.compliance_framework import GDPRComplianceEngine
                engine = GDPRComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                consents = engine.get_consent_status(extension)
                self._send_json({'consents': consents})
            except Exception as e:
                self.logger.error(f"Error getting GDPR consents: {e}")
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Database not available'}, 500)

    def _handle_record_gdpr_consent(self):
        \"\"\"Record GDPR consent\"\"\"
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.compliance_framework import GDPRComplianceEngine
                engine = GDPRComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                if engine.record_consent(body):
                    self._send_json({'success': True})
                else:
                    self._send_json({'error': 'Failed to record consent'}, 500)
            except Exception as e:
                self.logger.error(f"Error recording GDPR consent: {e}")
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Database not available'}, 500)

    def _handle_withdraw_gdpr_consent(self):
        \"\"\"Withdraw GDPR consent\"\"\"
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.compliance_framework import GDPRComplianceEngine
                engine = GDPRComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                if engine.withdraw_consent(body.get('extension'), body.get('consent_type')):
                    self._send_json({'success': True})
                else:
                    self._send_json({'error': 'Failed to withdraw consent'}, 500)
            except Exception as e:
                self.logger.error(f"Error withdrawing GDPR consent: {e}")
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Database not available'}, 500)

    def _handle_create_gdpr_request(self):
        \"\"\"Create GDPR data request\"\"\"
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.compliance_framework import GDPRComplianceEngine
                engine = GDPRComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                request_id = engine.create_data_request(body)
                if request_id:
                    self._send_json({'request_id': request_id, 'success': True})
                else:
                    self._send_json({'error': 'Failed to create request'}, 500)
            except Exception as e:
                self.logger.error(f"Error creating GDPR request: {e}")
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Database not available'}, 500)

    def _handle_get_gdpr_requests(self):
        \"\"\"Get pending GDPR data requests\"\"\"
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.compliance_framework import GDPRComplianceEngine
                engine = GDPRComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                requests = engine.get_pending_requests()
                self._send_json({'requests': requests})
            except Exception as e:
                self.logger.error(f"Error getting GDPR requests: {e}")
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Database not available'}, 500)
    """

    def _handle_get_soc2_controls(self):
        """Get SOC 2 Type 2 controls"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.compliance_framework import SOC2ComplianceEngine

                engine = SOC2ComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                controls = engine.get_all_controls()
                self._send_json({"controls": controls})
            except Exception as e:
                self.logger.error(f"Error getting SOC2 controls: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    def _handle_register_soc2_control(self):
        """Register SOC 2 Type 2 control"""
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.compliance_framework import SOC2ComplianceEngine

                engine = SOC2ComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                if engine.register_control(body):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "Failed to register control"}, 500)
            except Exception as e:
                self.logger.error(f"Error registering SOC2 control: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Database not available"}, 500)

    # PCI DSS Handlers - COMMENTED OUT
    """
    def _handle_get_pci_audit_log(self):
        \"\"\"Get PCI DSS audit log\"\"\"
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                from pbx.features.compliance_framework import PCIDSSComplianceEngine
                engine = PCIDSSComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                logs = engine.get_audit_log()
                self._send_json({'logs': logs})
            except Exception as e:
                self.logger.error(f"Error getting PCI audit log: {e}")
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Database not available'}, 500)

    def _handle_log_pci_event(self):
        \"\"\"Log PCI DSS event\"\"\"
        if self.pbx_core and self.pbx_core.database.enabled:
            try:
                body = self._get_body()
                from pbx.features.compliance_framework import PCIDSSComplianceEngine
                engine = PCIDSSComplianceEngine(self.pbx_core.database, self.pbx_core.config)
                if engine.log_audit_event(body):
                    self._send_json({'success': True})
                else:
                    self._send_json({'error': 'Failed to log event'}, 500)
            except Exception as e:
                self.logger.error(f"Error logging PCI event: {e}")
                self._send_json({'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Database not available'}, 500)
    """

    # Open-source integration handlers
    def _handle_jitsi_create_meeting(self):
        """POST /api/integrations/jitsi/meetings - Create Jitsi meeting"""
        available, error = self._check_integration_available("jitsi")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("POST /api/integrations/jitsi/meetings")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in Jitsi create meeting: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_jitsi_instant_meeting(self):
        """POST /api/integrations/jitsi/instant - Create instant meeting"""
        available, error = self._check_integration_available("jitsi")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("POST /api/integrations/jitsi/instant")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in Jitsi instant meeting: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_espocrm_search_contact(self):
        """GET /api/integrations/espocrm/contacts/search - Search contact by phone"""
        available, error = self._check_integration_available("espocrm")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("GET /api/integrations/espocrm/contacts/search")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in EspoCRM search contact: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_espocrm_create_contact(self):
        """POST /api/integrations/espocrm/contacts - Create contact"""
        available, error = self._check_integration_available("espocrm")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("POST /api/integrations/espocrm/contacts")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in EspoCRM create contact: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_espocrm_log_call(self):
        """POST /api/integrations/espocrm/calls - Log call"""
        available, error = self._check_integration_available("espocrm")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("POST /api/integrations/espocrm/calls")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in EspoCRM log call: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_matrix_send_message(self):
        """POST /api/integrations/matrix/messages - Send message to room"""
        available, error = self._check_integration_available("matrix")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("POST /api/integrations/matrix/messages")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in Matrix send message: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_matrix_send_notification(self):
        """POST /api/integrations/matrix/notifications - Send notification"""
        available, error = self._check_integration_available("matrix")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("POST /api/integrations/matrix/notifications")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in Matrix send notification: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_matrix_create_room(self):
        """POST /api/integrations/matrix/rooms - Create room"""
        available, error = self._check_integration_available("matrix")
        if not available:
            self._send_json({"error": error}, 400)
            return

        try:
            endpoints = self._get_integration_endpoints()
            handler = endpoints.get("POST /api/integrations/matrix/rooms")
            if handler:
                handler(self)
            else:
                self._send_json({"error": "Handler not found"}, 500)
        except Exception as e:
            self.logger.error(f"Error in Matrix create room: {e}")
            self._send_json({"error": str(e)}, 500)

    # BI Integration Handlers
    def _handle_get_bi_datasets(self):
        """GET /api/framework/bi-integration/datasets - Get available datasets"""
        try:
            from pbx.features.bi_integration import get_bi_integration

            bi = get_bi_integration(self.pbx_core.config if self.pbx_core else None)
            datasets = bi.get_available_datasets()
            self._send_json({"datasets": datasets})
        except Exception as e:
            self.logger.error(f"Error getting BI datasets: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_bi_statistics(self):
        """GET /api/framework/bi-integration/statistics - Get BI statistics"""
        try:
            from pbx.features.bi_integration import get_bi_integration

            bi = get_bi_integration(self.pbx_core.config if self.pbx_core else None)
            stats = bi.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting BI statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_bi_export_status(self, dataset_name: str):
        """GET /api/framework/bi-integration/export/{dataset} - Get export status"""
        try:
            from pbx.features.bi_integration import get_bi_integration

            bi = get_bi_integration(self.pbx_core.config if self.pbx_core else None)
            datasets = bi.get_available_datasets()
            dataset = next((d for d in datasets if d["name"] == dataset_name), None)
            if dataset:
                self._send_json(dataset)
            else:
                self._send_json({"error": "Dataset not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting export status: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_export_bi_dataset(self):
        """POST /api/framework/bi-integration/export - Export dataset"""
        try:
            body = self._get_body()
            dataset_name = body.get("dataset")
            export_format = body.get("format", "csv")

            if not dataset_name:
                self._send_json({"error": "Dataset name required"}, 400)
                return

            from pbx.features.bi_integration import ExportFormat, get_bi_integration

            bi = get_bi_integration(self.pbx_core.config if self.pbx_core else None)

            # Convert format string to enum
            format_enum = ExportFormat.CSV
            if export_format.lower() == "json":
                format_enum = ExportFormat.JSON
            elif export_format.lower() == "excel":
                format_enum = ExportFormat.EXCEL

            result = bi.export_dataset(dataset_name, format_enum)
            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error exporting dataset: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_create_bi_dataset(self):
        """POST /api/framework/bi-integration/dataset - Create custom dataset"""
        try:
            body = self._get_body()
            name = body.get("name")
            query = body.get("query")

            if not name or not query:
                self._send_json({"error": "Name and query required"}, 400)
                return

            from pbx.features.bi_integration import get_bi_integration

            bi = get_bi_integration(self.pbx_core.config if self.pbx_core else None)
            bi.create_custom_dataset(name, query)
            self._send_json({"success": True, "dataset": name})
        except Exception as e:
            self.logger.error(f"Error creating dataset: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_test_bi_connection(self):
        """POST /api/framework/bi-integration/test-connection - Test BI provider connection"""
        try:
            body = self._get_body()
            provider = body.get("provider", "tableau")
            credentials = body.get("credentials", {})

            from pbx.features.bi_integration import BIProvider, get_bi_integration

            bi = get_bi_integration(self.pbx_core.config if self.pbx_core else None)

            # Convert provider string to enum
            provider_enum = BIProvider.TABLEAU
            if provider.lower() == "powerbi":
                provider_enum = BIProvider.POWER_BI
            elif provider.lower() == "looker":
                provider_enum = BIProvider.LOOKER

            result = bi.test_connection(provider_enum, credentials)
            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error testing BI connection: {e}")
            self._send_json({"error": str(e)}, 500)

    # Call Tagging Handlers
    def _handle_get_call_tags(self):
        """GET /api/framework/call-tagging/tags - Get all tags"""
        try:
            from pbx.features.call_tagging import get_call_tagging

            tagging = get_call_tagging(self.pbx_core.config if self.pbx_core else None)
            tags = tagging.get_all_tags()
            self._send_json({"tags": tags})
        except Exception as e:
            self.logger.error(f"Error getting call tags: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_tagging_rules(self):
        """GET /api/framework/call-tagging/rules - Get tagging rules"""
        try:
            from pbx.features.call_tagging import get_call_tagging

            tagging = get_call_tagging(self.pbx_core.config if self.pbx_core else None)
            rules = tagging.get_all_rules()
            self._send_json({"rules": rules})
        except Exception as e:
            self.logger.error(f"Error getting tagging rules: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_tagging_statistics(self):
        """GET /api/framework/call-tagging/statistics - Get tagging statistics"""
        try:
            from pbx.features.call_tagging import get_call_tagging

            tagging = get_call_tagging(self.pbx_core.config if self.pbx_core else None)
            stats = tagging.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting tagging statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_create_call_tag(self):
        """POST /api/framework/call-tagging/tag - Create new tag"""
        try:
            body = self._get_body()
            name = body.get("name")
            description = body.get("description", "")
            color = body.get("color", "#007bff")

            if not name:
                self._send_json({"error": "Tag name required"}, 400)
                return

            from pbx.features.call_tagging import get_call_tagging

            tagging = get_call_tagging(self.pbx_core.config if self.pbx_core else None)
            tag_id = tagging.create_tag(name, description, color)
            self._send_json({"success": True, "tag_id": tag_id})
        except Exception as e:
            self.logger.error(f"Error creating tag: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_create_tagging_rule(self):
        """POST /api/framework/call-tagging/rule - Create tagging rule"""
        try:
            body = self._get_body()
            name = body.get("name")
            conditions = body.get("conditions", [])
            tag_id = body.get("tag_id")

            if not name or not tag_id:
                self._send_json({"error": "Name and tag_id required"}, 400)
                return

            from pbx.features.call_tagging import get_call_tagging

            tagging = get_call_tagging(self.pbx_core.config if self.pbx_core else None)
            rule_id = tagging.create_rule(name, conditions, tag_id)
            self._send_json({"success": True, "rule_id": rule_id})
        except Exception as e:
            self.logger.error(f"Error creating tagging rule: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_classify_call(self, call_id: str):
        """POST /api/framework/call-tagging/classify/{call_id} - Classify call"""
        try:
            from pbx.features.call_tagging import get_call_tagging

            tagging = get_call_tagging(self.pbx_core.config if self.pbx_core else None)
            tags = tagging.classify_call(call_id)
            self._send_json({"call_id": call_id, "tags": tags})
        except Exception as e:
            self.logger.error(f"Error classifying call: {e}")
            self._send_json({"error": str(e)}, 500)

    # Call Blending Handlers
    def _handle_get_blending_agents(self):
        """GET /api/framework/call-blending/agents - Get all agents"""
        try:
            from pbx.features.call_blending import get_call_blending

            blending = get_call_blending(self.pbx_core.config if self.pbx_core else None)
            agents = blending.get_all_agents()
            self._send_json({"agents": agents})
        except Exception as e:
            self.logger.error(f"Error getting blending agents: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_blending_statistics(self):
        """GET /api/framework/call-blending/statistics - Get blending statistics"""
        try:
            from pbx.features.call_blending import get_call_blending

            blending = get_call_blending(self.pbx_core.config if self.pbx_core else None)
            stats = blending.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting blending statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_blending_agent_status(self, agent_id: str):
        """GET /api/framework/call-blending/agent/{agent_id} - Get agent status"""
        try:
            from pbx.features.call_blending import get_call_blending

            blending = get_call_blending(self.pbx_core.config if self.pbx_core else None)
            status = blending.get_agent_status(agent_id)
            if status:
                self._send_json(status)
            else:
                self._send_json({"error": "Agent not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting agent status: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_register_blending_agent(self):
        """POST /api/framework/call-blending/agent - Register agent"""
        try:
            body = self._get_body()
            agent_id = body.get("agent_id")
            extension = body.get("extension")

            if not agent_id or not extension:
                self._send_json({"error": "agent_id and extension required"}, 400)
                return

            from pbx.features.call_blending import get_call_blending

            blending = get_call_blending(self.pbx_core.config if self.pbx_core else None)
            result = blending.register_agent(agent_id, extension)
            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error registering agent: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_set_agent_mode(self, agent_id: str):
        """POST /api/framework/call-blending/agent/{agent_id}/mode - Set agent mode"""
        try:
            body = self._get_body()
            mode = body.get("mode", "blended")

            from pbx.features.call_blending import get_call_blending

            blending = get_call_blending(self.pbx_core.config if self.pbx_core else None)
            result = blending.set_agent_mode(agent_id, mode)
            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error setting agent mode: {e}")
            self._send_json({"error": str(e)}, 500)

    # Geographic Redundancy Handlers
    def _handle_get_geo_regions(self):
        """GET /api/framework/geo-redundancy/regions - Get all regions"""
        try:
            from pbx.features.geographic_redundancy import get_geographic_redundancy

            geo = get_geographic_redundancy(self.pbx_core.config if self.pbx_core else None)
            regions = geo.get_all_regions()
            self._send_json({"regions": regions})
        except Exception as e:
            self.logger.error(f"Error getting geo regions: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_geo_statistics(self):
        """GET /api/framework/geo-redundancy/statistics - Get geo statistics"""
        try:
            from pbx.features.geographic_redundancy import get_geographic_redundancy

            geo = get_geographic_redundancy(self.pbx_core.config if self.pbx_core else None)
            stats = geo.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting geo statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_geo_region_status(self, region_id: str):
        """GET /api/framework/geo-redundancy/region/{region_id} - Get region status"""
        try:
            from pbx.features.geographic_redundancy import get_geographic_redundancy

            geo = get_geographic_redundancy(self.pbx_core.config if self.pbx_core else None)
            status = geo.get_region_status(region_id)
            if status:
                self._send_json(status)
            else:
                self._send_json({"error": "Region not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting region status: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_create_geo_region(self):
        """POST /api/framework/geo-redundancy/region - Create region"""
        try:
            body = self._get_body()
            region_id = body.get("region_id")
            name = body.get("name")
            location = body.get("location")

            if not region_id or not name or not location:
                self._send_json({"error": "region_id, name, and location required"}, 400)
                return

            from pbx.features.geographic_redundancy import get_geographic_redundancy

            geo = get_geographic_redundancy(self.pbx_core.config if self.pbx_core else None)
            result = geo.create_region(region_id, name, location)
            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error creating region: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_trigger_geo_failover(self, region_id: str):
        """POST /api/framework/geo-redundancy/region/{region_id}/failover - Trigger failover"""
        try:
            from pbx.features.geographic_redundancy import get_geographic_redundancy

            geo = get_geographic_redundancy(self.pbx_core.config if self.pbx_core else None)
            result = geo.trigger_failover(region_id)
            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error triggering failover: {e}")
            self._send_json({"error": str(e)}, 500)

    # Conversational AI Handlers
    def _handle_get_ai_config(self):
        """GET /api/framework/conversational-ai/config - Get AI configuration"""
        try:
            from pbx.features.conversational_ai import get_conversational_ai

            ai = get_conversational_ai(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            config = {
                "enabled": ai.enabled,
                "provider": ai.provider,
                "model": ai.model,
                "max_tokens": ai.max_tokens,
                "temperature": ai.temperature,
            }
            self._send_json(config)
        except Exception as e:
            self.logger.error(f"Error getting AI config: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_ai_statistics(self):
        """GET /api/framework/conversational-ai/statistics - Get AI statistics"""
        try:
            from pbx.features.conversational_ai import get_conversational_ai

            db_backend = getattr(self.pbx_core, "db", None) if self.pbx_core else None
            ai = get_conversational_ai(self.pbx_core.config if self.pbx_core else None, db_backend)
            stats = ai.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting AI statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_ai_conversations(self):
        """GET /api/framework/conversational-ai/conversations - Get active conversations"""
        try:
            from pbx.features.conversational_ai import get_conversational_ai

            ai = get_conversational_ai(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            conversations = [
                {
                    "call_id": conv.call_id,
                    "caller_id": conv.caller_id,
                    "started_at": conv.started_at.isoformat(),
                    "intent": conv.intent,
                    "message_count": len(conv.messages),
                }
                for conv in ai.active_conversations.values()
            ]
            self._send_json({"conversations": conversations})
        except Exception as e:
            self.logger.error(f"Error getting conversations: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_ai_conversation_history(self):
        """GET /api/framework/conversational-ai/history - Get conversation history from database"""
        try:
            from pbx.features.conversational_ai import get_conversational_ai

            db_backend = getattr(self.pbx_core, "db", None) if self.pbx_core else None
            ai = get_conversational_ai(self.pbx_core.config if self.pbx_core else None, db_backend)

            # Get limit from query parameters
            query_params = parse_qs(urlparse(self.path).query)
            limit = int(query_params.get("limit", [100])[0])

            history = ai.get_conversation_history(limit)
            self._send_json({"history": history})
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_start_ai_conversation(self):
        """POST /api/framework/conversational-ai/conversation - Start conversation"""
        try:
            body = self._get_body()
            call_id = body.get("call_id")
            caller_id = body.get("caller_id")

            if not call_id or not caller_id:
                self._send_json({"error": "call_id and caller_id required"}, 400)
                return

            from pbx.features.conversational_ai import get_conversational_ai

            ai = get_conversational_ai(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            context = ai.start_conversation(call_id, caller_id)

            self._send_json(
                {
                    "success": True,
                    "call_id": context.call_id,
                    "started_at": context.started_at.isoformat(),
                }
            )
        except Exception as e:
            self.logger.error(f"Error starting conversation: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_process_ai_input(self):
        """POST /api/framework/conversational-ai/process - Process user input"""
        try:
            body = self._get_body()
            call_id = body.get("call_id")
            user_input = body.get("input")

            if not call_id or not user_input:
                self._send_json({"error": "call_id and input required"}, 400)
                return

            from pbx.features.conversational_ai import get_conversational_ai

            ai = get_conversational_ai(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            result = ai.process_user_input(call_id, user_input)

            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error processing input: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_configure_ai_provider(self):
        """POST /api/framework/conversational-ai/config - Configure AI provider"""
        try:
            body = self._get_body()
            provider = body.get("provider")
            api_key = body.get("api_key")

            if not provider or not api_key:
                self._send_json({"error": "provider and api_key required"}, 400)
                return

            from pbx.features.conversational_ai import get_conversational_ai

            ai = get_conversational_ai(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            ai.configure_provider(provider, api_key, **body.get("options", {}))

            self._send_json({"success": True, "provider": provider})
        except Exception as e:
            self.logger.error(f"Error configuring provider: {e}")
            self._send_json({"error": str(e)}, 500)

    # Predictive Dialing Handlers
    def _handle_get_dialing_campaigns(self):
        """GET /api/framework/predictive-dialing/campaigns - Get all campaigns"""
        try:
            from pbx.features.predictive_dialing import get_predictive_dialer

            dialer = get_predictive_dialer(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            campaigns = [
                {
                    "campaign_id": c.campaign_id,
                    "name": c.name,
                    "status": c.status.value,
                    "dialing_mode": c.dialing_mode.value,
                    "total_contacts": c.total_contacts,
                    "contacts_completed": c.contacts_completed,
                    "successful_calls": c.successful_calls,
                }
                for c in dialer.campaigns.values()
            ]
            self._send_json({"campaigns": campaigns})
        except Exception as e:
            self.logger.error(f"Error getting campaigns: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_dialing_statistics(self):
        """GET /api/framework/predictive-dialing/statistics - Get dialing statistics"""
        try:
            from pbx.features.predictive_dialing import get_predictive_dialer

            dialer = get_predictive_dialer(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            stats = dialer.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting dialing statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_campaign_details(self, campaign_id: str):
        """GET /api/framework/predictive-dialing/campaign/{id} - Get campaign details"""
        try:
            from pbx.features.predictive_dialing import get_predictive_dialer

            dialer = get_predictive_dialer(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            stats = dialer.get_campaign_statistics(campaign_id)
            if stats:
                self._send_json(stats)
            else:
                self._send_json({"error": "Campaign not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting campaign details: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_create_dialing_campaign(self):
        """POST /api/framework/predictive-dialing/campaign - Create campaign"""
        try:
            body = self._get_body()
            campaign_id = body.get("campaign_id")
            name = body.get("name")
            dialing_mode = body.get("dialing_mode", "progressive")

            if not campaign_id or not name:
                self._send_json({"error": "campaign_id and name required"}, 400)
                return

            from pbx.features.predictive_dialing import DialingMode, get_predictive_dialer

            dialer = get_predictive_dialer(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )

            # Convert mode string to enum
            mode_enum = DialingMode.PROGRESSIVE
            if dialing_mode.lower() == "preview":
                mode_enum = DialingMode.PREVIEW
            elif dialing_mode.lower() == "predictive":
                mode_enum = DialingMode.PREDICTIVE
            elif dialing_mode.lower() == "power":
                mode_enum = DialingMode.POWER

            campaign = dialer.create_campaign(
                campaign_id,
                name,
                mode_enum,
                max_attempts=body.get("max_attempts", 3),
                retry_interval=body.get("retry_interval", 3600),
            )

            self._send_json(
                {"success": True, "campaign_id": campaign.campaign_id, "name": campaign.name}
            )
        except Exception as e:
            self.logger.error(f"Error creating campaign: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_start_dialing_campaign(self, campaign_id: str):
        """POST /api/framework/predictive-dialing/campaign/{id}/start - Start campaign"""
        try:
            from pbx.features.predictive_dialing import get_predictive_dialer

            dialer = get_predictive_dialer(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            dialer.start_campaign(campaign_id)
            self._send_json({"success": True, "status": "running"})
        except Exception as e:
            self.logger.error(f"Error starting campaign: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_pause_dialing_campaign(self, campaign_id: str):
        """POST /api/framework/predictive-dialing/campaign/{id}/pause - Pause campaign"""
        try:
            from pbx.features.predictive_dialing import get_predictive_dialer

            dialer = get_predictive_dialer(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            dialer.pause_campaign(campaign_id)
            self._send_json({"success": True, "status": "paused"})
        except Exception as e:
            self.logger.error(f"Error pausing campaign: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_add_campaign_contacts(self):
        """POST /api/framework/predictive-dialing/contacts - Add contacts to campaign"""
        try:
            body = self._get_body()
            campaign_id = body.get("campaign_id")
            contacts = body.get("contacts", [])

            if not campaign_id or not contacts:
                self._send_json({"error": "campaign_id and contacts required"}, 400)
                return

            from pbx.features.predictive_dialing import get_predictive_dialer

            dialer = get_predictive_dialer(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            count = dialer.add_contacts(campaign_id, contacts)

            self._send_json({"success": True, "contacts_added": count})
        except Exception as e:
            self.logger.error(f"Error adding contacts: {e}")
            self._send_json({"error": str(e)}, 500)

    # Voice Biometrics Handlers
    def _handle_get_voice_profiles(self):
        """GET /api/framework/voice-biometrics/profiles - Get all voice profiles"""
        try:
            from pbx.features.voice_biometrics import get_voice_biometrics

            vb = get_voice_biometrics(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            profiles = [
                {
                    "user_id": p.user_id,
                    "extension": p.extension,
                    "status": p.status,
                    "enrollment_completed": p.enrollment_completed,
                    "created_at": p.created_at.isoformat(),
                    "verification_count": p.verification_count,
                    "fraud_attempts": p.fraud_attempts,
                }
                for p in vb.profiles.values()
            ]
            self._send_json({"profiles": profiles})
        except Exception as e:
            self.logger.error(f"Error getting voice profiles: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_voice_statistics(self):
        """GET /api/framework/voice-biometrics/statistics - Get biometrics statistics"""
        try:
            from pbx.features.voice_biometrics import get_voice_biometrics

            vb = get_voice_biometrics(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            stats = vb.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting voice statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_voice_profile(self, user_id: str):
        """GET /api/framework/voice-biometrics/profile/{user_id} - Get voice profile"""
        try:
            from pbx.features.voice_biometrics import get_voice_biometrics

            vb = get_voice_biometrics(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            profile = vb.get_profile(user_id)
            if profile:
                self._send_json(
                    {
                        "user_id": profile.user_id,
                        "extension": profile.extension,
                        "status": profile.status,
                        "enrollment_completed": profile.enrollment_completed,
                        "created_at": profile.created_at.isoformat(),
                        "verification_count": profile.verification_count,
                        "fraud_attempts": profile.fraud_attempts,
                    }
                )
            else:
                self._send_json({"error": "Profile not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting voice profile: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_create_voice_profile(self):
        """POST /api/framework/voice-biometrics/profile - Create voice profile"""
        try:
            body = self._get_body()
            user_id = body.get("user_id")
            extension = body.get("extension")

            if not user_id or not extension:
                self._send_json({"error": "user_id and extension required"}, 400)
                return

            from pbx.features.voice_biometrics import get_voice_biometrics

            vb = get_voice_biometrics(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            profile = vb.create_profile(user_id, extension)

            self._send_json(
                {
                    "success": True,
                    "user_id": profile.user_id,
                    "extension": profile.extension,
                    "status": profile.status,
                }
            )
        except Exception as e:
            self.logger.error(f"Error creating voice profile: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_start_voice_enrollment(self):
        """POST /api/framework/voice-biometrics/enroll - Start enrollment"""
        try:
            body = self._get_body()
            user_id = body.get("user_id")

            if not user_id:
                self._send_json({"error": "user_id required"}, 400)
                return

            from pbx.features.voice_biometrics import get_voice_biometrics

            vb = get_voice_biometrics(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            result = vb.start_enrollment(user_id)

            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error starting enrollment: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_verify_speaker(self):
        """POST /api/framework/voice-biometrics/verify - Verify speaker"""
        try:
            body = self._get_body()
            user_id = body.get("user_id")
            # In a real implementation, audio_data would be base64 encoded string
            audio_data_str = body.get("audio_data", "")

            if not user_id:
                self._send_json({"error": "user_id required"}, 400)
                return

            # Convert base64 encoded audio data to bytes if provided
            if audio_data_str:
                try:
                    audio_data = base64.b64decode(audio_data_str)
                except (binascii.Error, ValueError) as e:
                    self._send_json({"error": f"Invalid base64 audio data: {str(e)}"}, 400)
                    return
            else:
                audio_data = b""
                audio_data = b""

            from pbx.features.voice_biometrics import get_voice_biometrics

            vb = get_voice_biometrics(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            result = vb.verify_speaker(user_id, audio_data)

            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error verifying speaker: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_voice_profile(self, user_id: str):
        """DELETE /api/framework/voice-biometrics/profile/{user_id} - Delete profile"""
        try:
            from pbx.features.voice_biometrics import get_voice_biometrics

            vb = get_voice_biometrics(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            success = vb.delete_profile(user_id)
            if success:
                self._send_json({"success": True})
            else:
                self._send_json({"error": "Profile not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error deleting voice profile: {e}")
            self._send_json({"error": str(e)}, 500)

    # Call Quality Prediction Handlers
    def _handle_get_quality_predictions(self):
        """GET /api/framework/call-quality-prediction/predictions - Get all predictions"""
        try:
            from pbx.features.call_quality_prediction import get_quality_prediction

            qp = get_quality_prediction(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            predictions = {call_id: pred for call_id, pred in qp.predictions.items()}
            self._send_json({"predictions": predictions})
        except Exception as e:
            self.logger.error(f"Error getting quality predictions: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_quality_statistics(self):
        """GET /api/framework/call-quality-prediction/statistics - Get prediction statistics"""
        try:
            from pbx.features.call_quality_prediction import get_quality_prediction

            qp = get_quality_prediction(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            stats = qp.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting quality statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_quality_alerts(self):
        """GET /api/framework/call-quality-prediction/alerts - Get active quality alerts from database"""
        try:
            from pbx.features.call_quality_prediction import get_quality_prediction

            db_backend = getattr(self.pbx_core, "db", None) if self.pbx_core else None
            qp = get_quality_prediction(self.pbx_core.config if self.pbx_core else None, db_backend)

            if qp.db:
                alerts = qp.db.get_active_alerts()
                self._send_json({"alerts": alerts})
            else:
                self._send_json({"alerts": [], "message": "Database not configured"})
        except Exception as e:
            self.logger.error(f"Error getting quality alerts: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_call_prediction(self, call_id: str):
        """GET /api/framework/call-quality-prediction/prediction/{call_id} - Get call prediction"""
        try:
            from pbx.features.call_quality_prediction import get_quality_prediction

            qp = get_quality_prediction(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            prediction = qp.get_prediction(call_id)
            if prediction:
                self._send_json(prediction)
            else:
                self._send_json({"error": "Prediction not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting call prediction: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_collect_quality_metrics(self):
        """POST /api/framework/call-quality-prediction/metrics - Collect quality metrics"""
        try:
            body = self._get_body()
            call_id = body.get("call_id")

            if not call_id:
                self._send_json({"error": "call_id required"}, 400)
                return

            from pbx.features.call_quality_prediction import NetworkMetrics, get_quality_prediction

            qp = get_quality_prediction(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )

            # Create metrics object from request
            metrics = NetworkMetrics()
            metrics.packet_loss = body.get("packet_loss", 0.0)
            metrics.jitter = body.get("jitter", 0.0)
            metrics.latency = body.get("latency", 0.0)
            metrics.bandwidth = body.get("bandwidth", 0.0)

            qp.collect_metrics(call_id, metrics)

            self._send_json({"success": True, "call_id": call_id})
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_train_quality_model(self):
        """POST /api/framework/call-quality-prediction/train - Train prediction model"""
        try:
            body = self._get_body()
            historical_data = body.get("data", [])

            if not historical_data:
                self._send_json({"error": "historical data required"}, 400)
                return

            from pbx.features.call_quality_prediction import get_quality_prediction

            qp = get_quality_prediction(
                self.pbx_core.config if self.pbx_core else None,
                getattr(self.pbx_core, "db", None) if self.pbx_core else None,
            )
            qp.train_model(historical_data)

            self._send_json({"success": True, "samples_trained": len(historical_data)})
        except Exception as e:
            self.logger.error(f"Error training model: {e}")
            self._send_json({"error": str(e)}, 500)

    # Video Codec Handlers
    def _handle_get_video_codecs(self):
        """GET /api/framework/video-codec/codecs - Get supported video codecs"""
        try:
            from pbx.features.video_codec import get_video_codec_manager

            vc = get_video_codec_manager(self.pbx_core.config if self.pbx_core else None)
            codecs = vc.available_codecs
            self._send_json({"codecs": codecs})
        except Exception as e:
            self.logger.error(f"Error getting video codecs: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_video_statistics(self):
        """GET /api/framework/video-codec/statistics - Get video codec statistics"""
        try:
            from pbx.features.video_codec import get_video_codec_manager

            vc = get_video_codec_manager(self.pbx_core.config if self.pbx_core else None)
            stats = vc.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting video statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_calculate_video_bandwidth(self):
        """POST /api/framework/video-codec/bandwidth - Calculate required bandwidth"""
        try:
            body = self._get_body()
            resolution_input = body.get("resolution", [1920, 1080])
            framerate = body.get("framerate", 30)
            codec = body.get("codec", "h264")
            quality = body.get("quality", "high")

            # Validate resolution input
            if not isinstance(resolution_input, (list, tuple)) or len(resolution_input) != 2:
                self._send_json({"error": "resolution must be [width, height]"}, 400)
                return

            try:
                resolution = (int(resolution_input[0]), int(resolution_input[1]))
            except (ValueError, TypeError):
                self._send_json({"error": "resolution values must be numeric"}, 400)
                return

            from pbx.features.video_codec import get_video_codec_manager

            vc = get_video_codec_manager(self.pbx_core.config if self.pbx_core else None)
            bandwidth = vc.calculate_bandwidth(resolution, framerate, codec, quality)

            self._send_json(
                {
                    "resolution": list(resolution),
                    "framerate": framerate,
                    "codec": codec,
                    "quality": quality,
                    "bandwidth_mbps": bandwidth,
                }
            )
        except Exception as e:
            self.logger.error(f"Error calculating bandwidth: {e}")
            self._send_json({"error": str(e)}, 500)

    # Mobile Number Portability Handlers
    def _handle_get_mobile_mappings(self):
        """GET /api/framework/mobile-portability/mappings - Get all number mappings"""
        try:
            from pbx.features.mobile_number_portability import get_mobile_number_portability

            mnp = get_mobile_number_portability(self.pbx_core.config if self.pbx_core else None)
            mappings = [
                {"business_number": number, **details}
                for number, details in mnp.number_mappings.items()
            ]
            self._send_json({"mappings": mappings})
        except Exception as e:
            self.logger.error(f"Error getting mobile mappings: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_mobile_statistics(self):
        """GET /api/framework/mobile-portability/statistics - Get portability statistics"""
        try:
            from pbx.features.mobile_number_portability import get_mobile_number_portability

            mnp = get_mobile_number_portability(self.pbx_core.config if self.pbx_core else None)
            stats = mnp.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting mobile statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_mobile_mapping(self, business_number: str):
        """GET /api/framework/mobile-portability/mapping/{number} - Get specific mapping"""
        try:
            from pbx.features.mobile_number_portability import get_mobile_number_portability

            mnp = get_mobile_number_portability(self.pbx_core.config if self.pbx_core else None)
            mapping = mnp.get_mapping(business_number)
            if mapping:
                self._send_json(mapping)
            else:
                self._send_json({"error": "Mapping not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting mobile mapping: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_create_mobile_mapping(self):
        """POST /api/framework/mobile-portability/mapping - Create number mapping"""
        try:
            body = self._get_body()
            business_number = body.get("business_number")
            extension = body.get("extension")
            mobile_device = body.get("mobile_device")

            if not all([business_number, extension, mobile_device]):
                self._send_json(
                    {"error": "business_number, extension, and mobile_device required"}, 400
                )
                return

            from pbx.features.mobile_number_portability import get_mobile_number_portability

            mnp = get_mobile_number_portability(self.pbx_core.config if self.pbx_core else None)
            result = mnp.map_number_to_mobile(
                business_number, extension, mobile_device, body.get("forward_to_mobile", True)
            )

            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error creating mobile mapping: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_toggle_mobile_mapping(self, business_number: str):
        """POST /api/framework/mobile-portability/mapping/{number}/toggle - Toggle mapping"""
        try:
            body = self._get_body()
            active = body.get("active", True)

            from pbx.features.mobile_number_portability import get_mobile_number_portability

            mnp = get_mobile_number_portability(self.pbx_core.config if self.pbx_core else None)
            success = mnp.toggle_mapping(business_number, active)

            if success:
                self._send_json({"success": True, "active": active})
            else:
                self._send_json({"error": "Mapping not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error toggling mobile mapping: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_delete_mobile_mapping(self, business_number: str):
        """DELETE /api/framework/mobile-portability/mapping/{number} - Delete mapping"""
        try:
            from pbx.features.mobile_number_portability import get_mobile_number_portability

            mnp = get_mobile_number_portability(self.pbx_core.config if self.pbx_core else None)
            success = mnp.remove_mapping(business_number)

            if success:
                self._send_json({"success": True})
            else:
                self._send_json({"error": "Mapping not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error deleting mobile mapping: {e}")
            self._send_json({"error": str(e)}, 500)

    # Call Recording Analytics Handlers
    def _handle_get_recording_analyses(self):
        """GET /api/framework/recording-analytics/analyses - Get all analyses"""
        try:
            from pbx.features.call_recording_analytics import get_recording_analytics

            ra = get_recording_analytics(self.pbx_core.config if self.pbx_core else None)
            analyses = {rec_id: analysis for rec_id, analysis in ra.analyses.items()}
            self._send_json({"analyses": analyses})
        except Exception as e:
            self.logger.error(f"Error getting recording analyses: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_recording_statistics(self):
        """GET /api/framework/recording-analytics/statistics - Get analytics statistics"""
        try:
            from pbx.features.call_recording_analytics import get_recording_analytics

            ra = get_recording_analytics(self.pbx_core.config if self.pbx_core else None)
            stats = ra.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting recording statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_recording_analysis(self, recording_id: str):
        """GET /api/framework/recording-analytics/analysis/{id} - Get specific analysis"""
        try:
            from pbx.features.call_recording_analytics import get_recording_analytics

            ra = get_recording_analytics(self.pbx_core.config if self.pbx_core else None)
            analysis = ra.get_analysis(recording_id)
            if analysis:
                self._send_json(analysis)
            else:
                self._send_json({"error": "Analysis not found"}, 404)
        except Exception as e:
            self.logger.error(f"Error getting recording analysis: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_analyze_recording(self):
        """POST /api/framework/recording-analytics/analyze - Analyze recording"""
        try:
            body = self._get_body()
            recording_id = body.get("recording_id")
            audio_path = body.get("audio_path")

            if not recording_id or not audio_path:
                self._send_json({"error": "recording_id and audio_path required"}, 400)
                return

            from pbx.features.call_recording_analytics import get_recording_analytics

            ra = get_recording_analytics(self.pbx_core.config if self.pbx_core else None)
            result = ra.analyze_recording(
                recording_id, audio_path, metadata=body.get("metadata", {})
            )

            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error analyzing recording: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_search_recordings(self):
        """POST /api/framework/recording-analytics/search - Search recordings"""
        try:
            body = self._get_body()
            criteria = body.get("criteria", {})

            from pbx.features.call_recording_analytics import get_recording_analytics

            ra = get_recording_analytics(self.pbx_core.config if self.pbx_core else None)
            results = ra.search_recordings(criteria)

            self._send_json({"results": results})
        except Exception as e:
            self.logger.error(f"Error searching recordings: {e}")
            self._send_json({"error": str(e)}, 500)

    # Predictive Voicemail Drop Handlers
    def _handle_get_voicemail_messages(self):
        """GET /api/framework/voicemail-drop/messages - Get all drop messages"""
        try:
            from pbx.features.predictive_voicemail_drop import get_voicemail_drop

            vd = get_voicemail_drop(self.pbx_core.config if self.pbx_core else None)
            messages = vd.list_messages()
            self._send_json({"messages": messages})
        except Exception as e:
            self.logger.error(f"Error getting voicemail messages: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_voicemail_drop_statistics(self):
        """GET /api/framework/voicemail-drop/statistics - Get drop statistics"""
        try:
            from pbx.features.predictive_voicemail_drop import get_voicemail_drop

            vd = get_voicemail_drop(self.pbx_core.config if self.pbx_core else None)
            stats = vd.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting voicemail drop statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_add_voicemail_message(self):
        """POST /api/framework/voicemail-drop/message - Add drop message"""
        try:
            body = self._get_body()
            message_id = body.get("message_id")
            name = body.get("name")
            audio_path = body.get("audio_path")

            if not all([message_id, name, audio_path]):
                self._send_json({"error": "message_id, name, and audio_path required"}, 400)
                return

            from pbx.features.predictive_voicemail_drop import get_voicemail_drop

            vd = get_voicemail_drop(self.pbx_core.config if self.pbx_core else None)
            vd.add_message(message_id, name, audio_path, description=body.get("description"))

            self._send_json({"success": True, "message_id": message_id})
        except Exception as e:
            self.logger.error(f"Error adding voicemail message: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_drop_voicemail(self):
        """POST /api/framework/voicemail-drop/drop - Drop message to voicemail"""
        try:
            body = self._get_body()
            call_id = body.get("call_id")
            message_id = body.get("message_id")

            if not call_id or not message_id:
                self._send_json({"error": "call_id and message_id required"}, 400)
                return

            from pbx.features.predictive_voicemail_drop import get_voicemail_drop

            vd = get_voicemail_drop(self.pbx_core.config if self.pbx_core else None)
            result = vd.drop_message(call_id, message_id)

            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error dropping voicemail: {e}")
            self._send_json({"error": str(e)}, 500)

    # DNS SRV Failover Handlers
    def _handle_get_srv_records(self):
        """GET /api/framework/dns-srv/records - Get SRV records"""
        try:
            from pbx.features.dns_srv_failover import get_dns_srv_failover

            dns = get_dns_srv_failover(self.pbx_core.config if self.pbx_core else None)
            # Get all cached records
            records = {}
            for key, record_list in dns.cache.items():
                records[key] = [
                    {"priority": r.priority, "weight": r.weight, "port": r.port, "target": r.target}
                    for r in record_list
                ]
            self._send_json({"records": records})
        except Exception as e:
            self.logger.error(f"Error getting SRV records: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_dns_srv_statistics(self):
        """GET /api/framework/dns-srv/statistics - Get DNS SRV statistics"""
        try:
            from pbx.features.dns_srv_failover import get_dns_srv_failover

            dns = get_dns_srv_failover(self.pbx_core.config if self.pbx_core else None)
            stats = dns.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting DNS SRV statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_lookup_srv(self):
        """POST /api/framework/dns-srv/lookup - Lookup SRV records"""
        try:
            body = self._get_body()
            service = body.get("service")
            protocol = body.get("protocol", "tcp")
            domain = body.get("domain")

            if not service or not domain:
                self._send_json({"error": "service and domain required"}, 400)
                return

            from pbx.features.dns_srv_failover import get_dns_srv_failover

            dns = get_dns_srv_failover(self.pbx_core.config if self.pbx_core else None)
            records = dns.lookup_srv(service, protocol, domain)

            self._send_json({"records": records})
        except Exception as e:
            self.logger.error(f"Error looking up SRV: {e}")
            self._send_json({"error": str(e)}, 500)

    # Session Border Controller Handlers
    def _handle_get_sbc_statistics(self):
        """GET /api/framework/sbc/statistics - Get SBC statistics"""
        try:
            from pbx.features.session_border_controller import get_session_border_controller

            sbc = get_session_border_controller(self.pbx_core.config if self.pbx_core else None)
            stats = sbc.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting SBC statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_sbc_relays(self):
        """GET /api/framework/sbc/relays - Get active RTP relays"""
        try:
            from pbx.features.session_border_controller import get_session_border_controller

            sbc = get_session_border_controller(self.pbx_core.config if self.pbx_core else None)
            relays = {call_id: relay for call_id, relay in sbc.active_relays.items()}
            self._send_json({"relays": relays})
        except Exception as e:
            self.logger.error(f"Error getting SBC relays: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_allocate_sbc_relay(self):
        """POST /api/framework/sbc/relay - Allocate RTP relay"""
        try:
            body = self._get_body()
            call_id = body.get("call_id")
            codec = body.get("codec", "PCMU")

            if not call_id:
                self._send_json({"error": "call_id required"}, 400)
                return

            from pbx.features.session_border_controller import get_session_border_controller

            sbc = get_session_border_controller(self.pbx_core.config if self.pbx_core else None)
            result = sbc.allocate_relay(call_id, codec)

            self._send_json(result)
        except Exception as e:
            self.logger.error(f"Error allocating SBC relay: {e}")
            self._send_json({"error": str(e)}, 500)

    # Data Residency Controls Handlers
    def _handle_get_data_regions(self):
        """GET /api/framework/data-residency/regions - Get configured regions"""
        try:
            from pbx.features.data_residency_controls import get_data_residency

            dr = get_data_residency(self.pbx_core.config if self.pbx_core else None)
            regions = {region.value: config for region, config in dr.region_configs.items()}
            self._send_json({"regions": regions})
        except Exception as e:
            self.logger.error(f"Error getting data regions: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_data_residency_statistics(self):
        """GET /api/framework/data-residency/statistics - Get residency statistics"""
        try:
            from pbx.features.data_residency_controls import get_data_residency

            dr = get_data_residency(self.pbx_core.config if self.pbx_core else None)
            stats = dr.get_statistics()
            self._send_json(stats)
        except Exception as e:
            self.logger.error(f"Error getting data residency statistics: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_get_storage_location(self):
        """POST /api/framework/data-residency/location - Get storage location"""
        try:
            body = self._get_body()
            category = body.get("category")
            user_region = body.get("user_region")

            if not category:
                self._send_json({"error": "category required"}, 400)
                return

            from pbx.features.data_residency_controls import get_data_residency

            dr = get_data_residency(self.pbx_core.config if self.pbx_core else None)
            location = dr.get_storage_location(category, user_region)

            self._send_json(location)
        except Exception as e:
            self.logger.error(f"Error getting storage location: {e}")
            self._send_json({"error": str(e)}, 500)


class ReusableHTTPServer(HTTPServer):
    """HTTPServer that allows immediate socket reuse after restart"""

    allow_reuse_address = True

    def server_bind(self):
        """Bind the server with socket reuse options"""
        # Set SO_REUSEADDR (already done by allow_reuse_address, but explicit is better)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Set SO_REUSEPORT if available (helps with rapid restarts)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (OSError, AttributeError):
                # SO_REUSEPORT not supported on this platform, continue without it
                pass

        # Call parent bind
        super().server_bind()


def get_process_using_port(port):
    """
    Detect what process is using a specific port

    Args:
        port (int): Port number to check

    Returns:
        str: Description of the process using the port, or None if not found
    """
    try:
        # Try lsof first (most reliable)
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-n", "-P"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                # Parse the second line (first data line after header)
                parts = lines[1].split()
                if len(parts) >= 2:
                    process_name = parts[0]
                    pid = parts[1]
                    return f"{process_name} (PID: {pid})"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        # Fallback to netstat
        result = subprocess.run(["netstat", "-tulpn"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if f":{port}" in line and "LISTEN" in line:
                    # Try to extract process info
                    parts = line.split()
                    if len(parts) >= 7:
                        process_info = parts[6]
                        return process_info
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
        pass

    return None


class PBXAPIServer:
    """REST API server for PBX with HTTPS support"""

    def __init__(self, pbx_core, host="0.0.0.0", port=8080):
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
        self.server_thread = None
        self.logger = get_logger()
        self.running = False
        self.ssl_enabled = False
        self.ssl_context = None

        # Set PBX core for handler
        PBXAPIHandler.pbx_core = pbx_core

        # Configure SSL/TLS if enabled
        self._configure_ssl()

    def _configure_ssl(self):
        """Configure SSL context if SSL is enabled in config"""
        ssl_config = self.pbx_core.config.get("api.ssl", {})
        ssl_enabled = ssl_config.get("enabled", False)

        if not ssl_enabled:
            self.logger.info("SSL/HTTPS is disabled - using HTTP")
            return

        cert_file = ssl_config.get("cert_file")
        key_file = ssl_config.get("key_file")

        # Check for in-house CA auto-request
        ca_config = ssl_config.get("ca", {})
        ca_enabled = ca_config.get("enabled", False)

        if ca_enabled and (not cert_file or not os.path.exists(cert_file)):
            self.logger.info("Certificate not found, attempting to request from in-house CA")
            if self._request_certificate_from_ca(ca_config, cert_file, key_file):
                self.logger.info("Certificate successfully obtained from in-house CA")
            else:
                self.logger.error("Failed to obtain certificate from in-house CA")
                self.logger.error("Falling back to manual certificate configuration")

        if not cert_file or not key_file:
            self.logger.error("=" * 80)
            self.logger.error("SSL CONFIGURATION ERROR")
            self.logger.error("=" * 80)
            self.logger.error(
                "SSL is enabled in config.yml but cert_file or key_file is not configured"
            )
            self.logger.error("")
            self.logger.error("To fix this issue, choose one of the following options:")
            self.logger.error("")
            self.logger.error(
                "Option 1: Generate a self-signed certificate (for development/testing)"
            )
            self.logger.error("  Run: python scripts/generate_ssl_cert.py")
            self.logger.error("")
            self.logger.error("Option 2: Disable SSL temporarily")
            self.logger.error("  Edit config.yml and set: api.ssl.enabled: false")
            self.logger.error("")
            self.logger.error("Option 3: Enable auto-request from in-house CA")
            self.logger.error("  Edit config.yml and set: api.ssl.ca.enabled: true")
            self.logger.error("")
            self.logger.error("The server will continue to run on HTTP instead of HTTPS.")
            self.logger.error("=" * 80)
            return

        if not os.path.exists(cert_file):
            self.logger.error("=" * 80)
            self.logger.error("SSL CERTIFICATE NOT FOUND")
            self.logger.error("=" * 80)
            self.logger.error(f"SSL certificate file not found: {cert_file}")
            self.logger.error("")
            self.logger.error("To fix this issue, choose one of the following options:")
            self.logger.error("")
            self.logger.error(
                "Option 1: Generate a self-signed certificate (for development/testing)"
            )
            self.logger.error("  Run: python scripts/generate_ssl_cert.py")
            self.logger.error("")
            self.logger.error("Option 2: Request a certificate from your CA")
            self.logger.error("  Run: python scripts/request_ca_cert.py")
            self.logger.error("")
            self.logger.error("Option 3: Enable auto-request from in-house CA")
            self.logger.error("  Edit config.yml and set: api.ssl.ca.enabled: true")
            self.logger.error("")
            self.logger.error("Option 4: Disable SSL temporarily")
            self.logger.error("  Edit config.yml and set: api.ssl.enabled: false")
            self.logger.error("")
            self.logger.error("The server will continue to run on HTTP instead of HTTPS.")
            self.logger.error("=" * 80)
            return

        if not os.path.exists(key_file):
            self.logger.error("=" * 80)
            self.logger.error("SSL PRIVATE KEY NOT FOUND")
            self.logger.error("=" * 80)
            self.logger.error(f"SSL private key file not found: {key_file}")
            self.logger.error("")
            self.logger.error("The private key file is missing. This usually means:")
            self.logger.error("  - The certificate was not generated properly")
            self.logger.error("  - The file was deleted or moved")
            self.logger.error("  - The path in config.yml is incorrect")
            self.logger.error("")
            self.logger.error("To fix this issue:")
            self.logger.error(
                "  1. Regenerate the certificate: python scripts/generate_ssl_cert.py"
            )
            self.logger.error("  2. Or disable SSL: Edit config.yml and set api.ssl.enabled: false")
            self.logger.error("")
            self.logger.error("The server will continue to run on HTTP instead of HTTPS.")
            self.logger.error("=" * 80)
            return

        try:
            # Create SSL context
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(cert_file, key_file)

            # Load CA certificate if provided (for client certificate
            # validation)
            ca_cert = ca_config.get("ca_cert")
            if ca_cert and os.path.exists(ca_cert):
                self.ssl_context.load_verify_locations(cafile=ca_cert)
                self.logger.info(f"Loaded CA certificate: {ca_cert}")

            # Configure strong cipher suites
            self.ssl_context.set_ciphers("HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4")

            # Require TLS 1.2 or higher
            self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Additional security settings
            self.ssl_context.options |= ssl.OP_NO_SSLv2
            self.ssl_context.options |= ssl.OP_NO_SSLv3
            self.ssl_context.options |= ssl.OP_NO_TLSv1
            self.ssl_context.options |= ssl.OP_NO_TLSv1_1

            self.ssl_enabled = True
            self.logger.info(f"SSL/HTTPS enabled with certificate: {cert_file}")

        except Exception as e:
            self.logger.error("=" * 80)
            self.logger.error("SSL CONFIGURATION FAILED")
            self.logger.error("=" * 80)
            self.logger.error(f"Failed to configure SSL: {e}")
            self.logger.error("")
            self.logger.error("Common causes:")
            self.logger.error("  - Invalid certificate or key file format")
            self.logger.error("  - Mismatched certificate and key pair")
            self.logger.error("  - Insufficient file permissions")
            self.logger.error("  - Corrupted certificate files")
            self.logger.error("")
            self.logger.error("To fix this issue:")
            self.logger.error(
                "  1. Regenerate the certificate: python scripts/generate_ssl_cert.py"
            )
            self.logger.error("  2. Or disable SSL: Edit config.yml and set api.ssl.enabled: false")
            self.logger.error("")
            self.logger.error("The server will continue to run on HTTP instead of HTTPS.")
            self.logger.error("=" * 80)
            import traceback

            traceback.print_exc()

    def _request_certificate_from_ca(self, ca_config, cert_file, key_file):
        """
        Request certificate from in-house CA

        This generates a CSR (Certificate Signing Request) and submits it to
        the in-house CA for signing.

        Args:
            ca_config: CA configuration dictionary
            cert_file: Path where to save the certificate
            key_file: Path where to save the private key

        Returns:
            True if certificate was successfully obtained
        """
        try:
            import requests
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID

            ca_server = ca_config.get("server_url")
            ca_endpoint = ca_config.get("request_endpoint", "/api/sign-cert")

            if not ca_server:
                self.logger.error("CA server URL not configured")
                return False

            # Get server hostname/IP for certificate request
            hostname = self.pbx_core.config.get("server.external_ip", "localhost")

            self.logger.info(
                f"Requesting certificate for hostname: {hostname} from CA: {ca_server}"
            )

            # Create certificate directory if it doesn't exist
            cert_dir = os.path.dirname(cert_file) or "certs"
            os.makedirs(cert_dir, exist_ok=True)

            # Check if we already have a private key, otherwise generate one
            if os.path.exists(key_file):
                self.logger.info(f"Using existing private key: {key_file}")
                with open(key_file, "rb") as f:
                    private_key = serialization.load_pem_private_key(f.read(), password=None)
            else:
                self.logger.info("Generating new RSA private key (2048 bits)")
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                )

                # Save private key
                with open(key_file, "wb") as f:
                    f.write(
                        private_key.private_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=serialization.NoEncryption(),
                        )
                    )

                # Set restrictive permissions on private key
                os.chmod(key_file, 0o600)
                self.logger.info(f"Private key saved to: {key_file}")

            # Generate CSR (Certificate Signing Request)
            self.logger.info("Generating Certificate Signing Request (CSR)")
            csr = (
                x509.CertificateSigningRequestBuilder()
                .subject_name(
                    x509.Name(
                        [
                            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                            x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PBX System"),
                            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
                        ]
                    )
                )
                .add_extension(
                    x509.SubjectAlternativeName(
                        [
                            x509.DNSName(hostname),
                            x509.DNSName("localhost"),
                        ]
                    ),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # Convert CSR to PEM format
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

            # Submit CSR to CA
            self.logger.info(f"Submitting CSR to CA: {ca_server}{ca_endpoint}")

            # Verify CA certificate if provided
            ca_cert = ca_config.get("ca_cert")
            verify = ca_cert if ca_cert and os.path.exists(ca_cert) else True

            response = requests.post(
                f"{ca_server}{ca_endpoint}",
                json={
                    "csr": csr_pem,
                    "hostname": hostname,  # hostname serves as common_name in the CSR
                },
                timeout=30,
                verify=verify,
            )

            if response.status_code != 200:
                self.logger.error(
                    f"CA server returned error: {
                        response.status_code}"
                )
                self.logger.error(f"Response: {response.text}")
                return False

            # Parse response
            cert_data = response.json()
            signed_cert = cert_data.get("certificate")

            if not signed_cert:
                self.logger.error("CA did not return a signed certificate")
                return False

            # Save certificate
            with open(cert_file, "w") as f:
                f.write(signed_cert)

            self.logger.info(f"Certificate saved to: {cert_file}")

            # Save CA certificate if returned
            ca_cert_data = cert_data.get("ca_certificate")
            if ca_cert_data and not ca_config.get("ca_cert"):
                ca_cert_path = os.path.join(cert_dir, "ca.crt")
                with open(ca_cert_path, "w") as f:
                    f.write(ca_cert_data)
                self.logger.info(f"CA certificate saved to: {ca_cert_path}")

            return True

        except ImportError as e:
            self.logger.error(f"Required library not available: {e}")
            self.logger.error("Install with: pip install requests cryptography")
            return False
        except Exception as e:
            self.logger.error(f"Error requesting certificate from in-house CA: {e}")
            import traceback

            traceback.print_exc()
            return False

    def start(self):
        """Start API server with retry logic for address binding"""
        max_retries = 3
        retry_delay = 2  # Initial delay in seconds
        last_exception = None

        for attempt in range(max_retries):
            try:
                self.server = ReusableHTTPServer((self.host, self.port), PBXAPIHandler)

                # Wrap with SSL if enabled
                if self.ssl_enabled and self.ssl_context:
                    self.server.socket = self.ssl_context.wrap_socket(
                        self.server.socket, server_side=True
                    )

                # Set timeout on socket to allow periodic checking of running flag
                self.server.socket.settimeout(1.0)
                self.running = True

                protocol = "https" if self.ssl_enabled else "http"

                # Check if there's a mismatch between config and actual state
                ssl_config = self.pbx_core.config.get("api.ssl", {})
                config_ssl_enabled = ssl_config.get("enabled", False)

                if config_ssl_enabled and not self.ssl_enabled:
                    # SSL is enabled in config but not actually running
                    self.logger.warning("=" * 80)
                    self.logger.warning("SSL/HTTPS CONFIGURATION MISMATCH")
                    self.logger.warning("=" * 80)
                    self.logger.warning("config.yml has api.ssl.enabled: true")
                    self.logger.warning("However, SSL could not be configured (see errors above)")
                    self.logger.warning("")
                    self.logger.warning("SERVER IS RUNNING ON HTTP (not HTTPS)")
                    self.logger.warning("")
                    self.logger.warning("Access the admin panel at:")
                    self.logger.warning(f"  http://{self.host}:{self.port}/admin/")
                    self.logger.warning("")
                    self.logger.warning("To fix this:")
                    self.logger.warning(
                        "  1. Generate SSL certificate: python scripts/generate_ssl_cert.py"
                    )
                    self.logger.warning("  2. Then restart the server: sudo systemctl restart pbx")
                    self.logger.warning("  OR")
                    self.logger.warning(
                        "  3. Disable SSL in config.yml: set api.ssl.enabled: false"
                    )
                    self.logger.warning("=" * 80)
                else:
                    self.logger.info(f"API server started on {protocol}://{self.host}:{self.port}")
                    if self.ssl_enabled:
                        self.logger.info(
                            f"Admin panel accessible at: {protocol}://{self.host}:{self.port}/admin/"
                        )

                # Start in separate thread
                self.server_thread = threading.Thread(target=self._run)
                self.server_thread.daemon = True
                self.server_thread.start()

                return True

            except OSError as e:
                last_exception = e

                # Reset running flag to ensure consistent state
                self.running = False

                # Clean up any partially created server to avoid leaving socket in bad state
                if self.server:
                    try:
                        self.server.server_close()
                    except OSError as cleanup_err:
                        self.logger.debug(f"Error during cleanup: {cleanup_err}")
                    finally:
                        self.server = None

                # Clear thread reference as well since start failed
                self.server_thread = None

                # Check if this is an "Address already in use" error
                if e.errno == errno.EADDRINUSE:
                    # Try to detect what process is using the port
                    process_info = get_process_using_port(self.port)

                    if attempt < max_retries - 1:
                        # Not the last attempt - log and retry
                        self.logger.warning(
                            f"Port {self.port} is already in use (attempt {attempt + 1}/{max_retries})"
                        )
                        if process_info:
                            self.logger.warning(f"  Port is being used by: {process_info}")
                        self.logger.warning(f"  Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        # Last attempt failed - provide detailed error
                        self.logger.error("=" * 80)
                        self.logger.error("API SERVER PORT CONFLICT")
                        self.logger.error("=" * 80)
                        self.logger.error(
                            f"Failed to start API server: Port {self.port} is already in use"
                        )
                        self.logger.error("")

                        if process_info:
                            self.logger.error(f"Port {self.port} is currently being used by:")
                            self.logger.error(f"  {process_info}")
                            self.logger.error("")

                        self.logger.error("To resolve this issue:")
                        self.logger.error("  1. Stop the process using the port:")
                        self.logger.error(f"     sudo lsof -ti:{self.port} | xargs kill -9")
                        self.logger.error("     OR")
                        self.logger.error(f"     sudo fuser -k {self.port}/tcp")
                        self.logger.error("")
                        self.logger.error("  2. Change the API port in config.yml:")
                        self.logger.error("     api:")
                        self.logger.error("       port: <different_port>")
                        self.logger.error("")
                        self.logger.error("  3. Check if another PBX instance is running:")
                        self.logger.error("     ps aux | grep python.*main.py")
                        self.logger.error("=" * 80)

                        return False
                else:
                    # Different OSError - log and retry
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"Failed to bind to port {self.port}: {e} (attempt {attempt + 1}/{max_retries})"
                        )
                        self.logger.warning(f"  Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        self.logger.error(f"Failed to start API server: {e}")
                        traceback.print_exc()
                        return False

            except Exception as e:
                last_exception = e
                self.logger.error(f"Failed to start API server: {e}")
                traceback.print_exc()

                # Reset running flag to ensure consistent state
                self.running = False

                # Clean up any partially created server to avoid leaving socket in bad state
                if self.server:
                    try:
                        self.server.server_close()
                    except OSError as cleanup_err:
                        self.logger.debug(f"Error during cleanup: {cleanup_err}")
                    finally:
                        self.server = None

                # Clear thread reference as well since start failed
                self.server_thread = None

                # For non-OSError exceptions, don't retry
                return False

        # If we get here, all retries failed
        self.logger.error(f"Failed to start API server after {max_retries} attempts")
        if last_exception:
            self.logger.error(f"Last error: {last_exception}")
        return False

    def _run(self):
        """Run server"""
        while self.running:
            try:
                self.server.handle_request()
            except socket.timeout:
                # Timeout allows us to check running flag periodically
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error handling request: {e}")
        self.logger.info("API server thread stopped")

    def stop(self):
        """Stop API server"""
        self.running = False

        # Wait for server thread to finish with timeout
        if self.server_thread and self.server_thread.is_alive():
            # The thread should exit on its own when running=False
            # Wait up to 2 seconds for it to finish
            self.server_thread.join(timeout=2.0)
            if self.server_thread.is_alive():
                self.logger.warning("API server thread did not stop cleanly")

        # Clear thread reference regardless of whether it stopped cleanly
        self.server_thread = None

        if self.server:
            try:
                self.server.server_close()
            except OSError as e:
                self.logger.error(f"Error closing API server: {e}")
            finally:
                self.server = None

        self.logger.info("API server stopped")
