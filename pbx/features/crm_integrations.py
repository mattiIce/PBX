"""
CRM Integration Framework
HubSpot and Zendesk integration for marketing and support
"""
from datetime import datetime
from typing import Dict, List, Optional

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

    def get_config(self) -> Optional[Dict]:
        """
        Get HubSpot integration configuration

        Returns:
            Configuration dict or None
        """
        try:
            result = self.db.execute(
                "SELECT * FROM hubspot_integration ORDER BY id DESC LIMIT 1"
            )

            if result and result[0]:
                row = result[0]
                self.enabled = bool(row[1])
                return {
                    'enabled': bool(row[1]),
                    'portal_id': row[3],
                    'sync_contacts': bool(row[4]),
                    'sync_deals': bool(row[5]),
                    'auto_create_contacts': bool(row[6]),
                    'last_sync': row[7]
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get HubSpot config: {e}")
            return None

    def update_config(self, config: Dict) -> bool:
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
                    config.get('enabled', False),
                    config.get('api_key_encrypted'),
                    config.get('portal_id'),
                    config.get('sync_contacts', True),
                    config.get('sync_deals', True),
                    config.get('auto_create_contacts', False)
                ]
                
                self.db.execute(
                    """UPDATE hubspot_integration 
                       SET enabled = ?, api_key_encrypted = ?, portal_id = ?,
                           sync_contacts = ?, sync_deals = ?, auto_create_contacts = ?
                       WHERE id = (SELECT MAX(id) FROM hubspot_integration)"""
                    if self.db.db_type == 'sqlite'
                    else """UPDATE hubspot_integration 
                       SET enabled = %s, api_key_encrypted = %s, portal_id = %s,
                           sync_contacts = %s, sync_deals = %s, auto_create_contacts = %s
                       WHERE id = (SELECT MAX(id) FROM hubspot_integration)""",
                    tuple(sql_params)
                )
            else:
                # Insert
                sql_params = [
                    config.get('enabled', False),
                    config.get('api_key_encrypted'),
                    config.get('portal_id'),
                    config.get('sync_contacts', True),
                    config.get('sync_deals', True),
                    config.get('auto_create_contacts', False)
                ]
                
                self.db.execute(
                    """INSERT INTO hubspot_integration 
                       (enabled, api_key_encrypted, portal_id, sync_contacts, sync_deals, auto_create_contacts)
                       VALUES (?, ?, ?, ?, ?, ?)"""
                    if self.db.db_type == 'sqlite'
                    else """INSERT INTO hubspot_integration 
                       (enabled, api_key_encrypted, portal_id, sync_contacts, sync_deals, auto_create_contacts)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    tuple(sql_params)
                )

            self.enabled = config.get('enabled', False)
            self.logger.info("Updated HubSpot integration config")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update HubSpot config: {e}")
            return False

    def sync_contact(self, contact_data: Dict) -> bool:
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

        # Framework implementation
        # TODO: Integrate with HubSpot Contacts API
        # - POST /crm/v3/objects/contacts
        # - Update existing contacts
        # - Handle API rate limits

        self._log_activity('hubspot', 'sync_contact', 'pending', str(contact_data))
        return True

    def create_deal(self, deal_data: Dict) -> bool:
        """
        Create deal in HubSpot
        Framework method - integrates with HubSpot API

        Args:
            deal_data: Deal information

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        # Framework implementation
        # TODO: Integrate with HubSpot Deals API
        # - POST /crm/v3/objects/deals
        # - Associate with contacts
        # - Set deal properties

        self._log_activity('hubspot', 'create_deal', 'pending', str(deal_data))
        return True

    def _log_activity(self, integration_type: str, action: str, status: str, details: str):
        """Log integration activity"""
        try:
            self.db.execute(
                """INSERT INTO integration_activity_log 
                   (integration_type, action, status, details)
                   VALUES (?, ?, ?, ?)"""
                if self.db.db_type == 'sqlite'
                else """INSERT INTO integration_activity_log 
                   (integration_type, action, status, details)
                   VALUES (%s, %s, %s, %s)""",
                (integration_type, action, status, details)
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

    def get_config(self) -> Optional[Dict]:
        """
        Get Zendesk integration configuration

        Returns:
            Configuration dict or None
        """
        try:
            result = self.db.execute(
                "SELECT * FROM zendesk_integration ORDER BY id DESC LIMIT 1"
            )

            if result and result[0]:
                row = result[0]
                self.enabled = bool(row[1])
                return {
                    'enabled': bool(row[1]),
                    'subdomain': row[2],
                    'email': row[4],
                    'auto_create_tickets': bool(row[5]),
                    'default_priority': row[6]
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get Zendesk config: {e}")
            return None

    def update_config(self, config: Dict) -> bool:
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
                    config.get('enabled', False),
                    config.get('subdomain'),
                    config.get('api_token_encrypted'),
                    config.get('email'),
                    config.get('auto_create_tickets', False),
                    config.get('default_priority', 'normal')
                ]
                
                self.db.execute(
                    """UPDATE zendesk_integration 
                       SET enabled = ?, subdomain = ?, api_token_encrypted = ?,
                           email = ?, auto_create_tickets = ?, default_priority = ?
                       WHERE id = (SELECT MAX(id) FROM zendesk_integration)"""
                    if self.db.db_type == 'sqlite'
                    else """UPDATE zendesk_integration 
                       SET enabled = %s, subdomain = %s, api_token_encrypted = %s,
                           email = %s, auto_create_tickets = %s, default_priority = %s
                       WHERE id = (SELECT MAX(id) FROM zendesk_integration)""",
                    tuple(sql_params)
                )
            else:
                # Insert
                sql_params = [
                    config.get('enabled', False),
                    config.get('subdomain'),
                    config.get('api_token_encrypted'),
                    config.get('email'),
                    config.get('auto_create_tickets', False),
                    config.get('default_priority', 'normal')
                ]
                
                self.db.execute(
                    """INSERT INTO zendesk_integration 
                       (enabled, subdomain, api_token_encrypted, email, auto_create_tickets, default_priority)
                       VALUES (?, ?, ?, ?, ?, ?)"""
                    if self.db.db_type == 'sqlite'
                    else """INSERT INTO zendesk_integration 
                       (enabled, subdomain, api_token_encrypted, email, auto_create_tickets, default_priority)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    tuple(sql_params)
                )

            self.enabled = config.get('enabled', False)
            self.logger.info("Updated Zendesk integration config")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update Zendesk config: {e}")
            return False

    def create_ticket(self, ticket_data: Dict) -> Optional[str]:
        """
        Create ticket in Zendesk
        Framework method - integrates with Zendesk API

        Args:
            ticket_data: Ticket information

        Returns:
            Ticket ID or None
        """
        if not self.enabled:
            return None

        # Framework implementation
        # TODO: Integrate with Zendesk Tickets API
        # - POST /api/v2/tickets
        # - Set requester, subject, description
        # - Handle priority and tags

        self._log_activity('zendesk', 'create_ticket', 'pending', str(ticket_data))
        return f"ticket-{int(datetime.now().timestamp())}"

    def update_ticket(self, ticket_id: str, update_data: Dict) -> bool:
        """
        Update ticket in Zendesk
        Framework method - integrates with Zendesk API

        Args:
            ticket_id: Ticket ID
            update_data: Update information

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        # Framework implementation
        # TODO: Integrate with Zendesk Tickets API
        # - PUT /api/v2/tickets/{ticket_id}
        # - Update status, priority, assignee

        self._log_activity('zendesk', 'update_ticket', 'pending', 
                          f"{ticket_id}: {update_data}")
        return True

    def _log_activity(self, integration_type: str, action: str, status: str, details: str):
        """Log integration activity"""
        try:
            self.db.execute(
                """INSERT INTO integration_activity_log 
                   (integration_type, action, status, details)
                   VALUES (?, ?, ?, ?)"""
                if self.db.db_type == 'sqlite'
                else """INSERT INTO integration_activity_log 
                   (integration_type, action, status, details)
                   VALUES (%s, %s, %s, %s)""",
                (integration_type, action, status, details)
            )
        except Exception as e:
            self.logger.error(f"Failed to log integration activity: {e}")

    def get_activity_log(self, limit: int = 100) -> List[Dict]:
        """
        Get integration activity log

        Args:
            limit: Maximum number of records

        Returns:
            List of activity dictionaries
        """
        try:
            result = self.db.execute(
                """SELECT * FROM integration_activity_log 
                   ORDER BY created_at DESC LIMIT ?"""
                if self.db.db_type == 'sqlite'
                else """SELECT * FROM integration_activity_log 
                   ORDER BY created_at DESC LIMIT %s""",
                (limit,)
            )

            activities = []
            for row in (result or []):
                activities.append({
                    'integration_type': row[1],
                    'action': row[2],
                    'status': row[3],
                    'details': row[4],
                    'created_at': row[5]
                })

            return activities

        except Exception as e:
            self.logger.error(f"Failed to get activity log: {e}")
            return []
