"""WebRTC Blueprint routes for PBX API.

Handles WebRTC session management, SDP offer/answer exchange,
ICE candidate handling, call initiation/hangup, DTMF, and
phone configuration.
"""

import traceback

from flask import Blueprint, Response, request

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

webrtc_bp = Blueprint("webrtc", __name__)

DEFAULT_WEBRTC_EXTENSION = "webrtc-admin"


# ========== WebRTC Session Management ==========


@webrtc_bp.route("/api/webrtc/session", methods=["POST"])
@require_auth
def handle_create_webrtc_session() -> Response:
    """Create a new WebRTC session."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_signaling"):
        return send_json({"error": "WebRTC not available"}, 500)

    verbose_logging = getattr(pbx_core.webrtc_signaling, "verbose_logging", False)

    try:
        data = get_request_body()
        extension = data.get("extension")

        if verbose_logging:
            logger.info("[VERBOSE] WebRTC session creation request:")
            logger.info(f"  Extension: {extension}")
            logger.info(f"  Client IP: {request.remote_addr}")

        if not extension:
            return send_json({"error": "Extension is required"}, 400)

        # Verify extension exists (allow virtual extensions starting with
        # 'webrtc-' for browser-based calling)
        is_virtual_extension = extension.startswith("webrtc-")
        if not is_virtual_extension and not pbx_core.extension_registry.get_extension(extension):
            if verbose_logging:
                logger.warning(f"[VERBOSE] Extension not found in registry: {extension}")
            return send_json({"error": "Extension not found"}, 404)

        session = pbx_core.webrtc_signaling.create_session(extension)

        response_data = {
            "success": True,
            "session": session.to_dict(),
            "ice_servers": pbx_core.webrtc_signaling.get_ice_servers_config(),
        }

        if verbose_logging:
            logger.info("[VERBOSE] Session created successfully:")
            logger.info(f"  Session ID: {session.session_id}")
            logger.info(
                f"  ICE servers configured: {len(response_data['ice_servers'].get('iceServers', []))}"
            )

        return send_json(response_data)
    except (KeyError, TypeError, ValueError) as e:
        if verbose_logging:
            logger.error(f"[VERBOSE] Error creating WebRTC session: {e}")
            logger.error(f"[VERBOSE] Traceback:\n{traceback.format_exc()}")
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/offer", methods=["POST"])
@require_auth
def handle_webrtc_offer() -> Response:
    """Handle WebRTC SDP offer."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_signaling"):
        return send_json({"error": "WebRTC not available"}, 500)

    verbose_logging = getattr(pbx_core.webrtc_signaling, "verbose_logging", False)

    try:
        data = get_request_body()
        session_id = data.get("session_id")
        sdp = data.get("sdp")

        if verbose_logging:
            logger.info("[VERBOSE] WebRTC offer received:")
            logger.info(f"  Session ID: {session_id}")
            logger.info(f"  SDP length: {len(sdp) if sdp else 0} bytes")
            logger.info(f"  Client IP: {request.remote_addr}")

        if not session_id or not sdp:
            return send_json({"error": "session_id and sdp are required"}, 400)

        answer_sdp = pbx_core.webrtc_signaling.handle_offer(session_id, sdp)

        if answer_sdp and answer_sdp != "__legacy__":
            if verbose_logging:
                logger.info("[VERBOSE] Offer handled, SDP answer generated")
            return send_json({
                "success": True,
                "message": "Offer received",
                "answer_sdp": answer_sdp,
            })
        if answer_sdp == "__legacy__":
            # aiortc unavailable – legacy mode (no real media)
            if verbose_logging:
                logger.info("[VERBOSE] Offer stored (legacy, no aiortc)")
            return send_json({"success": True, "message": "Offer received"})
        if verbose_logging:
            logger.warning("[VERBOSE] Session not found or offer processing failed")
        return send_json({"error": "Session not found or offer processing failed"}, 404)
    except (KeyError, TypeError, ValueError) as e:
        if verbose_logging:
            logger.error(f"[VERBOSE] Error handling WebRTC offer: {e}")
            logger.error(f"[VERBOSE] Traceback:\n{traceback.format_exc()}")
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/answer", methods=["POST"])
@require_auth
def handle_webrtc_answer() -> Response:
    """Handle WebRTC SDP answer."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_signaling"):
        return send_json({"error": "WebRTC not available"}, 500)

    try:
        data = get_request_body()
        session_id = data.get("session_id")
        sdp = data.get("sdp")

        if not session_id or not sdp:
            return send_json({"error": "session_id and sdp are required"}, 400)

        success = pbx_core.webrtc_signaling.handle_answer(session_id, sdp)

        if success:
            return send_json({"success": True, "message": "Answer received"})
        return send_json({"error": "Session not found"}, 404)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/ice-candidate", methods=["POST"])
@require_auth
def handle_webrtc_ice_candidate() -> Response:
    """Handle WebRTC ICE candidate."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_signaling"):
        return send_json({"error": "WebRTC not available"}, 500)

    verbose_logging = getattr(pbx_core.webrtc_signaling, "verbose_logging", False)

    try:
        data = get_request_body()
        session_id = data.get("session_id")
        candidate = data.get("candidate")

        if verbose_logging:
            logger.info("[VERBOSE] ICE candidate received:")
            logger.info(f"  Session ID: {session_id}")
            if candidate:
                logger.info(f"  Candidate: {candidate.get('candidate', 'N/A')}")

        if not session_id or not candidate:
            return send_json({"error": "session_id and candidate are required"}, 400)

        success = pbx_core.webrtc_signaling.add_ice_candidate(session_id, candidate)

        if success:
            return send_json({"success": True, "message": "ICE candidate added"})
        if verbose_logging:
            logger.warning("[VERBOSE] Session not found for ICE candidate")
        return send_json({"error": "Session not found"}, 404)
    except (KeyError, TypeError, ValueError) as e:
        if verbose_logging:
            logger.error(f"[VERBOSE] Error handling ICE candidate: {e}")
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/call", methods=["POST"])
@require_auth
def handle_webrtc_call() -> Response:
    """Initiate a call from WebRTC client."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_gateway"):
        return send_json({"error": "WebRTC gateway not available"}, 500)

    verbose_logging = False
    if hasattr(pbx_core, "webrtc_signaling"):
        verbose_logging = getattr(pbx_core.webrtc_signaling, "verbose_logging", False)

    try:
        data = get_request_body()
        session_id = data.get("session_id")
        target_extension = data.get("target_extension")

        if verbose_logging:
            logger.info("[VERBOSE] WebRTC call initiation request:")
            logger.info(f"  Session ID: {session_id}")
            logger.info(f"  Target Extension: {target_extension}")
            logger.info(f"  Client IP: {request.remote_addr}")

        if not session_id or not target_extension:
            return send_json({"error": "session_id and target_extension are required"}, 400)

        call_id = pbx_core.webrtc_gateway.initiate_call(
            session_id,
            target_extension,
            webrtc_signaling=(
                pbx_core.webrtc_signaling if hasattr(pbx_core, "webrtc_signaling") else None
            ),
        )

        if call_id:
            if verbose_logging:
                logger.info("[VERBOSE] Call initiated successfully:")
                logger.info(f"  Call ID: {call_id}")
            return send_json(
                {
                    "success": True,
                    "call_id": call_id,
                    "message": f"Call initiated to {target_extension}",
                }
            )
        if verbose_logging:
            logger.error("[VERBOSE] Call initiation failed - no call ID returned")
        return send_json({"error": "Failed to initiate call"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        if verbose_logging:
            logger.error(f"[VERBOSE] Exception in call handler: {e}")
            logger.error(f"[VERBOSE] Traceback:\n{traceback.format_exc()}")
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/hangup", methods=["POST"])
@require_auth
def handle_webrtc_hangup() -> Response:
    """Handle WebRTC call hangup/termination."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX core not available"}, 500)

    verbose_logging = False
    if hasattr(pbx_core, "webrtc_signaling"):
        verbose_logging = getattr(pbx_core.webrtc_signaling, "verbose_logging", False)

    try:
        data = get_request_body()
        session_id = data.get("session_id")
        call_id = data.get("call_id")

        if verbose_logging:
            logger.info("[VERBOSE] WebRTC hangup request:")
            logger.info(f"  Session ID: {session_id}")
            logger.info(f"  Call ID: {call_id}")
            logger.info(f"  Client IP: {request.remote_addr}")

        if not session_id:
            return send_json({"error": "session_id is required"}, 400)

        # Terminate the call if call_id is provided
        if call_id and hasattr(pbx_core, "call_manager"):
            call = pbx_core.call_manager.get_call(call_id)
            if call:
                if verbose_logging:
                    logger.info(f"[VERBOSE] Terminating call {call_id}")

                # End the call through call manager
                pbx_core.call_manager.end_call(call_id)

                if verbose_logging:
                    logger.info(f"[VERBOSE] Call {call_id} terminated successfully")
            elif verbose_logging:
                logger.warning(f"[VERBOSE] Call {call_id} not found in call manager")

        # Clean up WebRTC session
        if hasattr(pbx_core, "webrtc_signaling"):
            session = pbx_core.webrtc_signaling.get_session(session_id)
            if session:
                # Close the session
                pbx_core.webrtc_signaling.close_session(session_id)
                if verbose_logging:
                    logger.info(f"[VERBOSE] WebRTC session {session_id} closed")

        return send_json({"success": True, "message": "Call terminated successfully"})

    except (KeyError, TypeError, ValueError) as e:
        if verbose_logging:
            logger.error(f"[VERBOSE] Exception in hangup handler: {e}")
            logger.error(f"[VERBOSE] Traceback:\n{traceback.format_exc()}")
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/dtmf", methods=["POST"])
@require_auth
def handle_webrtc_dtmf() -> Response:
    """Handle DTMF tone sending from WebRTC client."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX core not available"}, 500)

    verbose_logging = False
    if hasattr(pbx_core, "webrtc_signaling"):
        verbose_logging = getattr(pbx_core.webrtc_signaling, "verbose_logging", False)

    try:
        data = get_request_body()
        session_id = data.get("session_id")
        digit = data.get("digit")
        duration = data.get("duration", 160)  # Default 160ms

        if verbose_logging:
            logger.info("[VERBOSE] WebRTC DTMF request:")
            logger.info(f"  Session ID: {session_id}")
            logger.info(f"  Digit: {digit}")
            logger.info(f"  Duration: {duration}ms")
            logger.info(f"  Client IP: {request.remote_addr}")

        if not session_id or digit is None:
            return send_json({"error": "session_id and digit are required"}, 400)

        # Validate digit
        if digit not in "0123456789*#":
            return send_json({"error": "Invalid digit. Must be 0-9, *, or #"}, 400)

        # Get the session
        if not hasattr(pbx_core, "webrtc_signaling"):
            return send_json({"error": "WebRTC signaling not available"}, 500)

        session = pbx_core.webrtc_signaling.get_session(session_id)
        if not session:
            return send_json({"error": "Session not found"}, 404)

        # Get the active call for this session
        if not session.call_id:
            return send_json({"error": "No active call for this session"}, 400)

        if verbose_logging:
            logger.info(f"[VERBOSE] Found call ID: {session.call_id}")

        # Get the call object
        call = None
        if hasattr(pbx_core, "call_manager"):
            call = pbx_core.call_manager.get_call(session.call_id)

        if not call:
            return send_json({"error": "Call not found"}, 404)

        if verbose_logging:
            logger.info(f"[VERBOSE] Found call object for {session.call_id}")
            logger.info(f"  Caller: {call.caller_extension}")
            logger.info(f"  Callee: {call.callee_extension}")

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
                    logger.info(f"[VERBOSE] Sending DTMF '{digit}' via RFC2833")

                # Send DTMF via RFC2833 and check return value
                success = target_handler.rfc2833_sender.send_dtmf(digit, duration_ms=duration)

                if success:
                    if verbose_logging:
                        logger.info(f"[VERBOSE] DTMF '{digit}' sent successfully")
                    return send_json(
                        {
                            "success": True,
                            "message": f'DTMF tone "{digit}" sent successfully',
                            "digit": digit,
                            "duration": duration,
                        }
                    )
                if verbose_logging:
                    logger.error(f"[VERBOSE] Failed to send DTMF '{digit}'")
                return send_json({"error": f'Failed to send DTMF tone "{digit}"'}, 500)
            if verbose_logging:
                logger.warning("[VERBOSE] No RFC2833 sender available for DTMF")
            return send_json({"error": "DTMF sending not available for this call"}, 500)
        if verbose_logging:
            logger.warning(f"[VERBOSE] No RTP handlers found for call {session.call_id}")
        return send_json({"error": "No RTP handlers available for this call"}, 500)

    except (KeyError, TypeError, ValueError) as e:
        if verbose_logging:
            logger.error(f"[VERBOSE] Exception in DTMF handler: {e}")
            logger.error(f"[VERBOSE] Traceback:\n{traceback.format_exc()}")
        return send_json({"error": str(e)}, 500)


# ========== WebRTC GET Routes ==========


@webrtc_bp.route("/api/webrtc/call-status", methods=["GET"])
@require_auth
def handle_webrtc_call_status() -> Response:
    """Get the current status of a WebRTC call.

    Query parameters:
        call_id: The call identifier to check status for.

    Returns call state (calling, ringing, connected, ended) so the
    browser can play appropriate local tones (ringback, etc.).
    """
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX core not available"}, 500)

    call_id = request.args.get("call_id")
    if not call_id:
        return send_json({"error": "call_id query parameter is required"}, 400)

    if not hasattr(pbx_core, "call_manager"):
        return send_json({"error": "Call manager not available"}, 500)

    call = pbx_core.call_manager.get_call(call_id)
    if not call:
        # Call may have ended and been removed from active calls
        return send_json({"success": True, "state": "ended"})

    return send_json({"success": True, "state": call.state.value})


@webrtc_bp.route("/api/webrtc/sessions", methods=["GET"])
@require_auth
def handle_get_webrtc_sessions() -> Response:
    """Get all WebRTC sessions."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_signaling"):
        return send_json({"error": "WebRTC not available"}, 500)

    try:
        sessions = pbx_core.webrtc_signaling.get_sessions_info()
        return send_json(sessions)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/phone-config", methods=["GET"])
@require_auth
def handle_get_webrtc_phone_config() -> Response:
    """Get WebRTC phone extension configuration."""
    pbx_core = get_pbx_core()
    try:
        # Get the configured extension for the webrtc admin phone
        extension = pbx_core.extension_db.get_config(
            "webrtc_phone_extension", DEFAULT_WEBRTC_EXTENSION
        )
        return send_json({"success": True, "extension": extension})
    except Exception as e:
        logger.error(f"Error getting WebRTC phone config: {e}")
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/ice-servers", methods=["GET"])
@require_auth
def handle_get_ice_servers() -> Response:
    """Get ICE servers configuration."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_signaling"):
        return send_json({"error": "WebRTC not available"}, 500)

    try:
        config = pbx_core.webrtc_signaling.get_ice_servers_config()
        return send_json(config)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@webrtc_bp.route("/api/webrtc/session/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_webrtc_session(subpath: str) -> Response:
    """Get specific WebRTC session."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webrtc_signaling"):
        return send_json({"error": "WebRTC not available"}, 500)

    try:
        session_id = subpath.rsplit("/", maxsplit=1)[-1]
        session = pbx_core.webrtc_signaling.get_session(session_id)

        if session:
            return send_json(session.to_dict())
        return send_json({"error": "Session not found"}, 404)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


# ========== WebRTC Configuration ==========


@webrtc_bp.route("/api/webrtc/phone-config", methods=["POST"])
@require_auth
def handle_set_webrtc_phone_config() -> Response:
    """set WebRTC phone extension configuration."""
    pbx_core = get_pbx_core()
    try:
        data = get_request_body()
        extension = data.get("extension")

        if not extension:
            return send_json({"error": "Extension is required"}, 400)

        # Validate extension exists or is a valid virtual extension
        is_virtual = extension.startswith("webrtc-")
        if not is_virtual:
            ext_info = pbx_core.extension_registry.get_extension(extension)
            if not ext_info:
                return send_json({"error": "Extension not found"}, 404)

        # Save the configuration
        success = pbx_core.extension_db.set_config("webrtc_phone_extension", extension, "string")

        if success:
            return send_json({"success": True, "extension": extension})
        return send_json({"error": "Failed to save configuration"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error setting WebRTC phone config: {e}")
        return send_json({"error": str(e)}, 500)
