"""
EspoCRM Integration (Free, Open-Source Alternative to Salesforce/HubSpot)
Enables contact management, deal tracking, and call logging
"""

from datetime import datetime, timezone

from pbx.utils.logger import get_logger

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class EspoCRMIntegration:
    """EspoCRM integration handler (100% Free & Open Source)"""

    def __init__(self, config: dict):
        """
        Initialize EspoCRM integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get("integrations.espocrm.enabled", False)

        # EspoCRM server details
        self.api_url = config.get("integrations.espocrm.api_url")
        if self.api_url and not self.api_url.endswith("/api/v1"):
            if not self.api_url.endswith("/"):
                self.api_url += "/"
            self.api_url += "api/v1"

        # Authentication
        self.api_key = config.get("integrations.espocrm.api_key")
        self.api_secret = config.get("integrations.espocrm.api_secret")

        # Feature flags
        self.auto_create_contacts = config.get("integrations.espocrm.auto_create_contacts", True)
        self.auto_log_calls = config.get("integrations.espocrm.auto_log_calls", True)
        self.screen_pop = config.get("integrations.espocrm.screen_pop", True)

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.error(
                    "EspoCRM integration requires 'requests' library. "
                    "Install with: pip install requests"
                )
                self.enabled = False
            elif not all([self.api_url, self.api_key]):
                self.logger.error("EspoCRM integration requires api_url and api_key")
                self.enabled = False
            else:
                self.logger.info(f"EspoCRM integration enabled (Server: {self.api_url})")

    def _make_request(
        self, method: str, endpoint: str, data: dict = None, params: dict = None
    ) -> dict | None:
        """
        Make authenticated API request to EspoCRM

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: URL parameters

        Returns:
            Response data or None on error
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return None

        try:
            url = f"{self.api_url}/{endpoint}"

            headers = {"X-Api-Key": self.api_key, "Content-type": "application/json"}

            response = requests.request(
                method=method, url=url, json=data, params=params, headers=headers, timeout=10
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                self.logger.error(f"EspoCRM API error: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            self.logger.error(f"EspoCRM API request failed: {e}")
            return None

    def find_contact_by_phone(self, phone_number: str) -> dict | None:
        """
        Find contact by phone number (screen pop)

        Args:
            phone_number: Phone number to search

        Returns:
            Contact details or None
        """
        if not self.enabled:
            return None

        try:
            # Clean phone number (remove non-digits)
            clean_phone = "".join(c for c in phone_number if c.isdigit())

            # Search contacts by phone
            params = {
                "where": [
                    {
                        "type": "or",
                        "value": [
                            {"type": "contains", "attribute": "phoneNumber", "value": clean_phone},
                            {
                                "type": "contains",
                                "attribute": "phoneNumberMobile",
                                "value": clean_phone,
                            },
                        ],
                    }
                ],
                "maxSize": 1,
            }

            result = self._make_request("GET", "Contact", params=params)

            if result and result.get("list"):
                contact = result["list"][0]
                self.logger.info(f"Found contact in EspoCRM: {contact.get('name')}")
                return contact

            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to find contact: {e}")
            return None

    def create_contact(
        self, name: str, phone: str, email: str = None, company: str = None, title: str = None
    ) -> dict | None:
        """
        Create new contact in EspoCRM

        Args:
            name: Contact name
            phone: Phone number
            email: Email address
            company: Company/account name
            title: Job title

        Returns:
            Created contact details or None
        """
        if not self.enabled or not self.auto_create_contacts:
            return None

        try:
            # Split name into first/last
            name_parts = name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            data = {"firstName": first_name, "lastName": last_name, "phoneNumber": phone}

            if email:
                data["emailAddress"] = email
            if title:
                data["title"] = title
            if company:
                data["accountName"] = company

            result = self._make_request("POST", "Contact", data=data)

            if result:
                self.logger.info(f"Created contact in EspoCRM: {result.get('id')}")
                return result

            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to create contact: {e}")
            return None

    def log_call(
        self, contact_id: str, direction: str, duration: int, status: str, description: str = None
    ) -> dict | None:
        """
        Log call activity in EspoCRM

        Args:
            contact_id: EspoCRM contact ID
            direction: 'Inbound' or 'Outbound'
            duration: Call duration in seconds
            status: 'Held', 'Not Held'
            description: Additional notes

        Returns:
            Created call record or None
        """
        if not self.enabled or not self.auto_log_calls:
            return None

        try:
            data = {
                "name": f"{direction} Call",
                "status": status,
                "direction": direction,
                "duration": duration,
                "contactsIds": [contact_id],
                "dateStart": datetime.now(timezone.utc).isoformat(),
            }

            if description:
                data["description"] = description

            result = self._make_request("POST", "Call", data=data)

            if result:
                self.logger.info(f"Logged call in EspoCRM: {result.get('id')}")
                return result

            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to log call: {e}")
            return None

    def get_contact(self, contact_id: str) -> dict | None:
        """
        Get contact details by ID

        Args:
            contact_id: EspoCRM contact ID

        Returns:
            Contact details or None
        """
        if not self.enabled:
            return None

        try:
            result = self._make_request("GET", f"Contact/{contact_id}")
            return result

        except requests.RequestException as e:
            self.logger.error(f"Failed to get contact: {e}")
            return None

    def update_contact(self, contact_id: str, updates: dict) -> dict | None:
        """
        Update contact information

        Args:
            contact_id: EspoCRM contact ID
            updates: Fields to update

        Returns:
            Updated contact or None
        """
        if not self.enabled:
            return None

        try:
            result = self._make_request("PUT", f"Contact/{contact_id}", data=updates)

            if result:
                self.logger.info(f"Updated contact: {contact_id}")
                return result

            return None

        except requests.RequestException as e:
            self.logger.error(f"Failed to update contact: {e}")
            return None

    def search_contacts(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search contacts by name or email

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            list of matching contacts
        """
        if not self.enabled:
            return []

        try:
            params = {
                "where": [
                    {
                        "type": "or",
                        "value": [
                            {"type": "contains", "attribute": "name", "value": query},
                            {"type": "contains", "attribute": "emailAddress", "value": query},
                        ],
                    }
                ],
                "maxSize": max_results,
            }

            result = self._make_request("GET", "Contact", params=params)

            if result and result.get("list"):
                return result["list"]

            return []

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to search contacts: {e}")
            return []

    def create_opportunity(
        self,
        name: str,
        amount: float,
        contact_id: str = None,
        account_id: str = None,
        stage: str = "Prospecting",
        close_date: str = None,
    ) -> dict | None:
        """
        Create sales opportunity/deal

        Args:
            name: Opportunity name
            amount: Deal value
            contact_id: Associated contact ID
            account_id: Associated account ID
            stage: Sales stage
            close_date: Expected close date (YYYY-MM-DD)

        Returns:
            Created opportunity or None
        """
        if not self.enabled:
            return None

        try:
            data = {"name": name, "amount": amount, "stage": stage}

            if contact_id:
                data["contactsIds"] = [contact_id]
            if account_id:
                data["accountId"] = account_id
            if close_date:
                data["closeDate"] = close_date

            result = self._make_request("POST", "Opportunity", data=data)

            if result:
                self.logger.info(f"Created opportunity in EspoCRM: {result.get('id')}")
                return result

            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to create opportunity: {e}")
            return None

    def get_recent_activities(self, contact_id: str, limit: int = 10) -> list[dict]:
        """
        Get recent activities for a contact

        Args:
            contact_id: EspoCRM contact ID
            limit: Maximum activities to return

        Returns:
            list of activities
        """
        if not self.enabled:
            return []

        try:
            # Get calls
            params = {
                "where": [{"type": "linkedWith", "attribute": "contacts", "value": [contact_id]}],
                "maxSize": limit,
                "orderBy": "dateStart",
                "order": "desc",
            }

            result = self._make_request("GET", "Call", params=params)

            if result and result.get("list"):
                return result["list"]

            return []

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to get activities: {e}")
            return []

    def handle_incoming_call(self, caller_id: str, extension: str) -> dict:
        """
        Handle incoming call event for screen pop

        Args:
            caller_id: Incoming caller ID
            extension: Extension receiving the call

        Returns:
            Dictionary with contact info and screen pop URL
        """
        if not self.enabled or not self.screen_pop:
            return {"success": False}

        try:
            # Find contact
            contact = self.find_contact_by_phone(caller_id)

            if not contact and self.auto_create_contacts:
                # Create new contact
                contact = self.create_contact(name=f"Unknown - {caller_id}", phone=caller_id)

            if contact:
                # Get recent activities
                activities = self.get_recent_activities(contact["id"], limit=5)

                # Generate screen pop URL
                screen_pop_url = (
                    f"{self.api_url.replace('/api/v1', '')}/#Contact/view/{contact['id']}"
                )

                return {
                    "success": True,
                    "contact": contact,
                    "activities": activities,
                    "screen_pop_url": screen_pop_url,
                }

            return {"success": False, "reason": "Contact not found"}

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to handle incoming call: {e}")
            return {"success": False, "error": str(e)}

    def handle_call_completed(
        self, caller_id: str, extension: str, duration: int, direction: str
    ) -> bool:
        """
        Log completed call to CRM

        Args:
            caller_id: Phone number of other party
            extension: Extension involved in call
            duration: Call duration in seconds
            direction: 'Inbound' or 'Outbound'

        Returns:
            bool: Success status
        """
        if not self.enabled or not self.auto_log_calls:
            return False

        try:
            # Find contact
            contact = self.find_contact_by_phone(caller_id)

            if not contact and self.auto_create_contacts:
                contact = self.create_contact(name=f"Unknown - {caller_id}", phone=caller_id)

            if contact:
                # Log the call
                status = "Held" if duration > 0 else "Not Held"
                self.log_call(
                    contact_id=contact["id"],
                    direction=direction,
                    duration=duration,
                    status=status,
                    description=f"Extension {extension}",
                )
                return True

            return False

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to log completed call: {e}")
            return False


# Export class
__all__ = ["EspoCRMIntegration"]
