"""
CRM Integration Framework
HubSpot and Zendesk integration for marketing and support
"""


from pbx.utils.logger import get_logger


class HubSpotIntegration:
    """
    HubSpot integration framework
    Marketing automation and CRM integration
    """

    def __init__(self, db_backend, config: dict):
        """
        Initialize HubSpot integration

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = False

        self.logger.info("HubSpot Integration Framework initialized")

    def get_config(self) -> dict | None:
        """
        Get HubSpot integration configuration

        Returns:
            Configuration dict or None
        """
        try:
            result = self.db.execute("SELECT * FROM hubspot_integration ORDER BY id DESC LIMIT 1")

            if result and result[0]:
                row = result[0]
                self.enabled = bool(row[1])
                return {
                    "enabled": bool(row[1]),
                    "portal_id": row[3],
                    "sync_contacts": bool(row[4]),
                    "sync_deals": bool(row[5]),
                    "auto_create_contacts": bool(row[6]),
                    "last_sync": row[7],
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get HubSpot config: {e}")
            return None

    def update_config(self, config: dict) -> bool:
        """
        Update HubSpot integration configuration

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if successful
        """
        try:
            # Check if config exists
            existing = self.get_config()

            if existing:
                # Update
                sql_params = [
                    config.get("enabled", False),
                    config.get("api_key_encrypted"),
                    config.get("portal_id"),
                    config.get("sync_contacts", True),
                    config.get("sync_deals", True),
                    config.get("auto_create_contacts", False),
                ]

                self.db.execute(
                    (
                        """UPDATE hubspot_integration
                       SET enabled = ?, api_key_encrypted = ?, portal_id = ?,
                           sync_contacts = ?, sync_deals = ?, auto_create_contacts = ?
                       WHERE id = (SELECT MAX(id) FROM hubspot_integration)"""
                        if self.db.db_type == "sqlite"
                        else """UPDATE hubspot_integration
                       SET enabled = %s, api_key_encrypted = %s, portal_id = %s,
                           sync_contacts = %s, sync_deals = %s, auto_create_contacts = %s
                       WHERE id = (SELECT MAX(id) FROM hubspot_integration)"""
                    ),
                    tuple(sql_params),
                )
            else:
                # Insert
                sql_params = [
                    config.get("enabled", False),
                    config.get("api_key_encrypted"),
                    config.get("portal_id"),
                    config.get("sync_contacts", True),
                    config.get("sync_deals", True),
                    config.get("auto_create_contacts", False),
                ]

                self.db.execute(
                    (
                        """INSERT INTO hubspot_integration
                       (enabled, api_key_encrypted, portal_id, sync_contacts, sync_deals, auto_create_contacts)
                       VALUES (?, ?, ?, ?, ?, ?)"""
                        if self.db.db_type == "sqlite"
                        else """INSERT INTO hubspot_integration
                       (enabled, api_key_encrypted, portal_id, sync_contacts, sync_deals, auto_create_contacts)
                       VALUES (%s, %s, %s, %s, %s, %s)"""
                    ),
                    tuple(sql_params),
                )

            self.enabled = config.get("enabled", False)
            self.logger.info("Updated HubSpot integration config")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update HubSpot config: {e}")
            return False

    def sync_contact(self, contact_data: dict) -> bool:
        """
        Sync contact to HubSpot
        Framework method - integrates with HubSpot API

        Args:
            contact_data: Contact information

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        try:
            # Get HubSpot API configuration
            config = self.get_config()
            if not config or not config.get("api_key"):
                self.logger.warning("HubSpot API key not configured")
                return False

            # Prepare contact data for HubSpot API
            properties = {}
            if contact_data.get("email"):
                properties["email"] = contact_data["email"]
            if contact_data.get("first_name"):
                properties["firstname"] = contact_data["first_name"]
            if contact_data.get("last_name"):
                properties["lastname"] = contact_data["last_name"]
            if contact_data.get("phone"):
                properties["phone"] = contact_data["phone"]
            if contact_data.get("company"):
                properties["company"] = contact_data["company"]

            # Make API request
            import requests

            headers = {
                "Content-type": "application/json",
                "Authorization": f"Bearer {config['api_key']}",
            }

            payload = {"properties": properties}

            # Use webhook URL if configured, otherwise use HubSpot API
            if config.get("webhook_url"):
                # Webhook-based integration
                response = requests.post(
                    config["webhook_url"],
                    json=payload,
                    headers={"Content-type": "application/json"},
                    timeout=10,
                )
            else:
                # Direct API integration
                config.get("portal_id", "")
                response = requests.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )

            if response.status_code in [200, 201]:
                self._log_activity(
                    "hubspot",
                    "sync_contact",
                    "success",
                    f"Contact synced: {contact_data.get('email')}",
                )
                return True
            else:
                self._log_activity(
                    "hubspot", "sync_contact", "error", f"API error: {response.status_code}"
                )
                self.logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self._log_activity("hubspot", "sync_contact", "error", str(e))
            self.logger.error(f"HubSpot API request failed: {e}")
            return False
        except Exception as e:
            self._log_activity("hubspot", "sync_contact", "error", str(e))
            self.logger.error(f"HubSpot sync error: {e}")
            return False

    def create_deal(self, deal_data: dict) -> bool:
        """
        Create deal in HubSpot
        Uses webhook or HubSpot API

        Args:
            deal_data: Deal information

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        try:
            # Get HubSpot API configuration
            config = self.get_config()
            if not config or not config.get("api_key"):
                self.logger.warning("HubSpot API key not configured")
                return False

            # Prepare deal data for HubSpot API
            properties = {}
            if deal_data.get("dealname"):
                properties["dealname"] = deal_data["dealname"]
            if deal_data.get("amount"):
                properties["amount"] = str(deal_data["amount"])
            if deal_data.get("dealstage"):
                properties["dealstage"] = deal_data["dealstage"]
            if deal_data.get("pipeline"):
                properties["pipeline"] = deal_data["pipeline"]
            if deal_data.get("closedate"):
                properties["closedate"] = deal_data["closedate"]

            # Make API request
            import requests

            headers = {
                "Content-type": "application/json",
                "Authorization": f"Bearer {config['api_key']}",
            }

            payload = {"properties": properties}

            # Add associations if provided (e.g., contact ID)
            if deal_data.get("contact_id"):
                payload["associations"] = [
                    {
                        "to": {"id": deal_data["contact_id"]},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 3,  # Deal to Contact association
                            }
                        ],
                    }
                ]

            # Use webhook URL if configured, otherwise use HubSpot API
            if config.get("webhook_url"):
                # Webhook-based integration
                response = requests.post(
                    config["webhook_url"],
                    json=payload,
                    headers={"Content-type": "application/json"},
                    timeout=10,
                )
            else:
                # Direct API integration
                response = requests.post(
                    "https://api.hubapi.com/crm/v3/objects/deals",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )

            if response.status_code in [200, 201]:
                self._log_activity(
                    "hubspot",
                    "create_deal",
                    "success",
                    f"Deal created: {deal_data.get('dealname')}",
                )
                return True
            else:
                self._log_activity(
                    "hubspot", "create_deal", "error", f"API error: {response.status_code}"
                )
                self.logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self._log_activity("hubspot", "create_deal", "error", str(e))
            self.logger.error(f"HubSpot API request failed: {e}")
            return False
        except Exception as e:
            self._log_activity("hubspot", "create_deal", "error", str(e))
            self.logger.error(f"HubSpot deal creation error: {e}")
            return False

    def _log_activity(self, integration_type: str, action: str, status: str, details: str):
        """Log integration activity"""
        try:
            self.db.execute(
                (
                    """INSERT INTO integration_activity_log
                   (integration_type, action, status, details)
                   VALUES (?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO integration_activity_log
                   (integration_type, action, status, details)
                   VALUES (%s, %s, %s, %s)"""
                ),
                (integration_type, action, status, details),
            )
        except Exception as e:
            self.logger.error(f"Failed to log integration activity: {e}")


class ZendeskIntegration:
    """
    Zendesk integration framework
    Helpdesk ticket creation and management
    """

    def __init__(self, db_backend, config: dict):
        """
        Initialize Zendesk integration

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = False

        self.logger.info("Zendesk Integration Framework initialized")

    def get_config(self) -> dict | None:
        """
        Get Zendesk integration configuration

        Returns:
            Configuration dict or None
        """
        try:
            result = self.db.execute("SELECT * FROM zendesk_integration ORDER BY id DESC LIMIT 1")

            if result and result[0]:
                row = result[0]
                self.enabled = bool(row[1])
                return {
                    "enabled": bool(row[1]),
                    "subdomain": row[2],
                    "email": row[4],
                    "auto_create_tickets": bool(row[5]),
                    "default_priority": row[6],
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get Zendesk config: {e}")
            return None

    def update_config(self, config: dict) -> bool:
        """
        Update Zendesk integration configuration

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if successful
        """
        try:
            existing = self.get_config()

            if existing:
                # Update
                sql_params = [
                    config.get("enabled", False),
                    config.get("subdomain"),
                    config.get("api_token_encrypted"),
                    config.get("email"),
                    config.get("auto_create_tickets", False),
                    config.get("default_priority", "normal"),
                ]

                self.db.execute(
                    (
                        """UPDATE zendesk_integration
                       SET enabled = ?, subdomain = ?, api_token_encrypted = ?,
                           email = ?, auto_create_tickets = ?, default_priority = ?
                       WHERE id = (SELECT MAX(id) FROM zendesk_integration)"""
                        if self.db.db_type == "sqlite"
                        else """UPDATE zendesk_integration
                       SET enabled = %s, subdomain = %s, api_token_encrypted = %s,
                           email = %s, auto_create_tickets = %s, default_priority = %s
                       WHERE id = (SELECT MAX(id) FROM zendesk_integration)"""
                    ),
                    tuple(sql_params),
                )
            else:
                # Insert
                sql_params = [
                    config.get("enabled", False),
                    config.get("subdomain"),
                    config.get("api_token_encrypted"),
                    config.get("email"),
                    config.get("auto_create_tickets", False),
                    config.get("default_priority", "normal"),
                ]

                self.db.execute(
                    (
                        """INSERT INTO zendesk_integration
                       (enabled, subdomain, api_token_encrypted, email, auto_create_tickets, default_priority)
                       VALUES (?, ?, ?, ?, ?, ?)"""
                        if self.db.db_type == "sqlite"
                        else """INSERT INTO zendesk_integration
                       (enabled, subdomain, api_token_encrypted, email, auto_create_tickets, default_priority)
                       VALUES (%s, %s, %s, %s, %s, %s)"""
                    ),
                    tuple(sql_params),
                )

            self.enabled = config.get("enabled", False)
            self.logger.info("Updated Zendesk integration config")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update Zendesk config: {e}")
            return False

    def create_ticket(self, ticket_data: dict) -> str | None:
        """
        Create ticket in Zendesk
        Uses webhook or Zendesk API

        Args:
            ticket_data: Ticket information (subject, description, requester_email, priority, tags)

        Returns:
            Ticket ID or None
        """
        if not self.enabled:
            return None

        try:
            # Get Zendesk API configuration
            config = self.get_config()
            if not config:
                self.logger.warning("Zendesk not configured")
                return None

            # Prepare ticket data for Zendesk API
            ticket = {
                "subject": ticket_data.get("subject", "Phone Call"),
                "comment": {
                    "body": ticket_data.get("description", "Ticket created from phone call")
                },
                "priority": ticket_data.get("priority", config.get("default_priority", "normal")),
            }

            # set requester
            if ticket_data.get("requester_email"):
                ticket["requester"] = {"email": ticket_data["requester_email"]}
            elif ticket_data.get("requester_name"):
                ticket["requester"] = {"name": ticket_data["requester_name"]}

            # Add tags if provided
            if ticket_data.get("tags"):
                ticket["tags"] = ticket_data["tags"]

            # Make API request
            import base64

            import requests

            # Build authentication
            subdomain = config.get("subdomain", "")
            email = config.get("email", "")
            api_token = config.get("api_token", "")

            # Use webhook URL if configured, otherwise use Zendesk API
            if config.get("webhook_url"):
                # Webhook-based integration
                response = requests.post(
                    config["webhook_url"],
                    json={"ticket": ticket},
                    headers={"Content-type": "application/json"},
                    timeout=10,
                )
            else:
                # Direct API integration
                auth_string = f"{email}/token:{api_token}"
                auth_bytes = base64.b64encode(auth_string.encode("utf-8"))
                auth_header = f"Basic {auth_bytes.decode('utf-8')}"

                headers = {"Content-type": "application/json", "Authorization": auth_header}

                response = requests.post(
                    f"https://{subdomain}.zendesk.com/api/v2/tickets.json",
                    json={"ticket": ticket},
                    headers=headers,
                    timeout=10,
                )

            if response.status_code in [200, 201]:
                result = response.json()
                ticket_id = str(result.get("ticket", {}).get("id", ""))
                self._log_activity(
                    "zendesk", "create_ticket", "success", f"Ticket created: {ticket_id}"
                )
                return ticket_id
            else:
                self._log_activity(
                    "zendesk", "create_ticket", "error", f"API error: {response.status_code}"
                )
                self.logger.error(f"Zendesk API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            self._log_activity("zendesk", "create_ticket", "error", str(e))
            self.logger.error(f"Zendesk API request failed: {e}")
            return None
        except Exception as e:
            self._log_activity("zendesk", "create_ticket", "error", str(e))
            self.logger.error(f"Zendesk ticket creation error: {e}")
            return None

    def update_ticket(self, ticket_id: str, update_data: dict) -> bool:
        """
        Update ticket in Zendesk
        Uses webhook or Zendesk API

        Args:
            ticket_id: Ticket ID
            update_data: Update information (status, priority, comment)

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        try:
            # Get Zendesk API configuration
            config = self.get_config()
            if not config:
                self.logger.warning("Zendesk not configured")
                return False

            # Prepare update data
            ticket = {}
            if update_data.get("status"):
                ticket["status"] = update_data["status"]
            if update_data.get("priority"):
                ticket["priority"] = update_data["priority"]
            if update_data.get("comment"):
                ticket["comment"] = {"body": update_data["comment"]}
            if update_data.get("assignee_id"):
                ticket["assignee_id"] = update_data["assignee_id"]

            # Make API request
            import base64

            import requests

            subdomain = config.get("subdomain", "")
            email = config.get("email", "")
            api_token = config.get("api_token", "")

            # Use webhook URL if configured, otherwise use Zendesk API
            if config.get("webhook_url"):
                # Webhook-based integration
                response = requests.put(
                    f"{config['webhook_url']}/{ticket_id}",
                    json={"ticket": ticket},
                    headers={"Content-type": "application/json"},
                    timeout=10,
                )
            else:
                # Direct API integration
                auth_string = f"{email}/token:{api_token}"
                auth_bytes = base64.b64encode(auth_string.encode("utf-8"))
                auth_header = f"Basic {auth_bytes.decode('utf-8')}"

                headers = {"Content-type": "application/json", "Authorization": auth_header}

                response = requests.put(
                    f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}.json",
                    json={"ticket": ticket},
                    headers=headers,
                    timeout=10,
                )

            if response.status_code == 200:
                self._log_activity(
                    "zendesk", "update_ticket", "success", f"Ticket updated: {ticket_id}"
                )
                return True
            else:
                self._log_activity(
                    "zendesk", "update_ticket", "error", f"API error: {response.status_code}"
                )
                self.logger.error(f"Zendesk API error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self._log_activity("zendesk", "update_ticket", "error", str(e))
            self.logger.error(f"Zendesk API request failed: {e}")
            return False
        except Exception as e:
            self._log_activity("zendesk", "update_ticket", "error", str(e))
            self.logger.error(f"Zendesk ticket update error: {e}")
            return False

    def _log_activity(self, integration_type: str, action: str, status: str, details: str):
        """Log integration activity"""
        try:
            self.db.execute(
                (
                    """INSERT INTO integration_activity_log
                   (integration_type, action, status, details)
                   VALUES (?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO integration_activity_log
                   (integration_type, action, status, details)
                   VALUES (%s, %s, %s, %s)"""
                ),
                (integration_type, action, status, details),
            )
        except Exception as e:
            self.logger.error(f"Failed to log integration activity: {e}")

    def get_activity_log(self, limit: int = 100) -> list[dict]:
        """
        Get integration activity log

        Args:
            limit: Maximum number of records

        Returns:
            list of activity dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT * FROM integration_activity_log
                   ORDER BY created_at DESC LIMIT ?"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM integration_activity_log
                   ORDER BY created_at DESC LIMIT %s"""
                ),
                (limit,),
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

            return activities

        except Exception as e:
            self.logger.error(f"Failed to get activity log: {e}")
            return []
