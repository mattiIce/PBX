"""
REST API endpoints for open-source integrations
Handles Jitsi, EspoCRM, and Matrix integrations
"""


def add_opensource_integration_endpoints(handler):
    """
    Add endpoint handlers for open-source integrations

    Args:
        handler: PBXAPIHandler instance
    """

    # Jitsi Meet endpoints
    def handle_jitsi_create_meeting(handler):
        """POST /api/integrations/jitsi/meetings - Create Jitsi meeting"""
        try:
            body = handler._get_body()

            # Get Jitsi integration
            jitsi = getattr(handler.pbx_core, "jitsi_integration", None)
            if not jitsi or not jitsi.enabled:
                handler._send_json({"error": "Jitsi integration not enabled"}, 400)
                return

            # Create meeting
            result = jitsi.create_meeting(
                room_name=body.get("room_name"),
                subject=body.get("subject"),
                moderator_name=body.get("moderator_name"),
                participant_names=body.get("participants", []),
                scheduled_time=body.get("scheduled_time"),
                duration_minutes=body.get("duration", 60),
            )

            handler._send_json(result)

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to create Jitsi meeting: {e}")
            handler._send_json({"error": str(e)}, 500)

    def handle_jitsi_instant_meeting(handler):
        """POST /api/integrations/jitsi/instant - Create instant meeting"""
        try:
            body = handler._get_body()

            jitsi = getattr(handler.pbx_core, "jitsi_integration", None)
            if not jitsi or not jitsi.enabled:
                handler._send_json({"error": "Jitsi integration not enabled"}, 400)
                return

            result = jitsi.create_instant_meeting(
                extension=body.get("extension"), contact_name=body.get("contact_name")
            )

            handler._send_json(result)

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to create instant meeting: {e}")
            handler._send_json({"error": str(e)}, 500)

    # EspoCRM endpoints
    def handle_espocrm_search_contact(handler):
        """GET /api/integrations/espocrm/contacts/search?phone={number} - Find contact by phone"""
        try:
            from urllib.parse import parse_qs, urlparse

            espocrm = getattr(handler.pbx_core, "espocrm_integration", None)
            if not espocrm or not espocrm.enabled:
                handler._send_json({"error": "EspoCRM integration not enabled"}, 400)
                return

            # Parse query parameters
            parsed = urlparse(handler.path)
            params = parse_qs(parsed.query)
            phone = params.get("phone", [""])[0]

            if not phone:
                handler._send_json({"error": "phone parameter required"}, 400)
                return

            # Search for contact
            contact = espocrm.find_contact_by_phone(phone)

            if contact:
                handler._send_json({"success": True, "contact": contact})
            else:
                handler._send_json({"success": False, "message": "Contact not found"})

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to search contact: {e}")
            handler._send_json({"error": str(e)}, 500)

    def handle_espocrm_create_contact(handler):
        """POST /api/integrations/espocrm/contacts - Create contact"""
        try:
            body = handler._get_body()

            espocrm = getattr(handler.pbx_core, "espocrm_integration", None)
            if not espocrm or not espocrm.enabled:
                handler._send_json({"error": "EspoCRM integration not enabled"}, 400)
                return

            result = espocrm.create_contact(
                name=body.get("name"),
                phone=body.get("phone"),
                email=body.get("email"),
                company=body.get("company"),
                title=body.get("title"),
            )

            if result:
                handler._send_json({"success": True, "contact": result})
            else:
                handler._send_json({"success": False, "error": "Failed to create contact"}, 500)

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to create contact: {e}")
            handler._send_json({"error": str(e)}, 500)

    def handle_espocrm_log_call(handler):
        """POST /api/integrations/espocrm/calls - Log call"""
        try:
            body = handler._get_body()

            espocrm = getattr(handler.pbx_core, "espocrm_integration", None)
            if not espocrm or not espocrm.enabled:
                handler._send_json({"error": "EspoCRM integration not enabled"}, 400)
                return

            result = espocrm.log_call(
                contact_id=body.get("contact_id"),
                direction=body.get("direction"),
                duration=body.get("duration"),
                status=body.get("status"),
                description=body.get("description"),
            )

            if result:
                handler._send_json({"success": True, "call": result})
            else:
                handler._send_json({"success": False, "error": "Failed to log call"}, 500)

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to log call: {e}")
            handler._send_json({"error": str(e)}, 500)

    # Matrix endpoints
    def handle_matrix_send_message(handler):
        """POST /api/integrations/matrix/messages - Send message to room"""
        try:
            body = handler._get_body()

            matrix = getattr(handler.pbx_core, "matrix_integration", None)
            if not matrix or not matrix.enabled:
                handler._send_json({"error": "Matrix integration not enabled"}, 400)
                return

            event_id = matrix.send_message(
                room_id=body.get("room_id"),
                message=body.get("message"),
                msg_type=body.get("msg_type", "m.text"),
            )

            if event_id:
                handler._send_json({"success": True, "event_id": event_id})
            else:
                handler._send_json({"success": False, "error": "Failed to send message"}, 500)

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to send Matrix message: {e}")
            handler._send_json({"error": str(e)}, 500)

    def handle_matrix_send_notification(handler):
        """POST /api/integrations/matrix/notifications - Send notification"""
        try:
            body = handler._get_body()

            matrix = getattr(handler.pbx_core, "matrix_integration", None)
            if not matrix or not matrix.enabled:
                handler._send_json({"error": "Matrix integration not enabled"}, 400)
                return

            success = matrix.send_notification(
                message=body.get("message"), room_id=body.get("room_id")
            )

            handler._send_json({"success": success})

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to send notification: {e}")
            handler._send_json({"error": str(e)}, 500)

    def handle_matrix_create_room(handler):
        """POST /api/integrations/matrix/rooms - Create room"""
        try:
            body = handler._get_body()

            matrix = getattr(handler.pbx_core, "matrix_integration", None)
            if not matrix or not matrix.enabled:
                handler._send_json({"error": "Matrix integration not enabled"}, 400)
                return

            room_id = matrix.create_room(
                name=body.get("name"),
                topic=body.get("topic"),
                invite_users=body.get("invite_users", []),
            )

            if room_id:
                handler._send_json({"success": True, "room_id": room_id})
            else:
                handler._send_json({"success": False, "error": "Failed to create room"}, 500)

        except (KeyError, TypeError, ValueError) as e:
            handler.pbx_core.logger.error(f"Failed to create Matrix room: {e}")
            handler._send_json({"error": str(e)}, 500)

    # Return endpoint mapping
    return {
        # Jitsi endpoints
        "POST /api/integrations/jitsi/meetings": handle_jitsi_create_meeting,
        "POST /api/integrations/jitsi/instant": handle_jitsi_instant_meeting,
        # EspoCRM endpoints
        "GET /api/integrations/espocrm/contacts/search": handle_espocrm_search_contact,
        "POST /api/integrations/espocrm/contacts": handle_espocrm_create_contact,
        "POST /api/integrations/espocrm/calls": handle_espocrm_log_call,
        # Matrix endpoints
        "POST /api/integrations/matrix/messages": handle_matrix_send_message,
        "POST /api/integrations/matrix/notifications": handle_matrix_send_notification,
        "POST /api/integrations/matrix/rooms": handle_matrix_create_room,
    }
