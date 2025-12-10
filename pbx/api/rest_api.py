"""
REST API Server for PBX Management
Provides HTTP/HTTPS API for managing PBX features
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime, date, timezone, timedelta
from typing import Optional
from pathlib import Path
import socket
import threading
import os
import mimetypes
import traceback
import zipfile
import tempfile
import shutil
import ssl
import ipaddress
from urllib.parse import urlparse, parse_qs
from pbx.utils.logger import get_logger
from pbx.utils.config import Config
from pbx.utils.tts import text_to_wav_telephony, is_tts_available, get_tts_requirements
from pbx.features.phone_provisioning import normalize_mac_address

# Optional imports for SSL certificate generation
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    SSL_GENERATION_AVAILABLE = True
except ImportError:
    SSL_GENERATION_AVAILABLE = False

# Admin directory path
ADMIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'admin')

# MAC address placeholders that indicate misconfiguration
# These are literal strings that appear in URLs when phones are misconfigured
# Note: $mac and $MA are CORRECT variables that phones should use - they should NOT be in this list
# Only include literal placeholders like {mac} that indicate the phone didn't substitute its actual MAC
MAC_ADDRESS_PLACEHOLDERS = ['{mac}', '{MAC}', '{Ma}']


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

    def _set_headers(self, status=200, content_type='application/json'):
        """Set response headers with security enhancements"""
        self.send_response(status)
        self.send_header('Content-type', content_type)
        
        # CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        
        # Security headers
        # X-Content-Type-Options: Prevent MIME type sniffing
        self.send_header('X-Content-Type-Options', 'nosniff')
        
        # X-Frame-Options: Prevent clickjacking
        self.send_header('X-Frame-Options', 'DENY')
        
        # X-XSS-Protection: Enable XSS filter (for older browsers)
        self.send_header('X-XSS-Protection', '1; mode=block')
        
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
        self.send_header('Content-Security-Policy', csp)
        
        # Referrer-Policy: Control referrer information
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        
        # Permissions-Policy: Control browser features
        self.send_header('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        
        self.end_headers()

    def _send_json(self, data, status=200):
        """Send JSON response"""
        self._set_headers(status)
        self.wfile.write(json.dumps(data, cls=DateTimeEncoder).encode())

    def _get_body(self):
        """Get request body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        return {}

    def do_OPTIONS(self):
        """Handle OPTIONS for CORS"""
        self._set_headers(204)

    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == '/api/provisioning/devices':
                self._handle_register_device()
            elif path.startswith('/api/provisioning/templates/') and path.endswith('/export'):
                # /api/provisioning/templates/{vendor}/{model}/export
                parts = path.split('/')
                if len(parts) >= 7:
                    vendor = parts[4]
                    model = parts[5]
                    # Validate vendor and model to prevent path traversal
                    import re
                    if re.match(r'^[a-z0-9_-]+$', vendor.lower()) and re.match(r'^[a-z0-9_-]+$', model.lower()):
                        self._handle_export_template(vendor, model)
                    else:
                        self._send_json({'error': 'Invalid vendor or model name'}, 400)
                else:
                    self._send_json({'error': 'Invalid path'}, 400)
            elif path == '/api/provisioning/reload-templates':
                self._handle_reload_templates()
            elif path.startswith('/api/provisioning/devices/') and '/static-ip' in path:
                # /api/provisioning/devices/{mac}/static-ip
                parts = path.split('/')
                if len(parts) >= 5:
                    mac = parts[4]
                    self._handle_set_static_ip(mac)
                else:
                    self._send_json({'error': 'Invalid path'}, 400)
            elif path == '/api/extensions':
                self._handle_add_extension()
            elif path == '/api/phones/reboot':
                self._handle_reboot_phones()
            elif path.startswith('/api/phones/') and path.endswith('/reboot'):
                # Extract extension number: /api/phones/{extension}/reboot
                parts = path.split('/')
                if len(parts) >= 4:
                    extension = parts[3]
                    self._handle_reboot_phone(extension)
                else:
                    self._send_json({'error': 'Invalid path'}, 400)
            elif path == '/api/integrations/ad/sync':
                self._handle_ad_sync()
            elif path == '/api/phone-book':
                self._handle_add_phone_book_entry()
            elif path == '/api/phone-book/sync':
                self._handle_sync_phone_book()
            elif path == '/api/paging/zones':
                self._handle_add_paging_zone()
            elif path == '/api/paging/devices':
                self._handle_configure_paging_device()
            elif path == '/api/webhooks':
                self._handle_add_webhook()
            elif path == '/api/webrtc/session':
                self._handle_create_webrtc_session()
            elif path == '/api/webrtc/offer':
                self._handle_webrtc_offer()
            elif path == '/api/webrtc/answer':
                self._handle_webrtc_answer()
            elif path == '/api/webrtc/ice-candidate':
                self._handle_webrtc_ice_candidate()
            elif path == '/api/webrtc/call':
                self._handle_webrtc_call()
            elif path == '/api/crm/screen-pop':
                self._handle_trigger_screen_pop()
            elif path == '/api/hot-desk/login':
                self._handle_hot_desk_login()
            elif path == '/api/hot-desk/logout':
                self._handle_hot_desk_logout()
            elif path == '/api/mfa/enroll':
                self._handle_mfa_enroll()
            elif path == '/api/mfa/verify-enrollment':
                self._handle_mfa_verify_enrollment()
            elif path == '/api/mfa/verify':
                self._handle_mfa_verify()
            elif path == '/api/mfa/disable':
                self._handle_mfa_disable()
            elif path == '/api/mfa/enroll-yubikey':
                self._handle_mfa_enroll_yubikey()
            elif path == '/api/mfa/enroll-fido2':
                self._handle_mfa_enroll_fido2()
            elif path == '/api/security/block-ip':
                self._handle_block_ip()
            elif path == '/api/security/unblock-ip':
                self._handle_unblock_ip()
            elif path == '/api/dnd/rule':
                self._handle_add_dnd_rule()
            elif path == '/api/dnd/register-calendar':
                self._handle_register_calendar_user()
            elif path == '/api/dnd/override':
                self._handle_dnd_override()
            elif path == '/api/skills/skill':
                self._handle_add_skill()
            elif path == '/api/skills/assign':
                self._handle_assign_skill()
            elif path == '/api/skills/queue-requirements':
                self._handle_set_queue_requirements()
            elif path == '/api/qos/clear-alerts':
                self._handle_clear_qos_alerts()
            elif path == '/api/qos/thresholds':
                self._handle_update_qos_thresholds()
            elif path == '/api/auto-attendant/menu-options':
                self._handle_add_auto_attendant_menu_option()
            elif path.startswith('/api/voicemail-boxes/') and path.endswith('/export'):
                self._handle_export_voicemail_box(path)
            elif path == '/api/ssl/generate-certificate':
                self._handle_generate_ssl_certificate()
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def do_PUT(self):
        """Handle PUT requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith('/api/provisioning/templates/'):
                # /api/provisioning/templates/{vendor}/{model}
                parts = path.split('/')
                if len(parts) >= 6:
                    vendor = parts[4]
                    model = parts[5]
                    # Validate vendor and model to prevent path traversal
                    import re
                    if re.match(r'^[a-z0-9_-]+$', vendor.lower()) and re.match(r'^[a-z0-9_-]+$', model.lower()):
                        self._handle_update_template(vendor, model)
                    else:
                        self._send_json({'error': 'Invalid vendor or model name'}, 400)
                else:
                    self._send_json({'error': 'Invalid path'}, 400)
            elif path.startswith('/api/extensions/'):
                # Extract extension number from path
                number = path.split('/')[-1]
                self._handle_update_extension(number)
            elif path == '/api/config':
                self._handle_update_config()
            elif path == '/api/config/section':
                self._handle_update_config_section()
            elif path.startswith('/api/voicemail/'):
                self._handle_update_voicemail(path)
            elif path == '/api/auto-attendant/config':
                self._handle_update_auto_attendant_config()
            elif path == '/api/auto-attendant/prompts':
                self._handle_update_auto_attendant_prompts()
            elif path.startswith('/api/auto-attendant/menu-options/'):
                self._handle_update_auto_attendant_menu_option(path)
            elif path.startswith('/api/voicemail-boxes/') and path.endswith('/greeting'):
                self._handle_upload_voicemail_greeting(path)
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith('/api/provisioning/devices/'):
                # Extract MAC address from path
                mac = path.split('/')[-1]
                self._handle_unregister_device(mac)
            elif path.startswith('/api/extensions/'):
                # Extract extension number from path
                number = path.split('/')[-1]
                self._handle_delete_extension(number)
            elif path.startswith('/api/voicemail/'):
                self._handle_delete_voicemail(path)
            elif path.startswith('/api/phone-book/'):
                # Extract extension from path
                extension = path.split('/')[-1]
                self._handle_delete_phone_book_entry(extension)
            elif path.startswith('/api/paging/zones/'):
                # Extract extension from path
                extension = path.split('/')[-1]
                self._handle_delete_paging_zone(extension)
            elif path.startswith('/api/dnd/rule/'):
                # Extract rule ID from path
                rule_id = path.split('/')[-1]
                self._handle_delete_dnd_rule(rule_id)
            elif path.startswith('/api/dnd/override/'):
                # Extract extension from path
                extension = path.split('/')[-1]
                self._handle_clear_dnd_override(extension)
            elif path.startswith('/api/skills/assign/'):
                # Extract agent_extension/skill_id from path
                parts = path.split('/')
                if len(parts) >= 5:
                    agent_extension = parts[-2]
                    skill_id = parts[-1]
                    self._handle_remove_skill_from_agent(agent_extension, skill_id)
                else:
                    self._send_json({'error': 'Invalid path'}, 400)
            elif path.startswith('/api/auto-attendant/menu-options/'):
                # Extract digit from path
                digit = path.split('/')[-1]
                self._handle_delete_auto_attendant_menu_option(digit)
            elif path.startswith('/api/voicemail-boxes/') and path.endswith('/clear'):
                self._handle_clear_voicemail_box(path)
            elif path.startswith('/api/voicemail-boxes/') and path.endswith('/greeting'):
                self._handle_delete_voicemail_greeting(path)
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        try:
            if path == '/api/status':
                self._handle_status()
            elif path == '/api/extensions':
                self._handle_get_extensions()
            elif path == '/api/calls':
                self._handle_get_calls()
            elif path == '/api/statistics':
                self._handle_get_statistics()
            elif path == '/api/qos/metrics':
                self._handle_get_qos_metrics()
            elif path == '/api/qos/alerts':
                self._handle_get_qos_alerts()
            elif path == '/api/qos/history':
                self._handle_get_qos_history()
            elif path == '/api/qos/statistics':
                self._handle_get_qos_statistics()
            elif path.startswith('/api/qos/call/'):
                self._handle_get_qos_call_metrics(path)
            elif path == '/api/config':
                self._handle_get_config()
            elif path == '/api/config/full':
                self._handle_get_full_config()
            elif path == '/api/ssl/status':
                self._handle_get_ssl_status()
            elif path == '/api/provisioning/devices':
                self._handle_get_provisioning_devices()
            elif path == '/api/provisioning/vendors':
                self._handle_get_provisioning_vendors()
            elif path == '/api/provisioning/templates':
                self._handle_get_provisioning_templates()
            elif path.startswith('/api/provisioning/templates/'):
                # /api/provisioning/templates/{vendor}/{model}
                parts = path.split('/')
                if len(parts) >= 6:
                    vendor = parts[4]
                    model = parts[5]
                    # Validate vendor and model to prevent path traversal
                    import re
                    if re.match(r'^[a-z0-9_-]+$', vendor.lower()) and re.match(r'^[a-z0-9_-]+$', model.lower()):
                        self._handle_get_template_content(vendor, model)
                    else:
                        self._send_json({'error': 'Invalid vendor or model name'}, 400)
                else:
                    self._send_json({'error': 'Invalid path'}, 400)
            elif path == '/api/provisioning/diagnostics':
                self._handle_get_provisioning_diagnostics()
            elif path == '/api/provisioning/requests':
                self._handle_get_provisioning_requests()
            elif path == '/api/registered-phones':
                self._handle_get_registered_phones()
            elif path == '/api/registered-phones/with-mac':
                self._handle_get_registered_phones_with_mac()
            elif path.startswith('/api/registered-phones/extension/'):
                # Extract extension: /api/registered-phones/extension/{number}
                extension = path.split('/')[-1]
                self._handle_get_registered_phones_by_extension(extension)
            elif path.startswith('/api/phone-lookup/'):
                # Extract identifier: /api/phone-lookup/{mac_or_ip}
                identifier = path.split('/')[-1]
                self._handle_phone_lookup(identifier)
            elif path == '/api/integrations/ad/status':
                self._handle_ad_status()
            elif path.startswith('/api/integrations/ad/search'):
                self._handle_ad_search()
            elif path == '/api/phone-book':
                self._handle_get_phone_book()
            elif path == '/api/phone-book/export/xml':
                self._handle_export_phone_book_xml()
            elif path == '/api/phone-book/export/cisco-xml':
                self._handle_export_phone_book_cisco_xml()
            elif path == '/api/phone-book/export/json':
                self._handle_export_phone_book_json()
            elif path.startswith('/api/phone-book/search'):
                self._handle_search_phone_book()
            elif path == '/api/paging/zones':
                self._handle_get_paging_zones()
            elif path == '/api/paging/devices':
                self._handle_get_paging_devices()
            elif path == '/api/paging/active':
                self._handle_get_active_pages()
            elif path == '/api/webhooks':
                self._handle_get_webhooks()
            elif path == '/api/webrtc/sessions':
                self._handle_get_webrtc_sessions()
            elif path == '/api/webrtc/ice-servers':
                self._handle_get_ice_servers()
            elif path.startswith('/api/webrtc/session/'):
                self._handle_get_webrtc_session(path)
            elif path.startswith('/api/crm/lookup'):
                self._handle_crm_lookup()
            elif path == '/api/crm/providers':
                self._handle_get_crm_providers()
            elif path == '/api/hot-desk/sessions':
                self._handle_get_hot_desk_sessions()
            elif path.startswith('/api/hot-desk/session/'):
                self._handle_get_hot_desk_session(path)
            elif path.startswith('/api/hot-desk/extension/'):
                self._handle_get_hot_desk_extension(path)
            elif path.startswith('/api/mfa/status/'):
                self._handle_get_mfa_status(path)
            elif path.startswith('/api/mfa/methods/'):
                self._handle_get_mfa_methods(path)
            elif path == '/api/security/threat-summary':
                self._handle_get_threat_summary()
            elif path.startswith('/api/security/check-ip/'):
                self._handle_check_ip(path)
            elif path.startswith('/api/dnd/status/'):
                self._handle_get_dnd_status(path)
            elif path.startswith('/api/dnd/rules/'):
                self._handle_get_dnd_rules(path)
            elif path == '/api/skills/all':
                self._handle_get_all_skills()
            elif path.startswith('/api/skills/agent/'):
                self._handle_get_agent_skills(path)
            elif path.startswith('/api/skills/queue/'):
                self._handle_get_queue_requirements(path)
            elif path.startswith('/api/voicemail/'):
                self._handle_get_voicemail(path)
            elif path == '/api/auto-attendant/config':
                self._handle_get_auto_attendant_config()
            elif path == '/api/auto-attendant/menu-options':
                self._handle_get_auto_attendant_menu_options()
            elif path == '/api/auto-attendant/prompts':
                self._handle_get_auto_attendant_prompts()
            elif path == '/api/voicemail-boxes':
                self._handle_get_voicemail_boxes()
            elif path.startswith('/api/voicemail-boxes/') and path.endswith('/greeting'):
                self._handle_get_voicemail_greeting(path)
            elif path.startswith('/api/voicemail-boxes/'):
                self._handle_get_voicemail_box_details(path)
            elif path.startswith('/provision/') and path.endswith('.cfg'):
                self._handle_provisioning_request(path)
            elif path == '' or path == '/admin':
                self._handle_admin_redirect()
            elif path.startswith('/admin/'):
                self._handle_static_file(path)
            else:
                self._send_json({'error': 'Not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_root(self):
        """Handle root path"""
        self._set_headers(content_type='text/html')
        html = """
        <html>
        <head><title>InHouse PBX API</title></head>
        <body>
            <h1>InHouse PBX System API</h1>
            <h2>Available Endpoints:</h2>
            <ul>
                <li>GET /api/status - System status</li>
                <li>GET /api/extensions - List extensions</li>
                <li>GET /api/calls - List active calls</li>
                <li>GET /api/statistics?days=7 - Get dashboard statistics and analytics</li>
                <li>GET /api/provisioning/devices - List provisioned devices</li>
                <li>GET /api/provisioning/vendors - List supported vendors</li>
                <li>POST /api/provisioning/devices - Register a device</li>
                <li>DELETE /api/provisioning/devices/{mac} - Unregister a device</li>
                <li>GET /provision/{mac}.cfg - Get device configuration</li>
                <li>GET /api/provisioning/templates - List all provisioning templates</li>
                <li>GET /api/provisioning/templates/{vendor}/{model} - Get template content</li>
                <li>POST /api/provisioning/templates/{vendor}/{model}/export - Export template to file</li>
                <li>PUT /api/provisioning/templates/{vendor}/{model} - Update template content</li>
                <li>POST /api/provisioning/reload-templates - Reload all templates from disk</li>
                <li>GET /api/registered-phones - List all registered phones (MAC/IP tracking)</li>
                <li>GET /api/registered-phones/with-mac - List registered phones with MAC addresses from provisioning</li>
                <li>GET /api/registered-phones/extension/{number} - List registered phones for extension</li>
                <li>GET /api/phone-lookup/{mac_or_ip} - Unified lookup by MAC or IP address with correlation</li>
                <li>GET /api/integrations/ad/search?q={query}&max_results={max} - Search Active Directory users by name, email, or telephoneNumber</li>
                <li>GET /api/integrations/ad/status - Get Active Directory integration status</li>
                <li>POST /api/integrations/ad/sync - Manually sync users from Active Directory</li>
            </ul>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _handle_status(self):
        """Get PBX status"""
        if self.pbx_core:
            status = self.pbx_core.get_status()
            self._send_json(status)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _handle_get_extensions(self):
        """Get extensions"""
        if self.pbx_core:
            extensions = self.pbx_core.extension_registry.get_all()
            data = [{'number': e.number, 'name': e.name, 'email': e.config.get('email'),
                    'registered': e.registered, 'allow_external': e.config.get('allow_external', True),
                    'ad_synced': e.config.get('ad_synced', False), 'voicemail_pin': e.config.get('voicemail_pin')}
                   for e in extensions]
            self._send_json(data)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _handle_get_calls(self):
        """Get active calls"""
        if self.pbx_core:
            calls = self.pbx_core.call_manager.get_active_calls()
            data = [str(call) for call in calls]
            self._send_json(data)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _validate_limit_parameter(self, params: dict, default: int, max_value: int) -> Optional[int]:
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
            limit = int(params.get('limit', [default])[0])
            if limit < 1:
                self._send_json({'error': 'limit must be at least 1'}, 400)
                return None
            if limit > max_value:
                self._send_json({'error': f'limit cannot exceed {max_value}'}, 400)
                return None
            return limit
        except ValueError:
            self._send_json({'error': 'Invalid limit parameter, must be an integer'}, 400)
            return None

    def _handle_get_statistics(self):
        """Get comprehensive statistics for dashboard"""
        if self.pbx_core and hasattr(self.pbx_core, 'statistics_engine'):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                days = int(params.get('days', [7])[0])
                
                # Get dashboard statistics
                stats = self.pbx_core.statistics_engine.get_dashboard_statistics(days)
                
                # Add call quality metrics
                stats['call_quality'] = self.pbx_core.statistics_engine.get_call_quality_metrics()
                
                # Add real-time metrics
                stats['real_time'] = self.pbx_core.statistics_engine.get_real_time_metrics(self.pbx_core)
                
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting statistics: {e}")
                self._send_json({'error': f'Error getting statistics: {str(e)}'}, 500)
        else:
            self._send_json({'error': 'Statistics engine not initialized'}, 500)

    def _handle_get_qos_metrics(self):
        """Get QoS metrics for all active calls"""
        if self.pbx_core and hasattr(self.pbx_core, 'qos_monitor'):
            try:
                metrics = self.pbx_core.qos_monitor.get_all_active_metrics()
                self._send_json({
                    'active_calls': len(metrics),
                    'metrics': metrics
                })
            except Exception as e:
                self.logger.error(f"Error getting QoS metrics: {e}")
                self._send_json({'error': f'Error getting QoS metrics: {str(e)}'}, 500)
        else:
            self._send_json({'error': 'QoS monitoring not enabled'}, 500)

    def _handle_get_qos_alerts(self):
        """Get QoS quality alerts"""
        if self.pbx_core and hasattr(self.pbx_core, 'qos_monitor'):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                
                # Validate limit parameter
                limit = int(params.get('limit', [50])[0])
                if limit < 1:
                    self._send_json({'error': 'limit must be at least 1'}, 400)
                    return
                if limit > 1000:
                    self._send_json({'error': 'limit cannot exceed 1000'}, 400)
                    return
                
                alerts = self.pbx_core.qos_monitor.get_alerts(limit)
                self._send_json({
                    'count': len(alerts),
                    'alerts': alerts
                })
            except ValueError as e:
                self.logger.error(f"Invalid parameter for QoS alerts: {e}")
                self._send_json({'error': 'Invalid limit parameter, must be an integer'}, 400)
            except Exception as e:
                self.logger.error(f"Error getting QoS alerts: {e}")
                self._send_json({'error': f'Error getting QoS alerts: {str(e)}'}, 500)
        else:
            self._send_json({'error': 'QoS monitoring not enabled'}, 500)

    def _handle_get_qos_history(self):
        """Get historical QoS metrics"""
        if self.pbx_core and hasattr(self.pbx_core, 'qos_monitor'):
            try:
                # Parse query parameters
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                
                # Validate limit parameter
                limit = int(params.get('limit', [100])[0])
                if limit < 1:
                    self._send_json({'error': 'limit must be at least 1'}, 400)
                    return
                if limit > 10000:
                    self._send_json({'error': 'limit cannot exceed 10000'}, 400)
                    return
                
                # Validate min_mos parameter
                min_mos = params.get('min_mos', [None])[0]
                if min_mos:
                    min_mos = float(min_mos)
                    if min_mos < 1.0 or min_mos > 5.0:
                        self._send_json({'error': 'min_mos must be between 1.0 and 5.0'}, 400)
                        return
                
                history = self.pbx_core.qos_monitor.get_historical_metrics(limit, min_mos)
                self._send_json({
                    'count': len(history),
                    'metrics': history
                })
            except ValueError as e:
                self.logger.error(f"Invalid parameter for QoS history: {e}")
                self._send_json({'error': 'Invalid parameters, check limit (integer) and min_mos (float)'}, 400)
            except Exception as e:
                self.logger.error(f"Error getting QoS history: {e}")
                self._send_json({'error': f'Error getting QoS history: {str(e)}'}, 500)
        else:
            self._send_json({'error': 'QoS monitoring not enabled'}, 500)

    def _handle_get_qos_statistics(self):
        """Get overall QoS statistics"""
        if self.pbx_core and hasattr(self.pbx_core, 'qos_monitor'):
            try:
                stats = self.pbx_core.qos_monitor.get_statistics()
                self._send_json(stats)
            except Exception as e:
                self.logger.error(f"Error getting QoS statistics: {e}")
                self._send_json({'error': f'Error getting QoS statistics: {str(e)}'}, 500)
        else:
            self._send_json({'error': 'QoS monitoring not enabled'}, 500)

    def _handle_get_qos_call_metrics(self, path):
        """Get QoS metrics for a specific call"""
        if self.pbx_core and hasattr(self.pbx_core, 'qos_monitor'):
            try:
                # Extract call_id from path: /api/qos/call/{call_id}
                call_id = path.split('/')[-1]
                metrics = self.pbx_core.qos_monitor.get_metrics(call_id)
                if metrics:
                    self._send_json(metrics)
                else:
                    self._send_json({'error': f'No QoS metrics found for call {call_id}'}, 404)
            except Exception as e:
                self.logger.error(f"Error getting call QoS metrics: {e}")
                self._send_json({'error': f'Error getting call QoS metrics: {str(e)}'}, 500)
        else:
            self._send_json({'error': 'QoS monitoring not enabled'}, 500)

    def _handle_get_provisioning_devices(self):
        """Get all provisioned devices"""
        if self.pbx_core and hasattr(self.pbx_core, 'phone_provisioning'):
            devices = self.pbx_core.phone_provisioning.get_all_devices()
            data = [d.to_dict() for d in devices]
            self._send_json(data)
        else:
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)

    def _handle_get_provisioning_vendors(self):
        """Get supported vendors and models"""
        if self.pbx_core and hasattr(self.pbx_core, 'phone_provisioning'):
            vendors = self.pbx_core.phone_provisioning.get_supported_vendors()
            models = self.pbx_core.phone_provisioning.get_supported_models()
            data = {
                'vendors': vendors,
                'models': models
            }
            self._send_json(data)
        else:
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
    
    def _handle_get_provisioning_diagnostics(self):
        """Get provisioning system diagnostics"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        provisioning = self.pbx_core.phone_provisioning
        
        # Gather diagnostic information
        diagnostics = {
            'enabled': True,
            'configuration': {
                'url_format': self.pbx_core.config.get('provisioning.url_format', 'Not configured'),
                'external_ip': self.pbx_core.config.get('server.external_ip', 'Not configured'),
                'api_port': self.pbx_core.config.get('api.port', 'Not configured'),
                'sip_host': self.pbx_core.config.get('server.sip_host', 'Not configured'),
                'sip_port': self.pbx_core.config.get('server.sip_port', 'Not configured'),
                'custom_templates_dir': self.pbx_core.config.get('provisioning.custom_templates_dir', 'Not configured')
            },
            'statistics': {
                'total_devices': len(provisioning.devices),
                'total_templates': len(provisioning.templates),
                'total_requests': len(provisioning.provision_requests),
                'successful_requests': sum(1 for r in provisioning.provision_requests if r.get('success')),
                'failed_requests': sum(1 for r in provisioning.provision_requests if not r.get('success'))
            },
            'devices': [d.to_dict() for d in provisioning.get_all_devices()],
            'vendors': provisioning.get_supported_vendors(),
            'models': provisioning.get_supported_models(),
            'recent_requests': provisioning.get_request_history(limit=20)
        }
        
        # Add warnings for common issues
        warnings = []
        if diagnostics['configuration']['external_ip'] == 'Not configured':
            warnings.append('server.external_ip is not configured - phones may not be able to reach the PBX')
        if diagnostics['statistics']['total_devices'] == 0:
            warnings.append('No devices registered - use POST /api/provisioning/devices to register devices')
        if diagnostics['statistics']['failed_requests'] > 0:
            warnings.append(f"{diagnostics['statistics']['failed_requests']} provisioning requests failed - check recent_requests for details")
        
        diagnostics['warnings'] = warnings
        
        self._send_json(diagnostics)
    
    def _handle_get_provisioning_requests(self):
        """Get provisioning request history"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        # Get limit from query parameter if provided
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        limit = int(query_params.get('limit', [50])[0])
        
        requests = self.pbx_core.phone_provisioning.get_request_history(limit=limit)
        self._send_json({
            'total': len(self.pbx_core.phone_provisioning.provision_requests),
            'limit': limit,
            'requests': requests
        })
    
    def _handle_get_provisioning_templates(self):
        """Get list of all provisioning templates"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        templates = self.pbx_core.phone_provisioning.list_all_templates()
        self._send_json({
            'templates': templates,
            'total': len(templates)
        })
    
    def _handle_get_template_content(self, vendor, model):
        """Get content of a specific template"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        content = self.pbx_core.phone_provisioning.get_template_content(vendor, model)
        if content:
            self._send_json({
                'vendor': vendor,
                'model': model,
                'content': content,
                'placeholders': [
                    '{{EXTENSION_NUMBER}}',
                    '{{EXTENSION_NAME}}',
                    '{{EXTENSION_PASSWORD}}',
                    '{{SIP_SERVER}}',
                    '{{SIP_PORT}}',
                    '{{SERVER_NAME}}'
                ]
            })
        else:
            self._send_json({'error': f'Template not found for {vendor} {model}'}, 404)
    
    def _handle_export_template(self, vendor, model):
        """Export template to file"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        success, message, filepath = self.pbx_core.phone_provisioning.export_template_to_file(vendor, model)
        if success:
            self._send_json({
                'success': True,
                'message': message,
                'filepath': filepath,
                'vendor': vendor,
                'model': model
            })
        else:
            self._send_json({'error': message}, 404)
    
    def _handle_update_template(self, vendor, model):
        """Update template content"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        try:
            body = self._get_body()
            content = body.get('content')
            
            if not content:
                self._send_json({'error': 'Missing template content'}, 400)
                return
            
            success, message = self.pbx_core.phone_provisioning.update_template(vendor, model, content)
            if success:
                self._send_json({
                    'success': True,
                    'message': message,
                    'vendor': vendor,
                    'model': model
                })
            else:
                self._send_json({'error': message}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_reload_templates(self):
        """Reload all templates from disk"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return
        
        success, message, stats = self.pbx_core.phone_provisioning.reload_templates()
        if success:
            self._send_json({
                'success': True,
                'message': message,
                'statistics': stats
            })
        else:
            self._send_json({'error': message}, 500)

    def _handle_get_registered_phones(self):
        """Get all registered phones from database"""
        logger = get_logger()
        if self.pbx_core and hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                phones = self.pbx_core.registered_phones_db.list_all()
                self._send_json(phones)
            except Exception as e:
                logger.error(f"Error loading registered phones from database: {e}")
                logger.error(f"  Database type: {self.pbx_core.registered_phones_db.db.db_type if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Database enabled: {self.pbx_core.registered_phones_db.db.enabled if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Traceback: {traceback.format_exc()}")
                self._send_json({'error': str(e), 'details': 'Check server logs for full error details'}, 500)
        else:
            # Return empty array when database is not available (graceful degradation)
            logger.warning("Registered phones database not available - returning empty list")
            if self.pbx_core:
                logger.warning(f"  pbx_core exists: True")
                logger.warning(f"  has registered_phones_db attr: {hasattr(self.pbx_core, 'registered_phones_db')}")
                if hasattr(self.pbx_core, 'registered_phones_db'):
                    logger.warning(f"  registered_phones_db is None: {self.pbx_core.registered_phones_db is None}")
            self._send_json([])

    def _handle_get_registered_phones_with_mac(self):
        """Get registered phones with MAC addresses from provisioning system"""
        logger = get_logger()
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return
        
        # Get registered phones (IP + Extension from SIP registrations)
        registered_phones = []
        if hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                registered_phones = self.pbx_core.registered_phones_db.list_all()
            except Exception as e:
                logger.error(f"Error loading registered phones: {e}")
        
        # Get provisioned devices (MAC + Extension from provisioning config)
        provisioned_devices = {}
        if hasattr(self.pbx_core, 'phone_provisioning'):
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
            extension = phone.get('extension_number')
            
            # Add MAC from provisioning if available and not already present
            if extension and extension in provisioned_devices and not phone.get('mac_address'):
                device = provisioned_devices[extension]
                enhanced['mac_address'] = device.mac_address
                enhanced['vendor'] = device.vendor
                enhanced['model'] = device.model
                enhanced['config_url'] = device.config_url
                enhanced['mac_source'] = 'provisioning'
            elif phone.get('mac_address'):
                enhanced['mac_source'] = 'sip_registration'
            
            enhanced_phones.append(enhanced)
        
        self._send_json(enhanced_phones)

    def _handle_phone_lookup(self, identifier):
        """Unified phone lookup by MAC or IP address"""
        logger = get_logger()
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return
        
        result = {
            'identifier': identifier,
            'type': None,
            'registered_phone': None,
            'provisioned_device': None,
            'correlation': None
        }
        
        # Normalize the identifier to detect if it's a MAC or IP
        from pbx.features.phone_provisioning import normalize_mac_address
        import re
        
        # Check if it looks like a MAC address using regex
        # Matches formats: XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, XXXXXXXXXXXX
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$')
        is_mac = bool(mac_pattern.match(identifier))
        
        # Check if it looks like an IP address using regex
        # Matches valid IPv4 addresses
        ip_pattern = re.compile(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
        is_ip = bool(ip_pattern.match(identifier))
        
        # Try MAC address lookup
        if is_mac:
            result['type'] = 'mac'
            normalized_mac = normalize_mac_address(identifier)
            
            # Check provisioning system
            if hasattr(self.pbx_core, 'phone_provisioning'):
                device = self.pbx_core.phone_provisioning.get_device(identifier)
                if device:
                    result['provisioned_device'] = device.to_dict()
            
            # Check registered phones
            if hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
                try:
                    phone = self.pbx_core.registered_phones_db.get_by_mac(normalized_mac)
                    if phone:
                        result['registered_phone'] = phone
                except Exception as e:
                    logger.error(f"Error looking up MAC in registered_phones: {e}")
        
        # Try IP address lookup
        elif is_ip:
            result['type'] = 'ip'
            
            # Check registered phones first
            if hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
                try:
                    phone = self.pbx_core.registered_phones_db.get_by_ip(identifier)
                    if phone:
                        result['registered_phone'] = phone
                        
                        # Now try to find MAC from provisioning using the extension
                        extension = phone.get('extension_number')
                        if extension and hasattr(self.pbx_core, 'phone_provisioning'):
                            device = None
                            # Search through provisioned devices for this extension
                            for dev in self.pbx_core.phone_provisioning.get_all_devices():
                                if dev.extension_number == extension:
                                    device = dev
                                    break
                            if device:
                                result['provisioned_device'] = device.to_dict()
                except Exception as e:
                    logger.error(f"Error looking up IP in registered_phones: {e}")
        else:
            result['type'] = 'unknown'
            self._send_json({'error': f'Could not determine if {identifier} is a MAC address or IP address'}, 400)
            return
        
        # Add correlation summary
        if result['registered_phone'] and result['provisioned_device']:
            result['correlation'] = {
                'matched': True,
                'extension': result['registered_phone'].get('extension_number'),
                'mac_address': result['provisioned_device'].get('mac_address'),
                'ip_address': result['registered_phone'].get('ip_address'),
                'vendor': result['provisioned_device'].get('vendor'),
                'model': result['provisioned_device'].get('model')
            }
        elif result['registered_phone']:
            result['correlation'] = {
                'matched': False,
                'message': 'Phone is registered but not provisioned in the system',
                'extension': result['registered_phone'].get('extension_number'),
                'ip_address': result['registered_phone'].get('ip_address')
            }
        elif result['provisioned_device']:
            result['correlation'] = {
                'matched': False,
                'message': 'Device is provisioned but not currently registered',
                'extension': result['provisioned_device'].get('extension_number'),
                'mac_address': result['provisioned_device'].get('mac_address')
            }
        else:
            result['correlation'] = {
                'matched': False,
                'message': 'No information found for this identifier'
            }
        
        self._send_json(result)

    def _handle_get_registered_phones_by_extension(self, extension):
        """Get registered phones for a specific extension"""
        logger = get_logger()
        if self.pbx_core and hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
            try:
                phones = self.pbx_core.registered_phones_db.get_by_extension(extension)
                self._send_json(phones)
            except Exception as e:
                logger.error(f"Error loading registered phones for extension {extension} from database: {e}")
                logger.error(f"  Extension: {extension}")
                logger.error(f"  Database type: {self.pbx_core.registered_phones_db.db.db_type if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Database enabled: {self.pbx_core.registered_phones_db.db.enabled if hasattr(self.pbx_core.registered_phones_db, 'db') else 'unknown'}")
                logger.error(f"  Traceback: {traceback.format_exc()}")
                self._send_json({'error': str(e), 'details': 'Check server logs for full error details'}, 500)
        else:
            # Return empty array when database is not available (graceful degradation)
            logger.warning(f"Registered phones database not available for extension {extension} - returning empty list")
            if self.pbx_core:
                logger.warning(f"  pbx_core exists: True")
                logger.warning(f"  has registered_phones_db attr: {hasattr(self.pbx_core, 'registered_phones_db')}")
                if hasattr(self.pbx_core, 'registered_phones_db'):
                    logger.warning(f"  registered_phones_db is None: {self.pbx_core.registered_phones_db is None}")
            self._send_json([])

    def _handle_register_device(self):
        """Register a device for provisioning"""
        logger = get_logger()
        
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            body = self._get_body()
            mac = body.get('mac_address')
            extension = body.get('extension_number')
            vendor = body.get('vendor')
            model = body.get('model')

            if not all([mac, extension, vendor, model]):
                self._send_json({'error': 'Missing required fields'}, 400)
                return

            device = self.pbx_core.phone_provisioning.register_device(
                mac, extension, vendor, model
            )
            
            # Automatically trigger phone reboot after registration
            # This ensures the phone fetches its fresh configuration immediately
            reboot_triggered = False
            try:
                ext = self.pbx_core.extension_registry.get(extension)
                if ext and ext.registered:
                    logger.info(f"Auto-provisioning: Automatically rebooting phone for extension {extension} after device registration")
                    reboot_triggered = self.pbx_core.phone_provisioning.reboot_phone(
                        extension, self.pbx_core.sip_server
                    )
                    if reboot_triggered:
                        logger.info(f"Auto-provisioning: Successfully triggered reboot for extension {extension}")
                    else:
                        logger.info(f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot")
                else:
                    logger.info(f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot")
            except Exception as reboot_error:
                logger.warning(f"Auto-provisioning: Could not auto-reboot phone for extension {extension}: {reboot_error}")
                # Don't fail the registration if reboot fails
            
            response = {
                'success': True,
                'device': device.to_dict()
            }
            if reboot_triggered:
                response['reboot_triggered'] = True
                response['message'] = 'Device registered and phone reboot triggered automatically'
            else:
                response['reboot_triggered'] = False
                response['message'] = 'Device registered. Phone will fetch config on next boot.'
            
            self._send_json(response)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_unregister_device(self, mac):
        """Unregister a device"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            success = self.pbx_core.phone_provisioning.unregister_device(mac)
            if success:
                self._send_json({'success': True, 'message': 'Device unregistered'})
            else:
                self._send_json({'error': 'Device not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_set_static_ip(self, mac):
        """Set static IP for a device"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            body = self._get_body()
            static_ip = body.get('static_ip')

            if not static_ip:
                self._send_json({'error': 'Missing static_ip field'}, 400)
                return

            success, message = self.pbx_core.phone_provisioning.set_static_ip(mac, static_ip)
            if success:
                self._send_json({'success': True, 'message': message})
            else:
                self._send_json({'error': message}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_provisioning_request(self, path):
        """Handle phone provisioning config request"""
        logger = get_logger()
        
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            logger.error("Phone provisioning not enabled but provisioning request received")
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            # Extract MAC address from path: /provision/{mac}.cfg
            filename = path.split('/')[-1]
            mac = filename.replace('.cfg', '')
            
            # Gather request information for logging
            request_info = {
                'ip': self.client_address[0] if self.client_address else 'Unknown',
                'user_agent': self.headers.get('User-Agent', 'Unknown'),
                'path': path
            }
            
            logger.info(f"Provisioning config request: path={path}, IP={request_info['ip']}")
            
            # Detect if MAC is a literal placeholder (misconfiguration)
            # Examples: {mac}, {MAC} - these indicate the phone didn't substitute its actual MAC
            # Note: $mac and $MA are not checked here - those are the CORRECT variable formats
            if mac in MAC_ADDRESS_PLACEHOLDERS:
                logger.error(f"CONFIGURATION ERROR: Phone requested provisioning with placeholder '{mac}' instead of actual MAC address")
                logger.error(f"  Request from IP: {request_info['ip']}")
                logger.error(f"  User-Agent: {request_info['user_agent']}")
                logger.error(f"")
                logger.error(f"  ⚠️  ROOT CAUSE: Phone is configured with wrong MAC variable format")
                logger.error(f"")
                logger.error(f"  📋 SOLUTION: Update provisioning URL to use correct MAC variable for your phone:")
                logger.error(f"")
                
                # Detect vendor from User-Agent and provide specific guidance
                user_agent = request_info['user_agent'].lower()
                if 'zultys' in user_agent:
                    logger.error(f"  ✓ Zultys Phones - Use: https://YOUR_PBX_IP:8080/provision/$mac.cfg")
                    logger.error(f"    Configure in: Phone Menu → Setup → Network → Provisioning")
                    logger.error(f"    Or DHCP Option 66: https://YOUR_PBX_IP:8080/provision/$mac.cfg")
                elif 'yealink' in user_agent:
                    logger.error(f"  ✓ Yealink Phones - Use: https://YOUR_PBX_IP:8080/provision/$mac.cfg")
                    logger.error(f"    Configure in: Web Interface → Settings → Auto Provision")
                elif 'polycom' in user_agent:
                    logger.error(f"  ✓ Polycom Phones - Use: https://YOUR_PBX_IP:8080/provision/$mac.cfg")
                    logger.error(f"    Configure in: Web Interface → Settings → Provisioning Server")
                elif 'cisco' in user_agent:
                    logger.error(f"  ✓ Cisco Phones - Use: https://YOUR_PBX_IP:8080/provision/$MA.cfg")
                    logger.error(f"    Note: Cisco uses $MA instead of $mac")
                    logger.error(f"    Configure in: Web Interface → Admin Login → Voice → Provisioning")
                elif 'grandstream' in user_agent:
                    logger.error(f"  ✓ Grandstream Phones - Use: https://YOUR_PBX_IP:8080/provision/$mac.cfg")
                    logger.error(f"    Configure in: Web Interface → Maintenance → Upgrade and Provisioning")
                else:
                    logger.error(f"  Common MAC variable formats by vendor:")
                    logger.error(f"    • Zultys, Yealink, Polycom, Grandstream: $mac")
                    logger.error(f"    • Cisco: $MA")
                logger.error(f"")
                logger.error(f"  📖 See PHONE_PROVISIONING.md for detailed vendor-specific instructions")
                
                self._send_json({
                    'error': 'Configuration error: MAC address placeholder detected',
                    'details': f'Phone is using placeholder "{mac}" instead of actual MAC. Update provisioning URL to use correct MAC variable format for your phone vendor.'
                }, 400)
                return
            
            logger.info(f"  MAC address from request: {mac}")

            # Generate configuration
            config_content, content_type = self.pbx_core.phone_provisioning.generate_config(
                mac, self.pbx_core.extension_registry, request_info
            )

            if config_content:
                self._set_headers(content_type=content_type)
                self.wfile.write(config_content.encode())
                logger.info(f"✓ Provisioning config delivered: {len(config_content)} bytes to {request_info['ip']}")
                
                # Store IP to MAC mapping in database for admin panel tracking
                # This allows correlation between provisioned devices and their network addresses
                if self.pbx_core and hasattr(self.pbx_core, 'registered_phones_db') and self.pbx_core.registered_phones_db:
                    try:
                        # Get the device to find its extension number
                        device = self.pbx_core.phone_provisioning.get_device(mac)
                        if device:
                            # Store/update the IP-MAC-Extension mapping
                            normalized_mac = normalize_mac_address(mac)
                            
                            # Store the mapping in the database
                            success, stored_mac = self.pbx_core.registered_phones_db.register_phone(
                                extension_number=device.extension_number,
                                ip_address=request_info['ip'],
                                mac_address=normalized_mac,
                                user_agent=request_info.get('user_agent', 'Unknown'),
                                contact_uri=None  # Not available during provisioning request
                            )
                            if success:
                                # stored_mac should equal normalized_mac since we're providing it
                                logger.info(f"  Stored IP-MAC mapping: {request_info['ip']} → {stored_mac} (ext {device.extension_number})")
                    except Exception as e:
                        # Don't fail provisioning if database storage fails
                        logger.warning(f"  Could not store IP-MAC mapping in database: {e}")
            else:
                logger.warning(f"✗ Provisioning failed for MAC {mac} from IP {request_info['ip']}")
                logger.warning(f"  Reason: Device not registered or template not found")
                logger.warning(f"  See detailed error messages above for troubleshooting guidance")
                logger.warning(f"  To register this device:")
                logger.warning(f"    curl -k -X POST https://YOUR_PBX_IP:8080/api/provisioning/devices \\")
                logger.warning(f"      -H 'Content-Type: application/json' \\")
                logger.warning(f"      -d '{{\"mac_address\":\"{mac}\",\"extension_number\":\"XXXX\",\"vendor\":\"VENDOR\",\"model\":\"MODEL\"}}'")
                logger.warning(f"    Note: Use -k with curl if using self-signed certificates")
                self._send_json({'error': 'Device or template not found'}, 404)
        except Exception as e:
            logger.error(f"Error handling provisioning request: {e}")
            logger.error(f"  Path: {path}")
            logger.error(f"  Traceback: {traceback.format_exc()}")
            self._send_json({'error': str(e)}, 500)

    def _handle_admin_redirect(self):
        """Redirect to admin panel"""
        self.send_response(302)
        self.send_header('Location', '/admin/index.html')
        self.end_headers()

    def _handle_static_file(self, path):
        """Serve static files from admin directory"""
        try:
            # Remove /admin prefix to get relative path
            file_path = path.replace('/admin/', '', 1)
            full_path = os.path.join(ADMIN_DIR, file_path)

            # Prevent directory traversal attacks - ensure path stays within admin directory
            real_admin_dir = os.path.realpath(ADMIN_DIR)
            real_full_path = os.path.realpath(full_path)

            if not real_full_path.startswith(real_admin_dir):
                self._send_json({'error': 'Access denied'}, 403)
                return

            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                self._send_json({'error': 'File not found'}, 404)
                return

            # Determine content type
            content_type, _ = mimetypes.guess_type(full_path)
            if not content_type:
                content_type = 'application/octet-stream'

            # Read and serve file
            with open(full_path, 'rb') as f:
                content = f.read()

            self._set_headers(content_type=content_type)
            self.wfile.write(content)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_get_config(self):
        """Get current configuration"""
        if self.pbx_core:
            config_data = {
                'smtp': {
                    'host': self.pbx_core.config.get('voicemail.smtp.host', ''),
                    'port': self.pbx_core.config.get('voicemail.smtp.port', 587),
                    'username': self.pbx_core.config.get('voicemail.smtp.username', '')
                },
                'email': {
                    'from_address': self.pbx_core.config.get('voicemail.email.from_address', '')
                },
                'email_notifications': self.pbx_core.config.get('voicemail.email_notifications', False)
            }
            self._send_json(config_data)
        else:
            self._send_json({'error': 'PBX not initialized'}, 500)

    def _handle_add_extension(self):
        """Add a new extension"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body()
            number = body.get('number')
            name = body.get('name')
            email = body.get('email')
            password = body.get('password')
            allow_external = body.get('allow_external', True)
            voicemail_pin = body.get('voicemail_pin')

            if not all([number, name, password]):
                self._send_json({'error': 'Missing required fields'}, 400)
                return

            # Validate extension number format (4 digits)
            if not str(number).isdigit() or len(str(number)) != 4:
                self._send_json({'error': 'Extension number must be 4 digits'}, 400)
                return

            # Validate password strength (minimum 8 characters)
            if len(password) < 8:
                self._send_json({'error': 'Password must be at least 8 characters'}, 400)
                return

            # Validate email format if provided
            if email and not Config.validate_email(email):
                self._send_json({'error': 'Invalid email format'}, 400)
                return

            # Check if extension already exists
            if self.pbx_core.extension_registry.get(number):
                self._send_json({'error': 'Extension already exists'}, 400)
                return

            # Try to add to database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Add to database
                # NOTE: For production, use FIPS-compliant hashing via pbx.utils.encryption.FIPSEncryption.hash_password()
                # Currently storing plain password; system supports both plain and hashed passwords
                password_hash = password
                success = self.pbx_core.extension_db.add(
                    number=number,
                    name=name,
                    password_hash=password_hash,
                    email=email if email else None,
                    allow_external=allow_external,
                    voicemail_pin=voicemail_pin if voicemail_pin else None,
                    ad_synced=False,
                    ad_username=None
                )
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.add_extension(number, name, email, password, allow_external)

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({'success': True, 'message': 'Extension added successfully'})
            else:
                self._send_json({'error': 'Failed to add extension'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_update_extension(self, number):
        """Update an existing extension"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body()
            name = body.get('name')
            email = body.get('email')
            password = body.get('password')  # Optional
            allow_external = body.get('allow_external')
            voicemail_pin = body.get('voicemail_pin')

            # Check if extension exists
            extension = self.pbx_core.extension_registry.get(number)
            if not extension:
                self._send_json({'error': 'Extension not found'}, 404)
                return

            # Validate password strength if provided (minimum 8 characters)
            if password and len(password) < 8:
                self._send_json({'error': 'Password must be at least 8 characters'}, 400)
                return

            # Validate email format if provided
            if email and not Config.validate_email(email):
                self._send_json({'error': 'Invalid email format'}, 400)
                return

            # Try to update in database first, fall back to config.yml
            if self.pbx_core.extension_db:
                # Update in database
                # NOTE: For production, use FIPS-compliant hashing via pbx.utils.encryption.FIPSEncryption.hash_password()
                # Currently storing plain password; system supports both plain and hashed passwords
                password_hash = password if password else None
                success = self.pbx_core.extension_db.update(
                    number=number,
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    allow_external=allow_external,
                    voicemail_pin=voicemail_pin
                )
            else:
                # Fall back to config.yml
                success = self.pbx_core.config.update_extension(number, name, email, password, allow_external)

            if success:
                # Reload extensions
                self.pbx_core.extension_registry.reload()
                self._send_json({'success': True, 'message': 'Extension updated successfully'})
            else:
                self._send_json({'error': 'Failed to update extension'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_delete_extension(self, number):
        """Delete an extension"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            # Check if extension exists
            extension = self.pbx_core.extension_registry.get(number)
            if not extension:
                self._send_json({'error': 'Extension not found'}, 404)
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
                self._send_json({'success': True, 'message': 'Extension deleted successfully'})
            else:
                self._send_json({'error': 'Failed to delete extension'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_update_config(self):
        """Update system configuration"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body()

            # Update configuration
            success = self.pbx_core.config.update_email_config(body)

            if success:
                self._send_json({'success': True, 'message': 'Configuration updated successfully. Restart required.'})
            else:
                self._send_json({'error': 'Failed to update configuration'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_get_full_config(self):
        """Get full system configuration for admin panel"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            # Return comprehensive configuration for the admin panel
            config_data = {
                'server': {
                    'sip_port': self.pbx_core.config.get('server.sip_port', 5060),
                    'external_ip': self.pbx_core.config.get('server.external_ip', ''),
                    'server_name': self.pbx_core.config.get('server.server_name', 'PBX System')
                },
                'api': {
                    'port': self.pbx_core.config.get('api.port', 8080),
                    'ssl': {
                        'enabled': self.pbx_core.config.get('api.ssl.enabled', False),
                        'cert_file': self.pbx_core.config.get('api.ssl.cert_file', 'certs/server.crt'),
                        'key_file': self.pbx_core.config.get('api.ssl.key_file', 'certs/server.key')
                    }
                },
                'features': {
                    'call_recording': self.pbx_core.config.get('features.call_recording', True),
                    'call_transfer': self.pbx_core.config.get('features.call_transfer', True),
                    'call_hold': self.pbx_core.config.get('features.call_hold', True),
                    'conference': self.pbx_core.config.get('features.conference', True),
                    'voicemail': self.pbx_core.config.get('features.voicemail', True),
                    'call_parking': self.pbx_core.config.get('features.call_parking', True),
                    'call_queues': self.pbx_core.config.get('features.call_queues', True),
                    'presence': self.pbx_core.config.get('features.presence', True),
                    'music_on_hold': self.pbx_core.config.get('features.music_on_hold', True),
                    'auto_attendant': self.pbx_core.config.get('features.auto_attendant', True),
                    'webrtc': {
                        'enabled': self.pbx_core.config.get('features.webrtc.enabled', True)
                    },
                    'webhooks': {
                        'enabled': self.pbx_core.config.get('features.webhooks.enabled', False)
                    },
                    'crm_integration': {
                        'enabled': self.pbx_core.config.get('features.crm_integration.enabled', True)
                    },
                    'hot_desking': {
                        'enabled': self.pbx_core.config.get('features.hot_desking.enabled', True),
                        'require_pin': self.pbx_core.config.get('features.hot_desking.require_pin', True)
                    },
                    'voicemail_transcription': {
                        'enabled': self.pbx_core.config.get('features.voicemail_transcription.enabled', True)
                    }
                },
                'voicemail': {
                    'max_message_duration': self.pbx_core.config.get('voicemail.max_message_duration', 180),
                    'max_greeting_duration': self.pbx_core.config.get('voicemail.max_greeting_duration', 30),
                    'no_answer_timeout': self.pbx_core.config.get('voicemail.no_answer_timeout', 30),
                    'allow_custom_greetings': self.pbx_core.config.get('voicemail.allow_custom_greetings', True),
                    'email_notifications': self.pbx_core.config.get('voicemail.email_notifications', True),
                    'smtp': {
                        'host': self.pbx_core.config.get('voicemail.smtp.host', ''),
                        'port': self.pbx_core.config.get('voicemail.smtp.port', 587),
                        'use_tls': self.pbx_core.config.get('voicemail.smtp.use_tls', True),
                        'username': self.pbx_core.config.get('voicemail.smtp.username', '')
                    },
                    'email': {
                        'from_address': self.pbx_core.config.get('voicemail.email.from_address', ''),
                        'from_name': self.pbx_core.config.get('voicemail.email.from_name', 'PBX Voicemail')
                    }
                },
                'recording': {
                    'auto_record': self.pbx_core.config.get('recording.auto_record', False),
                    'format': self.pbx_core.config.get('recording.format', 'wav'),
                    'storage_path': self.pbx_core.config.get('recording.storage_path', 'recordings')
                },
                'security': {
                    'password': {
                        'min_length': self.pbx_core.config.get('security.password.min_length', 12),
                        'require_uppercase': self.pbx_core.config.get('security.password.require_uppercase', True),
                        'require_lowercase': self.pbx_core.config.get('security.password.require_lowercase', True),
                        'require_digit': self.pbx_core.config.get('security.password.require_digit', True),
                        'require_special': self.pbx_core.config.get('security.password.require_special', True)
                    },
                    'rate_limit': {
                        'max_attempts': self.pbx_core.config.get('security.rate_limit.max_attempts', 5),
                        'lockout_duration': self.pbx_core.config.get('security.rate_limit.lockout_duration', 900)
                    },
                    'fips_mode': self.pbx_core.config.get('security.fips_mode', True)
                },
                'conference': {
                    'max_participants': self.pbx_core.config.get('conference.max_participants', 50),
                    'record_conferences': self.pbx_core.config.get('conference.record_conferences', False)
                }
            }
            
            self._send_json(config_data)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_update_config_section(self):
        """Update a specific section of system configuration"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body()
            section = body.get('section')
            data = body.get('data')

            if section is None or data is None:
                self._send_json({'error': 'Missing section or data'}, 400)
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
            merged_section = deep_merge(current_section.copy() if isinstance(current_section, dict) else {}, data)
            self.pbx_core.config.config[section] = merged_section
            
            # Save configuration
            success = self.pbx_core.config.save()

            if success:
                self._send_json({'success': True, 'message': 'Configuration updated successfully. Restart may be required for some changes.'})
            else:
                self._send_json({'error': 'Failed to save configuration'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_get_ssl_status(self):
        """Get SSL/HTTPS configuration status"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            ssl_config = self.pbx_core.config.get('api.ssl', {})
            cert_file = ssl_config.get('cert_file', 'certs/server.crt')
            key_file = ssl_config.get('key_file', 'certs/server.key')
            
            # Check if certificate files exist
            cert_exists = os.path.exists(cert_file)
            key_exists = os.path.exists(key_file)
            
            # Get certificate details if it exists
            cert_details = None
            if cert_exists and SSL_GENERATION_AVAILABLE:
                try:
                    with open(cert_file, 'rb') as f:
                        cert_data = f.read()
                        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                        
                        now = datetime.now(timezone.utc)
                        cert_details = {
                            'subject': cert.subject.rfc4514_string(),
                            'issuer': cert.issuer.rfc4514_string(),
                            'valid_from': cert.not_valid_before.isoformat(),
                            'valid_until': cert.not_valid_after.isoformat(),
                            'is_expired': cert.not_valid_after < now,
                            'days_until_expiry': (cert.not_valid_after - now).days,
                            'serial_number': str(cert.serial_number)
                        }
                except Exception as e:
                    self.logger.warning(f"Failed to parse certificate: {e}")
            
            status_data = {
                'enabled': ssl_config.get('enabled', False),
                'cert_file': cert_file,
                'key_file': key_file,
                'cert_exists': cert_exists,
                'key_exists': key_exists,
                'cert_details': cert_details,
                'ca': {
                    'enabled': ssl_config.get('ca', {}).get('enabled', False),
                    'server_url': ssl_config.get('ca', {}).get('server_url', '')
                }
            }
            
            self._send_json(status_data)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_generate_ssl_certificate(self):
        """Generate self-signed SSL certificate"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            body = self._get_body() or {}
            
            # Get parameters
            hostname = body.get('hostname', self.pbx_core.config.get('server.external_ip', 'localhost'))
            days_valid = body.get('days_valid', 365)
            cert_dir = body.get('cert_dir', 'certs')
            
            # Validate parameters
            if not hostname:
                hostname = 'localhost'
            
            if not isinstance(days_valid, int) or days_valid < 1 or days_valid > 3650:
                days_valid = 365
            
            self.logger.info(f"Generating self-signed SSL certificate for {hostname}")
            
            # Check if SSL generation is available
            if not SSL_GENERATION_AVAILABLE:
                self._send_json({
                    'error': 'Required cryptography library not available',
                    'details': 'Install with: pip install cryptography'
                }, 500)
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
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PBX System"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])
            
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
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.now(timezone.utc)
            ).not_valid_after(
                datetime.now(timezone.utc) + timedelta(days=days_valid)
            ).add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Write private key to file
            key_file = cert_path / "server.key"
            with open(key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set restrictive permissions on private key
            os.chmod(key_file, 0o600)
            
            # Write certificate to file
            cert_file = cert_path / "server.crt"
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            self.logger.info(f"SSL certificate generated successfully: {cert_file}")
            
            # Update configuration to enable SSL
            ssl_config = self.pbx_core.config.get('api.ssl', {})
            ssl_config['enabled'] = True
            ssl_config['cert_file'] = str(cert_file)
            ssl_config['key_file'] = str(key_file)
            
            self.pbx_core.config.config.setdefault('api', {})['ssl'] = ssl_config
            self.pbx_core.config.save()
            
            self._send_json({
                'success': True,
                'message': 'SSL certificate generated successfully. Server restart required to enable HTTPS.',
                'cert_file': str(cert_file),
                'key_file': str(key_file),
                'hostname': hostname,
                'valid_days': days_valid
            })
        except Exception as e:
            self.logger.error(f"Failed to generate SSL certificate: {e}")
            import traceback
            traceback.print_exc()
            self._send_json({'error': str(e)}, 500)

    def _handle_get_voicemail(self, path):
        """Get voicemail messages for an extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail not enabled'}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension} or /api/voicemail/{extension}/{message_id}
            parts = path.split('/')
            if len(parts) < 4:
                self._send_json({'error': 'Invalid path'}, 400)
                return

            extension = parts[3]

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            if len(parts) == 4:
                # List all messages
                messages = mailbox.get_messages()
                data = []
                for msg in messages:
                    data.append({
                        'id': msg['id'],
                        'caller_id': msg['caller_id'],
                        'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                        'listened': msg['listened'],
                        'duration': msg['duration']
                    })
                self._send_json({'messages': data})
            elif len(parts) == 5:
                # Get specific message or download audio
                message_id = parts[4]

                # Find message
                message = None
                for msg in mailbox.get_messages():
                    if msg['id'] == message_id:
                        message = msg
                        break

                if not message:
                    self._send_json({'error': 'Message not found'}, 404)
                    return

                # Check if request is for metadata only (via query parameter)
                # Use self.path to get the full request URL with query string
                query_params = parse_qs(urlparse(self.path).query)
                if query_params.get('metadata', [False])[0] in ['true', '1', True]:
                    # Return message metadata as JSON
                    self._send_json({
                        'id': message['id'],
                        'caller_id': message['caller_id'],
                        'timestamp': message['timestamp'].isoformat() if message['timestamp'] else None,
                        'listened': message['listened'],
                        'duration': message['duration'],
                        'file_path': message['file_path']
                    })
                else:
                    # Default: Serve audio file for playback in admin panel
                    if os.path.exists(message['file_path']):
                        self._set_headers(content_type='audio/wav')
                        with open(message['file_path'], 'rb') as f:
                            self.wfile.write(f.read())
                    else:
                        self._send_json({'error': 'Audio file not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_update_voicemail(self, path):
        """Update voicemail settings (mark as read, update PIN)"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail not enabled'}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension}/pin or /api/voicemail/{extension}/{message_id}/mark-read
            parts = path.split('/')
            if len(parts) < 4:
                self._send_json({'error': 'Invalid path'}, 400)
                return

            extension = parts[3]
            body = self._get_body()

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            if len(parts) == 5 and parts[4] == 'pin':
                # Update PIN
                pin = body.get('pin')
                if not pin:
                    self._send_json({'error': 'PIN required'}, 400)
                    return

                if mailbox.set_pin(pin):
                    # Also update in config
                    self.pbx_core.config.update_voicemail_pin(extension, pin)
                    self._send_json({'success': True, 'message': 'PIN updated successfully'})
                else:
                    self._send_json({'error': 'Invalid PIN format. Must be 4 digits.'}, 400)
            elif len(parts) == 6 and parts[5] == 'mark-read':
                # Mark message as read
                message_id = parts[4]
                mailbox.mark_listened(message_id)
                self._send_json({'success': True, 'message': 'Message marked as read'})
            else:
                self._send_json({'error': 'Invalid operation'}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_delete_voicemail(self, path):
        """Delete voicemail message"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail not enabled'}, 500)
            return

        try:
            # Parse path: /api/voicemail/{extension}/{message_id}
            parts = path.split('/')
            if len(parts) != 5:
                self._send_json({'error': 'Invalid path'}, 400)
                return

            extension = parts[3]
            message_id = parts[4]

            # Get mailbox
            mailbox = self.pbx_core.voicemail_system.get_mailbox(extension)

            # Delete message
            if mailbox.delete_message(message_id):
                self._send_json({'success': True, 'message': 'Message deleted successfully'})
            else:
                self._send_json({'error': 'Message not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_reboot_phone(self, extension):
        """Reboot a specific phone"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            # Send SIP NOTIFY to reboot the phone
            success = self.pbx_core.phone_provisioning.reboot_phone(
                extension,
                self.pbx_core.sip_server
            )

            if success:
                self._send_json({
                    'success': True,
                    'message': f'Reboot signal sent to extension {extension}'
                })
            else:
                self._send_json({
                    'error': f'Failed to send reboot signal to extension {extension}. Extension may not be registered.'
                }, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_ad_status(self):
        """Get Active Directory integration status"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            status = self.pbx_core.get_ad_integration_status()
            self._send_json(status)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_ad_sync(self):
        """Manually trigger Active Directory user synchronization"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        try:
            result = self.pbx_core.sync_ad_users()
            if result['success']:
                self._send_json({
                    'success': True,
                    'message': f'Successfully synchronized {result["synced_count"]} users from Active Directory',
                    'synced_count': result['synced_count']
                })
            else:
                self._send_json({
                    'success': False,
                    'error': result['error']
                }, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_ad_search(self):
        """Search for users in Active Directory"""
        if not self.pbx_core:
            self._send_json({'error': 'PBX not initialized'}, 500)
            return

        if not hasattr(self.pbx_core, 'ad_integration') or not self.pbx_core.ad_integration:
            self._send_json({'error': 'Active Directory integration not enabled'}, 500)
            return

        try:
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            query = query_params.get('q', [''])[0]
            
            if not query:
                self._send_json({'error': 'Query parameter "q" is required'}, 400)
                return
            
            # Get max_results parameter (optional) with validation
            try:
                max_results = int(query_params.get('max_results', ['50'])[0])
                if max_results < 1 or max_results > 100:
                    self._send_json({'error': 'max_results must be between 1 and 100'}, 400)
                    return
            except ValueError:
                self._send_json({'error': 'max_results must be a valid integer'}, 400)
                return
            
            # Search AD users using the telephoneNumber attribute (and other attributes)
            results = self.pbx_core.ad_integration.search_users(query, max_results)
            
            self._send_json({
                'success': True,
                'count': len(results),
                'results': results
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_reboot_phones(self):
        """Reboot all registered phones"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_provisioning'):
            self._send_json({'error': 'Phone provisioning not enabled'}, 500)
            return

        try:
            # Send SIP NOTIFY to all registered phones
            results = self.pbx_core.phone_provisioning.reboot_all_phones(
                self.pbx_core.sip_server
            )

            self._send_json({
                'success': True,
                'message': f'Rebooted {results["success_count"]} phones',
                'rebooted': results['rebooted'],
                'failed': results['failed'],
                'success_count': results['success_count'],
                'failed_count': results['failed_count']
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def log_message(self, format, *args):
        """Override to use PBX logger"""
        pass  # Suppress default logging

    # Phone Book API handlers
    def _handle_get_phone_book(self):
        """Get all phone book entries"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_book'):
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        try:
            entries = self.pbx_core.phone_book.get_all_entries()
            self._send_json(entries)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_export_phone_book_xml(self):
        """Export phone book as XML (Yealink format)"""
        try:
            # Try to use phone book feature if available
            if (self.pbx_core and hasattr(self.pbx_core, 'phone_book') and 
                self.pbx_core.phone_book and self.pbx_core.phone_book.enabled):
                xml_content = self.pbx_core.phone_book.export_xml()
            else:
                # Fallback: Generate from extension registry
                xml_content = self._generate_xml_from_extensions()
            
            self._set_headers(content_type='application/xml')
            self.wfile.write(xml_content.encode())
        except Exception as e:
            self.logger.error(f"Error exporting phone book XML: {e}")
            self._send_json({'error': str(e)}, 500)
    
    def _generate_xml_from_extensions(self):
        """Generate phone book XML from extension registry (fallback)"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'extension_registry'):
            return '<?xml version="1.0" encoding="UTF-8"?><YealinkIPPhoneDirectory><Title>Directory</Title></YealinkIPPhoneDirectory>'
        
        extensions = self.pbx_core.extension_registry.get_all()
        
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<YealinkIPPhoneDirectory>')
        xml_lines.append('  <Title>Company Directory</Title>')
        
        for ext in sorted(extensions, key=lambda x: x.name):
            xml_lines.append('  <DirectoryEntry>')
            name = ext.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            xml_lines.append(f'    <Name>{name}</Name>')
            xml_lines.append(f'    <Telephone>{ext.number}</Telephone>')
            xml_lines.append('  </DirectoryEntry>')
        
        xml_lines.append('</YealinkIPPhoneDirectory>')
        return '\n'.join(xml_lines)
    
    def _handle_export_phone_book_cisco_xml(self):
        """Export phone book as Cisco XML format"""
        try:
            # Try to use phone book feature if available
            if (self.pbx_core and hasattr(self.pbx_core, 'phone_book') and 
                self.pbx_core.phone_book and self.pbx_core.phone_book.enabled):
                xml_content = self.pbx_core.phone_book.export_cisco_xml()
            else:
                # Fallback: Generate from extension registry
                xml_content = self._generate_cisco_xml_from_extensions()
            
            self._set_headers(content_type='application/xml')
            self.wfile.write(xml_content.encode())
        except Exception as e:
            self.logger.error(f"Error exporting Cisco phone book XML: {e}")
            self._send_json({'error': str(e)}, 500)
    
    def _generate_cisco_xml_from_extensions(self):
        """Generate Cisco phone book XML from extension registry (fallback)"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'extension_registry'):
            return '<?xml version="1.0" encoding="UTF-8"?><CiscoIPPhoneDirectory><Title>Directory</Title></CiscoIPPhoneDirectory>'
        
        extensions = self.pbx_core.extension_registry.get_all()
        
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<CiscoIPPhoneDirectory>')
        xml_lines.append('  <Title>Company Directory</Title>')
        xml_lines.append('  <Prompt>Select a contact</Prompt>')
        
        for ext in sorted(extensions, key=lambda x: x.name):
            xml_lines.append('  <DirectoryEntry>')
            name = ext.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            xml_lines.append(f'    <Name>{name}</Name>')
            xml_lines.append(f'    <Telephone>{ext.number}</Telephone>')
            xml_lines.append('  </DirectoryEntry>')
        
        xml_lines.append('</CiscoIPPhoneDirectory>')
        return '\n'.join(xml_lines)
    
    def _handle_export_phone_book_json(self):
        """Export phone book as JSON"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_book'):
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        try:
            json_content = self.pbx_core.phone_book.export_json()
            self._set_headers(content_type='application/json')
            self.wfile.write(json_content.encode())
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_search_phone_book(self):
        """Search phone book entries"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_book'):
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        try:
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            query = query_params.get('q', [''])[0]
            
            if not query:
                self._send_json({'error': 'Query parameter "q" is required'}, 400)
                return
            
            results = self.pbx_core.phone_book.search(query)
            self._send_json(results)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_add_phone_book_entry(self):
        """Add or update a phone book entry"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_book'):
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        try:
            data = self._get_body()
            extension = data.get('extension')
            name = data.get('name')
            
            if not extension or not name:
                self._send_json({'error': 'Extension and name are required'}, 400)
                return
            
            success = self.pbx_core.phone_book.add_entry(
                extension=extension,
                name=name,
                department=data.get('department'),
                email=data.get('email'),
                mobile=data.get('mobile'),
                office_location=data.get('office_location'),
                ad_synced=data.get('ad_synced', False)
            )
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Phone book entry added/updated: {extension}'
                })
            else:
                self._send_json({'error': 'Failed to add phone book entry'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_delete_phone_book_entry(self, extension: str):
        """Delete a phone book entry"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_book'):
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        try:
            success = self.pbx_core.phone_book.remove_entry(extension)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Phone book entry deleted: {extension}'
                })
            else:
                self._send_json({'error': 'Failed to delete phone book entry'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_sync_phone_book(self):
        """Sync phone book from Active Directory"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'phone_book'):
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        if not self.pbx_core.phone_book or not self.pbx_core.phone_book.enabled:
            self._send_json({'error': 'Phone book feature not enabled'}, 500)
            return
        
        if not hasattr(self.pbx_core, 'ad_integration') or not self.pbx_core.ad_integration:
            self._send_json({'error': 'Active Directory integration not enabled'}, 500)
            return
        
        try:
            synced_count = self.pbx_core.phone_book.sync_from_ad(
                self.pbx_core.ad_integration,
                self.pbx_core.extension_registry
            )
            
            self._send_json({
                'success': True,
                'message': f'Phone book synced from Active Directory',
                'synced_count': synced_count
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    # Paging System API handlers
    def _handle_get_paging_zones(self):
        """Get all paging zones"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'paging_system'):
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        try:
            zones = self.pbx_core.paging_system.get_zones()
            self._send_json(zones)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_paging_devices(self):
        """Get all paging DAC devices"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'paging_system'):
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        try:
            devices = self.pbx_core.paging_system.get_dac_devices()
            self._send_json(devices)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_active_pages(self):
        """Get all active paging sessions"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'paging_system'):
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        try:
            active_pages = self.pbx_core.paging_system.get_active_pages()
            self._send_json(active_pages)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_add_paging_zone(self):
        """Add a paging zone"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'paging_system'):
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        try:
            data = self._get_body()
            extension = data.get('extension')
            name = data.get('name')
            
            if not extension or not name:
                self._send_json({'error': 'Extension and name are required'}, 400)
                return
            
            success = self.pbx_core.paging_system.add_zone(
                extension=extension,
                name=name,
                description=data.get('description'),
                dac_device=data.get('dac_device')
            )
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Paging zone added: {extension}'
                })
            else:
                self._send_json({'error': 'Failed to add paging zone'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_delete_paging_zone(self, extension: str):
        """Delete a paging zone"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'paging_system'):
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        try:
            success = self.pbx_core.paging_system.remove_zone(extension)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Paging zone deleted: {extension}'
                })
            else:
                self._send_json({'error': 'Failed to delete paging zone'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_configure_paging_device(self):
        """Configure a paging DAC device"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'paging_system'):
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        if not self.pbx_core.paging_system or not self.pbx_core.paging_system.enabled:
            self._send_json({'error': 'Paging system not enabled'}, 500)
            return
        
        try:
            data = self._get_body()
            device_id = data.get('device_id')
            device_type = data.get('device_type')
            
            if not device_id or not device_type:
                self._send_json({'error': 'device_id and device_type are required'}, 400)
                return
            
            success = self.pbx_core.paging_system.configure_dac_device(
                device_id=device_id,
                device_type=device_type,
                sip_uri=data.get('sip_uri'),
                ip_address=data.get('ip_address'),
                port=data.get('port', 5060)
            )
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'DAC device configured: {device_id}'
                })
            else:
                self._send_json({'error': 'Failed to configure DAC device'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_webhooks(self):
        """Get all webhook subscriptions"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webhook_system'):
            self._send_json({'error': 'Webhook system not available'}, 500)
            return
        
        try:
            subscriptions = self.pbx_core.webhook_system.get_subscriptions()
            self._send_json(subscriptions)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_add_webhook(self):
        """Add a webhook subscription"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webhook_system'):
            self._send_json({'error': 'Webhook system not available'}, 500)
            return
        
        try:
            data = self._get_body()
            url = data.get('url')
            events = data.get('events', ['*'])
            secret = data.get('secret')
            headers = data.get('headers')
            
            if not url:
                self._send_json({'error': 'URL is required'}, 400)
                return
            
            subscription = self.pbx_core.webhook_system.add_subscription(
                url=url,
                events=events,
                secret=secret,
                headers=headers
            )
            
            self._send_json({
                'success': True,
                'message': f'Webhook subscription added: {url}',
                'subscription': {
                    'url': subscription.url,
                    'events': subscription.events,
                    'enabled': subscription.enabled
                }
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_delete_webhook(self, url: str):
        """Delete a webhook subscription"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webhook_system'):
            self._send_json({'error': 'Webhook system not available'}, 500)
            return
        
        try:
            success = self.pbx_core.webhook_system.remove_subscription(url)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Webhook subscription deleted: {url}'
                })
            else:
                self._send_json({'error': 'Webhook subscription not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    # ========== WebRTC Handlers ==========
    
    def _handle_create_webrtc_session(self):
        """Create a new WebRTC session"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_signaling'):
            self._send_json({'error': 'WebRTC not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension = data.get('extension')
            
            if not extension:
                self._send_json({'error': 'Extension is required'}, 400)
                return
            
            # Verify extension exists
            if not self.pbx_core.extension_registry.get_extension(extension):
                self._send_json({'error': 'Extension not found'}, 404)
                return
            
            session = self.pbx_core.webrtc_signaling.create_session(extension)
            
            self._send_json({
                'success': True,
                'session': session.to_dict(),
                'ice_servers': self.pbx_core.webrtc_signaling.get_ice_servers_config()
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_webrtc_offer(self):
        """Handle WebRTC SDP offer"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_signaling'):
            self._send_json({'error': 'WebRTC not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            session_id = data.get('session_id')
            sdp = data.get('sdp')
            
            if not session_id or not sdp:
                self._send_json({'error': 'session_id and sdp are required'}, 400)
                return
            
            success = self.pbx_core.webrtc_signaling.handle_offer(session_id, sdp)
            
            if success:
                self._send_json({'success': True, 'message': 'Offer received'})
            else:
                self._send_json({'error': 'Session not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_webrtc_answer(self):
        """Handle WebRTC SDP answer"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_signaling'):
            self._send_json({'error': 'WebRTC not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            session_id = data.get('session_id')
            sdp = data.get('sdp')
            
            if not session_id or not sdp:
                self._send_json({'error': 'session_id and sdp are required'}, 400)
                return
            
            success = self.pbx_core.webrtc_signaling.handle_answer(session_id, sdp)
            
            if success:
                self._send_json({'success': True, 'message': 'Answer received'})
            else:
                self._send_json({'error': 'Session not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_webrtc_ice_candidate(self):
        """Handle WebRTC ICE candidate"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_signaling'):
            self._send_json({'error': 'WebRTC not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            session_id = data.get('session_id')
            candidate = data.get('candidate')
            
            if not session_id or not candidate:
                self._send_json({'error': 'session_id and candidate are required'}, 400)
                return
            
            success = self.pbx_core.webrtc_signaling.add_ice_candidate(session_id, candidate)
            
            if success:
                self._send_json({'success': True, 'message': 'ICE candidate added'})
            else:
                self._send_json({'error': 'Session not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_webrtc_call(self):
        """Initiate a call from WebRTC client"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_gateway'):
            self._send_json({'error': 'WebRTC gateway not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            session_id = data.get('session_id')
            target_extension = data.get('target_extension')
            
            if not session_id or not target_extension:
                self._send_json({'error': 'session_id and target_extension are required'}, 400)
                return
            
            call_id = self.pbx_core.webrtc_gateway.initiate_call(session_id, target_extension)
            
            if call_id:
                self._send_json({
                    'success': True,
                    'call_id': call_id,
                    'message': f'Call initiated to {target_extension}'
                })
            else:
                self._send_json({'error': 'Failed to initiate call'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_webrtc_sessions(self):
        """Get all WebRTC sessions"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_signaling'):
            self._send_json({'error': 'WebRTC not available'}, 500)
            return
        
        try:
            sessions = self.pbx_core.webrtc_signaling.get_sessions_info()
            self._send_json(sessions)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_webrtc_session(self, path: str):
        """Get specific WebRTC session"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_signaling'):
            self._send_json({'error': 'WebRTC not available'}, 500)
            return
        
        try:
            session_id = path.split('/')[-1]
            session = self.pbx_core.webrtc_signaling.get_session(session_id)
            
            if session:
                self._send_json(session.to_dict())
            else:
                self._send_json({'error': 'Session not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_ice_servers(self):
        """Get ICE servers configuration"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'webrtc_signaling'):
            self._send_json({'error': 'WebRTC not available'}, 500)
            return
        
        try:
            config = self.pbx_core.webrtc_signaling.get_ice_servers_config()
            self._send_json(config)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    # ========== CRM Integration Handlers ==========
    
    def _handle_crm_lookup(self):
        """Look up caller information"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'crm_integration'):
            self._send_json({'error': 'CRM integration not available'}, 500)
            return
        
        try:
            # Get phone number from query string
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            phone_number = query_params.get('phone', [None])[0]
            
            if not phone_number:
                self._send_json({'error': 'phone parameter is required'}, 400)
                return
            
            # Look up caller info
            caller_info = self.pbx_core.crm_integration.lookup_caller(phone_number)
            
            if caller_info:
                self._send_json({
                    'found': True,
                    'caller_info': caller_info.to_dict()
                })
            else:
                self._send_json({
                    'found': False,
                    'message': 'Caller not found'
                })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_crm_providers(self):
        """Get CRM provider status"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'crm_integration'):
            self._send_json({'error': 'CRM integration not available'}, 500)
            return
        
        try:
            providers = self.pbx_core.crm_integration.get_provider_status()
            self._send_json({
                'enabled': self.pbx_core.crm_integration.enabled,
                'providers': providers
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_trigger_screen_pop(self):
        """Trigger screen pop for a call"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'crm_integration'):
            self._send_json({'error': 'CRM integration not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            phone_number = data.get('phone_number')
            call_id = data.get('call_id')
            extension = data.get('extension')
            
            if not all([phone_number, call_id, extension]):
                self._send_json({'error': 'phone_number, call_id, and extension are required'}, 400)
                return
            
            self.pbx_core.crm_integration.trigger_screen_pop(phone_number, call_id, extension)
            
            self._send_json({
                'success': True,
                'message': 'Screen pop triggered'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    # ========== Hot-Desking Handlers ==========
    
    def _handle_hot_desk_login(self):
        """Handle hot-desk login"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'hot_desking'):
            self._send_json({'error': 'Hot-desking not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension = data.get('extension')
            device_id = data.get('device_id')
            ip_address = data.get('ip_address', self.client_address[0])
            pin = data.get('pin')
            
            if not all([extension, device_id]):
                self._send_json({'error': 'extension and device_id are required'}, 400)
                return
            
            success = self.pbx_core.hot_desking.login(extension, device_id, ip_address, pin)
            
            if success:
                profile = self.pbx_core.hot_desking.get_extension_profile(extension)
                self._send_json({
                    'success': True,
                    'message': f'Extension {extension} logged in',
                    'profile': profile
                })
            else:
                self._send_json({'error': 'Login failed'}, 401)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_hot_desk_logout(self):
        """Handle hot-desk logout"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'hot_desking'):
            self._send_json({'error': 'Hot-desking not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            device_id = data.get('device_id')
            extension = data.get('extension')  # Optional: logout specific extension
            
            if device_id:
                success = self.pbx_core.hot_desking.logout(device_id)
                if success:
                    self._send_json({
                        'success': True,
                        'message': f'Logged out from device {device_id}'
                    })
                else:
                    self._send_json({'error': 'No active session for device'}, 404)
            elif extension:
                count = self.pbx_core.hot_desking.logout_extension(extension)
                self._send_json({
                    'success': True,
                    'message': f'Extension {extension} logged out from {count} device(s)'
                })
            else:
                self._send_json({'error': 'device_id or extension is required'}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_mfa_enroll(self):
        """Handle MFA enrollment"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension_number = data.get('extension')
            
            if not extension_number:
                self._send_json({'error': 'extension is required'}, 400)
                return
            
            success, provisioning_uri, backup_codes = self.pbx_core.mfa_manager.enroll_user(extension_number)
            
            if success:
                self._send_json({
                    'success': True,
                    'provisioning_uri': provisioning_uri,
                    'backup_codes': backup_codes,
                    'message': 'MFA enrollment initiated. Scan QR code and verify with first code.'
                })
            else:
                self._send_json({'error': 'MFA enrollment failed'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_mfa_verify_enrollment(self):
        """Handle MFA enrollment verification"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension_number = data.get('extension')
            code = data.get('code')
            
            if not extension_number or not code:
                self._send_json({'error': 'extension and code are required'}, 400)
                return
            
            success = self.pbx_core.mfa_manager.verify_enrollment(extension_number, code)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': 'MFA successfully activated'
                })
            else:
                self._send_json({'error': 'Invalid code'}, 401)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_mfa_verify(self):
        """Handle MFA code verification"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension_number = data.get('extension')
            code = data.get('code')
            
            if not extension_number or not code:
                self._send_json({'error': 'extension and code are required'}, 400)
                return
            
            success = self.pbx_core.mfa_manager.verify_code(extension_number, code)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': 'MFA verification successful'
                })
            else:
                self._send_json({'error': 'Invalid code'}, 401)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_mfa_disable(self):
        """Handle MFA disable"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension_number = data.get('extension')
            
            if not extension_number:
                self._send_json({'error': 'extension is required'}, 400)
                return
            
            success = self.pbx_core.mfa_manager.disable_for_user(extension_number)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': 'MFA disabled successfully'
                })
            else:
                self._send_json({'error': 'Failed to disable MFA'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_mfa_enroll_yubikey(self):
        """Handle YubiKey enrollment"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension_number = data.get('extension')
            otp = data.get('otp')
            device_name = data.get('device_name', 'YubiKey')
            
            if not extension_number or not otp:
                self._send_json({'error': 'extension and otp are required'}, 400)
                return
            
            success, error = self.pbx_core.mfa_manager.enroll_yubikey(extension_number, otp, device_name)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': 'YubiKey enrolled successfully'
                })
            else:
                self._send_json({'error': error or 'YubiKey enrollment failed'}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_mfa_enroll_fido2(self):
        """Handle FIDO2/WebAuthn credential enrollment"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension_number = data.get('extension')
            credential_data = data.get('credential_data')
            device_name = data.get('device_name', 'Security Key')
            
            if not extension_number or not credential_data:
                self._send_json({'error': 'extension and credential_data are required'}, 400)
                return
            
            success, error = self.pbx_core.mfa_manager.enroll_fido2(extension_number, credential_data, device_name)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': 'FIDO2 credential enrolled successfully'
                })
            else:
                self._send_json({'error': error or 'FIDO2 enrollment failed'}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_mfa_methods(self, path: str):
        """Get enrolled MFA methods for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            extension = path.split('/')[-1]
            methods = self.pbx_core.mfa_manager.get_enrolled_methods(extension)
            
            self._send_json({
                'extension': extension,
                'methods': methods
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_mfa_status(self, path: str):
        """Get MFA status for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'mfa_manager'):
            self._send_json({'error': 'MFA not available'}, 500)
            return
        
        try:
            extension = path.split('/')[-1]
            enabled = self.pbx_core.mfa_manager.is_enabled_for_user(extension)
            
            self._send_json({
                'extension': extension,
                'mfa_enabled': enabled,
                'mfa_required': self.pbx_core.mfa_manager.required
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_block_ip(self):
        """Handle IP blocking"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'threat_detector'):
            self._send_json({'error': 'Threat detection not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            ip_address = data.get('ip_address')
            reason = data.get('reason', 'Manual block')
            duration = data.get('duration')  # Optional, in seconds
            
            if not ip_address:
                self._send_json({'error': 'ip_address is required'}, 400)
                return
            
            self.pbx_core.threat_detector.block_ip(ip_address, reason, duration)
            
            self._send_json({
                'success': True,
                'message': f'IP {ip_address} blocked successfully'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_unblock_ip(self):
        """Handle IP unblocking"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'threat_detector'):
            self._send_json({'error': 'Threat detection not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            ip_address = data.get('ip_address')
            
            if not ip_address:
                self._send_json({'error': 'ip_address is required'}, 400)
                return
            
            self.pbx_core.threat_detector.unblock_ip(ip_address)
            
            self._send_json({
                'success': True,
                'message': f'IP {ip_address} unblocked successfully'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_threat_summary(self):
        """Get threat detection summary"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'threat_detector'):
            self._send_json({'error': 'Threat detection not available'}, 500)
            return
        
        try:
            # Get hours parameter from query string
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            hours = int(params.get('hours', [24])[0])
            
            summary = self.pbx_core.threat_detector.get_threat_summary(hours)
            
            self._send_json(summary)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_check_ip(self, path: str):
        """Check if IP is blocked"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'threat_detector'):
            self._send_json({'error': 'Threat detection not available'}, 500)
            return
        
        try:
            ip_address = path.split('/')[-1]
            is_blocked, reason = self.pbx_core.threat_detector.is_ip_blocked(ip_address)
            
            self._send_json({
                'ip_address': ip_address,
                'is_blocked': is_blocked,
                'reason': reason
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_add_dnd_rule(self):
        """Handle adding DND rule"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'dnd_scheduler'):
            self._send_json({'error': 'DND Scheduler not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension = data.get('extension')
            rule_type = data.get('rule_type')  # 'calendar' or 'time_based'
            config = data.get('config', {})
            
            if not extension or not rule_type:
                self._send_json({'error': 'extension and rule_type are required'}, 400)
                return
            
            rule_id = self.pbx_core.dnd_scheduler.add_rule(extension, rule_type, config)
            
            self._send_json({
                'success': True,
                'rule_id': rule_id,
                'message': 'DND rule added successfully'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_delete_dnd_rule(self, rule_id: str):
        """Handle deleting DND rule"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'dnd_scheduler'):
            self._send_json({'error': 'DND Scheduler not available'}, 500)
            return
        
        try:
            success = self.pbx_core.dnd_scheduler.remove_rule(rule_id)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': 'DND rule deleted successfully'
                })
            else:
                self._send_json({'error': 'Rule not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_register_calendar_user(self):
        """Handle registering user for calendar-based DND"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'dnd_scheduler'):
            self._send_json({'error': 'DND Scheduler not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension = data.get('extension')
            email = data.get('email')
            
            if not extension or not email:
                self._send_json({'error': 'extension and email are required'}, 400)
                return
            
            self.pbx_core.dnd_scheduler.register_calendar_user(extension, email)
            
            self._send_json({
                'success': True,
                'message': f'Calendar monitoring registered for {extension}'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_dnd_override(self):
        """Handle manual DND override"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'dnd_scheduler'):
            self._send_json({'error': 'DND Scheduler not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            extension = data.get('extension')
            status = data.get('status')  # e.g., 'do_not_disturb', 'available'
            duration_minutes = data.get('duration_minutes')  # Optional
            
            if not extension or not status:
                self._send_json({'error': 'extension and status are required'}, 400)
                return
            
            # Convert status string to PresenceStatus enum
            from pbx.features.presence import PresenceStatus
            try:
                status_enum = PresenceStatus(status)
            except ValueError:
                self._send_json({'error': f'Invalid status: {status}'}, 400)
                return
            
            self.pbx_core.dnd_scheduler.set_manual_override(extension, status_enum, duration_minutes)
            
            self._send_json({
                'success': True,
                'message': f'Manual override set for {extension}'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_clear_dnd_override(self, extension: str):
        """Handle clearing DND override"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'dnd_scheduler'):
            self._send_json({'error': 'DND Scheduler not available'}, 500)
            return
        
        try:
            self.pbx_core.dnd_scheduler.clear_manual_override(extension)
            
            self._send_json({
                'success': True,
                'message': f'Override cleared for {extension}'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_dnd_status(self, path: str):
        """Get DND status for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'dnd_scheduler'):
            self._send_json({'error': 'DND Scheduler not available'}, 500)
            return
        
        try:
            extension = path.split('/')[-1]
            status = self.pbx_core.dnd_scheduler.get_status(extension)
            
            self._send_json(status)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_dnd_rules(self, path: str):
        """Get DND rules for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'dnd_scheduler'):
            self._send_json({'error': 'DND Scheduler not available'}, 500)
            return
        
        try:
            extension = path.split('/')[-1]
            rules = self.pbx_core.dnd_scheduler.get_rules(extension)
            
            self._send_json({
                'extension': extension,
                'rules': rules
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_add_skill(self):
        """Handle adding a new skill"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'skills_router'):
            self._send_json({'error': 'Skills routing not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            skill_id = data.get('skill_id')
            name = data.get('name')
            description = data.get('description', '')
            
            if not skill_id or not name:
                self._send_json({'error': 'skill_id and name are required'}, 400)
                return
            
            success = self.pbx_core.skills_router.add_skill(skill_id, name, description)
            
            if success:
                self._send_json({
                    'success': True,
                    'skill_id': skill_id,
                    'message': 'Skill added successfully'
                })
            else:
                self._send_json({'error': 'Skill already exists'}, 409)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_assign_skill(self):
        """Handle assigning skill to agent"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'skills_router'):
            self._send_json({'error': 'Skills routing not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            agent_extension = data.get('agent_extension')
            skill_id = data.get('skill_id')
            proficiency = data.get('proficiency', 5)
            
            if not agent_extension or not skill_id:
                self._send_json({'error': 'agent_extension and skill_id are required'}, 400)
                return
            
            success = self.pbx_core.skills_router.assign_skill_to_agent(agent_extension, skill_id, proficiency)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Skill assigned to agent {agent_extension}'
                })
            else:
                self._send_json({'error': 'Failed to assign skill'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_remove_skill_from_agent(self, agent_extension: str, skill_id: str):
        """Handle removing skill from agent"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'skills_router'):
            self._send_json({'error': 'Skills routing not available'}, 500)
            return
        
        try:
            success = self.pbx_core.skills_router.remove_skill_from_agent(agent_extension, skill_id)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Skill removed from agent {agent_extension}'
                })
            else:
                self._send_json({'error': 'Skill not found for agent'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_set_queue_requirements(self):
        """Handle setting queue skill requirements"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'skills_router'):
            self._send_json({'error': 'Skills routing not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            queue_number = data.get('queue_number')
            requirements = data.get('requirements', [])
            
            if not queue_number:
                self._send_json({'error': 'queue_number is required'}, 400)
                return
            
            success = self.pbx_core.skills_router.set_queue_requirements(queue_number, requirements)
            
            if success:
                self._send_json({
                    'success': True,
                    'message': f'Requirements set for queue {queue_number}'
                })
            else:
                self._send_json({'error': 'Failed to set requirements'}, 500)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_clear_qos_alerts(self):
        """Handle clearing QoS alerts"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'qos_monitor'):
            self._send_json({'error': 'QoS monitoring not available'}, 500)
            return
        
        try:
            count = self.pbx_core.qos_monitor.clear_alerts()
            self._send_json({
                'success': True,
                'message': f'Cleared {count} alerts'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_update_qos_thresholds(self):
        """Handle updating QoS alert thresholds"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'qos_monitor'):
            self._send_json({'error': 'QoS monitoring not available'}, 500)
            return
        
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            thresholds = {}
            
            # Validate and convert threshold values with range checking
            if 'mos_min' in data:
                mos_min = float(data['mos_min'])
                if mos_min < 1.0 or mos_min > 5.0:
                    self._send_json({'error': 'mos_min must be between 1.0 and 5.0'}, 400)
                    return
                thresholds['mos_min'] = mos_min
            
            if 'packet_loss_max' in data:
                packet_loss_max = float(data['packet_loss_max'])
                if packet_loss_max < 0.0 or packet_loss_max > 100.0:
                    self._send_json({'error': 'packet_loss_max must be between 0.0 and 100.0'}, 400)
                    return
                thresholds['packet_loss_max'] = packet_loss_max
            
            if 'jitter_max' in data:
                jitter_max = float(data['jitter_max'])
                if jitter_max < 0.0 or jitter_max > 1000.0:
                    self._send_json({'error': 'jitter_max must be between 0.0 and 1000.0 ms'}, 400)
                    return
                thresholds['jitter_max'] = jitter_max
            
            if 'latency_max' in data:
                latency_max = float(data['latency_max'])
                if latency_max < 0.0 or latency_max > 5000.0:
                    self._send_json({'error': 'latency_max must be between 0.0 and 5000.0 ms'}, 400)
                    return
                thresholds['latency_max'] = latency_max
            
            if not thresholds:
                self._send_json({'error': 'No valid threshold parameters provided'}, 400)
                return
            
            self.pbx_core.qos_monitor.update_alert_thresholds(thresholds)
            
            self._send_json({
                'success': True,
                'message': 'QoS thresholds updated',
                'thresholds': self.pbx_core.qos_monitor.alert_thresholds
            })
        except ValueError as e:
            self.logger.error(f"Invalid threshold value: {e}")
            self._send_json({'error': 'Invalid threshold values, must be valid numbers'}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_all_skills(self):
        """Get all skills"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'skills_router'):
            self._send_json({'error': 'Skills routing not available'}, 500)
            return
        
        try:
            skills = self.pbx_core.skills_router.get_all_skills()
            self._send_json({'skills': skills})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_agent_skills(self, path: str):
        """Get agent skills"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'skills_router'):
            self._send_json({'error': 'Skills routing not available'}, 500)
            return
        
        try:
            agent_extension = path.split('/')[-1]
            skills = self.pbx_core.skills_router.get_agent_skills(agent_extension)
            
            self._send_json({
                'agent_extension': agent_extension,
                'skills': skills
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_queue_requirements(self, path: str):
        """Get queue skill requirements"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'skills_router'):
            self._send_json({'error': 'Skills routing not available'}, 500)
            return
        
        try:
            queue_number = path.split('/')[-1]
            requirements = self.pbx_core.skills_router.get_queue_requirements(queue_number)
            
            self._send_json({
                'queue_number': queue_number,
                'requirements': requirements
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_hot_desk_sessions(self):
        """Get all hot-desk sessions"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'hot_desking'):
            self._send_json({'error': 'Hot-desking not available'}, 500)
            return
        
        try:
            sessions = self.pbx_core.hot_desking.get_active_sessions()
            self._send_json({
                'count': len(sessions),
                'sessions': sessions
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_hot_desk_session(self, path: str):
        """Get specific hot-desk session by device"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'hot_desking'):
            self._send_json({'error': 'Hot-desking not available'}, 500)
            return
        
        try:
            device_id = path.split('/')[-1]
            session = self.pbx_core.hot_desking.get_session(device_id)
            
            if session:
                self._send_json(session.to_dict())
            else:
                self._send_json({'error': 'No session found for device'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_hot_desk_extension(self, path: str):
        """Get hot-desk information for extension"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'hot_desking'):
            self._send_json({'error': 'Hot-desking not available'}, 500)
            return
        
        try:
            extension = path.split('/')[-1]
            devices = self.pbx_core.hot_desking.get_extension_devices(extension)
            sessions = []
            
            for device_id in devices:
                session = self.pbx_core.hot_desking.get_session(device_id)
                if session:
                    sessions.append(session.to_dict())
            
            self._send_json({
                'extension': extension,
                'logged_in': len(sessions) > 0,
                'device_count': len(devices),
                'sessions': sessions
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    # ========== Auto Attendant Management Handlers ==========
    
    def _handle_get_auto_attendant_config(self):
        """Get auto attendant configuration"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'auto_attendant'):
            self._send_json({'error': 'Auto attendant not available'}, 500)
            return
        
        try:
            aa = self.pbx_core.auto_attendant
            config = {
                'enabled': aa.enabled,
                'extension': aa.extension,
                'timeout': aa.timeout,
                'max_retries': aa.max_retries,
                'audio_path': aa.audio_path
            }
            self._send_json(config)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_update_auto_attendant_config(self):
        """Update auto attendant configuration"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'auto_attendant'):
            self._send_json({'error': 'Auto attendant not available'}, 500)
            return
        
        try:
            data = self._get_body()
            aa = self.pbx_core.auto_attendant
            
            # Update configuration
            config_changed = False
            if 'enabled' in data:
                aa.enabled = bool(data['enabled'])
                config_changed = True
            if 'extension' in data:
                aa.extension = str(data['extension'])
                config_changed = True
            if 'timeout' in data:
                aa.timeout = int(data['timeout'])
                config_changed = True
            if 'max_retries' in data:
                aa.max_retries = int(data['max_retries'])
                config_changed = True
            
            # Check if prompts configuration was updated
            prompts_updated = 'prompts' in data
            
            # Trigger voice regeneration if prompts or menu options changed
            if prompts_updated or config_changed:
                try:
                    self._regenerate_voice_prompts(data.get('prompts', {}))
                except Exception as e:
                    self.logger.warning(f"Failed to regenerate voice prompts: {e}")
            
            self._send_json({
                'success': True,
                'message': 'Auto attendant configuration updated successfully'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_auto_attendant_menu_options(self):
        """Get auto attendant menu options"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'auto_attendant'):
            self._send_json({'error': 'Auto attendant not available'}, 500)
            return
        
        try:
            aa = self.pbx_core.auto_attendant
            options = []
            for digit, option in aa.menu_options.items():
                options.append({
                    'digit': digit,
                    'destination': option['destination'],
                    'description': option['description']
                })
            self._send_json({'menu_options': options})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_add_auto_attendant_menu_option(self):
        """Add auto attendant menu option"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'auto_attendant'):
            self._send_json({'error': 'Auto attendant not available'}, 500)
            return
        
        try:
            data = self._get_body()
            digit = str(data.get('digit'))
            destination = data.get('destination')
            description = data.get('description', '')
            
            if not digit or not destination:
                self._send_json({'error': 'digit and destination are required'}, 400)
                return
            
            aa = self.pbx_core.auto_attendant
            aa.menu_options[digit] = {
                'destination': destination,
                'description': description
            }
            
            # Trigger voice regeneration after menu option addition
            try:
                self._regenerate_voice_prompts({})
            except Exception as e:
                self.logger.warning(f"Failed to regenerate voice prompts: {e}")
            
            self._send_json({
                'success': True,
                'message': f'Menu option {digit} added successfully'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_update_auto_attendant_menu_option(self, path: str):
        """Update auto attendant menu option"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'auto_attendant'):
            self._send_json({'error': 'Auto attendant not available'}, 500)
            return
        
        try:
            digit = path.split('/')[-1]
            data = self._get_body()
            
            aa = self.pbx_core.auto_attendant
            if digit not in aa.menu_options:
                self._send_json({'error': f'Menu option {digit} not found'}, 404)
                return
            
            if 'destination' in data:
                aa.menu_options[digit]['destination'] = data['destination']
            if 'description' in data:
                aa.menu_options[digit]['description'] = data['description']
            
            # Trigger voice regeneration after menu option update
            try:
                self._regenerate_voice_prompts({})
            except Exception as e:
                self.logger.warning(f"Failed to regenerate voice prompts: {e}")
            
            self._send_json({
                'success': True,
                'message': f'Menu option {digit} updated successfully'
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_delete_auto_attendant_menu_option(self, digit: str):
        """Delete auto attendant menu option"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'auto_attendant'):
            self._send_json({'error': 'Auto attendant not available'}, 500)
            return
        
        try:
            aa = self.pbx_core.auto_attendant
            if digit in aa.menu_options:
                del aa.menu_options[digit]
                # Trigger voice regeneration after menu option deletion
                try:
                    self._regenerate_voice_prompts({})
                except Exception as e:
                    self.logger.warning(f"Failed to regenerate voice prompts: {e}")
                
                self._send_json({
                    'success': True,
                    'message': f'Menu option {digit} deleted successfully'
                })
            else:
                self._send_json({'error': f'Menu option {digit} not found'}, 404)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_auto_attendant_prompts(self):
        """Get auto attendant prompt texts"""
        try:
            # Return current prompt configuration
            config = self.pbx_core.config if self.pbx_core else Config()
            aa_config = config.get('auto_attendant', {})
            
            prompts = aa_config.get('prompts', {
                'welcome': 'Thank you for calling {company_name}.',
                'main_menu': 'For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.',
                'invalid': 'That is not a valid option. Please try again.',
                'timeout': 'We did not receive your selection. Please try again.',
                'transferring': 'Please hold while we transfer your call.'
            })
            
            company_name = config.get('company_name', 'your company')
            
            self._send_json({
                'prompts': prompts,
                'company_name': company_name
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_update_auto_attendant_prompts(self):
        """Update auto attendant prompt texts and regenerate voices"""
        try:
            data = self._get_body()
            prompts = data.get('prompts', {})
            company_name = data.get('company_name')
            
            # Update configuration
            config = self.pbx_core.config if self.pbx_core else Config()
            
            # Ensure auto_attendant section exists
            if 'auto_attendant' not in config.config:
                config.config['auto_attendant'] = {}
            
            # Update prompts
            if prompts:
                config.config['auto_attendant']['prompts'] = prompts
            
            # Update company name
            if company_name:
                config.config['company_name'] = company_name
            
            # Save configuration
            success = config.save()
            if not success:
                raise Exception("Failed to save configuration file")
            
            # Trigger voice regeneration
            self._regenerate_voice_prompts(prompts, company_name)
            
            self._send_json({
                'success': True,
                'message': 'Prompts updated and voices regenerated successfully'
            })
        except Exception as e:
            self.logger.error(f"Error updating prompts: {e}")
            self._send_json({'error': str(e)}, 500)
    
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
                    f"TTS dependencies not available. Install with: {get_tts_requirements()}"
                )
            
            # Get configuration
            config = self.pbx_core.config if self.pbx_core else Config()
            aa_config = config.get('auto_attendant', {})
            
            if not company_name:
                company_name = config.get('company_name', 'your company')
            
            # Get prompt texts
            default_prompts = {
                'welcome': f'Thank you for calling {company_name}.',
                'main_menu': 'For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.',
                'invalid': 'That is not a valid option. Please try again.',
                'timeout': 'We did not receive your selection. Please try again.',
                'transferring': 'Please hold while we transfer your call.'
            }
            
            # Merge custom prompts
            prompts = {**default_prompts}
            if custom_prompts:
                prompts.update(custom_prompts)
            
            # Get output directory
            audio_path = aa_config.get('audio_path', 'auto_attendant')
            if not os.path.exists(audio_path):
                os.makedirs(audio_path)
            
            # Generate each prompt using shared TTS utility
            self.logger.info("Regenerating voice prompts using gTTS...")
            for filename, text in prompts.items():
                output_file = os.path.join(audio_path, f'{filename}.wav')
                
                try:
                    # Use shared utility function for TTS generation
                    if text_to_wav_telephony(text, output_file, language='en', tld='com', slow=False):
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
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail system not available'}, 500)
            return
        
        try:
            vm_system = self.pbx_core.voicemail_system
            boxes = []
            
            for extension, mailbox in vm_system.mailboxes.items():
                messages = mailbox.get_messages(unread_only=False)
                unread_count = len(mailbox.get_messages(unread_only=True))
                
                boxes.append({
                    'extension': extension,
                    'total_messages': len(messages),
                    'unread_messages': unread_count,
                    'has_custom_greeting': mailbox.has_custom_greeting(),
                    'storage_path': mailbox.storage_path
                })
            
            self._send_json({'voicemail_boxes': boxes})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_voicemail_box_details(self, path: str):
        """Get details of a specific voicemail box"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail system not available'}, 500)
            return
        
        try:
            # Extract extension from path, handling /export suffix
            parts = path.split('/')
            extension = parts[3] if len(parts) > 3 else None
            
            if not extension:
                self._send_json({'error': 'Invalid path'}, 400)
                return
            
            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            messages = mailbox.get_messages(unread_only=False)
            
            details = {
                'extension': extension,
                'total_messages': len(messages),
                'unread_messages': len(mailbox.get_messages(unread_only=True)),
                'has_custom_greeting': mailbox.has_custom_greeting(),
                'storage_path': mailbox.storage_path,
                'messages': []
            }
            
            for msg in messages:
                details['messages'].append({
                    'id': msg['id'],
                    'caller_id': msg['caller_id'],
                    'timestamp': msg['timestamp'].isoformat() if hasattr(msg['timestamp'], 'isoformat') else str(msg['timestamp']),
                    'listened': msg['listened'],
                    'duration': msg.get('duration'),
                    'file_path': msg['file_path']
                })
            
            self._send_json(details)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_export_voicemail_box(self, path: str):
        """Export all voicemails from a mailbox as a ZIP file"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail system not available'}, 500)
            return
        
        try:
            # Extract extension from path: /api/voicemail-boxes/{extension}/export
            parts = path.split('/')
            extension = parts[3] if len(parts) > 3 else None
            
            if not extension:
                self._send_json({'error': 'Invalid path'}, 400)
                return
            
            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            messages = mailbox.get_messages(unread_only=False)
            
            if not messages:
                self._send_json({'error': 'No messages to export'}, 404)
                return
            
            # Create temporary directory for ZIP creation
            temp_dir = tempfile.mkdtemp()
            zip_filename = f"voicemail_{extension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add a manifest file with message details
                    manifest_lines = ['Voicemail Export Manifest\n']
                    manifest_lines.append(f'Extension: {extension}\n')
                    manifest_lines.append(f'Export Date: {datetime.now().isoformat()}\n')
                    manifest_lines.append(f'Total Messages: {len(messages)}\n\n')
                    manifest_lines.append('Message Details:\n')
                    manifest_lines.append('-' * 80 + '\n')
                    
                    for msg in messages:
                        # Add audio file to ZIP
                        if os.path.exists(msg['file_path']):
                            arcname = os.path.basename(msg['file_path'])
                            zipf.write(msg['file_path'], arcname)
                            
                            # Add to manifest
                            manifest_lines.append(f"\nFile: {arcname}\n")
                            manifest_lines.append(f"Caller ID: {msg['caller_id']}\n")
                            manifest_lines.append(f"Timestamp: {msg['timestamp']}\n")
                            manifest_lines.append(f"Duration: {msg.get('duration', 'Unknown')}s\n")
                            manifest_lines.append(f"Status: {'Read' if msg['listened'] else 'Unread'}\n")
                    
                    # Add manifest to ZIP
                    zipf.writestr('MANIFEST.txt', ''.join(manifest_lines))
                
                # Read ZIP file content
                with open(zip_path, 'rb') as f:
                    zip_content = f.read()
                
                # Send ZIP file as response
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header('Content-Disposition', f'attachment; filename="{zip_filename}"')
                self.send_header('Content-Length', str(len(zip_content)))
                self.end_headers()
                self.wfile.write(zip_content)
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting voicemail box: {e}")
            self._send_json({'error': str(e)}, 500)
    
    def _handle_clear_voicemail_box(self, path: str):
        """Clear all messages from a voicemail box"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail system not available'}, 500)
            return
        
        try:
            # Extract extension from path: /api/voicemail-boxes/{extension}/clear
            parts = path.split('/')
            extension = parts[3] if len(parts) > 3 else None
            
            if not extension:
                self._send_json({'error': 'Invalid path'}, 400)
                return
            
            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            messages = mailbox.get_messages(unread_only=False)
            
            deleted_count = 0
            for msg in messages[:]:  # Create a copy to iterate over
                if mailbox.delete_message(msg['id']):
                    deleted_count += 1
            
            self._send_json({
                'success': True,
                'message': f'Cleared {deleted_count} voicemail message(s) from extension {extension}',
                'deleted_count': deleted_count
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_get_voicemail_greeting(self, path: str):
        """Get custom voicemail greeting"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail system not available'}, 500)
            return
        
        try:
            # Extract extension from path
            parts = path.split('/')
            extension = parts[3] if len(parts) > 3 else None
            
            if not extension:
                self._send_json({'error': 'Invalid path'}, 400)
                return
            
            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            greeting_path = mailbox.get_greeting_path()
            
            if not greeting_path or not os.path.exists(greeting_path):
                self._send_json({'error': 'No custom greeting found'}, 404)
                return
            
            # Serve greeting file
            with open(greeting_path, 'rb') as f:
                greeting_data = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Content-Disposition', f'attachment; filename="greeting_{extension}.wav"')
            self.send_header('Content-Length', str(len(greeting_data)))
            self.end_headers()
            self.wfile.write(greeting_data)
            
        except Exception as e:
            self.logger.error(f"Error getting voicemail greeting: {e}")
            self._send_json({'error': str(e)}, 500)
    
    def _handle_upload_voicemail_greeting(self, path: str):
        """Upload/update custom voicemail greeting"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail system not available'}, 500)
            return
        
        try:
            # Extract extension from path
            parts = path.split('/')
            extension = parts[3] if len(parts) > 3 else None
            
            if not extension:
                self._send_json({'error': 'Invalid path'}, 400)
                return
            
            # Get audio data from request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json({'error': 'No audio data provided'}, 400)
                return
            
            audio_data = self.rfile.read(content_length)
            
            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            
            if mailbox.save_greeting(audio_data):
                self._send_json({
                    'success': True,
                    'message': f'Custom greeting uploaded for extension {extension}'
                })
            else:
                self._send_json({'error': 'Failed to save greeting'}, 500)
                
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_delete_voicemail_greeting(self, path: str):
        """Delete custom voicemail greeting"""
        if not self.pbx_core or not hasattr(self.pbx_core, 'voicemail_system'):
            self._send_json({'error': 'Voicemail system not available'}, 500)
            return
        
        try:
            # Extract extension from path
            parts = path.split('/')
            extension = parts[3] if len(parts) > 3 else None
            
            if not extension:
                self._send_json({'error': 'Invalid path'}, 400)
                return
            
            vm_system = self.pbx_core.voicemail_system
            mailbox = vm_system.get_mailbox(extension)
            
            if mailbox.delete_greeting():
                self._send_json({
                    'success': True,
                    'message': f'Custom greeting deleted for extension {extension}'
                })
            else:
                self._send_json({'error': 'No custom greeting found'}, 404)
                
        except Exception as e:
            self._send_json({'error': str(e)}, 500)


class PBXAPIServer:
    """REST API server for PBX with HTTPS support"""

    def __init__(self, pbx_core, host='0.0.0.0', port=8080):
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
        ssl_config = self.pbx_core.config.get('api.ssl', {})
        ssl_enabled = ssl_config.get('enabled', False)
        
        if not ssl_enabled:
            self.logger.info("SSL/HTTPS is disabled - using HTTP")
            return
        
        cert_file = ssl_config.get('cert_file')
        key_file = ssl_config.get('key_file')
        
        # Check for in-house CA auto-request
        ca_config = ssl_config.get('ca', {})
        ca_enabled = ca_config.get('enabled', False)
        
        if ca_enabled and (not cert_file or not os.path.exists(cert_file)):
            self.logger.info("Certificate not found, attempting to request from in-house CA")
            if self._request_certificate_from_ca(ca_config, cert_file, key_file):
                self.logger.info("Certificate successfully obtained from in-house CA")
            else:
                self.logger.error("Failed to obtain certificate from in-house CA")
                self.logger.error("Falling back to manual certificate configuration")
        
        if not cert_file or not key_file:
            self.logger.error("SSL enabled but cert_file or key_file not configured")
            self.logger.error("Please configure api.ssl.cert_file and api.ssl.key_file in config.yml")
            self.logger.error("Or run: python scripts/generate_ssl_cert.py")
            self.logger.error("Or enable api.ssl.ca.enabled for in-house CA auto-request")
            return
        
        if not os.path.exists(cert_file):
            self.logger.error(f"SSL certificate file not found: {cert_file}")
            self.logger.error("Options:")
            self.logger.error("  1. Generate self-signed: python scripts/generate_ssl_cert.py")
            self.logger.error("  2. Request from CA: python scripts/request_ca_cert.py")
            self.logger.error("  3. Enable auto-request: set api.ssl.ca.enabled: true in config.yml")
            return
        
        if not os.path.exists(key_file):
            self.logger.error(f"SSL key file not found: {key_file}")
            return
        
        try:
            # Create SSL context
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(cert_file, key_file)
            
            # Load CA certificate if provided (for client certificate validation)
            ca_cert = ca_config.get('ca_cert')
            if ca_cert and os.path.exists(ca_cert):
                self.ssl_context.load_verify_locations(cafile=ca_cert)
                self.logger.info(f"Loaded CA certificate: {ca_cert}")
            
            # Configure strong cipher suites
            self.ssl_context.set_ciphers('HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4')
            
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
            self.logger.error(f"Failed to configure SSL: {e}")
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
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            
            ca_server = ca_config.get('server_url')
            ca_endpoint = ca_config.get('request_endpoint', '/api/sign-cert')
            
            if not ca_server:
                self.logger.error("CA server URL not configured")
                return False
            
            # Get server hostname/IP for certificate request
            hostname = self.pbx_core.config.get('server.external_ip', 'localhost')
            
            self.logger.info(f"Requesting certificate for hostname: {hostname} from CA: {ca_server}")
            
            # Create certificate directory if it doesn't exist
            cert_dir = os.path.dirname(cert_file) or 'certs'
            os.makedirs(cert_dir, exist_ok=True)
            
            # Check if we already have a private key, otherwise generate one
            if os.path.exists(key_file):
                self.logger.info(f"Using existing private key: {key_file}")
                with open(key_file, 'rb') as f:
                    private_key = serialization.load_pem_private_key(f.read(), password=None)
            else:
                self.logger.info("Generating new RSA private key (2048 bits)")
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                )
                
                # Save private key
                with open(key_file, 'wb') as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                # Set restrictive permissions on private key
                os.chmod(key_file, 0o600)
                self.logger.info(f"Private key saved to: {key_file}")
            
            # Generate CSR (Certificate Signing Request)
            self.logger.info("Generating Certificate Signing Request (CSR)")
            csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PBX System"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(hostname),
                    x509.DNSName("localhost"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Convert CSR to PEM format
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
            
            # Submit CSR to CA
            self.logger.info(f"Submitting CSR to CA: {ca_server}{ca_endpoint}")
            
            # Verify CA certificate if provided
            ca_cert = ca_config.get('ca_cert')
            verify = ca_cert if ca_cert and os.path.exists(ca_cert) else True
            
            response = requests.post(
                f"{ca_server}{ca_endpoint}",
                json={
                    'csr': csr_pem,
                    'hostname': hostname  # hostname serves as common_name in the CSR
                },
                timeout=30,
                verify=verify
            )
            
            if response.status_code != 200:
                self.logger.error(f"CA server returned error: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return False
            
            # Parse response
            cert_data = response.json()
            signed_cert = cert_data.get('certificate')
            
            if not signed_cert:
                self.logger.error("CA did not return a signed certificate")
                return False
            
            # Save certificate
            with open(cert_file, 'w') as f:
                f.write(signed_cert)
            
            self.logger.info(f"Certificate saved to: {cert_file}")
            
            # Save CA certificate if returned
            ca_cert_data = cert_data.get('ca_certificate')
            if ca_cert_data and not ca_config.get('ca_cert'):
                ca_cert_path = os.path.join(cert_dir, 'ca.crt')
                with open(ca_cert_path, 'w') as f:
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
        """Start API server"""
        try:
            self.server = HTTPServer((self.host, self.port), PBXAPIHandler)
            
            # Wrap with SSL if enabled
            if self.ssl_enabled and self.ssl_context:
                self.server.socket = self.ssl_context.wrap_socket(
                    self.server.socket,
                    server_side=True
                )
            
            # Set timeout on socket to allow periodic checking of running flag
            self.server.socket.settimeout(1.0)
            self.running = True

            protocol = "https" if self.ssl_enabled else "http"
            self.logger.info(f"API server started on {protocol}://{self.host}:{self.port}")

            # Start in separate thread
            server_thread = threading.Thread(target=self._run)
            server_thread.daemon = True
            server_thread.start()

            return True
        except Exception as e:
            self.logger.error(f"Failed to start API server: {e}")
            import traceback
            traceback.print_exc()
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
        if self.server:
            try:
                self.server.server_close()
            except (OSError, socket.error) as e:
                self.logger.error(f"Error closing API server: {e}")
        self.logger.info("API server stopped")
